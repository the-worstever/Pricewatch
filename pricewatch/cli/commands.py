"""CLI commands for PriceWatch."""
import click
from datetime import datetime, timedelta
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.wayback import WaybackClient
from ..core.sampling import SnapshotSampler
from ..extractors.main import PriceExtractor
from ..core.models import PriceTimeSeries
from ..export.modules import CSVExporter, ExcelExporter


console = Console()


@click.group()
def cli():
    """PriceWatch - Historical competitor price intelligence."""
    pass


@cli.command()
@click.argument('url')
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']),
              help='End date (YYYY-MM-DD)')
@click.option('--interval', type=click.Choice(['monthly', 'quarterly', 'annual']),
              default='quarterly', help='Sampling interval')
@click.option('--use-llm/--no-llm', default=False,
              help='Enable LLM fallback extraction')
@click.option('--llm-model', default='llama3.2',
              help='Ollama model for LLM extraction')
@click.option('--export-csv', type=click.Path(), help='Export to CSV file')
@click.option('--export-excel', type=click.Path(), help='Export to Excel file')
@click.option('--show-table/--no-table', default=True, help='Show results table')
def analyze(url, start_date, end_date, interval, use_llm, llm_model, 
            export_csv, export_excel, show_table):
    """Analyze historical pricing for a URL."""
    
    # Default dates
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=730)  # 2 years back
    
    console.print(f"\n[bold cyan]PriceWatch Analysis[/bold cyan]")
    console.print(f"URL: {url}")
    console.print(f"Period: {start_date.date()} to {end_date.date()}")
    console.print(f"Interval: {interval}")
    console.print(f"LLM Extraction: {'Enabled' if use_llm else 'Disabled'}\n")
    
    # Initialize components
    client = WaybackClient()
    sampler = SnapshotSampler(client)
    extractor = PriceExtractor(use_llm=use_llm, llm_model=llm_model)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Get snapshots
        task = progress.add_task("Finding snapshots...", total=None)
        
        if interval == 'monthly':
            snapshots = sampler.get_monthly_snapshots(url, start_date, end_date)
        elif interval == 'quarterly':
            snapshots = sampler.get_quarterly_snapshots(url, start_date, end_date)
        else:  # annual
            snapshots = sampler.get_annual_snapshots(url, start_date, end_date)
        
        progress.update(task, description=f"Found {len(snapshots)} snapshots")
        
        if not snapshots:
            console.print("[yellow]No snapshots found for this URL[/yellow]")
            return
        
        # Extract prices
        task = progress.add_task("Extracting prices...", total=len(snapshots))
        
        price_snapshots = []
        for snapshot in snapshots:
            try:
                html = client.fetch_html(snapshot)
                ps = extractor.extract_from_snapshot(snapshot, html)
                price_snapshots.append(ps)
            except Exception as e:
                console.print(f"[red]Error processing {snapshot.timestamp}: {e}[/red]")
            
            progress.advance(task)
    
    # Build time series
    successful = sum(1 for ps in price_snapshots if ps.has_prices)
    
    timeseries = PriceTimeSeries(
        url=url,
        snapshots=price_snapshots,
        start_date=start_date,
        end_date=end_date,
        total_snapshots=len(snapshots),
        successful_extractions=successful
    )
    
    console.print(f"\n[green]✓[/green] Analysis complete")
    console.print(f"Success rate: {timeseries.success_rate:.1%} ({successful}/{len(snapshots)})\n")
    
    # Show table
    if show_table:
        display_results_table(timeseries)
    
    # Export
    if export_csv:
        CSVExporter.export_timeseries(timeseries, Path(export_csv))
        console.print(f"[green]✓[/green] Exported to CSV: {export_csv}")
    
    if export_excel:
        ExcelExporter.export_timeseries(timeseries, Path(export_excel))
        console.print(f"[green]✓[/green] Exported to Excel: {export_excel}")


@cli.command()
@click.argument('url')
def snapshots(url):
    """List available snapshots for a URL."""
    
    console.print(f"\n[bold cyan]Available Snapshots[/bold cyan]")
    console.print(f"URL: {url}\n")
    
    client = WaybackClient()
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=console) as progress:
        task = progress.add_task("Querying Wayback Machine...", total=None)
        snapshots = client.get_snapshots(url, limit=100)
    
    if not snapshots:
        console.print("[yellow]No snapshots found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Wayback URL", style="dim")
    
    for snapshot in snapshots[:50]:  # Show first 50
        table.add_row(
            snapshot.timestamp.strftime('%Y-%m-%d %H:%M'),
            str(snapshot.status_code),
            snapshot.wayback_url
        )
    
    console.print(table)
    console.print(f"\nShowing 50 of {len(snapshots)} total snapshots")


def display_results_table(timeseries: PriceTimeSeries):
    """Display results in a formatted table."""
    
    table = Table(show_header=True, header_style="bold magenta", title="Price History")
    table.add_column("Date", style="cyan")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Currency", style="dim")
    table.add_column("Type", style="yellow")
    table.add_column("Tier", style="blue")
    table.add_column("Match", style="dim")
    table.add_column("Confidence", justify="right", style="dim")
    
    for ps in timeseries.snapshots:
        date_str = ps.snapshot.timestamp.strftime('%Y-%m-%d')
        match_str = "✓" if ps.snapshot.is_exact_match else f"~{ps.snapshot.distance_days}d"
        
        if not ps.has_prices:
            table.add_row(
                date_str,
                "[red]N/A[/red]",
                "",
                "",
                "",
                match_str,
                ""
            )
            continue
        
        for i, price in enumerate(ps.prices):
            display_date = date_str if i == 0 else ""
            display_match = match_str if i == 0 else ""
            
            table.add_row(
                display_date,
                f"${price.value:,.2f}" if price.currency.value == "USD" else f"{price.value:,.2f}",
                price.currency.value,
                price.price_type.value,
                price.tier_name or "",
                display_match,
                f"{price.confidence:.0%}"
            )
    
    console.print(table)


if __name__ == '__main__':
    cli()
