"""
pricewatch/__init__.py
"""
__version__ = "0.1.0"

from .core.wayback import WaybackClient
from .core.sampling import SnapshotSampler
from .core.extractor import PriceExtractor
from .core.models import (
    PriceTimeSeries,
    PriceSnapshot,
    Snapshot,
    ExtractedPrice,
    Currency,
    PriceType,
    ExtractionMethod
)

__all__ = [
    'WaybackClient',
    'SnapshotSampler',
    'PriceExtractor',
    'PriceTimeSeries',
    'PriceSnapshot',
    'Snapshot',
    'ExtractedPrice',
    'Currency',
    'PriceType',
    'ExtractionMethod',
]


"""
pricewatch/core/__init__.py
"""
from .wayback import WaybackClient
from .sampling import SnapshotSampler
from .extractor import PriceExtractor
from .models import (
    PriceTimeSeries,
    PriceSnapshot,
    Snapshot,
    ExtractedPrice
)

__all__ = [
    'WaybackClient',
    'SnapshotSampler',
    'PriceExtractor',
    'PriceTimeSeries',
    'PriceSnapshot',
    'Snapshot',
    'ExtractedPrice',
]


"""
pricewatch/extractors/__init__.py
"""
from .regex_extractor import RegexPriceExtractor
from .dom_extractor import DOMPriceExtractor
from .llm_extractor import LLMPriceExtractor

__all__ = [
    'RegexPriceExtractor',
    'DOMPriceExtractor',
    'LLMPriceExtractor',
]


"""
pricewatch/export/__init__.py
"""
from .csv_export import CSVExporter, ExcelExporter

__all__ = ['CSVExporter', 'ExcelExporter']


"""
pricewatch/cli/__init__.py
"""
from .commands import cli

__all__ = ['cli']
