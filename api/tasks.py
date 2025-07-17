import threading
import queue
import os
import time
from io import BytesIO
import requests
import pandas as pd

from .banks.registry import get_processor

WEBHOOK_URL = "https://automatizacion.commerk.com:4444/webhook/8dafec2e-f35a-4c3c-bcae-2a395effe7e6"
MAX_RETRIES = 3


def _read_file(file, ext, sheet, header, skip):
    if ext == '.csv':
        return pd.read_csv(file, header=header, skiprows=skip)
    engine = 'openpyxl'
    if ext == '.xls':
        engine = 'xlrd'
    return pd.read_excel(
        file,
        sheet_name=(int(sheet) if sheet and str(sheet).isdigit() else sheet),
        header=header,
        skiprows=skip,
        engine=engine,
    )


def process_and_send(file_name: str, data: bytes, params: dict) -> None:
    """Parse the Excel file and send the JSON payload to the webhook."""
    base = os.path.basename(file_name)
    ext = os.path.splitext(base)[1].lower()

    branch = str(params.get('branch', '')).lower()
    sheet = params.get('worksheet')
    header = int(params.get('header_row', 0)) if str(params.get('header_row', '0')).isdigit() else 0
    skip = int(params.get('skip_rows')) if str(params.get('skip_rows', '')).isdigit() else None
    remove_unnamed = str(params.get('remove_unnamed', 'true')).lower() == 'true'

    with BytesIO(data) as f:
        df = _read_file(f, ext, sheet, header, skip)

    processor = get_processor(branch)
    if processor:
        df = processor(df)

    if remove_unnamed:
        df = df.loc[:, ~df.columns.str.contains(r'^Unnamed')]
    df.dropna(how='all', inplace=True)
    df.fillna('', inplace=True)
    df = df.astype(str)

    records = df.to_dict(orient='records')
    key = 'data' if branch in ('occidente', 'agrario', 'alianza', 'bbva', 'avvillas', 'itau') else 'movimientos'

    payload = {
        'bank_key': branch,
        'file_name': base,
        'params': params,
        key: records,
    }

    response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    print(f">>> WEBHOOK RESPONSE for {base}: {response.status_code}")


class UploadWorker:
    """Background worker to process Excel uploads."""

    def __init__(self) -> None:
        self.queue: 'queue.Queue[tuple[str, str, bytes, dict]]' = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def enqueue(self, file_name: str, data: bytes, params: dict) -> None:
        print(f">>> ENQUEUING EXCEL: {file_name}, queue size before: {self.queue.qsize()}")
        self.queue.put((file_name, data, params))
        print(f">>> EXCEL ENQUEUED: {file_name}, queue size after: {self.queue.qsize()}")

    def get_queue_status(self) -> dict:
        return {
            'queue_size': self.queue.qsize(),
            'thread_alive': self.thread.is_alive(),
            'thread_daemon': self.thread.daemon,
        }

    def _run(self) -> None:
        print(">>> EXCEL WORKER THREAD STARTED")
        while True:
            try:
                file_name, data, params = self.queue.get()
                print(f">>> PROCESSING EXCEL: {file_name}")
                success = False
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        process_and_send(file_name, data, params)
                        success = True
                        break
                    except Exception as e:
                        print(f">>> ERROR on attempt {attempt} for {file_name}: {e}")
                        if attempt < MAX_RETRIES:
                            time.sleep(2)
                        else:
                            self._report_error(file_name, e)
                if success:
                    print(f">>> ✅ COMPLETED: {file_name}")
                else:
                    print(f">>> ❌ FAILED: {file_name}")
            except Exception as e:
                print(f">>> CRITICAL ERROR in excel worker thread: {e}")
            finally:
                try:
                    self.queue.task_done()
                except Exception:
                    pass

    def _report_error(self, file_name: str, exc: Exception) -> None:
        try:
            requests.post(WEBHOOK_URL, json={'error': str(exc), 'file': file_name}, timeout=10)
        except Exception as e2:
            print("Webhook error after failure:", e2)


worker = UploadWorker()
