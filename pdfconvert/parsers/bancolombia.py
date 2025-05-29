# pdfconvert/parsers/bancolombia.py
from pdfconvert.utils.parse_bancolombia import parse_bancolombia

class ParserBancolombia:
    """
    Parser para el formato de texto plano de Bancolombia.
    """
    def __init__(self, parse_func=None):
      # si no se pasa ninguna función, usamos la original
        self.parse_func = parse_func or parse_bancolombia

    def parse(self, text: str) -> dict:
        return self.parse_func(text)
