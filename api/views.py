import json
import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import openpyxl
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from requests.exceptions import RequestException
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ExcelToJsonView(APIView):
    """
    API endpoint para convertir archivos Excel a JSON con manejo mejorado
    de hojas de trabajo y errores comunes.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({'error': 'No se proporcionó ningún archivo'}, status=status.HTTP_400_BAD_REQUEST)
        
        excel_file = request.FILES['file']
        
        # Verificar extensión
        if not excel_file.name.endswith(('.xlsx', '.xls', '.csv')):
            return Response({'error': 'El archivo debe ser de tipo Excel (.xlsx, .xls) o CSV (.csv)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Parámetros adicionales opcionales
            worksheet_name = request.data.get('worksheet', None)
            
            # Convertir worksheet_name a entero si es un número, o mantenerlo como string
            if worksheet_name is not None:
                try:
                    worksheet_name = int(worksheet_name)
                except ValueError:
                    # Si no se puede convertir a entero, se mantiene como string (nombre de hoja)
                    pass
            
            header_row = request.data.get('header_row')
            if header_row and header_row.isdigit():
                header_row = int(header_row)
            else:
                header_row = 0  # Por defecto, primera fila
                
            skip_rows = request.data.get('skip_rows')
            if skip_rows and skip_rows.isdigit():
                skip_rows = int(skip_rows)
            else:
                skip_rows = None
                
            remove_unnamed = request.data.get('remove_unnamed', 'true').lower() == 'true'
            
            # Procesar el archivo Excel
            result = self.process_excel_file(
                excel_file, 
                sheet_name=worksheet_name, 
                header=header_row,
                skiprows=skip_rows,
                remove_unnamed=remove_unnamed
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            return Response({
                'error': f'Error al procesar el archivo: {str(e)}',
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def process_excel_file(self, file, sheet_name=None, header=0, skiprows=None, remove_unnamed=True):
        """
        Procesa un archivo Excel y devuelve los datos en formato JSON.
        
        Args:
            file: Archivo de Excel a procesar
            sheet_name: Nombre o índice de la hoja (None para obtener la primera)
            header: Fila a usar como encabezado (0 por defecto)
            skiprows: Filas a omitir al inicio (None por defecto)
            remove_unnamed: Si se deben eliminar columnas sin nombre (True por defecto)
        
        Returns:
            Lista de diccionarios con los datos del Excel
        """
        try:
            # Intentar leer con pandas
            if file.name.endswith('.csv'):
                df = pd.read_csv(file, header=header, skiprows=skiprows)
            else:
                # Si no se especificó hoja, intentar leer la primera
                if sheet_name is None:
                    # Leer todas las hojas para obtener sus nombres
                    xl = pd.ExcelFile(file)
                    sheet_names = xl.sheet_names
                    
                    if not sheet_names:
                        raise ValueError("El archivo Excel no contiene hojas de trabajo")
                    
                    # Usar la primera hoja
                    sheet_name = sheet_names[0]
                    
                df = pd.read_excel(file, sheet_name=sheet_name, header=header, skiprows=skiprows)
            
            # Eliminar columnas sin nombre si se solicita
            if remove_unnamed:
                unnamed_cols = [col for col in df.columns if 'Unnamed:' in str(col)]
                if unnamed_cols:
                    df = df.drop(columns=unnamed_cols)
            
            # Eliminar filas completamente vacías
            df = df.dropna(how='all')
            
            # Convertir los valores NaN/None a cadenas vacías
            df = df.fillna('')
            
            # Convertir todos los valores a cadenas
            for col in df.columns:
                df[col] = df[col].astype(str)
            
            # Convertir DataFrame a lista de diccionarios
            result = df.to_dict(orient='records')
            
            return {
                'data': result,
                'metadata': {
                    'total_rows': len(result),
                    'columns': df.columns.tolist(),
                    'sheet_name': sheet_name
                }
            }
            
        except Exception as e:
            # Si hay un problema con una hoja específica, intentar con la primera
            if "not found" in str(e) and sheet_name is not None:
                try:
                    # Leer todas las hojas disponibles
                    xl = pd.ExcelFile(file)
                    sheet_names = xl.sheet_names
                    
                    if sheet_names:
                        # Intentar con la primera hoja
                        return self.process_excel_file(
                            file, 
                            sheet_name=sheet_names[0],
                            header=header,
                            skiprows=skiprows,
                            remove_unnamed=remove_unnamed
                        )
                except:
                    pass
            
            # Si todos los intentos fallan, relanzar la excepción original
            raise e
        
# tu_app/views.py


class SAPConnectView(APIView):
    def post(self, request, *args, **kwargs):
        # Verificar variables de entorno con os.getenv
        required = [
            'B1_SERVER_ENV', 'B1_SLPORT_ENV', 'B1_SLPATH_ENV',
            'B1_USER_ENV',   'B1_PASS_ENV',   'B1_COMP_ENV',
        ]
        missing = [v for v in required if not os.getenv(v)]
        if missing:
            return Response(
                {'error': f'Faltan variables de entorno: {", ".join(missing)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        base = f"{os.getenv('B1_SERVER_ENV')}:{os.getenv('B1_SLPORT_ENV')}"
        path = os.getenv('B1_SLPATH_ENV').rstrip('/') + '/Login'
        url = f"{base}{path}"

        payload = {
            "UserName": os.getenv('B1_USER_ENV'),
            "Password": os.getenv('B1_PASS_ENV'),
            "CompanyDB": os.getenv('B1_COMP_ENV'),
        }

        try:
            resp = requests.post(url, json=payload,
                                 headers={'Content-Type': 'application/json'},
                                 timeout=30, verify=False)
            resp.raise_for_status()
        except RequestException as e:
            code = e.response.status_code if getattr(e, 'response', None) else 500
            detail = getattr(e.response, 'text', str(e))
            return Response(
                {'error': 'Error conectando a SAP B1', 'details': detail},
                status=code
            )

        data = resp.json()
        if 'SessionId' not in data:
            return Response({'error': 'No vino SessionId', 'raw': data},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'sessionId': data['SessionId'],
            'cookies': resp.cookies.get_dict(),
            'version': data.get('Version'),
            'timeout': data.get('SessionTimeout'),
            
        }, status=status.HTTP_200_OK)
        
        
        
class testView(APIView):
    def post (self, request, *args, **kwargs):
        # Verificar variables de entorno con os.getenv
        Response(
            {'message': 'Hello World!', 'data': request.data},
            status=status.HTTP_200_OK
        )