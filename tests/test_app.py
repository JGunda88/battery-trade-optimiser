import requests
import json
url = "http://127.0.0.1:8000/optimise_battery"
payload = {
    "market_excel_path": r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\MarketData.xlsx",
    "battery_excel_path": r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\BatteryProperties.xlsx",
    "results_output_path": r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\results.xlsx"
}

response = requests.post(url, json=payload)
print("Status code:", response.status_code)
print("Response JSON:", response.json())