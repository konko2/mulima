import typing as typ
from pathlib import Path
from datetime import datetime

import mutagen
import mutagen.mp3
import mutagen.id3
import mutagen.flac


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
        'mulima_upd_time'
        # quality?
        # lyric?
    ]

    UPD_TIME_TAG_FORMAT = '%d.%m.%Y %H:%M'

    is_modified: bool

    #TODO: rename? to Track.is(path), Track.is_file(path), Track.file_is_proper_track(path)
    @classmethod
    def could_created_from(cls, path: Path) -> bool:
        return path.suffix.lstrip('.') in cls.AVAILABLE_TRACK_EXTENSIONS

    def __init__(self, path: Path):
        if not self.could_created_from(path):
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

            if 'TXXX:_mulima_upd_time' in m_file.tags:
                mulima_upd_time = m_file['TXXX:_mulima_upd_time'].text[0]
            else:
                mulima_upd_time = None

            self.__tags = {
                'title': m_file['TIT2'].text[0] if 'TIT2' in m_file else None,
                'artist': m_file['TPE1'].text[0] if 'TPE1' in m_file else None,
                'album': m_file['TALB'].text[0] if 'TALB' in m_file else None,
                'date': date,
                'composer': m_file['TCOM'].text[0] if 'TCOM' in m_file else None,
                'tracknumber': m_file['TRCK'].text[0] if 'TRCK' in m_file else None,
                'genre': m_file['TCON'].text[0] if 'TCON' in m_file else None,
                'mulima_upd_time': mulima_upd_time
            }
        elif isinstance(m_file, mutagen.flac.FLAC):
            if '_mulima_upd_time' in m_file.tags:
                mulima_upd_time = m_file['_mulima_upd_time'][0]
            else:
                mulima_upd_time = None

            self.__tags = {
                'title': m_file['title'][0] if 'title' in m_file else None,
                'artist': m_file['artist'][0] if 'artist' in m_file else None,
                'album': m_file['album'][0] if 'album' in m_file else None,
                'date': m_file['date'][0] if 'date' in m_file else None,
                'composer': m_file['composer'][0] if 'composer' in m_file else None,
                'tracknumber': m_file['tracknumber'][0] if 'tracknumber' in m_file else None,
                'genre': m_file['genre'][0] if 'genre' in m_file else None,
                'mulima_upd_time': mulima_upd_time
            }

        self.is_modified = False

    def get_path(self) -> Path:
        return self.__path

    def get_mulima_upd_time(self):
        return datetime.strptime(self.get_tag('mulima_upd_time'), self.UPD_TIME_TAG_FORMAT)

    def get_tags(self):
        return self.__tags.copy()

    def get_tag(self, tag: str) -> str:
        if tag not in self.TAG_ALIASES:
            raise ValueError(f'unexpected tag alias: {tag}')

        return self.__tags[tag]

    def set_tag(self, tag: str, value: typ.Optional[str]) -> None:
        self.is_modified = True

        if tag not in self.TAG_ALIASES:
            raise ValueError(f'unexpected tag alias: {tag}')

        if tag is 'mulima_upd_time':
            raise ValueError(f'read-only tag')

        self.__tags[tag] = value

    def remove_tag(self, tag):
        self.set_tag(tag, None)

    def write(self):
        if self.is_modified:
            if isinstance(self.__mutagen_file, mutagen.mp3.MP3):
                self._fill_tags_to_mp3_mfile()
            elif isinstance(self.__mutagen_file, mutagen.flac.FLAC):
                self._fill_tags_to_flac_mfile()

            self.__mutagen_file.save()

    def _fill_tags_to_mp3_mfile(self):
        m_file = self.__mutagen_file
        if isinstance(m_file, mutagen.mp3.MP3):
            title_val = self.__tags.get('title')
            if title_val is not None:
                m_file.tags.add(mutagen.id3.TIT2(text = str(title_val)))
            elif 'TIT2' in m_file.tags:
                del m_file.tags['TIT2']

            artist_val = self.__tags.get('artist')
            if artist_val is not None:
                m_file.tags.add(mutagen.id3.TPE1(text = str(artist_val)))
            elif 'TPE1' in m_file.tags:
                del m_file.tags['TPE1']

            album_val = self.__tags.get('album')
            if album_val is not None:
                m_file.tags.add(mutagen.id3.TALB(text = str(album_val)))
            elif 'TALB' in m_file.tags:
                del m_file.tags['TALB']

            date_val = self.__tags.get('date')
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

            composer_val = self.__tags.get('composer')
            if composer_val is not None:
                m_file.tags.add(mutagen.id3.TCOM(text = str(composer_val)))
            elif 'TCOM' in m_file.tags:
                del m_file.tags['TCOM']

            tracknumber_val = self.__tags.get('tracknumber')
            if tracknumber_val is not None:
                m_file.tags.add(mutagen.id3.TRCK(text = str(tracknumber_val)))
            elif 'TRCK' in m_file.tags:
                del m_file.tags['TRCK']

            genre_val = self.__tags.get('genre')
            if genre_val is not None:
                m_file.tags.add(mutagen.id3.TCON(text = str(genre_val)))
            elif 'TCON' in m_file.tags:
                del m_file.tags['TCON']

            m_file.tags.add(mutagen.id3.TXXX(
                desc='_mulima_upd_time',
                text=str(datetime.now())
            ))

    def _fill_tags_to_flac_mfile(self):
        equal_tag_names = ['title', 'artist', 'album', 'date', 'composer', 'tracknumber', 'genre']
        for tag in equal_tag_names:
            tag_val = self.__tags.get(tag)
            if tag_val is not None:
                self.__mutagen_file[tag] = str(tag_val)
            elif tag in self.__mutagen_file.tags:
                del self.__mutagen_file.tags[tag]

        self.__mutagen_file.tags['_mulima_upd_time'] = str(datetime.now())

    def has_pics(self) -> bool:
        if isinstance(self.__mutagen_file, mutagen.mp3.MP3):
            return any(id3_tag.startswith('APIC') for id3_tag in self.__mutagen_file.tags.keys())
        elif isinstance(self.__mutagen_file, mutagen.flac.FLAC):
            return bool(self.__mutagen_file.pictures)

    def clear_pics(self):
        self.is_modified = True

        m_file = self.__mutagen_file
        if isinstance(m_file, mutagen.mp3.MP3):
            for id3_tag in list(m_file.tags.keys()):
                if id3_tag.startswith('APIC'):
                    del m_file.tags[id3_tag]
        elif isinstance(m_file, mutagen.flac.FLAC):
            m_file.clear_pictures()

    def set_cover(self, *, data: bytes, mimetype: str):
        if mimetype not in self.AVAILABLE_PICS_MIMETYPES:
            raise ValueError('unexpected picture mimetype')

        self.is_modified = True

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

    @classmethod
    def rename(cls, filepath: Path, formatting_pattern: str):
        """
        rename track due to it's tags
        :param filepath: original path to file
        :param formatting_pattern: Pattern, used to build new track filename.
        Use names in Track.TAG_ALIASES as keyword parameters for string's format method, to replace it with tag values
        :return:
        """
        track = cls(filepath)
        tags = {tag: '' if val is None else val for tag, val in track.get_tags().items()}

        filename = formatting_pattern.format(**tags)
        if filename is not filepath.stem:
            filepath.rename(filepath.parent + filename + filepath.suffix)
