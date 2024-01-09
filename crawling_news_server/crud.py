from __future__ import annotations

from typing import List, Type, Union, Dict

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from . import models, schemas
from .models import RSS, RSSItem


def get_rss(db: Session, rss_id: int) -> models.RSS | None:
    return db.query(models.RSS).filter(models.RSS.id == rss_id).first()


def get_rss_all(db: Session) -> List[Type[RSS]]:
    return db.query(models.RSS).filter(models.RSS.is_active == 1).all()


def get_rss_by_url(db: Session, url: str) -> models.RSS | None:
    return db.query(models.RSS).filter(models.RSS.url == url).first()


def create_rss(db: Session, rss: schemas.ItemRSSCreate):
    db_rss = models.RSS(
        name=rss.name,
        url=rss.url,
        title=rss.title,
        description=rss.description,
        link=rss.link,
        delay=rss.delay,
        category=rss.category
    )
    db.add(db_rss)
    db.commit()
    db.refresh(db_rss)
    return db_rss


def update_rss_active(db: Session, rss_id: int, is_active: bool) -> models.RSS | None:
    db_rss = get_rss(db, rss_id)
    if not db_rss:
        return None
    db_rss.is_active = is_active
    db.add(db_rss)
    db.commit()
    db.refresh(db_rss)
    return db_rss


def update_rss_obj(db: Session, db_rss: models.RSS) -> models.RSS | None:
    db.add(db_rss)
    db.commit()
    db.refresh(db_rss)
    return db_rss


def update_rss_from_rss_dict(db: Session, rss_id: int, feed: dict[str, str | None]) -> None:
    db_rss = get_rss(db, rss_id)

    db_rss.title = feed.get("title", db_rss.title)
    db_rss.description = feed.get("description", db_rss.description)
    db_rss.language = feed.get("language", db_rss.language)
    db_rss.copyright = feed.get("rights", db_rss.copyright)
    db_rss.last_build_date = feed.get("updated", db_rss.last_build_date)
    db_rss.web_master = feed.get("publisher", db_rss.web_master)

    return update_rss_obj(db, db_rss)


def get_rss_item_by_rss_id_and_link(db: Session, rss_id: int, link: str) -> models.RSSItem | None:
    return db.query(models.RSSItem).filter(models.RSSItem.rss_id == rss_id, models.RSSItem.link == link).first()


def create_rss_item(db: Session, rss_id: int, rss_item: schemas.ItemRssItemCreate):
    db_rss_item = models.RSSItem(
        rss_id=rss_id,
        title=rss_item.title,
        description=rss_item.description,
        link=rss_item.link,
        author=rss_item.author,
        category=rss_item.category,
        comments=rss_item.comments,
        enclosure=rss_item.enclosure,
        guid=rss_item.guid,
        pub_date=rss_item.pub_date,
        source=rss_item.source,
        extra=rss_item.extra,
    )
    db.add(db_rss_item)
    db.commit()
    db.refresh(db_rss_item)
    return db_rss_item


def create_rss_response_record(db: Session, rss_id: int, link: str, body: str, status_code: int = 200):
    db_response_record = models.ResponseRecord(
        rss_id=rss_id,
        link=link,
        body=body,
        status_code=status_code
    )

    db.add(db_response_record)
    db.commit()
    db.refresh(db_response_record)
    return db_response_record


def find_rss_title(db: Session, title: str, page_number: int, page_limit: int) -> dict[str, Union[int, list[Type[models.RSSItem]]]]:
    """
    https://gist.github.com/jas-haria/a993d4ef213b3c0dd1500f86d31ad749
    https://stackoverflow.com/questions/4186062/sqlalchemy-order-by-descending

    """
    query = db.query(models.RSSItem).filter(
        and_(*[models.RSSItem.title.like(f"%{word}%") for word in title.split()])
    ).order_by(models.RSSItem.id.desc())
    length = query.count()
    if page_number > 0:
        query = query.offset((page_number - 1) * page_limit)
    query = query.limit(page_limit)
    return {
        "total_count": length,
        "data": query.all()
    }


def get_rss_responses(db: Session, rss_id: int, page_number: int, page_limit: int) -> dict[str, list[Type[models.ResponseRecord]] | int]:
    query = (db
             .query(models.ResponseRecord)
             .filter_by(rss_id=rss_id)
             .order_by(models.ResponseRecord.id.desc()))
    length = query.count()
    if page_number > 0:
        query = query.offset((page_number - 1) * page_limit)
    query = query.limit(page_limit)
    return {
        "total_count": length,
        "data": query.all()
    }


def get_all_rss_responses(db: Session, page_number: int, page_limit: int) -> dict[str, list[Type[models.ResponseRecord]] | int]:
    query = (db
             .query(models.ResponseRecord)
             .order_by(models.ResponseRecord.id.desc()))
    length = query.count()
    if page_number > 0:
        query = query.offset((page_number - 1) * page_limit)
    query = query.limit(page_limit)
    return {
        "total_count": length,
        "data": query.all()
    }


def get_rss_items(db: Session, rss_id: int, page_number: int, page_limit: int) -> dict[str, list[Type[RSSItem]] | int]:
    query = db.query(models.RSSItem).filter_by(rss_id=rss_id).order_by(models.RSSItem.id.desc())
    length = query.count()
    if page_number > 0:
        query = query.offset((page_number - 1) * page_limit)
    query = query.limit(page_limit)
    return {
        "total_count": length,
        "data": query.all()
    }


def get_all_rss(db: Session, page_number: int, page_limit: int) -> dict[str, list[Type[RSS]] | int]:
    query = db.query(models.RSS).order_by(models.RSS.id.desc())
    length = query.count()
    if page_number > 0:
        query = query.offset((page_number - 1) * page_limit)
    query = query.limit(page_limit)
    return {
        "total_count": length,
        "data": query.all()
    }


def get_all_rss_search(db: Session, q: str, page_number: int, page_limit: int) -> dict[str, list[Type[RSS]] | int]:
    filter_list = [models.RSS.name.like(f"%{word}%") for word in q.split()]
    filter_list.extend([models.RSS.title.like(f"%{word}%") for word in q.split()])
    filter_list.extend([models.RSS.description.like(f"%{word}%") for word in q.split()])
    filter_list.extend([models.RSS.category.like(f"%{word}%") for word in q.split()])
    query = (db.query(models.RSS)
             .filter(or_(*filter_list))
             .order_by(models.RSS.id.desc()))
    length = query.count()
    if page_number > 0:
        query = query.offset((page_number - 1) * page_limit)
    query = query.limit(page_limit)
    return {
        "total_count": length,
        "data": query.all()
    }
