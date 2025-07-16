import threading
import queue
import time
from io import BytesIO
import os
import requests

from .registry import get_handler

WEBHOOK_URL = "https://automatizacion.commerk.com:4444/webhook/8dafec2e-f35a-4c3c-bcae-2a395effe7e6"
MAX_RETRIES = 3


def process_and_send(bank_key: str, file_name: str, data: bytes) -> None:
    """Parse the PDF if needed and send it to the webhook."""
    file_basename = os.path.basename(file_name)
    print(f">>> STARTING PROCESS_AND_SEND for: {file_basename} ({len(data)} bytes) with bank_key: {bank_key}")
    
    # Only Bancolombia uses Textract processing
    if bank_key == "bancolombia_textract":
        print(f">>> PROCESSING WITH TEXTRACT: {file_basename}")
        handler = get_handler(bank_key)
        if not handler:
            raise ValueError(f"Banco '{bank_key}' no soportado")
            
        # Process with Textract and send JSON payload
        parser = handler["parser"]
        with BytesIO(data) as f:
            print(f">>> CALLING PARSER for: {file_basename}")
            payload = parser.parse(f)
        payload["file_name"] = file_basename
        payload["bank_key"] = bank_key
        
        print(f">>> SENDING JSON PAYLOAD to webhook for: {file_basename}")
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f">>> WEBHOOK RESPONSE for {file_basename}: {response.status_code}")
        print(f"Sent processed JSON payload for {bank_key}")
    else:
        # Send raw PDF file for external processing (all other banks)
        print(f">>> SENDING RAW PDF to webhook for: {file_basename}")
        response = requests.post(
            WEBHOOK_URL,
            files={"file": (file_basename, data, "application/pdf")},
            data={"bank_key": bank_key, "file_name": file_basename},
            timeout=10,
        )
        print(f">>> WEBHOOK RESPONSE for {file_basename}: {response.status_code}")
        print(f"Sent raw PDF file for {bank_key}")
    
    print(f">>> COMPLETED PROCESS_AND_SEND for: {file_basename}")


class UploadWorker:
    """Background worker that processes uploaded PDFs sequentially."""

    def __init__(self):
        self.queue: 'queue.Queue[tuple[str, str, bytes]]' = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def enqueue(self, bank_key: str, file_name: str, data: bytes) -> None:
        """Add a file to the processing queue."""
        print(f">>> ENQUEUING FILE: {file_name} for bank: {bank_key}, queue size before: {self.queue.qsize()}")
        self.queue.put((bank_key, file_name, data))
        print(f">>> FILE ENQUEUED: {file_name}, queue size after: {self.queue.qsize()}")

    def get_queue_status(self) -> dict:
        """Get current queue status for monitoring."""
        return {
            "queue_size": self.queue.qsize(),
            "thread_alive": self.thread.is_alive(),
            "thread_daemon": self.thread.daemon
        }

    def _run(self) -> None:
        print(">>> WORKER THREAD STARTED")
        while True:
            try:
                print(f">>> WAITING FOR FILES IN QUEUE (current size: {self.queue.qsize()})")
                bank_key, file_name, data = self.queue.get()
                print(f">>> PROCESSING FILE: {file_name} for bank: {bank_key}")
                
                success = False
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        print(f">>> ATTEMPT {attempt} for file: {file_name}")
                        process_and_send(bank_key, file_name, data)
                        print(f">>> SUCCESS: File {file_name} processed and sent")
                        success = True
                        break
                    except Exception as e:
                        print(f">>> ERROR on attempt {attempt} for {file_name}: {str(e)}")
                        if attempt < MAX_RETRIES:
                            print(f">>> RETRYING in 2 seconds... (attempt {attempt}/{MAX_RETRIES})")
                            time.sleep(2)
                        else:
                            print(f">>> FAILED ALL ATTEMPTS for file: {file_name}")
                            self._report_error(bank_key, file_name, e)

                if success:
                    print(f">>> ✅ COMPLETED: {file_name}")
                else:
                    print(f">>> ❌ FAILED: {file_name}")
                    
            except Exception as e:
                print(f">>> CRITICAL ERROR in worker thread: {str(e)}")
                # Continue processing even if there's a critical error
            finally:
                # ALWAYS mark task as done to prevent queue blocking
                try:
                    self.queue.task_done()
                    print(f">>> FINISHED PROCESSING, remaining queue size: {self.queue.qsize()}")
                except Exception as e:
                    print(f">>> Error marking task done: {str(e)}")

    def _report_error(self, bank_key: str, file_name: str, exc: Exception) -> None:
        print(f">>> REPORTING ERROR for file: {file_name}, error: {str(exc)}")
        try:
            response = requests.post(
                WEBHOOK_URL,
                json={"error": str(exc), "file": file_name, "bank_key": bank_key},
                timeout=10,
            )
            print(f">>> ERROR REPORTED to webhook for {file_name}: {response.status_code}")
        except Exception as e2:
            print("Webhook error after failure:", e2)


worker = UploadWorker()
