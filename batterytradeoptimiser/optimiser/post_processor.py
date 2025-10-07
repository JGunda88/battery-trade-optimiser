"""
This module contains the PostProcessor class that processes the optimiser solution
and writes the results to an Excel file. It also prepares a response dictionary that is consumed by the API.
"""
from dataclasses import asdict
from pathlib import Path
import pandas as pd
from batterytradeoptimiser.optimiser.settings import Settings

from batterytradeoptimiser.optimiser.pulp_modeller import OptimiserSolution


class PostProcessor:
    def __init__(self, solution: OptimiserSolution, results_path: str | Path):
        self.solution = solution
        self.results_path = Path(results_path)

    def run(self) -> dict:
        """
        Main method that exposes the post-processor functionality.
        Write optimiser solution to Excel — all time series in one sheet.
        :return: dict containing job status, objective value, messages, and output paths
        """
        sol_dict = asdict(self.solution)

        # Extract only the time series dicts (ignore scalars)
        series_dicts = {k: v for k, v in sol_dict.items() if isinstance(v, dict)}

        # Convert each dict into a DataFrame column (aligning timestamps)
        df = None
        for key, value in series_dicts.items():
            col = pd.DataFrame(list(value.items()), columns=["timestamp", key])
            if df is None:
                df = col
            else:
                df = pd.merge(df, col, on="timestamp", how="outer")

        # Sort timestamps for neatness
        df = df.sort_values("timestamp")

        # Write Excel File: Summary + all time series side by side
        with pd.ExcelWriter(self.results_path, engine="openpyxl") as writer:
            # Summary sheet
            pd.DataFrame({
                "Field": ["status", "objective"],
                "Value": [sol_dict["status"], sol_dict["objective"]],
            }).to_excel(writer, sheet_name="Summary", index=False)

            # Single sheet with all aligned time series
            df.to_excel(writer, sheet_name="TimeSeries", index=False)


        # prepare and return response as dict
        solver_status = self.solution.status
        job_status = "SUCCESS" if str(solver_status).lower() in ["optimal", "feasible"] else "FAILED"
        objective_value = round(float(self.solution.objective), Settings.decimal_places)
        messages = [f"solver used: {str(Settings.solver).upper()}",
                    f"solver status: {solver_status}",
                    f"optimiser run time (s): {round(self.solution.optimiser_run_time, Settings.decimal_places)}"]
        return {
            "job_status": job_status,
            "objective_gbp":objective_value,
            "messages": messages,
            "outputs": {"results_output_path": str(self.results_path)},
        }
