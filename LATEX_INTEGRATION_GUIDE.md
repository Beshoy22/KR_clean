# LaTeX Integration Guide

## ✅ Files Now Compatible with Springer Nature Template

Both files have been updated to work directly with your `sn-jnl` document class:

- `algorithms_pseudocode.tex` - 4 DPLL algorithm pseudocodes
- `results_tables.tex` - 5 results tables

## 📝 How to Include in Your Paper

### Option 1: Use \input (Recommended)

Add where you want the algorithms/tables to appear:

```latex
\section{Methodology}\label{sec3}

% ... your text ...

\subsection{DPLL Variants}

Here we present the four DPLL algorithm variants tested in our experiments.

% Include all 4 algorithms
\input{algorithms_pseudocode.tex}

% Continue with your text...
```

For tables:

```latex
\section{Results}\label{sec5}

% ... your text ...

% Include all 5 tables
\input{results_tables.tex}

% Continue with your text...
```

### Option 2: Copy-Paste Individual Algorithms/Tables

Open `algorithms_pseudocode.tex` and copy just the algorithm you need:

```latex
\section{Methodology}\label{sec3}

\subsection{Base DPLL}

We implement a baseline DPLL solver with naive unit propagation:

% Copy Algorithm 1 from algorithms_pseudocode.tex (lines 6-51)
\begin{algorithm}[H]
\caption{Base DPLL}
\begin{algorithmic}[1]
...
\end{algorithmic}
\end{algorithm}
```

Same for tables - copy individual tables from `results_tables.tex` as needed.

## 🔧 Placement in Your Paper

Based on your current structure:

```latex
\section{Algorithm}\label{sec3}

% Your existing DPLL algorithm is already here
% You can replace or supplement it with the 4 variants:

\input{algorithms_pseudocode.tex}

% This will add all 4 algorithms right after your existing one
```

```latex
\section{Results}\label{sec5}

% Add tables here:
\input{results_tables.tex}

% Or add them individually:
% Copy Table 1 (Performance Summary)
% Copy Table 2 (Statistical Significance)
% etc.
```

## 📊 Which Tables/Algorithms to Include

### Recommended for Paper:

**Algorithms (in Methodology section):**
- Algorithm 1: Base DPLL - shows baseline
- Algorithm 2: Watched Literals DPLL - shows main optimization
- Algorithm 3 or 4: Pick one (Preprocessing OR Combined)

**Tables (in Results section):**
- **Table 1**: Performance Summary - MUST INCLUDE (shows main results)
- **Table 3**: Speedup Factors - MUST INCLUDE (shows 106× speedup!)
- **Table 2**: Statistical Significance - Include if you want p-values
- **Table 4**: Solver Metrics - Include if discussing propagation behavior
- **Table 5**: SAT/UNSAT Breakdown - Optional, for detailed analysis

## ⚠️ Important Notes

1. **Packages Already Included**: Your template already has:
   - `\usepackage{algorithm}`
   - `\usepackage{algpseudocode}`
   - `\usepackage{booktabs}`

   So no additional packages needed!

2. **Floats May Move**: LaTeX may move `[H]` floats. If you want exact placement:
   - Change `[H]` to `[htbp]` for more flexibility
   - Or use `[!t]` to force top of page

3. **Page Breaks**: With 4 algorithms + 5 tables, expect 3-4 pages of content
   - Consider spreading across sections
   - Use `\clearpage` to force page breaks if needed

## 🎯 Quick Test

To test if files work, add this to your paper after `\section{Results}`:

```latex
\section{Results}\label{sec5}

\input{results_tables.tex}

\section{Discussion}\label{sec6}
```

Compile and check for errors. If it compiles, you're good to go!

## 🐛 Common Issues & Fixes

### Error: "Undefined control sequence \botrule"

Some Springer templates use `\bottomrule` instead of `\botrule`.

**Fix**: In `results_tables.tex`, replace all `\botrule` with `\bottomrule`

```bash
sed -i 's/\\botrule/\\bottomrule/g' results_tables.tex
```

### Error: "Float(s) lost"

Too many floats.

**Fix**: Add `\clearpage` between sections:

```latex
\section{Results}
\input{results_tables.tex}
\clearpage
\section{Discussion}
```

### Error: "Multiply defined labels"

If you have duplicate `\label{tab:performance}` etc.

**Fix**: Rename labels to be unique:
```latex
\label{tab:dpll-performance}
\label{tab:dpll-statistics}
```

## ✅ Testing Your Integration

1. **Compile your main document**:
   ```bash
   pdflatex main.tex
   ```

2. **Check output**:
   - Algorithms should have numbered captions
   - Tables should be formatted with booktabs style
   - References like `Table~\ref{tab:performance}` should work

3. **If errors occur**:
   - Check the error message
   - Look for the line number
   - See "Common Issues & Fixes" above

---

**Files are ready to use!** Just `\input` them or copy-paste the specific algorithms/tables you need.
