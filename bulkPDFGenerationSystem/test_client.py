import requests
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_bulk_generation():
    # 1. Prepare a bulk request
    items = []
    for i in range(10):  # Test with 10 items for the Bulk PDF Generation System
        items.append({
            "user_id": f"user_{i}",
            "data": {
                "name": f"Customer {i}",
                "amount": 100 * (i + 1),
                "date": "2026-06-15"
            }
        })
    
    payload = {
        "idempotency_key": str(uuid.uuid4()),
        "items": items
    }
    
    # 2. Submit the job
    print(f"Submitting bulk job with {len(items)} items...")
    response = requests.post(f"{BASE_URL}/jobs", json=payload)
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"Job submitted. ID: {job_id}")
    
    # 3. Poll for status
    while True:
        status_response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        status_data = status_response.json()
        print(f"Status: {status_data['status']} | Progress: {status_data['progress']} | Completed: {status_data['completed']}")
        
        if status_data["status"] in ["COMPLETED", "FAILED", "PARTIAL_FAILURE"]:
            break
        
        time.sleep(2)
    
    # 4. List items and download one
    items_response = requests.get(f"{BASE_URL}/jobs/{job_id}/items")
    items_list = items_response.json()
    
    if items_list:
        item_id = items_list[0]["item_id"]
        download_response = requests.get(f"{BASE_URL}/jobs/{job_id}/items/{item_id}/download")
        print(f"Download URL for first item: {download_response.json()['download_url']}")

if __name__ == "__main__":
    # Wait a bit for the server to start if running everything together
    time.sleep(2)
    test_bulk_generation()
