import grequests
import requests
from bs4 import BeautifulSoup as bs
import json
import datetime
import asyncio
import re
from typing import List, Tuple
from itertools import chain
from timeit import default_timer as timer


def _write_json(new_data: list, filename: str):
    with open(filename, "a+", encoding="utf-8") as file:
        start = timer()
        file.seek(0)
        file_data = []
        if file.read() != "":
            file.seek(0)
            file_data = json.load(file)
        file_data.extend(new_data)
        file.seek(0)
        file.truncate()
        json.dump(file_data, file, ensure_ascii=False, indent=4)
        stop = timer()
        print('_write_json', stop-start)


def _write_txt(text: tuple, filename: str):
    with open(filename, 'a+', encoding="utf-8") as file:
        start = timer()
        file.write(''.join(text).strip('\n'))
        stop = timer()
        print('_write_txt', stop-start)


class Product():
    def __init__(self, name, protein: float, fat: float, carbohydrates: float, kcal: float = None):
        self.name = name
        self.protein = protein
        self.fat = fat
        self.carbohydrates = carbohydrates
        self.kcal = kcal

    def __repr__(self):
        return f'{self.name} - Б:{self.protein}, Ж:{self.fat}, У:{self.carbohydrates} - {self.kcal} ккал/100г\n'

    def __dir__(self):
        return {"named": self.name,
                "protein": self.protein,
                "fat": self.carbohydrates,
                "kcal": self.kcal}


def _get_pages(links: Tuple[str]) -> Tuple[requests.Response] | None:
    start = timer()
    requests = (grequests.get(l) for l in links)
    responses = grequests.map(requests, len(links) if links else 1)
    success = {id: x for id, x in enumerate(responses) if x.status_code == 200}
    fail = {id: x for id, x in enumerate(responses) if x.status_code != 200}
    i = iter(range(10))
    while fail and (next(i, None) is not None):
        resps = grequests.map((grequests.get(i.url)
                              for i in fail.values()), len(fail))
        n_resps = dict(zip(fail.keys(), resps))
        success.update(
            {id: x for id, x in n_resps.items() if x.status_code == 200})
        fail = {id: x for id, x in n_resps.items() if x.status_code != 200}
    stop = timer()
    print('_get_responses', stop-start)
    if fail:
        return
    return tuple(success.values())


def _get_products(content: str) -> List[Product] | None:
    products = []
    soup = bs(content, 'lxml')
    table = soup.find('div', class_='view-content').find('tbody')
    for tr in table.find_all('tr'):
        name = str(tr.find('td',
                           class_='views-field-title').find('a').contents[0])
        protein = tr.find('td',
                          class_='views-field-field-protein-value').contents[0].strip()
        if protein == "":
            protein = 0
        fat = tr.find('td',
                      class_='views-field-field-fat-value').contents[0].strip()
        if fat == "":
            fat = 0
        carbohydrates = tr.find('td',
                                class_='views-field-field-carbohydrate-value').contents[0].strip()
        if carbohydrates == "":
            carbohydrates = 0
        kcal = tr.find(
            'td', class_='views-field-field-kcal-value').contents[0].strip()
        if kcal == "":
            kcal = 0
        products.append(Product(name=name, protein=protein,
                                fat=fat, carbohydrates=carbohydrates, kcal=kcal))
    return products


def _new_get_products(content: str) -> List[Product] | None:
    products = []
    soup = bs(content, 'lxml')
    table = soup.find('table', class_='views-table')
    if not table:
        return
    for tr in table.find('tbody').find_all('tr'):
        name = str(tr.find('td',
                           class_='views-field-title').find('a').contents[0])
        protein = tr.find('td',
                          class_='views-field-field-protein-value').contents[0].strip()
        fat = tr.find('td',
                      class_='views-field-field-fat-value').contents[0].strip()
        carbohydrates = tr.find('td',
                                class_='views-field-field-carbohydrate-value').contents[0].strip()
        kcal = tr.find(
            'td', class_='views-field-field-kcal-value').contents[0].strip()

        products.append(
            Product(name, *(p if p else 0 for p in (protein, fat, carbohydrates, kcal))))
    return products


def _get_links(content: str, link: str) -> Tuple[str] | None:
    start = timer()
    soup = bs(content, 'lxml')
    div = soup.find('div', class_='item-list')
    li = div.find('li', class_='pager-last')
    a = str(li.find('a').get('href'))
    s = re.findall(r'page=(\d+)', a)
    stop = timer()
    print('_get_links', stop-start)
    if s:
        return tuple(f'{link}?page={i}' for i in range(
            1, int(s[0])+1))


def parsing_all(link: str = 'https://calorizator.ru', page: str = '/product/all'):
    start = timer()
    first_link = (f'{link}{page}', )
    first_page = _get_pages(first_link)[0]
    links = _get_links(first_page.text, f'{link}{page}')
    responses = (first_page,) + _get_pages(links)
    pr = timer()
    products = tuple(chain.from_iterable((_new_get_products(response.text)
                                          for response in responses)))
    prs = timer()
    print('all_products', prs-pr)
    text = (repr(product) for product in products)
    json_text = [product.__dict__ for product in products]
    d = datetime.datetime.now().__str__().replace(":", "-")
    _write_txt(text, f'calories_{d}.txt')
    _write_json(json_text, f'calories_{d}.json')
    stop = timer()
    print('parsing_all', stop-start)


if __name__ == '__main__':
    parsing_all()
