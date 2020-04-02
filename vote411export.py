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
        formatter.add_name_and_party(self.name, f'({self.party})')

        for i, q in enumerate(self.questions):
            if not self.answers[i]:
                self.answers[i] = "No response was received."

            # No paragraph break between question and answer
            formatter.add_q_and_a(f'{i+1}. {q}', self.answers[i])

    # Sorting:
    # Adjust as needed to match ballot order.
    def __lt__(self, other):
        return self.sortkey < other.sortkey


class TextFormatter:
    def __init__(self):
        pass

    def add_office(self, office, description):
        print("===", office)
        print(description)
        print()

    def add_name_and_party(self, name, party):
        print("*", name)
        print(party)
        print()

    def add_q_and_a(self, question, answer):
        print(question)
        print(answer)
        print()

    def save(self, outfile):
        pass


class HtmlFormatter:
    def __init__(self):
        self.htmlstr = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>asdf</title>
</head>

<body>
'''

    def add_office(self, office, description):
        self.htmlstr += f'<h1>{office}</h1>\n<p>' + description + '\n'

    def add_name_and_party(self, name, party):
        self.htmlstr += f'\n<h2>{name}</h2>\n' + party

    def add_q_and_a(self, question, answer):
        self.htmlstr += f'<p>\n<b>{question}</b><br />\n' + answer

    def save(self, outfile):
        self.htmlstr += '''
</body>
</html>
'''
        outfile = 'savedoc.html'
        with open(outfile, 'w') as outfp:
            outfp.write(self.htmlstr)
        print('Saved to', outfile)


class DocxFormatter:
    FONT_NAME = "Times New Roman"
    BASE_SIZE = 12
    TITLE_SIZE = 16
    NAME_SIZE = 14
    QUESTION_SIZE = 14

    def __init__(self):
        self.doc = docx.Document()
        self.para = None

        # Diane says she just uses normal text and changes the size
        # and boldness, but I can't help but think that using actual
        # headers would make it easier for the newspaper to convert
        # it to HTML for their website. Make it optional:
        self.use_headings = True

        font = self.doc.styles['Normal'].font
        font.name = self.FONT_NAME
        font.size = docx.shared.Pt(self.BASE_SIZE)

    def add_office(self, office, description):
        if self.use_headings:
            heading = self.doc.add_heading(office, 1)
            self.set_heading_style(heading, self.TITLE_SIZE)
            self.doc.add_paragraph(description)

        else:
            self.para = self.doc.add_paragraph('')
            run = self.para.add_run(office + '\n')
            run.bold = True
            run.font.size = docx.shared.Pt(self.TITLE_SIZE)
            run = self.para.add_run(description)

    def add_name_and_party(self, name, party):
        if self.use_headings:
            heading = self.doc.add_heading(name, 2)
            self.set_heading_style(heading, self.NAME_SIZE)
            self.doc.add_paragraph(party)

        else:
            if not self.para:
                self.para = self.doc.add_paragraph('')
            run = self.para.add_run('\n' + name + '\n')
            run.bold = True
            run.font.size = docx.shared.Pt(self.NAME_SIZE)
            run = self.para.add_run(party)
            run.font.size = docx.shared.Pt(self.BASE_SIZE)

    def add_q_and_a(self, question, answer):
        self.para = self.doc.add_paragraph('')

        run = self.para.add_run(question)
        run.bold = True
        run.font.size = docx.shared.Pt(self.QUESTION_SIZE)

        self.para.add_run('\n')
        run = self.para.add_run(answer)
        run.font.size = docx.shared.Pt(self.BASE_SIZE)

    def set_heading_style(self, heading, font_size):
        heading.style.font.size = docx.shared.Pt(font_size)

        # https://stackoverflow.com/questions/60921603/how-do-i-change-heading-font-face-and-size-in-python-docx
        rFonts = heading.style.element.rPr.rFonts
        rFonts.set(docx.oxml.ns.qn("w:asciiTheme"), self.FONT_NAME)

        # Also change the color from blue to black:

        # This works, using the same technique as for font name,
        # but is obscure:
        # color = heading.style.element.rPr.color
        # color.set(docx.oxml.ns.qn("w:val"), "000000")

        # A more readable way.
        # The .color attribute on Font is a ColorFormat object,
        # not an RGBColor directly
        heading.style.font.color.rgb = docx.shared.RGBColor(0, 0, 0)

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

                formatter.add_office(row[office_i],
                                     html_converter.handle(row[desc_i]).strip())

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




