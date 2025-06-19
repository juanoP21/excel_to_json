from __future__ import annotations

import pandas as pd


def _parse_row(row: pd.Series) -> list[dict]:
    """Return one or two records based on GMF value."""
    fecha_raw = row.get("Fecha Transacción", "")
    fecha_raw = "" if pd.isna(fecha_raw) else str(fecha_raw).strip()
    try:
        fecha_raw = row.get("Fecha Transacción", "")
        fecha_raw = "" if pd.isna(fecha_raw) else str(fecha_raw).strip()
        fecha = pd.to_datetime(fecha_raw, dayfirst=True, errors="coerce")
        fecha = fecha.strftime("%d/%m/%Y") if fecha is not pd.NaT else ""
    except Exception:
        fecha = ""

    concepto_raw = row.get("Concepto", "")
    concepto = "" if pd.isna(concepto_raw) else str(concepto_raw).strip()

    benef_raw = row.get("Beneficiario", "")
    beneficiario = "" if pd.isna(benef_raw) else str(benef_raw).strip()

    def _clean(val: str) -> float:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return 0.0
        val = str(val)
        if val.lower() in {"nan", ""}:
            return 0.0
        val = val.replace("$", "").replace("\xa0", "").replace(" ", "")
        if "," in val:
            val = val.replace(".", "")
            val = val.replace(",", ".")
        else:
            val = val.replace(",", "")
        try:
            num = float(val)
            return 0.0 if pd.isna(num) else num
        except Exception:
            return 0.0

    valor = _clean(row.get("Valor", "0"))
    gmf = _clean(row.get("GMF", "0"))

    if valor >= 0:
        credito = f"{valor:.2f}" if valor else ""
        debito = ""
    else:
        credito = ""
        debito = f"{-valor:.2f}" if valor else ""

    records = [{
        "Fecha": fecha,
        "importe_credito": credito,
        "importe_debito": debito,
        "referencia": beneficiario,
        "Info_detallada": concepto,
    }]

    if gmf:
        records.append({
            "Fecha": fecha,
            "importe_credito": "",
            "importe_debito": f"{abs(gmf):.2f}",
            "referencia": beneficiario,
            "Info_detallada": "GMF",
        })

    return records


def process(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()
    required_columns = {"Fecha Transacción", "Concepto", "Valor"}
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

    records = []
    for _, row in df.iterrows():
        records.extend(_parse_row(row))

    return pd.DataFrame(records)