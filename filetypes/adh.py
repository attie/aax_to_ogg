#!/usr/bin/env python3

import json
import shutil
import os.path
import urllib.request
from pprint import pprint
from collections import OrderedDict
from progressbar import ProgressBar, Percentage, Bar, AdaptiveETA

from aax_to_ogg.product import ProductHelper
from aax_to_ogg.library import Library
from aax_to_ogg.filetypes.aax import FileHandler_aax

class FileHandler_adh:
    @staticmethod
    def can_handle_file(filename):
        if filename[-4:] != '.adh':
            return

        return True

    def __init__(self, file_handler, filename):
        if not self.can_handle_file(filename):
            raise Exception('cannot handle the given file...')

        self.file_handler = file_handler
        self.filename = filename

        self.supported_awtypes = {
            'aax': 'aax'
        }
        self.supported_codecs = {
            'mp332': 'mp332'
        }

    def process(self):
        info = self.parse()

        if 'domain' not in info:
            raise Exception('unknown domain...')

        if 'product_id' not in info:
            raise Exception('unknown product_id...')

        if info['product_id'] != 'null':
            search_term = info['product_id']
        else:
            search_term = info['title']

        book_id = ProductHelper.search_for_book_id(info['domain'], search_term)

        if info['product_id'] != book_id:
            print('search for "%s" returned book ID: %s ... is this correct?' % ( search_term, book_id ))

            response = None
            while response not in [ 'y', 'n' ]:
                response = input('[y/n]: ').lower()

            if response != 'y':
                raise Exception('incorrect book ID located...')

        if info['product_id'] == 'null':
            info['product_id'] = ProductHelper.get_product_id(info['domain'], book_id)

        book_metadata = ProductHelper.get_book_metadata(info['domain'], book_id)
        book_path = Library.make_book_absdir(book_metadata)

        print('Storing in "%s"...' % ( book_path ))

        metadata = os.path.join(book_path, '%s.json' % ( book_id ))
        with open(metadata, 'w') as f:
            json.dump(book_metadata, f)

        filename_new = os.path.join(book_path, '%s.adh' % ( book_id ))
        shutil.move(self.filename, filename_new)
        self.filename = filename_new

        new_filename = self.download(info)

        plugin = self.file_handler.get_file_handler(new_filename)

        p = plugin(self.file_handler, new_filename)
        p.split()

    # ---

    def read(self):
        with open(self.filename, 'r') as f:
            return f.read().strip()

    def parse(self):
        text = self.read()
        return OrderedDict(part.split('=', 1) for part in text.split('&'))

    def check_compatibility(self, info):
        if 'awtype' not in info:
            raise Exception('unknown awtype...')
        awtype = info['awtype'].lower()

        if 'codec' not in info:
            raise Exception('unknown codec...')
        codec = info['codec'].lower()

        if awtype in self.supported_awtypes:
            extension = self.supported_awtypes[awtype]
        elif codec in self.supported_codecs:
            extension = self.supported_codecs[codec]
        else:
            raise Exception('unsupported file... [%s]' % ( self.filename ))

        return extension

    def download(self, info):
        extension = self.check_compatibility(info)

        basename, _ = os.path.splitext(self.filename)
        target = '%s.%s' % ( basename, extension )

        if os.path.exists(target):
            raise Exception('target file aready exists... %s' % ( target ))

        url = ProductHelper.get_adh_url(info)

        # uses progressbar2
        prog = ProgressBar(maxval=100, widgets=[
            'Downloading "%s"... ' % ( os.path.basename(target) ),
            Percentage(),
            ' ', Bar(), ' ',
            AdaptiveETA()
        ])

        def report_callback(count, block_size, total_size):
            percent = ((count * block_size) / total_size) * 100
            prog.update(min(percent, 100))

        prog.start()

        opener = urllib.request.build_opener()
        opener.addheaders = [
            ('User-Agent', 'Audible ADM 6.6.0.19;Windows Vista  Build 9200'),
        ]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(url, filename = target, reporthook = report_callback)

        prog.finish()

        return target
