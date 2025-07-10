import boto3
import os
import uuid
import time
import re
import json
from datetime import datetime


def _is_amount(text: str) -> bool:
    """Check if text looks like a monetary amount (e.g., '2,304,747.00' or '1,100,000')"""
    if not text:
        return False
    text = text.strip()
    # Pattern for amounts: digits with optional commas and decimal places
    amount_pattern = r'^\d{1,3}(?:,\d{3})*(?:\.\d{2})?$'
    return bool(re.match(amount_pattern, text))


def _parse_amount(raw: str) -> float:
    """Return numeric value from raw with decimal point as '.', treating commas as thousand separators."""
    text = str(raw or "").strip()
    # Normalize various minus symbols to plain hyphen
    for ch in ('\u2212', '\u2013', '\u2014'):
        text = text.replace(ch, '-')

    # Detect negative via parentheses or leading/trailing minus
    negative = False
    if text.startswith('(') and text.endswith(')'):
        negative = True
        text = text[1:-1].strip()
    if text.endswith('-'):
        negative = True
        text = text[:-1].strip()
    if text.startswith('-'):
        negative = True
        text = text[1:].strip()

    # Strip any currency symbols, spaces, letters
    text = re.sub(r'[^\d\.,]', '', text)

    # If both separators appear, decide which is decimal by last occurrence
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            # comma is decimal → replace comma with dot, remove dots as thousands
            text = text.replace('.', '')
            text = text.replace(',', '.')
        else:
            # dot is decimal → remove commas as thousands
            text = text.replace(',', '')
    elif ',' in text:
        # only commas → remove them (treat as thousand sep)
        text = text.replace(',', '')
    # else only dots or only digits → leave as-is

    try:
        value = float(text)
    except ValueError:
        value = 0.0

    return -value if negative else value


def _format_date(raw: str) -> tuple[str, datetime | None]:
    """Return (formatted_date, datetime_obj) from various raw formats."""
    if not raw:
        return "", None
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%d/%m/%Y"), dt
        except Exception:
            continue
    try:
        dt = datetime.fromisoformat(text)
        return dt.strftime("%d/%m/%Y"), dt
    except Exception:
        return text, None

def parse_func(movimientos):
    """Transform Textract rows into the final ordered structure."""
    registros = []

    for mov in movimientos:
        ref1 = mov.get("referencia1", "").strip()
        ref2 = mov.get("referencia2", "").strip()

        # Handle cases where references contain amounts
        ref_parts = []
        amount_from_ref = None

        # Check if ref2 is an amount
        if ref2:
            if _is_amount(ref2):
                amount_from_ref = ref2
                print(f"Found amount in referencia2: {ref2}")
            else:
                ref_parts.append(ref2)

        # Build the reference name
        if len(ref_parts) >= 2:
            # only concatenate if they differ
            if ref_parts[0] != ref_parts[1]:
                nombre = f"{ref_parts[0]}-{ref_parts[1]}"
            else:
                nombre = ref_parts[0]
        elif len(ref_parts) == 1:
            nombre = ref_parts[0]
        else:
            # both references were amounts or empty
            if ref1 and ref2:
                if _is_amount(ref1) and _is_amount(ref2):
                    nombre = f"{ref1}"
                elif _is_amount(ref1):
                    nombre = f"{ref1}"
                elif _is_amount(ref2):
                    nombre = f"{ref2}"
                else:
                    nombre = ref1  # they are equal non-amounts
            else:
                nombre = ref1 or ref2
        
        desc = mov.get("descripcion", "").strip()
        raw_val = (
            mov.get("valor")
            or mov.get("documento")
            or mov.get("credito")
            or mov.get("debito")
            or mov.get("importe_credito")
            or mov.get("importe_debito")
            or mov.get("documentovalor")
            or ""
        )
        
        # If no valor found but we have an amount in references, use it
        if (not raw_val or raw_val.strip() == "0" or raw_val.strip() == "") and amount_from_ref:
            raw_val = amount_from_ref
            print(f"Using amount from reference as valor: {amount_from_ref}")

        val = _parse_amount(raw_val)
        print(f"Raw value: {raw_val}, parsed value: {val}")
        raw_str = str(raw_val).strip()
        fecha_fmt, fecha_dt = _format_date(mov.get("fecha", ""))
        if val >= 0:
            importe_credito = f"{val:.2f}"
            importe_debito = 0.0
        else:
            importe_credito = 0.0
            importe_debito = f"{abs(val):.2f}"

        registro = {
            "Fecha": fecha_fmt,
            "importe_credito": importe_credito,
            "importe_debito": importe_debito,
            "referencia": nombre,
            "Info_detallada": f"{desc} ".strip(),
            "Info_detallada2": mov.get("sucursal_canal", ""),
        }

        registros.append((fecha_dt or datetime.max, registro))
    registros.sort(key=lambda r: r[0])
    
    # Retornamos con la estructura {"results": [movimientos]}
    return {"results": [r[1] for r in registros]}

class TextractParser:
    """Parser that extracts tables from PDF files using Amazon Textract.

    The parser now uses the asynchronous ``start_document_analysis`` API with
    the ``TABLES`` feature. The uploaded PDF is placed in S3 and Textract is
    polled via ``get_document_analysis`` until the job finishes.
    """

    def __init__(self, parse_func, bucket: str | None = None):
        self.parse_func = parse_func
        self._client = None
        self._s3 = None
        self.bucket = bucket or os.getenv("TEXTRACT_S3_BUCKET")

    def _normalize_header(self, header: str) -> str:
        mapping = {
            "FECHA": "fecha",
            "DESCRIPCION": "descripcion",
            "DESCRIPCIÓN": "descripcion",
            "SUCURSALCANAL": "sucursal_canal",
            "SUCURSAL/CANAL": "sucursal_canal",
            "REFERENCIA1": "referencia1",
            "REFERENCIA 1": "referencia1",
            "REFERENCIA2": "referencia2",
            "REFERENCIA 2": "referencia2",
            "DOCUMENTO": "documento",
            "VALOR": "valor",
        }
        head = header.upper().replace(" ", "").replace("_", "")
        head = head.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
        return mapping.get(head, head.lower())

    def _get_cell_text(self, cell, block_map):
        text = ""
        for rel in cell.get("Relationships", []):
            if rel.get("Type") == "CHILD":
                for cid in rel.get("Ids", []):
                    child = block_map.get(cid)
                    if not child:
                        continue
                    if child.get("BlockType") == "WORD":
                        text += child.get("Text", "") + " "
                    elif child.get("BlockType") == "SELECTION_ELEMENT":
                        if child.get("SelectionStatus") == "SELECTED":
                            text += "X "
        return text.strip()

    def _extract_tables(self, blocks):
        block_map = {b["Id"]: b for b in blocks}
        tables = []
        for block in blocks:
            if block.get("BlockType") != "TABLE":
                continue
            rows = {}
            for rel in block.get("Relationships", []):
                if rel.get("Type") != "CHILD":
                    continue
                for cid in rel.get("Ids", []):
                    cell = block_map.get(cid)
                    if not cell or cell.get("BlockType") != "CELL":
                        continue
                    r = cell.get("RowIndex")
                    c = cell.get("ColumnIndex")
                    rows.setdefault(r, {})[c] = self._get_cell_text(cell, block_map)
            if rows:
                ordered = []
                for r in sorted(rows):
                    row = [rows[r].get(c, "") for c in sorted(rows[r])]
                    ordered.append(row)
                tables.append(ordered)
        return tables

    def _merge_rows(self, rows: list[dict]) -> list[dict]:
        """Combine multiline rows coming from Textract tables."""
        merged: list[dict] = []
        current: dict | None = None

        for row in rows:
            fecha = row.get("fecha", "").strip()
            val_key = "valor" if "valor" in row else "documento"
            valor = row.get(val_key, "").strip()

            if not fecha:
                # 1) Si solo tiene importe y no fecha, cierra "current"
                if valor and current is not None:
                    current[val_key] = valor
                    merged.append(current)
                    current = None
                    continue

                # 2) Si no tiene fecha ni importe, continua descripcion
                if current is not None:
                    for k, v in row.items():
                        if not v or k in {"fecha", val_key}:
                            continue
                        prev = current.get(k, "")
                        current[k] = f"{prev} {v}".strip() if prev else v
                    continue

            # Al llegar aqui, la fila trae fecha: cierra la anterior
            if current is not None:
                merged.append(current)
            current = row.copy()

        if current is not None:
            merged.append(current)

        return merged

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                'textract',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name="us-east-2"
            )
        return self._client

    @property
    def s3(self):
        if self._s3 is None:
            self._s3 = boto3.client(
                's3',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name="us-east-2"
            )
        return self._s3

    def parse(self, file_obj):
        data = file_obj.read()
        print(">>> TEXTRACT FILE SIZE:", len(data), "bytes")
        if not self.bucket:
            raise ValueError("TEXTRACT_S3_BUCKET not configured")

        key = f"textract_uploads/{uuid.uuid4()}.pdf"
        print(">>> uploading to S3:", self.bucket, key)
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)

        print(">>> starting Textract job...")
        try:
            start_resp = self.client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {'Bucket': self.bucket, 'Name': key}
                },
                FeatureTypes=['TABLES']
            )
        except Exception as e:
            print(">>> TEXTRACT ERROR:", e)
            raise

        job_id = start_resp['JobId']
        print(">>> JOB ID:", job_id)
        next_token = None
        blocks = []
        while True:
            if next_token:
                resp = self.client.get_document_analysis(JobId=job_id, NextToken=next_token)
            else:
                resp = self.client.get_document_analysis(JobId=job_id)

            status = resp.get('JobStatus')
            print(">>> JOB STATUS:", status, "TOKEN:", next_token)
            if status == 'FAILED':
                raise RuntimeError(f"Textract job {job_id} failed")

            blocks.extend(resp.get('Blocks', []))
            next_token = resp.get('NextToken')

            if status == 'SUCCEEDED' and not next_token:
                break
            time.sleep(1)

        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
        except Exception as e:
            print(">>> S3 cleanup error:", e)

        print(">>> TOTAL BLOCKS:", len(blocks))

        tables = self._extract_tables(blocks)
        print(">>> TABLES FOUND:", len(tables))
        if not tables:
            raise ValueError("No tables detected in document")

        header = tables[0][0]
        print(">>> HEADER ROW:", header)
        keys = [self._normalize_header(h) for h in header]

        movimientos = []
        for t_idx, table in enumerate(tables):
            rows = table
            norm_first = [self._normalize_header(h) for h in table[0]]
            if norm_first == keys:
                rows = table[1:]
            elif t_idx == 0:
                rows = table[1:]
            for row in rows:
                mov = {}
                for idx, cell in enumerate(row):
                    if idx >= len(keys):
                        break
                    key = keys[idx]
                    if key:
                        mov[key] = cell
                if mov:
                    movimientos.append(mov)

        print(">>> MOVIMIENTOS COUNT:", len(movimientos))
        if movimientos:
            print(">>> MOVIMIENTOS:", movimientos)
        movimientos = self._merge_rows(movimientos)
        print(">>> MOVIMIENTOS AFTER MERGE:", len(movimientos))
        if movimientos:
            print(">>> FIRST MERGED MOVIMIENTO:", movimientos[0])
        

        for m in movimientos:
            if m.get("descripcion","").upper().startswith("TRANSFERENCIA DESDE NEQUI"):
                m["referencia1"] = re.sub(r"^\d+\s*", "", m["referencia1"]).strip()

        # 3) Post-procesado final
        return self.parse_func(movimientos)
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python textract.py <ruta_al_pdf>")
        sys.exit(1)

    ruta_pdf = sys.argv[1]
    # Leemos el PDF en binario
    with open(ruta_pdf, "rb") as f:
        parser = TextractParser(parse_func, bucket=os.getenv("TEXTRACT_S3_BUCKET"))
        movimientos = parser.parse(f)

    # Imprimimos el resultado en JSON bonito
    print(json.dumps(movimientos, indent=2, ensure_ascii=False))
