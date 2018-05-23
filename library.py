import os

from aax_to_ogg.util import safe_filename

class Library:
    @staticmethod
    def build_book_dir(book_metadata):
        path = []

        if book_metadata['series'] is not None:
            path.append(book_metadata['series'])
            
        book_title = ''
        if book_metadata['series_book'] is not None:
            book_title += '%s' % ( book_metadata['series_book'] )
        if book_metadata['title'] is not None:
            if book_title != '':
                book_title += ' - '
            book_title += book_metadata['title']
        if book_title != '':
            path.append(book_title)

        # only fix up the first component of the path...
        if len(path) > 0 and path[0][:4] == 'The ':
            path[0] = '%s, The' % ( path[0][4:] )

        return os.path.join(*[ safe_filename(p) for p in path ])

    @classmethod
    def build_book_absdir(cls, library_path, book_metadata):
        book_path = cls.build_book_dir(book_metadata)
        book_path = os.path.join(library_path, book_path)
        return os.path.abspath(book_path)

    @classmethod
    def make_book_absdir(cls, library_path, book_metadata):
        book_path = cls.build_book_absdir(library_path, book_metadata)
        os.makedirs(book_path, exist_ok=True)
        return book_path
