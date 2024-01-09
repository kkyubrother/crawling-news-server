from typing import Optional
import datetime
from pydantic import BaseModel, Field


class ItemRSS(BaseModel):
    name: str
    url: str
    title: str
    description: str
    link: str
    delay: int
    category: str
    pass


class ItemRSSCreate(ItemRSS):
    pass


class ItemRSSResponse(ItemRSS):
    id: int
    is_active: int

    category: Optional[str] = Field(default=None)
    cloud: Optional[str] = Field(default=None)
    copyright: Optional[str] = Field(default=None)
    docs: Optional[str] = Field(default=None)
    generator: Optional[str] = Field(default=None)
    language: Optional[str] = Field(default=None)
    last_build_date: Optional[str] = Field(default=None)
    managing_editor: Optional[str] = Field(default=None)
    pub_date: Optional[str] = Field(default=None)
    rating: Optional[str] = Field(default=None)
    skip_hours: Optional[str] = Field(default=None)
    text_input: Optional[str] = Field(default=None)
    ttl: Optional[str] = Field(default=None)
    web_master: Optional[str] = Field(default=None)

    extra: Optional[str] = Field(default=None)


class ItemRssItem(BaseModel):
    title: str
    description: str
    link: str

    author: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    comments: Optional[str] = Field(default=None)
    enclosure: Optional[str] = Field(default=None)
    guid: Optional[str] = Field(default=None)
    pub_date: Optional[str] = Field(default=None)
    source: Optional[str] = Field(default=None)

    extra: Optional[str] = Field(default=None)


class ItemRssItemCreate(ItemRssItem):
    pass


class ItemRssItemCreateNewscj(ItemRssItemCreate):
    guid: str
    pub_date: str
    author: str
    pass


class ItemRssItemResponse(ItemRssItem):
    id: int
    rss_id: int
    pass


class ResponseRecordDto(BaseModel):
    id: int
    link: str
    status_code: int
    body: str
    created_at: datetime.datetime
    rss_id: int
