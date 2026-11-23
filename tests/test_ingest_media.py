"""Test the media ingestion functionality."""

from pathlib import Path

import pytest

from src import ingest_media

import logging

import pytest
import requests

import src.ingest_media as ingest
from tests.conftest import make_movie

GATTACA = "Gattaca (1997) [tmdbid-782]"
ALIEN = "Alien (1979) [tmdbid-348]"

MOVIES_INPUTS = Path(__file__).parent / "tests_inputs" / "movies"


@pytest.mark.parametrize(
    "folder_name, expect_failed_files",
    [
        ("empty movie folder (1999) [tmdbid-1234]", False),
        ("title (200) [tmdbid-1234]", True),
        ("title (2000) [tmdid-1234]", True),
    ],
)
def test_check_folder_rejects_empty_or_invalid_folder_names(
    monkeypatch, folder_name, expect_failed_files
):
    folder_path = MOVIES_INPUTS / folder_name

    def fail_if_called(**kwargs):
        pytest.fail("TMDB lookup should not run for an invalid folder")

    monkeypatch.setattr(ingest_media, "get_tmdb_details", fail_if_called)

    valid_files, failed_files = ingest_media.check_movie_folder(folder_path)
    assert valid_files == []
    if expect_failed_files:
        assert set(failed_files) == {
            path for path in folder_path.iterdir() if path.is_file()
        }
    else:
        assert failed_files == []


def test_check_folder_returns_only_valid_matching_movie_files(monkeypatch):
    folder_path = MOVIES_INPUTS / "title (2000) [tmdbid-1234]"
    accepted_paths = {
        folder_path,
        folder_path / "title (2000) [tmdbid-1234].mp4",
        folder_path / "title (2000) [tmdbid-1234] - 576p.mp4",
    }
    expected_failed_paths = {
        folder_path / "title (200) [tmdbid-1234].mp4",
        folder_path / "incorrect_title (2000) [tmdbid-1234].mp4",
        folder_path / "title (2000) [tmdbid-4321].mp4",
    }
    requested_details = []

    def get_details(name, API_KEY, media_type):
        requested_details.append((name, API_KEY, media_type))
        return {"title": "title"}

    def check_name(name, tmdb_response, media_type):
        return tmdb_response["title"], name in accepted_paths

    monkeypatch.setattr(ingest_media, "API_KEY", "test-api-key")
    monkeypatch.setattr(ingest_media, "get_tmdb_details", get_details)
    monkeypatch.setattr(ingest_media, "check_tmdb_name", check_name)

    valid_files, failed_files = ingest_media.check_movie_folder(
        folder_path
    )

    assert set(valid_files) == accepted_paths - {folder_path}
    assert set(failed_files) == expected_failed_paths
    assert requested_details == [(folder_path, "test-api-key", "movies")]


def tree(root):
    """All files under root as relative posix strings (for whole-tree assertions)."""
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
 
 
class TestCheckMovieFolder:
    def test_valid_folder(self, dirs):
        d = make_movie(dirs[0], GATTACA, [f"{GATTACA}.mp4"])
        assert ingest.check_movie_folder(d) == ([d / f"{GATTACA}.mp4"], [])
 
    def test_empty_folder(self, dirs):
        d = make_movie(dirs[0], GATTACA, [])
        assert ingest.check_movie_folder(d) == ([], [])
 
    @pytest.mark.parametrize("folder", [
        "Gattaca [tmdbid-782]",          # no year
        "Gattaca (1997)",                # no id
        "Gattaca (1997) [tmdbid-999]",   # id unknown to TMDB
        "Alien (1979) [tmdbid-782]",     # title mismatches TMDB
    ])
    def test_bad_folder_fails_every_file(self, dirs, folder):
        d = make_movie(dirs[0], folder, [f"{folder}.mp4", "notes.txt"])
        valid, failed = ingest.check_movie_folder(d)
        assert valid == []
        assert sorted(failed) == sorted([d / f"{folder}.mp4", d / "notes.txt"])
 
    def test_bad_files_failed_good_kept(self, dirs):
        good = f"{GATTACA}.mp4"
        bad = [f"{GATTACA}.srt", "Gattaca [tmdbid-782].mp4", "Gattaca (1997).mp4", "Alien (1979) [tmdbid-782].mp4"]
        d = make_movie(dirs[0], GATTACA, [good, *bad])
        valid, failed = ingest.check_movie_folder(d)
        assert valid == [d / good]
        assert sorted(failed) == sorted(d / b for b in bad)
 
    def test_folder_with_dot_in_title(self, dirs):
        name = "Mr. Nobody (2009) [tmdbid-187]"
        d = make_movie(dirs[0], name, [f"{name}.mkv"])
        assert ingest.check_movie_folder(d)[0] == [d / f"{name}.mkv"]
 
    def test_tmdb_error_payload_fails_files(self, dirs):
        name = "Whatever (2000) [tmdbid-999999]"
        d = make_movie(dirs[0], name, [f"{name}.mp4"])
        valid, failed = ingest.check_movie_folder(d)
        assert valid == [] and failed == [d / f"{name}.mp4"]
 
 
class TestConvertToIngestPaths:
    def test_destination_is_under_given_root(self, tmp_path):
        src = tmp_path / "ingest" / GATTACA / f"{GATTACA}.mp4"
        root = tmp_path / "media"
        assert ingest.convert_to_ingest_paths(root, [src]) == [(root / GATTACA / f"{GATTACA}.mp4", src)]
 
 
class TestMoveFiles:
    def test_creates_missing_folders_and_moves(self, tmp_path):
        src = tmp_path / "a" / "f.mp4"
        src.parent.mkdir()
        src.write_text("data")
        dst = tmp_path / "x" / "y" / "f.mp4"
        assert ingest.move_files([(dst, src)]) == []
        assert dst.read_text() == "data" and not src.exists()
 
    def test_never_overwrites_and_reports_skipped(self, tmp_path):
        src = tmp_path / "a" / "f.mp4"
        src.parent.mkdir()
        src.write_text("new")
        dst = tmp_path / "lib" / "f.mp4"
        dst.parent.mkdir()
        dst.write_text("old")
        assert ingest.move_files([(dst, src)]) == [(dst, src)]
        assert dst.read_text() == "old"
        assert src.read_text() == "new"
 
    def test_existing_folder_not_recreated(self, tmp_path, monkeypatch):
        src = tmp_path / "a" / "f.mp4"
        src.parent.mkdir()
        src.write_text("data")
        dst = tmp_path / "lib" / "Movie" / "f.mp4"
        dst.parent.mkdir(parents=True)
        (dst.parent / "other.mkv").write_text("keep")
        calls = []
        real_mkdir = type(dst).mkdir
        def spy(self, *a, **k):
            calls.append(self)
            return real_mkdir(self, *a, **k)
        monkeypatch.setattr(type(dst), "mkdir", spy)
        ingest.move_files([(dst, src)])
        assert dst.parent not in calls
        assert (dst.parent / "other.mkv").read_text() == "keep"
 
    def test_one_collision_does_not_stop_the_rest(self, tmp_path):
        s1, s2 = tmp_path / "s" / "1.mp4", tmp_path / "s" / "2.mp4"
        s1.parent.mkdir()
        s1.write_text("1"); s2.write_text("2")
        d1, d2 = tmp_path / "lib" / "1.mp4", tmp_path / "lib" / "2.mp4"
        d1.parent.mkdir()
        d1.write_text("old")
        ingest.move_files([(d1, s1), (d2, s2)])
        assert d1.read_text() == "old" and d2.read_text() == "2"
 
    def test_collision_is_logged(self, tmp_path, caplog):
        src = tmp_path / "f.mp4"; src.write_text("n")
        dst = tmp_path / "lib" / "f.mp4"; dst.parent.mkdir(); dst.write_text("o")
        with caplog.at_level(logging.WARNING):
            ingest.move_files([(dst, src)])
        assert any("already exists" in r.message for r in caplog.records)
 
 
class TestCrossFilesystemMove:
    @pytest.fixture
    def cross(self, monkeypatch):
        monkeypatch.setattr(ingest, "_same_filesystem", lambda s, d: False)
 
    @pytest.fixture
    def pair(self, tmp_path):
        src = tmp_path / "a" / "f.mp4"
        src.parent.mkdir()
        src.write_text("data")
        return tmp_path / "lib" / "Movie" / "f.mp4", src
 
    def test_copy_then_delete(self, pair, cross):
        dst, src = pair
        assert ingest.move_files([(dst, src)]) == []
        assert dst.read_text() == "data" and not src.exists()
        assert [p.name for p in dst.parent.iterdir()] == ["f.mp4"]   # no .partial left behind
 
    def test_failed_copy_leaves_source_and_no_destination(self, pair, cross, monkeypatch):
        dst, src = pair
        def boom(s, d):
            Path(d).write_text("half")
            raise OSError("disk full")
        monkeypatch.setattr(ingest.shutil, "copy2", boom)
        with pytest.raises(OSError):
            ingest.move_files([(dst, src)])
        assert src.read_text() == "data"
        assert not dst.exists()
        assert list(dst.parent.iterdir()) == []
 
    def test_size_mismatch_is_rejected(self, pair, cross, monkeypatch):
        dst, src = pair
        monkeypatch.setattr(ingest.shutil, "copy2", lambda s, d: Path(d).write_text("da"))
        with pytest.raises(OSError):
            ingest.move_files([(dst, src)])
        assert src.exists() and not dst.exists() and list(dst.parent.iterdir()) == []
 
    def test_stale_partial_from_earlier_run_is_replaced(self, pair, cross):
        dst, src = pair
        dst.parent.mkdir(parents=True)
        (dst.parent / "f.mp4.partial").write_text("junk from a crash")
        ingest.move_files([(dst, src)])
        assert dst.read_text() == "data"
        assert [p.name for p in dst.parent.iterdir()] == ["f.mp4"]
 
    def test_same_filesystem_uses_plain_rename(self, pair, monkeypatch):
        dst, src = pair
        def no_copy(*a, **k):
            raise AssertionError("copy should not be used on the same filesystem")
        monkeypatch.setattr(ingest.shutil, "copy2", no_copy)
        ingest.move_files([(dst, src)])
        assert dst.read_text() == "data" and not src.exists()
 
 
class TestRemoveEmptyFolders:
    def test_removes_only_empty(self, tmp_path):
        empty, full, nested = tmp_path / "empty", tmp_path / "full", tmp_path / "nested"
        empty.mkdir()
        full.mkdir(); (full / "f").write_text("x")
        (nested / "sub").mkdir(parents=True)
        ingest.remove_empty_folders([empty, full, nested])
        assert not empty.exists()
        assert full.exists() and nested.exists()   # nested has a (empty) subfolder: left alone
 
    def test_already_gone_is_fine(self, tmp_path):
        ingest.remove_empty_folders([tmp_path / "missing"])
 
 
class TestIngestMovies:
    def test_end_to_end(self, dirs):
        ingest_dir, media_dir, failed_dir = dirs
        make_movie(ingest_dir, GATTACA, [f"{GATTACA}.mp4", f"{GATTACA}.srt"])
        make_movie(ingest_dir, "Bad Folder", ["x.mp4", "y.mkv"])
        ingest.ingest_movies()
 
        assert tree(media_dir) == [f"{GATTACA}/{GATTACA}.mp4"]
        assert tree(failed_dir) == sorted([f"{GATTACA}/{GATTACA}.srt", "Bad Folder/x.mp4", "Bad Folder/y.mkv"])
        assert (media_dir / GATTACA / f"{GATTACA}.mp4").read_text() == f"content of {GATTACA}.mp4"
        assert ingest_dir.is_dir() and list(ingest_dir.iterdir()) == []   # all folders removed, root kept
 
    def test_valid_file_collision_is_quarantined_not_overwritten(self, dirs):
        ingest_dir, media_dir, failed_dir = dirs
        make_movie(media_dir, GATTACA, [f"{GATTACA}.mp4"])
        (media_dir / GATTACA / f"{GATTACA}.mp4").write_text("ORIGINAL")
        make_movie(ingest_dir, GATTACA, [f"{GATTACA}.mp4"])
        ingest.ingest_movies()
        assert (media_dir / GATTACA / f"{GATTACA}.mp4").read_text() == "ORIGINAL"
        assert tree(failed_dir) == [f"{GATTACA}/{GATTACA}.mp4"]
        assert not (ingest_dir / GATTACA).exists()
 
    def test_existing_failed_file_not_overwritten_and_source_kept(self, dirs):
        ingest_dir, media_dir, failed_dir = dirs
        make_movie(failed_dir, "Bad Folder", ["x.mp4"])
        (failed_dir / "Bad Folder" / "x.mp4").write_text("EARLIER")
        make_movie(ingest_dir, "Bad Folder", ["x.mp4"])
        ingest.ingest_movies()
        assert (failed_dir / "Bad Folder" / "x.mp4").read_text() == "EARLIER"
        assert (ingest_dir / "Bad Folder" / "x.mp4").exists()   # nothing lost, folder kept
 
    def test_adds_to_existing_library_folder(self, dirs):
        ingest_dir, media_dir, _ = dirs
        make_movie(media_dir, GATTACA, [f"{GATTACA} - 1080p.mkv"])
        make_movie(ingest_dir, GATTACA, [f"{GATTACA}.mp4"])
        ingest.ingest_movies()
        assert tree(media_dir) == sorted([f"{GATTACA}/{GATTACA} - 1080p.mkv", f"{GATTACA}/{GATTACA}.mp4"])
 
    def test_empty_folder_is_removed(self, dirs):
        ingest_dir, _, failed_dir = dirs
        make_movie(ingest_dir, GATTACA, [])
        ingest.ingest_movies()
        assert list(ingest_dir.iterdir()) == []
        assert not failed_dir.exists()
 
    def test_empty_ingest(self, dirs):
        ingest.ingest_movies()
 
    def test_multiple_movies(self, dirs):
        ingest_dir, media_dir, _ = dirs
        make_movie(ingest_dir, GATTACA, [f"{GATTACA}.mp4"])
        make_movie(ingest_dir, ALIEN, [f"{ALIEN}.mkv"])
        ingest.ingest_movies()
        assert tree(media_dir) == sorted([f"{GATTACA}/{GATTACA}.mp4", f"{ALIEN}/{ALIEN}.mkv"])
 
    def test_subfolders_are_left_alone(self, dirs):
        ingest_dir, media_dir, failed_dir = dirs
        d = make_movie(ingest_dir, GATTACA, [f"{GATTACA}.mp4"])
        (d / "extras").mkdir()
        (d / "extras" / "behind.mkv").write_text("x")
        ingest.ingest_movies()
        assert (d / "extras" / "behind.mkv").exists()   # folder kept because it isn't empty
 
    def test_tmdb_outage_aborts_before_anything_moves(self, dirs, monkeypatch):
        ingest_dir, media_dir, failed_dir = dirs
        make_movie(ingest_dir, GATTACA, [f"{GATTACA}.mp4"])
        make_movie(ingest_dir, ALIEN, [f"{ALIEN}.mkv"])
        real = ingest.get_tmdb_details
        def flaky(name, API_KEY, media_type):
            if "348" in name.name:
                raise requests.ConnectionError("down")
            return real(name, API_KEY, media_type)
        monkeypatch.setattr(ingest, "get_tmdb_details", flaky)
        with pytest.raises(requests.ConnectionError):
            ingest.ingest_movies()
        assert tree(ingest_dir) == sorted([f"{GATTACA}/{GATTACA}.mp4", f"{ALIEN}/{ALIEN}.mkv"])
        assert list(media_dir.iterdir()) == []
        assert not failed_dir.exists()
 
 
@pytest.fixture
def clean_root_logger():
    root = logging.getLogger()
    before, level = list(root.handlers), root.level
    yield
    for h in list(root.handlers):
        if h not in before:
            root.removeHandler(h)
            h.close()
    root.setLevel(level)
 
 
class TestLogging:
    def test_creates_file_and_parent_dirs(self, tmp_path, clean_root_logger):
        log_file = tmp_path / "logs" / "deep" / "ingest.log"
        handlers = ingest.setup_logging(log_file)
        logging.getLogger("src.ingest_media").warning("hello log")
        for h in handlers:
            h.flush()
        text = log_file.read_text()
        assert "hello log" in text and "WARNING" in text and "src.ingest_media" in text
 
    def test_appends_across_runs(self, tmp_path, clean_root_logger):
        log_file = tmp_path / "ingest.log"
        for msg in ("first run", "second run"):
            handlers = ingest.setup_logging(log_file)
            logging.getLogger("x").info(msg)
            for h in handlers:
                h.flush(); logging.getLogger().removeHandler(h); h.close()
        text = log_file.read_text()
        assert "first run" in text and "second run" in text
 
    def test_ingest_run_is_written_to_file(self, dirs, tmp_path, clean_root_logger):
        ingest_dir, _, _ = dirs
        make_movie(ingest_dir, "Bad Folder", ["x.mp4"])
        log_file = tmp_path / "ingest.log"
        handlers = ingest.setup_logging(log_file)
        ingest.ingest_movies()
        for h in handlers:
            h.flush()
        text = log_file.read_text()
        assert "Folder name does not contain a valid year: Bad Folder" in text
        assert "Moving file" in text and "Done:" in text