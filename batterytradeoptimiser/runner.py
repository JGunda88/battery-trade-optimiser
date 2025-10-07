from pathlib import Path
from utils.check_io_files import FileChecker
from batterytradeoptimiser.optimiser.pre_processing import PreProcessor
from batterytradeoptimiser.optimiser.pulp_modeller import PulpModeller
from batterytradeoptimiser.optimiser.post_processor import PostProcessor

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
        :return: dict containing the response for the FastAPI endpoint.
        """
        self._check_io_files()
        result = self._call_optimiser()
        return result

    def _check_io_files(self):
        """
        Validate input files and prepare output path.
        There is no point of running optimiser if the inputs are not valid or the output path cannot be prepared.
        :return: None
        """
        self.market_path = FileChecker(self._market_excel_path).validate_excel_file()
        self.battery_path = FileChecker(self._battery_excel_path).validate_excel_file()
        self.results_path = FileChecker(self._results_output_path).prepare_output_path()

    def _call_optimiser(self) -> dict:
        """
        Call the optimiser pipeline: pre-process input, solve model, post-process results.
        :return: dict containing the response for the FastAPI endpoint.
        """
        # pre-process input data
        processed_input = PreProcessor(market_data=self.market_path, battery_data=self.battery_path).run()
        # build and solve the optimisation model
        solution = PulpModeller(processed_input).solve_model()
        # post-process the solution and write the results into Excel file, and prepare a response dict for the app
        response = PostProcessor(solution, self.results_path).run()

        return response