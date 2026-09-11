## 1. Introduction

The objective of constructing a novel omnibus normality test utilizing a penalized empirical process is methodologically ambitious and mathematically sound. To strengthen the paper for publication or inclusion in a broader dissertation, the introduction must better situate the necessity of such a test within modern empirical frameworks. Standard normality tests often fail in high-dimensional or computationally intensive contexts, such as evaluating residuals in machine learning models applied to remote sensing data or analyzing spatial autoregressive models in development economics. Expanding the introduction to explicitly reference the limitations of the Shapiro-Wilk test in the presence of heavy-tailed distributions typical of climate and agricultural yield data will provide a stronger applied motivation for an omnibus alternative.

  

## 2. Theoretical Foundations

Expanding the theoretical foundations requires connecting the proposed approach to a broader set of established theorems and alternative normality tests.

  

### 2.1 The Shapiro-Wilk Test

While the Shapiro-Wilk (SW) test serves as a natural benchmark due to its power properties, an expanded literature review must address other prominent empirical distribution function (EDF) tests. Include analytical comparisons with the Anderson-Darling test, which places heavier weight on the tails of the distribution, and the Jarque-Bera (Bowman-Shenton) test, which directly utilizes sample skewness and kurtosis. Discussing these alternatives establishes why a penalized Generalized Least Squares (GLS) approach over the empirical process might capture deviations that EDF and moment-based tests miss.

  

### 2.2 Generalized Least Squares Regression

The transition from Ordinary Least Squares (OLS) to GLS to handle the correlated errors of the ordered empirical process is structurally correct. The literature review here should be expanded to discuss the application of feasible generalized least squares (FGLS) in spatial econometrics, where accounting for autocorrelation matrix structures is standard practice. Connecting the covariance matrix of the standardized probability integral transform to spatial or temporal weighting matrices will enrich the theoretical context.

  

### 2.3 Penalized Regression

The discussion of $L_1$ and $L_2$ penalties should briefly touch upon the Elastic Net to demonstrate a comprehensive understanding of regularization. The theoretical justification for introducing bias to control variance in the predictor function is accurate, but the section would benefit from a formal proof demonstrating the convergence properties of $\hat{\beta}_{PGLS}$ as the penalty parameter varies.

  

### 2.4 Smoothing Splines

The distinction drawn between true smoothing splines defined over a continuous domain and the discrete basis vector approach employed in the paper is a critical theoretical differentiation. To elevate this section, introduce the concept of Reproducing Kernel Hilbert Spaces (RKHS). Framing the discrete roughness penalty as a finite-dimensional approximation of an RKHS norm will provide a highly rigorous mathematical foundation for the penalty term.

  

### 2.5 Basis Vectors and Eigenvectors

The selection of eigenvectors derived from the covariance matrix $\sigma$ to form the basis $X$ is analogous to Principal Component Analysis (PCA). The literature review should explicitly state this connection, noting that the eigenvectors spanning $\mathbb{R}^n$ orthogonally decompose the variance of the empirical process.

  

### 2.6 Generalized Lambda and Generalized Pareto Distributions

The use of the Generalized Pareto Distribution (GPD) and Generalized Lambda Distribution (GLD) via L-moments allows for precise manipulation of skewness and kurtosis. The review should reference extreme value theory, where GPD is foundational. This is particularly relevant for applications modeling extreme deviations, such as climatic shocks in sustainable development models.

  

## 3. Methods

The methodology requires a critical re-evaluation of parameter selection and asymptotic properties to ensure analytical rigor.

  

### 3.1 Sampling from Empirical Process and Estimation of Covariance Matrix

The approximation of the expected value of the uniform order statistic as $E[s(i)] \approx \frac{i}{n+1}$ is standard but introduces approximation error in small samples. The methodology should evaluate the use of exact expected values or alternative plotting positions, such as Blom or rankit scores, to determine if the approximation systematically biases the zero-mean process $s^*(i)$.

  

### 3.2 Construction of the Penalized Generalized Least Squares Objective Function

The objective function successfully integrates the GLS estimator with a discrete roughness penalty $P = X^T D^T D X$. However, the reliance on a static weighted first-difference matrix $D$ assumes that adjacent order statistics capture the entirety of the function's roughness. A methodological critique must address whether second-order differences or a varying bandwidth approach would yield a more optimal smoothing matrix $H$.

  

### 3.3 Choice of the Design Matrix X

Utilizing the eigenvectors of $\sigma$ correctly aligns the regression with the directions of maximal variance. However, because eigenvectors are global over the domain, they may poorly approximate highly localized deviations in the empirical process. Testing B-splines or localized polynomial bases as alternative design matrices could significantly alter the test's sensitivity to specific non-normal departures.

  

### 3.4 Construction of the Test Statistic

The Mahalanobis distance test statistic $g = \hat{\beta}_{PGLS}^T C^{-1} \hat{\beta}_{PGLS}$ weights all orthogonal deviations equally. Because higher-order eigenvectors represent noise rather than systematic structural departures from normality, the methodology should explore applying a decay function to the weights in $C^{-1}$. Truncating or penalizing the influence of lower-variance eigenvectors could improve the power of the test.

  

### 3.5 Simulation for Known Non-Normal Distributions

The limitation of the simulation to a sample size of $n=20$ is the most significant structural weakness of the methodology. A rigorous omnibus test must establish finite sample performance across various sizes ($n=50, 100, 500, 1000$) and prove its asymptotic distribution as $n \to \infty$. Furthermore, the arbitrary selection of $\lambda = 2,000,000$ to force 4 degrees of freedom is methodologically unsound. Generalized Cross-Validation (GCV) or restricted maximum likelihood (REML) must be implemented to select $\lambda$ optimally for each sample.

  

## 4. Empirical Results

The interpretation of the Monte Carlo simulations requires deeper analytical parsing of why the proposed test underperforms against Shapiro-Wilk in specific contexts.

  

### 4.1 Comparison of t-, chi-square, and gamma distribution results

The Penalized GLS (PGLS) test matches SW for the symmetric t-distribution but exhibits a 10 to 20 percentage point deficit in power for the asymmetric gamma and chi-square distributions. This discrepancy suggests the roughness penalty $P$ or the eigenvector basis $X$ is mathematically constrained when capturing asymmetric directional skew. The critique should investigate whether the discrete derivative matrix $D$ forces an artificial symmetry on the smoothed predictions.

**This is the spine of the rewrite, not one empirical-results item among several.** A generic omnibus test that roughly matches Shapiro-Wilk is not a strong thesis result; a specific, falsifiable mechanism — the symmetric penalty structurally under-fitting skewed deviations — followed through to an asymmetry-aware fix is. It is also the one result in this manuscript that connects directly to substantive motivation: climate-shock and agricultural-yield residuals are exactly the heavy-tailed, skewed distributions where this gap would matter in practice (see §5 and Phase 5 below). Reframe the introduction and conclusion around this mechanism explicitly, rather than treating it as a limitation to note in passing.

  

### 4.2 Comparison for Generalized Pareto Distribution

The performance of PGLS mirroring SW for near-normal GPDs (where L-skew and L-kurtosis approach zero) is expected. However, the failure of both tests in these regimes highlights the fundamental limit of distinguishing minute structural deviations from finite-sample noise.

  

## 5. Conclusions and Further Research

To finalize the thesis, the further research section must transition from theoretical parameter tuning to concrete applied empirics. Propose implementing the PGLS normality test to evaluate the residual distributions of large-scale predictive models, such as machine learning algorithms used to forecast agricultural yields from satellite imagery. If the error terms in such models exhibit heavy tails that the PGLS test captures more effectively than the SW test, the practical utility of the novel omnibus approach is immediately validated.

  

## 6. References

The bibliography is heavily weighted toward foundational texts (e.g., Shapiro & Wilk, 1965; Craven & Wahba, 1979). An expanded literature review necessitates the inclusion of modern computational statistics papers, specifically recent advancements in high-dimensional covariance matrix estimation and regularized empirical processes.

  

## 7. Acknowledgments

No methodological critique is required for this section.

  

## 8. Appendix: R Code to Reproduce Results

The provided computational implementation requires optimization for the test to be scalable beyond $n=20$.

  

### 8.1 Main PGLS Test Script

The loop structure utilized for the Monte Carlo simulations limits computational efficiency. Matrix operations should be vectorized where possible, and parallel processing architectures (e.g., the `parallel` or `foreach` packages in R) must be integrated to facilitate simulations for large $n$.

  

### 8.2 Function to Generate All Plots

The graphical output relies on base R plotting functions. Transitioning to `ggplot2` will provide the programmatic flexibility required to overlay theoretical asymptotic density curves against the empirical simulation results.

  

### 8.3 Calculation of Simulation Matrix Function

The calculation of the covariance matrix through repeated random sampling introduces simulation variance into the foundational parameters. Analytical derivation of the covariance matrix of the normal order statistics, or utilizing established tables for smaller $n$, would eliminate this noise.

  

### 8.4 Standardized Residual Function

The standardization loop mapping the sample to the probability integral transform is mathematically correct but computationally heavy. Vectorizing the sorting and mapping processes will drastically reduce overhead during 10,000+ iteration simulations.

  

### 8.5 Distribution and Test Calculation Function

The conditional logic (`if/else`) routing the distribution types should be modularized. Creating a distinct closure for each distribution will clean the namespace and improve runtime efficiency.

  

### 8.6 Helper Function for Distribution Comparison Plot

Density extraction processes should explicitly define the bandwidth selection method (e.g., Silverman's rule of thumb) to ensure transparency in how the kernel density estimates are smoothed prior to visualization.

  

### 8.7 Generalized Pareto Distribution Quantile Function

The closed-form L-moment estimations are executed correctly. Validating these outputs against established numerical limits will ensure floating-point errors do not compound during generation.

  

### 8.8 Generalized Pareto Table Calculation Function

The matrix initialization and scaling algorithms for the L-moments require boundary condition checks. Ensuring that $\lambda$ parameters do not force the GPD into undefined variance regimes is critical before passing the vectors to the main PGLS estimator.





# Step by Step Plan

A structured revision of the manuscript requires a deliberate transition from a computational proof-of-concept to a mathematically exhaustive and empirically scalable omnibus normality test. The current framework successfully synthesizes probability integral transforms, orthogonal variance decomposition, and penalized regression. To achieve the analytical rigor necessary for an advanced academic submission, the revision must sequentially address computational inefficiencies, formalize the functional analysis underpinnings of the penalty parameters, prove asymptotic consistency, and validate the test's power against complex real-world data structures. The following execution plan is ordered by implementation complexity, beginning with immediate computational refactoring and culminating in applied empirical modeling.

  

### Prioritization Note (synced with PhD research timeline, added 2026-09-10)

Four adjustments to the phase plan below, made after checking it against the broader first-year research schedule (`Ground Truth - PhD Research Plan.md`, Project 06):

- **Do Phase 1 and the low-risk Phase 3 items first, in parallel with each other.** Vectorization, deterministic covariance estimation, and the second-order difference matrix are cheap, largely independent of the rest, and unblock everything downstream. Target September–October.
- **Data-driven λ (GCV/REML) changes what "the null distribution" means.** Once λ is selected per-sample rather than fixed, the finite-sample null distribution of the test statistic $g$ is itself selection-dependent — referencing a fixed asymptotic or chi-square distribution after adaptive selection will generally misstate size. Before finalizing Phase 4, recalibrate via a parametric bootstrap that re-runs the GCV/REML selection step under simulated null data, rather than treating the reference distribution as fixed.
- **Eigenvector Influence Decay is a prerequisite for the asymptotic argument, not just a power improvement.** The design matrix $X$ has dimension $n$, so $\hat{\beta}_{PGLS}$ lives in a space that grows with the sample — standard fixed-dimension GLS asymptotics don't directly apply. Truncating/decaying the weight given to higher-order eigenvectors decouples the number of *active* basis directions from $n$, which is very likely what makes a consistency proof well-posed at all. Do this work, and confirm it's stable, before attempting the proof in Phase 4.
- **Treat the full asymptotic-consistency proof as optional/stretch for this revision cycle.** The finite-sample simulation study across $n \in \{50, 100, 500, 1000\}$ carries most of the needed credibility on its own; formal weak-convergence results for a quadratic form in a penalized, growing-dimension GLS estimator are a genuinely open-ended theoretical problem, not a bounded revision task. Push it out rather than let it block everything after it.
- **Push Phase 5 to January 2027**, after Project 04 (the PhD research toolkit that fuses ACLED conflict, IDMC displacement, and climate-shock data into a panel) stabilizes. That gives the applied-validation step real, already-assembled panel-data residuals — climate/conflict/displacement models, not a separately gathered validation dataset — for free.

  

### Phase 1: Computational Optimization and Algorithmic Refactoring (Low Complexity)

The underlying R code requires structural improvements to ensure scalability for larger sample sizes and more rigorous Monte Carlo iterations. These steps involve software engineering adjustments rather than mathematical re-derivations.

  

- **Vectorization of Simulation Matrices:** Replace the `for` loops in the main PGLS script and distribution iterations with vectorized apply functions or parallel processing architecture (e.g., utilizing the `parallel` package). This will significantly reduce the computational overhead when expanding the simulation iterations from $10,000$ to $100,000$ or beyond.
    
      
    
- **Deterministic Covariance Estimation:** Eliminate the simulation variance introduced by randomly estimating the covariance matrix $\sigma$ of the standardized probability integral transform. Substitute this step with exact analytical calculations of expected order statistics or high-precision established tables, ensuring that the design matrix $X$ is perfectly deterministic for a given $n$.
    
      
    
- **Modularize Distribution Functions:** Refactor the conditional `if/else` block mapping the generalized Pareto, generalized lambda, and standard distributions into discrete, self-contained closures to streamline the hypothesis testing execution.
    
      
    

### Phase 2: Theoretical Framing and Literature Integration (Low-Medium Complexity)

The manuscript must explicitly connect the mechanics of the PGLS test to broader subfields in functional analysis and econometrics. This involves expanding the text without necessarily altering the underlying mathematical mechanics.

  

- **Formalize the Roughness Penalty:** Situate the discrete penalty matrix $P = X^T D^T D X$ within the context of Reproducing Kernel Hilbert Spaces (RKHS). Define the finite-dimensional approximation explicitly, demonstrating how the weighted first-difference matrix acts as a discrete analog to minimizing the norm of the second derivative in an RKHS.
    
      
    
- **Connect to Principal Component Analysis (PCA):** Expand Section 3.3 to explicitly define the design matrix $X$ as an orthogonal variance decomposition of the empirical process. Frame the eigenvectors as principal components that capture the geometric direction of departures from normality in descending order of magnitude.
    
      
    
- **Contextualize Generalized Least Squares:** Broaden the literature review in Section 2.2 to parallel the use of Feasible Generalized Least Squares (FGLS) in spatial econometrics. Draw analogies between the correlated errors of the empirical order statistics and spatial or temporal autocorrelation matrices, providing a robust justification for departing from OLS.
    
      
    

### Phase 3: Analytical Parameter Calibration (Medium Complexity)

The arbitrary selection of critical model parameters must be replaced with data-driven, analytically sound optimization techniques.

  

- **Dynamic Penalty Selection:** Remove the static regularization parameter $\lambda = 2,000,000$. Implement Generalized Cross-Validation (GCV) or Restricted Maximum Likelihood (REML) estimators to dynamically select the optimal $\lambda$ that balances fidelity and smoothness for each unique sample matrix. Note: once $\lambda$ is data-dependent, the null distribution of $g$ becomes selection-dependent too — see the recalibration note in the Prioritization Note above before treating any reference distribution as fixed in Phase 4.
    
      
    
- **Advanced Difference Matrices:** Modify the weighted difference matrix $D$ to compute second-order discrete derivatives. While a first-order difference penalizes non-zero slopes, a second-order difference penalizes curvature, strictly aligning the methodology with the $\int \hat{f''}(x_i)^2 dx$ term found in true smoothing splines.
    
      
    
- **Eigenvector Influence Decay:** Reconstruct the Mahalanobis distance test statistic $g = \hat{\beta}_{PGLS}^T C^{-1} \hat{\beta}_{PGLS}$. Introduce a spectral decay function to the inverse covariance matrix $C^{-1}$ that penalizes or truncates the weights of higher-order eigenvectors, which primarily capture white noise rather than systemic structural deviations from the zero vector.
    
      
    

### Phase 4: Asymptotic Evaluation and Finite Sample Scaling (Medium-High Complexity)

A valid omnibus test must define its behavior beyond a single, restricted small-sample environment.

  

- **Expand $n$-Space Simulations:** Execute the optimized PGLS code across a spectrum of finite sample sizes, specifically $n \in \{50, 100, 500, 1000\}$. Document how the comparative power gap between the PGLS approach and the Shapiro-Wilk test behaves as degrees of freedom increase.
    
      
    
- **Derive Asymptotic Properties (optional/stretch, see Prioritization Note above):** Formally define the asymptotic distribution of the test statistic $g$ as $n \to \infty$. Utilize probability limits to prove the consistency of the $\hat{\beta}_{PGLS}$ estimator, establishing that the probability of rejecting a false null hypothesis converges to $1$. Requires the Eigenvector Influence Decay work from Phase 3 first, since $X$'s dimension grows with $n$ and the proof needs the number of active basis directions decoupled from it.
    
      
    

### Phase 5: Applied Empirical Validation (High Complexity)

Theoretical simulations on the chi-square or generalized Pareto distributions serve as a foundation, but the true utility of an omnibus test is proven against real-world econometric or computational data structures that inherently violate Shapiro-Wilk assumptions.

  

- **Analyze High-Dimensional Residuals (target: January 2027, once Project 04 stabilizes):** Apply the fully optimized PGLS test to the residual distributions of large-scale predictive models. First candidate: the causal-ML and panel-data models built for the PhD research toolkit (Project 02/04 — the ACLED/IDMC/climate/cash-transfer fusion), which reuses already-assembled data instead of requiring a separate validation dataset; general candidates beyond that include machine learning algorithms (e.g., random forests or deep neural networks) trained to predict crop yields from satellite remote sensing imagery, where error terms frequently exhibit heavy tails and nonlinear spatial dependencies.
    
      
    
- **Evaluate Spatial Autoregressive Models:** Test the methodology on variables drawn from development economics or climate-adaptive agriculture studies. Demonstrate that when analyzing spatially clustered variables, the PGLS test correctly identifies systematic structural deviations in the residuals that standard empirical distribution function (EDF) tests obscure.