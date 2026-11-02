import argparse
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from helper_functions import (
    get_list_folder_paths,
    get_list_folders,
    get_tmdb_details,
    tmdb_get_collection_details,
)

load_dotenv()
API_KEY = os.getenv("API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")


def initialise_movie_collections(folder_path: Path) -> dict:

    print("Initialising collections now...\n")
    folder_names = get_list_folders(folder_path=folder_path)

    collections = {}

    for i, folder in enumerate(folder_names):
        tmdb_response = get_tmdb_details(
            name=folder, API_KEY=API_KEY, media_type="movies"
        )

        if tmdb_response["belongs_to_collection"] is not None:
            collection_details = tmdb_get_collection_details(
                tmdb_collection_id=tmdb_response["belongs_to_collection"]["id"],
                API_KEY=API_KEY,
            )
            if collection_details["original_name"] not in collections.keys():
                collections[collection_details["original_name"]] = collection_details
                collections[collection_details["original_name"]]["owned"] = {
                    "id": [tmdb_response["id"]],
                    "name": [tmdb_response["title"]],
                }
                collections[collection_details["original_name"]]["missing"] = {
                    "id": [],
                    "name": [],
                }
            else:
                collections[collection_details["original_name"]]["owned"]["id"].append(
                    tmdb_response["id"]
                )
                collections[collection_details["original_name"]]["owned"][
                    "name"
                ].append(tmdb_response["title"])

    for collection_name in collections.keys():
        for part in collections[collection_name]["parts"]:
            if part["id"] not in collections[collection_name]["owned"]["id"]:
                collections[collection_name]["missing"]["id"].append(part["id"])
                collections[collection_name]["missing"]["name"].append(part["title"])
                collections[collection_name]["missing"]["n"] = len(
                    collections[collection_name]["missing"]["id"]
                )

    return collections


def initialise_series_collections(folder_path: Path) -> dict:

    print("Initialising collections now...\n")
    folder_names = get_list_folders(folder_path=folder_path)
    folder_paths = get_list_folder_paths(folder_path=folder_path)

    collections = {}

    for i, folder in enumerate(folder_names):
        series_name = " ".join(folder.split(" ")[:-2])
        owned_series = get_list_folders(folder_path=folder_paths[i])
        tmdb_response = get_tmdb_details(
            name=folder, API_KEY=API_KEY, media_type="tv_shows"
        )
        tmdb_seasons = [season["name"] for season in tmdb_response.get("seasons", [])]
        tmdb_season_adjusted = []
        for season in tmdb_seasons:
            if (
                len(season.split(" ")[-1]) == 1
                and season.split(" ")[-1].isdigit()
                and season.split(" ")[0] == "Season"
            ):
                tmdb_season_adjusted.append("Season 0" + season.split(" ")[-1])
            elif (
                len(season.split(" ")[-1]) == 2
                and season.split(" ")[-1].isdigit()
                and season.split(" ")[0] == "Season"
            ):
                tmdb_season_adjusted.append(season)
        for series in owned_series:
            if series in tmdb_season_adjusted:
                if series_name not in collections.keys():
                    collections[series_name] = {
                        "tmdb_id": tmdb_response["id"],
                        "name": tmdb_response["name"],
                        "series_owned": [series],
                        "series_missing": [],
                    }
                else:
                    collections[series_name]["series_owned"].append(series)

        for tmdb_season in tmdb_season_adjusted:
            if tmdb_season not in owned_series:
                collections[series_name]["series_missing"].append(tmdb_season)

    return collections


def parse_series_collections_to_textfile(collections: dict, filename: str):

    with open(filename, "w") as f:
        for series_name in collections.keys():
            f.write(f"Series: {series_name}\n")
            f.write(
                f"Total Seasons: {len(collections[series_name]['series_owned']) + len(collections[series_name]['series_missing'])}\n"
            )
            f.write(f"Owned Seasons: {len(collections[series_name]['series_owned'])}\n")
            f.write(
                f"Missing Seasons: {len(collections[series_name]['series_missing'])}\n"
            )
            f.write("\n")
            f.write("Owned Seasons:\n")
            for i, season in enumerate(
                sorted(collections[series_name]["series_owned"])
            ):
                f.write(f"\t{i + 1}. {season}\n")
            f.write("\n")
            if len(collections[series_name]["series_missing"]) > 0:
                f.write("Missing Seasons:\n")
                for i, season in enumerate(
                    sorted(collections[series_name]["series_missing"])
                ):
                    f.write(f"\t{i + 1}. {season}\n")
            f.write("\n\n")


def parse_movies_collections_to_textfile(collections: dict, filename: str):

    with open(filename, "w") as f:
        for collection_name in collections.keys():
            f.write(f"Collection: {collection_name}\n")
            f.write(f"Total Parts: {len(collections[collection_name]['parts'])}\n")
            f.write(
                f"Owned Parts: {len(collections[collection_name]['owned']['id'])}\n"
            )
            f.write(
                f"Missing Parts: {len(collections[collection_name]['missing']['id'])}\n"
            )
            f.write("\n")
            f.write("Owned Parts:\n")
            for i, part in enumerate(collections[collection_name]["owned"]["name"]):
                f.write(f"\t{i + 1}. {part}\n")
            f.write("\n")
            if len(collections[collection_name]["missing"]["id"]) > 0:
                f.write("Missing Parts:\n")
                for i, part in enumerate(
                    collections[collection_name]["missing"]["name"]
                ):
                    f.write(f"\t{i + 1}. {part}\n")
            f.write("\n\n")


def parse_movies_to_text_file(folder_path: Path, output_file: Path) -> None:
    folder_names = sorted(get_list_folders(folder_path=folder_path))
    with open(output_file, "w") as f:
        for i, folder in enumerate(folder_names):
            tmdb_response = get_tmdb_details(
                name=folder, API_KEY=API_KEY, media_type="movies"
            )
            f.write(
                f"{i + 1}. {tmdb_response['title']} ({tmdb_response['release_date'][:4]})\n"
            )


def main(folder_path: Path, media_type: str, config: dict):
    if media_type == "movies":
        collections = initialise_movie_collections(folder_path=folder_path)
        parse_movies_collections_to_textfile(
            collections=collections,
            filename=Path(config["syncthing_path"]) / "movies_collections.txt",
        )
        parse_movies_to_text_file(
            folder_path=folder_path,
            output_file=Path(config["syncthing_path"]) / "movies.txt",
        )
    elif media_type == "tv_shows":
        collections = initialise_series_collections(folder_path=folder_path)
        parse_series_collections_to_textfile(
            collections=collections,
            filename=Path(config["syncthing_path"]) / "tv_shows_collections.txt",
        )


if __name__ == "__main__":
    with open("src/config.yml", "r") as f:
        config = yaml.safe_load(f)
    parser = argparse.ArgumentParser(description="Check media in a folder")
    parser.add_argument(
        "folder_path", type=str, help="The path of the media folder to check"
    )
    parser.add_argument(
        "media_type",
        type=str,
        help="The media type to check, can be one of 'movies' or 'tv_shows'",
    )
    args = parser.parse_args()
    folder_path = args.folder_path
    media_type = args.media_type

    main(folder_path=folder_path, media_type=media_type, config=config)
