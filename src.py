import datetime
import typing as typ
import pathlib
import os

import mutagen


# Only for MP3!?!?!? (ID3) use easy versions
# Title: TIT2
# Artist: TPE1
# Album: TALB
# TRACK NUMBER: TRCK
# Genre: TCON
# Date: TDRC or TYER or TORY or TDAT or TRDA or TDOR or TDRL

# ID3v2 / OGG_VORBIS


PICS_EXTENSIONS = ['jpeg', 'jpg', 'png', 'bmp']


class Archive:
    def __init__(self, path: str):
        self.path = pathlib.Path(path)

    def get_artist_tag_stat(self) -> typ.Dict[str, int]:
        stat = dict()
        for root, _, files in os.walk(self.path):
            for file_name in files:
                music_file = mutagen.File(f'{root}/{file_name}', easy=True)
                if music_file is not None:
                    tag_val = music_file.tags['artist'][0] if 'artist' in music_file.tags else None
                    stat[tag_val] = stat.get(tag_val, 0) + 1

        return stat

    # track
    # check title existent


class ArtistArchive(Archive):
    def __init__(self, path: str, possible_artist_names: typ.List[str], *, case_sensitive=True):
        super().__init__(path)
        self.possible_artist_names = possible_artist_names
        self.last_update_time = None
        self.case_sensitive = case_sensitive

    def set_artist_tag(self, *, missed_only=False, new_only=True):
        possible_artist_names = self.possible_artist_names
        if self.case_sensitive:
            possible_artist_names = [artist_name.casefold() for artist_name in possible_artist_names]

        for root, _, files in os.walk(self.path):
            for file_name in files:
                file_path = pathlib.Path(root, file_name)
                music_file = mutagen.File(file_path, easy=True)
                if music_file is not None:
                    if new_only and self.last_update_time is not None:
                        file_modification_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_modification_time < self.last_update_time:
                            continue

                    artist_tag = music_file.tags.get('artist')
                    if missed_only and artist_tag is not None:
                        continue

                    artist_tag_value = '' if artist_tag is None else artist_tag[0]
                    artist_tag_value = artist_tag_value if self.case_sensitive else artist_tag_value.casefold()
                    if any(artist_name in artist_tag_value for artist_name in possible_artist_names):
                        continue

                    music_file.tags['artist'] = self.possible_artist_names[0]
                    music_file.save()



class AlbumArchive(Archive):
    def __init__(self, path: str, album_name: str):
        super().__init__(path)
        self.album_name = album_name
        self.last_update_time = None

    def set_album_tag(self):
        for root, _, files in os.walk(self.path):
            for file_name in files:
                file_path = pathlib.Path(root, file_name)
                music_file = mutagen.File(file_path, easy=True)
                if music_file is not None:
                    music_file.tags['album'] = self.album_name
                    music_file.save()

    # def check_missed_tracks_by_number_tag(self):
    #     for root, _, files in os.walk(self.path):
    #         root_track_numbers = list()
    #         for file_name in files:
    #             file_path = pathlib.Path(root, file_name)
    #             music_file = mutagen.File(file_path, easy=True)
    #             if music_file and ''



     # check missed tracks if track numbers exist
     # set picture cover if picture cover exist
     # update filename (title should be exist)



class PlaylistArchive(Archive):
    pass
    # numerate filenames by adding time

# My player can see only first elements from text frames lists


if __name__ == '__main__':
    a = Archive('/Users/konstantin/Desktop')
    print(a.get_artist_tag_stat())
