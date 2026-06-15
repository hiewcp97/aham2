# Bulk PDF Generation Service Bulk PDF Generation System

This is a Python-based Bulk PDF Generation System of a scalable bulk PDF generation system, designed according to the specifications in `problem.md` and the architecture in `architecture.md`.

## System Overview

The system follows an asynchronous, event-driven architecture to handle large-scale PDF generation requests without blocking the API. It implements a three-tier hierarchy for processing:

1.  **Job**: The top-level bulk request from the user.
2.  **JobBatch**: Chunks of work (e.g., 5-100 items per batch) published to the queue to balance throughput and cost.
3.  **JobItem**: Individual PDF generation tasks tracked for granular progress and failure reporting.

### Core Components:
- **API Service (FastAPI):** Handles job submission, status polling, and batch/item listing.
- **Job Orchestrator:** Chunks bulk requests into batches and enqueues them into the message queue. Includes logic to retry failed items.
- **Message Queue (Simulated SQS):** Decouples the API from the worker pool.
- **Worker Pool:** Processes batches of items, generates PDFs using `ReportLab`, and "uploads" them to storage.
- **Metadata Store (SQLite/SQLAlchemy):** Tracks the state of jobs, batches, and individual items.
- **Object Storage (Simulated S3):** Stores the generated PDF files.

## Project Structure

```text
bulkPDFGenerationSystem/
├── main.py                 # FastAPI API Service
├── orchestrator.py         # Job chunking and retry logic
├── worker.py               # Background task processor
├── pdf_generator.py        # PDF rendering logic (ReportLab)
├── models.py               # SQLAlchemy Database models (Job, Batch, Item)
├── database.py             # Database connection and session management
├── services.py             # Simulated AWS SQS and S3 services
├── run.py                  # Entry point to run API and Worker concurrently
├── requirements.txt        # Project dependencies
├── stress_test.js          # K6 stress testing script
├── test_client.py          # Standard integration test client
├── test_failure.py         # Partial failure simulation test
├── test_retry.py           # Full retry-to-success lifecycle test
├── metadata.db             # SQLite database (generated at runtime)
├── outputs/                # Temporary directory for local PDF generation
├── storage/                # Simulated S3 bucket storage
└── tests/                  # Pytest unit tests
    ├── test_orchestrator.py
    └── test_worker.py
```

## Prerequisites

- Python 3.9+
- [K6](https://k6.io/docs/get-started/installation/) (for stress testing)

## Setup and Installation

1. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   ```

2. **Activate the virtual environment:**
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```
   - **Windows:**
     ```bash
     .\venv\Scripts\activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r bulkPDFGenerationSystem/requirements.txt
   ```

## How to Run

1. **Run the system (API + Worker):**
   ```bash
   python3 -m bulkPDFGenerationSystem.run
   ```
   *Note: Ensure your virtual environment is activated. If python3 not working can try python -m xxxx*

2. **Run the standard test client:**
   In a separate terminal:
   ```bash
   python3 -m bulkPDFGenerationSystem.test_client
   ```

3. **Run the failure simulation test:**
   ```bash
   python3 -m bulkPDFGenerationSystem.test_failure
   ```

4. **Run the retry-to-success lifecycle test:**
   ```bash
   python3 -m bulkPDFGenerationSystem.test_retry
   ```

## API Documentation

The system provides a RESTful API for job management and status tracking. By default, interactive documentation (Swagger UI) is available at `http://localhost:8000/docs`.

### 1. Job Submission
**Endpoint:** `POST /jobs`  
**Description:** Submits a new bulk PDF generation job.  
**Request Body:**
```json
{
  "idempotency_key": "unique-uuid-or-client-id",
  "items": [
    {
      "user_id": "customer_123",
      "data": { "name": "John Doe", "amount": 1500, "date": "2026-06-15" }
    }
  ]
}
```
**Response:** `200 OK`
```json
{
  "job_id": "uuid-string",
  "status": "PENDING",
  "total_items": 1
}
```

### 2. Job Status Polling
**Endpoint:** `GET /jobs/{job_id}`  
**Description:** Retrieves the high-level status and progress of a job.  
**Response:** `200 OK`
```json
{
  "job_id": "uuid-string",
  "status": "PROCESSING",
  "total_items": 100,
  "completed": 45,
  "failed": 2,
  "progress": "47.00%"
}
```

### 3. List Job Batches
**Endpoint:** `GET /jobs/{job_id}/batches`  
**Description:** Lists the status of all batches within a job.  
**Response:** `200 OK`
```json
[
  {
    "batch_id": "uuid-string",
    "status": "SUCCESS",
    "total_items": 5,
    "completed": 5,
    "failed": 0
  }
]
```

### 4. List Job Items
**Endpoint:** `GET /jobs/{job_id}/items`  
**Description:** Lists detailed status and S3 URIs for all items in a job.  
**Response:** `200 OK`
```json
[
  {
    "item_id": "uuid-string",
    "batch_id": "uuid-string",
    "status": "COMPLETED",
    "s3_uri": "s3://bucket/filename.pdf",
    "error": null
  }
]
```

### 5. Download Item
**Endpoint:** `GET /jobs/{job_id}/items/{item_id}/download`  
**Description:** Generates a URL to retrieve the generated PDF. (Simulated in this prototype).  
**Response:** `200 OK`
```json
{
  "download_url": "/absolute/path/to/local/storage/file.pdf"
}
```

### 6. Retry Failed Items (Administrative)
**Endpoint:** `POST /jobs/{job_id}/retry`  
**Description:** Automatically re-queues all failed items for a specific job.  
**Response:** `200 OK`
```json
{
  "job_id": "uuid-string",
  "retried_count": 2,
  "status": "PROCESSING",
  "message": "2 items re-queued"
}
```

## Stress Testing (K6)

The Bulk PDF Generation System includes a sample stress test script using [K6](https://k6.io/).
**This is useful to check the current setup able to handle high traffic or not**

1. **Install K6:**
   Follow the [official installation guide](https://k6.io/docs/get-started/installation/).

2. **Run the stress test:**
   Ensure the system is running, then execute:
   ```bash
   k6 run bulkPDFGenerationSystem/stress_test.js
   ```

The script will ramp up virtual users and measure the latency and success rate of job submissions.

## Testing

### Unit Tests
The Bulk PDF Generation System includes a suite of unit tests using `pytest` to verify core logic:
```bash
python3 -m pytest bulkPDFGenerationSystem/tests/
```
Tests cover:
- **Orchestrator**: Correct chunking of items into batches and retry re-queuing logic.
- **Worker**: Item processing success/failure logic and state updates.
- **Models**: Database constraints and relationships.

### Functional Testing
- `test_failure.py`: Verifies that the system correctly reports a `PARTIAL_FAILURE` state while completing successful items.
- `test_retry.py`: Demonstrates a full recovery lifecycle: initial failure -> fix in database -> successful retry to completion.

## Database Inspection

Since the Bulk PDF Generation System uses SQLite, you can easily inspect the system state using the `sqlite3` command-line tool.

1. **Open the database:**
   ```bash
   sqlite3 bulkPDFGenerationSystem/metadata.db
   ```

2. **Common queries:**
   - **Check all jobs:**
     ```sql
     SELECT id, status, completed_count, failed_count FROM jobs;
     ```
   - **Check batches for a specific job:**
     ```sql
     SELECT id, status, total_items FROM job_batches WHERE job_id = 'YOUR_JOB_ID';
     ```
   - **Count completed items:**
     ```sql
     SELECT status, COUNT(*) FROM job_items GROUP BY status;
     ```
   - **View failed items and their errors:**
     ```sql
     SELECT id, error_message FROM job_items WHERE status = 'FAILED';
     ```

3. **Exit sqlite3:** Type `.exit` or press `Ctrl+D`.

## Design Rationale

- **Batching Strategy**: Instead of 100k individual messages, the system sends batches (e.g., 50 items per message). This dramatically reduces SQS costs and API overhead while maintaining high throughput.
- **Idempotency**: The `idempotency_key` at the API layer prevents duplicate processing of retried bulk requests.
- **Granular Visibility**: By tracking each `JobItem`, the system provides precise progress metrics (e.g., "85,400 / 100,000 completed") and specific error messages for failed documents.
- **Resilience**: A failure in one PDF does not crash the entire batch. The worker continues processing and reports the specific failure to the database.
- **Administrative Recovery**: The explicit retry endpoint allows operators to recover from systemic failures without requiring callers to resubmit massive bulk payloads.

## Known Limitations & Future Improvements

- **Horizontal Scaling**: In production, workers would run in independent containers (ECS) scaling based on SQS queue depth.
- **Database Proxy**: A real system would use RDS Proxy to manage connection pooling during massive scale-out events.
- **Dead Letter Queues (DLQ)**: While status tracking is implemented, a production system would use SQS DLQs to handle "poison pill" messages after multiple retries.
