import threading
import queue
import time
from io import BytesIO
import requests

from .registry import get_handler

WEBHOOK_URL = "https://automatizacion.commerk.com:4444/webhook/8dafec2e-f35a-4c3c-bcae-2a395effe7e6"
MAX_RETRIES = 3

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
            handler = get_handler(bank_key)
            if not handler:
                err = ValueError(f"Banco '{bank_key}' no soportado")
                self._report_error(file_name, err)
                self.queue.task_done()
                continue

            parser = handler["parser"]
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    with BytesIO(data) as f:
                        payload = parser.parse(f)
                    payload["file_name"] = file_name
                    requests.post(WEBHOOK_URL, json=payload, timeout=10)
                    break
                except Exception as e:
                    print(f"Processing error on attempt {attempt} for {file_name}:", e)
                    if attempt < MAX_RETRIES:
                        time.sleep(2)
                    else:
                        self._report_error(file_name, e)

            self.queue.task_done()

    def _report_error(self, file_name: str, exc: Exception) -> None:
        try:
            requests.post(
                WEBHOOK_URL,
                json={"error": str(exc), "file": file_name},
                timeout=10,
            )
        except Exception as e2:
            print("Webhook error after failure:", e2)


worker = UploadWorker()
