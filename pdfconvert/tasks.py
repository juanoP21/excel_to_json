import threading
import queue
import time
from io import BytesIO
import os
import requests

from .registry import get_handler
from api.banks.registry import get_processor, EXCEL_ENABLED_BANKS
from api.utils import read_table

WEBHOOK_URL = "https://automatizacion.commerk.com:4444/webhook/8dafec2e-f35a-4c3c-bcae-2a395effe7e6"
MAX_RETRIES = 3



def process_and_send(bank_key: str, file_name: str, data: bytes, params: dict | None = None) -> None:
    """Parse the file if needed and send it to the webhook."""
    params = params or {}
    file_basename = os.path.basename(file_name)

    if bank_key == "bancolombia_textract":
        handler = get_handler(bank_key)
        if not handler:
            raise ValueError(f"Banco '{bank_key}' no soportado")

        parser = handler["parser"]
        with BytesIO(data) as f:
            payload = parser.parse(f)
        payload["file_name"] = file_basename
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
        return

    if bank_key in EXCEL_ENABLED_BANKS:
        ext = os.path.splitext(file_name)[1].lower()
        sheet = params.get("worksheet")
        header = params.get("header_row", 0)
        header = int(header) if str(header).isdigit() else 0
        skip = params.get("skip_rows")
        skip = int(skip) if str(skip).isdigit() else None
        remove_unnamed = str(params.get("remove_unnamed", "true")).lower() == "true"

        with BytesIO(data) as buf:
            df = read_table(buf, ext, sheet, header, skip)

        processor = get_processor(bank_key)
        if processor:
            df = processor(df)

        if remove_unnamed:
            df = df.loc[:, ~df.columns.str.contains(r"^Unnamed")]
        df.dropna(how="all", inplace=True)
        df.fillna("", inplace=True)
        df = df.astype(str)

        records = df.to_dict(orient="records")
        payload = {"movimientos": records, "file_name": file_basename}
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
        return

    requests.post(
        WEBHOOK_URL,
        files={"file": (file_basename, data, "application/pdf")},
        data={"bank_key": bank_key, "file_name": file_basename},
        timeout=10,
    )

class UploadWorker:
    """Background worker that processes uploaded PDFs sequentially."""

    def __init__(self):
        self.queue: 'queue.Queue[tuple[str, str, bytes, dict]]' = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def enqueue(self, bank_key: str, file_name: str, data: bytes, params: dict | None = None) -> None:
        """Add a file to the processing queue."""
        self.queue.put((bank_key, file_name, data, params or {}))

    def _run(self) -> None:
        while True:
            bank_key, file_name, data, params = self.queue.get()
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    process_and_send(bank_key, file_name, data, params)
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
