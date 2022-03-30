#!/usr/bin/env python3

# An example of how to change the selection programmatically
# in a GTK3 TreeView.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class TreeViewWindow(Gtk.Window):

    def __init__(self, wordlist):
        super().__init__()

        self.wordlist = wordlist
        self.wordindex = 0

        self.cur_row = None

        self.width = 350
        self.height = 500
        self.set_default_size(self.width, self.height)

        main_vbox = Gtk.VBox(spacing = 10)
        self.add(main_vbox)

        #
        # Left pane: the font list, a TreeView backed by a ListStore
        #
        sw = Gtk.ScrolledWindow()
        # sw.set_policy(Gtk.POLICY_AUTOMATIC, Gtk.POLICY_AUTOMATIC)

        store = Gtk.ListStore(str)
        self.treeview = Gtk.TreeView(model=store)

        selection = self.treeview.get_selection()
        # selection.set_mode(Gtk.SELECTION_MULTIPLE)

        # self.treeview.connect("cursor-changed", self.render_font);

        sw.add(self.treeview)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Items", rendererText, text=0)
        column.set_sort_column_id(0)
        self.treeview.set_search_column(0)
        self.treeview.append_column(column)

        main_vbox.pack_start(sw, True, True, 0)

        self.connect("delete_event", Gtk.main_quit)
        self.connect("destroy", Gtk.main_quit)
        self.connect("key-press-event", self.key_press_event)

        with open("/usr/share/dict/words") as dictfp:
            for line in dictfp:
                store.append([line.strip()])

        # Done with UI, finish showing window
        self.show_all()

    def key_press_event(self, widget, event):
        if event.string == "q":
            Gtk.main_quit()

        if event.string == " ":
            self.next_word()

    def next_word(self):
        """Select the treeview row matching the given word, if any.
        """
        if not self.wordlist:
            print("I have no words.")
            return

        word = self.wordlist[self.wordindex]
        self.wordindex = (self.wordindex + 1) % len(self.wordlist)
        print("Looking for", word)

        # Iterate through the treeview
        store = self.treeview.get_model()
        for row, treemodelrow in enumerate(store):
            # treemodelrow is a gi.overrides.Gtk.TreeModelRow
            # treemodelrow[0] is the name of the font
            if treemodelrow[0] == word:
                # print("Matched line", row, treemodelrow[0])
                col0 = self.treeview.get_column(0)
                self.treeview.set_cursor(row, col0, True)
                # In fontasia, the treeview won't scroll automatically,
                # but in this program, it does so scroll_to_cell isn't needed.
                # self.treeview.scroll_to_cell(row)
                return

            treemodelrow = treemodelrow.get_next()

        print("Couldn't find", word)


if __name__ == '__main__':
    import sys

    tvw = TreeViewWindow(sys.argv[1:])

    Gtk.main()

