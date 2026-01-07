"""Streamlit web application for PriceWatch."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pricewatch.core.wayback import WaybackClient
from pricewatch.core.sampling import SnapshotSampler
from pricewatch.core.extractor import PriceExtractor
from pricewatch.core.models import PriceTimeSeries
from pricewatch.export.csv_export import CSVExporter


# Page config
st.set_page_config(
    page_title="PriceWatch - Competitor Price Intelligence",
    page_icon="📊",
    layout="wide"
)


def main():
    st.title("📊 PriceWatch")
    st.subheader("Historical Competitor Price Intelligence")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    
    url = st.sidebar.text_input(
        "Product/Pricing Page URL",
        placeholder="https://competitor.com/pricing"
    )
    
    # Date range
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=730)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now()
        )
    
    # Sampling interval
    interval = st.sidebar.selectbox(
        "Sampling Interval",
        ["Quarterly", "Monthly", "Annual"]
    )
    
    # Advanced options
    with st.sidebar.expander("Advanced Options"):
        use_llm = st.checkbox(
            "Enable LLM Extraction",
            help="Use local LLM (Ollama) as fallback for difficult pages"
        )
        
        if use_llm:
            llm_model = st.text_input("Ollama Model", value="llama3.2")
        else:
            llm_model = "llama3.2"
        
        max_distance = st.slider(
            "Max Snapshot Distance (days)",
            min_value=7,
            max_value=90,
            value=45,
            help="Maximum days to search for nearest snapshot"
        )
    
    # Analyze button
    analyze_button = st.sidebar.button("🔍 Analyze", type="primary", use_container_width=True)
    
    # Main content
    if not url:
        st.info("👆 Enter a product/pricing page URL in the sidebar to get started")
        
        # Example/instructions
        st.markdown("---")
        st.markdown("### How it works")
        st.markdown("""
        1. **Enter URL**: Provide a competitor's pricing or product page
        2. **Configure**: Set date range and sampling interval
        3. **Analyze**: PriceWatch will:
           - Query the Wayback Machine for archived snapshots
           - Extract prices using multiple methods (regex, DOM parsing, optional LLM)
           - Build a complete price history timeline
        4. **Explore**: View interactive charts and export data
        """)
        
        st.markdown("### Example URLs")
        st.markdown("""
        - SaaS pricing pages (e.g., `https://example.com/pricing`)
        - Product pages with prices
        - Subscription plan pages
        """)
        
        return
    
    # Analysis
    if analyze_button:
        run_analysis(
            url=url,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            interval=interval.lower(),
            use_llm=use_llm,
            llm_model=llm_model,
            max_distance=max_distance
        )
    
    # Show cached results
    if 'timeseries' in st.session_state:
        display_results(st.session_state.timeseries)


def run_analysis(url, start_date, end_date, interval, use_llm, llm_model, max_distance):
    """Run the price analysis."""
    
    # Initialize
    client = WaybackClient()
    sampler = SnapshotSampler(client)
    extractor = PriceExtractor(use_llm=use_llm, llm_model=llm_model)
    
    # Progress
    progress_bar = st.progress(0, text="Finding snapshots...")
    
    try:
        # Get snapshots
        if interval == 'monthly':
            snapshots = sampler.get_monthly_snapshots(url, start_date, end_date, max_distance)
        elif interval == 'quarterly':
            snapshots = sampler.get_quarterly_snapshots(url, start_date, end_date, max_distance)
        else:  # annual
            snapshots = sampler.get_annual_snapshots(url, start_date, end_date, max_distance)
        
        if not snapshots:
            st.error("No snapshots found for this URL in the specified date range")
            return
        
        st.info(f"Found {len(snapshots)} snapshots")
        
        # Extract prices
        price_snapshots = []
        total = len(snapshots)
        
        for i, snapshot in enumerate(snapshots):
            progress = (i + 1) / total
            progress_bar.progress(
                progress,
                text=f"Extracting prices... ({i+1}/{total})"
            )
            
            try:
                html = client.fetch_html(snapshot)
                ps = extractor.extract_from_snapshot(snapshot, html)
                price_snapshots.append(ps)
            except Exception as e:
                st.warning(f"Failed to process {snapshot.timestamp.date()}: {e}")
        
        progress_bar.progress(1.0, text="Complete!")
        
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
        
        # Store in session
        st.session_state.timeseries = timeseries
        
        st.success(f"✓ Analysis complete! Success rate: {timeseries.success_rate:.1%}")
        
    except Exception as e:
        st.error(f"Analysis failed: {e}")
        import traceback
        st.code(traceback.format_exc())


def display_results(timeseries: PriceTimeSeries):
    """Display analysis results."""
    
    st.markdown("---")
    st.header("Results")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Snapshots", timeseries.total_snapshots)
    with col2:
        st.metric("Successful Extractions", timeseries.successful_extractions)
    with col3:
        st.metric("Success Rate", f"{timeseries.success_rate:.1%}")
    with col4:
        df = timeseries.to_dataframe()
        if not df.empty and 'price' in df.columns:
            avg_price = df['price'].mean()
            st.metric("Average Price", f"${avg_price:.2f}")
        else:
            st.metric("Average Price", "N/A")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📈 Chart", "📋 Data Table", "💾 Export"])
    
    with tab1:
        display_chart(timeseries)
    
    with tab2:
        display_data_table(timeseries)
    
    with tab3:
        display_export_options(timeseries)


def display_chart(timeseries: PriceTimeSeries):
    """Display interactive price chart."""
    
    df = timeseries.to_dataframe()
    
    if df.empty:
        st.warning("No price data to display")
        return
    
    # Group by tier if multiple tiers
    tiers = df['tier'].unique()
    
    fig = go.Figure()
    
    if len(tiers) > 1:
        # Multiple series for different tiers
        for tier in tiers:
            tier_data = df[df['tier'] == tier]
            
            tier_name = tier if pd.notna(tier) else "Unknown"
            
            fig.add_trace(go.Scatter(
                x=tier_data['date'],
                y=tier_data['price'],
                mode='lines+markers',
                name=tier_name,
                hovertemplate=(
                    f'<b>{tier_name}</b><br>' +
                    'Date: %{x|%Y-%m-%d}<br>' +
                    'Price: $%{y:.2f}<br>' +
                    '<extra></extra>'
                )
            ))
    else:
        # Single series
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['price'],
            mode='lines+markers',
            name='Price',
            line=dict(color='#4472C4', width=3),
            marker=dict(size=8),
            hovertemplate=(
                'Date: %{x|%Y-%m-%d}<br>' +
                'Price: $%{y:.2f}<br>' +
                '<extra></extra>'
            )
        ))
    
    fig.update_layout(
        title="Price History Over Time",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        hovermode='closest',
        height=500,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_data_table(timeseries: PriceTimeSeries):
    """Display data in table format."""
    
    df = timeseries.to_dataframe()
    
    if df.empty:
        st.warning("No data to display")
        return
    
    # Format for display
    display_df = df.copy()
    display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
    display_df['price'] = display_df['price'].apply(lambda x: f"${x:.2f}")
    display_df['confidence'] = display_df['confidence'].apply(lambda x: f"{x:.0%}")
    
    # Reorder columns
    columns = ['date', 'price', 'currency', 'type', 'tier', 'confidence', 'method', 'is_exact']
    display_df = display_df[columns]
    
    # Rename for clarity
    display_df.columns = [
        'Date', 'Price', 'Currency', 'Type', 'Tier',
        'Confidence', 'Method', 'Exact Match'
    ]
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # Copy to clipboard helper
    st.info("💡 You can copy this table directly to Excel by selecting cells and pressing Ctrl+C")


def display_export_options(timeseries: PriceTimeSeries):
    """Display export options."""
    
    st.subheader("Export Data")
    
    # CSV export
    df = timeseries.to_dataframe()
    
    if not df.empty:
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"pricewatch_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        st.markdown("---")
        
        st.subheader("Excel-Ready Format")
        st.markdown("Copy the table below and paste directly into Excel:")
        
        # Format for Excel
        excel_df = df.copy()
        excel_df['date'] = pd.to_datetime(excel_df['date']).dt.strftime('%Y-%m-%d')
        
        st.dataframe(excel_df, use_container_width=True)
    else:
        st.warning("No data to export")


if __name__ == '__main__':
    main()
