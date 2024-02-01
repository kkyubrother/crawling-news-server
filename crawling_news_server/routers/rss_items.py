from fastapi import APIRouter
import logging

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session

from crawling_news_server import crud, models, schemas
from crawling_news_server.database import get_db, Base, engine, get_context_db


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    prefix="/items",
)


@router.get("/", response_model=schemas.RssItemListResponse)
async def read_rss_item(q: str, offset: int = 1, limit: int = 50, distinct: bool = True, db: Session = Depends(get_db)):
    return crud.find_rss_item_by_title(db, q, offset, limit, distinct)

