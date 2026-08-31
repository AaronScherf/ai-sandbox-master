---
source_pdf: Analysis_Exercises.pdf
folder_category: problem_sets
total_pages: 11
routing: hybrid
model: gemini-3.1-flash-lite
pages_repaired: 1
repaired_pages: [5]
tags: [real-analysis, optimization-theory, economics-mathematics, mathematical-economics, mathematical-methods-economics, optimization, economics-applications]
postprocessed: true
---

<!-- page 1 -->

Analysis: Guided Exercises

### Instructions

This problem set develops the main ideas of topology, continuity, and multivariate differential calculus that will be used throughout graduate economics.

Several problems contain guided steps or hints. These are part of the learning process. You should write a complete argument rather than simply answering the individual prompts.

Unless otherwise stated, all norms are Euclidean norms.

## 1 Topology and Continuity in $\mathbb{R}^n$

### Problem 1. Norms and the topology of $\mathbb{R}^n$

For $x = (x_1, \dots, x_n) \in \mathbb{R}^n$, define
$$\|x\|_2 = \left( \sum_{i=1}^n x_i^2 \right)^{1/2}, \quad \|x\|_\infty = \max_{1 \le i \le n} |x_i|.$$

(a) Prove that
$$\|x\|_\infty \le \|x\|_2 \le \sqrt{n} \|x\|_\infty.$$

(b) Deduce that, for a sequence $(x_k) \subseteq \mathbb{R}^n$,
$$\|x_k - x\|_2 \to 0 \iff \|x_k - x\|_\infty \to 0.$$

(c) Show that the two norms generate the same open sets.

*Guidance.* For part (c), compare balls. Given $r > 0$, find $r_1, r_2 > 0$ such that
$$B_{\infty, r_1}(x) \subseteq B_{2, r}(x), \quad B_{2, r_2}(x) \subseteq B_{\infty, r}(x).$$

### Problem 2. Continuous functions and open or closed sets

Let
$$f : \mathbb{R}^n \to \mathbb{R}$$
be continuous.

<!-- page 2 -->

(a) Prove that
$$\{x \in \mathbb{R}^n : f(x) > c\}$$
is open.

(b) Prove that
$$\{x \in \mathbb{R}^n : f(x) \ge c\}$$
is closed.

(c) Use these results, rather than returning directly to the definitions, to classify the following sets as open or closed:
$$A = \{x \in \mathbb{R}^n : \|x\|^2 < 1\},$$
$$B = \{x \in \mathbb{R}^n : x^\top Q x \le 1\},$$
where $Q$ is a fixed symmetric $n \times n$ matrix, and
$$C = \{(x, y) \in \mathbb{R}^2 : y = x^2\}.$$

*Guidance.* Try to express each set as the inverse image of an open or closed subset of $\mathbb{R}$ under a continuous scalar-valued function.

### Problem 3. Closed sets and convergent sequences

Prove that $A \subseteq \mathbb{R}^n$ is closed if and only if
$$x_k \in A, \quad x_k \to x \implies x \in A.$$

*Guided proof.*

First suppose that $A$ is closed and
$$x_k \in A, \quad x_k \to x.$$
Assume, toward a contradiction, that $x \notin A$. Since $A^c$ is open, there exists some $\varepsilon > 0$ such that
$$B_\varepsilon(x) \subseteq A^c.$$
Use convergence of $x_k$ to obtain a contradiction.

For the converse, suppose the sequential property holds but $A$ is not closed. Then $A^c$ is not open. Show that there exists $x \in A^c$ such that, for every $k$,
$$B_{1/k}(x) \cap A \ne \emptyset.$$
Choose
$$x_k \in B_{1/k}(x) \cap A$$
and finish the argument.

*Proof technique to remember.* When a neighborhood property fails, try to construct a sequence.

<!-- page 3 -->

## 2 Compactness and Its Consequences

### Problem 4. A closed subset of a compact set

Suppose $K \subseteq \mathbb{R}^n$ is compact and $F \subseteq K$ is closed. Prove that $F$ is compact.

*Guidance.* Take an arbitrary sequence
$$(x_k) \subseteq F.$$
Since it is also a sequence in $K$, compactness gives a convergent subsequence
$$x_{k_j} \to x.$$
Which assumption guarantees that $x \in F$?

In your proof, make clear the distinct roles played by compactness and closedness.

### Problem 5. Continuous images of compact sets

Suppose $K \subseteq \mathbb{R}^n$ is compact and
$$f : K \to \mathbb{R}^m$$
is continuous.

(a) Prove that $f(K)$ is compact.

(b) Deduce that if $m = 1$, then $f$ attains both a maximum and a minimum on $K$.

(c) Construct examples showing that the conclusion in part (b) can fail if:
(i) the domain is bounded but not closed;
(ii) the domain is closed but unbounded;
(iii) the domain is compact but $f$ is not continuous.

*Guidance for part (a).* Take a sequence
$$y_k \in f(K).$$
Choose $x_k \in K$ such that
$$f(x_k) = y_k.$$
Now use compactness and continuity in that order.

### Problem 6. Continuous bijections from compact sets

Let $K \subseteq \mathbb{R}^n$ be compact, and suppose
$$f : K \to Y \subseteq \mathbb{R}^m$$
is a continuous bijection.

<!-- page 4 -->

Prove that
$$f^{-1} : Y \to K$$
is continuous.

*Guided contradiction argument.* Take a sequence
$$y_k \to y$$
and define
$$x_k = f^{-1}(y_k), \quad x = f^{-1}(y).$$
Suppose that $x_k \not\to x$. Show that there exist $\varepsilon > 0$ and a subsequence $(x_{k_j})$ such that
$$\|x_{k_j} - x\| \ge \varepsilon$$
for every $j$.

Use compactness to extract a further convergent subsequence
$$x_{k_{j_\ell}} \to x^*.$$

Now compare
$$f(x_{k_{j_\ell}}) \to f(x^*)$$
with
$$f(x_{k_{j_\ell}}) = y_{k_{j_\ell}} \to y.$$

Identify where uniqueness of limits is used and where injectivity of $f$ is used.

## 3 Differentiability as Linear Approximation

### Problem 7. The derivative is unique

Suppose $f : \mathbb{R}^n \to \mathbb{R}^m$ satisfies
$$f(x + h) = f(x) + Ah + r_A(h)$$
and also
$$f(x + h) = f(x) + Bh + r_B(h),$$
where $A, B : \mathbb{R}^n \to \mathbb{R}^m$ are linear maps and
$$\frac{\|r_A(h)\|}{\|h\|} \to 0, \quad \frac{\|r_B(h)\|}{\|h\|} \to 0.$$

Prove that
$$A = B.$$

*Guidance.* Fix an arbitrary $v \in \mathbb{R}^n$ and set
$$h = tv.$$

<!-- page 5 -->

Compare the two approximations and divide by $t \ne 0$. Then let $t \to 0$.

Why does showing
$$(A - B)v = 0$$
for every $v$ imply $A = B$?

### Problem 8. Directional derivatives are not enough

Consider
$$f(x, y) = \begin{cases} \dfrac{x^2 y}{x^2 + y^2}, & (x, y) \ne (0, 0), \\ 0, & (x, y) = (0, 0). \end{cases}$$

(a) Prove that $f$ is continuous at $(0, 0)$.

(b) Compute
$$f_x(0, 0), \quad f_y(0, 0).$$

(c) For an arbitrary direction $v = (a, b)$, compute
$$D_v f(0, 0).$$

(d) Show that every directional derivative at the origin exists.

(e) Is the map
$$v \longmapsto D_v f(0, 0)$$
linear?

(f) Deduce that $f$ is not differentiable at the origin.

Conclude by explaining, in your own words, the distinction among
$$\text{partial derivatives}, \quad \text{directional derivatives}, \quad \text{the derivative } Df(x).$$

### Problem 9. Continuous partial derivatives imply differentiability

Suppose
$$f : \mathbb{R}^2 \to \mathbb{R}$$
has partial derivatives in a neighborhood of $(a, b)$, and suppose $f_x$ and $f_y$ are continuous at $(a, b)$.
Prove that $f$ is differentiable at $(a, b)$.

Begin by writing
$$f(a + h, b + k) - f(a, b) = \left[ f(a + h, b + k) - f(a, b + k) \right] + \left[ f(a, b + k) - f(a, b) \right].$$

1. Apply the one-dimensional mean value theorem to the two differences.

<!-- page 6 -->

2. Show that, for suitable intermediate points $\xi$ and $\eta$,

$$f(a + h, b + k) - f(a, b) = f_{x}(\xi, b + k)h + f_{y}(a, \eta)k.$$

3. Subtract
$$f_{x}(a, b)h + f_{y}(a, b)k.$$

4. Bound the absolute value of the resulting remainder by

$$|f_{x}(\xi, b + k) - f_{x}(a, b)| |h| + |f_{y}(a, \eta) - f_{y}(a, b)| |k|.$$

5. Divide by
$$\sqrt{h^2 + k^2}$$
and complete the proof.

Indicate precisely where continuity of the partial derivatives is used.

## 4 Restricting Multivariate Problems to Lines

### Problem 10. The multivariate mean-value idea

Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}$$
be differentiable, and suppose the entire line segment joining $a$ and $b$ lies in $U$.

Define
$$g(t) = f(a + t(b - a)), \quad 0 \le t \le 1.$$

(a) Prove that
$$g'(t) = Df(a + t(b - a))(b - a).$$

(b) Apply the one-dimensional mean value theorem to show that there exists a point $c$ on the segment from $a$ to $b$ such that
$$f(b) - f(a) = Df(c)(b - a).$$

(c) Deduce the bound
$$|f(b) - f(a)| \le \sup_{z \in [a,b]} \|Df(z)\| \|b - a\|.$$

(d) Suppose now that $U$ is convex and
$$Df(x) = 0 \quad \text{for every } x \in U.$$
Prove that $f$ is constant on $U$.

*Proof technique to remember.* A useful strategy in multivariate calculus is
$$\text{multivariate problem} \longrightarrow \text{restrict to a line} \longrightarrow \text{apply one-variable calculus.}$$

6

<!-- page 7 -->

### Problem 11. If the Hessian vanishes, the function is affine

Let $U \subseteq \mathbb{R}^n$ be open and convex. Suppose
$$f : U \to \mathbb{R}$$
is $C^2$ and
$$H_f(x) = 0 \quad \text{for every } x \in U.$$

Prove that there exist $a \in \mathbb{R}^n$ and $b \in \mathbb{R}$ such that
$$f(x) = a^\top x + b \quad \text{for every } x \in U.$$

*Guidance.* Treat
$$\nabla f : U \to \mathbb{R}^n$$
as a function in its own right.
What is
$$D(\nabla f)(x)?$$

Use the previous problem to show that $\nabla f$ is constant. Then consider
$$g(x) = f(x) - a^\top x.$$

### Problem 12. Taylor's theorem in several variables

Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}$$
be $C^2$, and suppose that the line segment from $x$ to $x + h$ lies entirely in $U$.
Define
$$g(t) = f(x + th), \quad 0 \le t \le 1.$$

(a) Show that
$$g'(t) = \nabla f(x + th)^\top h.$$

(b) Show that
$$g''(t) = h^\top H_f(x + th)h.$$

(c) Apply the one-dimensional Taylor theorem to $g$ between 0 and 1 to prove that, for some $\theta \in (0, 1)$,
$$f(x + h) = f(x) + \nabla f(x)^\top h + \frac{1}{2} h^\top H_f(x + \theta h)h.$$

Why does the second-order term involve the scalar quadratic form
$$h^\top H_f h$$
rather than merely the vector $H_f h$?

<!-- page 8 -->

## 5 Inverse and Implicit Functions

### Problem 13. Local versus global invertibility

Consider
$$F(x, y) = \begin{pmatrix} e^x \cos y \\ e^x \sin y \end{pmatrix}.$$

(a) Compute $DF(x, y)$.

(b) Show that
$$\det DF(x, y) \ne 0$$
for every $(x, y) \in \mathbb{R}^2$.

(c) State precisely what the inverse function theorem implies at an arbitrary point $(x, y)$.

(d) Show that
$$F(x, y + 2\pi) = F(x, y).$$

(e) Is $F$ globally one-to-one? Explain why your answer does not contradict the inverse function theorem.

Now consider
$$f(x) = x^3.$$

(f) The function is globally one-to-one, but
$$f'(0) = 0.$$
Why does this not contradict the inverse function theorem?

(g) Write down $f^{-1}$ and determine whether $f^{-1}$ is differentiable at 0.

Your answer should make clear the distinctions between
$$\text{local and global}$$
and between
$$\text{sufficient and necessary conditions.}$$

### Problem 14. What can be solved for implicitly?

Consider the level surface
$$F(x, y, z) = x^2 + y^2 + z^2 - 1 = 0.$$

First consider the point
$$p = (0, 0, 1).$$

<!-- page 9 -->

(a) Can the equation locally be solved in the form
$$z = g(x, y)?$$

Which partial derivative determines the answer?

(b) Can it locally be solved in the form
$$x = h(y, z)?$$

Explain.

Now consider the point
$$q = (1, 0, 0).$$

(c) Repeat parts (a)–(b) at $q$.

(d) Explain geometrically why the answers change as we move from $p$ to $q$.

(e) Suppose that near $p$,
$$z = g(x, y).$$

Starting from
$$F(x, y, g(x, y)) = 0,$$

derive formulas for
$$g_x(x, y), \quad g_y(x, y)$$

using the chain rule.

Do not begin by quoting a memorized implicit differentiation formula.

## 6 Comprehension Check

### Problem 15. Diagnose the statement

For each statement below, decide whether it is true or false.

If it is true, give a short proof or cite the appropriate result and explain why its hypotheses are satisfied. If it is false, give a counterexample and explain which implication fails.

(a) If $f$ is differentiable at $x$, then $f$ is continuous at $x$.

(b) If all partial derivatives of $f$ exist at $x$, then $f$ is differentiable at $x$.

(c) If every directional derivative of $f$ exists at $x$, then $f$ is differentiable at $x$.

(d) If all first partial derivatives exist in a neighborhood of $x$ and are continuous at $x$, then $f$ is differentiable at $x$.

(e) A continuous image of a compact set is compact.

<!-- page 10 -->

(f) A continuous image of a closed set is closed.

(g) A closed subset of a compact set is compact.

(h) If $D f(x)$ is invertible, then $f$ is globally one-to-one.

(i) If $D f(x)$ is singular, then $f$ cannot possess a differentiable local inverse at $x$.

(j) If $D f(x)$ is singular, then $f$ cannot be locally one-to-one near $x$.

(k) If $U \subseteq \mathbb{R}^n$ is convex and $D f(x) = 0$ for every $x \in U$, then $f$ is constant on $U$.

(l) If $U \subseteq \mathbb{R}^n$ is convex and $H_f(x) = 0$ for every $x \in U$, then $f$ is affine on $U$.

## Optional Extensions

The following problems are not required. They provide additional proof practice and connect the topology developed above with later results in multivariate calculus.

### Extension 1. Nested compact sets

Suppose
$$K_1 \supseteq K_2 \supseteq K_3 \supseteq \cdots$$
is a decreasing sequence of nonempty compact subsets of $\mathbb{R}^n$.
Prove that
$$\bigcap_{k=1}^\infty K_k \ne \emptyset.$$

*Guidance.* Choose
$$x_k \in K_k.$$
All of these points belong to $K_1$, so extract a convergent subsequence.
If
$$x_{k_j} \to x,$$
fix an arbitrary $N$. For sufficiently large $j$,
$$k_j \ge N.$$
Use the nestedness of the sets and closedness of $K_N$.

### Extension 2. Invertible matrices form an open set

Identify the space of $n \times n$ real matrices with $\mathbb{R}^{n^2}$, and define
$$GL_n(\mathbb{R}) = \{A \in \mathbb{R}^{n \times n} : \det A \ne 0\}.$$

(a) Prove that $GL_n(\mathbb{R})$ is open.

<!-- page 11 -->

(b) Suppose $f : \mathbb{R}^n \to \mathbb{R}^n$ is $C^1$ and $Df(x^*)$ is invertible. Prove that there exists $\varepsilon > 0$ such that $Df(x)$ remains invertible whenever
$$\|x - x^*\| < \varepsilon.$$

*Guidance.* Regard
$$\det : \mathbb{R}^{n^2} \to \mathbb{R}$$
as a continuous function and write
$$GL_n(\mathbb{R}) = \det{}^{-1}(\mathbb{R} \setminus \{0\}).$$

11