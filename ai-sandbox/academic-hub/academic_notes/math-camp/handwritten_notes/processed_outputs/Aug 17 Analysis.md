---
source_pdf: Aug 17 Analysis.pdf
folder_category: handwritten_notes
total_pages: 25
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [real-analysis]
---

<!-- page 1 -->

Optimizing sequence to
$\inf / \sup \subseteq \mathbb{R}$

completeness $\iff A \subseteq \mathbb{R}$ bounded $\implies A$ has $\inf / \sup$

$\sup A$ is not always attained
e.g. $A = [0, 1)$

but $\exists \{x_k\} \subseteq A$ s.t. $x_k \uparrow \sup A$ monotonically approaches

e.g. $x_k = 1 - \frac{1}{k}$

suppose $S = \sup A : a \le S, \forall a \in A$

$\forall \varepsilon > 0, \exists a_\varepsilon \in A : S - \varepsilon < a_\varepsilon \le S$

<!-- page 2 -->

Take $\varepsilon_k = \frac{1}{k} \qquad k=1 \quad k=2 \ldots \quad k=\infty$
[number line diagram showing points $S - \varepsilon_1$ with $a_1$, $S - \varepsilon_2$ with $a_2$, up to $S$]
$\color{red}{\text{how to choose } a_k?}$ $\quad S - \varepsilon_1 \quad S - \varepsilon_2 \qquad S$

$\implies a_{\varepsilon_k} \in (S - \varepsilon_k, S]$

$x_k = \max \{ a_1, \ldots, a_k \}$

$\{ x_k \}$ is incr $\uparrow \implies x_k \to S$
$\text{as } k \to \infty$

thus if $a_n \le X_n \le b_n$ then
$\begin{array}{ccc} \text{can be} & \downarrow & \swarrow X \to X_* \\ & X_* & X_* \quad \text{converges} \end{array}$

above is weaker notion of
attaining max, via monotonically
approaching & converging

<!-- page 3 -->

In $\mathbb{R}^n$, total orders are not
as well behaved

ie lexicographic order $\color{red}{\text{is}}$
$\color{red}{\text{what is term}}$
$\color{red}{\text{for type}}$
$\color{red}{\text{of order}}$
$\color{red}{\text{weak order?}}$

---

Cont. Mappings

Compact sets in $\mathbb{R}^n$ (closest thing to finiteness in arbitrary set)

1) Finite covering: $\{ U_\alpha \}_{\alpha \in A}$ open sets
$\text{for } K \subseteq \bigcup_{\alpha \in A} U_\alpha$
$\implies K \subseteq \bigcup_{i=1}^n U_{\alpha_i}$

<!-- page 4 -->

2) Sequential compactness

$\forall \{ X_n \} \subseteq K : \exists \{ X_{n_k} \}$ conv. subseq.
s.t. $\{ X_{n_k} \} \to L \quad \text{limit in } K$

3) Heine-Borel

$K \text{ closed \& bounded } (\text{in } \mathbb{R}^n)$
$\implies \text{compact}$

$\text{bounded in } \mathbb{R}^n \implies \exists \text{ conv. subseq}$
$\implies \text{bounded set has limit points}$

if set is finite, conv. subseq.
can just pick same elem.

<!-- page 5 -->

For inf. sets, compactness
describes behavior of accumulation

---

Cont. of Mappings

$f : D \subseteq \mathbb{R}^n \to \mathbb{R}^m$

$x = \begin{bmatrix} x_1 \\ \vdots \\ x_n \end{bmatrix} \mapsto f(x) = \begin{bmatrix} f_1(x) \\ \vdots \\ f_m(x) \end{bmatrix}$

$\lim_{x \to a} f(x) = f(a) = f\left(\lim_{x \to a} x\right)$

$$\Updownarrow$$

if $U \subseteq \mathbb{R}^m$ open $\implies f^{-1}(U)$ open
$\qquad\text{codomain}\qquad\qquad\text{preimage (and domain)}$

not saying open sets map to open sets

contr ex : $f^1 \implies$ constant (closed)

<!-- page 6 -->

Continuous functions on compact sets

Claim: if $K$ compact & $f$ cont,
then $f(K)$ compact

Proof: if $K$ compact, by Heine-Borel,
$K$ closed & bounded

WTS: $f(K)$ closed & bounded
but HB depends on $\color{red}{???}$

seq proof:
Take $\{ y_k \} \subseteq f(K)$
define $x_k : f(x_k) = y_k$
by compact: $\{ x_{n_k} \}$ $x_{n_j} \to x^* \in K$
by continuity: $y_{k_j} = f(x_{k_j}) \to f(x^*) \in f(K)$
$\square$

<!-- page 7 -->

The Heine-Borel Theorem states that a subset $K \subseteq \mathbb{R}^n$ (equipped with the standard Euclidean topology) is compact if and only if it is closed and bounded.

### Applicability in Euclidean Space ($\mathbb{R}^n$)

In finite-dimensional Euclidean space $\mathbb{R}^n$, the equivalence holds completely:

$$\text{Compactness (every open cover has a finite subcover)} \iff \text{Sequential Compactness}$$

* **Direction 1 ($\text{Compact} \implies \text{Closed and Bounded}$):** Holds in any metric space $(X, d)$.
  * If $K$ is compact, it is bounded because $\{ B(x_0, m) \}_{m=1}^\infty$ forms an open cover for any fixed $x_0 \in X$, admitting a finite subcover.
  * It is closed because for any $y \notin K$, the open sets separating points in $K$ from $y$ yield a neighborhood around $y$ disjoint from $K$.

* **Direction 2 ($\text{Closed and Bounded} \implies \text{Compact}$):** Relies critically on the **Bolzano-Weierstrass property** and the completeness/finite dimensionality of $\mathbb{R}^n$.
  * A bounded set in $\mathbb{R}^n$ can be enclosed within an $n$-dimensional hypercube $[a, b]^n$.
  * The interval $[a, b]$ is compact (by the supremum property / nested intervals), and finite products of compact sets are compact (Tychonoff's Theorem).
  * A closed subset of a compact space is compact.

### When Does Heine-Borel Fail?

The equivalence $\text{Compact} \iff \text{Closed and Bounded}$ **fails** outside finite-dimensional Euclidean spaces:

<!-- page 8 -->

Cont. funct attain its max / min
on compact sets

if $f(K)$ compact $\iff f(K)$ closed & bounded

$s = \sup f(K)$, $i = \inf f(K)$

by optimizing sequence

$\exists y_k \to s$, $z_k \to i$

subsequences $\uparrow$

$\{ y_k \}, \{ z_k \} \subseteq f(K)$

if compact, $s, i \in f(K)$

so $\max_{x \in D} f(x)$ generally only solvable if $D$ compact

<!-- page 9 -->

# Calculus Refresher on Differentiation

$$f'(x) = \frac{df}{dx} = \frac{d}{dx} f(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$$

marginal rate of change

# Mean Value Theorem

*Lagrange*

$$f(b) - f(a) = f'(t_i)(b - a) \quad t_i \in (a, b)$$

### Taylor Approximation by polynomials

$$f(x) = f(x_0) + f'(x_0)(x - x_0) + \frac{1}{2!} f''(x_0)(x - x_0)^2 + \dots + \frac{1}{k!} f^{(k)}(x_0)(x - x_0)^k + o\left((x - x_0)^k\right)$$
$$\leftarrow \text{remainder term}$$

If $R(x) = o\left((x - x_0)^k\right) \quad \lim_{x \to x_0} \frac{R(x)}{(x - x_0)^k} \to 0$

$\color{red}{\text{Check out edgeworth expansion}}$

<!-- page 10 -->

Fund. Theorem of Calculus

$$F(x) = \int_{a}^{x} f(t) \, dt$$

$$F(b) - F(a) = \int_{a}^{b} f(t) \, dt$$

antiderivative of function is $\color{red}{???}$

Derivatives easy to calculate,
trick is proving existence

Integrals usually exist
but harder to calculate

Think of integral as area under curve
Riemann integral

<!-- page 11 -->

Euclidean space in linear algebra
defined by inner product

Aside: mapping to scalar in $\mathbb{R}$

---

Differential

$1st$ order approximation (linear)

$Df(a): \mathbb{R}^n \to \mathbb{R}^m$ linear map

in standard basis in $\mathbb{R}^n$,
linear map is matrix (Jacobian)

$f$ differentiable at $a$ if
$\exists$ linear map $L$
s.t. $f(a+h) - f(a) = L h + o(\|h\|) \quad \leftarrow \text{remainder}$

$\begin{array}{c} a+h \\ \nwarrow \uparrow h \\ a \end{array}$

$L$ is differential
$L = Df(a)$

goal is to find linear map $L$

<!-- page 12 -->

$D \subseteq \mathbb{R}^n$

$\begin{array}{c} a+h \\ \nwarrow \uparrow h \\ a \end{array}$ $\xrightarrow{\quad f \quad}$ $\begin{array}{l} \nearrow f(a+h) \\ \vdots o(\|h\|) \text{ remainder} \\ \nearrow f(a) + L h \quad \begin{array}{l} \text{linear} \\ \text{approx} \end{array} \\ f(a) \end{array}$

$L : \mathbb{R}^n \to \mathbb{R}^m$ linear then $\exists C = C(a) < \infty$

s.t. $\|L h\|_{\mathbb{R}^m} \le C \|h\|_{\mathbb{R}^n}$

Linear maps not only bounded,
also Lipschitz

small perturbation of linear map
only deviates output linearly
so we can bound output
by bounding input

<!-- page 13 -->

# Introduction to Lipschitz Continuity for Linear Maps

In graduate-level analysis and economic theory, establishing the continuity and stability of linear operators is foundational. Your teaching assistant was describing the fundamental property that **every linear map between finite-dimensional normed vector spaces is Lipschitz continuous**.

To formalize this, let $V = \mathbb{R}^n$ and $W = \mathbb{R}^m$ be normed vector spaces equipped with norms $\|\cdot\|_n$ and $\|\cdot\|_m$, respectively. Let $T : \mathbb{R}^n \to \mathbb{R}^m$ be a linear transformation.

## 1. The Lipschitz Condition

A function $f : \mathbb{R}^n \to \mathbb{R}^m$ is called **Lipschitz continuous** on its domain if there exists a real constant $K \ge 0$ such that for all vectors $x, y \in \mathbb{R}^n$:

$$\|f(x) - f(y)\|_m \le K \|x - y\|_n$$

When $f$ is a linear map $T$, we exploit its linearity. Setting $x - y = h$ (representing the small perturbation or deviation in the input) and noting that $T(x) - T(y) = T(x - y) = T(h)$, the Lipschitz condition simplifies to:

$$\|T(h)\|_m \le C \|h\|_n$$

for some finite constant $C = C(n, m) < \infty$ that depends on the dimensions (and the specific choice of norms), but is independent of $h$.

<!-- page 14 -->

## 2. Why Linear Maps Satisfy This Property

In finite-dimensional spaces, linearity guarantees boundedness, and boundedness is equivalent to Lipschitz continuity. To see why $C$ exists, we can express the linear map $T$ in terms of an $m \times n$ matrix $A$ relative to the standard bases.

For any vector $h = (h_1, h_2, \dots, h_n)^T \in \mathbb{R}^n$, the image under the linear map is $T(h) = Ah$. Using the properties of matrix norms induced by vector norms (or subordinate matrix norms), we have:

$$\|Ah\|_m \le \|A\| \|h\|_n$$

where $\|A\|$ is the operator norm defined as:

$$\|A\| = \sup_{v \neq 0} \frac{\|Av\|_m}{\|v\|_n}$$

Because $\mathbb{R}^n$ is finite-dimensional, all norms are equivalent, and the unit sphere in $\mathbb{R}^n$ is compact. A continuous function (the mapping $v \mapsto \|Av\|_m$) on a compact set attains its maximum. Therefore, the operator norm $\|A\|$ is guaranteed to be a finite real number $C$.

## 3. Analytical Implications for Perturbation Analysis

Your TA emphasized that bounding the input perturbation bounds the output deviation. In comparative statics, optimization, and numerical analysis, this implies that linear approximations possess strict local and global stability.

If you perturb an input $x$ by a vector $h$, the output error is bounded linearly:

$$\|T(x+h) - T(x)\|_m = \|Th\|_m \le C \|h\|_n$$

This guarantees that infinitesimal changes in inputs cannot produce unbounded or discontinuous jumps in the outputs of linear systems.

<!-- page 15 -->

$e_i = \begin{pmatrix} 0 \\ \vdots \\ 1 \\ \vdots \\ 0 \end{pmatrix} \begin{array}{l} \text{std basis} \\ \text{vector} \end{array} \quad e_i \in h$

Proof: Take $e_1, \dots, e_n$

$$h = \sum_{i=1}^n h_i e_i \quad \text{\color{red}???}$$

$$\|L(h)\| = \|L \left( \sum h_i e_i \right)\| = \|\sum h_i L e_i\|$$

by $\Delta$ inequality,

$$\|L(h)\| \le \sum \|h_i L e_i\| = \sum |h_i| \|L e_i\|$$

$$\le \left( \max_i \|L(e_i)\| \right) \sum |h_i|$$

$$\le \sqrt{n} \|h\| \quad \text{\reflectbox{$\curvearrowleft$}}$$

$\begin{aligned} \|h\| &= \sqrt{h_1^2 + \dots + h_n^2} \\ &\le \sqrt{n(\max h_i)} \quad \text{\color{red}?}\end{aligned}$

$$\|h\| \ge \sum |h_i|$$

$$\text{\color{red}use Cauchy-Schwartz?}$$

<!-- page 16 -->

This proof establishes an explicit bound for the Lipschitz constant $C$ of a linear operator $L : \mathbb{R}^n \to \mathbb{R}^m$ by decomposing the input along the standard orthonormal basis and applying the Cauchy-Schwarz inequality.

### Step-by-Step Proof Breakdown

#### 1. Basis Expansion and Linearity

Let $\{e_1, e_2, \dots, e_n\}$ denote the standard basis for $\mathbb{R}^n$, where $e_i = (0, \dots, 1, \dots, 0)^T$. Any vector $h \in \mathbb{R}^n$ can be uniquely expressed as a linear combination of these basis vectors:

$$h = \sum_{i=1}^n h_i e_i$$

Applying the linear transformation $L$ to $h$:

$$L(h) = L \left( \sum_{i=1}^n h_i e_i \right) = \sum_{i=1}^n h_i L(e_i)$$

#### 2. Triangle Inequality and Absolute Homogeneity

Taking the norm $\|\cdot\|$ on the codomain $\mathbb{R}^m$ and applying the generalized triangle inequality alongside absolute homogeneity ($\|\alpha v\| = |\alpha| \|v\|$):

$$\|L(h)\| = \left\| \sum_{i=1}^n h_i L(e_i) \right\| \le \sum_{i=1}^n \|h_i L(e_i)\| = \sum_{i=1}^n |h_i| \|L(e_i)\|$$

#### 3. Factoring Out the Maximum Basis Image

Since the basis is finite, the set of transformed norms $\{\|L(e_1)\|, \dots, \|L(e_n)\|\}$ is finite and achieves a well-defined maximum:

$$M = \max_{1 \le i \le n} \|L(e_i)\| < \infty$$

Bounding each $\|L(e_i)\| \le M$:

$$\sum_{i=1}^n |h_i| \|L(e_i)\| \le M \sum_{i=1}^n |h_i| = \left( \max_{1 \le i \le n} \|L(e_i)\| \right) \sum_{i=1}^n |h_i|$$

<!-- page 17 -->

### 4. Resolving the Red Annotation via Cauchy-Schwarz

To bound $\sum_{i=1}^n |h_i|$ in terms of the Euclidean norm $\|h\| = \sqrt{\sum_{i=1}^n h_i^2}$, apply the **Cauchy-Schwarz inequality** in $\mathbb{R}^n$ to the vectors $u = (|h_1|, \dots, |h_n|)^T$ and the all-ones vector $\mathbf{1} = (1, \dots, 1)^T$:

$$\sum_{i=1}^n |h_i| = \sum_{i=1}^n 1 \cdot |h_i| = \langle \mathbf{1}, u \rangle \le \|\mathbf{1}\|_2 \|u\|_2$$

Evaluating the norms:

* $\|\mathbf{1}\|_2 = \sqrt{\sum_{i=1}^n 1^2} = \sqrt{n}$
* $\|u\|_2 = \sqrt{\sum_{i=1}^n |h_i|^2} = \sqrt{\sum_{i=1}^n h_i^2} = \|h\|$

Thus:

$$\sum_{i=1}^n |h_i| \le \sqrt{n} \|h\|$$

*(Note on your handwritten annotation: the inequality is $\sum |h_i| \le \sqrt{n} \|h\|$, rather than $\|h\| \ge \sum |h_i|$).*

### Final Synthesis

Combining the steps yields:

$$\|L(h)\| \le \left( \max_{1 \le i \le n} \|L(e_i)\| \right) (\sqrt{n} \|h\|) = \underbrace{\left( \sqrt{n} \max_{1 \le i \le n} \|L(e_i)\| \right)}_C \|h\|$$

Setting $C = \sqrt{n} \max_{1 \le i \le n} \|L(e_i)\| < \infty$ produces the Lipschitz bound $\|L(h)\| \le C \|h\|$, where $C$ depends exclusively on the dimension $n$ and the transformation $L$, independent of the perturbation $h$.

<!-- page 18 -->

$$\frac{\|L(h)\|}{\|h\|} \text{ is bounded by Lipschitz}$$

$$= \left\| L\left(\frac{h}{\|h\|}\right) \right\| \quad \text{\color{red}\begin{array}{l} \text{Lipschitz} \\ \text{const} \end{array}}$$

$$\|L\|_{\text{Lp}} = \sup \|L(h)\|$$
$$\text{when } \|h\| = 1$$

$$\text{Lipschitz const} \implies \text{continuity}$$

<!-- page 19 -->

### Mathematical Breakdown

#### 1. Normalization and Homogeneity

For any nonzero vector $h \in \mathbb{R}^n \setminus \{0\}$, the scalar $\frac{1}{\|h\|}$ can be passed inside the linear map $L$ and the norm via absolute homogeneity:

$$\frac{\|L(h)\|}{\|h\|} = \left\| \frac{1}{\|h\|} L(h) \right\| = \left\| L\left(\frac{h}{\|h\|}\right) \right\|$$

Letting $u = \frac{h}{\|h\|}$, the vector $u$ lies on the unit sphere $S^{n-1} = \{x \in \mathbb{R}^n : \|x\| = 1\}$. Therefore, evaluating the ratio $\frac{\|L(h)\|}{\|h\|}$ over all nonzero $h$ is equivalent to evaluating $\|L(u)\|$ exclusively over unit vectors.

#### 2. The Induced Operator Norm ($\|L\|_{\text{op}}$)

The quantity $\|L\|_{\text{op}}$ (denoted in your notes as $\|L\|_p$ or the operator norm) is defined as the supremum of $\|L(h)\|$ on the unit sphere:

$$\|L\|_{\text{op}} = \sup_{\|h\|=1} \|L(h)\| = \sup_{h \neq 0} \frac{\|L(h)\|}{\|h\|}$$

Because $S^{n-1}$ is closed and bounded in $\mathbb{R}^n$ (compact by the Heine-Borel theorem) and the mapping $h \mapsto \|L(h)\|$ is continuous, the Extreme Value Theorem guarantees that the supremum is achieved as a maximum:

$$\|L\|_{\text{op}} = \max_{\|h\|=1} \|L(h)\| = C < \infty$$

This finite value $C = \|L\|_{\text{op}}$ serves as the minimal (optimal) Lipschitz constant for $L$, directly recovering the bound:

$$\|L(h)\| \le \|L\|_{\text{op}} \|h\| \quad \forall h \in \mathbb{R}^n$$

---

#### 3. Implication: Lipschitz Continuity $\implies$ Uniform Continuity $\implies$ Continuity

To show that Lipschitz continuity directly implies standard continuity in the $(\varepsilon, \delta)$-framework:

* Fix an arbitrary point $x_0 \in \mathbb{R}^n$ and let $\varepsilon > 0$.
* Choose $\delta = \frac{\varepsilon}{\|L\|_{\text{op}}}$ (assuming $\|L\|_{\text{op}} > 0$; if $\|L\|_{\text{op}} = 0$, $L$ is the zero map and continuity is trivial).
* For any $x \in \mathbb{R}^n$ satisfying $\|x - x_0\| < \delta$:

$$\|L(x) - L(x_0)\| = \|L(x - x_0)\| \le \|L\|_{\text{op}} \|x - x_0\| < \|L\|_{\text{op}} \cdot \frac{\varepsilon}{\|L\|_{\text{op}}} = \varepsilon$$

Since $\delta$ depends solely on $\varepsilon$ and $\|L\|_{\text{op}}$ (and not on the point $x_0$), this demonstrates that finite-dimensional linear operators are not only continuous, but **globally and uniformly continuous**.

<!-- page 20 -->

Take $x_k \to x^* \quad : \quad h_k = x^* - x_k$

$$\|h_k\| \to 0 \quad \text{as } k \to \infty$$

$$\|L(x_k) - L(x^*)\| =$$

$$\|L(h_k)\| \le C \|h_k\| \to 0$$

$$\implies L(x_k) \to L(x^*)$$

$$\text{as } k \to \infty$$

{\color{red} Be able to replicate such proof on exam}

<!-- page 21 -->

This proof establishes that **Lipschitz continuity implies sequential continuity** (and therefore standard continuity) for a linear operator $L$.

### Step-by-Step Proof Breakdown

#### 1. Sequential Characterization of Convergence in the Domain

Let $(x_k)_{k=1}^\infty \subset \mathbb{R}^n$ be a sequence converging to $x^* \in \mathbb{R}^n$, denoted $x_k \to x^*$. By the metric definition of convergence in a normed space:

$$\lim_{k \to \infty} \|x_k - x^*\| = 0$$

Defining the error vector (perturbation) as $h_k = x_k - x^*$ (or $h_k = x^* - x_k$), this is equivalent to:

$$\|h_k\| \to 0 \quad \text{as } k \to \infty$$

#### 2. Linearity of the Operator

Evaluating the difference between the images under $L$:

$$L(x_k) - L(x^*) = L(x_k - x^*) = L(h_k)$$

Taking the codomain norm yields the exact equality:

$$\|L(x_k) - L(x^*)\| = \|L(h_k)\|$$

#### 3. Applying the Lipschitz Bound

From the previously established Lipschitz property, there exists a constant $C = \|L\|_{\text{op}} < \infty$ such that $\|L(v)\| \le C\|v\|$ for all $v \in \mathbb{R}^n$. Applying this to $h_k$:

$$\|L(x_k) - L(x^*)\| = \|L(h_k)\| \le C\|h_k\|$$

<!-- page 22 -->

#### 4. The Squeeze Theorem (Sandwich Rule)

Because norms are non-negative, the distance is bounded below and above:

$$0 \le \|L(x_k) - L(x^*)\| \le C\|h_k\|$$

Taking limits as $k \to \infty$:

$$\lim_{k \to \infty} C\|h_k\| = C \cdot \lim_{k \to \infty} \|h_k\| = C \cdot 0 = 0$$

By the **Squeeze Theorem** for real sequences:

$$\lim_{k \to \infty} \|L(x_k) - L(x^*)\| = 0 \implies L(x_k) \to L(x^*) \quad \text{as } k \to \infty$$

### Theorems and Principles Invoked

*   **Sequential Criterion for Continuity:** In metric/normed spaces, a mapping $f$ is continuous at $x^*$ if and only if for every sequence $x_k \to x^*$, the sequence of images satisfies $f(x_k) \to f(x^*)$.
*   **Linearity / Additivity:** The identity $L(x_k) - L(x^*) = L(x_k - x^*)$ allows the continuity problem at an arbitrary point $x^*$ to reduce to continuity at the origin $0$.
*   **Algebra of Limits and the Squeeze Theorem:** Used to pass the limit through the product $C\|h_k\|$ and trap $\|L(x_k) - L(x^*)\|$ to $0$.

### Analytical Significance

This sequence-based argument proves that linear operators commute with limit operations:

$$\lim_{k \to \infty} L(x_k) = L\left(\lim_{k \to \infty} x_k\right)$$

In real analysis and economics (e.g., dynamic programming, fixed-point theory, and comparative statics), this property allows you to interchange linear expectations, matrix multiplications, and projections directly across limiting sequences.

<!-- page 23 -->

Differentiability implies continuity

$$f(a+h) - f(a) = Df(a)h + o(\|h\|)$$

$$\|f(a+h) - f(a)\| = \|Df(a)h + o(\|h\|)\|$$

$$\le C \|h\| + \|o(\|h\|)\| \qquad \text{\color{red}???}$$

$$\to 0$$
$$\text{as } h \to 0$$

$$\|o(\|h\|)\| \to 0$$
$$\text{norm of rem.}$$
$$\text{goes to } 0$$
$$\text{as } h \to 0$$

$$\overline{\phantom{XXXXXXXXXXXXXX}}$$

as we get
arbitrarily close to $a$, ($h \to 0$)
approximation becomes closer
to function value
& remainder error goes
to $0$

<!-- page 24 -->

This argument proves that **(Fréchet) differentiability at a point implies continuity at that point** by decomposing the increment into a bounded linear principal part and a sublinear remainder.

### 1. The Meaning of the Little-$o$ Remainder $o(\|h\|)$

Let $U \subseteq \mathbb{R}^n$ be open, and let $f : U \to \mathbb{R}^m$. By definition, $f$ is **differentiable at $a \in U$** if there exists a continuous linear map $Df(a) : \mathbb{R}^n \to \mathbb{R}^m$ (represented by the Jacobian matrix $J_f(a)$) such that:

$$f(a+h) - f(a) = Df(a)h + r(h)$$

where the error/remainder vector $r(h)$ is $o(\|h\|)$.

Little-$o$ notation means the error vanishes **strictly faster than linearly** with respect to the perturbation length $\|h\|$:

$$\lim_{h \to 0} \frac{\|r(h)\|}{\|h\|} = 0$$

Because $\frac{\|r(h)\|}{\|h\|} \to 0$ as $h \to 0$, it immediately follows that the norm of the remainder vanishes as well:

$$\lim_{h \to 0} \|r(h)\| = \lim_{h \to 0} \left( \frac{\|r(h)\|}{\|h\|} \cdot \|h\| \right) = 0 \cdot 0 = 0$$

---

### 2. Norm Decomposition and Triangle Inequality

Starting from the definition:

$$f(a+h) - f(a) = Df(a)h + r(h)$$

Taking the codomain norm and applying the **triangle inequality** (noting a slight typographical correction from your notes, where an equality was written instead of $\le$):

$$\|f(a+h) - f(a)\| = \|Df(a)h + r(h)\| \le \|Df(a)h\| + \|r(h)\|$$

---

### 3. Where the Multiplier $C$ Comes From

Since the derivative $Df(a)$ is a **linear map** from $\mathbb{R}^n$ to $\mathbb{R}^m$, we apply the linear operator bound derived on the previous pages:

$$\|Df(a)h\| \le C\|h\|$$

where $C = \|Df(a)\|_{\text{op}} < \infty$ is the operator norm of the derivative at the point $a$.

Substituting this into the triangle inequality bound yields:

$$\|f(a+h) - f(a)\| \le C\|h\| + \|r(h)\|$$

*This does not claim that $f$ is globally Lipschitz continuous; rather, it uses the fact that the linear differential operator $Df(a)$ is bounded/Lipschitz to dominate the first-order variation.*

<!-- page 25 -->

### 4. Taking the Limit as $h \to 0$

Now evaluate the limit as the perturbation vector vanishes ($h \to 0$):

* For the linear part: $\lim_{h \to 0} C\|h\| = C \cdot 0 = 0$
* For the remainder: $\lim_{h \to 0} \|r(h)\| = 0$

By the Squeeze Theorem:

$$0 \le \lim_{h \to 0} \|f(a+h) - f(a)\| \le \lim_{h \to 0} \Big(C\|h\| + \|r(h)\|\Big) = 0 + 0 = 0$$

Thus:

$$\lim_{h \to 0} \|f(a+h) - f(a)\| = 0 \iff \lim_{h \to 0} f(a+h) = f(a)$$

Setting $x = a + h$, this is the standard definition of continuity:

$$\lim_{x \to a} f(x) = f(a)$$

Hence, differentiability at $a$ guarantees continuity at $a$.