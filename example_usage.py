"""Basic usage example for PriceWatch."""
from datetime import datetime, timedelta
from pathlib import Path

from pricewatch import (
    WaybackClient,
    SnapshotSampler,
    PriceExtractor,
    PriceTimeSeries
)
from pricewatch.export.csv_export import CSVExporter, ExcelExporter


def main():
    """Run a complete price analysis example."""
    
    # Configuration
    url = "https://www.example.com/pricing"  # Replace with actual URL
    start_date = datetime.now() - timedelta(days=730)  # 2 years back
    end_date = datetime.now()
    
    print(f"PriceWatch Analysis")
    print(f"URL: {url}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print()
    
    # Initialize components
    print("Initializing...")
    client = WaybackClient(rate_limit=0.5)
    sampler = SnapshotSampler(client)
    extractor = PriceExtractor(use_llm=False)  # Set to True if Ollama is available
    
    # Step 1: Get snapshots
    print("Finding snapshots...")
    snapshots = sampler.get_quarterly_snapshots(
        url=url,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"Found {len(snapshots)} snapshots")
    
    if not snapshots:
        print("No snapshots found. Try a different URL or date range.")
        return
    
    # Step 2: Extract prices from each snapshot
    print("\nExtracting prices...")
    price_snapshots = []
    
    for i, snapshot in enumerate(snapshots, 1):
        print(f"  Processing {i}/{len(snapshots)}: {snapshot.timestamp.date()}", end="")
        
        try:
            # Fetch HTML
            html = client.fetch_html(snapshot)
            
            # Extract prices
            ps = extractor.extract_from_snapshot(snapshot, html)
            price_snapshots.append(ps)
            
            # Show result
            if ps.has_prices:
                prices_str = ", ".join(f"${p.value:.2f}" for p in ps.prices)
                print(f" → {prices_str}")
            else:
                print(" → No prices found")
                
        except Exception as e:
            print(f" → Error: {e}")
    
    # Step 3: Build time series
    successful = sum(1 for ps in price_snapshots if ps.has_prices)
    
    timeseries = PriceTimeSeries(
        url=url,
        snapshots=price_snapshots,
        start_date=start_date,
        end_date=end_date,
        total_snapshots=len(snapshots),
        successful_extractions=successful
    )
    
    # Step 4: Display results
    print(f"\n{'='*60}")
    print(f"Results")
    print(f"{'='*60}")
    print(f"Total snapshots: {timeseries.total_snapshots}")
    print(f"Successful extractions: {timeseries.successful_extractions}")
    print(f"Success rate: {timeseries.success_rate:.1%}")
    print()
    
    # Show price history
    print("Price History:")
    print(f"{'Date':<12} {'Price':<15} {'Currency':<10} {'Type':<10} {'Tier':<15}")
    print("-" * 62)
    
    for ps in price_snapshots:
        if not ps.has_prices:
            print(f"{ps.snapshot.timestamp.strftime('%Y-%m-%d'):<12} {'N/A':<15}")
            continue
        
        for price in ps.prices:
            print(
                f"{ps.snapshot.timestamp.strftime('%Y-%m-%d'):<12} "
                f"${price.value:<14.2f} "
                f"{price.currency.value:<10} "
                f"{price.price_type.value:<10} "
                f"{price.tier_name or '':<15}"
            )
    
    # Step 5: Export
    print(f"\n{'='*60}")
    print("Exporting...")
    
    # CSV export
    csv_path = Path("pricewatch_output.csv")
    CSVExporter.export_timeseries(timeseries, csv_path)
    print(f"✓ CSV exported to: {csv_path}")
    
    # Excel export (if openpyxl is installed)
    try:
        excel_path = Path("pricewatch_output.xlsx")
        ExcelExporter.export_timeseries(timeseries, excel_path, include_charts=True)
        print(f"✓ Excel exported to: {excel_path}")
    except ImportError:
        print("⚠ Excel export skipped (install openpyxl to enable)")
    
    # Step 6: Pandas DataFrame
    print("\nDataFrame preview:")
    df = timeseries.to_dataframe()
    print(df.head(10))
    
    print(f"\n{'='*60}")
    print("Analysis complete!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
