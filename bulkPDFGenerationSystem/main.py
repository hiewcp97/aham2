from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
import uuid
from typing import List
from pydantic import BaseModel

from .database import init_db, get_db
from .models import Job, JobBatch, JobItem, JobStatus, BatchStatus, ItemStatus
from .orchestrator import orchestrate_job, retry_failed_items
from .services import s3_service

app = FastAPI(title="Bulk PDF Generation Service")

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    # Force re-creation of tables to reflect model changes
    from .database import engine
    from .models import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# Pydantic models for API
class PDFItem(BaseModel):
    user_id: str
    data: dict

class JobRequest(BaseModel):
    idempotency_key: str
    items: List[PDFItem]

class JobResponse(BaseModel):
    job_id: str
    status: str
    total_items: int

@app.post("/jobs", response_model=JobResponse)
def create_job(request: JobRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Check for idempotency
    existing_job = db.query(Job).filter(Job.idempotency_key == request.idempotency_key).first()
    if existing_job:
        return JobResponse(
            job_id=existing_job.id,
            status=existing_job.status.value,
            total_items=existing_job.total_items
        )

    job_id = str(uuid.uuid4())
    new_job = Job(
        id=job_id,
        idempotency_key=request.idempotency_key,
        status=JobStatus.PENDING,
        total_items=len(request.items)
    )
    db.add(new_job)
    db.commit()

    # Trigger orchestrator asynchronously
    background_tasks.add_task(orchestrate_job, job_id, [item.dict() for item in request.items], db)

    return JobResponse(
        job_id=job_id,
        status="PENDING",
        total_items=len(request.items)
    )

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.id,
        "status": job.status.value,
        "total_items": job.total_items,
        "completed": job.completed_count,
        "failed": job.failed_count,
        "progress": f"{(job.completed_count + job.failed_count) / job.total_items * 100:.2f}%" if job.total_items > 0 else "0%"
    }

@app.get("/jobs/{job_id}/batches")
def list_job_batches(job_id: str, db: Session = Depends(get_db)):
    batches = db.query(JobBatch).filter(JobBatch.job_id == job_id).all()
    return [
        {
            "batch_id": b.id,
            "status": b.status.value,
            "total_items": b.total_items,
            "completed": b.completed_count,
            "failed": b.failed_count
        } for b in batches
    ]

@app.get("/jobs/{job_id}/items")
def list_job_items(job_id: str, db: Session = Depends(get_db)):
    items = db.query(JobItem).filter(JobItem.job_id == job_id).all()
    return [
        {
            "item_id": item.id,
            "batch_id": item.batch_id,
            "status": item.status.value,
            "s3_uri": item.s3_uri,
            "error": item.error_message
        } for item in items
    ]

@app.get("/jobs/{job_id}/items/{item_id}/download")
def download_item(job_id: str, item_id: str, db: Session = Depends(get_db)):
    item = db.query(JobItem).filter(JobItem.id == item_id, JobItem.job_id == job_id).first()
    if not item or not item.s3_uri:
        raise HTTPException(status_code=404, detail="Item not found or not completed")
    
    download_url = s3_service.get_download_url(item.s3_uri)
    return {"download_url": download_url}

@app.post("/jobs/{job_id}/retry")
def retry_job(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    retried_count = retry_failed_items(job_id, db)
    
    return {
        "job_id": job_id,
        "retried_count": retried_count,
        "status": "PROCESSING",
        "message": f"{retried_count} items re-queued"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
