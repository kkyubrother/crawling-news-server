import os
import random
from urllib.parse import urlparse


def load_ua_list() -> list[str]:
    with open(os.path.join(os.getcwd(), "user-agents.txt"), encoding='utf-8') as f:
        return f.readlines()


__UA_LIST: list[str] = load_ua_list()


def get_header() -> dict:
    return {
        'User-Agent': random.choice(__UA_LIST).strip()
    }


def normalize_url(base_url: str, target_url: str) -> str:
    """추출한 url 을 정규화한다."""
    if target_url.startswith("http://") or target_url.startswith("https://"):
        rss_url = target_url
    else:
        pared_base_url = urlparse(base_url)
        if target_url.startswith("//"):
            rss_url = f"{pared_base_url.scheme}:{target_url}"
        elif target_url.startswith("/"):
            rss_url = f"{pared_base_url.scheme}://{pared_base_url.netloc}{target_url}"
        else:
            rss_url = f"{pared_base_url.scheme}://{pared_base_url.netloc}/{target_url}"
    return rss_url
