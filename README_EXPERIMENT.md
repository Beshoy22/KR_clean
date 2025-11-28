# DPLL Optimization Experiments

## Installation

```bash
pip install -r requirements.txt
```

## Running Experiments

Run all 408 experiments (34 puzzles × 4 variants × 3 repetitions):

```bash
python experiment_runner.py --puzzles puzzles/ --output results/raw_results.csv --workers 128
```

**Parameters:**
- `--puzzles`: Directory containing DIMACS CNF puzzle files
- `--output`: Output CSV file path
- `--workers`: Number of parallel processes (default: 128)
- `--resume`: Resume from existing results file

**Timeouts:**
- 9×9 puzzles: 300 seconds
- 16×16 puzzles: 600 seconds
- 25×25 puzzles: 900 seconds

## Analyzing Results

Generate statistics, plots, and LaTeX tables:

```bash
python statistical_analysis.py --results results/raw_results.csv --output analysis/
```

**Outputs:**
- `summary_statistics.txt`: Descriptive statistics
- `statistical_tests.csv`: Friedman and Wilcoxon test results
- `boxplots_solve_time.png`: Performance visualization
- `scaling_curves.png`: Scaling behavior
- `table_summary.tex`: LaTeX table for paper

## Expected Runtime

With 128 CPUs: ~4-6 hours for complete experiment.
