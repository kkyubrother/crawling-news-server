from typing import Optional, List, Any
import datetime
from pydantic import BaseModel, Field


class RssDto(BaseModel):
    name: str
    url: str
    title: str
    description: str
    link: str
    delay: int
    category: str
    pass


class RssCreateDto(RssDto):
    pass


class RssResponseDto(RssDto):
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


class RssItemDto(BaseModel):
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


class RssItemCreateDto(RssItemDto):
    pass


class RssItemResponseDto(RssItemDto):
    id: int
    rss_id: int
    rss: RssResponseDto
    pass


class ResponseRecordDto(BaseModel):
    id: int
    link: str
    status_code: int
    body: str
    created_at: datetime.datetime
    rss_id: int


class PaginationResponse(BaseModel):
    total_count: int
    data: List[Any]


class RssItemListResponse(PaginationResponse):
    data: List[RssItemDto]


class RssResponse(PaginationResponse):
    data: List[RssResponseDto]


class RssRecordResponse(PaginationResponse):
    data: List[ResponseRecordDto]
