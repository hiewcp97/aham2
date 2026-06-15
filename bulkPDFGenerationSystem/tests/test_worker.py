import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bulkPDFGenerationSystem.models import Base, Job, JobBatch, JobItem, JobStatus, BatchStatus, ItemStatus
from bulkPDFGenerationSystem.worker import process_item, worker_process
from bulkPDFGenerationSystem.services import sqs_service, s3_service

# Setup in-memory SQLite for testing
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_process_item_success(db):
    # Setup
    item_id = "item-success"
    item = JobItem(id=item_id, input_data={"data": {"name": "Test"}}, status=ItemStatus.PENDING)
    db.add(item)
    db.commit()
    
    # Execute
    success = process_item(db, item_id)
    
    # Verify
    assert success is True
    updated_item = db.query(JobItem).filter(JobItem.id == item_id).first()
    assert updated_item.status == ItemStatus.COMPLETED
    assert updated_item.s3_uri is not None
    assert "s3://" in updated_item.s3_uri

def test_process_item_failure(db):
    # Setup
    item_id = "item-fail"
    item = JobItem(id=item_id, input_data={"data": {"simulate_failure": True}}, status=ItemStatus.PENDING)
    db.add(item)
    db.commit()
    
    # Execute
    success = process_item(db, item_id)
    
    # Verify
    assert success is False
    updated_item = db.query(JobItem).filter(JobItem.id == item_id).first()
    assert updated_item.status == ItemStatus.FAILED
    assert "Simulated PDF generation failure" in updated_item.error_message
