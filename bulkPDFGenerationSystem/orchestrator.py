import uuid
import logging
from sqlalchemy.orm import Session
from .models import Job, JobBatch, JobItem, JobStatus, BatchStatus, ItemStatus
from .services import sqs_service

logger = logging.getLogger(__name__)

BATCH_SIZE = 5  # Small batch size for Bulk PDF Generation System demonstration

def orchestrate_job(job_id: str, items_payload: list, db: Session):
    """
    Chunks a bulk job into batches and enqueues them.
    """
    logger.info(f"Orchestrating job {job_id} with {len(items_payload)} items")
    
    # 1. Update job status to PROCESSING
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = JobStatus.PROCESSING
    db.commit()
    
    # 2. Chunk items into batches
    for i in range(0, len(items_payload), BATCH_SIZE):
        batch_id = str(uuid.uuid4())
        chunk = items_payload[i : i + BATCH_SIZE]
        
        # Create JobBatch record
        new_batch = JobBatch(
            id=batch_id,
            job_id=job_id,
            status=BatchStatus.PENDING,
            total_items=len(chunk)
        )
        db.add(new_batch)
        db.flush() # Ensure batch_id is available for items
        
        batch_item_ids = []
        for data in chunk:
            item_id = str(uuid.uuid4())
            new_item = JobItem(
                id=item_id,
                job_id=job_id,
                batch_id=batch_id,
                status=ItemStatus.PENDING,
                input_data=data
            )
            db.add(new_item)
            batch_item_ids.append(item_id)
        
        # 3. Enqueue the batch message
        sqs_service.send_message({
            "job_id": job_id,
            "batch_id": batch_id,
            "item_ids": batch_item_ids
        })
        
    db.commit()
    logger.info(f"Finished enqueuing {len(items_payload)} items in batches for job {job_id}")

def retry_failed_items(job_id: str, db: Session):
    """
    Identifies failed items for a job and re-enqueues them in new batches.
    """
    failed_items = db.query(JobItem).filter(JobItem.job_id == job_id, JobItem.status == ItemStatus.FAILED).all()
    if not failed_items:
        logger.info(f"No failed items found for job {job_id}")
        return 0

    logger.info(f"Retrying {len(failed_items)} failed items for job {job_id}")
    
    # Update job state
    job = db.query(Job).filter(Job.id == job_id).first()
    job.status = JobStatus.PROCESSING
    job.failed_count -= len(failed_items)
    db.commit()

    # Re-chunk failed items into new batches
    for i in range(0, len(failed_items), BATCH_SIZE):
        batch_id = str(uuid.uuid4())
        chunk = failed_items[i : i + BATCH_SIZE]
        
        new_batch = JobBatch(
            id=batch_id,
            job_id=job_id,
            status=BatchStatus.PENDING,
            total_items=len(chunk)
        )
        db.add(new_batch)
        db.flush()
        
        item_ids = []
        for item in chunk:
            item.status = ItemStatus.PENDING
            item.batch_id = batch_id
            item.error_message = None
            item_ids.append(item.id)
            
        sqs_service.send_message({
            "job_id": job_id,
            "batch_id": batch_id,
            "item_ids": item_ids
        })
    
    db.commit()
    return len(failed_items)
