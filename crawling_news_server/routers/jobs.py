from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from crawling_news_server import crud, schemas
from crawling_news_server.database import get_db
from crawling_news_server.jobs import add_job_rss_crawling, scheduler

router = APIRouter(
    prefix="/api/v2/jobs",
    tags=["jobs"]
)


@router.get("/")
async def get_jobs():
    jobs = scheduler.get_jobs()
    return [{
        "id": job.id,
        "name": job.name,
        "next": f"{job.next_run_time}"
    } for job in jobs]


@router.post("/")
async def create_job(rss_id: int, db: Session = Depends(get_db)):
    db_rss = crud.get_rss(db, rss_id)
    if not db_rss:
        raise HTTPException(status_code=404, detail="RSS not found")
    add_job_rss_crawling(db_rss)
    return db_rss


@router.delete("/{job_id}")
async def delete_job(job_id: int):
    job = scheduler.get_job(f"{job_id}")
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_data = {
        "id": job.id,
        "name": job.name,
        "next": f"{job.next_run_time}"
    }
    scheduler.remove_job(f"{job_id}")
    return job_data
