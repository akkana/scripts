#!/usr/bin/env python

# A module for downloading a queue of URLs asynchronously to local files.

# TODO:
# - Catch and save errors
# - UrlDownloadQueue: keep track of what's new, in progress,
#   successfully downloaded, and errored, and have queries for them.
# - UrlDownloadQueue: handle different servers differently,
#   not overloading any one server with two many downloads,
#   looking for a new server if one is already being hit but
#   we have a new thread pool available.

import sys
import urllib2
from cookielib import CookieJar
import StringIO
import gzip
import datetime

# Use processes:
# from multiprocessing import Pool as ThreadPool
# Use threads:
from multiprocessing.dummy import Pool as ThreadPool

class UrlDownloader:
    '''Manage downloading of a single URL (threadable).
       Keep track of download success or failure.
    '''
    # Status codes for self.status:
    SUCCESS = 0
    ERROR = -1
    EMPTY = 1
    DOWNLOADING = 2

    def __init__(self, url, localpath, timeout=100,
                 user_agent=None, referrer=None, allow_cookies=False):
        '''Arguments:
            url: the original url to be downloaded
            localpath: where to save it
            timeout=100, referrer=None, user_agent=None, allow_cookies=False
        '''
        self.orig_url = url
        self.localpath = localpath
        self.timeout = timeout
        self.user_agent = user_agent
        self.allow_cookies = allow_cookies
        self.referrer = referrer

        # Things we will set during the download
        self.status = UrlDownloader.EMPTY
        self.errmsg = None
        self.cururl = None
        self.bytes_downloaded = 0
        self.done = False
        # self.socket = None
        self.is_gzip = False
        self.response = None

        # things we might want to query later:
        self.final_url = None
        self.host = None
        self.prefix = None
        self.encoding = None

    def __repr__(self):
        s = "UrlDownloader(%s -> %s)" % (self.orig_url, self.localpath)
        # if self.cururl:
        #     s += "\n  Current URL: %s" % self.cururl
        # if self.final_url and self.final_url != self.cururl:
        #     s += "\n  Final URL: %s" % self.final_url
        # s += "\n  Timeout: %d" % self.timeout
        # if self.user_agent:
        #     s += "\n  User agent: %d" % self.user_agent
        # if self.referrer:
        #     s += "\n  Timeout: %d" % self.timeout
        # if self.allow_cookies:
        #     s += "\n  Cookies allowed"
        # else:
        #     s += "\n  No cookies"

        return s

    def resolve(self):
        '''Resolve the URL, follow any redirects, but don't
           actually download the content.
        '''
        request = urllib2.Request(self.orig_url)

        # If we're after the single-page URL, we may need a referrer
        if self.referrer:
            request.add_header('Referer', self.referrer)

        if self.user_agent:
            request.add_header('User-Agent', self.user_agent)

        # A few sites, like http://nymag.com, gzip their http.
        # Python doesn't handle that automatically: we have to ask for it.
        request.add_header('Accept-encoding', 'gzip')

        if self.allow_cookies:
            # Allow for cookies in the request: some sites, notably nytimes.com,
            # degrade to an infinite redirect loop if cookies aren't enabled.
            cj = CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        else:
            opener = urllib2.build_opener()

        self.response = opener.open(request, timeout=self.timeout)
        # Lots of ways this can fail.
        # e.g. ValueError, "unknown url type"
        # or BadStatusLine: ''

        # At this point it would be lovely to check whether the
        # mime type is HTML. Unfortunately, all we have is a
        # httplib.HTTPMessage instance which is completely
        # undocumented (see http://bugs.python.org/issue3428).

        # It's not documented, but sometimes after urlopen
        # we can actually get a content type. If it's not
        # text/something, that's bad.
        # ctype = self.response.headers['content-type']
        # if ctype and ctype != '' and ctype[0:4] != 'text':
        #     print >>sys.stderr, url, "isn't text -- skipping"
        #     self.response.close()
        #     raise ContentsNotTextError

        # Were we redirected? geturl() will tell us that.
        self.cururl = self.response.geturl()

        # but sadly, that means we need another request object
        # to parse out the host and prefix:
        real_request = urllib2.Request(self.cururl)
        real_request.add_header('User-Agent', self.user_agent)

        self.host = real_request.get_host()
        self.prefix = real_request.get_type() + '://' + self.host + '/'

        # urllib2 unfortunately doesn't read unicode,
        # so try to figure out the current encoding:
        self.encoding = self.response.headers.getparam('charset')
        enctype = self.response.headers['content-type'].split('charset=')
        if len(enctype) > 1:
            self.encoding = enctype[-1]
        else:
            self.encoding = 'utf-8'

        self.final_url = self.response.geturl()
        if self.final_url != self.cururl:
            print >>sys.stderr, "cururl != final_url!"
            print >>sys.stderr, self.cururl, "!=", self.final_url

        # Is the URL gzipped? If so, we'll need to uncompress it.
        self.is_gzip = self.response.info().get('Content-Encoding') == 'gzip'

    def download(self):
        '''Read the content of the link, already resolve()d.
        '''
        # This can die with socket.error, "connection reset by peer"
        # And it may not set html, so initialize it first:
        html = None
        try:
            html = self.response.read()
        # XXX Need to guard against IncompleteRead -- but what class owns it??
        #except httplib.IncompleteRead, e:
        #    print >>sys.stderr, "Ignoring IncompleteRead on", url
        except Exception, e:
            print >>sys.stderr, "Unknown error from self.response.read()", url

        # html can be undefined here. If so, no point in doing anything else.
        if not html:
            print >>sys.stderr, "Didn't read anything from self.response.read()"
            raise NoContentError

        if self.is_gzip:
            buf = StringIO.StringIO(html)
            f = gzip.GzipFile(fileobj=buf)
            html = f.read()

        #print >>sys.stderr, "self.response.read() returned type", type(html)
        # Want to end up with unicode. In case it's str, decode it:
        if type(html) is str:
            # But sometimes this raises errors anyway, even using
            # the page's own encoding, so use 'replace':
            html = html.decode(self.encoding, 'replace')

        # No docs say I should close this. I can only assume.
        self.response.close()

        self.bytes_downloaded = len(html)
        self.save_file(html)
        # print "Downloaded", self.bytes_downloaded, "to", self.localpath

    def save_file(self, bytes, encoding="utf-8"):
        '''Save the bytes we just downloaded to the local file path.
        '''
        fp = open(self.localpath, 'w')
        if isinstance(bytes, unicode):
            fp.write(bytes.encode(encoding))
        else:
            fp.write(bytes)
        fp.close()

    def resolve_and_download(self):
        '''Resolve the URL, following any redirects,
           then actually download the URL to the local file.
           Return self, which includes details like status code and errstring.
        '''
        # We must catch all errors here, otherwise they'll go ignored
        # since we're running inside a thread pool and the main
        # thread won't catch our exceptions.
        if self.status != UrlDownloader.EMPTY:
            self.errmsg = "Eek: tried to download when status was %d" \
                          % self.status
            self.status = UrlDownloader.ERROR
            return self

        self.status = UrlDownloader.DOWNLOADING
        try:
            self.resolve()
            self.download()
            self.status = UrlDownloader.SUCCESS
        except Exception, e:
            self.status = UrlDownloader.ERROR
            self.errmsg = str(e)

        return self

class UrlDownloadQueue:
    '''Maintains a queue of UrlDownloaders and keeps them downloading
    (eventually asynchronously).

    Call download_queue.add(url, localfile=localfile)
      or download_queue.add(UrlDownloader)
    to add another url to be downloaded.
    Optional arguments:
      callback       to be notified when the download is ready
      timeout        in milliseconds
      referrer
      user_agent
      allow_cookies  default False
    '''
    def __init__(self, maxthreads=4):
        self.queue = []     # implemented as a list
        self.succeeded = []
        self.in_progress = []
        self.failed = []
        self.pool = None
        self.maxthreads = maxthreads

    def __len__(self) :
        return len(self.queue)

    def __repr__(self):
        return '\n'.join(map(str, self.queue))

    def pop(this):
        return self.queue.pop()

    def add(self, url, **kwargs):
        '''Add a new URL to the queue to be downloaded.
        '''
        kwargs['url'] = url
        if 'localpath' not in kwargs:
            raise ValueError("UrlDownloadQueue.add needs localpath")

        if not isinstance(url, UrlDownloader):
            url = UrlDownloader(**kwargs)
        self.queue.insert(0, url)

    def download(self, maxthreads=4):
        '''Start or continue downloading.
        If maxthreads==0, stay in the current thread and process
        anything available, then return.
        If maxthreads>0, use a separate thread for every download,
        but no more than maxthreads at any given time.
        '''
        # XXX If maxthreads==1, would like to start a subthread
        # (if we don't already have one)
        # and process everything in that thread.

        if not self.pool:
            # Make the Pool of workers, maxthreads possible processes
            self.pool = ThreadPool(self.maxthreads)

        while len(self.queue):
            urldl = self.queue[-1]
            res = self.pool.apply_async(UrlDownloader.resolve_and_download,
                                        (urldl,),
                                        callback=self.cb)
            self.in_progress.append(urldl)
            #self.queue.pop()
            self.queue.remove(urldl)

        # close the pool and wait for the work to finish 
        self.pool.close()

    def cb(self, res):
        '''Callback that will be called for each UrlDownloader
           when it's finished downloading (or has errored out).
           res is a UrlDownloader object.
        '''
        if res.status == UrlDownloader.SUCCESS:
            # print "::::: Callback success! Downloaded %d bytes" % res.bytes_downloaded
            self.succeeded.append(res)
        elif res.status == UrlDownloader.ERROR:
            # print "::::: Callback ERROR!", res.errmsg
            self.failed.append(res)
        else:
            # print "::::: Callback: status was", res.status
            self.failed.append(res)
        self.in_progress.remove(res)

    def print_status(self):
        '''Print a summary of what we did and didn't download successfully.
        '''
        print "\n===== Succeeded:"
        for u in self.succeeded:
            print u

        print "\n===== Failed:"
        for u in self.failed:
            print "%s:\n    %s" % (str(u), u.errmsg)

        if len(self.in_progress):
            print "\n===== Still in progress:"
            for u in self.in_progress:
                print u

    def processing(self):
        '''Do we still have URLs in our queues that haven't been processed?
        '''
        return (len(self.queue) + len(self.in_progress) > 0)

if __name__ == "__main__":
    import os
    import urlparse
    import posixpath
    import time

    dlqueue = UrlDownloadQueue()

    for url in sys.argv[1:]:
        parsed = urlparse.urlparse(url)
        # self.scheme = parsed.scheme
        host = parsed.netloc
        rooturlpath = posixpath.normpath(parsed.path)
        filename = os.path.basename(rooturlpath)
        if not filename or filename == ".":
            filename = "INDEX"
        localpath = os.path.join("/tmp/urls", "%s-%s" % (host, filename))

        dlqueue.add(url=url, localpath=localpath,
                    timeout=5000, allow_cookies=True)
    
    # print "\nQueue now (len %d):" % len(dlqueue)
    # print dlqueue
    # print "================="

    dlqueue.download(4)

    # Now things are downloading asynchronously.
    # Loop until they're all done.
    while dlqueue.processing():
        print "processing ..."
        time.sleep(.1)

    dlqueue.print_status()

