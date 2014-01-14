#!/usr/bin/env python
# -*- coding: utf-8 -*-

# this file should rename to douban_fm_lib.py and should only have net functions

import sys, os, time, thread, glib, gobject, datetime
import pickle
import pygst
pygst.require("0.10")
import gst, json, urllib, httplib, contextlib, random, binascii, calendar
from select import select
from Cookie import SimpleCookie
from contextlib import closing 
from dateutil import parser

class PrivateFM(object):
    def __init__ (self, channel):
        self.cache = Cache()
        self.channel = channel
        # todo remove this var
        self.dbcl2 = None
        self.init_cookie()
        self.login()

    def init_cookie(self):
        self.cookie = {}
        cookie = self.cache.get('cookie', {})
        self.merge_cookie(cookie)
    
    def login(self):
        if self.remember_cookie():
            self.login_from_cookie()
        else:
            self.get_user_input_name_pass()
            self.login_from_net(self.username, self.password)

    def get_user_input_name_pass(self):
        self.username = raw_input("请输入豆瓣登录账户：")

        # todo 听说有个可以显示*的
        import getpass
        self.password = getpass.getpass("请输入豆瓣登录密码：")

    def remember_cookie(self):
        return 'dbcl2' in self.cookie and 'bid' in self.cookie

    # todo remove this method
    def login_from_cookie(self):
        dbcl2 = self.cookie['dbcl2'].value
        if dbcl2 and len(dbcl2) > 0:
            self.dbcl2 = dbcl2
            self.uid = self.dbcl2.split(':')[0]
        self.bid = self.cookie['bid'].value

    def login_from_net(self, username, password):
        print u'正在登录...'
        data = {
                'source': 'radio',
                'alias': username, 
                'form_password': password,
                'remember': 'on',
                'task': 'sync_channel_list'
                }
        # the flow of geting captcha should be invisibe to user
        # so, we should only show one message of geting captha image
        captcha_id = self.get_captcha_id()
        captcha = self.get_captcha_solution(captcha_id)
        data['captcha_id'] = captcha_id
        data['captcha_solution'] = captcha
        data = urllib.urlencode(data)

        print 'Login ...'
        with closing(self.get_fm_conn()) as conn:
            headers = self.get_headers_for_request({
                'Origin': 'http://douban.fm',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
            conn.request("POST", "/j/login", data, headers)
            response = conn.getresponse()

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            body = response.read();
            body = json.loads(body)
            if body['r'] != 0:
                print 'login failed'
                print body['err_msg']
                thread.exit()
                return
            user_info = body['user_info']
            play_record = user_info['play_record']
            print user_info['name'],
            print '累计收听'+str(play_record['played'])+'首',
            print '加红心'+str(play_record['liked'])+'首',
            print '收藏兆赫'+str(play_record['fav_chls_count'])+'个'
            self.login_from_cookie()

    def get_captcha_solution(self, captcha_id):
        self.show_captcha_image(captcha_id)
        c = raw_input('验证码: ')
        return c

    def get_fm_conn(self):
        return httplib.HTTPConnection("douban.fm")

    def show_captcha_image(self, captcha_id):
        with closing(self.get_fm_conn()) as conn:
            path = "/misc/captcha?size=m&id=" + captcha_id

            import cStringIO

            headers = self.get_headers_for_request()

            conn.request("GET", path, None, headers)
            response = conn.getresponse()

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            if response.status == 200:
                body = response.read()
                from PIL import Image
                f = cStringIO.StringIO(body)
                img = Image.open(f)
                img.show();


    def get_headers_for_request(self, extra = {}):
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
        for key in extra:
            headers[key] = extra[key]
        return headers

    def get_captcha_id(self, path = "/j/new_captcha"):
        with closing(self.get_fm_conn()) as conn:

            headers = self.get_headers_for_request()

            conn.request("GET", path, None, headers)
            response = conn.getresponse()

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            if response.status == 302:
                print '...'
                redirect_url = response.getheader('location')
                return self.get_captcha_id(redirect_url)
            if response.status == 200:
                body = response.read()
                return body.strip('"')

    def save_cookie(self, cookie):
        self.merge_cookie(cookie)
        self.cache.set('cookie', self.cookie)

    # maybe we should extract a class XcCookie(SimpleCookie)
    # merge(SimpleCookie)
    def merge_cookie(self, cookie):
        for key in cookie:
            expires = cookie[key]['expires']
            if expires:
                expires = parser.parse(expires)
                expires = calendar.timegm(expires.utctimetuple())
                now = time.time()
                if expires > now:
                    self.cookie[key] = cookie[key]
                else:
                    if key in self.cookie:
                        del self.cookie[key]
            else:
                self.cookie[key] = cookie[key]

    # todo XcCookie.get_request_string()
    def get_cookie_for_request(self):
        cookie_segments = []
        for key in self.cookie:
            cookie_segment = key + '="' + self.cookie[key].value + '"'
            cookie_segments.append(cookie_segment)
        return '; '.join(cookie_segments)
  
    def get_params(self, typename=None):
        params = {}
        params['r'] = ''.join(random.sample('0123456789abcdefghijklmnopqrstuvwxyz0123456789', 10))
        params['uid'] = self.uid
        params['channel'] = self.channel
        params['from'] = 'mainsite'
        if typename is not None:
            params['type'] = typename
        return params

    def communicate(self, params):
        data = urllib.urlencode(params)
        with closing(httplib.HTTPConnection("douban.fm")) as conn:
            conn.request('GET', "/j/mine/playlist?"+data, None, self.get_headers_for_request())
            result = conn.getresponse().read()
            return result

    def playlist(self):
        print 'Fetching playlist ...'
        params = self.get_params('n')
        result = self.communicate(params)
        result = json.loads(result)
        if result.has_key('logout') and result['logout'] == 1:
            print 'need relogin'
            self.get_user_input_name_pass()
            self.login_from_net(self.username, self.password)
            return self.playlist()
        else:
            return result['song']
     
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

class Cache:
    """docstring for cache"""
    def has(self, name):
        file_name = self.get_cache_file_name(name)
        return os.path.exists(file_name)

    def get(self, name, default = None):
        file_name = self.get_cache_file_name(name)
        if not os.path.exists(file_name):
            return default
        cache_file = open(file_name, 'rb')
        content = pickle.load(cache_file)
        cache_file.close()
        return content

    def set(self, name, content):
        file_name = self.get_cache_file_name(name)
        cache_file = open(file_name, 'wb')
        pickle.dump(content, cache_file)
        cache_file.close()

    def get_cache_file_name(self, name):
        # file should put into a `cache` dir
        return name + '.cache'

