"""
Settings for the battery trade optimiser.
"""
class Settings:
    step_size = 0.5  # Step size 0.5 hours (30 minutes)
    solver = "cbc"  # Solver to use: "cbc" or "pulp_default"
    time_budget = 60  # Time limit for solver in seconds, None for no limit
    threads = 1  # Number of threads for solver, if supported
    mip_gap = 0.01  # MIP gap for solver, if supported
    presolve = True  # Whether to use presolve in solver, if supported
    terminal_soc_penalty_per_mwh = 100000.0  # Penalty for terminal state of charge in $/MWh