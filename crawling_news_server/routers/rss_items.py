from typing import Optional
import datetime
from fastapi import APIRouter, Query
import logging

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session

from crawling_news_server import crud, models, schemas
from crawling_news_server.database import get_db, Base, engine, get_context_db


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/api/v2/items",
)


@router.get('/', response_model=schemas.RssItemListResponse)
def read_rss_items(
        q: Optional[str] = None, start_dt: Optional[str] = None, end_dt: Optional[str] = None,
        offset: int = 1, limit: int = 50, distinct: bool = True,
        white_rss_id: Optional[str] = Query(None, description="include rss_id list", example='1,2,3'),
        black_rss_id: Optional[str] = Query(None, description="exclude rss_id list", example='4,5,6'),
        db: Session = Depends(get_db)):

    if white_rss_id and black_rss_id:
        raise HTTPException(400, "white and black")

    if white_rss_id:
        white_rss_id: list[int] = list(map(int, white_rss_id.split(",")))
    else:
        white_rss_id: None = None

    if black_rss_id:
        black_rss_id: list[int] = list(map(int, black_rss_id.split(",")))
    else:
        black_rss_id: None = None

    if start_dt:
        try:
            datetime.datetime.fromisoformat(start_dt)
        except ValueError:
            raise HTTPException(400, "start_dt is error")

    if end_dt:
        try:
            datetime.datetime.fromisoformat(end_dt)
        except ValueError:
            raise HTTPException(400, "end_dt is error")

    return crud.find_rss_item_by_title(db, q, offset, limit, distinct, start_dt, end_dt, white_rss_id, black_rss_id)
