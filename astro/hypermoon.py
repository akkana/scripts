#!/usr/bin/env python3

# Invent silly names for the moon

import sys, os
import random
import cgi


def hypermoon(filename, num=4):
    with open(filename, encoding='utf-8') as fp:
        lines = fp.readlines()

        words = [ lines[random.randint(0, len(lines))].strip()
                  for i in range(num) ]
        words.append('moon')
        return ' '.join(words)


if __name__ == '__main__':
    random.seed()
    num = 4

    if 'REQUEST_METHOD' in os.environ:
        print('''Content-Type: text/html

<head>
<title>Tonight's Moon</title>
</head>
<body>''')
        form = cgi.FieldStorage()

        if 'nwords' in form:
            try:
                num = int(form['nwords'].value)
            except:
                print("<p>I don't understand 'nwords=%s'"
                      % form['nwords'].value)
                num = 4

        print("<p>Tonight's moon is a <b>")

    else:
        form = None
        if len(sys.argv) > 1:
            num = int(sys.argv[1])

    print(hypermoon('/usr/share/dict/words', num))

    if form:
        print('</b>\n</body>\n</html>')
