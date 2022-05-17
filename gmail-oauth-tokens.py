#!/usr/bin/env python

#
# Copyright 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
     # http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

#
# Derived from oauth2.py (https://github.com/google/gmail-oauth2-tools).
# Heavily modified and rewritten by Stefan Krah.
#
# Works for Microsoft Office 365 in addition to Gmail.


import os
import sys
import json
import argparse
import time
try:
    import urllib.request as urllibrequest
    import urllib.parse as urllibparse
    from http.server import HTTPServer, BaseHTTPRequestHandler
    urlparse = urllibparse
    def codebytes(b): return b.encode("utf8")
except: #py2
    import urlparse
    import urllib as urllibparse
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    urllibrequest = urllibparse
    def codebytes(b): return b

# Local webserver nonsense required to receive code from redirect
class OAuthRedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = urlparse.urlparse(self.path)
        query_string = urlparse.parse_qs(response.query)
        code = query_string["code"][0]
        self.server.oauth_code = code
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><head></head><body><h2>Your json file is updated.</h2></body></html>")

class OAuthRedirectServer(HTTPServer):
    def __init__(self, port):
        self.oauth_code = None
        HTTPServer.__init__(self, ("localhost", int(port)), OAuthRedirectHandler)
        self.timeout = None

class OAuth2(object):

    def __init__(self, token_data_path):
        self.token_data_path = token_data_path

        with open(self.token_data_path) as f:
            self.data = json.load(f)

    def copy(self, *keys):
        data = {}
        for k in keys:
            data[k] = self.data[k]
        return data

    def query(self, params):
        lst = []
        for param in sorted(params.items(), key=lambda x: x[0]):
            escaped = urllibparse.quote(param[1], safe='~-._')
            lst.append('%s=%s' % (param[0], escaped))
        return '&'.join(lst)

    def code_url(self, port):
        params = self.copy('scope', 'client_id')
        params['redirect_uri'] = 'http://localhost:' + str(port) + '/'
        params['response_type'] = 'code'
        params['access_type'] = 'offline'
        params['prompt'] = 'consent'
        return '%s?%s' % (self.data['auth_uri'], self.query(params))

    def get_response(self, url, params):
        encoded = urllibparse.urlencode(params).encode('ascii')
        response = urllibrequest.urlopen(url, encoded).read()
        return json.loads(response)

    def update_config(self, d):
        self.data['access_token'] = d['access_token']
        self.data['expires_at'] = time.time() + d['expires_in'] - 100

        refresh_token = d.get('refresh_token')
        if refresh_token is not None:
            self.data['refresh_token'] = refresh_token

        with open(self.token_data_path, "w") as f:
            json.dump(self.data, f)

    def init_tokens(self, code, port):
        params = self.copy('user', 'client_id', 'client_secret')
        params['redirect_uri'] = 'http://localhost:' + str(port) + '/'
        params['code'] = code
        params['grant_type'] = 'authorization_code'

        d = self.get_response(self.data['token_uri'], params)
        self.update_config(d)

    def refresh_tokens(self):
        params = self.copy('client_id', 'client_secret', 'refresh_token')
        params['grant_type'] = 'refresh_token'

        d = self.get_response(self.data['token_uri'], params)
        self.update_config(d)

    def token(self):
        if time.time() >= self.data.get('expires_at'):
            self.refresh_tokens()

        return self.data['access_token']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--init", action="store_true", default=False,
                        help="initialize access and refresh tokens")
    parser.add_argument('tokenfile', metavar='<token data file path>',
                        help="location of the token data file")
    parser.add_argument("-p", "--port", default="8083",
                        help="local port to use for receiving oauth2 redirect")

    args = parser.parse_args()
    auth = OAuth2(args.tokenfile)

    if args.init:
        print("Visit this url to obtain a verification code:")
        print("    %s\n" % auth.code_url(args.port))
        oauthd = OAuthRedirectServer(args.port)
        try:
            oauthd.handle_request()
            auth.init_tokens(oauthd.oauth_code,args.port)
        finally:
            oauthd.server_close()
        print("\naccess token\n")

    print("%s" % auth.token())

    sys.exit(0)
