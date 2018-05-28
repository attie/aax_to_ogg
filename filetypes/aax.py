#!/usr/bin/env python3

import re
import json
import shutil
import os.path
import subprocess
from multiprocessing import Pool
from pprint import pprint
from aax_to_ogg.util import tell_bounds, human_to_seconds

from aax_to_ogg.args import config
from aax_to_ogg.product import ProductHelper
from aax_to_ogg.library import Library

class FileHandler_aax:
    @staticmethod
    def can_handle_file(filename):
        return re.match('^(?P<book_id>[a-zA-Z0-9]{10})(_ep[56])?\.aax$', os.path.basename(filename))

    def __init__(self, file_handler, filename):
        if not self.can_handle_file(filename):
            raise Exception('cannot handle the given file...')

        self.file_handler = file_handler
        self.filename = filename

    def process(self):
        book_id = self.can_handle_file(self.filename).groupdict()['book_id']
        book_metadata = ProductHelper.get_book_metadata(config.domain, book_id)
        book_path = Library.make_book_absdir(book_metadata)

        metadata = os.path.join(book_path, '%s.json' % ( book_id ))
        with open(metadata, 'w') as f:
            json.dump(book_metadata, f)

        filename_new = os.path.join(book_path, '%s.aax' % ( book_id ))
        shutil.move(self.filename, filename_new)
        self.filename = filename_new

        self.split()

    # ---

    def split(self):
        basename, _ = os.path.splitext(self.filename)

        i = AaxInfo(self.filename)
        s = AaxSplit(i)

        with open('%s.txt' % ( basename ), 'wb') as f:
            for line in i.get_output():
                f.write(line.encode('utf-8'))
                f.write(b'\r\n')

        s.extract_cover_art()
        s.extract_chapters()

class AaxInfo:
    def __init__(self, filename):
        self.filename = filename

        self.metadata = {}
        self.chapters = []
        self.streams = {}

        self.state = -1
        self.lines = None

    def get_output(self):
        if self.state == -1:
            self.run()
        return self.lines

    def get_metadata(self):
        if self.state == -1:
            self.run()
        return self.metadata

    def get_chapters(self):
        if self.state == -1:
            self.run()
        if len(self.chapters) == 0:
            return [ {
                'chapter_id': '0',
                't_start': float(0),
                't_end': self.metadata['duration'],
                'title': None,
            } ]
        return self.chapters

    def run(self):
        args = [
            'ffprobe',
            self.filename
        ]

        kwargs = {
            'stdin': subprocess.DEVNULL,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE
        }

        p = subprocess.run(args, **kwargs)
        # it runs to completion!

        stderr = p.stderr.decode('utf-8')
        self.lines = stderr.rstrip('\n').split('\n')

        self.state = 0
        for line in self.lines:
            state_fname = '_state_%d' % ( self.state )

            state_f = getattr(self, state_fname, None)
            if not callable(state_f):
                raise Exception('invalid state...')

            if state_f(line):
                continue

            self._state_1(line)

    def _state_0(self, line):
        # look for the beginning of the interesting stuff
        if re.match('^Input #[0-9]+', line):
            self.state = 1

        # prevent the other states from being run
        return True

    def _state_1(self, line):
        if re.match('^  Metadata:$', line):
            # this means we're in the "metadata" section...
            self.state = 2
        elif re.match('^  Duration: ', line):
            # this means we're in the "chapter" section..."
            self.state = 3

            m = re.match('^  Duration: (?P<duration>[0-9:\.]+), start: (?P<t_start>[0-9]+(?:\.[0-9]+)?), bitrate: (?P<bitrate>[0-9]+) kb/s', line)
            if m is not None:
                m = m.groupdict()
                self.metadata['bitrate'] = int(m['bitrate'])
                self.metadata['duration'] = human_to_seconds(m['duration'])

        # returning other than True will cause us to be run _again_
        return True

    def _state_2(self, line):
        # process metadata key/value pairs
        key, value = ( _.strip() for _ in line.split(':', 1) )
        if key not in self.metadata:
            self.metadata[key] = value

    def _state_3(self, line):
        # process chapter information
        m = re.match('^    Chapter #(?P<chapter_id>[0-9]+(:[0-9]+)?): start (?P<t_start>[0-9]+(?:\.[0-9]+)?), end (?P<t_end>[0-9]+(?:\.[0-9]+)?)$', line)
        if m is not None:
            m = m.groupdict()
            self.chapters.append({
                'chapter_id': m['chapter_id'],
                't_start': float(m['t_start']),
                't_end': float(m['t_end']),
                'title': None, # we just give it a NULL title for now
            })

        m = re.match('^      title +: (?P<title>.+)$', line)
        if m is not None:
            # ah hah! now the title is filled in
            self.chapters[-1] = { **self.chapters[-1], **m.groupdict() }

        m = re.match('^    Stream #(?P<stream_id>[0-9]+(:[0-9]+)?)(\((?P<lang>[^\)]+)\))?: (?P<type>[^:]+): (?P<format>.+)$', line)
        if m is not None:
            stream = m.groupdict()
            m = re.match('^(?P<codec>mp3), (?P<sample_rate>[0-9]+) Hz, (?P<channels>stereo|mono), (?P<sample_shape>(s|u)(8|16|24|32)p?), (?P<bitrate>[0-9]+) kb/s', stream['format'])
            if m is not None:
                stream['mp3'] = m.groupdict()
            m = re.match('^(?P<codec>aac) \(LC\) \(aavd / 0x[0-9a-fA-F]+\), (?P<sample_rate>[0-9]+) Hz, (?P<channels>stereo|mono), (?P<sample_shape>((s|u)(8|16|24|32)|flt)p?), (?P<bitrate>[0-9]+) kb/s', stream['format'])
            if m is not None:
                stream['aac'] = m.groupdict()

            self.streams[stream['stream_id']] = stream

class AaxSplit:
    def __init__(self, aax_info):
        self.aax_info = aax_info
        self.basename, _ = os.path.splitext(self.aax_info.filename)

        m = aax_info.get_metadata()
        if 'bitrate' in m:
            self.bitrate = m['bitrate']
        else:
            self.bitrate = config.bitrate

        self.activation_bytes = self.pick_activation_bytes()

    def pick_activation_bytes(self):
        for ab in [ None, *config.activation_bytes ]:
            if self.test_activation_bytes(ab):
                return ab

        raise Exception('unable to decrypt AAX... missing activation bytes...')

    def test_activation_bytes(self, activation_bytes):
        args = [
            'ffmpeg',
            '-y',
        ]
        if activation_bytes is not None:
            args.extend([
                '-activation_bytes', activation_bytes,
            ])
        args.extend([
            '-ss', '0',
            '-i', self.aax_info.filename,
            '-to', '0.01',
            '-vn',
            '-codec:a', 'libvorbis',
            '-f', 'ogg',
            '/dev/null'
        ])

        kwargs = {
            'stdin': subprocess.DEVNULL,
            'stdout': subprocess.DEVNULL,
            'stderr': subprocess.DEVNULL
        }

        p = subprocess.run(args, **kwargs)
        return p.returncode == 0

    def extract_cover_art(self):
        args = [
            'ffmpeg',
            '-y',
            '-i', self.aax_info.filename,
            '-an',
            '-vsync', '2',
            '%s.jpg' % ( self.basename )
        ]

        kwargs = {
            'stdin': subprocess.DEVNULL,
            'stdout': subprocess.DEVNULL,
            'stderr': subprocess.DEVNULL
        }

        p = subprocess.run(args, **kwargs)

    def extract_chapters(self):
        pool = Pool(processes=config.parallel)

        for i, first, last, chapter in tell_bounds(self.aax_info.get_chapters()):
            if not config.no_snip:
                if first:
                    chapter['t_start'] += config.snip_intro_len
                    self.extract_chapter(self.aax_info.filename, i, 0, chapter['t_start'], 'This is Audible', pool=pool)
                if last:
                    t = chapter['t_end'] - config.snip_outro_len
                    self.extract_chapter(self.aax_info.filename, i + 2, t, chapter['t_end'], 'Audible hopes you have enjoied...', pool=pool)
                    chapter['t_end'] = t

            self.extract_chapter(self.aax_info.filename, i + 1, chapter['t_start'], chapter['t_end'], chapter['title'], pool=pool)

        pool.close()
        pool.join()

    def extract_chapter(self, input_filename, num, t_start, t_end, title, pool=None):
        if pool is not None:
            pool.apply_async(self.extract_chapter, (input_filename, num, t_start, t_end, title))
            return

        args = [
            'ffmpeg',
            '-y',
            '-loglevel', 'error',
        ]
        if self.activation_bytes is not None:
            args.extend([
                '-activation_bytes', self.activation_bytes,
            ])
        args.extend([
            '-accurate_seek',
            '-ss', '%.6f' % ( t_start ),
            '-i', input_filename,
            '-to', '%.6f' % ( t_end - t_start ),
            '-vn',
            '-codec:a', 'libvorbis',
            '-ab', '%dk' % ( self.bitrate ),
            '%s_part%03d.ogg' % ( self.basename, num )
        ])

        kwargs = {
            'stdin': subprocess.DEVNULL,
            'stdout': subprocess.DEVNULL
        }

        print('    Extracting #%d... (%s)' % ( num, title ))

        subprocess.run(args, **kwargs)
