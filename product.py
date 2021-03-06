from pprint import pprint

import re
import urllib.parse, urllib.request
import json
from sys import stderr
from lxml import html
from collections import OrderedDict

from aax_to_ogg.args import config

class ProductHelper:
    xpath_search_item_all   = "//li[contains(concat(' ',normalize-space(@class),' '),' productListItem ')]"
    xpath_product_info_json = "//div[@id='bottom-0']/script[2]/text()"

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
        arg_keys = [
            'user_id',
            'product_id',
            'codec',
            'awtype',
            'cust_id',
        ]

        prefix = info['assemble_url']

        args = OrderedDict()
        for arg_key in arg_keys:
            args[arg_key] = info[arg_key]

        url = prefix + '?' + urllib.parse.urlencode(args)

        return url

    @classmethod
    def search_for_book_id(cls, domain, search_term):
        # search for the book ID
        url = cls.get_search_url(domain, search_term)
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
    def get_product_id(cls, domain, book_id):
        url = cls.get_book_url(domain, book_id)
        with urllib.request.urlopen(url) as book_req:
            et = html.fromstring(book_req.read())

        info_json_raw = et.xpath(cls.xpath_product_info_json)
        if len(info_json_raw) < 1:
            raise Exception('no info JSON located...')

        if len(info_json_raw) > 1:
            print('WARNING: multiple info JSON options located...')

        for ij in info_json_raw:
            try:
                ij = json.loads(ij)
                product_id = ij[0]['sku']
                return product_id
            except:
                continue

        raise Exception('no valid info JSON options located...')

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
        url = cls.get_search_url(domain, book_id)
        if config.debug:
            print('Retrieving book metadata from [%s]' % ( url ), file=stderr)

        with urllib.request.urlopen(url) as search_req:
            et = html.fromstring(search_req.read())

        #with open('x.html', 'wb') as f:
        #    f.write(html.tostring(et))

        #with open('x.html', 'rb') as f:
        #    et = html.fromstring(f.read())

        data = {}

        datapoints = {
            'title':        { 'xpath_append': "/h3/a/text()",                      'class': 'bc-list-item'     },
            'author':       { 'xpath_append': "/span/a/text()",                    'class': 'authorLabel'      },
            'narrator':     { 'xpath_append': "/span/a/text()",                    'class': 'narratorLabel'    },
            'publisher':    { 'xpath_append': "/span/a/text()",                    'class': 'publisherLabel'   },
            'release_date': { 'xpath_append': "/span/text()",                      'class': 'releaseDateLabel', 'regex_match': '^Release date: (?P<d>[0-9]{2})-(?P<m>[0-9]{2})-(?P<y>[0-9]{2})$', 'replace': '20%(y)s-%(m)s-%(d)s' },
            'series':       { 'xpath_append': "/span/a/text()",                    'class': 'seriesLabel'      },
            'series_book':  { 'xpath_append': "/span/a/following-sibling::text()", 'class': 'seriesLabel',      'regex_match': '^, (?P<book>.*)$', 'replace': '%(book)s' },
            'series_link':  { 'xpath_append': "/span/a/@href",                     'class': 'seriesLabel'      },

        }
        for key, info in datapoints.items():
            if 'xpath' not in info:
                info['xpath']  = cls.xpath_search_item_all + "[1]"
                info['xpath'] += "//li[contains(concat(' ',normalize-space(@class),' '),' %(class)s ')]"
            if 'xpath_append' in info:
                info['xpath'] += info['xpath_append']

            info['xpath'] = info['xpath'] % ( info )

            if config.debug:
                print('=== %s ===' % ( key ), file=stderr)
                print('       XPath: %s' % ( info['xpath'] ), file=stderr)

            x = et.xpath(info['xpath'])
            if len(x) != 1:
                data[key] = None
                continue

            value = ' '.join(x[0].split())

            if config.debug:
                print('Before Fixup: %s' % ( value ), file=stderr)

            if 'regex_match' in info and 'replace' in info:
                match = re.match(info['regex_match'], value)
                value = info['replace'] % ( match.groupdict() )

            if config.debug:
                print(' After Fixup: %s' % ( value ), file=stderr)

            data[key] = value

        if data['series_book'] is not None:
            if data['series_book'][:2] == ', ':
                data['series_book'] = data['series_book'][2:]
            if data['series_book'][:5] == 'Book ':
                data['series_book'] = float(data['series_book'][5:])

        if data['series_link'] is not None:
            data['series_link'] = data['series_link'].rsplit('=', 1)[-1]

        return data
