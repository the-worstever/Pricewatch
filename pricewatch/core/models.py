"""Data models for PriceWatch."""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class ExtractionMethod(str, Enum):
    """Method used to extract price."""
    REGEX = "regex"
    DOM = "dom"
    LLM = "llm"
    MANUAL = "manual"


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    UNKNOWN = "UNKNOWN"


class PriceType(str, Enum):
    """Type of pricing."""
    MONTHLY = "monthly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"
    UNKNOWN = "unknown"


class ExtractedPrice(BaseModel):
    """A single extracted price value."""
    value: float
    currency: Currency = Currency.USD
    price_type: PriceType = PriceType.UNKNOWN
    tier_name: Optional[str] = None
    raw_text: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    extraction_method: ExtractionMethod
    
    def normalized_annual_usd(self, exchange_rate: float = 1.0) -> float:
        """Convert to normalized annual USD price."""
        base = self.value * exchange_rate
        if self.price_type == PriceType.MONTHLY:
            return base * 12
        return base


class Snapshot(BaseModel):
    """A Wayback Machine snapshot."""
    url: str
    timestamp: datetime
    wayback_url: str
    status_code: int = 200
    is_exact_match: bool = True  # False if nearest snapshot was used
    distance_days: int = 0  # Days from requested date
    
    
class PriceSnapshot(BaseModel):
    """Prices extracted from a snapshot."""
    snapshot: Snapshot
    prices: List[ExtractedPrice]
    html_length: int
    extraction_time_ms: float
    errors: List[str] = Field(default_factory=list)
    
    @property
    def has_prices(self) -> bool:
        return len(self.prices) > 0
    
    @property
    def primary_price(self) -> Optional[ExtractedPrice]:
        """Return the most confident price."""
        if not self.prices:
            return None
        return max(self.prices, key=lambda p: p.confidence)


class PriceTimeSeries(BaseModel):
    """Complete time series of prices for a URL."""
    url: str
    snapshots: List[PriceSnapshot]
    start_date: datetime
    end_date: datetime
    total_snapshots: int
    successful_extractions: int
    
    @property
    def success_rate(self) -> float:
        if self.total_snapshots == 0:
            return 0.0
        return self.successful_extractions / self.total_snapshots
    
    def to_dataframe(self):
        """Convert to pandas DataFrame for analysis."""
        import pandas as pd
        
        rows = []
        for ps in self.snapshots:
            if ps.has_prices:
                for price in ps.prices:
                    rows.append({
                        'date': ps.snapshot.timestamp,
                        'price': price.value,
                        'currency': price.currency.value,
                        'type': price.price_type.value,
                        'tier': price.tier_name,
                        'confidence': price.confidence,
                        'method': price.extraction_method.value,
                        'is_exact': ps.snapshot.is_exact_match,
                        'wayback_url': ps.snapshot.wayback_url,
                    })
        
        return pd.DataFrame(rows)
