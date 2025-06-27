from .plaintext import PlainTextParser
from .bancolombia import ParserBancolombia
from .bogota import ParserBogota
from .davivienda import ParserDavivienda
from .casa_bolsa import ParserCasaBolsa
from .textract import TextractParser
from .ocr_textract import TextractOCRParser
__all__ = [
    "PlainTextParser",
    "ParserBancolombia",
    "ParserBogota",
    "ParserDavivienda",
    "ParserCasaBolsa",
    "TextractParser",
    "TextractOCRParser",
]