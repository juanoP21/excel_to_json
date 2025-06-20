import re
from datetime import datetime

def parse_bancolombia(text: str) -> dict:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

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
    i = 0
    while i < len(lines):
        line = lines[i]
        found = False
        for label, key in header_map.items():
            if line.startswith(f"{label}:"):
                after_colon = line.split(":", 1)[1].strip()
                if after_colon:
                    raw = after_colon
                else:
                    raw = lines[i+1].strip() if i+1 < len(lines) else ""
                    i += 1  # saltar línea ya procesada
                if key.startswith('saldo_'):
                    raw = raw.replace('$', '').replace(',', '')
                data[key] = raw
                found = True
                break
        i += 1 if not found else 1

    for key in header_map.values():
        data.setdefault(key, "")

    start = next((i+1 for i, l in enumerate(lines) if l.upper().startswith("FECHA")), len(lines))

    date_re = re.compile(r'^\d{4}/\d{2}/\d{2}$')
    fullnum_re = re.compile(r'^-?[\d,]+\.\d+$')
    tail_re = re.compile(r'^(.+?)\s+(-?[\d,]+\.\d+)$')
    ops_re = re.compile(r'(TRANSFERENCIA|REDESCONSIGNACION|CONSIGNACION|IMPTO|VALOR|COMIS|INTERESES|ABONO|DEPÓSITO|DEPOSITO|RETIRO|PAGO|CONSIG|RECAUDO|TRASL)', re.IGNORECASE)
    ref_pattern = re.compile(r'^\*?\d{3,18}$')

    movimientos = []
    i = start
    while i < len(lines):
        if date_re.match(lines[i]):
            raw_fecha = lines[i]
            block = []
            i += 1
            while i < len(lines) and not date_re.match(lines[i]):
                block.append(lines[i])
                i += 1
            if not block:
                continue
            raw_val, j = "", None
            for k in range(len(block)-1, -1, -1):
                if fullnum_re.match(block[k]):
                    raw_val, j = block[k].replace(',', ''), k
                    break
                m = tail_re.match(block[k])
                if m:
                    raw_val, j = m.group(2).replace(',', ''), k
                    block[k] = m.group(1).strip()
                    break
            if j is None:
                j = len(block)

            raw_desc = block[0]
            ref_lines = block[1:j]

            if 'NEQUI' in raw_desc.upper() and ref_lines:
                idx_n = raw_desc.upper().find('NEQUI')
                nombre = raw_desc[idx_n + len('NEQUI'):].strip()
                partes = [p.strip() for p in ([nombre] if nombre else []) + ref_lines]
                referencia1 = ' '.join(partes)
                referencia2 = ""
            else:
                refs = []
                for lr in ref_lines:
                    for tok in re.findall(r'\*?\d+', lr):
                        if ref_pattern.match(tok):
                            refs.append(tok)
                        if len(refs) == 2:
                            break
                    if len(refs) == 2:
                        break
                if len(refs) < 2:
                    for tok in re.findall(r'\*?\d+', raw_desc):
                        if ref_pattern.match(tok) and tok not in refs:
                            refs.append(tok)
                        if len(refs) == 2:
                            break
                referencia1 = refs[0] if refs else ""
                referencia2 = refs[1] if len(refs) > 1 else ""

            up = raw_desc.upper()
            if up.startswith('CNB'):
                sucursal_canal = 'CNB REDES'
                desc = raw_desc[len('CNB'):].strip()
                desc = re.sub(r'(?i)^REDESCONSIG', 'CONSIG', desc)
                descripcion = re.sub(r'\*?\d+', '', desc).strip()
            else:
                rest = re.sub(r'\*?\d+', '', raw_desc).strip()
                m = ops_re.search(rest)
                if m:
                    pref, suf = rest[:m.start()].strip(), rest[m.start():].strip()
                    if pref.upper().endswith('IVA'):
                        sucursal_canal = pref[:-3].strip()
                        descripcion = 'IVA ' + suf
                    else:
                        sucursal_canal = pref
                        descripcion = suf
                else:
                    sucursal_canal, descripcion = '', rest

            try:
                fecha_iso = datetime.strptime(raw_fecha, '%Y/%m/%d').date().isoformat()
            except:
                fecha_iso = raw_fecha

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

    data["movimientos"] = movimientos
    data["transformado"] = parse_bancolombia_transformado(movimientos)
    return data
def parse_bancolombia_transformado(data: dict) -> dict:
    print(f"Procesando {len(data)} movimientos...")
    movimientos = sorted(
        data,
        key=lambda m: (
            datetime.fromisoformat(m.get('fecha'))
            if isinstance(m.get('fecha'), str) else datetime.max
        ),
    )
    resultado = []

    for mov in movimientos:
        try:
            fecha_dt = datetime.fromisoformat(mov['fecha'])
            fecha_str = fecha_dt.strftime('%d/%m/%Y')
        except Exception:
            fecha_str = mov.get('fecha', '')

        desc_up = mov.get('descripcion', '').strip().upper()
        if desc_up == "IMPTO GOBIERNO X":
            descripcion = "IMPTO GOBIERNO 4X100"
            referencia = ""
        else:
            descripcion = mov.get('descripcion', '')
            r1 = mov.get('referencia1', '').strip()
            r2 = mov.get('referencia2', '').strip()
            refs = []
            if r1: refs.append(r1)
            if r2 and r2 != r1: refs.append(r2)
            if len(refs) == 2:
                referencia = f"{refs[0]}-{refs[1]}"
            elif refs:
                referencia = refs[0]
            else:
                referencia = ""

        try:
            val = float(mov.get('valor', 0))
        except Exception:
            val = 0.0

        if val >= 0:
            importe_credito = f"{val:.2f}"
            importe_debito = ""
        else:
            importe_credito = ""
            importe_debito = f"{-val:.2f}"

        resultado.append({
            "Fecha": fecha_str,
            "importe_credito": importe_credito,
            "importe_debito": importe_debito,
            "referencia": referencia,
            "Info_detallada": descripcion,
            "Info_detallada2": mov.get('sucursal_canal', ''),
        })

    return { "result": resultado }