"""
Sample unit test for the PreProcessor class.
"""
import unittest
from pathlib import Path
from batterytradeoptimiser.optimiser.pre_processing import PreProcessor, BatteryProperties, MarketSeries

class TestPreProcessor(unittest.TestCase):
    def setUp(self):
        # Update these paths to point to your sample test Excel files
        self.market_data_path = Path(r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\BatteryProperties.xlsx")
        self.battery_data_path = Path(r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\MarketData.xlsx")

    def test_preprocessor_run(self):
        preprocessor = PreProcessor(market_data=self.market_data_path, battery_data=self.battery_data_path)
        processed_input = preprocessor.run()

        # Test battery properties extraction
        self.assertIsInstance(processed_input.battery_properties, BatteryProperties)
        bp = processed_input.battery_properties
        self.assertGreater(bp.capacity_mwh, 0)

        # Test market series extraction
        self.assertIsInstance(processed_input.market_series, MarketSeries)
        ms = processed_input.market_series
        self.assertIsInstance(ms.market1_price_hh, dict)


        # Check that time_points are sorted strings
        self.assertTrue(all(isinstance(tp, str) for tp in ms.time_points))
        self.assertEqual(ms.time_points, sorted(ms.time_points))

if __name__ == "__main__":
    unittest.main()
