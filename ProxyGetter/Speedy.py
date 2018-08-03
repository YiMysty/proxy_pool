import requests
import Queue
import threading
from bs4 import BeautifulSoup
import sys
import re
import json
reload(sys)
sys.setdefaultencoding('utf-8')

class Speedy:
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    baseUrl =  'https://www.amazon.com/s/ref=nb_sb_noss_1?url=search-alias%3Damazonfresh&field-keywords='
    proxies = { } 
    
    def __init__(self, items = [], zipCode = None, proxies = None):
        self.items = items
        self.zipCode = zipCode
        self.queue = Queue.Queue()
        self.proxies = proxies
        self.init()

    def getAll(self):
        content = requests.get("http://www.chefling-redis.com:6060/get_all/").content
        return len(content.split('/n')) > 3

    def init(self,):
        url = self.baseUrl + 'egg'
        response = requests.get(url, headers = self.headers, proxies=self.proxies, timeout = 3)
        cookies = response.cookies
        changeAddressUrl = 'https://www.amazon.com/gp/delivery/ajax/address-change.html'
        changeAddressPayload = {
            'zipCode': self.zipCode,
            'locationType': 'LOCATION_INPUT',
            'deviceType': 'web',
            'pageType': 'search',
            'actionSource': 'glow'
        }
        response = requests.post(changeAddressUrl, data = changeAddressPayload, headers = self.headers, cookies = cookies, proxies=self.proxies, timeout = 3)
        self.cookies = response.cookies
    
    def get(self, url, name):
        result = {
            'name' : name,
            'raw' : ""
        }
        try:
            response = requests.get(url, headers = self.headers, cookies = self.cookies, proxies=self.proxies, timeout = 3)
        except:
            return result
        if response.status_code == 200:
            result['raw'] = response.text

        self.queue.put(result)
        return result
    
    def getDetail(self, asinCode):
        detailUrl = 'https://www.amazon.com/gp/product/' + asinCode + '?fpw=fresh'
        response = requests.get(detailUrl, headers = self.headers, cookies = self.cookies, proxies=self.proxies, timeout = 3)
        if response.status_code == 200:
            return self.parseDetail(response.text)
        return {'decription': [], 'recommendation': []}
    
    def parseDetail(self, content):
        soup = BeautifulSoup(content, 'lxml')
        bullets = soup.find('div', {'id': 'feature-bullets'})
        items = []
        if bullets != None:
            items = bullets.find_all('span', {'class': 'a-list-item'})
        features = [];
        for item in items:
            if item.text != None:
                features.append(item.text)
        recommends = []
        items = soup.select("[data-p13n-asin-metadata]")
        for item in items:
            recommend = {"asin" : json.loads(item['data-p13n-asin-metadata'])['asin']}
            img = item.find('img')
            recommend['src'] = img['src']
            recommend['name'] = img['alt']
            recommend['price'] = ''
            price = item.find("span", {'class': 'p13n-sc-price'})
            if price != None:
                recommend['price'] =  item.find("span", {'class': 'p13n-sc-price'}).text
            rating = item.find("span", {'class': 'a-icon-alt'})
            recommend['rating'] = 'NA';
            if rating != None:
                recommend['rating'] = rating.text
            recommends.append(recommend)
        return {'decription': features, 'recommendation': recommends}
    
    # BeautifulSoup has memory issue when trying to run in multiple threads, thus sync this part
    def parse(self, content):
        result = {
            'name': content['name'],
            'search': []
        }
        if content['raw'] == "":
            return result
        html = content['raw']
        soup = BeautifulSoup(html, 'lxml')
        items = soup.find_all('li', id=re.compile(r'result_'))
        for item in items:
            i = {}
            i['asin'] = item['data-asin']
            img= item.find('img', {'srcset' : re.compile(r'https')})
            i['name'] = img['alt']
            i['src']  = img['src']
            i['price'] = ''
            price = item.find('span', {'class': 'a-offscreen'})
            if price != None:
                i['price'] = item.find('span', {'class': 'a-offscreen'}).text
            i['priceDescription'] = ''
            description = item.find('span', {'class', 'a-size-base a-color-base'})
            if description:
                i['priceDescription'] = description.text
            i['rating'] = ''
            rating = item.find('i', {'class': 'a-icon-star'})
            if rating:
                i['rating'] = rating.find('span', {'class': 'a-icon-alt'}).text
            result['search'].append(i)
        return result

    def runAsync(self):
        urls = [self.baseUrl + item for item in self.items]
        for i, url in enumerate(urls):
            t = threading.Thread(target=self.get, args = (url, self.items[i]))
            t.daemon = True
            t.start()
        count = 0
        result = []
        while count < len(self.items):
            result.append(self.parse(self.queue.get()))
            count += 1
        return result
    
    def run(self):
        pass


def main():
    speedy = Speedy(['egg'], '98043')
    print speedy.runAsync()
    # print speedy.getDetail('B00RWV5U2S')

if __name__ == '__main__':
    main()
    