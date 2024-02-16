import os
from contextlib import contextmanager
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()
# https://ca.ramel.be/117
# https://viewise.tistory.com/entry/Ubuntu-2204-Wake-on-lan-%EC%84%A4%EC%A0%95-%EC%84%9C%EB%B9%84%EC%8A%A4%EB%A1%9C-%EB%93%B1%EB%A1%9D%ED%95%98%EA%B8%B0
# https://engpro.tistory.com/434
# https://pimylifeup.com/ubuntu-enable-wake-on-lan/
# https://necromuralist.github.io/posts/enabling-wake-on-lan/
# https://ccclog.tistory.com/104

# https://www.cyberciti.biz/faq/how-to-setup-mariadb-ssl-and-secure-connections-from-clients/
# https://docs.sqlalchemy.org/en/14/dialects/mysql.html#ssl-connections
# https://4urdev.tistory.com/82
# https://ddart.net/xe/board/12867

# https://wikidocs.net/87477

SQLALCHEMY_DATABASE_URL = os.environ.get("DB_PATH")

connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL.split("//")[0]:
    connect_args['check_same_thread'] = False
else:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL + '?ssl=true'
    connect_args = {
        "ssl": {
            "ssl_ca": "ca.pem",
            "ssl_cert": "client-cert.pem",
            "ssl_key": "client-key.pem"
        }
    }

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_size=100
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_context_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()