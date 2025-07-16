import os
from rest_framework.views   import APIView
from rest_framework.response import Response
from rest_framework          import status
from django.views import View
from django.shortcuts import render

from pdfconvert.tasks import worker

from pdfconvert.parsers.plaintext import PlainTextParser
from pdfconvert.registry          import get_handler
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
        print(">> > TEXT RECEIVED:") 
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
        # print(">>> RAW MOVIMIENTOS COUNT:", len(payload.get("movimientos", [])))
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
        print(f">>> PDFTextractView called with bank_key: {bank_key}")
        print(f">>> Request FILES: {list(request.FILES.keys())}")
        print(f">>> Request POST: {dict(request.POST)}")
        
        # Handle both single and multiple files
        files = request.FILES.getlist('files') or request.FILES.getlist('file')
        if not files:
            # Fallback to single file for backwards compatibility
            single_file = request.FILES.get('file') or request.FILES.get('files')
            if single_file:
                files = [single_file]
        
        if not files:
            print(">>> No files found in request.FILES")
            print(f">>> Available files: {list(request.FILES.keys())}")
            return Response(
                {"error": "Archivo no proporcionado", "detail": "Se requiere el campo 'file' o 'files'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        print(f">>> {len(files)} file(s) received")
        
        # Enqueue all files for processing
        enqueued_files = []
        failed_files = []
        
        for file in files:
            try:
                print(f">>> Processing file: {file.name}, size: {file.size} bytes")
                worker.enqueue(bank_key, file.name, file.read())
                enqueued_files.append(file.name)
                print(f">>> File enqueued for processing: {file.name}")
            except Exception as e:
                failed_files.append({"file": file.name, "error": str(e)})
                print(f">>> Error enqueueing file {file.name}: {str(e)}")

        # Prepare response
        if enqueued_files and not failed_files:
            message = f"✅ {len(enqueued_files)} archivo(s) encolado(s) para procesamiento"
            response_status = status.HTTP_202_ACCEPTED
        elif enqueued_files and failed_files:
            message = f"⚠️ {len(enqueued_files)} archivo(s) encolado(s), {len(failed_files)} fallaron"
            response_status = status.HTTP_202_ACCEPTED
        else:
            message = f"❌ No se pudo encolar ningún archivo"
            response_status = status.HTTP_400_BAD_REQUEST

        return Response({
            "message": message,
            "bank_key": bank_key,
            "enqueued_files": enqueued_files,
            "failed_files": failed_files,
            "total_files": len(files),
            "queue_size": worker.get_queue_status()["queue_size"]
        }, status=response_status)


class PDFUploadView(View):
    """Simple HTML interface to upload a PDF and process it with Textract."""

    template_name = "pdfconvert/upload.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        bank_key = request.POST.get("bank_key", "").strip()
        files = request.FILES.getlist("files") or request.FILES.getlist("file")

        if not bank_key or not files:
            msg = "Debe proporcionar el banco y al menos un archivo PDF."
            return render(request, self.template_name, {"message": msg, "success": False})

        handler = get_handler(bank_key)
        if not handler:
            msg = f'Banco "{bank_key}" no soportado.'
            return render(request, self.template_name, {"message": msg, "success": False})

        for f in files:
            worker.enqueue(bank_key, f.name, f.read())

        msg = f"{len(files)} archivo(s) encolado(s) para procesamiento."
        return render(request, self.template_name, {"message": msg, "success": True})


class QueueStatusView(APIView):
    """API endpoint to check the current status of the processing queue."""
    
    def get(self, request, *args, **kwargs):
        """Get current queue status."""
        try:
            status_info = worker.get_queue_status()
            return Response({
                "status": "ok",
                "queue_status": status_info,
                "message": f"Queue has {status_info['queue_size']} pending files"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "status": "error",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


