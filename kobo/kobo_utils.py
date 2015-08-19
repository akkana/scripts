#!/usr/bin/env python

import os, sys
import sqlite3

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
            if 'selectors' in kwargs:
                selectors = ','.join(kwargs['selectors'])
            if 'modifiers' in kwargs:
                modifiers = " WHERE " + kwargs['modifiers']
            if 'order' in kwargs:
                order = " ORDER BY " + kwargs['order']

        sql = "SELECT %s FROM %s%s%s" % (selectors, tablename,
                                         modifiers, order)
        print sql
        print
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

        # dlist = []
        # for row in l:
        #     d = {}
        #     for i, field in enumerate(fields):
        #         d[field] = l[i]
        #     dlist.append(d)
        # return dlist

    def print_table(self, tablename, **kwargs):
        '''Usage: print_table(tablename, selectors='*', modifiers='', order='')
        '''
        if kwargs and 'selectors' in kwargs:
            fields = kwargs['selectors']
        else:
            fields = self.get_field_names(tablename)

        for row in self.get_list(tablename, **kwargs):
            for i, f in enumerate(fields):
                # Must coerce row[i] to unicode before encoding,
                # even though it should be unicode already,
                # because it could be null.
                print f.encode('UTF-8'), ":", unicode(row[i]).encode('UTF-8')
            print

    # Adding entries to shelves:
    '''
INSERT INTO Cars(Id, Name, Price) VALUES(1, 'Audi', 52642);

select * from Shelf;
2015-08-17T20:07:57Z||science fiction|2015-08-17T20:07:57Z|science fiction||false|true|false
2015-08-17T20:09:06Z||mystery|2015-08-17T20:09:06Z|mystery||false|true|false

select * from ShelfContent;
science fiction|file:///mnt/onboard/books/the_martian.epub|2015-08-17T20:07:57Z|false|false
science fiction|file:///mnt/onboard/books/some_remarks.epub|2015-08-17T20:07:57Z|false|false
mystery|file:///mnt/onboard/books/The_Cold_Dish.epub|2015-08-17T20:09:06Z|false|false
mystery|file:///mnt/onboard/books/Death_Without_Company.epub|2015-08-17T20:09:06Z|false|false
mystery|file:///mnt/onboard/books/Pastime.epub|2015-08-17T20:09:06Z|false|false
mystery|file:///mnt/onboard/books/Playmates.epub|2015-08-17T20:09:06Z|false|false
mystery|8e8948a3-e946-43ed-8461-edd0957d050d|2015-08-17T20:09:06Z|false|false
... etc.

 PRAGMA table_info(Shelf);
0|CreationDate|TEXT|0||0
1|Id|TEXT|0||0
2|InternalName|TEXT|0||1
3|LastModified|TEXT|0||0
4|Name|TEXT|0||0
5|Type|TEXT|0||0
6|_IsDeleted|BOOL|0||0
7|_IsVisible|BOOL|0||0
8|_IsSynced|BOOL|0||0

PRAGMA table_info(ShelfContent);
0|ShelfName|TEXT|0||1
1|ContentId|TEXT|0||2
2|DateModified|TEXT|0||0
3|_IsDeleted|BOOL|0||0
4|_IsSynced|BOOL|0||0

'''
    def make_new_shelf(self, shelfname):
        print "Making a new shelf called", shelfname
        # Skip type since it's not clear what it is and it's never set:
        query = '''INSERT INTO Shelf(CreationDate, Id, InternalName,
                  LastModified, Name, _IsDeleted, _IsVisible, _IsSynced)
VALUES (DATE('now'), '', '%s', DATE('now'), '%s', 0, 1, 1);
''' % (shelfname, shelfname)
        print query
        self.cursor.execute(query)

    def add_new_shelf_content(self, kobobook, shelfname):
        print "Adding", kobobook["Title"], "to shelf", shelfname
        query = '''INSERT INTO ShelfContent(ShelfName, ContentId, DateModified,
                         _IsDeleted, _IsSynced)
VALUES ('%s', '%s', DATE('now'), 0, 0);''' % (shelfname, kobobook['ContentID'])
        print query
        self.cursor.execute(query)
