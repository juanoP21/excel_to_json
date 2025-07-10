import os
import re
import calendar

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser

from .parsers import TextractOCRParser


def _format_spanish_date(date_str: str) -> str:
    """Return date in DD/mm/yyyy format; if day missing, use last day of the month."""
    s = date_str.strip().lower().replace(' del ', ' de ')
    # Numeric date
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if m:
        d, mo, y = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{int(y):04d}"
    # Textual date
    months = {
        'enero':'01','febrero':'02','marzo':'03','abril':'04','mayo':'05','junio':'06',
        'julio':'07','agosto':'08','septiembre':'09','setiembre':'09','octubre':'10',
        'noviembre':'11','diciembre':'12'
    }
    m = re.match(
        r"^(?:(\d{1,2})(?:\s+de)?\s+)?"
        r"([a-zñáéíóú]+)"
        r"(?:\s+(?:de|del))?\s+(\d{4})$", s, re.IGNORECASE
    )
    if not m:
        return date_str
    day, mon, year = m.groups()
    mm = months.get(mon.lower())
    if not mm:
        return date_str
    if day:
        dd = int(day)
    else:
        dd = calendar.monthrange(int(year), int(mm))[1]
    return f"{dd:02d}/{mm}/{year}"


def _extract_receipts(text: str) -> list[dict]:
    """Extract receipts from OCR text using regex patterns for specified cities and omit footers."""
    # Define cities for header matching
    cities = [
        'Palmira', 'Pradera', 'Candelaria', 'Villagorgona', 'Tuluá',
        'Buenaventura', 'Cartago', 'Guadalajara de Buga', 'Florida',
        'Santiago de Cali', 'Santiago de cali', 'Cali'
    ]
    
    # Build city alternation regex, escape spaces
    city_pattern = '|'.join(re.escape(c) for c in cities)

    header_re = re.compile(
        rf"""(?m)                           # Multilínea
        ^(?P<ciudad>{city_pattern})\b      # Captura la ciudad base
        [^\n,]*,\s*                        # Permite sufijos hasta la coma
        (?P<fecha>
            \d{{1,2}}/\d{{1,2}}/\d{{2,4}} |                    # Formato numérico
            \d{{1,2}}(?:\s+de)?\s+[A-Za-zñáéíóú]+(?:\s+(?:de|del))?\s+\d{{4}}
        )
        """,
        re.IGNORECASE | re.VERBOSE
    )
    
    info_re = re.compile(
        r"Debe\s*A:\s*(?P<nombre>.*?)\r?\n.*?"
        r"Cédula[:\s]*(?P<cedula>[\d\.\s]+).*?"
        r"No\.?\s*DE\s*DALE[:\s]*(?P<dale>[\d\s]+)",
        re.IGNORECASE | re.DOTALL
    )
    
    total_re = re.compile(r"(?mi)(?:La suma de|TOTAL).*?\$?\s*([\d\.,]+)")

    receipts = []
    headers = list(header_re.finditer(text))
    
    for idx, m in enumerate(headers):
        city_raw = m.group('ciudad').strip()
        date_raw = m.group('fecha').strip()
        date_fmt = _format_spanish_date(date_raw)

        start = m.end()
        end = headers[idx+1].start() if idx+1 < len(headers) else len(text)
        block = text[start:end]
        
        # Remove footer starting at FMR or similar patterns
        block = re.split(r"\n(?:FMR|FEMR|TEMR|FHR)\b", block)[0]

        info = info_re.search(block)
        name = info.group('nombre').strip() if info else ''
        ced = info.group('cedula').replace('.', '').replace(' ', '').strip() if info else None
        dale = info.group('dale').replace(' ', '').strip() if info else None

        tot_match = total_re.search(block)
        total = tot_match.group(1).strip() if tot_match else None

        receipts.append({
            'ciudad': city_raw,
            'fecha': date_fmt,
            'nombre': name,
            'cedula': ced,
            'no_de_dale': dale,
            'total': total,
        })
    
    return receipts


class TextractOCRView(APIView):
    """APIView for extracting text and parsing receipts with specified cities."""
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'error':'Archivo no proporcionado','detail':'campo "file" requerido'},
                            status=status.HTTP_400_BAD_REQUEST)

        bucket = os.getenv('TEXTRACT_S3_BUCKET')
        if not bucket:
            return Response({'error':'TEXTRACT_S3_BUCKET no configurado'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        parser = TextractOCRParser(bucket)
        try:
            payload = parser.parse(uploaded)
        except Exception as e:
            return Response({'error':'Error al procesar OCR','detail':str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        text = payload.get('text','')
        try:
            data = _extract_receipts(text)
        except Exception as e:
            return Response({'error':'Error al extraer recibos','detail':str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'results': data}, status=status.HTTP_200_OK)