import boto3
import os
import uuid
import time
import re
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
        merged: list[dict] = []
        current: dict | None = None

        for row in rows:
            fecha = row.get("fecha", "").strip()
            # Chequeamos si esta fila trae un importe (en tu caso lo nombras 'documento')
            val_key = "valor" if "valor" in row else "documento"
            valor = row.get(val_key, "").strip()

            if not fecha:
                # 1) Si sólo tiene importe y no fecha, es el cierre de current
                if valor and current is not None:
                    # fusiona el importe en el campo correcto
                    current[val_key] = valor
                    merged.append(current)
                    current = None
                    continue

                # 2) Si no tiene fecha ni importe, es continuación de texto
                if current is not None:
                    for k, v in row.items():
                        if not v or k == "fecha" or k == val_key:
                            continue
                        prev = current.get(k, "")
                        current[k] = f"{prev} {v}".strip() if prev else v
                    continue

            # Si llegamos aquí, trae fecha: cerramos el anterior (si existía) y empezamos uno nuevo
            if current is not None:
                merged.append(current)
            current = row.copy()

        # Al final, si quedó uno abierto, lo añadimos
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
            print(">>> FIRST MERGED MOVIMIENTO:", movimientos[0])\
                
        for m in movimientos:
            if m.get("descripcion", "").upper().startswith("TRANSFERENCIA DESDE NEQUI"):
                ref = m.get("referencia1", "").strip()
                # Partimos por la primera tanda de dígitos y nos quedamos con lo que viene después
                parts = re.split(r"\s*\d+\s*", ref, maxsplit=1)
                if len(parts) > 1:
                    ref = parts[1]
                # Eliminamos cualquier dígito residual
                ref = re.sub(r"\d+", "", ref).strip()
                m["referencia1"] = ref
        return self.parse_func(movimientos)