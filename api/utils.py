import pandas as pd
from io import BytesIO, BufferedIOBase


def read_table(file: BufferedIOBase | BytesIO, ext: str, sheet: str | None = None,
               header: int = 0, skip: int | None = None) -> pd.DataFrame:
    """Read an Excel/CSV file into a DataFrame."""
    if ext == '.csv':
        return pd.read_csv(file, header=header, skiprows=skip)

    engine = 'openpyxl'
    if ext == '.xls':
        engine = 'xlrd'

    return pd.read_excel(
        file,
        sheet_name=(int(sheet) if sheet and str(sheet).isdigit() else sheet),
        header=header,
        skiprows=skip,
        engine=engine,
    )

