from __future__ import with_statement

import requests, requests_toolbelt as toolbelt
from adict import adict

def bool_to_yesno(data):
    '''
    Convert boolean values to 'yes' and 'no' strings
    for compliance with Encoding.com API
    '''
    if data is True:
        return 'yes'
    elif data is False:
        return 'no'
    elif isinstance(data, dict):
        for k, v in data.iteritems():
            data[k] = bool_to_yesno(v)
        return data
    elif isinstance(data, list):
        for i, v in enumerate(data):
            data[i] = bool_to_yesno(v)
        return data
    else:
        return data

try:
    from lxml import etree
    def format_query(**data):
        def _build_tree(name, data, parent=None):

            if isinstance(data, dict):
                node = etree.Element(name)
                for k, v in data.iteritems():
                    element = _build_tree(k, v, node)
                    node.append(element)

            elif isinstance(data, list):
                node = parent or etree.Element('query')
                for v in data:
                    element = _build_tree(name, v, node)
                    node.append(element)

            else:
                node = etree.Element(name)
                node.text = data
                return node

            return node

        data['notify_format'] = 'xml'
        return {'xml': _build_tree('query', bool_to_yesno(data))}

    def parse_results(text):
        result = etree.fromstring(text)

        if hasattr(result.response, 'errors'):
            raise RuntimeError(result.response.errors)

        return result.response

except:
    from simplejson import dumps as tojson, loads as fromjson
    def format_query(**data):
        data['notify_format'] = 'json'
        return {'json': tojson({'query': bool_to_yesno(data)})}

    def parse_results(text):
        result = fromjson(text, object_hook=adict)

        if 'errors' in result.response:
            raise RuntimeError(result.response.errors)

        return result.response

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



class UploadedFile(object):
    def __init__(self, sid, upload_url=None):
        self.sid = sid
        self.upload_url = upload_url or UPLOAD_URL

    @property
    def progress(self):
        return decode_encoding_json(requests.get(self.upload_url + '/progress', params={'X-Progress-ID': self.sid}).text)

    @property
    def fileinfo(self):
        return decode_encoding_json(requests.get(self.upload_url + '/fileinfo.php', params={'sid': self.sid}).text)

    @property
    def s3info(self):
        return decode_encoding_json(requests.get(self.upload_url + '/s3info.php', params={'sid': self.sid}).text)

    def __str__(self):
        return '<UploadedFile %s>' % self.sid

    def wait(self):
        from time import sleep

        #print 'Step 1'
        #while True:
            #progress = self.progress
            #print progress
            #if progress['state'] == 'done':
                #break
            #sleep(5)

        #print 'Step 2'
        while True:
            progress = self.s3info
            #print progress
            if progress['state'] == 'error':
                raise RuntimeError('error uploading file to encoding.com (%r)' % progress)

            if progress['state'] == 'done':
                break

            sleep(2)

        return self.fileinfo

from hashlib import md5, sha256
from time import strftime, gmtime, time

ENCODING_API_URL = 'https://manage.encoding.com'
UPLOAD_URL = 'https://upload.encoding.com'

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

        results = self._execute_request(query)

        return parse_results(results)

    def get_status(self, ids=[], extended=False):
        query = format_query(
                    userid=self.userid,
                    userkey=self.userkey,
                    action='GetStatus',
                    extended='yes' if extended else 'no',
                    mediaid=','.join(ids))

        results = self._execute_request(query)

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

        results = self._execute_request(query)

        return parse_results(results)


    def _execute_request(self, query, path='', method='post'):
        response = requests.request(method, self.url + path, data=query)
        return response.text

    def upload_media(self, filename, upload_url=None):
        upload_url = upload_url or UPLOAD_URL

        params = self._signature(filename)
        data = toolbelt.MultipartEncoder(params)

        response = requests.post(upload_url + '/upload',
                data=data,
                headers={'Content-Type': data.content_type})

        #return parse_results(response.text)
        assert response.status_code == 200

        return UploadedFile(params['sid'], upload_url)

    def _signature(self, filename):

        userfile = (filename, open(filename, 'rb'), 'application/octet-stream')
        timestamp = strftime('%Y-%m-%d %H:%M:%S %z', gmtime())
        sid = md5(str(self.userid) + str(time())).hexdigest()
        signature = sha256(
            timestamp +
            sid +
            self.userkey
            ).hexdigest()
        uid = str(self.userid)

        return dict(
                uid=uid,
                sid=sid,
                userfile=userfile,
                timestamp=timestamp,
                signature=signature
                )

