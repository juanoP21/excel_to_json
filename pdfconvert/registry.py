# pdfconvert/registry.py
from pdfconvert.parsers.bancolombia import ParserBancolombia
from pdfconvert.serializers.bancolombia import BancolombiaSerializer
from pdfconvert.utils.parse_bancolombia import parse_bancolombia, parse_bancolombia_transformado

HANDLERS = {
    'bancolombia': {
        'parser':    ParserBancolombia(parse_func=parse_bancolombia),
        'serializer': BancolombiaSerializer
    },
    'bancolombia_transformado': {
        'parser':    ParserBancolombia(parse_func=parse_bancolombia_transformado),
        'serializer': None  # No usamos serializer aquí
    },
}

def get_handler(key: str):
    return HANDLERS.get(key)