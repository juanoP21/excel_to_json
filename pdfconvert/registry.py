from pdfconvert.parsers.bancolombia import ParserBancolombia
from pdfconvert.serializers.bancolombia import BancolombiaSerializer
from pdfconvert.utils.parse_bancolombia import parse_bancolombia, parse_bancolombia_transformado
from pdfconvert.parsers.davivienda import ParserDavivienda
from pdfconvert.utils.parse_davivienda import (
    parse_davivienda,
    parse_davivienda_transformado,
)

HANDLERS = {
    'bancolombia': {
        'parser':    ParserBancolombia(parse_func=parse_bancolombia),
        'serializer': BancolombiaSerializer
    },
    'bancolombia_transformado': {
        'parser':    ParserBancolombia(parse_func=parse_bancolombia_transformado),
        'serializer': None  # No usamos serializer aquí
    },
    'davivienda': {
        'parser':    ParserDavivienda(parse_func=parse_davivienda),
        'serializer': None,
    },
    'davivienda_transformado': {
        'parser':    ParserDavivienda(parse_func=parse_davivienda_transformado),
        'serializer': None,
    },
}

def get_handler(key: str):
    return HANDLERS.get(key)