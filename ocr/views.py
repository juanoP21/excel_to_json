from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser

from .parsers import TextractOCRParser
import re


def _format_spanish_date(date_str: str) -> str:
    """Return date in ``DD/mm/yyyy`` format if possible.

    If the day number is missing, the last day of the month is used.
    """
    match = re.search(
        r"(?:(\d{1,2})\s+de\s+)?([A-Za-z\u00f1\u00e1\u00e9\u00ed\u00f3\u00fa]+)\s+del?\s*(\d{4})",
        date_str,
        re.IGNORECASE,
    )
    if not match:
        return date_str
    day, month_name, year = match.groups()
    months = {
        "enero": "01",
        "febrero": "02",
        "marzo": "03",
        "abril": "04",
        "mayo": "05",
        "junio": "06",
        "julio": "07",
        "agosto": "08",
        "septiembre": "09",
        "setiembre": "09",
        "octubre": "10",
        "noviembre": "11",
        "diciembre": "12",
    }
    month = months.get(month_name.lower())
    if not month:
        return date_str

    if day:
        day_num = int(day)
    else:
        import calendar
        day_num = calendar.monthrange(int(year), int(month))[1]

    return f"{day_num:02d}/{month}/{year}"


def _extract_receipts(text: str) -> list[dict]:
    """Parse Textract plain text into structured receipt data."""
    pattern = re.compile(
        r"Santiago de Ca(?:li|ll),?\s*(?P<fecha>.*?\d{4}).*?"
        r"DEBE A:\s*(?P<debe_a>.*?)\nLa suma.*?TOTAL\n\$?\.?\s*(?P<total>[\d\.,]+)",
        re.IGNORECASE | re.DOTALL,
    )

    receipts: list[dict] = []
    for match in pattern.finditer(text):
        raw_fecha = match.group("fecha").strip()
        fecha = _format_spanish_date(raw_fecha)
        data_block = match.group("debe_a").strip()
        total = match.group("total").strip()

        name = data_block.splitlines()[0].strip() if data_block else ""
        cedula_match = re.search(r"Cedula[:\s]*(\d+)", data_block, re.IGNORECASE)
        cedula = cedula_match.group(1) if cedula_match else None
        dale_match = re.search(
            r"No\.?\s*DE\s*DALE:?\s*(\d+)", data_block, re.IGNORECASE
        )
        no_de_dale = dale_match.group(1) if dale_match else None

        block = match.group(0)
        turnos_nums = re.findall(r"\n(\d+)\n\d{2}/\d{2}/\d{4}", block)
        turnos = max(map(int, turnos_nums)) if turnos_nums else None

        receipts.append(
            {
                "fecha": fecha,
                "nombre": name,
                "Cedula": cedula,
                "No. DE DALE": no_de_dale,
                "Turnos": turnos,
                "total": total,
            }
        )

    return receipts

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
        text = payload.get("text", "")
        data = _extract_receipts(text)

        return Response({"results": data}, status=status.HTTP_200_OK)
