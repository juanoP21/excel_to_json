from pdfconvert.utils.parse_casa_bolsa import parse_casa_bolsa, parse_casa_bolsa_transformado


class ParserCasaBolsa:
    """Parser para el formato de texto plano de Casa Bolsa."""

    def __init__(self, parse_func=None):
        self.parse_func = parse_func or parse_casa_bolsa

    def parse(self, text: str) -> dict:
        return self.parse_func(text)