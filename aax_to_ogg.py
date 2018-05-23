#!/usr/bin/env python3

from glob import glob

from AdhHandler import AdhHandler

OUTPUT_BITRATE=96

SNIP_AUDIBLE=True
SNIP_INTRO=2.2
SNIP_OUTRO=3.6

from pprint import pprint

def handle_adh(filename):
    h = AdhHandler(filename)
    info = h.parse_adh()
    pprint(info)

for filename in glob('*.adh'):
    handle_adh(filename)
