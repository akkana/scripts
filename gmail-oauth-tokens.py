#!/usr/bin/python3

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
from pprint import pprint
try:    # python 3
    import urllib.request as urllibrequest
    import urllib.parse as urllibparse
    from urllib.error import HTTPError
    raw_input = input
except: # python 2
    import urllib as urllibparse
    urllibrequest = urllibparse
    from urllib2 import HTTPError

DEBUG = False


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

    def code_url(self):
        params = self.copy('scope', 'client_id', 'redirect_uri')
        params['response_type'] = 'code'
        return '%s?%s' % (self.data['auth_uri'], self.query(params))

    def get_response(self, url, params):
        encoded = urllibparse.urlencode(params).encode('ascii')
        try:
            response = urllibrequest.urlopen(url, encoded).read()
            return json.loads(response)
        except HTTPError:
            print("The tokens have expired and Google gave an "
                  "Error 400: Bad Request", file=sys.stderr)
            # self.authenticate()
            exit(1)

    def update_config(self, d):
        self.data['access_token'] = d['access_token']
        self.data['expires_at'] = time.time() + d['expires_in'] - 100
        if DEBUG:
            print("New expiration:", time.localtime(self.data['expires_at']),
                  file=sys.stderr)

        refresh_token = d.get('refresh_token')
        if refresh_token is not None:
            self.data['refresh_token'] = refresh_token
        elif DEBUG:
            print("No refresh token", file=sys.stderr)

        with open(self.token_data_path, "w") as f:
            json.dump(self.data, f)

    def init_tokens(self, code):
        params = self.copy('user', 'client_id', 'client_secret',
                           'redirect_uri')
        params['code'] = code
        params['grant_type'] = 'authorization_code'

        d = self.get_response(self.data['token_uri'], params)
        self.update_config(d)

    def refresh_tokens(self):
        if DEBUG:
            print("Refreshing token", file=sys.stderr)
        params = self.copy('client_id', 'client_secret', 'refresh_token')
        params['grant_type'] = 'refresh_token'

        d = self.get_response(self.data['token_uri'], params)
        if DEBUG:
            print("Refresh response:", file=sys.stderr)
            pprint(d, stream=sys.stderr)
        self.update_config(d)

    def token(self):
        if DEBUG:
            print("JSON data:", file=sys.stderr)
            pprint(self.data, stream=sys.stderr)
        expired = self.data.get('expires_at')
        if time.time() >= float(expired):
            if DEBUG:
                print("Need to refresh tokens: expired at",
                      time.strftime('%Y-%m-%d %H:%M', time.gmtime(expired)),
                      file=sys.stderr)
            self.refresh_tokens()

        return self.data['access_token']

    def authenticate(self):
        """Called from --init, or (maybe) if refresh_tokens fails with a 400"""
        print("Visit this url to obtain a verification code:",
              file=sys.stderr)
        print("    %s\n" % auth.code_url(), file=sys.stderr)

        # Write the prompt to stderr so it won't interfere with
        # the eventual code printed. raw_input only knows how
        # to prompt to stdout.
        sys.stderr.write("Enter verification code: ")
        try:
            code = raw_input()
            response = auth.init_tokens(code)
        except EOFError:
            print("Looks like you need to authenticate again.")
            print("Try running", self.token_data_path,
                  "in a terminal")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--init", action="store_true", default=False,
                        help="initialize access and refresh tokens")
    parser.add_argument("-d", "--debug", action="store_true", default=False,
                        help="print debugging output, for testing")
    parser.add_argument('tokenfile', metavar='<token data file path>',
                        help="location of the token data file")

    args = parser.parse_args()
    if args.debug:
        DEBUG = True

    auth = OAuth2(args.tokenfile)

    if args.init:
        auth.authenticate()
    else:
        sys.stdout.write("%s" % auth.token())

    sys.exit(0)
