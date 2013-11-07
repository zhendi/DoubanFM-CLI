#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, thread, glib, gobject, datetime
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
        self.init_cookie()
        self.login(username, password)

    def init_cookie(self):
        self.cookie = {}
        cookie = self.get_cache('cookie', {})
        self.merge_cookie(cookie)
    
    def login(self, username, password):
        print u'正在登录...'
        data = {
                'source': 'radio',
                'alias': username, 
                'form_password': password,
                'remember': 'on',
                'task': 'sync_channel_list'
                }
        # captcha_id = self.get_captcha_id()
        # captcha = self.get_captcha_solution(captcha_id)
        # data['captcha_id'] = captcha_id
        # data['captcha_solution'] = captcha
        # data = urllib.urlencode(data)
        print 'login ...'
        with closing(self.get_fm_conn()) as conn:
            # headers = self.get_headers_for_request({
            #     'Origin': 'http://douban.fm',
            #     'Content-Type': 'application/x-www-form-urlencoded',
            # })
            # conn.request("POST", "/j/login", data, headers)
            # response = conn.getresponse()

            # set_cookie = response.getheader('Set-Cookie')
            # if not set_cookie is None:
            #     cookie = SimpleCookie(set_cookie)
            #     self.save_cookie(cookie)

            # print response.status
            # body = response.read();
            body = '{"user_info":{"ck":"0-jp","play_record":{"fav_chls_count":7,"liked":418,"banned":100,"played":9954},"is_new_user":0,"uid":"xiaochi2","third_party_info":null,"url":"http:\/\/www.douban.com\/people\/xiaochi2\/","is_dj":false,"id":"2778286","is_pro":false,"name":"小池·水"},"r":0}'
            body = json.loads(body)
            if body['r'] != 0:
                print 'login failed'
                thread.exit()
                return 
            print 'ok'
            dbcl2 = self.cookie['dbcl2'].value
            if dbcl2 and len(dbcl2) > 0:
                self.dbcl2 = dbcl2
                self.uid = self.dbcl2.split(':')[0]
            self.bid = self.cookie['bid'].value

    def get_captcha_solution(self, captcha_id):
        self.show_captcha_image(captcha_id)
        c = raw_input('captcha:')
        return c

    def get_fm_conn(self):
        return httplib.HTTPConnection("douban.fm")

    def show_captcha_image(self, captcha_id):
        with closing(self.get_fm_conn()) as conn:
            print 'fetching captcha image...'
            path = "/misc/captcha?size=m&id=" + captcha_id

            import cStringIO

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
        print 'fetching captcha id ...'
        with closing(self.get_fm_conn()) as conn:

            headers = self.get_headers_for_request()

            conn.request("GET", path, None, headers)
            response = conn.getresponse()

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            print response.status

            if response.status == 302:
                redirect_url = response.getheader('location')
                return self.get_captcha_id(redirect_url)
            if response.status == 200:
                body = response.read()
                return body.strip('"')

    def save_cookie(self, cookie):
        self.merge_cookie(cookie)
        self.set_cache('cookie', self.cookie)

    def merge_cookie(self, cookie):
        for key in cookie:
            expires = cookie[key]['expires']
            if expires:
                expires = time.strptime(expires, '%a, %d-%b-%Y %H:%M:%S GMT')
                expires = time.mktime(expires)
                now = time.time()
                if expires > now:
                    self.cookie[key] = cookie[key]
                else:
                    if key in self.cookie:
                        del self.cookie[key]
            else:
                self.cookie[key] = cookie[key]

    def get_cookie_for_request(self):
        cookie_segments = []
        for key in self.cookie:
            cookie_segment = key + '="' + self.cookie[key].value + '"'
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
        
    def get_cache(self, name, default = None):
        print 'get cache', name
        file_name = self.get_cache_file_name(name)
        if not os.path.exists(file_name):
            return default
        cache_file = open(file_name, 'rb')
        content = pickle.load(cache_file)
        cache_file.close()
        return content

    def set_cache(self, name, content):
        file_name = self.get_cache_file_name(name)
        cache_file = open(file_name, 'wb')
        pickle.dump(content, cache_file)
        cache_file.close()

    def get_cache_file_name(self, name):
        return name + '.cache'