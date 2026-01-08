"""DOM-based price extraction with heuristics."""
import re
from typing import List, Optional
from bs4 import BeautifulSoup, Tag

from ..core.models import ExtractedPrice, Currency, PriceType, ExtractionMethod


class DOMPriceExtractor:
    """Extract prices using DOM structure and heuristics."""
    
    # Common pricing container classes/ids
    PRICE_CONTAINER_PATTERNS = [
        r'price', r'pricing', r'cost', r'fee',
        r'plan', r'tier', r'package',
        r'subscription', r'billing'
    ]
    
    # Price element patterns
    PRICE_ELEMENT_PATTERNS = [
        r'amount', r'value', r'rate'
    ]
    
    def __init__(self):
        self.regex_extractor = None  # Lazy import to avoid circular dependency
    
    def extract(self, html: str) -> List[ExtractedPrice]:
        """
        Extract prices using DOM structure.
        
        Args:
            html: HTML content
            
        Returns:
            List of extracted prices
        """
        soup = BeautifulSoup(html, 'lxml')
        
        prices = []
        
        # Strategy 1: Find price containers
        containers = self._find_price_containers(soup)
        
        for container in containers:
            container_prices = self._extract_from_container(container)
            prices.extend(container_prices)
        
        # Strategy 2: Look for prominent large text (often prices)
        if len(prices) < 3:  # If we didn't find much
            prominent_prices = self._extract_prominent_prices(soup)
            prices.extend(prominent_prices)
        
        # Deduplicate by value
        seen = set()
        unique_prices = []
        for price in prices:
            if price.value not in seen:
                seen.add(price.value)
                unique_prices.append(price)
        
        return sorted(unique_prices, key=lambda p: p.value)
    
    def _find_price_containers(self, soup: BeautifulSoup) -> List[Tag]:
        """Find likely price container elements."""
        containers = []
        
        for pattern in self.PRICE_CONTAINER_PATTERNS:
            # Find by class
            for tag in soup.find_all(class_=re.compile(pattern, re.I)):
                if isinstance(tag, Tag):
                    containers.append(tag)
            
            # Find by id
            for tag in soup.find_all(id=re.compile(pattern, re.I)):
                if isinstance(tag, Tag):
                    containers.append(tag)
            
            # Find by data attributes
            for tag in soup.find_all(attrs={'data-price': True}):
                if isinstance(tag, Tag):
                    containers.append(tag)
        
        return containers
    
    def _extract_from_container(self, container: Tag) -> List[ExtractedPrice]:
        """Extract prices from a container element."""
        prices = []
        
        # Get text content
        text = container.get_text()
        
        # Look for currency symbols and numbers
        price_pattern = r'([$€£¥])\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        
        for match in re.finditer(price_pattern, text):
            symbol = match.group(1)
            value_str = match.group(2)
            
            try:
                value = float(value_str.replace(',', ''))
                
                # Realistic price check
                if value < 0.01 or value > 1000000:
                    continue
                
                currency = self._symbol_to_currency(symbol)
                
                # Try to get tier from container
                tier = self._extract_tier_from_container(container)
                
                # Detect price type
                price_type = self._detect_price_type(text)
                
                prices.append(ExtractedPrice(
                    value=value,
                    currency=currency,
                    price_type=price_type,
                    tier_name=tier,
                    raw_text=match.group(0),
                    confidence=0.85,  # DOM is more reliable than regex
                    extraction_method=ExtractionMethod.DOM
                ))
                
            except ValueError:
                continue
        
        return prices
    
    def _extract_prominent_prices(self, soup: BeautifulSoup) -> List[ExtractedPrice]:
        """Look for large, prominent text that might be prices."""
        prices = []
        
        # Find elements with large font sizes (common for pricing)
        for tag in soup.find_all(['h1', 'h2', 'h3', 'span', 'div', 'p']):
            if not isinstance(tag, Tag):
                continue
            
            # Check if element has style indicating prominence
            style = tag.get('style', '')
            classes = ' '.join(tag.get('class', []))
            
            # Look for large font indicators
            is_prominent = (
                'font-size' in style.lower() or
                'large' in classes.lower() or
                'big' in classes.lower() or
                'heading' in classes.lower()
            )
            
            if not is_prominent:
                continue
            
            text = tag.get_text()
            price_match = re.search(r'([$€£¥])\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
            
            if price_match:
                symbol = price_match.group(1)
                value_str = price_match.group(2)
                
                try:
                    value = float(value_str.replace(',', ''))
                    
                    if 0.01 <= value <= 1000000:
                        prices.append(ExtractedPrice(
                            value=value,
                            currency=self._symbol_to_currency(symbol),
                            price_type=self._detect_price_type(text),
                            tier_name=None,
                            raw_text=price_match.group(0),
                            confidence=0.75,
                            extraction_method=ExtractionMethod.DOM
                        ))
                except ValueError:
                    pass
        
        return prices
    
    def _extract_tier_from_container(self, container: Tag) -> Optional[str]:
        """Try to extract tier name from container."""
        # Look for heading within container
        for heading in container.find_all(['h1', 'h2', 'h3', 'h4']):
            text = heading.get_text().strip()
            if text and len(text) < 50:
                return text
        
        # Look for data attributes
        tier = container.get('data-plan') or container.get('data-tier')
        if tier:
            return str(tier)
        
        return None
    
    @staticmethod
    def _symbol_to_currency(symbol: str) -> Currency:
        """Convert currency symbol to Currency enum."""
        mapping = {
            '$': Currency.USD,
            '€': Currency.EUR,
            '£': Currency.GBP,
            '¥': Currency.JPY,
        }
        return mapping.get(symbol, Currency.USD)
    
    @staticmethod
    def _detect_price_type(text: str) -> PriceType:
        """Detect price type from text."""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['month', 'monthly', '/mo']):
            return PriceType.MONTHLY
        elif any(kw in text_lower for kw in ['year', 'annual', 'yearly', '/yr']):
            return PriceType.ANNUAL
        
        return PriceType.UNKNOWN
