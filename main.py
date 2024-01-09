import os
from typing import Annotated, Type, List, Optional
from dotenv import load_dotenv
import logging
import datetime
from time import struct_time
import random
from pytz import utc

from fastapi import FastAPI, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

import crawling_news_server.crawl.util
import crawling_news_server.crawl.response_to_text
from crawling_news_server import crud, models, schemas
from crawling_news_server.database import get_db, Base, engine, get_context_db

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

import requests
import urllib3
import html

from crawling_news_server.crawl import rss_fixer

load_dotenv()
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


jobstores = {}
if os.environ.get("JOB_STORE"):
    jobstores['default'] = SQLAlchemyJobStore(url=os.environ.get("JOB_DB_PATH"), engine_options={'pool_size': 100})

executors = {
    'default': ThreadPoolExecutor(50),
    'processpool': ProcessPoolExecutor(50)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 50
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)
app = FastAPI(
    version="0.1.1"
)


def crawling(rss_id: int, url: str):
    logging.info(f"[{rss_id}]({url:<55}): Crawling...")

    add_count = 0
    with get_context_db() as db:
        try:
            if not crud.get_rss(db, rss_id).is_active:
                logging.info(f"[{rss_id}]({url:<55}): Remove job")
                scheduler.remove_job(f"{rss_id}")

        except Exception as e:
            logging.error(f"[{rss_id}]({url:<55}): Remove job Error {e}")

        try:
            response = requests.get(url, headers=crawling_news_server.crawl.util.get_header(), verify=False)
            response.raise_for_status()

            text = crawling_news_server.crawl.response_to_text.response_to_text(url, response)

            crud.create_rss_response_record(db, rss_id, url, text, response.status_code)

            rss_obj = rss_fixer.fix_rss(url, response.text)

            db_rss = crud.get_rss(db, rss_id)

            db_rss.title = rss_obj.get('feed', {}).get("title", db_rss.title)
            db_rss.description = rss_obj.get('feed', {}).get("description", db_rss.description)
            db_rss.language = rss_obj.get('feed', {}).get("language", db_rss.language)
            db_rss.rights = rss_obj.get('feed', {}).get("rights", db_rss.rights)
            db_rss.last_build_date = rss_obj.get('feed', {}).get("updated", db_rss.last_build_date)
            db_rss.web_master = rss_obj.get('feed', {}).get("publisher", db_rss.web_master)

            # try:
            #     db_rss.title = rss_obj['feed'].title
            # except:
            #     pass
            # try:
            #     db_rss.description = rss_obj['feed'].description
            # except:
            #     pass
            # try:
            #     db_rss.language = rss_obj['feed'].language
            # except:
            #     pass
            # try:
            #     db_rss.rights = rss_obj['feed'].rights
            # except:
            #     pass
            # try:
            #     db_rss.last_build_date = rss_obj['feed'].updated
            # except:
            #     pass
            # try:
            #     db_rss.web_master = rss_obj['feed'].publisher
            # except:
            #     pass
            crud.update_rss_obj(db, db_rss)

            for item in rss_obj.entries:
                db_rss_item = crud.get_rss_item_by_rss_id_and_link(db, rss_id, item.link)
                if db_rss_item is not None:
                    continue

                try:

                    rss_item = schemas.ItemRssItemCreateNewscj(
                        title=item.title,
                        link=item.link,
                        description="",
                        guid=item.link,
                        pub_date=datetime.datetime.utcnow().isoformat(),
                        author="",
                        category="",
                    )

                    try:
                        rss_item.description = html.unescape(item.summary)
                    except Exception as e:
                        logging.warning(f"[{rss_id}]({url:<55}): description error: {e}")
                    try:
                        rss_item.author = item.author
                    except Exception as e:
                        logging.warning(f"[{rss_id}]({url:<55}): author error: {e}")
                    try:
                        rss_item.category = item.category
                    except Exception as e:
                        logging.warning(f"[{rss_id}]({url:<55}): category error: {e}")
                    try:
                        rss_item.pub_date = item.published
                    except Exception as e:
                        logging.warning(f"[{rss_id}]({url:<55}): category error: {e}")

                    crud.create_rss_item(db, rss_id, rss_item)
                    add_count += 1
                except Exception as e:
                    logging.error(f"[{rss_id}]({url:<55}): rss_item error: {e}")

            if add_count == 0:
                if len(rss_obj.entries):
                    try:
                        rss_item_time: struct_time = rss_obj.entries[0].published_parsed

                        if (datetime.datetime.utcnow().year - rss_item_time.tm_year) > 1:
                            logging.info(f"[{rss_id}]({url:<55}): Not Update, Remove job")
                            crud.update_rss_active(db, rss_id, False)
                            scheduler.remove_job(f"{rss_id}")

                        else:
                            scheduler.reschedule_job(f"{rss_id}", trigger='interval',
                                                     seconds=3600 + random.randint(0, 600))
                    except:
                        scheduler.reschedule_job(f"{rss_id}", trigger='interval', seconds=3600 + random.randint(0, 600))
                else:
                    scheduler.reschedule_job(f"{rss_id}", trigger='interval', seconds=3600 + random.randint(0, 600))

            elif add_count / len(rss_obj.entries) > 0.5:
                logging.info(f"[{rss_id}]({url:<55}): Add {add_count} items")
                scheduler.reschedule_job(f"{rss_id}", trigger='interval', seconds=random.randint(600, 1200))

            else:
                logging.info(f"[{rss_id}]({url:<55}): Add {add_count} items")
                scheduler.reschedule_job(f"{rss_id}", trigger='interval', seconds=random.randint(1200, 1800))

        except requests.exceptions.HTTPError as http_error:
            response: requests.Response = http_error.response
            logging.warning(f"[{rss_id}]({url:<55}): {http_error}")
            text = crawling_news_server.crawl.response_to_text.response_to_text(url, response)
            crud.create_rss_response_record(db, rss_id, url, text, response.status_code)
            scheduler.reschedule_job(f"{rss_id}", trigger='interval', seconds=3600 + random.randint(0, 120))

            if not crud.get_rss(db, rss_id).is_active:
                logging.info(f"[{rss_id}]({url:<55}): Remove job")
                scheduler.remove_job(f"{rss_id}")

        except requests.exceptions.ConnectionError:
            logging.info(f"[{rss_id}]({url:<55}): Remove job")
            crud.update_rss_active(db, rss_id, False)
            scheduler.remove_job(f"{rss_id}")

        except Exception as e:
            logging.warning(f"[{rss_id}]({url:<55}): {e}")
            if not crud.get_rss(db, rss_id).is_active:
                logging.info(f"[{rss_id}]({url:<55}): Remove job")
                scheduler.remove_job(f"{rss_id}")
            pass


def add_job_rss_crawling(db_rss: Type[models.RSS]):
    rss_id = db_rss.id
    name = db_rss.name
    delay = db_rss.delay
    if delay < 400:
        delay = random.randint(200, 400)

    url = db_rss.url
    next_run_time = (datetime.datetime.utcnow() + datetime.timedelta(seconds=(random.randint(0, 120) + 60)))

    scheduler.add_job(
        crawling,
        'interval',
        [rss_id, url],
        id=f"{rss_id}",
        name=f"{name}",
        seconds=delay,
        replace_existing=True,
        next_run_time=next_run_time
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
            add_job_rss_crawling(db_rss)

        scheduler.start()


@app.get('/rss', response_model=List[schemas.ItemRSSResponse])
async def read_rss(q: Optional[str] = None, offset: int = 1, limit: int = 50,db: Session = Depends(get_db)):
    if q:
        return crud.get_all_rss_search(db, q, offset, limit)["data"]

    else:
        return crud.get_all_rss(db, offset, limit)["data"]


@app.get("/rss/item")
async def read_rss_item(q: str, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.find_rss_title(db, q, offset, limit)
    pass


@app.get('/rss/job')
async def read_rss_job(db: Session = Depends(get_db)):
    pass


@app.get('/rss/responses', response_model=List[schemas.ResponseRecordDto])
async def read_rss(offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_all_rss_responses(db, offset, limit)['data']


@app.get("/rss/{rss_id}", response_model=schemas.ItemRSSResponse)
async def read_user(rss_id: int, db: Session = Depends(get_db)):
    db_rss = crud.get_rss(db, rss_id)
    if db_rss is None:
        raise HTTPException(status_code=404, detail="RSS not found")
    return db_rss


@app.get("/rss/{rss_id}/items", response_model=List[schemas.ItemRssItemResponse])
async def read_rss_item_by_rss_id(rss_id: int, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_rss_items(db, rss_id, offset, limit)['data']


@app.get("/rss/{rss_id}/responses", response_model=List[schemas.ResponseRecordDto])
async def read_rss_item_by_rss_id(rss_id: int, offset: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return crud.get_rss_responses(db, rss_id, offset, limit)['data']


@app.post("/rss", response_model=schemas.ItemRSS)
async def create_rss(rss: Annotated[
    schemas.ItemRSSCreate,
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
