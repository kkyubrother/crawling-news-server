import os
from typing import Annotated, Type, List, Optional
from dotenv import load_dotenv
import logging

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from crawling_news_server import crud, models, schemas
from crawling_news_server.database import get_db, Base, engine, get_context_db

import urllib3

from crawling_news_server.jobs import add_job_rss_crawling, scheduler

load_dotenv()
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(
    version="0.1.2",
    title="뉴스 수집 및 검색",
    summary="개인용 뉴스 수집 및 검색 서비스 제공",
    description="""# 목적
개인을 위한 뉴스 수집과 검색 서비스

# 버전
<details>
<summary>[2024-01-24] v0.1.2</summary>

* RssItem에 Rss 정보 포함
</details>
<details>
<summary>[2024-01-08] v0.1.1</summary>

* rss 기본 api 추가
</details>

<details>
<summary>[2024-01-02] v0.1.0</summary>

* 기초 완성
</details>

"""
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOW_ORIGINS", "*").split(";"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event('startup')
def init_data():
    Base.metadata.create_all(engine)
    db = get_db().__next__()

    db_rss_all = crud.get_rss_all(db)
    if os.environ.get("JOB_EXECUTE") == "TRUE":
        for db_rss in db_rss_all:
            if not db_rss.is_active:
                continue

            if not scheduler.get_job(f"{db_rss.id}"):
                add_job_rss_crawling(db_rss)

        scheduler.start()


@app.get('/rss', response_model=schemas.RssResponse)
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


@app.get("/rss/item", response_model=schemas.RssItemListResponse)
async def read_rss_item(q: str, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.find_rss_title(db, q, offset, limit)


@app.get('/rss/job')
async def read_rss_job(db: Session = Depends(get_db)):
    pass


@app.get('/rss/responses', response_model=schemas.RssRecordResponse)
async def read_rss(offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_all_rss_responses(db, offset, limit)


@app.get("/rss/{rss_id}", response_model=schemas.RssResponseDto)
async def read_user(rss_id: int, db: Session = Depends(get_db)):
    db_rss = crud.get_rss(db, rss_id)
    if db_rss is None:
        raise HTTPException(status_code=404, detail="RSS not found")
    return db_rss


@app.get("/rss/{rss_id}/items", response_model=List[schemas.RssItemResponseDto])
async def read_rss_item_by_rss_id(rss_id: int, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_rss_items(db, rss_id, offset, limit)['data']


@app.get("/rss/{rss_id}/responses", response_model=List[schemas.ResponseRecordDto])
async def read_rss_item_by_rss_id(rss_id: int, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_rss_responses(db, rss_id, offset, limit)['data']


@app.post("/rss", response_model=schemas.RssDto)
async def create_rss(rss: Annotated[
    schemas.RssCreateDto,
    Body(openapi_examples={
        "newscj": {
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


@app.get("/jobs")
async def get_jobs():
    jobs = scheduler.get_jobs()
    return [{
        "id": job.id,
        "name": job.name,
        "next": f"{job.next_run_time}"
    } for job in jobs]
    pass


@app.post("/jobs")
async def create_job(rss_id: int, db: Session = Depends(get_db)):
    db_rss = crud.get_rss(db, rss_id)
    add_job_rss_crawling(db_rss)
    return db_rss


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = scheduler.get_job(f"{job_id}")
    job_data = {
        "id": job.id,
        "name": job.name,
        "next": f"{job.next_run_time}"
    }
    scheduler.remove_job(f"{job_id}")
    return job_data


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
