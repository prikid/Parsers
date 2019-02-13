import requests
from urllib.parse import urlparse
from Nested2CSV import Nested2CSV
from multiprocessing import Pool


class MyParser:

    def __init__(self, url):
        self.url = url
        self.parsed_url = urlparse(url)
        self.host = self.parsed_url.scheme + '://' + self.parsed_url.netloc

    @staticmethod
    def __return_or_fail(request, return_type):
        if request.status_code == 200:
            if return_type == 'text':
                return request.text
            elif return_type == 'json':
                return request.json()
            else:
                raise Exception('Unrecognized return type')
        else:
            raise Exception('Request failed')

    def __get_data(self, type, **kwargs):
        if 'method' not in kwargs.keys():
            method = 'get'
        else:
            method = kwargs['method']
            del kwargs['method']

        r = requests.request(method, self.url, **kwargs)
        return self.__return_or_fail(r, type)

    def get_html(self, **kwargs):
        return self.__get_data('text', **kwargs)

    def get_json(self, **kwargs):
        return self.__get_data('json', **kwargs)

    @staticmethod
    def try_scrape(func):
        res = func()
        # TODO enable try block (when it will be clear what kind of exceptions we have to use)
        # try:
        #     res = func()
        # except:
        #     res = ''

        return res

    @staticmethod
    def nested_data_to_csv(filename, data):
        Nested2CSV(data).to_csv(filename)

    @staticmethod
    def do_multiprocessing(func, data_list,  processes=5):
        with Pool(processes=processes) as pool:
            return pool.map(func, data_list)
