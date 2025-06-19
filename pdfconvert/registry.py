from pdfconvert.parsers.bancolombia import ParserBancolombia
from pdfconvert.serializers.bancolombia import BancolombiaSerializer
from pdfconvert.utils.parse_bancolombia import parse_bancolombia, parse_bancolombia_transformado
from pdfconvert.parsers.davivienda import ParserDavivienda
from pdfconvert.utils.parse_davivienda import (
    parse_davivienda,
    parse_davivienda_transformado,
)
from pdfconvert.parsers.bogota import ParserBogota
from pdfconvert.utils.parse_bogota import (
    parse_bogota,
    parse_bogota_transformado,
)
from pdfconvert.parsers.casa_bolsa import ParserCasaBolsa
from pdfconvert.utils.parse_casa_bolsa import (
    parse_casa_bolsa,
    parse_casa_bolsa_transformado,
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
    'bogota': {
        'parser':    ParserBogota(parse_func=parse_bogota),
        'serializer': None,
    },
    'bogota_transformado': {
        'parser':    ParserBogota(parse_func=parse_bogota_transformado),
        'serializer': None,
    },'casa_bolsa': {
        'parser':    ParserCasaBolsa(parse_func=parse_casa_bolsa),
        'serializer': None,
    },
    'casa_bolsa_transformado': {
        'parser':    ParserCasaBolsa(parse_func=parse_casa_bolsa_transformado),
        'serializer': None,
    },
}

def get_handler(key: str):
    return HANDLERS.get(key)