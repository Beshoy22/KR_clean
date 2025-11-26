# DPLL Performance Comparison: Non-Consecutive Sudoku

**Research Question:** Empirical Analysis of DPLL Optimization Techniques for Highly-Constrained Combinatorial Problems: A Case Study on Non-Consecutive Sudoku

## Overview

This repository contains a comprehensive experimental framework for comparing four DPLL solver variants on non-consecutive Sudoku puzzles of varying sizes (9×9, 16×16, 25×25).

### DPLL Variants

1. **BaseDPLL**: Naive implementation with basic unit propagation and simple data structures
2. **WatchedLiteralsDPLL**: 2-watched literal scheme for efficient unit propagation
3. **PreprocessingDPLL**: Heavy preprocessing (unit propagation, pure literal elimination, subsumption, BVE)
4. **CombinedDPLL**: Best of all worlds (preprocessing + watched literals + phase saving)

## Experimental Design

### Dataset
- **9×9 puzzles**: 20 puzzles (10 SAT, 10 UNSAT)
- **16×16 puzzles**: 10 puzzles (5 SAT, 5 UNSAT)
- **25×25 puzzles**: 4 puzzles (2 SAT, 2 UNSAT)
- **Total**: 34 puzzles

### Configuration
- **Repetitions**: 3 runs per puzzle-variant combination
- **Total runs**: 34 puzzles × 4 variants × 3 reps = **408 experiments**
- **Parallelization**: 128 threads
- **Timeouts**:
  - 9×9: 5 minutes (300s)
  - 16×16: 10 minutes (600s)
  - 25×25: 15 minutes (900s)

### Metrics Collected
- Wall-clock time
- Number of decisions
- Number of backtracks
- Number of unit propagations
- Number of conflicts
- Peak memory usage (MB)
- Success rate (within timeout)
- Correctness (matches expected SAT/UNSAT)

## Installation

### Prerequisites
- Python 3.8+
- 128 CPU cores (or adjust `--threads` parameter)

### Setup
```bash
# Clone repository
git clone <repository-url>
cd KR_clean

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Run Experiments

```bash
# Full experiment with default settings (128 threads, 3 repetitions)
python experiment_runner.py

# Custom configuration
python experiment_runner.py \
    --threads 64 \
    --repetitions 5 \
    --timeout-9x9 600 \
    --timeout-16x16 1200 \
    --timeout-25x25 1800

# Test specific variants only
python experiment_runner.py --variants base watched

# Custom puzzle and results directories
python experiment_runner.py \
    --puzzle-dir puzzles \
    --results-dir my_results
```

**Command-line Arguments:**
- `--puzzle-dir`: Directory containing puzzle files (default: `puzzles`)
- `--results-dir`: Output directory for results (default: `results`)
- `--threads`: Number of parallel threads (default: `128`)
- `--repetitions`: Number of repetitions per experiment (default: `3`)
- `--variants`: DPLL variants to test (default: `base watched preprocessing combined`)
- `--timeout-9x9`: Timeout for 9×9 puzzles in seconds (default: `300`)
- `--timeout-16x16`: Timeout for 16×16 puzzles in seconds (default: `600`)
- `--timeout-25x25`: Timeout for 25×25 puzzles in seconds (default: `900`)

### 2. Resume Interrupted Experiments

The experiment runner automatically detects completed runs and resumes from where it left off:

```bash
# Simply re-run the same command
python experiment_runner.py
```

The script reads `results/raw_results.csv` and skips already completed experiments.

### 3. Analyze Results

```bash
# Run full statistical analysis
python statistical_analysis.py

# Custom input/output paths
python statistical_analysis.py \
    --results results/raw_results.csv \
    --output analysis
```

**Analysis Outputs:**
- `analysis/summary_statistics.txt`: Descriptive statistics
- `analysis/statistical_tests.csv`: P-values and effect sizes
- `analysis/boxplots_solve_time.png`: Box plots by puzzle size
- `analysis/scaling_curves.png`: Scaling behavior across sizes
- `analysis/metrics_comparison.png`: Comparison of decisions, backtracks, propagations
- `analysis/table_summary.tex`: LaTeX table for paper
- `analysis/table_speedup.tex`: Speedup factors table

## Output Files

### During Experiment
- `results/raw_results.csv`: Raw experimental data (updated in real-time)
- `results/experiment.log`: Detailed execution log

### After Analysis
- Summary statistics
- Statistical significance tests (Friedman, Wilcoxon with Bonferroni correction)
- Visualizations (PNG, 300 DPI)
- LaTeX tables (ready for Springer Nature format)

## File Structure

```
KR_clean/
├── puzzles/                      # Puzzle files
│   ├── !puzzles_manifest.csv     # Puzzle metadata
│   ├── puzzle1.txt                # 9×9 SAT puzzles
│   ├── ...
│   └── puzzle34.txt               # 25×25 UNSAT puzzles
├── encoder.py                     # CNF encoding for non-consecutive Sudoku
├── solver.py                      # Solver interface (stub)
├── dpll_variants.py               # Four DPLL implementations
├── experiment_runner.py           # Parallel experiment orchestration
├── statistical_analysis.py        # Statistical tests and visualizations
├── requirements.txt               # Python dependencies
└── README_EXPERIMENT.md           # This file
```

## Research Paper Structure

Based on results, the paper will follow this structure:

1. **Abstract** (200 words)
2. **Introduction** (2 pages): Motivation, research questions, contributions
3. **Background & Related Work** (1.5 pages): DPLL, SAT optimizations, Sudoku-as-SAT
4. **Methodology** (2 pages):
   - DPLL variants description
   - Non-consecutive Sudoku encoding
   - Experimental setup
5. **Results** (2.5 pages):
   - Performance comparison
   - Scaling analysis
   - Statistical significance
   - Efficiency metrics
6. **Discussion** (1.5 pages): Interpretation, practical recommendations
7. **Conclusion & Future Work** (0.5 pages)

## Key Research Questions

1. **Primary**: Which optimization provides the best performance-to-complexity tradeoff?
2. **Secondary**: How do different DPLL optimizations scale with problem size (9×9 vs 16×16 vs 25×25)?
3. **Tertiary**: How do optimizations interact? (Does combined beat individual optimizations?)

## Expected Findings

### Hypotheses
- **Watched literals**: 10-100× speedup due to reduced clause checks
- **Preprocessing**: Significant problem space reduction, especially for highly-constrained instances
- **Combined**: Synergistic effects, best overall performance
- **Scaling**: Watched literals should scale much better to 16×16 and 25×25

## Statistical Methodology

- **Friedman test**: Overall significance across all variants (non-parametric repeated measures)
- **Wilcoxon signed-rank tests**: Pairwise comparisons with Bonferroni correction (α = 0.05/6 = 0.0083)
- **Effect sizes**: Speedup ratios, median differences
- **Survival analysis**: Handling timeouts as censored data

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **Memory issues**: Reduce number of threads
   ```bash
   python experiment_runner.py --threads 64
   ```

3. **Timeout too short**: Increase timeout limits
   ```bash
   python experiment_runner.py --timeout-25x25 3600
   ```

4. **Resume not working**: Check CSV file integrity
   ```bash
   head -n 5 results/raw_results.csv
   ```

## Performance Tips

- Use SSD storage for faster CSV writes
- On NUMA systems, consider `numactl` for better memory locality
- Monitor with `htop` to ensure full CPU utilization
- For 25×25 puzzles, consider increasing timeout if needed

## Citation

If you use this framework or data, please cite:

```bibtex
@article{yourname2024dpll,
  title={Empirical Analysis of DPLL Optimization Techniques for Highly-Constrained
         Combinatorial Problems: A Case Study on Non-Consecutive Sudoku},
  author={Your Name},
  journal={Conference/Journal Name},
  year={2024}
}
```

## License

[Your License Here]

## Contact

For questions or issues, please contact [Your Email] or open an issue on GitHub.

## Acknowledgments

- Non-consecutive Sudoku constraint encoding
- DPLL optimization techniques from SAT literature
- Statistical methodology guidance

---

**Note**: This is a research experiment framework. Results may vary based on hardware, system load, and random factors. Always run multiple repetitions for statistical validity.
