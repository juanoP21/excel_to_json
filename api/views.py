+15
-16

import os
import pandas as pd
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from .banks.registry import get_processor

class ExcelToJsonView(APIView):
    """
    Convierte .xlsx, .xls o .csv a JSON.
    Si se envía el parámetro ``branch`` se buscará un procesador
    específico para ese banco, registrado en ``api.banks.registry``.
    Parámetros opcionales (form-data/body):
      - branch: clave del banco para activar la lógica específica
      - worksheet: nombre o índice de hoja
      - header_row: índice de la fila de encabezado (por defecto 0)
      - skip_rows: número de filas a omitir al inicio
      - remove_unnamed: 'true'/'false' (por defecto 'true')
    """
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
            key = 'movimientos' if branch in ('occidente', 'agrario','alianza','bbva','avvillas') else 'data'
            return Response({key: records}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _read_file(self, file, ext, sheet, header, skip):
        if ext == '.csv':
            return pd.read_csv(file, header=header, skiprows=skip)
        return pd.read_excel(
            file,
            sheet_name=(int(sheet) if sheet and sheet.isdigit() else sheet),
            header=header,
            skiprows=skip
        )