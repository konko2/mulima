import typing as typ
import pathlib
import os

import mutagen


# Only for MP3!?!?!? (ID3)
# Title: TIT2
# Artist: TPE1
# Album: TALB
# TRACK NUMBER: TRCK
# Genre: TCON
# Date: TDRC or TYER or TORY or TDAT or TRDA or TDOR or TDRL


class Archive:
    def __init__(self, path: str):
        self.path = pathlib.Path(path)

    def get_artist_tag_stat(self) -> typ.Dict[str, int]:
        return self.__get_text_tag_stat('TPE1')

    def get_album_tag_stat(self) -> typ.Dict[str, int]:
        return self.__get_text_tag_stat('TALB')

    # track

    def __get_text_tag_stat(self, tag_frame_id: str) -> typ.Dict[str, int]:
        stat = dict()
        for root_pathname, _, filenames in os.walk(self.path):
            for file_name in filenames:
                music_file = mutagen.File(f'{root_pathname}/{file_name}')
                if music_file:
                    if tag_frame_id in music_file.tags:
                        tag_val = music_file.tags[tag_frame_id].text[0]
                    else:
                        tag_val = None

                    stat[tag_val] = stat.get(tag_val, 0) + 1
        return stat

    # check title existent


class ArtistArchive(Archive):
    pass
    # check artist name
    # stat by updating time


class AlbumArchive(Archive):
    pass
    # check album name
    # if track has number, add to filename
    # add cover picture if exists


class PlaylistArchive(Archive):
    pass
    # numerate filenames by adding time

# My player can see only first elements from text frames lists


if __name__ == '__main__':
    a = Archive('/Users/konstantin/Desktop')
    print(a.get_artist_tag_stat())
    print(a.get_album_tag_stat())
