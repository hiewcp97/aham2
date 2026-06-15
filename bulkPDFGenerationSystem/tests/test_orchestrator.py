import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bulkPDFGenerationSystem.models import Base, Job, JobBatch, JobItem, JobStatus
from bulkPDFGenerationSystem.orchestrator import orchestrate_job
from bulkPDFGenerationSystem.services import sqs_service

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

def test_orchestrate_job_chunks_correctly(db):
    # Setup
    job_id = "test-job"
    items = [{"data": i} for i in range(12)] # 12 items, BATCH_SIZE=5 -> 3 batches
    job = Job(id=job_id, total_items=12)
    db.add(job)
    db.commit()
    
    # Execute
    orchestrate_job(job_id, items, db)
    
    # Verify
    batches = db.query(JobBatch).filter(JobBatch.job_id == job_id).all()
    assert len(batches) == 3
    assert batches[0].total_items == 5
    assert batches[1].total_items == 5
    assert batches[2].total_items == 2
    
    # Verify items
    items_count = db.query(JobItem).filter(JobItem.job_id == job_id).count()
    assert items_count == 12
    
    # Verify SQS messages
    assert sqs_service.get_queue_depth() == 3
    # Clean up SQS for other tests
    while sqs_service.receive_message(): pass

def test_job_idempotency_logic(db):
    # This would usually be in main.py, but we can test the model/DB level unique constraint
    job1 = Job(id="job1", idempotency_key="key1")
    db.add(job1)
    db.commit()
    
    import sqlalchemy.exc
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        job2 = Job(id="job2", idempotency_key="key1")
        db.add(job2)
        db.commit()
