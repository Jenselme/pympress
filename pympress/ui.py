#       ui.py
#
#       Copyright 2010 Thomas Jost <thomas.jost@gmail.com>
#       Copyright 2014 Julien Enselme <jujens@jujens.eu>
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
:mod:`pympress.ui` -- GUI management
------------------------------------

This module contains the whole graphical user interface of pympress, which is
made of two separate windows: the Content window, which displays only the
current page in full size, and the Presenter window, which displays both the
current and the next page, as well as a time counter and a clock.

Both windows are managed by the :class:`~pympress.ui.UI` class.
"""

import time

import pkg_resources

from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import GLib, GdkPixbuf
from gi.repository import Gdk

try:
    from pympress import util
except ImportError:
    import util

#: "Regular" PDF file (without notes)
PDF_REGULAR = 0
#: Content page (left side) of a PDF file with notes
PDF_CONTENT_PAGE = 1
#: Notes page (right side) of a PDF file with notes
PDF_NOTES_PAGE = 2


class UI:
    """Pympress GUI management."""

    #: Content window, as a :class:`Gtk.Window` instance.
    c_win = Gtk.Window(Gtk.WindowType.TOPLEVEL)
    #: :class:`~Gtk.AspectFrame` for the Content window.
    c_frame = Gtk.AspectFrame(ratio=4./3., obey_child=False)
    #: :class:`~Gtk.DrawingArea` for the Content window.
    c_da = Gtk.DrawingArea()

    #: :class:`~Gtk.AspectFrame` for the current slide in the Presenter window.
    p_frame_cur = Gtk.AspectFrame(yalign=1, ratio=4./3., obey_child=False)
    #: :class:`~Gtk.DrawingArea` for the current slide in the Presenter window.
    p_da_cur = Gtk.DrawingArea()
    #: Slide counter :class:`~Gtk.Label` for the current slide.
    label_cur = Gtk.Label()
    #: :class:`~Gtk.EventBox` associated with the slide counter label in the Presenter window.
    eb_cur = Gtk.EventBox()
    #: :class:`~Gtk.Entry` used to switch to another slide by typing its number.
    entry_cur = Gtk.Entry()

    #: :class:`~Gtk.AspectFrame` for the next slide in the Presenter window.
    p_frame_next = Gtk.AspectFrame(yalign=1, ratio=4./3., obey_child=False)
    #: :class:`~Gtk.DrawingArea` for the next slide in the Presenter window.
    p_da_next = Gtk.DrawingArea()
    #: Slide counter :class:`~Gtk.Label` for the next slide.
    label_next = Gtk.Label()

    #: Elapsed time :class:`~Gtk.Label`.
    label_time = Gtk.Label()
    #: Clock :class:`~Gtk.Label`.
    label_clock = Gtk.Label()

    #: Time at which the counter was started.
    start_time = 0
    #: Time elapsed since the beginning of the presentation.
    delta = 0
    #: Timer paused status.
    paused = True

    #: Fullscreen toggle. By default, don't start in fullscreen mode.
    fullscreen = False

    #: Current :class:`~pympress.document.Document` instance.
    doc = None

    #: Whether to use notes mode or not
    notes_mode = False

    def __init__(self, doc):
        """
        :param doc: the current document
        :type  doc: :class:`pympress.document.Document`
        """
        black = Gdk.Color(0, 0, 0)

        # Common to both windows
        icon_list = util.load_icons()

        # Use notes mode by default if the document has notes
        self.notes_mode = doc.has_notes()

        # Content window
        self.c_win.set_title("pympress content")
        self.c_win.set_default_size(1024, 728)
        self.c_win.modify_bg(Gtk.StateFlags.NORMAL, black)
        self.c_win.connect("delete-event", Gtk.main_quit)
        self.c_win.set_icon_list(icon_list)

        self.c_frame.modify_bg(Gtk.StateFlags.NORMAL, black)

        self.c_da.modify_bg(Gtk.StateFlags.NORMAL, black)
        self.c_da.connect("draw", self.on_expose)
        self.c_da.set_name("c_da")

        self.c_frame.add(self.c_da)
        self.c_win.add(self.c_frame)

        self.c_win.add_events(Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.SCROLL_MASK)
        self.c_win.connect("key-press-event", self.on_navigation)
        self.c_win.connect("scroll-event", self.on_navigation)

        # Presenter window
        p_win = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        p_win.set_title("pympress presenter")
        p_win.set_default_size(1024, 728)
        p_win.set_position(Gtk.WindowPosition.CENTER)
        p_win.connect("delete-event", Gtk.main_quit)
        p_win.set_icon_list(icon_list)

        # Put Menu and Table in VBox
        bigvbox = Gtk.VBox(False, 2)
        p_win.add(bigvbox)

        # UI Manager for menu
        ui_manager = Gtk.UIManager()

        # UI description
        ui_desc = '''
        <menubar name="MenuBar">
          <menu action="File">
            <menuitem action="Quit"/>
          </menu>
          <menu action="Presentation">
            <menuitem action="Pause timer"/>
            <menuitem action="Reset timer"/>
            <menuitem action="Fullscreen"/>
            <menuitem action="Notes mode"/>
          </menu>
          <menu action="Help">
            <menuitem action="About"/>
          </menu>
        </menubar>'''
        ui_manager.add_ui_from_string(ui_desc)

        # Accelerator group
        accel_group = ui_manager.get_accel_group()
        p_win.add_accel_group(accel_group)

        # Action group
        action_group = Gtk.ActionGroup("MenuBar")
        # Name, stock id, label, accelerator, tooltip, action [, is_active]
        action_group.add_actions([
            ("File", None, "_File"),
            ("Presentation", None, "_Presentation"),
            ("Help", None, "_Help"),

            ("Quit", Gtk.STOCK_QUIT, "_Quit", "q", None, Gtk.main_quit),
            ("Reset timer", None, "_Reset timer", "r", None, self.reset_timer),
            ("About", None, "_About", None, None, self.menu_about),
        ])
        action_group.add_toggle_actions([
            ("Pause timer", None, "_Pause timer", "p", None, self.switch_pause, True),
            ("Fullscreen", None, "_Fullscreen", "f", None, self.switch_fullscreen, False),
            ("Notes mode", None, "_Note mode", "n", None, self.switch_mode, self.notes_mode),
        ])
        ui_manager.insert_action_group(action_group)

        # Add menu bar to the window
        menubar = ui_manager.get_widget('/MenuBar')
        h = ui_manager.get_widget('/MenuBar/Help')
        h.set_right_justified(True)
        bigvbox.pack_start(menubar, False, False, 0)

        # A little space around everything in the window
        align = Gtk.Alignment()
        align.set(0.5, 0.5, 1, 1)
        align.set_padding(20, 20, 20, 20)

        # Table
        table = Gtk.Table(2, 10, False)
        table.set_col_spacings(25)
        table.set_row_spacings(25)
        align.add(table)
        bigvbox.pack_end(align, False, False, 0)

        # "Current slide" frame
        frame = Gtk.Frame()
        frame.set_label("Current slide")
        table.attach(frame, 0, 6, 0, 1)
        align = Gtk.Alignment()
        align.set(0.5, 0.5, 1, 1)
        align.set_padding(0, 0, 12, 0)
        frame.add(align)
        vbox = Gtk.VBox()
        align.add(vbox)
        vbox.pack_start(self.p_frame_cur, False, False, 0)
        self.eb_cur.set_visible_window(False)
        self.eb_cur.connect("event", self.on_label_event)
        vbox.pack_start(self.eb_cur, False, False, 10)
        self.p_da_cur.modify_bg(Gtk.StateFlags.NORMAL, black)
        self.p_da_cur.connect("draw", self.on_expose)
        self.p_da_cur.set_name("p_da_cur")
        self.p_da_cur.set_size_request(0, 400)  #FIXME: size of preview is fixed
        self.p_frame_cur.add(self.p_da_cur)

        # "Current slide" label and entry
        self.label_cur.set_justify(Gtk.Justification.CENTER)
        self.label_cur.set_use_markup(True)
        self.eb_cur.add(self.label_cur)
        self.entry_cur.set_alignment(0.5)
        self.entry_cur.modify_font(Pango.FontDescription('36'))

        # "Next slide" frame
        frame = Gtk.Frame()
        frame.set_label("Next slide")
        table.attach(frame, 6, 10, 0, 1)
        align = Gtk.Alignment()
        align.set(0.5, 0.5, 1, 1)
        align.set_padding(0, 0, 12, 0)
        frame.add(align)
        vbox = Gtk.VBox()
        align.add(vbox)
        self.label_next.set_justify(Gtk.Justification.CENTER)
        self.label_next.set_use_markup(True)
        vbox.pack_end(self.label_next, False, False, 10)
        vbox.pack_end(self.p_frame_next, False, False, 0)
        self.p_da_next.modify_bg(Gtk.StateFlags.NORMAL, black)
        self.p_da_next.connect("draw", self.on_expose)
        self.p_da_next.set_name("p_da_next")
        self.p_da_next.set_size_request(0, 290)  #FIXME: size of preview is fixed
        self.p_frame_next.add(self.p_da_next)

        # "Time elapsed" frame
        frame = Gtk.Frame()
        frame.set_label("Time elapsed")
        table.attach(frame, 0, 5, 1, 2, yoptions=Gtk.AttachOptions.FILL)
        align = Gtk.Alignment()
        align.set(0.5, 0.5, 1, 1)
        align.set_padding(10, 10, 12, 0)
        frame.add(align)
        self.label_time.set_justify(Gtk.Justification.CENTER)
        self.label_time.set_use_markup(True)
        align.add(self.label_time)

        # "Clock" frame
        frame = Gtk.Frame()
        frame.set_label("Clock")
        table.attach(frame, 5, 10, 1, 2, yoptions=Gtk.AttachOptions.FILL)
        align = Gtk.Alignment()
        align.set(0.5, 0.5, 1, 1)
        align.set_padding(10, 10, 12, 0)
        frame.add(align)
        self.label_clock.set_justify(Gtk.Justification.CENTER)
        self.label_clock.set_use_markup(True)
        align.add(self.label_clock)

        p_win.connect("destroy", Gtk.main_quit)
        p_win.show_all()


        # Add events
        p_win.add_events(Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.SCROLL_MASK)
        p_win.connect("key-press-event", self.on_navigation)
        p_win.connect("scroll-event", self.on_navigation)

        # Hyperlinks if available
        if util.poppler_links_available():
            self.c_da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                                    Gdk.EventMask.POINTER_MOTION_MASK)
            self.c_da.connect("button-press-event", self.on_link)
            self.c_da.connect("motion-notify-event", self.on_link)

            self.p_da_cur.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                                        Gdk.EventMask.POINTER_MOTION_MASK)
            self.p_da_cur.connect("button-press-event", self.on_link)
            self.p_da_cur.connect("motion-notify-event", self.on_link)

            self.p_da_next.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                                        Gdk.EventMask.POINTER_MOTION_MASK)
            self.p_da_next.connect("button-press-event", self.on_link)
            self.p_da_next.connect("motion-notify-event", self.on_link)

        # Setup timer
        GLib.timeout_add(250, self.update_time)

        # Document
        self.doc = doc

        # Show all windows
        self.c_win.show_all()
        p_win.show_all()

    def run(self):
        """Run the GTK main loop."""
        Gtk.main()

    def menu_about(self, widget=None, event=None):
        """Display the "About pympress" dialog."""
        about = Gtk.AboutDialog()
        about.set_program_name("pympress")
        about.set_version(pympress.__version__)
        about.set_copyright("(c) 2009, 2010 Thomas Jost")
        about.set_comments("""pympress is a little PDF reader written in Python
                            using Poppler for PDF rendering and GTK for the GUI.""")
        about.set_website("http://www.pympress.org/")
        try:
            req = pkg_resources.Requirement.parse("pympress")
            icon_fn = pkg_resources.resource_filename(req, "share/pixmaps/pympress-128.png")
            about.set_logo(Gdk.pixbuf_new_from_file(icon_fn))
        except Exception as e:
            print(e)
        about.run()
        about.destroy()

    def on_page_change(self, unpause=True):
        """
        Switch to another page and display it.

        This is a kind of event which is supposed to be called only from the
        :class:`~pympress.document.Document` class.

        :param unpause: ``True`` if the page change should unpause the timer,
           ``False`` otherwise
        :type  unpause: boolean
        """
        page_cur = self.doc.current_page()
        page_next = self.doc.next_page()

        # Aspect ratios
        pr = page_cur.get_aspect_ratio(self.notes_mode)
        self.c_frame.set_property("ratio", pr)
        self.p_frame_cur.set_property("ratio", pr)

        if page_next is not None:
            pr = page_next.get_aspect_ratio(self.notes_mode)
            self.p_frame_next.set_property("ratio", pr)

        # Start counter if needed
        if unpause:
            self.paused = False
            if self.start_time == 0:
                self.start_time = time.time()

        # Update display
        self.update_page_numbers()

        # Don't queue draw event but draw directly (faster)
        self.on_expose(self.c_da)
        self.on_expose(self.p_da_cur)
        self.on_expose(self.p_da_next)

        # Prerender the 4 next pages and the 2 previous ones
        cur = page_cur.number()
        page_max = min(self.doc.pages_number(), cur + 5)
        page_min = max(0, cur - 2)

    def on_expose(self, widget, event=None):
        """
        Manage expose events for both windows.

        This callback may be called either directly on a page change or as an
        event handler by GTK. In both cases, it determines which widget needs to
        be updated, and updates it.

        :param widget: the widget to update
        :type  widget: :class:`Gtk.Widget`
        :param event: the GTK event (or ``None`` if called directly)
        :type  event: :class:`Gdk.Event`
        """

        if widget in [self.c_da, self.p_da_cur]:
            # Current page
            page = self.doc.current_page()
        else:
            # Next page: it can be None
            page = self.doc.next_page()
            parent = widget.get_parent()
            if page is None:
                widget.hide()
                parent.set_shadow_type(Gtk.ShadowType.NONE)
                return
            else:
                widget.show_all()
                parent.set_shadow_type(Gtk.ShadowType.IN)

        self.render_page(page, widget,)
        window = widget.get_window()
        ww, wh = window.get_width(), window.get_height()
        pb = GdkPixbuf.Pixbuf()
        pb.new(GdkPixbuf.Colorspace.RGB, False, 8, ww, wh)
        Gdk.pixbuf_get_from_window(window, 0, 0, ww, wh)

    def on_navigation(self, widget, event):
        """
        Manage events as mouse scroll or clicks for both windows.

        :param widget: the widget in which the event occured (ignored)
        :type  widget: :class:`Gtk.Widget`
        :param event: the event that occured
        :type  event: :class:`Gdk.Event`
        """
        if event.type == Gdk.EventType.KEY_PRESS:
            name = Gdk.keyval_name(event.keyval)

            if name in ["Right", "Down", "Page_Down", "space"]:
                self.doc.goto_next()
            elif name in ["Left", "Up", "Page_Up", "BackSpace"]:
                self.doc.goto_prev()
            elif name == 'Home':
                self.doc.goto_home()
            elif name == 'End':
                self.doc.goto_end()
            elif (name.upper() in ["F", "F11"]) \
                or (name == "Return" and event.state & Gdk.ModifierType.MOD1_MASK) \
                or (name.upper() == "L" and event.state & Gdk.ModifierType.CONTROL_MASK):
                self.switch_fullscreen()
            elif name.upper() == "Q":
                Gtk.main_quit()
            elif name == "Pause":
                self.switch_pause()
            elif name.upper() == "R":
                self.reset_timer()

            # Some key events are already handled by toggle actions in the
            # presenter window, so we must handle them in the content window
            # only to prevent them from double-firing
            elif widget is self.c_win:
                if name.upper() == "P":
                    self.switch_pause()
                elif name.upper() == "N":
                    self.switch_mode()

        elif event.type == Gdk.EventScroll:
            if event.direction in [Gdk.ScrollDirection.RIGHT, Gdk.ScrollDirection.LEFT]:
                self.doc.goto_next()
            else:
                self.doc.goto_prev()

        else:
            print("Unknown event %s" % event.type)

    def on_link(self, widget, event):
        """
        Manage events related to hyperlinks.

        :param widget: the widget in which the event occured
        :type  widget: :class:`Gtk.Widget`
        :param event: the event that occured
        :type  event: :class:`Gdk.Event`
        """

        # Where did the event occur?
        if widget is self.p_da_next:
            page = self.doc.next_page()
            if page is None:
                return
        else:
            page = self.doc.current_page()

        # Normalize event coordinates and get link
        x, y = event.get_coords()
        window = widget.get_window()
        ww, wh = ww, wh = window.get_width(), window.get_height()
        x2, y2 = x/ww, y/wh
        link = page.get_link_at(x2, y2)

        # Event type?
        if event.type == Gdk.EventType.BUTTON_PRESS:
            if link is not None:
                dest = link.get_destination()
                self.doc.goto(dest)

        elif event.type == Gdk.EventType.MOTION_NOTIFY:
            if link is not None:
                cursor = Gdk.Cursor(Gdk.HAND2)
                window.set_cursor(cursor)
            else:
                window.set_cursor(None)

        else:
            print("Unknown event %s" % event.type)

    def on_label_event(self, widget, event):
        """
        Manage events on the current slide label/entry.

        This function replaces the label with an entry when clicked, replaces
        the entry with a label when needed, etc. The nasty stuff it does is an
        ancient kind of dark magic that should be avoided as much as possible...

        :param widget: the widget in which the event occured
        :type  widget: :class:`Gtk.Widget`
        :param event: the event that occured
        :type  event: :class:`Gdk.Event`
        """

        widget = self.eb_cur.get_child()

        # Click on the label
        if widget is self.label_cur and event.type == Gdk.EventType.BUTTON_PRESS:
            # Set entry text
            self.entry_cur.set_text("%d/%d" % (self.doc.current_page().number()+1,
                                        self.doc.pages_number()))
            self.entry_cur.select_region(0, -1)

            # Replace label with entry
            self.eb_cur.remove(self.label_cur)
            self.eb_cur.add(self.entry_cur)
            self.entry_cur.show()
            self.entry_cur.grab_focus()

        # Key pressed in the entry
        elif widget is self.entry_cur and event.type == Gdk.EventType.KEY_RELEASE:
            name = Gdk.keyval_name(event.keyval)

            # Return key --> restore label and goto page
            if name == "Return" or name == "KP_Return" or name == "KP_Enter":
                text = self.entry_cur.get_text()
                self.restore_current_label()

                # Deal with the text
                n = self.doc.current_page().number() + 1
                try:
                    s = text.split('/')[0]
                    n = int(s)
                except ValueError:
                    print("Invalid number: %s" % text)

                n -= 1
                if n != self.doc.current_page().number():
                    if n <= 0:
                        n = 0
                    elif n >= self.doc.pages_number():
                        n = self.doc.pages_number() - 1
                    self.doc.goto(n)

            # Escape key --> just restore the label
            elif name == "Escape":
                self.restore_current_label()

        # Propagate the event further
        return False

    def render_page(self, page, widget):
        """
        Render a page on a widget.

        This function takes care of properly initializing the widget so that
        everything looks fine in the end. The rendering to a Cairo surface is
        done using the :meth:`pympress.document.Page.render_cairo` method.

        :param page: the page to render
        :type  page: :class:`pympress.document.Page`
        :param widget: the widget on which the page must be rendered
        :type  widget: :class:`Gtk.DrawingArea`
        """

        # Make sure the widget is initialized
        window = widget.get_window()
        if not window:
            return

        # Widget size
        ww, wh = window.get_width(), window.get_height()

        # Manual double buffering (since we use direct drawing instead of
        # calling queue_draw() on the widget)
        rect = Gdk.Rectangle()
        rect.x = 0
        rect.y = 0
        rect.width = ww
        rect.height = wh
        window.begin_paint_rect(rect)

        cr = window.cairo_create()
        page.render_cairo(cr, ww, wh)

        # Blit off-screen buffer to screen
        window.end_paint()

    def restore_current_label(self):
        """
        Make sure that the current page number is displayed in a label and not
        in an entry. If it is an entry, then replace it with the label.
        """
        child = self.eb_cur.get_child()
        if child is not self.label_cur:
            self.eb_cur.remove(child)
            self.eb_cur.add(self.label_cur)

    def update_page_numbers(self):
        """Update the displayed page numbers."""

        text = "<span font='36'>%s</span>"

        cur_nb = self.doc.current_page().number()
        cur = "%d/%d" % (cur_nb + 1, self.doc.pages_number())
        next = "--"
        if cur_nb + 2 <= self.doc.pages_number():
            next = "%d/%d" % (cur_nb + 2, self.doc.pages_number())

        self.label_cur.set_markup(text % cur)
        self.label_next.set_markup(text % next)
        self.restore_current_label()

    def update_time(self):
        """
        Update the timer and clock labels.

        :return: ``True`` (to prevent the timer from stopping)
        :rtype: boolean
        """

        text = "<span font='36'>%s</span>"

        # Current time
        clock = time.strftime("%H:%M:%S")

        # Time elapsed since the beginning of the presentation
        if not self.paused:
            self.delta = time.time() - self.start_time
        elapsed = "%02d:%02d" % (int(self.delta/60), int(self.delta % 60))
        if self.paused:
            elapsed += " (pause)"

        self.label_time.set_markup(text % elapsed)
        self.label_clock.set_markup(text % clock)

        return True

    def switch_pause(self, widget=None, event=None):
        """Switch the timer between paused mode and running (normal) mode."""
        if self.paused:
            self.start_time = time.time() - self.delta
            self.paused = False
        else:
            self.paused = True
        self.update_time()

    def reset_timer(self, widget=None, event=None):
        """Reset the timer."""
        self.start_time = time.time()
        self.update_time()

    def switch_fullscreen(self, widget=None, event=None):
        """
        Switch the Content window to fullscreen (if in normal mode) or to normal
        mode (if fullscreen).
        """
        if self.fullscreen:
            self.c_win.unfullscreen()
            self.fullscreen = False
        else:
            self.c_win.fullscreen()
            self.fullscreen = True

    def switch_mode(self, widget=None, event=None):
        """
        Switch the display mode to "Notes mode" or "Normal mode" (without notes)
        """
        if self.notes_mode:
            self.notes_mode = False
        else:
            self.notes_mode = True

        self.on_page_change(False)
