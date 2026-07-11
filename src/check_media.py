import os
from pathlib import Path
import argparse
import re
from dotenv import load_dotenv

from helper_functions import (
    check_tmdbid_in_name,
    check_year_in_name,
    get_tmdb_details,
    check_tmdb_name,
    check_folder_not_empty,
    get_list_folders,
    get_list_folder_paths,
)

load_dotenv()
API_KEY = os.getenv("API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
    


def check_series_folder_names(folder_path: Path):
    print("Checking SERIES folders now ...\n")

    series_folder_errors = []

    folder_paths = get_list_folder_paths(folder_path=folder_path)
    folders = get_list_folders(folder_path=folder_path)

    for i, folder_path in enumerate(folder_paths):
        series_folders = get_list_folders(folder_path=folder_path)
        for series_folder in series_folders:
            if not bool(re.match(r'^Season \d{2}$', series_folder)):
                series_folder_errors.append((folders[i], series_folder))

    if len(series_folder_errors) > 0:
        print("WARNING - The following series errors have been found:")
        for folder, series_folder in series_folder_errors:
            print(f"\t - {folder} <---> {series_folder}")

    print(f"The total number of errors found was {len(series_folder_errors)}. Please fix these now.\n")


def check_series_file_names(folder_path: Path):
    print("Checking SERIES files now ...\n")

    series_file_errors = []

    folder_paths = get_list_folder_paths(folder_path=folder_path)
    folders = get_list_folders(folder_path=folder_path)

    for i, folder_path in enumerate(folder_paths):
        series_name = " ".join(folders[i].split(" ")[:-2])
        series_paths = get_list_folder_paths(folder_path=folder_path)
        for series_path in series_paths:
            series_files = os.listdir(series_path)
            for series_file in series_files:
                if series_name not in series_file:
                    series_file_errors.append((series_name, series_file))
                if not re.search(r'S\d{2}E\d{2}', series_file):
                    series_file_errors.append((series_name, series_file))

    if len(series_file_errors) > 0:
        print("WARNING - The following series FILE errors have been found:")
        for folder, series_file in series_file_errors:
            print(f"\t - {folder} <---> {series_file}")

    print(f"The total number of errors found was {len(series_file_errors)}. Please fix these now.\n")
                

def check_folder_names(folder_path:Path, API_KEY: str, media_type: str):
    print("Checking folders now ...\n")
    empty_folders = []
    tmdbid_errors = []
    year_errors = []
    tmdb_response_errors = []
    tmdb_name_errors = []

    folder_names = get_list_folders(folder_path=folder_path)
    folder_paths = get_list_folder_paths(folder_path=folder_path)

    for i, folder in enumerate(folder_names):
        tmdb_response = get_tmdb_details(name=folder, API_KEY=API_KEY, media_type=media_type)
        if check_folder_not_empty(folder_paths[i]) == 0:
            empty_folders.append(folder)
        if not check_tmdbid_in_name(check_string=folder):
            tmdbid_errors.append(folder)
        if not check_year_in_name(check_string=folder):
            year_errors.append(folder)
        if tmdb_response is not None  and tmdb_response.get("status_message") != "The resource you requested could not be found.":
            title, check = check_tmdb_name(name=folder, tmdb_response=tmdb_response, media_type=media_type)
            if not check:
                tmdb_name_errors.append((folder, title))
        else:
            tmdb_response_errors.append(folder)

    empty_folders = sorted(empty_folders)
    tmdbid_errors = sorted(tmdbid_errors)
    year_errors = sorted(year_errors)
    tmdb_response_errors = sorted(tmdb_response_errors)
    tmdb_name_errors = sorted(tmdb_name_errors, key=lambda x: x[0])

    if len(empty_folders) > 0:
        print("WARNING - The following FOLDERS are empty:")
        for folder in empty_folders:
            print(f"\t - {folder}")
    if len(tmdbid_errors) > 0:
        print("WARNING - The following TMDBID naming errors have been found:")
        for folder in tmdbid_errors:
            print(f"\t - {folder}")
    if len(year_errors) > 0:
        print("WARNING - The following YEAR errors have been found:")
        for folder in year_errors:
            print(f"\t - {folder}")
    if len(tmdb_response_errors) > 0:
        print("WARNING - The following media did not return any TMDB data:")
        for folder in tmdb_response_errors:
            print(f"\t - {folder}")
    if len(tmdb_name_errors) > 0:
        print("INFO - The following media did not match the TMDB title for the film:")
        for folder, tmdb_name in tmdb_name_errors:
            print(f"\t - {folder} <---> {tmdb_name}")
    total_errors = len(tmdbid_errors) + len(year_errors) + len(tmdb_response_errors) + len(tmdb_name_errors)
    print(f"\nThe total number of errors found was {total_errors}. Please fix these now.\n")


def check_files_match_folder(folder_path: Path, folder: str) -> tuple[str, str]:
    files = os.listdir(folder_path)
    files_not_match = []

    for file in files:
        file_name = Path(file).stem.replace("-dvd1", "").replace("-dvd2", "").replace(" - 576p", "").replace(" - 1080p", "")
        if file_name != folder:
            files_not_match.append((folder, file))

    return files_not_match


def check_content_movies(folder_path: Path):
    print("Checking files now ...\n")

    mismatch_errors = []

    folder_names = get_list_folders(folder_path=folder_path)
    folder_paths = get_list_folder_paths(folder_path=folder_path)

    for i, folder in enumerate(folder_names):
        files_not_match = check_files_match_folder(folder_path=folder_paths[i], folder=folder)
        if len(files_not_match) > 0:
            mismatch_errors.extend(files_not_match)

    mismatch_errors = sorted(mismatch_errors, key=lambda x: x[0])

    if len(mismatch_errors) > 0:
        print("WARNING - The following FILES do not match their CONTAINING folder:")
        for folder, file in mismatch_errors:
            print(f"\t - {folder} <---> {file}")


def main(folder_path: Path, media_type: str):
    if media_type == "movies":
        progress = input("Would you like to check the folder structure now? [Y/n]") or "y"
        if progress.lower() in ["y", "yes"]:
            check_folder_names(folder_path=folder_path, API_KEY=API_KEY, media_type=media_type)
        else:
            print("Skipping the folder checks ...")
        progress = input("Would you like to check the files now? [Y/n]") or "y"
        if progress.lower() in ["y", "yes"]:
            check_content_movies(folder_path=folder_path)
        else:
            print("Skipping the file checks ...")
    elif media_type == "tv_shows":
        progress = input("Would you like to check the folder structure now? [Y/n]") or "y"
        if progress.lower() in ["y", "yes"]:
            check_folder_names(folder_path=folder_path, API_KEY=API_KEY, media_type=media_type)
            check_series_folder_names(folder_path=folder_path)
            check_series_file_names(folder_path=folder_path)
    else:
        raise ValueError("media_type should be either 'movies' or 'tv_shows'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check media in a folder")
    parser.add_argument("folder_path", type=str, help="The path of the media folder to check")
    parser.add_argument("media_type", type=str, help="The media type to check, can be one of 'movies' or 'tv_shows'")
    args = parser.parse_args()
    folder_path = args.folder_path
    media_type = args.media_type
    main(folder_path=folder_path, media_type=media_type)



