#!/usr/bin/env python3

# Built out from https://www.scrapingbee.com/blog/crawling-python/

import logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup


logging.basicConfig(
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)


class Crawler:

    def __init__(self, urls=[]):
        self.urls_to_visit = urls
        self.visited_urls = []
        self.nonhtml_urls = []
        self.bad_urls = []
        self.external_urls = []

        self.base_url = "http://localhost/"
        self.internal_equiv = [
                                "http://shallowsky.com",
                                "https://shallowsky.com",
                                "http://www.shallowsky.com",
                                "https://www.shallowsky.com",
                              ]

    def get_linked_urls(self, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all('a'):
            path = link.get('href')
            if path and path.startswith('/'):
                path = urljoin(url, path)
            yield path

        # XXX Do the same for img URLs, but don't recurse on them

    def is_internal(self, url):
        if ':' not in url:
            return True
        if url.startswith(self.base_url):
            return True
        # for equiv in self.internal_equiv:
        #     if url.startswith(equiv):
        #         return True
        return False

    def map_equiv(self, url):
        # If url starts with any of the equivalent domains,
        # replace them with the base url.
        for equiv in self.internal_equiv:
            if url.startswith(equiv):
                return self.base_url + url[len(equiv):]
        return url

    def add_url_to_visit(self, url):
        if not self.is_internal(url):
            if url not in self.external_urls:
                self.external_urls.append(url)
            return

        # Strip off any named anchors
        try:
            url = url[:url.index('#')]
        except ValueError:
            pass

        if url not in self.visited_urls and url not in self.urls_to_visit \
           and url not in self.nonhtml_urls and url not in self.bad_urls:
            # and url not in self.external_urls:
            # print("Will visit", url)
            self.urls_to_visit.append(url)

    def crawl(self, url):
        # Check MIME type; don't try to parse non-HTML files
        head = requests.head(url)
        if 'Content-Type' not in head.headers:
            print(url, ": No Content-Type! headers:", head.headers)
            self.nonhtml_urls.append(url)
            return
        if not head.headers['Content-Type'].startswith("text/html"):
            self.nonhtml_urls.append(url)
            return
        html = requests.get(url).text

        for suburl in self.get_linked_urls(url, html):
            # print("linked url:", suburl)
            # Make it absolute
            suburl = urljoin(url, suburl)
            # print("absolute:", suburl)
            suburl = self.map_equiv(suburl)
            # print("mapped:", suburl)
            self.add_url_to_visit(suburl)

    def check_external_link(self, url):
        """Check headers for an external link.
           Return True if it's good, else False.
        """
        logging.info(f'Checking external link: {url}')
        try:
            head = requests.head(url, timeout=10, allow_redirects=True)
        except:
            return False
        return (head.status_code == 200)

    def check_all_externals(self):
        self.bad_externals = []
        for url in self.external_urls:
            if not self.check_external_link(url):
                self.bad_externals.append(url)

    def run(self):
        while self.urls_to_visit:
            url = self.urls_to_visit.pop(0)
            # logging.info(f'Crawling: {url}')
            try:
                self.crawl(url)
            except Exception:
                self.bad_urls.append(url)
                logging.exception(f'Failed to crawl: {url}')
            finally:
                self.visited_urls.append(url)


if __name__ == '__main__':
    crawler = Crawler(urls=['http://localhost/'])
    try:
        crawler.run()

        # Check external links
        crawler.check_all_externals()

    except KeyboardInterrupt:
        print("Interrupt")

    with open("/tmp/urls-bad.txt", "w") as fp:
        for url in crawler.bad_urls:
            print(url, file=fp)

    with open("/tmp/urls-internal.txt", "w") as fp:
        for url in crawler.visited_urls:
            print(url, file=fp)

        print("\nNON-HTML FILES:\n", file=fp)

        for url in crawler.nonhtml_urls:
            print(url, file=fp)

    with open("/tmp/urls-external-good.txt", "w") as goodfp:
        with open("/tmp/urls-external-bad.txt", "w") as badfp:
            for url in crawler.external_urls:
                if url in crawler.bad_externals:
                    print(url, file=badfp)
                else:
                    print(url, file=goodfp)


