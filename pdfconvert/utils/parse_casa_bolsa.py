import re
from datetime import datetime


def parse_casa_bolsa(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    date_re = re.compile(r'^\d{4}-\d{2}-\d{2}')
    # algunas lineas pueden iniciar con "CUENTA OMNIBUS" o "CUENTA ÓMNIBUS"
    alt_start_re = re.compile(r'^cuenta\s+[oó]mnibus.*\d{4}-\d{2}-\d{2}',
                              re.IGNORECASE)
    movimientos = []
    i = 0
    while i < len(lines):
        if date_re.match(lines[i]) or alt_start_re.match(lines[i]):
            block = [lines[i]]
            i += 1
            while i < len(lines) and not date_re.match(lines[i]) and not alt_start_re.match(lines[i]):
                block.append(lines[i])
                i += 1
            movimientos.append(_parse_block(block))
        else:
            i += 1
    return {"movimientos": movimientos, "transformado": parse_casa_bolsa_transformado({"movimientos": movimientos})}


def _parse_block(block):
    joined = " ".join(block)
    m_date = re.search(r"\d{4}-\d{2}-\d{2}", joined)
    fecha = m_date.group(0) if m_date else ""
    rest = joined[m_date.end():].strip() if m_date else joined
    tokens = rest.split()
    tipo_transaccion = tokens[0] if tokens else ""
    # buscar primera ocurrencia de $ como indicador de valor movimiento
    m_val = re.search(r'\$-?[\d,.]+', rest)
    valor = m_val.group().replace("$", "") if m_val else "0"
    valor_clean = valor.replace(',', '')
    try:
        valor_float = float(valor_clean)
    except Exception:
        valor_float = 0.0
    pre_val = rest[:m_val.start()] if m_val else rest
    detalle_tokens = pre_val.split()
    if detalle_tokens and detalle_tokens[0].lower() == tipo_transaccion.lower():
        detalle_tokens.pop(0)
    while detalle_tokens and detalle_tokens[0].lower() == tipo_transaccion.lower():
        detalle_tokens.pop(0)
    while detalle_tokens and re.fullmatch(r'\d[\d-]*', detalle_tokens[0]):
        detalle_tokens.pop(0)
    while detalle_tokens and re.match(r'^[\d,.-]+$', detalle_tokens[-1]):
        detalle_tokens.pop()
    while detalle_tokens and detalle_tokens[-1] == '-':
        detalle_tokens.pop()
    detalle = " ".join(detalle_tokens)
    return {
        "Fecha": fecha,
        "Tipo": tipo_transaccion,
        "Detalle": detalle,
        "Valor": valor_float,
    }


def parse_casa_bolsa_transformado(data: dict) -> dict:
    resultado = []
    for mov in data['movimientos']:
        fecha_raw = mov.get('Fecha', '')
        try:
            fecha_obj = datetime.fromisoformat(fecha_raw)
            fecha = fecha_obj.strftime('%d/%m/%Y')
        except Exception:
            fecha = fecha_raw
        tipo = mov.get('Tipo', '')
        detalle = mov.get('Detalle', '')
        valor = mov.get('Valor', 0)
        credito = ''
        debito = ''
        tipo_low = tipo.lower()
        if tipo_low in ['deposito', 'depósito']:
            credito = f"{abs(valor):.2f}"
        elif tipo_low in ['retiro', 'rete', 'retefuente', 'rete fuente', 'rete_fuente']:
            debito = f"{abs(valor):.2f}"
        else:
            if valor >= 0:
                credito = f"{valor:.2f}"
            else:
                debito = f"{-valor:.2f}"
        resultado.append({
            'Fecha': fecha,
            'importe_credito': credito,
            'importe_debito': debito,
            'referencia': tipo,
            'Info_detallada': detalle,
            'Info_detallada2': ''
        })
    return {'result': resultado}