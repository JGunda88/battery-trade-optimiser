from dataclasses import dataclass
from pathlib import Path
import pandas as pd

@dataclass
class BatteryProperties:
    """
    Data class to hold battery properties with default values.
    These defaults are overridden by reading the input excel file.
    """
    capacity_mwh: float = 4.0
    initial_soc_mwh: float = capacity_mwh
    max_charge_mw: float = 2.0
    max_discharge_mw: float = 2.0
    charging_efficiency: float = 0.95
    discharging_efficiency: float = 0.95
    lifetime_years: int = 10
    lifetime_cycles: int = 5000
    degradation_per_cycle: float = 0.001
    capex_gbp:float = 50000.0
    opex_fixed_annual_gbp: float = 5000.0

@dataclass
class MarketSeries:
    """
    Data class to hold market price series and time points.
    """
    market1_price_hh: dict[str, float] # half-hourly prices for Market 1
    market2_price_h: dict[str, float]  # hourly prices for Market 2
    market2_price_hh: dict[str, float] # half-hourly prices for Market 2 (extrapolated)
    time_points: list[str] # sorted list of half-hourly timestamp strings

@dataclass
class ProcessedInput:
    """
    Data class to hold all processed input data.
    This will be passed to the optimiser.
    """
    battery_properties: BatteryProperties
    market_series: MarketSeries

class PreProcessor:
    """
    Class to handle pre-processing of input data from Excel files.
    It reads battery properties and market price series, and packs them into structured data classes: BatteryProperties,
    MarketSeries, and ProcessedInput.
    """
    def __init__(self, market_data: Path, battery_data: Path):
        """
        Initializes the PreProcessor with paths to market data and battery data Excel files.
        :param market_data:
        :param battery_data:
        """
        self.market_data = market_data
        self.battery_data = battery_data
        self.processed_input = None

    def run(self) -> ProcessedInput:
        """
        Main method to execute the pre-processing steps. This is the only method exposed to the outside.
        :return:
        """
        battery_properties = self._extract_battery_properties()
        market_series = self._extract_market_series()
        return ProcessedInput(
            battery_properties=battery_properties,
            market_series=market_series
        )

    def _extract_battery_properties(self):
        """
        Reads battery property data from an Excel file with a single sheet named 'Data'.
        Only the 'Parameter' and 'Values' columns are read. The method extracts the following battery attributes:
        - Max charging rate (MW)
        - Max discharging rate (MW)
        - Max storage volume (MWh)
        - Battery charging efficiency (converted from loss fraction to efficiency)
        - Battery discharging efficiency (converted from loss fraction to efficiency)
        - Lifetime (years and cycles)
        - Storage volume degradation rate (converted from percent to fraction if needed)
        - Capex (£)
        - Fixed Operational Costs (£/year)

        The initial state of charge (`initial_soc`) is set equal to the storage capacity.

        Returns:
            BatteryProperties: An instance populated with the extracted and processed values.

        Raises:
            ValueError: If any required parameter is missing from the Excel file.

        """
        df = pd.read_excel(self.battery_data, sheet_name="Data", usecols=["Parameter", "Values"]) # type: ignore
        df.columns = ["parameter", "value"]
        df["parameter"] = df["parameter"].str.lower().str.strip()

        def clean_value(val):
            if isinstance(val, str):
                val = val.replace("£", "").replace(",", "").strip()
            try:
                return float(val)
            except ValueError:
                return val

        df["value"] = df["value"].apply(clean_value)
        kv = dict(zip(df["parameter"], df["value"]))

        mapping = {
            "max charging rate": "max_charge_mw",
            "max discharging rate": "max_discharge_mw",
            "max storage volume": "capacity_mwh",
            "battery charging efficiency": "charging_efficiency",
            "battery discharging efficiency": "discharging_efficiency",
            "lifetime (1)": "lifetime_years",
            "lifetime (2)": "lifetime_cycles",
            "storage volume degradation rate": "degradation_per_cycle",
            "capex": "capex_gbp",
            "fixed operational costs": "opex_fixed_annual_gbp"
        }

        properties = {}
        for excel_key, field in mapping.items():
            if excel_key not in kv:
                raise ValueError(f"Missing parameter: {excel_key}")
            properties[field] = kv[excel_key]

        # Set initial_soc equal to capacity_mwh
        properties["initial_soc_mwh"] = properties["capacity_mwh"]
        
        # Convert efficiencies from loss to efficiency
        properties["charging_efficiency"] = 1.0 - properties["charging_efficiency"]
        properties["discharging_efficiency"] = 1.0 - properties["discharging_efficiency"]

        if properties["degradation_per_cycle"] > 1:
            properties["degradation_per_cycle"] /= 100.0

        return BatteryProperties(**properties)

    def _extract_market_series(self):
        """
        Reads market price data from an Excel file with two sheets:
          - 'Half-hourly data': Contains Market 1 prices at half-hourly intervals.
          - 'Hourly data': Contains Market 2 prices at hourly intervals.

        Market 2 hourly prices are extrapolated to half-hourly by duplicating each hourly price for both the :00 and :30 time slots.

        Returns:
            MarketSeries: An instance containing:
                - market1_price_hh: dict of half-hourly Market 1 prices (timestamp string to price)
                - market1_price_h: dict of hourly Market 1 prices (if available)
                - market2_price_hh: dict of half-hourly Market 2 prices (timestamp string to price, extrapolated)
                - time_points: sorted list of all half-hourly timestamp strings
       """
        # Read half-hourly data (Market 1)
        df_hh = pd.read_excel(self.market_data, sheet_name="Half-hourly data")
        df_hh["timestamp"] = pd.to_datetime(df_hh["timestamp"])
        df_hh["timestamp"] = df_hh["timestamp"].map(self.round_to_half_hour)
        df_hh = df_hh.sort_values("timestamp")
        market1_price_hh = dict(zip(df_hh["timestamp"].dt.strftime("%Y-%m-%d %H:%M"), df_hh["Market 1 Price [£/MWh]"]))

        # Read hourly data (Market 2)
        df_h = pd.read_excel(self.market_data, sheet_name="Hourly data")
        df_h["timestamp"] = pd.to_datetime(df_h["timestamp"], errors='coerce')
        df_h["timestamp"] = df_h["timestamp"].map(self.round_to_half_hour)
        if df_h["timestamp"].isna().any():
            raise ValueError(f"Invalid or missing timestamps found in 'Hourly data' sheet: {df_h[df_h['timestamp'].isna()]}")
        df_h = df_h.sort_values("timestamp")

        # Extrapolate hourly prices to half-hourly
        market2_price_h = {}
        market2_price_hh = {}
        for idx, row in df_h.iterrows():
            price = round(row["Market 2 Price [£/MWh]"], 2)
            t1 = row["timestamp"]
            t2 = t1 + pd.Timedelta(minutes=30)
            market2_price_h[t1.strftime("%Y-%m-%d %H:%M")] = price
            market2_price_hh[t1.strftime("%Y-%m-%d %H:%M")] = price
            market2_price_hh[t2.strftime("%Y-%m-%d %H:%M")] = price


        # All half-hourly time points
        time_points = sorted(list(market1_price_hh.keys()))
        time_points = time_points[0:12] # limit to first 336 points for testing

        # for tp in time_points[:100]:
        #     print(f" tp --> {tp} - M1--> {market1_price_hh.get(tp)} - M2 --> {market2_price_hh.get(tp)}")

        return MarketSeries(
            market1_price_hh=market1_price_hh,
            market2_price_h=market2_price_h,
            market2_price_hh=market2_price_hh,
            time_points=time_points
        )

    def _read_market_series2(self):
        """
        Reads market price data from an Excel file with two sheets:
          - 'Half-hourly data': Market 1 prices at half-hourly intervals.
          - 'Hourly data': Market 2 prices at hourly intervals.

        Uses Market 1's half-hourly timestamps as reference. For each timestamp:
          - If it matches an hour in Market 2, uses that price.
          - If it is a half-hour timestamp, uses the previous hour's price from Market 2.

        Returns:
            MarketSeries: Contains aligned price dictionaries and timepoints.
        """
        # Read Market 1 (half-hourly)
        df_hh = pd.read_excel(self.market_data, sheet_name="Half-hourly data")
        df_hh["timestamp"] = pd.to_datetime(df_hh["timestamp"])
        df_hh = df_hh.sort_values("timestamp")
        market1_price_hh = dict(zip(df_hh["timestamp"].dt.strftime("%Y-%m-%d %H:%M"), df_hh["price"]))

        # Get hourly prices for Market 1 if available
        df_hh_hourly = df_hh[df_hh["timestamp"].dt.minute == 0]
        market1_price_h = dict(zip(df_hh_hourly["timestamp"].dt.strftime("%Y-%m-%d %H:%M"), df_hh_hourly["price"]))

        # Read Market 2 (hourly)
        df_h = pd.read_excel(self.market_data, sheet_name="Hourly data")
        df_h["timestamp"] = pd.to_datetime(df_h["timestamp"])
        df_h = df_h.sort_values("timestamp")
        market2_hourly = dict(zip(df_h["timestamp"].dt.strftime("%Y-%m-%d %H:%M"), df_h["price"]))

        # Build Market 2 half-hourly prices aligned to Market 1 timepoints
        time_points = sorted(market1_price_hh.keys())
        market2_price_hh = {}
        for ts_str in time_points:
            ts = pd.to_datetime(ts_str)
            hour_str = ts.replace(minute=0).strftime("%Y-%m-%d %H:%M")
            if ts.minute == 0:
                # Exact hour, use Market 2 price if available
                price = market2_hourly.get(hour_str)
            else:
                # Half-hour, use previous hour's price
                price = market2_hourly.get(hour_str)
            if price is None:
                raise ValueError(f"Missing Market 2 price for hour {hour_str}")
            market2_price_hh[ts_str] = price

        return MarketSeries(
            market1_price_hh=market1_price_hh,
            market1_price_h=market1_price_h,
            market2_price_hh=market2_price_hh,
            time_points=time_points
        )

    def _extract_market_series_2(self):
        # -------- Market 1 half hourly from sheet "Half-hourly data" --------
        df_m1_hh = pd.read_excel(self.market_data, sheet_name="Half-hourly data",
                                 usecols=["Unnamed: 0", "Market 1 Price [£/MWh]"])
        df_m1_hh.columns = ["timestamp", "price"]
        df_m1_hh["timestamp"] = pd.to_datetime(df_m1_hh["timestamp"], errors="coerce")
        df_m1_hh = df_m1_hh.dropna(subset=["timestamp"]).copy()
        df_m1_hh["timestamp"] = df_m1_hh["timestamp"].map(round_to_half_hour)
        df_m1_hh = df_m1_hh.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
        m1_hh_raw = dict(zip(df_m1_hh["timestamp"], df_m1_hh["price"].astype(float)))

        # -------- Market 2 hourly from sheet "Hourly data", then expand to half hourly --------
        df_m2_h = pd.read_excel(self.market_data, sheet_name="Hourly data",
                                usecols=["Unnamed: 0", "Market 2 Price [£/MWh]"])
        df_m2_h.columns = ["timestamp", "price"]
        df_m2_h["timestamp"] = pd.to_datetime(df_m2_h["timestamp"], errors="coerce")
        if df_m2_h["timestamp"].isna().any():
            bad = df_m2_h[df_m2_h["timestamp"].isna()]
            raise ValueError(f"Invalid or missing timestamps in 'Hourly data':\n{bad}")

        df_m2_h["timestamp"] = df_m2_h["timestamp"].map(round_to_half_hour)
        df_m2_h = df_m2_h.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
        m2_h = dict(zip(df_m2_h["timestamp"], df_m2_h["price"].astype(float)))

        # expand Market 2 hourly → half hourly at t and t+30
        m2_hh_raw: Dict[pd.Timestamp, float] = {}
        for t, p in m2_h.items():
            t = pd.to_datetime(t)
            m2_hh_raw[t] = p
            m2_hh_raw[t + pd.Timedelta(minutes=30)] = p

        # -------- build canonical indices and enforce equality --------
        keys_m1_hh = set(m1_hh_raw.keys())
        keys_m2_hh = set(m2_hh_raw.keys())

        # require exact match; if not, show small diffs and raise
        if keys_m1_hh != keys_m2_hh:
            only_m1 = sorted(k for k in keys_m1_hh - keys_m2_hh)[:10]
            only_m2 = sorted(k for k in keys_m2_hh - keys_m1_hh)[:10]
            raise ValueError(
                "Half hourly timestamp mismatch between Market 1 and Market 2.\n"
                f"Only in Market 1 (sample): {[t.strftime('%Y-%m-%d %H:%M') for t in only_m1]}\n"
                f"Only in Market 2 (sample): {[t.strftime('%Y-%m-%d %H:%M') for t in only_m2]}"
            )

        canon_hh = sorted(keys_m1_hh)
        # build hourly canonical index from the half hourly one
        canon_h = [t for t in canon_hh if t.minute == 0]

        # -------- rebuild aligned dicts on canonical indices --------
        market1_price_hh = {t.strftime("%Y-%m-%d %H:%M"): float(m1_hh_raw[t]) for t in canon_hh}
        market2_price_hh = {t.strftime("%Y-%m-%d %H:%M"): float(m2_hh_raw[t]) for t in canon_hh}

        market1_price_h = {t.strftime("%Y-%m-%d %H:%M"): float(m1_hh_raw[t]) for t in canon_h}
        market2_price_h = {t.strftime("%Y-%m-%d %H:%M"): float(m2_hh_raw[t]) for t in canon_h}

        time_points = [t.strftime("%Y-%m-%d %H:%M") for t in canon_hh]

        return MarketSeries(
            market1_price_hh=market1_price_hh,
            market1_price_h=market1_price_h,
            market2_price_hh=market2_price_hh,
            time_points=time_points
        )

    @staticmethod
    def round_to_half_hour(ts: pd.Timestamp) -> pd.Timestamp:
        """
        It is possible that input timestamps are not exactly on the half-hour.
        This function rounds them to the nearest half-hour (:00 or :30) to ensure that data of two markets is aligned.

        """
        ts = pd.to_datetime(ts)
        minute = ts.minute

        if minute < 15:
            # closer to :00
            return ts.replace(minute=0, second=0, microsecond=0)
        elif minute < 45:
            # closer to :30
            return ts.replace(minute=30, second=0, microsecond=0)
        else:
            # closer to next hour :00
            ts_next = ts + pd.Timedelta(hours=1)
            return ts_next.replace(minute=0, second=0, microsecond=0)