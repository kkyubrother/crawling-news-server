from typing import Optional
from datetime import datetime

formats_to_try = [
    "%d %b %Y %H:%M:%S %Z",
    "%a,%d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %z",
    "%Y.%m.%d",
    "%Y%m%d%H%M%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H-%M-%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S.%f%z",
]


def parse_date(date_string: Optional[str]) -> Optional[datetime]:
    """알려진 포멧으로 datetime으로 변환 시도"""
    if not date_string:
        return None

    date_string = date_string.replace("KST", "+0900")
    for date_format in formats_to_try:
        try:
            return datetime.strptime(date_string, date_format)
        except ValueError:
            pass

    return None
