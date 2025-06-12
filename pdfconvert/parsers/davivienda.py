from pdfconvert.utils.parse_davivienda import parse_davivienda, parse_davivienda_transformado


class ParserDavivienda:
    """Parser para el formato de texto plano de Davivienda."""

    def __init__(self, parse_func=None):
        self.parse_func = parse_func or parse_davivienda

    def parse(self, text: str) -> dict:
        return self.parse_func(text)