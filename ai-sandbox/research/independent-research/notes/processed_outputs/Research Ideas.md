---
source_docx: Research Ideas.docx
word_count: 1884
conversion_warnings: 0
tags: [development-economics, heterodox-economics]
---

Research Ideas:

# <a id="_1644or29n1cf"></a>Random Notes

- Combination of heterodox economics with novel empirical methods, focused on real-time / big data, to get away from neoclassical “small world” models based on assumptions and methodological frameworks. 
	- Investigate “what the data is saying” to determine “what is going on here” and interpret that according to various economic rationales, presenting various options of interpretations, historical parallels, and policy recommendations based on related evidence
- Development economics without the patronizing approach to “developing” economies, with a focus on intra-national disparities, to improve equity and safeguards / programs for vulnerable / low-income / at-risk people
- Focus on applications in policy / programs / interventions, not just theories; contextually situated cases, not global assumptions
	- Focus on both domestic issues locally and in areas where I have cultural competency (South America, Eastern Europe)
- Culturally sensitive / non-imperialist economics that doesn’t assume Western enlightenment moral foundations for utilitarianism
	- Using local language, dissemination
- Focus on improving policies / programs / interventions for working class rather than “macroeconomic stability” for investors and capitalists
	- Investigating wage stagnation and oligopoly power in rich world
	- Impacts of AI and technology on work / labor / unemployment
- Methodological focus on diverse data analysis, beyond traditional econometrics and panel data; mixed methods using NLP / LLM to supplement quant / admin data
	- Away from “average” effects, national statistics, “optimizing” solutions
	- Towards particular targeting, distributional effects, impacts on vulnerable
	- Accountability to results / progress via rigorous MEL focus
- Gender inclusive, anti-racist approach; understanding and undoing systemic oppression through improved economic policies / development interventions
- Mixing traditional “rich world” solutions (social safety net) with “development” solutions (microfinance, aid programs, etc) to better suit diverse societies
	- USA has elements of society that require more “development” focused interventions, while middle income countries work to build social safety net programs; how to combine them to ensure sustainability, local ownership, democratic engagement, balancing international relations with donor engagement, etc.

# <a id="_ll8j6tt3v5il"></a>Multidimensional Welfare & Vector Optimization

Rather than collapsing economic complexity into a single 1-dimensional price or welfare index, my research explores using multi-functional matrix systems and choice correspondences to map resource allocations directly into multi-dimensional value spaces (e.g., balancing efficiency, equity, and sustainability). This framework utilizes higher-codimension affine subspaces and vector-maximum theorems to rigorously model political-economy trade-offs and policy mechanism design on a smooth, continuous Pareto frontier.

# <a id="_4xit0ynl0o5m"></a>Agent Based Models for Climate and Conflict Shocks

- Combine geospatial data on climate models, agricultural production, demographics, population distribution, transportation networks, observed conflict events, mobile networks, health and emergency services, and humanitarian response to model mitigation vs adaptation, preparedness vs response, comparing costs vs lives saved, economic and ecological recovery, human displacement
	- Model varying potential interventions

# <a id="_d4o5srwxlhjm"></a>ML Global Approximations vs. Causal Interpretability in Dynamic Models

__The Core Problem: Dimensionality vs. Interpretability__

- __The Grid Trap:__ Traditional global solution methods (like splines) suffer from the curse of dimensionality. Attempting to solve a model with dozens of interacting variables (e.g., massive spatiotemporal climate and agricultural state spaces) creates an exponentially uncomputable hypercube.
- __The ML Solution:__ Deep Neural Networks (DNNs) bypass this using __mesh-free__ approximation. By stochastically sampling the ergodic set (where the system actually spends its time) and using gradient descent to minimize equation errors, DNNs easily solve high-dimensional systems.
- __The Black Box Trade-off:__ While DNNs provide unprecedented global accuracy, they destroy mechanistic interpretability. You lose the cleanly defined partial derivatives required to isolate marginal effects and defend specific causal policy interventions.

__The Pitfalls of Uncertainty & Bias__

- __Epistemic Uncertainty:__ We can map a DNN's ignorance using Monte Carlo simulations (e.g., Monte Carlo Dropout) to find where prediction errors blow up—usually during rare, extreme shocks outside the ergodic set. This yields *reliability* (we know where the model is guessing) but still fails to recover causal mechanisms.
- __Spectral Bias (The Danger Zone):__ Neural networks naturally prioritize learning smooth, generalized, low-frequency functions. In environmental and economic systems defined by sharp, highly non-linear thresholds (like sudden ecological collapses or critical agricultural tipping points), the DNN will likely "smooth over" the crisis, embedding a dangerous structural bias into its predictions.

__Potential Research Question (The Frontier):__ How can we bridge the gap between computational power and structural econometrics? Specifically, can we design loss functions or hybrid architectures that force mesh-free ML algorithms to mathematically respect sharp, non-linear ecological tipping points while maintaining the rigorous causal inference needed to evaluate sustainable development interventions?

# <a id="_cbh3f59v5ybi"></a>Microeconomic Optimization Alternatives to Theoretical Analytic Approaches

The tension between structural analytical modeling and non-parametric or data-driven optimization is a central methodological debate in modern econometrics and quantitative economics. Your assessment is correct: the traditional analytical Lagrangian paradigm requires the ex-ante specification of a functional form (e.g., Cobb-Douglas, CES, Translog), meaning the resulting optimization is conditional on those structural assumptions.

When starting directly with observed data from an economy, bypassing rigid functional forms to avoid misspecification bias is a primary motivation for utilizing alternative mathematical toolkits. However, the solution is generally not to apply heuristic search algorithms like hill climbing to the raw data, but rather to use __shape-constrained non-parametric estimation__ or __algorithmic data-driven optimization__.

The comparative benefits, mathematical trade-offs, and methodology of optimizing without preconditioning on an assumed functional form are structured as follows:

## <a id="_vo4djejfz329"></a>__1. Non-Parametric Optimization: Data Envelopment Analysis (DEA)__

If your objective is to evaluate profit maximization or cost minimization for a firm producing $n$ products using $m$ inputs without assuming a production function $f(x)$, the standard economic approach relies on __Data Envelopment Analysis (DEA)__ or __Stochastic Frontier Analysis (SFA)__.

Instead of assuming a specific algebraic form, DEA uses linear programming to construct an empirical production possibility frontier directly from the observed input-output vectors of all firms in the data.

- __The Mathematical Mechanism:__ Axiomatic properties derived from microeconomic theory—such as monotonicity (inputs are goods) and convexity of the technology set—are imposed as linear inequality constraints. The optimization problem for a specific firm's efficiency score $\theta^*$ is formulated as a linear program:
- $$\begin{aligned} \text{maximize } & \theta \\ \text{subject to } & \sum_{j=1}^{J} \gamma_j y_{nj} \ge \theta y_{n0}, \quad \forall n=1, \dots, N \\ & \sum_{j=1}^{J} \gamma_j x_{mj} \le x_{m0}, \quad \forall m=1, \dots, M \\ & \gamma_j \ge 0 \end{aligned}$$
- where $y_{nj}$ and $x_{mj}$ are the observed outputs and inputs of firm $j$, and $\gamma_j$ represents the weights used to construct the virtual peer firm.
- __The Benefit:__ This is a purely data-driven numerical optimization. It completely avoids functional misspecification bias while remaining entirely disciplined by economic theory (convexity and monotonicity). Because it maps to a linear program, it is solved exactly using the Simplex or Interior Point methods, bypassing the inefficiencies of heuristic search algorithms.

### <a id="_qrhg37q17e0g"></a>1. Data Envelopment Analysis (DEA) in Python

To execute non-parametric optimization directly on observed economic inputs and outputs (bypassing functional forms like Cobb-Douglas), researchers use specialized solvers that wrap linear programming APIs.

A prominent library for this is __Pyfrontier__ (or alternatively pyDEA), which handles the optimization loop over individual Decision Making Units (DMUs) using PuLP or SciPy backends.

## <a id="_4dh6egeu6otp"></a>__2. Shape-Constrained Non-Parametric Econometrics__

A closely related alternative is to estimate the unknown utility or production function non-parametrically using the observed data, while explicitly constraining the estimator to satisfy structural economic axioms.

- __Methodology:__ Rather than estimating a standard unconstrained polynomial or kernel regression—which can yield non-monotonic or non-concave functions due to finite-sample noise—you solve a __Shape-Constrained Kernel Estimation (SCKE)__ or __Sieve Estimator__ problem.
- __The Optimization Problem:__ The estimator minimizes the sum of squared residuals subject to the mathematical requirements that the first derivative is non-negative and the second derivative matrix (Hessian) is negative semi-definite at all data points:
- $$\begin{aligned} \text{minimize } & \sum_{i=1}^{N} \left( y_i - \hat{f}(x_i) \right)^2 \\ \text{subject to } & \nabla \hat{f}(x_i) \ge \mathbf{0}, \quad \nabla^2 \hat{f}(x_i) \preceq \mathbf{0} \quad \forall i \end{aligned}$$
- __The Numerical Framework:__ This optimization cannot be solved analytically via standard Lagrangians because $\hat{f}$ lives in an infinite-dimensional function space. Instead, it is projected onto a finite-dimensional basis (sieves) and solved numerically using __Semi-Definite Programming (SDP)__ or __Constrained Spline Optimization__.

### <a id="_r85k59z5b8a"></a>2. Shape-Constrained Optimization (Imposing Curvature Constraints)

If you choose to use data-driven methods but need to ensure the estimated function complies with microeconomic axioms (such as marginal utility diminishing with consumption, meaning a strictly concave function where $\nabla^2 f \preceq 0$), simple unconstrained regressions fall short.

The library __gamfit__ (or shape-constrained additive models in packages like scikit-shapes or R's scam) solves this by binding the regression coefficients via inequality constraints during optimization.

#### <a id="_syu6407t5p7q"></a>The Optimization Loop Mechanics

If you look into the core source code of shape-constrained optimization engines (often written in optimized backends like C++ or Rust to speed up loop execution), the library sets up a penalised spline objective.

To enforce shape=concave, the package sets up a system of second-difference matrix inequalities on the spline coefficients vector $\beta$:

$$\mathbf{D}_2 \beta \le \mathbf{0}$$

It then passes this system to a __Quadratic Programming (QP)__ solver using active-set or interior-point methods. The solver steps through iterations until it minimizes the squared errors while strictly keeping the KKT stationarity conditions within the feasible, concave boundaries.

## <a id="_6656t8yde8ya"></a>__3. Structural vs. Non-Parametric: The Methodological Trade-offs__

If non-parametric numerical methods allow you to optimize without assuming a functional form, why do structural analytical models persist? The choice depends on the trade-off between __internal validity (robustness to misspecification)__ and __counterfactual policy invariance__.

__Dimension__

__Structural Analytical Approach (Assumed Functional Form)__

__Data-Driven / Non-Parametric Numerical Approach__

__Misspecification Bias__

__High risk.__ If the true technology is translog but you assume Cobb-Douglas, your optimization results and elasticity estimates will be fundamentally biased.

__Minimal risk.__ The data dictates the shape of the frontier or function; the model adapts to arbitrary curvatures.

__Data Requirements__

__Low.__ Can calibrate parameters (e.g., share parameters $\alpha$) using a small number of empirical moments or baseline data points.

__High.__ Non-parametric convergence rates suffer from the "curse of dimensionality" as the number of inputs $m$ and outputs $n$ increases.

__Counterfactual Analysis__

__High capacity.__ Because the parameters capture invariant deep structural primitives (e.g., risk aversion, technological substitution elasticity), you can simulate behavior under entirely new economic regimes or out-of-sample price shocks (__Lucas Critique__ compliance).

__Limited capacity.__ Non-parametric frontiers are only valid within the support of the observed data. They cannot reliably predict optimization behavior under an unprecedented policy shock or price regime.

__Economic Interpretability__

__Direct.__ Multipliers map explicitly to shadow prices; parameters map to marginal rates of substitution.

__Indirect.__ Results are often represented as empirical efficiency distributions or localized numerical gradients.

## <a id="_coemz6d9ad3h"></a>

## <a id="_uqvulepyiahr"></a>__4. Bridging the Gap: The Structural Estimation Paradigm__

Modern empirical economics rarely chooses between pure ungrounded theory and pure unstructured data optimization. Instead, the standard paradigm is __Structural Estimation__ (e.g., using Mathematical Programming with Equilibrium Constraints, or MPEC).

In this framework, the researcher assumes a flexible functional form (like a normalized quadratic or a random-coefficients logit) but treats the structural parameters as unknowns to be estimated. The algorithm nests the firm's or consumer's analytical optimization problem *inside* an empirical optimization loop (such as Maximum Likelihood or Generalized Method of Moments). The external loop optimizes over the parameter space to find the values that make the analytically derived optimal choices match the observed empirical distribution as closely as possible.
