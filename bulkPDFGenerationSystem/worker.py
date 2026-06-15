import time
import logging
import os
import uuid
from .services import sqs_service, s3_service
from .pdf_generator import generate_pdf
from .database import SessionLocal
from .models import Job, JobBatch, JobItem, JobStatus, BatchStatus, ItemStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_item(db, item_id):
    """
    Processes a single PDF generation item.
    """
    item = db.query(JobItem).filter(JobItem.id == item_id).first()
    if not item:
        logger.error(f"Item {item_id} not found in DB")
        return False

    try:
        item.status = ItemStatus.PROCESSING
        db.commit()

        logger.info(f"Generating PDF for item {item_id} with data: {item.input_data}")
        # Generate PDF
        output_filename = f"{item_id}.pdf"
        local_path = f"bulkPDFGenerationSystem/outputs/{output_filename}"
        generate_pdf(item.input_data.get("data", {}), local_path)

        # Upload to simulated S3
        s3_uri = s3_service.upload_file(local_path, output_filename)

        # Clean up
        if os.path.exists(local_path):
            os.remove(local_path)

        # Update Item
        item.status = ItemStatus.COMPLETED
        item.s3_uri = s3_uri
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error processing item {item_id}: {str(e)}")
        item.status = ItemStatus.FAILED
        item.error_message = str(e)
        db.commit()
        return False

def worker_process():
    """
    Simulates a worker pulling batches from SQS and processing them.
    """
    logger.info("Worker started. Polling for batches...")
    
    while True:
        message = sqs_service.receive_message()
        if message:
            batch_id = message.get("batch_id")
            job_id = message.get("job_id")
            item_ids = message.get("item_ids", [])
            
            logger.info(f"Processing batch {batch_id} for job {job_id} ({len(item_ids)} items)")
            
            db = SessionLocal()
            try:
                # 1. Update Batch status to PROCESSING
                batch = db.query(JobBatch).filter(JobBatch.id == batch_id).first()
                if batch:
                    batch.status = BatchStatus.PROCESSING
                    db.commit()

                # 2. Process all items in the batch
                completed_in_batch = 0
                failed_in_batch = 0
                
                for item_id in item_ids:
                    success = process_item(db, item_id)
                    if success:
                        completed_in_batch += 1
                    else:
                        failed_in_batch += 1
                
                # 3. Update Batch summary
                if batch:
                    batch.completed_count = completed_in_batch
                    batch.failed_count = failed_in_batch
                    batch.status = BatchStatus.SUCCESS if failed_in_batch == 0 else BatchStatus.FAILED
                
                # 4. Update parent Job summary
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.completed_count += completed_in_batch
                    job.failed_count += failed_in_batch
                    
                    if job.completed_count + job.failed_count == job.total_items:
                        if job.failed_count == 0:
                            job.status = JobStatus.COMPLETED
                        elif job.completed_count == 0:
                            job.status = JobStatus.FAILED
                        else:
                            job.status = JobStatus.PARTIAL_FAILURE
                
                db.commit()
                logger.info(f"Finished batch {batch_id}. Success: {completed_in_batch}, Failed: {failed_in_batch}")
                
            except Exception as e:
                logger.error(f"Unexpected error in batch {batch_id}: {str(e)}")
                db.rollback()
            finally:
                db.close()
                sqs_service.delete_message(message)
        else:
            time.sleep(1)

if __name__ == "__main__":
    worker_process()
