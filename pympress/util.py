#       util.py
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

"""
:mod:`pympress.util` -- various utility functions
-------------------------------------------------
"""

import pkg_resources
import os, os.path, sys
from gi.repository import Poppler

from gi.repository import Gdk
import os


def load_icons():
    """
    Load pympress icons from the pixmaps directory (usually
    :file:`/usr/share/pixmaps` or something similar).

    :return: loaded icons
    :rtype: list of :class:`Gtk.gdk.Pixbuf`
    """

    #FIXME: req = pkg_resources.Requirement.parse("pympress")
    #FIXME: icon_names = pkg_resources.resource_listdir(req, "share/pixmaps")
    icon_names = os.listdir("share/pixmaps")
    icons = []
    for icon_name in icon_names:
        if os.path.splitext(icon_name)[1].lower() != ".png":
            continue
        #FIXME: icon_fn = pkg_resources.resource_filename(req, "share/pixmaps/%s" % icon_name)
        icon_fn = icon_name
        try:
            icon_pixbuf = Gdk.pixbuf_new_from_file(icon_fn)
            icons.append(icon_pixbuf)
        except Exception as e:
            print(e)
    return icons


def poppler_links_available():
    """Check if hyperlinks are supported in python-Poppler.

    :return: ``True`` if python-poppler is recent enough to support hyperlinks,
       ``False`` otherwise
    :rtype: boolean
    """

    try:
        type(Poppler.ActionGotoDest)
    except AttributeError:
        return False
    else:
        return True
