# PriceWatch Quickstart Guide

Get started with PriceWatch in 5 minutes.

## Installation

### Option 1: Using uv (Recommended)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/yourcompany/pricewatch.git
cd pricewatch
./setup.sh
```

### Option 2: Using pip

```bash
git clone https://github.com/yourcompany/pricewatch.git
cd pricewatch
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[streamlit,export]"
```

## 3 Ways to Use PriceWatch

### 1. Command Line (Fastest)

```bash
# Activate environment
source .venv/bin/activate

# Basic analysis
pricewatch analyze https://competitor.com/pricing

# With export
pricewatch analyze https://competitor.com/pricing --export-csv results.csv

# Custom date range
pricewatch analyze https://competitor.com/pricing \
  --start-date 2023-01-01 \
  --end-date 2024-12-31 \
  --interval monthly
```

**Output Example:**
```
PriceWatch Analysis
URL: https://competitor.com/pricing
Period: 2023-01-01 to 2024-12-31
Interval: quarterly

✓ Analysis complete
Success rate: 87.5% (7/8)

┏━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Date       ┃ Price    ┃ Currency ┃ Type     ┃ Tier         ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ 2023-01-01 │ $29.99   │ USD      │ monthly  │ Professional │
│ 2023-04-01 │ $29.99   │ USD      │ monthly  │ Professional │
│ 2023-07-01 │ $34.99   │ USD      │ monthly  │ Professional │
│ 2023-10-01 │ $34.99   │ USD      │ monthly  │ Professional │
└────────────┴──────────┴──────────┴──────────┴──────────────┘
```

### 2. Web Interface (Best for Exploration)

```bash
# Activate environment
source .venv/bin/activate

# Launch app
streamlit run streamlit_app/app.py
```

Then open http://localhost:8501

**Web Interface Features:**
1. Enter competitor URL
2. Select date range
3. Click "Analyze"
4. View interactive chart
5. Download CSV

### 3. Python Code (Best for Integration)

```python
from datetime import datetime, timedelta
from pricewatch import WaybackClient, SnapshotSampler, PriceExtractor

# Setup
client = WaybackClient()
sampler = SnapshotSampler(client)
extractor = PriceExtractor()

# Analyze
url = "https://competitor.com/pricing"
start = datetime.now() - timedelta(days=365)
snapshots = sampler.get_quarterly_snapshots(url, start)

results = []
for snapshot in snapshots:
    html = client.fetch_html(snapshot)
    prices = extractor.extract_from_snapshot(snapshot, html)
    results.append(prices)

# Export
from pricewatch.export.csv_export import CSVExporter
CSVExporter.export_timeseries(timeseries, "output.csv")
```

## Common Use Cases

### Track Single Competitor

```bash
pricewatch analyze https://competitor.com/pricing \
  --interval quarterly \
  --export-csv competitor_prices.csv
```

### Compare Multiple Tiers

The tool automatically detects and extracts all pricing tiers (Basic, Pro, Enterprise, etc.)

### Monthly Price Changes

```bash
pricewatch analyze https://competitor.com/pricing \
  --interval monthly \
  --start-date 2024-01-01
```

### Long-Term Historical Analysis

```bash
pricewatch analyze https://competitor.com/pricing \
  --start-date 2018-01-01 \
  --interval annual
```

## Tips for Best Results

### 1. Choose the Right URL
✅ Good: `https://competitor.com/pricing`
✅ Good: `https://competitor.com/plans`
❌ Bad: `https://competitor.com/` (homepage)
❌ Bad: Checkout or cart pages

### 2. Set Appropriate Date Ranges
- **Quarterly**: Best for most cases (2-5 years)
- **Monthly**: For detailed recent analysis (6-18 months)
- **Annual**: For long-term trends (5+ years)

### 3. Check Wayback Coverage First

```bash
pricewatch snapshots https://competitor.com/pricing
```

If there are gaps, adjust your date range accordingly.

### 4. Enable LLM for Difficult Pages

Some pricing pages have unusual layouts. If standard extraction fails:

```bash
# Make sure Ollama is running
ollama serve

# Pull a model (first time only)
ollama pull llama3.2

# Run with LLM
pricewatch analyze https://difficult-competitor.com/pricing --use-llm
```

## Troubleshooting

### No Snapshots Found
```
Problem: "No snapshots found for this URL"
Solution: 
  1. Check URL is correct
  2. Verify page exists in Wayback: https://web.archive.org
  3. Try broader date range
```

### Low Success Rate
```
Problem: "Success rate: 30% (3/10)"
Solutions:
  1. Enable LLM extraction: --use-llm
  2. Try different URL (e.g., /pricing vs /plans)
  3. Check if prices are in images (not extractable)
```

### LLM Extraction Fails
```
Problem: "LLM extraction failed"
Solutions:
  1. Check Ollama is running: ollama list
  2. Pull model: ollama pull llama3.2
  3. Check Ollama logs: journalctl -u ollama
```

### Rate Limiting
```
Problem: Requests timing out or failing
Solution: Increase rate limit:
```

```python
client = WaybackClient(rate_limit=1.0)  # 1 second between requests
```

## Export Formats

### CSV
Standard spreadsheet format, easy to open in Excel/Google Sheets:

```bash
pricewatch analyze URL --export-csv output.csv
```

### Excel
Formatted workbook with charts:

```bash
# Requires: pip install openpyxl
pricewatch analyze URL --export-excel output.xlsx
```

### Pandas DataFrame (Python)
```python
df = timeseries.to_dataframe()
print(df.head())

# Standard pandas operations
df.groupby('tier')['price'].mean()
df.plot(x='date', y='price')
```

## Advanced Features

### Custom Sampling

```python
from pricewatch.core.sampling import SnapshotSampler

sampler = SnapshotSampler(client)

# Custom: First day of each month
snapshots = sampler.get_monthly_snapshots(
    url, 
    start_date, 
    end_date,
    max_distance_days=15  # Tighter tolerance
)
```

### Filter by Tier

```python
df = timeseries.to_dataframe()
pro_prices = df[df['tier'] == 'Professional']
```

### Confidence Filtering

```python
df = timeseries.to_dataframe()
high_confidence = df[df['confidence'] > 0.8]
```

## Next Steps

### For Analysts
1. Export to CSV
2. Create comparison dashboard in Excel
3. Track month-over-month changes
4. Build competitor pricing database

### For Developers
1. Read `ARCHITECTURE.md` for system design
2. Integrate into existing tools
3. Build automated monitoring
4. Add custom extractors

### For Teams
1. Deploy Streamlit app on shared server
2. Create shared workspace for analysis
3. Schedule regular competitive analysis
4. Build alerting for price changes

## Getting Help

- **Issues**: https://github.com/yourcompany/pricewatch/issues
- **Documentation**: See README.md and ARCHITECTURE.md
- **Examples**: Check `examples/` directory
- **Slack**: #pricewatch-support

## Quick Reference

```bash
# Install
./setup.sh

# Analyze
pricewatch analyze URL

# Export
pricewatch analyze URL --export-csv output.csv

# Web UI
streamlit run streamlit_app/app.py

# Check snapshots
pricewatch snapshots URL

# Help
pricewatch --help
pricewatch analyze --help
```

---

**Ready to start?** Pick your favorite interface and analyze your first competitor! 🚀
