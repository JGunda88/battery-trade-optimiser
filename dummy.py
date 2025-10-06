# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path

app = FastAPI(title="Aurora Battery Service")

class OptimiseBatteryRequest(BaseModel):
    market_excel_path: str = Field(..., description="Path to the market data Excel file")
    battery_excel_path: str = Field(..., description="Path to the battery properties Excel file")
    results_output_path: str = Field(..., description="Path to write the results file")

class OptimiseBatteryResponse(BaseModel):
    status: str
    message: str
    inputs: dict
    outputs: dict

def _validate_input_files(market_path: Path, battery_path: Path):
    if not market_path.exists() or not market_path.is_file():
        raise HTTPException(status_code=400, detail=f"Market file not found: {market_path}")
    if not battery_path.exists() or not battery_path.is_file():
        raise HTTPException(status_code=400, detail=f"Battery file not found: {battery_path}")
    # Basic extension check for clarity only
    valid_ext = {".xls", ".xlsx"}
    if market_path.suffix.lower() not in valid_ext:
        raise HTTPException(status_code=400, detail="Market file must be an Excel file")
    if battery_path.suffix.lower() not in valid_ext:
        raise HTTPException(status_code=400, detail="Battery file must be an Excel file")

def _prepare_output_path(path: Path):
    # Create parent folder if needed
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot prepare output folder: {e}")

@app.post("/optimise_battery", response_model=OptimiseBatteryResponse)
def optimise_battery(req: OptimiseBatteryRequest):
    market_path = Path(req.market_excel_path).expanduser().resolve()
    battery_path = Path(req.battery_excel_path).expanduser().resolve()
    results_path = Path(req.results_output_path).expanduser().resolve()

    # 1) Validate inputs
    _validate_input_files(market_path, battery_path)
    _prepare_output_path(results_path)

    # 2) Placeholder for the next step
    # Here we will load data, run the optimiser, and write results
    # For now we just return a confirmed handshake so we can test the route
    # result = run_job(market_path, battery_path, results_path)  # to be added

    return OptimiseBatteryResponse(
        status="ok",
        message="Inputs validated and output location is ready. Optimiser call will be added next.",
        inputs={
            "market_excel_path": str(market_path),
            "battery_excel_path": str(battery_path),
        },
        outputs={
            "results_output_path": str(results_path)
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000,)