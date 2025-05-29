# pdfconvert/utils/parse_bancolombia.py

import re
from datetime import datetime

def parse_bancolombia(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # 1) Encabezados (igual que antes)
    header_map = {
        'Empresa': 'empresa',
        'Número de Cuenta': 'numero_cuenta',
        'Fecha y Hora Actual': 'fecha_hora_actual',
        'NIT': 'nit',
        'Tipo de cuenta': 'tipo_cuenta',
        'Fecha y Hora Consulta': 'fecha_hora_consulta',
        'Impreso por': 'impreso_por',
        'Saldo Efectivo Actual': 'saldo_efectivo_actual',
        'Saldo en Canje Actual': 'saldo_canje_actual',
        'Saldo Total Actual': 'saldo_total_actual',
    }
    data = {}
    for idx, line in enumerate(lines):
        for label, key in header_map.items():
            if line.startswith(f"{label}:"):
                raw = line.split(":",1)[1].strip() \
                      or (lines[idx+1].strip() if idx+1 < len(lines) else "")
                if key.startswith('saldo_'):
                    raw = raw.replace('$','').replace(',','')
                data[key] = raw
    for key in header_map.values():
        data.setdefault(key, "")

    # 2) Localizo inicio de movimientos
    start = next((i+1 for i,l in enumerate(lines) if l.upper().startswith("FECHA")), len(lines))

    # 3) Regex
    date_re    = re.compile(r'^\d{4}/\d{2}/\d{2}$')
    fullnum_re = re.compile(r'^-?[\d,]+\.\d+$')
    tail_re    = re.compile(r'^(.+?)\s+(-?[\d,]+\.\d+)$')
    ops_re     = re.compile(
        r'(TRANSFERENCIA|REDESCONSIGNACION|CONSIGNACION|IMPTO|VALOR|COMIS|INTERESES|ABONO|DEPÓSITO|DEPOSITO|RETIRO|PAGO)',
        re.IGNORECASE
    )

    movimientos = []
    i = start
    while i < len(lines):
        if date_re.match(lines[i]):
            raw_fecha = lines[i]
            block = []
            i += 1
            while i < len(lines) and not date_re.match(lines[i]):
                block.append(lines[i]); i += 1
            if not block:
                continue

            # 4) Extraigo raw_val y limpio esa línea
            raw_val = ""
            j = None
            for k in range(len(block)-1, -1, -1):
                line_k = block[k]
                if fullnum_re.match(line_k):
                    raw_val, j = line_k.replace(',',''), k
                    break
                m = tail_re.match(line_k)
                if m:
                    raw_val, j = m.group(2).replace(',',''), k
                    block[k] = m.group(1).strip()
                    break
            if j is None:
                j = len(block)

            # 5) Determino descripción vs referencias
            if len(block) > 1:
                # multilínea
                raw_desc_line = block[0]
                ref_lines     = block[1:j]
                referencia1   = " ".join(ref_lines).strip()
            else:
                # unilínea
                raw_desc_line = block[0]
                nums = re.findall(r'\b\d+\b', raw_desc_line)
                referencia1 = nums[0] if nums else ""

            referencia2 = ""

            # 6) Quito todos los dígitos de la línea para hacer split branch/op
            resto = re.sub(r'\b\d+\b','', raw_desc_line).strip()

            m_op = ops_re.search(resto)
            if m_op:
                prefix = resto[:m_op.start()].strip()
                suffix = resto[m_op.start():].strip()
                # Si 'IVA' se ha pegado al nombre de la sucursal,
                # lo sacamos al principio de la descripción
                if prefix.upper().endswith('IVA'):
                        sucursal_canal = prefix[:-3].strip()        # quita 'IVA'
                        descripcion    = 'IVA ' + suffix           # lo antepone a la desc.
                else:
                        sucursal_canal = prefix
                        descripcion    = suffix
            else:
                sucursal_canal = ""
                descripcion    = resto

            # 7) Fecha a ISO
            try:
                fecha_iso = datetime.strptime(raw_fecha, '%Y/%m/%d').date().isoformat()
            except ValueError:
                fecha_iso = raw_fecha

            movimientos.append({
                'fecha':          fecha_iso,
                'descripcion':    descripcion,
                'sucursal_canal': sucursal_canal,
                'referencia1':    referencia1,
                'referencia2':    referencia2,
                'documento':      '',
                'valor':          raw_val,
            })
        else:
            i += 1

    data['movimientos'] = movimientos
    return data
