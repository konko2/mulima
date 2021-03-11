import datetime
import typing as typ
from pathlib import Path
import os

import mutagen


PICS_EXTENSIONS = ['jpeg', 'jpg', 'png', 'bmp']


class ABCArchive:
    def __init__(self, path: str):
        self.path = Path(path)

    def get_dirs_tracks(self) -> typ.Dict[Path, typ.List[mutagen.File]]:
        dir_tracks = dict()
        for root, _, files in os.walk(self.path):
            dir_path = Path(root)
            tracks = (mutagen.File(dir_path/file_name, easy=True) for file_name in files)
            dir_tracks[dir_path] = [t for t in tracks if t is not None]
        return dir_tracks

    def get_artist_tag_stat(self) -> typ.Dict[str, int]:
        stat = dict()
        for root, _, files in os.walk(self.path):
            for file_name in files:
                music_file = mutagen.File(f'{root}/{file_name}', easy=True)
                if music_file is not None:
                    tag_val = music_file.tags['artist'][0] if 'artist' in music_file.tags else None
                    stat[tag_val] = stat.get(tag_val, 0) + 1

        return stat

    @staticmethod
    def set_track_filename(track: mutagen.File, formatting_pattern: str):
        filepath = Path(track.filename)
        filename = formatting_pattern.format(
            title=track.tags.get('title', ''),
            artist=track.tags.get('artist', ''),
            album=track.tags.get('album', ''),
            date=track.tags.get('date', ''),
            composer=track.tags.get('composer', ''),
            tracknumber=track.tags.get('tracknumber', ''),
            author=track.tags.get('author', '')
        )
        filepath.rename(filepath.parent + filename + filepath.suffix)

    def update(self):
        raise NotImplementedError

    # track
    # check title existent


class ArtistArchive(ABCArchive):
    def __init__(self, path: str, possible_artist_names: typ.List[str], *, case_sensitive=True):
        super().__init__(path)
        self.possible_artist_names = possible_artist_names
        self.last_update_time = None
        self.case_sensitive = case_sensitive

    def set_artist_tag(self, *, missed_only=False, new_only=True):
        checking_artist_names = self.possible_artist_names  # artist names for checking (considering case sensitivity)
        if self.case_sensitive:
            checking_artist_names = [artist_name.casefold() for artist_name in checking_artist_names]

        for root, _, files in os.walk(self.path):
            for file_name in files:
                file_path = Path(root, file_name)
                track = mutagen.File(file_path, easy=True)
                if track is not None:
                    if new_only and self.last_update_time is not None:
                        file_modification_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_modification_time < self.last_update_time:
                            continue

                    artist_tag = track.tags.get('artist')
                    if missed_only and artist_tag is not None:
                        continue

                    artist_tag_value = '' if artist_tag is None else artist_tag[0]
                    artist_tag_value = artist_tag_value if self.case_sensitive else artist_tag_value.casefold()
                    if any(artist_name in artist_tag_value for artist_name in checking_artist_names):
                        continue

                    track.tags['artist'] = self.possible_artist_names[0]
                    track.save()

    def update(self):
        raise NotImplementedError


class AlbumArchive(ABCArchive):
    def __init__(self, path: str, album_name: str):
        super().__init__(path)
        self.album_name = album_name
        self.last_update_time = None

    def set_album_tag(self):
        folded_album_name = self.album_name.casefold()
        for _, track_list in self.get_dirs_tracks():
            for track in track_list:
                if 'album' not in track.tags or folded_album_name not in track.tags['album']:
                    track.tags['album'] = self.album_name
                    track.save()

    # TODO: rename
    # TODO: remove?
    def get_dirs_tracks_number_and_dirs_tracks_total(self) -> typ.Tuple[
        typ.Dict[Path, typ.Dict[Path, typ.Optional[int]]],
        typ.Dict[Path, typ.Dict[Path, typ.Optional[int]]]
    ]:
        dir_tracks_number = dict()
        dir_tracks_total = dict()

        for dir_path, track_list in self.get_dirs_tracks().items():
            tracks_number = dict()
            tracks_total = dict()
            for track in track_list:
                file_path = Path(track.filename)
                tracks_number[file_path] = int(track['tracknumber'][0]) if 'tracknumber' in track.tags else None
                tracks_total[file_path] = int(track['tracktotal'][0]) if 'tracktotal' in track.tags else None

            if tracks_number:
                dir_tracks_number[dir_path] = tracks_number
            if tracks_total:
                dir_tracks_total[dir_path] = tracks_total

        return dir_tracks_number, dir_tracks_total

    def update(self):
        # TODO coding check
        self.set_album_tag()

        dirs_tracks_number, dirs_tracks_total = self.get_dirs_tracks_number_and_dirs_tracks_total()  # TODO rename
        for directory in dirs_tracks_number:
            correct_total_values = set(dirs_tracks_total[directory].values())
            correct_total_values.discard(None)
            if len(correct_total_values) > 1:
                for track_path in dirs_tracks_total[directory]:
                    del mutagen.File(track_path, easy=True).tags['total']

            track_filename_pattern = '{track_name}'

            correct_track_numbers = set(dirs_tracks_number[directory].values())
            correct_track_numbers.discard(None)
            if len(correct_track_numbers) == len(dirs_tracks_number[directory]):
                track_filename_pattern = '{tracknumber}. {track_name}'

            # TODO
            for track_path in dirs_tracks_number:
                track = mutagen.File(track_path, easy=True)
                if 'title' in track.tags:
                    self.set_track_filename(mutagen.File(track_path, easy=True), track_filename_pattern)

        # TODO album cover adding

        # TODO: add stat


     # check missed tracks if track numbers exist
     # set picture cover if picture cover exist


class PlaylistArchive(ABCArchive):
    pass
    # numerate filenames by adding time

# My player can see only first elements from text frames lists


if __name__ == '__main__':
    a = ABCArchive('/Users/konstantin/Desktop')
    print(a.get_artist_tag_stat())
