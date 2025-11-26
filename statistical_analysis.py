"""
Statistical Analysis for DPLL Performance Comparison

Generates:
- Summary statistics
- Statistical significance tests
- Visualizations (box plots, scaling curves, heatmaps)
- LaTeX tables for paper
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import friedmanchisquare, wilcoxon
import argparse
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class DPLLAnalyzer:
    """Statistical analyzer for DPLL experiment results"""

    def __init__(self, results_csv: str, output_dir: str = "analysis"):
        self.df = pd.read_csv(results_csv)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Setup plotting style
        sns.set_style("whitegrid")
        sns.set_palette("husl")

    def preprocess_data(self):
        """Preprocess and clean data"""
        print("Preprocessing data...")

        # For timeouts, use the timeout value as upper bound
        self.df['wall_time_bounded'] = self.df.apply(
            lambda row: row['timeout_limit'] if row['timed_out'] else row['wall_time'],
            axis=1
        )

        # Calculate median across repetitions
        self.df_median = self.df.groupby(
            ['puzzle_id', 'puzzle_size', 'expected_status', 'variant']
        ).agg({
            'wall_time_bounded': 'median',
            'decisions': 'median',
            'backtracks': 'median',
            'unit_propagations': 'median',
            'peak_memory_mb': 'median',
            'timed_out': 'any',  # If any rep timed out
            'correct': 'all'  # All reps must be correct
        }).reset_index()

        print(f"Dataset: {len(self.df)} total runs")
        print(f"Median dataset: {len(self.df_median)} unique experiments")

    def summary_statistics(self):
        """Generate summary statistics"""
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)

        # Overall statistics by variant
        summary = self.df_median.groupby('variant').agg({
            'wall_time_bounded': ['median', 'mean', 'std'],
            'decisions': ['median', 'mean'],
            'backtracks': ['median', 'mean'],
            'unit_propagations': ['median', 'mean'],
            'timed_out': 'sum',
            'correct': 'sum'
        })

        print("\nOverall Statistics by Variant:")
        print(summary)

        # Statistics by size and variant
        summary_by_size = self.df_median.groupby(['puzzle_size', 'variant']).agg({
            'wall_time_bounded': ['median', 'mean', 'std'],
            'timed_out': 'sum',
            'correct': 'sum'
        })

        print("\nStatistics by Puzzle Size and Variant:")
        print(summary_by_size)

        # Success rates
        print("\nSuccess Rates (% solved within timeout):")
        success_rates = self.df_median.groupby(['puzzle_size', 'variant']).agg({
            'timed_out': lambda x: 100 * (1 - x.mean())
        }).round(2)
        print(success_rates)

        # Save to file
        with open(self.output_dir / "summary_statistics.txt", 'w') as f:
            f.write("SUMMARY STATISTICS\n")
            f.write("=" * 80 + "\n\n")
            f.write("Overall Statistics by Variant:\n")
            f.write(summary.to_string() + "\n\n")
            f.write("Statistics by Puzzle Size and Variant:\n")
            f.write(summary_by_size.to_string() + "\n\n")
            f.write("Success Rates (% solved within timeout):\n")
            f.write(success_rates.to_string() + "\n")

    def statistical_tests(self):
        """Perform statistical significance tests"""
        print("\n" + "=" * 80)
        print("STATISTICAL SIGNIFICANCE TESTS")
        print("=" * 80)

        results = []

        # Test for each puzzle size separately
        for puzzle_size in sorted(self.df_median['puzzle_size'].unique()):
            print(f"\n--- Puzzle Size: {puzzle_size}×{puzzle_size} ---")

            df_size = self.df_median[self.df_median['puzzle_size'] == puzzle_size]

            # Get variants
            variants = sorted(df_size['variant'].unique())

            # Friedman test (non-parametric repeated measures)
            groups = [
                df_size[df_size['variant'] == v]['wall_time_bounded'].values
                for v in variants
            ]

            if len(groups) >= 2 and all(len(g) > 0 for g in groups):
                try:
                    stat, p_value = friedmanchisquare(*groups)
                    print(f"Friedman Test: χ² = {stat:.4f}, p = {p_value:.6f}")

                    results.append({
                        'puzzle_size': puzzle_size,
                        'test': 'Friedman',
                        'statistic': stat,
                        'p_value': p_value,
                        'significant': p_value < 0.05
                    })

                    # Pairwise Wilcoxon tests with Bonferroni correction
                    if p_value < 0.05:
                        print("\nPairwise Wilcoxon Signed-Rank Tests:")

                        n_comparisons = len(variants) * (len(variants) - 1) // 2
                        alpha_corrected = 0.05 / n_comparisons

                        for i, v1 in enumerate(variants):
                            for v2 in variants[i+1:]:
                                data1 = df_size[df_size['variant'] == v1]['wall_time_bounded'].values
                                data2 = df_size[df_size['variant'] == v2]['wall_time_bounded'].values

                                # Align by puzzle_id
                                merged = df_size[df_size['variant'].isin([v1, v2])].pivot(
                                    index='puzzle_id',
                                    columns='variant',
                                    values='wall_time_bounded'
                                )

                                if v1 in merged.columns and v2 in merged.columns:
                                    data1 = merged[v1].dropna()
                                    data2 = merged[v2].dropna()

                                    if len(data1) > 0 and len(data2) > 0:
                                        stat, p = wilcoxon(data1, data2, alternative='two-sided')
                                        significant = p < alpha_corrected

                                        speedup = data1.median() / data2.median()

                                        print(f"  {v1} vs {v2}: W={stat:.2f}, p={p:.6f} {'*' if significant else ''}, "
                                              f"speedup={speedup:.2f}×")

                                        results.append({
                                            'puzzle_size': puzzle_size,
                                            'test': f'Wilcoxon {v1} vs {v2}',
                                            'statistic': stat,
                                            'p_value': p,
                                            'significant': significant,
                                            'speedup': speedup
                                        })

                except Exception as e:
                    print(f"Error in statistical test: {str(e)}")

        # Save results
        results_df = pd.DataFrame(results)
        results_df.to_csv(self.output_dir / "statistical_tests.csv", index=False)
        print(f"\nStatistical test results saved to {self.output_dir / 'statistical_tests.csv'}")

    def plot_boxplots(self):
        """Generate box plots of solve times"""
        print("\nGenerating box plots...")

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        for idx, puzzle_size in enumerate(sorted(self.df_median['puzzle_size'].unique())):
            ax = axes[idx]

            df_size = self.df_median[self.df_median['puzzle_size'] == puzzle_size]

            # Remove timeouts for better visualization (or cap at timeout)
            df_plot = df_size[~df_size['timed_out']].copy()

            sns.boxplot(
                data=df_plot,
                x='variant',
                y='wall_time_bounded',
                ax=ax,
                order=['base', 'watched', 'preprocessing', 'combined']
            )

            ax.set_yscale('log')
            ax.set_title(f'{puzzle_size}×{puzzle_size} Sudoku', fontsize=14)
            ax.set_xlabel('DPLL Variant', fontsize=12)
            ax.set_ylabel('Solve Time (seconds, log scale)', fontsize=12)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / "boxplots_solve_time.png", dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Box plots saved to {self.output_dir / 'boxplots_solve_time.png'}")

    def plot_scaling_curves(self):
        """Generate scaling curves"""
        print("\nGenerating scaling curves...")

        # Median solve time by size and variant
        scaling_data = self.df_median.groupby(['puzzle_size', 'variant']).agg({
            'wall_time_bounded': 'median'
        }).reset_index()

        plt.figure(figsize=(10, 7))

        for variant in ['base', 'watched', 'preprocessing', 'combined']:
            data = scaling_data[scaling_data['variant'] == variant]

            plt.plot(
                data['puzzle_size'],
                data['wall_time_bounded'],
                marker='o',
                markersize=10,
                linewidth=2,
                label=variant.capitalize()
            )

        plt.yscale('log')
        plt.xlabel('Puzzle Size (N×N)', fontsize=14)
        plt.ylabel('Median Solve Time (seconds, log scale)', fontsize=14)
        plt.title('Scaling Behavior of DPLL Variants', fontsize=16)
        plt.legend(fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks([9, 16, 25])

        plt.savefig(self.output_dir / "scaling_curves.png", dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Scaling curves saved to {self.output_dir / 'scaling_curves.png'}")

    def plot_metrics_comparison(self):
        """Compare different metrics across variants"""
        print("\nGenerating metrics comparison plots...")

        metrics = ['decisions', 'backtracks', 'unit_propagations']
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        for idx, metric in enumerate(metrics):
            ax = axes[idx]

            # Filter out timeouts
            df_plot = self.df_median[~self.df_median['timed_out']]

            data = df_plot.groupby('variant')[metric].median()

            data.plot(
                kind='bar',
                ax=ax,
                color=sns.color_palette("husl", len(data))
            )

            ax.set_title(f'{metric.replace("_", " ").title()}', fontsize=14)
            ax.set_xlabel('DPLL Variant', fontsize=12)
            ax.set_ylabel(f'Median {metric.replace("_", " ").title()}', fontsize=12)
            ax.set_yscale('log')
            ax.grid(True, alpha=0.3, axis='y')
            ax.tick_params(axis='x', rotation=45)

        plt.tight_layout()
        plt.savefig(self.output_dir / "metrics_comparison.png", dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Metrics comparison saved to {self.output_dir / 'metrics_comparison.png'}")

    def generate_latex_tables(self):
        """Generate LaTeX tables for paper"""
        print("\nGenerating LaTeX tables...")

        # Table 1: Summary statistics
        summary = self.df_median.groupby(['puzzle_size', 'variant']).agg({
            'wall_time_bounded': 'median',
            'decisions': 'median',
            'timed_out': lambda x: f"{100*(1-x.mean()):.1f}%"
        }).round(2)

        latex_table1 = summary.to_latex(
            caption="Median solve times and success rates by puzzle size and variant",
            label="tab:summary"
        )

        with open(self.output_dir / "table_summary.tex", 'w') as f:
            f.write(latex_table1)

        # Table 2: Speedup ratios
        baseline_times = self.df_median[self.df_median['variant'] == 'base'].set_index('puzzle_id')['wall_time_bounded']

        speedup_data = []
        for variant in ['watched', 'preprocessing', 'combined']:
            variant_times = self.df_median[self.df_median['variant'] == variant].set_index('puzzle_id')['wall_time_bounded']

            for puzzle_size in sorted(self.df_median['puzzle_size'].unique()):
                puzzles = self.df_median[self.df_median['puzzle_size'] == puzzle_size]['puzzle_id'].unique()

                speedups = []
                for pid in puzzles:
                    if pid in baseline_times.index and pid in variant_times.index:
                        if variant_times[pid] > 0:
                            speedups.append(baseline_times[pid] / variant_times[pid])

                if speedups:
                    speedup_data.append({
                        'Puzzle Size': f'{puzzle_size}×{puzzle_size}',
                        'Variant': variant.capitalize(),
                        'Median Speedup': f'{np.median(speedups):.2f}×'
                    })

        speedup_df = pd.DataFrame(speedup_data)
        latex_table2 = speedup_df.to_latex(
            index=False,
            caption="Speedup factors relative to baseline DPLL",
            label="tab:speedup"
        )

        with open(self.output_dir / "table_speedup.tex", 'w') as f:
            f.write(latex_table2)

        print(f"LaTeX tables saved to {self.output_dir}")

    def run_full_analysis(self):
        """Run complete analysis pipeline"""
        print("\n" + "=" * 80)
        print("DPLL PERFORMANCE ANALYSIS")
        print("=" * 80)

        self.preprocess_data()
        self.summary_statistics()
        self.statistical_tests()
        self.plot_boxplots()
        self.plot_scaling_curves()
        self.plot_metrics_comparison()
        self.generate_latex_tables()

        print("\n" + "=" * 80)
        print(f"Analysis complete! Results saved to {self.output_dir}")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Statistical analysis of DPLL experiment results"
    )

    parser.add_argument(
        '--results',
        type=str,
        default='results/raw_results.csv',
        help='Path to raw results CSV file'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='analysis',
        help='Output directory for analysis results'
    )

    args = parser.parse_args()

    analyzer = DPLLAnalyzer(args.results, args.output)
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
