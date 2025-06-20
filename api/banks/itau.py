from __future__ import annotations

import pandas as pd


def _parse_row(row: pd.Series) -> dict:
    """Return a dict with the required keys for the JSON output."""
    fecha = str(row.get("fecha", "")).strip()
    debito = str(row.get("debito", "")).strip()
    credito = str(row.get("credito", "")).strip()
    referencia = str(row.get("referencia", "")).strip()
    descripcion = str(row.get("descripcion", "")).strip()
    ciudad = str(row.get("ciudad", "")).strip()

    fecha_dt = pd.to_datetime(fecha, dayfirst=True, errors="coerce")
    fecha_formatted = (
        fecha_dt.strftime("%d/%m/%Y") if fecha_dt is not pd.NaT else ""
    )

    return {
        "Fecha": fecha_formatted,
        "importe_credito": credito,
        "importe_debito": debito,
        "referencia": referencia,
        "Info_detallada": descripcion,
        "Info_detallada2": ciudad,
    }


def _find_column(lowered: dict[str, str], names: list[str]) -> str | None:
    """Return the first matching column from ``lowered``.

    ``lowered`` maps lower-case names to the original column names in the
    DataFrame.  ``names`` contains candidate column headings to try.
    """

    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def process(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the DataFrame from Banco Itaú to the required shape."""
    df.columns = df.columns.str.strip()

    lowered = {c.lower(): c for c in df.columns}

    fecha_col = _find_column(lowered, ["fecha"])
    debito_col = _find_column(lowered, ["debito", "debitos", "débito", "débitos"])
    credito_col = _find_column(lowered, ["credito", "creditos", "crédito", "créditos"])
    desc_col = _find_column(lowered, ["descripcion", "descripción"])
    ciudad_col = _find_column(lowered, ["ciudad"])
    ref_col = _find_column(lowered, ["no. documento", "codigo movimiento", "código movimiento"])

    missing = [
        name
        for name, col in [
            ("Fecha", fecha_col),
            ("Débitos", debito_col),
            ("Créditos", credito_col),
            ("Descripción", desc_col),
            ("Ciudad", ciudad_col),
        ]
        if col is None
    ]
    if missing:
        raise ValueError(f"Columnas faltantes: {', '.join(sorted(missing))}")

    records = []
    for _, row in df.iterrows():
        mapped = {
            "fecha": row[fecha_col],
            "debito": row[debito_col],
            "credito": row[credito_col],
            "descripcion": row[desc_col],
            "ciudad": row[ciudad_col],
            "referencia": row[ref_col] if ref_col else "",
        }
        records.append(_parse_row(pd.Series(mapped)))

    return pd.DataFrame(records)