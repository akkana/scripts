#!/usr/bin/env python3

import csv
import docx
import html2text

html_converter = html2text.HTML2Text()
html_converter.body_width = 0


class TextResponse:
    def __init__(self):
        pass

    def add_header(self, s, level):
        print('*', s)
        print()

    def add_paragraph(self, s):
        print(s)
        print()

    def add_bold_paragraph(self, s):
        print('*', s)
        print()

    def save(self, outfile):
        pass


class DocxResponse:
    def __init__(self):
        self.doc = docx.Document()

    def add_header(self, s, level):
        self.doc.add_heading(s, level-1)

    def add_paragraph(self, s):
        self.doc.add_paragraph(s)

    def add_bold_paragraph(self, s):
        # https://www.geeksforgeeks.org/python-working-with-docx-module/
        para = self.doc.add_paragraph('')
        para.add_run(s).bold = True

    def save(self, outfile):
        self.doc.save(outfile)
        print("Saved to", outfile)


# Read tab-separated files
def convert_vote411_file(filename, fmt='text'):
    # This doesn't work:
    # tab-separated files exported by VOTE411 have column names
    # up to the second question, but after that, the columns
    # are blank. So you can't just use csv.DictReader.
    with open(filename) as csvfp:
        reader = csv.DictReader(csvfp, delimiter='\t')

        response = None

        for row in reader:
            # For /lwvnm20_tdv-all.txt, Each row is an OrderedDict with:
            # ID	Name	Last Name	Private Email	Contact Name	Security Code	Party Affiliation	Race/Referendum	Description of Race/Referendum	Category of Race/Referendum	Occupation	Mailing Address	Campaign Phone	Website	Street address	Campaign Email	Facebook	Twitter	OCD	facebook	Question 1	Guide Answer 1	Print Answer 1	Question 2	Guide Answer 2	Print Answer 2	...

            if not response:
                if fmt == 'text':
                    response = TextResponse()
                elif fmt == 'docx':
                    response = DocxResponse()

                response.add_header(row['Race/Referendum'], 1)
                response.add_paragraph(html_converter.handle(row['Description of Race/Referendum']))

            response.add_header(row['Name'], 2)
            response.add_paragraph('(' + row['Party Affiliation'] + ')')

            questionnum = 1
            while True:
                qidx = f'Question {questionnum}'
                if qidx not in row:
                    break

                # response.add_header(row[qidx], 3)
                response.add_bold_paragraph(row[qidx])
                gidx = f'Guide Answer {questionnum}'
                # I don't know what the Print Answer is for,
                # but empirically it seems to be blank.
                # pidx = f'Print Answer {questionnum}'
                answer = row[gidx]
                if answer:
                    response.add_paragraph(answer)
                else:
                    response.add_paragraph("No response was received.")

                questionnum += 1

        # Done with loop over tab-separated lines.
        response.save('savedoc.docx')


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Convert Vote411 tab-separated files to text or docx")
    parser.add_argument('-F', "--format", dest="format", default='text',
                        action="store", help="Output format: text or docx")
    parser.add_argument('infiles', nargs='+',
                        help="Input files, in tab-separated format")
    args = parser.parse_args(sys.argv[1:])

    for f in args.infiles:
        convert_vote411_file(f, fmt=args.format)




