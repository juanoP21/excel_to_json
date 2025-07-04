import boto3
import os
import uuid
import time
import re
import json


def _parse_amount(raw: str) -> float:
    """Return numeric value from a raw amount string.

    Handles values using either comma or dot as decimal separator and
    supports optional minus signs or parentheses for negative numbers.
    If parsing fails, ``0.0`` is returned.
    """
    if not raw:
        return 0.0

    text = str(raw).strip()
    negative = False

    # Handle trailing/leading minus sign or parentheses
    if text.startswith('(') and text.endswith(')'):
        negative = True
        text = text[1:-1]
    if text.endswith('-'):
        negative = True
        text = text[:-1]
    if text.startswith('-'):
        negative = True
        text = text[1:]

    # Remove currency symbols and spaces
    text = re.sub(r'[^0-9,\.]+', '', text)

    if ',' in text and '.' in text:
        # whichever separator appears last is the decimal separator
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '')
            text = text.replace(',', '.')
        else:
            text = text.replace(',', '')
    elif text.count(',') > 1 and '.' not in text:
        text = text.replace(',', '')
    elif text.count('.') > 1 and ',' not in text:
        text = text.replace('.', '')
    elif ',' in text:
        # Assume comma is decimal if there's a single comma with two digits after
        parts = text.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            text = text.replace('.', '')
            text = text.replace(',', '.')
        else:
            text = text.replace(',', '')
    elif '.' in text:
        parts = text.split('.')
        if len(parts) == 2 and len(parts[1]) <= 2:
            text = text.replace(',', '')
        else:
            text = text.replace('.', '')

    try:
        value = float(text)
    except Exception:
        value = 0.0

    return -value if negative else value

def parse_func(movimientos):
    """
    Post-procesado de movimientos:
    - Concatena el nombre del remitente (referencia1) al final de la descripción.
    - Si la descripción contiene "NEQUI", mueve el valor a importe_credito.
      En caso contrario, lo coloca en importe_debito.
    - Deja intactos tus nombres de campo de salida.
    """
    salida = []
    for mov in movimientos:
        # Extraemos el nombre del remitente tal como vino en Textract
        nombre = mov.get("referencia1", "").strip()

        # Descripción original detectada en la tabla
        desc = mov.get("descripcion", "").strip()

        # Valor puede venir en diferentes campos
        raw_val = (
            mov.get("valor")
            or mov.get("documento")
            or mov.get("credito")
            or mov.get("debito")
            or mov.get("importe_credito")
            or mov.get("importe_debito")
            or ""
        )

        # Formateamos la fecha si es posible
        fecha_raw = mov.get("fecha", "")
        try:
            from datetime import datetime

            fecha_dt = datetime.fromisoformat(fecha_raw)
            fecha_fmt = fecha_dt.strftime("%d/%m/%Y")
        except Exception:
            fecha_fmt = fecha_raw

        if val >= 0:
            importe_credito = f"{val:.2f}"
            importe_debito = ""
        else:
            importe_credito = ""
            importe_debito = f"{-val:.2f}"

        salida.append({
            "Fecha": fecha_fmt,
            "importe_credito": importe_credito,
            "importe_debito": importe_debito,
            "referencia": nombre,
            "Info_detallada": f"{desc} {nombre}".strip(),
            "Info_detallada2": mov.get("sucursal_canal", ""),
        })
    return salida

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

    def _merge_rows(self, movimientos):
        consolidados = []
        for mov in movimientos:
            fecha = mov.get("fecha", "").strip()
            ref   = mov.get("referencia1", "").strip()

            # Si NO tiene fecha pero SÍ tiene referencia => es continuación
            if not fecha and ref and consolidados:
                anterior = consolidados[-1]
                anterior["referencia1"] = (
                    anterior.get("referencia1","").strip()
                    + " "
                    + ref
                ).strip()
            else:
                consolidados.append(mov.copy())
        return consolidados

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
