# pdfconvert/views.py

from rest_framework.views   import APIView
from rest_framework.response import Response
from rest_framework          import status

from pdfconvert.parsers.plaintext import PlainTextParser
from pdfconvert.registry          import get_handler

# pdfconvert/views.py

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
            "empresa","numero_cuenta","fecha_hora_actual","nit","tipo_cuenta"
        ]})
        print(">>> RAW MOVIMIENTOS COUNT:", len(payload.get("movimientos", [])))

        serializer = handler["serializer"](data=payload)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)

        print(">>> SERIALIZER ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
