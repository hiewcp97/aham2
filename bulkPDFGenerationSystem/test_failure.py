import requests
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_partial_failure():
    print("\n--- Starting Partial Failure Test ---")
    # 1. Prepare a request where some items fail
    items = []
    for i in range(5):
        items.append({
            "user_id": f"user_success_{i}",
            "data": {"name": f"Successful Customer {i}"}
        })
    
    # Add 2 items that will fail
    for i in range(2):
        items.append({
            "user_id": f"user_fail_{i}",
            "data": {
                "name": f"Failing Customer {i}",
                "simulate_failure": True
            }
        })
    
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "items": items
    }
    
    # 2. Submit the job
    print(f"Submitting bulk job with {len(items)} items (expecting 2 failures)...")
    response = requests.post(f"{BASE_URL}/jobs", json=payload)
    job_id = response.json()["job_id"]
    
    # 3. Poll for status
    while True:
        status_data = requests.get(f"{BASE_URL}/jobs/{job_id}").json()
        print(f"Status: {status_data['status']} | Progress: {status_data['progress']} | Completed: {status_data['completed']} | Failed: {status_data['failed']}")
        
        if status_data["status"] in ["COMPLETED", "FAILED", "PARTIAL_FAILURE"]:
            break
        time.sleep(2)
    
    # 4. Check items
    items_list = requests.get(f"{BASE_URL}/jobs/{job_id}/items").json()
    failed_items = [i for i in items_list if i["status"] == "FAILED"]
    print(f"Verified {len(failed_items)} items failed with error: {failed_items[0]['error'] if failed_items else 'None'}")

if __name__ == "__main__":
    test_partial_failure()
