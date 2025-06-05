from typing import Callable, Dict
import pandas as pd

from . import occidente, popular, agrario

HANDLERS: Dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    'occidente': occidente.process,
    'popular': popular.process,
    'agrario': agrario.process,
}


def get_processor(bank: str) -> Callable[[pd.DataFrame], pd.DataFrame] | None:
    """Return the processor function for a given bank key."""
    return HANDLERS.get(bank)