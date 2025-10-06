# postprocessing.py
from modelling.base import Solution
import pandas as pd

class PostProcessor:
    def __init__(self, solution: Solution, results_path):
        self.solution = solution
        self.results_path = results_path

    def run(self) -> dict:
        # write CSV
        df = pd.DataFrame(self.solution.series)
        df.to_csv(self.results_path, index=False)

        # build API payload
        return {
            "objective_gbp": self.solution.objective_gbp or 0.0,
            "messages": [f"solve status: {self.solution.status}"],
            "outputs": {"results_output_path": str(self.results_path)},
        }
