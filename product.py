from pprint import pprint

import urllib.parse, urllib.request
from lxml import html

class ProductHelper:
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
        book_paths = et.xpath("//li[contains(concat(' ',normalize-space(@class),' '),' productListItem ')]//a[contains(concat(' ',normalize-space(@class),' '),' bc-link ')][starts-with(@href,'/pd/')][img]/@href")
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
            'title':        {                          'xpath': "//h1[@itemprop='name']/text()",                   },
            'author':       { 'text': 'Written by:',                                                               },
            'narrator':     { 'text': 'Narrated by:',                                                              },
            'publisher':    { 'text': 'Publisher:',    'xpath': "//li[span[contains(text(),$text)]]/span/a/text()" },
            'release_date': { 'text': 'Release Date:',                                                             },
            'series':       { 'text': 'Series:',       'xpath': "//li/span[contains(text(),$text)]/a/text()"       },
            'series_book':  { 'text': 'Series:',       'xpath': "//li/span[contains(text(),$text)]/span/text()"    },
            'series_link':  { 'text': 'Series:',       'xpath': "//li/span[contains(text(),$text)]/a/@href"        },
        }
        for key, info in datapoints.items():
            if 'xpath' not in info or info['xpath'] is None:
                info['xpath'] = "//li[span[contains(text(),$text)]]/span/a/span/text()"
            if 'text' not in info:
                info['text'] = None

            x = et.xpath(info['xpath'], text = info['text'])
            if len(x) != 1:
                data[key] = None
                continue

            data[key] = x[0]

        if data['series_book'] is not None:
            if data['series_book'][:2] == ', ':
                data['series_book'] = data['series_book'][2:]
            if data['series_book'][:5] == 'Book ':
                data['series_book'] = float(data['series_book'][5:])

        if data['series_link'] is not None:
            data['series_link'] = data['series_link'].rsplit('=', 1)[-1]

        return data
