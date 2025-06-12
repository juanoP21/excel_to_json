import re
from datetime import datetime


def _clean_number(value: str) -> str:
    value = value.replace('.', '').replace(',', '.')
    return value.strip()


def _clean_ref(value: str) -> str:
    value = value.strip().strip("'")
    value = re.sub(r'^0+', '', value)
    return value


def parse_davivienda(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    start = next((i for i, l in enumerate(lines) if l.lower().startswith('fecha')), len(lines))
    end = next((i for i, l in enumerate(lines) if l.lower().startswith('total abonos')), len(lines))

    movimientos = []
    for line in lines[start + 1:end]:
        if '$' not in line:
            continue
        try:
            prefix, val_total, rest = line.split('$', 2)
        except ValueError:
            continue
        val_total = _clean_number(val_total)
        tail = rest.strip().split()
        if not tail:
            continue
        valor_cheque = _clean_number(tail[0])
        if len(tail) >= 5:
            nit = tail[1]
            ref1 = tail[2]
            ref2 = tail[3]
            terminal = tail[4]
        else:
            nit = ''
            ref1 = tail[1] if len(tail) > 1 else ''
            ref2 = tail[2] if len(tail) > 2 else ''
            terminal = tail[3] if len(tail) > 3 else ''

        jor_match = re.search(r'\s+(Normal|Adicional)\s+', prefix)
        jor = jor_match.group(1) if jor_match else ''
        part1 = prefix[:jor_match.start()].strip() if jor_match else prefix
        part2 = prefix[jor_match.end():].strip() if jor_match else ''
        parts = part1.split()
        if len(parts) < 4:
            continue
        fecha, doc = parts[0], parts[1]
        tran = ' '.join(parts[2:4])
        ofi = ' '.join(parts[4:])
        tokens2 = part2.split()
        hora = tokens2[0] if len(tokens2) > 0 else ''
        mot = tokens2[1] if len(tokens2) > 1 else ''
        desc_mot = ' '.join(tokens2[2:]) if len(tokens2) > 2 else ''

        movimientos.append({
            'Fecha': fecha,
            'Doc': doc,
            'Tran': tran,
            'Ofi': ofi,
            'Jor': jor,
            'Hora': hora,
            'Mot': mot,
            'Desc Mot.': desc_mot,
            'Valor Total': val_total,
            'Valor Cheque': valor_cheque,
            'NIT Origen': nit,
            'Referencia 1': ref1,
            'Referencia 2': ref2,
            'Terminal': terminal,
        })

    totales = {}
    if end < len(lines) - 1:
        nums = re.findall(r'\$\s*([\d.,]+)', lines[end + 1])
        if len(nums) >= 3:
            totales['Total Abonos'] = _clean_number(nums[0])
            totales['Total retiros y debitos'] = _clean_number(nums[1])
            totales['Movimiento neto'] = _clean_number(nums[2])

    return {
        'movimientos': movimientos,
        'totales': totales,
        'transformado': parse_davivienda_transformado({'movimientos': movimientos, 'totales': totales})
    }


def parse_davivienda_transformado(data: dict) -> dict:
    movimientos = data['movimientos']
    resultado = []
    for mov in movimientos:
        fecha = mov.get('Fecha', '')
        valor = float(mov.get('Valor Total', '0') or 0)
        tran = mov.get('Tran', '')
        if tran.lower() in ['deposito especial', 'notas credito']:
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