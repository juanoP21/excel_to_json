from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser

from .parsers import TextractOCRParser

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

        return Response(payload, status=status.HTTP_200_OK)
