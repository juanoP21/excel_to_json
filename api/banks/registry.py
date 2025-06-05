from typing import Callable, Dict
import pandas as pd

from . import occidente, popular

HANDLERS: Dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    'occidente': occidente.process,
    'popular': popular.process,
}


def get_processor(bank: str) -> Callable[[pd.DataFrame], pd.DataFrame] | None:
    """Return the processor function for a given bank key."""
    return HANDLERS.get(bank)