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
    
    # Only Bancolombia uses Textract processing
    if bank_key == "bancolombia_textract":
        handler = get_handler(bank_key)
        if not handler:
            raise ValueError(f"Banco '{bank_key}' no soportado")
            
        # Process with Textract and send JSON payload
        parser = handler["parser"]
        with BytesIO(data) as f:
            payload = parser.parse(f)
        payload["file_name"] = file_basename
        payload["bank_key"] = bank_key
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"Sent processed JSON payload for {bank_key}")
    else:
        # Send raw PDF file for external processing (all other banks)
        requests.post(
            WEBHOOK_URL,
            files={"file": (file_basename, data, "application/pdf")},
            data={"bank_key": bank_key, "file_name": file_basename},
            timeout=10,
        )
        print(f"Sent raw PDF file for {bank_key}")


class UploadWorker:
    """Background worker that processes uploaded PDFs sequentially."""

    def __init__(self):
        self.queue: 'queue.Queue[tuple[str, str, bytes]]' = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def enqueue(self, bank_key: str, file_name: str, data: bytes) -> None:
        """Add a file to the processing queue."""
        self.queue.put((bank_key, file_name, data))

    def _run(self) -> None:
        while True:
            bank_key, file_name, data = self.queue.get()
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    process_and_send(bank_key, file_name, data)
                    break
                except Exception as e:
                    print(f"Processing error on attempt {attempt} for {file_name}:", e)
                    if attempt < MAX_RETRIES:
                        time.sleep(2)
                    else:
                        self._report_error(bank_key, file_name, e)

            self.queue.task_done()

    def _report_error(self, bank_key: str, file_name: str, exc: Exception) -> None:
        try:
            requests.post(
                WEBHOOK_URL,
                json={"error": str(exc), "file": file_name, "bank_key": bank_key},
                timeout=10,
            )
        except Exception as e2:
            print("Webhook error after failure:", e2)


worker = UploadWorker()
