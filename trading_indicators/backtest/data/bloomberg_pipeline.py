"""
Bloomberg Data Pipeline
=======================
Pulls OHLCV + enrichment data from Bloomberg Terminal via blpapi.

Requirements:
    - Bloomberg Terminal running with API enabled
    - pip install blpapi (download from Bloomberg)

Usage:
    from data.bloomberg_pipeline import BloombergPipeline
    bbg = BloombergPipeline()
    df = bbg.get_historical("ESA Index", "2024-01-01", "2024-12-31", "DAILY")

If you don't have blpapi installed, use the Excel BDH approach:
    1. In Bloomberg Excel Add-in, use:
       =BDH("ESA Index","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME","2024-01-01","2024-12-31","per=cd")
    2. Export to CSV
    3. Use csv_loader.py instead
"""
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BLOOMBERG, DATA


class BloombergPipeline:
    """Pull data from Bloomberg Terminal API."""

    def __init__(self, host=None, port=None):
        self.host = host or BLOOMBERG.host
        self.port = port or BLOOMBERG.port
        self.session = None
        self._connected = False

    def connect(self):
        """Establish Bloomberg API session."""
        try:
            import blpapi
        except ImportError:
            raise ImportError(
                "blpapi not installed. Install from Bloomberg WAPI page or use "
                "the Excel BDH export workflow instead (see docstring)."
            )
        session_options = blpapi.SessionOptions()
        session_options.setServerHost(self.host)
        session_options.setServerPort(self.port)

        self.session = blpapi.Session(session_options)
        if not self.session.start():
            raise ConnectionError("Failed to start Bloomberg session")
        if not self.session.openService("//blp/refdata"):
            raise ConnectionError("Failed to open //blp/refdata service")
        self._connected = True
        print(f"Connected to Bloomberg on {self.host}:{self.port}")

    def get_historical(self, ticker: str, start_date: str, end_date: str,
                       periodicity: str = "DAILY",
                       fields: list = None) -> pd.DataFrame:
        """
        Pull historical OHLCV data.

        Args:
            ticker: Bloomberg ticker (e.g., "ESA Index", "CLA Comdty")
            start_date: "YYYY-MM-DD"
            end_date: "YYYY-MM-DD"
            periodicity: "DAILY", "WEEKLY", "MONTHLY",
                         or for intraday: use get_intraday() instead
            fields: Override default OHLCV fields

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        if not self._connected:
            self.connect()

        import blpapi
        service = self.session.getService("//blp/refdata")
        request = service.createRequest("HistoricalDataRequest")

        request.getElement("securities").appendValue(ticker)
        flds = fields or BLOOMBERG.fields
        for f in flds:
            request.getElement("fields").appendValue(f)

        request.set("startDate", start_date.replace("-", ""))
        request.set("endDate", end_date.replace("-", ""))
        request.set("periodicitySelection", periodicity)
        request.set("adjustmentSplit", True)

        self.session.sendRequest(request)

        data = []
        while True:
            event = self.session.nextEvent(500)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    field_data = sec_data.getElement("fieldData")
                    for i in range(field_data.numValues()):
                        bar = field_data.getValueAsElement(i)
                        row = {"date": bar.getElementAsDatetime("date")}
                        for f in flds:
                            try:
                                row[f] = bar.getElementAsFloat(f)
                            except Exception:
                                row[f] = np.nan
                        data.append(row)
            if event.eventType() == blpapi.Event.RESPONSE:
                break

        df = pd.DataFrame(data)
        if df.empty:
            print(f"Warning: No data returned for {ticker}")
            return df

        # Rename to standard columns
        col_map = {
            "PX_OPEN": "open", "PX_HIGH": "high", "PX_LOW": "low",
            "PX_LAST": "close", "VOLUME": "volume"
        }
        df = df.rename(columns=col_map)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def get_intraday(self, ticker: str, start_dt: str, end_dt: str,
                     interval: int = 60) -> pd.DataFrame:
        """
        Pull intraday bars.

        Args:
            ticker: Bloomberg ticker
            start_dt: "YYYY-MM-DDTHH:MM:SS" (e.g., "2024-06-01T09:30:00")
            end_dt: "YYYY-MM-DDTHH:MM:SS"
            interval: Bar size in minutes (1, 5, 15, 30, 60)

        Returns:
            DataFrame with: datetime, open, high, low, close, volume
        """
        if not self._connected:
            self.connect()

        import blpapi
        service = self.session.getService("//blp/refdata")
        request = service.createRequest("IntradayBarRequest")

        request.set("security", ticker)
        request.set("eventType", "TRADE")
        request.set("interval", interval)
        request.set("startDateTime", start_dt)
        request.set("endDateTime", end_dt)

        self.session.sendRequest(request)

        data = []
        while True:
            event = self.session.nextEvent(500)
            for msg in event:
                if msg.hasElement("barData"):
                    bar_data = msg.getElement("barData").getElement("barTickData")
                    for i in range(bar_data.numValues()):
                        bar = bar_data.getValueAsElement(i)
                        data.append({
                            "datetime": bar.getElementAsDatetime("time"),
                            "open": bar.getElementAsFloat("open"),
                            "high": bar.getElementAsFloat("high"),
                            "low": bar.getElementAsFloat("low"),
                            "close": bar.getElementAsFloat("close"),
                            "volume": bar.getElementAsInteger("volume"),
                        })
            if event.eventType() == blpapi.Event.RESPONSE:
                break

        df = pd.DataFrame(data)
        if not df.empty:
            df["datetime"] = pd.to_datetime(df["datetime"])
            df["date"] = df["datetime"].dt.date
            df = df.sort_values("datetime").reset_index(drop=True)
        return df

    def get_reference(self, ticker: str, fields: list = None) -> dict:
        """
        Pull current snapshot data (BDP equivalent).

        Args:
            ticker: Bloomberg ticker
            fields: List of fields (e.g., ["PX_LAST", "IVOL_MID", "VOLUME"])

        Returns:
            dict of {field: value}
        """
        if not self._connected:
            self.connect()

        import blpapi
        service = self.session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")
        request.getElement("securities").appendValue(ticker)

        flds = fields or BLOOMBERG.enrichment_fields
        for f in flds:
            request.getElement("fields").appendValue(f)

        self.session.sendRequest(request)

        result = {}
        while True:
            event = self.session.nextEvent(500)
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_array = msg.getElement("securityData")
                    for i in range(sec_array.numValues()):
                        sec = sec_array.getValueAsElement(i)
                        field_data = sec.getElement("fieldData")
                        for f in flds:
                            try:
                                result[f] = field_data.getElementAsFloat(f)
                            except Exception:
                                try:
                                    result[f] = str(field_data.getElement(f))
                                except Exception:
                                    result[f] = None
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        return result

    def get_correlation_matrix(self, tickers: list, start_date: str,
                                end_date: str) -> pd.DataFrame:
        """
        Pull close prices for multiple tickers and compute correlation matrix.
        Useful for portfolio risk: checking if your positions are correlated.
        """
        frames = {}
        for t in tickers:
            df = self.get_historical(t, start_date, end_date)
            if not df.empty:
                frames[t] = df.set_index("date")["close"]

        if not frames:
            return pd.DataFrame()

        combined = pd.DataFrame(frames)
        returns = combined.pct_change().dropna()
        return returns.corr()

    def disconnect(self):
        if self.session:
            self.session.stop()
            self._connected = False


# ============================================================
# EXCEL BDH EXPORT HELPER
# ============================================================
def generate_bdh_formulas(ticker: str, start_date: str, end_date: str,
                          interval: str = "cd") -> str:
    """
    Generate Bloomberg Excel formulas you can paste into your spreadsheet.
    This is the fallback when blpapi isn't available.

    Args:
        ticker: e.g., "ESA Index"
        start_date: "2024-01-01"
        end_date: "2024-12-31"
        interval: "cd" (calendar day), "cw" (week), "cm" (month)

    Returns:
        String of Excel formulas to paste
    """
    s = start_date.replace("-", "")
    e = end_date.replace("-", "")
    formulas = f"""
Bloomberg Excel BDH Formulas — paste these into your Bloomberg Excel workbook:

=== OHLCV Daily Data ===
Cell A1: =BDH("{ticker}","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME","{s}","{e}","per={interval}")

=== Intraday (if you have BDH intraday access) ===
Cell A1: =BDH("{ticker}","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME","{s}","{e}","per=hr")

=== Enrichment Snapshot ===
Current Price:      =BDP("{ticker}","PX_LAST")
Implied Vol:        =BDP("{ticker}","IVOL_MID")
Open Interest:      =BDP("{ticker}","OPEN_INT")
52W High:           =BDP("{ticker}","HIGH_52WEEK")
52W Low:            =BDP("{ticker}","LOW_52WEEK")
Beta:               =BDP("{ticker}","EQY_BETA")
Volume Today:       =BDP("{ticker}","VOLUME")
ATR (manual):       Use BDH to pull 14 days of highs/lows/closes, then calculate

=== Commitment of Traders (if applicable) ===
Net Non-Commercial: =BDP("CFTCES Index","NET_NON_COMMERCIAL_POSITION")

=== After Export ===
1. Copy the data range
2. Paste Special > Values to remove Bloomberg links
3. Save as CSV with headers: date,open,high,low,close,volume
4. Use csv_loader.py to load into the backtester
"""
    return formulas


if __name__ == "__main__":
    # If run directly, print the Excel helper formulas
    print(generate_bdh_formulas("ESA Index", DATA.start_date, DATA.end_date))
    print("\n--- Other common tickers ---")
    for name, ticker in [
        ("E-mini Nasdaq", "NQA Index"),
        ("Crude Oil", "CLA Comdty"),
        ("Gold", "GCA Comdty"),
        ("10Y Treasury", "TYA Comdty"),
    ]:
        print(f"\n{name}:")
        print(f'  =BDH("{ticker}","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME","{DATA.start_date.replace("-","")}","{DATA.end_date.replace("-","")}","per=cd")')
