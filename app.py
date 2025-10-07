"""
A FastAPI application to optimise battery charging and discharging profiles across two market segments.
It exposes a single POST endpoint `/optimise_battery`. The endpoint consumes a JSON payload containing paths to
input Excel files and an output path.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import time
from batterytradeoptimiser.runner import Runner
from utils.custom_excpetions import InputFileMissing, InvalidFileType, OutputPathError
from batterytradeoptimiser.optimiser.settings import Settings

app = FastAPI(title="Battery Trade Optimiser API", version="0.1.0")

class OptimiseBatteryRequest(BaseModel):
    """
    Request model for the /optimise_battery endpoint.
    It includes paths to the market data Excel file, battery properties Excel file, and the output file path.
    """
    market_excel_path: str = Field(..., description="Market data Excel file path")
    battery_excel_path: str = Field(..., description="Battery properties Excel file path")
    results_output_path: str = Field(..., description="Output file path for results")

class OptimiseBatteryResponse(BaseModel):
    """
    Response model for the /optimise_battery endpoint.
    It includes the status of the job, a message, outputs from the optimisation, and optional details.
    """
    job_status: str
    objective_gbp: float | None = None
    messages: list[str] | None = None
    outputs: dict = Field(..., description="Dictionary containing output file paths")
    job_serving_time: float | None = Field(None, description="Time taken to serve the job in seconds")

@app.post("/optimise_battery", response_model=OptimiseBatteryResponse)
def optimise_battery(req: OptimiseBatteryRequest):
    """
    Endpoint to optimise battery charging and discharging profiles.
    :param req: OptimiseBatteryRequest
    :return: OptimiseBatteryResponse
    """
    application_start_time = time.time()
    try:
        result = Runner(req.market_excel_path, req.battery_excel_path, req.results_output_path).run()
        return OptimiseBatteryResponse(
            job_status=result["job_status"],
            objective_gbp=result.get("objective_gbp"),
            messages=result.get("messages"),
            outputs=result["outputs"],
            job_serving_time=round(time.time() - application_start_time, Settings.decimal_places)
        )
    except (InputFileMissing, InvalidFileType) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OutputPathError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000,reload=True)