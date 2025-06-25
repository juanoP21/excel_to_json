import boto3
import os

class TextractParser:
    """Parser that uses Amazon Textract to extract text from a PDF file."""

    def __init__(self, parse_func):
        self.parse_func = parse_func
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                'textract',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=os.getenv('AWS_DEFAULT_REGION')
            )
        return self._client

    def parse(self, file_obj):
        data = file_obj.read()
        print(">>> TEXTRACT FILE SIZE:", len(data), "bytes")
        response = self.client.analyze_document(Document={'Bytes': data},FeatureTypes=['FORMS'])
        # lines = [blk['Text'] for blk in response.get('Blocks', []) if blk.get('BlockType') == 'LINE']
        # text = '\n'.join(lines)
        blocks = response['Blocks']

        print(">>> TEXTRACT RESPONSE:", blocks[:200], "...")
        return self.parse_func(blocks)