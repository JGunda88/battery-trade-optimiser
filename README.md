# Battery Trade Optimiser
Battery Trade Optimiser is a Python-based application designed to optimize the charging and discharging 
schedules of a battery energy storage system (BESS) across two market segments with different settlement intervals.
The goal is to maximize profit by optimally trading battery capacity in different markets while 
respecting battery operational constraints.  

> **Note that the project is still in its early stage, as it seems to have performance issues with larger datasets and 
> also issues with constraint modelling.**

## Project Overview
This project provides a complete pipeline for battery trading optimization, including:
- Data Pre-processing: Reads and processes input data from Excel files containing battery properties and 
  market price series.
- Mathematical Optimization Model: Formulates and solves a MILP model 
  using PuLP to determine optimal battery charge/discharge profiles.
- Post-processing: Extracts and writes the optimization results to Excel file.
- API Interface: A FastAPI-based REST API exposes the optimization functionality.
 
# Key Features
### Battery Properties Handling: 
Supports various battery parameters such as capacity, charge/discharge limits, 
efficiencies, lifetime, degradation, CAPEX, and OPEX. But all of these not used currently in the model.
###  Market Data Integration: 
Handles two market price series:
Market 1 prices at half-hourly intervals.
Market 2 prices at hourly intervals, extrapolated to half-hourly for alignment.
### Optimization Model:
- Maximizes profit by scheduling battery charge/discharge across both markets.
- Enforces operational constraints including no simultaneous charging and discharging, state-of-charge (SoC) limits, and market-specific consistency constraints.
- Supports solver selection (CBC, Gurobi, CPLEX) with configurable parameters.
- Extensible and Modular: Clean separation of concerns with data classes, pre-processing, modelling, post-processing, and API layers.
 
# Core Components
### 1. PreProcessor
- Reads battery properties and market price data from Excel files.
- Converts and cleans data, including efficiency conversions.
- Aligns timestamps to nearest half-hour for consistent time series.
- Outputs structured data classes for use in the optimization model.
### 2. PulpModeller
- Builds and solves the MILP optimization model using PuLP.
- Defines decision variables for charging/discharging power and SoC.
- Applies constraints for battery operation and market trading rules.
- Extracts and returns the solution with detailed time series and status.
### 3. PostProcessor
- Converts the optimization solution into pandas DataFrames.
- Writes results to Excel files with summary and time series sheets.
- Prepares response dictionaries for API consumption.
### 4. Runner
Orchestrates the full pipeline: input validation, pre-processing, optimization, and post-processing.
Returns structured results for API responses.
### 5. FastAPI Application
- Provides a REST API endpoint /optimise_battery to run the optimization.
- Accepts JSON payload with paths to input Excel files and output location.
- Returns job status, objective value, messages, and output file paths.
- Handles exceptions and returns appropriate HTTP error codes.
 
# Usage
1. Prepare input Excel files:
Market Data: Two sheets named "Half-hourly data" and "Hourly data" with timestamps and prices.
Battery Properties: A sheet named "Data" with parameters and values.
2. Run the FastAPI server: 
    ```shell
    uvicorn app:app --host 127.0.0.1 --port 8000 --reload
    ```
3. Submit a POST request to /optimise_battery with JSON body:
    ```json
   {
     "market_excel_path": "path/to/market_data.xlsx",
     "battery_excel_path": "path/to/battery_properties.xlsx",
     "results_output_path": "path/to/output_results.xlsx"
   }
   ```   
4. Receive optimization results including profit objective and output file lo

# Dependencies
Project dependecies are managed via poetry.  To install dependencies, run:
```shell
poetry install
```
Key dependencies include:
- Python 3.8+
- FastAPI
- Pydantic
- pandas
- PuLP
- openpyxl
- Optional: Gurobi or CPLEX solvers 
 
# Testing
At present no unit tests are provided.
But there is a test script "test_end_point.py" under tests folder to test the API endpoint with sample data files.
The user can use this script to test the functionality at API level or the Optimisation level.
 
 # Contact
For questions or contributions, please contact Jagadeesh Gunda, jack.jagadeesh@gmail.com.
