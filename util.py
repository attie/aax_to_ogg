import re

"""
    yields once for each item in iterable
    yields ( i, first, last, item )
    the very first yield will have first = True
    the very last yield will have last = True
    all yields will have i incrementing, starting from 0
"""
def tell_bounds(iterable):
    it = iter(iterable)

    count = 0
    first = True

    prev = next(it)
    for val in it:
        yield count, first, False, prev
        prev = val

        count += 1
        first = False

    yield count, first, True, prev

def safe_filename(filename):
    # 'Blah: This' becomes 'Blah - This'
    filename = re.sub(' *: +', ' - ', filename)

    # limit the permitted characters, hard
    keep_chars = ( ' ', '.', '_', '-' )
    filename = ''.join(c for c in filename if c.isalnum() or c in keep_chars).rstrip()

    # cannot end with a dot... for Windows
    filename = re.sub('\.+$', '', filename)

    return filename

def human_to_seconds(human):
    # we expect 'human' to be clock time - e.g: '07:37:22.21'
    # what about things that are >24h??

    sec = 0
    for t in human.split(':'):
        sec *= 60
        sec += float(t)

    return sec
