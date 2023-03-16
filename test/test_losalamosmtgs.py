#!/usr/bin/env python3

import unittest

from bs4 import BeautifulSoup

import losalamosmtgs

from datetime import datetime

class TestLosAlamosMtgs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def compare_generated_html(self, filebase, convtype, meetingdate):
        html = losalamosmtgs.html_agenda_fitz(f"test/files/{filebase}.pdf",
                                              meetingdate)

        # Save to a temp file: use this when adding new test files.
        # with open("/tmp/html.html", "w") as fp:
        #     fp.write(html)
        #     print("Wrote /tmp/html.html")

        with open(f"test/files/{filebase}-{convtype}.html") as fp:
            compare_html = fp.read()
        self.assertEqual(html, compare_html)

    def test_pdftohtml_fitz(self):
        try:
            import fitz
        except ModuleNotFoundError:
            print("Fitz (mupdf) not installed, so not testing it")
            return

        self.compare_generated_html("2023-02-07-CountyCouncil", "fitz",
                                    datetime(2023, 2, 7, 6, 0))
        self.compare_generated_html("2023-02-28-CountyCouncil", "fitz",
                                    datetime(2023, 2, 28, 6, 0))
        self.compare_generated_html("2023-03-15-DPU", "fitz",
                                    datetime(2023, 3, 15, 5, 30))
        self.compare_generated_html("2022-03-17-EnvironmentalSustainabilityBoard",
                                     "fitz", datetime(2023, 3, 17, 5, 30))

    def test_merge_tags(self):
        self.maxDiff = None

        soup = BeautifulSoup('''<p style="position:absolute;top:783px;left:82px;white-space:nowrap" class="ft15"><b>6.</b></p>
<p style="position:absolute;top:783px;left:144px;white-space:nowrap" class="ft15"><b>PUBLIC COMMENT FOR ITEMS ON CONSENT AGENDA</b></p>
<p style="position:absolute;top:829px;left:82px;white-space:nowrap" class="ft15"><b>7.</b></p>
<p style="position:absolute;top:829px;left:144px;white-space:nowrap" class="ft15"><b>CONSENT AGENDA</b></p>
<p style="position:absolute;top:861px;left:252px;white-space:nowrap" class="ft113"><i>The following items are presented.</i></p>
<p class="ft113">Lorem Ipsum, so there.</p>
''', 'lxml')
        for tag in soup.find_all('p'):
            del tag["style"]

        losalamosmtgs.join_consecutive_tags(soup, 'p')
        self.assertEqual(str(soup), '''<html><body><p class="ft15"><b>6.</b><b>PUBLIC COMMENT FOR ITEMS ON CONSENT AGENDA</b></p>

<p class="ft15"><b>7.</b><b>CONSENT AGENDA</b></p>

<p class="ft113"><i>The following items are presented.</i>Lorem Ipsum, so there.</p>

</body></html>''')

        losalamosmtgs.join_consecutive_tags(soup, 'i')
        self.assertEqual(str(soup), '''<html><body><p class="ft15"><b>6.</b><b>PUBLIC COMMENT FOR ITEMS ON CONSENT AGENDA</b></p>

<p class="ft15"><b>7.</b><b>CONSENT AGENDA</b></p>

<p class="ft113"><i>The following items are presented.</i>Lorem Ipsum, so there.</p>

</body></html>''')

        losalamosmtgs.join_consecutive_tags(soup, 'b')
        self.assertEqual(str(soup), '''<html><body><p class="ft15"><b>6.PUBLIC COMMENT FOR ITEMS ON CONSENT AGENDA</b></p>

<p class="ft15"><b>7.CONSENT AGENDA</b></p>

<p class="ft113"><i>The following items are presented.</i>Lorem Ipsum, so there.</p>

</body></html>''')


if __name__ == '__main__':
    unittest.main()


