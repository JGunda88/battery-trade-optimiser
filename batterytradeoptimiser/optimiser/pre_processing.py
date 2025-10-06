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