#!/usr/bin/env python3

import csv
import docx
import html2text

html_converter = html2text.HTML2Text()
html_converter.body_width = 0


class Candidate:
    def __init__(self, name, lastname, party, questions, answers):
        '''name, lastname, party are strings
           questions and answers are lists
        '''
        self.name = name
        self.lastname = lastname
        self.party = party
        self.questions = questions
        self.answers = answers

        self.sortkey = ''.join([ c.lower() for c in self.lastname
                                           if c.isalpha() ])


    def output(self, formatter):
        formatter.add_header(self.name, 2)
        formatter.add_paragraph('(' + self.party + ')')

        for i, q in enumerate(self.questions):
            # formatter.add_header(q, 3)
            formatter.add_bold_paragraph(q)
            if self.answers[i]:
                formatter.add_paragraph(self.answers[i])
            else:
                formatter.add_paragraph("No response was received.")

    # Sorting:
    # Adjust as needed to match ballot order.
    def __lt__(self, other):
        return self.sortkey < other.sortkey


class TextFormatter:
    def __init__(self):
        pass

    def add_header(self, s, level):
        print('===', s)
        print()

    def add_paragraph(self, s):
        print(s)
        print()

    def add_bold_paragraph(self, s):
        print('*', s)
        print()

    def save(self, outfile):
        pass


class HtmlFormatter:
    def __init__(self):
        print ('''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>asdf</title>
</head>

<body>
''')

    def add_header(self, s, level):
        print(f'<h{level}>{s}</h{level}>')

    def add_paragraph(self, s):
        print(f'<p>{s}</p>')

    def add_bold_paragraph(self, s):
        print(f'<p><b>{s}</b></p>')

    def save(self, outfile):
        print('''
</body>
</html>''')


class DocxFormatter:
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
    with open(filename) as csvfp:
        reader = csv.reader(csvfp, delimiter='\t')

        # Get the first line, and use it to figure out important fields
        columnnames = next(reader)

        # tab-separated files exported by VOTE411 have column names
        # up to the second question, but after that, the columns
        # are blank. That's why this can't use csv.DictReader.
        # Instead, go through and figure out the indices for
        # the columns that will be needed.
        name_i = columnnames.index('Name')
        lastname_i = columnnames.index('Last Name')
        office_i = columnnames.index('Race/Referendum')
        desc_i = columnnames.index('Description of Race/Referendum')
        party_i = columnnames.index('Party Affiliation')
        question1_i = columnnames.index('Question 1')

        formatter = None
        candidates = []

        for row in reader:
            # For /lwvnm20_tdv-all.txt, Each row is an OrderedDict with:
            # ID	Name	Last Name	Private Email	Contact Name	Security Code	Party Affiliation	Race/Referendum	Description of Race/Referendum	Category of Race/Referendum	Occupation	Mailing Address	Campaign Phone	Website	Street address	Campaign Email	Facebook	Twitter	OCD	facebook	Question 1	Guide Answer 1	Print Answer 1	Question 2	Guide Answer 2	Print Answer 2	...

            if not formatter:
                if fmt == 'text':
                    formatter = TextFormatter()
                elif fmt == 'html':
                    formatter = HtmlFormatter()
                elif fmt == 'docx':
                    formatter = DocxFormatter()

                formatter.add_header(row[office_i], 1)
                formatter.add_paragraph(html_converter.handle(row[desc_i]))

            # Loop over the questions. They start at index question1_i
            # and there are three columns for each question:
            # question, Guide Answer, Print Answer.
            # Print Answers are always blank, I don't know what they're for.
            questions = []
            answers = []
            questionnum = 1
            while True:
                q_i = question1_i + (questionnum-1) * 3
                # print(row)
                # print("q_i", q_i, "len", len(row))
                if len(row) < q_i + 2:
                    break
                questions.append(row[q_i])
                answers.append(row[q_i + 1])

                questionnum += 1


            candidates.append(Candidate(row[name_i], row[lastname_i],
                                        row[party_i], questions, answers))

        # Done with loop over tab-separated lines. All candidates are read.
        candidates.sort()

        for candidate in candidates:
            candidate.output(formatter)

        formatter.save('savedoc.docx')


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Convert Vote411 tab-separated files to text or docx")
    parser.add_argument('-F', "--format", dest="format", default='text',
                        action="store", help="Output format: text, html, docx")
    parser.add_argument('infiles', nargs='+',
                        help="Input files, in tab-separated format")
    args = parser.parse_args(sys.argv[1:])

    for f in args.infiles:
        convert_vote411_file(f, fmt=args.format)




