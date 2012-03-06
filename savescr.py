#!/usr/bin/env python
##
## Copyright (c) 2012 Zhihao Yuan <lichray AT gmail.com>
## All rights reserved.
##
## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions
## are met:
## 1. Redistributions of source code must retain the above copyright
##    notice, this list of conditions and the following disclaimer.
## 2. Redistributions in binary form must reproduce the above copyright
##    notice, this list of conditions and the following disclaimer in the
##    documentation and/or other materials provided with the distribution.
##

# Cairo only supports PNG

SSTITLE   = 'Save the PNG file...'
SSCMD     = 'import -quality 04 -border -frame png:-'
SSCMD_ALT = 'import -quality 04 png:-'
CMTCOLORS = 'E88390 7FC49D 8A8FB2 7FC9E8 E77FB5 FFF78C'
CMTALPHA  =  0.62

from cStringIO import StringIO
import sys, os
from getopt import getopt
import pygtk
pygtk.require20()
import gtk, cairo

def savescr(cmd):
    orig = os.popen(cmd).read()
    gui = Gui(SSTITLE, StringIO(orig), os.getcwd())
    if gui.saving():
        with open(gui.chooser.get_filename(), 'wb') as f:
            f.write(orig)

class Gui(object):
    def __init__(self, title, fobj, path = None):
        self.chooser = gtk.FileChooserDialog(title,
                action = gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons = (gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        try:
            self.chooser.set_icon(gtk.icon_theme_get_default()
                    .load_icon("camera", 48, gtk.ICON_LOOKUP_FORCE_SVG))
        except: pass
        self.chooser.set_do_overwrite_confirmation(1)
        self.chooser.set_current_folder(path)

        fter = gtk.FileFilter()
        fter.add_mime_type('image/png')
        self.chooser.set_filter(fter)

        self.editor = Editor(fobj, CMTCOLORS, CMTALPHA)
        self.chooser.remove(self.chooser.vbox)
        vpan = gtk.VPaned()
        vpan.add1(self.editor)
        vpan.add2(self.chooser.vbox)
        self.chooser.add(vpan)
        vpan.set_position(self.chooser.get_size()[1] / 2)

    def saving(self):
        self.editor.parent.show_all()
        return self.chooser.run() == gtk.RESPONSE_OK

    def __del__(self):
        self.chooser.destroy()

class Editor(gtk.ScrolledWindow):
    def __init__(self, fobj, palette, alpha = 1.0):
        gtk.ScrolledWindow.__init__(self)

        self.__sfce = cairo.ImageSurface.create_from_png(fobj)

        def expose(area, event):
            ctx = area.window.cairo_create()
            ctx.set_source_surface(self.__sfce, 0, 0)
            ctx.paint()

        self.canvas = gtk.DrawingArea()
        self.canvas.set_size_request(self.__sfce.get_width(),
                                     self.__sfce.get_height())
        self.canvas.connect('expose-event', expose)

        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.add_with_viewport(self.canvas)

        self.canvas.set_events(gtk.gdk.POINTER_MOTION_MASK
                             | gtk.gdk.BUTTON_PRESS_MASK
                             | gtk.gdk.BUTTON_RELEASE_MASK)
        id = self.canvas.connect('motion-notify-event', self.scrollto)
        self.canvas.handler_block(id)
        self.canvas.connect('button-press-event', lambda w, e:
                e.button == 1 and e.type == gtk.gdk.BUTTON_PRESS
                and self.canvas.handler_unblock(id) or self.pressat(e))
        self.canvas.connect('button-release-event', lambda w, e:
                e.button == 1 and e.type == gtk.gdk.BUTTON_RELEASE
                and self.canvas.handler_block(id))
        self.canvas.connect('realize', lambda w:
                w.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR)))

    def pressat(self, event):
        self.__dragfrom = (event.x, event.y)

    def scrollto(self, area, event):
        h, v = self.get_hscrollbar(), self.get_vscrollbar()
        h.set_value(h.get_value() + self.__dragfrom[0] - event.x)
        v.set_value(v.get_value() + self.__dragfrom[1] - event.y)

    def getsurface(self):
        return self.__sfce


if __name__ == '__main__':
    cmd = SSCMD

    for k, v in getopt(sys.argv[1:], 'hn')[0]:
        if k == '-h':
            print '''%s: [options]...
options:
  -n       no window frame
  -h       display this help''' % os.path.basename(sys.argv[0])
            sys.exit(1)
        elif k == '-n':
            cmd = SSCMD_ALT

    savescr(cmd)
