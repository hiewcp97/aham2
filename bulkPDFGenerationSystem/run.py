import threading
import uvicorn
import time
from bulkPDFGenerationSystem.main import app
from bulkPDFGenerationSystem.worker import worker_process

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def run_worker():
    worker_process()

if __name__ == "__main__":
    # Start worker in a separate thread
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()
    
    # Start API in the main thread
    run_api()
