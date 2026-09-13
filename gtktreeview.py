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

        sw = Gtk.ScrolledWindow()
        # sw.set_policy(Gtk.POLICY_AUTOMATIC, Gtk.POLICY_AUTOMATIC)

        # The store is either a ListStore or TreeStore,
        # depending on whether it's flat or hierarchical.
        store = Gtk.TreeStore(str)
        self.treeview = Gtk.TreeView(model=store)

        selection = self.treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        selection.connect("changed", self.tree_changed);
        # There's also "cursor-changed" on the treeview,
        # but that doesn't work with multi selection

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

        print("Reading the dictionary ...")

        initial_letter = None
        curparent = None
        with open("/usr/share/dict/words") as dictfp:
            for line in dictfp:
                word = line.strip()
                if word[0].upper() != initial_letter:
                    initial_letter = word[0].upper()
                    # Appending these items takes too long for a demo; stop at D
                    if initial_letter == 'D':
                        break
                    curparent = store.append(None, [initial_letter])
                store.append(curparent, [word])
        print("Done with dictionary")

        # Done with UI, finish showing window
        self.show_all()

    def key_press_event(self, widget, event):
        if event.string == "q":
            Gtk.main_quit()

        if event.string == " ":
            self.next_word()

    def select_name(self, name):
        def visit(model, path, iter, data=None):
            depth = path.get_depth()
            #     1 = top-level, 2 = child, 3 = grandchild, etc.
            has_kids = model.iter_has_child(iter)
            #     does this particular row have kids?
            indent = "  " * (depth - 1)
            # print(f"{indent}{model[iter][0]}  (depth={depth}, "
            #       f"has_children={has_kids})")
            if model[iter][0] == name:
                # Expand ancestor rows so the row is visible.
                # This expands every ancestor of the path.
                self.treeview.expand_to_path(path)

                # Select it
                # selection.unselect_all()
                selection.select_path(path)

                # Scroll so it's visible.
                # Adding 0.5, 0.0 centers vertically, keeping horizontal as-is
                # use_align=False (third arg) means don't center it
                # if it's already visible.
                # Call expand_to_path first, before calling scroll_to_cell.
                self.treeview.scroll_to_cell(path, None, False)
                # , 0.5, 0.0)
                # Arguably, should only call scroll_to_cell on the first
                # selected line.

                return True
            return False

        model.foreach(visit)
        # Another way to do this:
        # model.iter_parent(iter) returns None for top-level rows,
        # or the parent iter otherwise; another way to distinguish
        # "has no parent" (top-level) from "has a parent."

    def tree_changed(self, widget):
        selection = self.treeview.get_selection()
        model, paths = selection.get_selected_rows()
        # paths is a list of Gtk.TreePath objects.
        if not paths:
            return None

        print("Selected:")
        for path in paths:
            print("   ", model[path][0])

        # return the first selected line
        return model[paths[0]][0]

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

