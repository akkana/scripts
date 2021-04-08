#!/usr/bin/env python3

# Chrome cookie code from https://stackoverflow.com/a/56936539

import sqlite3
import sys
from os import getenv, path
import os
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
import keyring
import shutil
import tempfile
import json


def get_firefox_cookies(cookiesfile, url=None):
    # https://docs.python.org/3/library/sqlite3.html#sqlite3.connect
    # says this opens the database read-only, but it doesn't:
    # the command still bombs out with
    # sqlite3.OperationalError: database is locked
    # db_uri = "file://%s?mode=ro" % cookiesfile
    # conn = sqlite3.connect(db_uri, uri=True, timeout=3)

    # So instead, how about just copying the file?
    dbfile = tempfile.NamedTemporaryFile()
    dbfile.close()
    shutil.copyfile(cookiesfile, dbfile.name)

    conn = sqlite3.connect(dbfile.name, timeout=3)
    cur = conn.cursor()
    sqlquery = "SELECT host, name, value FROM moz_cookies"
    # Other rows you can get: path, isSecure, expiry.
    if url:
        sqlquery += " WHERE host LIKE '%%%s%%'" % url
    print(sqlquery)
    cur.execute(sqlquery)

    cookies = []
    for host, name, value in cur.fetchall():
        cookies.append({ 'host': host, 'name': name, 'value': value })

        # Example of how you'd use this with cookielib:
        # c = cookielib.Cookie(0, item[4], item[5],
        #     None, False,
        #     item[0], item[0].startswith('.'), item[0].startswith('.'),
        #     item[1], False,
        #     item[2],
        #     item[3], item[3]=="",
        #     None, None, {})
        # final_cookie.set_cookie(c)

    conn.close()
    return cookies


def get_chrome_cookies(cookiesfile, url=None):

    def chrome_decrypt(encrypted_value, key=None):
        dec = AES.new(key, AES.MODE_CBC, IV=iv).decrypt(encrypted_value[3:])
        decrypted = dec[:-dec[-1]].decode('utf8')
        return decrypted

    sqlquery = 'SELECT host_key, name, value, encrypted_value FROM cookies'
    if url:
        # sqlquery += ' WHERE host_key == "%s"' % url
        sqlquery += " WHERE host_key LIKE '%%%s%%'" % url
    print(sqlquery)

    conn = sqlite3.connect(cookiesfile)
    cursor = conn.cursor()
    cursor.execute(sqlquery)

    cookies = []

    if sys.platform == 'win32':
        import win32crypt

        for host_key, name, value, encrypted_value in cursor.fetchall():
            print("Stuff:", stuff)
            if value or (encrypted_value[:3] == b'v10'):
                cookies.append({ 'host': host_key,
                                 'name': name,
                                 'value': value })
            else:
                decrypted_value = win32crypt.CryptUnprotectData(
                    encrypted_value, None, None, None, 0)[1].decode('utf-8') \
                    or 'ERROR'
                cookies.append({ 'host': host_key,
                                 'name': name,
                                 'value': decrypted_value })

    elif sys.platform == 'linux':
        my_pass = 'peanuts'.encode('utf8')
        iterations = 1
        key = PBKDF2(my_pass, salt, length, iterations)
        for host_key, name, value, encrypted_value in cursor.fetchall():
            decrypted_tuple = (host_key, name,
                               chrome_decrypt(encrypted_value, key=key))
            cookies.append({ 'host': decrypted_tuple[0],
                             'name': decrypted_tuple[1],
                             'value': decrypted_tuple[2] })

    else:
        print("Sorry, don't know how to decrypt except on linux and win32")

    conn.close()
    return cookies


if __name__ == '__main__':
    salt = b'saltysalt'
    iv = b' ' * 16
    length = 16

    if len(sys.argv) <= 1:
        print("Usage: %s cookiefile [host]" % os.path.basename(sys.argv[0]))
        print("host can be a partial pattern, e.g. nytimes.")
        print("")
        print("Some cookiefiles found on this system:")

        print("\nChrome/Chromium:")
        os.system("/usr/bin/locate */Default/Cookies")

        print("\nFirefox:")
        # Adding the */ in the locate command prevents locate from
        # automatically doing *PAT* and so matching cookies.sqlite-wal.
        os.system("/usr/bin/locate */cookies.sqlite")

        sys.exit(0)

    cookiefile = os.path.expanduser(sys.argv[1])
    if len(sys.argv) > 2:
        url = sys.argv[2]
    else:
        url = None

    if cookiefile.endswith(".sqlite"):
        print("Chrome cookies in", cookiefile)
        cookies = get_firefox_cookies(cookiefile, url)
    else:
        print("Firefox cookies in", cookiefile)
        cookies = get_chrome_cookies(cookiefile, url)

    # Print cookies in JSON format, prettyprinted
    print(json.dumps(cookies, indent=4, sort_keys=True))


