from bs4 import BeautifulSoup
import re
from MyParser import MyParser
from pprint import pprint


class CatalogPage(MyParser):
    def __init__(self, start_url):
        super().__init__(start_url)
        self.can_load_more = False

    def __get_page_html(self, page_num):
        headers = {'x-requested-with': 'XMLHttpRequest'}
        params = {'nextPage': page_num}
        res_json = self.get_json(headers=headers, params=params)

        if res_json['status'] == 'success':
            self.can_load_more = not 'can_load_more' in res_json or res_json['can_load_more']==1
            return res_json['html']
        else:
            raise Exception('Catalog page load error')

    def __get_items_from_html(self, html):
        soup = BeautifulSoup(html, 'lxml')
        divs = soup.find_all('div', class_='collection-result')

        items = []
        for div in divs:
            a = div.find('div', class_='result-description').find('a')
            items.append({
                'collection': a.text,
                'url': self.host + a['href']
            })
            # break   # TODO for debug
            # print('Item scraped:',  items[-1]['name'])

        return items

    def get_items(self, page_num):
        return self.__get_items_from_html(self.__get_page_html(page_num))


class Prices(MyParser):
    def __init__(self, region):
        super().__init__('https://www.centura.ca/en/api/collections/tile/getTileSKUsPrices')
        self.prices = {}
        self.region = region

    def __fetch(self, collection):
        collection = collection.lower()

        headers = {'cookie': 'c_region=' + self.region + ';'}
        data = {'collection': collection}

        res_json = self.get_json(method='post', data=data, headers=headers)
        if res_json['status'] == 'success':
            return res_json['response']
        else:
            raise Exception('Prices load error')

    def get_price_data(self, collection, sku):
        collection = collection.lower()
        sku = sku.lower()

        if collection not in self.prices.keys():
            data = self.__fetch(collection)
            self.prices[collection] = data

        # if collection in self.prices.keys() and (type(self.prices[collection]) is dict and sku in self.prices[collection].keys()):
        try:
            return self.prices[collection][sku]
        except:
            print('Price error in collection ', collection)
            return False




class ItemPage(MyParser):
    def __init__(self, url, prices_object):
        super().__init__(url)
        self.prices = prices_object

    def __get_sku_lines(self, sku_container):

        # remove tooltips
        tooltips = sku_container.find_all('span', class_='tooltip-wrapper')
        for t in tooltips:
            t.decompose()

        lines = sku_container.find('div', class_='').find_all('div', class_='sku-line', recursive=False)
        params_list = [line.get_text(strip=True).encode('ascii', 'ignore').decode() for line in lines]
        return ', '.join(params_list)

    def __get_sku_dimensions(self, sku):
        dims_list = []
        lines = sku.find('div', class_='sku-dimensions').find_all('div', class_='sku-line')
        for line in lines:
            spans = line.find_all('span')
            dims = [span.text.replace('\u2009', '') for span in spans]
            dims_list.append(' x '.join(dims))

        return ', '.join(dims_list)

    def __scrape_item_page(self, html):
        soup = BeautifulSoup(html, 'lxml')

        collection = self.try_scrape(lambda: soup.find('div', class_='wrapper')['data-collection'])

        data = {
            'colors': [],
            'description': self.try_scrape(lambda: soup.find('div', class_='product-description').text.strip())
        }

        colors_divs = soup.find('div', class_='sku-zone').find_all('div', class_=re.compile(r"^colour-\d$"))
        for color in colors_divs:
            skus_container = color.find('div', class_='skus')
            color = {
                'color': self.try_scrape(lambda: skus_container.find('h2').next_element.strip()),
                'skus': []
            }

            sku_divs = skus_container.find_all('div', class_='sku')
            for sku_div in sku_divs:
                sku = self.try_scrape(lambda: sku_div.find('div', class_='sku-name')['data-name'].strip())
                price_data = self.prices.get_price_data(collection, sku)

                params = {
                    'sku': sku.upper(),
                    'price': price_data['price'] if price_data else '',
                    'qty_info': price_data['qty_info'] if price_data else '',
                    'dimensions': self.__get_sku_dimensions(sku_div),
                    'params': self.__get_sku_lines(sku_div)
                }

                color['skus'].append(params)

            data['colors'].append(color)

        return data

    def get_item_data(self):
        html = self.get_html()
        return self.__scrape_item_page(html)


region = 'toronto'
prices_object = Prices(region)

def get_and_update_item(item):
    global prices_object

    new_item = item.copy()
    item_page = ItemPage(new_item['url'], prices_object)
    item_data = item_page.get_item_data()
    print('   item ', new_item['collection'], ' parsed')

    new_item.update(item_data)
    return new_item


def get_catalog(page_num):
    items = CatalogPage('https://www.centura.ca/en/products/tile/').get_items(page_num)
    print('Catalog page ', page_num, ' parsed')

    return items


def main():
    all_items = []
    # ----------------- Parse catalog pages -------------------------
    max_pages = 1

    # one process way
    cat_page = CatalogPage('https://www.centura.ca/en/products/tile/')
    for page_num in range(max_pages):
        items = cat_page.get_items(page_num)
        all_items += items
        print('Catalog page ', page_num, ' parsed')
        if not cat_page.can_load_more:
            break

    # print(all_items)
    # exit()

    # multiprocess way
    # items_lists = MyParser.do_multiprocessing(get_catalog, range(max_pages), min(max_pages, 10))
    # all_items = [j for i in items_lists for j in i]
    # ------------------------------------------------------------------

    # --------------- Parse items pages ----------------------------
    # one process way
    # res_list = [get_and_update_item(item) for item in all_items]

    # multiprocess way
    res_list = MyParser.do_multiprocessing(get_and_update_item, all_items, 20)
    # ---------------------------------------------------------------

    MyParser.nested_data_to_csv('centura.csv', res_list)
    print('Success')


if __name__ == '__main__':
    main()
