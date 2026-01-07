"""Snapshot sampling strategies."""
from datetime import datetime, timedelta
from typing import List, Optional
from dateutil.relativedelta import relativedelta

from .models import Snapshot
from .wayback import WaybackClient


class SnapshotSampler:
    """Sample snapshots at regular intervals."""
    
    def __init__(self, client: WaybackClient):
        self.client = client
    
    def get_quarterly_snapshots(
        self,
        url: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        max_distance_days: int = 45
    ) -> List[Snapshot]:
        """
        Get snapshots at quarterly intervals.
        
        Args:
            url: Target URL
            start_date: First quarter to sample
            end_date: Last quarter to sample (default: today)
            max_distance_days: Max days to search for nearest snapshot
            
        Returns:
            List of snapshots at quarterly intervals
        """
        if end_date is None:
            end_date = datetime.now()
        
        target_dates = self._generate_quarterly_dates(start_date, end_date)
        snapshots = []
        
        for target in target_dates:
            snapshot = self.client.get_closest_snapshot(
                url, target, max_distance_days
            )
            if snapshot:
                snapshots.append(snapshot)
        
        return snapshots
    
    def get_monthly_snapshots(
        self,
        url: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        max_distance_days: int = 20
    ) -> List[Snapshot]:
        """Get snapshots at monthly intervals."""
        if end_date is None:
            end_date = datetime.now()
        
        target_dates = self._generate_monthly_dates(start_date, end_date)
        snapshots = []
        
        for target in target_dates:
            snapshot = self.client.get_closest_snapshot(
                url, target, max_distance_days
            )
            if snapshot:
                snapshots.append(snapshot)
        
        return snapshots
    
    def get_annual_snapshots(
        self,
        url: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        max_distance_days: int = 90
    ) -> List[Snapshot]:
        """Get snapshots at annual intervals."""
        if end_date is None:
            end_date = datetime.now()
        
        target_dates = self._generate_annual_dates(start_date, end_date)
        snapshots = []
        
        for target in target_dates:
            snapshot = self.client.get_closest_snapshot(
                url, target, max_distance_days
            )
            if snapshot:
                snapshots.append(snapshot)
        
        return snapshots
    
    @staticmethod
    def _generate_quarterly_dates(
        start: datetime,
        end: datetime
    ) -> List[datetime]:
        """Generate dates for start of each quarter."""
        dates = []
        current = start.replace(day=1)
        
        # Align to quarter start
        quarter_month = ((current.month - 1) // 3) * 3 + 1
        current = current.replace(month=quarter_month)
        
        while current <= end:
            dates.append(current)
            current += relativedelta(months=3)
        
        return dates
    
    @staticmethod
    def _generate_monthly_dates(
        start: datetime,
        end: datetime
    ) -> List[datetime]:
        """Generate dates for start of each month."""
        dates = []
        current = start.replace(day=1)
        
        while current <= end:
            dates.append(current)
            current += relativedelta(months=1)
        
        return dates
    
    @staticmethod
    def _generate_annual_dates(
        start: datetime,
        end: datetime
    ) -> List[datetime]:
        """Generate dates for start of each year."""
        dates = []
        current = start.replace(month=1, day=1)
        
        while current <= end:
            dates.append(current)
            current += relativedelta(years=1)
        
        return dates
