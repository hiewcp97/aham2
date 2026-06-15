import requests
import time
import uuid
from bulkPDFGenerationSystem.database import SessionLocal
from bulkPDFGenerationSystem.models import JobItem

BASE_URL = "http://localhost:8000"

def test_retry_lifecycle():
    print("\n--- Starting Retry Lifecycle Test ---")
    
    # 1. Submit job with items that will fail
    items = []
    for i in range(5):
        items.append({
            "user_id": f"user_retry_{i}",
            "data": {
                "name": f"Retry Customer {i}",
                "simulate_failure": True
            }
        })
    
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "items": items
    }
    
    print(f"Submitting job with {len(items)} items (all will fail initially)...")
    response = requests.post(f"{BASE_URL}/jobs", json=payload)
    job_id = response.json()["job_id"]
    
    # 2. Wait for failures
    while True:
        status_data = requests.get(f"{BASE_URL}/jobs/{job_id}").json()
        print(f"Status: {status_data['status']} | Progress: {status_data['progress']} | Failed: {status_data['failed']}")
        
        if status_data["status"] == "FAILED":
            print("Job reached FAILED state as expected.")
            break
        time.sleep(2)

    # 3. "Fix" the items in the DB by removing the failure flag
    print("Simulating a 'fix' by removing failure flags in the database...")
    from sqlalchemy.orm.attributes import flag_modified
    db = SessionLocal()
    failed_items = db.query(JobItem).filter(JobItem.job_id == job_id).all()
    for item in failed_items:
        # Update input_data to remove simulate_failure
        new_data = item.input_data.copy()
        if "data" in new_data and "simulate_failure" in new_data["data"]:
            del new_data["data"]["simulate_failure"]
        item.input_data = new_data
        flag_modified(item, "input_data")
    db.commit()
    db.close()

    # 4. Trigger retry
    print(f"Triggering retry for job {job_id}...")
    retry_response = requests.post(f"{BASE_URL}/jobs/{job_id}/retry")
    print(f"Retry response: {retry_response.json()}")

    # 5. Wait for success
    while True:
        status_data = requests.get(f"{BASE_URL}/jobs/{job_id}").json()
        print(f"Status: {status_data['status']} | Progress: {status_data['progress']} | Completed: {status_data['completed']}")
        
        if status_data["status"] == "COMPLETED":
            print("Job successfully completed after retry!")
            break
        elif status_data["status"] == "FAILED":
            print("Job failed again. Something is wrong.")
            break
        time.sleep(2)

if __name__ == "__main__":
    test_retry_lifecycle()
