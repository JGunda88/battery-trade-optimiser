from pathlib import Path
from batterytradeoptimiser.optimiser.pre_processing import PreProcessor

# Update these paths to match your sample files
market_data_path = Path(r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\MarketData.xlsx")
battery_data_path = Path(r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\BatteryProperties.xlsx")

def test_preprocessor():
    pre = PreProcessor(market_data=market_data_path, battery_data=battery_data_path)
    processed = pre.run()
    print("Battery Properties:")
    print(processed.battery_properties)
    print("\n Market Series:")
    print("Market 1 (half-hourly):", list(processed.market_series.market1_price_hh.items())[:3], "...")
    print("Market 2 (hourly):", list(processed.market_series.market2_price_h.items())[:3], "...")
    print("Market 2 (half-hourly):", list(processed.market_series.market2_price_hh.items())[:3], "...")
    print("Time points:", processed.market_series.time_points[:3], "...")

if __name__ == "__main__":
    test_preprocessor()
