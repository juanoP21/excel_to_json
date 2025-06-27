import boto3
import os
import uuid
import time

class TextractOCRParser:
    """Extract plain text from PDFs using Amazon Textract"""
    def __init__(self, bucket: str | None = None):
        self.bucket = bucket or os.getenv("TEXTRACT_S3_BUCKET")
        self._client = None
        self._s3 = None

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
        if not self.bucket:
            raise ValueError("TEXTRACT_S3_BUCKET not configured")

        key = f"textract_ocr/{uuid.uuid4()}.pdf"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)

        start = self.client.start_document_text_detection(
            DocumentLocation={'S3Object': {'Bucket': self.bucket, 'Name': key}}
        )
        job_id = start['JobId']
        next_token = None
        blocks = []
        while True:
            if next_token:
                resp = self.client.get_document_text_detection(JobId=job_id, NextToken=next_token)
            else:
                resp = self.client.get_document_text_detection(JobId=job_id)
            status = resp.get('JobStatus')
            if status == 'FAILED':
                raise RuntimeError(f"Textract job {job_id} failed")
            blocks.extend(resp.get('Blocks', []))
            next_token = resp.get('NextToken')
            if status == 'SUCCEEDED' and not next_token:
                break
            time.sleep(1)

        self.s3.delete_object(Bucket=self.bucket, Key=key)

        lines = [b['Text'] for b in blocks if b.get('BlockType') == 'LINE']
        return {"text": "\n".join(lines)}
