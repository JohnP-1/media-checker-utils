"""Test the media ingestion functionality."""

from pathlib import Path

import pytest

from src import ingest_media

MOVIES_INPUTS = Path(__file__).parent / "tests_inputs" / "movies"


@pytest.mark.parametrize(
    "folder_name",
    [
        "empty movie folder (1999) [tmdbid-1234]",
        "title (200) [tmdbid-1234]",
        "title (2000) [tmdid-1234]",
    ],
)
def test_check_folder_rejects_empty_or_invalid_folder_names(
    monkeypatch, folder_name
):
    folder_path = MOVIES_INPUTS / folder_name

    def fail_if_called(**kwargs):
        pytest.fail("TMDB lookup should not run for an invalid folder")

    monkeypatch.setattr(ingest_media, "get_tmdb_details", fail_if_called)

    assert ingest_media.check_movie_folder(folder_path) == (True, [])


def test_check_folder_returns_only_valid_matching_movie_files(monkeypatch):
    folder_path = MOVIES_INPUTS / "title (2000) [tmdbid-1234]"
    accepted_paths = {
        folder_path,
        folder_path / "title (2000) [tmdbid-1234].mp4",
        folder_path / "title (2000) [tmdbid-1234] - 576p.mp4",
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

    folder_exists, files_to_ingest = ingest_media.check_movie_folder(
        folder_path
    )

    assert folder_exists is True
    assert set(files_to_ingest) == accepted_paths - {folder_path}
    assert requested_details == [(folder_path, "test-api-key", "movies")]
