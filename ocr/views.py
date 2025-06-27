from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser

from .parsers import TextractOCRParser
import re


def _extract_receipts(text: str) -> list[dict]:
    """Parse Textract plain text into structured receipt data."""
    pattern = re.compile(
        r"(\d{1,2} de [A-Za-záéíóúÁÉÍÓÚ]+ del \d{4}|[A-Za-záéíóúÁÉÍÓÚ]+ del \d{4})"
        r".*?DEBE A:\s*(.*?)\nLa suma.*?TOTAL\n\$?\.?\s*(\d+[\.,]\d+)",
        re.IGNORECASE | re.DOTALL,
    )

    receipts: list[dict] = []
    for match in pattern.finditer(text):
        fecha = match.group(1).strip()
        debe_a = match.group(2).strip()
        total = match.group(3).strip()

        block = match.group(0)
        turnos_nums = re.findall(r"\n(\d+)\n\d{2}/\d{2}/\d{4}", block)
        turnos = max(map(int, turnos_nums)) if turnos_nums else None

        receipts.append(
            {
                "fecha": fecha,
                "DEBE A": debe_a,
                "Turnos": turnos,
                "total": total,
            }
        )

    return receipts

class TextractOCRView(APIView):
    """Return plain text extracted from a PDF using Amazon Textract."""
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"error": "Archivo no proporcionado", "detail": "Se requiere el campo 'file'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parser = TextractOCRParser()
        try:
            payload = parser.parse(file)
        except Exception as e:
            print(">>> OCR TEXTRACT ERROR:", e)
            return Response(
                {"error": "Error al procesar el archivo", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        text = payload.get("text", "")
        data = _extract_receipts(text)

        return Response({"results": data}, status=status.HTTP_200_OK)
