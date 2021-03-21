import datetime
import typing as typ
from pathlib import Path
import os
from itertools import chain
import mimetypes

import mutagen
import mutagen.mp3
import mutagen.id3
import mutagen.flac
import PIL


PICS_EXTENSIONS = ['jpeg', 'jpg', 'png', 'bmp']


class Track:
    AVAILABLE_PICS_MIMETYPES = ['image/jpeg', 'image/png', 'image/bmp']
    AVAILABLE_TRACK_EXTENSIONS = ['mp3', 'flac']  # wav, m4a, aac
    TAG_ALIASES = [
        'title',
        'artist',
        'album',
        'date',
        'composer',
        'tracknumber',
        'genre'
        # quality?
        # lyric?
    ]

    tags: typ.Dict[str, typ.Optional[str]]

    def __init__(self, path: Path):
        if path.suffix.lstrip('.') not in self.AVAILABLE_TRACK_EXTENSIONS:
            raise ValueError(f"given track has extension '{path.suffix.lstrip('.')}', "
                             f"but should be one of follow: {self.AVAILABLE_TRACK_EXTENSIONS}")

        self.__path = path
        self.__mutagen_file = m_file = mutagen.File(path)
        self.new_cover = None

        if isinstance(m_file, mutagen.mp3.MP3):
            if 'TDRC' in m_file:
                date = m_file['TDRC'].text[0]
            elif 'TDAT' in m_file:
                date = m_file['TDAT'].text[0]
            elif 'TYER' in m_file:
                date = m_file['TYER'].text[0]
            else:
                date = None

            self.tags = {
                'title': m_file['TIT2'].text[0] if 'TIT2' in m_file else None,
                'artist': m_file['TPE1'].text[0] if 'TPE1' in m_file else None,
                'album': m_file['TALB'].text[0] if 'TALB' in m_file else None,
                'date': date,
                'composer': m_file['TCOM'].text[0] if 'TCOM' in m_file else None,
                'tracknumber': m_file['TRCK'].text[0] if 'TRCK' in m_file else None,
                'genre': m_file['TCON'].text[0] if 'TCON' in m_file else None
            }
        elif isinstance(m_file, mutagen.flac.FLAC):

            self.tags = {
                'title': m_file['title'][0] if 'title' in m_file else None,
                'artist': m_file['artist'][0] if 'artist' in m_file else None,
                'album': m_file['album'][0] if 'album' in m_file else None,
                'date': m_file['date'][0] if 'date' in m_file else None,
                'composer': m_file['composer'][0] if 'composer' in m_file else None,
                'tracknumber': m_file['tracknumber'][0] if 'tracknumber' in m_file else None,
                'genre': m_file['genre'][0] if 'genre' in m_file else None
            }

    @property
    def path(self):
        return self.__path

    def write(self):
        unexpected_tags = self.tags.keys() - self.TAG_ALIASES
        if self.tags.keys() - self.TAG_ALIASES:
            raise ValueError(f'unexpected tags aliases: {unexpected_tags}')

        if isinstance(self.__mutagen_file, mutagen.mp3.MP3):
            self._fill_tags_to_mp3_mfile()
        elif isinstance(self.__mutagen_file, mutagen.flac.FLAC):
            self._fill_tags_to_flac_mfile()

        self.__mutagen_file.save()

    def _fill_tags_to_mp3_mfile(self):
        m_file = self.__mutagen_file
        if isinstance(m_file, mutagen.mp3.MP3):
            title_val = self.tags.get('title')
            if title_val is not None:
                m_file.tags.add(mutagen.id3.TIT2(text = str(title_val)))
            elif 'TIT2' in m_file.tags:
                del m_file.tags['TIT2']

            artist_val = self.tags.get('artist')
            if artist_val is not None:
                m_file.tags.add(mutagen.id3.TPE1(text = str(artist_val)))
            elif 'TPE1' in m_file.tags:
                del m_file.tags['TPE1']

            album_val = self.tags.get('album')
            if album_val is not None:
                m_file.tags.add(mutagen.id3.TALB(text = str(album_val)))
            elif 'TALB' in m_file.tags:
                del m_file.tags['TALB']

            date_val = self.tags.get('date')
            if date_val is not None:
                if m_file.tags.version == (2, 3, 0):
                    m_file.tags.add(mutagen.id3.TDAT(text = str(date_val)))
                elif m_file.tags.version == (2, 4, 0):
                    m_file.tags.add(mutagen.id3.TDRC(text = str(date_val)))
            elif 'TDAT' in m_file.tags:
                del m_file['TDAT']
            elif 'TDRC' in m_file.tags:
                del m_file['TDRC']
            elif 'TYER' in m_file.tags:
                del m_file['TYER']

            composer_val = self.tags.get('composer')
            if composer_val is not None:
                m_file.tags.add(mutagen.id3.TCOM(text = str(composer_val)))
            elif 'TCOM' in m_file.tags:
                del m_file.tags['TCOM']

            tracknumber_val = self.tags.get('tracknumber')
            if tracknumber_val is not None:
                m_file.tags.add(mutagen.id3.TRCK(text = str(tracknumber_val)))
            elif 'TRCK' in m_file.tags:
                del m_file.tags['TRCK']

            genre_val = self.tags.get('genre')
            if genre_val is not None:
                m_file.tags.add(mutagen.id3.TCON(text = str(genre_val)))
            elif 'TCON' in m_file.tags:
                del m_file.tags['TCON']

    def _fill_tags_to_flac_mfile(self):
        for tag in self.TAG_ALIASES:
            tag_val = self.tags.get(tag)
            if tag_val is not None:
                self.__mutagen_file[tag] = str(tag_val)
            elif tag in self.__mutagen_file.tags:
                del self.__mutagen_file.tags[tag]

    def has_pics(self) -> bool:
        if isinstance(self.__mutagen_file, mutagen.mp3.MP3):
            return any(id3_tag.startswith('APIC') for id3_tag in self.__mutagen_file.tags.keys())
        elif isinstance(self.__mutagen_file, mutagen.flac.FLAC):
            return bool(self.__mutagen_file.pictures)

    def clear_pics(self):
        m_file = self.__mutagen_file
        if isinstance(m_file, mutagen.mp3.MP3):
            for id3_tag in list(m_file.tags.keys()):
                if id3_tag.startswith('APIC'):
                    del m_file.tags[id3_tag]
        elif isinstance(m_file, mutagen.flac.FLAC):
            m_file.clear_pictures()

    def add_cover(self, *, data: bytes, mimetype: str):
        if mimetype not in self.AVAILABLE_PICS_MIMETYPES:
            raise ValueError('unexpected picture mimetype')

        if isinstance(self.__mutagen_file, mutagen.mp3.MP3):
            self.__mutagen_file.tags.add(mutagen.id3.APIC(
                encoding=3,
                mime=mimetype,
                type=3,
                desc=u'cover',
                data=data
            ))
        if isinstance(self.__mutagen_file, mutagen.flac.FLAC):
            pic = mutagen.flac.Picture()
            pic.data = data
            pic.mime = mimetype
            pic.type = 3
            pic.desc = u'cover'
            self.__mutagen_file.add_picture(pic)


class ABCArchive:
    def __init__(self, path: str):
        self.path = Path(path)

    def get_dirs_tracks(self, *, easy) -> typ.Dict[Path, typ.List[mutagen.File]]:
        dir_tracks = dict()
        for root, _, files in os.walk(self.path):
            dir_path = Path(root)
            tracks = (mutagen.File(dir_path/file_name, easy=easy) for file_name in files)
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
    COVER_SIZE_LIMIT_PX = (800, 600)

    def __init__(self, path: str, album_name: str):
        super().__init__(path)
        self.album_name = album_name
        self.last_update_time = None

    def set_album_tag(self):
        folded_album_name = self.album_name.casefold()
        for _, track_list in self.get_dirs_tracks(easy=True):
            for track in track_list:
                if 'album' not in track.tags or folded_album_name not in track.tags['album']:
                    track.tags['album'] = self.album_name
                    track.save()

    # TODO: rename
    # TODO: remove?
    # TODO: rm tracktotal
    def get_dirs_tracks_number_and_dirs_tracks_total(self) -> typ.Tuple[
        typ.Dict[Path, typ.Dict[Path, typ.Optional[int]]],
        typ.Dict[Path, typ.Dict[Path, typ.Optional[int]]]
    ]:
        dir_tracks_number = dict()
        dir_tracks_total = dict()

        for dir_path, track_list in self.get_dirs_tracks(easy=True).items():
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

    def set_cover(self):
        ordered_cover_fname_patterns = list(chain(
            [f'cover.{ext}' for ext in PICS_EXTENSIONS],
            [f'*cover*.{ext}' for ext in PICS_EXTENSIONS],
            [f'*.{ext}' for ext in PICS_EXTENSIONS]
        ))

        root_cover_candidates = list(chain(*(
            self.path.glob(pattern) for pattern in ordered_cover_fname_patterns
        )))

        any_pictures = list(chain(*(
            self.path.rglob(f'*.{ext}') for ext in PICS_EXTENSIONS
        )))

        if any_pictures:
            for dir_path, track_list in self.get_dirs_tracks(easy=False).items():
                cover_candidates_from_this_dir = list(chain(*(
                    dir_path.glob(pattern) for pattern in ordered_cover_fname_patterns
                )))

                cover_candidates = cover_candidates_from_this_dir + root_cover_candidates + any_pictures
                cover_path = cover_candidates[0]
                with PIL.Image.open(cover_path) as cover:
                    # TODO move to func
                    if cover.width > self.COVER_SIZE_LIMIT_PX[0] or cover.self.COVER_SIZE_LIMIT_PX[1]:
                        resize_proportion = min([
                            self.COVER_SIZE_LIMIT_PX[0] / cover.width,
                            self.COVER_SIZE_LIMIT_PX[1] / cover.height,
                            1
                        ])
                        new_size = (int(cover.width * resize_proportion),
                                    int(cover.height * resize_proportion))

                        # TODO try image.tumbnail


                    for track in track_list:
                        if isinstance(track, mutagen.mp3.MP3):
                            track.tags.add_tag(mutagen.id3.APIC(
                                encoding=3,
                                mime=mimetypes.guess_type(cover_path)[0],
                                type=3,
                                desc=u'cover',
                                data=cover.tobytes()
                            ))
                            track.save()
                        if isinstance(track, mutagen.flac.FLAC):
                            pic = mutagen.flac.Picture()
                            pic.data = cover.tobytes()
                            pic.mime = mimetypes.guess_type(cover_path)[0]
                            pic.type = 3
                            pic.desc = u'cover'
                            track.add_picture(pic)
                            track.save()

    def update(self):
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


class SoundCloudArchive(ABCArchive):
    pass


class SpotifyArchive(ABCArchive):
    pass


if __name__ == '__main__':
    a = ABCArchive('/Users/konstantin/Desktop')
    print(a.get_artist_tag_stat())
