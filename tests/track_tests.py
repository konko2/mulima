import pytest
from src import Track
from pathlib import Path
import shutil
import tempfile


@pytest.fixture
def mp3_track():
    source_path = Path('data/file.mp3')

    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir, source_path.name)
    shutil.copy2(source_path, temp_path)

    return Track(temp_path)


class MP3TrackTests:
    def test_tag_getting(self, mp3_track):
        expected_tags = {
            'title': 'filename',
            'artist': 'AArtist',
            'album': 'ALBUM',
            'date': '2019',
            'tracknumber': '5',
            'genre': 'genreee',
            'composer': None
        }

        assert all(mp3_track.get_tag(tag) == value for tag, value in expected_tags.values())
        assert mp3_track.get_tags == expected_tags

    def test_wrong_tag_getting(self, mp3_track):
        pass  #raises

    def test_tag_setting(self):
        pass

    def test_cover_setting(self):
        pass

    def test_writing_without_modification(self):
        pass


class FlacTrackTests:
    pass
