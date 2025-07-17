
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

    # Parse date - handle YYYY/MM/DD format and convert to DD/MM/YYYY
    fecha_formatted = ""
    if fecha:
        try:
            # If date is in YYYY/MM/DD format
            if "/" in fecha:
                parts = fecha.split("/")
                if len(parts) == 3:
                    # Check if first part is year (4 digits)
                    if len(parts[0]) == 4 and parts[0].isdigit():
                        # YYYY/MM/DD format
                        year, month, day = parts
                        fecha_formatted = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
                    else:
                        # Assume DD/MM/YYYY format already
                        fecha_formatted = fecha
                else:
                    fecha_formatted = fecha
            else:
                # Try parsing with pandas as fallback
                fecha_dt = pd.to_datetime(fecha, errors="coerce")
                if fecha_dt is not pd.NaT:
                    fecha_formatted = fecha_dt.strftime("%d/%m/%Y")
                else:
                    fecha_formatted = fecha
        except Exception:
            fecha_formatted = fecha  # Keep original if parsing fails

    return {
        "Fecha": fecha_formatted,
        "importe_credito": credito,
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
    result = pd.DataFrame(records)

    # Sort transactions by date from earliest to latest
    fechas = pd.to_datetime(result["Fecha"], format="%d/%m/%Y", errors="coerce")
    result.insert(0, "_sort_date", fechas)
    result.sort_values("_sort_date", inplace=True)
    result.drop(columns=["_sort_date"], inplace=True)
    result.reset_index(drop=True, inplace=True)

    return result
