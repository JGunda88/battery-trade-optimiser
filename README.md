# Battery Trade Optimiser
## Overview
Battery Trade Optimiser is a prototype optimisation service designed to determine optimal charging and 
discharging schedules for a Battery Energy Storage System across multiple electricity market segments with different 
settlement intervals.

The objective is to maximise trading value while respecting battery operational constraints such as state of charge 
limits, charge and discharge limits, and temporal consistency across markets.

## What this Project Demonstrates
- End to end optimisation workflow from raw data to decision outputs
- Handling of multiple market time resolutions (half-hourly and hourly)
- Structured separation of preprocessing, modelling, and post-processing
- Exposure of optimisation logic through an API service

## Problem Context
Battery operators often participate in multiple electricity markets simultaneously, where:

- Different markets operate at different time resolutions
- Prices vary across time and across markets
- Operational constraints must be strictly enforced

This results in a coupled optimisation problem involving:
- Time alignment across markets
- State of charge tracking over time
- Charge and discharge scheduling decisions
- Revenue maximisation under operational constraints

This project provides a simplified but representative implementation of such a problem.

## Project Overview
This project provides a complete pipeline for battery trading optimization, including:
- Data Pre-processing: Reads and processes input data from Excel files containing battery properties and market price series.
- Mathematical Optimization Model: Formulates and solves a MILP model using PuLP to determine optimal battery 
  charge/discharge profiles.
- Post-processing: Extracts optimisation results and writes outputs to Excel.
- API Interface: A FastAPI based REST interface exposes the optimisation workflow.
 
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
 
## Setup Instructions

1. Install Poetry (if not installed):

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone the repository and navigate into it:

```bash
git clone <repo-url>
cd batterytradeoptimiser
```

3. Install dependencies and create virtual environment:

```bash
poetry install
```

4. (Optional) Activate the virtual environment:

```bash
poetry shell
```

5. Run the application or scripts using:

```bash
poetry run python app.py
```

# Usage
1. Prepare input Excel files:
Market Data: Two sheets named "Half-hourly data" and "Hourly data" with timestamps and prices.
Battery Properties: A sheet named "Data" with parameters and values.
Sample input files are provided in the "sample_data" folder. 
Some scripts reference local file paths and solver configurations. These should be updated based on the target environment before execution.
2. Configure settings in optimiser/settings.py if required (e.g., solver choice, market horizon, etc).
3. Run the FastAPI server: 
    ```shell
    uvicorn app:app --host 127.0.0.1 --port 8000 --reload
    ```
4. Submit a POST request to /optimise_battery with JSON body:
    ```json
   {
     "market_excel_path": "path/to/market_data.xlsx",
     "battery_excel_path": "path/to/battery_properties.xlsx",
     "results_output_path": "path/to/output_results.xlsx"
   }
   ```   
5. Retrieve optimization results including objective value and output file

# Dependencies
Project dependencies are managed via poetry. To install dependencies, run:
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
Basic test scripts are included to validate preprocessing and optimisation behaviour. 
These can be used to test both API level execution and optimisation outputs.

# Contact
For questions or contributions, please contact Jagadeesh Gunda, jack.jagadeesh@gmail.com.
