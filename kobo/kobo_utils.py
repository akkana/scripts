#!/usr/bin/env python

import os, sys
import sqlite3

def escape_quotes(s):
    return s.replace("'", "''")

class KoboDB:
    def __init__(self, mountpath):
        self.mountpath = mountpath
        self.dbpath = None
        self.conn = None
        self.cursor = None

    def connect(self, dbpath=None):
        if dbpath:
            self.dbpath = dbpath
        elif self.mountpath:
            self.dbpath = os.path.join(mountpath, ".kobo/KoboReader.sqlite")
        else:
            print "No DB path specified"
            return

        self.conn = sqlite3.connect(self.dbpath)
        self.cursor = self.conn.cursor()

    def close(self):
        self.conn.commit()
        self.conn.close()
        self.conn = None
        self.cursor = None

    def get_field_names(self, tablename):
        '''I haven't found documentation, but PRAGMA table_info returns:
           (index, fieldname, type, None, 0)
           I don't know what the None and 0 represent.
        '''
        self.cursor.execute('PRAGMA table_info(%s);' % tablename)
        return [ row[1] for row in self.cursor.fetchall() ]

    def get_list(self, tablename, **kwargs):
        '''Usage: get_list(tablename, selectors='*', modifiers='', order='')
        '''
        selectors = '*'
        modifiers = ''
        order = ''
        if kwargs:
            if 'selectors' in kwargs and kwargs['selectors']:
                if type(kwargs['selectors']) is list:
                    selectors = ','.join(kwargs['selectors'])
                else:
                    selectors = kwargs['selectors']
            if 'modifiers' in kwargs and kwargs['modifiers']:
                if type(kwargs['modifiers']) is list:
                    modifiers = " WHERE " + 'AND'.join(kwargs['modifiers'])
                else:
                    modifiers = " WHERE " + kwargs['modifiers']
            if 'order' in kwargs and kwargs['order']:
                order = " ORDER BY " + kwargs['order']

        sql = "SELECT %s FROM %s%s%s;" % (selectors, tablename,
                                          modifiers, order)
        print sql
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_dlist(self, tablename, **kwargs):
        '''Usage: get_dlist(tablename, selectors='*', modifiers='', order='')
        '''
        l = self.get_list(tablename, **kwargs)

        if kwargs and 'selectors' in kwargs:
            fields = kwargs['selectors']
        else:
            fields = self.get_field_names(tablename)

        return [ dict(zip(fields, values)) for values in l ]

    def get_book_by_id(self, id):
        sql = "SELECT Title,Attribution FROM content WHERE ContentID='%s';" \
              % escape_quotes(id);
        # print sql
        self.cursor.execute(sql)
        return self.cursor.fetchall()[0]

    def list_books(self):
        books = self.get_dlist("content",
                               selectors=[ 'ContentID', 'Title', 'Attribution',
                                           'Description', 'NumShortcovers',
                                           'IsEncrypted', 'IsDownloaded',
                                           'adobe_location' ],
                               modifiers="content.BookTitle is null",
                               order="content.Title")

        for book in books:
            print "%s (%s)" % (book["Title"], book["Attribution"])
            print "  ContentID:", book["ContentID"]
            if book["NumShortcovers"]:
                print "  Chapters:", book["NumShortcovers"]
            print "  Encrypted?", book["IsEncrypted"],
            print "   Downloaded?", book["IsDownloaded"],
            if book["adobe_location"]:
                if book["adobe_location"] == book["ContentID"]:
                    print "    adobe_location: Yes"
                else:
                    print "\n  adobe_location:", book["adobe_location"]
            else:
                print

            # Description is very long; make this optional.
            # print "  Description:", book["Description"]

            print


    def list_shelves(self, names=None):
        allshelves = {}
        if names:
            modifiers = " AND ".join(["ShelfName=%s" % name for name in names])
        else:
            modifiers = None

        sc = self.get_dlist("ShelfContent", modifiers=modifiers)

        for item in sc:
            if item["ShelfName"] not in allshelves:
                allshelves[item["ShelfName"]] = [ item["ContentId"] ]
            else:
                allshelves[item["ShelfName"]].append(item["ContentId"])

        for shelf in allshelves:
            print "\n===", shelf, "==="
            for id in allshelves[shelf]:
                print "    %s (%s)" % self.get_book_by_id(id)

    def has_shelf(self, shelfname):
        shelves = self.get_dlist("Shelf", selectors=[ "Name" ],
                                 modifiers=[ "Name='%s'" % shelfname ])
        print "Has shelf %s?" % shelfname, bool(shelves)
        return bool(shelves)

    def print_table(self, tablename, **kwargs):
        '''Usage: print_table(tablename, selectors='*', modifiers='', order='')
        '''
        if kwargs and 'selectors' in kwargs and kwargs['selectors']:
            fields = kwargs['selectors']
            print "kwargs: fields =", fields
        else:
            fields = self.get_field_names(tablename)
            print "no kwargs: fields =", fields

        for row in self.get_list(tablename, **kwargs):
            for i, f in enumerate(fields):
                # Must coerce row[i] to unicode before encoding,
                # even though it should be unicode already,
                # because it could be null.
                print f.encode('UTF-8'), ":", unicode(row[i]).encode('UTF-8')

    # Adding entries to shelves:
    def make_new_shelf(self, shelfname):
        print "=== Current shelves:"
        self.print_table("Shelf", selectors=[ "Name" ])
        print "==="
        print "Making a new shelf called", shelfname
        # Skip type since it's not clear what it is and it's never set.
        # For the final three, PRAGMA table_info(Shelf); says they're
        # type BOOL, and querying that table shows true and false there,
        # but absolutely everyone on the web says you have to use
        # 1 and 0 for sqlite3 and that there is no boolean type.
        query = '''INSERT INTO Shelf(CreationDate, Id, InternalName,
                  LastModified, Name, _IsDeleted, _IsVisible, _IsSynced)
VALUES (DATETIME('now'), %s, '%s', DATETIME('now'), '%s', 0, 1, 1);
''' % (shelfname, shelfname, shelfname)
        print query
        self.cursor.execute(query)

    def add_to_shelf(self, kobobook, shelfname):
        print "==="
        print "Adding", kobobook["Title"], "to shelf", shelfname
        query = '''INSERT INTO ShelfContent(ShelfName, ContentId, DateModified,
                         _IsDeleted, _IsSynced)
VALUES ('%s', '%s', DATE('now'), 0, 0);''' % (shelfname,
                                              escape_quotes(kobobook['ContentID']))
        print query
        self.cursor.execute(query)
        self.conn.commit()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="""Show details about a Kobo ebook reader.
By default, show a list of books.

Copyright 2015 by Akkana Peck; share and enjoy under the GPLv2 or later.""",
                         formatter_class=argparse.RawDescriptionHelpFormatter)

    # Options:
    parser.add_argument("-m", "--mountdir", default="/kobo",
                    help="""Path where the Kobo is mounted. Default: /kobo""")
    parser.add_argument("-d", "--db",
                        default="$mountdir/.kobo/KoboReader.sqlite",
                        help="""Path to the database.
Default: $mountdir/.kobo/KoboReader.sqlite""")

    # Things we can do:
    parser.add_argument("-s", "--shelves", action='store_true', default=False,
                        help="""Show shelves""")
    parser.add_argument("-S", "--shelfnames", action='store_true',
                        default=False,
                        help="""Show shelf names but not their contents""")

    args = parser.parse_args()
    args.db = args.db.replace('$mountdir', args.mountdir)

    try:
        koboDB = KoboDB(args.mountdir)
        koboDB.connect(args.db)
    except Exception, e:
        print "Couldn't open database at %s for Kobo mounted at %s" % \
            (args.db, args.mountdir)
        print e
        sys.exit(1)

    if args.shelfnames:
        shelves = koboDB.get_dlist("Shelf", selectors=[ "Name" ])
        for shelf in shelves:
            print shelf["Name"]
    elif args.shelves:
        koboDB.list_shelves()
    else:
        koboDB.list_books()
