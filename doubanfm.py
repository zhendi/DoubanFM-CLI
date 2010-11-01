#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, thread, glib, gobject
import pygst
pygst.require("0.10")
import gst, json, urllib, httplib, contextlib, random
from select import select
from Cookie import SimpleCookie

class PrivateFM(object):
    def __init__ (self, username, password):
        self.dbcl2 = None
        self.login(username, password)
    
    def login(self, username, password):
        data = urllib.urlencode({'form_email':username, 'form_password':password})
        with contextlib.closing(httplib.HTTPConnection("www.douban.com")) as conn:
            conn.request("POST", "/accounts/login", data, {"Content-Type":"application/x-www-form-urlencoded"})
            cookie = SimpleCookie(conn.getresponse().getheader('Set-Cookie'))
            dbcl2 = cookie['dbcl2'].value
            if dbcl2 and len(dbcl2) > 0:
                self.dbcl2 = dbcl2
                self.uid = self.dbcl2.split(':')[0]
            self.bid = cookie['bid'].value
  
    def get_params(self, typename=None):
        params = {}
        params['r'] = random.random()
        params['uid'] = self.uid
        params['channel'] = '0' 
        if typename is not None:
            params['type'] = typename
        return params

    def communicate(self, params):
        data = urllib.urlencode(params)
        cookie = 'dbcl2="%s"; bid="%s"' % (self.dbcl2, self.bid)
        header = {"Cookie": cookie}
        with contextlib.closing(httplib.HTTPConnection("douban.fm")) as conn:
            conn.request('GET', "/j/mine/playlist?"+data, None, header)
            result = conn.getresponse().read()
            return result

    def playlist(self):
        params = self.get_params('n')
        result = self.communicate(params)
        return json.loads(result)['song']
     
    def del_song(self, sid, aid):
        params = self.get_params('b')
        params['sid'] = sid
        params['aid'] = aid
        result = self.communicate(params)
        return json.loads(result)['song']

    def fav_song(self, sid, aid):
        params = self.get_params('r')
        params['sid'] = sid
        params['aid'] = aid
        self.communicate(params)

    def unfav_song(self, sid, aid):
        params = self.get_params('u')
        params['sid'] = sid
        params['aid'] = aid
        self.communicate(params)

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

    def get_songlist(self):
        if self.user:
            self.songlist = self.user.playlist()
        elif self.private:
            self.username = raw_input("请输入豆瓣登录账户：") 
            self.password = raw_input("请输入豆瓣登录密码：") 
            self.user = PrivateFM(self.username, self.password)
            self.songlist = self.user.playlist()
        else:
            self.songlist = json.loads(urllib.urlopen(self.ch).read())['song']

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
            print u'正在播放： '+r['title']+u'     歌手： '+r['artist']
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
    8  民谣兆赫
    9  轻音乐兆赫
'''
print channel_info    
c = raw_input('请输入您想听的频道数字:')
doubanfm = DoubanFM_CLI(c)
use_info = u'''
    跳过输入n，加心输入f，删歌输入d
'''
print use_info
while 1:
    thread.start_new_thread(doubanfm.start, ())
    gobject.threads_init()
    loop = glib.MainLoop()
    loop.run()


