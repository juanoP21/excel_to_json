from __future__ import annotations

import pandas as pd

# Revisar el parseo porque es diferente
def _parse_row(row: pd.Series) -> dict:
    """Return a dict with the required keys for the JSON output."""
    fecha = str(row.get("Fecha", "")).strip()
    debito = str(row.get("Débito", "")).strip()
    credito = str(row.get("Crédito", "")).strip()

    referencia = str(
        row.get("Referencia", row.get("Nro. Documento", row.get("Documento", "")))
    ).strip()
    transaccion = str(row.get("Transacción", "")).strip()
    oficina = str(row.get("Oficina", "")).strip()

    return {
        "Fecha": pd.to_datetime(fecha, dayfirst=True, errors="coerce").strftime("%d/%m/%Y"),
        "importe_credito": credito,
        "importe_debito": debito,
        "referencia": referencia,
        "Info_detallada": transaccion,
        "Info_detallada2": oficina,
    }


def process(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the DataFrame from Banco Agrario to the required shape."""

    df.columns = df.columns.str.strip()
    required_columns = {"Fecha", "Crédito", "Débito", "Transacción", "Oficina"}
    if not required_columns.issubset(df.columns):
        missing = required_columns.difference(df.columns)
        raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

    records = [_parse_row(row) for _, row in df.iterrows()]
    return pd.DataFrame(records)