from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from sqlalchemy.sql import func
from sqlalchemy import ForeignKey, String, Text, DateTime, text, Engine
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql.types import LONGTEXT
from sqlalchemy.inspection import inspect

from .database import Base


class RSS(Base):
    __tablename__ = "rss"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(1024))
    url: Mapped[str] = mapped_column(String(768), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    delay: Mapped[int] = mapped_column(server_default='60')

    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    link: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Optional
    category: Mapped[Optional[str]] = mapped_column(String(128))
    cloud: Mapped[Optional[str]] = mapped_column(String(128))
    copyright: Mapped[Optional[str]] = mapped_column(String(128))
    docs: Mapped[Optional[str]] = mapped_column(Text)
    generator: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(String(128))
    last_build_date: Mapped[Optional[str]] = mapped_column(String(128))
    managing_editor: Mapped[Optional[str]] = mapped_column(String(128))
    pub_date: Mapped[Optional[str]] = mapped_column(String(128))
    rating: Mapped[Optional[str]] = mapped_column(String(128))
    skip_hours: Mapped[Optional[str]] = mapped_column(String(128))
    text_input: Mapped[Optional[str]] = mapped_column(String(128))
    ttl: Mapped[Optional[str]] = mapped_column(String(128))
    web_master: Mapped[Optional[str]] = mapped_column(String(128))

    extra: Mapped[Optional[str]] = mapped_column(Text)

    publish_date: Mapped[str] = mapped_column(String(11), default="", server_default="")
    publish_time: Mapped[str] = mapped_column(String(22), default="", server_default="")
    publish_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), server_default=func.now())

    image: Mapped["RSSImage"] = relationship("RSSImage", back_populates="rss")
    items: Mapped[List["RSSItem"]] = relationship()
    responses: Mapped[List["ResponseRecord"]] = relationship(lazy=True)


class RSSImage(Base):
    __tablename__ = "rss_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    link: Mapped[str] = mapped_column(String(1024), nullable=False)
    width: Mapped[Optional[str]] = mapped_column(String(64))
    height: Mapped[Optional[str]] = mapped_column(String(64))

    rss_id: Mapped[int] = mapped_column(ForeignKey("rss.id"))
    rss: Mapped["RSS"] = relationship(back_populates="image")


class RSSItem(Base):
    __tablename__ = "rss_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    link: Mapped[str] = mapped_column(String(768), nullable=False, index=True)

    # Optional
    author: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(128))
    comments: Mapped[Optional[str]] = mapped_column(Text)
    enclosure: Mapped[Optional[str]] = mapped_column(Text)
    guid: Mapped[Optional[str]] = mapped_column(String(1024))
    pub_date: Mapped[Optional[str]] = mapped_column(String(128))
    source: Mapped[Optional[str]] = mapped_column(Text)

    extra: Mapped[Optional[str]] = mapped_column(Text)

    publish_date: Mapped[str] = mapped_column(String(11), default="", server_default="")
    publish_time: Mapped[str] = mapped_column(String(22), default="", server_default="")
    publish_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), server_default=func.now())

    rss_id: Mapped[int] = mapped_column(ForeignKey("rss.id"))
    rss = relationship("RSS", back_populates="items")

    @classmethod
    def create_fulltext_index(cls, engine: Engine):
        index_name = 'title_fulltext_index'
        inspector = inspect(engine)
        with engine.connect() as conn:
            # if not engine.dialect.has_index(conn, index_name, cls.__tablename__):
            if not any(index['name'] == index_name for index in inspector.get_indexes(cls.__tablename__)):
                index_query = text(f'CREATE FULLTEXT INDEX {index_name} ON {cls.__tablename__} (title)')
                conn.execute(index_query)


class ResponseEncoding(Base):
    __tablename__ = "response_encodings"

    id: Mapped[int] = mapped_column(primary_key=True)
    link: Mapped[str] = mapped_column(String(768), nullable=False, index=True)
    encoding: Mapped[str] = mapped_column(String(768), nullable=False, index=True)


class ResponseRecord(Base):
    __tablename__ = "response_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    link: Mapped[str] = mapped_column(String(768), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(server_default="200")
    body: Mapped[str] = mapped_column(LONGTEXT)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rss_id: Mapped[int] = mapped_column(ForeignKey("rss.id"))
    rss = relationship("RSS", back_populates="responses", lazy=True)
