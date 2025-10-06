"""
A FastAPI application to optimise battery trading.
It exposes a single POST endpoint `/optimise_battery`. The endpoint consumes a JSON payload containing paths to
input Excel files and an output path.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from batterytradeoptimiser.runner import Runner
from utils.custom_excpetions import InputFileMissing, InvalidFileType, OutputPathError

app = FastAPI(title="Aurora Battery Service")

class OptimiseBatteryRequest(BaseModel):
    market_excel_path: str = Field(..., description="Market data Excel file path")
    battery_excel_path: str = Field(..., description="Battery properties Excel file path")
    results_output_path: str = Field(..., description="Output file path for results")

class OptimiseBatteryResponse(BaseModel):
    status: str
    message: str
    outputs: dict
    details: dict | None = None

@app.post("/optimise_battery", response_model=OptimiseBatteryResponse)
def optimise_battery(req: OptimiseBatteryRequest):
    try:
        result = Runner(req.market_excel_path, req.battery_excel_path, req.results_output_path).run()
        return OptimiseBatteryResponse(
            status="ok",
            message="Job completed",
            outputs=result["outputs"],
            details={"messages": result.get("messages", []), "objective_gbp": result.get("objective_gbp")}
        )
    except (InputFileMissing, InvalidFileType) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OutputPathError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000,)