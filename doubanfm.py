#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, thread, glib, gobject, re
import pickle, ConfigParser
import pygst
pygst.require("0.10")
import gst, json, urllib, urllib2, httplib, contextlib, random, binascii
from select import select
from Cookie import SimpleCookie
from contextlib import closing
import douban

class DoubanFM_CLI:
    def __init__(self, channel):
        config = ConfigParser.SafeConfigParser({'interval': '0'})
        config.read('doubanfm.config')
        self.delay_after_every_song = config.getfloat('DEFAULT', 'interval')
        self.skip_mode = False
        self.user = None
        self.username = ''
        self.channel = channel
        if channel == '0' or channel == '-3':
            self.private = True
        else:
            self.private = False
        self.player = gst.element_factory_make("playbin", "player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        self.ch = 'http://douban.fm/j/mine/playlist?type=p&sid=&channel='+channel

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

    def get_songlist(self):
        if self.user:
            self.songlist = self.user.playlist()
        elif self.private:
            self.user = douban.PrivateFM(self.channel)
            self.songlist = self.user.playlist()
        else:
            self.songlist = json.loads(urllib.urlopen(self.ch).read())['song']

    def control(self,r):
        rlist, _, _ = select([sys.stdin], [], [], 1)
        if rlist:
            s = sys.stdin.readline()
            if s[0] == 'n':
                print '下一首...'
                self.skip_mode = True
                return 'next'
            elif s[0] == 'f' and self.private:
                print '正在加心...'
                self.user.fav_song(r['sid'], r['aid'])
                print "加心成功:)"
                return 'fav'
            elif s[0] == 'd' and self.private:
                print '不再收听...'
                self.songlist = self.user.del_song(r['sid'], r['aid'])
                print "删歌成功:)"
                return 'del'

    def start(self):
        self.get_songlist()
        is_first_song = True
        for r in self.songlist:
            song_uri = r['url']
            self.playmode = True

            if not is_first_song and not self.skip_mode:
                if self.delay_after_every_song > 0:
                    print '-'
                    time.sleep(self.delay_after_every_song)
            self.skip_mode = False
            is_first_song = False

            print u'正在播放： '+r['title']+u'     歌手： '+r['artist'],
            if int(r['like']) == 1:
                print u'    ♥'
            else:
                print

            self.player.set_property("uri", song_uri) # when ads, flv, warning print
            self.player.set_state(gst.STATE_PLAYING)
            while self.playmode:
                c = self.control(r)
                if c == 'next' or c == 'del':
                    self.player.set_state(gst.STATE_NULL)
                    self.playmode = False
                    break
        if loop is not None:
            loop.quit()


class Channel:

    def __init__(self):
        cid = "101" # why cid is 101 ?
        self.url = "http://douban.fm/j/explore/channel_detail?channel_id=" + cid
        self.init_info()

    def init_info(self):
        cache = douban.Cache()
        if cache.has('channel'):
            self.info = cache.get('channel')
        else:
            self.info = {
                    0: "私人",
                    -3: "红心"
                }
            self.get_id_and_name()
            cache.set('channel', self.info)

    def get_id_and_name(self):
        print 'Fetching channel list ...'
        # this var should name to text or string or something
        self.html = urllib2.urlopen(self.url).read()
        chls = json.loads(self.html)["data"]["channel"]["creator"]["chls"]
        for chl in chls:
            id = chl["id"]
            name = chl["name"]
            self.info[id] = name

    def show(self):
        print u'频道列表：'
        for i in sorted(self.info.iterkeys()):
            print("%8s %s" % (i, self.info[i]))

def main():
    print u'豆瓣电台'
    Channel().show()
    c = raw_input('请输入您想听的频道数字:')
    print u"\r\n\t跳过输入n，加心输入f，删歌输入d\r\n"
    doubanfm = DoubanFM_CLI(c)
    while 1:
        # doubanfm.start()
        # break
        thread.start_new_thread(doubanfm.start, ())
        gobject.threads_init()
        loop = glib.MainLoop()
        loop.run()


if __name__ == "__main__":
    loop = None
    try:
        main()
    except KeyboardInterrupt:
        print
