#!/usr/bin/env python

def gen_lircrc(lircd_conf):
    for line in open(lircd_conf):
        line = line.strip()
        if not line.startswith("KEY_"):
            continue
        words = line.split()
        print('''    begin
        prog = beep
        button = %s
        config = %s, %s
    end''' % (words[0], words[0], words[1]))

if __name__ == '__main__':
    import sys
    gen_lircrc(sys.argv[1])

