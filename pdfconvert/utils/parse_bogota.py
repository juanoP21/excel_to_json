import re
from datetime import datetime


def _clean_number(value: str) -> str:
    value = value.replace('.', '').replace(',', '.')
    return value.strip()


def _clean_ref(value: str) -> str:
    value = value.strip().strip("'")
    value = re.sub(r'^0+', '', value)
    return value


def parse_bogota(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    start = 0
    for i, l in enumerate(lines):
        if l.lower().startswith('fecha'):
            start = i + 1
            break

    movimientos = []
    date_re = re.compile(r'^\d{2}/\d{2}/\d{4}')
    amount_re = re.compile(r'^\d[\d\.]*,\d{2}$')
    dc_re = re.compile(r'^(CR|DR)$', re.IGNORECASE)

    i = start
    while i < len(lines):
        line = lines[i]
        if date_re.match(line):
            tokens = line.split()
            fecha = tokens[0]
            doc = tokens[1] if len(tokens) > 1 else ''
            descripcion_parts = [' '.join(tokens[2:])] if len(tokens) > 2 else []
            i += 1
            while i < len(lines) and not amount_re.match(lines[i]):
                descripcion_parts.append(lines[i])
                i += 1
            descripcion = ' '.join(descripcion_parts).strip()

            valor = '0'
            if i < len(lines) and amount_re.match(lines[i]):
                valor = _clean_number(lines[i])
                i += 1

            dc = ''
            if i < len(lines) and dc_re.match(lines[i]):
                dc = lines[i].upper()
                i += 1

            if i < len(lines) and (',' in lines[i]):
                i += 1

            nit = ''
            ref1 = ''
            if i < len(lines) and lines[i].isdigit():
                nit = lines[i]
                i += 1
            if i < len(lines) and lines[i].isdigit():
                ref1 = lines[i]
                i += 1

            ofi = ''
            if i < len(lines) and not date_re.match(lines[i]):
                ofi = lines[i]
                i += 1

            movimientos.append({
                'Fecha': fecha,
                'Doc': doc,
                'Tran': descripcion,
                'Ofi': ofi,
                'Valor Total': valor,
                'NIT Origen': nit,
                'Referencia 1': ref1,
                'Desc Mot.': descripcion,
                'D/C': dc,
            })
        else:
            i += 1

    totales = {}
    for idx, l in enumerate(lines):
        if l.lower().startswith('total abonos'):
            nums = re.findall(r'([\d\.]+,\d{2})', l)
            if len(nums) >= 3:
                totales['Total Abonos'] = _clean_number(nums[0])
                totales['Total retiros y debitos'] = _clean_number(nums[1])
                totales['Movimiento neto'] = _clean_number(nums[2])
            break

    return {
        'movimientos': movimientos,
        'totales': totales,
        'transformado': parse_bogota_transformado({'movimientos': movimientos, 'totales': totales})
    }


def parse_bogota_transformado(data: dict) -> dict:
    movimientos = data['movimientos']
    resultado = []
    for mov in movimientos:
        fecha = mov.get('Fecha', '')
        try:
            valor = float(mov.get('Valor Total', '0') or 0)
        except Exception:
            valor = 0.0
        dc = mov.get('D/C', '').upper()
        if dc == 'CR':
            credito = f"{valor:.2f}"
            debito = '0'
        else:
            debito = f"{valor:.2f}"
            credito = '0'
        nit = _clean_ref(mov.get('NIT Origen', ''))
        ref1 = _clean_ref(mov.get('Referencia 1', ''))
        referencia = f"{nit}-{ref1}" if nit and ref1 else nit or ref1
        resultado.append({
            'Fecha': fecha,
            'importe_credito': credito,
            'importe_debito': debito,
            'referencia': referencia,
            'Info_detallada': mov.get('Desc Mot.', ''),
            'Info_detallada2': mov.get('Ofi', ''),
        })
    return {'result': resultado}