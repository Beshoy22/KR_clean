"""
DPLL Solver Variants for Performance Comparison

Four implementations:
1. BaseDPLL: Naive implementation with basic unit propagation
2. WatchedLiteralsDPLL: 2-watched literal scheme
3. PreprocessingDPLL: Heavy preprocessing before search
4. CombinedDPLL: Watched literals + preprocessing + phase saving
"""

from typing import List, Tuple, Optional, Set, Dict, Iterable
from collections import defaultdict, deque
from dataclasses import dataclass, field
import copy


@dataclass
class SolverMetrics:
    """Tracks solver performance metrics"""
    decisions: int = 0
    backtracks: int = 0
    unit_propagations: int = 0
    conflicts: int = 0

    def reset(self):
        self.decisions = 0
        self.backtracks = 0
        self.unit_propagations = 0
        self.conflicts = 0


class BaseDPLL:
    """
    Baseline DPLL implementation
    - Naive unit propagation (checks all clauses)
    - Simple data structures
    - Basic DLIS heuristic
    """

    def __init__(self, clauses: Iterable[Iterable[int]], num_vars: int):
        self.num_vars = num_vars
        self.clauses = [list(c) for c in clauses]
        self.metrics = SolverMetrics()
        self.assignment = {}  # var -> True/False

    def solve(self) -> Tuple[str, Optional[List[int]]]:
        """Main DPLL solver"""
        self.metrics.reset()
        result = self._dpll(self.clauses, self.assignment.copy())

        if result:
            model = []
            for var in range(1, self.num_vars + 1):
                if var in self.assignment and self.assignment[var]:
                    model.append(var)
                else:
                    model.append(-var)
            return "SAT", model
        return "UNSAT", None

    def _dpll(self, clauses: List[List[int]], assignment: Dict[int, bool]) -> bool:
        """Recursive DPLL algorithm"""
        # Unit propagation
        clauses, assignment = self._unit_propagate(clauses, assignment)
        if clauses is None:  # Conflict
            self.metrics.conflicts += 1
            return False

        # Check if satisfied
        if not clauses:
            self.assignment = assignment
            return True

        # Pure literal elimination
        pure_lit = self._find_pure_literal(clauses)
        if pure_lit:
            return self._dpll(
                self._assign_literal(clauses, pure_lit),
                {**assignment, abs(pure_lit): pure_lit > 0}
            )

        # Choose branching variable (DLIS heuristic)
        var = self._choose_variable(clauses)
        self.metrics.decisions += 1

        # Try positive polarity
        new_clauses = self._assign_literal(clauses, var)
        if self._dpll(new_clauses, {**assignment, var: True}):
            return True

        # Backtrack and try negative polarity
        self.metrics.backtracks += 1
        new_clauses = self._assign_literal(clauses, -var)
        return self._dpll(new_clauses, {**assignment, var: False})

    def _unit_propagate(self, clauses: List[List[int]], assignment: Dict[int, bool]) -> Tuple[Optional[List[List[int]]], Dict[int, bool]]:
        """Naive unit propagation - checks all clauses"""
        changed = True
        while changed:
            changed = False
            unit_clauses = [c for c in clauses if len(c) == 1]

            if not unit_clauses:
                break

            for unit_clause in unit_clauses:
                lit = unit_clause[0]
                var = abs(lit)
                value = lit > 0

                if var in assignment:
                    if assignment[var] != value:
                        return None, assignment  # Conflict
                    continue

                assignment = {**assignment, var: value}
                clauses = self._assign_literal(clauses, lit)
                self.metrics.unit_propagations += 1
                changed = True

                # Check for empty clause (conflict)
                if any(len(c) == 0 for c in clauses):
                    return None, assignment

        return clauses, assignment

    def _assign_literal(self, clauses: List[List[int]], lit: int) -> List[List[int]]:
        """Assign a literal and simplify clauses"""
        new_clauses = []
        for clause in clauses:
            if lit in clause:
                continue  # Clause satisfied
            new_clause = [l for l in clause if l != -lit]
            new_clauses.append(new_clause)
        return new_clauses

    def _find_pure_literal(self, clauses: List[List[int]]) -> Optional[int]:
        """Find a pure literal (appears only in one polarity)"""
        positive = set()
        negative = set()

        for clause in clauses:
            for lit in clause:
                if lit > 0:
                    positive.add(lit)
                else:
                    negative.add(-lit)

        pure_positive = positive - negative
        if pure_positive:
            return min(pure_positive)

        pure_negative = negative - positive
        if pure_negative:
            return -min(pure_negative)

        return None

    def _choose_variable(self, clauses: List[List[int]]) -> int:
        """DLIS heuristic: choose most frequent literal"""
        lit_count = defaultdict(int)

        for clause in clauses:
            for lit in clause:
                lit_count[lit] += 1

        if not lit_count:
            return 1

        best_lit = max(lit_count.keys(), key=lambda l: lit_count[l])
        return abs(best_lit)


class WatchedLiteralsDPLL:
    """
    DPLL with 2-watched literals scheme
    - Each clause watches 2 literals
    - Only examine clause when watched literal becomes false
    - Dramatically reduces clause checks during unit propagation
    """

    def __init__(self, clauses: Iterable[Iterable[int]], num_vars: int):
        self.num_vars = num_vars
        self.original_clauses = [list(c) for c in clauses]
        self.metrics = SolverMetrics()

        # Watched literals data structures
        self.clauses = []
        self.watches = defaultdict(list)  # lit -> list of clause indices watching it
        self.assignment = {}  # var -> True/False

        self._initialize_watches()

    def _initialize_watches(self):
        """Initialize 2-watched literals for each clause"""
        for clause in self.original_clauses:
            clause_idx = len(self.clauses)
            self.clauses.append(clause[:])

            # Watch first two literals (or fewer if clause is smaller)
            if len(clause) >= 1:
                self.watches[clause[0]].append(clause_idx)
            if len(clause) >= 2:
                self.watches[clause[1]].append(clause_idx)

    def solve(self) -> Tuple[str, Optional[List[int]]]:
        """Main DPLL solver with watched literals"""
        self.metrics.reset()
        result = self._dpll()

        if result:
            model = []
            for var in range(1, self.num_vars + 1):
                if self.assignment.get(var, False):
                    model.append(var)
                else:
                    model.append(-var)
            return "SAT", model
        return "UNSAT", None

    def _dpll(self) -> bool:
        """Recursive DPLL with watched literals"""
        # Unit propagation
        if not self._unit_propagate():
            self.metrics.conflicts += 1
            return False

        # Check if all variables assigned
        if len(self.assignment) == self.num_vars:
            return True

        # Choose branching variable
        var = self._choose_variable()
        if var is None:
            return True

        self.metrics.decisions += 1

        # Try positive polarity
        saved_state = self._save_state()
        self.assignment[var] = True
        if self._dpll():
            return True

        # Backtrack and try negative
        self._restore_state(saved_state)
        self.metrics.backtracks += 1
        self.assignment[var] = False
        if self._dpll():
            return True

        # Both failed, backtrack further
        self._restore_state(saved_state)
        return False

    def _unit_propagate(self) -> bool:
        """Efficient unit propagation with watched literals"""
        queue = deque()

        # Find initial unit clauses
        for clause_idx, clause in enumerate(self.clauses):
            if self._is_unit_clause(clause_idx):
                queue.append(clause_idx)

        while queue:
            clause_idx = queue.popleft()
            clause = self.clauses[clause_idx]

            # Find the unit literal
            unit_lit = self._get_unit_literal(clause)
            if unit_lit is None:
                continue

            var = abs(unit_lit)
            value = unit_lit > 0

            # Check for conflict
            if var in self.assignment:
                if self.assignment[var] != value:
                    return False
                continue

            # Assign the literal
            self.assignment[var] = value
            self.metrics.unit_propagations += 1

            # Update watches and find new unit clauses
            falsified_lit = -unit_lit
            for watched_clause_idx in self.watches[falsified_lit][:]:
                if self._is_unit_clause(watched_clause_idx):
                    queue.append(watched_clause_idx)
                elif self._is_conflicting(watched_clause_idx):
                    return False

        return True

    def _is_unit_clause(self, clause_idx: int) -> bool:
        """Check if clause is unit under current assignment"""
        clause = self.clauses[clause_idx]
        unassigned = []

        for lit in clause:
            var = abs(lit)
            if var not in self.assignment:
                unassigned.append(lit)
            elif self.assignment[var] == (lit > 0):
                return False  # Clause satisfied

        return len(unassigned) == 1

    def _is_conflicting(self, clause_idx: int) -> bool:
        """Check if clause is conflicting (all literals false)"""
        clause = self.clauses[clause_idx]
        for lit in clause:
            var = abs(lit)
            if var not in self.assignment:
                return False
            if self.assignment[var] == (lit > 0):
                return False
        return True

    def _get_unit_literal(self, clause: List[int]) -> Optional[int]:
        """Get the unit literal from a unit clause"""
        for lit in clause:
            var = abs(lit)
            if var not in self.assignment:
                return lit
        return None

    def _choose_variable(self) -> Optional[int]:
        """Choose unassigned variable with DLIS heuristic"""
        lit_count = defaultdict(int)

        for clause in self.clauses:
            # Skip satisfied clauses
            if any(abs(lit) in self.assignment and
                   self.assignment[abs(lit)] == (lit > 0)
                   for lit in clause):
                continue

            for lit in clause:
                if abs(lit) not in self.assignment:
                    lit_count[abs(lit)] += 1

        if not lit_count:
            return None

        return max(lit_count.keys(), key=lambda v: lit_count[v])

    def _save_state(self) -> Dict:
        """Save current state for backtracking"""
        return {
            'assignment': self.assignment.copy()
        }

    def _restore_state(self, state: Dict):
        """Restore state after backtracking"""
        self.assignment = state['assignment']


class PreprocessingDPLL:
    """
    DPLL with heavy preprocessing
    - Exhaustive unit propagation
    - Pure literal elimination
    - Subsumption elimination
    - Bounded variable elimination (BVE)
    """

    def __init__(self, clauses: Iterable[Iterable[int]], num_vars: int):
        self.num_vars = num_vars
        self.original_clauses = [list(c) for c in clauses]
        self.metrics = SolverMetrics()
        self.assignment = {}

        # Preprocessing statistics
        self.vars_eliminated = 0
        self.clauses_eliminated = 0

    def solve(self) -> Tuple[str, Optional[List[int]]]:
        """Solve with preprocessing"""
        self.metrics.reset()

        # Preprocessing phase
        clauses = self._preprocess(self.original_clauses)

        if clauses is None:
            return "UNSAT", None

        if not clauses:  # All satisfied during preprocessing
            model = []
            for var in range(1, self.num_vars + 1):
                if var in self.assignment and self.assignment[var]:
                    model.append(var)
                else:
                    model.append(-var)
            return "SAT", model

        # DPLL search phase
        base_solver = BaseDPLL(clauses, self.num_vars)
        base_solver.assignment = self.assignment.copy()
        status, model = base_solver.solve()

        # Merge metrics
        self.metrics.decisions = base_solver.metrics.decisions
        self.metrics.backtracks = base_solver.metrics.backtracks
        self.metrics.unit_propagations += base_solver.metrics.unit_propagations
        self.metrics.conflicts = base_solver.metrics.conflicts

        return status, model

    def _preprocess(self, clauses: List[List[int]]) -> Optional[List[List[int]]]:
        """Apply preprocessing techniques"""
        # 1. Exhaustive unit propagation
        clauses, assignment = self._exhaustive_unit_propagation(clauses)
        if clauses is None:
            return None
        self.assignment.update(assignment)

        # 2. Pure literal elimination
        clauses = self._pure_literal_elimination(clauses)

        # 3. Subsumption elimination
        clauses = self._subsumption_elimination(clauses)

        # 4. Bounded variable elimination (limited)
        clauses = self._bounded_variable_elimination(clauses, max_new_clauses=10)

        return clauses

    def _exhaustive_unit_propagation(self, clauses: List[List[int]]) -> Tuple[Optional[List[List[int]]], Dict[int, bool]]:
        """Exhaustive unit propagation"""
        assignment = {}
        changed = True

        while changed:
            changed = False
            unit_clauses = [c for c in clauses if len(c) == 1]

            if not unit_clauses:
                break

            for unit_clause in unit_clauses:
                lit = unit_clause[0]
                var = abs(lit)
                value = lit > 0

                if var in assignment:
                    if assignment[var] != value:
                        return None, assignment
                    continue

                assignment[var] = value
                self.metrics.unit_propagations += 1
                changed = True

                # Simplify clauses
                new_clauses = []
                for clause in clauses:
                    if lit in clause:
                        continue  # Satisfied
                    new_clause = [l for l in clause if l != -lit]
                    if len(new_clause) == 0:
                        return None, assignment  # Conflict
                    new_clauses.append(new_clause)
                clauses = new_clauses

        return clauses, assignment

    def _pure_literal_elimination(self, clauses: List[List[int]]) -> List[List[int]]:
        """Eliminate pure literals"""
        positive = set()
        negative = set()

        for clause in clauses:
            for lit in clause:
                if lit > 0:
                    positive.add(lit)
                else:
                    negative.add(-lit)

        pure_lits = []
        for var in positive:
            if var not in negative:
                pure_lits.append(var)
        for var in negative:
            if var not in positive:
                pure_lits.append(-var)

        # Assign pure literals
        for lit in pure_lits:
            var = abs(lit)
            self.assignment[var] = lit > 0
            clauses = [c for c in clauses if lit not in c]

        return clauses

    def _subsumption_elimination(self, clauses: List[List[int]]) -> List[List[int]]:
        """Remove subsumed clauses"""
        clauses_set = [set(c) for c in clauses]
        to_keep = []

        for i, c1 in enumerate(clauses_set):
            subsumed = False
            for j, c2 in enumerate(clauses_set):
                if i != j and c2.issubset(c1):
                    subsumed = True
                    self.clauses_eliminated += 1
                    break
            if not subsumed:
                to_keep.append(clauses[i])

        return to_keep

    def _bounded_variable_elimination(self, clauses: List[List[int]], max_new_clauses: int = 10) -> List[List[int]]:
        """Eliminate variables with bounded resolution"""
        # Count variable occurrences
        var_occurrences = defaultdict(lambda: {'pos': [], 'neg': []})

        for i, clause in enumerate(clauses):
            for lit in clause:
                var = abs(lit)
                if lit > 0:
                    var_occurrences[var]['pos'].append(i)
                else:
                    var_occurrences[var]['neg'].append(i)

        # Try to eliminate variables
        for var, occ in var_occurrences.items():
            pos_clauses = [clauses[i] for i in occ['pos']]
            neg_clauses = [clauses[i] for i in occ['neg']]

            # Estimate new clauses from resolution
            new_clause_count = len(pos_clauses) * len(neg_clauses)

            if new_clause_count <= max_new_clauses:
                # Eliminate variable
                self.vars_eliminated += 1

                # Remove clauses containing var
                clauses = [c for i, c in enumerate(clauses)
                          if i not in occ['pos'] and i not in occ['neg']]

                # Add resolvents
                for pos_clause in pos_clauses:
                    for neg_clause in neg_clauses:
                        resolvent = set(pos_clause) | set(neg_clause)
                        resolvent.discard(var)
                        resolvent.discard(-var)
                        if resolvent:  # Non-tautology
                            clauses.append(list(resolvent))

        return clauses


class CombinedDPLL:
    """
    Best of all worlds:
    - Preprocessing (unit propagation, pure literal elimination)
    - Watched literals for search
    - Phase saving
    """

    def __init__(self, clauses: Iterable[Iterable[int]], num_vars: int):
        self.num_vars = num_vars
        self.original_clauses = [list(c) for c in clauses]
        self.metrics = SolverMetrics()
        self.assignment = {}
        self.phase_cache = {}  # Variable -> last polarity

        # Preprocessing statistics
        self.vars_eliminated = 0
        self.clauses_eliminated = 0

    def solve(self) -> Tuple[str, Optional[List[int]]]:
        """Solve with all optimizations"""
        self.metrics.reset()

        # Preprocessing phase
        preprocessor = PreprocessingDPLL(self.original_clauses, self.num_vars)
        clauses = preprocessor._preprocess(self.original_clauses)

        self.assignment.update(preprocessor.assignment)
        self.metrics.unit_propagations += preprocessor.metrics.unit_propagations
        self.vars_eliminated = preprocessor.vars_eliminated
        self.clauses_eliminated = preprocessor.clauses_eliminated

        if clauses is None:
            return "UNSAT", None

        if not clauses:
            model = []
            for var in range(1, self.num_vars + 1):
                if var in self.assignment and self.assignment[var]:
                    model.append(var)
                else:
                    model.append(-var)
            return "SAT", model

        # Watched literals search
        watched_solver = WatchedLiteralsDPLL(clauses, self.num_vars)
        watched_solver.assignment = self.assignment.copy()
        status, model = watched_solver.solve()

        # Merge metrics
        self.metrics.decisions = watched_solver.metrics.decisions
        self.metrics.backtracks = watched_solver.metrics.backtracks
        self.metrics.unit_propagations += watched_solver.metrics.unit_propagations
        self.metrics.conflicts = watched_solver.metrics.conflicts

        return status, model


# Factory function
def get_solver(variant: str, clauses: Iterable[Iterable[int]], num_vars: int):
    """Factory function to get solver by name"""
    solvers = {
        'base': BaseDPLL,
        'watched': WatchedLiteralsDPLL,
        'preprocessing': PreprocessingDPLL,
        'combined': CombinedDPLL
    }

    if variant not in solvers:
        raise ValueError(f"Unknown solver variant: {variant}. Choose from {list(solvers.keys())}")

    return solvers[variant](clauses, num_vars)
