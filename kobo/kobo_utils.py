#!/usr/bin/env python

import os, sys
import sqlite3

class KoboDB:
    def __init__(self, mountpath):
        self.mountpath = mountpath
        self.dbpath = None

    def connect(self, dbpath=None):
        if dbpath:
            self.dbpath = dbpath
        elif self.mountpath:
            self.dbpath = os.path.join(mountpath, ".kobo/KoboReader.sqlite")
        else:
            print "No DB path specified"
            return

        conn = sqlite3.connect(self.dbpath)
        self.cursor = conn.cursor()

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
