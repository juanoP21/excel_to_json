from __future__ import annotations

import pandas as pd


def _clean_amount(val: object) -> float:
    """Return ``val`` converted to ``float`` removing thousand separators."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    val = str(val).strip().replace("$", "").replace("\xa0", "").replace(" ", "")
    if "," in val and "." in val:
        val = val.replace(".", "").replace(",", ".")
    else:
        val = val.replace(",", "")
    try:
        return float(val)
    except Exception:
        return 0.0


def _parse_row(row: pd.Series, fecha_col: str) -> dict:
    """Return a dict with the required keys for the JSON output."""

    fecha_raw = row.get(fecha_col, "")
    fecha_raw = "" if pd.isna(fecha_raw) else str(fecha_raw).strip()
    fecha_dt = pd.to_datetime(fecha_raw, dayfirst=True, errors="coerce")
    fecha_formatted = fecha_dt.strftime("%d/%m/%Y") if fecha_dt is not pd.NaT else ""

    importe = _clean_amount(row.get("IMPORTE (COP)", 0))

    concepto_raw = row.get("CONCEPTO", "")
    concepto = "" if pd.isna(concepto_raw) else str(concepto_raw).strip()

    obs_raw = row.get("OBSERVACIONES", "")
    observaciones = "" if pd.isna(obs_raw) else str(obs_raw).strip()

    lower_concepto = concepto.lower()
    amount_str = f"{abs(importe):.2f}" if importe else "0"

    if "retiro" in lower_concepto or "rete fuente" in lower_concepto or importe < 0:
        credito = "0"
        debito = amount_str
    elif "deposito" in lower_concepto or importe > 0:
        credito = amount_str
        debito = "0"
    else:
        credito = "0"
        debito = "0"

    return {
        "Fecha": fecha_formatted,
        "importe_credito": credito,
        "importe_debito": debito,
        "referencia": observaciones,
        "Info_detallada": concepto,
    }


def process(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the DataFrame from Banco BBVA to the required shape."""

    df.columns = df.columns.str.strip()

    date_col = None
    for col in ("FECHA DE OPERACIÓN", "FECHA VALOR", "FECHA"):
        if col in df.columns:
            date_col = col
            break

    required = {"IMPORTE (COP)", "CONCEPTO", "OBSERVACIONES"}
    if not date_col or not required.issubset(df.columns):
        missing = set(required)
        if not date_col:
            missing.add("FECHA")
        else:
            missing -= df.columns
        raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

    records = [_parse_row(row, date_col) for _, row in df.iterrows()]
    return pd.DataFrame(records)