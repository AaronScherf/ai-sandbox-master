---
source_pdf: Practice Sheet.pdf
folder_category: problem_sets
total_pages: 43
routing: hybrid
model: gemini-3.1-flash-lite
pages_repaired: 2
repaired_pages: [35, 43]
tags: [real-analysis, economics-mathematics, mathematical-economics, mathematical-methods-economics, optimization]
---

<!-- page 1 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 1

**PhD Mathematics Camp**
**Comprehensive Practice Sheet**

This sheet is organized by topic and is intended for independent practice.

**I. Linear Algebra**

**Practice Problem 1. Involutions**

Let $V$ be a finite-dimensional real vector space and let $T : V \to V$ satisfy
$$T^2 = I.$$
For $v \in V$, define
$$v_+ = \frac{1}{2}(v + Tv), \quad v_- = \frac{1}{2}(v - Tv).$$

(a) Show that $v = v_+ + v_-$.
(b) Show that $Tv_+ = v_+$ and $Tv_- = -v_-$.
(c) Show that the eigenspaces corresponding to $1$ and $-1$ intersect only at $0$.
(d) Conclude that $T$ is diagonalizable.

**Answer space**

<!-- page 2 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 2

**Practice Problem 2. A nilpotent operator**

Let $V = P_4(\mathbb{R})$ and define $D : V \to V$ by $D(p) = p'$.
(a) Write the matrix of $D$ in the basis $(1, x, x^2, x^3, x^4)$.
(b) Find $\ker D$ and $\text{range } D$.
(c) Explain why $D^5 = 0$.
(d) Show that $I + D$ is invertible and find $(I + D)^{-1}$ as a polynomial in $D$.
(e) Show similarly that $I - 2D$ is invertible and find its inverse.

**Answer space**

<!-- page 3 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 3

**II. Topology and Continuity in $\mathbb{R}^n$**

**Practice Problem 3. A set with an accumulating edge**

Let
$$S = \bigcup_{n=1}^{\infty} \left( \left\{ \frac{1}{n} \right\} \times [0, 1] \right) \subseteq \mathbb{R}^2.$$

(a) Show that $S$ is bounded but not closed.
(b) Determine the closure $\overline{S}$.
(c) Prove that your proposed closure is closed.
(d) Is $S$ compact? Is $\overline{S}$ compact?

**Answer space**

<!-- page 4 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 4

**Practice Problem 4. Nested closed subsets of a compact set**

Let $K \subseteq \mathbb{R}^n$ be compact and let
$$F_1 \supseteq F_2 \supseteq F_3 \supseteq \cdots$$
be nonempty closed subsets of $K$.

(a) Choose $x_n \in F_n$ and use compactness to obtain a convergent subsequence.
(b) Prove that
$$\bigcap_{n=1}^{\infty} F_n \neq \varnothing.$$
(c) Give a nested sequence of nonempty closed subsets of $\mathbb{R}$ with empty intersection, and identify the hypothesis that fails.

**Answer space**

<!-- page 5 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 5

**Practice Problem 5. Positive separation**

Let $K \subseteq \mathbb{R}^n$ be compact and $F \subseteq \mathbb{R}^n$ be closed, with $K \cap F = \varnothing$. Define
$$d(K, F) = \inf \{ \|x - y\| : x \in K, y \in F \}.$$

(a) Prove that $d(K, F) > 0$.
(b) Give an example of two disjoint closed subsets of $\mathbb{R}^2$ whose distance is zero.
*Hint for (a):* If the infimum were zero, choose $x_n \in K$ and $y_n \in F$ with $\|x_n - y_n\| \to 0$.

**Answer space**

<!-- page 6 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 6

**III. Differential Calculus**

**Practice Problem 6. Chain rule in matrix form**

Define
$$F(x, y) = \begin{pmatrix} x^2 y \\ e^{x-y} \end{pmatrix}, \quad G(u, v) = u + \log v.$$
Let $p = (1, 1)$.
(a) Compute $DF(p)$ and $DG(F(p))$.
(b) Use the matrix chain rule to compute $D(G \circ F)(p)$.
(c) Compute $G(F(x, y))$ explicitly and verify your answer directly.
(d) Let $\gamma(t) = (1 + t, 1 - t)$. Compute
$$\left. \frac{d}{dt} (G \circ F)(\gamma(t)) \right|_{t=0}$$
without first expanding the full one-variable composite.

**Answer space**

<!-- page 7 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 7

**Practice Problem 7. Implicit functions for a system**

Consider the system
$$x + y + z = 3, \quad xy + 2z = 3,$$
near $(1, 1, 1)$.
(a) Use the implicit function theorem to justify that $y = \phi(x)$ and $z = \psi(x)$ can be defined locally near $x = 1$.
(b) Compute $\phi'(1)$ and $\psi'(1)$.
(c) Compute $\phi''(1)$ and $\psi''(1)$.
(d) Give second-order approximations to $\phi(x)$ and $\psi(x)$ near $x = 1$.

**Answer space**

<!-- page 8 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 8

**Practice Problem 8. Hessians and an inconclusive test**

Consider
$$f(x, y) = x^4 + y^4 - 2x^2 + 2y^2.$$
(a) Find all critical points.
(b) Compute the Hessian and classify all critical points.
(c) Find the second-order Taylor polynomial centered at $(1, 0)$.
(d) Consider instead $g(x, y) = x^4 - y^4$. The Hessian test at the origin is inconclusive. Classify the origin directly.

**Answer space**

<!-- page 9 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 9

**IV. Optimization**

**Practice Problem 9. One equality constraint**

Find the maximizer of
$$2x + y + 3z - x^2 - y^2 - z^2$$
subject to
$$x + y + z = 2.$$
(a) Set up and solve the Lagrange first-order conditions.
(b) Explain why the solution is the unique global maximizer.
(c) Verify the second-order condition along feasible directions $d$ satisfying $d_1 + d_2 + d_3 = 0$.

**Answer space**

<!-- page 10 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 10

**Practice Problem 10. Several equality constraints**

Find the maximizer of
$$-x^2 - y^2 - z^2$$
subject to
$$x + y + z = 3, \quad x - z = 0.$$
(a) Form the Lagrangian and solve for the optimizer and multipliers.
(b) Solve the same problem by eliminating the constraints first.
(c) Explain why the two methods must give the same global solution.

**Answer space**

<!-- page 11 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 11

**Practice Problem 11. Multiple inequality constraints in three variables**

Find the maximizer of
$$f(x, y, z) = -x^2 - y^2 - z^2 + xy + yz + 3x - y + 4z$$
subject to
$$x + y \leq 2, \quad y + z \geq 4.$$
(a) Show that $f$ is strictly concave.
(b) Find the unconstrained maximizer and check feasibility.
(c) Write the complete KKT conditions.
(d) Determine the active constraints, the maximizer, and the multipliers.
(e) Explain why the KKT point is the unique global maximizer.

**Answer space**

<!-- page 12 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 12

**Practice Problem 12. Mixed constraints and an active-set calculation**

Find the maximizer of
$$-(x - 2)^2 - (y - 1)^2 - (z - 2)^2$$
subject to
$$x + y + z \leq \frac{5}{2}, \quad x \leq 1, \quad x, y, z \geq 0.$$
(a) Show that the problem has a unique global maximizer.
(b) Write the complete KKT conditions.
(c) Determine the active constraints and solve for the optimizer and multipliers.
(d) Check complementary slackness explicitly.

**Answer space**

<!-- page 13 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 13

**Practice Problem 13. A nonlinear convex feasible set**

Find the maximizer of
$$6x - x^2 - y^2$$
subject to
$$4y - x^2 \geq 0, \quad 5 - x - y \geq 0.$$

(a) Show that the feasible set is convex and the objective is strictly concave.
(b) Write the KKT conditions.
(c) Show that $(2, 1)$ satisfies KKT and determine the multipliers.
(d) Explain why this proves that $(2, 1)$ is the unique global maximizer.

**Answer space**

<!-- page 14 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 14

**Practice Problem 14. A parametric KKT problem and the value function**

For $b > 0$, define
$$V(b) = \max_{x,y \geq 0} \{-(x - 2)^2 - (y - 1)^2 : x + y \leq b\}.$$

(a) Solve for $x^*(b)$ and $y^*(b)$ for all $b > 0$. Identify all regime thresholds.
(b) Find the multiplier $\lambda(b)$ on $x + y \leq b$.
(c) Find $V(b)$ explicitly in each regime.
(d) Verify that $V'(b) = \lambda(b)$ wherever the derivative exists.
(e) Determine whether $V$ is once and twice differentiable at the regime thresholds.

**Answer space**

<!-- page 15 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 15

**Practice Problem 15. Two-tier maximization**

Consider
$$\max\{xy - y^2 + 2y : 0 \leq x \leq 2, \ 0 \leq y \leq 2 - x\}.$$

For each fixed $x \in [0, 2]$, define
$$v(x) = \max_{0 \leq y \leq 2 - x} \{xy - y^2 + 2y\}.$$

(a) Find the unconstrained maximizer in $y$ and determine when it is feasible.
(b) Derive the lower-tier optimizer $y^*(x)$ and the piecewise value function $v(x)$.
(c) Maximize $v(x)$ and find the global maximizer of the original problem.
(d) Write the KKT conditions for the original problem and verify the solution.

**Answer space**

<!-- page 16 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 16

**Practice Problem 16. Quadratic forms and constrained maximization**

Find all maximizers of
$$xy + yz - xz$$
subject to
$$x^2 + y^2 + z^2 \leq 1.$$

(a) Write the objective as $u^\top Au$ for a symmetric matrix $A$.
(b) Find the eigenvalues and eigenspaces of $A$.
(c) Determine the maximum value and all maximizers.
(d) Verify the result using Lagrange multipliers.

*You may use:* for symmetric $A$, the maximum of $u^\top Au$ over $\|u\| = 1$ is the largest eigenvalue.

**Answer space**

<!-- page 17 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 17

**Practice Problem 17. KKT is not automatically sufficient**

Consider
$$\max_{x,y} \ x^2 - y^2$$
subject to
$$x^2 + y^2 \leq 1.$$

(a) Write the KKT conditions and find all KKT points.
(b) Determine the global maximizers.
(c) Show that $(0, 0)$ satisfies KKT but is not a local maximum.
(d) Explain why there is no contradiction with KKT sufficiency for concave maximization.

**Answer space**

<!-- page 18 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 18

**Practice Problem 18. Failure of constraint qualification**

Consider
$$\max_{x \in \mathbb{R}} \ x$$
subject to
$$x^2 \leq 0.$$

(a) Find the feasible set and the global maximizer.
(b) Write the KKT conditions and show that no multiplier satisfies stationarity at the maximizer.
(c) Compute the gradient of the active constraint and explain what regularity condition fails.

**Answer space**

<!-- page 19 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 19

**Practice Problem 19. Second-order conditions on feasible directions**

Consider
$$\max_{x,y} \ y$$
subject to
$$y + x^2 = 0.$$

(a) Solve the problem directly.
(b) Form the Lagrangian and find the multiplier at the maximizer.
(c) Find all first-order feasible directions at the maximizer.
(d) Compute the Hessian of the Lagrangian and show that it is negative on every nonzero feasible direction.
(e) Explain why the Hessian of the objective alone misses the relevant curvature.

**Answer space**

<!-- page 20 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 20

**V. Probability Theory**

**Practice Problem 20. A covariance identity**

Let $X, Y$ have finite second moments. Prove
$$\text{Cov}(X, Y) = \text{Cov}(X, \mathbb{E}[Y \mid X]).$$

*Hint:* First show that $\mathbb{E}[XY] = \mathbb{E}[X\mathbb{E}[Y \mid X]]$.

**Answer space**

<!-- page 21 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 21

**Practice Problem 21. Sample variance**

Let $X_1, \dots, X_n$ be i.i.d. with mean $\mu$ and variance $\sigma^2 < \infty$, and let $\overline{X}_n = n^{-1} \sum_i X_i$.

(a) Prove
$$\sum_{i=1}^n (X_i - \overline{X}_n)^2 = \sum_{i=1}^n (X_i - \mu)^2 - n(\overline{X}_n - \mu)^2.$$

(b) Define
$$S_n^2 = \frac{1}{n-1} \sum_{i=1}^n (X_i - \overline{X}_n)^2.$$

Show that $\mathbb{E}[S_n^2] = \sigma^2$.

**Answer space**

<!-- page 22 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 22

**Practice Problem 22. Conditional expectation as the best predictor**

Let $m(X) = \mathbb{E}[Y \mid X]$. For any square-integrable function $g(X)$, prove
$$\mathbb{E}[(Y - g(X))^2] = \mathbb{E}[(Y - m(X))^2] + \mathbb{E}[(m(X) - g(X))^2].$$

*Hint:* Expand
$$Y - g(X) = (Y - m(X)) + (m(X) - g(X))$$
and condition on $X$ to eliminate the cross term. What does the identity imply about $m(X)$?

**Answer space**

<!-- page 23 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 23

**VI. Additional Conceptual and Proof Practice**

**A. Linear Algebra**

**Practice Problem 23. Rank–nullity without coordinates**

Suppose $T : \mathbb{R}^4 \to \mathbb{R}^2$ is linear and
$$\ker T = \{(x_1, x_2, x_3, x_4) \in \mathbb{R}^4 : x_1 = 5x_2, \ x_3 = 7x_4\}.$$

Without constructing a matrix for $T$, prove that $T$ is surjective. Make clear where finite dimensionality enters your argument.

**Answer space**

<!-- page 24 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 24

**Practice Problem 24. Spanning and independence as properties of a map**

Let $v_1, \dots, v_m \in V$, and define
$$T : \mathbb{R}^m \to V, \quad T(z_1, \dots, z_m) = z_1 v_1 + \dots + z_m v_m.$$

Prove directly from the definitions that
(a) $v_1, \dots, v_m$ spans $V$ if and only if $T$ is surjective;
(b) $v_1, \dots, v_m$ is linearly independent if and only if $T$ is injective.

Explain why this single map packages the two basic questions one asks about a list of vectors.

**Answer space**

<!-- page 25 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 25

**Practice Problem 25. Rank one and outer products**

Let $A$ be a nonzero $m \times n$ real matrix. Prove that
$$\text{rank} A = 1$$
if and only if there exist nonzero vectors $c \in \mathbb{R}^m$ and $d \in \mathbb{R}^n$ such that
$$A = cd^\top.$$
Equivalently, prove that $A_{jk} = c_j d_k$ for every $j, k$.
*Hint.* If rank $A = 1$, choose one nonzero column and express every other column as a scalar multiple of it.

**Answer space**

<!-- page 26 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 26

**Practice Problem 26. Idempotent maps and direct sums**

Let $P \in \mathcal{L}(V)$ satisfy $P^2 = P$.
(a) For arbitrary $v \in V$, show that
$$v = (v - Pv) + Pv$$
with $v - Pv \in \ker P$ and $Pv \in \text{range } P$.
(b) Prove that $\ker P \cap \text{range } P = \{0\}$.
(c) Conclude that
$$V = \ker P \oplus \text{range } P.$$
(d) Use the decomposition to prove that $P$ is diagonalizable and identify its possible eigenvalues.

**Answer space**

<!-- page 27 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 27

**Practice Problem 27. Similarity preserves eigenvalues**

Let $T \in \mathcal{L}(V)$ and let $S \in \mathcal{L}(V)$ be invertible.
(a) Prove that $T$ and $S^{-1}TS$ have the same eigenvalues.
(b) If $v$ is an eigenvector of $T$ with eigenvalue $\lambda$, identify an eigenvector of $S^{-1}TS$ with the same eigenvalue.
(c) Explain why changing basis changes the matrix representing a linear transformation but does not change its eigenvalues.

**Answer space**

<!-- page 28 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 28

**B. Topology and Continuity**

**Practice Problem 28. Equivalent norms and the topology of $\mathbb{R}^n$**

For $x = (x_1, \dots, x_n) \in \mathbb{R}^n$, define
$$\|x\|_2 = \left( \sum_{i=1}^n x_i^2 \right)^{1/2}, \quad \|x\|_\infty = \max_i |x_i|.$$
(a) Prove
$$\|x\|_\infty \leq \|x\|_2 \leq \sqrt{n} \|x\|_\infty.$$
(b) Deduce that convergence in one norm is equivalent to convergence in the other.
(c) Compare balls to prove that the two norms generate the same open subsets of $\mathbb{R}^n$.

**Answer space**

<!-- page 29 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 29

**Practice Problem 29. Continuous functions and level sets**

Let $f : \mathbb{R}^n \to \mathbb{R}$ be continuous and let $c \in \mathbb{R}$.
(a) Prove that $\{x : f(x) > c\}$ is open.
(b) Prove that $\{x : f(x) \geq c\}$ is closed.
(c) Use these results to classify the sets
$$A = \{x : \|x\|_2 < 1\}, \quad B = \{x : x^\top Q x \leq 1\},$$
where $Q$ is a fixed symmetric matrix, and
$$C = \{(x, y) \in \mathbb{R}^2 : y = x^2\}.$$
Do not return to the ball definition in part (c).

**Answer space**

<!-- page 30 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 30

**Practice Problem 30. Closed sets and convergent sequences**

Prove that $A \subseteq \mathbb{R}^n$ is closed if and only if
$$x_k \in A, \quad x_k \to x \implies x \in A.$$
For the reverse implication, if $A$ is not closed, construct a sequence by choosing
$$x_k \in A \cap B_{1/k}(x)$$
for a suitable point $x \notin A$.

**Answer space**

<!-- page 31 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 31

**Practice Problem 31. Compactness and its consequences**

Let $K \subseteq \mathbb{R}^n$ be compact.
(a) If $F \subseteq K$ is closed, prove that $F$ is compact.
(b) If $f : K \to \mathbb{R}^m$ is continuous, prove that $f(K)$ is compact.
(c) Deduce that a continuous real-valued function on $K$ attains both a maximum and a minimum.
(d) Give examples showing that attainment can fail if the domain is bounded but not closed, if the domain is closed but unbounded, or if the domain is compact but the function is not continuous.

**Answer space**

<!-- page 32 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 32

**Practice Problem 32. Continuous bijections from compact sets**

Let $K \subseteq \mathbb{R}^n$ be compact and let
$$f : K \to Y \subseteq \mathbb{R}^m$$
be a continuous bijection. Prove that
$$f^{-1} : Y \to K$$
is continuous.
*Suggested route.* Let $y_k \to y$, put $x_k = f^{-1}(y_k)$ and $x = f^{-1}(y)$, and argue by contradiction using compactness and injectivity.

**Answer space**

<!-- page 33 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 33

**Practice Problem 33. A positive function on a compact set**

Let $K \subseteq \mathbb{R}^n$ be compact and let $f : K \to \mathbb{R}$ be continuous. Suppose
$$f(x) > 0 \quad \text{for every } x \in K.$$
Prove that there exists $\varepsilon > 0$ such that
$$f(x) \geq \varepsilon \quad \text{for every } x \in K.$$
Give an example showing that the conclusion can fail when $K$ is closed but not compact.

**Answer space**

**C. Differential Calculus**

<!-- page 34 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 34

**Practice Problem 34. The derivative is unique**

Suppose $f : \mathbb{R}^n \to \mathbb{R}^m$ satisfies
$$f(x + h) = f(x) + Ah + r_A(h)$$
and also
$$f(x + h) = f(x) + Bh + r_B(h),$$
where $A, B : \mathbb{R}^n \to \mathbb{R}^m$ are linear and
$$\frac{\|r_A(h)\|}{\|h\|} \to 0, \quad \frac{\|r_B(h)\|}{\|h\|} \to 0.$$
Prove that $A = B$.
*Hint.* Fix $v \in \mathbb{R}^n$ and set $h = tv$.

**Answer space**

<!-- page 35 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 35

**Practice Problem 35. Directional derivatives are not enough**

Define
$$f(x, y) = \begin{cases} \frac{x^2y}{x^2 + y^2}, & (x, y) \neq (0, 0), \\ 0, & (x, y) = (0, 0). \end{cases}$$
(a) Prove that $f$ is continuous at $(0, 0)$.
(b) Compute $f_x(0, 0)$ and $f_y(0, 0)$.
(c) For $v = (a, b) \neq 0$, compute $D_v f(0, 0)$.
(d) Show that every directional derivative exists, but $v \mapsto D_v f(0, 0)$ is not linear.
(e) Deduce that $f$ is not differentiable at the origin.

**Answer space**

<!-- page 36 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 36

**Practice Problem 36. Continuous partial derivatives imply differentiability**

Suppose $f : \mathbb{R}^2 \to \mathbb{R}$ has partial derivatives in a neighborhood of $(a, b)$ and that $f_x$ and $f_y$ are continuous at $(a, b)$. Prove that $f$ is differentiable at $(a, b)$.
Begin with
$$f(a + h, b + k) - f(a, b) = [f(a + h, b + k) - f(a, b + k)] + [f(a, b + k) - f(a, b)]$$
and apply the one-dimensional mean value theorem to the two differences. Indicate precisely where continuity of the partial derivatives is used.

**Answer space**

<!-- page 37 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 37

**Practice Problem 37. Restricting a multivariate problem to a line**

Let $f : U \subseteq \mathbb{R}^n \to \mathbb{R}$ be differentiable, and suppose the line segment joining $a$ and $b$ lies in $U$. Define
$$g(t) = f(a + t(b - a)), \quad 0 \le t \le 1.$$

(a) Show that
$$g'(t) = Df(a + t(b - a))(b - a).$$

(b) Apply the one-dimensional mean value theorem to show that for some $c$ on the segment,
$$f(b) - f(a) = Df(c)(b - a).$$

(c) Deduce
$$|f(b) - f(a)| \le \sup_{z \in [a,b]} \|Df(z)\| \|b - a\|.$$

(d) If $U$ is convex and $Df(x) = 0$ for every $x \in U$, prove that $f$ is constant on $U$.

**Answer space**

<!-- page 38 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 38

**Practice Problem 38. If the Hessian vanishes, the function is affine**

Let $U \subseteq \mathbb{R}^n$ be open and convex, and let $f : U \to \mathbb{R}$ be $C^2$. Suppose
$$H_f(x) = 0 \quad \text{for every } x \in U.$$

Prove that there exist $a \in \mathbb{R}^n$ and $b \in \mathbb{R}$ such that
$$f(x) = a^\top x + b \quad \text{for every } x \in U.$$

*Hint.* Treat $\nabla f$ as a function and use the previous problem.

**Answer space**

<!-- page 39 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 39

**Practice Problem 39. Taylor’s theorem by restriction to a line**

Let $f : U \subseteq \mathbb{R}^n \to \mathbb{R}$ be $C^2$, and suppose the segment from $x$ to $x + h$ lies in $U$. Define
$$g(t) = f(x + th), \quad 0 \le t \le 1.$$

(a) Compute $g'(t)$ and $g''(t)$.

(b) Apply the one-dimensional Taylor theorem to prove that for some $\theta \in (0, 1)$,
$$f(x + h) = f(x) + \nabla f(x)^\top h + \frac{1}{2} h^\top H_f(x + \theta h) h.$$

(c) Explain why the second-order term is a scalar quadratic form.

**Answer space**

<!-- page 40 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 40

**Practice Problem 40. Local versus global invertibility**

Consider
$$F(x, y) = \begin{pmatrix} e^x \cos y \\ e^x \sin y \end{pmatrix}.$$

(a) Compute $DF(x, y)$ and show that $\det DF(x, y) \neq 0$ everywhere.

(b) State precisely what the inverse function theorem implies at an arbitrary point.

(c) Show that $F(x, y + 2\pi) = F(x, y)$. Why does this not contradict part (b)?

(d) Now consider $f(x) = x^3$. It is globally one-to-one but $f'(0) = 0$. Why does this not contradict the inverse function theorem?

(e) Write $f^{-1}$ and determine whether it is differentiable at 0.

**Answer space**

<!-- page 41 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 41

**Practice Problem 41. What can be solved for implicitly?**

Consider the sphere
$$F(x, y, z) = x^2 + y^2 + z^2 - 1 = 0.$$

At $p = (0, 0, 1)$:
(a) Can the equation locally be solved as $z = g(x, y)$? Which partial derivative determines the answer?
(b) Can it locally be solved as $x = h(y, z)$? Explain.

Repeat the two questions at $q = (1, 0, 0)$.

Finally, near $p$, start from $F(x, y, g(x, y)) = 0$ and derive formulas for $g_x$ and $g_y$ using the chain rule.

**Answer space**

<!-- page 42 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 42

**Practice Problem 42. Diagnose the statement**

For each statement, decide whether it is true or false. If true, give a short proof or cite the appropriate theorem and explain why its hypotheses are satisfied. If false, give a counterexample.

(a) Differentiability at a point implies continuity there.
(b) Existence of every directional derivative at a point implies differentiability there.
(c) A continuous image of a closed set is closed.
(d) A closed subset of a compact set is compact.
(e) If $Df(x)$ is invertible, then $f$ is globally one-to-one.
(f) If $Df(x)$ is singular, then $f$ cannot possess a differentiable local inverse at $x$.
(g) If $Df(x)$ is singular, then $f$ cannot be locally one-to-one near $x$.
(h) If $U$ is convex and $H_f(x) = 0$ for all $x \in U$, then $f$ is affine on $U$.

**Answer space**

<!-- page 43 -->

PhD Mathematics Camp – Comprehensive Practice Sheet 43

**Suggested References**

* Sheldon Axler, *Linear Algebra Done Right*, 4th ed., Springer, 2024.
* Gilbert Strang, *Introduction to Linear Algebra*, 5th ed., Wellesley–Cambridge Press, 2016.
* Rangarajan K. Sundaram, *A First Course in Optimization Theory*, Chapters 5–7.
* Carl P. Simon and Lawrence Blume, *Mathematics for Economists*, Chapters 18–19.
* Stephen Boyd and Lieven Vandenberghe, *Convex Optimization*, Chapters 4–5.