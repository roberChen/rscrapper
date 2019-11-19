import re
import urllib
import urllib.request as req
import gzip
from io import BytesIO
import json
import time
from pprint import pprint
from urllib import parse
import socket
import sys,os

from lxml import html
import random


def printc(strcolor,*argc,**kwargs):
    if strcolor == "red":
        colortype = '31'
    elif strcolor == 'green':
        colortype = '32'
    elif  strcolor == 'yellow':
        colortype = '33'
    elif strcolor == 'blue':
        colortype ='34'
    elif strcolor == 'pink':
        colortype = '35'
    elif strcolor == 'cyan':
        colortype = '36'
    elif strcolor == 'white':
        colortype = '37'
    print('\033[{}m'.format(colortype),end='',flush=True)
    print(*argc,**kwargs,flush=True)
    print('\033[0m',end='',flush=True)

class Base:
    def __init__(self):
        raise NotImplementedError('action must be defined')
    def save(self,fname):
        raise NotImplementedError('action must be defined')
    def load(self,fname):
        raise NotImplementedError('action must be defined')

class Browser(Base):
    def __init__(self,savef='',cookiestack=None,timeout=5,retry=2,unicode='utf-8'):
        self.webpages = {}
        self.cookiestack = cookiestack or Cookiestack()
        self.timeout = timeout
        self.retry = retry
        self.unicode = unicode
        self.stacks = []
        self.cookiestack.delexpires()
        self.User_agent = self.get_user_agent()

    def snapshot(self,fname,cookiefname):
        webpages_l = [{'url':web.url,
                       'html' if web.html else 'read':web.html or str(web.read),
                       'headers':web.headers,
                       'User_Agent':web.User_Agent,
                       'data':web.data,
                       'method':web.method,
                       'param':web.param} for web in self.webpages.values()]
        d = {'webpages':webpages_l,
             'cookiestackfname':cookiefname,
             'timeout':self.timeout,
             'retry':self.retry,
             'unicode':self.unicode,
             'User_agent':self.User_agent}
        with open(fname,'w') as f:
            jstxt = json.dumps(d)
            f.write(jstxt)
        self.cookiesave(cookiefname)

    def cookiesave(self,fname):
        self.cookiestack.save(fname)

    def load(self,fname):
        with open(fname,'r') as f:
            d = json.loads(f.read())
            print(d)
            self.timeout = d['timeout']
            self.unicode   = d['unicode']
            self.User_agent = d['User_agent']
            self.cookiestack = Cookiestack()
            self.cookiestack.loadall(d['cookiestackfname'])
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

    def browse(self,url,fname=None,save=False,nocookie=False,unicode=None,\
               timeout=None,retry=None,data=None,param=None,method='GET',\
               nohtml=False):
        cookiestack = self.cookiestack if not nocookie else None
        web = Webpage(url,User_agent=self.User_agent,cookiestack=cookiestack, \
                      timeout=timeout or self.timeout,retry=retry or self.retry,\
                      unicode=unicode or self.unicode,data=data,param=param,method=method)
        web.get(nohtml=nohtml)
        if not self.cookiestack.update(web):
            return web
        if fname or save:
            fname = fname or web.url+'.save'
            mode = 'w' if web.html else 'wb'
            with open(fname,mode) as f:
                try:
                    f.write(web.html or web.read)
                except TypeError as e:
                    web.reget(nohtml=nohtml)
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

    def addcookies(self,webdom,cookiedict):
        self.cookiestack.addcookie(webdom,cookiedict)

    def selebrowse(self,func):
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.wait import WebDriverWait
        import time
        browser = webdriver.Firefox()
        func(browser)
        for ele in browser.get_cookies():
            self.cookiestack.adddictcookie(ele["domain"],ele)


    def __call__(self, *args, **kwargs):
        return self.browse(*args,**kwargs)


class Cookiestack(Base):
    def __init__(self,fname='cookie.1'):
        self.cookies = {}
        self.savefile = fname
        self.load()
        self.delexpires()
        self.filep = open(fname,'a')
        for webdom,dct in self.cookies.items():
            for v in dct.values():
                self.save(webdom,v)
        # {'name':name,
        #  'value':value,
        #  keys:vals}
        # including:
        # 'expires' , 'secure' , 'path' etc.

    def addcookie(self,webdom,string_list,debug=False):
        if webdom not in self.cookies.keys():
            self.cookies[webdom] = {}
        d = {}
        for ele in string_list:
            l = ele.split(';')
            print('cookie list:',l)
            i, max = 0, len(l)
            while i < max:
                str = l[i]
                if str == 'Secure':
                    d['Secure'] = 'True'
                elif str == 'HttpOnly':
                    d['HttpOnly'] = 'True'
                elif '=' in str:
                    # print(ele)
                    [key, val] = str.split('=')
                    if i == 0:
                        d['name'] = key
                        d['value'] = val
                    else:
                        d[key] = val
                i += 1
            if debug:
                if d['name'] in self.cookies[webdom]:
                    print('Update:', d['name'], d['value'])
                else:
                    print('Add:', d['name'], d['value'])
            self.cookies[webdom][d['name']] = d
            self.save(webdom,d)
        return 1

    def update(self,web,debug=False):
        webdom = UrlList(web.url)[2]
        if webdom not in self.cookies:
            self.cookies[webdom] = {}
        if not web.response:
            return 0
        for ele in web.response.headers._headers:
            if ele[0] == 'Set-Cookie':
                self.addcookie(webdom,[ele[1]],debug=debug)
        return 1


    def getcookies(self,url,isdom=False):
        if url == '':
            printc('red','Error: url should not be empty')
        webdom = UrlList(url)[2]
        res = {}
        if webdom not in self.cookies:
            printc('red','Cookies of domain',webdom,'cannot be found.')
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


    def save(self,webdom,d):
        print("saving:",webdom,d)
        dct = {'webdom':webdom,
               'd':d}
        self.filep.write(json.dumps(dct)+'\n')

    def load(self):
        if not self.savefile in os.listdir():
            return 0
        with open(self.savefile,'r') as fp:
            fp.seek(0,0)
            for l in fp.readlines():
                if l == '\n':
                    continue
                print(l)
                dct = json.loads(l)
                print('loads:',dct)
                webdom = dct['webdom']
                d = dct ['d']
                if webdom not in self.cookies.keys():
                    self.cookies[webdom] = {}
                self.cookies[webdom][d['name']] = d


    def domchk(self,url):
        print('checking url:',url)
        webdom = UrlList(url)
        return webdom[2] in self.cookies.keys()

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

    def adddictcookie(self,webdom,dict):
        if webdom not in self.cookies.keys():
            self.cookies[webdom] = {}
        self.cookies[webdom][dict['name']] = dict

    def __add__(self, other):
        return self.cookies.update(other.cookies)

    def __str__(self):
        return 'Cookie contains {} site(s) \n {} '.format(self.cookies.__len__(), \
                                                          '\n'.join(self.cookies.keys()))
    def __getitem__(self, item):
        return self.cookies[item]

    def __call__(self, *args, **kwargs):
        self.updates(*args,**kwargs)

    def __exit__(self):
        self.filep.close()

class Webpage(Base):
    def __init__(self,url,cookiestack=None,timeout=10,retry=2, \
                 User_agent=None,unicode='utf8',data:dict=None,method='GET',param:dict=None,\
                 header:dict=None):
        self.url = url
        self.headers = header or {}
        self.param:dict = param or {}
        self.request = None
        self.response = None
        self.method = method
        self.html = None
        self.read = None
        self.unicode = unicode
        self.data:dict = data or {}
        self.cookiestack = cookiestack
        self.User_Agent = User_agent
        self.timeout = timeout
        self.retry = retry

    def get(self,*argv,timeout=2, retry=2, debug=False, \
             nohtml=False,unverifiable=False):
        if not self.url:
            return None
        if self.data:
            data = parse.urlencode(self.data).encode('ascii')
        else:
            data = None
        if not self.url.startswith('https://') and not self.url.startswith('http://'):
            self.url = 'https://' + self.url
        if 'User-Agent' not in self.headers and self.User_Agent:
            self.headers['User-Agent'] = self.User_Agent
        self.headers.update(argv)
        self.addcookies()
        print('Start downloading:', self.url)
        try:
            self.request = req.Request(self.url, headers=self.headers, data=data)
            self.request.param = self.param
            self.method = 'GET' if not self.data else 'POST'
            self.request.method = self.method
            if debug:
                print(self.request.data)
            self.response = req.urlopen(self.request, timeout=timeout)
        except (urllib.error.URLError,socket.timeout) as e:

            print('Download error No.', e.errno,end='')
            if hasattr(e,'reason'):
                print('\treason:',e.reason)
            else:
                print()
            if hasattr(e, 'code') and 500 <= e.code < 600:
                print('Error code:',e.code)
            self.reget(timeout=timeout, retry=retry - 1, debug=debug,nohtml=nohtml)
        try:
            _read = BytesIO()
            bs , reading , total = 1024 * 8 , 0 , 0
            if 'Content-Length' in self.response.headers:
                content_length = int(self.response.getheader('Content-Length'))
            else:
                content_length = 0
            print('\033[32m', end='')
            while True:
                block = self.response.read(bs)
                if not block:
                    break
                reading += len(block)
                if content_length:
                    print('\rLoading:{:4.2%}\t{} bytes.'.format(reading/content_length,reading) \
                          ,end='')
                else:
                    print('\rLoading:{} bytes.'.format(reading),end='')
                _read.write(block)
            print()
            _read.flush()
            self.read = _read.getvalue()
            print('\033[0m',end='')
            if  len(self.read) == 0 or (content_length != 0 and reading < content_length):
                printc('red','Error: retrival incomplite. {} / {} bytes'.format(reading,content_length))
                self.reget(timeout=timeout, retry=retry - 1, debug=debug,nohtml=nohtml)
        except socket.timeout as e:
            printc('red','Socket timeout:{}'.format(e))
            time.sleep(1)
            self.reget(timeout=timeout, retry=retry - 1, debug=debug,nohtml=nohtml)
        except:
            return self.url
        self.encode = self.response.getheader('Content-Encoding')
        if debug:
            print(self.read, '\nEncode:', self.encode)
        # decode if html is a gzip file
        if self.encode == 'gzip':
            byte = BytesIO(self.read)
            file = gzip.GzipFile(fileobj=byte)
            self.read = file.read()
        if nohtml:
            #print('Return webpage.read')
            return self.read
        try:
            self.html = self.read.decode(self.unicode, errors='ignore')
        except (TypeError,AttributeError) as e:
            printc('red','Occured Error:{}',format(e))
            time.sleep(2)
            self.reget(timeout=timeout,retry = retry -1,debug=debug,nohtml=nohtml)
        print('Return webpage.html')
        return self.html

    def reget(self,timeout=2, retry=2, debug=False, \
             nohtml=False,sleep=1):
        printc('yellow','sleep',sleep,'seconds')
        time.sleep(sleep)
        if retry == 0:
            printc('yellow','Retry remains 0, sleep 5 s.')
            time.sleep(5)
            ans = input('Retry is now zero, do you still want' + \
                        ' to retry after failing this time?')
            retry = 1 if ans == 'Yes' or ans == 'Y' \
                         or ans == 'yes' or ans == 'y'  or ans == '' else retry
        if retry > 0:
            return self.get(timeout=timeout, retry=retry - 1, debug=debug,nohtml=nohtml)
        else:
            return None

    def xpath(self,path):
        if not self.html:
            return []
        tree = html.fromstring(self.html.encode(self.unicode))
        return tree.xpath(path)

    def addcookies(self, cookiestack=None):
        cookiestack = cookiestack or self.cookiestack
        if not cookiestack:
            return -1
        if cookiestack.domchk(self.url):
            self.headers['Cookie'] = cookiestack.getstrcookie(self.url)

    def save(self,fname=''):
        fname = fname or (self.url+'.save' if self.html else self.url+'.byte')
        mode = 'w' if self.html else 'wb'
        with open(fname,mode) as f:
            print('save mode:',mode)
            f.write(self.html or self.read)



class UrlList():
    def __init__(self,url='',scheme='',internet='',dom='',port='',*path,ftype='.html'):
        self.urllist = [scheme,internet,dom,port,*path,ftype] \
                            if not url else self.urlsplit(url)
        self.fullurl = url or ''

    def getfullurl(self,update=False):
        if self.fullurl and not update:
            return self.fullurl
        self.fullurl = self.urllist[0] + '://' + self.urllist[1] + '.' + self.urllist[2] + \
               ('' if not self.urllist[3] else (':'+self.urllist[3])) + \
                '/' + '/'.join(self.urllist[5:-1]) + '.' + self.urllist[-1]
        return self.fullurl


    def urlsplit(self, url):
        if '://' in url:
            [scheme, specificpart] = url.split('://')
        else:
            scheme, specificpart = '', url
        if '?' in specificpart:
            mainpart,data = specificpart.split('?')
            params = data.split('&')
        else:
            mainpart = specificpart
            params = []
        split = mainpart.split('/')
        resl = re.findall('([^\.]*\.)?([^:\.]*\.[^:\.]*)(:[0-9]*)?', split[0])
        if resl:
            (internet, domain, port) = resl[0]
        else:
            (internet, domain, port) = ('', '', '')
        if len(split) > 1:
            if '.' in split[-1]:
                type = split[-1].split('.')[-1]
                f = '.'.join(split[-1].split('.')[:-1])
            else:
                f, type = split[-1], ''
            self.urllist = [scheme, internet[:-1], domain, port[1:],*split[1:-1],f,*params,type]
        else:
            self.urllist = [scheme, internet[:-1], domain, port[1:],*params]
        #print(self.urllist)
        return self.urllist

    def __getitem__(self, item):
        return self.urllist[item]
    def __str__(self):
        return str(self.urllist)


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




