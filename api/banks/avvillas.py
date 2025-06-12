from __future__ import annotations

import pandas as pd


def _parse_row(row: pd.Series) -> dict:
    """Return a dict with the required keys for the JSON output."""

    fecha_raw = str(row.get("Fecha", "")).strip()
    fecha_dt = pd.to_datetime(fecha_raw, errors="coerce")
    fecha = fecha_dt.strftime("%d/%m/%Y") if fecha_dt is not pd.NaT else ""

    debito = str(row.get("Débitos", "")).strip()
    credito = str(row.get("Créditos", "")).strip()
    referencia = str(row.get("Desc. Oficina", "")).strip()
    transaccion = str(row.get("Transacción", "")).strip()

    return {
        "Fecha": fecha,
        "importe_credito": credito,
        "importe_debito": debito,
        "referencia": referencia,
        "Info_detallada": transaccion,
    }


def process(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the DataFrame from Banco AV Villas to the required shape."""

    df.columns = df.columns.str.strip()
    required_columns = {"Fecha", "Transacción", "Desc. Oficina", "Débitos", "Créditos"}
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

    records = [_parse_row(row) for _, row in df.iterrows()]
    return pd.DataFrame(records)