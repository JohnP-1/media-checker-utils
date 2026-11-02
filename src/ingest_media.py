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


def ingest_movies():
    ingest_items_paths = get_list_folder_paths(folder_path=PATH_INGEST_MOVIES)


def main():
    # ingest movies

    # ingest tv shows
    pass

if __name__ == "__main__":
    main()