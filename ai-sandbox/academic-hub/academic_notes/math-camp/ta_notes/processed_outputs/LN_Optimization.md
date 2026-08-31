---
source_pdf: LN_Optimization.pdf
folder_category: ta_notes
total_pages: 112
routing: gemini_batched
model: gemini-3.1-flash-lite
pages_repaired: 19
repaired_pages: [9, 10, 20, 35, 53, 55, 58, 62, 66, 71, 72, 73, 82, 83, 87, 91, 94, 101, 109]
tags: [real-analysis, optimization-theory, economics-mathematics, mathematical-economics, mathematical-methods-economics, optimization]
---

<!-- page 1 -->

Part III: Optimization, Convexity and
Correspondences$^\dagger$

Hao Jiang$^*$

2026 PhD Math Camp

Updated on August 20, 2026

__________________________________________________________________
$^*$All remaining errors are my own.
$^\dagger$Typesetting and visual design are informed by public mathematical lecture-note templates, including Gilles
Castel’s lecture notes, rafisics’ lecture-notes template, and Jack’s Math Notes Template with Color Box.

1

<!-- page 2 -->

Contents

Introduction . . . 6

1 Convex Sets and Convex Geometry . . . 7
1.1 Convex Sets and Convex Combinations . . . 7
1.2 Convex Hulls . . . 9
1.3 Convex Cones . . . 10
1.4 Operations That Preserve Convexity . . . 11
1.5 Affine Sets, Hyperplanes, and Half-Spaces . . . 12
1.6 Relative Interior . . . 14
1.7 Supporting Hyperplanes . . . 14
1.8 Support Functions and Linear Valuation . . . 15
1.9 Projection onto a Closed Convex Set . . . 17
1.10 Separating Hyperplanes . . . 21

2 Convex and Concave Functions . . . 23
2.1 Convexity and Concavity . . . 23
2.2 Jensen’s Inequality . . . 24
2.3 First-Order Characterization of Concavity . . . 26
2.4 Monotonicity of the Gradient . . . 28
2.5 Second-Order Characterization and the Hessian . . . 29
2.6 Practical Definiteness Checks . . . 31
2.7 Epigraphs and Hypographs . . . 32
2.8 Quasiconcavity . . . 33
2.9 Strict Curvature and Uniqueness . . . 36

3 Optimization in Euclidean Space . . . 37
3.1 The Optimization Problem . . . 37
3.2 Existence: Compactness and Continuity . . . 38
3.3 Existence on Unbounded Sets: Coercivity . . . 39
3.4 Local and Global Optima . . . 41
3.5 Interior First-Order Conditions . . . 42
3.6 Second-Order Conditions . . . 43

2

<!-- page 3 -->

3.7 Optimization over a Convex Set . . . 44
3.8 Normal Cones . . . . . . . . . . . . . . 46

4 Equality-Constrained Optimization . . . 47
4.1 Tangent Directions to the Feasible Set . . . 47
4.2 The Geometry of Lagrange Multipliers . . . 48
4.3 The Lagrangian . . . . . . . . . . . . . 49
4.4 Why the Rank Condition Matters . . . . 50
4.5 Second-Order Conditions on the Tangent Space . . . 50
4.6 The Reduced Hessian . . . . . . . . . . 51
4.7 Bordered Hessians . . . . . . . . . . . 52
4.8 Shadow-Value Interpretation of Multipliers . . . 56

5 Inequality-Constrained Optimization . . . 57
5.1 Active and Inactive Constraints . . . . 57
5.2 The KKT Conditions . . . . . . . . . . 58
5.3 Complementary Slackness . . . . . . . 59
5.4 Constraint Qualifications . . . . . . . 61
5.5 Second-Order KKT Conditions and Critical Directions . . . 62
5.6 KKT Sufficiency for Concave Problems . . . 63
5.7 KKT as a Normal-Cone Condition . . . 64
5.8 Worked Example: Consumer Choice with Corners . . . 65
5.9 Worked Example: Resource Allocation . . . 66

6 Convex Optimization and Duality . . . 67
6.1 The Lagrangian as a Relaxed Objective . . . 67
6.2 The Dual Function and Dual Problem . . . 68
6.3 Weak Duality . . . . . . . . . . . . . . 69
6.4 Strong Duality . . . . . . . . . . . . . 70
6.5 Complementary Slackness from Zero Duality Gap . . . 71
6.6 Saddle Points of the Lagrangian . . . . 71
6.7 A Simple Duality Example . . . . . . . 72

3

<!-- page 4 -->

7 Parameterized Optimization and Value Functions ... 74
7.1 Smooth Comparative Statics from First-Order Conditions ... 75
7.2 Constrained Comparative Statics and the KKT Matrix ... 76
7.3 The Scalar Comparative-Statics Formula ... 78
7.4 The Envelope Theorem: Unconstrained Case ... 79
7.5 A Second-Order Envelope Formula ... 81
7.6 Constrained Envelope Theorem ... 82
7.7 Example: Indirect Utility and Roy’s Identity ... 83
7.8 Example: Profit Function and Hotelling’s Lemma ... 84
7.9 Concavity and Convexity of Value Functions ... 84
7.10 Indirect Utility and Expenditure as Value Functions ... 85

8 Correspondences ... 86
8.1 Set-Valued Maps ... 87
8.2 Graphs and Inverse Images ... 88
8.3 Upper Hemicontinuity ... 89
8.4 Sequential Form of Upper Hemicontinuity ... 89
8.5 Lower Hemicontinuity ... 90
8.6 Why the Two Notions Differ ... 91
8.7 Compact- and Convex-Valued Correspondences ... 92
8.8 Closed Graph and Upper Hemicontinuity ... 92
8.9 A Small Calculus of Correspondences ... 93
8.10 A Correspondence Can Be Better Behaved Than Any Selection ... 94

9 The Maximum Theorem ... 95
9.1 The Parameterized Problem ... 95
9.2 One-Sided Stability of the Value Function ... 96
9.3 Berge’s Maximum Theorem ... 97
9.4 Unique Optimizers Give Continuous Policy Functions ... 100
9.5 Example: Quadratic Tracking Problem ... 100
9.6 Example: Demand Correspondence ... 101
9.7 What Berge’s Theorem Does Not Give ... 102

4

<!-- page 5 -->

10 Fixed-Point Theorems 102

10.1 Fixed Points ... 102

10.2 Brouwer’s Fixed-Point Theorem ... 103

10.3 Why Brouwer’s Assumptions Matter ... 105

10.4 Approximate Fixed Points and Residuals ... 105

10.5 From Functions to Correspondences ... 106

10.6 Nash Equilibrium as a Fixed Point ... 107

10.7 Finite Games and Mixed Strategies ... 109

10.8 Brouwer versus Kakutani ... 110

10.9 The Architecture of an Equilibrium-Existence Proof ... 110

References and Further Reading 111

5

<!-- page 6 -->

# Introduction

Optimization problems appear almost everywhere in economics. A household chooses a consumption plan, a firm chooses inputs, a worker chooses search effort, a planner chooses an allocation, and an econometrician chooses a parameter vector that minimizes an objective function. In each case we are asked to select the best point from a set of feasible alternatives.

At first sight this sounds like a problem for calculus. We write down first-order conditions, solve them, and call the answer an optimum. That approach is often useful, but it hides several logically different questions.

First, does an optimizer exist at all? A first-order condition cannot answer this. For example, the function
$$f(x) = x$$
has no maximizer on the open interval $(0, 1)$ even though the problem is perfectly smooth. Existence is fundamentally a question about the geometry of the feasible set and the continuity of the objective.

Second, if an optimizer exists, how can we recognize it? Here derivatives become important. But a stationary point need not be a maximum, and a local maximum need not be globally optimal. We therefore need curvature conditions that allow local information to carry global force.

Third, economic models rarely contain only one optimization problem. Prices, productivity, wealth, policies, and aggregate states vary. We must understand how the optimal value and the set of optimal choices change when the underlying problem changes.

The material is organized around one progression:
$$\text{convex geometry} \longrightarrow \text{optimality and duality}$$
$$\longrightarrow \text{value functions and correspondences} \longrightarrow \text{fixed points.}$$

Convexity comes first because it is what turns local first-order information into global statements. Correspondences enter when optimization need not select a unique point, and fixed-point theorems then turn those set-valued choices into equilibrium existence.

Throughout, all spaces are finite-dimensional Euclidean spaces unless stated otherwise. The analysis developed in Part II—compactness, continuity, differentiability, Taylor expansion, and the geometry of gradients—will be used repeatedly without being redeveloped from first principles.

6

<!-- page 7 -->

# 1 Convex Sets and Convex Geometry

Part II already introduced convex sets as an important class of connected sets. We now return to convexity for a different reason. In optimization, convexity says that if two choices are feasible, then every average of those choices is feasible as well. This simple geometric property is what allows local movements to reveal global information.

The basic object is a line segment. Given $x, y \in \mathbb{R}^n$, the segment joining them is
$$[x, y] = \{(1 - t)x + ty : 0 \leq t \leq 1\}.$$

The parameter $t$ moves continuously from $x$ to $y$. A set is convex precisely when it contains every such segment whose endpoints it contains.

## 1.1 Convex Sets and Convex Combinations

**Definition 1.1 — Convex Set**

A set
$$C \subseteq \mathbb{R}^n$$
is convex if for every $x, y \in C$ and every $t \in [0, 1]$,
$$(1 - t)x + ty \in C.$$
Equivalently, the line segment joining any two points of $C$ is contained in $C$.

The definition is geometric, but it is also the form that appears naturally in probability and economics. If an agent chooses $x$ with probability $1 - t$ and $y$ with probability $t$, then the expected choice is
$$(1 - t)x + ty.$$
Thus convexity says that averages, mixtures, or lotteries over feasible points remain feasible.

**Example 1.2 — Basic Convex and Nonconvex Sets**

The following sets are convex:
$$\mathbb{R}^n, \quad \{x \in \mathbb{R}^n : a^T x = b\}, \quad \{x \in \mathbb{R}^n : a^T x \leq b\},$$
Euclidean balls, rectangles, simplices, and linear subspaces.

By contrast, the unit sphere
$$\{x \in \mathbb{R}^n : \|x\| = 1\}$$

7

<!-- page 8 -->

is not convex when $n \geq 2$. Two points on the sphere generally have a midpoint lying strictly
inside the sphere.

[Image: Two diagrams showing convexity. The left diagram shows a convex shape with points $x$ and $y$ connected by a line segment entirely within the shape. The right diagram shows a nonconvex shape with an inward notch; the line segment between $x$ and $y$ crosses the "missing notch" outside the shape.]

Figure 1: Convexity requires the entire segment between two feasible points to remain inside the
feasible set. On the right, the inward notch removes part of the segment.

The definition extends from two points to any finite collection.

**Definition 1.3 — Convex Combination**

Let $x_1, \dots, x_m \in \mathbb{R}^n$. A point of the form
$$\sum_{i=1}^{m} \lambda_i x_i,$$
where
$$\lambda_i \geq 0, \quad \sum_{i=1}^{m} \lambda_i = 1,$$
is called a convex combination of $x_1, \dots, x_m$.

**Proposition 1.4 — Convex Sets Contain Finite Convex Combinations**

If $C$ is convex and $x_1, \dots, x_m \in C$, then every convex combination
$$\sum_{i=1}^{m} \lambda_i x_i$$
belongs to $C$.

8

<!-- page 9 -->

**Proof**

The claim follows by induction on $m$. The case $m = 2$ is exactly the definition of convexity.
Suppose the result holds for $m - 1$ points. Let
$$\lambda_1, \dots, \lambda_m \geq 0, \quad \sum_{i=1}^m \lambda_i = 1.$$
If $\lambda_m = 1$, the convex combination equals $x_m \in C$. Otherwise set
$$\alpha = 1 - \lambda_m > 0$$
and define
$$y = \sum_{i=1}^{m-1} \frac{\lambda_i}{\alpha} x_i.$$
The coefficients in this sum are nonnegative and add to one, so the induction hypothesis gives $y \in C$. Then
$$\sum_{i=1}^m \lambda_i x_i = \alpha y + \lambda_m x_m,$$
which belongs to $C$ by convexity.

This proposition allows us to move freely between the two-point and many-point versions of convexity. It also explains why probability distributions naturally enter convex analysis: an expectation is an average with nonnegative weights summing to one.

### 1.2 Convex Hulls

Given an arbitrary set, we can ask for the smallest convex set that contains it. The answer is obtained by allowing all finite convex combinations.

**Definition 1.5 — Convex Hull**
For $A \subseteq \mathbb{R}^n$, the convex hull of $A$ is
$$\text{co}(A) = \left\{ \sum_{i=1}^m \lambda_i x_i : \begin{array}{l} m \in \mathbb{N}, x_i \in A, \\ \lambda_i \geq 0, \sum_{i=1}^m \lambda_i = 1 \end{array} \right\}.$$

**Proposition 1.6 — Minimality of the Convex Hull**
The set $\text{co}(A)$ is convex, contains $A$, and is contained in every convex set that contains $A$.

9

<!-- page 10 -->

**Proof**

Every $x \in A$ belongs to $\text{co}(A)$ by choosing the one-point combination $x$.
To show convexity, take
$$u = \sum_{i=1}^m \alpha_i x_i, \quad v = \sum_{j=1}^k \beta_j y_j$$
in $\text{co}(A)$ and $t \in [0, 1]$. Then
$$(1 - t)u + tv = \sum_{i=1}^m (1 - t)\alpha_i x_i + \sum_{j=1}^k t\beta_j y_j.$$
All coefficients are nonnegative and their sum is
$$(1 - t) \sum_i \alpha_i + t \sum_j \beta_j = 1.$$
Hence $(1 - t)u + tv \in \text{co}(A)$.
Finally, if $C$ is convex and contains $A$, then proposition 1.4 implies that every finite convex combination of points of $A$ belongs to $C$. Therefore
$$\text{co}(A) \subseteq C.$$

A useful economic interpretation is randomization. If $A$ is the set of deterministic outcomes available to an agent, then $\text{co}(A)$ is the set of expected outcomes that can be generated by finite lotteries over those alternatives.

### 1.3 Convex Cones

Convex combinations keep coefficients nonnegative and force them to sum to one. If we drop the adding-up restriction, we obtain a cone. Cones are useful whenever only the *direction* of a vector matters, as with feasible directions, normal vectors, and KKT multipliers.

**Definition 1.7 — Cone and Convex Cone**
A set $K \subseteq \mathbb{R}^n$ is a cone if
$$x \in K, \alpha \geq 0 \implies \alpha x \in K.$$
It is a convex cone if, in addition,
$$x, y \in K, \alpha, \beta \geq 0 \implies \alpha x + \beta y \in K.$$

The nonnegative orthant
$$\mathbb{R}^n_+ = \{x \in \mathbb{R}^n : x_i \geq 0 \ \forall i\}$$

10

<!-- page 11 -->

is the basic example. More generally, given vectors $v_1, \dots, v_m$, the set
$$\text{cone}\{v_1, \dots, v_m\} = \left\{ \sum_{i=1}^m \lambda_i v_i : \lambda_i \geq 0 \right\}$$
is the convex cone generated by those vectors.
This is exactly the geometry that will reappear in KKT conditions: the outward normal at an optimum is represented as a nonnegative combination of active constraint normals.

## 1.4 Operations That Preserve Convexity

Economic feasible sets are usually constructed from several restrictions. We therefore need simple rules for building new convex sets from old ones.

**Proposition 1.8 — Intersections Preserve Convexity**

Let $\{C_\alpha\}_{\alpha \in I}$ be any family of convex subsets of $\mathbb{R}^n$. Then
$$\bigcap_{\alpha \in I} C_\alpha$$
is convex.

**Proof**

Take $x, y$ in the intersection. Then $x, y \in C_\alpha$ for every $\alpha$. Since each $C_\alpha$ is convex,
$$(1 - t)x + ty \in C_\alpha$$
for every $t \in [0, 1]$ and every $\alpha$. Hence the same point belongs to the intersection.

**Example 1.9 — Linear Inequalities**

Consider
$$C = \{x \in \mathbb{R}^n : Ax \leq b\},$$
where the inequality is interpreted componentwise. Each row of $Ax \leq b$ defines a half-space. Since half-spaces are convex and intersections preserve convexity, $C$ is convex.
This is why feasible sets in linear programming are convex automatically.

Convexity is also preserved by affine transformations.

11

<!-- page 12 -->

**Proposition 1.10 — Affine Images and Inverse Images**

Let
$$T(x) = Ax + b$$
be an affine mapping.
(i) If $C$ is convex, then $T(C)$ is convex.
(ii) If $D$ is convex, then the inverse image
$$T^{-1}(D) = \{x : T(x) \in D\}$$
is convex.

**Proof**

For the first statement, take $u = T(x)$ and $v = T(y)$ with $x, y \in C$. Then
$$(1 - t)u + tv = A((1 - t)x + ty) + b = T((1 - t)x + ty).$$
Because $C$ is convex, the point $(1 - t)x + ty$ belongs to $C$.

For the second statement, suppose $x, y \in T^{-1}(D)$. Then $T(x), T(y) \in D$, and
$$T((1 - t)x + ty) = (1 - t)T(x) + tT(y) \in D.$$
Hence $(1 - t)x + ty \in T^{-1}(D)$.

**1.5 Affine Sets, Hyperplanes, and Half-Spaces**

Convexity allows coefficients between zero and one. If we instead allow arbitrary real coefficients that sum to one, we obtain affine geometry.

**Definition 1.11 — Affine Set**

A set $A \subseteq \mathbb{R}^n$ is affine if for every $x, y \in A$ and every $t \in \mathbb{R}$,
$$(1 - t)x + ty \in A.$$

An affine set contains the entire line through any two of its points. Every linear subspace is affine, but affine sets need not pass through the origin. In fact, every nonempty affine set is a translated linear subspace.

12

<!-- page 13 -->

**Proposition 1.12 — Affine Sets Are Translated Subspaces**

Let $A \subseteq \mathbb{R}^n$ be nonempty. Then $A$ is affine if and only if there exist a linear subspace $V$ and a point $x_0$ such that
$$A = x_0 + V.$$

**Proof**

Suppose first that $A$ is affine and choose $x_0 \in A$. Set
$$V = A - x_0 = \{x - x_0 : x \in A\}.$$
We show that $V$ is a subspace. Clearly $0 \in V$. If $u = x - x_0$ and $v = y - x_0$ belong to $V$, and $\alpha, \beta \in \mathbb{R}$, then
$$\alpha u + \beta v + x_0 = \alpha x + \beta y + (1 - \alpha - \beta)x_0.$$
The coefficients on the right sum to one, and repeated use of the affine property shows that this affine combination belongs to $A$. Hence $\alpha u + \beta v \in V$. Therefore $V$ is a subspace and $A = x_0 + V$.

Conversely, if $A = x_0 + V$ with $V$ a subspace, then for $x = x_0 + u$ and $y = x_0 + v$,
$$(1 - t)x + ty = x_0 + (1 - t)u + tv \in x_0 + V$$
for every $t \in \mathbb{R}$.

The most important affine sets for optimization are hyperplanes.

**Definition 1.13 — Hyperplane and Half-Spaces**

Let $a \in \mathbb{R}^n$ with $a \neq 0$ and let $b \in \mathbb{R}$. The set
$$H = \{x \in \mathbb{R}^n : a^T x = b\}$$
is a **hyperplane**. The sets
$$H^- = \{x : a^T x \leq b\}, \quad H^+ = \{x : a^T x \geq b\}$$
are the corresponding closed **half-spaces**.

The vector $a$ is normal to the hyperplane. If $x, y \in H$, then
$$a^T(x - y) = 0,$$
so every direction within the hyperplane is orthogonal to $a$.

<!-- page 14 -->

The budget set from consumer theory is the canonical economic example:
$$B(p, w) = \{x \in \mathbb{R}^L_+ : p^T x \leq w\}.$$
The budget hyperplane $p^T x = w$ has normal vector $p$. Prices therefore define a linear functional that ranks bundles according to expenditure.

**1.6 Relative Interior**

A convex set may live in a lower-dimensional affine space. A line segment in $\mathbb{R}^2$ has empty ordinary interior, even though it clearly has points that are "inside" the segment. For optimization with equality constraints, the correct notion is interior relative to the affine hull.

**Definition 1.14 — Affine Hull and Relative Interior**

The **affine hull** of a set $C$, denoted $\text{aff}(C)$, is the smallest affine set containing $C$.
The **relative interior** of $C$ is
$$\text{relint}(C) = \{x \in C : \exists r > 0 \text{ such that } B_r(x) \cap \text{aff}(C) \subseteq C\}.$$

For a full-dimensional convex set, relative interior agrees with ordinary interior. For a line segment, the relative interior is the segment without its two endpoints. The notion will reappear when we discuss strict feasibility and constraint qualifications.

**1.7 Supporting Hyperplanes**

A hyperplane can do more than describe a linear constraint. It can touch a convex set at a boundary point while leaving the entire set on one side.

**Definition 1.15 — Supporting Hyperplane**

Let $C \subseteq \mathbb{R}^n$ and let $x^* \in C$. A hyperplane
$$H = \{x : a^T x = b\}, \quad a \neq 0,$$
**supports** $C$ at $x^*$ if
$$a^T x^* = b$$
and either
$$a^T x \leq b \quad \forall x \in C,$$
or
$$a^T x \geq b \quad \forall x \in C.$$

Supporting hyperplanes are the geometric prototype of shadow prices. After orienting the normal

<!-- page 15 -->

[Image: A convex set C in the x1-x2 plane. A line (supporting hyperplane) touches the boundary of C at point x*. An arrow labeled "outward normal a" points away from C at x*.]

Figure 2: A supporting hyperplane touches the convex set at $x^*$ without cutting through it. Once the normal is oriented outward, $a^T x \leq a^T x^*$ for every $x \in C$.

vector so that the set lies in the half-space
$$a^T x \leq a^T x^*,$$
the vector $a$ assigns a linear value to each point and $x^*$ maximizes that linear value over the set. Reversing the sign of $a$ reverses the orientation but not the hyperplane itself.

With this orientation, the following two statements are the same:
$$a^T x \leq a^T x^* \quad \forall x \in C$$
and
$$x^* \in \arg \max_{x \in C} a^T x.$$

Thus linear optimization and supporting geometry are two descriptions of the same object.

**1.8 Support Functions and Linear Valuation**

A supporting hyperplane can be encoded by a scalar-valued function. Given a set of possible vectors, ask how large a linear valuation can be on that set. This construction is simple, but it links convex geometry directly to profit maximization and duality.

**Definition 1.16 — Support Function**

Let $A \subseteq \mathbb{R}^n$ be nonempty. Its **support function** is
$$\sigma_A(p) = \sup_{x \in A} p^T x, \quad p \in \mathbb{R}^n.$$

<!-- page 16 -->

The value may be $+\infty$ when $A$ is unbounded in a direction valued positively by $p$. If $A$ is compact, the supremum is finite and is attained.

The terminology comes from supporting hyperplanes. If $A$ is compact and $x^*$ maximizes $p^T x$ over $A$, then
$$p^T x \leq \sigma_A(p) = p^T x^* \quad \forall x \in A.$$
Thus the level set
$$\{x : p^T x = \sigma_A(p)\}$$
is a supporting hyperplane whenever $p \neq 0$.

**Proposition 1.17 — Basic Properties of the Support Function**

Let $A \subseteq \mathbb{R}^n$ be nonempty. Then:
(i) $\sigma_A$ is convex;
(ii) $\sigma_A$ is positively homogeneous:
$$\sigma_A(tp) = t\sigma_A(p) \quad t \geq 0;$$
(iii) $\sigma_A$ depends only on the closed convex hull of $A$:
$$\sigma_A = \sigma_{\overline{\text{co}(A)}}.$$
If $A$ is bounded and
$$M = \sup_{x \in A} \|x\| < \infty,$$
then
$$|\sigma_A(p) - \sigma_A(q)| \leq M\|p - q\|,$$
so the support function is globally Lipschitz.

**Proof**

For convexity, let $p, q \in \mathbb{R}^n$ and $t \in [0, 1]$. For every $x \in A$,
$$((1 - t)p + tq)^T x = (1 - t)p^T x + tq^T x \leq (1 - t)\sigma_A(p) + t\sigma_A(q).$$
Taking the supremum over $x$ gives convexity.
Positive homogeneity follows directly from
$$\sup_{x \in A} (tp)^T x = t \sup_{x \in A} p^T x \quad t \geq 0.$$

<!-- page 17 -->

A linear functional has the same supremum on $A$ as on all finite convex combinations of points in $A$, and continuity of $x \mapsto p^T x$ leaves the supremum unchanged after taking closure. Hence $\sigma_A = \sigma_{\overline{\text{co}(A)}}$.
Finally,
$$\sigma_A(p) - \sigma_A(q) \leq \sup_{x \in A} (p - q)^T x$$
$$\leq M\|p - q\|.$$
Interchanging $p$ and $q$ gives the absolute-value bound.

**Example 1.18 — Profit Is a Support Function**

Let $Y \subseteq \mathbb{R}^L$ be a firm's set of technologically feasible net-output vectors. At price vector $p$, competitive profit is
$$\pi(p) = \sup_{y \in Y} p^T y = \sigma_Y(p).$$
Therefore profit is convex and positively homogeneous in prices, regardless of whether $Y$ itself is convex. Moreover,
$$\sigma_Y = \sigma_{\overline{\text{co}(Y)}}.$$
Linear prices therefore cannot distinguish a technology set from its closed convex hull when we observe only the profit function. This is a useful example of a general principle: optimization by linear functionals naturally sees convexified opportunity sets.

**1.9 Projection onto a Closed Convex Set**

The cleanest proof of separation begins with a geometric fact that is useful in its own right: every point has a unique closest point in a nonempty closed convex set.

**Theorem 1.19 — Projection onto a Closed Convex Set**

Let $C \subseteq \mathbb{R}^n$ be nonempty, closed, and convex. For every $y \in \mathbb{R}^n$, there exists a unique point
$$P_C(y) \in C$$
such that
$$\|y - P_C(y)\| = \inf_{x \in C} \|y - x\|.$$

<!-- page 18 -->

**Proof**

We first prove existence. Choose a minimizing sequence $\{x_k\} \subseteq C$ such that
$$\|y - x_k\| \to \inf_{x \in C} \|y - x\|.$$
The sequence is bounded: eventually all $x_k$ lie in some closed ball centered at $y$. By Bolzano–Weierstrass, a subsequence converges to some $x^*$. Since $C$ is closed, $x^* \in C$. Continuity of the norm gives
$$\|y - x^*\| = \inf_{x \in C} \|y - x\|.$$
For uniqueness, suppose $x_1, x_2 \in C$ are distinct minimizers and write
$$d = \|y - x_1\| = \|y - x_2\|.$$
Convexity implies that their midpoint
$$m = \frac{x_1 + x_2}{2}$$
belongs to $C$. The parallelogram identity gives
$$\|y - m\|^2 = \frac{1}{2}\|y - x_1\|^2 + \frac{1}{2}\|y - x_2\|^2 - \frac{1}{4}\|x_1 - x_2\|^2 < d^2,$$
contradicting minimality. Hence the minimizer is unique.

The closest-point condition has a first-order geometric implication.

**Proposition 1.20 — Projection Inequality**

Let $x^* = P_C(y)$. Then
$$(y - x^*)^T(x - x^*) \leq 0 \quad \forall x \in C.$$

**Proof**

Fix $x \in C$. For $t \in [0, 1]$, convexity gives
$$x_t = x^* + t(x - x^*) \in C.$$
Since $x^*$ minimizes distance to $y$, the function
$$\phi(t) = \|y - x_t\|^2$$

<!-- page 19 -->

has a minimum at $t = 0$ over $[0, 1]$. Therefore its right derivative satisfies
$$\phi'(0^+) \geq 0.$$
But
$$\phi'(0) = -2(y - x^*)^T(x - x^*),$$
which gives the claimed inequality.

The vector $y - x^*$ therefore points outward from the set: every feasible direction from $x^*$ forms a nonacute angle with the outward vector $y - x^*$.

**Proposition 1.21 — Projection Is Nonexpansive**

Let $C \subseteq \mathbb{R}^n$ be nonempty, closed, and convex. Then
$$\|P_C(y) - P_C(z)\| \leq \|y - z\| \quad \forall y, z \in \mathbb{R}^n.$$
In particular, the projection map $P_C : \mathbb{R}^n \to C$ is continuous.

**Proof**

Set
$$u = P_C(y), \quad v = P_C(z).$$
The projection inequality applied first to $y$ and then to $z$ gives
$$(y - u)^T(v - u) \leq 0$$
and
$$(z - v)^T(u - v) \leq 0.$$
Equivalently,
$$(y - u)^T(u - v) \geq 0, \quad -(z - v)^T(u - v) \geq 0.$$
Adding yields
$$(y - z)^T(u - v) \geq \|u - v\|^2.$$
By Cauchy–Schwarz,
$$\|u - v\|^2 \leq \|y - z\|\|u - v\|.$$
If $u \neq v$, divide by $\|u - v\|$; if $u = v$, the conclusion is immediate.

<!-- page 20 -->

**Example 1.22 — Projection as Constrained Least Squares**

Suppose an unrestricted estimator or target vector is $\hat{\beta} \in \mathbb{R}^n$, but prior restrictions require
$$\beta \in C,$$
where $C$ is nonempty, closed, and convex. The constrained quadratic problem
$$\min_{\beta \in C} \|\beta - \hat{\beta}\|^2$$
has the unique solution
$$\beta^C = P_C(\hat{\beta}).$$
The projection inequality becomes
$$(\hat{\beta} - \beta^C)^T(\beta - \beta^C) \leq 0 \quad \forall \beta \in C.$$
If $C$ is a linear subspace, both $\beta^C + h$ and $\beta^C - h$ are feasible whenever $h \in C$. Applying the inequality to both directions forces
$$(\hat{\beta} - \beta^C)^T h = 0 \quad \forall h \in C.$$
Thus ordinary least-squares orthogonality is the subspace case of the more general projection inequality for convex restrictions.

[Image: A convex set C. A point y outside C. A point x* = P_C(y) on the boundary of C. A dashed line tangent to C at x*. A solid line passing through x* perpendicular to the vector y - x*, labeled "strict separator". An arrow from x* to y labeled "y - x*".]

Figure 3: Projection produces separation. The vector $y - x^*$ is normal to a supporting hyperplane at the closest point; translating that hyperplane toward $y$ gives strict separation.

<!-- page 21 -->

**1.10 Separating Hyperplanes**

We can now prove the fundamental separation result.

**Theorem 1.23 — Strict Separation of a Point and a Closed Convex Set**

Let $C \subseteq \mathbb{R}^n$ be nonempty, closed, and convex, and let $y \notin C$. Then there exist $a \neq 0$ and $b \in \mathbb{R}$ such that
$$a^T x < b < a^T y \quad \forall x \in C.$$

**Proof**

Let
$$x^* = P_C(y)$$
be the closest point in $C$ to $y$, and set
$$a = y - x^*.$$
Because $y \notin C$, we have $a \neq 0$.
By proposition 1.20,
$$a^T(x - x^*) \leq 0 \quad \forall x \in C,$$
so
$$a^T x \leq a^T x^* \quad \forall x \in C.$$
On the other hand,
$$a^T y = a^T x^* + \|a\|^2 > a^T x^*.$$
Choose any number $b$ satisfying
$$a^T x^* < b < a^T y.$$
Then
$$a^T x < b < a^T y$$
for every $x \in C$.

The point-versus-set result extends to two convex sets when one of them is compact. The compactness assumption guarantees that the positive distance between the two sets is attained.

**Theorem 1.24 — Strong Separation of Two Convex Sets**

Let $K, C \subseteq \mathbb{R}^n$ be nonempty, disjoint, and convex. Suppose $K$ is compact and $C$ is closed. Then

<!-- page 22 -->

there exists a nonzero vector $a$ such that
$$\sup_{y \in C} a^T y < \inf_{x \in K} a^T x.$$
Thus the two sets lie on opposite sides of a hyperplane with a strictly positive gap.

**Proof**

For $x \in K$, let
$$d_C(x) = \inf_{y \in C} \|x - y\|.$$
The distance function is continuous, and because $K$ is compact it attains its minimum at some $x^* \in K$. Since $K$ and $C$ are disjoint and $C$ is closed,
$$d_C(x^*) > 0.$$
Let
$$y^* = P_C(x^*)$$
and set
$$a = x^* - y^* \neq 0.$$
The projection inequality gives
$$a^T(y - y^*) \leq 0 \quad \forall y \in C,$$
so
$$a^T y \leq a^T y^*.$$
Because $(x^*, y^*)$ realizes the minimum distance between $K$ and $C$, the point $x^*$ also minimizes $x \mapsto \|x - y^*\|$ over $K$. Repeating the same one-sided derivative argument along the segment from $x^*$ to any $x \in K$ gives
$$a^T(x - x^*) \geq 0,$$
so
$$a^T x \geq a^T x^*.$$
Finally,
$$a^T x^* - a^T y^* = \|a\|^2 > 0.$$
Combining the inequalities proves the strict gap.

<!-- page 23 -->

**Remark 1.25 — Separation Terminology**

Authors use slightly different terminology for separation. The economically important distinction is whether the linear functional merely orders the two sets or separates them with a positive margin. The theorem above gives the stronger conclusion
$$\sup_{C} a^T y < \inf_{K} a^T x,$$
which is often called *strong separation*. The point-versus-closed-set theorem is the special case $K = \{y\}$.

The separation results are one of the deepest reasons convexity is so useful in economics. If an alternative lies outside a closed convex opportunity set—or if two convex opportunity sets are disjoint under the hypotheses above—a linear functional can certify that fact. In economic language, a price vector can separate what is attainable from what is not.

This same geometric idea will reappear twice. KKT multipliers represent an outward normal as a combination of active constraint normals. Dual variables then turn that normal into a numerical bound on the primal objective. Separation, KKT, and duality are therefore not three unrelated techniques; they are three views of the same supporting geometry.

**2 Convex and Concave Functions**

Convex sets describe the geometry of feasible choices. We now turn to the geometry of objective functions.

For maximization problems, the natural curvature assumption is concavity. Its importance is not merely that a concave function has a familiar "bowl turned upside down" shape. The crucial fact is that concavity converts local comparisons into global comparisons. Once a differentiable concave function has no profitable first-order direction, there is no profitable move anywhere in the domain.

**2.1 Convexity and Concavity**

Let $C \subseteq \mathbb{R}^n$ be convex. The line segment between any $x, y \in C$ is contained in the domain, so it makes sense to compare the value of a function at an average of $x$ and $y$ with the average of the function values.

**Definition 2.1 — Convex and Concave Functions**

A function
$$f : C \to \mathbb{R}$$

<!-- page 24 -->

is **convex** if
$$f((1 - t)x + ty) \leq (1 - t)f(x) + tf(y)$$
for every $x, y \in C$ and every $t \in [0, 1]$.
It is **concave** if
$$f((1 - t)x + ty) \geq (1 - t)f(x) + tf(y)$$
for every $x, y \in C$ and every $t \in [0, 1]$.
The function is **strictly convex** or **strictly concave** if the corresponding inequality is strict whenever $x \neq y$ and $t \in (0, 1)$.

A function is concave if and only if its negative is convex. Thus most results can be stated for one class and translated to the other by multiplying by $-1$.

Geometrically, the graph of a convex function lies below the chord joining any two points on the graph. The graph of a concave function lies above its chords.

**Example 2.2 — Some Familiar Curvature Patterns**

On their natural domains:
$$x \mapsto x^2$$
is strictly convex,
$$x \mapsto \log x$$
is strictly concave on $(0, \infty)$, and
$$x \mapsto ax + b$$
is both convex and concave.
For $0 < \alpha < 1$, the function
$$x \mapsto x^\alpha$$
is strictly concave on $(0, \infty)$ because
$$\frac{d^2}{dx^2} x^\alpha = \alpha(\alpha - 1)x^{\alpha - 2} < 0.$$

**2.2 Jensen’s Inequality**

The two-point definition extends to finite averages exactly as convexity of sets did.

<!-- page 25 -->

Figure 4: The chord comparison is the geometric content of convexity and concavity.

**Theorem 2.3 — Finite Jensen Inequality**

Let $C$ be convex, let $x_1, \dots, x_m \in C$, and let
$$\lambda_i \geq 0, \quad \sum_{i=1}^m \lambda_i = 1.$$
If $f$ is convex, then
$$f\left(\sum_{i=1}^m \lambda_i x_i\right) \leq \sum_{i=1}^m \lambda_i f(x_i).$$
If $f$ is concave, the inequality is reversed.

**Proof**

The proof is the same induction argument used for finite convex combinations. For a convex function the case $m = 2$ is the definition. Group the first $m - 1$ terms into one convex combination and apply the two-point inequality, then use the induction hypothesis to bound the grouped term.

In probability notation, Jensen's inequality becomes especially memorable. If $X$ is a finite-valued random vector and $f$ is concave, then
$$f(\mathbb{E}[X]) \geq \mathbb{E}[f(X)].$$
For a concave utility function, utility of the mean is at least expected utility. This is one mathematical expression of aversion to mean-preserving risk.

<!-- page 26 -->

**Example 2.4 — Jensen and Consumption Risk**

Suppose consumption is either 1 or 4, each with probability 1/2, and utility is
$$u(c) = \sqrt{c}.$$
Expected consumption is
$$\mathbb{E}[c] = \frac{1}{2}(1) + \frac{1}{2}(4) = \frac{5}{2}.$$
Utility from receiving the mean consumption for sure is
$$u(\mathbb{E}[c]) = \sqrt{\frac{5}{2}} \approx 1.581,$$
whereas expected utility under the risky allocation is
$$\mathbb{E}[u(c)] = \frac{1}{2}(1) + \frac{1}{2}(2) = 1.5.$$
The gap is not an accident of these numbers. Concavity guarantees
$$u(\mathbb{E}[c]) \geq \mathbb{E}[u(c)]$$
for every finite lottery. Jensen's inequality is therefore the mathematical step behind the familiar statement that, holding mean consumption fixed, a risk-averse expected-utility consumer dislikes dispersion.

**2.3 First-Order Characterization of Concavity**

Concavity becomes particularly useful when the function is differentiable. Recall from Part II that the differential gives the tangent hyperplane
$$y \longmapsto f(x) + \nabla f(x)^T(y - x)$$
at the point $x$. A differentiable concave function always lies below this tangent hyperplane.

**Theorem 2.5 — First-Order Characterization of Concavity**

Let $C \subseteq \mathbb{R}^n$ be open and convex, and let
$$f : C \to \mathbb{R}$$
be differentiable. Then $f$ is concave if and only if
$$f(y) \leq f(x) + \nabla f(x)^T(y - x)$$

<!-- page 27 -->

for every $x, y \in C$.

**Proof**

Suppose first that $f$ is concave. Fix $x, y \in C$ and define
$$\phi(t) = f(x + t(y - x)), \quad 0 \leq t \leq 1.$$
The function $\phi$ is concave. For $t \in (0, 1]$,
$$\phi(t) \geq (1 - t)\phi(0) + t\phi(1),$$
so
$$\phi(1) - \phi(0) \leq \frac{\phi(t) - \phi(0)}{t}.$$
Letting $t \downarrow 0$ gives
$$f(y) - f(x) \leq \phi'(0) = \nabla f(x)^T(y - x).$$
Conversely, suppose the tangent inequality holds. Let
$$z = (1 - t)x + ty, \quad 0 < t < 1.$$
Apply the tangent inequality at $z$ once to $x$ and once to $y$:
$$f(x) \leq f(z) + \nabla f(z)^T(x - z),$$
$$f(y) \leq f(z) + \nabla f(z)^T(y - z).$$
Multiply the first inequality by $1 - t$, the second by $t$, and add. Since
$$(1 - t)(x - z) + t(y - z) = 0,$$
we obtain
$$(1 - t)f(x) + tf(y) \leq f(z),$$
which is concavity.

There is an important economic interpretation. At $x$, the gradient gives the vector of marginal values. Concavity says that evaluating a distant move $y - x$ using current marginal values gives an *upper bound* on the true gain:
$$f(y) - f(x) \leq \nabla f(x)^T(y - x).$$
Marginal values therefore decline sufficiently quickly that the linear approximation overstates the benefit of a finite move.
The first major optimization consequence follows immediately.

<!-- page 28 -->

Figure 5: A differentiable concave function lies below every tangent line. The tangent therefore supplies a global upper bound, not merely a local approximation.

**Corollary 2.6 — Stationarity Is Globally Sufficient under Concavity**

Let $C$ be open and convex, and let $f : C \to \mathbb{R}$ be differentiable and concave. If
$$\nabla f(x^*) = 0,$$
then $x^*$ is a global maximizer of $f$ on $C$.

**Proof**

For every $y \in C$, theorem 2.5 gives
$$f(y) \leq f(x^*) + \nabla f(x^*)^T(y - x^*) = f(x^*).$$
Thus concavity changes the status of the first-order condition: stationarity is no longer merely a candidate condition; it certifies global optimality.

**2.4 Monotonicity of the Gradient**

The first-order characterization has another useful consequence. Gradients of concave functions move in the opposite direction from the displacement of the choice.

**Proposition 2.7 — Monotonicity of the Gradient**

Let $C$ be open and convex and let $f : C \to \mathbb{R}$ be differentiable.
If $f$ is concave, then
$$(\nabla f(x) - \nabla f(y))^T(x - y) \leq 0 \quad \forall x, y \in C.$$
If $f$ is convex, the inequality is reversed.

<!-- page 29 -->

**Proof**

For concave $f$,
$$f(y) \leq f(x) + \nabla f(x)^T(y - x)$$
and
$$f(x) \leq f(y) + \nabla f(y)^T(x - y).$$
Adding and rearranging gives
$$(\nabla f(x) - \nabla f(y))^T(x - y) \leq 0.$$
In one dimension this simply says that the derivative of a concave function is weakly decreasing.

**2.5 Second-Order Characterization and the Hessian**

Part II showed that the Hessian is the matrix representing the quadratic term in the second-order Taylor expansion. Because the Hessian of a $C^2$ scalar function is symmetric, its eigenvalues describe curvature in orthogonal directions.
For a symmetric matrix $A$, recall the notation
$$A \geq 0$$
for positive semidefiniteness and
$$A \leq 0$$
for negative semidefiniteness.

**Definition 2.8 — Definiteness of a Symmetric Matrix**

Let $A = A^T \in \mathbb{R}^{n \times n}$.
(i) $A$ is **positive semidefinite**, written $A \geq 0$, if
$$h^T Ah \geq 0 \quad \forall h \in \mathbb{R}^n.$$
(ii) $A$ is **positive definite**, written $A > 0$, if
$$h^T Ah > 0 \quad \forall h \neq 0.$$
(iii) Negative semidefiniteness and negative definiteness are defined by reversing the inequalities.

By the spectral theorem,
$$A = Q\Lambda Q^T,$$

<!-- page 30 -->

where $Q$ is orthogonal and $\Lambda$ is diagonal. Therefore
$$h^T Ah = \sum_{i=1}^n \lambda_i z_i^2, \quad z = Q^T h.$$
Hence
$$A \geq 0 \iff \lambda_i \geq 0 \text{ for every } i,$$
and similarly for the other forms of definiteness.
This eigenvalue description is the most geometric one: each eigenvector gives a principal direction of curvature, and its eigenvalue gives the sign and magnitude of that curvature.

**Theorem 2.9 — Second-Order Characterization of Convexity and Concavity**

Let $C \subseteq \mathbb{R}^n$ be open and convex and let $f \in C^2(C)$. Then
$$f \text{ is convex} \iff H_f(x) \geq 0 \quad \forall x \in C,$$
and
$$f \text{ is concave} \iff H_f(x) \leq 0 \quad \forall x \in C.$$
Moreover, if
$$H_f(x) < 0 \quad \forall x \in C,$$
then $f$ is strictly concave.

**Proof**

Fix $x, y \in C$ and define the one-variable restriction
$$\phi(t) = f(x + t(y - x)), \quad 0 \leq t \leq 1.$$
By the chain rule,
$$\phi''(t) = (y - x)^T H_f(x + t(y - x))(y - x).$$
Thus $H_f \leq 0$ everywhere if and only if every restriction of $f$ to a line segment has nonpositive second derivative. By the one-variable second-derivative criterion, this is equivalent to concavity along every segment, which is exactly concavity of $f$. The convex case follows by applying the result to $-f$.
If the Hessian is negative definite everywhere, then for $x \neq y$ we have
$$\phi''(t) < 0$$
for all $t$, so each line restriction is strictly concave. Hence $f$ is strictly concave.

The converse to the final statement is false: a strictly concave $C^2$ function can have a singular Hessian

<!-- page 31 -->

at isolated points. For example,
$$f(x) = -x^4$$
is strictly concave on $\mathbb{R}$, but
$$f''(0) = 0.$$
Strict negative definiteness is therefore a convenient sufficient condition, not a necessary one.

**2.6 Practical Definiteness Checks**

Eigenvalues give the cleanest geometric description of definiteness, but in hand calculations it is often faster to work with determinants. Let
$$A = A^T \in \mathbb{R}^{n \times n},$$
and let
$$\Delta_k$$
denote the determinant of the leading $k \times k$ principal submatrix of $A$.

**Proposition 2.10 — Sylvester Criteria**

For a real symmetric matrix $A$:
(i) $A > 0$ if and only if
$$\Delta_k > 0 \quad k = 1, \dots, n.$$
(ii) $A < 0$ if and only if
$$(-1)^k \Delta_k > 0 \quad k = 1, \dots, n.$$
Thus the leading principal minors of a negative-definite matrix alternate in sign, starting with a negative first minor.

For a two-variable problem,
$$A = \begin{pmatrix} a & b \\ b & c \end{pmatrix},$$
so the test becomes especially simple:
$$A < 0 \iff a < 0 \text{ and } ac - b^2 > 0,$$
while
$$A > 0 \iff a > 0 \text{ and } ac - b^2 > 0.$$
The determinant alone is not enough: if $ac - b^2 < 0$, the quadratic form has both positive and negative directions and the matrix is indefinite.

<!-- page 32 -->

**Remark 2.11 — Definite versus Semidefinite Tests**

The leading-principal-minor test above characterizes *definiteness*. It should not be mechanically extended to semidefiniteness. For positive semidefiniteness one may check that *every* principal minor is nonnegative; for negative semidefiniteness, a principal minor of order $k$ must have sign $(-1)^k$ or be zero. In optimization this distinction matters because a semidefinite Hessian gives only a necessary condition at a local optimum and may leave the second-order test inconclusive.

These determinant checks will reappear below in a modified form. Equality constraints remove some directions from consideration, so the ordinary Hessian is replaced either by a *reduced Hessian* on the tangent space or, for hand calculations, by a *bordered Hessian*.

**2.7 Epigraphs and Hypographs**

There is a useful way to translate curvature of a function into convexity of a set.

**Definition 2.12 — Epigraph and Hypograph**

For $f : C \to \mathbb{R}$, define the **epigraph**
$$\text{epi}(f) = \{(x, r) \in C \times \mathbb{R} : r \geq f(x)\}$$
and the **hypograph**
$$\text{hypo}(f) = \{(x, r) \in C \times \mathbb{R} : r \leq f(x)\}.$$

**Proposition 2.13 — Geometry of Convex and Concave Functions**

Let $C$ be convex.
(i) $f$ is convex if and only if $\text{epi}(f)$ is convex.
(ii) $f$ is concave if and only if $\text{hypo}(f)$ is convex.

**Proof**

We prove the convex case. Suppose $f$ is convex and take
$$(x, r), (y, s) \in \text{epi}(f).$$
Then $r \geq f(x)$ and $s \geq f(y)$. For $t \in [0, 1]$,
$$(1 - t)r + ts \geq (1 - t)f(x) + tf(y) \geq f((1 - t)x + ty).$$

<!-- page 33 -->

Hence the convex combination lies in the epigraph.
Conversely, suppose the epigraph is convex. Since
$$(x, f(x)), (y, f(y)) \in \text{epi}(f),$$
their convex combination belongs to the epigraph. Therefore
$$(1 - t)f(x) + tf(y) \geq f((1 - t)x + ty),$$
which is convexity.

Figure 6: For a convex function, the region above the graph is convex. This converts a curvature property of a function into an ordinary convex-set statement.

This translation is conceptually important because it allows separation theorems for sets to generate first-order and duality results for functions.

**2.8 Quasiconcavity**

Concavity is often stronger than economic applications require. In consumer theory, for example, utility is ordinal: only the ranking of bundles matters. A strictly increasing transformation of a utility function represents the same preferences, even though it may destroy literal concavity.
The weaker notion that survives increasing transformations is quasiconcavity.

**Definition 2.14 — Quasiconcavity**

Let $C$ be convex. A function $f : C \to \mathbb{R}$ is **quasiconcave** if
$$f((1 - t)x + ty) \geq \min\{f(x), f(y)\}$$
for every $x, y \in C$ and every $t \in [0, 1]$.

<!-- page 34 -->

It is **strictly quasiconcave** if, whenever $x \neq y$ and $t \in (0, 1)$,
$$f((1 - t)x + ty) > \min\{f(x), f(y)\}.$$
Quasiconcavity does not compare the value at a mixture with the weighted average of $f(x)$ and $f(y)$. It only requires the mixture to be at least as good as the worse of the two endpoints.
The geometric characterization is especially important in economics.

**Theorem 2.15 — Upper Contour Set Characterization**

Let $C$ be convex. A function $f : C \to \mathbb{R}$ is quasiconcave if and only if every upper contour set
$$U_\alpha = \{x \in C : f(x) \geq \alpha\}$$
is convex.

**Proof**

Suppose $f$ is quasiconcave. If $x, y \in U_\alpha$, then
$$f((1 - t)x + ty) \geq \min\{f(x), f(y)\} \geq \alpha,$$
so $(1 - t)x + ty \in U_\alpha$.
Conversely, fix $x, y \in C$ and set
$$\alpha = \min\{f(x), f(y)\}.$$
Then $x, y \in U_\alpha$. If every upper contour set is convex, then
$$(1 - t)x + ty \in U_\alpha,$$
so
$$f((1 - t)x + ty) \geq \alpha = \min\{f(x), f(y)\}.$$

**Corollary 2.16 — Concavity Implies Quasiconcavity**

Every concave function on a convex set is quasiconcave.

**Proof**

Concavity gives
$$f((1 - t)x + ty) \geq (1 - t)f(x) + tf(y).$$

<!-- page 35 -->

A weighted average lies between its two endpoints, so
$$(1 - t)f(x) + tf(y) \geq \min\{f(x), f(y)\}.$$
The reverse implication fails. A function can have convex upper contour sets without satisfying the cardinal inequality required by concavity.

Figure 7: Quasiconcavity is a statement about upper contour sets. If two bundles are at least as good as $\bar{u}$, every mixture on the segment between them is also at least as good.

**Proposition 2.17 — Increasing Transformations Preserve Quasiconcavity**

Suppose $f : C \to \mathbb{R}$ is quasiconcave and
$$\phi : f(C) \to \mathbb{R}$$
is strictly increasing. Then $\phi \circ f$ is quasiconcave.

**Proof**

Since $\phi$ is increasing,
$$\phi(f((1 - t)x + ty)) \geq \phi(\min\{f(x), f(y)\}) = \min\{\phi(f(x)), \phi(f(y))\}.$$
This is why quasiconcavity, rather than concavity of a particular utility index, is the natural curvature condition for convex preferences.

**Example 2.18 — Cobb-Douglas Preferences**

Consider
$$u(x_1, x_2) = x_1^\alpha x_2^{1-\alpha}, \quad 0 < \alpha < 1,$$

<!-- page 36 -->

on $\mathbb{R}_{++}^2$. The strictly increasing transformation log gives
$$\log u(x_1, x_2) = \alpha \log x_1 + (1 - \alpha) \log x_2,$$
which is strictly concave. Therefore $u$ is strictly quasiconcave.
The point is not that the logarithm is somehow the "true" utility function. It is that a convenient increasing transformation reveals the convexity of the underlying preference ordering.

**2.9 Strict Curvature and Uniqueness**

Concavity is about global shape. Strict concavity adds enough curvature to rule out two distinct optimal points.

**Proposition 2.19 — Uniqueness under Strict Concavity**

Let $C$ be convex and let $f : C \to \mathbb{R}$ be strictly concave. If a maximizer exists, it is unique.

**Proof**

Suppose $x \neq y$ are both maximizers and let their common objective value be $M$. For any $t \in (0, 1)$, convexity of $C$ gives
$$z = (1 - t)x + ty \in C.$$
Strict concavity implies
$$f(z) > (1 - t)f(x) + tf(y) = M,$$
contradicting maximality of $M$.

Exactly the same argument shows that strict quasiconcavity is enough for uniqueness. The assumptions doing the work should be kept separate: compactness and continuity are existence conditions; strict curvature is a uniqueness condition. A model may have one without the other.

<!-- page 37 -->

# 3 Optimization in Euclidean Space

We now place the preceding geometry inside an optimization problem. The most important habit in this section is to separate three questions that are often blurred together:

(1) Does a solution exist?
(2) If it exists, how can it be characterized?
(3) Under what conditions is a candidate globally optimal and unique?

The first question is topological. The second is differential. The third is geometric. Much of optimization theory consists of knowing which tool answers which question.

## 3.1 The Optimization Problem

A generic maximization problem takes the form
$$\max_{x \in X} f(x),$$
where
$$X \subseteq \mathbb{R}^n$$
is the feasible set and
$$f: X \to \mathbb{R}$$
is the objective function.

### Definition 3.1 — Maximum, Maximizer, and Argmax
A point $x^* \in X$ is a **global maximizer** of $f$ on $X$ if
$$f(x^*) \geq f(x) \quad \forall x \in X.$$
The set of all maximizers is
$$\arg \max_{x \in X} f(x) = \{x \in X : f(x) \geq f(y) \text{ for every } y \in X\}.$$
If this set is nonempty, the number
$$\max_{x \in X} f(x)$$
is called the maximum value.

It is important to distinguish
$$\sup_{x \in X} f(x)$$

<!-- page 38 -->

from
$$\max_{x \in X} f(x).$$
The supremum may exist without being attained.

### Example 3.2 — A Supremum without a Maximizer
Consider
$$\max_{0 < x < 1} x.$$
The set of attainable objective values is $(0, 1)$, so
$$\sup_{0 < x < 1} x = 1.$$
But 1 is not feasible. Hence
$$\arg \max_{0 < x < 1} x = \emptyset.$$
The problem has a finite supremum but no maximizer.

This is why it is dangerous to begin an optimization problem by differentiating. There may be nothing to characterize.

## 3.2 Existence: Compactness and Continuity

The fundamental existence result was already proved in Part II as the extreme-value theorem. Here we reinterpret it as an optimization theorem.

### Theorem 3.3 — Weierstrass Existence Theorem
Let $X \subseteq \mathbb{R}^n$ be nonempty and compact, and let
$$f: X \to \mathbb{R}$$
be continuous. Then
$$\arg \max_{x \in X} f(x) \neq \emptyset,$$
and
$$\arg \min_{x \in X} f(x) \neq \emptyset.$$

The theorem combines two types of assumptions. Compactness keeps feasible sequences from escaping to infinity or converging to excluded boundary points. Continuity keeps objective values from jumping at a limit. Together, they allow a maximizing sequence to converge to a feasible point that attains the supremum.

<!-- page 39 -->

### Proof
We prove the maximum statement. Let
$$M = \sup_{x \in X} f(x).$$
Choose a maximizing sequence $\{x_k\} \subseteq X$ such that
$$f(x_k) \to M.$$
Since $X$ is compact, some subsequence satisfies
$$x_{k_j} \to x^*$$
for a point $x^* \in X$. By continuity,
$$f(x_{k_j}) \to f(x^*).$$
But the left-hand side converges to $M$, so
$$f(x^*) = M.$$
Hence $x^*$ is a maximizer.

The proof pattern reappears throughout economic theory: choose nearly optimal points, use compactness to obtain a convergent subsequence, and use continuity to pass the objective value to the limit.

## 3.3 Existence on Unbounded Sets: Coercivity

Economic choice sets are often unbounded. A firm can in principle choose arbitrarily large capital, or a statistical parameter may range over all of $\mathbb{R}^n$. We can still obtain existence if the objective becomes sufficiently unattractive far away.

### Definition 3.4 — Coercivity
A continuous function $f: \mathbb{R}^n \to \mathbb{R}$ is **coercive for minimization** if
$$\|x\| \to \infty \implies f(x) \to +\infty.$$
For maximization, the analogous coercivity condition is
$$\|x\| \to \infty \implies f(x) \to -\infty.$$

<!-- page 40 -->

### Proposition 3.5 — Coercivity Gives Existence
If $f: \mathbb{R}^n \to \mathbb{R}$ is continuous and
$$\|x\| \to \infty \implies f(x) \to -\infty,$$
then $f$ attains a global maximum on $\mathbb{R}^n$.

### Proof
Choose any $x_0 \in \mathbb{R}^n$. By the assumed limit, there exists $R > 0$ such that
$$\|x\| > R \implies f(x) < f(x_0).$$
Therefore no global maximizer can lie outside the closed ball
$$\bar{B}_R(0).$$
The problem can be restricted to this compact set. By theorem 3.3, a maximizer exists there, and hence on all of $\mathbb{R}^n$.

The idea is *compactification*: even when the primitive choice set is unbounded, the objective may allow us to prove that all relevant choices lie in some compact subset.

### Example 3.6 — A Firm Problem on an Unbounded Choice Set
Suppose a firm chooses output $q \geq 0$ and earns
$$\pi(q) = aq - \frac{b}{2}q^2, \quad a, b > 0.$$
The feasible set $[0, \infty)$ is not compact, but
$$\pi(q) \to -\infty \quad \text{as } q \to \infty.$$
Hence the maximization problem still has a solution. In fact,
$$\pi'(q) = a - bq,$$
so the unique maximizer is
$$q^* = \frac{a}{b}.$$
The quadratic cost term is doing two jobs: economically, it makes marginal cost rise; mathematically, it prevents a maximizing sequence from escaping to infinity.

<!-- page 41 -->

## 3.4 Local and Global Optima

Calculus is inherently local. It examines what happens under small changes in $x$. Optimization problems, however, usually ask for a global comparison against every feasible alternative.

### Definition 3.7 — Local Maximizer
A point $x^* \in X$ is a **local maximizer** of $f$ on $X$ if there exists $r > 0$ such that
$$f(x^*) \geq f(x)$$
for every
$$x \in X \cap B_r(x^*).$$
It is a **strict local maximizer** if the inequality is strict for every $x \neq x^*$ in that neighborhood.

Every global maximizer is a local maximizer, but the converse is false for a general function. Concavity is what closes the gap.

### Theorem 3.8 — Local Maxima Are Global for Concave Problems
Let $X \subseteq \mathbb{R}^n$ be convex and let $f: X \to \mathbb{R}$ be concave. Then every local maximizer of $f$ on $X$ is a global maximizer.

### Proof
Let $x^*$ be a local maximizer. Suppose, toward a contradiction, that there exists $y \in X$ with
$$f(y) > f(x^*).$$
Because $X$ is convex, for every $t \in (0, 1)$,
$$x_t = (1 - t)x^* + ty \in X.$$
Moreover, $x_t \to x^*$ as $t \downarrow 0$. Concavity gives
$$f(x_t) \geq (1 - t)f(x^*) + tf(y) > f(x^*).$$
For sufficiently small $t$, this contradicts local optimality of $x^*$.

The proof captures the economic force of convexity and concavity. If a distant feasible point is better, then moving even a tiny fraction of the way toward it must already be an improvement. A local optimum therefore cannot hide from a superior global alternative.

<!-- page 42 -->

## 3.5 Interior First-Order Conditions

Suppose now that $X$ contains an open neighborhood of a candidate point $x^*$. At an interior optimum we can move a little in every direction. The derivative must therefore assign zero first-order gain to every direction.

### Theorem 3.9 — First-Order Necessary Condition
Let $U \subseteq \mathbb{R}^n$ be open and let
$$f: U \to \mathbb{R}$$
be differentiable. If $x^* \in U$ is a local maximizer or local minimizer, then
$$\nabla f(x^*) = 0.$$

### Proof
Fix any direction $v \in \mathbb{R}^n$ and define
$$\phi(t) = f(x^* + tv)$$
for $t$ sufficiently close to zero. Since $x^*$ is an interior local optimum, $t = 0$ is a local optimum of $\phi$. The one-variable first-order condition gives
$$0 = \phi'(0) = \nabla f(x^*)^T v.$$
Because this holds for every $v$,
$$\nabla f(x^*) = 0.$$

The condition is necessary, not sufficient.

### Example 3.10 — A Stationary Point That Is Not An Optimum
Let
$$f(x, y) = x^2 - y^2.$$
Then
$$\nabla f(0, 0) = 0.$$
But along the $x$-axis,
$$f(t, 0) = t^2 > 0 = f(0, 0)$$
for $t \neq 0$, while along the $y$-axis,
$$f(0, t) = -t^2 < 0 = f(0, 0).$$

<!-- page 43 -->

Thus $(0, 0)$ is neither a local maximum nor a local minimum. It is a saddle point.

## 3.6 Second-Order Conditions

At a stationary point, the first-order term in Taylor's theorem disappears. The leading local change is then the quadratic form generated by the Hessian:
$$f(x^* + h) - f(x^*) = \frac{1}{2} h^T H_f(x^*) h + o(\|h\|^2).$$
This immediately gives the standard second-order tests.

### Theorem 3.11 — Second-Order Necessary and Sufficient Conditions
Let $f \in C^2(U)$ and let $x^* \in U$.
(i) If $x^*$ is a local maximizer, then
$$\nabla f(x^*) = 0 \quad \text{and} \quad H_f(x^*) \leq 0.$$
(ii) If
$$\nabla f(x^*) = 0 \quad \text{and} \quad H_f(x^*) < 0,$$
then $x^*$ is a strict local maximizer.

### Proof
The first-order condition has already been proved. If $x^*$ is a local maximum, then for every direction $v$, the one-variable restriction
$$\phi(t) = f(x^* + tv)$$
has a local maximum at $t = 0$. Hence
$$\phi''(0) = v^T H_f(x^*) v \leq 0.$$
Since this holds for every $v$, the Hessian is negative semidefinite.
For sufficiency, suppose $H_f(x^*) < 0$. Since the Hessian is symmetric, its largest eigenvalue is strictly negative. Hence there exists $c > 0$ such that
$$h^T H_f(x^*) h \leq -c\|h\|^2$$

<!-- page 44 -->

for every $h$. Taylor's theorem gives
$$f(x^* + h) - f(x^*) \leq -\frac{c}{2}\|h\|^2 + o(\|h\|^2).$$
For sufficiently small nonzero $h$, the remainder is dominated by the negative quadratic term, so the difference is strictly negative.

If the Hessian is merely negative semidefinite, the second-order test can be inconclusive. Higher-order terms may determine the local behavior.

## 3.7 Optimization over a Convex Set

The condition $\nabla f(x^*) = 0$ depends on being able to move in every direction. At a boundary point this is false. The correct first-order condition compares the gradient only with feasible directions.

Suppose $X$ is convex and $x^* \in X$. Every point $x \in X$ generates the feasible segment
$$x^* + t(x - x^*), \quad 0 \leq t \leq 1.$$
If $x^*$ maximizes $f$, the directional derivative along this segment cannot be positive.

### Theorem 3.12 — First-Order Condition on a Convex Feasible Set
Let $X \subseteq \mathbb{R}^n$ be convex and let $f$ be differentiable on an open set containing $X$. If $x^*$ is a local maximizer of $f$ on $X$, then
$$\nabla f(x^*)^T (x - x^*) \leq 0 \quad \forall x \in X.$$
If, in addition, $f$ is concave on $X$, then this condition is also sufficient for $x^*$ to be a global maximizer.

### Proof
For necessity, fix $x \in X$ and define
$$\phi(t) = f(x^* + t(x - x^*)), \quad 0 \leq t \leq 1.$$
For sufficiently small $t \geq 0$, local optimality implies
$$\phi(t) \leq \phi(0).$$
Hence the right derivative at zero satisfies
$$\phi'(0^+) = \nabla f(x^*)^T (x - x^*) \leq 0.$$

<!-- page 45 -->

For sufficiency, suppose $f$ is concave. Then
$$f(x) \leq f(x^*) + \nabla f(x^*)^T (x - x^*) \leq f(x^*)$$
for every $x \in X$.

This inequality is often called a **variational inequality**. It is the natural boundary version of the stationary condition. If $x^*$ is interior, then both $v$ and $-v$ are feasible local directions, forcing the inner product to be zero in every direction and hence recovering
$$\nabla f(x^*) = 0.$$

### Example 3.13 — A Boundary Optimum
Consider
$$\max_{x \geq 0} -(x + 1)^2.$$
The unconstrained stationary point is $x = -1$, which is infeasible. The constrained maximizer is
$$x^* = 0.$$
Here
$$f'(0) = -2 \neq 0.$$
This does not violate optimality because feasible movements satisfy $x - x^* \geq 0$, and
$$f'(0)(x - x^*) = -2x \leq 0.$$
The gradient points outside the feasible set.

### Example 3.14 — A Portfolio Problem as Convex Optimization
Let $w \in \mathbb{R}^n$ be portfolio weights, $\mu$ expected returns, and $\Sigma > 0$ a covariance matrix. For risk-aversion parameter $\gamma > 0$, consider
$$\max_{w \geq 0, \mathbf{1}^T w = 1} \left\{ \mu^T w - \frac{\gamma}{2} w^T \Sigma w \right\}.$$
The simplex is compact and convex, while the objective is strictly concave because $\Sigma > 0$. Hence a unique global optimizer exists.
If the optimum is interior to the simplex, the gradient must be orthogonal to every zero-sum reallocation direction. If some weights are zero, the same first-order idea becomes one-sided: moving mass into an excluded asset cannot raise the objective. The normal-cone and KKT

<!-- page 46 -->

formulations below are precisely the systematic way to encode those boundary inequalities.

## 3.8 Normal Cones

The variational inequality can be expressed geometrically. At a boundary point, the gradient of a maximized objective must lie in the outward normal cone of the feasible set.

### Definition 3.15 — Normal Cone
Let $X \subseteq \mathbb{R}^n$ be convex and let $x^* \in X$. The **normal cone** to $X$ at $x^*$ is
$$N_X(x^*) = \{v \in \mathbb{R}^n : v^T (x - x^*) \leq 0 \text{ for every } x \in X\}.$$

Thus theorem 3.12 can be written as
$$\nabla f(x^*) \in N_X(x^*).$$

For an interior point, the normal cone is $\{0\}$. At a smooth boundary point, it is the ray generated by an outward normal vector. KKT multipliers will provide a concrete representation of this normal vector when $X$ is described by constraints.

[Image: A circle with a point $x^*$ on the boundary. An arrow labeled $N_X(x^*)$ points outward from $x^*$. Label: "smooth boundary: one outward ray". To the right, a corner of a square with $x^*$ at the vertex. Two arrows point outward from $x^*$ into a shaded region. Label: "corner: a cone of outward normals"]

Figure 8: The normal cone records all outward first-order directions. It collapses to a single ray at a smooth boundary point but widens at a corner.

<!-- page 47 -->

# 4 Equality-Constrained Optimization

We now study optimization problems in which feasible choices must satisfy smooth equalities. The familiar Lagrange multiplier formula will emerge from the geometry of tangent directions rather than being introduced as an algebraic trick.

Consider
$$\max_{x \in \mathbb{R}^n} f(x) \quad \text{subject to} \quad g(x) = 0,$$
where
$$g: \mathbb{R}^n \to \mathbb{R}^m.$$
The feasible set is the level set
$$X = \{x : g(x) = 0\}.$$
If the gradients of the constraints are linearly independent, this set behaves locally like a smooth surface of dimension $n - m$.

## 4.1 Tangent Directions to the Feasible Set

Suppose a differentiable curve
$$\gamma: (-\varepsilon, \varepsilon) \to \mathbb{R}^n$$
lies entirely in the feasible set and passes through $x^*$ at $t = 0$:
$$g(\gamma(t)) = 0, \quad \gamma(0) = x^*.$$
Differentiating gives
$$Dg(x^*) \gamma'(0) = 0.$$
Thus every feasible velocity vector belongs to the kernel of the Jacobian.

### Definition 4.1 — Linearized Tangent Space
Let $g: \mathbb{R}^n \to \mathbb{R}^m$ be differentiable and let $x^*$ satisfy $g(x^*) = 0$. The **linearized tangent space** is
$$T(x^*) = \ker Dg(x^*) = \{v \in \mathbb{R}^n : Dg(x^*)v = 0\}.$$

When
$$\text{rank } Dg(x^*) = m,$$
the implicit function theorem shows that the feasible set is locally a smooth $(n - m)$-dimensional surface and that this linearized space is its actual tangent space.

<!-- page 48 -->

## 4.2 The Geometry of Lagrange Multipliers

At a constrained optimum, the objective cannot increase to first order along any feasible tangent direction. Hence
$$\nabla f(x^*)^T v = 0 \quad \forall v \in T(x^*).$$
In other words,
$$\nabla f(x^*) \in T(x^*)^\perp.$$
Linear algebra now does the rest. Since
$$T(x^*) = \ker Dg(x^*),$$
we have
$$(\ker Dg(x^*))^\perp = \text{range}(Dg(x^*)^T).$$
Therefore the gradient of the objective must be a linear combination of the gradients of the constraints.

[Image: A coordinate system with $x_1$ and $x_2$ axes. An ellipse labeled $g(x) = 0$. A point $x^*$ on the ellipse. A line tangent to the ellipse at $x^*$ labeled "objective level set". An arrow labeled $\nabla f(x^*) \parallel \nabla g(x^*)$ pointing from $x^*$ labeled "common normal direction"]

### Theorem 4.2 — Lagrange Multiplier Theorem
Let
$$f: \mathbb{R}^n \to \mathbb{R}, \quad g: \mathbb{R}^n \to \mathbb{R}^m$$
be continuously differentiable near $x^*$. Suppose $x^*$ is a local maximizer or minimizer of $f$ subject to
$$g(x) = 0,$$
and suppose
$$\text{rank } Dg(x^*) = m.$$
Then there exists $\lambda^* \in \mathbb{R}^m$ such that
$$\nabla f(x^*) + Dg(x^*)^T \lambda^* = 0.$$

<!-- page 49 -->

**Proof**

Under the rank condition, the implicit function theorem identifies the tangent space to the feasible set at $x^*$ as
$$T(x^*) = \ker Dg(x^*).$$
If $v \in T(x^*)$, there exists a feasible differentiable curve through $x^*$ with velocity $v$. Since $x^*$ is a local optimum, the derivative of the objective along that curve is zero:
$$\nabla f(x^*)^T v = 0.$$
Thus $\nabla f(x^*)$ is orthogonal to $\ker Dg(x^*)$. By the fundamental theorem of linear algebra,
$$(\ker Dg(x^*))^\perp = \text{range}(Dg(x^*)^T).$$
Hence there exists $\eta \in \mathbb{R}^m$ with
$$\nabla f(x^*) = Dg(x^*)^T \eta.$$
Setting $\lambda^* = -\eta$ gives the stated equation.

The theorem explains the multiplier formula. It is not an independent computational device. It is a coordinate representation of the geometric statement
$$\text{objective gradient} \perp \text{feasible tangent directions.}$$

### 4.3 The Lagrangian

The multiplier equation is usually packaged in a scalar function.

**Definition 4.3 — Lagrangian for Equality Constraints**

For
$$\max_x f(x) \quad \text{subject to} \quad g(x) = 0,$$
define the **Lagrangian**
$$\mathcal{L}(x, \lambda) = f(x) + \lambda^T g(x).$$

The first-order conditions become
$$\nabla_x \mathcal{L}(x^*, \lambda^*) = 0, \quad g(x^*) = 0.$$

Thus we solve $n + m$ equations for $n + m$ unknowns $(x, \lambda)$.

The multiplier theorem tells us that these equations are necessary at a regular local optimum. It does not say that every solution is optimal.

<!-- page 50 -->

### 4.4 Why the Rank Condition Matters

The rank condition is a constraint qualification. It ensures that the gradients of the constraints correctly describe the local geometry of the feasible set.

**Example 4.4 — Failure of the Multiplier Rule under Degeneracy**

Consider
$$\max_x x \quad \text{subject to} \quad x^2 = 0.$$
The feasible set contains only $x^* = 0$, so $x^*$ is trivially both the constrained maximum and minimum.
But the constraint gradient is
$$g'(0) = 0.$$
The multiplier equation would require
$$1 + \lambda g'(0) = 1 = 0,$$
which is impossible.
The optimization problem is not ill-defined. What fails is the linearization of the constraint: the derivative of $x^2$ at zero is zero and therefore does not reveal that the feasible set has collapsed to a single point.

This example is worth remembering whenever a system of first-order conditions appears not to admit multipliers. The problem may lie in the constraint representation rather than in the optimum.

### 4.5 Second-Order Conditions on the Tangent Space

For unconstrained optimization, the Hessian is tested in every direction. Under equality constraints, only directions tangent to the feasible set are relevant to first order.

Let
$$\mathcal{L}(x, \lambda) = f(x) + \lambda^T g(x).$$
At a regular constrained optimum $(x^*, \lambda^*)$, the correct quadratic form is
$$v^T H_{xx} \mathcal{L}(x^*, \lambda^*) v$$
restricted to
$$v \in T(x^*) = \ker Dg(x^*).$$

<!-- page 51 -->

**Theorem 4.5 — Second-Order Conditions with Equality Constraints**

Suppose $f$ and $g$ are $C^2$, $x^*$ is feasible, the rank condition holds, and $\lambda^*$ satisfies the first-order conditions.
(i) If $x^*$ is a local maximizer, then
$$v^T H_{xx} \mathcal{L}(x^*, \lambda^*) v \leq 0$$
for every
$$v \in \ker Dg(x^*).$$
(ii) If
$$v^T H_{xx} \mathcal{L}(x^*, \lambda^*) v < 0$$
for every nonzero
$$v \in \ker Dg(x^*),$$
then $x^*$ is a strict local maximizer subject to $g(x) = 0$.

The theorem says that curvature matters only along directions in which one can move while remaining feasible to first order. Negative definiteness on all of $\mathbb{R}^n$ is stronger than necessary.

### 4.6 The Reduced Hessian

The tangent-space condition can be turned into an ordinary matrix-definiteness test. Write
$$G = Dg(x^*) \in \mathbb{R}^{m \times n}, \quad H = H_{xx} \mathcal{L}(x^*, \lambda^*) \in \mathbb{R}^{n \times n}.$$
Under the rank condition,
$$\text{rank } G = m,$$
so the tangent space has dimension $n - m$. Choose a matrix
$$Z \in \mathbb{R}^{n \times (n-m)}$$
whose columns form a basis for
$$\ker G.$$
Every tangent direction can then be written uniquely as
$$v = Zq, \quad q \in \mathbb{R}^{n-m}.$$
Substituting this representation into the quadratic form gives
$$v^T H v = q^T (Z^T H Z) q.$$

<!-- page 52 -->

**Definition 4.6 — Reduced Hessian**

The matrix
$$H_R = Z^T H_{xx} \mathcal{L}(x^*, \lambda^*) Z$$
is called the **reduced Hessian** of the Lagrangian relative to the equality constraints.

**Corollary 4.7 — Second-Order Conditions via the Reduced Hessian**

Under the assumptions of theorem 4.5:
(i) a constrained local maximum requires
$$H_R \leq 0;$$
(ii) if
$$H_R < 0,$$
then $x^*$ is a strict constrained local maximum;
(iii) for a constrained minimum, reverse the signs.

The result does not depend on the particular basis $Z$. If another tangent-space basis is $\tilde{Z} = ZR$ with $R$ nonsingular, then
$$\tilde{Z}^T H \tilde{Z} = R^T (Z^T H Z) R.$$
Congruence by a nonsingular matrix preserves definiteness. The reduced Hessian is therefore a coordinate representation of an intrinsic object: curvature restricted to the feasible tangent space.

### 4.7 Bordered Hessians

For small problems economists often avoid constructing a tangent-space basis explicitly. Instead, the constraint Jacobian and the Hessian of the Lagrangian are assembled into one saddle-point matrix.

**Definition 4.8 — Bordered Hessian**

For $m$ equality constraints in $n$ choice variables, define
$$\mathcal{B} = \begin{pmatrix} 0_{m \times m} & G \\ G^T & H \end{pmatrix}, \quad G = Dg(x^*), \quad H = H_{xx} \mathcal{L}(x^*, \lambda^*).$$
The matrix $\mathcal{B}$ is the **bordered Hessian**.

The zero block records that the Lagrangian is linear in the multipliers. The off-diagonal blocks record the linearized constraints, and the lower-right block records curvature. Thus the bordered Hessian

<!-- page 53 -->

is not a different second-order theory. It packages the same objects that appear in the tangent-space test.

**One constraint and two choice variables**

The simplest case reveals exactly where the familiar determinant sign comes from. Let
$$g(x_1, x_2) = 0$$
be one regular constraint and write, at the candidate point,
$$g_i = \frac{\partial g}{\partial x_i}, \quad L_{ij} = \frac{\partial^2 \mathcal{L}}{\partial x_i \partial x_j}.$$
Then
$$\mathcal{B} = \begin{pmatrix} 0 & g_1 & g_2 \\ g_1 & L_{11} & L_{12} \\ g_2 & L_{12} & L_{22} \end{pmatrix}.$$
A tangent vector is
$$v = \begin{pmatrix} g_2 \\ -g_1 \end{pmatrix},$$
because $\nabla g^T v = 0$. Direct expansion gives
$$\det \mathcal{B} = -v^T H v.$$
Consequently,
$$\det \mathcal{B} > 0$$
means negative curvature along the one-dimensional feasible tangent and therefore gives the strict second-order condition for a constrained maximum. Similarly,
$$\det \mathcal{B} < 0$$
gives the strict second-order condition for a constrained minimum.
This sign reversal is much easier to remember once one sees the identity: the bordered determinant is, up to sign, the second derivative in the only feasible direction.

**The general leading-minor check**

There is also a determinant rule for several equality constraints. It is useful for hand calculations, although the reduced-Hessian formulation is usually conceptually cleaner.

First reorder the choice variables, if necessary, so that the first $m$ columns of $G$ form a nonsingular $m \times m$ matrix. Let
$$\mathcal{B}_r$$

<!-- page 54 -->

denote the leading $r \times r$ principal submatrix of the bordered Hessian in this ordering. The relevant minors are the last $n - m$ leading principal minors,
$$r = 2m + 1, \dots, m + n.$$

**Proposition 4.9 — Bordered-Hessian Sign Check**

Suppose LICQ holds and the first-order Lagrange conditions are satisfied.
For a **strict constrained maximum**, a sufficient second-order check is
$$(-1)^{r-m} \det \mathcal{B}_r > 0, \quad r = 2m + 1, \dots, m + n.$$
Equivalently, the relevant minors alternate in sign, beginning with sign $(-1)^{m+1}$ at order $2m + 1$.
For a **strict constrained minimum**, a sufficient check is
$$(-1)^m \det \mathcal{B}_r > 0, \quad r = 2m + 1, \dots, m + n.$$
Thus all the relevant minors have the same sign $(-1)^m$.

For a maximum, the determinant of the full bordered Hessian therefore has sign
$$\text{sgn}(\det \mathcal{B}) = (-1)^n,$$
provided all the required minors satisfy the strict test. The full determinant alone is not enough when $n - m > 1$: the intermediate minors carry information about the remaining feasible directions.

**Remark 4.10 — Which Second-Order Test Should You Use?**

The hierarchy is useful to remember.
If the tangent space is easy to describe, test
$$v^T H v$$
directly. If there are many variables but a convenient null-space basis, form the reduced Hessian $Z^T H Z$. If the problem is small and written explicitly in coordinates, the bordered-Hessian determinant rules can be the fastest hand calculation. These are three algebraic representations of the same curvature restriction, not three competing criteria.

<!-- page 55 -->

**Example 4.11 — Cobb–Douglas Utility: A Full Bordered-Hessian Check**

Consider the interior consumer problem
$$\max_{x_1, x_2 > 0} \alpha \log x_1 + (1 - \alpha) \log x_2$$
subject to
$$w - p_1 x_1 - p_2 x_2 = 0, \quad 0 < \alpha < 1.$$
The Lagrangian is
$$\mathcal{L} = \alpha \log x_1 + (1 - \alpha) \log x_2 + \lambda(w - p_1 x_1 - p_2 x_2).$$
The first-order conditions yield
$$x_1^* = \frac{\alpha w}{p_1}, \quad x_2^* = \frac{(1 - \alpha)w}{p_2}.$$
At any interior candidate, the bordered Hessian is
$$\mathcal{B} = \begin{pmatrix} 0 & -p_1 & -p_2 \\ -p_1 & -\frac{\alpha}{x_1^2} & 0 \\ -p_2 & 0 & -\frac{1 - \alpha}{x_2^2} \end{pmatrix}.$$
Because there is one constraint and two choice variables, only the full determinant is needed.
Direct calculation gives
$$\det \mathcal{B} = p_1^2 \frac{1 - \alpha}{x_2^2} + p_2^2 \frac{\alpha}{x_1^2} > 0.$$
Hence the candidate satisfies the strict second-order condition for a constrained maximum.
The same conclusion is immediate from the tangent-space formulation. A tangent vector to the budget line is
$$v = \begin{pmatrix} p_2 \\ -p_1 \end{pmatrix},$$
and therefore
$$v^T H v = -\frac{\alpha p_2^2}{x_1^2} - \frac{(1 - \alpha)p_1^2}{x_2^2} < 0.$$
The two calculations are exactly equivalent:
$$\det \mathcal{B} = -v^T H v > 0.$$

<!-- page 56 -->

### 4.8 Shadow-Value Interpretation of Multipliers

Multipliers acquire economic meaning when a parameter relaxes a constraint. Consider
$$V(a) = \max_x f(x) \quad \text{subject to} \quad g(x) = a.$$
Write the constraint as
$$a - g(x) = 0$$
and the Lagrangian as
$$\mathcal{L}(x, \lambda; a) = f(x) + \lambda^T (a - g(x)).$$
Under the regularity conditions needed for the envelope theorem, which we will prove later,
$$\frac{\partial V}{\partial a_i} = \lambda_i^*.$$
Thus the multiplier measures the marginal value of relaxing the corresponding constraint.

**Example 4.12 — Utility Maximization and the Marginal Utility of Wealth**

Consider
$$V(p, w) = \max_{x \in \mathbb{R}_+^L} u(x) \quad \text{subject to} \quad w - p^T x = 0,$$
and suppose the optimum is interior. The Lagrangian is
$$\mathcal{L}(x, \lambda) = u(x) + \lambda(w - p^T x).$$
The first-order condition is
$$\nabla u(x^*) = \lambda^* p.$$
For each good $i$,
$$u_i(x^*) = \lambda^* p_i.$$
The multiplier converts units of wealth into units of utility. Later the envelope theorem will make this precise:
$$\frac{\partial V}{\partial w} = \lambda^*.$$

**Example 4.13 — Cost Minimization**

A firm chooses capital and labor to minimize the cost of producing $\bar{y}$:
$$\min_{K, L} rK + wL \quad \text{subject to} \quad F(K, L) = \bar{y}.$$

<!-- page 57 -->

Use the Lagrangian
$$\mathcal{L}(K, L, \lambda) = rK + wL + \lambda(\bar{y} - F(K, L)).$$
The first-order conditions are
$$r = \lambda F_K, \quad w = \lambda F_L.$$
Therefore
$$\frac{F_K}{F_L} = \frac{r}{w}.$$
At an interior cost-minimizing input bundle, the marginal rate of technical substitution equals the factor-price ratio.

### 5 Inequality-Constrained Optimization

Equality constraints restrict the feasible set to a smooth surface. Inequality constraints introduce a new feature: some restrictions bind at the optimum and others do not. The Karush–Kuhn–Tucker conditions keep track of this distinction through nonnegative multipliers and complementary slackness.

We adopt a maximization convention throughout this section. Consider
$$\max_{x \in \mathbb{R}^n} f(x)$$
subject to
$$g_i(x) \geq 0, \quad i = 1, \dots, m,$$
and
$$h_j(x) = 0, \quad j = 1, \dots, \ell.$$
With this sign convention, the multipliers on inequality constraints will be nonnegative and the Lagrangian will contain $+\lambda_i g_i(x)$.

### 5.1 Active and Inactive Constraints

**Definition 5.1 — Active Constraint**

A feasible inequality constraint
$$g_i(x) \geq 0$$
is **active** or **binding** at $x^*$ if
$$g_i(x^*) = 0.$$
It is **inactive** or **slack** if
$$g_i(x^*) > 0.$$

<!-- page 58 -->

An inactive constraint does not restrict sufficiently small movements around $x^*$. An active constraint does. This simple observation is the source of complementary slackness.

**Example 5.2 — Nonnegativity at a Corner**

Suppose a consumer chooses $x_i \geq 0$. Written in our convention, the constraint is
$$g_i(x) = x_i \geq 0.$$
If $x_i^* > 0$, nonnegativity is inactive. If $x_i^* = 0$, the constraint is active and prevents movement in the negative $x_i$ direction.

### 5.2 The KKT Conditions

Define the Lagrangian
$$\mathcal{L}(x, \lambda, \mu) = f(x) + \sum_{i=1}^m \lambda_i g_i(x) + \sum_{j=1}^\ell \mu_j h_j(x),$$
where
$$\lambda_i \geq 0.$$

**Theorem 5.3 — Karush–Kuhn–Tucker Necessary Conditions**

Suppose $x^*$ is a local maximizer of the constrained problem above and suppose LICQ holds at $x^*$. Then there exist multipliers
$$\lambda^* \in \mathbb{R}_+^m, \quad \mu^* \in \mathbb{R}^\ell$$
such that:
(i) **Stationarity:**
$$\nabla f(x^*) + \sum_{i=1}^m \lambda_i^* \nabla g_i(x^*) + \sum_{j=1}^\ell \mu_j^* \nabla h_j(x^*) = 0.$$
(ii) **Primal feasibility:**
$$g_i(x^*) \geq 0, \quad h_j(x^*) = 0.$$
(iii) **Dual feasibility:**
$$\lambda_i^* \geq 0.$$
(iv) **Complementary slackness:**
$$\lambda_i^* g_i(x^*) = 0 \quad \text{for } i = 1, \dots, m.$$

Geometrically, stationarity says that the objective gradient lies in the outward normal cone generated by the active restrictions. The multipliers are simply the coefficients in that normal-vector

<!-- page 59 -->

decomposition.
The sign restriction on $\lambda_i$ follows from the orientation of an inequality. For $g_i(x) \geq 0$, the vector $-\nabla g_i(x^*)$ points outward from the feasible side. Stationarity can therefore be written as
$$\nabla f(x^*) = -\sum_i \lambda_i^* \nabla g_i(x^*) - \sum_j \mu_j^* \nabla h_j(x^*).$$
For an active inequality, only a nonnegative multiple of the outward normal is available.

[Figure 9: KKT stationarity at a corner. The objective gradient lies in the outward normal cone and is represented by a nonnegative combination of active-constraint normals.]

### 5.3 Complementary Slackness

The condition
$$\lambda_i^* g_i(x^*) = 0$$
contains an important either–or statement.
If the constraint is slack,
$$g_i(x^*) > 0,$$
then necessarily
$$\lambda_i^* = 0.$$
A small relaxation of an already slack constraint has no first-order value.
If
$$\lambda_i^* > 0,$$
then necessarily
$$g_i(x^*) = 0.$$
A constraint can carry a positive shadow value only if it binds.

<!-- page 60 -->

The converse is not true: a constraint may bind and still have a zero multiplier. It can be geometrically active without being marginally valuable.

**Example 5.4 — A Borrowing Constraint and an Euler Inequality**

A two-period household chooses saving $s$ according to
$$\max_{s \geq 0} \{u(w - s) + \beta v((1 + r)s + y_2)\},$$
where $s \geq 0$ rules out borrowing. Write
$$g(s) = s \geq 0$$
and attach multiplier $\lambda \geq 0$. Stationarity is
$$-u'(w - s^*) + \beta(1 + r)v'((1 + r)s^* + y_2) + \lambda^* = 0.$$
If the household saves strictly positive amounts, then $\lambda^* = 0$ and we recover the usual Euler equation
$$u'(c_1) = \beta(1 + r)v'(c_2).$$
If instead $s^* = 0$, then $\lambda^* \geq 0$ and stationarity implies
$$u'(c_1) \geq \beta(1 + r)v'(c_2).$$
The consumer would like to move resources from period 2 toward period 1, but the borrowing constraint prevents it. Complementary slackness is therefore exactly what turns an Euler equation into an Euler inequality at a constrained household optimum.

**Example 5.5 — A Binding Constraint with Zero Multiplier**

Consider
$$\max_{x \geq 0} -x^2.$$
The unique optimum is $x^* = 0$, so the nonnegativity constraint binds. Write
$$\mathcal{L}(x, \lambda) = -x^2 + \lambda x.$$
Stationarity gives
$$-2x^* + \lambda^* = 0,$$
so
$$\lambda^* = 0.$$
The constraint is binding, but relaxing it slightly to allow small negative $x$ does not improve

<!-- page 61 -->

the objective to first order because the unconstrained optimum is already at zero.

## 5.4 Constraint Qualifications

The KKT conditions are not a purely formal consequence of writing down a Lagrangian. They require the active constraints to describe the local feasible geometry correctly. Conditions that guarantee this are called constraint qualifications.

A common local condition is linear independence of active constraint gradients.

### Definition 5.6 — LICQ
The **linear independence constraint qualification** holds at a feasible point $x^*$ if the vectors
$$\{\nabla h_j(x^*)\}_{j=1}^\ell$$
together with
$$\{\nabla g_i(x^*) : g_i(x^*) = 0\}$$
are linearly independent.

LICQ is easy to state and useful for smooth nonlinear programs, but convex optimization has a particularly convenient alternative based on strict feasibility.

### Definition 5.7 — Slater Condition
Consider a problem with concave inequality functions $g_i$ and affine equality constraints. **Slater's condition** holds if there exists a point $\bar{x}$ such that
$$h_j(\bar{x}) = 0 \quad \forall j$$
and
$$g_i(\bar{x}) > 0 \quad \forall i.$$
Such a point is called **strictly feasible**.

Slater's condition is global rather than local. Geometrically, it says that the feasible set contains a point lying strictly inside all inequality constraints, relative to the affine equality restrictions.

### Example 5.8 — Why Strict Feasibility Matters
Compare the ordinary constraint
$$x \geq 0$$

<!-- page 62 -->

with the degenerate representation
$$-x^2 \geq 0.$$
The second inequality has the feasible set $\{0\}$, so there is no point at which the inequality is strict. At its only feasible point,
$$\left.\frac{d}{dx}(-x^2)\right|_{x=0} = 0,$$
so the linearized constraint contains no information about which movements are actually feasible. Slater's condition excludes precisely this kind of degeneracy in a convex program.

## 5.5 Second-Order KKT Conditions and Critical Directions

The first-order KKT conditions identify candidates. In a nonconcave nonlinear problem, we may still need a local second-order test. The subtlety is the same as with equality constraints: curvature matters only along directions that remain relevant after the first-order restrictions have been imposed.

Let
$$A(x^*) = \{i : g_i(x^*) = 0\}$$
be the active inequality constraints, and split them according to their KKT multipliers:
$$A_+ = \{i \in A(x^*) : \lambda_i^* > 0\}, \quad A_0 = \{i \in A(x^*) : \lambda_i^* = 0\}.$$

For our maximization convention $g_i(x) \geq 0$, a first-order feasible direction must point weakly into the feasible side of every active inequality.

### Definition 5.9 — Critical Cone
At a KKT point $(x^*, \lambda^*, \mu^*)$, the **critical cone** is
$$C(x^*, \lambda^*) = \left\{ d : \begin{aligned} \nabla h_j(x^*)^T d &= 0 && \forall j, \\ \nabla g_i(x^*)^T d &= 0 && \forall i \in A_+, \\ \nabla g_i(x^*)^T d &\geq 0 && \forall i \in A_0 \end{aligned} \right\}.$$

Why do constraints with positive multipliers enter as equalities? KKT stationarity gives
$$\nabla f(x^*)^T d = -\sum_{i \in A(x^*)} \lambda_i^* \nabla g_i(x^*)^T d.$$

A feasible direction with
$$\nabla g_i(x^*)^T d > 0$$
for an active constraint carrying $\lambda_i^* > 0$ already lowers the objective to first order. Second-order curvature matters only when that first-order loss disappears. Those are precisely the critical directions.

<!-- page 63 -->

### Theorem 5.10 — Second-Order KKT Test
Assume the problem is $C^2$, LICQ holds at a KKT point, and write
$$H_L = H_{xx} \mathcal{L}(x^*, \lambda^*, \mu^*).$$
If $x^*$ is a local maximizer, then
$$d^T H_L d \leq 0 \quad \forall d \in C(x^*, \lambda^*).$$
Conversely, if
$$d^T H_L d < 0 \quad \forall d \in C(x^*, \lambda^*) \setminus \{0\},$$
then $x^*$ satisfies the strong second-order sufficient condition for a strict local maximum.

If every active inequality is strictly complementary, so that every active multiplier is positive, the critical cone becomes a linear tangent space: all active constraints enter with equality. The theorem then reduces to the equality-constrained tangent-space test. If the program is globally concave, however, no local second-order check is needed for sufficiency: KKT itself already certifies the global maximum. That is the important special case to which we now turn.

## 5.6 KKT Sufficiency for Concave Problems

The necessary KKT theorem applies much more broadly than convex optimization. But its strongest payoff comes when the objective and feasible set have the right curvature. Then the same conditions become sufficient for global optimality.

Consider
$$\max_x f(x)$$
subject to
$$g_i(x) \geq 0, \quad h_j(x) = 0,$$
where $f$ and each $g_i$ are concave and each $h_j$ is affine.
Because a superlevel set of a concave function is convex,
$$\{x : g_i(x) \geq 0\}$$
is convex. Intersecting these sets with affine equality sets therefore produces a convex feasible set.

### Theorem 5.11 — KKT Sufficiency for Concave Maximization
Suppose $f$ and the inequality functions $g_i$ are concave and the equality functions $h_j$ are affine. If a feasible point $x^*$ and multipliers $(\lambda^*, \mu^*)$ satisfy the KKT conditions, then $x^*$ is a global

<!-- page 64 -->

maximizer.

### Proof
Fix KKT multipliers $(\lambda^*, \mu^*)$ and define
$$L(x) = f(x) + \sum_i \lambda_i^* g_i(x) + \sum_j \mu_j^* h_j(x).$$
Because $f$ and the $g_i$ are concave and the $h_j$ are affine, $L$ is concave in $x$. KKT stationarity gives
$$\nabla L(x^*) = 0,$$
so concavity implies
$$L(x) \leq L(x^*) \quad \forall x.$$
If $x$ is feasible, then $g_i(x) \geq 0, h_j(x) = 0$, and $\lambda_i^* \geq 0$, so
$$L(x) \geq f(x).$$
At $x^*$, complementary slackness and equality feasibility give
$$L(x^*) = f(x^*).$$
Therefore every feasible $x$ satisfies
$$f(x) \leq L(x) \leq L(x^*) = f(x^*),$$
which proves global optimality.

The proof gives a useful way to read KKT in a concave program: the optimal multipliers construct a concave Lagrangian whose unconstrained maximizer is the constrained primal optimum.

## 5.7 KKT as a Normal-Cone Condition

Suppose for simplicity that there are no equality constraints and that the active constraint gradients generate the normal cone of the feasible set. Stationarity says
$$\nabla f(x^*) = -\sum_{i \in A(x^*)} \lambda_i^* \nabla g_i(x^*), \quad \lambda_i^* \geq 0,$$
where $A(x^*)$ is the set of active constraints.
Thus the multiplier equations are a coordinate representation of the single geometric condition
$$\nabla f(x^*) \in N_X(x^*).$$

<!-- page 65 -->

Each positive multiplier identifies an active restriction that contributes to the supporting normal at the optimum.

## 5.8 Worked Example: Consumer Choice with Corners

Consider
$$\max_{x_1, x_2 \geq 0} u(x_1, x_2)$$
subject to
$$w - p_1 x_1 - p_2 x_2 \geq 0.$$
Write the Lagrangian as
$$\mathcal{L} = u(x_1, x_2) + \lambda(w - p_1 x_1 - p_2 x_2) + \eta_1 x_1 + \eta_2 x_2,$$
with
$$\lambda, \eta_1, \eta_2 \geq 0.$$
The KKT conditions are
$$u_1(x) - \lambda p_1 + \eta_1 = 0,$$
$$u_2(x) - \lambda p_2 + \eta_2 = 0,$$
$$w - p_1 x_1 - p_2 x_2 \geq 0, \quad x_1, x_2 \geq 0,$$
$$\lambda, \eta_1, \eta_2 \geq 0,$$
and
$$\lambda(w - p_1 x_1 - p_2 x_2) = 0,$$
$$\eta_1 x_1 = 0, \quad \eta_2 x_2 = 0.$$
If preferences are locally nonsatiated, the budget binds, so
$$w - p_1 x_1 - p_2 x_2 = 0.$$
If both goods are consumed positively, then
$$\eta_1 = \eta_2 = 0,$$
and we recover the familiar interior condition
$$\frac{u_1}{u_2} = \frac{p_1}{p_2}.$$
If, say, $x_2 = 0$, then $\eta_2$ may be positive and the interior equality becomes an inequality. From stationarity,
$$u_2 = \lambda p_2 - \eta_2 \leq \lambda p_2,$$

<!-- page 66 -->

so
$$\frac{u_2}{p_2} \leq \lambda.$$
The excluded good delivers no more marginal utility per dollar than the goods actually purchased. This is the economic content of complementary slackness: interior choices satisfy marginal equalities; corner choices satisfy the corresponding one-sided inequalities.

## 5.9 Worked Example: Resource Allocation

A planner allocates a resource $R$ across $n$ activities:
$$\max_{x_1, \dots, x_n \geq 0} \sum_{i=1}^n u_i(x_i)$$
subject to
$$R - \sum_{i=1}^n x_i \geq 0,$$
where each $u_i$ is increasing and concave.
The Lagrangian is
$$\mathcal{L} = \sum_{i=1}^n u_i(x_i) + \lambda \left( R - \sum_{i=1}^n x_i \right) + \sum_{i=1}^n \eta_i x_i.$$
For every activity used positively,
$$\eta_i = 0$$
and stationarity gives
$$u_i'(x_i) = \lambda.$$
Thus all active uses have the same marginal benefit. If an activity receives zero resources, then
$$u_i'(0) \leq \lambda.$$
The common multiplier $\lambda$ is the marginal value of the aggregate resource.

### Remark 5.12 — Sign Conventions
Two conventions are common:
$$\max f(x) \quad \text{s.t.} \quad g_i(x) \geq 0$$
with
$$\mathcal{L} = f + \sum_i \lambda_i g_i, \quad \lambda_i \geq 0,$$

<!-- page 67 -->

or
$$\min f(x) \quad \text{s.t.} \quad g_i(x) \leq 0$$
with the same nonnegative-multiplier convention.
Both are correct. Errors arise only when the sign of the inequality, the sign in the Lagrangian, and the sign restriction on the multiplier are mixed inconsistently.

# 6 Convex Optimization and Duality

The KKT conditions already show that multipliers help characterize constrained optima. Duality reveals a deeper interpretation. A multiplier vector generates a new optimization problem whose value provides a bound on what the original problem can achieve. The dual problem searches for the tightest such bound.

This section is deliberately finite-dimensional and focused on the ideas economists use most often: weak duality, strong duality, shadow values, and the relation between KKT conditions and saddle points.

We continue to use the maximization convention
$$\max_x f(x)$$
subject to
$$g_i(x) \geq 0, \quad i = 1, \dots, m,$$
and
$$Ax = b,$$
where $f$ and the $g_i$ are concave.

## 6.1 The Lagrangian as a Relaxed Objective

For multipliers
$$\lambda \in \mathbb{R}_+^m, \quad \mu \in \mathbb{R}^p,$$
define
$$\mathcal{L}(x, \lambda, \mu) = f(x) + \sum_{i=1}^m \lambda_i g_i(x) + \mu^T(Ax - b).$$
If $x$ is feasible, then
$$g_i(x) \geq 0$$
and
$$Ax - b = 0.$$

<!-- page 68 -->

Therefore
$$\mathcal{L}(x, \lambda, \mu) \geq f(x)$$
for every feasible $x$ and every $\lambda \geq 0$.
This inequality is the starting point of duality. The Lagrangian is an objective that rewards satisfaction of the inequality constraints at rates $\lambda_i$. For any fixed multipliers, maximizing the Lagrangian over all $x$ gives an upper bound on what any feasible $x$ can achieve.

## 6.2 The Dual Function and Dual Problem

### Definition 6.1 — Dual Function
The **dual function** is
$$q(\lambda, \mu) = \sup_{x \in \mathbb{R}^n} \mathcal{L}(x, \lambda, \mu), \quad \lambda \geq 0.$$

Because the supremum is taken over all $x$, feasible or not,
$$q(\lambda, \mu) \geq \mathcal{L}(x, \lambda, \mu) \geq f(x)$$
for every feasible $x$.
If the primal optimal value is
$$p^* = \sup \{f(x) : g_i(x) \geq 0, Ax = b\},$$
then
$$q(\lambda, \mu) \geq p^*$$
for every dual-feasible pair $(\lambda, \mu)$.
Since every dual choice produces an upper bound, it is natural to choose the smallest one.

### Definition 6.2 — Lagrange Dual Problem
The **dual problem** is
$$\inf_{\lambda \geq 0, \mu} q(\lambda, \mu).$$
Its optimal value is denoted by $d^*$.

<!-- page 69 -->

## 6.3 Weak Duality

### Theorem 6.3 — Weak Duality
For every primal maximization problem and its Lagrange dual defined above,
$$p^* \leq d^*.$$
More strongly, for every primal-feasible $x$ and every dual-feasible $(\lambda, \mu)$,
$$f(x) \leq q(\lambda, \mu).$$

### Proof
If $x$ is primal feasible, then
$$\mathcal{L}(x, \lambda, \mu) \geq f(x).$$
By definition of the dual function,
$$q(\lambda, \mu) = \sup_z \mathcal{L}(z, \lambda, \mu) \geq \mathcal{L}(x, \lambda, \mu).$$
Thus
$$f(x) \leq q(\lambda, \mu).$$
Taking the supremum over primal-feasible $x$ gives
$$p^* \leq q(\lambda, \mu),$$
and then taking the infimum over dual-feasible multipliers gives
$$p^* \leq d^*.$$

The difference
$$d^* - p^*$$
is the **duality gap**. Weak duality says it can never be negative.

### Remark 6.4 — Dual Variables as Certificates
Suppose we have found a feasible $x$ with value $f(x)$ and multipliers $(\lambda, \mu)$ with dual value $q(\lambda, \mu)$. Then
$$f(x) \leq p^* \leq d^* \leq q(\lambda, \mu).$$
Hence
$$0 \leq p^* - f(x) \leq q(\lambda, \mu) - f(x).$$

<!-- page 70 -->

The primal–dual gap therefore gives a certificate of how far the feasible point can be from optimality.

This is one reason duality is useful computationally as well as theoretically. A dual solution can certify that a primal candidate is nearly optimal without knowing the true optimum in advance.

## 6.4 Strong Duality

Weak duality always holds. Strong duality is the stronger statement that the best dual bound is exact.

### Definition 6.5 — Strong Duality
Strong duality holds if
$$p^* = d^*.$$
Equivalently, the duality gap is zero.

Strong duality does not hold for every nonlinear problem. Convexity together with a constraint qualification is what makes it robust.

### Theorem 6.6 — Strong Duality under Slater's Condition
Consider the concave maximization problem
$$\max_x f(x)$$
subject to
$$g_i(x) \geq 0, \quad Ax = b,$$
where $f$ and all $g_i$ are concave. Suppose the problem is feasible and Slater's condition holds: there exists $\bar{x}$ satisfying
$$A\bar{x} = b$$
and
$$g_i(\bar{x}) > 0 \quad \forall i.$$
Assume the primal optimal value is finite. Then
$$p^* = d^*.$$
Moreover, the dual optimum is attained.

A full proof can be built from a separating-hyperplane theorem applied to an appropriate convex set of attainable objective and constraint values. The geometry is worth seeing even if we do not

<!-- page 71 -->

reproduce every technical detail.
Define the set
$$C = \left\{ (u, t) \in \mathbb{R}^m \times \mathbb{R} : \begin{aligned} \exists x \text{ with } Ax = b, \\ g_i(x) \geq u_i \quad \forall i, \\ f(x) \geq t \end{aligned} \right\}.$$
Concavity of $f$ and the $g_i$ implies that $C$ is convex. The primal value $p^*$ marks the highest point of $C$ above $u = 0$. A separating hyperplane at that boundary produces coefficients that become the optimal multipliers. Slater's condition rules out a degenerate separator and ensures the coefficient on the objective coordinate is nonzero, allowing the hyperplane equation to be normalized into the Lagrange dual.

Thus strong duality is another manifestation of convex separation.

## 6.5 Complementary Slackness from Zero Duality Gap

Suppose primal and dual optima are attained and strong duality holds. Let $x^*$ be primal optimal and $(\lambda^*, \mu^*)$ dual optimal. Then
$$f(x^*) = q(\lambda^*, \mu^*).$$
But weak duality was obtained through the chain
$$f(x^*) \leq \mathcal{L}(x^*, \lambda^*, \mu^*) \leq q(\lambda^*, \mu^*).$$
If the first and last terms are equal, every inequality in between must be an equality. Therefore
$$\sum_i \lambda_i^* g_i(x^*) = 0.$$
Since every term in the sum is nonnegative,
$$\lambda_i^* g_i(x^*) = 0 \quad \forall i.$$
Complementary slackness is therefore not an isolated algebraic condition. Under strong duality it is forced by the equality of primal and dual values.

## 6.6 Saddle Points of the Lagrangian

The primal problem maximizes with respect to $x$. The dual problem minimizes with respect to multipliers. At an optimum, these two directions meet in a saddle point.

<!-- page 72 -->

### Definition 6.7 — Lagrangian Saddle Point
A triple $(x^*, \lambda^*, \mu^*)$ with $\lambda^* \geq 0$ is a **saddle point** of $\mathcal{L}$ if
$$\mathcal{L}(x, \lambda^*, \mu^*) \leq \mathcal{L}(x^*, \lambda^*, \mu^*) \leq \mathcal{L}(x^*, \lambda, \mu)$$
for every $x$ and every $\lambda \geq 0, \mu \in \mathbb{R}^p$.

The left inequality says that, given the optimal multipliers, $x^*$ maximizes the Lagrangian. The right inequality says that, at the optimal primal point, the chosen multipliers minimize the Lagrangian.

### Theorem 6.8 — KKT, Strong Duality, and Saddle Points
For a differentiable concave program satisfying Slater's condition, the following are equivalent for a primal-feasible $x^*$ and dual-feasible $(\lambda^*, \mu^*)$:
(i) $x^*$ and $(\lambda^*, \mu^*)$ are primal and dual optimal;
(ii) the KKT conditions hold;
(iii) $(x^*, \lambda^*, \mu^*)$ is a saddle point of the Lagrangian.

The equivalence is useful because it lets us move between three languages for the same solution: primal–dual optimality, first-order KKT conditions, and a saddle point of the Lagrangian.

## 6.7 A Simple Duality Example

Consider
$$\max_{x \geq 0} \left\{ ax - \frac{1}{2}x^2 \right\}$$
subject to
$$R - x \geq 0,$$
where $a, R > 0$. The Lagrangian is
$$\mathcal{L}(x, \lambda) = ax - \frac{1}{2}x^2 + \lambda(R - x), \quad \lambda \geq 0.$$
For fixed $\lambda$, the Lagrangian is maximized over the remaining domain $x \geq 0$ at
$$x(\lambda) = \max\{a - \lambda, 0\}.$$
Hence the dual function is piecewise:
$$q(\lambda) = \begin{cases} \frac{1}{2}(a - \lambda)^2 + \lambda R, & 0 \leq \lambda \leq a, \\ \lambda R, & \lambda \geq a. \end{cases}$$

<!-- page 73 -->

The dual problem minimizes this upper bound over $\lambda \geq 0$.
If $R \geq a$, the resource constraint is slack at the unconstrained optimum,
$$x^* = a, \quad \lambda^* = 0.$$
If $R < a$, the resource constraint binds and
$$x^* = R, \quad \lambda^* = a - R > 0.$$
In either case,
$$q(\lambda^*) = f(x^*) = p^*,$$
so the best dual upper bound exactly equals the primal value.

[Figure 10: Weak duality makes every dual value an upper bound on the primal value. Strong duality means that the best such bound touches $p^*$ at $\lambda^*$.]

The multiplier is exactly the marginal gain from relaxing the resource limit. The figure also makes the logic of duality visible: weak duality is the inequality $q(\lambda) \geq p^*$; strong duality is the contact point at the minimizing multiplier.

**Example 6.9 — Duality as Decentralized Resource Allocation**
Consider a planner who allocates a scarce resource across $n$ uses:
$$\max_{x_i \geq 0} \sum_{i=1}^n u_i(x_i) \quad \text{s.t.} \quad \sum_{i=1}^n x_i \leq R,$$
with each $u_i$ increasing and concave. Using the constraint $R - \sum_i x_i \geq 0$, the Lagrangian is
$$\mathcal{L}(x, \lambda) = \sum_{i=1}^n u_i(x_i) + \lambda \left( R - \sum_{i=1}^n x_i \right).$$

<!-- page 74 -->

For a fixed $\lambda \geq 0$, maximization separates across uses:
$$q(\lambda) = \lambda R + \sum_{i=1}^n \sup_{x_i \geq 0} \{ u_i(x_i) - \lambda x_i \}.$$
The single dual variable $\lambda$ therefore acts like a common scarcity price. Each activity chooses its demand independently at that price, and the dual problem adjusts $\lambda$ until the aggregate resource constraint is priced as tightly as possible. Under Slater's condition, the minimizing dual price is the planner's shadow value and there is no duality gap.

# 7 Parameterized Optimization and Value Functions
Economic optimization problems depend on parameters. A consumer's problem depends on prices and wealth. A firm's problem depends on productivity and factor prices. A planner's problem depends on resource endowments and policy instruments. Once a problem is parameterized, two new objects appear naturally: the value function and the set of optimal choices.
Let
$$\theta \in \Theta \subseteq \mathbb{R}^k$$
index the environment and consider
$$V(\theta) = \sup_{x \in X(\theta)} f(x, \theta).$$

**Definition 7.1 — Value Function and Solution Correspondence**
For the parameterized problem above, the **value function** is
$$V(\theta) = \sup_{x \in X(\theta)} f(x, \theta).$$
The **solution correspondence** is
$$S(\theta) = \arg \max_{x \in X(\theta)} f(x, \theta).$$
If the optimizer is unique, we write
$$S(\theta) = \{ x^*(\theta) \}$$
and identify the solution correspondence with the policy function $x^*(\theta)$.

A parameterized problem generates several objects, and they answer different questions. Existence

<!-- page 75 -->

concerns whether the argmax is nonempty; stability concerns continuity of the value and solution set; comparative statics concerns how an optimizer moves; the envelope theorem concerns how the optimized value moves. In particular, the derivative of the value and the derivative of the policy are not the same object.

## 7.1 Smooth Comparative Statics from First-Order Conditions
Begin with an unconstrained interior problem
$$V(\theta) = \max_{x \in \mathbb{R}^n} f(x, \theta),$$
and suppose the optimizer $x^*(\theta)$ is locally unique and interior. The first-order condition is
$$\nabla_x f(x^*(\theta), \theta) = 0.$$
This is a system of $n$ equations in the $n$ unknown components of $x^*$. The implicit function theorem tells us when the solution varies smoothly with $\theta$.

**Theorem 7.2 — Differential Comparative Statics**
Suppose $f$ is $C^2$ and, at $(x^*, \theta^*)$,
$$\nabla_x f(x^*, \theta^*) = 0.$$
If
$$H_{xx} f(x^*, \theta^*)$$
is nonsingular, then there is a neighborhood of $\theta^*$ on which the first-order condition determines a unique differentiable branch of stationary points $x(\theta)$ through $x^*$. Along that branch,
$$D_\theta x(\theta) = -[H_{xx} f(x(\theta), \theta)]^{-1} D_{x\theta} f(x(\theta), \theta).$$
If the Hessian is negative definite at $(x^*, \theta^*)$, then after shrinking the neighborhood if necessary, this branch consists of strict local maximizers.

**Proof**
Define
$$F(x, \theta) = \nabla_x f(x, \theta).$$
The first-order condition is
$$F(x(\theta), \theta) = 0.$$
The derivative with respect to $x$ is
$$D_x F(x^*, \theta) = H_{xx} f(x^*, \theta),$$

<!-- page 76 -->

which is nonsingular by assumption. The implicit function theorem therefore yields a local differentiable stationary branch $x(\theta)$ through $(x^*, \theta^*)$. Differentiating the identity
$$F(x(\theta), \theta) = 0$$
gives
$$D_x F D_\theta x + D_\theta F = 0.$$
Solving for $D_\theta x$ gives the formula. Negative definiteness is an open condition on symmetric matrices, so if the Hessian is negative definite at the base point it remains negative definite nearby. The second-order sufficient condition then shows that the stationary branch consists of strict local maximizers.

## 7.2 Constrained Comparative Statics and the KKT Matrix
The same implicit-function logic works with equality constraints, but now the unknowns include both the policy and the multipliers. Consider
$$\max_x f(x, \theta) \quad \text{subject to} \quad g(x, \theta) = 0,$$
where $g$ has $m$ components. Let
$$\mathcal{L}(x, \lambda; \theta) = f(x, \theta) + \lambda^T g(x, \theta).$$
At a regular stationary point, stack the first-order system in the order
$$\begin{pmatrix} g(x, \theta) \\ \nabla_x \mathcal{L}(x, \lambda; \theta) \end{pmatrix} = 0.$$
Its Jacobian with respect to $(\lambda, x)$ is
$$\mathcal{K} = \begin{pmatrix} 0 & G \\ G^T & H \end{pmatrix}, \quad G = D_x g(x^*, \theta), \quad H = H_{xx} \mathcal{L}(x^*, \lambda^*; \theta).$$
This is exactly the bordered Hessian from equality-constrained second-order analysis.

**Proposition 7.3 — Why the Bordered Hessian Is Nonsingular under the Strong SOC**
Suppose $G$ has full row rank and
$$v^T H v < 0 \quad \forall v \in \ker G \setminus \{0\}.$$

<!-- page 77 -->

Then the bordered KKT matrix
$$\mathcal{K} = \begin{pmatrix} 0 & G \\ G^T & H \end{pmatrix}$$
is nonsingular.

**Proof**
Suppose
$$\mathcal{K} \begin{pmatrix} a \\ v \end{pmatrix} = 0.$$
The first block equation gives
$$Gv = 0.$$
The second gives
$$G^T a + Hv = 0.$$
Premultiplying by $v^T$ and using $Gv = 0$ yields
$$v^T H v = 0.$$
Negative definiteness on $\ker G$ therefore implies $v = 0$. Then $G^T a = 0$. Because $G$ has full row rank, $G^T$ has trivial null space, so $a = 0$. Hence the kernel of $\mathcal{K}$ is trivial.

This result is useful because it connects the strong second-order condition directly to differential comparative statics. The implicit function theorem gives a locally unique differentiable branch $(\lambda^*(\theta), x^*(\theta))$, and differentiation of the KKT system gives
$$\begin{pmatrix} 0 & G \\ G^T & H \end{pmatrix} \begin{pmatrix} D_\theta \lambda^* \\ D_\theta x^* \end{pmatrix} = - \begin{pmatrix} g_\theta \\ \mathcal{L}_{x\theta} \end{pmatrix}.$$
Thus the bordered Hessian has a second role beyond the determinant test: it is the linear system that maps primitive parameter changes into changes in optimal choices and shadow values.

**Remark 7.4 — Three Roles of the Same Matrix**
For equality-constrained problems, the matrix
$$\begin{pmatrix} 0 & G \\ G^T & H \end{pmatrix}$$
appears in three places:
(i) its minors provide the classical bordered-Hessian second-order checks;

<!-- page 78 -->

(ii) its nonsingularity is implied by LICQ plus the strong reduced-Hessian condition;
(iii) its inverse delivers local comparative statics for both the optimizer and the multipliers.
This is why the bordered Hessian is worth learning even when the tangent-space formulation is conceptually primary.

## 7.3 The Scalar Comparative-Statics Formula
In one choice dimension and one parameter dimension,
$$\frac{dx^*}{d\theta} = -\frac{f_{x\theta}}{f_{xx}}.$$
At a local maximum satisfying the nonsingularity condition above, the one-dimensional second-order necessary condition implies
$$f_{xx} < 0.$$
Hence, along such a regular maximizing branch, the sign of the comparative-static response is the sign of the cross-partial:
$$f_{x\theta} > 0 \implies \frac{dx^*}{d\theta} > 0.$$
This formula is useful, but it is local and differentiable. Later courses develop monotone comparative statics that can obtain directional conclusions without assuming smoothness or uniqueness.

**Example 7.5 — Monopoly: Policy Response versus Value Response**
A monopolist faces inverse demand
$$p(q) = a - bq, \quad a, b > 0,$$
and constant marginal cost $c < a$. Profit is
$$\pi(q; a) = (a - c)q - bq^2.$$
The first-order condition gives
$$q^*(a) = \frac{a - c}{2b}, \quad \frac{dq^*}{da} = \frac{1}{2b} > 0.$$
This is the comparative-static response of behavior. Optimized profit is
$$\Pi(a) = \pi(q^*(a); a) = \frac{(a - c)^2}{4b}.$$

<!-- page 79 -->

Differentiating gives
$$\Pi'(a) = \frac{a - c}{2b} = q^*(a).$$
The second equality is the envelope theorem in action: the direct effect of a larger demand intercept on profit is $\partial \pi / \partial a = q$, evaluated at the optimum. The induced movement of $q^*$ does not enter the first derivative of optimized profit.

## 7.4 The Envelope Theorem: Unconstrained Case
Suppose
$$V(\theta) = f(x^*(\theta), \theta).$$
Differentiating mechanically gives
$$\frac{dV}{d\theta} = \nabla_x f(x^*, \theta)^T \frac{dx^*}{d\theta} + f_\theta(x^*, \theta).$$
At an interior optimum,
$$\nabla_x f(x^*, \theta) = 0.$$
The entire indirect effect through the change in the optimizer disappears to first order.

**Theorem 7.6 — Envelope Theorem: Smooth Interior Case**
Suppose $f$ is continuously differentiable and $x^*(\theta)$ is a differentiable interior optimizer of
$$V(\theta) = \max_x f(x, \theta).$$
Then
$$\frac{dV}{d\theta} = f_\theta(x^*(\theta), \theta).$$
For a vector parameter,
$$\nabla_\theta V(\theta) = \nabla_\theta f(x^*(\theta), \theta).$$

**Proof**
Apply the chain rule:
$$\frac{dV}{d\theta} = \nabla_x f(x^*, \theta)^T x^{*'}(\theta) + f_\theta(x^*, \theta).$$
The first-order condition sets the first term equal to zero.

There is also a useful geometric way to read the theorem. For each fixed choice $x$, define a curve in the parameter
$$\phi_x(\theta) = f(x, \theta).$$

<!-- page 80 -->

Then
$$V(\theta) = \sup_x \phi_x(\theta)$$
is the upper envelope of this family. At a parameter where a unique smooth optimizer $x^*(\theta)$ is active, the value function touches the curve $\phi_{x^*(\theta)}$ and inherits its slope with respect to $\theta$.

[Figure 11: The value function is an upper envelope of objective curves indexed by the choice. At a smooth unique optimum, the envelope and the active curve have the same parameter slope—the geometric content of the envelope theorem.]

The economic intuition is important. Reoptimization changes the choice by $dx^*$. But at an interior optimum, the objective is locally flat with respect to the choice variable. The first-order welfare effect of that induced choice movement is therefore zero. Only the direct effect of the parameter remains.

**Remark 7.7 — Policy Derivative versus Value Derivative**
The formulas
$$\frac{dx^*}{d\theta} = -\frac{f_{x\theta}}{f_{xx}}$$
and
$$\frac{dV}{d\theta} = f_\theta$$
answer different questions.
The first asks how behavior changes. The second asks how optimized welfare changes. Knowing the envelope derivative does not tell us the behavioral response, and knowing the behavioral response is usually unnecessary for the first derivative of the value.

<!-- page 81 -->

## 7.5 A Second-Order Envelope Formula
The first-order envelope theorem removes the behavioral response from $V'(\theta)$. At second order, the response of the optimizer reappears in a structured way. This is useful in welfare comparisons and in the Le Chatelier–Samuelson principle.
For simplicity, let $\theta$ be scalar and consider a smooth interior strict local maximum with nonsingular Hessian
$$H = H_{xx} f(x^*(\theta), \theta) < 0.$$
From the envelope theorem,
$$V'(\theta) = f_\theta(x^*(\theta), \theta).$$
Differentiating once more gives
$$V''(\theta) = f_{\theta\theta} + f_{\theta x} x^{*'}(\theta).$$
Using
$$x^{*'}(\theta) = -H^{-1} f_{x\theta},$$
we obtain
$$V''(\theta) = f_{\theta\theta} - f_{\theta x} H^{-1} f_{x\theta}.$$

**Proposition 7.8 — Second-Order Envelope Formula**
Under the smooth interior assumptions above,
$$V''(\theta) = f_{\theta\theta} - f_{\theta x} (H_{xx} f)^{-1} f_{x\theta},$$
with all derivatives evaluated at $(x^*(\theta), \theta)$. For a vector parameter, the analogous Hessian formula is
$$D_{\theta\theta}^2 V = f_{\theta\theta} - f_{\theta x} H^{-1} f_{x\theta}.$$

Because $H < 0$ implies $H^{-1} < 0$,
$$-f_{\theta x} H^{-1} f_{x\theta} \geq 0.$$
The second term is therefore an *adjustment effect*. Relative to holding the choice fixed, allowing the decision maker to reoptimize weakly raises the second derivative of the optimized value with respect to the parameter. In economic language, flexibility attenuates the adverse effect of a perturbation or amplifies the favorable one, locally. The first-order envelope theorem says adjustment has no first-order value at the original optimum; this second-order formula measures its next-order value.

**Example 7.9 — Quadratic Adjustment and the Value of Flexibility**
Consider
$$f(x, \theta) = -\frac{a}{2}x^2 + \theta x, \quad a > 0.$$

<!-- page 82 -->

The optimum is
$$x^*(\theta) = \frac{\theta}{a},$$
and
$$V(\theta) = \frac{\theta^2}{2a}.$$
Here
$$f_{\theta\theta} = 0, \quad f_{x\theta} = 1, \quad H = -a.$$
The second-order envelope formula gives
$$V''(\theta) = 0 - 1 \left( -\frac{1}{a} \right) 1 = \frac{1}{a},$$
exactly as direct differentiation of the value function does. Holding $x$ fixed would produce zero curvature in $\theta$; all of the curvature of the optimized value comes from the ability to adjust the choice.

## 7.6 Constrained Envelope Theorem
Now consider
$$V(\theta) = \max_x f(x, \theta)$$
subject to
$$g_i(x, \theta) \geq 0, \quad h_j(x, \theta) = 0.$$
The Lagrangian is
$$\mathcal{L}(\lambda, \mu; \theta) = f(x, \theta) + \sum_i \lambda_i g_i(x, \theta) + \sum_j \mu_j h_j(x, \theta).$$

**Theorem 7.10 — Constrained Envelope Theorem**
Suppose the optimizer and multipliers are locally differentiable in $\theta$, the KKT conditions hold, and the active set is locally stable so that the usual differentiation is valid. Then
$$\frac{dV}{d\theta} = \frac{\partial \mathcal{L}}{\partial \theta}(x^*, \lambda^*, \mu^*; \theta).$$
That is,
$$\frac{dV}{d\theta} = f_\theta + \sum_i \lambda_i^* g_{i,\theta} + \sum_j \mu_j^* h_{j,\theta}.$$

<!-- page 83 -->

**Proof**
Write
$$V(\theta) = f(x^*(\theta), \theta).$$
Differentiating gives
$$V' = f_x^T x^{*'} + f_\theta.$$
Stationarity gives
$$f_x = -\sum_i \lambda_i^* g_{i,x} - \sum_j \mu_j^* h_{j,x}.$$
Hence
$$V' = f_\theta - \sum_i \lambda_i^* g_{i,x}^T x^{*'} - \sum_j \mu_j^* h_{j,x}^T x^{*'}.$$
For equality constraints,
$$h_j(x^*(\theta), \theta) = 0,$$
so differentiation yields
$$h_{j,x}^T x^{*'} + h_{j,\theta} = 0.$$
For an active inequality constraint, the same differentiation gives
$$g_{i,x}^T x^{*'} + g_{i,\theta} = 0.$$
For an inactive inequality constraint, complementary slackness gives
$$\lambda_i^* = 0.$$
Substituting these identities yields
$$V' = f_\theta + \sum_i \lambda_i^* g_{i,\theta} + \sum_j \mu_j^* h_{j,\theta}.$$

This theorem makes the shadow-value interpretation precise. If a parameter relaxes a binding constraint, the associated multiplier determines its first-order value.

## 7.7 Example: Indirect Utility and Roy's Identity
Consider the interior utility-maximization problem
$$V(p, w) = \max_x u(x)$$
subject to
$$w - p^T x = 0.$$

<!-- page 84 -->

The Lagrangian is
$$\mathcal{L}(x, \lambda; p, w) = u(x) + \lambda(w - p^T x).$$
The envelope theorem gives
$$V_w(p, w) = \lambda^*,$$
and for each price $p_i$,
$$V_{p_i}(p, w) = -\lambda^* x_i^*.$$
Provided
$$V_w(p, w) = \lambda^* > 0,$$
dividing gives
$$x_i^*(p, w) = -\frac{V_{p_i}(p, w)}{V_w(p, w)}.$$
This is Roy's identity. The result is not a separate trick from consumer theory; it is a direct consequence of the constrained envelope theorem.

## 7.8 Example: Profit Function and Hotelling's Lemma
Earlier we identified competitive profit with the support function of the technology set:
$$\pi(p) = \sup_{y \in Y} p^T y = \sigma_Y(p).$$
This immediately explains why $\pi$ is convex and positively homogeneous in prices. When the supremum is attained at a unique net-output vector $y^*(p)$ and the profit function is differentiable, the envelope theorem adds a local statement:
$$\nabla_p \pi(p) = y^*(p).$$
Thus convex geometry gives the global shape of the profit function, while the envelope theorem identifies its gradient with the firm's net supply at points of differentiability.

## 7.9 Concavity and Convexity of Value Functions
Optimization often preserves curvature. This matters especially in dynamic programming, where today's value function becomes tomorrow's objective.

**Theorem 7.11 — Partial Maximization Preserves Concavity**
Let $X \subseteq \mathbb{R}^n$ be convex and let
$$f : X \times \Theta \to \mathbb{R}$$

<!-- page 85 -->

be jointly concave in $(x, \theta)$, where $\Theta$ is convex. Define
$$V(\theta) = \sup_{x \in X} f(x, \theta).$$
Assume the supremum is finite. Then $V$ is concave on $\Theta$.

**Proof**

Fix $\theta_1, \theta_2 \in \Theta$ and $t \in [0, 1]$. Let $\varepsilon > 0$ and choose $x_1, x_2 \in X$ such that
$$f(x_i, \theta_i) \geq V(\theta_i) - \varepsilon, \quad i = 1, 2.$$
Since $X$ is convex,
$$x_t = (1 - t)x_1 + tx_2 \in X.$$
Joint concavity gives
$$f(x_t, (1 - t)\theta_1 + t\theta_2) \geq (1 - t)f(x_1, \theta_1) + tf(x_2, \theta_2)$$
$$\geq (1 - t)V(\theta_1) + tV(\theta_2) - \varepsilon.$$
Since $V$ is the supremum over $x$,
$$V((1 - t)\theta_1 + t\theta_2) \geq (1 - t)V(\theta_1) + tV(\theta_2) - \varepsilon.$$
Letting $\varepsilon \downarrow 0$ proves concavity.

There is a parallel result for minimization: partial minimization of a jointly convex function over a convex set preserves convexity.

### 7.10 Indirect Utility and Expenditure as Value Functions

Many familiar objects in microeconomics are value functions.
The indirect utility function is
$$V(p, w) = \max_{x \geq 0} \{u(x) : p^T x \leq w\}.$$
The expenditure function is
$$e(p, \bar{u}) = \min_{x \geq 0} \{p^T x : u(x) \geq \bar{u}\}.$$
The profit function is
$$\pi(p) = \sup_{y \in Y} p^T y.$$

85

<!-- page 86 -->

The cost function is
$$c(w, q) = \inf_{x} \{w^T x : F(x) \geq q\}.$$
These functions inherit structure from optimization. For example, $\pi(p)$ is the supremum of linear functions of $p$, and therefore is convex in prices. The expenditure function is the infimum of linear expenditure over bundles delivering a fixed utility, and is concave in prices under the usual conditions. Such curvature properties are not accidents; they are consequences of how value functions are constructed.

**Remark 7.12 — Nondifferentiable Value Functions**

Even when the primitive objective is smooth, the value function need not be differentiable. A change in the identity of the optimizer can create a kink.
For example,
$$V(\theta) = \max\{\theta, -\theta\} = |\theta|$$
comes from maximizing two smooth alternatives, but $V$ is not differentiable at $\theta = 0$ because both alternatives are optimal there.
This is one reason correspondences are needed: at the parameter values where the value function develops a kink, the optimizer is often set-valued.

## 8 Correspondences

An ordinary function assigns one output to each input. Optimization does not generally behave that way. A parameterized problem may have several maximizers, a game may have several best replies, and an equilibrium may not be unique. The natural mathematical object is therefore a set-valued map, or correspondence.
The distinction is not cosmetic. If
$$S(\theta) = \arg \max_{x \in X(\theta)} f(x, \theta)$$
contains several points, forcing ourselves to choose one arbitrarily can destroy continuity even when the underlying optimization problem behaves perfectly well. It is often the whole set $S(\theta)$ that has the right continuity property.

86

<!-- page 87 -->

### 8.1 Set-Valued Maps

**Definition 8.1 — Correspondence**

Let $X$ and $Y$ be sets. A correspondence
$$F : X \rightrightarrows Y$$
assigns to each $x \in X$ a subset
$$F(x) \subseteq Y.$$
If $F(x)$ is a singleton for every $x$, the correspondence can be identified with an ordinary function.

The double arrow
$$\rightrightarrows$$
is a visual reminder that the output can contain more than one point.

**Example 8.2 — Argmax Correspondence**

For
$$f(x, \theta) = \theta x, \quad x \in [-1, 1],$$
define
$$S(\theta) = \arg \max_{x \in [-1, 1]} \theta x.$$
Then
$$S(\theta) = \begin{cases} \{-1\}, & \theta < 0, \\ [-1, 1], & \theta = 0, \\ \{1\}, & \theta > 0. \end{cases}$$
At $\theta = 0$, every feasible choice is optimal. There is no single-valued optimizer that is continuous through zero, but the set-valued argmax has a natural stability property that we will formalize below.

**Example 8.3 — The Same Correspondence as a Two-Good Demand Problem**

A consumer has one unit of wealth, prices are both one, and utility is
$$u_\theta(x_1, x_2) = (1 + \theta)x_1 + x_2, \quad x_1 + x_2 \leq 1, \quad x_1, x_2 \geq 0.$$
For $\theta > 0$, good 1 gives strictly more utility per dollar, so demand is $(1, 0)$. For $\theta < 0$, demand

87

<!-- page 88 -->

is $(0, 1)$. At $\theta = 0$, every point on the budget line
$$x_1 + x_2 = 1$$
is optimal. Thus a tiny preference perturbation can eliminate many tied choices, but it does not create a new choice far away from the old demand set. This is exactly the asymmetry captured by upper, rather than lower, hemicontinuity of an argmax correspondence.

## 8.2 Graphs and Inverse Images

**Definition 8.4 — Graph of a Correspondence**

The graph of a correspondence $F : X \rightrightarrows Y$ is
$$\text{Gr}(F) = \{(x, y) \in X \times Y : y \in F(x)\}.$$

A correspondence has a closed graph if limits of graph points remain on the graph.

**Definition 8.5 — Closed Graph**

The correspondence $F : X \rightrightarrows Y$ has a closed graph if
$$\text{Gr}(F)$$
is closed in $X \times Y$.
In metric spaces, this means that whenever
$$x_k \to x, \quad y_k \to y, \quad y_k \in F(x_k),$$
we have
$$y \in F(x).$$

The graph formulation is particularly convenient in equilibrium analysis. If a sequence of parameter-choice pairs satisfies an optimality or best-response condition and converges, closed graph ensures that the limiting pair still satisfies the condition.
For an ordinary function $f$, closed graph is weaker than continuity unless additional compactness conditions are imposed. The same caution is needed for correspondences.

88

<!-- page 89 -->

## 8.3 Upper Hemicontinuity

The first continuity notion controls the appearance of new values.

**Definition 8.6 — Upper Hemicontinuity**

A correspondence
$$F : X \rightrightarrows Y$$
is upper hemicontinous at $x \in X$ if for every open set $V \subseteq Y$ with
$$F(x) \subseteq V,$$
there exists a neighborhood $U$ of $x$ such that
$$F(x') \subseteq V \quad \forall x' \in U.$$

The definition says that if we place an open envelope around the entire set $F(x)$, then nearby values of the correspondence eventually remain inside that envelope.
The useful intuition is
nearby parameters cannot suddenly create choices far away from $F(x)$.
Upper hemicontinuity allows some values in $F(x)$ to disappear under perturbation. It only prevents completely new distant values from appearing.

## 8.4 Sequential Form of Upper Hemicontinuity

Before giving the sequence test, we isolate a boundedness condition that prevents selected values from escaping to infinity as the argument approaches a point.

**Definition 8.7 — Local Boundedness**

A correspondence
$$F : X \rightrightarrows \mathbb{R}^m$$
is locally bounded at $x$ if there exist a neighborhood $U$ of $x$ and a bounded set $B \subseteq \mathbb{R}^m$ such that
$$F(x') \subseteq B \quad \forall x' \in U.$$

In Euclidean spaces, local boundedness turns a closed-graph condition into an especially simple sequence test for upper hemicontinuity.

89

<!-- page 90 -->

**Proposition 8.8 — Sequential Test for Upper Hemicontinuity**

Let $F : X \rightrightarrows \mathbb{R}^m$ be compact-valued and locally bounded near $x$. Then $F$ is upper hemicontinous at $x$ if and only if the following property holds:
whenever
$$x_k \to x, \quad y_k \in F(x_k), \quad y_k \to y,$$
we have
$$y \in F(x).$$

The conclusion is exactly a closed-graph property. The local boundedness assumption is what ensures that a sequence of nearby selected values has a convergent subsequence when needed.
In many economic applications the codomain itself is compact. Then local boundedness is automatic, and upper hemicontinuity plus closed values is essentially equivalent to closed graph.

## 8.5 Lower Hemicontinuity

Upper hemicontinuity controls new values. Lower hemicontinuity controls the survival of old values.

**Definition 8.9 — Lower Hemicontinuity**

A correspondence
$$F : X \rightrightarrows Y$$
is lower hemicontinous at $x \in X$ if, whenever an open set $V \subseteq Y$ satisfies
$$F(x) \cap V \neq \emptyset,$$
there exists a neighborhood $U$ of $x$ such that
$$F(x') \cap V \neq \emptyset \quad \forall x' \in U.$$

The intuition is
every value available at $x$ can be approximated by values available nearby.

In metric spaces this has a convenient sequential form.

**Proposition 8.10 — Sequential Test for Lower Hemicontinuity**

A correspondence $F : X \rightrightarrows Y$ between metric spaces is lower hemicontinous at $x$ if and only

90

<!-- page 91 -->

if, for every sequence
$$x_k \to x$$
and every
$$y \in F(x),$$
there exist points
$$y_k \in F(x_k)$$
such that
$$y_k \to y.$$

## 8.6 Why the Two Notions Differ

Consider
$$F(t) = \begin{cases} \{-1\}, & t < 0, \\ \{-1, 1\}, & t = 0, \\ \{1\}, & t > 0. \end{cases}$$
At $t = 0$, the correspondence is upper hemicontinous: nearby values are always either $-1$ or $1$, both of which already belong to $F(0)$.
But it is not lower hemicontinous at zero. The point $-1 \in F(0)$ cannot be approximated by values $F(t_k)$ along a sequence $t_k \downarrow 0$, because then $F(t_k) = \{1\}$.
This is the typical stability pattern for optimization. At a knife-edge parameter, several choices may tie. A small perturbation may eliminate some of those old solutions, but upper hemicontinuity rules out the appearance of a completely new, distant solution. Lower hemicontinuity is the stronger requirement that every old solution can itself be tracked by nearby solutions.

[Image: A graph showing the correspondence $S(\theta)$. For $\theta < 0$, $S(\theta) = \{-1\}$. For $\theta > 0$, $S(\theta) = \{1\}$. At $\theta = 0$, $S(0) = [-1, 1]$.]

Figure 12: The argmax correspondence for $\max_{x \in [-1, 1]} \theta x$. At the tie, old maximizers can disappear under perturbation, but no distant new maximizers appear.

91

<!-- page 92 -->

**Definition 8.11 — Continuous Correspondence**

A correspondence is continuous at $x$ if it is both upper and lower hemicontinous at $x$.

For a single-valued correspondence, either upper or lower hemicontinuity reduces to ordinary continuity; requiring both therefore adds nothing in the single-valued case.

## 8.7 Compact- and Convex-Valued Correspondences

Fixed-point and maximum theorems require not only continuity properties but also structure of the value sets.

**Definition 8.12 — Compact- and Convex-Valued**

A correspondence $F : X \rightrightarrows \mathbb{R}^m$ is
(i) **compact-valued** if $F(x)$ is compact for every $x$;
(ii) **convex-valued** if $F(x)$ is convex for every $x$;
(iii) **nonempty-valued** if $F(x) \neq \emptyset$ for every $x$.

These properties have direct economic meanings. Compact-valuedness prevents solution sets from escaping. Convex-valuedness says that mixtures of solutions remain solutions. For best-response correspondences, quasiconcavity of payoff in one's own action is what often generates convex-valuedness.

## 8.8 Closed Graph and Upper Hemicontinuity

It is useful to know precisely when closed graph and upper hemicontinuity coincide.

**Proposition 8.13 — Upper Hemicontinuity Implies Closed Graph**

Let $X$ be a metric space and let $F : X \rightrightarrows \mathbb{R}^m$ be upper hemicontinous and closed-valued. Then $F$ has a closed graph.

**Proof**

Suppose
$$x_k \to x, \quad y_k \in F(x_k), \quad y_k \to y.$$
Assume toward a contradiction that $y \notin F(x)$. Since $F(x)$ is closed in the metric space $\mathbb{R}^m$, the distance from $y$ to $F(x)$ is strictly positive. Hence we can choose an open set $V$ containing $F(x)$

92

<!-- page 93 -->

whose closure does not contain $y$. Upper hemicontinuity implies that, for sufficiently large $k$,
$$F(x_k) \subseteq V.$$
Hence $y_k \in V$ eventually. But $y_k \to y$ and $y \notin \overline{V}$, a contradiction.

The converse requires a boundedness condition.

**Proposition 8.14 — Closed Graph plus Local Boundedness Implies Upper Hemicontinuity**

Let $F : X \rightrightarrows \mathbb{R}^m$ have closed graph and compact values. If $F$ is locally bounded at $x$, then $F$ is upper hemicontinous at $x$.

**Proof**

Suppose upper hemicontinuity fails at $x$. Then there exists an open set $V$ containing $F(x)$ and a sequence $x_k \to x$ with points
$$y_k \in F(x_k) \setminus V.$$
Local boundedness implies that $\{y_k\}$ is eventually bounded. Passing to a subsequence,
$$y_{k_j} \to y.$$
Because the graph is closed,
$$y \in F(x) \subseteq V.$$
Since $V$ is open, $y_{k_j} \in V$ for all sufficiently large $j$, contradicting the construction.

In a compact codomain $Y$, local boundedness is automatic. This is why equilibrium proofs on compact strategy spaces often state Kakutani using "closed graph" instead of "upper hemicontinuity."

## 8.9 A Small Calculus of Correspondences

Equilibrium arguments routinely combine several correspondences. Two closure properties are especially useful and save us from reproving continuity every time a product of individual choice sets is formed.

**Proposition 8.15 — Compact Images and Products**

(i) Let $K$ be compact and let $F : K \rightrightarrows \mathbb{R}^m$ be upper hemicontinous and compact-valued. Then
$$F(K) = \bigcup_{x \in K} F(x)$$

93

<!-- page 94 -->

is compact.
(ii) For $i = 1, \dots, N$, let
$$F_i : X \rightrightarrows \mathbb{R}^{m_i}$$
be upper hemicontinous and compact-valued. Then the product correspondence
$$F(x) = F_1(x) \times \dots \times F_N(x)$$
is upper hemicontinous and compact-valued. If each $F_i$ is lower hemicontinous, then the product is lower hemicontinous as well.

**Proof**

For the first statement, take any sequence
$$y_k \in F(K).$$
Choose $x_k \in K$ with $y_k \in F(x_k)$. Compactness of $K$ gives a subsequence $x_{k_j} \to x \in K$. Upper hemicontinuity and compact-valuedness imply local boundedness and closed graph, so after taking a further subsequence if necessary, $y_{k_j}$ converges to some $y \in F(x)$. Hence every sequence in $F(K)$ has a convergent subsequence with limit in $F(K)$.
For the product statement, compact-valuedness follows from finite products of compact sets. If $x_k \to x$ and
$$y_k = (y_{1k}, \dots, y_{Nk}) \in F(x_k)$$
converges to $y = (y_1, \dots, y_N)$, then $y_{ik} \in F_i(x_k)$ and closed graph of each $F_i$ gives $y_i \in F_i(x)$ for every $i$. The product therefore has closed graph and is locally bounded, hence is upper hemicontinous. The lower-hemicontinuity statement follows by approximating each component of any $y \in F(x)$ and assembling the component sequences.

The product result will be used directly in the Nash-existence proof: once every player's best-response correspondence is well behaved, the joint best-response correspondence inherits the same regularity.

## 8.10 A Correspondence Can Be Better Behaved Than Any Selection

Return to the argmax example
$$S(\theta) = \begin{cases} \{-1\}, & \theta < 0, \\ [-1, 1], & \theta = 0, \\ \{1\}, & \theta > 0. \end{cases}$$
The correspondence is upper hemicontinous at zero. But any single-valued selection $s(\theta) \in S(\theta)$ must satisfy
$$s(\theta) = -1 \quad \text{for } \theta < 0,$$

94

<!-- page 95 -->

and
$$s(\theta) = 1 \quad \text{for } \theta > 0.$$
No choice of $s(0)$ makes the selection continuous.
The discontinuity belongs to the arbitrary act of selecting one optimizer, not to the solution set itself. This is exactly why correspondence language is indispensable.

## 9 The Maximum Theorem

We now have all the ingredients needed to study continuity of optimization itself. The question is simple to state. Suppose both the objective function and the feasible set change continuously with a parameter. Does the optimized value also change continuously? Do optimal choices stay close to the old solution set?
The answer is Berge's maximum theorem. It is one of the central bridges between analysis and economics because it combines compactness, continuity, correspondences, and optimization in a single result.

## 9.1 The Parameterized Problem

Let
$$\Theta \subseteq \mathbb{R}^k$$
be a parameter space and let
$$X \subseteq \mathbb{R}^n$$
be the choice space. Suppose the feasible set depends on the parameter through a correspondence
$$\Gamma : \Theta \rightrightarrows X.$$
Let
$$f : \Theta \times X \to \mathbb{R}$$
be the objective. Define
$$V(\theta) = \max_{x \in \Gamma(\theta)} f(\theta, x)$$
and
$$S(\theta) = \arg \max_{x \in \Gamma(\theta)} f(\theta, x).$$
There are two derived objects. The value function $V$ is single-valued. The optimizer $S$ is generally a correspondence.
Berge's theorem needs both directions of continuity of the feasible correspondence, but they do different jobs. Rather than hide that asymmetry inside one long proof, it is useful to isolate the two one-sided statements first.

95

<!-- page 96 -->

## 9.2 One-Sided Stability of the Value Function

For a scalar function $v : \Theta \to \mathbb{R}$, the sequential definitions are convenient: $v$ is upper semicontinuous at $\theta$ if
$$\theta_k \to \theta \implies \limsup_{k \to \infty} v(\theta_k) \leq v(\theta),$$
and lower semicontinuous if
$$\theta_k \to \theta \implies \liminf_{k \to \infty} v(\theta_k) \geq v(\theta).$$
A real-valued function is continuous exactly when both inequalities hold.

**Proposition 9.1 — Lower Semicontinuity of the Optimal Value**

Suppose $\Gamma$ is nonempty-valued and lower hemicontinous at $\theta$, and $f$ is continuous. Define
$$V(\theta') = \sup_{x \in \Gamma(\theta')} f(\theta', x),$$
and assume $V(\theta)$ is finite. Then $V$ is lower semicontinuous at $\theta$.

**Proof**

Let $\theta_k \to \theta$ and fix $\varepsilon > 0$. Choose $x \in \Gamma(\theta)$ such that
$$f(\theta, x) > V(\theta) - \varepsilon.$$
Lower hemicontinuity provides $x_k \in \Gamma(\theta_k)$ with
$$x_k \to x.$$
Therefore
$$V(\theta_k) \geq f(\theta_k, x_k),$$
so continuity of $f$ gives
$$\liminf_{k \to \infty} V(\theta_k) \geq f(\theta, x) > V(\theta) - \varepsilon.$$
Letting $\varepsilon \downarrow 0$ proves the claim.

The argument has a clear interpretation: start from a nearly optimal choice in the limiting problem and use lower hemicontinuity to keep a nearby version of that choice feasible after a perturbation. This prevents the optimized value from jumping down.

96

<!-- page 97 -->

**Proposition 9.2 — Upper Semicontinuity of the Optimal Value**

Suppose $\Gamma$ is nonempty-valued, compact-valued, and upper hemicontinuous at $\theta$, and $f$ is continuous. Define
$$V(\theta') = \max_{x \in \Gamma(\theta')} f(\theta', x).$$
Then $V$ is upper semicontinuous at $\theta$.

**Proof**

Let $\theta_k \to \theta$ and choose
$$x_k \in \arg \max_{x \in \Gamma(\theta_k)} f(\theta_k, x).$$
Because $\Gamma(\theta)$ is compact and $\Gamma$ is upper hemicontinuous, the nearby sets $\Gamma(\theta_k)$ eventually lie in a common bounded neighborhood of $\Gamma(\theta)$. Choose a subsequence along which
$$V(\theta_{k_j}) \to \limsup_{k \to \infty} V(\theta_k).$$
After passing to a further subsequence,
$$x_{k_j} \to \bar{x}.$$
Upper hemicontinuity and compact values imply closed graph, so
$$\bar{x} \in \Gamma(\theta).$$
Continuity of $f$ then yields
$$\limsup_{k \to \infty} V(\theta_k) = f(\theta, \bar{x}) \leq V(\theta).$$

Here the proof follows optimizers from nearby problems toward the limit. Upper hemicontinuity prevents those optimizers from escaping to a new distant region, so the optimized value cannot jump upward.

**9.3 Berge’s Maximum Theorem**

The two one-sided propositions now fit together immediately.

**Theorem 9.3 — Berge’s Maximum Theorem**

Let $\Theta \subseteq \mathbb{R}^k$ and $X \subseteq \mathbb{R}^n$. Suppose
$$\Gamma: \Theta \rightrightarrows X$$

<!-- page 98 -->

is nonempty-valued, compact-valued, and continuous, and suppose
$$f: \Theta \times X \to \mathbb{R}$$
is continuous. Define
$$V(\theta) = \max_{x \in \Gamma(\theta)} f(\theta, x)$$
and
$$S(\theta) = \arg \max_{x \in \Gamma(\theta)} f(\theta, x).$$
Then:
(i) $V$ is continuous;
(ii) $S(\theta)$ is nonempty and compact for every $\theta$;
(iii) $S$ is upper hemicontinuous.

**Proof**

Fix $\theta$. Since $\Gamma(\theta)$ is nonempty and compact and $x \mapsto f(\theta, x)$ is continuous, Weierstrass implies that $S(\theta)$ is nonempty. It is a closed subset of $\Gamma(\theta)$, hence compact.
Because $\Gamma$ is both lower and upper hemicontinuous, proposition 9.1 and proposition 9.2 imply that $V$ is both lower and upper semicontinuous. Therefore $V$ is continuous.
It remains to prove upper hemicontinuity of $S$. Suppose
$$\theta_k \to \theta, \quad x_k \in S(\theta_k), \quad x_k \to x.$$
Since $x_k \in \Gamma(\theta_k)$ and $\Gamma$ has closed graph,
$$x \in \Gamma(\theta).$$
Moreover,
$$f(\theta_k, x_k) = V(\theta_k).$$
Taking limits and using continuity of $f$ and $V$ gives
$$f(\theta, x) = V(\theta),$$
so
$$x \in S(\theta).$$
Thus $S$ has closed graph. As a subcorrespondence of the locally bounded correspondence $\Gamma$, it is locally bounded; its values are compact. Hence proposition 8.14 implies that $S$ is upper hemicontinuous.

<!-- page 99 -->

The proof separates the theorem into three pieces with different logical ingredients: Weierstrass gives existence at a fixed parameter, the two one-sided maximum results give continuity of the value, and closed graph plus local boundedness gives stability of the argmax set. This modular structure is often easier to reuse than memorizing Berge’s theorem as a single black box.

**Corollary 9.4 — Berge with a Fixed Feasible Set**

Let $K \subseteq \mathbb{R}^n$ be nonempty and compact and let
$$f: \Theta \times K \to \mathbb{R}$$
be continuous. Then
$$V(\theta) = \max_{x \in K} f(\theta, x)$$
is continuous, and
$$S(\theta) = \arg \max_{x \in K} f(\theta, x)$$
is nonempty, compact-valued, and upper hemicontinuous.

This fixed-domain form is the version used most often in games: the strategy set is held fixed while payoffs vary with opponents' actions or beliefs. All of the technical work about continuity of the feasible correspondence disappears.

**Proposition 9.5 — Quasiconcavity Makes the Argmax Convex**

Fix a parameter $\theta$. Suppose $\Gamma(\theta)$ is convex and $f(\theta, \cdot)$ is quasiconcave. Then
$$S(\theta) = \arg \max_{x \in \Gamma(\theta)} f(\theta, x)$$
is convex. If $f(\theta, \cdot)$ is strictly quasiconcave, then $S(\theta)$ contains at most one point.

**Proof**

Let $x, y \in S(\theta)$ and let their common maximal value be $M$. For $t \in [0, 1]$, convexity of $\Gamma(\theta)$ gives
$$z = (1 - t)x + ty \in \Gamma(\theta).$$
Quasiconcavity gives
$$f(\theta, z) \geq \min\{f(\theta, x), f(\theta, y)\} = M.$$
Since $M$ is already the maximum, equality holds and $z \in S(\theta)$. Under strict quasiconcavity, two distinct maximizers would make the displayed inequality strict for $t \in (0, 1)$, contradicting maximality.

This proposition supplies precisely the convex-valuedness that Kakutani requires for best-response

<!-- page 100 -->

correspondences.

**9.4 Unique Optimizers Give Continuous Policy Functions**

If the argmax is always a singleton, upper hemicontinuity becomes ordinary continuity.

**Corollary 9.6 — Continuity under Uniqueness**

Under the assumptions of theorem 9.3, suppose that for every $\theta$ the maximizer is unique:
$$S(\theta) = \{x^*(\theta)\}.$$
Then the policy function
$$x^*: \Theta \to X$$
is continuous.

**Proof**

A single-valued upper hemicontinuous correspondence is an ordinary continuous function. More explicitly, if $\theta_k \to \theta$, any convergent subsequence of $x^*(\theta_k)$ must converge to a point in
$$S(\theta) = \{x^*(\theta)\}.$$
Local boundedness gives subsequential compactness, and uniqueness forces every subsequence limit to equal $x^*(\theta)$. Hence the whole sequence converges to $x^*(\theta)$.

Strict concavity is a common way to supply uniqueness. Combined with Berge’s theorem, it upgrades an upper-hemicontinuous argmax correspondence to a continuous policy function.

**9.5 Example: Quadratic Tracking Problem**

Consider
$$V(\theta) = \max_{x \in [0, 1]} -(x - \theta)^2, \quad \theta \in \mathbb{R}.$$
The feasible correspondence is constant:
$$\Gamma(\theta) = [0, 1].$$
The objective is continuous and strictly concave in $x$. Therefore Berge’s theorem and uniqueness imply that the optimizer is continuous.

<!-- page 101 -->

We can solve it directly:
$$x^*(\theta) = \begin{cases} 0, & \theta \leq 0, \\ \theta, & 0 < \theta < 1, \\ 1, & \theta \geq 1. \end{cases}$$
The value function is
$$V(\theta) = \begin{cases} -\theta^2, & \theta \leq 0, \\ 0, & 0 < \theta < 1, \\ -(\theta - 1)^2, & \theta \geq 1. \end{cases}$$
Both are continuous. The policy has kinks at the points where the constraint becomes binding, but no jumps.

[Image: Plot of $x^*(\theta)$ showing a line segment from $(0,0)$ to $(1,1)$ with horizontal segments at $0$ for $\theta < 0$ and $1$ for $\theta > 1$. Label: policy]
[Image: Plot of $V(\theta)$ showing a downward-opening parabola centered at $0$ for $\theta < 0$, a flat segment at $0$ for $0 < \theta < 1$, and a downward-opening parabola centered at $1$ for $\theta > 1$. Label: value]

Figure 13: Berge gives continuity even when constraints switch status. The policy is continuous but kinked at $\theta = 0$ and $\theta = 1$; the value function remains continuous.

**9.6 Example: Demand Correspondence**

Let
$$B(p, w) = \{x \in \mathbb{R}^L_+ : p^T x \leq w\},$$
with strictly positive prices and positive wealth. On a compact parameter set bounded away from zero prices, the budget correspondence is continuous and compact-valued after using the budget bound to restrict consumption. If utility is continuous, Berge’s theorem implies that Marshallian demand
$$D(p, w) = \arg \max_{x \in B(p, w)} u(x)$$
is nonempty, compact-valued, and upper hemicontinuous. If preferences are strictly convex, equivalently utility is strictly quasiconcave under a suitable representation, demand is single-valued and continuous.
This is the mathematical route from continuous preferences and compact budget sets to continuous demand.

<!-- page 102 -->

**9.7 What Berge’s Theorem Does Not Give**

Berge’s theorem is a continuity theorem, not a differentiability theorem. Even with smooth primitives, a policy or value function can fail to be differentiable when constraints become active or when multiple optima meet.
It also does not guarantee lower hemicontinuity of the argmax correspondence. At a parameter value with multiple tied optima, some of those optima may disappear under an arbitrarily small perturbation.
The basic stability result is therefore asymmetric:
argmax correspondences are naturally upper hemicontinuity, not necessarily continuous.

**10 Fixed-Point Theorems**

Optimization describes individual choice. Equilibrium adds mutual consistency. A consumer chooses given prices, but equilibrium prices must be consistent with aggregate choices. A firm chooses given wages, but equilibrium wages depend on labor demand and supply. A player chooses a best response to the strategies of other players, but those other strategies must themselves be best responses.
Mathematically, many equilibrium problems take the form
$$x \in F(x).$$
If $F$ is single-valued, this is
$$x = F(x).$$
Such a point is called a fixed point.

**10.1 Fixed Points**

**Definition 10.1 — Fixed Point**

Let $X$ be a set.
(i) If $f: X \to X$ is a function, a point $x^* \in X$ is a fixed point if
$$f(x^*) = x^*.$$
(ii) If $F: X \rightrightarrows X$ is a correspondence, a point $x^* \in X$ is a fixed point if
$$x^* \in F(x^*).$$

<!-- page 103 -->

The correspondence formulation contains the function formulation as a special case.
Before stating the general finite-dimensional theorem, it is useful to see the one-dimensional argument. It uses only the intermediate value theorem.

**Proposition 10.2 — Fixed Point on an Interval**

Every continuous function
$$f: [0, 1] \to [0, 1]$$
has a fixed point.

**Proof**

Define
$$g(x) = f(x) - x.$$
Since $f(0) \in [0, 1]$,
$$g(0) = f(0) \geq 0.$$
Since $f(1) \in [0, 1]$,
$$g(1) = f(1) - 1 \leq 0.$$
The function $g$ is continuous. By the intermediate value theorem, there exists $x^* \in [0, 1]$ such that
$$g(x^*) = 0.$$
Hence
$$f(x^*) = x^*.$$

This proof already reveals the role of the self-map condition. At the left endpoint, $f$ cannot point further left; at the right endpoint, it cannot point further right. Continuity forces a crossing.

**10.2 Brouwer’s Fixed-Point Theorem**

The higher-dimensional generalization is one of the foundational results of topology.

**Theorem 10.3 — Brouwer Fixed-Point Theorem**

Let
$$K \subseteq \mathbb{R}^n$$
be nonempty, compact, and convex. Every continuous mapping
$$f: K \to K$$

<!-- page 104 -->

[Image: Plot showing a diagonal dashed line $y=x$ and a solid curve $y=f(x)$ intersecting at a point $x^*$.]

Figure 14: In one dimension, a fixed point is an intersection with the diagonal. The intermediate-value argument shows that a continuous self-map of $[0, 1]$ cannot avoid a crossing.

has a fixed point. That is, there exists $x^* \in K$ such that
$$f(x^*) = x^*.$$

**Remark 10.4 — Why Convex Projection Fits Brouwer**

One standard route from Brouwer’s theorem on a simplex to the theorem on an arbitrary compact convex set uses the projection map studied earlier. Choose a simplex $T$ large enough to contain $K$. By proposition 1.21,
$$P_K: T \to K$$
is continuous. If $f: K \to K$ is continuous, then
$$g = f \circ P_K: T \to K \subseteq T$$
is a continuous self-map of the simplex. A fixed point $z$ of $g$ must lie in $K$; therefore $P_K(z) = z$ and
$$f(z) = z.$$
This proof architecture is useful because it shows that the projection theorem is not an isolated geometric result: it is also a device for transporting fixed-point theorems to convex subsets.

We will use Brouwer rather than prove the full simplex theorem. The proof in general dimension requires topological machinery beyond the scope of these notes. What matters for applications is understanding each assumption.

<!-- page 105 -->

**10.3 Why Brouwer’s Assumptions Matter**

**Continuity.** If discontinuities are allowed, a self-map can jump over every potential fixed point. For example,
$$f(x) = \begin{cases} 1, & x < 1/2, \\ 0, & x \geq 1/2 \end{cases}$$
maps $[0, 1]$ into itself but has no fixed point.
**Compactness.** The map
$$f(x) = x + 1$$
from $\mathbb{R}$ to itself is continuous and the domain is convex, but there is no fixed point. A fixed point can "escape to infinity."
**Convexity.** Consider the unit circle
$$S^1 = \{x \in \mathbb{R}^2 : \|x\| = 1\}$$
and rotate every point by $90^\circ$. This is a continuous self-map of a compact set, but it has no fixed point. The circle is not convex.
These examples show that Brouwer is not simply a continuity theorem. The geometry of the domain matters essentially.

**10.4 Approximate Fixed Points and Residuals**

For computation, one often obtains a point whose fixed-point equation holds only approximately. Compactness gives a useful qualitative guarantee: a sufficiently small residual cannot occur far away from the exact fixed-point set.

**Proposition 10.5 — Small Residuals Are Near the Fixed-Point Set**

Let $K \subseteq \mathbb{R}^n$ be nonempty and compact and let $f: K \to K$ be continuous. Let
$$F = \{x \in K : f(x) = x\}$$
be the fixed-point set, and assume $F \neq \emptyset$. For every $\varepsilon > 0$ there exists $\delta > 0$ such that
$$\|f(z) - z\| < \delta \implies \text{dist}(z, F) < \varepsilon.$$

**Proof**

Fix $\varepsilon > 0$ and consider the compact set
$$C = \{z \in K : \text{dist}(z, F) \geq \varepsilon\}.$$

<!-- page 106 -->

The residual function
$$r(z) = \|f(z) - z\|$$
is continuous. It is strictly positive on $C$, because $C$ contains no fixed point. Therefore it attains a strictly positive minimum
$$\delta_0 = \min_{z \in C} r(z) > 0.$$
Taking any $0 < \delta < \delta_0$ proves the result.

For numerical equilibrium work, this is the right qualitative interpretation of a small fixed-point residual. It says that residual convergence forces distance to the exact equilibrium set to vanish. It does not select among multiple equilibria, and it does not provide a useful quantitative error bound without additional structure such as a contraction or an error-bound condition.

**10.5 From Functions to Correspondences**

Brouwer is not enough for many economic problems because best responses can be set-valued. If a player is indifferent between several actions, there is no canonical single best-response function. Selecting one arbitrarily may destroy continuity.
The correct extension is Kakutani’s theorem.

**Theorem 10.6 — Kakutani Fixed-Point Theorem**

Let
$$K \subseteq \mathbb{R}^n$$
be nonempty, compact, and convex. Let
$$F: K \rightrightarrows K$$
be a correspondence such that:
(i) $F(x)$ is nonempty for every $x \in K$;
(ii) $F(x)$ is convex for every $x \in K$;
(iii) $F(x)$ is closed for every $x \in K$;
(iv) $F$ is upper hemicontinous.
Then there exists $x^* \in K$ such that
$$x^* \in F(x^*).$$

Because $K$ itself is compact, one often sees the theorem stated with "closed graph" in place of upper hemicontinuity and closed values. On a compact domain and codomain, these formulations are equivalent under the conditions used here.

<!-- page 107 -->

If $F$ is single-valued,
$$F(x) = \{f(x)\},$$
then convex-valuedness is automatic and upper hemicontinuity reduces to continuity of $f$. Kakutani therefore collapses to Brouwer.
The new requirement is convexity of the value set. Why is this reasonable in economics? Suppose $F(x)$ is a best-response set generated by maximizing a quasiconcave objective over a convex action set. If $y_1$ and $y_2$ are both maximizers, then every mixture
$$(1 - t)y_1 + ty_2$$
is at least as good as the worse endpoint and therefore is also optimal. The best-response set is convex.
Thus quasiconcavity, which earlier guaranteed convex upper contour sets, now becomes the condition that allows Kakutani to operate.

**10.6 Nash Equilibrium as a Fixed Point**

Consider a game with players $i = 1, \dots, N$. Player $i$ chooses
$$s_i \in S_i,$$
and receives payoff
$$u_i(s_i, s_{-i}).$$
For each profile of opponents' strategies $s_{-i}$, define the best-response correspondence
$$B_i(s_{-i}) = \arg \max_{a_i \in S_i} u_i(a_i, s_{-i}).$$
The joint best-response correspondence is
$$B(s) = B_1(s_{-1}) \times \dots \times B_N(s_{-N}).$$
A strategy profile $s^*$ is a Nash equilibrium exactly when every player's strategy is a best response to the others:
$$s_i^* \in B_i(s_{-i}^*) \quad \forall i.$$
Equivalently,
$$s^* \in B(s^*).$$
Nash equilibrium is therefore a fixed point of the best-response correspondence.

<!-- page 108 -->

**Theorem 10.7 — Existence of Nash Equilibrium under Standard Convexity Conditions**

Suppose, for each player $i$,
$$S_i \subseteq \mathbb{R}^{n_i}$$
is nonempty, compact, and convex. Suppose each payoff
$$u_i: S_1 \times \dots \times S_N \to \mathbb{R}$$
is continuous in the full strategy profile and quasiconcave in $s_i$ holding $s_{-i}$ fixed. Then the game has a Nash equilibrium.

**Proof**

Let
$$S = S_1 \times \dots \times S_N.$$
Finite products of nonempty compact convex sets are nonempty, compact, and convex.
Fix player $i$. Treat $s_{-i}$ as the parameter and $S_i$ as the fixed feasible set. By corollary 9.4, continuity of $u_i$ and compactness of $S_i$ imply that
$$B_i(s_{-i}) \neq \emptyset,$$
that $B_i$ is compact-valued, and that it is upper hemicontinous. By proposition 9.5, quasiconcavity of $u_i(\cdot, s_{-i})$ makes $B_i$ convex-valued.
The joint best-response correspondence is the finite product
$$B(s) = B_1(s_{-1}) \times \dots \times B_N(s_{-N}).$$
By proposition 8.15, it is compact-valued and upper hemicontinous; nonemptiness and convex-valuedness are preserved by finite products as well.
Kakutani’s theorem gives some
$$s^* \in S$$
such that
$$s^* \in B(s^*).$$
By construction, this is a Nash equilibrium.

Each assumption has a distinct job: compactness and continuity give best responses, quasiconcavity makes the best-response values convex, and Kakutani converts those properties into mutual consistency. The final subsection abstracts this argument into a reusable equilibrium-existence template.

<!-- page 109 -->

### 10.7 Finite Games and Mixed Strategies

A finite game may fail to have a pure-strategy Nash equilibrium. Mixed strategies convexify the strategy sets.

If player $i$ has $m_i$ pure actions, a mixed strategy is a probability vector
$$\sigma_i \in \Delta^{m_i-1} = \left\{ p \in \mathbb{R}_+^{m_i} : \sum_{j=1}^{m_i} p_j = 1 \right\}.$$

The simplex $\Delta^{m_i-1}$ is nonempty, compact, and convex.

Expected payoff is multilinear in mixed strategies and therefore continuous. Holding opponents' strategies fixed, expected payoff is linear in one's own mixed strategy, so it is both concave and convex. Hence the best-response set is convex.

The preceding theorem therefore applies.

::: {.infobox}
**Corollary 10.8 — Nash's Existence Theorem for Finite Games**

Every finite normal-form game has at least one Nash equilibrium in mixed strategies.
:::

This is an important example of *convexification by randomization*. A discrete pure action set is not convex, but the set of lotteries over those actions is a simplex. The fixed-point theorem operates on the convexified strategy space.

::: {.infobox}
**Example 10.9 — Cournot Equilibrium as a Fixed Point**

Two firms choose quantities $q_1, q_2 \geq 0$. Inverse demand is
$$P(Q) = a - bQ, \quad Q = q_1 + q_2,$$
and both firms have constant marginal cost $c < a$. Firm $i$'s profit is
$$\pi_i(q_i, q_j) = [a - c - b(q_i + q_j)]q_i.$$
For an interior best response,
$$a - c - 2bq_i - bq_j = 0,$$
so
$$BR_i(q_j) = \max\left\{0, \frac{a - c - bq_j}{2b}\right\}.$$
A Nash equilibrium is a pair $(q_1^*, q_2^*)$ at which the two best-response graphs intersect. Symmetry gives
$$q_1^* = q_2^* = \frac{a - c}{3b}.$$
:::

<!-- page 110 -->

The familiar diagram of crossing reaction curves is therefore literally a fixed-point diagram: each coordinate of the candidate profile must reproduce the best response to the other coordinate.

[Image: A graph with $q_1$ on the horizontal axis and $q_2$ on the vertical axis. Two downward-sloping lines represent $q_2 = BR_2(q_1)$ and $q_1 = BR_1(q_2)$. They intersect at a point labeled "Nash equilibrium" with coordinates $(q_1^*, q_2^*)$.]

Figure 15: Cournot equilibrium is the intersection of the two best-response relations. The intersection condition is precisely mutual best response, hence a fixed point.

### 10.8 Brouwer versus Kakutani

The two fixed-point theorems serve different situations:

| | Brouwer | Kakutani |
| :--- | :--- | :--- |
| object | $f : K \to K$ | $F : K \rightrightarrows K$ |
| continuity | continuous | upper hemicontinuous |
| values | single point | nonempty, convex, closed |
| conclusion | $f(x^*) = x^*$ | $x^* \in F(x^*)$ |

If a model naturally produces a continuous policy function, Brouwer may be enough. If optimization produces multiple best responses or multiple optimal choices, forcing a single-valued selection is usually the wrong move; Kakutani is designed for exactly that situation.

### 10.9 The Architecture of an Equilibrium-Existence Proof

Many equilibrium proofs in graduate economics can be organized into the same five steps.

**Step 1.** Choose a compact convex set $K$ in which equilibrium objects will live.

<!-- page 111 -->

**Step 2.** Define a function or correspondence
$$F : K \rightrightarrows K$$
whose fixed points are exactly equilibria.

**Step 3.** Prove nonemptiness and convexity of $F(x)$. Optimization and quasiconcavity often do this.

**Step 4.** Prove continuity or upper hemicontinuity. Berge's maximum theorem often does this.

**Step 5.** Apply Brouwer or Kakutani.

The hard economic work is usually hidden in Steps 1–4: finding a suitable compact set, showing that individual problems have solutions, and proving the correspondence is well behaved. The fixed-point theorem is the final logical step, not the whole proof.

### References and Further Reading

The exposition in this part has been developed for the present math camp rather than following any single text chapter by chapter. The references below are useful for alternative proofs, additional examples, and deeper treatments.

### References

[1] Kim C. Border. *Selected Lecture Notes on Mathematical Economics and Convex Analysis*. Kim C. Border Repository, archived by P. J. Healy at Ohio State University. Especially relevant here are *Separating Hyperplane Theorems*, *Convex Analysis and Profit/Cost/Support Functions*, *Introduction to Correspondences*, *Classical Envelope Theorem*, *Constrained Maxima and Saddlepoints*, and *Fixed Point Theory*. https://healy.econ.ohio-state.edu/kcb/.

[2] Angel de la Fuente. *Mathematical Methods and Models for Economists*. Cambridge University Press, 2000.

[3] Rangarajan K. Sundaram. *A First Course in Optimization Theory*. Cambridge University Press, 1996.

[4] Carl P. Simon and Lawrence Blume. *Mathematics for Economists*. W. W. Norton, 1994.

[5] Stephen Boyd and Lieven Vandenberghe. *Convex Optimization*. Cambridge University Press, 2004. The book and associated lecture material are available from https://web.stanford.edu/~boyd/cvxbook/.

[6] Charalambos D. Aliprantis and Kim C. Border. *Infinite Dimensional Analysis: A Hitchhiker's Guide*. Springer, 3rd edition, 2006.

<!-- page 112 -->

[7] Muhamet Yıldız. *Game Theory: Lecture Notes*, MIT 14.126. MIT OpenCourseWare, https://ocw.mit.edu/courses/14-126-game-theory-spring-2024/.

[8] Gabriele Farina. *Nonlinear Optimization: Lecture Notes*, MIT 6.7220 / 15.084, Spring 2025. MIT OpenCourseWare, https://ocw.mit.edu/courses/6-7220j-nonlinear-optimization-spring-2025/.

[9] Robert M. Freund. *Nonlinear Programming*, MIT 15.084J lecture notes. Massachusetts Institute of Technology.

[10] Martin J. Osborne. *Mathematical Methods for Economic Theory*. Online mathematical-economics notes; see especially the constrained-optimization material and bordered-Hessian calculations.