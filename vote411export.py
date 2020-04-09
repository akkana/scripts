#!/usr/bin/env python3

# Export the "Tab-Delimited, Candidate Full Export" from
# Vote411/lwv.thevoterguide.org, and format it appropriately
# for a printed voter guide.

import csv
import docx
import html2text
import re

html_converter = html2text.HTML2Text()
html_converter.body_width = 0


class Candidate:
    def __init__(self, name, lastname, office, party, questions, answers):
        '''name, lastname, party are strings
           questions and answers are lists
        '''
        # For comparing, use lowercase, collapse multiple spaces,
        # and remove any dots after middle initials.
        # It's unpredictable whether a candidate without a middle name
        # will have two spaces or one between the names in the export
        # file, and our uploading was completely inconsistent about
        # whether middle initials have a dot after them.
        self.comparename = re.sub('\.', '',
                                  re.sub(' +', ' ', name.lower()))

        self.name = name

        # OPTIONAL: Convert name to title case.
        # THIS COULD INTRODUCE ERRORS, e.g. MacPhee would become Macphee.
        # If using this option, be sure to proofread carefully!
        if self.name.isupper():
            self.name = self.name.title()

        # OPTIONAL: Add a . after a single initial that lacks one.
        self.name = re.sub(' ([A-Z]) ', ' \\1. ', self.name)

        if self.comparename.endswith(' (write-in)'):
            self.comparename = self.comparename[:-11]
        self.lastname = lastname

        self.office = office

        if party == 'Dem':
            self.party = 'Democrat'
        elif party == 'Rep':
            self.party = 'Democrat'
        elif party == 'Lib' or party == 'L':
            self.party = 'Libertarian'
        else:
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
<title>Voter Guide</title>
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


def sort_candidates(candidates, order):
    """Sort candidates according to the order in which they appear
       in the order list, if any; otherwise, alphabetically.
    """
    if not order:
        print("Sorting alphabetically")
        return candidates.sort()

    sorted_candidates = []
    num_prezzies = 0

    for cand_o in order:
        # Vote411 doesn't export presidential candidates for some reason.
        if cand_o['Contest'] == 'President of the United States':
            num_prezzies += 1
            continue

        fullname = ' '.join([cand_o['First Name'],
                             cand_o['Middle Name'],
                             cand_o['Last Name']])

        # Candidate may or may not have a middle name, so collapse
        # that extra space.
        fullname = re.sub(' +', ' ', fullname.lower())
        # print("Looking for", fullname)
        foundit = False
        for cand_c in candidates:
            if cand_c.comparename == fullname:
                sorted_candidates.append(cand_c)
                foundit = True
                break
        if not foundit:
            print(f"Couldn't find {fullname} ({cand_o['Contest']} {cand_o['District']})")

    # Done. Did we find everybody?
    if len(sorted_candidates) != len(order) - num_prezzies:
        print("Eek, didn't get everybody!")
        print("\nSorted:", len(sorted_candidates))
        print("Order file has:", len(order))
        print()

        sys.exit(1)

    return sorted_candidates


# Read tab-separated files
def convert_vote411_file(filename, fmt='text', orderfile=None):
    # Read the orderfile, if any:
    order = []
    if orderfile:
        with open(orderfile) as orderfp:
            reader = csv.DictReader(orderfp)
            for row in reader:
                order.append(row)
                # Each row has: Contest,District,County,
                #               First Name,Middle Name,Last Name,
                #               Party,Ballot Order,Status
                # We'll do an inefficient search through it for each
                # candidate, because performance is completely unimportant
                # so no point in complicating the code with
                # pointless optimization.

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

        if fmt == 'text':
            formatter = TextFormatter()
        elif fmt == 'html':
            formatter = HtmlFormatter()
        elif fmt == 'docx':
            formatter = DocxFormatter()

        candidates = []

        for row in reader:
            # For /lwvnm20_tdv-all.txt, Each row is an OrderedDict with:
            # ID	Name	Last Name	Private Email	Contact Name	Security Code	Party Affiliation	Race/Referendum	Description of Race/Referendum	Category of Race/Referendum	Occupation	Mailing Address	Campaign Phone	Website	Street address	Campaign Email	Facebook	Twitter	OCD	facebook	Question 1	Guide Answer 1	Print Answer 1	Question 2	Guide Answer 2	Print Answer 2	...

            # Loop over the questions. They start at index question1_i
            # and there are three columns for each question:
            # question, Guide Answer, Print Answer.
            # Print Answers are always blank; apparently that column is for
            # some leagues that have different answers for their printed VG.
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
                                        row[office_i], row[party_i],
                                        questions, answers))

        # Done with loop over tab-separated lines. All candidates are read.
        # candidates.sort()

        cur_office = None
        for candidate in sort_candidates(candidates, order):
            if candidate.office != cur_office:
                cur_office = candidate.office
                print_office = candidate.office \
                                      .replace('NM', 'N.M.') \
                                      .replace('DISTRICT', 'District')
                desc = html_converter.handle(row[desc_i]) \
                                     .strip() \
                                     .replace('NM', 'N.M.')
                formatter.add_office(print_office, desc)
            candidate.output(formatter)

        formatter.save('savedoc.docx')


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Convert Vote411 tab-separated files to text or docx")
    parser.add_argument('-F', "--format", dest="format", default='text',
                        action="store", help="Output format: text, html, docx")
    parser.add_argument('-o', "--orderfile", dest="orderfile", default=None,
                        help="A CSV file listing all candidates in order")
    parser.add_argument('infiles', nargs='+',
                        help="Input files, in tab-separated format")
    args = parser.parse_args(sys.argv[1:])

    for f in args.infiles:
        convert_vote411_file(f, fmt=args.format, orderfile=args.orderfile)




