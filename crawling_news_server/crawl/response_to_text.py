import requests
from urllib.parse import urlparse


def response_to_text(url: str, response: requests.Response) -> str:
    parsed_url = urlparse(url)
    if (parsed_url.netloc == 'www.boannews.com'
            or parsed_url.netloc == 'www.drnews.co.kr'
            or parsed_url.netloc == 'news.kmib.co.kr'
            or parsed_url.netloc == 'rss.kmib.co.kr'
            or parsed_url.netloc == 'www.popco.net'
            or parsed_url.netloc == 'www.bseconomy.com'
            or parsed_url.netloc == 'www.joseilbo.com'
            # or parsed_url.netloc == 'sport.chosun.com'
            or parsed_url.netloc == 'www.withleisure.co.kr'
    ):
        response.encoding = 'euc-kr'
        text = response.text
    # elif parsed_url.netloc == 'rss.edaily.co.kr':
    elif response.content.startswith(b'\xef\xbb\xbf'):
        text = response.content.lstrip(b'\xef\xbb\xbf').decode('utf-8').strip()
    else:
        text = response.text
    return text.strip()
