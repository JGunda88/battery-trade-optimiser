from pathlib import Path
from utils.check_io_files import FileChecker
from batterytradeoptimiser.optimiser.pre_processing import PreProcessor
from batterytradeoptimiser.optimiser.pulp_modeller import PulpModeller

class Runner(object):
    def __init__(self, market_excel_path: str, battery_excel_path: str, results_output_path: str):
        self._market_excel_path = market_excel_path
        self._battery_excel_path = battery_excel_path
        self._results_output_path = results_output_path
        # Will be set after validation
        self.market_path: Path | None = None
        self.battery_path: Path | None = None
        self.results_path: Path | None = None

    def run(self):
        """
        Main method that exposes the runner functionality.
        Validate input files and output path, then call the optimiser pipeline.
        Returns a result dict expected by the FastAPI response mapper.
        :return:
        """
        self._check_io_files()
        result = self._call_optimiser()
        return result

    def _check_io_files(self):
        """
        Validate input files and prepare output path.
        There is no point of running optimiser if the inputs are not valid or the output path cannot be prepared.
        :return:
        """
        self.market_path = FileChecker(self._market_excel_path).validate_excel_file()
        self.battery_path = FileChecker(self._battery_excel_path).validate_excel_file()
        self.results_path = FileChecker(self._results_output_path).prepare_output_path()

    def _call_optimiser(self) -> dict:
        """
        Placeholder for the real optimiser call.
        Replace this with: load data → optimise → write results.
        :return:
        """
        # pre-process input data
        processed_input = PreProcessor(market_data=self.market_path, battery_data=self.battery_path).run()
        solution = PulpModeller(processed_input).solve_model()
        # call the selected modeller to build and solve the problem
        # if settings.modeller = "PULP":
        #     solution = PulpModeller(processed_input).solve()
        # elif settings.modeller = "PYOMO":
        #     solution = PyomoModeller(processed_input).solve()
        # elif settings.modeller = "Gurobi":
        #     solution = GurobiModeller(processed_input).solve()

        # post-process the solution and write the results into REST response and excel file
        # PostProcessor(solution, self.results_path).run()









        return {
            "objective_gbp": 0.0,
            "messages": ["runner placeholder"],
            "outputs": {"results_output_path": str(self.results_path)}
        }



