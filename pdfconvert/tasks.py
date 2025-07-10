import threading
import queue
from io import BytesIO
import requests

from .registry import get_handler

WEBHOOK_URL = "https://automatizacion.commerk.com:4444/webhook/8dafec2e-f35a-4c3c-bcae-2a395effe7e6"

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
            try:
                handler = get_handler(bank_key)
                if not handler:
                    raise ValueError(f"Banco '{bank_key}' no soportado")
                parser = handler["parser"]
                with BytesIO(data) as f:
                    payload = parser.parse(f)
                payload["file_name"] = file_name
                try:
                    requests.post(WEBHOOK_URL, json=payload, timeout=10)
                except Exception as e:
                    print("Webhook error:", e)
            except Exception as e:
                print("Processing error:", e)
                try:
                    requests.post(WEBHOOK_URL, json={"error": str(e)}, timeout=10)
                except Exception as e2:
                    print("Webhook error after failure:", e2)
            finally:
                self.queue.task_done()


worker = UploadWorker()
