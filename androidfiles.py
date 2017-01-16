#!/usr/bin/env python

import sys, os
import subprocess
import posixpath

def is_android(path):
    return path.startswith("android:")

def strip_schema(path):
    '''Strip off any android: prefix in the path.
    '''
    if path.startswith("android:"):
        return path[8:]
    return path

def listdir(path, sort=True, sizes=False):
    '''List the contents of the given directory.
       Returns a list of filenames if sizes=False.
       If sizes=True, returns a list of tuples (filename, int size).
    '''
    proc = subprocess.Popen(["adb", "shell", "ls", "-l", strip_schema(path)],
                            shell=False,
                            stdout=subprocess.PIPE)
    stdout_lines = proc.communicate()[0].split('\n')
    file_list = []
    for l in stdout_lines:
        l = l.strip().split()
        if len(l) == 7:
            if sizes:
                try:
                    file_list.append((l[-1], int(l[3])))
                except:
                    # This could happen for the initial "Total:" line
                    pass
            else:
                file_list.append(l[-1])
    if sort:
        file_list.sort()

    return file_list

def copyto(f, outdir, fname):
    '''Copy a local file (f is the full pathname) to the android device
       at android location outdir, android new filename fname.
    '''
    subprocess.call(["adb", "push", f, posixpath.join(strip_schema(outdir),
                                                      fname)])

if __name__ == "__main__":
    # copyto('/home/akkana/POD/Science/Story_Collider/249076872-the-story-collider-jonaki-bhattacharyya-losing-control.mp3', 'android:/mnt/extSdCard/Music/Podcasts', '16-05-99-so-special.mp3')

    if len(sys.argv) < 2:
        print("Usage: %s path [path ...]" % os.path.basename(sys.argv[0]))
        sys.exit(1)

    sizes = True

    for path in (sys.argv[1:]):
        files = listdir(path, sizes=sizes)
        if sizes:
            print("%s:" % path)
            for f in files:
                print("%d\t%s" % (int(f[1]/1000), f[0]))
        else:
            print("%s: %s" % (path, ', '.join(files)))

