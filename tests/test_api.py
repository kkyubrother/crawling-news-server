import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from crawling_news_server.database import Base, get_db
from crawling_news_server.crawl.network import is_safe_url, safe_request_get
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_hello(client):
    response = client.get("/hello/world")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello world"}


def test_ssrf_protection():
    assert is_safe_url("http://127.0.0.1") is False
    assert is_safe_url("http://localhost:8000") is False
    assert is_safe_url("http://10.0.0.1") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data") is False
    assert is_safe_url("https://google.com") is True


def test_create_and_get_rss(client):
    # Create RSS
    payload = {
        "name": "Test News",
        "url": "https://example.com/rss",
        "title": "Test Title",
        "description": "Test Desc",
        "link": "https://example.com",
        "delay": 60,
        "category": "Test"
    }
    res = client.post("/api/v2/rss/", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Test News"
    rss_id = data["id"]

    # Get RSS list
    res_list = client.get("/api/v2/rss/")
    assert res_list.status_code == 200
    assert res_list.json()["total_count"] == 1

    # Get specific RSS
    res_single = client.get(f"/api/v2/rss/{rss_id}")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == rss_id


def test_ssrf_blocked_on_crawl_api(client):
    res = client.post("/api/v2/rss/crawl?url=http://127.0.0.1/admin")
    assert res.status_code == 400
    assert "Invalid or restricted URL" in res.json()["detail"]


def test_jobs_api(client):
    res = client.get("/api/v2/jobs/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
