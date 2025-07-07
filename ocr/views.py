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
    print(">>> _extract_receipts: Iniciando extracción de recibos")
    print(f">>> _extract_receipts: Texto de entrada tiene {len(text)} caracteres")
    
    pattern = re.compile(
        r"Santiago de Ca(?:li|ll),?\s*(?P<fecha>.*?\d{4}).*?"
        r"DEBE A:\s*(?P<debe_a>.*?)\nLa suma.*?TOTAL\n\$?\.?\s*(?P<total>[\d\.,]+)",
        re.IGNORECASE | re.DOTALL,
    )

    receipts: list[dict] = []
    matches_found = 0
    for match in pattern.finditer(text):
        matches_found += 1
        print(f">>> _extract_receipts: Encontrada coincidencia #{matches_found}")
        raw_fecha = match.group("fecha").strip()
        fecha = _format_spanish_date(raw_fecha)
        data_block = match.group("debe_a").strip()
        total = match.group("total").strip()
        
        print(f">>> _extract_receipts: fecha raw='{raw_fecha}', formateada='{fecha}'")
        print(f">>> _extract_receipts: total='{total}'")

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

    print(f">>> _extract_receipts: Total de recibos extraídos: {len(receipts)}")
    if not receipts:
        print(">>> _extract_receipts: No se encontraron recibos. Mostrando muestra del texto:")
        print(f">>> _extract_receipts: Primeros 500 caracteres: {text[:500]}")
    
    return receipts

class TextractOCRView(APIView):
    """Return plain text extracted from a PDF using Amazon Textract."""
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        print(">>> OCR VIEW: Recibida petición POST")
        file = request.FILES.get('file')
        if not file:
            print(">>> OCR VIEW: No se proporcionó archivo")
            return Response(
                {"error": "Archivo no proporcionado", "detail": "Se requiere el campo 'file'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        print(f">>> OCR VIEW: Archivo recibido - {file.name}, tamaño: {file.size} bytes")
        parser = TextractOCRParser()
        try:
            print(">>> OCR VIEW: Iniciando procesamiento con TextractOCRParser")
            payload = parser.parse(file)
            print(">>> OCR TEXTRACT PAYLOAD:", payload)
        except Exception as e:
            print(">>> OCR TEXTRACT ERROR:", e)
            return Response(
                {"error": "Error al procesar el archivo", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        text = payload.get("text", "")
        print(f">>> OCR VIEW: Texto extraído, longitud: {len(text)} caracteres")
        print(f">>> OCR VIEW: Primeros 200 caracteres del texto: {text[:200]}")
        
        data = _extract_receipts(text)
        print(f">>> OCR VIEW: Recibos extraídos: {len(data)} elementos")
        print(f">>> OCR VIEW: Datos extraídos: {data}")

        return Response({"results": data}, status=status.HTTP_200_OK)
