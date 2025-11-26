# Experimental Setup - Complete Methodology

## 📋 Overview

This document explains the complete experimental methodology for comparing four DPLL variants on non-consecutive Sudoku puzzles, including dataset composition, repetition strategy, timeout handling, statistical methodology, and reproducibility measures.

---

## 1. Dataset Composition

### 1.1 Puzzle Collection

**Source:** Existing puzzles in repository (`puzzles/` directory)

**Total:** 34 unique non-consecutive Sudoku puzzles

**Distribution by Size:**
```
Size    SAT    UNSAT    Total    Clues (SAT/UNSAT)
9×9     10     10       20       25/26
16×16   5      5        10       77/78
25×25   2      2        4        188/189
```

**Rationale for distribution:**
- **9×9**: Most common Sudoku size, allows fine-grained analysis
- **16×16**: Tests scalability to intermediate complexity
- **25×25**: Stress test for algorithmic limits
- **SAT/UNSAT balance**: Tests both solution finding and unsatisfiability proofs

### 1.2 Puzzle Characteristics

**Non-consecutive constraint:** Orthogonally adjacent cells cannot contain consecutive digits (e.g., if cell A = 5, adjacent cells ≠ 4 and ≠ 6)

**Clause count (approximate):**
- **9×9**: ~20,000 clauses
- **16×16**: ~50,000 clauses
- **25×25**: ~120,000 clauses

**Why non-consecutive Sudoku?**
- Highly constrained → heavy unit propagation
- NP-complete → computationally interesting
- Structured constraints → tests real-world SAT patterns
- Scales exponentially → reveals optimization limits

---

## 2. DPLL Variants Tested

### 2.1 Variant Descriptions

**1. Base DPLL** (Baseline)
- Naive unit propagation (checks all clauses)
- Pure literal elimination
- DLIS (Dynamic Largest Individual Sum) variable selection
- Purpose: Establish baseline performance

**2. Watched Literals DPLL**
- 2-watched literals scheme (each clause watches 2 literals)
- Only checks clauses when watched literals become false
- State save/restore for backtracking
- Purpose: Test algorithmic optimization (reduce clause checks)

**3. Preprocessing DPLL**
- Exhaustive unit propagation before search
- Pure literal elimination
- Subsumption elimination (remove subsumed clauses)
- Bounded Variable Elimination (BVE) with k_max = 10
- Then uses Base DPLL for search
- Purpose: Test structural reduction

**4. Combined DPLL**
- Full preprocessing pipeline
- Watched literals for search phase
- Phase saving (cache variable polarity)
- Purpose: Test synergy of multiple optimizations

### 2.2 Implementation Details

**Language:** Python 3.8+

**Key libraries:**
- `dataclasses` for structured data
- `collections.defaultdict` for efficient lookups
- `signal.SIGALRM` for hard timeout enforcement

**Encoding:** Variables mapped as `var(r,c,v) = r*N*N + c*N + v` (DIMACS format)

---

## 3. Repetition Strategy

### 3.1 Why 3 Repetitions?

**Problem:** Timing measurements can vary due to:
- System load fluctuations
- CPU cache effects
- OS scheduling randomness
- Background processes

**Solution:** Run each (puzzle, variant) combination 3 times

**Rationale for 3:**
- **Too few (1-2)**: High variance, unreliable
- **Just right (3-5)**: Sufficient to measure variance
- **Too many (10+)**: Diminishing returns, excessive compute time

**Total runs:** 34 puzzles × 4 variants × 3 reps = **408 experiments**

### 3.2 Aggregation Method

**Raw data:** Each repetition saved individually to `results/raw_results.csv`
```csv
puzzle_id,variant,repetition,wall_time,...
1,base,1,12.34,...
1,base,2,11.98,...
1,base,3,12.56,...
```

**Aggregation:** Compute **median** across 3 repetitions per (puzzle, variant)
```python
df_median = df.groupby(['puzzle_id', 'variant']).agg({
    'wall_time_bounded': 'median',  # Median time
    'decisions': 'median',
    'backtracks': 'median',
    'timed_out': 'any'  # If ANY rep times out, mark as timeout
})
```

### 3.3 Why Median (not Mean)?

**Median is robust to outliers:**
- If 1 run is abnormally slow (background process), median ignores it
- Mean would be skewed by outliers
- For timing data, median is standard practice (e.g., benchmarking literature)

**Example:**
```
Repetitions: [0.18s, 0.19s, 5.23s]  ← outlier due to OS scheduling
Mean:   1.87s  ← misleading
Median: 0.19s  ← representative
```

---

## 4. Timeout Handling

### 4.1 Timeout Values

**Fixed by puzzle size (non-negotiable):**
- **9×9**: 300 seconds (5 minutes)
- **16×16**: 600 seconds (10 minutes)
- **25×25**: 900 seconds (15 minutes)

**Rationale:**
- Longer puzzles need more time (exponential scaling)
- Fixed per size (not per variant) for fair comparison
- Conservative limits to avoid indefinite hangs

### 4.2 Timeout Enforcement

**Mechanism:** Unix `signal.SIGALRM` (kernel-level, guaranteed)

```python
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(int(timeout) + 1)  # Set alarm

# Solver runs...

signal.alarm(0)  # Cancel if finishes early
```

**Why SIGALRM?**
- ProcessPoolExecutor timeouts are unreliable (can hang indefinitely)
- SIGALRM is kernel-enforced (cannot be ignored)
- Guarantees termination within timeout + 1 second

### 4.3 Timeout Data Handling

**If timeout occurs:**
```python
wall_time = timeout_limit  # Use timeout as upper bound
timed_out = True
status = "TIMEOUT"
```

**Statistical handling:**
- Timeouts treated as **censored data** (right-censored at timeout value)
- Analysis uses `wall_time_bounded = timeout if timed_out else actual_time`
- Success rate = % of instances solved within timeout

**Why this approach?**
- Preserves information (we know solve time ≥ timeout)
- Allows median computation (timeout is a valid upper bound)
- Standard practice in survival analysis

---

## 5. Statistical Methodology

### 5.1 Experimental Design Type

**Repeated measures design:**
- Same puzzles tested with all 4 variants
- Creates paired data (each puzzle is its own control)
- Reduces inter-puzzle variability
- More statistical power than independent samples

### 5.2 Primary Statistical Tests

**Step 1: Overall Significance (Friedman Test)**

**What it is:** Non-parametric alternative to repeated-measures ANOVA

**When used:** For each puzzle size (9×9, 16×16, 25×25), test if variants differ

**Null hypothesis (H₀):** All variants have identical performance distributions

**Alternative (H₁):** At least one variant differs

**Implementation:**
```python
from scipy.stats import friedmanchisquare

groups = [base_times, watched_times, preprocessing_times, combined_times]
stat, p_value = friedmanchisquare(*groups)
```

**Decision rule:** If p < 0.05, proceed to pairwise tests

**Why Friedman (not ANOVA)?**
- Timing data is often **non-normal** (skewed, heavy-tailed)
- Friedman makes no distributional assumptions
- More conservative (less Type I error) for non-normal data
- Standard for performance benchmarking

---

**Step 2: Pairwise Comparisons (Wilcoxon Signed-Rank Test)**

**What it is:** Non-parametric paired t-test

**When used:** After Friedman shows significance, compare each pair of variants

**Null hypothesis (H₀):** Variant A and Variant B have identical distributions

**Alternative (H₁):** Distributions differ

**Implementation:**
```python
from scipy.stats import wilcoxon

# Align by puzzle_id to ensure pairing
merged = df.pivot(index='puzzle_id', columns='variant', values='wall_time')
data1 = merged['base']
data2 = merged['watched']

stat, p_value = wilcoxon(data1, data2, alternative='two-sided')
```

**Decision rule:** Significant if p < α_corrected (Bonferroni-adjusted)

**Why Wilcoxon (not paired t-test)?**
- Same rationale as Friedman: non-parametric
- Robust to outliers and non-normality
- Only assumes symmetry of differences (weaker than normality)

---

### 5.3 Multiple Comparison Correction

**Problem:** Testing 6 pairwise comparisons (4 variants → C(4,2) = 6)
- Each test at α = 0.05
- Family-wise error rate increases: P(any false positive) = 1 - (1-0.05)⁶ ≈ 26.5%

**Solution: Bonferroni Correction**

**Adjusted significance level:**
```
α_corrected = α_family / n_comparisons
α_corrected = 0.05 / 6 = 0.0083
```

**Decision rule:** Reject H₀ only if p < 0.0083

**Why Bonferroni?**
- **Conservative:** Controls family-wise error rate (FWER)
- **Simple:** Easy to calculate and interpret
- **Standard:** Widely accepted in experimental research
- **Appropriate:** We have relatively few comparisons (6)

**Alternatives considered:**
- Holm-Bonferroni: Less conservative, but Bonferroni sufficient here
- FDR (Benjamini-Hochberg): Controls false discovery rate instead of FWER (less stringent)

We chose Bonferroni for maximum rigor.

---

### 5.4 Effect Size Measures

**Beyond p-values, we report:**

**1. Speedup Ratios**
```
Speedup = median(Base) / median(Variant)

Example:
Base median: 11.99s
Watched median: 0.18s
Speedup: 11.99 / 0.18 = 66.6×
```

**2. Success Rates**
```
Success rate = (# solved within timeout / # total) × 100%
```

**3. Median differences** (reported in tables)

**Why these measures?**
- **Practical significance** ≠ statistical significance
- A 1% speedup might be statistically significant but practically irrelevant
- Speedup ratios communicate real-world impact
- Success rates show solver reliability

---

### 5.5 Handling Tied Data

**Issue:** Multiple instances may have identical median times (especially timeouts)

**Wilcoxon with ties:**
- `scipy.stats.wilcoxon` handles ties via normal approximation
- Adds continuity correction automatically
- Reduces statistical power slightly (conservative)

**Impact on results:** Minimal - most non-timeout instances have distinct times

---

### 5.6 Statistical Assumptions

**Friedman Test Assumptions:**
1. ✅ Repeated measures (same puzzles across variants)
2. ✅ Ordinal data (times are ordinal)
3. ✅ Independent observations (puzzles are independent)

**Wilcoxon Test Assumptions:**
1. ✅ Paired data (aligned by puzzle_id)
2. ✅ Ordinal data
3. ⚠️ Symmetry of differences (approximately true for log-times)

**Verification:** Log-transform times if needed to improve symmetry

---

## 6. Parallelization Strategy

### 6.1 Implementation

**Framework:** Python `concurrent.futures.ProcessPoolExecutor`

**Workers:** 128 parallel processes

**Task distribution:** Each (puzzle, variant, repetition) runs in separate process

**Why process-based (not thread-based)?**
- Python GIL (Global Interpreter Lock) limits threading performance
- CPU-bound workload → multiprocessing is ideal
- Process isolation prevents cross-contamination

### 6.2 Resource Management

**Total experiments:** 408 runs

**Wall-clock time estimate:**
- With 128 threads: ~2-4 hours (depends on timeout rate)
- Serial execution: ~200+ hours

**Memory:** Each process uses ~50-100 MB (acceptable for 128 processes)

### 6.3 Result Collection

**Thread-safe CSV writing:**
```python
csv_lock = Lock()

def save_result(result):
    with csv_lock:
        csv.writer.writerow(result)
```

**Why thread-safe?**
- Multiple processes write results concurrently
- Without lock: CSV corruption (interleaved lines)
- With lock: Serialized writes (safe)

---

## 7. Reproducibility Measures

### 7.1 Determinism

**Deterministic solvers:**
- DPLL with fixed heuristics is deterministic
- Same puzzle + variant → same result across repetitions

**Sources of variability:**
- Timing measurements (OS scheduling)
- Memory measurements (system load)

**Mitigations:**
- 3 repetitions + median (reduces timing variance)
- Fixed random seeds (none needed - solvers are deterministic)

### 7.2 Version Control

**All code in Git:**
- Experiment framework: `experiment_runner.py`
- Solvers: `dpll_variants.py`
- Analysis: `statistical_analysis.py`
- Commit hash documented in paper

### 7.3 Data Provenance

**Raw data preserved:**
- `results/raw_results.csv`: Every single run (408 rows)
- `results/experiment.log`: Timestamped execution log
- Both committed to repository

**Reproducible analysis:**
```bash
# Anyone can re-run analysis
python statistical_analysis.py --results results/raw_results.csv
```

### 7.4 Hardware Specification

**Document in paper:**
- CPU: [Your server specs]
- RAM: [Amount]
- OS: Linux (kernel version)
- Python: 3.8+ (exact version)

**Why this matters:** Timing results are hardware-dependent

---

## 8. Experimental Procedure

### 8.1 Pre-Experiment Validation

**Before full run:**
1. ✅ Test all 4 solvers on 2 small puzzles (correctness check)
2. ✅ Verify timeout enforcement (run with 2s timeout on hard puzzle)
3. ✅ Check CSV output format (inspect headers, data types)

### 8.2 Execution Command

```bash
python experiment_runner.py \
    --puzzle-dir puzzles \
    --results-dir results \
    --threads 128 \
    --repetitions 3 \
    --timeout-9x9 300 \
    --timeout-16x16 600 \
    --timeout-25x25 900
```

### 8.3 Progress Monitoring

**Real-time monitoring:**
- Progress bar with tqdm (shows current puzzle/variant)
- Log file updates in real-time (`tail -f results/experiment.log`)
- CSV grows incrementally (resumable if interrupted)

### 8.4 Post-Experiment Analysis

**After completion:**
```bash
# Generate statistics and plots
python statistical_analysis.py --results results/raw_results.csv --output analysis
```

**Outputs:**
- `analysis/summary_statistics.txt`
- `analysis/statistical_tests.csv`
- `analysis/*.png` (figures)

---

## 9. Threats to Validity

### 9.1 Internal Validity

**Potential issues:**
- ⚠️ Implementation quality varies (our implementations, not reference implementations)
- ⚠️ Timeout values affect success rates (different timeouts → different results)

**Mitigations:**
- ✅ Multiple repetitions reduce measurement error
- ✅ Statistical tests account for variability
- ✅ All variants use same timeout per puzzle size (fair comparison)

### 9.2 External Validity

**Generalizability:**
- ⚠️ Results specific to non-consecutive Sudoku
- ⚠️ May not generalize to industrial SAT benchmarks
- ⚠️ Small dataset (34 puzzles)

**Mitigations:**
- ✅ Balanced SAT/UNSAT distribution
- ✅ Multiple puzzle sizes (9×9, 16×16, 25×25)
- ✅ Results align with theoretical expectations (watched literals should help unit-propagation-heavy instances)

### 9.3 Construct Validity

**Are we measuring what we claim?**
- ✅ Wall-clock time measures overall performance
- ✅ Decisions/backtracks measure solver behavior
- ✅ Success rate measures reliability
- ⚠️ Our implementations may not reflect "optimal" versions of each technique

---

## 10. What to Include in Paper's Experimental Setup Section

### 10.1 Essential Details

**Dataset (1 paragraph):**
```
We evaluated four DPLL variants on 34 non-consecutive Sudoku puzzles:
20 (9×9), 10 (16×16), and 4 (25×25), evenly split between SAT and UNSAT
instances. Puzzles were encoded as CNF using standard Sudoku constraints
plus non-consecutive constraints (orthogonally adjacent cells cannot differ
by 1), resulting in approximately 20K, 50K, and 120K clauses for the three
sizes respectively.
```

**Variants (1 paragraph):**
```
We implemented four DPLL variants: (1) Base DPLL with naive unit propagation,
(2) Watched Literals DPLL using the 2-watched literal scheme, (3) Preprocessing
DPLL applying exhaustive unit propagation, pure literal elimination, subsumption,
and bounded variable elimination before search, and (4) Combined DPLL integrating
preprocessing with watched literals search.
```

**Experimental Protocol (1 paragraph):**
```
Each puzzle-variant combination was executed 3 times, and median values were
used for analysis to reduce timing variance. Timeouts were set at 300s (9×9),
600s (16×16), and 900s (25×25), enforced via Unix SIGALRM. Experiments ran
in parallel using 128 processes on [hardware specs]. All code and data are
available at [repository URL].
```

**Statistical Analysis (1 paragraph):**
```
We assessed overall significance using the Friedman test (non-parametric
repeated-measures) followed by pairwise Wilcoxon signed-rank tests with
Bonferroni correction (α = 0.05/6 = 0.0083) for multiple comparisons.
Timeouts were treated as censored observations at the timeout limit. Effect
sizes were quantified as speedup ratios (baseline time / variant time).
```

### 10.2 Supplementary Materials

**In appendix or online supplement:**
- Complete dataset description (puzzle sources, clue counts)
- Implementation details (pseudocode in main paper)
- Full statistical test results (Table 2 in paper)
- Hardware specifications

---

## 11. Summary Checklist

**Before writing the Experimental Setup section, ensure you can answer:**

- [ ] **Dataset:** How many puzzles? What sizes? SAT/UNSAT split?
- [ ] **Variants:** What are the 4 variants? Key differences?
- [ ] **Repetitions:** How many runs? Why 3? How aggregated?
- [ ] **Timeouts:** What values? Why those values? How enforced?
- [ ] **Parallelization:** How many threads? Why process-based?
- [ ] **Statistics:** What tests? Why those tests? What α level?
- [ ] **Reproducibility:** How can others replicate?
- [ ] **Validity:** What are the threats? What mitigations?

**All answered? You're ready to write! ✅**

---

## 12. Key Takeaways for Paper

**Emphasize these methodological strengths:**

1. ✅ **Rigorous statistical testing** (Friedman + Bonferroni-corrected Wilcoxon)
2. ✅ **Multiple repetitions** (reduces variance)
3. ✅ **Repeated measures design** (paired comparisons, more power)
4. ✅ **Conservative approach** (non-parametric tests, Bonferroni correction)
5. ✅ **Reproducible** (all code/data available)
6. ✅ **Fair comparison** (same timeout per size, same puzzles)

**Your methodology is solid - sell it!** 🎯
