"""Wayback Machine API client."""
import requests
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote
import time

from .models import Snapshot


class WaybackClient:
    """Client for interacting with Wayback Machine CDX API."""
    
    CDX_API = "http://web.archive.org/cdx/search/cdx"
    WAYBACK_PREFIX = "https://web.archive.org/web"
    
    def __init__(self, rate_limit: float = 0.5):
        """
        Initialize client.
        
        Args:
            rate_limit: Minimum seconds between requests
        """
        self.rate_limit = rate_limit
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PriceWatch/0.1.0 (Market Intelligence Tool)'
        })
    
    def _rate_limit_sleep(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()
    
    def get_snapshots(
        self,
        url: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Snapshot]:
        """
        Get all snapshots for a URL.
        
        Args:
            url: Target URL
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            limit: Maximum number of snapshots
            
        Returns:
            List of Snapshot objects
        """
        self._rate_limit_sleep()
        
        params = {
            'url': url,
            'output': 'json',
            'fl': 'timestamp,original,statuscode',
            'filter': 'statuscode:200',
            'collapse': 'timestamp:8',  # One per day
        }
        
        if from_date:
            params['from'] = from_date.strftime('%Y%m%d')
        if to_date:
            params['to'] = to_date.strftime('%Y%m%d')
        if limit:
            params['limit'] = limit
        
        try:
            response = self.session.get(self.CDX_API, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if not data or len(data) < 2:  # First row is header
                return []
            
            snapshots = []
            for row in data[1:]:  # Skip header
                timestamp_str, original_url, status = row
                
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                wayback_url = f"{self.WAYBACK_PREFIX}/{timestamp_str}id_/{original_url}"
                
                snapshots.append(Snapshot(
                    url=original_url,
                    timestamp=timestamp,
                    wayback_url=wayback_url,
                    status_code=int(status),
                    is_exact_match=True,
                    distance_days=0
                ))
            
            return snapshots
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch snapshots: {e}")
    
    def get_closest_snapshot(
        self,
        url: str,
        target_date: datetime,
        max_distance_days: int = 60
    ) -> Optional[Snapshot]:
        """
        Find closest snapshot to target date.
        
        Args:
            url: Target URL
            target_date: Desired date
            max_distance_days: Maximum acceptable distance
            
        Returns:
            Closest Snapshot or None
        """
        from datetime import timedelta
        
        # Search window around target
        from_date = target_date - timedelta(days=max_distance_days)
        to_date = target_date + timedelta(days=max_distance_days)
        
        snapshots = self.get_snapshots(url, from_date, to_date)
        
        if not snapshots:
            return None
        
        # Find closest
        closest = min(
            snapshots,
            key=lambda s: abs((s.timestamp - target_date).days)
        )
        
        distance = abs((closest.timestamp - target_date).days)
        
        if distance > max_distance_days:
            return None
        
        closest.is_exact_match = distance == 0
        closest.distance_days = distance
        
        return closest
    
    def fetch_html(self, snapshot: Snapshot) -> str:
        """
        Fetch HTML content from snapshot.
        
        Args:
            snapshot: Snapshot to fetch
            
        Returns:
            HTML content
        """
        self._rate_limit_sleep()
        
        try:
            # Use id_ modifier to get raw content without Wayback toolbar
            clean_url = snapshot.wayback_url
            
            response = self.session.get(clean_url, timeout=30)
            response.raise_for_status()
            
            return response.text
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch HTML: {e}")
