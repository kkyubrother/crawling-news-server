import datetime

from fastapi import APIRouter

import os
from typing import Annotated, Type, List, Optional
from dotenv import load_dotenv
import logging

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from crawling_news_server import crud, models, schemas, crawl
from crawling_news_server.database import get_db, Base, engine, get_context_db

import urllib3

from crawling_news_server.jobs import add_job_rss_crawling, scheduler
from crawling_news_server.crawl.extract_rss_data import extract_rss_urls
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/api/v2/rss",
)


@router.get('/', response_model=schemas.RssResponse)
async def read_rss(q: Optional[str] = None, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    """

    :param q: title과 description에서 해당 텍스트를 검색한다.
    :param offset: 페이지 번호
    :param limit: 1회 요청 페이지  갯수
    :param db: DB 세션
    :return: RSS 객체
    """
    if q:
        return crud.get_all_rss_search(db, q, offset, limit)

    else:
        return crud.get_all_rss(db, offset, limit)


@router.get('/items', response_model=schemas.RssItemListResponse)
async def read_rss_items(
        q: Optional[str] = None, start_dt: Optional[str] = None, end_dt: Optional[str] = None,
        offset: int = 1, limit: int = 50, distinct: bool = True, db: Session = Depends(get_db)):

    if start_dt:
        try:
            datetime.datetime.fromisoformat(start_dt)
        except:
            raise HTTPException(400, "start_dt is error")

    if end_dt:
        try:
            datetime.datetime.fromisoformat(end_dt)
        except:
            raise HTTPException(400, "end_dt is error")

    logger.info(f"{start_dt}, {end_dt}")

    return crud.find_rss_item_by_title(db, q, offset, limit, distinct, start_dt, end_dt)


@router.get("/{rss_id}", response_model=schemas.RssResponseDto)
async def read_user(rss_id: int, db: Session = Depends(get_db)):
    db_rss = crud.get_rss(db, rss_id)
    if db_rss is None:
        raise HTTPException(status_code=404, detail="RSS not found")
    return db_rss


@router.get("/{rss_id}/items", response_model=List[schemas.RssItemResponseDto])
async def read_rss_item_by_rss_id(rss_id: int, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_rss_items(db, rss_id, offset, limit)['data']


@router.get("/{rss_id}/responses", response_model=List[schemas.ResponseRecordDto])
async def read_rss_item_by_rss_id(rss_id: int, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_rss_responses(db, rss_id, offset, limit)['data']


@router.post("/", response_model=schemas.RssDto)
async def create_rss(rss: Annotated[
    schemas.RssCreateDto,
    Body(openapi_examples={
        "chosun": {
            "summary": "조선일보 기본 데이터",
            "value": {
                "name": "조선일보 - 전체기사",
                "url": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",
                "title": "조선일보 - 전체기사",
                "description": "조선일보",
                "link": "https://www.chosun.com/",
                "delay": 60,
                "category": "전체기사"
            }
        }
    })
], db: Session = Depends(get_db)):
    db_rss = crud.get_rss_by_url(db, url=rss.url)
    if db_rss:
        raise HTTPException(status_code=400, detail="url already registered")

    db_rss = crud.create_rss(db, rss)
    if not db_rss:
        raise HTTPException(status_code=400, detail="Can't add RSS")

    add_job_rss_crawling(db_rss)
    return db_rss


@router.post("/crawl")
async def crawl_from(url: str, db: Session = Depends(get_db)):
    data = await extract_rss_urls(url)
    logger.info(data)
    return data
    pass


@router.post("/{rss_id}/crawl")
async def crawl_at(rss_id: int, db: Session = Depends(get_db)):
    add_count = 0
    rss = crud.get_rss(db, rss_id)

    response = requests.get(rss.url, headers=crawl.util.get_header(), verify=False)

    text = crawl.response_to_text.response_to_text(rss.url, response)
    rss_obj = crawl.rss_fixer.fix_rss(rss.url, response.text)

    crud.update_rss_from_rss_dict(db, rss_id, rss_obj.get("feed", {}))
    rt = []

    for item in rss_obj.entries:
        if crud.get_rss_item_by_rss_id_and_link(db, rss_id, item.link) is not None:
            continue

        if item := crud.create_rss_item_from_rss_item_obj(db, rss_id, item):
            rt.append(item)
            add_count += 1

    crud.create_rss_response_record(db, rss_id, rss.url, ("" if add_count else "<!-- ENTRY ZERO -->") + text, response.status_code)

    logger.info(rt)

    return {
        "total_count": add_count,
        "data": [row.id for row in rt],
        "response": {
            "status": response.status_code,
            "body": text
        }
    }
