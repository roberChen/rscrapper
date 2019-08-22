import re
import urllib
import urllib.request as req
import gzip
from io import BytesIO
import json
import time
from pprint import pprint
from urllib import parse

from lxml import html
import random

class Base:
    def __init__(self):
        raise NotImplementedError('action must be defined')
    def save(self,fname):
        raise NotImplementedError('action must be defined')
    def load(self,fname):
        raise NotImplementedError('action must be defined')

class Browser(Base):
    def __init__(self,fname='',cookiestack=None,timeout=5,retry=2):
        self.webpages = {}
        self.cookiestack = cookiestack or Cookiestack()
        self.timeout = timeout
        self.retry = retry
        self.codec = 'utf8'
        if fname:
            self.load(fname)
        self.cookiestack.delexpires()
        self.User_agent = self.get_user_agent()

    def save(self,fname):
        webpages_l = [{'url':web.url,
                       'html' if web.html else 'read':web.html or str(web.read),
                       'headers':web.headers,
                       'User_Agent':web.User_Agent,
                       'data':web.data,
                       'method':web.method,
                       'param':web.param} for web in self.webpages.values()]
        d = {'webpages':webpages_l,
             'cookiestack':self.cookiestack.cookies,
             'timeout':self.timeout,
             'retry':self.retry,
             'codec':self.codec,
             'User_agent':self.User_agent}
        with open(fname,'w') as f:
            jstxt = json.dumps(d)
            f.write(jstxt)

    def load(self,fname):
        with open(fname,'r') as f:
            d = json.loads(f.read())
            print(d)
            self.timeout = d['timeout']
            self.codec   = d['codec']
            self.User_agent = d['User_agent']
            self.cookiestack = Cookiestack()
            self.cookiestack.cookies = d['cookiestack']
            self.cookiestack.delexpires()
            self.webpages = []
            for web in d['webpages']:
                webobj = Webpage(web['url'],cookiestack=self.cookiestack,\
                                 timeout=self.timeout,retry=self.retry,\
                                 codec=self.codec,data=web['data'],method=web['method'],\
                                 param=web['param'])
                if 'html' in  web:
                    webobj.html = web['html']
                else:
                    webobj.read = eval(web['read'])
                self.webpages.append(webobj)

    def browse(self,url,fname=None,save=False,nocookie=False,codec=None,\
               timeout=None,retry=None,data=None,param=None,method='GET'):
        cookiestack = self.cookiestack if not nocookie else None
        web = Webpage(url,User_agent=self.User_agent,cookiestack=cookiestack, \
                      timeout=timeout or self.timeout,retry=retry or self.retry,\
                      codec=codec or self.codec,data=data,param=param,method=method)
        web.get()
        self.cookiestack.update(web)
        if fname or save:
            fname = fname or web.url+'.save'
            mode = 'w' if web.html else 'wb'
            with open(fname,mode) as f:
                f.write(web.html or web.read)
        self.webpages[web.url] = web
        return web

    def get_user_agent(self):
        UserAgent = ['Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:67.0) Gecko/20100101 Firefox/67.0',
                   'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)',
                   'Mozilla/5.0(Macintosh;IntelMacOSX10.6;rv:2.0.1)Gecko/20100101Firefox/4.0.1',
                   'Opera/9.80(Macintosh;IntelMacOSX10.6.8;U;en)Presto/2.8.131Version/11.11'
                   ]
        max = len(UserAgent) - 1
        using_agent = UserAgent[random.randint(0, max)]
        print('User-agent: ', using_agent)
        return using_agent

    def __call__(self, *args, **kwargs):
        return self.browse(*args,**kwargs)


class Cookiestack(Base):
    def __init__(self):
        self.cookies = {}
        # {'name':name,
        #  'value':value,
        #  keys:vals}
        # including:
        # 'expires' , 'secure' , 'path' etc.

    def update(self,web,debug=False):
        webdom = re.findall('[^\.]*\.([^\./]*\.[^\./]*)/?.*',web.url)[0]
        if webdom not in self.cookies:
            self.cookies[webdom] = {}
        for ele in web.response.headers._headers:
            if ele[0] == 'Set-Cookie':
                # div cookies by ';':
                d = {}
                l = ele[1].split(';')
                i , max = 0 , len(l)
                while i<max:
                    str = l[i]
                    if str == 'secure':
                        d['secure'] = 'True'
                    elif '=' in str:
                        # print(ele)
                        [key, val] = str.split('=')
                        if i == 0:
                            d['name'] = key
                            d['value'] = val
                        else:
                            d[key] = val
                    i+=1
                if d['name'] in self.cookies[webdom]:
                    print('Update:',d['name'],d['value'])
                else:
                    print('Add:',d['name'],d['value'])
                self.cookies[webdom][d['name']] = d


    def getcookies(self,url,isdom=False):
        if url == '':
            print('Error: url should not be empty')
        webdom = re.findall('[^\.]*\.([^\./]*\.[^\./]*)/?.*', url)[0] if not isdom else url
        res = {}
        if webdom not in self.cookies:
            print('Cookies of domain',webdom,'cannot be found.')
            return res
        for (name,dval) in self.cookies[webdom].items():
            res[name] = dval['value']
        return res

    def getstrcookie(self,url,isdom=False):
        d = self.getcookies(url,isdom)
        return ';'.join(['{}={}'.format(name,key) for (name,key) in d.items()])

    def delexpires(self):
        for domd in self.cookies:
            for ele in domd:
                if 'expires' not in ele:
                    continue
                exptime = time.strptime(ele['expires'],'%a, %d-%b-%Y %H:%M:%S GMT')
                if time.gmtime() > exptime:
                    domd.pop(ele)

    def load(self,fname):
        with open(fname,'r') as file:
            self.cookies = json.load(file)
        self.delexpires()

    def save(self,fname):
        with open(fname,'w') as file:
            json.dump(self.cookies,file)

    def domchk(self,url,isdom=False):
        print('checking url:',url)
        webdom = re.findall('[^\.]*\.([^\./]*\.[^\./]*)/?.*', url)[0] if not isdom else url
        return webdom in self.cookies.keys()

    def show(self):
        for (doms,d) in self.cookies.items():
            print('-'*50)
            print(doms)
            print('-'*15)
            for dict in d.values():
                for (k,v) in dict.items():
                    print(k,v)
                print()
        print('-'*50)

    def __add__(self, other):
        return self.cookies.update(other.cookies)

    def __str__(self):
        return 'Cookie contains {} site(s) \n {} '.format(self.cookies.__len__(), \
                                                          '\n'.join(self.cookies.keys()))
    def __getitem__(self, item):
        return self.cookies[item]

    def __call__(self, *args, **kwargs):
        self.updates(*args,**kwargs)

class Webpage(Base):
    def __init__(self,url,cookiestack=None,timeout=10,retry=2, \
                 User_agent=None,codec='utf8',data:dict={},method='GET',param:dict={},\
                 header:dict={}):
        self.url = url
        self.headers = header
        self.param:dict = param
        self.request = None
        self.response = None
        self.method = method
        self.html = None
        self.read = None
        self.codec = codec
        self.data:dict = data
        self.cookiestack = cookiestack
        self.User_Agent = User_agent
        self.timeout = timeout
        self.retry = retry

    def get(self,codec=None, timeout=2, retry=2, debug=False, useragent=None, \
             nohtml=False,headers=None,data={},param={},method=None,**argv):
        data.update(self.data or {})
        self.data = data
        if self.data:
            data = parse.urlencode(self.data).encode('ascii')
        else:
            data = None
        param.update(self.param or {})
        self.param = param
        self.codec = codec or self.codec or 'utf8'
        if not self.url.startswith('https://') and not self.url.startswith('http://'):
            self.url = 'https://' + self.url
        self.User_Agent = useragent or self.User_Agent
        if 'User-Agent' not in self.headers:
            self.headers['User-Agent'] = self.User_Agent
        if headers:
            self.headers.update(headers)
        self.headers.update(argv)
        self.addcookies()
        print('Start downloading:', self.url)
        try:
            self.request = req.Request(self.url, headers=self.headers, data=data)
            self.param = param.update(self.param)
            self.request.param = self.param
            self.method = 'GET' if not self.data else 'POST'
            self.request.method = method or self.method
            if debug:
                print(self.request.data)
            self.response = req.urlopen(self.request, timeout=timeout)
        except urllib.error.URLError as e:
            print('Download error No.', e.errno, ':\n\t', e.reason)
            if retry > 0:
                retry -= 1
                if hasattr(e, 'code') and 500 <= e.code < 600:
                    return self.request(timeout=timeout, retry=retry - 1, debug=debug)
        self.read = self.response.read()
        self.encode = self.response.getheader('Content-Encoding')
        if debug:
            print(self.read, '\nEncode:', self.encode)
        # decode if html is a gzip file
        if self.encode == 'gzip':
            byte = BytesIO(self.read)
            file = gzip.GzipFile(fileobj=byte)
            self.read = file.read()
        if nohtml:
            return self.read
        self.html = self.read.decode(self.codec, errors='ignore')
        return self.html

    def xpath(self,path):
        if not self.html:
            return []
        tree = html.fromstring(self.html.encode(self.codec))
        return tree.xpath(path)

    def addcookies(self, cookiestack=None):
        cookiestack = cookiestack or self.cookiestack
        if not cookiestack:
            return -1
        if cookiestack.domchk(self.url):
            self.headers['Cookie'] = cookiestack.getstrcookie(self.url)

    def save(self,fname=''):
        fname = fname or self.url+'.save' if self.html else self.url+'.byte'
        mode = 'w' if self.html else 'wb'
        with open(fname,mode) as f:
            f.write(self.html or self.read)



if __name__ == "__main__":
    browser = Browser(timeout=10)
    forum = browser.browse('https://bbs.yamibo.com',codec='gbk')
    sendmail_src = forum.xpath('//script')[-3].attrib['src']
    send_web = browser(forum.url + '/' + sendmail_src,codec='gbk')
    form = browser('https://bbs.yamibo.com/member.php?mod=logging&action=login&infloat=yes&handlekey=login&inajax=1&ajaxtarget=fwin_content_login',\
                   codec = 'gbk')
    formhash = form.xpath('//input[@type="hidden"]')[0].attrib['value']
    action = form.xpath('//form')[0].attrib['action']
    data = {'formhash':formhash,
                        'referer':'https://bbs.yamibo.com/forum.php',
                        'loginfield':'username',
                        'username':'scrappyyamibo',
                        'password':'scrappypassword163',
                        'questionid':'0',
                        'answer':''}
    post = browser.browse('https://bbs.yamibo.com/' + action,data=data,codec='gbk')
    forum = browser.browse('https://bbs.yamibo.com', codec='gbk')
    browser.cookiestack.show()
    browser.save('browser.1')
    del browser
    b2 = Browser(fname='browser.1')
    print(b2.webpages)




