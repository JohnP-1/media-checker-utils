import argparse
import logging
import os
import re
from pathlib import Path

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

load_dotenv()
API_KEY = os.getenv("API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")


def check_movie_folder(folder_path: Path) -> tuple[bool, list[Path]]:
    logger.info(f"Checking folder: {folder_path}")
    file_paths_ingest = []

    # check if folder is empty
    if not check_folder_not_empty(folder_path):
        logger.warning(f"Ingestion failed -- Folder is empty: {folder_path}")
        return folder_path.is_dir(), file_paths_ingest

    # check if folder name has year in it
    if not check_year_in_name(folder_path):
        logger.warning(f"Ingestion failed -- Folder name does not contain a valid year: {folder_path.name}")
        return folder_path.is_dir(), file_paths_ingest

    # check if folder name has tmdbid in it
    if not check_tmdbid_in_name(folder_path):
        logger.warning(f"Ingestion failed -- Folder name does not contain a valid TMDB ID: {folder_path.name}")
        return folder_path.is_dir(), file_paths_ingest

    # check if folder name matches tmdb name
    tmdb_data = get_tmdb_details(
        name=folder_path, API_KEY=API_KEY, media_type="movies"
    )
    if tmdb_data is None:
        logger.warning(f"Ingestion failed -- No TMDB data found for folder: {folder_path.name}")
        return folder_path.is_dir(), file_paths_ingest
    _, folder_name_matches = check_tmdb_name(
        name=folder_path, tmdb_response=tmdb_data, media_type="movies"
    )
    if not folder_name_matches:
        logger.warning(f"Ingestion failed -- Folder name does not match TMDB name: {folder_path.name}")
        return folder_path.is_dir(), file_paths_ingest

    # Get a list of file paths in the folder
    folder_exists = folder_path.is_dir()
    files = get_list_file_paths(folder_path=folder_path)

    for file in files:
        # check if file name has year in it
        if not check_year_in_name(file):
            logger.warning(f"Ingestion failed -- File name does not contain a valid year: {file.name}")
            continue
        # check if file name has tmdbid in it
        if not check_tmdbid_in_name(file):
            logger.warning(f"Ingestion failed -- File name does not contain a valid TMDB ID: {file.name}")
            continue
        if not check_valid_file_extension(file):
            logger.warning(f"Ingestion failed -- File name does not have a valid extension: {file.name}")
            continue
        # check if file name matches tmdb name
        _, file_name_matches = check_tmdb_name(
            name=file, tmdb_response=tmdb_data, media_type="movies"
        )
        if not file_name_matches:
            logger.warning(f"Ingestion failed -- File name does not match TMDB name: {file.name}")
            continue

        file_paths_ingest.append(file)

    return folder_exists, file_paths_ingest


def convert_to_ingest_paths(ingest_path: Path, folder_path: Path, file_paths: list[Path]) -> tuple[Path, list[Path]]:
    """Convert a folder path and its file paths to ingestion paths.

    Parameters
    ----------
    ingest_path : Path
        Base path for ingestion.
    folder_path : Path
        Original folder path.
    file_paths : list of Path
        Original file paths.

    Returns
    -------
    tuple of Path and list of Path
        Ingest folder path and corresponding ingestion file paths.
    """
    ingestion_folder_path = ingest_path / folder_path.name
    ingestion_file_paths = [ingestion_folder_path / file.name for file in file_paths]
    return ingestion_folder_path, ingestion_file_paths



def ingest_movies():
    folders_to_create = []
    files_to_ingest = []
    ingest_items_paths = get_list_folder_paths(folder_path=PATH_INGEST_MOVIES)
    for folder_path in ingest_items_paths:
        folder_exists, files_to_ingest_item = check_movie_folder(folder_path)
        if not folder_exists:
            folders_to_create.append(folder_path)

        files_to_ingest += files_to_ingest_item

    


def main():
    # ingest movies

    # ingest tv shows
    pass

if __name__ == "__main__":
    main()