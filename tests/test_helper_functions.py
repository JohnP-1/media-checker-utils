from pathlib import Path

import pytest

from src.helper_functions import (
    check_file_matches_folder,
    check_files_match_folder,
    check_folder_not_empty,
    check_tmdbid_in_name,
    check_year_in_name,
    get_list_file_paths,
    get_list_folder_paths,
    get_tmdb_details,
    get_tmdbid,
    tmdb_get_collection_details,
)


@pytest.fixture
def movie_folder_path():
    return Path("tests/tests_inputs/movies/title (2000) [tmdbid-1234]")


@pytest.fixture
def empty_movie_folder_path():
    return Path("tests/tests_inputs/movies/empty movie folder (1999) [tmdbid-1234]")


def test_check_files_match_folder(movie_folder_path):

    file_paths_match, file_paths_not_match = check_files_match_folder(folder_path=movie_folder_path)

    file_paths_match_expected = ["title (2000) [tmdbid-1234].mp4",
                                 "title (2000) [tmdbid-1234] - 576p.mp4"]
    file_paths_not_match_expected = ["title (200) [tmdbid-1234].mp4",
                                     "incorrect_title (2000) [tmdbid-1234].mp4",
                                     "title (2000) [tmdbid-4321].mp4"]

    assert sorted([f.name for f in file_paths_match]) == sorted(file_paths_match_expected)
    assert sorted([f.name for f in file_paths_not_match]) == sorted(file_paths_not_match_expected)


def test_check_file_matches_folder(movie_folder_path):

    assert check_file_matches_folder(folder=movie_folder_path, file_name=Path("title (2000) [tmdbid-1234].mp4")) is True
    assert check_file_matches_folder(folder=movie_folder_path, file_name=Path("title (200) [tmdbid-1234].mp4")) is False
    assert check_file_matches_folder(folder=movie_folder_path, file_name=Path("title (2000) [tmdbid-4321].mp4")) is False
    assert check_file_matches_folder(folder=movie_folder_path, file_name=Path("title (2000) [tmbid-1234].mp4")) is False

@pytest.mark.parametrize(
    "file_name, expected_result",
    [
        ("title (2000) [tmdbid-1234].mp4", True),
        ("title (200) [tmdbid-1234].mp4", False),
        ("title (2000) [tmdbid-4321].mp4", False),
        ("title (2000) [tmbid-1234].mp4", False),
        ("title (2000) [tmdbid-1234] - 576p.mp4", True),
        ("title (2000) [tmdbid-1234] - 1080p.mp4", True),
        ("title (2000) [tmdbid-1234] - Directors Cut.mp4", True),
        ("title (2000) [tmdbid-1234] - Theatrical Cut.mp4", True),
        ("title (2000) [tmdbid-1234] - Final Cut.mp4", True),
    ],
)
def test_check_file_matches_folder_suffixes(movie_folder_path, file_name, expected_result):
    assert check_file_matches_folder(folder=movie_folder_path, file_name=Path(file_name)) is expected_result


def test_folder_not_empty(movie_folder_path, empty_movie_folder_path):
    assert check_folder_not_empty(folder_path=movie_folder_path) is True
    assert check_folder_not_empty(folder_path=empty_movie_folder_path) is False

@pytest.mark.parametrize(
    "check_path, expected_result",
    [
        ("tests/tests_inputs/movies/title (2000) [tmdbid-1234]", True),
        ("tests/tests_inputs/movies/title (2000) [tmdbid-1234]/title (200) [tmdbid-1234].mp4", True),
        ("tests/tests_inputs/movies/title (2000) [tmdid-1234]", False),
        ("tests/tests_inputs/movies/title (2000) [tmdid-1234]/title (2000) [tmdbid-1234].mp4", True),
    ]
)
def test_check_tmdbid_in_name(check_path, expected_result):
    assert check_tmdbid_in_name(Path(check_path)) is expected_result


@pytest.mark.parametrize(
    "check_path, expected_result",
    [
        ("tests/tests_inputs/movies/title (200) [tmdbid-1234]", False),
        ("tests/tests_inputs/movies/title (200) [tmdbid-1234]/title (2000) [tmdbid-1234].mp4", True),
        ("tests/tests_inputs/movies/title (2000) [tmdid-1234]/title (2000) [tmdbid-1234].mp4", True),
        ("tests/tests_inputs/movies/title (2000) [tmdbid-1234]/title (200) [tmdbid-1234].mp4", False),
    ]
)
def test_check_year_in_name(check_path, expected_result):
    assert check_year_in_name(Path(check_path)) is expected_result


def test_get_list_file_paths(tmp_path):
    direct_file = tmp_path / "movie.mp4"
    direct_file.touch()
    subfolder = tmp_path / "subfolder"
    subfolder.mkdir()
    nested_file = subfolder / "nested.mp4"
    nested_file.touch()

    assert set(get_list_file_paths(tmp_path)) == {direct_file}


def test_get_list_folder_paths(tmp_path):
    direct_folder = tmp_path / "movies"
    direct_folder.mkdir()
    subfolder = direct_folder / "nested"
    subfolder.mkdir()
    (tmp_path / "movie.mp4").touch()

    assert set(get_list_folder_paths(tmp_path)) == {direct_folder}


@pytest.mark.parametrize(
    "name, expected_tmdbid",
    [
        (Path("movie title [tmdbid-1234]"), 1234),
        (Path("show title [tmdbid-987654].mkv"), 987654),
        (Path("movie title without an ID"), None),
    ],
)
def test_get_tmdbid(name, expected_tmdbid):
    assert get_tmdbid(name) == expected_tmdbid


@pytest.mark.parametrize(
    "media_type, endpoint_type",
    [
        ("movies", "movie"),
        ("tv_shows", "tv"),
    ],
)
def test_get_tmdb_details_requests_tmdb_data(
    monkeypatch, media_type, endpoint_type
):
    response_data = {"id": 1234, "name": "Example"}
    requested_urls = []

    class MockResponse:
        def json(self):
            return response_data

    def mock_get(url):
        requested_urls.append(url)
        return MockResponse()

    monkeypatch.setattr("src.helper_functions.requests.get", mock_get)

    result = get_tmdb_details(
        name=Path("Example (2000) [tmdbid-1234]"),
        API_KEY="test-api-key",
        media_type=media_type,
    )

    assert result == response_data
    assert requested_urls == [
        f"https://api.themoviedb.org/3/{endpoint_type}/1234?api_key=test-api-key"
    ]


def test_get_tmdb_details_without_tmdbid_does_not_make_request(monkeypatch):
    def fail_if_called(url):
        pytest.fail(f"Unexpected request to {url}")

    monkeypatch.setattr("src.helper_functions.requests.get", fail_if_called)

    assert (
        get_tmdb_details(
            name=Path("Example (2000)"),
            API_KEY="test-api-key",
            media_type="movies",
        )
        is None
    )


def test_tmdb_get_collection_details_requests_and_returns_collection(
    monkeypatch,
):
    response_data = {"id": 5678, "name": "Example Collection"}
    requested_urls = []

    class MockResponse:
        def json(self):
            return response_data

    def mock_get(url):
        requested_urls.append(url)
        return MockResponse()

    monkeypatch.setattr("src.helper_functions.requests.get", mock_get)

    result = tmdb_get_collection_details(
        tmdb_collection_id=5678,
        API_KEY="test-api-key",
    )

    assert result == response_data
    assert requested_urls == [
        "https://api.themoviedb.org/3/collection/5678?api_key=test-api-key"
    ]
