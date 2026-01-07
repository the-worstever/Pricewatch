# PriceWatch Architecture

## System Overview

PriceWatch is a multi-interface market intelligence tool designed for tracking competitor pricing over time using historical web archive data from the Internet Archive's Wayback Machine.

### Design Philosophy

1. **Modular**: Core functionality separated from interfaces
2. **Production-Ready**: Error handling, rate limiting, type safety
3. **Flexible**: Multiple extraction strategies with automatic fallback
4. **Montaigne-Style**: Single codebase, multiple interfaces

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Interface Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │   CLI    │  │ Streamlit│  │   Python Library     │ │
│  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘ │
└───────┼─────────────┼───────────────────┼──────────────┘
        │             │                   │
┌───────┴─────────────┴───────────────────┴──────────────┐
│                  Application Layer                      │
│  ┌────────────────────────────────────────────────┐    │
│  │  PriceExtractor (Orchestration)                │    │
│  │  - Pipeline coordination                       │    │
│  │  - Multi-strategy extraction                   │    │
│  │  - Result deduplication                        │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │  SnapshotSampler (Temporal Logic)              │    │
│  │  - Quarterly/monthly/annual sampling           │    │
│  │  - Nearest snapshot selection                  │    │
│  │  - Date range management                       │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────┐
│                   Extraction Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │  Regex   │  │   DOM    │  │    LLM (Ollama)      │ │
│  │ Patterns │  │ Heuristic│  │      Fallback        │ │
│  └──────────┘  └──────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────┐
│                   Data Access Layer                     │
│  ┌────────────────────────────────────────────────┐    │
│  │  WaybackClient                                 │    │
│  │  - CDX API queries                             │    │
│  │  - HTML retrieval                              │    │
│  │  - Rate limiting                               │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │  Export Module                                 │    │
│  │  - CSV generation                              │    │
│  │  - Excel formatting                            │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────┐
│                   Data Model Layer                      │
│  - PriceTimeSeries                                      │
│  - PriceSnapshot                                        │
│  - ExtractedPrice                                       │
│  - Snapshot                                             │
│  (All Pydantic models for validation)                   │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. WaybackClient (`core/wayback.py`)

**Purpose**: Interface to Internet Archive Wayback Machine

**Responsibilities**:
- Query CDX API for available snapshots
- Fetch archived HTML content
- Rate limit requests to be respectful
- Handle network errors gracefully

**Key Methods**:
```python
def get_snapshots(url, from_date, to_date, limit) -> List[Snapshot]
def get_closest_snapshot(url, target_date, max_distance_days) -> Snapshot
def fetch_html(snapshot) -> str
```

**Design Decisions**:
- Built-in 0.5s rate limiting (configurable)
- Uses `id_` modifier to get clean HTML without Wayback toolbar
- Session reuse for connection pooling
- Collapse parameter to reduce duplicate timestamps

### 2. SnapshotSampler (`core/sampling.py`)

**Purpose**: Intelligent temporal sampling of archived snapshots

**Responsibilities**:
- Generate target dates at regular intervals
- Find nearest available snapshot when exact date unavailable
- Handle gaps in archive coverage
- Support multiple sampling frequencies

**Key Methods**:
```python
def get_quarterly_snapshots(url, start_date, end_date) -> List[Snapshot]
def get_monthly_snapshots(url, start_date, end_date) -> List[Snapshot]
def get_annual_snapshots(url, start_date, end_date) -> List[Snapshot]
```

**Design Decisions**:
- Quarterly default balances coverage vs. API load
- Configurable max_distance_days (default 45 for quarterly)
- Marks snapshots as "exact" or "nearest" with distance metadata
- Uses dateutil.relativedelta for accurate month/quarter math

### 3. Price Extraction Pipeline

#### 3a. RegexPriceExtractor (`extractors/regex_extractor.py`)

**Strategy**: Fast pattern matching for common price formats

**Strengths**:
- Very fast (no parsing overhead)
- High precision for standard formats
- Good coverage of common patterns

**Limitations**:
- Can miss prices in complex layouts
- Struggles with unusual formatting
- May extract unrelated numbers

**Patterns Handled**:
- `$99.99`, `$9,999.99`
- `€49.99`, `£29.99`
- `99 USD`, `USD 99`
- Context-aware price type detection

#### 3b. DOMPriceExtractor (`extractors/dom_extractor.py`)

**Strategy**: HTML structure analysis with heuristics

**Strengths**:
- Better context awareness
- Can identify pricing containers
- Extracts tier names from headings
- Handles prominence signals (large fonts)

**Limitations**:
- Slower than regex
- Depends on reasonable HTML structure
- May miss deeply nested prices

**Heuristics**:
1. Find pricing containers (class/id patterns)
2. Look for prominent text (h1-h4, large fonts)
3. Extract context (tier names, billing period)
4. Confidence scoring based on method

#### 3c. LLMPriceExtractor (`extractors/llm_extractor.py`)

**Strategy**: Local LLM (Ollama) for ambiguous cases

**Strengths**:
- Can handle complex layouts
- Understands natural language context
- Good for unusual page structures

**Limitations**:
- Slower (~1-5 seconds per page)
- Requires local Ollama installation
- Less deterministic than rule-based methods
- Token limits require page truncation

**Implementation**:
- Automatic availability check
- Text preprocessing to reduce tokens
- JSON-structured prompts for reliability
- Temperature 0.1 for factual extraction

### 4. PriceExtractor (`core/extractor.py`)

**Purpose**: Orchestrate multi-stage extraction pipeline

**Pipeline Flow**:
```
1. Regex Extraction (always)
   ↓
2. DOM Extraction (if < 3 prices found)
   ↓
3. LLM Extraction (if < 2 prices found AND enabled)
   ↓
4. Deduplication & Confidence Ranking
   ↓
5. Return PriceSnapshot
```

**Design Decisions**:
- Prefer faster methods when sufficient results found
- Deduplicate by value, keep highest confidence
- Merge results from multiple extractors
- Track extraction method and confidence for each price

### 5. Data Models (`core/models.py`)

**Architecture**: Pydantic for validation and serialization

**Key Models**:

```python
ExtractedPrice:
  - value: float
  - currency: Currency enum
  - price_type: PriceType enum
  - tier_name: Optional[str]
  - confidence: float [0.0-1.0]
  - extraction_method: ExtractionMethod enum

PriceSnapshot:
  - snapshot: Snapshot
  - prices: List[ExtractedPrice]
  - extraction_time_ms: float
  - errors: List[str]

PriceTimeSeries:
  - url: str
  - snapshots: List[PriceSnapshot]
  - start_date: datetime
  - end_date: datetime
  - success_rate: float (computed)
  - to_dataframe(): pd.DataFrame
```

**Benefits**:
- Automatic validation
- Type safety
- Easy serialization (JSON, CSV)
- Self-documenting code

## Interface Implementations

### CLI (`cli/commands.py`)

**Technology**: Click + Rich

**Commands**:
- `pricewatch analyze URL [options]`
- `pricewatch snapshots URL`

**Features**:
- Progress indicators (Rich)
- Formatted tables
- Color-coded output
- Export options

### Streamlit App (`streamlit_app/app.py`)

**Technology**: Streamlit + Plotly

**Features**:
- URL configuration UI
- Date range picker
- Real-time progress
- Interactive charts (Plotly)
- Data table with copy/paste support
- CSV download

**Design**:
- Sidebar for configuration
- Main area for results
- Tabbed interface (Chart / Table / Export)
- Session state for caching results

### Python Library

**Entry Points**:
```python
from pricewatch import (
    WaybackClient,
    SnapshotSampler,
    PriceExtractor,
    PriceTimeSeries
)
```

**Usage Pattern**:
```python
client = WaybackClient()
sampler = SnapshotSampler(client)
extractor = PriceExtractor()

snapshots = sampler.get_quarterly_snapshots(url, start, end)
price_snapshots = [
    extractor.extract_from_snapshot(s, client.fetch_html(s))
    for s in snapshots
]
timeseries = PriceTimeSeries(...)
```

## Export Module

### CSV Export
- Standard CSV format
- Optional metadata columns
- Excel-compatible
- UTF-8 encoding

### Excel Export
- Formatted headers
- Auto-column sizing
- Optional embedded charts
- Multiple sheets (future)

## Error Handling Strategy

### Network Errors
```python
try:
    html = client.fetch_html(snapshot)
except requests.RequestException:
    # Log error, continue with next snapshot
    # Store error in PriceSnapshot.errors
```

### Extraction Errors
- Never fail entire analysis due to one extraction failure
- Collect errors in PriceSnapshot
- Continue with available data
- Report success rate

### User Input Validation
- Pydantic for data validation
- Click for CLI argument validation
- Streamlit for UI validation

## Performance Considerations

### Rate Limiting
- 0.5s default between Wayback requests
- Configurable via WaybackClient
- Respect Archive.org's infrastructure

### Extraction Speed
- Regex: ~5ms per page
- DOM: ~20ms per page
- LLM: ~2000ms per page

### Memory Usage
- Process snapshots sequentially (streaming)
- Don't hold all HTML in memory
- Pandas DataFrame only for final results

### Caching
- No built-in caching (could be added)
- Streamlit session state for UI
- Future: Redis/SQLite cache layer

## Extensibility Points

### Custom Extractors
```python
class CustomExtractor:
    def extract(self, html: str) -> List[ExtractedPrice]:
        # Your logic here
        pass
```

### Custom Sampling
```python
class CustomSampler:
    def get_snapshots(self, url, start, end) -> List[Snapshot]:
        # Your logic here
        pass
```

### Custom Export
```python
class CustomExporter:
    @staticmethod
    def export_timeseries(timeseries, path):
        # Your logic here
        pass
```

## Testing Strategy

### Unit Tests
- Each extractor independently
- Sampling logic
- Date calculations

### Integration Tests
- Full pipeline with realistic HTML
- Multiple price formats
- Edge cases (no prices, malformed HTML)

### E2E Tests (Manual)
- Real Wayback Machine queries
- Real competitor URLs
- Different date ranges

## Deployment Scenarios

### 1. Individual Analyst
- CLI tool on local machine
- Ad-hoc analysis
- Quick exports

### 2. Team Dashboard
- Streamlit app on internal server
- Shared analysis
- Scheduled updates (future)

### 3. Automated Monitoring
- Python library in scheduled jobs
- Database storage (future)
- Alert generation (future)

### 4. API Service
- FastAPI wrapper (future)
- RESTful endpoints
- Multi-user support

## Future Architecture Considerations

### Database Layer
```
PriceTimeSeries → PostgreSQL
- Persistent storage
- Historical queries
- Change detection
```

### Queue System
```
Celery + Redis
- Async analysis jobs
- Better scalability
- Progress tracking
```

### Caching Layer
```
Redis/SQLite
- Cache HTML snapshots
- Cache extracted prices
- Reduce Wayback load
```

### Authentication
```
FastAPI + OAuth
- Multi-user access
- Usage quotas
- Audit logging
```

## Security Considerations

### Current
- No authentication required (local use)
- No user data storage
- Read-only Wayback access

### Future (if deployed as service)
- Rate limiting per user
- Input validation (URL whitelisting)
- Audit logging
- Secure secrets management (API keys)

## Maintenance

### Dependency Updates
- Regular security patches
- Wayback API compatibility
- Python version support

### Monitoring
- Success rates
- Extraction performance
- Error patterns
- API availability

### Documentation
- Keep README updated
- Architecture doc (this file)
- API documentation (future)
- User guides

## Assumptions Recap

1. **Wayback Coverage**: URLs are archived
2. **Price Display**: Prices are in HTML text (not images)
3. **Layout Stability**: Pricing page structure somewhat consistent
4. **Rate Limits**: 0.5s between requests is acceptable
5. **Currency**: USD default when ambiguous
6. **Sampling**: Quarterly is sufficient granularity

## Known Limitations

1. **JavaScript**: Cannot extract dynamically loaded prices
2. **Authentication**: Cannot access paywalled content
3. **Internationalization**: Limited currency support
4. **Real-time**: Historical data only, not current
5. **Scale**: Single-threaded processing (for now)

## Success Metrics

- **Extraction Success Rate**: Target >80%
- **Performance**: <1 minute for 2 years quarterly analysis
- **Accuracy**: High confidence prices should be correct
- **Usability**: Non-technical users can run CLI
- **Reliability**: Graceful failure handling

---

Last Updated: 2024
Version: 0.1.0
