"""
parsers/base.py

Abstract base class for all data parsers.
Defines the contract: any parser must implement parse() and return list[Press].

Today: ProductivityCSVParser reads a CSV file.
Tomorrow: ProductivityAPIParser hits the Auto-Count API.
The calculations and UI never know which one is running.
"""

from abc import ABC, abstractmethod
from models.press import Press


class ProductivityParser(ABC):

    @abstractmethod
    def parse(self, source, machine_log=None) -> list[Press]:
        """
        Parse a data source and return one Press object per machine.

        Parameters
        ----------
        source : any
            Primary data source — operation-level data for time accounting
            and sheet counts.
            For CSV parser: a file path (str or Path) to Productivity by Machine.
            For API parser: a URL, credentials, date range, etc.
        machine_log : any, optional
            Secondary data source — shift-level data for shift counting.
            Required for the mins_per_shift display calculation.
            For CSV parser: a file path to the Machine Log export.
            If not provided, total_shifts on each Press will be 0.

        Returns
        -------
        list[Press]
            One fully-populated Press per machine found in the source.
        """
