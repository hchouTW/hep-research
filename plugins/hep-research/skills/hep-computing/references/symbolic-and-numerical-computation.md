# Symbolic and numerical computation (SymPy, SciPy)

Use when the deliverable is a symbolic derivation checked by computer, a numerical integral, an ODE solution, a root
or a minimum, and the question is whether the number is right to the precision claimed. The validation ladder
(known case, convergence, sensitivity, independent method, sanity) is in
[numerical and computational methods](numerical-and-computational-methods.md); this file is the code-level
checklist. Pick the interpreter first with `<plugin root>/skills/hep-computing/scripts/find_python.py --require sympy scipy`
and record the versions it reports.

Every snippet below was run on 2026-10-13 with SymPy 1.14.0, SciPy 1.18.1, NumPy 2.5.3 (Python 3.13); the numbers
quoted are from that run.

## Decision rules

1. Every number leaves with an error estimate and the setting that produced it (tolerance, number of points,
   method). A result without one is unvalidated.
2. One run is not convergence: repeat with the tolerance tightened by a factor of 10 (or the grid refined by 2) and
   report the change. If the conclusion moves, the first run was not converged.
3. Cross-check with a second method on at least one point: a different integrator, an analytic limit, a series,
   or the symbolic result evaluated numerically.
4. Read the solver's status, not only its value: `quad`'s warnings, `solve_ivp`'s `status` and `message`,
   `minimize`'s `success`. In the run above, BFGS on the Rosenbrock function with `tol=1e-10` returned a point near
   (1, 1) with `success=False` ("Desired error not necessarily achieved due to precision loss").
5. Stop when the stated accuracy target is met and the cross-check agrees within it.

## SymPy

- Declare assumptions: `sp.sqrt(x**2)` stays `sqrt(x**2)` for a plain symbol and becomes `x` for
  `sp.symbols("x", positive=True)`. Wrong or missing assumptions are the commonest reason a simplification "fails"
  or a wrong one "succeeds"; state them (`real`, `positive`, `integer`) as the physics demands, not to make
  `simplify` work.
- `simplify` is a heuristic with no completeness guarantee: a result that does not simplify to 0 is not proof that
  two expressions differ. Try targeted rewrites (`expand`, `factor`, `trigsimp`, `powsimp`, `cancel`) and, always,
  a numeric check.
- Numeric identity check: `f = sp.lambdify(x, lhs - rhs, "math")` and evaluate at random points in the physical
  domain (and near its edges); for `sin(x)**2 + cos(x)**2 - 1` the largest residual over 100 points was 2.2e-16.
  A residual far above rounding at any point means the identity is false there (or a branch cut was crossed).
- Exact arithmetic: keep inputs as `sp.Rational(1, 3)` or `sp.S("1/3")`, not `1/3` (a Python float) when the
  result must be exact; convert at the end with `.evalf(n)` for `n` digits.
- `lambdify` to `"numpy"` for arrays, `"math"` or `"mpmath"` for scalars and high precision. The generated function
  inherits floating-point cancellation the symbolic form hid: check it against `.evalf` at a few points.
- Units and conventions (metric signature, factors of 2 pi, natural units) are physics, not SymPy: they come from
  hep-theory, and the code states them in its header.

## Integration with `scipy.integrate.quad`

- `val, err = quad(f, a, b)` returns an absolute error estimate; report both, and pass `epsabs`/`epsrel` when the
  default (`1.49e-8`) is not what the result needs.
- Integrable endpoint singularities are handled: `quad(lambda t: 1/sqrt(t), 0, 1)` gave 1.9999999999999993 with an
  estimate of 3.8e-15. Interior kinks and discontinuities: pass them with `points=[...]` (the `|t - 0.3|` integral
  took 357 evaluations without and was split at the kink with).
- Narrow peaks are missed silently: a Gaussian of width 0.007 at 50 on [0, 100] returned 3.7e-52 with an error
  estimate of 0.0, and still 3.7e-52 with `points=[50]` (the peak sat at a subinterval edge where no node falls).
  Splitting the range explicitly ([0, 49.9], [49.9, 50.1], [50.1, 100]) gave 0.0177245385090 against the exact
  0.0177245385091. Know where the integrand lives before integrating it.
- Infinite ranges are allowed (`-np.inf`, `np.inf`): the Gaussian integral gave sqrt(pi) to 1e-16 with an estimate
  of 1.4e-8. For slowly decaying tails, change variables (`t = 1/u`) and check both forms agree.
- Oscillatory integrands: `weight="cos"`/`"sin"` with `wvar`, or integrate period by period; a plain `quad` on many
  periods hits its subdivision `limit` (default 50) and warns. Raise `limit` only together with a cross-check.
- Second method: `scipy.integrate.fixed_quad`/Gauss-Legendre at increasing order, Monte Carlo with its standard
  error, or the analytic value in a limit.

## ODEs with `scipy.integrate.solve_ivp`

- Method: `RK45` (default) for non-stiff problems; `Radau`, `BDF` or `LSODA` for stiff ones (rates differing by many
  orders of magnitude, decays, chemical-like networks). On the stiff Robertson system to t = 100, `RK45` needed
  729,668 function evaluations and `Radau` 726, with the same final state to 6 digits.
- Tolerances: `rtol` (default 1e-3) and `atol` (default 1e-6) set the local error per step, not the global error.
  Set `atol` below the smallest component that matters (components near 0 otherwise have no accuracy). For
  `y' = -y` to t = 5 the global error was 1.3e-6, 1.0e-7 and 7.6e-11 at `rtol` 1e-4, 1e-5, 1e-8.
- Tolerance check: rerun at `rtol/10` (and `atol/10`) and report the largest change of the quantities you publish;
  it must be below the accuracy you claim.
- Events: a function `g(t, y)` with `g.terminal = True` stops the integration where `g` crosses zero; for
  `y' = -y`, `y = 0.5` was located at 0.69314718 (ln 2 = 0.6931471806). Events are located to the solver's
  tolerance, so set it to the precision the event time needs.
- Check `sol.status` (0: reached the end, 1: a terminal event, -1: failed) and `sol.message`; a failed integration
  still returns the points it reached.

## Roots and minima

- Bracketing root finders (`scipy.optimize.brentq`, `bisect`) are guaranteed inside a sign change; pass `xtol` and
  `rtol` (brentq on `t**3 - 2` with `xtol=1e-14` matched 2**(1/3) to all printed digits). Open methods (`newton`)
  need a good start and can jump to another root: check the residual and the bracket afterwards.
- `scipy.optimize.minimize`: read `success` and `message`, check the gradient at the result, and restart from
  another starting point; a local minimizer finds a local minimum. Likelihood fits belong to hep-statistics.

## Record

The `computational-run` record lists the interpreter and package versions, the method and tolerances of every
solver, the convergence check (setting, change) and the cross-check (method, agreement).

## Handoffs

- Deriving the expression, its conventions and its validity domain: hep-theory.
- Fits, intervals, toys and their coverage: hep-statistics.
- Code speed: [performance profiling](performance-profiling.md).
