import pulp
from dataclasses import dataclass

@dataclass
class OptimiserSolution:
    status: str
    objective: float
    charge_power_m1: dict[str, float]
    discharge_power_m1: dict[str, float]
    charge_power_m2: dict[str, float]
    discharge_power_m2: dict[str, float]
    state_of_charge: dict[str, float]
    is_discharging: dict[str, int]

class PulpModeller(object):
    def __init__(self, processed_data):
        self.processed_data = processed_data
        self.step_h = 0.5  # half-hourly steps

    def solve_model(self) -> OptimiserSolution:
        """
        Main method to create, solve the model, and extract the solution.
        :return:
        """
        # Implement model solving logic here
        self._create_model()
        self._integrate_variables()
        self._integrate_constraints()
        self._integrate_objective()
        solver = self._get_solver(solver_name="cbc", time_budget=300, gap=0.01, threads=2)
        self.m.solve(solver)
        self._write_lp_and_iis()
        return self._extract_solution()

    def _create_model(self):
        # Implement model creation logic here
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
        Add following constraints:
        C1: charge_power_m1 + charge_power_m2 <= bp.max_charge_mw
        C2: discharge_power_m1 + discharge_power_m2 <= bp.max_discharge_mw
        C3: state_of_charge[t] = state_of_charge[t-1] + (charge_power_m1[t] + charge_power_m2[t]) * charging_efficiency - (discharge_power_m1[t] + discharge_power_m2[t]) / discharging_efficiency
        C4: state_of_charge[t] in [0, bp.capacity_mwh]
        C5: No simultaneous charge and discharge:
            discharge_power_m1[t] + discharge_power_m2[t] <= M * y[t],
            charge_power_m1[t] + charge_power_m2[t] <= M * (1 - y[t]),

            where y[t] is a binary variable: y(t) = 1 if discharging, 0 if charging or idle
            M is a sufficiently large constant (e.g., max_discharge_mw)
        C6: Terminal condition on state_of_charge (e.g., equal to initial SoC)
        :return:
        """
        ms = self.processed_data.market_series
        bp = self.processed_data.battery_properties
        time_points = ms.time_points

        # Binary variable for charge/discharge state
        self.is_discharging = pulp.LpVariable.dicts(
            "is_discharging", time_points, cat="Binary"
        )
        M = bp.max_discharge_mw + bp.max_charge_mw  # Big-M

        for idx, t in enumerate(time_points):
            # C1: Total charging power limit
            self.m += (
                self.charge_power_m1[t] + self.charge_power_m2[t] <= bp.max_charge_mw,
                f"C1_Max_Charge_Limit_{t}"
            )
            # C2: Total discharging power limit
            self.m += (
                self.discharge_power_m1[t] + self.discharge_power_m2[t] <= bp.max_discharge_mw,
                f"C2_Max_Discharge_Limit_{t}"
            )
            # C3, C4: No simultaneous charge and discharge
            self.m += (
                self.discharge_power_m1[t] + self.discharge_power_m2[t] <= M * self.is_discharging[t],
                f"C3_No_Simultaneous_Discharge_{t}"
            )
            self.m += (
                self.charge_power_m1[t] + self.charge_power_m2[t] <= M * (1 - self.is_discharging[t]),
                f"C4_No_Simultaneous_Charge_{t}"
            )
            # C5: SoC update (skip t=0)
            if idx > 0:
                t_prev = time_points[idx - 1]
                self.m += (
                    self.state_of_charge[t] ==
                    self.state_of_charge[t_prev]
                    + (self.charge_power_m1[t] + self.charge_power_m2[t]) * bp.charging_efficiency*self.step_h
                    - (self.discharge_power_m1[t] + self.discharge_power_m2[t])*self.step_h / bp.discharging_efficiency,
                    f"C5_SoC_Update_{t}"
                )

        # C6: Terminal SoC equals initial SoC
        self.m += (
            self.state_of_charge[time_points[-1]] == bp.initial_soc_mwh,
            "C6_Terminal_SoC"
        )
        # C7: Market 2 Charge Consistency Constraint: charge_power_m2[t] == charge_power_m2[t+1]
        # C8: Market 2 Discharge Consistency Constraint: discharge_power_m2[t] == discharge_power_m2[t+1]
        # Ensures that the charging/discharging power allocated to Market 2 remains constant within each hour
        for i in range(0, len(time_points) - 1, 2):
            t = time_points[i]
            t_next = time_points[i + 1]
            self.m += (
                self.charge_power_m2[t] == self.charge_power_m2[t_next],
                f"C7_Market2_Charge_Consistency_{t}"
            )
            self.m += (
                self.discharge_power_m2[t] == self.discharge_power_m2[t_next],
                f"C8_Market2_Discharge_Consistency_{t}"
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
                self.discharge_power_m1[t] * ms.market1_price_hh[t]*self.step_h
                - self.charge_power_m1[t] * ms.market1_price_hh[t]*self.step_h
                + self.discharge_power_m2[t] * ms.market2_price_hh[t]
                - self.charge_power_m2[t] * ms.market2_price_hh[t]
            )
        self.m += pulp.lpSum(profit_terms), "Total_Profit"

    def _get_solver(self, solver_name="cbc", time_budget=300, gap=0.01, threads=2):
        """
        Returns the solver instance based on the solver_name.
        Supported: 'cbc', 'gurobi', 'cplex'
        """
        solver_name = solver_name.lower()
        if solver_name == "gurobi":
            return pulp.GUROBI_CMD(msg=True, timeLimit=time_budget, gapRel=gap, threads=threads)
        elif solver_name == "cplex":
            return pulp.CPLEX_CMD(msg=True, timeLimit=time_budget, gapRel=gap, threads=threads)
        else:  # Default to CBC
            return pulp.PULP_CBC_CMD(msg=True, timeLimit=time_budget, gapRel=gap, threads=threads)

    def _write_lp_and_iis(self, lp_filename="model.lp", iis_filename="model.ilp"):
        """
        Writes the LP file and, if infeasible, the IIS file for debugging.
        """
        self.m.writeLP(lp_filename)
        # Write IIS file if model is infeasible and solver supports it
        if pulp.LpStatus[self.m.status] == "Infeasible":
            try:
                self.m.writeMPS("model.mps")
                pulp.findIIS(self.m, iis_filename)
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
            is_discharging={t: int(round(pulp.value(self.is_discharging[t]))) for t in time_points}
        )