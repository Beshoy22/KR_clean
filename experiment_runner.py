"""
Experiment Runner for DPLL Performance Comparison

Features:
- Parallel execution with configurable thread count
- Timeout handling based on puzzle size
- Thread-safe CSV logging
- Resume capability
- Progress tracking
- Comprehensive metrics collection
"""

import os
import csv
import time
import logging
import argparse
import multiprocessing as mp
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError
from threading import Lock
from tqdm import tqdm
import signal
import psutil
import tracemalloc

from encoder import to_cnf
from dpll_variants import get_solver


# Global CSV lock for thread-safe writing
csv_lock = Lock()


@dataclass
class ExperimentConfig:
    """Configuration for the experiment"""
    puzzle_dir: str = "puzzles"
    results_dir: str = "results"
    num_threads: int = 128
    num_repetitions: int = 3
    timeout_9x9: int = 300  # 5 minutes
    timeout_16x16: int = 600  # 10 minutes
    timeout_25x25: int = 900  # 15 minutes
    variants: List[str] = None

    def __post_init__(self):
        if self.variants is None:
            self.variants = ['base', 'watched', 'preprocessing', 'combined']


@dataclass
class ExperimentResult:
    """Results from a single experiment run"""
    puzzle_id: int
    puzzle_size: int
    expected_status: str  # SAT or UNSAT
    variant: str
    repetition: int
    status: str  # SAT, UNSAT, or TIMEOUT
    wall_time: float
    decisions: int
    backtracks: int
    unit_propagations: int
    conflicts: int
    peak_memory_mb: float
    timeout_limit: float
    timed_out: bool
    correct: bool  # Whether result matches expected status

    def to_dict(self) -> Dict:
        return asdict(self)


def setup_logging(results_dir: str):
    """Setup logging to file"""
    os.makedirs(results_dir, exist_ok=True)
    log_file = os.path.join(results_dir, "experiment.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


def load_puzzle_manifest(puzzle_dir: str) -> Dict[int, Tuple[int, str]]:
    """Load puzzle manifest with metadata"""
    manifest_path = os.path.join(puzzle_dir, "!puzzles_manifest.csv")
    manifest = {}

    with open(manifest_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            puzzle_id = int(row['puzzle_id'])
            size = int(row['n'])
            status = row['status']
            manifest[puzzle_id] = (size, status)

    return manifest


def get_timeout_for_size(size: int, config: ExperimentConfig) -> float:
    """Get timeout in seconds based on puzzle size"""
    if size == 9:
        return config.timeout_9x9
    elif size == 16:
        return config.timeout_16x16
    elif size == 25:
        return config.timeout_25x25
    else:
        raise ValueError(f"Unknown puzzle size: {size}")


class TimeoutException(Exception):
    """Exception raised when timeout occurs"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutException("Solver timeout")


def run_single_experiment(
    puzzle_id: int,
    puzzle_path: str,
    variant: str,
    repetition: int,
    expected_status: str,
    puzzle_size: int,
    timeout: float
) -> ExperimentResult:
    """
    Run a single experiment (one puzzle, one variant, one repetition)
    This function will be called in a separate process
    """

    # Start memory tracking
    tracemalloc.start()
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    try:
        # Encode puzzle to CNF
        clauses, num_vars = to_cnf(puzzle_path)

        # Create solver
        solver = get_solver(variant, clauses, num_vars)

        # Set up signal-based timeout (Unix only, guaranteed to work)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout) + 1)  # Set alarm for timeout + 1 second buffer

        # Solve with timeout
        start_time = time.time()
        try:
            status, model = solver.solve()
            wall_time = time.time() - start_time
            signal.alarm(0)  # Cancel the alarm
        except TimeoutException:
            # Timeout occurred
            wall_time = timeout
            signal.alarm(0)  # Cancel the alarm
            logging.warning(f"TIMEOUT: puzzle {puzzle_id}, variant {variant}, rep {repetition} (limit: {timeout}s)")

            tracemalloc.stop()
            return ExperimentResult(
                puzzle_id=puzzle_id,
                puzzle_size=puzzle_size,
                expected_status=expected_status,
                variant=variant,
                repetition=repetition,
                status="TIMEOUT",
                wall_time=timeout,
                decisions=0,
                backtracks=0,
                unit_propagations=0,
                conflicts=0,
                peak_memory_mb=0.0,
                timeout_limit=timeout,
                timed_out=True,
                correct=False
            )

        # Memory measurement
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        mem_after = process.memory_info().rss / 1024 / 1024
        peak_memory_mb = max(peak / 1024 / 1024, mem_after - mem_before)

        # Extract metrics
        metrics = solver.metrics

        return ExperimentResult(
            puzzle_id=puzzle_id,
            puzzle_size=puzzle_size,
            expected_status=expected_status,
            variant=variant,
            repetition=repetition,
            status=status,
            wall_time=wall_time,
            decisions=metrics.decisions,
            backtracks=metrics.backtracks,
            unit_propagations=metrics.unit_propagations,
            conflicts=metrics.conflicts,
            peak_memory_mb=peak_memory_mb,
            timeout_limit=timeout,
            timed_out=False,
            correct=(status == expected_status)
        )

    except Exception as e:
        # Handle any errors
        signal.alarm(0)  # Cancel alarm
        tracemalloc.stop()
        logging.error(f"Error in puzzle {puzzle_id}, variant {variant}, rep {repetition}: {str(e)}")

        return ExperimentResult(
            puzzle_id=puzzle_id,
            puzzle_size=puzzle_size,
            expected_status=expected_status,
            variant=variant,
            repetition=repetition,
            status="ERROR",
            wall_time=timeout,
            decisions=0,
            backtracks=0,
            unit_propagations=0,
            conflicts=0,
            peak_memory_mb=0.0,
            timeout_limit=timeout,
            timed_out=True,
            correct=False
        )


def run_with_timeout(args):
    """Wrapper to run experiment with timeout"""
    puzzle_id, puzzle_path, variant, repetition, expected_status, puzzle_size, timeout = args

    try:
        # Use ProcessPoolExecutor for timeout enforcement
        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                run_single_experiment,
                puzzle_id,
                puzzle_path,
                variant,
                repetition,
                expected_status,
                puzzle_size,
                timeout
            )

            result = future.result(timeout=timeout)
            return result

    except TimeoutError:
        # Timeout occurred
        logging.warning(f"Timeout: puzzle {puzzle_id}, variant {variant}, rep {repetition}")

        return ExperimentResult(
            puzzle_id=puzzle_id,
            puzzle_size=puzzle_size,
            expected_status=expected_status,
            variant=variant,
            repetition=repetition,
            status="TIMEOUT",
            wall_time=timeout,
            decisions=0,
            backtracks=0,
            unit_propagations=0,
            conflicts=0,
            peak_memory_mb=0.0,
            timeout_limit=timeout,
            timed_out=True,
            correct=False
        )
    except Exception as e:
        logging.error(f"Error: puzzle {puzzle_id}, variant {variant}, rep {repetition}: {str(e)}")

        return ExperimentResult(
            puzzle_id=puzzle_id,
            puzzle_size=puzzle_size,
            expected_status=expected_status,
            variant=variant,
            repetition=repetition,
            status="ERROR",
            wall_time=timeout,
            decisions=0,
            backtracks=0,
            unit_propagations=0,
            conflicts=0,
            peak_memory_mb=0.0,
            timeout_limit=timeout,
            timed_out=True,
            correct=False
        )


def save_result_to_csv(result: ExperimentResult, csv_path: str):
    """Thread-safe CSV writing"""
    with csv_lock:
        file_exists = os.path.exists(csv_path)

        with open(csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=result.to_dict().keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(result.to_dict())


def load_completed_runs(csv_path: str) -> set:
    """Load already completed runs for resume capability"""
    if not os.path.exists(csv_path):
        return set()

    completed = set()
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (
                int(row['puzzle_id']),
                row['variant'],
                int(row['repetition'])
            )
            completed.add(key)

    return completed


def generate_experiment_tasks(config: ExperimentConfig, manifest: Dict) -> List[Tuple]:
    """Generate all experiment tasks"""
    tasks = []

    for puzzle_id, (puzzle_size, expected_status) in manifest.items():
        puzzle_path = os.path.join(config.puzzle_dir, f"puzzle{puzzle_id}.txt")
        timeout = get_timeout_for_size(puzzle_size, config)

        for variant in config.variants:
            for repetition in range(1, config.num_repetitions + 1):
                tasks.append((
                    puzzle_id,
                    puzzle_path,
                    variant,
                    repetition,
                    expected_status,
                    puzzle_size,
                    timeout
                ))

    return tasks


def run_experiments(config: ExperimentConfig, logger: logging.Logger):
    """Main experiment runner"""
    logger.info("=" * 80)
    logger.info("DPLL Performance Comparison Experiment")
    logger.info("=" * 80)
    logger.info(f"Configuration:")
    logger.info(f"  Puzzle directory: {config.puzzle_dir}")
    logger.info(f"  Results directory: {config.results_dir}")
    logger.info(f"  Number of threads: {config.num_threads}")
    logger.info(f"  Repetitions per experiment: {config.num_repetitions}")
    logger.info(f"  Variants: {config.variants}")
    logger.info(f"  Timeouts: 9×9={config.timeout_9x9}s, 16×16={config.timeout_16x16}s, 25×25={config.timeout_25x25}s")
    logger.info("=" * 80)

    # Load puzzle manifest
    manifest = load_puzzle_manifest(config.puzzle_dir)
    logger.info(f"Loaded {len(manifest)} puzzles")

    # Setup results
    os.makedirs(config.results_dir, exist_ok=True)
    csv_path = os.path.join(config.results_dir, "raw_results.csv")

    # Check for resume
    completed_runs = load_completed_runs(csv_path)
    logger.info(f"Found {len(completed_runs)} completed runs")

    # Generate all tasks
    all_tasks = generate_experiment_tasks(config, manifest)
    logger.info(f"Total experiment runs: {len(all_tasks)}")

    # Filter out completed tasks
    tasks_to_run = [
        task for task in all_tasks
        if (task[0], task[2], task[3]) not in completed_runs
    ]

    logger.info(f"Runs to execute: {len(tasks_to_run)}")

    if not tasks_to_run:
        logger.info("All experiments already completed!")
        return

    # Run experiments in parallel
    logger.info("Starting parallel execution...")
    logger.info(f"Using {config.num_threads} worker processes")

    results_collected = 0

    with ProcessPoolExecutor(max_workers=config.num_threads) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(run_with_timeout, task): task
            for task in tasks_to_run
        }

        # Process results with progress bar
        with tqdm(total=len(tasks_to_run), desc="Experiments", unit="run") as pbar:
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                puzzle_id, _, variant, repetition, _, _, _ = task

                try:
                    result = future.result()

                    # Save result immediately
                    save_result_to_csv(result, csv_path)
                    results_collected += 1

                    # Update progress
                    pbar.update(1)
                    pbar.set_postfix({
                        'puzzle': puzzle_id,
                        'variant': variant,
                        'status': result.status
                    })

                    # Log result
                    logger.info(
                        f"Completed: puzzle={puzzle_id}, variant={variant}, "
                        f"rep={repetition}, status={result.status}, "
                        f"time={result.wall_time:.2f}s"
                    )

                except Exception as e:
                    logger.error(f"Failed to process result: {str(e)}")

    logger.info("=" * 80)
    logger.info(f"Experiment completed! Results saved to {csv_path}")
    logger.info(f"Total results collected: {results_collected}")
    logger.info("=" * 80)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Run DPLL performance comparison experiments"
    )

    parser.add_argument(
        '--puzzle-dir',
        type=str,
        default='puzzles',
        help='Directory containing puzzle files'
    )

    parser.add_argument(
        '--results-dir',
        type=str,
        default='results',
        help='Directory to save results'
    )

    parser.add_argument(
        '--threads',
        type=int,
        default=128,
        help='Number of parallel threads'
    )

    parser.add_argument(
        '--repetitions',
        type=int,
        default=3,
        help='Number of repetitions per experiment'
    )

    parser.add_argument(
        '--variants',
        nargs='+',
        default=['base', 'watched', 'preprocessing', 'combined'],
        help='DPLL variants to test'
    )

    parser.add_argument(
        '--timeout-9x9',
        type=int,
        default=300,
        help='Timeout for 9×9 puzzles (seconds)'
    )

    parser.add_argument(
        '--timeout-16x16',
        type=int,
        default=600,
        help='Timeout for 16×16 puzzles (seconds)'
    )

    parser.add_argument(
        '--timeout-25x25',
        type=int,
        default=900,
        help='Timeout for 25×25 puzzles (seconds)'
    )

    args = parser.parse_args()

    # Create config
    config = ExperimentConfig(
        puzzle_dir=args.puzzle_dir,
        results_dir=args.results_dir,
        num_threads=args.threads,
        num_repetitions=args.repetitions,
        variants=args.variants,
        timeout_9x9=args.timeout_9x9,
        timeout_16x16=args.timeout_16x16,
        timeout_25x25=args.timeout_25x25
    )

    # Setup logging
    logger = setup_logging(config.results_dir)

    # Run experiments
    try:
        run_experiments(config, logger)
    except KeyboardInterrupt:
        logger.info("Experiment interrupted by user")
    except Exception as e:
        logger.error(f"Experiment failed with error: {str(e)}")
        raise


if __name__ == "__main__":
    # Required for Windows compatibility with multiprocessing
    mp.set_start_method('spawn', force=True)
    main()
