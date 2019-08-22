from .browser import *
import time
import json

class Scrapper(Base):
    def __init__(self):
        self.browser = Browser()
        self.urlhisto = {}

    def scrap(self):
        raise NotImplementedError('scrapping action must be defined')

    def browse(self,url,*argv,**kwargs):
        if url not in self.urlhisto:
            self.urlhisto[url] = []
        self.urlhisto[url].append(time.localtime())
        return self.browser.browse(url, *argv, **kwargs)

    def save(self,scrapperfname='scrapper.1',browserfname='browser.1'):
        d = {'urlhisto':self.urlhisto,
             'browserf':browserfname}
        with open(scrapperfname,'w') as f:
            json.dump(d,f)
        self.browser.save(browserfname)

    def load(self,scrapperfname):
        with open(scrapperfname,'r') as f:
            d = json.load(f)
            self.urlhisto = d['urlhisto']
            self.browser.load(d['browserfname'])


if __name__ == '__main__':
    class yamibo(Scrapper):
        def __init__(self):
            Scrapper.__init__(self)

        def scrap(self):
            self.browser.timeout = 10
            forum = self.browse('https://bbs.yamibo.com', codec='gbk')
            sendmail_src = forum.xpath('//script')[-3].attrib['src']
            send_web = self.browse(forum.url + '/' + sendmail_src, codec='gbk')
            form = self.browse(
                'https://bbs.yamibo.com/member.php?mod=logging&action=login&infloat=yes&handlekey=login&inajax=1&ajaxtarget=fwin_content_login', \
                codec='gbk')
            formhash = form.xpath('//input[@type="hidden"]')[0].attrib['value']
            action = form.xpath('//form')[0].attrib['action']
            data = {'formhash': formhash,
                    'referer': 'https://bbs.yamibo.com/forum.php',
                    'loginfield': 'username',
                    'username': 'scrappyyamibo',
                    'password': 'scrappypassword163',
                    'questionid': '0',
                    'answer': ''}
            post = self.browse('https://bbs.yamibo.com/' + action, data=data, codec='gbk')
            forum = self.browse('https://bbs.yamibo.com', codec='gbk')
            self.browser.cookiestack.show()
            self.save()
    scrapper = yamibo()
    scrapper.scrap()


