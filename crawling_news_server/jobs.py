import os
import logging
import datetime
import random
from time import struct_time
from typing import Type


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
import requests
from pytz import utc

from crawling_news_server import models
from crawling_news_server.database import get_context_db
from crawling_news_server import crud
from crawling_news_server import crawl

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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


def crawling(rss_id: int, url: str) -> None:
    logger.info(f"[{rss_id:<10}]({url:<55}): Crawling...")

    def reschedule(base_seconds: int):
        scheduler.reschedule_job(f"{rss_id}", trigger='interval', seconds=base_seconds + random.randint(0, 600))

    add_count = 0
    with get_context_db() as db:

        try:
            if not crud.get_rss(db, rss_id).is_active:
                logging.info(f"[{rss_id:<10}]({url:<55}): Not active rss, remove job")
                scheduler.remove_job(f"{rss_id}")
                return

        except Exception as e:
            logging.error(f"[{rss_id:<10}]({url:<55}): Remove job Error {e}")

        try:
            response = requests.get(url, headers=crawl.util.get_header(), verify=False)
            response.raise_for_status()

            text = crawl.response_to_text.response_to_text(url, response)
            rss_obj = crawl.rss_fixer.fix_rss(url, response.text)

            crud.update_rss_from_rss_dict(db, rss_id, rss_obj.get("feed", {}))

            for item in rss_obj.entries:
                if crud.get_rss_item_by_rss_id_and_link(db, rss_id, item.link) is not None:
                    continue

                if crud.create_rss_item_from_rss_item_obj(db, rss_id, item):
                    add_count += 1

            if add_count == 0:
                if len(rss_obj.entries):
                    try:
                        rss_item_time: struct_time = rss_obj.entries[0].published_parsed

                        if (datetime.datetime.utcnow().year - rss_item_time.tm_year) > 1:
                            crud.create_rss_response_record(db, rss_id, url, text, response.status_code)
                            logger.info(f"[{rss_id:<10}]({url:<55}): Not Update, Remove job")
                            crud.update_rss_active(db, rss_id, False)
                            scheduler.remove_job(f"{rss_id}")

                        else:
                            reschedule(3600)

                    except:
                        reschedule(3600)

                else:
                    crud.create_rss_response_record(db, rss_id, url, "<!-- ENTRY ZERO -->" + text, response.status_code)
                    reschedule(7200)

            elif add_count / len(rss_obj.entries) > 0.5:
                crud.create_rss_response_record(db, rss_id, url, text, response.status_code)
                logger.info(f"[{rss_id:<10}]({url:<55}): Add {add_count} items")
                reschedule(600)

            else:
                crud.create_rss_response_record(db, rss_id, url, text, response.status_code)
                logger.info(f"[{rss_id:<10}]({url:<55}): Add {add_count} items")
                reschedule(1200)

        except requests.exceptions.HTTPError as http_error:
            response: requests.Response = http_error.response
            logger.warning(f"[{rss_id:<10}]({url:<55}): {http_error}")
            text = crawl.response_to_text.response_to_text(url, response)
            crud.create_rss_response_record(db, rss_id, url, text, response.status_code)
            reschedule(3600)

            if not crud.get_rss(db, rss_id).is_active:
                logger.info(f"[{rss_id:<10}]({url:<55}): Remove job")
                scheduler.remove_job(f"{rss_id}")

        except requests.exceptions.ConnectionError:
            logger.info(f"[{rss_id:<10}]({url:<55}): Connection Error, Remove job")
            crud.update_rss_active(db, rss_id, False)
            scheduler.remove_job(f"{rss_id}")

        except Exception as e:
            logger.warning(f"[{rss_id:<10}]({url:<55}): {e}")
            if not crud.get_rss(db, rss_id).is_active:
                logger.info(f"[{rss_id:<10}]({url:<55}): Remove job")
                scheduler.remove_job(f"{rss_id}")
            pass
    pass
