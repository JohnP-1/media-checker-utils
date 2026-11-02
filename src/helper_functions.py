import logging
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

log = logging.getLogger(__name__)


SUFFIXES_TO_REMOVE = [
    "-dvd1",
    " - dvd1",
    "-dvd2",
    " - dvd2",
    " - 576p",
    " - 1080p",
    " - Directors Cut",
    " - Theatrical Cut",
    " - Final Cut",
]

NORMALISE_SYMBOLS = [
    ":",
    "-",
    "_",
    "'",
    " ",
]

PATTERN = re.compile(r"\s*\(\d{4}\)\s*\[tmdbid-\d+\].*$")

VALID_FILE_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov"]


def check_files_match_folder(folder_path: Path) -> tuple[str, str]:
    """Separate files by whether their names match the containing folder.

    Remove recognized release suffixes from each file stem before comparing it
    with the folder name.

    Parameters
    ----------
    folder_path : Path
        Folder whose immediate files to compare.

    Returns
    -------
    tuple of list of Path
        Lists of matching and non-matching file paths, respectively.
    """
    folder = folder_path.name
    files = get_list_file_paths(folder_path=folder_path)
    file_paths_match = []
    file_paths_not_match = []

    for file in files:
        file_name = file.stem
        for suffix in SUFFIXES_TO_REMOVE:
            file_name = file_name.replace(suffix, "")
        if file_name != folder:
            file_paths_not_match.append(file)
        else:
            file_paths_match.append(file)

    return file_paths_match, file_paths_not_match


def check_file_matches_folder(folder: Path, file_name: Path) -> bool:
    """Check whether a file name matches its folder name.

    Remove recognized release suffixes from the file stem before comparing it
    with the folder name.

    Parameters
    ----------
    folder : Path
        Folder whose name to compare against.
    file_name : Path
        File path whose stem to compare.

    Returns
    -------
    bool
        Whether the trimmed file stem matches the folder name.
    """
    file_name_trimmed = file_name.stem
    for suffix in SUFFIXES_TO_REMOVE:
        file_name_trimmed = file_name_trimmed.replace(suffix, "")

    return folder.name == file_name_trimmed


def check_folder_not_empty(folder_path: Path):
    """Check whether a directory contains at least one entry.

    Parameters
    ----------
    folder_path : Path
        Directory to inspect.

    Returns
    -------
    bool
        Whether the directory contains any entries.

    Raises
    ------
    ValueError
        If ``folder_path`` is not a directory.
    """
    if not folder_path.is_dir():
        log.error(f"Provided path is not a directory: {folder_path}")
        raise ValueError(f"Provided path is not a directory: {folder_path}")
    return bool(len(os.listdir(folder_path)))


def check_tmdbid_in_name(check_path: Path) -> bool:
    """Check whether a path's name contains a TMDB ID marker.

    Parameters
    ----------
    check_path : Path
        Path whose name to inspect for a marker such as ``[tmdbid-123]``.

    Returns
    -------
    bool
        Whether the name contains a TMDB ID marker with a numeric ID.
    """
    return bool(re.search(r"\[tmdbid-\d+\]", str(check_path.name)))


def check_tmdb_name(name: Path, tmdb_response, media_type: str) -> bool:
    """Compare a media name with the title in a TMDB response.

    Normalize the media name and compare it with the response title. Select
    ``"title"`` for movies and ``"name"`` for TV shows.

    Parameters
    ----------
    name : Path
        Media path whose name to compare.
    tmdb_response : dict
        TMDB response containing the title for the selected media type.
    media_type : str
        Media type to check: ``"movies"`` or ``"tv_shows"``.

    Returns
    -------
    tuple
        TMDB title and a boolean indicating whether the names match.
    """
    if media_type == "movies":
        title_key = "title"
    elif media_type == "tv_shows":
        title_key = "name"

    normalized_name = PATTERN.sub("", name.stem)
    for symbol in NORMALISE_SYMBOLS:
        normalized_name = normalized_name.replace(symbol, "")

    normalized_tmdb_name = name
    for symbol in NORMALISE_SYMBOLS:
        normalized_tmdb_name = normalized_tmdb_name.replace(symbol, "")

    if normalized_tmdb_name in normalized_name:
        return tmdb_response[title_key], True
    return tmdb_response[title_key], False


def check_year_in_name(check_path: Path) -> bool:
    """Check whether a path's name contains a four-digit year in parentheses.

    Parameters
    ----------
    check_path : Path
        Path whose name to inspect.

    Returns
    -------
    bool
        Whether the name contains a year such as ``(2000)``.
    """
    return bool(re.search(r"\(\d{4}\)", str(check_path.name)))


def check_valid_file_extension(file_path: Path) -> bool:
    """Check whether a file has a supported media extension.

    Compare the extension case-insensitively with the supported extensions.

    Parameters
    ----------
    file_path : Path
        File path whose extension to check.

    Returns
    -------
    bool
        Whether the extension is supported.
    """
    return file_path.suffix.lower() in VALID_FILE_EXTENSIONS


def get_list_file_paths(folder_path: Path) -> list[Path]:
    """Return the immediate file paths contained in a directory.

    Parameters
    ----------
    folder_path : Path
        Directory whose files to list.

    Returns
    -------
    list of Path
        Paths to immediate files, excluding files in subdirectories.
    """
    return [f for f in folder_path.iterdir() if f.is_file()]


def get_list_folder_paths(folder_path: Path):
    """Return the immediate subdirectory paths contained in a directory.

    Parameters
    ----------
    folder_path : Path
        Directory whose subdirectories to list.

    Returns
    -------
    list of Path
        Paths to immediate subdirectories.
    """
    return [f for f in folder_path.iterdir() if f.is_dir()]


def get_tmdbid(name: Path) -> int | None:
    """Extract a numeric TMDB ID from a path's name.

    Look for a marker such as ``[tmdbid-123]`` in the final path component.

    Parameters
    ----------
    name : Path
        Path whose name to inspect.

    Returns
    -------
    int or None
        Extracted TMDB ID, or ``None`` if the name has no TMDB ID marker.
    """
    if "tmdbid" in name.name:
        match = re.search(r"\[([^\]]*)\]", name.name)
        return int(match.group(1).replace("tmdbid-", ""))



def get_tmdb_details(name: Path, API_KEY: str, media_type: str):
    """Fetch TMDB details for a movie or TV show.

    Extract the TMDB ID from ``name`` and request the corresponding API
    resource when an ID is present.

    Parameters
    ----------
    name : Path
        Media path whose name contains a TMDB ID marker.
    API_KEY : str
        API key used to authenticate the TMDB request.
    media_type : str
        Media type to request: ``"movies"`` or ``"tv_shows"``.

    Returns
    -------
    dict or None
        TMDB response data, or ``None`` if ``name`` has no TMDB ID marker.
    """
    tmdbid = get_tmdbid(name=name)

    if media_type == "movies":
        tmdb_media_type = "movie"
    elif media_type == "tv_shows":
        tmdb_media_type = "tv"

    if tmdbid is not None:
        BASE_URL = f"https://api.themoviedb.org/3/{tmdb_media_type}/{tmdbid}"
        endpoint = f"{BASE_URL}?api_key={API_KEY}"

        r = requests.get(endpoint)
        data = r.json()
        return data
    else:
        return None


def title_only(p: Path) -> str:
    """Return a media title without its year and TMDB ID suffix.

    Parameters
    ----------
    p : Path
        Media path whose stem to clean.

    Returns
    -------
    str
        Title with a trailing year and TMDB ID marker removed.
    """
    return PATTERN.sub("", p.stem)


def tmdb_get_collection_details(tmdb_collection_id: int, API_KEY: str):
    """Fetch details for a TMDB collection.

    Parameters
    ----------
    tmdb_collection_id : int
        TMDB identifier of the collection to retrieve.
    API_KEY : str
        API key used to authenticate the TMDB request.

    Returns
    -------
    dict
        JSON response data for the collection.
    """
    BASE_URL = f"https://api.themoviedb.org/3/collection/{tmdb_collection_id}"
    endpoint = f"{BASE_URL}?api_key={API_KEY}"

    r = requests.get(endpoint)
    data = r.json()
    return data




