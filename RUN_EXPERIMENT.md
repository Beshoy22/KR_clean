# Quick Start Guide: Running the Full DPLL Experiment

## 🚀 TL;DR - Run the Full Experiment

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Run the full experiment with default settings
python experiment_runner.py

# This will run:
# - 34 puzzles × 4 variants × 3 repetitions = 408 total runs
# - Using 128 parallel threads
# - With timeouts: 5min (9×9), 10min (16×16), 15min (25×25)
# - Estimated total time: 2-4 hours
```

## 📊 What You'll Get

### During Execution
- **Real-time progress bar** showing current puzzle and status
- **Thread-safe logging** to `results/experiment.log`
- **Periodic CSV updates** to `results/raw_results.csv`
- **Resume capability** - can safely interrupt and restart

### After Completion
```
results/
├── raw_results.csv       # All 408 experiment results
└── experiment.log        # Detailed execution log
```

## 📈 Analyzing Results

After the experiment completes:

```bash
# Run full statistical analysis
python statistical_analysis.py

# This generates:
# - Summary statistics
# - Statistical significance tests (Friedman, Wilcoxon)
# - Box plots, scaling curves, metrics comparison
# - LaTeX tables for your paper
```

Output will be in `analysis/`:
```
analysis/
├── summary_statistics.txt
├── statistical_tests.csv
├── boxplots_solve_time.png
├── scaling_curves.png
├── metrics_comparison.png
├── table_summary.tex
└── table_speedup.tex
```

## 🎯 Expected Results

Based on the test run:

### 9×9 Puzzles
- **Base DPLL**: ~10-300s (some may timeout)
- **Watched Literals**: ~0.2-0.6s (**~50-500× faster**)
- **Preprocessing**: ~0.1-0.5s
- **Combined**: ~0.1-0.3s (**best overall**)

### 16×16 Puzzles
- **Base DPLL**: Will timeout on most
- **Watched Literals**: ~5-30s
- **Preprocessing**: ~2-15s
- **Combined**: ~1-10s

### 25×25 Puzzles
- **Base DPLL**: Will timeout on all
- **Watched Literals**: ~30-300s (some timeouts)
- **Preprocessing**: ~20-200s
- **Combined**: ~10-120s (**only one reliably solving 25×25**)

## ⚙️ Customization

### Run Specific Variants
```bash
# Test only watched literals vs combined
python experiment_runner.py --variants watched combined
```

### Adjust Resources
```bash
# Use fewer threads (for testing or limited resources)
python experiment_runner.py --threads 64

# More repetitions for better statistics
python experiment_runner.py --repetitions 5
```

### Modify Timeouts
```bash
# Longer timeouts for harder puzzles
python experiment_runner.py \
    --timeout-9x9 600 \
    --timeout-16x16 1200 \
    --timeout-25x25 1800
```

### Custom Output Directory
```bash
# Different results directory
python experiment_runner.py --results-dir my_experiment_results
```

## 🔄 Resume After Interruption

If the experiment is interrupted (Ctrl+C, system restart, etc.):

```bash
# Simply re-run the same command
python experiment_runner.py

# The script will:
# 1. Read results/raw_results.csv
# 2. Identify completed runs
# 3. Skip them and continue with remaining experiments
```

Example output when resuming:
```
Loaded 34 puzzles
Found 150 completed runs  ← Previously completed
Total experiment runs: 408
Runs to execute: 258     ← Only run remaining ones
```

## 📊 Monitor Progress

### Real-time Monitoring

**Terminal 1** (run experiment):
```bash
python experiment_runner.py
```

**Terminal 2** (monitor results):
```bash
# Watch CSV file grow
watch -n 5 "wc -l results/raw_results.csv"

# Check latest results
tail -f results/experiment.log

# Count completed by variant
tail -n +2 results/raw_results.csv | cut -d',' -f4 | sort | uniq -c
```

### CPU Utilization
```bash
# Verify all 128 threads are being used
htop

# Or check average load
uptime
```

## 🐛 Troubleshooting

### Issue: Import Errors
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

### Issue: Memory Exhausted
```bash
# Solution: Reduce threads
python experiment_runner.py --threads 64
```

### Issue: All Base DPLL Timing Out
This is expected! Base DPLL is the naive baseline and will timeout on many puzzles, especially 16×16 and 25×25. This demonstrates the need for optimizations.

### Issue: CSV File Corrupted
```bash
# Check for incomplete lines
tail results/raw_results.csv

# If corrupted, remove last incomplete line and resume
head -n -1 results/raw_results.csv > results/raw_results_fixed.csv
mv results/raw_results_fixed.csv results/raw_results.csv
python experiment_runner.py
```

## 📝 Paper Results Checklist

After analysis completes, you should have:

- [ ] `analysis/summary_statistics.txt` - for Results section
- [ ] `analysis/statistical_tests.csv` - for significance claims
- [ ] `analysis/boxplots_solve_time.png` - Figure 1 in paper
- [ ] `analysis/scaling_curves.png` - Figure 2 in paper
- [ ] `analysis/metrics_comparison.png` - Figure 3 in paper
- [ ] `analysis/table_summary.tex` - Table 1 in paper
- [ ] `analysis/table_speedup.tex` - Table 2 in paper

## 🎯 Key Metrics for Paper

From `analysis/summary_statistics.txt`, extract:

1. **Median solve times** by variant and size
2. **Success rates** (% solved within timeout)
3. **Speedup factors** relative to baseline
4. **Statistical significance** (p-values from tests)
5. **Effect sizes** (Cohen's d, speedup ratios)

## 📧 Share Results

After completion:
```bash
# Package everything for sharing
tar -czf dpll_experiment_results.tar.gz results/ analysis/

# Share the archive
# It contains all raw data and analysis outputs
```

## ⏱️ Time Estimates

| Configuration | Estimated Time |
|--------------|----------------|
| Default (128 threads, 3 reps) | 2-4 hours |
| With 64 threads | 4-8 hours |
| With 5 reps instead of 3 | 3-6 hours |
| Single variant only | 30-60 min |

**Note**: Time varies based on:
- How many base DPLL runs timeout (they take full timeout duration)
- System load and CPU performance
- Storage I/O speed (for CSV writes)

## 🎓 For Your Research Report

### Methodology Section
Copy these exact parameters:
- **Puzzles**: 34 (20×9×9, 10×16×16, 4×25×25)
- **Variants**: 4 (Base, Watched, Preprocessing, Combined)
- **Repetitions**: 3
- **Timeouts**: 300s (9×9), 600s (16×16), 900s (25×25)
- **Total Runs**: 408
- **Parallelization**: 128 threads
- **Hardware**: [Your server specs]
- **Statistical Tests**: Friedman test, Wilcoxon signed-rank with Bonferroni correction (α=0.0083)

---

**Good luck with your experiment!** 🚀

For questions or issues, see README_EXPERIMENT.md or check the logs in `results/experiment.log`.
