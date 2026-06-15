import os
import shutil
import queue
import uuid
import logging

# Simulation of S3
class S3Service:
    def __init__(self, storage_dir="bulkPDFGenerationSystem/storage"):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def upload_file(self, file_path, object_name):
        dest_path = os.path.join(self.storage_dir, object_name)
        shutil.copy(file_path, dest_path)
        return f"s3://bulk-pdf-bucket/{object_name}"

    def get_download_url(self, s3_uri):
        # In a real S3 service, this would return a pre-signed URL.
        # Here we just return a local path for simulation.
        object_name = s3_uri.split("/")[-1]
        return os.path.abspath(os.path.join(self.storage_dir, object_name))

# Simulation of SQS
class SQSService:
    def __init__(self):
        self.queue = queue.Queue()

    def send_message(self, message_body):
        self.queue.put(message_body)

    def receive_message(self):
        try:
            return self.queue.get(block=False)
        except queue.Empty:
            return None

    def delete_message(self, message):
        # In simulation, get() already removes it. 
        # In real SQS, you need to delete it using receipt handle.
        pass

    def get_queue_depth(self):
        return self.queue.qsize()

s3_service = S3Service()
sqs_service = SQSService()
