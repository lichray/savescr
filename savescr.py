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

SSTITLE   = 'Save the screenshot'
CMTCOLORS = '#E88390 #7FC49D #8A8FB2 #7FC9E8 #E77FB5 #FFF78C'
CMTALPHA  =  0.62

import sys, os
from getopt import getopt
import pygtk
pygtk.require20()
import gtk, cairo, gobject
import colorsys, mimetypes

def savescr(fobj):
    with fobj:
        gui = Gui(SSTITLE, fobj, os.getcwd())
    if gui.saving(fobj.name):
        gui.editor.saveto(gui.chooser.get_filename())

class Gui(object):
    def __init__(self, title, fobj, path = ''):
        self.chooser = gtk.FileChooserDialog(title,
                action = gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons = (gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        try:
            self.chooser.set_icon(gtk.icon_theme_get_default()
                    .load_icon("camera", 48, gtk.ICON_LOOKUP_FORCE_SVG))
        except: pass
        self.chooser.set_do_overwrite_confirmation(1)
        if path: self.chooser.set_current_folder(path)

        self.editor = Editor(fobj, CMTCOLORS.split(), CMTALPHA)
        self.chooser.remove(self.chooser.vbox)
        vpan = gtk.VPaned()
        vpan.pack1(self.editor, 0, 0)
        vpan.pack2(self.chooser.vbox, 0, 0)
        self.chooser.add(vpan)
        vpan.set_position(self.chooser.get_size()[1] / 2)

    def saving(self, filename = ''):
        self.chooser.set_filename(filename)
        self.editor.parent.show_all()
        return self.chooser.run() == gtk.RESPONSE_OK

    def __del__(self):
        self.chooser.destroy()

class Editor(gtk.HBox):
    class Stroke(list):
        def __init__(self, color = (0.0, 0.0, 0.0)):
            self.color = color

    def __init__(self, fobj, palette, alpha = 1.0):
        gtk.HBox.__init__(self)
        self.set_spacing(5)
        self.__strokes = []
        self.alpha = alpha
        self.linewidth = self.get_screen().get_resolution() / 6

        self.__sfce = cairo.ImageSurface.create_from_png(fobj)
        self.__cursor = [ gtk.gdk.Cursor(self.get_display(),
            gtk.gdk.pixbuf_new_from_xpm_data(xpm), 0, 7)
            for xpm in cursor_xpm ]

        def expose(area, event):
            ctx = area.window.cairo_create()
            ctx.set_source_surface(self.__sfce, 0, 0)
            ctx.paint()
            self.__drawon(ctx)

        self.canvas = gtk.DrawingArea()
        self.canvas.set_size_request(self.__sfce.get_width(),
                                     self.__sfce.get_height())
        self.canvas.connect('expose-event', expose)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(self.canvas)

        self.comment = Comment(palette)
        self.pack_start(self.comment, 0)
        self.pack_start(sw)

        self.comment.connect('reset-event', self.reset)
        self.comment.connect('undo-event', self.undo)

        self.canvas.set_events(gtk.gdk.POINTER_MOTION_MASK
                             | gtk.gdk.BUTTON_PRESS_MASK
                             | gtk.gdk.BUTTON_RELEASE_MASK
                             | gtk.gdk.ENTER_NOTIFY_MASK)
        id = self.canvas.connect('motion-notify-event',
                lambda *args: (self.drawto if self.comment.getcolor()
                    else self.scrollto)(*args), sw)
        self.canvas.handler_block(id)
        self.canvas.connect('button-press-event', lambda w, e:
                self.canvas.handler_unblock(id) or self.pressat(w, e)
                if e.button == 1 and e.type == gtk.gdk.BUTTON_PRESS
                else endbrush(e))
        self.canvas.connect('button-release-event', lambda w, e:
                self.canvas.handler_block(id) or self.redraw()
                or self.setcursor()
                if e.button == 1 and e.type == gtk.gdk.BUTTON_RELEASE
                else None)
        self.canvas.connect('enter-notify-event', lambda w, e:
                self.setcursor())

        def endbrush(event):
            if event.button == 3:
                self.comment.setcolor()
                self.setcursor()

    def setcursor(self, n = None):
        self.canvas.window.set_cursor(self.__cursor
                [(2 if self.comment.getcolor() else 0) if n == None else n])

    def pressat(self, area, event):
        self.__ctx = area.window.cairo_create()
        self.__dragfrom = (event.x, event.y)
        if self.comment.getcolor():
            self.__strokes.append(Editor.Stroke(self.comment.getcolor()))
            self.__strokes[-1].append(self.__dragfrom)
        else:
            self.setcursor(1)

    def scrollto(self, area, event, w):
        h, v = w.get_hscrollbar(), w.get_vscrollbar()
        h.set_value(h.get_value() + self.__dragfrom[0] - event.x)
        v.set_value(v.get_value() + self.__dragfrom[1] - event.y)

    def drawto(self, area, event, w):
        r, g, b = self.comment.getcolor()
        self.__ctx.set_source_rgba(r, g, b, self.alpha)
        self.__ctx.set_line_width(self.linewidth)
        self.__ctx.move_to(self.__strokes[-1][-1][0],
                           self.__strokes[-1][-1][1])
        self.__ctx.line_to(event.x, event.y)
        self.__ctx.stroke()
        self.__strokes[-1].append((event.x, event.y))

    def undo(self, area):
        if self.__strokes:
            self.__strokes.pop()
        self.redraw()

    def reset(self, area):
        self.__strokes = []
        self.redraw()

    def redraw(self):
        self.canvas.emit('expose-event', None)

    def saveto(self, filename):
        self.__drawon(cairo.Context(self.__sfce))
        ft, _ = mimetypes.guess_type(filename)
        if ft == None or ft == 'image/png':
            self.__sfce.write_to_png(filename)
            return
        try:
            import Image
            img = Image.frombuffer("RGBA",
                    (self.__sfce.get_width(), self.__sfce.get_height()),
                    self.__sfce.get_data(), "raw", "BGRA", 0, 1)
            img.convert('RGB').save(filename, quality = 90)
        except:
            import pipes
            fp, _ = os.popen2('convert - ' + pipes.quote(filename))
            self.__sfce.write_to_png(fp)

    def __drawon(self, ctx):
        for s in self.__strokes:
            r, g, b = s.color
            ctx.set_source_rgba(r, g, b, self.alpha)
            ctx.set_line_width(self.linewidth)
            ctx.set_line_join(cairo.LINE_JOIN_BEVEL)
            ctx.move_to(s[0][0], s[0][1])
            for x, y in s[1:]:
                ctx.line_to(x, y)
            ctx.stroke()

class Comment(gtk.Fixed):
    def __init__(self, palette):
        gtk.Fixed.__init__(self)

        pixels = int(1.8 * self.get_screen().get_resolution() / 6)
        buttons = []

        def make_button(type = gtk.Button, *args, **kwargs):
            btn = type(*args, **kwargs)
            btn.set_can_focus(0)
            btn.set_size_request(pixels, pixels)
            btn.set_relief(gtk.RELIEF_NONE)
            self.put(btn, 0, len(self.children()) * pixels)
            return btn

        for c in palette:
            btn = make_button(gtk.ToggleButton, '')
            btn.child.set_markup(u'<span size="xx-large">\u2759</span>')
            rgb = gtk.gdk.Color(c)
            for st in [ gtk.STATE_NORMAL,
                        gtk.STATE_ACTIVE,
                        gtk.STATE_SELECTED ]:
                btn.child.modify_fg(st, rgb)
            btn.color = (rgb.red_float, rgb.green_float, rgb.blue_float)
            h, s, v = colorsys.rgb_to_hsv(*btn.color)
            btn.child.modify_fg(gtk.STATE_PRELIGHT,
                    gtk.gdk.color_from_hsv(h, s, v * 1.1))
            buttons.append(btn)

        for i in range(len(buttons)):
            buttons[i].connect('released', (lambda i = i: lambda w:
                    [ x.set_active(0) for x in buttons[:i] + buttons[i+1:] ]
                    and self.setcolor(buttons[i].color) if w.get_active()
                    else self.setcolor())())

        for i in range(2):
            btn = make_button()
            btn.set_image(gtk.image_new_from_stock(
                    [ gtk.STOCK_UNDO, gtk.STOCK_CLEAR ][i],
                    gtk.ICON_SIZE_BUTTON))
            btn.connect('clicked', (lambda i = i: lambda w:
                    self.emit([ 'undo-event', 'reset-event' ][i]))())

        self.setcolor()

    def setcolor(self, color = None):
        self.__color = color
        if not color:
            for btn in self.children():
                if hasattr(btn, 'set_active'):
                    btn.set_active(0)

    def getcolor(self):
        return self.__color

gobject.type_register(Comment)
gobject.signal_new("reset-event", Comment, gobject.SIGNAL_RUN_FIRST,
        gobject.TYPE_NONE, ())
gobject.signal_new("undo-event", Comment, gobject.SIGNAL_RUN_FIRST,
        gobject.TYPE_NONE, ())

cursor_xpm = [
[
"16 16 3 1",
" 	c None",
".	c #000000",
"+	c #FFFFFF",
"       ..       ",
"   .. .++...    ",
"  .++..++.++.   ",
"  .++..++.++. . ",
"   .++.++.++..+.",
"   .++.++.++.++.",
" .. .+++++++.++.",
".++..++++++++++.",
".+++.+++++++++. ",
" .++++++++++++. ",
"  .+++++++++++. ",
"  .++++++++++.  ",
"   .+++++++++.  ",
"    .+++++++.   ",
"     .++++++.   ",
"     .++++++.   "],
[
"16 16 3 1",
" 	c None",
".	c #000000",
"+	c #FFFFFF",
"                ",
"                ",
"                ",
"                ",
"    .. .. ..    ",
"   .++.++.++..  ",
"   .++++++++.+. ",
"   ..+++++++++. ",
"  .+.+++++++++. ",
"  .+++++++++++. ",
"  .+++++++++++. ",
"  .++++++++++.  ",
"   .+++++++++.  ",
"    .+++++++.   ",
"     .++++++.   ",
"     .++++++.   "],
[
"16 16 3 1",
" 	c None",
".	c #FFFFFF",
"+	c #000000",
"     .+++++.    ",
"    .++...++.   ",
"    .+..++.++.  ",
"   .+.+.+++.+.  ",
"   .+.++....+.  ",
"  .+..+.+++.+.  ",
"  .+.+...+.+.   ",
" .+..+..+..+.   ",
" .+.+...+.+.    ",
".+.++..+..+.    ",
".+.+...+.+.     ",
".+++..+..+.     ",
".+.++++.+.      ",
".+....+++.      ",
".+...++..       ",
".++++..         "],
]

if __name__ == '__main__':
    cmd = 'import'
    opt = { 'quality' : '-quality 04',
            'screen'  : '-screen',
            'frame'   : '-frame -border' }
    arg = 'png:-'
    filename = ''

    for k, v in getopt(sys.argv[1:], 'c:f:hnw')[0]:
        if k == '-h':
            print '''%s: [options]...
Options:
  -c COLORS  set commenting colors
  -f FILE|-  read an image, not screenshot
  -n         do not include window frame
  -w         take image from window
  -h         display this help''' % sys.argv[0]
            sys.exit(1)
        elif k == '-c':
            CMTCOLORS = v
        elif k == '-f':
            filename = v
        elif k == '-w':
            del opt['screen']
        elif k == '-n':
            del opt['frame']

    if filename:
        fp = open(filename) if filename != '-' else sys.stdin
    else:
        fp = os.popen(' '.join([cmd] + opt.values() + [arg]))

    savescr(fp)
