import os
import pandas as pd
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

class ExcelToJsonView(APIView):
    """
    Convierte .xlsx, .xls o .csv a JSON, con lógica especial para ramas:
      - 'occidente'
      - 'popular'
    Parámetros opcionales (form-data/body):
      - branch: 'occidente' o 'popular' (para activar lógica de cada rama)
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
            # Lógica de ramas
            if branch == 'occidente':
                # TODO: implementar lógica específica de 'occidente'
                pass
            elif branch == 'popular':
                # TODO: implementar lógica específica de 'popular'
                pass

            # Lectura y limpieza
            df = self._read_file(excel_file, ext, sheet, header, skip)
            if remove_unnamed:
                df = df.loc[:, ~df.columns.str.contains(r'^Unnamed')]
            df.dropna(how='all', inplace=True)
            df.fillna('', inplace=True)
            df = df.astype(str)

            # Respuesta JSON
            records = df.to_dict(orient='records')
            return Response({
                'data': records,
            }, status=status.HTTP_200_OK)

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
