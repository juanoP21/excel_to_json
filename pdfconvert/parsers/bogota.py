from pdfconvert.utils.parse_bogota import parse_bogota, parse_bogota_transformado

class ParserBogota:
    """Parser para el formato de texto plano de Banco de Bogota."""

    def __init__(self, parse_func=None):
        self.parse_func = parse_func or parse_bogota

    def parse(self, text: str) -> dict:
        return self.parse_func(text)