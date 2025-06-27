
from rest_framework.views   import APIView
from rest_framework.response import Response
from rest_framework          import status

from pdfconvert.parsers.plaintext import PlainTextParser
from pdfconvert.registry          import get_handler
from pdfconvert.parsers.ocr_textract import TextractOCRParser
from rest_framework.parsers import MultiPartParser


class PDFConvertView(APIView):
    parser_classes = [PlainTextParser]

    def post(self, request, bank_key, *args, **kwargs):
        handler = get_handler(bank_key)
        if not handler:
            return Response(
                {"error": f'Banco "{bank_key}" no soportado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        texto = request.data
        print(">>> TEXT RECEIVED:") 
        print(texto[:200], "...")  # primeros 200 caracteres

        try:
            payload = handler["parser"].parse(texto)
        except Exception as e:
            print(">>> PARSE ERROR:", str(e))
            return Response(
                {"error": "Error al parsear el texto", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        print(">>> PAYLOAD HEADERS:", {k: payload.get(k) for k in [
            "empresa", "numero_cuenta", "fecha_hora_actual", "nit", "tipo_cuenta"
        ]})
        print(">>> RAW MOVIMIENTOS COUNT:", len(payload.get("movimientos", [])))
        serializer_class = handler.get("serializer")
        if serializer_class is None:
            # Si no hay serializer definido, devolvemos el payload directamente
            return Response(payload, status=status.HTTP_200_OK)

        serializer = serializer_class(data=payload)
        if serializer.is_valid():
            return Response(payload, status=status.HTTP_200_OK)

        print(">>> SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class PDFTextractView(APIView):
    """View to handle PDF uploads processed with Amazon Textract."""
    parser_classes = [MultiPartParser]

    def post(self, request, bank_key, *args, **kwargs):
        handler = get_handler(bank_key)
        print(">>> HANDLER:", handler)
        if not handler:
            return Response(
                {"error": f'Banco "{bank_key}" no soportado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        file = request.FILES.get('file')
        if not file:
            return Response(
                {"error": "Archivo no proporcionado", "detail": "Se requiere el campo 'file'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payload = handler["parser"].parse(file)
        except Exception as e:
            print(">>> TEXTRACT PARSE ERROR:", str(e))
            return Response(
                {"error": "Error al procesar el archivo", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer_class = handler.get("serializer")
        if serializer_class is None:
            return Response(payload, status=status.HTTP_200_OK)

        serializer = serializer_class(data=payload)
        if serializer.is_valid():
            return Response(payload, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
