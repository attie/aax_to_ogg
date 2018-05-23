import argparse
import os.path
import multiprocessing

class Args:
    def __init__(self):
        self.p = argparse.ArgumentParser(description = 'Process ADH or AAX files in to Ogg/Vorbis')

        # TODO: default = None - auto detect new users, and store the activation bytes _somewhere_
        self.p.add_argument('-a', '--activation-bytes',
            type=str, action='append',
            help='the activation bytes used by ffmpeg to decrypt the AAX files',
            default=[]
        )

        self.p.add_argument('-b', '--bitrate',
            type=int, action='store',
            help='the output bitrate to use, in kb/s',
            default=96
        )

        self.p.add_argument('-p', '--parallel',
            type=int, action='store',
            help='the number of ffmpeg processes to run in parallel',
            default=multiprocessing.cpu_count()
        )

        self.p.add_argument('-d', '--domain',
            type=str, action='store',
            help='the Audible domain to use when locating metadata (only use for direct AAX ingestion)',
            default='www.audible.co.uk'
        )

        self.p.add_argument('-l', '--library',
            type=os.path.abspath, action='store',
            help='the directory to use as the library',
            default='./audio'
        )

        self.p.add_argument('-s', '--no-snip',
            action='store_true',
            help='do not snip the "This is Audible", and "Audible hopes you have enjoied" from the first and last chapters'
        )

        self.p.add_argument('-i', '--snip-intro-len',
            type=float, action='store',
            help='how many seconds to snip when removing the intro',
            default=2.2
        )

        self.p.add_argument('-o', '--snip-outro-len',
            type=float, action='store',
            help='how many seconds to snip when removing the outro',
            default=3.6
        )

        self.p.add_argument('--debug',
            action='store_true',
            help='enable debug mode'
        )

        self.p.add_argument('files',
            type=str, action='store',nargs='+', 
            help='the file(s) to convert'
        )

    def parse(self):
        return self.p.parse_args()
