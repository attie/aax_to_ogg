# Overview

## What is it?

This utility will take `*.adh` or `*.aax` files as provided by Audible, strip the DRM, and split them into chapters.
It will also attempt to locate metadata and orgaise the resulting files into a library.

Chapters will be split and the transcoding will run in parallel - one job per CPU thread.

## What does it need?

You will need to have `ffmepg` installed on your system, and you will need to have your "_activation bytes_" to decrypt protected content.

## Usage

```bash
$ python3 -m aax_to_ogg
usage: aax_to_ogg [-h] [-a ACTIVATION_BYTES] [-b BITRATE] [-p PARALLEL]
                  [-d DOMAIN] [-l LIBRARY] [-s] [-i SNIP_INTRO_LEN]
                  [-o SNIP_OUTRO_LEN] [--debug]
                  files [files ...]

Process ADH or AAX files in to Ogg/Vorbis

positional arguments:
  files                 the file(s) to convert

optional arguments:
  -h, --help            show this help message and exit
  -a ACTIVATION_BYTES, --activation-bytes ACTIVATION_BYTES
                        the activation bytes used by ffmpeg to decrypt the AAX
                        files
  -b BITRATE, --bitrate BITRATE
                        the output bitrate to use, in kb/s
  -p PARALLEL, --parallel PARALLEL
                        the number of ffmpeg processes to run in parallel
  -d DOMAIN, --domain DOMAIN
                        the Audible domain to use when locating metadata (only
                        use for direct AAX ingestion)
  -l LIBRARY, --library LIBRARY
                        the directory to use as the library
  -s, --no-snip         do not snip the "This is Audible", and "Audible hopes
                        you have enjoied" from the first and last chapters
  -i SNIP_INTRO_LEN, --snip-intro-len SNIP_INTRO_LEN
                        how many seconds to snip when removing the intro
  -o SNIP_OUTRO_LEN, --snip-outro-len SNIP_OUTRO_LEN
                        how many seconds to snip when removing the outro
  --debug               enable debug mode
```
