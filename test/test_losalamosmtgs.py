#!/usr/bin/env python3

import unittest

from bs4 import BeautifulSoup

import losalamosmtgs

class TestCleanUp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

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


