---
source_pdf: old_exam_2021.pdf
folder_category: problem_sets
total_pages: 22
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [real-analysis, optimization-theory, economics-mathematics, mathematical-economics, mathematical-methods-economics, optimization, economics-applications]
---

<!-- page 1 -->

1. **(40 points (5 points each))** Are the following statements true or false? If true, provide a proof. If false, proivde a counter example

(a) Let $(X, d)$ be a non-empty metric space, and $S \subset X$. If $S$ has a limit point, then $S$ has an infinite number of elements.

(b) Every diagonalizable matrix is invertible.

(c) Every convergent sequence is a Cauchy sequence.

(d) Let $(X, d_X)$ and $(Y, d_Y)$ be metric spaces, and function $f : X \to Y$. The function $f$ is a continuous function iff $f(E)$ is open in $(Y, d_Y)$ for any set $E$ open in $(X, d_X)$.

(e) Let $(X, d)$ be a metric space and $S \subset X$. If $S$ is closed and bounded then it is compact.

(f) Let $(X, d)$ be a complete metric space, $T_1$ and $T_2$ be self-maps on $X$. If $T_1$ is a contraction, and $T_2$ is non-expansive, i.e., $d(T_2(x), T_2(y)) \le d(x, y)$ for any $x, y \in X$, then both composite self-maps $T_1 \circ T_2$ and $T_2 \circ T_1$ are contractions.

(g) An arbitrary intersection of compact sets is compact.

(h) Let $\{x_n\}_{n=1}^\infty$ and $\{y_n\}_{n=1}^\infty$ be two convergent sequences in $\mathbb{R}$ such that $x_n > y_n$ for all $n \in \mathbb{N}$ and $x_n \to x$ and $y_n \to y$. Then $x > y$.

---

a) True

Let $a \in X$ be a limit point of $S$.
s.t. $\forall \varepsilon > 0$, $\exists B_\varepsilon(a)$ s.t.
$$(B_\varepsilon(a) \setminus \{a\}) \cap S \neq \emptyset$$

Claim:
If $S$ has limit point $a$, the open ball $B_\varepsilon(a)$ contains an infinite number of elements $b \in S$.

By contradiction,
assume $(B_\varepsilon(a) \setminus \{a\}) \cap S$ is finite, containing $\{b_1, b_2, \dots, b_n\}$.
Define radius $r = \min_{1 \le i \le n} d(a, b_i)$

<!-- page 2 -->

Since each $b_i \in (B_\epsilon(a) \setminus \{a\}) \cap S$,
$b_i \neq a \quad \forall b_i$
such that $d(a, b_i) > 0 \quad \forall b_i$
thus $\min d(a, b_i) = r > 0$

Let $B_r(a)$ be open ball of radius $r$ around $a$ s.t. $B_r(a) \subset B_\epsilon(a)$

Since $r$ is min distance,
no other point $b_j \in B_\epsilon(a)$
can satisfy $d(a, b_j) < r$,
thus
$$(B_r(a) \setminus \{a\}) \cap S = \emptyset$$
but since $a$ is limit point,
any open ball $(B(a) \setminus \{a\}) \cap S \neq \emptyset$

Contradiction, thus $B_\epsilon(a)$ has infinite elements.
Since $B_\epsilon(a) \subset S$,
$S$ has infinite elements.

<!-- page 3 -->

(b) Every diagonalizable matrix is invertible.
(c) Every convergent sequence is a Cauchy sequence.

b) False

If $A$ is diagonalizable, $\exists X, D$ s.t.
$$AX = XD \quad \text{w/ } D = \begin{bmatrix} \lambda_1 & & 0 \\ & \ddots & \\ 0 & & \lambda_n \end{bmatrix}$$
$$\Rightarrow A = X D X^{-1} \qquad \text{w/ } X \text{ invertible}$$

For $A$ to be invertible,
$\det A \neq 0$ must be true

counterexample:
take $M_0 = \begin{bmatrix} 0 & \cdots & 0 \\ \vdots & \ddots & \vdots \\ 0 & \cdots & 0 \end{bmatrix}$, already diagonal
so trivially diagonalizable
$\det M_0 = 0$, so not invertible
thus at least one diagonalizable matrix not invertible

<!-- page 4 -->

(b) Every diagonalizable matrix is invertible.
(c) Every convergent sequence is a Cauchy sequence.

c) True

To be convergent $(x_n)_{n=1}^\infty$ to $L$
$$\forall \varepsilon > 0, \exists N \in \mathbb{N} \text{ s.t. } \forall n > N,$$
$$d(x_n, L) < \varepsilon$$
or w/ norm, $\|x_n - L\| < \varepsilon$

To be cauchy,
$$\forall \varepsilon > 0, \exists N \in \mathbb{N} \text{ s.t. } \forall m, n \ge N,$$
$$d(x_n, x_m) < \varepsilon$$
or w/ norm $\|x_n - x_m\| < \varepsilon$

If $(x_n)_{n=1}^\infty$ converges to limit $L$,
take $m > n > N$, s.t.
$$d(x_n, x_m) < d(x_n, L) < \varepsilon$$
then $d(x_n, x_m) < \varepsilon$, thus cauchy

<!-- page 5 -->

(d) Let $(X, d_X)$ and $(Y, d_Y)$ be metric spaces, and function $f : X \to Y$. The function $f$ is a continuous function iff $f(E)$ is open in $(Y, d_Y)$ for any set $E$ open in $(X, d_X)$.
(e) Let $(X, d)$ be a metric space and $S \subset X$. If S is closed and bounded then it is compact.

d) True, Continuous funct preserve open sets

To prove

<!-- page 6 -->

(d) Let $(X, d_X)$ and $(Y, d_Y)$ be metric spaces, and function $f : X \to Y$. The function $f$ is a continuous function iff $f(E)$ is open in $(Y, d_Y)$ for any set $E$ open in $(X, d_X)$.
(e) Let $(X, d)$ be a metric space and $S \subset X$. If $S$ is closed and bounded then it is compact.

e) False, Heine-Borel only holds for finite normed space

If $S$ closed + bounded,

closed: for all limit points $S'$ of $S$,
$$S' \subseteq S \quad \text{s.t.}$$
for all sequences $(x_n)_{n=1}^\infty \subseteq S$
that converge to limit $L \in X$,
then $L \in S$

bounded: $\exists x_0 \in X \quad \& \quad M > 0$
$$\text{s.t.} \quad d(x, x_0) < M \quad \forall x \in S$$

compact: $S$ compact if every
open cover of $S$, $\mathcal{U}$ s.t. $S \subset \mathcal{U}$,
has finite subcover

<!-- page 7 -->

* **Closed Set:**
  A subset $S$ is **closed** if its complement $X \setminus S$ is open in $X$. Equivalently:
  * $S$ contains all of its limit points: $S' \subseteq S$ (hence $\overline{S} = S$).
  * For every sequence $(x_n)_{n=1}^\infty \subseteq S$ that converges to a limit $L \in X, L \in S$.

* **Bounded Set:**
  A subset $S$ is **bounded** if there exists a point $x_0 \in X$ and a real number $M > 0$ such that:

  $$d(x, x_0) < M \quad \forall x \in S$$

  Equivalently, the diameter of $S$ is finite: $\mathrm{diam}(S) = \sup_{x,y \in S} d(x, y) < \infty$.

* **Compact Set:**
  * **Open Cover Definition:** A subset $S$ is **compact** if every open cover of $S$ has a finite subcover. That is, if $S \subseteq \bigcup_{\alpha \in I} U_\alpha$ where each $U_\alpha \subseteq X$ is open, there exists a finite subcollection $\{\alpha_1, \dots, \alpha_n\} \subseteq I$ such that:

    $$S \subseteq \bigcup_{i=1}^n U_{\alpha_i}$$

  * **Sequential Compactness (Equivalent in Metric Spaces):** $S$ is sequentially compact if every sequence in $S$ has a subsequence that converges to a limit point belonging to $S$.

### Standard Counterexamples

* **Infinite Set with Discrete Metric:**
  Let $X$ be an infinite set equipped with the discrete metric $d(x, y) = 1$ if $x \neq y$, and $d(x, x) = 0$.
  * The entire space $S = X$ is closed (its complement $\emptyset$ is open).
  * $S$ is bounded ($\mathrm{diam}(S) \le 1$).
  * $S$ is **not compact:** The open cover $\{\{x\} : x \in X\}$ consists of singletons (which are open balls $B_{1/2}(x)$). No finite subcollection can cover the infinite set $X$.

<!-- page 8 -->

(f) Let $(X, d)$ be a complete metric space, $T_1$ and $T_2$ be self-maps on $X$. If $T_1$ is a contraction, and $T_2$ is non-expansive, i.e., $d(T_2(x), T_2(y)) \le d(x, y)$ for any $x, y \in X$, then both composite self-maps $T_1 \circ T_2$ and $T_2 \circ T_1$ are contractions.

$f)$

$$T_1 \circ T_2(x) = T_1(T_2(x))$$

The statement is **true**.

**Proof**

Let $(X, d)$ be a complete metric space and let $x, y \in X$ be arbitrary points.

* **Hypotheses:**
  1. $T_1 : X \to X$ is a contraction mapping, meaning there exists a constant $k \in [0, 1)$ such that:

     $$d(T_1(a), T_1(b)) \le k \, d(a, b) \quad \forall a, b \in X$$

  2. $T_2 : X \to X$ is non-expansive (Lipschitz continuous with constant $L = 1$):

     $$d(T_2(a), T_2(b)) \le d(a, b) \quad \forall a, b \in X$$

* **Part 1: Showing $T_1 \circ T_2$ is a Contraction**

  Evaluate the distance under the composite map:

  $$d((T_1 \circ T_2)(x), (T_1 \circ T_2)(y)) = d(T_1(T_2(x)), T_1(T_2(y)))$$

  Applying the contraction property of $T_1$ with $a = T_2(x)$ and $b = T_2(y)$:

  $$d(T_1(T_2(x)), T_1(T_2(y))) \le k \, d(T_2(x), T_2(y))$$

  Applying the non-expansiveness of $T_2$:

  $$k \, d(T_2(x), T_2(y)) \le k \, d(x, y)$$

  Combining these inequalities yields:

  $$d((T_1 \circ T_2)(x), (T_1 \circ T_2)(y)) \le k \, d(x, y)$$

  Since $k \in [0, 1)$, $T_1 \circ T_2$ is a contraction mapping with contraction constant $k$.

<!-- page 9 -->

* **Part 2: Showing $T_2 \circ T_1$ is a Contraction**

  Evaluate the distance under the composite map:

  $$d((T_2 \circ T_1)(x), (T_2 \circ T_1)(y)) = d(T_2(T_1(x)), T_2(T_1(y)))$$

  Applying the non-expansiveness of $T_2$ with $a = T_1(x)$ and $b = T_1(y)$:

  $$d(T_2(T_1(x)), T_2(T_1(y))) \le d(T_1(x), T_1(y))$$

  Applying the contraction property of $T_1$:

  $$d(T_1(x), T_1(y)) \le k \, d(x, y)$$

  Combining these inequalities yields:

  $$d((T_2 \circ T_1)(x), (T_2 \circ T_1)(y)) \le k \, d(x, y)$$

  Since $k \in [0, 1)$, $T_2 \circ T_1$ is a contraction mapping with contraction constant $k$.

<!-- page 10 -->

(g) An arbitrary intersection of compact sets is compact.
(h) Let $\{x_n\}_{n=1}^\infty$ and $\{y_n\}_{n=1}^\infty$ be two convergent sequences in $\mathbb{R}$ such that $x_n > y_n$ for all $n \in \mathbb{N}$ and $x_n \to x$ and $y_n \to y$. Then $x > y$.

$g)$

As compact sets $C_i \subseteq X, \forall C_i$

$C_i \subseteq \bigcup_{\alpha \in I}^{\text{open cover}} U_\alpha$ where $U_\alpha \subseteq X$ is open,

$\exists$ finite subcollection $\{\alpha_1, \dots, \alpha_n\} \subseteq I$

s.t. $C_i \subseteq \bigcup_{i=1}^n U_{\alpha_i} \quad \text{finite subcover}$

---

**Compact Set:**

* **Open Cover Definition:** A subset $S$ is **compact** if every open cover of $S$ has a finite subcover. That is, if $S \subseteq \bigcup_{\alpha \in I} U_\alpha$ where each $U_\alpha \subseteq X$ is open, there exists a finite subcollection $\{\alpha_1, \dots, \alpha_n\} \subseteq I$ such that:

$$S \subseteq \bigcup_{i=1}^n U_{\alpha_i}$$

---

For arbitrary intersection $\bigcap C_j \subseteq \bigcup C_i$

the intersection of their finite subcovers

$J = \bigcap_j \left(\bigcup_{i=1}^n U_{\alpha_{i,j}}\right)$ forms a finite subcollection

covering $\bigcap C_j$ s.t. $\bigcap C_j \subseteq J$

<!-- page 11 -->

To evaluate whether an arbitrary intersection of compact sets is always compact, consider the topological properties in general topological spaces versus Hausdorff (and metric) spaces:

* **In Hausdorff Spaces (including all Metric Spaces):**
  * In any Hausdorff space $X$, every compact subset $K_i \subseteq X$ is **closed**.
  * The intersection of an arbitrary family of closed sets, $\bigcap_{i \in I} K_i$, is always closed.
  * Pick any fixed member $K_{i_0}$ from the family. The intersection satisfies $\bigcap_{i \in I} K_i \subseteq K_{i_0}$.
  * Since a closed subset of a compact space is compact, $\bigcap_{i \in I} K_i$ is a closed subset of the compact set $K_{i_0}$, and is therefore **compact**.

* **In General (Non-Hausdorff) Topological Spaces:**
  * In non-Hausdorff spaces, compact subsets are not necessarily closed, and an intersection of two compact subsets can fail to be compact.
  * **Standard Counterexample:** Let $X = \mathbb{R} \cup \{p, q\}$ be the real line with two non-Hausdorff origins $p$ and $q$ (open neighborhoods of $p$ and $q$ are of the form $(U \setminus \{0\}) \cup \{p\}$ and $(U \setminus \{0\}) \cup \{q\}$ for open sets $U \subseteq \mathbb{R}$ containing $0$).
    * The sets $K_1 = [-1, 1] \setminus \{0\} \cup \{p\}$ and $K_2 = [-1, 1] \setminus \{0\} \cup \{q\}$ are both compact subsets of $X$.
    * Their intersection is $K_1 \cap K_2 = [-1, 1] \setminus \{0\}$, which is not compact.

An arbitrary intersection of compact sets is **always compact in any metric or Hausdorff space**, but does not hold in arbitrary non-Hausdorff topological spaces.

<!-- page 12 -->

(g) An arbitrary intersection of compact sets is compact.
(h) Let $\{x_n\}_{n=1}^\infty$ and $\{y_n\}_{n=1}^\infty$ be two convergent sequences in $\mathbb{R}$ such that $x_n > y_n$ for all $n \in \mathbb{N}$ and $x_n \to x$ and $y_n \to y$. Then $x > y$.

<!-- page 13 -->

(h) Let $\{x_n\}_{n=1}^\infty$ and $\{y_n\}_{n=1}^\infty$ be two convergent sequences in $\mathbb{R}$ such that $x_n > y_n$ for all $n \in \mathbb{N}$ and $x_n \to x$ and $y_n \to y$. Then $x > y$.

$$\text{if } \{x_n\}_{n=1}^\infty \to x \quad \text{and} \quad \{y_n\}_{n=1}^\infty \to y, \quad \text{and } x_n > y_n$$

$$\forall \varepsilon > 0, \exists R \in \mathbb{N} \quad \text{s.t.} \quad \forall n \ge R, |x_n - x| < \varepsilon$$

$$\exists M \in \mathbb{N} \quad \text{s.t.} \quad \forall m \ge M, |y_m - y| < \varepsilon$$

---

A sequence of real numbers $(x_n)_{n=1}^\infty$ is said to **converge** to a real number $L \in \mathbb{R}$ (written $\lim_{n \to \infty} x_n = L$ or $x_n \to L$) if:

$$\forall \varepsilon > 0, \exists N \in \mathbb{N} \quad \text{such that} \quad \forall n \ge N, |x_n - L| < \varepsilon$$

---

False, strict inequality fails

---

To test whether strict inequalities between sequence terms are preserved in the limit, consider the following counterexample:

* Let $x_n = \frac{1}{n}$ for all $n \in \mathbb{N}$.
* Let $y_n = 0$ for all $n \in \mathbb{N}$.

Evaluating the conditions:

* **Sequence comparison:** For every $n \in \mathbb{N}$, $\frac{1}{n} > 0 \implies x_n > y_n$.
* **Limits:**

$$x = \lim_{n \to \infty} x_n = \lim_{n \to \infty} \frac{1}{n} = 0$$

$$y = \lim_{n \to \infty} y_n = \lim_{n \to \infty} 0 = 0$$

Comparing the limits gives $x = y = 0$, which violates the strict inequality $x > y$.

The correct preservation theorem for limits guarantees only the non-strict inequality:

$$x_n \ge y_n \quad \text{or} \quad x_n > y_n \implies \lim_{n \to \infty} x_n \ge \lim_{n \to \infty} y_n \quad (x \ge y)$$

<!-- page 14 -->

2. **(15 points)** Consider the following matrix

$$A = \begin{pmatrix} 5 & -3 \\ -6 & 2 \end{pmatrix}$$

is it diagonalizable in $\mathbb{C}$? Is it diagonalizable in $\mathbb{R}$? If yes, diagonalize it, i.e. find a 2x2 matrix $P$ such that $A = P\Lambda P^{-1}$, where $\Lambda$ is a diagonal matrix. Also, find an expression for $A^n$ for an $n \in \mathbb{N}$. As $n \to \infty$, does $A^n$ converge to some real matrix $B$? Is the matrix $A$ positive definite? negative definite? neither?

<!-- page 15 -->

3. **(15 points (5 points each))**. Consider the following function defined for $X_1 > 0, X_2 > 0, \dots, X_n > 0$ as
$$Y = F(X_1, X_2, \dots, X_n) = \sum_{i=1}^n \alpha_i X_i^\gamma$$

where $\alpha_i > 0, i = 1, \dots, n$ and $\gamma \neq 0$ are parameters.

(a) Is $F$ homogeneous? If so, state its order of homogeneity. Is $F$ homothetic?

(b) For what values of $\gamma$ is $F$ concave? For what values of $\gamma$ is it convex?
*(Hint: Consider three different cases of $\gamma$, $\gamma < 0$, $\gamma \in (0, 1]$, $\gamma \ge 1$) and evaluate the second order derivative of $x_i^\gamma$ for each case. What would this tell you? Is the sum of concave functions a concave function?*

(c) Log-linearize the equation $Y = F(X_1, X_2, \dots, X_n)$ around a point $(Y^*, X_1^*, \dots, X_n^*)$ satisfying this equation and represent the linearised equation in a percentage deviation format, i.e., the variables should take the form $\hat{z} = \frac{z - z^*}{z^*}$.

<!-- page 16 -->

(b) For what values of $\gamma$ is $F$ concave? For what values of $\gamma$ is it convex?
*(Hint: Consider three different cases of $\gamma$, $\gamma < 0$, $\gamma \in (0, 1]$, $\gamma \ge 1$) and evaluate the second order derivative of $x_i^\gamma$ for each case. What would this tell you? Is the sum of concave functions a concave function?*

<!-- page 17 -->

(c) Log-linearize the equation $Y = F(X_1, X_2, \dots, X_n)$ around a point $(Y^*, X_1^*, \dots, X_n^*)$ satisfying this equation and represent the linearised equation in a percentage deviation format, i.e., the variables should take the form $\hat{z} = \frac{z - z^*}{z^*}$.

<!-- page 18 -->

4. **(10 points)** For the correspondence $F$ pictured below, answer the following questions. No formal proof required, a brief justification would suffice.

![Graph of correspondence F](image)

(a) **(3 points)** Is the correspondence upper hemicontinuous at $x_1$ and $x_2$?
(b) **(3 points)** Is the correspondence lower hemicontinuous at $x_1$ and $x_2$?
(c) **(3 points)** Is the correspondence closed valued? compact valued? convex valued?
(d) **(1 points)** Does the correspondence have a closed graph?

<!-- page 19 -->

4. **(10 points)** For the correspondence $F$ pictured below, answer the following questions. No formal proof required, a brief justification would suffice.

![Graph of correspondence F](image)

(a) **(3 points)** Is the correspondence upper hemicontinuous at $x_1$ and $x_2$?
(b) **(3 points)** Is the correspondence lower hemicontinuous at $x_1$ and $x_2$?
(c) **(3 points)** Is the correspondence closed valued? compact valued? convex valued?
(d) **(1 points)** Does the correspondence have a closed graph?

<!-- page 20 -->

5. **(20 points)** Consider the following problem

$$\max_{(x_1, x_2) \in \mathbb{R}^2} x_1^{\frac{1}{2}} + x_2^{\frac{1}{2}}$$

s.t

$$p_1 x_1 + p_2 x_2 \le m,$$
$$x_1 \ge 0,$$
$$x_2 \ge 0$$

where $p_1, p_2, m \in \mathbb{R}_{++}$ are parameters.

(a) **(4 points)** Does a solution exist? If yes, why?

(b) **(2 points)** Argue that the budget constraint binds at any possible maximum.

(c) **(10 points)** Set up the Lagrange and solve the problem.

(d) **(2 points)** Are there any potential maximisers where the constraint qualification would fail?

(e) **(2 points)** Differentiate the indirect utility function w.r.t. $m$ and your Lagrange function w.r.t. $m$ to verify the envelope theorem.

<!-- page 21 -->

5. **(20 points)** Consider the following problem

$$\max_{(x_1, x_2) \in \mathbb{R}^2} x_1^{\frac{1}{2}} + x_2^{\frac{1}{2}}$$

s.t

$$p_1 x_1 + p_2 x_2 \le m,$$
$$x_1 \ge 0,$$
$$x_2 \ge 0$$

where $p_1, p_2, m \in \mathbb{R}_{++}$ are parameters.

(a) **(4 points)** Does a solution exist? If yes, why?

(b) **(2 points)** Argue that the budget constraint binds at any possible maximum.

(c) **(10 points)** Set up the Lagrange and solve the problem.

(d) **(2 points)** Are there any potential maximisers where the constraint qualification would fail?

(e) **(2 points)** Differentiate the indirect utility function w.r.t. $m$ and your Lagrange function w.r.t. $m$ to verify the envelope theorem.

<!-- page 22 -->

5. **(20 points)** Consider the following problem

$$\max_{(x_1, x_2) \in \mathbb{R}^2} x_1^{\frac{1}{2}} + x_2^{\frac{1}{2}}$$

s.t

$$p_1 x_1 + p_2 x_2 \le m,$$
$$x_1 \ge 0,$$
$$x_2 \ge 0$$

where $p_1, p_2, m \in \mathbb{R}_{++}$ are parameters.

(a) **(4 points)** Does a solution exist? If yes, why?

(b) **(2 points)** Argue that the budget constraint binds at any possible maximum.

(c) **(10 points)** Set up the Lagrange and solve the problem.

(d) **(2 points)** Are there any potential maximisers where the constraint qualification would fail?

(e) **(2 points)** Differentiate the indirect utility function w.r.t. $m$ and your Lagrange function w.r.t. $m$ to verify the envelope theorem.