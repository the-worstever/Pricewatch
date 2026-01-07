"""Regex-based price extraction."""
import re
from typing import List
from bs4 import BeautifulSoup

from ..core.models import ExtractedPrice, Currency, PriceType, ExtractionMethod


class RegexPriceExtractor:
    """Extract prices using regex patterns."""
    
    # Price patterns for different formats
    PATTERNS = [
        # $99.99, $99, $9,999.99
        r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        # €99.99, €99
        r'€\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        # £99.99
        r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        # 99.99 USD, 99 USD
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',
        # 99.99 EUR
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*EUR',
        # USD 99.99
        r'USD\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        # Price: $99
        r'(?:price|cost|fee):\s*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]
    
    CURRENCY_SYMBOLS = {
        '$': Currency.USD,
        '€': Currency.EUR,
        '£': Currency.GBP,
        '¥': Currency.JPY,
    }
    
    CURRENCY_CODES = {
        'USD': Currency.USD,
        'EUR': Currency.EUR,
        'GBP': Currency.GBP,
        'JPY': Currency.JPY,
        'CAD': Currency.CAD,
        'AUD': Currency.AUD,
    }
    
    PRICE_TYPE_KEYWORDS = {
        'month': PriceType.MONTHLY,
        'monthly': PriceType.MONTHLY,
        'mo': PriceType.MONTHLY,
        '/month': PriceType.MONTHLY,
        '/mo': PriceType.MONTHLY,
        'year': PriceType.ANNUAL,
        'annual': PriceType.ANNUAL,
        'annually': PriceType.ANNUAL,
        '/year': PriceType.ANNUAL,
        '/yr': PriceType.ANNUAL,
    }
    
    def extract(self, html: str) -> List[ExtractedPrice]:
        """
        Extract prices from HTML using regex.
        
        Args:
            html: HTML content
            
        Returns:
            List of extracted prices
        """
        # Parse HTML to get clean text
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'noscript']):
            element.decompose()
        
        text = soup.get_text()
        
        prices = []
        seen_values = set()  # Deduplicate
        
        for pattern in self.PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                full_match = match.group(0)
                price_str = match.group(1)
                
                # Parse numeric value
                try:
                    value = float(price_str.replace(',', ''))
                except ValueError:
                    continue
                
                # Skip if already seen or unrealistic
                if value in seen_values or value < 0.01 or value > 1000000:
                    continue
                
                seen_values.add(value)
                
                # Detect currency
                currency = self._detect_currency(full_match, text[max(0, match.start()-50):match.end()+50])
                
                # Detect price type
                context = text[max(0, match.start()-100):match.end()+100]
                price_type = self._detect_price_type(context)
                
                # Detect tier
                tier = self._detect_tier(context)
                
                prices.append(ExtractedPrice(
                    value=value,
                    currency=currency,
                    price_type=price_type,
                    tier_name=tier,
                    raw_text=full_match,
                    confidence=0.8,  # Regex has good precision
                    extraction_method=ExtractionMethod.REGEX
                ))
        
        # Sort by value to get consistent ordering
        prices.sort(key=lambda p: p.value)
        
        return prices
    
    def _detect_currency(self, match_text: str, context: str) -> Currency:
        """Detect currency from match and context."""
        # Check for currency symbols
        for symbol, currency in self.CURRENCY_SYMBOLS.items():
            if symbol in match_text:
                return currency
        
        # Check for currency codes
        for code, currency in self.CURRENCY_CODES.items():
            if code in match_text.upper() or code in context.upper():
                return currency
        
        return Currency.USD  # Default assumption
    
    def _detect_price_type(self, context: str) -> PriceType:
        """Detect if price is monthly, annual, etc."""
        context_lower = context.lower()
        
        for keyword, price_type in self.PRICE_TYPE_KEYWORDS.items():
            if keyword in context_lower:
                return price_type
        
        return PriceType.UNKNOWN
    
    def _detect_tier(self, context: str) -> str | None:
        """Try to detect pricing tier name."""
        context_lower = context.lower()
        
        tier_keywords = [
            'starter', 'basic', 'free', 'hobby',
            'professional', 'pro', 'business', 'team',
            'enterprise', 'premium', 'plus',
            'standard', 'advanced', 'ultimate'
        ]
        
        for tier in tier_keywords:
            if tier in context_lower:
                return tier.capitalize()
        
        return None
