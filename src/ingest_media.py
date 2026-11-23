import argparse
import logging
import logging.handlers
import os
import shutil
import signal
import time
from pathlib import Path
 
try:  # not available on Windows (e.g. when running the tests on a dev machine)
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
 
from dotenv import load_dotenv
 
from src.helper_functions import (
    check_folder_not_empty,
    check_tmdb_name,
    check_tmdbid_in_name,
    check_valid_file_extension,
    check_year_in_name,
    get_list_file_paths,
    get_list_folder_paths,
    get_tmdb_details,
)
 
logger = logging.getLogger(__name__)
 
PATH_INGEST_MOVIES = Path("/mnt/storage/ingest/movies/ingest")
PATH_INGEST_TVSHOWS = Path("/mnt/storage/ingest/tvshows/ingest")
 
PATH_MEDIA_MOVIES = Path("/mnt/storage/files/media/movies")
PATH_MEDIA_TVSHOWS = Path("/mnt/storage/files/media/tvshows")
 
# Must NOT be inside the ingest folder, or it would be picked up as an ingest item.
PATH_FAILED_MOVIES = Path("/mnt/storage/ingest/movies/failed")
 
PATH_LOG_FILE = Path("/mnt/storage/ingest/ingest.log")
PATH_LOCK_FILE = Path("/mnt/storage/ingest/ingest.lock")
 
DEFAULT_INTERVAL_SECONDS = 15 * 60
DEFAULT_SETTLE_SECONDS = 5 * 60
 
load_dotenv()
API_KEY = os.getenv("API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")


def setup_logging(log_file: Path = PATH_LOG_FILE, level: int = logging.INFO) -> list[logging.Handler]:
    """Log to both the console and a file on disk (appending across runs)."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    console_handler = logging.StreamHandler()
    handlers = [file_handler, console_handler]

    root = logging.getLogger()
    root.setLevel(level)
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    return handlers


def check_movie_folder(folder_path: Path) -> tuple[list[Path], list[Path]]:
    """Validate a movie folder and the files in it.

    Returns
    -------
    tuple of list of Path
        ``(valid_files, failed_files)``. If the folder itself fails validation,
        every file in it is returned as failed.
    """
    logger.info(f"Checking folder: {folder_path}")
    files = get_list_file_paths(folder_path=folder_path)
    valid_files: list[Path] = []
    failed_files: list[Path] = []

    if not check_folder_not_empty(folder_path):
        logger.warning(f"Folder is empty (will be removed): {folder_path}")
        return valid_files, failed_files

    if not check_year_in_name(folder_path):
        logger.warning(f"Ingestion failed -- Folder name does not contain a valid year: {folder_path.name}")
        return valid_files, files

    if not check_tmdbid_in_name(folder_path):
        logger.warning(f"Ingestion failed -- Folder name does not contain a valid TMDB ID: {folder_path.name}")
        return valid_files, files

    tmdb_data = get_tmdb_details(name=folder_path, API_KEY=API_KEY, media_type="movies")
    if tmdb_data is None or "title" not in tmdb_data:
        logger.warning(f"Ingestion failed -- No TMDB data found for folder: {folder_path.name}")
        return valid_files, files
    _, folder_name_matches = check_tmdb_name(name=folder_path, tmdb_response=tmdb_data, media_type="movies")
    if not folder_name_matches:
        logger.warning(f"Ingestion failed -- Folder name does not match TMDB name: {folder_path.name}")
        return valid_files, files

    for file in files:
        if not check_year_in_name(file):
            logger.warning(f"Ingestion failed -- File name does not contain a valid year: {file.name}")
        elif not check_tmdbid_in_name(file):
            logger.warning(f"Ingestion failed -- File name does not contain a valid TMDB ID: {file.name}")
        elif not check_valid_file_extension(file):
            logger.warning(f"Ingestion failed -- File name does not have a valid extension: {file.name}")
        elif not check_tmdb_name(name=file, tmdb_response=tmdb_data, media_type="movies")[1]:
            logger.warning(f"Ingestion failed -- File name does not match TMDB name: {file.name}")
        else:
            valid_files.append(file)
            continue
        failed_files.append(file)

    return valid_files, failed_files


def convert_to_ingest_paths(ingest_path: Path, file_paths: list[Path]) -> list[tuple[Path, Path]]:
    """Return ``(destination, original)`` pairs: ``ingest_path / parent folder name / file name``."""
    destinations = [ingest_path / f.parent.name / f.name for f in file_paths]
    return list(zip(destinations, file_paths))


def _same_filesystem(src: Path, dest_dir: Path) -> bool:
    return os.stat(src).st_dev == os.stat(dest_dir).st_dev


def _safe_move(src: Path, dst: Path) -> None:
    """Move ``src`` to ``dst`` so that ``dst`` only ever appears complete.

    On the same filesystem this is an atomic rename. Across filesystems (e.g. two
    ZFS datasets) the file is copied to ``<name>.partial`` next to ``dst``, its size
    checked, renamed into place, and only then is the source deleted. If anything
    fails, the partial file is removed and the source is left untouched.
    """
    if _same_filesystem(src, dst.parent):
        src.rename(dst)
        return

    partial = dst.with_name(dst.name + ".partial")
    if partial.exists():
        logger.warning(f"Removing stale partial file from an earlier run: {partial}")
        partial.unlink()
    try:
        shutil.copy2(src, partial)
        if partial.stat().st_size != src.stat().st_size:
            raise OSError(f"Size mismatch after copying {src} to {partial}")
        partial.rename(dst)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    src.unlink()


def move_files(path_pairs: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    """Move ``(destination, original)`` pairs without ever overwriting anything.

    Folders are only created when they do not already exist. A file whose
    destination already exists is left where it is.

    Returns
    -------
    list of tuple of Path
        The pairs that were skipped because the destination already existed.
    """
    skipped = []
    for destination, original in path_pairs:
        if destination.exists():
            logger.warning(f"Skipping -- destination already exists: {destination} (source: {original})")
            skipped.append((destination, original))
            continue
        logger.info(f"Moving file {original} to {destination}")
        if not destination.parent.exists():
            destination.parent.mkdir(parents=True)
        _safe_move(original, destination)
    return skipped


def remove_empty_folders(folders: list[Path]) -> None:
    """Remove each given folder if (and only if) it is now empty."""
    for folder in folders:
        if folder.is_dir() and not any(folder.iterdir()):
            logger.info(f"Removing empty folder: {folder}")
            folder.rmdir()
        elif folder.is_dir():
            logger.warning(f"Folder not empty, leaving in place: {folder}")


def ingest_movies():
    folders = get_list_folder_paths(folder_path=PATH_INGEST_MOVIES)

    valid_files: list[Path] = []
    failed_files: list[Path] = []
    for folder in folders:
        valid, failed = check_movie_folder(folder)
        valid_files += valid
        failed_files += failed

    skipped = move_files(convert_to_ingest_paths(PATH_MEDIA_MOVIES, valid_files))
    failed_files += [original for _, original in skipped]

    still_stuck = move_files(convert_to_ingest_paths(PATH_FAILED_MOVIES, failed_files))

    remove_empty_folders(folders)

    logger.info(
        f"Done: {len(valid_files) - len(skipped)} ingested, "
        f"{len(failed_files) - len(still_stuck)} quarantined, "
        f"{len(still_stuck)} could not be moved"
    )


def run_locked(job, lock_file: Path | None = None) -> bool:
    """Run ``job`` unless another ingest holds the lock. Returns whether it ran."""
    if fcntl is None:  # pragma: no cover
        logger.warning("fcntl unavailable: running without a lock")
        job()
        return True
    lock_file = lock_file or PATH_LOCK_FILE
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_file, "a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.warning("Previous ingest is still running; skipping this run")
            return False
        job()
        return True
 
 
def run_forever(job, interval, *, clock=time.monotonic, sleep=time.sleep, max_cycles=None) -> None:
    """Call ``job`` every ``interval`` seconds, never overlapping itself.
 
    If a run takes longer than the interval, the scheduled runs it overran are
    skipped and the next one starts at the following interval boundary. A failing
    run is logged and retried at the next interval.
    """
    next_run = clock()
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        try:
            job()
        except Exception:
            logger.exception("Ingest run failed; will retry at the next interval")
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            break
 
        next_run += interval
        now = clock()
        if now >= next_run:
            missed = int((now - next_run) // interval) + 1
            logger.warning(f"Run overran the {interval}s interval; skipping {missed} scheduled run(s)")
            next_run += missed * interval
        sleep(max(0.0, next_run - clock()))
 
 
def install_signal_handlers() -> None:
    """Turn SIGTERM (``docker stop``) into SystemExit so in-flight copies clean up."""
    def handler(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, handler)
 
 
def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest movies from the ingest folder into the media library.")
    parser.add_argument("--loop", action="store_true", help="run forever instead of once")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS,
                        help="seconds between runs in --loop mode (default: 900)")
    parser.add_argument("--settle", type=int, default=DEFAULT_SETTLE_SECONDS,
                        help="ignore folders changed within this many seconds (default: 300)")
    return parser.parse_args(argv)
 
 
def main(argv=None):
    args = parse_args(argv)
    setup_logging()
    if not API_KEY:
        logger.error("API_KEY is not set (check your .env / environment)")
        raise SystemExit(1)
 
    def job():
        run_locked(lambda: ingest_movies(settle_seconds=args.settle))
 
    install_signal_handlers()
    logger.info(f"Starting ingest ({'every %ds' % args.interval if args.loop else 'single run'}, settle {args.settle}s)")
    if args.loop:
        run_forever(job, args.interval)
    else:
        try:
            job()
        except Exception:
            logger.exception("Ingest aborted")
            raise
 
 
if __name__ == "__main__":
    main()