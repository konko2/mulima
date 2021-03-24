from datetime import datetime
import typing as typ
from pathlib import Path
import os
from itertools import chain
import mimetypes
from collections import Counter

from mulima.track_processor import Track

from PIL import Image


class ABCArchive:
    last_update_time: typ.Optional[datetime]

    def __init__(self, path: str):
        self.path = Path(path)
        self.last_update_time = None

    def find_tracks(self) -> typ.List[Path]:
        tracks = list()
        for _, _, files in os.walk(self.path):
            for file in files:
                filepath = Path(file)
                if Track.could_created_from(filepath):
                    tracks.append(filepath)

        return tracks

    @staticmethod
    def manage_title_tags(track_list: typ.List[Track]):
        for track in track_list:
            if track.get_tag('title') is None:
                track.set_tag('title', track.get_path().stem)

    def update(self, *, new_only: bool):
        """
        updates tracks info
        :param new_only: if True will consider only new founded tracks
        :param filename_pattern: if not None will rename track's filename due to it's tags
        :return:
        """
        raise NotImplementedError

    # def sync(self):
    #     raise NotImplementedError
    #
    # def stat(self):
    #     raise NotImplementedError
    #
    # def json_load(self):
    #     raise NotImplementedError


class ArtistArchive(ABCArchive):
    ordered_possible_artist_names: typ.List[str]
    case_sensitive: bool

    def __init__(self, path: str, ordered_possible_artist_names: typ.List[str], *, case_sensitive: bool = True):
        super().__init__(path)

        self.ordered_possible_artist_names = ordered_possible_artist_names
        self.case_sensitive = case_sensitive

    def manage_artist_tags(self, track_list: typ.List[Track], *, missed_only: bool):
        casefolded_possible_artist_names = {name.casefold() for name in self.ordered_possible_artist_names}

        for track in track_list:
            artist_tag_value = track.get_tag('artist')
            if artist_tag_value is None:
                track.set_tag('artist', self.ordered_possible_artist_names[0])
            elif missed_only is not None:
                if self.case_sensitive:
                    if any(artist_name in artist_tag_value
                           for artist_name in self.ordered_possible_artist_names):
                        continue
                    track.set_tag('artist', self.ordered_possible_artist_names[0])
                else:
                    folded_artist_tag_value = artist_tag_value.casefold()
                    if any(folded_artist_name in folded_artist_tag_value
                           for folded_artist_name in casefolded_possible_artist_names):
                        continue  # for example collaboration of artists, tag could be 'A & B (feat C)'
                    track.set_tag('artist', self.ordered_possible_artist_names[0])

    @staticmethod
    def update_filenames(filepath_list: typ.List[Path]):
        for filepath in filepath_list:
            desirable_filename = Track(filepath).get_tag('title')
            if filepath.stem is not desirable_filename:
                Track.rename(filepath, desirable_filename)

    def update(self, *, new_only: bool = True):
        track_list = [Track(filepath) for filepath in self.find_tracks()]
        if new_only and self.last_update_time is not None:
            track_list = [track for track in track_list
                          if track.get_mulima_upd_time() > self.last_update_time]

        self.manage_artist_tags(track_list, missed_only=False)
        self.manage_title_tags(track_list)

        for track in track_list:
            track.write()

        self.update_filenames([track.get_path() for track in track_list])

        self.last_update_time = datetime.now()


class AlbumArchive(ABCArchive):
    COVER_PIC_MAX_SIZE = (600, 600)  # in pixels
    album_name: str

    def __init__(self, path: str, album_name: str):
        super().__init__(path)
        self.album_name = album_name

    def manage_album_tags(self, track_list: typ.List[Track]):
        for track in track_list:
            album_tag_value = track.get_tag('album')

            # album tag name could contain part info (like 'album p.1'), so
            # finding album name in tag value is proper check than equality
            if album_tag_value is None or self.album_name not in album_tag_value:
                track.set_tag('album', self.album_name)

    @staticmethod
    def manage_tracknumber_tags(tracks_by_album_and_directory: typ.Dict[(str, Path), typ.List[Track]]):
        for track_list in tracks_by_album_and_directory.values():
            # do not use int for tracknumber, because it could be with letters: '1a',''2b'
            tracknumbers_quantities = Counter([track.get_tag('tracknumber') for track in track_list
                                               if track.get_tag('tracknumber') is not None])

            if any(quantity > 1 for quantity in tracknumbers_quantities.values()):
                for track in track_list:
                    track.remove_tag('tracknumber')

    @staticmethod
    def manage_tracktotal_tags(tracks_by_album_and_directory: typ.Dict[(str, Path), typ.List[Track]]):
        for track_list in tracks_by_album_and_directory.values():
            tracktotals_values = {track.get_tag('tracktotal') for track in track_list
                                  if track.get_tag('tracktotal') is not None}

            if len(tracktotals_values) > 1:
                for track in track_list:
                    track.remove_tag('tracktotal')

    def manage_covers(self, tracks_by_directory: typ.Dict[Path, typ.List[Track]]):
        pics_extensions = [mimetypes.guess_extension(mt).lstip('.')
                           for mt in Track.AVAILABLE_PICS_MIMETYPES]

        ordered_cover_fname_patterns = list(chain(
            [f'cover.{ext}' for ext in pics_extensions],
            [f'*cover*.{ext}' for ext in pics_extensions],
            [f'*.{ext}' for ext in pics_extensions]
        ))

        root_cover_candidates = list(chain(*(
            self.path.glob(pattern) for pattern in ordered_cover_fname_patterns
        )))

        any_pictures = list(chain(*(
            self.path.rglob(f'*.{ext}') for ext in pics_extensions
        )))

        if any_pictures:
            for dir_path, track_list in tracks_by_directory.items():
                this_dir_cover_candidates = list(chain(*(
                    dir_path.glob(pattern) for pattern in ordered_cover_fname_patterns
                )))

                cover_candidates = this_dir_cover_candidates + root_cover_candidates + any_pictures
                cover_path = cover_candidates[0]

                cover = Image.open(cover_path)
                cover.tumbnail(self.COVER_PIC_MAX_SIZE)
                cover_data = cover.tobytes()

                cover_mimetype = mimetypes.guess_type(cover_path)
                for track in track_list:
                    track.set_cover(data=cover_data, mimetype=cover_mimetype)

    @staticmethod
    def _get_tracks_by_album_and_directory(
            track_list: typ.List[Track]
    ) -> typ.Dict[typ.Tuple[str, Path], typ.List[Track]]:
        tracks_by_album_and_directory = dict()
        for track in track_list:
            directory = track.get_path().parent
            album_tag_val = track.get_tag('album')

            if (album_tag_val, directory) not in tracks_by_album_and_directory:
                tracks_by_album_and_directory[(album_tag_val, directory)] = list()
            tracks_by_album_and_directory[(album_tag_val, directory)].append(track)

        return tracks_by_album_and_directory

    @staticmethod
    def _get_tracks_by_directory(track_list: typ.List[Track]) -> typ.Dict[Path, typ.List[Track]]:
        tracks_by_directory = dict()
        for track in track_list:
            directory = track.get_path().parent

            if directory not in tracks_by_directory:
                tracks_by_directory[directory] = list()
            tracks_by_directory[directory].append(track)

        return tracks_by_directory

    @staticmethod
    def update_filenames(track_filepath_by_directory: typ.Dict[Path, typ.List[Path]]):
        for filepath_list in track_filepath_by_directory.values():
            track_list = [Track(filepath) for filepath in filepath_list]
            tracknumber_list = [track.get_tag('tracknumber') for track in track_list]

            evey_tracknumber_unique = len(set(tracknumber_list)) == len(tracknumber_list)
            use_tracknumber_if_filenames = False
            if None not in tracknumber_list and evey_tracknumber_unique:
                use_tracknumber_if_filenames = True

            for track in track_list:
                filepath = track.get_path()
                title, tracknumber = track.get_tag('title'), track.get_tag('tracknumber')
                desirable_filename = f'{tracknumber}. {title}' if use_tracknumber_if_filenames else f'{title}'

                if filepath.stem is not desirable_filename:
                    Track.rename(filepath, desirable_filename)

    def update(self, *, new_only: bool):
        track_list = [Track(filepath) for filepath in self.find_tracks()]
        if new_only and self.last_update_time is not None:
            track_list = [track for track in track_list
                          if track.get_mulima_upd_time() > self.last_update_time]

        tracks_by_directory = self._get_tracks_by_directory(track_list)
        tracks_by_album_and_directory = self._get_tracks_by_album_and_directory(track_list)

        self.manage_album_tags(track_list)
        self.manage_tracknumber_tags(tracks_by_album_and_directory)
        self.manage_tracktotal_tags(tracks_by_album_and_directory)
        self.manage_covers(tracks_by_directory)
        self.manage_title_tags(track_list)

        for track in track_list:
            track.write()

        self.update_filenames({directory: [track.get_path() for track in track_list]
                               for directory, track_list in tracks_by_directory.items()})

        self.last_update_time = datetime.now()
