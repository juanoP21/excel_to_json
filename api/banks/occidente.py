
from __future__ import annotations

import pandas as pd


def _parse_row(row: pd.Series) -> dict:
    """Return a dict with the required keys for the JSON output."""

    fecha = str(row.get("Fecha", "")).strip()
    debito = str(row.get("Débitos", "")).strip()
    credito = str(row.get("Créditos", "")).strip()

    raw_referencia = row.get("Nro. Documento", "")
    referencia = "" if pd.isna(raw_referencia) else str(raw_referencia).strip()
    if referencia.lower() == "nan":
        referencia = ""
    elif raw_referencia == 0:
        referencia = "AVENIDA 3A. NORTE"
    transaccion = str(row.get("Transacción", "")).strip()

    # If "Nro. Documento" is empty try to extract it from the end of
    # "Transacción".  Many rows include the document number as the last word
    # in the transaction description.
    if not referencia:
        parts = transaccion.rsplit(" ", 1)
        if len(parts) == 2 and any(ch.isdigit() for ch in parts[1]):
            referencia = parts[1]
            transaccion = parts[0]
        else:
            referencia = "AVENIDA 3A. NORTE"

    if referencia == transaccion:
        referencia = ""

    return {
        "Fecha": pd.to_datetime(fecha, dayfirst=True, errors="coerce").strftime("%m/%d/%Y"), "importe_credito": credito,
        "importe_debito": debito,
        "referencia": referencia,
        "Info_detallada": transaccion,
    }


def process(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the DataFrame from Banco de Occidente to the required shape."""

    # Normalise column names by stripping whitespace
    df.columns = df.columns.str.strip()

    required_columns = {"Fecha", "Débitos", "Créditos", "Nro. Documento", "Transacción"}
    if not required_columns.issubset(df.columns):
        missing = required_columns.difference(df.columns)
        raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

    records = [_parse_row(row) for _, row in df.iterrows()]
    return pd.DataFrame(records)
