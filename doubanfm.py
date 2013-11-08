#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, thread, glib, gobject
import pickle
import pygst
pygst.require("0.10")
import gst, json, urllib, httplib, contextlib, random, binascii
from select import select
from Cookie import SimpleCookie
from contextlib import closing 
from douban import PrivateFM

class DoubanFM_CLI:
    def __init__(self, channel):
        self.user = None
        self.username = ''
        if channel == '0':
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
            self.get_user_name_pass()
            self.user = PrivateFM(self.username, self.password)
            self.songlist = self.user.playlist()
        else:
            self.songlist = json.loads(urllib.urlopen(self.ch).read())['song']

    def get_user_name_pass(self):
        self.user_name_pass_cache_file_name = 'cache_info'
        info = self.get_user_name_pass_cache()
        if info is None:
            self.get_user_input_name_pass()
            info = {'username': self.username, 'password': self.password}
            self.set_user_name_pass_cache(info)
        else:
            self.username = info['username']
            self.password = info['password']

    def set_user_name_pass_cache(self, info):
        cache_file = open(self.user_name_pass_cache_file_name, 'wb')
        pickle.dump(info, cache_file)
        cache_file.close()

    def get_user_name_pass_cache(self):
        if not os.path.exists(self.user_name_pass_cache_file_name):
            return None
        cache_file = open(self.user_name_pass_cache_file_name, 'rb')
        info = pickle.load(cache_file)
        cache_file.close()
        return info

    def get_user_input_name_pass(self):
        self.username = raw_input("请输入豆瓣登录账户：") 
        import getpass
        self.password = getpass.getpass("请输入豆瓣登录密码：") 

    def control(self,r):
        rlist, _, _ = select([sys.stdin], [], [], 1)
        if rlist:
            s = sys.stdin.readline()
            if s[0] == 'n':
                return 'next'
            elif s[0] == 'f' and self.private:
                self.user.fav_song(r['sid'], r['aid'])
                print "加心成功:)"
                return 'fav'
            elif s[0] == 'd' and self.private:
                self.songlist = self.user.del_song(r['sid'], r['aid'])
                print "删歌成功:)"
                return 'del'

    def start(self):
        self.get_songlist()
        for r in self.songlist:
            song_uri = r['url']
            self.playmode = True
            print u'正在播放： '+r['title']+u'     歌手： '+r['artist']+'    ',
            if r['like']:
                print u'♥'
            else:
                print u'x'
            self.player.set_property("uri", song_uri)
            self.player.set_state(gst.STATE_PLAYING)
            while self.playmode:
                c = self.control(r)
                if c == 'next' or c == 'del':
                    self.player.set_state(gst.STATE_NULL)
                    self.playmode = False
                    break 
        loop.quit()

channel_info = u'''
    0  私人兆赫
    1  华语兆赫
    2  欧美兆赫
    3  70兆赫
    4  80兆赫
    5  90兆赫
    6  粤语兆赫
    7  摇滚兆赫
    8  轻音乐兆赫
    9  民谣兆赫
'''
#print channel_info    
# c = raw_input('请输入您想听的频道数字:')
c = '0'
doubanfm = DoubanFM_CLI(c)
use_info = u'''
    跳过输入n，加心输入f，删歌输入d
'''
#print use_info
while 1:
    doubanfm.start()
    break
    # thread.start_new_thread(doubanfm.start, ())
    # gobject.threads_init()
    # loop = glib.MainLoop()
    # loop.run()

