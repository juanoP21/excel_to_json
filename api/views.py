import os
import pandas as pd
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from .tasks import worker as excel_worker


from .banks.registry import get_processor

class ExcelToJsonView(APIView):
  
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        excel_file = request.FILES.get('file')
        if not excel_file:
            return Response({'error': 'No se proporcionó ningún archivo'},
                            status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(excel_file.name)[1].lower()
        if ext not in ('.csv', '.xls', '.xlsx'):
            return Response({'error': 'Formato no soportado'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Parámetros comunes
        branch = request.data.get('branch', '').lower()
        sheet  = request.data.get('worksheet')
        header = int(request.data.get('header_row', 0)) if request.data.get('header_row', '').isdigit() else 0
        skip   = int(request.data.get('skip_rows')) if request.data.get('skip_rows', '').isdigit() else None
        remove_unnamed = request.data.get('remove_unnamed', 'true').lower() == 'true'

        try:
            # Leer el archivo
            df = self._read_file(excel_file, ext, sheet, header, skip)

            # Aplicar procesamiento específico del banco si existe
            processor = get_processor(branch)
            if processor:
                df = processor(df)

            if remove_unnamed:
                df = df.loc[:, ~df.columns.str.contains(r'^Unnamed')]
            df.dropna(how='all', inplace=True)
            df.fillna('', inplace=True)
            df = df.astype(str)

            # Respuesta JSON
            records = df.to_dict(orient='records')
            key = 'movimientos' if branch in ('occidente', 'agrario','alianza','bbva','avvillas','itau') else 'data'
            return Response({key: records}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _read_file(self, file, ext, sheet, header, skip):
        if ext == '.csv':
            return pd.read_csv(file, header=header, skiprows=skip)
        engine = 'openpyxl'
        if ext == '.xls':
            engine = 'xlrd'
        return pd.read_excel(
            file,
            sheet_name=(int(sheet) if sheet and sheet.isdigit() else sheet),
            header=header,
            skiprows=skip,
            engine=engine,
        )


class ExcelUploadView(APIView):
    """Enqueue Excel files for background processing."""

    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('files') or request.FILES.getlist('file')
        if not files:
            single = request.FILES.get('file')
            if single:
                files = [single]
        if not files:
            return Response(
                {'error': 'Archivo no proporcionado', 'detail': "Se requiere el campo 'file' o 'files'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        params = {
            'branch': request.data.get('branch', '').lower(),
            'worksheet': request.data.get('worksheet'),
            'header_row': request.data.get('header_row', 0),
            'skip_rows': request.data.get('skip_rows'),
            'remove_unnamed': request.data.get('remove_unnamed', 'true'),
        }

        enqueued = []
        failed = []
        for f in files:
            try:
                excel_worker.enqueue(f.name, f.read(), params)
                enqueued.append(f.name)
            except Exception as e:
                failed.append({'file': f.name, 'error': str(e)})

        if enqueued and not failed:
            message = f"✅ {len(enqueued)} archivo(s) encolado(s)"
            status_code = status.HTTP_202_ACCEPTED
        elif enqueued and failed:
            message = f"⚠️ {len(enqueued)} archivo(s) encolado(s), {len(failed)} fallaron"
            status_code = status.HTTP_202_ACCEPTED
        else:
            message = "❌ No se pudo encolar ningún archivo"
            status_code = status.HTTP_400_BAD_REQUEST

        return Response({
            'message': message,
            'enqueued_files': enqueued,
            'failed_files': failed,
            'queue_size': excel_worker.get_queue_status()['queue_size'],
            'params': params,
        }, status=status_code)
