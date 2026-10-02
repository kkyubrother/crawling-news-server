import os
from typing import Annotated, Type, List, Optional
from dotenv import load_dotenv
import logging

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from crawling_news_server import crud, models, schemas, __version__, __description__
from crawling_news_server.database import get_db, Base, engine, get_context_db
from crawling_news_server.routers import rss, rss_items, jobs

import urllib3

from crawling_news_server.jobs import add_job_rss_crawling, scheduler

load_dotenv()
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    Base.metadata.create_all(engine)
    models.RSSItem.create_fulltext_index(engine)

    with get_context_db() as db:
        db_rss_all = crud.get_rss_all(db)
        if os.environ.get("JOB_EXECUTE") == "TRUE":
            for db_rss in db_rss_all:
                if not db_rss.is_active:
                    continue

                if not scheduler.get_job(f"{db_rss.id}"):
                    add_job_rss_crawling(db_rss)

            scheduler.start()

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    version=__version__,
    title="뉴스 수집 및 검색",
    summary="개인용 뉴스 수집 및 검색 서비스 제공",
    description=__description__,
    lifespan=lifespan
)

origins = [origin.strip() for origin in os.environ.get("ALLOW_ORIGINS", "*").split(";") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rss.router)
app.include_router(rss_items.router)
app.include_router(jobs.router)


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
