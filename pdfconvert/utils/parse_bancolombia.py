# pdfconvert/utils/parse_bancolombia.py

import re
from datetime import datetime

def parse_bancolombia(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # 1) Encabezados
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
                raw = line.split(":", 1)[1].strip() or (lines[idx+1].strip() if idx+1 < len(lines) else "")
                if key.startswith('saldo_'):
                    raw = raw.replace('$','').replace(',','')
                data[key] = raw
    for key in header_map.values():
        data.setdefault(key, "")

    # 2) Inicio de movimientos
    start = next((i+1 for i,l in enumerate(lines) if l.upper().startswith("FECHA")), len(lines))

    # 3) Patrones
    date_re    = re.compile(r'^\d{4}/\d{2}/\d{2}$')
    fullnum_re = re.compile(r'^-?[\d,]+\.\d+$')
    tail_re    = re.compile(r'^(.+?)\s+(-?[\d,]+\.\d+)$')
    ops_re     = re.compile(
        r'(TRANSFERENCIA|REDESCONSIGNACION|CONSIGNACION|IMPTO|VALOR|COMIS|INTERESES|ABONO|DEPÓSITO|DEPOSITO|RETIRO|PAGO|CONSIG|RECAUDO)',
        re.IGNORECASE
    )
    ref_pattern = re.compile(r'^\*?\d{3,18}$')

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

            # 4) Extraer valor
            raw_val, j = "", None
            for k in range(len(block)-1, -1, -1):
                if fullnum_re.match(block[k]):
                    raw_val, j = block[k].replace(',',''), k; break
                m = tail_re.match(block[k])
                if m:
                    raw_val, j = m.group(2).replace(',',''), k
                    block[k] = m.group(1).strip(); break
            if j is None: j = len(block)

            # 5) Descripción y referencias
            raw_desc = block[0]
            ref_lines = block[1:j]

            # NEQUI
            if 'NEQUI' in raw_desc.upper() and ref_lines:
                idx_n = raw_desc.upper().find('NEQUI')
                nombre = raw_desc[idx_n+len('NEQUI'):].strip()
                partes = [nombre] + ref_lines
                referencia1 = '\n'.join(partes)
                referencia2 = ""
            else:
                refs = []
                for lr in ref_lines:
                    for tok in re.findall(r'\*?\d+', lr):
                        if ref_pattern.match(tok): refs.append(tok)
                        if len(refs)==2: break
                    if len(refs)==2: break
                if len(refs)<2:
                    for tok in re.findall(r'\*?\d+', raw_desc):
                        if ref_pattern.match(tok) and tok not in refs: refs.append(tok)
                        if len(refs)==2: break
                referencia1 = refs[0] if refs else ""
                referencia2 = refs[1] if len(refs)>1 else ""

            # 6) Sucursal y descripción final
            up = raw_desc.upper()
            if up.startswith('CNB'):
                sucursal_canal = 'CNB REDES'
                # recortar CNB y normalizar termino CONSIG
                desc = raw_desc[len('CNB'):].strip()
                # reemplazar REDESCONSIG por CONSIG
                desc = re.sub(r'(?i)^REDESCONSIG', 'CONSIG', desc)
                # eliminar números
                descripcion = re.sub(r'\*?\d+', '', desc).strip()
            else:
                rest = re.sub(r'\*?\d+', '', raw_desc).strip()
                m = ops_re.search(rest)
                if m:
                    pref, suf = rest[:m.start()].strip(), rest[m.start():].strip()
                    if pref.upper().endswith('IVA'):
                        sucursal_canal = pref[:-3].strip(); descripcion = 'IVA '+suf
                    else:
                        sucursal_canal = pref; descripcion = suf
                else:
                    sucursal_canal, descripcion = '', rest

            # 7) Fecha ISO
            try: fecha_iso = datetime.strptime(raw_fecha, '%Y/%m/%d').date().isoformat()
            except: fecha_iso = raw_fecha

            movimientos.append({
                'fecha': fecha_iso,
                'descripcion': descripcion,
                'sucursal_canal': sucursal_canal,
                'referencia1': referencia1,
                'referencia2': referencia2,
                'documento': '',
                'valor': raw_val,
            })
        else:
            i += 1

    data['movimientos'] = movimientos
    return data