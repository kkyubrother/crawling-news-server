import re
from urllib.parse import urlparse
import feedparser


def fix_rss(url: str, text: str) -> feedparser.FeedParserDict:
    parsed_url = urlparse(url)
    # 카테고리 중첩 제거
    text = re.sub(r"(]]>)?</category>\s*<category>(<!\[CDATA\[)?", ":", text)

    # CDATA 추가 시도
    if m := re.search(r"(?<=<description>).+?(?=</description>)", text):
        if not re.match(r"(?<=<!\[CDATA\[).+?(?=]]>)", m.group()):
            text = re.sub(
                r"(?<=<description>)(.+?)(?=</description>)",
                r"<![CDATA[\g<1>]]>", text)

    text = re.sub(r"<!\[CDATA\[<!\[CDATA\[(.+?)]]>]]>", r"<![CDATA[\g<1>]]>", text)

    if parsed_url.netloc == 'www.joseilbo.com':
        p = re.compile(r"(?<=</link>)\s*<!\[CDATA\[(.+?)]]>\s*(?=<dc:creator>)")
        if m := p.search(text):
            text = p.sub(r"\n<description><![CDATA[\g<1>]]></description>\n", text)

    elif parsed_url.netloc == 'www.countryhome.co.kr':
        text = re.sub("<script .+\n?.+</script>", "", text, re.DOTALL)
        text = re.sub("><", ">\n<", text)

    elif parsed_url.netloc == 'newshound7.blogspot.com':
        text = re.sub("</author><title type='text'>", "<title>", text, re.DOTALL)
        text = text.replace(' type="text"', '')
        text = text.replace("type='text'", '')
        text = text.replace("</author>", '')

    elif parsed_url.netloc == 'www.okfashion.co.kr':
        text = re.sub("<font.+</font>(</?br/?>)", "", text)
        text = text.strip()
        text = text.replace("</author>", "</author><description><![CDATA[")

    elif parsed_url.netloc == 'fcnews.co.kr':
        text = re.sub(
            r"</description>(?!<content:encoded>|<atom:updated>)",
            "</description><content:encoded><![CDATA[",
            text.replace("\n", "")
        )
        pass

    elif parsed_url.netloc == 'www.countryhome.co.kr':
        webpage_data = re.sub(
            r"]](?=<)",
            "]]>",
            text
        )
        pass

    # CDATA 테그 닫기 잘못된 부분 변경
    text = re.sub(
        r"<([^>]+)>(<!\[CDATA\[)(.*?)(]])</(\S+)>",
        r"<\g<1>><![CDATA[\g<3>]]></\g<5>>",
        text)

    return feedparser.parse(text)
