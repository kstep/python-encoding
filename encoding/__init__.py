from __future__ import with_statement

import httplib, urllib, requests, requests_toolbelt as toolbelt
from adict import adict

try:
    from lxml import etree
    def format_query(**data):
        def _build_tree(node, data):

            for k, v in data.items():
                if isinstance(v, list):
                    for item in v:
                        element = etree.Element(k)
                        if isinstance(item, dict):
                            element = _build_tree(element, item)
                        else:
                            element.text = item

                        node.append(element)

                else:
                    element = etree.Element(k)
                    if isinstance(item, dict):
                        element = _build_tree(element, item)
                    else:
                        element.text = item

                    node.append(element)

            return node

        data['notify_format'] = 'xml'
        return {'xml': _build_tree(etree.Element('query'), data)}

    def parse_results(text):
        result = etree.fromstring(text)
        return result

except:
    from simplejson import dumps as tojson, loads as fromjson
    def format_query(**data):
        data['notify_format'] = 'json'
        print data
        return {'json': tojson({'query': data})}

    def parse_results(text):
        result = fromjson(text, object_hook=adict)
        if 'errors' in result.response:
            raise RuntimeError(result.response.errors)

def decode_encoding_json(text):
    from simplejson import JSONDecodeError
    try:
        return fromjson(text, object_hook=adict)

    except JSONDecodeError:
        text = text.strip()

        if text.startswith('new Object('):
            text = text[11:]
        if text.endswith(')'):
            text = text[:-1]
        text = text.replace("'", '"')

        return fromjson(text, object_hook=adict)


ENCODING_API_URL = 'manage.encoding.com:80'

class Encoding(object):

    def __init__(self, userid, userkey, url=ENCODING_API_URL):
        self.url = url
        self.userid = userid
        self.userkey = userkey

    def get_media_info(self, ids=[]):

        query = format_query(userid=self.userid,
                userkey=self.userkey,
                action='GetMediaInfo',
                mediaid=','.join(ids))

        results = self._execute_request(query, {'Content-Type': 'application/x-www-form-urlencoded'})

        return parse_results(results)

    def get_status(self, ids=[], extended=False):
        query = format_query(
                    userid=self.userid,
                    userkey=self.userkey,
                    action='GetStatus',
                    extended='yes' if extended else 'no',
                    mediaid=','.join(ids))

        results = self._execute_request(query, {'Content-Type': 'application/x-www-form-urlencoded'})

        return parse_results(results)

    def add_media(self, source=[], formats=[], notify='', instant=False):

        query = format_query(
                    userid=self.userid,
                    userkey=self.userkey,
                    action='AddMedia',
                    source=source,
                    notify=notify,
                    instant='yes' if instant else 'no',
                    format=formats)

        results = self._execute_request(query, {'Content-Type': 'application/x-www-form-urlencoded'})

        return parse_results(results)


    def _execute_request(self, query, headers, path='', method='POST'):

        params = urllib.urlencode(query)

        conn = httplib.HTTPConnection(self.url)
        conn.request(method, path, params, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()

        return data

    def _parse_results(self, results):
        return etree.fromstring(results)
