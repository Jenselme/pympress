#!/usr/bin/env python3
#
#       pympress
#
#       Copyright 2009, 2010 Thomas Jost <thomas.jost@gmail.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import os.path
import sys

from gi.repository import Gtk

#FIXME: line under (seems deprecated)
from gi.repository import Gdk

import pympress.document

if __name__ == '__main__':
    Gdk.threads_init()

    # PDF file to open
    name = None
    if len(sys.argv) > 1:
        name = os.path.abspath(sys.argv[1])

        # Check if the path is valid
        if not os.path.exists(name):
            msg="""Could not find the file "%s".""" % name
            dialog = Gtk.MessageDialog(type=Gtk.MESSAGE_ERROR, buttons=Gtk.BUTTONS_OK, message_format=msg)
            dialog.set_position(Gtk.WindowPosition.CENTER)
            dialog.run()
            sys.exit(1)

    else:
        # Use a GTK file dialog to choose file
        dialog = Gtk.FileChooserDialog("Open...", None,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_position(Gtk.WindowPosition.CENTER)

        filter = Gtk.FileFilter()
        filter.set_name("PDF files")
        filter.add_mime_type("application/pdf")
        filter.add_pattern("*.pdf")
        dialog.add_filter(filter)

        filter = Gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name =  dialog.get_filename()
        elif response != Gtk.ResponseType.CANCEL:
            raise ValueError("Invalid response")

        dialog.destroy()

    if name is None:
        # Use a GTK dialog to tell we need a file
        msg="""No file selected!\n\nYou can specify the PDF file to open on the command line if you don't want to use the "Open File" dialog."""
        dialog = Gtk.MessageDialog(type=Gtk.MESSAGE_ERROR, buttons=Gtk.BUTTONS_OK, message_format=msg)
        dialog.set_position(Gtk.WIN_POS_CENTER)
        dialog.run()
        sys.exit(1)

    # Really open the PDF file
    pympress.document.Document("file://" + name)
