"""
This module contains two methods to test the core functionality.
1) test_post_request_to_api(): Sends a POST request to the FastAPI endpoint and prints the response.
   For this test to work, the FastAPI server must be running (i.e. run app.py with uvicorn).
2) test_direct_call(): Directly calls the Runner class to test the core functionality without FastAPI.
"""

import requests
import json

# Configuration
URL = "http://127.0.0.1:8000/optimise_battery"
TIMEOUT = 120  # seconds

# Payload with paths to input and output files
payload = {
    "market_excel_path": r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\MarketData.xlsx",
    "battery_excel_path": r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\BatteryProperties.xlsx",
    "results_output_path": r"C:\Users\JGunda\Desktop\BatterTradeOptimiser\sample_data\results.xlsx"
}

def test_post_request_to_api():
    """
    Test sending a POST request to the FastAPI endpoint.
    :return:
    """
    try:
        print("Sending request to server...")
        response = requests.post(URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()  # Raise HTTPError for 4xx/5xx responses

        print("\n Success!")
        print("Status Code:", response.status_code)
        print("Response JSON:", json.dumps(response.json(), indent=2))

    except requests.exceptions.ConnectionError:
        print("\n Connection failed. Is the server running?")
        print("Make sure the server is started with: uvicorn your_app:app --reload")

    except requests.exceptions.Timeout:
        print("\n Request timed out after", TIMEOUT, "seconds")
        print("Check if the server is unresponsive or taking too long to process")

    except requests.exceptions.HTTPError as e:
        print("\n HTTP Error:", e)
        print("Server response:", response.text)

    except requests.exceptions.JSONDecodeError:
        print("\n Invalid JSON response received")
        print("Raw response:", response.text)

    except Exception as e:
        print("\n Unexpected error:", str(e))

def test_direct_call():
    """
    Test directly calling the Runner class without FastAPI.
    This bypasses the web server and tests the core functionality. Dev regression tests will be done using this style.
    :return:
    """
    # Directly call the Runner class without FastAPI
    from batterytradeoptimiser.runner import Runner
    runner = Runner(
        market_excel_path=payload["market_excel_path"],
        battery_excel_path=payload["battery_excel_path"],
        results_output_path=payload["results_output_path"]
    )
    result = runner.run()
    print("Result:", json.dumps(result, indent=2))

if __name__ == "__main__":
    """
    Choose how to call the test: via API or direct call.
    Uncomment the desired test function.
    """
    # test_post_request_to_api()
    test_direct_call()
