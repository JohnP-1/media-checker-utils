import pytest
 
import src.ingest_media as ingest
 
# Fake TMDB database keyed by id, so no network calls are made.
FAKE_TMDB = {
    782: {"title": "Gattaca"},
    187: {"title": "Mr. Nobody"},
    935: {"title": "Dr. Strangelove or: How I Learned to Stop Worrying and Love the Bomb"},
    348: {"title": "Alien"},
    679: {"title": "Aliens"},
}
 
 
@pytest.fixture
def dirs(tmp_path, monkeypatch):
    ingest_dir = tmp_path / "ingest"
    media_dir = tmp_path / "media"
    failed_dir = tmp_path / "failed"
    ingest_dir.mkdir()
    media_dir.mkdir()
    monkeypatch.setattr(ingest, "PATH_INGEST_MOVIES", ingest_dir)
    monkeypatch.setattr(ingest, "PATH_MEDIA_MOVIES", media_dir)
    monkeypatch.setattr(ingest, "PATH_FAILED_MOVIES", failed_dir)  # not created: code must create it
 
    def fake_details(name, API_KEY, media_type):
        from src.helper_functions import get_tmdbid
        tmdbid = get_tmdbid(name)
        if tmdbid is None:
            return None
        return FAKE_TMDB.get(tmdbid, {"success": False, "status_code": 34})
 
    monkeypatch.setattr(ingest, "get_tmdb_details", fake_details)
    return ingest_dir, media_dir, failed_dir
 
 
def make_movie(root, folder, files):
    d = root / folder
    d.mkdir(parents=True, exist_ok=True)
    for f in files:
        (d / f).write_text(f"content of {f}")
    return d
 