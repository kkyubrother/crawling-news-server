import re
import sys
from typing import Optional

from bs4 import BeautifulSoup
import aiohttp
import requests
from crawling_news_server.crawl.util import get_header, normalize_url
from urllib.parse import urlparse


def is_ignore_url(url: str) -> bool:
    if url == "http://feeds.feedburner.com/brandbucket":
        return True
    elif url.startswith("http://lifeedu.or.kr"):
        return True
    elif url.startswith("http://www.mohrss.gov.cn"):
        return True
    elif url.startswith("https://www.toutiao.com"):
        return True
    elif url.startswith("https://www.ichannela.com"):
        return True
    elif url.startswith("http://www.ichannela.com"):
        return True
    elif url.startswith("https://people.incruit.com"):
        return True
    elif url.startswith("https://m.yicai.com"):
        return True
    elif url.startswith("https://white.contentsfeed.com"):
        return True

    return False


async def fetch(url: str, encoding: Optional[str] = None):
    # https://www.inflearn.com/questions/667190/%ED%8C%8C%EC%9D%B4%EC%8D%AC-%EC%BD%94%EB%A3%A8%ED%8B%B4-%EC%82%AC%EC%9A%A9%ED%95%98%EA%B8%B0-aiohttp%EB%A1%9C-crawling%EC%8B%9C%EC%97%90-ssl-error-%EB%B0%9C%EC%83%9D
    # SSL 에러 무시
    # connector = aiohttp.TCPConnector(ssl=False, limit=30)
    # async with aiohttp.ClientSession(connector=connector) as session:
    #     async with session.get(url, headers=get_header()) as resp:
    #         try:
    #             resp.raise_for_status()
    #
    #             if encoding:
    #                 return resp.content.read()
    #
    #             with open(path, 'wb') as fd:
    #                 async for chunk in resp.content.iter_chunked(chunk_size):
    #                     fd.write(chunk)
    #         except Exception as e:
    #             print(f"Status Error {url}: {e}", file=sys.stderr)

    response_bytes = requests.get(url, headers=get_header(), verify=False).content

    webpage_data = ""
    try:
        webpage_data = response_bytes.decode('euc-kr')
    except UnicodeDecodeError:
        try:
            webpage_data = response_bytes.decode('utf-8', errors="replace")
        except:
            try:
                webpage_data = response_bytes.decode('cp949')
            except:
                webpage_data = response_bytes.decode('ascii')

    if not webpage_data:
        Exception("no webpage data")

    return webpage_data


def create_beautifulsoup(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, 'html.parser')

    # for item in soup.select('link[href=""]'):
    #     item.decompose()
    for item in soup.select('style'):
        item.decompose()
    # for item in soup.select('meta'):
    #     item.decompose()
    for item in soup.select('script'):
        item.decompose()
    # for item in soup.select('link[rel!="alternate"]'):
    #     item.decompose()
    return soup


def extract_rss_url_from_link_tag(url: str, soup: BeautifulSoup) -> list:
    rss_url_list = set()
    link_rss_list = soup.select('link[rel="alternate"][type="application/rss+xml"]')
    for item in link_rss_list:
        href = item.extract()['href']
        rss_url_list.add(normalize_url(url, href))
    return list(rss_url_list)


def extract_rss_url_from_body(url: str, soup: BeautifulSoup) -> list:
    rss_url_list = set()
    tag_list = soup.find_all(href=re.compile(r"rss|feed"))
    for item in tag_list:
        extracted_item = item.extract()
        href = extracted_item['href']
        if 'javascript:' in href or "#" in href:
            continue

        rss_url_list.add(normalize_url(url, href))
    return list(rss_url_list)


async def extract_rss_urls(url: str):
    webpage_text = await fetch(url)
    # print(webpage_text, file=sys.stdout)

    soup = create_beautifulsoup(webpage_text)
    print(soup, file=sys.stdout)

    data = {'link': extract_rss_url_from_link_tag(url, soup), 'body': extract_rss_url_from_body(url, soup)}

    return data
