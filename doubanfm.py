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

class PrivateFM(object):
    def __init__ (self, username, password):
        self.dbcl2 = None
        print 'get cookie from file...'
        self.cookie = self.get_cache('cookie', {})

        self.login(username, password)
    
    def login(self, username, password):
        print u'正在登录...'
        print {'form_email':username, 'form_password':password}
        print "/accounts/login"
        data = {
                'source': 'radio',
                'alias': username, 
                'form_password': password
                }
        captcha = self.get_captcha_solution()
        return
        data = urllib.urlencode()
        print data
        with closing(httplib.HTTPConnection("www.douban.com")) as conn:
            conn.request("POST", "/accounts/login", data, {"Content-Type":"application/x-www-form-urlencoded"})
            cookie = SimpleCookie(conn.getresponse().getheader('Set-Cookie'))
            if not cookie.has_key('dbcl2'):
                print 'login failed'
                thread.exit()
                return 
            dbcl2 = cookie['dbcl2'].value
            if dbcl2 and len(dbcl2) > 0:
                self.dbcl2 = dbcl2
                self.uid = self.dbcl2.split(':')[0]
            self.bid = cookie['bid'].value

    def get_captcha_solution(self):
        self.show_captcha_image()
        print 'get'

    def get_fm_conn(self):
        return httplib.HTTPConnection("douban.fm")

    def show_captcha_image(self):
        captcha_id = self.get_captcha_id()
        print captcha_id
        
        with closing(self.get_fm_conn()) as conn:
            print '========================'
            print 'fetching captcha image...'
            path = "/misc/captcha?size=m&id=" + captcha_id
            print path
            
            headers = self.get_headers_for_request()

            conn.request("GET", path, None, headers)
            response = conn.getresponse()
            print response.status

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            if response.status == 200:
                body = response.read()
                print body

                from PIL import Image
                r_data = binascii.unhexlify(body)

                stream = io.BytesIO(r_data)

                img = Image.open(stream)
                img.show();


    def get_headers_for_request(self):
        headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/28.0.1500.71 Chrome/28.0.1500.71 Safari/537.36',
            'Referer': 'http://douban.fm/',
            'Accept-Language': 'zh-CN,zh;q=0.8'
        }
        if self.cookie:
            cookie_str = self.get_cookie_for_request()
            headers['Cookie'] = cookie_str
        return headers

    def get_captcha_id(self, path = "/j/new_captcha"):
        with closing(self.get_fm_conn()) as conn:
            print 'fetching captcha id...'

            headers = self.get_headers_for_request()

            conn.request("GET", path, None, headers)
            response = conn.getresponse()
            print response.status

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            if response.status == 302:
                redirect_url = response.getheader('location')
                return self.get_captcha_id(redirect_url)
            if response.status == 200:
                body = response.read()
                return body.strip('"')

    def save_cookie(self, cookie):
        for key in cookie:
            # todo expire
            self.cookie[key] = cookie[key].value
        self.set_cache('cookie', self.cookie)

    def get_cookie_for_request(self):
        cookie_segments = []
        for key in self.cookie:
            cookie_segment = key + '="' + self.cookie[key] + '"'
            cookie_segments.append(cookie_segment)
        return '; '.join(cookie_segments)
  
    def get_params(self, typename=None):
        params = {}
        params['r'] = random.random()
        params['uid'] = self.uid
        params['channel'] = '0' 
        if typename is not None:
            params['type'] = typename
        return params

    def communicate(self, params):
        print 'communicate'
        print params
        data = urllib.urlencode(params)
        cookie = 'dbcl2="%s"; bid="%s"' % (self.dbcl2, self.bid)
        header = {"Cookie": cookie}
        with closing(httplib.HTTPConnection("douban.fm")) as conn:
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
            return
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

    def get_cache(self, name, default = None):
        file_name = self.get_cache_file_name(name)
        if not os.path.exists(file_name):
            return default
        cache_file = open(file_name, 'rb')
        i = pickle.load(cache_file)
        cache_file.close()
        return i

    def set_cache(self, name, content):
        file_name = self.get_cache_file_name(name)
        cache_file = open(file_name, 'wb')
        pickle.dump(content, cache_file)
        cache_file.close()

    def get_cache_file_name(self, name):
        return name + '.cache'

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
        return
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
    8  轻音乐兆赫
    9  民谣兆赫
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

