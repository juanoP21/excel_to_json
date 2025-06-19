import re
from datetime import datetime


def parse_casa_bolsa(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Ubicamos la sección "Movimiento del Periodo" y procesamos solo a partir de allí
    start = 0
    for i, l in enumerate(lines):
        if "movimiento del periodo" in l.lower():
            start = i + 1
            break
    lines = lines[start:]

    # Cada transacción de Cuenta Ómnibus inicia con esta línea
    alt_start_re = re.compile(r'^cuenta\s+[oó]mnibus.*\d{4}-\d{2}-\d{2}', re.IGNORECASE)

    movimientos = []
    i = 0
    while i < len(lines):
        if alt_start_re.match(lines[i]):
            block = [lines[i]]
            i += 1
            while i < len(lines) and not alt_start_re.match(lines[i]):
                block.append(lines[i])
                i += 1
            parsed = _parse_block(block)
            # Omitimos movimientos que correspondan al saldo inicial
            tipo_low = parsed.get("Tipo", "").lower()
            detalle_low = parsed.get("Detalle", "").lower()
            if tipo_low == "saldo" and "inicial" in detalle_low:
                continue
            movimientos.append(parsed)
        else:
            i += 1

    return {
        "movimientos": movimientos,
        "transformado": parse_casa_bolsa_transformado({"movimientos": movimientos}),
    }


def _parse_block(block):
    joined = " ".join(block)
    m_date = re.search(r"\d{4}-\d{2}-\d{2}", joined)
    fecha = m_date.group(0) if m_date else ""
    rest = joined[m_date.end():].strip() if m_date else joined
    tokens = rest.split()
    tipo_transaccion = tokens[0] if tokens else ""
    if len(tokens) > 1:
        tok1 = tokens[1]
        first_lower = tipo_transaccion.lower()
        second_lower = tok1.lower()
        if (
            first_lower == "rete" and second_lower == "fuente"
        ) or (
            first_lower == "saldo" and second_lower == "inicial"
        ):
            tipo_transaccion = f"{tipo_transaccion} {tok1}"
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
    tipo_tokens = tipo_transaccion.split()
    for tt in tipo_tokens:
        if detalle_tokens and detalle_tokens[0].lower() == tt.lower():
            detalle_tokens.pop(0)
    while (
        len(detalle_tokens) > 1
        and detalle_tokens[0].lower() == tipo_tokens[0].lower()
        and (
            detalle_tokens[1].lower() == tipo_tokens[0].lower()
            or re.fullmatch(r"\d[\d-]*", detalle_tokens[1])
        )
    ):
        detalle_tokens.pop(0)
    while detalle_tokens and re.fullmatch(r"\d[\d-]*", detalle_tokens[0]):
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
        if tipo_low.startswith('deposito') or tipo_low.startswith('depósito'):
            credito = f"{abs(valor):.2f}"
        elif (
            tipo_low.startswith('retiro')
            or tipo_low.startswith('rete fuente')
            or tipo_low.startswith('retefuente')
            or tipo_low == 'rete'
        ):
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