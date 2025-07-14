from typing import Callable, Dict
import pandas as pd

from . import occidente, popular, agrario, alianza, bbva, avvillas, itau

HANDLERS: Dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    'occidente': occidente.process,
    'popular': popular.process,
    'agrario': agrario.process,
    'alianza': alianza.process,
    'bbva': bbva.process,
    'avvillas': avvillas.process,
    'itau': itau.process,
}

# Banks supported via the Excel parser
EXCEL_ENABLED_BANKS = {
    'occidente',
    'agrario',
    'alianza',
    'bbva',
    'avvillas',
    'itau',
}


def get_processor(bank: str) -> Callable[[pd.DataFrame], pd.DataFrame] | None:
    """Return the processor function for a given bank key."""
    return HANDLERS.get(bank)   
