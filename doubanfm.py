#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, thread
import glib, gobject
import pygst
pygst.require("0.10")
import gst
import json,urllib2
from select import select

class DoubanFM_CLI:

    def __init__(self, channel):
        self.player = gst.element_factory_make("playbin", "player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        self.ch = 'http://douban.fm/j/mine/playlist?channel='+channel

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.playmode = False
        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.playmode = False

    def start(self):
        rets = json.loads(urllib2.urlopen(self.ch).read())
        for r in rets['song']:
            song_uri = r['url']
            self.playmode = True
            print u'正在播放： '+r['title']+u'     歌手： '+r['artist']
            self.player.set_property("uri", song_uri)
            self.player.set_state(gst.STATE_PLAYING)
            while self.playmode:
                rlist, _, _ = select([sys.stdin], [], [], 1)
                if rlist:
                    s = sys.stdin.readline()
                    if s[0] == 'n':
                        self.player.set_state(gst.STATE_NULL)
                        self.playmode = False
                        break 
        loop.quit()
        

channel_info = u'''
    1  华语兆赫
    2  欧美兆赫
    3  70兆赫
    4  80兆赫
    5  90兆赫
    6  粤语兆赫
'''
print channel_info    
c = raw_input('请输入您想听的频道数字:')
doubanfm = DoubanFM_CLI(c)
print u'如需跳过歌曲请输入n'
while 1:
    thread.start_new_thread(doubanfm.start, ())
    gobject.threads_init()
    loop = glib.MainLoop()
    loop.run()


