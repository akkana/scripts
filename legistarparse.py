#!/usr/bin/env python3

# Parse a legistar PDF calendar page using pdfminer

# https://stackoverflow.com/a/59423919

from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.layout import LTTextBoxHorizontal

# For keeping a list sorted:
import bisect


# Keep track of the start position of columns.
# Round to integers. Keep sorted.
column_exes = []


def parse_pdf_file(filename):
    # convert all horizontal text into a lines list (one entry per line)
    # document is a file stream
    document = open(filename, 'rb')
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    exes = set()
    for page in PDFPage.get_pages(document):
        interpreter.process_page(page)
        layout = device.get_result()
        for element in layout:
            if not isinstance(element, LTTextBoxHorizontal):
                continue

            # element is a LTTextBoxHorizontal
            # and has get_text()
            # x0 y0 x1 y1 width neight
            # bbox: (x0, y0, x1, y1)
            # print(element.get_text(), element.x0, element.y0)

            col = determine_column(element)
            print(element.get_text(), col, element.y0)

    print("Columns:", column_exes)


# How much slop in deciding something is in the same column?
COLSLOP = 1.5

def determine_column(textbox:LTTextBoxHorizontal) -> int:
    """Which column, rounded to the nearest inch, is this textbox in?
       If column_exes doesn't have a column for it, add one.
    """
    x0 = textbox.x0
    for colx in column_exes:
        if abs(x0 - colx) < COLSLOP:
            return colx
        print(x0, "too far from", colx)

    # Insert into the list
    x0 = int(x0)
    bisect.insort(column_exes, x0)
    return x0


if __name__ == '__main__':
    import sys

    parse_pdf_file(sys.argv[1])



