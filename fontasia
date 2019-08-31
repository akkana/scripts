#!/usr/bin/python2

# fontasia 0.7:
# List all fonts on the system and let the user group them into categories.
#
# Can be run as a standalone script, or as a GIMP plug-in font chooser
# (where it shows up as Windows->Fontasia).

#
# Contributors: Akkana Peck, Mikael Magnusson, Michael Schumacher
#
# More info on fontasia: http://shallowsky.com/software/fontasia

# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

# Thanks to jan bodnar's ZetCode.com PyGTK/Pango tutorial.

import gtk
import pango
import os, re

# A buttonbox class, which can hold an arbitrary number of buttons.
# This is expected to occupy a space which may expand or contract.
# May want to experiment with several different layouts.

# The base buttonbox class is a simple vbox:
class Buttonbox():
    def __init__(self):
        self.widget = gtk.VBox(spacing=8)
    def addButton(self, btn):
        self.widget.pack_start(btn, expand=False)

# Attempt at different-sized buttons that wrap:
# this doesn't work yet, gtk doesn't offer any straightforward way.
class ButtonboxWrap(Buttonbox):
    def __init__(self):
        self.widget = gtk.HBox(spacing=8)

    def addButton(self, btn):
        self.widget.pack_start(btn, expand=False)

# A 2-dimensional table:
class ButtonboxTable(Buttonbox):
    def __init__(self):
        self.rows = 8
        self.widget = gtk.Table(homogeneous=False)
        self.cur_row = 0
        self.cur_col = 0

    def addButton(self, btn):
        self.widget.attach(btn, self.cur_col, self.cur_col+1,
                           self.cur_row, self.cur_row+1,
                           xpadding=3, ypadding=2)
        # fill vertically first
        self.cur_row += 1
        if self.cur_row >= self.rows:
            self.cur_row = 0
            self.cur_col += 1

class FontApp(gtk.Window):
    def __init__(self):
        super(FontApp, self).__init__()

        # When the quit button is pressed we'll set the quit flag,
        # but won't actually quit -- the caller has to do that
        # after checking the selected font.
        self.quit = False

        # No categories to start with
        self.category_fontlists = []
        self.category_buttons = []
        self.oldcolors = None
        self.highlightcolor = None
        self.DEFAULT_TEXT = "The quick brown fox jumped over the lazy dog"
        self.preview_text = self.DEFAULT_TEXT
        self.DEFAULT_FONT_SIZE = 18
        self.fontsize = self.DEFAULT_FONT_SIZE
        self.fancy_list = True

        # Default sizes: can be overridden in .config/fontasia/fontasia.conf
        self.win_width = 760
        self.win_height = 400
        self.preview_height = 56
        self.list_width = 250

        # Have we changed anything, so we need to rewrite the config file?
        self.modified = False

        self.set_border_width(8)
        self.connect("destroy", self.save_and_quit)
        self.set_title("Fontasia: Categorize your fonts")

        main_vbox = gtk.VBox(spacing = 10)
        self.add(main_vbox)

        hbox = gtk.HBox(spacing = 10)
        main_vbox.pack_start(hbox, expand=False)

        #
        # The preview
        #
        self.preview = gtk.Entry()
        self.preview.set_width_chars(45)
        self.preview.set_text(self.preview_text)

        # Don't use fallbacks for characters not in the current font.
        # This apparently doesn't work.
        al = pango.AttrList()
        al.insert(pango.AttrFallback(False, 0, -1))
        self.preview.get_layout().set_attributes(al)

        hbox.pack_start(self.preview, expand=True)

        # Quit button
        btn = gtk.Button("Quit")
        hbox.pack_end(btn, expand=False)
        btn.connect("clicked", self.save_and_quit);

        main_hbox = gtk.HBox(spacing = 10)
        main_vbox.add(main_hbox)

        #
        # Left pane: the font list
        #
        self.sw = gtk.ScrolledWindow()
        self.sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        context = self.create_pango_context()
        self.all_families = context.list_families()
        self.store = gtk.ListStore(str)

        self.treeView = gtk.TreeView(self.store)
        self.treeView.set_rules_hint(True)
        self.store.set_sort_column_id(0, gtk.SORT_ASCENDING)

        selection = self.treeView.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)

        self.treeView.connect("cursor-changed", self.render_font);

        self.sw.add(self.treeView)

        self.create_column(self.treeView)

        main_hbox.pack_start(self.sw, expand=False)

        #
        # Right pane: the controls
        #
        vbox = gtk.VBox(spacing=15)
        main_hbox.pack_start(vbox, expand=True)

        # Box to hold font size, view category etc.
        hbox = gtk.HBox(spacing=10)
        vbox.pack_start(hbox, expand=False)

        # Checkbox for showing fonts in the font list
        self.fancy_btn = gtk.ToggleButton("Fancy list")
        self.fancy_btn.set_active(self.fancy_list)
        self.fancy_btn.connect("toggled", self.toggle_fancy_list_cb);
        hbox.pack_start(self.fancy_btn, expand=False)

        # Font size
        label = gtk.Label("Size:")
        hbox.pack_start(label, expand=False)

        adj = gtk.Adjustment(self.fontsize, 1, 1000, 1)
        self.sizespin = gtk.SpinButton(adj)
        self.sizespin.set_numeric(True)
        self.sizespin.connect("value-changed", self.render_font);
        hbox.pack_start(self.sizespin, expand=False)

        # Bold and italic buttons
        self.bold_btn = gtk.ToggleButton("Bold")
        hbox.pack_start(self.bold_btn, expand=False)
        self.bold_btn.connect("toggled", self.render_font);
        self.italic_btn = gtk.ToggleButton("Italic")
        hbox.pack_start(self.italic_btn, expand=False)
        self.italic_btn.connect("toggled", self.render_font);

        #
        # View category menu
        #
        label = gtk.Label("View:")
        # This is supposed to right-align the label, but alas it does nothing:
        label.set_alignment(1.0, .5)
        # This also doesn't right-align, but the docs are clear on that:
        # label.set_justify(gtk.JUSTIFY_RIGHT)
        hbox.pack_start(label, expand=False)

        self.view_cat_combo = gtk.combo_box_new_text()
        hbox.pack_start(self.view_cat_combo, expand=False)
        self.combo_connect_id = self.view_cat_combo.connect("changed",
                                                            self.combochanged)

        # Now we can get the default button background (I hope):
        widgcopy = btn.get_style().copy()
        self.oldcolors = widgcopy.bg
        self.highlightcolor = gtk.gdk.Color(0, 65535, 0)

        # Categories header row
        hbox = gtk.HBox(spacing=8)
        vbox.pack_start(hbox, expand=False)
        label = gtk.Label("Categories")
        hbox.pack_start(label, expand=False)

        entry = gtk.Entry()
        entry.set_width_chars(20)
        hbox.pack_start(entry, expand=False)

        btn = gtk.Button("Add category")
        hbox.pack_start(btn, expand=False)
        btn.set_sensitive(False)
        btn.connect("clicked", self.add_category, entry);
        # The entry and button are tied together:
        entry.connect("changed", self.new_cat_entry_changed, btn);

        #
        # The buttonbox: the list of category togglebuttons.
        #
        self.buttonbox = ButtonboxTable()
        vbox.pack_start(self.buttonbox.widget, expand=True)

        #
        # Just before showing, update everything:
        #
        self.read_category_file()

        # Set size requests, now that we've read them from the config file:
        self.set_default_size(self.win_width, self.win_height)

        self.sw.set_size_request(self.list_width, -1)
        #self.sw.set_size_request(self.list_width, self.list_height)
        self.preview.set_size_request(-1, self.preview_height)

        self.update_font_list()

        # Done with UI, finish showing window
        self.show_all()

        # Setting size_requests earlier set the *minimum* size,
        # but we don't want to do that. So reset the size request
        # once the widgets have already been sized.
        # Alas, gtk has no way to just set the size without
        # specifying a minimum; size_allocate() is a no-op.
        #self.sw.set_size_request(self.list_width, 1)
        #self.preview.set_size_request(-1, -1)

    def save_and_quit(self, widget=None):
        self.write_category_file()
        self.quit = True
        # gtk.main_quit()

    def toggle_fancy_list_cb(self, widget):
        self.fancy_list = widget.get_active()
        self.toggle_fancy_list(self.fancy_list)
        #self.update_font_list()

    def toggle_fancy_list(self, yesno):
        column = self.treeView.get_column(0)
        rendererText = column.get_cell_renderers()[0]
        if self.fancy_list:
            column.set_cell_data_func(rendererText, self.set_list_font)
        else:
            column.set_cell_data_func(rendererText, None)
            rendererText.set_property('font', None)

    def set_list_font(self, column, cell, model, iter):
        fontname = model.get_value(iter, 0)

        # If the font name ends with a number, we're in trouble --
        # pango will try to interpret the number as a HUGE size.
        # Sample fonts to test: Math2, Math3,
        # Plain Cred 1978 from ttf-larabie-uncommon.
        # A few fonts still give width problems, like
        # Radios in Motion and Radios in Motion Hard.
        # Scriptina - Alternates and Coca-Cola.
        fontname = re.sub('[0-9]+$', '', fontname)

        cell.set_property('font', fontname)

    def create_column(self, treeView):
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Font name", rendererText, text=0)
        column.set_sort_column_id(0)
        if self.fancy_list:
            column.set_cell_data_func(rendererText, self.set_list_font)
        treeView.set_search_column(0)
        treeView.append_column(column)

    def is_font_in_category(self, fontname, catname):
        for i in range(0, len(self.category_buttons)):
            if self.category_buttons[i].get_name() == catname:
                return ( fontname in self.category_fontlists[i] )
        return False

    #
    # If the font is already in the category, this will remove it;
    # else add it.
    #
    def toggle_font_in_category(self, fontname, catname):
        for i in range(0, len(self.category_buttons)):
            if self.category_buttons[i].get_name() == catname:
                if fontname in self.category_fontlists[i]:
                    self.category_fontlists[i].remove(fontname)
                else:
                    self.category_fontlists[i].append(fontname)
                return

    #
    # This is the callback from the font category togglebuttons.
    # It calls toggle_font_in_category.
    #
    def toggle_cur_font_in_cat(self, widget, catname):
        selection = self.treeView.get_selection()
        model, item = selection.get_selected_rows()

        # Read all the selected fonts, not just the first one:
        for x in item:
            fontname = model[x[0]][0]
            #print "Adding", fontname, "to", catname
            self.toggle_font_in_category(fontname, catname)
            self.update_category_buttons(fontname)
        self.treeView.grab_focus()

    # Update the View Categories combobox:
    def update_cats_menu(self):
        if self.combo_connect_id:
            self.view_cat_combo.handler_block(self.combo_connect_id)

        self.view_cat_combo.get_model().clear()
        self.view_cat_combo.append_text("All fonts")
        self.view_cat_combo.append_text("All in categories")
        self.view_cat_combo.append_text("All uncategorized")

        for btn in self.category_buttons:
            catname = btn.get_name()
            item = gtk.MenuItem(catname)
            self.view_cat_combo.append_text(catname)

        self.view_cat_combo.set_active(0)

        if self.combo_connect_id:
            self.view_cat_combo.handler_unblock(self.combo_connect_id)

    # How to get the active text from a combobox:
    def cur_category(self):
        model = self.view_cat_combo.get_model()
        active = self.view_cat_combo.get_active()
        if active < 0:
            return None
        return model[active][0]

    def combochanged(self, widget):
        curcat = self.cur_category()
        if curcat:
            self.update_font_list(curcat)

    def update_font_list(self, catname = "All fonts"):
        # figure out which buttons are toggled:
        # categories = []
        # for btn in self.category_buttons:
        #     if btn.get_active():
        #         categories.append(btn.get_name())
        # show_all = (len(categories) == 0)

        special = (catname[0:3] == "All")
        if special:
            show_all = (catname == "All fonts")
            show_all_in_cats = (catname == "All in categories")
            show_all_not_in_cats = (catname == "All uncategorized")
        # if show_all or show_all_in_cats:
        #     for catbtn in self.category_buttons:
        #         catbtn.set_active(show_all_in_cats)

        # Create or clear the list store:
        self.store.clear()

        for ff in self.all_families:
            fname = ff.get_name()

            # Else not a special case. Just check for cat membership:
            if not special:
                if self.is_font_in_category(fname, catname):
                    self.store.append([fname])
                continue

            if show_all:
                self.store.append([fname])
                continue

            if show_all_in_cats:
                for catbtn in self.category_buttons:
                    if self.is_font_in_category(fname, catbtn.get_name()):
                        self.store.append([fname])
                        break

            if show_all_not_in_cats:
                is_in_cat = False
                for catbtn in self.category_buttons:
                    if self.is_font_in_category(fname, catbtn.get_name()):
                        is_in_cat = True
                        break
                if not is_in_cat:
                    self.store.append([fname])
                continue

        # Reset all the button colors, since nothing is selected now
        # (eventually might be nice to retain the old selection,
        # if it's still in the list):
        for btn in self.category_buttons:
            self.change_button_color(btn, False)

    #
    # Lines in the category file look like:
    # catname: font, font, font ...
    #
    def read_category_file(self) :
        try:
            from win32com.shell import shellcon, shell
            homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        except ImportError:
            homedir = os.getenv("HOME")

        self.cat_file_name = os.path.join(homedir, ".config", "fontasia",
                                          "fontasia.conf")

        filename = self.cat_file_name
        if not os.access(filename, os.R_OK):
            filename = "/etc/xdg/fontasia/defaults"
        try:
            catfp = open(filename, "r")
            while 1:
                line = catfp.readline()
                if not line: break
                line = line.strip()
                if line[0] == '#':     # Skip comments
                    continue

                if line[0:4] == "set ":
                    varval = line[4:].strip().split("=")
                    if varval[0] == "string":
                        self.preview.set_text(varval[1].strip())
                        continue
                    if varval[0] == "fontsize":
                        self.fontsize = int(varval[1])
                        self.sizespin.set_value(self.fontsize)
                        continue
                    if varval[0] == "fancy_list":
                        self.fancy_list = (varval[1] == "True")
                        self.fancy_btn.set_active(self.fancy_list)
                        self.toggle_fancy_list(self.fancy_list)
                        continue
                    if varval[0] == "win_width":
                        self.win_width = int(varval[1])
                        continue
                    if varval[0] == "win_height":
                        self.win_height = int(varval[1])
                        continue
                    if varval[0] == "preview_height":
                        self.preview_height = int(varval[1])
                        continue
                    if varval[0] == "list_width":
                        self.list_width = int(varval[1])
                        continue

                    # Arguably should save any other values
                    # for writing back to the file even though
                    # we don't understand any others
                    else:
                        print "Skipping unknown setting", varval[0]
                        continue

                colon = line.find(":")
                if colon < 0:
                    print "Didn't understand line", line,
                    continue
                catname = line[0:colon].strip()
                self.add_category(catname)
                line = line[colon+1:].strip()
                fonts = line.split(",")
                for font in fonts:
                    font = font.strip()
                    self.toggle_font_in_category(font, catname)
            catfp.close()
            self.update_cats_menu()

        except IOError:
            print "No fontasia conf file yet -- Welcome to fontasia!"

            # Set up a couple of default categories with likely fonts
            self.add_category('monospace')
            self.toggle_font_in_category('Courier 10 Pitch', 'monospace')
            self.toggle_font_in_category('DejaVu Sans Mono', 'monospace')
            self.toggle_font_in_category('FreeMono', 'monospace')
            self.toggle_font_in_category('Monospace', 'monospace')
            self.toggle_font_in_category('Liberation Mono', 'monospace')
            self.toggle_font_in_category('Nimbus Mono L', 'monospace')
            self.add_category('script')
            self.toggle_font_in_category('Purisa', 'script')
            self.toggle_font_in_category('URW Chancery L', 'script')

            return

    def write_category_file(self):
        catdir = os.path.dirname(self.cat_file_name)
        if not os.path.exists(catdir):
            os.mkdir(catdir)
        catfp = open(self.cat_file_name, "w")
        txt = self.preview.get_text()
        if txt != self.DEFAULT_TEXT:
            try:
                print >>catfp, "set string=" + txt
            except:
                print "Problem saving the string -- reverting to default string"

        fontsize = self.sizespin.get_value()
        if fontsize != self.DEFAULT_FONT_SIZE:
            print >>catfp, "set fontsize=" + str(int(fontsize))

        # Get the current sizes for the list and the preview
        alloc = self.get_allocation()
        print >>catfp, "set win_width=" + str(alloc.width)
        print >>catfp, "set win_height=" + str(alloc.height)
        alloc = self.sw.get_allocation()
        print >>catfp, "set list_width=" + str(alloc.width)
        alloc = self.preview.get_allocation()
        print >>catfp, "set preview_height=" + str(alloc.height)

        if not self.fancy_list:
            print >>catfp, "set fancy_list=False"

        for i in range(0, len(self.category_buttons)):
            catname = self.category_buttons[i].get_name()
            print >>catfp, catname + ":", ', '.join(self.category_fontlists[i])
        catfp.close()
        print "Saved to", self.cat_file_name

    def new_cat_entry_changed(self, entry, btn):
        btn.set_sensitive(entry.get_text_length() > 0)

    def category_exists(self, catname):
        for btn in self.category_buttons:
            if btn.get_name() == catname:
                return True
        return False

    def add_category(self, newcat, entry=None):
        if entry:
            newcat = entry.get_text()

        # Make sure we don't already have this category:
        if (self.category_exists(newcat)):
            return

        btn = gtk.Button(newcat)  # was togglebutton
        btn.set_name(newcat)
        self.buttonbox.addButton(btn)
        btn.connect("clicked", self.toggle_cur_font_in_cat, newcat);
        btn.show()

        self.category_buttons.append(btn)
        self.category_fontlists.append([])
        self.update_cats_menu()

        # If any fonts are selected, most likely the user wants them
        # added to the new category.
        self.toggle_cur_font_in_cat(None, newcat)

        if (entry):
            entry.set_text("")

    #
    # Callback for the main toggle buttons down the right half of the window.
    #
    #def category_toggle(self, widget, catname):
    #    self.update_font_list()

    def change_button_color(self, btn, yesno):
        if self.oldcolors is None:
            self.oldcolors = btn.get_modifier_style().bg
        if self.highlightcolor is None:
            self.highlightcolor = gtk.gdk.Color(0, 65535, 0)
        if yesno:
            btn.modify_bg(gtk.STATE_NORMAL, self.highlightcolor)
            btn.modify_bg(gtk.STATE_ACTIVE, self.highlightcolor)
            btn.modify_bg(gtk.STATE_PRELIGHT, self.highlightcolor)
            btn.modify_bg(gtk.STATE_SELECTED, self.highlightcolor)
        else:
            btn.modify_bg(gtk.STATE_NORMAL, self.oldcolors[gtk.STATE_NORMAL])
            btn.modify_bg(gtk.STATE_ACTIVE, self.oldcolors[gtk.STATE_ACTIVE])
            btn.modify_bg(gtk.STATE_PRELIGHT,
                          self.oldcolors[gtk.STATE_PRELIGHT])
            btn.modify_bg(gtk.STATE_SELECTED,
                          self.oldcolors[gtk.STATE_SELECTED])

    def update_category_buttons(self, fontname):
        for i in range(0, len(self.category_buttons)):
            if fontname in self.category_fontlists[i]:
                self.change_button_color(self.category_buttons[i], True)
                # Can't call set_active because that invokes the
                # callback which recursively calls this function.
                #self.category_buttons[i].set_active(True)
            else:
                self.change_button_color(self.category_buttons[i], False)
                #self.category_buttons[i].set_active(False)

    def current_font(self):
        selection = self.treeView.get_selection()
        model, item = selection.get_selected_rows()
        if not item:
            return None
        # Only render the first font.
        return model[item[0][0]][0]

    def render_font(self, widget):
        # Heroic efforts to keep font changes in the Entry from
        # making the whole window resize every time.
        # GTK offers no way to say "make the damn entry stay the same size."
        #self.allow_grow = False
        #self.set_property("allow-grow", False)
        alloc = self.preview.get_allocation()
        if alloc.width > 1 and alloc.height > 1:
            self.preview.set_size_request(alloc.width, alloc.height)

        fontname = self.current_font()
        size = int(self.sizespin.get_value()) * pango.SCALE

        fontdesc = pango.FontDescription(fontname)
        fontdesc.set_size(size)
        if self.bold_btn.get_active():
            fontdesc.set_weight(pango.WEIGHT_BOLD)
        else:
            fontdesc.set_weight(pango.WEIGHT_NORMAL)
        if self.italic_btn.get_active():
            fontdesc.set_style(pango.STYLE_ITALIC)
        else:
            fontdesc.set_style(pango.STYLE_NORMAL)

        self.preview.modify_font(fontdesc)

        self.update_category_buttons(fontname)

        # Now that we're done changing things,
        # allow resizing from the user again:
        # Unfortunately this is still too early: the entry still resizes!
        # So for now, live with the user not being able to resize smaller.
        #self.preview.set_size_request(-1, -1)

    def show_all_categories(self, widget):
        for btn in self.category_buttons:
            btn.set_active(False)
        self.update_font_list()

def python_fu_fontasia():
    fontwin = FontApp()

    # fontwin.connect("destroy", gtk.main_quit)
    # gtk.main()

    while not fontwin.quit:
        gtk.main_iteration()

    pdb.gimp_context_set_font(fontwin.current_font())

if __name__ == '__main__':
    import sys
    # Are we being run as a GIMP plug-in?
    if sys.argv[0].endswith("gimp"):
        from gimpfu import *

        register(
            "python_fu_fontasia",
            "An alternate font chooser.",
            "An alternate font chooser.",
            "Akkana Peck",
            "Akkana Peck",
            "2016",
            "Fontasia...",
            "",
            [
                # No arguments
            ],
            [],
            python_fu_fontasia,
            menu = "<Image>/Windows/"
        )

        # Call GIMP's main loop, which will call python_fu_fontasia
        # and handle cleaning up afterward.
        main()
    else:
        fontwin = FontApp()
        while not fontwin.quit:
            gtk.main_iteration()
        # Trust that the FontApp has already saved new categories, etc.
        sys.exit(0)
