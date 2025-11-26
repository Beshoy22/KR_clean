"""
SAT Assignment Part 1 - Non-consecutive Sudoku Encoder (Puzzle -> CNF)

THIS is the file to edit.

Implement: to_cnf(input_path) -> (clauses, num_vars)

You're required to use a variable mapping as follows:
    var(r,c,v) = r*N*N + c*N + v
where r,c are in range (0...N-1) and v in (1...N).

You must encode:
  (1) Exactly one value per cell
  (2) For each value v and each row r: exactly one column c has v
  (3) For each value v and each column c: exactly one row r has v
  (4) For each value v and each sqrt(N)×sqrt(N) box: exactly one cell has v
  (5) Non-consecutive: orthogonal neighbors cannot differ by 1
  (6) Clues: unit clauses for the given puzzle
"""


from typing import Tuple, Iterable
import os
import math
from typing import List, Tuple, Iterable, Union
from dataclasses import dataclass


def remove_index(lst: List, index: int) -> List:
    if index < 0 or index >= len(lst):
        raise IndexError("Index out of range")
    return lst[:index] + lst[index+1:]


def set_deletion(whole_set,item):
    return whole_set - {item}


@dataclass
class Variable:
    row: int
    col: int
    val: int
    neg : bool = False

    def __repr__(self) -> str:
        return f"{self.row}{self.col}{self.val}" if not self.neg else f"-{self.row}{self.col}{self.val}"


class SATSolver:

    def __init__(self, filepath: str) -> None:
        with open(filepath, 'r') as f:
            lines = f.readlines()

        self.sudoku_grid = [
            [
                int(num) for num in line.strip('\n').split(' ') if num.strip()
            ] for line in lines if line.strip()
        ]

        self.N = len(self.sudoku_grid)
        self.model = []
        self.number_of_variables = self.N ** 3
        self.clauses = []
        self.whole_set = set(range(1,self.N+1))

    
    def print_sudoku(self) -> None:
        """
        Pretty print a Sudoku board represented as a list of lists.
        Works for any N x N Sudoku where N is a perfect square (e.g., 4x4, 9x9, 16x16).
        Automatically adjusts cell width for multi-digit or lettered values.
        Empty cells are represented by 0.
        """
        grid = self.sudoku_grid
        N = len(grid)
        n = int(N ** 0.5)

        if n * n != N:
            raise ValueError(f"Grid size {N}x{N} is not a valid Sudoku (N must be a perfect square).")

        # Compute maximum cell width (for alignment)
        # If numbers go beyond 9 (e.g., 10–16), convert to base-36 (A, B, C…)
        def format_val(v):
            if v == 0:
                return "."
            else:
                return str(v)

        max_val = max(max(row) for row in grid)
        cell_width = max(len(format_val(max_val)), 1)

        def cell_str(v):
            return format_val(v).rjust(cell_width)

        # Print the Sudoku
        for i, row in enumerate(grid):
            if i % n == 0 and i != 0:
                # Horizontal separator
                sep_length = (cell_width + 1) * N + (n - 1) * 2 - 1
                print("-" * sep_length)

            row_display = ""
            for j, val in enumerate(row):
                if j % n == 0 and j != 0:
                    row_display += "| "
                row_display += cell_str(val) + " "
            print(row_display.rstrip())


    def map_variable(self, var: Union[Variable, Tuple[Variable]]) -> Union[int, Tuple[int]]:
        """
        Map (row, column, value) to a unique variable number.
        var(r,c,v) = r*N*N + c*N + v
        where r,c are in range (0...N-1) and v in (1...N).
        
        If var is a Variable, returns an int.
        If var is a Tuple of Variables, returns a Tuple of ints.
        """
        if isinstance(var, tuple):
            return tuple(self.map_variable(v) for v in var)
        else:
            _num = var.row * self.N * self.N + var.col * self.N + var.val
            return _num if not var.neg else -_num


    def generate_model(self) -> None:
        """
        Generate variable mapping for Sudoku encoding.
        var(r,c,v) = r*N*N + c*N + v
        where r,c are in range (0...N-1) and v in (1...N).
        """
        N = self.N
        
        _clauses = []

        for i in range(self.N):
            for j in range(self.N):
                if self.sudoku_grid[i][j] == 0: continue

                self.model.append(
                    (Variable(i, j, self.sudoku_grid[i][j]),)
                )
                _clauses.append(
                    (Variable(i, j, self.sudoku_grid[i][j]),)
                )
        
        return _clauses


    def encode(self) -> Tuple[Iterable[Iterable[int]], int]:
        """
        Encode the Sudoku puzzle to DIMACS CNF format.
        Returns a tuple (clauses, num_vars).
        """

        model_clauses = self.generate_model()

        rule1_clauses = self.generate_rule1_one_per_cell()
        rule2_clauses = self.generate_rule2_row_constraint()
        rule3_clauses = self.generate_rule3_col_constraint()
        rule4_clauses = self.generate_rule4_box_constraint()
        rule5_clauses = self.generate_rule5_non_consecutive()
        rule5_clauses = self.generate_rule5_non_consecutive()

        _clauses = model_clauses + rule1_clauses + rule2_clauses + rule3_clauses + rule4_clauses + rule5_clauses

        self.clauses = list(
            map(lambda x: self.map_variable(x), _clauses)
        )

        return self.clauses, self.number_of_variables


    def save_cnf(self, output_path: str) -> None:
        """
        Save the CNF clauses to a file in DIMACS format.
        """
        """Write DIMACS CNF to a file path or file-like (stdout)."""
        close = False
        if isinstance(output_path, str):
            f = open(output_path, "w")
            close = True
        else:
            f = output_path
        try:
            clauses = list(self.clauses)
            f.write(f"p cnf {self.number_of_variables} {len(clauses)}\n")
            for cl in clauses:
                f.write(" ".join(str(l) for l in cl) + " 0\n")
        finally:
            if close:
                f.close()


    def generate_rule1_one_per_cell(self):
        """
        Each cell must contain exactly one value.
        - At least one: (v1 OR v2 OR ... OR vN)
        - At most one: (-vi OR -vj) for all pairs i < j
        """
        _clauses = []

        for i in range(self.N):
            for j in range(self.N):
                # At least one value per cell
                at_least_one = tuple(Variable(i, j, v) for v in range(1, self.N+1))
                _clauses.append(at_least_one)
                
                # At most one value per cell (pairwise constraints)
                for v1 in range(1, self.N+1):
                    for v2 in range(v1+1, self.N+1):
                        lhs = Variable(i, j, v1, neg=True)
                        rhs = Variable(i, j, v2, neg=True)
                        _clauses.append((lhs, rhs))

        return _clauses


    def generate_rule2_row_constraint(self):
        """
        Each value must appear exactly once in each row.
        - At least once: For each row r and value v, at least one column has that value
        - At most once: No two columns in the same row have the same value
        """
        _clauses = []

        for r in range(self.N):
            for v in range(1, self.N+1):
                # At least one occurrence of v in row r
                at_least_one = tuple(Variable(r, c, v) for c in range(self.N))
                _clauses.append(at_least_one)
                
                # At most one occurrence (pairwise)
                for c1 in range(self.N):
                    for c2 in range(c1+1, self.N):
                        lhs = Variable(r, c1, v, neg=True)
                        rhs = Variable(r, c2, v, neg=True)
                        _clauses.append((lhs, rhs))

        return _clauses


    def generate_rule3_col_constraint(self):
        """
        Each value must appear exactly once in each column.
        """
        _clauses = []

        for c in range(self.N):
            for v in range(1, self.N+1):
                # At least one occurrence of v in column c
                at_least_one = tuple(Variable(r, c, v) for r in range(self.N))
                _clauses.append(at_least_one)
                
                # At most one occurrence (pairwise)
                for r1 in range(self.N):
                    for r2 in range(r1+1, self.N):
                        lhs = Variable(r1, c, v, neg=True)
                        rhs = Variable(r2, c, v, neg=True)
                        _clauses.append((lhs, rhs))

        return _clauses


    def generate_rule4_box_constraint(self):
        """
        Each value must appear exactly once in each box.
        """
        _clauses = []
        n = int(self.N ** 0.5)

        for box_row in range(n):
            for box_col in range(n):
                # Get all cells in this box
                cells = []
                for i in range(n):
                    for j in range(n):
                        r = box_row * n + i
                        c = box_col * n + j
                        cells.append((r, c))  # Fixed: removed +1
                
                for v in range(1, self.N+1):
                    # At least one occurrence of v in this box
                    at_least_one = tuple(Variable(r, c, v) for r, c in cells)
                    _clauses.append(at_least_one)
                    
                    # At most one occurrence (pairwise)
                    for idx1 in range(len(cells)):
                        for idx2 in range(idx1+1, len(cells)):
                            r1, c1 = cells[idx1]
                            r2, c2 = cells[idx2]
                            lhs = Variable(r1, c1, v, neg=True)
                            rhs = Variable(r2, c2, v, neg=True)
                            _clauses.append((lhs, rhs))

        return _clauses


    def generate_rule5_non_consecutive(self):
        """
        Orthogonally adjacent cells should have values >1 w.r.t value in current cell
        """
        _clauses = []
        
        for i in range(self.N):
            for j in range(self.N):
                for v in range(1, self.N+1):
                    # Define adjacent cells
                    adjacent = []
                    if i > 0:  # Top
                        adjacent.append((i-1, j))
                    if i < self.N-1:  # Bottom
                        adjacent.append((i+1, j))
                    if j > 0:  # Left
                        adjacent.append((i, j-1))
                    if j < self.N-1:  # Right
                        adjacent.append((i, j+1))
                    
                    # For each adjacent cell, add constraints
                    for adj_r, adj_c in adjacent:
                        # If (i,j) = v, then adjacent cannot be v-1
                        if v > 1:
                            lhs = Variable(i, j, v, neg=True)
                            rhs = Variable(adj_r, adj_c, v-1, neg=True)
                            _clauses.append((lhs, rhs))
                        # If (i,j) = v, then adjacent cannot be v+1
                        if v < self.N:
                            lhs = Variable(i, j, v, neg=True)
                            rhs = Variable(adj_r, adj_c, v+1, neg=True)
                            _clauses.append((lhs, rhs))

        return _clauses



def to_cnf(input_path: str) -> Tuple[Iterable[Iterable[int]], int]:
    """
    Read puzzle from input_path and return (clauses, num_vars).

    - clauses: iterable of iterables of ints (each clause), no trailing 0s
    - num_vars: must be N^3 with N = grid size
    """
    solver = SATSolver(input_path)
    clauses, num_vars = solver.encode()
    
    return clauses, num_vars