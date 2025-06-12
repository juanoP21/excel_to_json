from __future__ import annotations

import pandas as pd


def _get_description_column(df: pd.DataFrame) -> str:
    """Return the column name that holds the transaction description.

    Banco Popular spreadsheets have used different headings for the
    description column.  This helper tries a list of known names and
    returns the first one found.
    """

    candidates = [
        "transcripcion",
        "Transcripción",
        "Transaccion",
        "Transacción",
        "Descripcion",
        "Descripción",
    ]

    lowered = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lowered:
            return lowered[name.lower()]

    raise ValueError("No se encontró una columna de descripción válida")


def _parse_row(row: pd.Series, desc_col: str) -> dict:
    """Return a dict with the required keys for the JSON output."""

    fecha = str(row.get("Fecha", "")).strip()
    debito = str(row.get("Débitos", "")).strip()
    credito = str(row.get("Créditos", "")).strip()
    referencia = str(row.get("No. Documento", "")).strip()
    oficina = str(row.get("Desc. Oficina", "")).strip()

    descripcion = str(row.get(desc_col, "")).strip()
    descripcion = descripcion.replace("0", "").strip()

    fecha_dt = pd.to_datetime(fecha, dayfirst=True, errors="coerce")
    fecha_formatted = fecha_dt.strftime("%m/%d/%Y") if fecha_dt is not pd.NaT else ""
    return {
        "Fecha": fecha_formatted,
        "importe_credito": credito,
        "importe_debito": debito,
        "referencia": referencia,
        "Info_detallada": descripcion,
        "Info_detallada2": oficina,
    }


def process(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the DataFrame from Banco Popular to the required shape."""

    # Normalise column names by stripping whitespace
    df.columns = df.columns.str.strip()

    required_columns = {
        "Fecha",
        "No. Documento",
        "Débitos",
        "Créditos",
        "Desc. Oficina",
    }

    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

    desc_col = _get_description_column(df)

    records = [_parse_row(row, desc_col) for _, row in df.iterrows()]
    return pd.DataFrame(records)