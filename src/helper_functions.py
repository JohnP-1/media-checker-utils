import os
from pathlib import Path
import re
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")


def check_tmdbid_in_name(check_string: str) -> bool:
    return bool(re.search(r'\[tmdbid-\d+\]', check_string))


def check_year_in_name(check_string: str) -> bool:
    return bool(re.search(r'\(\d{4}\)', check_string)) 


def get_tmdb_details(name: str, API_KEY: str, media_type: str):
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


def check_tmdb_name(name: str, tmdb_response, media_type: str) -> bool:

    if media_type == "movies":
        title_key = "title"
    elif media_type == "tv_shows":
        title_key = "name"
    if tmdb_response[title_key].replace(":", "").replace("-", "").replace("_", "").replace("\'", "").replace(" ", "").lower() in name.replace(":", "").replace("-", "").replace("_", "").replace("\'", "").replace(" ", "").lower():
        return tmdb_response[title_key], True
    else:
        return tmdb_response[title_key], False
    

def tmdb_get_collection_details(tmdb_collection_id: int, API_KEY: str):
    BASE_URL = f"https://api.themoviedb.org/3/collection/{tmdb_collection_id}"
    endpoint = f"{BASE_URL}?api_key={API_KEY}"

    r = requests.get(endpoint)
    data = r.json()
    return data


def check_folder_not_empty(folder_path: Path):
    return len(os.listdir(folder_path))


def get_list_folders(folder_path: Path):
    return [ f.name for f in os.scandir(folder_path) if f.is_dir()]


def get_list_folder_paths(folder_path: Path):
    return [f.path for f in os.scandir(folder_path) if f.is_dir()]


def get_tmdbid(name: str) -> int | None:
    if "tmdbid" in name:
        match = re.search(r'\[([^\]]*)\]', name)
        return int(match.group(1).replace("tmdbid-", ""))