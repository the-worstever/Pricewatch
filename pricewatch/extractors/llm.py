"""LLM-assisted price extraction as fallback."""
import json
import re
from typing import List, Optional
from bs4 import BeautifulSoup

from ..core.models import ExtractedPrice, Currency, PriceType, ExtractionMethod


class LLMPriceExtractor:
    """Extract prices using local LLM when other methods fail."""
    
    def __init__(self, ollama_model: str = "llama3.2", ollama_host: str = "http://localhost:11434"):
        """
        Initialize LLM extractor.
        
        Args:
            ollama_model: Ollama model to use
            ollama_host: Ollama API endpoint
        """
        self.model = ollama_model
        self.host = ollama_host
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests
            response = requests.get(f"{self.host}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def extract(self, html: str) -> List[ExtractedPrice]:
        """
        Extract prices using LLM.
        
        Args:
            html: HTML content
            
        Returns:
            List of extracted prices
        """
        if not self.available:
            return []
        
        # Clean HTML to reduce token count
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove non-content elements
        for element in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav']):
            element.decompose()
        
        # Get main content text (limited)
        text = soup.get_text()
        text = ' '.join(text.split())  # Normalize whitespace
        
        # Limit text length for LLM
        max_chars = 4000
        if len(text) > max_chars:
            # Try to find pricing section
            pricing_section = self._find_pricing_section(text)
            if pricing_section:
                text = pricing_section[:max_chars]
            else:
                text = text[:max_chars]
        
        # Query LLM
        prices = self._query_llm(text)
        
        return prices
    
    def _find_pricing_section(self, text: str) -> Optional[str]:
        """Try to isolate pricing-relevant section."""
        text_lower = text.lower()
        
        # Find keywords
        pricing_keywords = ['pricing', 'price', 'plans', 'cost', 'subscription', 'buy']
        
        best_section = None
        best_score = 0
        
        # Split into chunks
        chunks = [text[i:i+1000] for i in range(0, len(text), 500)]
        
        for chunk in chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for kw in pricing_keywords if kw in chunk_lower)
            
            if score > best_score:
                best_score = score
                best_section = chunk
        
        return best_section
    
    def _query_llm(self, text: str) -> List[ExtractedPrice]:
        """Query Ollama for price extraction."""
        try:
            import requests
        except ImportError:
            return []
        
        prompt = f"""Extract all pricing information from the following text. Return ONLY a JSON array with this structure:
[
  {{
    "value": 99.99,
    "currency": "USD",
    "type": "monthly",
    "tier": "Professional",
    "confidence": 0.9
  }}
]

Rules:
- Extract only explicit prices (numbers with currency)
- type can be: "monthly", "annual", "one_time", or "unknown"
- currency: "USD", "EUR", "GBP", etc.
- confidence: 0.0 to 1.0
- tier: name of pricing tier if mentioned

Text:
{text}

JSON array:"""
        
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for factual extraction
                        "num_predict": 500,
                    }
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return []
            
            result = response.json()
            llm_output = result.get('response', '')
            
            # Parse JSON from response
            prices = self._parse_llm_response(llm_output)
            
            return prices
            
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return []
    
    def _parse_llm_response(self, response: str) -> List[ExtractedPrice]:
        """Parse LLM JSON response into ExtractedPrice objects."""
        # Try to find JSON array in response
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if not json_match:
            return []
        
        try:
            data = json.loads(json_match.group(0))
            
            prices = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                
                try:
                    # Map LLM output to our model
                    currency_str = item.get('currency', 'USD').upper()
                    try:
                        currency = Currency[currency_str]
                    except KeyError:
                        currency = Currency.USD
                    
                    type_str = item.get('type', 'unknown').lower()
                    price_type = PriceType.UNKNOWN
                    if type_str == 'monthly':
                        price_type = PriceType.MONTHLY
                    elif type_str == 'annual':
                        price_type = PriceType.ANNUAL
                    elif type_str == 'one_time':
                        price_type = PriceType.ONE_TIME
                    
                    prices.append(ExtractedPrice(
                        value=float(item['value']),
                        currency=currency,
                        price_type=price_type,
                        tier_name=item.get('tier'),
                        raw_text=f"{item.get('currency', '$')}{item['value']}",
                        confidence=float(item.get('confidence', 0.7)),
                        extraction_method=ExtractionMethod.LLM
                    ))
                except (KeyError, ValueError, TypeError):
                    continue
            
            return prices
            
        except json.JSONDecodeError:
            return []
