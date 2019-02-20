from pprint import pprint

import re
import urllib.parse, urllib.request
from lxml import html

class ProductHelper:
    xpath_search_item_all   = "//li[contains(concat(' ',normalize-space(@class),' '),' productListItem ')]"

    @staticmethod
    def get_search_url(domain, search_keywords):
        prefix = 'https://' + domain + '/search?'
        return prefix + urllib.parse.urlencode({ 'advsearchKeywords': search_keywords })

    @staticmethod
    def get_book_url(domain, book_id):
        # TODO: handle 302 here?
        prefix = 'https://' + domain + '/pd/'
        return prefix + book_id

    @staticmethod
    def get_adh_url(info):
        prefix = 'http://cdl.audible.com/cgi-bin/aw_assemble_title_dynamic.aa?'
        url = prefix + urllib.parse.urlencode(info)
        return url

    @classmethod
    def product_id_to_book_id(cls, domain, product_id):
        # search for the product ID
        url = cls.get_search_url(domain, product_id)
        with urllib.request.urlopen(url) as search_req:
            et = html.fromstring(search_req.read())

        # pick out the link that _should_ point at the book's ID
        book_paths = et.xpath(cls.xpath_search_item_all + "//a[contains(concat(' ',normalize-space(@class),' '),' bc-link ')][starts-with(@href,'/pd/')][img]/@href")
        if len(book_paths) < 1:
            raise Exception('no results for book search...')

        if len(book_paths) > 1:
            print('WARNING: multiple results for book search...')

        book_id = book_paths[0].rsplit('/', 1)
        if len(book_id) != 2 or len(book_id[-1]) != 10:
            raise Exception('unexpected book ID... - %s' % ( book_id ))
        book_id = book_id[-1]

        return book_id

    @classmethod
    def get_book_metadata(cls, domain, book_id):
        data = {
            'title': None,
            'author': None,
            'narrator': None,
            'series': None,
            'publisher': None,
        }

        # load the book's page
        url = cls.get_book_url(domain, book_id)
        with urllib.request.urlopen(url) as search_req:
            et = html.fromstring(search_req.read())

        #with open('x.html', 'wb') as f:
        #    f.write(html.tostring(et))

        #with open('x.html', 'rb') as f:
        #    et = html.fromstring(f.read())

        data = {}

        datapoints = {
            'title':        { 'xpath_append': "/h1/text()",                   'class': 'bc-list-item'     },
            'author':       { 'xpath_append': "/a/text()",                    'class': 'authorLabel'      },
            'narrator':     { 'xpath_append': "/a/text()",                    'class': 'narratorLabel'    },
            'publisher':    { 'xpath_append': "/a/text()",                    'class': 'publisherLabel'   },
            'release_date': { 'xpath_append': "/text()",                      'class': 'releaseDateLabel', 'regex_match': '^Release date: (?P<d>[0-9]{2})-(?P<m>[0-9]{2})-(?P<y>[0-9]{2})$', 'replace': '20%(y)s-%(m)s-%(d)s' },
            'series':       { 'xpath_append': "/a/text()",                    'class': 'seriesLabel'      },
            'series_book':  { 'xpath_append': "/a/following-sibling::text()", 'class': 'seriesLabel',      'regex_match': '^, (?P<book>.*)$', 'replace': '%(book)s' },
            'series_link':  { 'xpath_append': "/a/@href",                     'class': 'seriesLabel'      },

        }
        for key, info in datapoints.items():
            if 'xpath' not in info:
                info['xpath'] = "//li[contains(concat(' ',normalize-space(@class),' '),' %(class)s ')]"
            if 'xpath_append' in info:
                info['xpath'] += info['xpath_append']

            info['xpath'] = info['xpath'] % ( info )

            x = et.xpath(info['xpath'])
            if len(x) != 1:
                data[key] = None
                continue

            value = ' '.join(x[0].split())

            if 'regex_match' in info and 'replace' in info:
                match = re.match(info['regex_match'], value)
                value = info['replace'] % ( match.groupdict() )

            data[key] = value

        if data['series_book'] is not None:
            if data['series_book'][:2] == ', ':
                data['series_book'] = data['series_book'][2:]
            if data['series_book'][:5] == 'Book ':
                data['series_book'] = float(data['series_book'][5:])

        if data['series_link'] is not None:
            data['series_link'] = data['series_link'].rsplit('=', 1)[-1]

        return data
