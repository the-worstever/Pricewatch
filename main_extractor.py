"""Main price extraction pipeline."""
import time
from typing import List
from datetime import datetime

from .models import PriceSnapshot, Snapshot, ExtractedPrice
from ..extractors.regex_extractor import RegexPriceExtractor
from ..extractors.dom_extractor import DOMPriceExtractor
from ..extractors.llm_extractor import LLMPriceExtractor


class PriceExtractor:
    """Multi-stage price extraction pipeline."""
    
    def __init__(self, use_llm: bool = False, llm_model: str = "llama3.2"):
        """
        Initialize extractor.
        
        Args:
            use_llm: Enable LLM fallback extraction
            llm_model: Ollama model for LLM extraction
        """
        self.regex_extractor = RegexPriceExtractor()
        self.dom_extractor = DOMPriceExtractor()
        
        self.use_llm = use_llm
        self.llm_extractor = None
        if use_llm:
            self.llm_extractor = LLMPriceExtractor(ollama_model=llm_model)
    
    def extract_from_snapshot(self, snapshot: Snapshot, html: str) -> PriceSnapshot:
        """
        Extract prices from snapshot HTML.
        
        Args:
            snapshot: Snapshot metadata
            html: HTML content
            
        Returns:
            PriceSnapshot with extracted prices
        """
        start_time = time.time()
        
        all_prices: List[ExtractedPrice] = []
        errors: List[str] = []
        
        # Stage 1: Regex extraction
        try:
            regex_prices = self.regex_extractor.extract(html)
            all_prices.extend(regex_prices)
        except Exception as e:
            errors.append(f"Regex extraction failed: {e}")
        
        # Stage 2: DOM extraction (if regex found few results)
        if len(all_prices) < 3:
            try:
                dom_prices = self.dom_extractor.extract(html)
                all_prices.extend(dom_prices)
            except Exception as e:
                errors.append(f"DOM extraction failed: {e}")
        
        # Stage 3: LLM fallback (if still no good results)
        if len(all_prices) < 2 and self.use_llm and self.llm_extractor:
            try:
                llm_prices = self.llm_extractor.extract(html)
                all_prices.extend(llm_prices)
            except Exception as e:
                errors.append(f"LLM extraction failed: {e}")
        
        # Deduplicate and merge prices
        final_prices = self._deduplicate_prices(all_prices)
        
        extraction_time = (time.time() - start_time) * 1000  # ms
        
        return PriceSnapshot(
            snapshot=snapshot,
            prices=final_prices,
            html_length=len(html),
            extraction_time_ms=extraction_time,
            errors=errors
        )
    
    def _deduplicate_prices(self, prices: List[ExtractedPrice]) -> List[ExtractedPrice]:
        """
        Deduplicate prices, keeping highest confidence for each value.
        
        Args:
            prices: List of extracted prices
            
        Returns:
            Deduplicated list
        """
        if not prices:
            return []
        
        # Group by value
        by_value = {}
        for price in prices:
            if price.value not in by_value:
                by_value[price.value] = []
            by_value[price.value].append(price)
        
        # Keep best price for each value
        deduplicated = []
        for value, price_list in by_value.items():
            # Prefer higher confidence and better extraction method
            best = max(
                price_list,
                key=lambda p: (
                    p.confidence,
                    self._method_priority(p.extraction_method)
                )
            )
            deduplicated.append(best)
        
        return sorted(deduplicated, key=lambda p: p.value)
    
    @staticmethod
    def _method_priority(method) -> int:
        """Get priority score for extraction method."""
        from .models import ExtractionMethod
        
        priority = {
            ExtractionMethod.DOM: 3,
            ExtractionMethod.REGEX: 2,
            ExtractionMethod.LLM: 1,
            ExtractionMethod.MANUAL: 4,
        }
        return priority.get(method, 0)
