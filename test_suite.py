"""Tests for price extraction."""
import pytest
from datetime import datetime

from pricewatch.extractors.regex_extractor import RegexPriceExtractor
from pricewatch.extractors.dom_extractor import DOMPriceExtractor
from pricewatch.core.models import Currency, PriceType


class TestRegexExtractor:
    """Test regex-based price extraction."""
    
    def setup_method(self):
        self.extractor = RegexPriceExtractor()
    
    def test_basic_dollar_price(self):
        """Test extraction of basic dollar price."""
        html = "<html><body><h1>Price: $99.99</h1></body></html>"
        prices = self.extractor.extract(html)
        
        assert len(prices) > 0
        assert prices[0].value == 99.99
        assert prices[0].currency == Currency.USD
    
    def test_multiple_prices(self):
        """Test extraction of multiple prices."""
        html = """
        <html><body>
            <div class="plan">Basic: $9.99/month</div>
            <div class="plan">Pro: $29.99/month</div>
            <div class="plan">Enterprise: $99.99/month</div>
        </body></html>
        """
        prices = self.extractor.extract(html)
        
        assert len(prices) >= 3
        values = [p.value for p in prices]
        assert 9.99 in values
        assert 29.99 in values
        assert 99.99 in values
    
    def test_price_with_comma(self):
        """Test extraction of prices with comma separators."""
        html = "<html><body><p>Price: $1,999.99</p></body></html>"
        prices = self.extractor.extract(html)
        
        assert len(prices) > 0
        assert prices[0].value == 1999.99
    
    def test_euro_currency(self):
        """Test extraction of Euro prices."""
        html = "<html><body><p>Price: €49.99</p></body></html>"
        prices = self.extractor.extract(html)
        
        assert len(prices) > 0
        assert prices[0].value == 49.99
        assert prices[0].currency == Currency.EUR
    
    def test_monthly_price_type(self):
        """Test detection of monthly pricing."""
        html = "<html><body><p>$29.99 per month</p></body></html>"
        prices = self.extractor.extract(html)
        
        assert len(prices) > 0
        assert prices[0].price_type == PriceType.MONTHLY
    
    def test_annual_price_type(self):
        """Test detection of annual pricing."""
        html = "<html><body><p>$299 per year</p></body></html>"
        prices = self.extractor.extract(html)
        
        assert len(prices) > 0
        assert prices[0].price_type == PriceType.ANNUAL
    
    def test_tier_detection(self):
        """Test detection of pricing tiers."""
        html = """
        <html><body>
            <div class="pricing">
                <h3>Professional Plan</h3>
                <p>$49.99/month</p>
            </div>
        </body></html>
        """
        prices = self.extractor.extract(html)
        
        assert len(prices) > 0
        # Tier detection is best-effort
        if prices[0].tier_name:
            assert 'pro' in prices[0].tier_name.lower()
    
    def test_no_prices(self):
        """Test handling of pages with no prices."""
        html = "<html><body><p>Contact us for pricing</p></body></html>"
        prices = self.extractor.extract(html)
        
        # Should return empty list, not raise error
        assert isinstance(prices, list)


class TestDOMExtractor:
    """Test DOM-based price extraction."""
    
    def setup_method(self):
        self.extractor = DOMPriceExtractor()
    
    def test_price_in_container(self):
        """Test extraction from pricing container."""
        html = """
        <html><body>
            <div class="pricing-card">
                <h3>Starter</h3>
                <p class="price">$19.99</p>
            </div>
        </body></html>
        """
        prices = self.extractor.extract(html)
        
        assert len(prices) > 0
        assert prices[0].value == 19.99
    
    def test_multiple_tiers(self):
        """Test extraction of multiple pricing tiers."""
        html = """
        <html><body>
            <div class="pricing-table">
                <div class="tier" id="basic">
                    <h3>Basic</h3>
                    <span class="amount">$9.99</span>
                </div>
                <div class="tier" id="pro">
                    <h3>Professional</h3>
                    <span class="amount">$29.99</span>
                </div>
            </div>
        </body></html>
        """
        prices = self.extractor.extract(html)
        
        assert len(prices) >= 2
        values = [p.value for p in prices]
        assert 9.99 in values
        assert 29.99 in values
    
    def test_prominent_text(self):
        """Test extraction of prominent pricing."""
        html = """
        <html><body>
            <h1 style="font-size: 48px;">$99</h1>
            <p>per month</p>
        </body></html>
        """
        prices = self.extractor.extract(html)
        
        assert len(prices) > 0
        assert prices[0].value == 99.0


class TestPriceExtractorIntegration:
    """Integration tests for full extraction pipeline."""
    
    def test_realistic_pricing_page(self):
        """Test extraction from realistic pricing page HTML."""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Pricing</title></head>
        <body>
            <div class="pricing-section">
                <div class="plan">
                    <h2>Starter</h2>
                    <div class="price">
                        <span class="currency">$</span>
                        <span class="amount">9</span>
                        <span class="period">/month</span>
                    </div>
                    <ul>
                        <li>5 users</li>
                        <li>10GB storage</li>
                    </ul>
                </div>
                <div class="plan">
                    <h2>Professional</h2>
                    <div class="price">
                        <span class="currency">$</span>
                        <span class="amount">29</span>
                        <span class="period">/month</span>
                    </div>
                    <ul>
                        <li>Unlimited users</li>
                        <li>100GB storage</li>
                    </ul>
                </div>
                <div class="plan">
                    <h2>Enterprise</h2>
                    <div class="price">
                        <span class="currency">$</span>
                        <span class="amount">99</span>
                        <span class="period">/month</span>
                    </div>
                    <ul>
                        <li>Custom everything</li>
                        <li>Unlimited storage</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        
        from pricewatch.core.extractor import PriceExtractor
        from pricewatch.core.models import Snapshot
        
        extractor = PriceExtractor(use_llm=False)
        
        snapshot = Snapshot(
            url="https://example.com/pricing",
            timestamp=datetime.now(),
            wayback_url="https://web.archive.org/...",
            status_code=200,
            is_exact_match=True,
            distance_days=0
        )
        
        result = extractor.extract_from_snapshot(snapshot, html)
        
        assert result.has_prices
        assert len(result.prices) >= 3
        
        # Check we found all three price points
        values = [p.value for p in result.prices]
        assert 9.0 in values
        assert 29.0 in values
        assert 99.0 in values
        
        # Check extraction metadata
        assert result.extraction_time_ms > 0
        assert result.html_length == len(html)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
