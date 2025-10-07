import pulp
from dataclasses import dataclass
import time
from batterytradeoptimiser.optimiser.settings import Settings

@dataclass
class OptimiserSolution:
    """
    Dataclass to hold the optimiser solution details. Can be extended as needed.
    """
    status: str # e.g., "Optimal", "Infeasible"
    objective: float   # Objective value of the solved model - profit in GBP
    charge_power_m1: dict[str, float] # Charge power in MW for Market 1 (half-hourly)
    discharge_power_m1: dict[str, float] # Discharge power in MW for Market 1 (half-hourly)
    charge_power_m2: dict[str, float]  # Charge power in MW for Market 2 (hourly)
    discharge_power_m2: dict[str, float] # Discharge power in MW for Market 2 (hourly)
    state_of_charge: dict[str, float] # State of Charge in MWh at each time point
    is_discharging: dict[str, int] # Binary indicator if discharging (1) or not (0) at each time point
    optimiser_run_time: float | None = None # Time taken to solve the model in seconds

class PulpModeller(object):
    def __init__(self, processed_data):
        self.optimiser_run_time = None # Time taken to solve the model
        self.processed_data = processed_data

    def solve_model(self) -> OptimiserSolution:
        """
        Main method to create, solve the model, and extract the solution.
        This is the only method exposed to the outside.
        :return:
        """
        # Implement model solving logic here
        start = time.perf_counter()
        self._create_model()
        self._integrate_variables()
        self._integrate_constraints()
        self._integrate_objective()
        solver = self._get_solver()
        self.m.solve(solver)
        self._write_lp_and_iis()
        self.optimiser_run_time = time.perf_counter() - start
        return self._extract_solution()

    def _create_model(self):
        """
        Create an empty PuLP model. Later variables, constraints, and objective will be added to this model.
        :return:
        """
        self.m = pulp.LpProblem("BatteryBESS_MILP_Binary", pulp.LpMaximize)

    def _integrate_variables(self):
        """
        Integrate decision variables into the model.
        Following variables are created.
        charge_power_m1[t] in [0, max_charge_mw] # Market 1
        discharge_power_m1[t] in [0, max_discharge_mw] # Market 1
        charge_power_m1[t] [0, max_charge_mw] # Market 2
        discharge_power_m1[t] in [0, max_discharge_mw] # Market 2
        state_of_charge[t] in [0, max_energy_mwh] # state of charge at end of step t. state_of_charge[0] = Battery_initial_soc
        is_discharging[t] in {0,1} # mode: 0 charge/idle, 1 discharge/idle
        :return:
        """
        ms = self.processed_data.market_series
        bp = self.processed_data.battery_properties
        time_points = ms.time_points
        # Charge/discharge power for Market 1 (half-hourly)
        self.charge_power_m1 = pulp.LpVariable.dicts(
            "charge_power_m1", time_points, lowBound=0, upBound=bp.max_charge_mw, cat="Continuous"
        )
        self.discharge_power_m1 = pulp.LpVariable.dicts(
            "discharge_power_m1", time_points, lowBound=0, upBound=bp.max_discharge_mw, cat="Continuous"
        )

        # Charge/discharge power for Market 2 (half-hourly)
        self.charge_power_m2 = pulp.LpVariable.dicts(
            "charge_power_m2", time_points, lowBound=0, upBound=bp.max_charge_mw, cat="Continuous"
        )
        self.discharge_power_m2 = pulp.LpVariable.dicts(
            "discharge_power_m2", time_points, lowBound=0, upBound=bp.max_discharge_mw, cat="Continuous"
        )

        # State of charge (SoC) at each time point
        self.state_of_charge = pulp.LpVariable.dicts(
            "state_of_charge", time_points, lowBound=0, upBound=bp.capacity_mwh, cat="Continuous"
        )

        # set initial state of charge to full capacity
        self.m += self.state_of_charge[time_points[0]] == bp.initial_soc_mwh, "Initial_SoC_Constraint"

        # Binary variable for charge/discharge state
        self.is_discharging = pulp.LpVariable.dicts(
            "is_discharging", time_points, cat="Binary"
        )

    def _integrate_constraints(self):
        """
        Integrate constraints into the model.
        :return:
        """
        self._apply_limits_on_charging_discharging()
        self._apply_no_simultaneous_charge_discharge()
        self._apply_soc_update()
        self._apply_terminal_soc_constraint()
        self._apply_bounds_on_soc()
        self._apply_market2_consistency_constraints()

    def _apply_limits_on_charging_discharging(self):
        """
        Apply limits on charging and discharging power.
        :return:
        """
        ms = self.processed_data.market_series
        bp = self.processed_data.battery_properties
        time_points = ms.time_points

        for tp in time_points:
            # Total charging power limit
            self.m += (
                self.charge_power_m1[tp] + self.charge_power_m2[tp] <= bp.max_charge_mw,
                f"Max_Charge_Limit_{tp}"
            )
            # Total discharging power limit
            self.m += (
                self.discharge_power_m1[tp] + self.discharge_power_m2[tp] <= bp.max_discharge_mw,
                f"Max_Discharge_Limit_{tp}"
            )

    def _apply_no_simultaneous_charge_discharge(self):
        """
        Apply no simultaneous charge and discharge constraints.
        :return:
        """
        ms = self.processed_data.market_series
        bp = self.processed_data.battery_properties
        time_points = ms.time_points
        M = bp.max_discharge_mw + bp.max_charge_mw  # Big-M

        for tp in time_points:
            self.m += (
                self.discharge_power_m1[tp] + self.discharge_power_m2[tp] <= M * self.is_discharging[tp],
                f"No_Simultaneous_Discharge_{tp}"
            )
            self.m += (
                self.charge_power_m1[tp] + self.charge_power_m2[tp] <= M * (1 - self.is_discharging[tp]),
                f"No_Simultaneous_Charge_{tp}"
            )

    def _apply_soc_update(self):
        """
        Apply state of charge update constraints.
        :return:
        """
        ms = self.processed_data.market_series
        bp = self.processed_data.battery_properties
        time_points = ms.time_points

        for idx, t in enumerate(time_points):
            if idx > 0:
                t_prev = time_points[idx - 1]
                self.m += (
                    self.state_of_charge[t] ==
                    self.state_of_charge[t_prev]
                    + (self.charge_power_m1[t] + self.charge_power_m2[t]) * bp.charging_efficiency*Settings.step_size
                    - (self.discharge_power_m1[t] + self.discharge_power_m2[t])*Settings.step_size / bp.discharging_efficiency,
                    f"SoC_Update_{t}"
                )

    def _apply_terminal_soc_constraint(self):
        """
        Apply terminal state of charge constraint.
        :return:
        """
        ms = self.processed_data.market_series
        bp = self.processed_data.battery_properties
        time_points = ms.time_points

        self.m += (
            self.state_of_charge[time_points[-1]] == bp.initial_soc_mwh,
            "Terminal_SoC"
        )

    def _apply_terminal_soc_constraint_flexible(self, target_soc: float):
        """
        Apply terminal state of charge constraint with flexibility.
        :param target_soc: Target state of charge at the end of the time horizon.
        :return:
        """
        ms = self.processed_data.market_series
        bp = self.processed_data.battery_properties
        time_points = ms.time_points

        # Allow deviation from target_soc with a penalty in the objective function
        deviation = pulp.LpVariable("soc_deviation", lowBound=0, cat="Continuous")
        self.m += (
            self.state_of_charge[time_points[-1]] >= target_soc - deviation,
            "Terminal_SoC_Lower_Bound"
        )
        self.m += (
            self.state_of_charge[time_points[-1]] <= target_soc + deviation,
            "Terminal_SoC_Upper_Bound"
        )
        # Add penalty for deviation in the objective function
        penalty_per_mwh = Settings.terminal_soc_penalty_per_mwh  # Define this in settings
        self.m += penalty_per_mwh * deviation, "Terminal_SoC_Deviation_Penalty"

    def _apply_bounds_on_soc(self):
        """
        Apply bounds on state of charge.
        :return:
        """
        ms = self.processed_data.market_series
        bp = self.processed_data.battery_properties
        time_points = ms.time_points

        for tp in time_points:
            self.m += (
                self.state_of_charge[tp] >= 0,
                f"SoC_Lower_Bound_{tp}"
            )
            self.m += (
                self.state_of_charge[tp] <= bp.capacity_mwh,
                f"SoC_Upper_Bound_{tp}"
            )

    def _apply_market2_consistency_constraints(self):
        """
        Apply Market 2 consistency constraints.
        Ensures that the charging/discharging power allocated to Market 2 remains constant within each hour.
        C7: Market 2 Charge Consistency Constraint: charge_power_m2[t] == charge_power_m2[t+1]
        C8: Market 2 Discharge Consistency Constraint: discharge_power_m2[t] == discharge_power_m2[t+1]
        :return:
        """
        ms = self.processed_data.market_series
        time_points = ms.time_points

        for i in range(0, len(time_points) - 1, 2):
            tp = time_points[i]
            tp_next = time_points[i + 1]
            self.m += (
                self.charge_power_m2[tp] == self.charge_power_m2[tp_next],
                f"Market2_Charge_Consistency_{tp}"
            )
            self.m += (
                self.discharge_power_m2[tp] == self.discharge_power_m2[tp_next],
                f"Market2_Discharge_Consistency_{tp}"
            )

    def _integrate_objective(self):
        """
        Sets the objective function:
        Maximize total profit = sum over t of (
            discharge_power_m1[t] * market1_price_hh[t]*0.5
            - charge_power_m1[t] * market1_price_hh[t]*0.5
            + discharge_power_m2[t] * market2_price_hh[t]
            - charge_power_m2[t] * market2_price_hh[t]
        )
        """
        ms = self.processed_data.market_series
        time_points = ms.time_points

        profit_terms = []
        for t in time_points:
            profit_terms.append(
                self.discharge_power_m1[t] * ms.market1_price_hh[t]*Settings.step_size
                - self.charge_power_m1[t] * ms.market1_price_hh[t]*Settings.step_size
                + self.discharge_power_m2[t] * ms.market2_price_hh[t]
                - self.charge_power_m2[t] * ms.market2_price_hh[t]
            )
        self.m += pulp.lpSum(profit_terms), "Total_Profit"

    def _get_solver(self):
        """
        Returns the solver instance based on the solver_name.
        Supported: 'cbc', 'gurobi', 'cplex'
        """
        solver_name = Settings.solver.lower()
        time_budget = Settings.time_budget
        threads = Settings.threads
        presolve = Settings.presolve
        gap = Settings.mip_gap
        solver_path = r"C:\gurobi1201\win64\bin\gurobi_cl.exe"  # Example path to Gurobi executable
        if solver_name == "gurobi":
            return pulp.GUROBI_CMD(msg=True, timeLimit=time_budget, gapRel=gap, threads=threads, path=solver_path)
        elif solver_name == "cplex":
            return pulp.CPLEX_CMD(msg=True, timeLimit=time_budget, gapRel=gap, threads=threads)
        else:  # Default to CBC
            return pulp.PULP_CBC_CMD(msg=True, timeLimit=time_budget, gapRel=gap, threads=threads,
                                     presolve=presolve)

    def _write_lp_and_iis(self):
        """
        Writes the LP file and, if infeasible, the IIS file for debugging.
        """
        self.m.writeLP(Settings.lp_filename)
        # Write IIS file if model is infeasible and solver supports it
        if pulp.LpStatus[self.m.status] == "Infeasible":
            try:
                self.m.writeMPS("model.mps")
                pulp.findIIS(self.m, Settings.iis_filename)
            except Exception:
                pass  # IIS extraction may not be supported by all solvers

    def _extract_solution(self):
        """
        Extracts the solution from the solved model and returns an OptimiserSolution dataclass.
        :return:
        """
        ms = self.processed_data.market_series
        time_points = ms.time_points

        status = pulp.LpStatus[self.m.status]
        objective = pulp.value(self.m.objective)

        def extract_var_dict(var_dict):
            return {t: pulp.value(var_dict[t]) for t in time_points}

        return OptimiserSolution(
            status=status,
            objective=objective,
            charge_power_m1=extract_var_dict(self.charge_power_m1),
            discharge_power_m1=extract_var_dict(self.discharge_power_m1),
            charge_power_m2=extract_var_dict(self.charge_power_m2),
            discharge_power_m2=extract_var_dict(self.discharge_power_m2),
            state_of_charge=extract_var_dict(self.state_of_charge),
            is_discharging={t: int(round(pulp.value(self.is_discharging[t]))) for t in time_points},
            optimiser_run_time=self.optimiser_run_time
        )