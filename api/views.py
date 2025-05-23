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
    Procesa archivos de manera diferente según su nombre.
    """
    parser_classes = (MultiPartParser, FormParser)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Configuración de procesadores por nombre de archivo
        self.file_processors = {
            'occidente': self.process_occidente_file,
            'popular': self.process_popular_file,
            # Agregar más procesadores aquí según sea necesario
            # 'banco_x': self.process_banco_x_file,
            # 'empresa_y': self.process_empresa_y_file,
        }

    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response({'error': 'No se proporcionó ningún archivo'}, status=status.HTTP_400_BAD_REQUEST)
        
        excel_file = request.FILES['file']
        
        # Verificar extensión
        if not excel_file.name.endswith(('.xlsx', '.xls', '.csv')):
            return Response({'error': 'El archivo debe ser de tipo Excel (.xlsx, .xls) o CSV (.csv)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Determinar el tipo de archivo basado en el nombre
            file_type = self.determine_file_type(excel_file.name)
            
            # Parámetros adicionales opcionales
            worksheet_name = request.data.get('worksheet', None)
            
            # Convertir worksheet_name a entero si es un número, o mantenerlo como string
            if worksheet_name is not None:
                try:
                    worksheet_name = int(worksheet_name)
                except ValueError:
                    pass
            
            header_row = request.data.get('header_row')
            if header_row and header_row.isdigit():
                header_row = int(header_row)
            else:
                header_row = 0
                
            skip_rows = request.data.get('skip_rows')
            if skip_rows and skip_rows.isdigit():
                skip_rows = int(skip_rows)
            else:
                skip_rows = None
                
            remove_unnamed = request.data.get('remove_unnamed', 'true').lower() == 'true'
            
            # Procesar el archivo según su tipo
            if file_type in self.file_processors:
                result = self.file_processors[file_type](
                    excel_file, 
                    sheet_name=worksheet_name, 
                    header=header_row,
                    skiprows=skip_rows,
                    remove_unnamed=remove_unnamed
                )
            else:
                # Procesamiento por defecto
                result = self.process_default_file(
                    excel_file, 
                    sheet_name=worksheet_name, 
                    header=header_row,
                    skiprows=skip_rows,
                    remove_unnamed=remove_unnamed
                )
            
            # Agregar información del tipo de archivo detectado
            result['file_type'] = file_type
            result['original_filename'] = excel_file.name
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            return Response({
                'error': f'Error al procesar el archivo: {str(e)}',
                'traceback': traceback.format_exc(),
                'filename': excel_file.name,
                'detected_type': self.determine_file_type(excel_file.name)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def determine_file_type(self, filename):
        """
        Determina el tipo de archivo basado en su nombre.
        Retorna la clave del procesador correspondiente o 'default' si no coincide.
        """
        filename_lower = filename.lower()
        
        if 'occidente' in filename_lower:
            return 'occidente'
        elif 'popular' in filename_lower:
            return 'popular'
        # Agregar más condiciones aquí
        # elif 'banco_x' in filename_lower:
        #     return 'banco_x'
        # elif 'empresa_y' in filename_lower:
        #     return 'empresa_y'
        else:
            return 'default'

    def process_occidente_file(self, file, sheet_name=None, header=0, skiprows=None, remove_unnamed=True):
        """
        Procesador específico para archivos de Occidente.
        Mantiene la estructura original del Excel exactamente como viene.
        Estructura esperada: Fecha | importe_credito | importe_debito | referencia | Info_detallada
        """
        try:
            # Leer el archivo base
            df = self._read_excel_file(file, sheet_name, header, skiprows)
            
            # Para archivos de Occidente, mantener la estructura EXACTA del Excel original
            # NO eliminar columnas unnamed para preservar la estructura
            # NO renombrar columnas para mantener los nombres originales
            
            # Solo eliminar filas completamente vacías
            df = df.dropna(how='all')
            
            # Mantener valores NaN como están o convertir a vacío solo si es necesario
            # Para preservar la estructura, usar fillna con cuidado
            df = df.fillna('')
            
            # Convertir valores a string manteniendo el formato original
            for col in df.columns:
                if col in ['importe_credito', 'importe_debito']:
                    # Para columnas de montos, mantener formato numérico si es posible
                    try:
                        # Intentar mantener como numérico, pero convertir a string para JSON
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        df[col] = df[col].astype(str)
                    except:
                        df[col] = df[col].astype(str)
                elif 'fecha' in col.lower():
                    # Para fechas, mantener formato original
                    df[col] = df[col].astype(str)
                else:
                    # Para el resto, convertir a string manteniendo el contenido original
                    df[col] = df[col].astype(str)
            
            # Convertir DataFrame a lista de diccionarios manteniendo estructura original
            result = df.to_dict(orient='records')
            
            # Información adicional específica para archivos de Occidente
            total_creditos = 0
            total_debitos = 0
            
            # Calcular totales si existen las columnas
            if 'importe_credito' in df.columns:
                try:
                    total_creditos = pd.to_numeric(df['importe_credito'], errors='coerce').sum()
                except:
                    pass
            
            if 'importe_debito' in df.columns:
                try:
                    total_debitos = pd.to_numeric(df['importe_debito'], errors='coerce').sum()
                except:
                    pass
            
            return {
                'data': result,
                'metadata': {
                    'total_rows': len(result),
                    'columns': df.columns.tolist(),
                    'sheet_name': sheet_name,
                    'processor_type': 'occidente',
                    'original_structure_preserved': True,
                    'transformations_applied': [
                        'empty_rows_removed',
                        'data_type_conversion_minimal',
                        'original_column_names_preserved'
                    ]
                },
                'summary': {
                    'total_creditos': float(total_creditos) if total_creditos else 0,
                    'total_debitos': float(total_debitos) if total_debitos else 0,
                    'balance': float(total_creditos - total_debitos) if (total_creditos or total_debitos) else 0,
                    'transacciones_credito': len([r for r in result if r.get('importe_credito', '0') != '0']),
                    'transacciones_debito': len([r for r in result if r.get('importe_debito', '0') != '0'])
                }
            }
            
        except Exception as e:
            raise Exception(f"Error procesando archivo Occidente: {str(e)}")

    def process_popular_file(self, file, sheet_name=None, header=0, skiprows=None, remove_unnamed=True):
        """
        Procesador específico para archivos Popular.
        Personaliza la lógica según las necesidades específicas de estos archivos.
        """
        try:
            # Leer el archivo base
            df = self._read_excel_file(file, sheet_name, header, skiprows)
            
            # Procesamiento específico para Popular
            if remove_unnamed:
                unnamed_cols = [col for col in df.columns if 'Unnamed:' in str(col)]
                if unnamed_cols:
                    df = df.drop(columns=unnamed_cols)
            
            # Limpiar datos específicos para Popular
            df = df.dropna(how='all')
            df = df.fillna('N/A')  # Diferente valor por defecto para Popular
            
            # Transformaciones específicas para Popular
            # Ejemplo: Diferentes mapeos de columnas
            column_mapping = {
                # Agregar mapeo de columnas específico para Popular
                # 'Col_Popular_1': 'columna_estandar_1',
                # 'Col_Popular_2': 'columna_estandar_2',
            }
            df = df.rename(columns=column_mapping)
            
            # Formateo específico para Popular
            for col in df.columns:
                if 'fecha' in col.lower():
                    # Formateo específico de fechas para Popular
                    try:
                        df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
                    except:
                        df[col] = df[col].astype(str)
                else:
                    df[col] = df[col].astype(str)
            
            # Aplicar filtros específicos para Popular
            # Ejemplo: Agregar columnas calculadas
            # df['total_calculado'] = df['columna1'].astype(float) + df['columna2'].astype(float)
            
            result = df.to_dict(orient='records')
            
            return {
                'data': result,
                'metadata': {
                    'total_rows': len(result),
                    'columns': df.columns.tolist(),
                    'sheet_name': sheet_name,
                    'processor_type': 'popular',
                    'transformations_applied': [
                        'removed_unnamed_columns' if remove_unnamed else None,
                        'date_formatting_applied',
                        'custom_null_handling'
                    ]
                },
                'summary': {
                    'date_columns_processed': [col for col in df.columns if 'fecha' in col.lower()],
                    'calculated_columns_added': []  # Lista de columnas calculadas añadidas
                }
            }
            
        except Exception as e:
            raise Exception(f"Error procesando archivo Popular: {str(e)}")

    def process_default_file(self, file, sheet_name=None, header=0, skiprows=None, remove_unnamed=True):
        """
        Procesador por defecto para archivos que no coinciden con ningún tipo específico.
        """
        return self.process_excel_file(file, sheet_name, header, skiprows, remove_unnamed)

    def _read_excel_file(self, file, sheet_name=None, header=0, skiprows=None):
        """
        Método auxiliar para leer archivos Excel de manera consistente.
        """
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, header=header, skiprows=skiprows)
        else:
            if sheet_name is None:
                xl = pd.ExcelFile(file)
                sheet_names = xl.sheet_names
                if not sheet_names:
                    raise ValueError("El archivo Excel no contiene hojas de trabajo")
                sheet_name = sheet_names[0]
            
            df = pd.read_excel(file, sheet_name=sheet_name, header=header, skiprows=skiprows)
        
        return df

    def process_excel_file(self, file, sheet_name=None, header=0, skiprows=None, remove_unnamed=True):
        """
        Procesamiento básico de archivos Excel (método original mantenido para compatibilidad).
        """
        try:
            df = self._read_excel_file(file, sheet_name, header, skiprows)
            
            if remove_unnamed:
                unnamed_cols = [col for col in df.columns if 'Unnamed:' in str(col)]
                if unnamed_cols:
                    df = df.drop(columns=unnamed_cols)
            
            df = df.dropna(how='all')
            df = df.fillna('')
            
            for col in df.columns:
                df[col] = df[col].astype(str)
            
            result = df.to_dict(orient='records')
            
            return {
                'data': result,
                'metadata': {
                    'total_rows': len(result),
                    'columns': df.columns.tolist(),
                    'sheet_name': sheet_name,
                    'processor_type': 'default'
                }
            }
            
        except Exception as e:
            if "not found" in str(e) and sheet_name is not None:
                try:
                    xl = pd.ExcelFile(file)
                    sheet_names = xl.sheet_names
                    
                    if sheet_names:
                        return self.process_excel_file(
                            file, 
                            sheet_name=sheet_names[0],
                            header=header,
                            skiprows=skiprows,
                            remove_unnamed=remove_unnamed
                        )
                except:
                    pass
            
            raise e

