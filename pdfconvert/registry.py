# pdfconvert/registry.py
from pdfconvert.parsers.bancolombia    import ParserBancolombia
from pdfconvert.serializers.bancolombia import BancolombiaSerializer
from pdfconvert.parsers.bancolombia    import ParserBancolombia
from pdfconvert.utils.parse_bancolombia import parse_bancolombia
from pdfconvert.serializers.bancolombia import BancolombiaSerializer
HANDLERS = {
    'bancolombia': {
        'parser':    ParserBancolombia(),
        'serializer': BancolombiaSerializer
    }, 'bancolombia': {
        # ahora inyectamos explícitamente la función de parseo
        'parser':    ParserBancolombia(parse_func=parse_bancolombia),
        'serializer': BancolombiaSerializer
    },
    # aquí podrás agregar otros bancos...
}

def get_handler(key: str):
    return HANDLERS.get(key)
