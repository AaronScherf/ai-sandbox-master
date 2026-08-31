---
source_pdf: LN_Analysis.pdf
folder_category: ta_notes
total_pages: 155
routing: gemini_batched
model: gemini-3.1-flash-lite
pages_repaired: 21
repaired_pages: [18, 33, 48, 78, 81, 84, 85, 87, 88, 92, 93, 95, 96, 97, 98, 106, 107, 108, 109, 110, 144]
tags: []
---

<!-- page 1 -->

Part II: Analysis in Euclidean Spaces$^{\dagger}$

Hao Jiang$^{*}$

2026 PhD Math Camp

Updated on August 18, 2026

$^{*}$All remaining errors are my own.
$^{\dagger}$Typesetting and visual design are informed by public mathematical lecture-note templates, including Gilles Castel’s lecture notes, rafisics’ lecture-notes template, and Jack’s Math Notes Template with Color Box.

1

<!-- page 2 -->

Contents

Introduction . . . 4

1 Bounds and Completeness of the Real Numbers . . . 5
1.1 Bounds, Maxima, and Minima . . . 5
1.2 Supremum and Infimum . . . 7
1.3 Completeness of the Real Numbers . . . 11

2 Euclidean Space, Convergence, and Compactness . . . 17
2.1 Euclidean Space and Norms . . . 17
2.2 Sequences and Convergence in $\mathbb{R}^n$ . . . 20
2.3 Open and Closed Sets . . . 22
2.4 Closure, Limit Points, and Boundary . . . 24
2.5 Cauchy Sequences and Completeness . . . 29
2.6 Compactness . . . 31
2.7 Connected and Convex Sets . . . 37

3 Limits and Continuous Mappings . . . 39
3.1 Limits of Mappings . . . 40
3.2 Continuous Mappings . . . 45
3.3 Continuity and the Topology of Euclidean Space . . . 49
3.4 Continuous Mappings on Compact Sets . . . 52
3.5 Semicontinuity and Existence . . . 55
3.6 Pointwise and Uniform Convergence of Functions . . . 58
3.7 Uniform Continuity and Connectedness . . . 61

4 One-Dimensional Calculus: A Refresher . . . 67
4.1 Derivatives and Linear Approximation . . . 67
4.2 Mean-Value Theorems, Monotonicity, and Convexity . . . 69
4.3 Taylor’s Theorem in One Variable . . . 75
4.4 The Fundamental Theorem of Calculus . . . 76

2

<!-- page 3 -->

5 Differential Calculus in Euclidean Space 78
5.1 Differentiability as Linear Approximation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 79
5.2 Jacobians and Partial Derivatives . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 83
5.3 Criteria for Differentiability . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 86
5.4 Directional Derivatives and the Gradient . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 92
5.5 The Chain Rule . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 95
5.6 Differentiable Curves and Tangent Directions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 97

6 Mean-Value Theorems and Higher-Order Approximation 101
6.1 Mean-Value Theorems and Estimates . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 101
6.2 Second and Higher-Order Derivatives . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 104
6.3 The Hessian and Symmetry of Second Derivatives . . . . . . . . . . . . . . . . . . . . . . . . . 105
6.4 Taylor’s Theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 106
6.5 Local Quadratic Approximation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 111

7 Fixed Points and Local Solvability 115
7.1 Lipschitz and Contraction Mappings . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 115
7.2 The Banach Fixed-Point Theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 117
7.3 The Inverse Function Theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 120
7.4 The Implicit Function Theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 124
7.5 Differentiating Implicit Functions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 128
7.6 Comparative Statics . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 129

8 Monotone Comparative Statics and Topkis’s Theorem 132
8.1 Order, Lattices, and Increasing Differences . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 132
8.2 Scalar Monotone Comparative Statics . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 134
8.3 Topkis’s Monotonicity Theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 136
8.4 Monotone Fixed Points and Tarski’s Theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . 140

9 Integration in Euclidean Space 143
9.1 Multiple and Iterated Integrals . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 144
9.2 Change of Variables . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 148
9.3 Parameter-Dependent Integrals . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 150
9.4 Differentiation Under the Integral Sign . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 151

References 155

3

<!-- page 4 -->

# Introduction

Analysis supplies the language for four questions that recur throughout economic models. Does a candidate object exist? Is it stable when primitives change? Can a nonlinear relation be replaced locally by a simpler approximation? When may a limit, derivative, or integral be moved through another operation? The results in these notes are organized around those questions rather than around analysis as an abstract subject in its own right.

Two ideas will appear repeatedly. The first is a global one. Completeness and compactness turn boundedness or approximation into existence: suprema exist, convergent subsequences can be extracted, continuous functions attain extrema, and suitable maps possess fixed points. The second is local. A differentiable map is well approximated by a linear map, and a twice differentiable function by a quadratic form. The inverse and implicit function theorems turn that local approximation into local solvability and comparative statics.

[Diagram: completeness and compactness $\rightarrow$ existence and attainment $\rightarrow$ fixed points and equilibrium; continuity and uniform control $\rightarrow$ linear and quadratic approximation $\rightarrow$ inverse/implicit maps and local statics; order and complementarity $\rightarrow$ Topkis and Tarski $\rightarrow$ integration and interchanging limits. Arrows connect these boxes.]

Figure 1: A roadmap for Part II. Global existence arguments, local approximation, order methods, and integration are developed separately but repeatedly reinforce one another.

The setting is deliberately finite dimensional. We work mainly in $\mathbb{R}^n$, where the geometry is visible and the strongest economic uses can be developed without the machinery of general topological vector spaces or measure theory. At the same time, several results are stated in a form that makes their later extensions recognizable. For example, uniform convergence is introduced before differentiation under an integral, semicontinuity before existence arguments in optimization, and order-theoretic fixed points alongside the differential approach to comparative statics.

The notation is consistent with Part I. Norms are written $\|\cdot\|$, $Df(a)$ denotes the derivative as a linear map, $J_f(a)$ its matrix in standard coordinates, and $\text{d}$ is used for the upright differential in expressions such as $\text{d}x$ and $\text{d}f$. Proofs are included when they reveal a reusable argument; examples are used to show how the hypotheses enter calculations.

4

<!-- page 5 -->

1 Bounds and Completeness of the Real Numbers

Throughout Part I, we used $\mathbb{R}$ as the scalar field without examining its order structure in any detail. For analysis, one additional property of the real numbers becomes fundamental: the real line has no “gaps.” This property is called completeness.

Before stating completeness precisely, we introduce the language of bounds. This will allow us to distinguish carefully between a set having an upper bound and actually having a largest element.

1.1 Bounds, Maxima, and Minima

Let

$$A \subseteq \mathbb{R}$$

be a nonempty set.

Definition 1.1 — Upper and Lower Bounds

A number $M \in \mathbb{R}$ is an upper bound of $A$ if

$$x \leq M$$
for every $x \in A$.

Similarly, a number $m \in \mathbb{R}$ is a lower bound of $A$ if

$$m \leq x$$
for every $x \in A$.

The set $A$ is said to be bounded above if it has an upper bound, bounded below if it has a lower bound, and bounded if it is bounded both above and below.

Bounds need not be unique. For example, if

$$A = [0, 1],$$

then every number $M \geq 1$ is an upper bound, and every number $m \leq 0$ is a lower bound.

A different question is whether one of the elements of the set itself is larger or smaller than all the others.

Definition 1.2 — Maximum and Minimum

Let $A \subseteq \mathbb{R}$ be nonempty.

An element $a^* \in A$ is the maximum of $A$ if

$$x \leq a^*$$
for every $x \in A$.

5

<!-- page 6 -->

We then write

$$a^* = \max A.$$

An element $a_* \in A$ is the **minimum** of $A$ if

$$a_* \leq x \quad \text{for every } x \in A.$$

We then write

$$a_* = \min A.$$

Notice the distinction. An upper bound of $A$ need not belong to $A$, but the maximum, if it exists, must be an element of $A$. Similarly, a lower bound need not belong to $A$, whereas the minimum must.

For example, consider

$$A = [0, 1).$$

The set is bounded since

$$0 \leq x \leq 1 \quad \text{for every } x \in A.$$

Moreover,

$$\min A = 0.$$

However, $A$ has no maximum. Indeed, for every $x \in A$,

$$x < \frac{x + 1}{2} < 1,$$

and therefore

$$\frac{x + 1}{2} \in A$$

is strictly larger than $x$. Thus no element of $A$ can be the largest element.

If a maximum or minimum exists, it is unique. For instance, if $a, b \in A$ are both maxima, then

$$a \leq b \quad \text{and} \quad b \leq a,$$

and therefore

$$a = b.$$

The example $[0, 1)$ shows that boundedness alone does not guarantee the existence of a maximum. Nevertheless, there is a clear sense in which 1 is the “upper edge” of this set. This motivates the next concept.

6

<!-- page 7 -->

1.2 Supremum and Infimum

Suppose that $A \subseteq \mathbb{R}$ is nonempty and bounded above. Among all upper bounds, we would like to identify the smallest one.

**Definition 1.3 — Supremum and Infimum**

Let $A \subseteq \mathbb{R}$ be nonempty.

A number $s \in \mathbb{R}$ is the supremum, or least upper bound, of $A$ if

$$x \leq s \quad \text{for every } x \in A,$$

and, for every $s' < s$, there exists $x \in A$ such that

$$s' < x.$$

We write

$$s = \sup A.$$

Similarly, a number $i \in \mathbb{R}$ is the infimum, or greatest lower bound, of $A$ if

$$i \leq x \quad \text{for every } x \in A,$$

and, for every $i' > i$, there exists $x \in A$ such that

$$x < i'.$$

We write

$$i = \inf A.$$

The first condition in the definition of the supremum says that $s$ is an upper bound. The second says that any number strictly smaller than $s$ fails to be an upper bound. Thus $s$ is the smallest upper bound.

Equivalently,

$$\sup A = \min \{M \in \mathbb{R} : x \leq M \text{ for every } x \in A\},$$

whenever this minimum exists. Similarly,

$$\inf A = \max \{m \in \mathbb{R} : m \leq x \text{ for every } x \in A\}.$$

It is often useful to express the second part of the definition using $\varepsilon$.

If

$$s = \sup A,$$

7

<!-- page 8 -->

then for every $\varepsilon > 0$, there exists some $x_{\varepsilon} \in A$ such that

$$s - \varepsilon < x_{\varepsilon} \leq s.$$

Indeed, $s - \varepsilon < s$, so $s - \varepsilon$ cannot be an upper bound of $A$.

Similarly, if

$$i = \inf A,$$

then for every $\varepsilon > 0$, there exists some $x_{\varepsilon} \in A$ such that

$$i \leq x_{\varepsilon} < i + \varepsilon.$$

Thus elements of $A$ can be found arbitrarily close to its supremum from below, and arbitrarily close to its infimum from above. This does not imply that the supremum or infimum belongs to the set.

The $\varepsilon$-characterization of the supremum and infimum has a useful sequential interpretation. Even when the extremal value is not attained, we can find points whose values approach it arbitrarily closely.

**Definition 1.4 — Maximizing and Minimizing Sequences**

Let

$$f : A \to \mathbb{R}.$$

Suppose the finite supremum

$$\sup_{x \in A} f(x)$$

exists. A sequence

$$\{x_k\} \subseteq A$$

is called a maximizing sequence for $f$ if

$$f(x_k) \to \sup_{x \in A} f(x).$$

Similarly, if the finite infimum $\inf_{x \in A} f(x)$ exists, a sequence

$$\{x_k\} \subseteq A$$

is called a minimizing sequence for $f$ if

$$f(x_k) \to \inf_{x \in A} f(x).$$

The existence of such sequences follows directly from the definition of supremum and infimum.

8

<!-- page 9 -->

**Proposition 1.5 — Existence of Optimizing Sequences**

Let
$$f : A \to \mathbb{R}, \quad A \neq \emptyset.$$
If $\sup_{x \in A} f(x)$ exists as a finite real number, then $f$ has a maximizing sequence. If $\inf_{x \in A} f(x)$ exists as a finite real number, then $f$ has a minimizing sequence.

**Proof**

Suppose first that the finite infimum exists, and set
$$m = \inf_{x \in A} f(x).$$
For every $k \in \mathbb{N}$, the defining property of the infimum gives some $x_k \in A$ such that
$$m \leq f(x_k) < m + \frac{1}{k}.$$
Hence
$$0 \leq f(x_k) - m < \frac{1}{k},$$
so
$$f(x_k) \to m.$$
Thus $\{x_k\}$ is a minimizing sequence.

The maximizing case is analogous: if
$$M = \sup_{x \in A} f(x),$$
choose $x_k \in A$ so that
$$M - \frac{1}{k} < f(x_k) \leq M.$$
Then
$$f(x_k) \to M.$$

**Remark 1.6 — Approximation versus Attainment**

An optimizing sequence need not converge, and even if it converges, its limit need not belong to the feasible set.

Thus the existence of a minimizing sequence is much weaker than the existence of a minimizer. What it guarantees is only that the infimum can be approached arbitrarily closely.

Later, compactness will supply convergent subsequences, while closedness and continuity will

9

<!-- page 10 -->

allow the limiting point to remain feasible and attain the limiting objective value.

Returning to

$$A = [0, 1),$$

we have

$$\inf A = 0, \quad \sup A = 1.$$

Since $0 \in A$,

$$\min A = \inf A = 0.$$

But since $1 \notin A$, there is no maximum, even though

$$\sup A = 1.$$

This gives the important distinction

a supremum is a bound, whereas a maximum is an attained bound.

If a maximum exists, however, it must coincide with the supremum.

***

**Proposition 1.7 — Maximum and Supremum**

Let $A \subseteq \mathbb{R}$ be nonempty.

If $\max A$ exists, then

$$\sup A = \max A.$$

Similarly, if $\min A$ exists, then

$$\inf A = \min A.$$

**Proof**

Suppose

$$a^* = \max A.$$

Since

$$x \leq a^* \quad \forall x \in A,$$

$a^*$ is an upper bound of $A$.

Now let $M$ be any upper bound of $A$. Since $a^* \in A$, we must have

$$a^* \leq M.$$

10

<!-- page 11 -->

Therefore $a^*$ is the smallest upper bound, so

$$a^* = \sup A.$$

The proof for the minimum and infimum is analogous.

We will frequently apply these concepts not directly to a set of numbers, but to the values taken by a function.

Let

$$f : A \to \mathbb{R}.$$

We use the notation

$$\sup_{x \in A} f(x) := \sup \{f(x) : x \in A\},$$

and similarly

$$\inf_{x \in A} f(x) := \inf \{f(x) : x \in A\}.$$

For example, if

$$f : (0, 1) \to \mathbb{R}, \quad f(x) = x,$$

then

$$\sup_{x \in (0,1)} f(x) = 1, \quad \inf_{x \in (0,1)} f(x) = 0,$$

but neither value is attained.

Thus

$$\sup_{x \in A} f(x)$$

and

$$\max_{x \in A} f(x)$$

are not interchangeable. Writing a maximum asserts the existence of some $x^* \in A$ such that

$$f(x^*) = \sup_{x \in A} f(x).$$

Later we will prove that continuity and compactness provide important conditions under which such an $x^*$ must exist.

### 1.3 Completeness of the Real Numbers

We have defined the supremum of a set, but we have not yet shown that it exists.

Suppose $A$ is nonempty and bounded above. There are upper bounds of $A$, but why must there be a smallest upper bound?

11

<!-- page 12 -->

The answer comes from the property that distinguishes the real numbers from an ordered field such as the rational numbers.

We take the usual algebraic and order properties of $\mathbb{R}$ as given. In addition, the real numbers satisfy the following completeness axiom.

**Theorem 1.8 — Completeness Axiom**

Let $X, Y \subseteq \mathbb{R}$ be nonempty sets such that

$$x \leq y \quad \text{for every } x \in X \text{ and every } y \in Y.$$

Then there exists a real number $c \in \mathbb{R}$ such that

$$x \leq c \leq y \quad \text{for every } x \in X \text{ and every } y \in Y.$$

In words, if one nonempty set lies entirely to the left of another nonempty set, then there is a real number separating them.

From theorem 1.8 we obtain the existence of suprema and infima.

**Theorem 1.9 — Least-Upper-Bound Principle**

Every nonempty subset of $\mathbb{R}$ that is bounded above has a unique supremum.

**Proof**

Let

$$A \subseteq \mathbb{R}$$

be nonempty and bounded above, and let

$$U = \{y \in \mathbb{R} : x \leq y \text{ for every } x \in A\}$$

be the set of all upper bounds of $A$.

Because $A$ is bounded above,

$$U \neq \emptyset.$$

Moreover, by the definition of an upper bound,

$$x \leq y \quad \text{for every } x \in A \text{ and every } y \in U.$$

By theorem 1.8, there exists $c \in \mathbb{R}$ such that

$$x \leq c \leq y \quad \forall x \in A, \quad \forall y \in U.$$

12

<!-- page 13 -->

The first inequality,
$$x \leq c \quad \forall x \in A,$$
shows that $c$ itself is an upper bound of $A$, so
$$c \in U.$$
The second inequality,
$$c \leq y \quad \forall y \in U,$$
shows that $c$ is the smallest element of the set of upper bounds.
Therefore
$$c = \sup A.$$
Uniqueness follows because a set cannot have two distinct least upper bounds.

The analogous result for infima follows immediately from theorem 1.9.

### Corollary 1.10 — Greatest-Lower-Bound Principle
Every nonempty subset of $\mathbb{R}$ that is bounded below has a unique infimum.

### Proof
Let $A \subseteq \mathbb{R}$ be nonempty and bounded below. Then
$$-A = \{-x : x \in A\}$$
is nonempty and bounded above. Hence
$$\sup(-A)$$
exists by the least-upper-bound principle.
Changing signs reverses inequalities, so
$$\inf A = -\sup(-A).$$
Therefore $\inf A$ exists and is unique.

The least-upper-bound principle is often itself used as the statement of completeness. The formulation above follows directly from the completeness axiom, and the two formulations are equivalent.
The importance of completeness is that it turns boundedness into an existence statement:
$$A \neq \emptyset, \quad A \text{ bounded above} \implies \sup A \in \mathbb{R}.$$

<!-- page 14 -->

Notice carefully what it does *not* say. It does not imply
$$\sup A \in A.$$
For example,
$$\sup(0, 1) = 1,$$
even though
$$1 \notin (0, 1).$$
Completeness guarantees the existence of the least upper bound as a real number; additional conditions are needed to guarantee that this bound is attained by an element of the set.
One useful consequence of completeness is the Archimedean property.

### Proposition 1.11 — Archimedean Property
The natural numbers are not bounded above in $\mathbb{R}$. In particular, for every $\varepsilon > 0$, there exists $n \in \mathbb{N}$ such that
$$0 < \frac{1}{n} < \varepsilon.$$

### Proof
Suppose, to the contrary, that $\mathbb{N}$ is bounded above. By the least-upper-bound principle,
$$s := \sup \mathbb{N}$$
exists.
Since
$$s - 1 < s,$$
the definition of the supremum implies that there exists $n \in \mathbb{N}$ such that
$$s - 1 < n \leq s.$$
It follows that
$$n + 1 > s.$$
But
$$n + 1 \in \mathbb{N},$$
contradicting the fact that $s$ is an upper bound of $\mathbb{N}$.
Thus $\mathbb{N}$ is not bounded above.

<!-- page 15 -->

Now let $\varepsilon > 0$. Since $\mathbb{N}$ is unbounded above, there exists $n \in \mathbb{N}$ such that
$$n > \frac{1}{\varepsilon}.$$
Therefore
$$0 < \frac{1}{n} < \varepsilon.$$
The consequence used repeatedly below is the scale $1/n$: for every $\varepsilon > 0$, some $1/n$ is smaller than $\varepsilon$.
The Archimedean property gives a supply of arbitrarily small positive lengths. Combined with completeness, it yields the shrinking-interval principle that underlies many existence arguments.

### Theorem 1.12 — Nested Interval Principle
Let
$$I_k = [a_k, b_k], \quad k = 1, 2, \dots,$$
be nonempty closed intervals satisfying
$$I_1 \supseteq I_2 \supseteq \dots$$
and
$$b_k - a_k \longrightarrow 0.$$
Then there is a unique point $c \in \mathbb{R}$ such that
$$c \in I_k \quad \text{for every } k.$$

### Proof
Set
$$A = \{a_k : k \geq 1\}, \quad B = \{b_k : k \geq 1\}.$$
Nestedness implies
$$a_m \leq b_n \quad \text{for every } m, n.$$
Indeed, if $m \leq n$, then $a_m \leq a_n \leq b_n$; if $m > n$, then $a_m \leq b_m \leq b_n$. By the completeness axiom there is a number $c$ satisfying
$$a_m \leq c \leq b_n \quad \text{for every } m, n.$$
Taking $m = n = k$ shows that $c \in I_k$ for every $k$.
If $c$ and $d$ both belonged to every interval, then
$$|c - d| \leq b_k - a_k \quad \text{for every } k.$$

<!-- page 16 -->

The right-hand side tends to zero, so $c = d$.

[Image: A diagram showing nested intervals $I_1 \supset I_2 \supset I_3 \supset I_4 \supset \dots$ all containing a common point $c$.]

Figure 2: Nested closed intervals whose lengths shrink to zero pin down a unique point. This is a geometric form of completeness.
This theorem turns a sequence of increasingly accurate bounds into a point. The same idea gives the one-dimensional subsequence theorem used later in $\mathbb{R}^n$.

### Theorem 1.13 — Bolzano–Weierstrass in $\mathbb{R}$
Every bounded sequence of real numbers has a convergent subsequence.

### Proof
Let $\{x_k\}$ be bounded, and choose a closed interval $I_1$ containing all of its terms. Bisect $I_1$. At least one of the two halves contains infinitely many terms of the sequence; call that half $I_2$.
Repeat the construction. We obtain nested closed intervals
$$I_1 \supseteq I_2 \supseteq \dots$$
such that $I_j$ contains infinitely many terms and
$$|I_j| = 2^{-(j-1)}|I_1| \longrightarrow 0.$$
By theorem 1.12, there is a unique
$$c \in \bigcap_{j=1}^{\infty} I_j.$$
Because each $I_j$ contains infinitely many terms, we may choose indices
$$n_1 < n_2 < \dots$$
with $x_{n_j} \in I_j$. Since both $x_{n_j}$ and $c$ lie in $I_j$,
$$|x_{n_j} - c| \leq |I_j| \longrightarrow 0.$$

<!-- page 17 -->

Thus $x_{n_j} \to c$.

## 2 Euclidean Space, Convergence, and Compactness
Passing from the real line to $\mathbb{R}^n$ changes the geometry more than the logic. Absolute value is replaced by a norm, intervals by balls, and a point can now be approached from many directions. The notions of convergence, closedness, completeness, and compactness nevertheless retain the same basic meaning.
We develop these ideas only as far as they are needed later for continuity, differentiation, and existence arguments.

### 2.1 Euclidean Space and Norms
Recall that
$$\mathbb{R}^n = \{x = (x_1, \dots, x_n) : x_i \in \mathbb{R}\}.$$
We think of an element $x \in \mathbb{R}^n$ interchangeably as a point or as a vector.
For
$$x = (x_1, \dots, x_n), \quad y = (y_1, \dots, y_n),$$
their usual inner product is
$$x \cdot y = \sum_{i=1}^n x_i y_i.$$
This induces the Euclidean norm
$$\|x\| = \sqrt{x \cdot x} = \left( \sum_{i=1}^n x_i^2 \right)^{1/2}.$$
More generally, it is useful to isolate the properties of a norm.

### Definition 2.1 — Norm
A norm on $\mathbb{R}^n$ is a function
$$\|\cdot\| : \mathbb{R}^n \to \mathbb{R}$$
such that, for every $x, y \in \mathbb{R}^n$ and $\lambda \in \mathbb{R}$,
$$\|x\| \geq 0, \quad \|x\| = 0 \iff x = 0,$$
$$\|\lambda x\| = |\lambda|\|x\|,$$

<!-- page 18 -->

and
$$\|x + y\| \leq \|x\| + \|y\|.$$
The last inequality is called the triangle inequality.
Unless otherwise stated, we will use the Euclidean norm
$$\|x\|_2 = \left( \sum_{i=1}^n x_i^2 \right)^{1/2}$$
and simply write it as $\|x\|$.
Two other commonly used norms are
$$\|x\|_1 = \sum_{i=1}^n |x_i|$$
and
$$\|x\|_\infty = \max_{1 \leq i \leq n} |x_i|.$$
These norms measure size differently, but the standard norms generate the same notion of closeness.
For example,
$$\|x\|_\infty \leq \|x\|_2 \leq \sqrt{n} \|x\|_\infty.$$
Indeed,
$$|x_i| \leq \left( \sum_{j=1}^n x_j^2 \right)^{1/2} = \|x\|_2$$
for every $i$, while
$$\|x\|_2^2 = \sum_{i=1}^n x_i^2 \leq n \|x\|_\infty^2.$$
Consequently,
$$x_k \to x \text{ in } \|\cdot\|_2 \iff x_k \to x \text{ in } \|\cdot\|_\infty.$$
The same conclusion holds for $\|\cdot\|_1$. We will work with the Euclidean norm throughout. The stronger statement that *any* two norms on $\mathbb{R}^n$ are equivalent is a finite-dimensional theorem whose usual proof uses compactness of the unit sphere; it is not needed at this stage.
The norm gives a natural notion of distance.

### Definition 2.2 — Euclidean Distance
For $x, y \in \mathbb{R}^n$, the Euclidean distance between $x$ and $y$ is
$$d(x, y) = \|x - y\|.$$

<!-- page 19 -->

[Image: A diagram showing three shapes in the $x_1, x_2$ plane: a diamond (labeled $\|x\|_1 \leq 1$), a circle (labeled $\|x\|_2 \leq 1$), and a square (labeled $\|x\|_\infty \leq 1$).]

Figure 3: The unit balls of three common norms in $\mathbb{R}^2$. Their shapes differ, but in finite dimensions they generate the same notion of convergence.
The triangle inequality for the norm gives
$$d(x, z) \leq d(x, y) + d(y, z).$$
Thus the familiar distance on the real line,
$$d(x, y) = |x - y|,$$
is simply the case $n = 1$.
For $a \in \mathbb{R}^n$ and $r > 0$, define the open ball
$$B_r(a) = \{x \in \mathbb{R}^n : \|x - a\| < r\},$$
and the closed ball
$$\overline{B}_r(a) = \{x \in \mathbb{R}^n : \|x - a\| \leq r\}.$$
A set $S \subseteq \mathbb{R}^n$ is called bounded if there exists $R > 0$ such that
$$S \subseteq B_R(0).$$
Equivalently, there exists $M < \infty$ such that
$$\|x\| \leq M \quad \forall x \in S.$$

<!-- page 20 -->

## 2.2 Sequences and Convergence in $\mathbb{R}^n$
A sequence in $\mathbb{R}^n$ is a collection
$$\{x_k\}_{k=1}^\infty, \quad x_k \in \mathbb{R}^n.$$
Write
$$x_k = (x_k^1, \dots, x_k^n).$$

### Definition 2.3 — Convergence of a Sequence
A sequence $\{x_k\} \subseteq \mathbb{R}^n$ converges to $a \in \mathbb{R}^n$ if
$$\|x_k - a\| \to 0 \quad \text{as } k \to \infty.$$
We then write
$$x_k \to a$$
or
$$\lim_{k \to \infty} x_k = a.$$
Equivalently, $x_k \to a$ if for every $\varepsilon > 0$, there exists $N \in \mathbb{N}$ such that
$$k \geq N \implies \|x_k - a\| < \varepsilon.$$
Thus convergence means that eventually every term of the sequence lies in every prescribed neighborhood of $a$.
A useful feature of Euclidean space is that convergence can be checked coordinate by coordinate.

### Proposition 2.4 — Coordinatewise Convergence
Let
$$x_k = (x_k^1, \dots, x_k^n), \quad a = (a_1, \dots, a_n).$$
Then
$$x_k \to a$$
if and only if
$$x_k^i \to a_i \quad \text{for every } i = 1, \dots, n.$$

### Proof
Suppose first that
$$x_k \to a.$$

<!-- page 21 -->

For each coordinate $i$,
$$|x_k^i - a_i| \leq \|x_k - a\|.$$
Therefore
$$\|x_k - a\| \to 0 \implies |x_k^i - a_i| \to 0.$$
Conversely, suppose
$$x_k^i \to a_i \quad \text{for every } i.$$
Then
$$\|x_k - a\| \leq \sqrt{n} \max_{1 \leq i \leq n} |x_k^i - a_i|.$$
Since there are only finitely many coordinates, the right-hand side converges to zero. Hence
$$x_k \to a.$$
This simple result allows many facts about sequences in $\mathbb{R}^n$ to be reduced to familiar one-dimensional facts.
For example, limits are unique. If
$$x_k \to a \quad \text{and} \quad x_k \to b,$$
then
$$\|a - b\| \leq \|a - x_k\| + \|x_k - b\| \to 0,$$
so
$$a = b.$$
Also, every convergent sequence is bounded. Indeed, if
$$x_k \to a,$$
then for sufficiently large $k$,
$$\|x_k - a\| < 1,$$
and hence
$$\|x_k\| \leq \|a\| + 1.$$
The finitely many remaining terms can be bounded separately.
A subsequence of $\{x_k\}$ is a sequence of the form
$$\{x_{k_j}\}_{j=1}^\infty,$$
where
$$k_1 < k_2 < \dots.$$

<!-- page 22 -->

If
$$x_k \to a,$$
then every subsequence also converges to $a$.

## 2.3 Open and Closed Sets
We now use balls to describe the local geometry of subsets of $\mathbb{R}^n$.

### Definition 2.5 — Open and Closed Sets
A set $U \subseteq \mathbb{R}^n$ is open if for every $x \in U$, there exists $\delta > 0$ such that
$$B_\delta(x) \subseteq U.$$
A set $F \subseteq \mathbb{R}^n$ is closed if its complement
$$\mathbb{R}^n \setminus F$$
is open.
Thus an open set contains a small ball around each of its points.
For example, every open ball
$$B_r(a)$$
is open. To see this, let
$$x \in B_r(a).$$
Then
$$\|x - a\| < r.$$
Choose
$$0 < \delta < r - \|x - a\|.$$
If
$$y \in B_\delta(x),$$
then by the triangle inequality,
$$\|y - a\| \leq \|y - x\| + \|x - a\| < \delta + \|x - a\| < r.$$
Hence
$$B_\delta(x) \subseteq B_r(a).$$
Similarly, the closed ball
$$\overline{B}_r(a)$$

<!-- page 23 -->

is closed.
The terminology "open" and "closed" should not be interpreted as opposites in the ordinary linguistic sense. A set can be neither open nor closed, and the sets
$$\emptyset \quad \text{and} \quad \mathbb{R}^n$$
are both open and closed.
Open and closed sets behave well under the basic operations on sets.

### Proposition 2.6 — Operations on Open and Closed Sets
The following properties hold in $\mathbb{R}^n$.
(1) The union of any collection of open sets is open.
(2) The intersection of finitely many open sets is open.
(3) The intersection of any collection of closed sets is closed.
(4) The union of finitely many closed sets is closed.

### Proof
Suppose
$$U = \bigcup_{\alpha \in A} U_\alpha,$$
where every $U_\alpha$ is open. If $x \in U$, then
$$x \in U_{\alpha_0}$$
for some $\alpha_0$. Since $U_{\alpha_0}$ is open, there exists $\delta > 0$ such that
$$B_\delta(x) \subseteq U_{\alpha_0} \subseteq U.$$
Hence $U$ is open.
Now suppose
$$U = \bigcap_{i=1}^m U_i,$$
where $U_1, \dots, U_m$ are open. If $x \in U$, choose $\delta_i > 0$ such that
$$B_{\delta_i}(x) \subseteq U_i.$$
Set
$$\delta = \min_{1 \leq i \leq m} \delta_i.$$

<!-- page 24 -->

Then
$$B_\delta(x) \subseteq \bigcap_{i=1}^m U_i,$$
so $U$ is open.
The statements about closed sets follow from De Morgan's laws by taking complements.
Sometimes we work inside a subset
$$D \subseteq \mathbb{R}^n$$
rather than in all of $\mathbb{R}^n$.

### Definition 2.7 — Relative Open and Closed Sets
Let $E \subseteq D \subseteq \mathbb{R}^n$.
The set $E$ is open relative to $D$ if there exists an open set $U \subseteq \mathbb{R}^n$ such that
$$E = D \cap U.$$
Similarly, $E$ is closed relative to $D$ if there exists a closed set $F \subseteq \mathbb{R}^n$ such that
$$E = D \cap F.$$
For example,
$$[0, 1)$$
is not open in $\mathbb{R}$, but it is open relative to
$$[0, 2],$$
since
$$[0, 1) = [0, 2] \cap (-1, 1).$$
Relative openness will become useful whenever the domain of a function is itself a constrained subset of Euclidean space.

## 2.4 Closure, Limit Points, and Boundary
We now introduce several related ways of describing how a point is situated relative to a set.
Let
$$S \subseteq \mathbb{R}^n, \quad a \in \mathbb{R}^n.$$

<!-- page 25 -->

**Definition 2.8 — Interior, Limit, and Boundary Points**

The point $a$ is an **interior point** of $S$ if there exists $\delta > 0$ such that
$$B_\delta(a) \subseteq S.$$

The point $a$ is a **limit point** or **accumulation point** of $S$ if
$$B_\delta(a) \cap (S \setminus \{a\}) \neq \emptyset$$
for every $\delta > 0$.

The point $a$ is a **boundary point** of $S$ if every ball around $a$ contains both a point of $S$ and a point outside $S$:
$$B_\delta(a) \cap S \neq \emptyset$$
and
$$B_\delta(a) \cap S^c \neq \emptyset$$
for every $\delta > 0$.

We denote the set of interior points of $S$ by
$$S^\circ,$$
and the set of boundary points by
$$\partial S.$$
The **closure** of $S$, denoted by
$$\overline{S},$$
is the union of $S$ and all of its limit points.

These concepts have particularly useful sequential characterizations.

**Proposition 2.9 — Sequential Characterizations of Closure and Limit Points**

Let $S \subseteq \mathbb{R}^n$ and $a \in \mathbb{R}^n$.
(1) $a$ is a limit point of $S$ if and only if there exists a sequence
$$x_k \in S \setminus \{a\}$$
such that
$$x_k \to a.$$
(2)
$$a \in \overline{S}$$
if and only if there exists a sequence
$$x_k \in S$$
such that
$$x_k \to a.$$

<!-- page 26 -->

**Proof**

We prove (1).
Suppose first that $a$ is a limit point of $S$. For each $k \in \mathbb{N}$,
$$B_{1/k}(a) \cap (S \setminus \{a\}) \neq \emptyset.$$
Choose
$$x_k \in B_{1/k}(a) \cap (S \setminus \{a\}).$$
Then
$$\|x_k - a\| < \frac{1}{k},$$
and therefore
$$x_k \to a.$$
Conversely, suppose there exists
$$x_k \in S \setminus \{a\}$$
such that
$$x_k \to a.$$
Given any $\delta > 0$, for sufficiently large $k$,
$$\|x_k - a\| < \delta.$$
Therefore
$$x_k \in B_\delta(a) \cap (S \setminus \{a\}),$$
so $a$ is a limit point.

For (2), suppose first that $a \in \overline{S}$. If $a \in S$, the constant sequence $x_k = a$ lies in $S$ and converges to $a$. If $a \notin S$, then $a$ is a limit point of $S$, so part (1) supplies a sequence in $S$ converging to $a$.
Conversely, suppose $x_k \in S$ and $x_k \to a$. If $a \in S$, then $a \in \overline{S}$ immediately. If $a \notin S$, then every $x_k$ is different from $a$, and the argument in part (1) shows that $a$ is a limit point of $S$. Hence again $a \in \overline{S}$.

The sequential characterization gives an extremely useful test for closedness.

<!-- page 27 -->

**Proposition 2.10 — Sequential Characterization of Closed Sets**

A set $F \subseteq \mathbb{R}^n$ is closed if and only if
$$x_k \in F, \quad x_k \to x$$
imply
$$x \in F.$$

Thus:
$$F \text{ is closed} \iff F \text{ contains the limits of all convergent sequences in } F.$$
Equivalently,
$$F \text{ is closed} \iff \overline{F} = F.$$

The closure can also be characterized as the smallest closed set containing $S$:
$$\overline{S} = \bigcap \{F \subseteq \mathbb{R}^n : F \text{ is closed and } S \subseteq F\}.$$

For example,
$$\overline{(0, 1)} = [0, 1],$$
and
$$\partial(0, 1) = \{0, 1\}.$$
Similarly, for an open ball,
$$\overline{B_r(a)} = \overline{B_r(a)},$$
and
$$\partial B_r(a) = \{x : \|x - a\| = r\}.$$

**Definition 2.11 — Distance from a Point to a Set**

Let $A \subseteq \mathbb{R}^n$ be nonempty. The **distance from $x$ to $A$** is
$$\text{dist}(x, A) := \inf_{a \in A} \|x - a\|.$$
The infimum need not be attained unless additional assumptions are imposed on $A$.

The distance function packages several elementary topological facts into one continuous object.

<!-- page 28 -->

**Proposition 2.12 — Distance Functions Are Lipschitz**

For every nonempty $A \subseteq \mathbb{R}^n$ and every $x, y \in \mathbb{R}^n$,
$$|\text{dist}(x, A) - \text{dist}(y, A)| \leq \|x - y\|.$$
Consequently $x \mapsto \text{dist}(x, A)$ is continuous. Moreover,
$$\overline{A} = \{x \in \mathbb{R}^n : \text{dist}(x, A) = 0\}.$$

**Proof**

For any $a \in A$, the triangle inequality gives
$$\|x - a\| \leq \|x - y\| + \|y - a\|.$$
Taking the infimum over $a \in A$ yields
$$\text{dist}(x, A) \leq \|x - y\| + \text{dist}(y, A).$$
Interchanging $x$ and $y$ gives the reverse estimate, and the Lipschitz bound follows.
If $x \in \overline{A}$, then every ball around $x$ meets $A$, so points of $A$ can be found arbitrarily close to $x$ and $\text{dist}(x, A) = 0$. Conversely, if the distance is zero, for every $k$ there is $a_k \in A$ with
$$\|x - a_k\| < \frac{1}{k}.$$
Thus $a_k \to x$, and the sequential characterization of closure gives $x \in \overline{A}$.

[Figure 4: Distance to a set is defined by an infimum. For the closed set drawn here the distance is attained at a nearest point $a^* \in A$; attainment is not part of the definition in general.]

<!-- page 29 -->

**2.5 Cauchy Sequences and Completeness**

The definition of convergence refers to the limit $a$. In many applications, however, we want to determine whether a sequence converges before we know what the limit is.
The Cauchy criterion solves this problem by comparing the terms of the sequence with each other.

**Definition 2.13 — Cauchy Sequence**

A sequence
$$\{x_k\} \subseteq \mathbb{R}^n$$
is a **Cauchy sequence** if for every $\varepsilon > 0$ there exists $N \in \mathbb{N}$ such that
$$m, k \geq N \implies \|x_m - x_k\| < \varepsilon.$$

Thus the terms of a Cauchy sequence eventually become arbitrarily close to one another.
An equivalent formulation, used frequently in elementary treatments, is that for every $\varepsilon > 0$ there exists $N$ such that
$$k \geq N \implies \|x_k - x_N\| < \varepsilon.$$
The two formulations are equivalent up to replacing $\varepsilon$ by $\varepsilon/2$.
Every convergent sequence is Cauchy.
Indeed, if
$$x_k \to a,$$
then for sufficiently large $m, k$,
$$\|x_m - a\| < \frac{\varepsilon}{2}, \quad \|x_k - a\| < \frac{\varepsilon}{2},$$
and hence
$$\|x_m - x_k\| \leq \|x_m - a\| + \|x_k - a\| < \varepsilon.$$
The converse is much more important. It depends on completeness.

**Definition 2.14 — Complete Normed Space**

A normed space is called **complete** if every Cauchy sequence in the space converges to a point of the space.

The completeness of the real numbers from the previous section implies the completeness of Euclidean space.
We first recall how completeness gives convergence of a real Cauchy sequence.
Let
$$\{x_k\} \subseteq \mathbb{R}$$

<!-- page 30 -->

be Cauchy. A Cauchy sequence is bounded, so for every $N$ the tail
$$\{x_k : k \geq N\}$$
is bounded. Define
$$a_N = \inf_{k \geq N} x_k, \quad b_N = \sup_{k \geq N} x_k.$$
These numbers exist by completeness of $\mathbb{R}$. Moreover,
$$a_N \leq a_{N+1} \leq b_{N+1} \leq b_N.$$
The Cauchy property implies that the diameter of the tail becomes arbitrarily small. More precisely, for every $\varepsilon > 0$, there exists $N$ such that
$$b_N - a_N \leq \varepsilon.$$
Now define
$$L := \sup_{N \geq 1} a_N.$$
The sequence $\{a_N\}$ is bounded above, for example by $b_1$, so $L$ exists. For every $N$, the number $b_N$ is an upper bound for all $a_j$, and hence
$$a_N \leq L \leq b_N.$$
If $k \geq N$, then also
$$a_N \leq x_k \leq b_N.$$
Therefore
$$|x_k - L| \leq b_N - a_N.$$
Since the right-hand side can be made arbitrarily small, we conclude that
$$x_k \to L.$$
Thus every real Cauchy sequence converges.
We can now pass coordinatewise to $\mathbb{R}^n$.

**Theorem 2.15 — Completeness of Euclidean Space**

Every Cauchy sequence in $\mathbb{R}^n$ converges. Hence
$$\mathbb{R}^n$$
is complete.

<!-- page 31 -->

**Proof**

Let
$$x_k = (x_k^1, \dots, x_k^n)$$
be Cauchy in $\mathbb{R}^n$.
For each coordinate $i$,
$$|x_m^i - x_k^i| \leq \|x_m - x_k\|.$$
Hence
$$\{x_k^i\}$$
is a Cauchy sequence in $\mathbb{R}$.
By completeness of $\mathbb{R}$, there exists $a_i \in \mathbb{R}$ such that
$$x_k^i \to a_i.$$
Set
$$a = (a_1, \dots, a_n).$$
By proposition 2.4,
$$x_k \to a.$$
Therefore every Cauchy sequence in $\mathbb{R}^n$ converges.

A useful consequence is that a closed subset of $\mathbb{R}^n$ is itself complete.
Indeed, let
$$F \subseteq \mathbb{R}^n$$
be closed and let $\{x_k\} \subseteq F$ be Cauchy. Since $\mathbb{R}^n$ is complete,
$$x_k \to x$$
for some $x \in \mathbb{R}^n$. Since $F$ is closed,
$$x \in F.$$

**2.6 Compactness**

Completeness concerns whether Cauchy sequences have limits. Compactness is a different global finiteness property. In Euclidean space it can be expressed equivalently in terms of convergent subsequences or finite subcovers of open covers.
We begin with one of the fundamental facts about Euclidean space.

<!-- page 32 -->

**Theorem 2.16 — Bolzano-Weierstrass**

Every bounded sequence in $\mathbb{R}^n$ has a convergent subsequence.

**Proof**

Let
$$x_k = (x_k^1, \dots, x_k^n)$$
be bounded.
Then each coordinate sequence
$$\{x_k^i\}_{k=1}^\infty$$
is bounded in $\mathbb{R}$.
By theorem 1.13, the first coordinate sequence has a convergent subsequence
$$x_{k_j}^1.$$
Restrict attention to this subsequence. Its second coordinate sequence is still bounded, so it has a further subsequence for which the second coordinate converges.
Continuing finitely many times, we obtain a subsequence
$$\{x_{k_j}\}$$
for which every coordinate converges:
$$x_{k_j}^i \to a_i, \quad i = 1, \dots, n.$$
Therefore
$$x_{k_j} \to (a_1, \dots, a_n)$$
by coordinatewise convergence.

The proof is a finite diagonal extraction: apply the real theorem one coordinate at a time, retaining a subsequence at each step.
We now introduce compactness in its open-cover form.

**Definition 2.17 — Compactness**

Let $K \subseteq \mathbb{R}^n$.
A collection of open sets
$$\{U_\alpha\}_{\alpha \in A}$$

<!-- page 33 -->

is an **open cover** of $K$ if
$$K \subseteq \bigcup_{\alpha \in A} U_\alpha.$$
The set $K$ is **compact** if every open cover of $K$ contains a finite subcover. That is, whenever
$$K \subseteq \bigcup_{\alpha \in A} U_\alpha,$$
there exist
$$\alpha_1, \dots, \alpha_m$$
such that
$$K \subseteq \bigcup_{i=1}^m U_{\alpha_i}.$$

The open-cover definition becomes concrete in Euclidean space through the following characterization.

**Theorem 2.18 — Heine-Borel**

A set
$$K \subseteq \mathbb{R}^n$$
is compact if and only if it is closed and bounded.

**Proof**

If $K = \emptyset$, then $K$ is compact, closed, and bounded, so the result is immediate. Assume henceforth that $K$ is nonempty.
We first prove necessity.
Suppose $K$ is compact.
To see that $K$ is bounded, consider the open cover
$$K \subseteq \bigcup_{m=1}^\infty B_m(0).$$
Compactness gives a finite subcover. Since the balls are nested, there is some $M$ such that
$$K \subseteq B_M(0).$$
Thus $K$ is bounded.
We next show that $K$ is closed. Let
$$a \notin K.$$

<!-- page 34 -->

For each $x \in K$, define
$$r_x = \frac{1}{2}\|x - a\|.$$
The balls
$$\{B_{r_x}(x) : x \in K\}$$
form an open cover of $K$. By compactness, there exist $x_1, \dots, x_m \in K$ such that
$$K \subseteq \bigcup_{i=1}^m B_{r_{x_i}}(x_i).$$
Let
$$\delta = \min_{1 \leq i \leq m} r_{x_i} > 0.$$
If
$$y \in B_{r_{x_i}}(x_i),$$
then
$$\|y - a\| \geq \|x_i - a\| - \|y - x_i\| > 2r_{x_i} - r_{x_i} = r_{x_i} \geq \delta.$$
Hence
$$B_\delta(a) \cap K = \emptyset.$$
Therefore $K^c$ is open and $K$ is closed.
Now suppose conversely that $K$ is closed and bounded, and let
$$\{U_\alpha\}_{\alpha \in A}$$
be an open cover of $K$.
We first claim that there exists $\delta > 0$ such that for every $x \in K$, some $U_\alpha$ contains the entire ball
$$B_\delta(x).$$
Suppose not. Then for every $m \in \mathbb{N}$ there exists $x_m \in K$ such that
$$B_{1/m}(x_m)$$
is not contained in any member of the cover.
Because $K$ is bounded, the sequence $\{x_m\}$ is bounded. By the Bolzano-Weierstrass theorem, it has a subsequence
$$x_{m_j} \to x.$$
Because $K$ is closed,
$$x \in K.$$

<!-- page 35 -->

Choose $U_{\alpha_0}$ containing $x$. Since $U_{\alpha_0}$ is open, there exists $r > 0$ such that
$$B_r(x) \subseteq U_{\alpha_0}.$$
For sufficiently large $j$,
$$\|x_{m_j} - x\| < \frac{r}{2} \quad \text{and} \quad \frac{1}{m_j} < \frac{r}{2}.$$
Therefore
$$B_{1/m_j}(x_{m_j}) \subseteq B_r(x) \subseteq U_{\alpha_0},$$
a contradiction.
Thus such a $\delta > 0$ exists.
We next show that $K$ can be covered by finitely many balls of radius $\delta/2$.
Choose $x_1 \in K$. If
$$K \subseteq B_{\delta/2}(x_1),$$
we are done. Otherwise choose
$$x_2 \in K \setminus B_{\delta/2}(x_1).$$
Continue in this way.
If this process did not terminate, we would obtain a bounded sequence $\{x_j\} \subseteq K$ satisfying
$$\|x_i - x_j\| \geq \frac{\delta}{2} \quad (i \neq j).$$
Such a sequence cannot have a convergent subsequence, contradicting Bolzano-Weierstrass.
Hence for some finite collection
$$x_1, \dots, x_N \in K,$$
$$K \subseteq \bigcup_{i=1}^N B_{\delta/2}(x_i).$$
For each $i$, choose $U_{\alpha_i}$ such that
$$B_\delta(x_i) \subseteq U_{\alpha_i}.$$
Then
$$K \subseteq \bigcup_{i=1}^N U_{\alpha_i}.$$
Thus the original open cover has a finite subcover, so $K$ is compact.

Two features of compactness are visible in the proof. A compact set cannot extend arbitrarily far from the origin, and it cannot contain an infinite sequence whose points remain a fixed positive distance apart. The second fact is the sequential content behind Bolzano-Weierstrass.
The open-cover definition also has an equivalent sequential formulation.

<!-- page 36 -->

**Corollary 2.19 — Sequential Compactness**

For
$$K \subseteq \mathbb{R}^n,$$
the following are equivalent:
(1) $K$ is compact;
(2) every sequence
$$\{x_k\} \subseteq K$$
has a convergent subsequence whose limit belongs to $K$;
(3) $K$ is closed and bounded.

Indeed, if $K$ is closed and bounded, every sequence in $K$ is bounded, so Bolzano-Weierstrass gives a convergent subsequence. Closedness guarantees that its limit remains in $K$.
Conversely, suppose every sequence in $K$ has a convergent subsequence with limit in $K$. If $K$ were unbounded, we could choose
$$x_k \in K$$
with
$$\|x_k\| > k,$$
which cannot have a convergent subsequence.
If $K$ were not closed, there would exist a sequence
$$x_k \in K$$
converging to some
$$x \notin K.$$
Every subsequence would have the same limit $x$, contradicting sequential compactness.
Thus $K$ is closed and bounded, hence compact.
A particularly useful consequence is the following.

**Proposition 2.20 — Closed Subsets of Compact Sets**

A closed subset of a compact set is compact.

Indeed, if
$$F \subseteq K,$$
where $F$ is closed and $K$ is compact, then $K$ is bounded, so $F$ is bounded. Hence $F$ is closed and bounded, and therefore compact by theorem 2.18.

<!-- page 37 -->

For example, every closed ball
$$\overline{B}_r(a)$$
is compact.
By contrast, the open ball
$$B_r(a)$$
is bounded but not closed, and therefore is not compact.

**Remark 2.21 — Compactness and the Finite Intersection Property**
There is a useful dual way to read the open-cover definition. A family $\{F_\alpha\}$ of closed subsets of a compact set $K$ has the **finite intersection property** if every finite subfamily has nonempty intersection. Compactness is equivalent to the statement that every such family satisfies
$$\bigcap_\alpha F_\alpha \neq \emptyset.$$
The equivalence follows by taking complements. In economic existence proofs this formulation is often convenient: rather than covering a feasible set by open sets, one constructs increasingly restrictive closed conditions and shows that every finite collection of them can be satisfied simultaneously.

### 2.7 Connected and Convex Sets
Compactness is a global notion describing whether a set can "escape" or develop missing limit points. Connectedness describes a different global property: whether a set can be separated into two disjoint pieces.
Because we have not yet developed continuity of mappings, we begin with the purely set-theoretic definition.

**Definition 2.22 — Connected Set**
A set
$$S \subseteq \mathbb{R}^n$$
is **connected** if there do not exist two nonempty disjoint sets $U, V \subseteq S$, both open relative to $S$, such that
$$S = U \cup V.$$
If such $U$ and $V$ exist, $S$ is called **disconnected**.

The real intervals provide the basic example.

<!-- page 38 -->

**Proposition 2.23 — Intervals Are Connected**
Every interval in $\mathbb{R}$ is connected.

**Proof**
Let $I \subseteq \mathbb{R}$ be an interval. Suppose, to the contrary, that
$$I = U \cup V,$$
where $U$ and $V$ are nonempty, disjoint, and open relative to $I$. Choose
$$u \in U, \quad v \in V.$$
After relabeling if necessary, assume $u < v$.
Consider
$$A = U \cap [u, v].$$
The set $A$ is nonempty and bounded above by $v$, so the least-upper-bound principle gives
$$c := \sup A.$$
Since $I$ is an interval and $u, v \in I$, we have $[u, v] \subseteq I$, and therefore $c \in I$.
If $c \in U$, then $c \neq v$ because $v \in V$ and $U \cap V = \emptyset$. Hence $c < v$. Relative openness of $U$ gives $\varepsilon > 0$ such that
$$(c - \varepsilon, c + \varepsilon) \cap I \subseteq U.$$
After shrinking $\varepsilon$ if necessary, choose
$$c < z < \min\{c + \varepsilon, v\}.$$
Then $z \in U \cap [u, v] = A$, contradicting $c = \sup A$.
If $c \in V$, relative openness of $V$ gives $\varepsilon > 0$ such that
$$(c - \varepsilon, c + \varepsilon) \cap I \subseteq V.$$
By the defining property of the supremum, there exists $a \in A$ such that
$$c - \varepsilon < a \leq c.$$
Because $A \subseteq U$ and $c \in V$, we have $a \neq c$, so $a < c$. Therefore $a \in (c - \varepsilon, c + \varepsilon) \cap I \subseteq V$. But $a \in A \subseteq U$, contradicting $U \cap V = \emptyset$.
Thus no such separation exists, and $I$ is connected.

A particularly important geometric class of subsets of Euclidean space is given by convex sets.

<!-- page 39 -->

**Definition 2.24 — Convex Set**
A set
$$C \subseteq \mathbb{R}^n$$
is **convex** if for every
$$x, y \in C$$
and every
$$t \in [0, 1],$$
we have
$$(1 - t)x + ty \in C.$$
Thus a set is convex if the line segment joining any two of its points lies entirely inside the set.
The line segment joining $x$ and $y$ will be denoted
$$[x, y] = \{(1 - t)x + ty : t \in [0, 1]\}.$$
For example, balls, boxes, half-spaces, and affine subspaces are convex. A circle or sphere is not convex, because the line segment joining two points on the sphere generally passes through its interior.
At this stage, convexity is simply a geometric property. Once continuity and paths have been introduced, we will prove that convex sets are path connected, and hence connected; see proposition 3.30.
Compactness and connectedness will reappear immediately: continuous mappings preserve both, and compactness will turn local continuity into global conclusions.

## 3 Limits and Continuous Mappings
We now study mappings
$$f : D \subseteq \mathbb{R}^n \to \mathbb{R}^m.$$
The definitions of limit and continuity are the familiar one-dimensional ones with absolute values replaced by norms. What changes is the geometry: in several variables, $x$ can approach a point $a$ along infinitely many curves and directions. For that reason, sequential tests and norm estimates become especially effective.

<!-- page 40 -->

### 3.1 Limits of Mappings
Let
$$D \subseteq \mathbb{R}^n, \quad f : D \to \mathbb{R}^m.$$
To discuss the behavior of $f(x)$ as $x$ approaches $a$, the point $a$ need not itself belong to $D$. We only require that points of $D$ can approach $a$ arbitrarily closely.
Recall that $a \in \mathbb{R}^n$ is a limit point of $D$ if every neighborhood of $a$ contains a point of
$$D \setminus \{a\}.$$

**Definition 3.1 — Limit of a Mapping**
Let $a$ be a limit point of $D$ and let $b \in \mathbb{R}^m$.
We say that
$$f(x) \to b \quad \text{as } x \to a$$
if, for every $\varepsilon > 0$, there exists $\delta > 0$ such that
$$x \in D, \quad 0 < \|x - a\| < \delta$$
imply
$$\|f(x) - b\| < \varepsilon.$$
We write
$$\lim_{x \to a} f(x) = b.$$
Thus
$$\lim_{x \to a} f(x) = b$$
means that the values of $f(x)$ can be made arbitrarily close to $b$ by taking $x$ sufficiently close to $a$.
Notice that the value $f(a)$ plays no role in this definition. In fact, $f(a)$ need not even be defined.
Geometrically, for every ball
$$B_\varepsilon(b) \subseteq \mathbb{R}^m,$$
there must be a sufficiently small ball around $a$ such that
$$f(B_\delta(a) \cap (D \setminus \{a\})) \subseteq B_\varepsilon(b).$$
As in one dimension, a limit, if it exists, is unique.

<!-- page 41 -->

**Proposition 3.2 — Uniqueness of Limits**
If
$$\lim_{x \to a} f(x) = b \quad \text{and} \quad \lim_{x \to a} f(x) = c,$$
then
$$b = c.$$

**Proof**
Suppose
$$b \neq c,$$
and set
$$\varepsilon = \frac{1}{3}\|b - c\| > 0.$$
The two limit assumptions give radii $\delta_b, \delta_c > 0$ such that
$$0 < \|x - a\| < \delta_b \implies \|f(x) - b\| < \varepsilon,$$
and
$$0 < \|x - a\| < \delta_c \implies \|f(x) - c\| < \varepsilon.$$
Since $a$ is a limit point of $D$, there exists $x \in D$ with
$$0 < \|x - a\| < \min\{\delta_b, \delta_c\}.$$
For this $x$,
$$\|b - c\| \leq \|b - f(x)\| + \|f(x) - c\| < 2\varepsilon = \frac{2}{3}\|b - c\|,$$
a contradiction.

The $\varepsilon$-$\delta$ definition is fundamental, but in Euclidean space there is an equivalent characterization that is often much easier to use.

**Theorem 3.3 — Sequential Characterization of Limits**
Let $a$ be a limit point of $D$. Then
$$\lim_{x \to a} f(x) = b$$
if and only if, for every sequence
$$\{x_k\} \subseteq D \setminus \{a\}$$
such that
$$x_k \to a,$$
we have
$$f(x_k) \to b.$$

<!-- page 42 -->

**Proof**
Suppose first that
$$\lim_{x \to a} f(x) = b,$$
and let
$$x_k \to a.$$
Given $\varepsilon > 0$, choose $\delta > 0$ from the definition of the limit. For sufficiently large $k$,
$$0 < \|x_k - a\| < \delta,$$
and therefore
$$\|f(x_k) - b\| < \varepsilon.$$
Hence
$$f(x_k) \to b.$$
Conversely, suppose the sequential condition holds but
$$\lim_{x \to a} f(x) \neq b.$$
Then there exists some $\varepsilon_0 > 0$ such that for every $\delta > 0$ there is an $x \in D$ satisfying
$$0 < \|x - a\| < \delta$$
but
$$\|f(x) - b\| \geq \varepsilon_0.$$
For each $k \in \mathbb{N}$, choose $x_k \in D$ such that
$$0 < \|x_k - a\| < \frac{1}{k}$$
and
$$\|f(x_k) - b\| \geq \varepsilon_0.$$
Then
$$x_k \to a,$$
but
$$f(x_k) \not\to b,$$
contradicting the sequential condition.

<!-- page 43 -->

This criterion is particularly useful in several variables. To show that a limit *does not* exist, it is enough to find two sequences approaching the same point along which the function has different limiting behavior.
For example, consider
$$f(x, y) = \frac{xy}{x^2 + y^2}, \quad (x, y) \neq (0, 0).$$
Along the line
$$y = kx,$$
we have
$$f(x, kx) = \frac{k}{1 + k^2}.$$
Thus different values of $k$ give different limiting values as
$$(x, kx) \to (0, 0).$$
Therefore
$$\lim_{(x, y) \to (0, 0)} \frac{xy}{x^2 + y^2}$$
does not exist.
There is, however, an important warning.
Checking only straight lines is sufficient to *disprove* the existence of a limit, but it is generally not sufficient to *prove* that a limit exists.
A more subtle example is
$$g(x, y) = \frac{x^2y}{x^4 + y^2}, \quad (x, y) \neq (0, 0).$$
Along any straight line through the origin,
$$(x, y) = (\alpha t, \beta t),$$
one finds
$$g(\alpha t, \beta t) \to 0.$$
Thus checking every straight line would suggest the candidate limit 0. However, along the parabola
$$y = x^2,$$
we have
$$g(x, x^2) = \frac{1}{2}$$
for every $x \neq 0$. Hence
$$\lim_{(x, y) \to (0, 0)} g(x, y)$$
does not exist.

<!-- page 44 -->

Thus a genuine multivariable limit must be independent of *every* possible way of approaching the point.

[Figure 5: A coordinate plane showing a point (0,0). A straight line labeled $y=x$ and a parabola labeled $y=x^2$ both pass through (0,0). An arrow along the line and an arrow along the parabola both point to (0,0), with a label "same destination, different approach".]

Figure 5: In several variables there are infinitely many ways to approach the same point. Agreement along straight lines alone does not control curved paths.
On the other hand, estimates can often establish a limit directly. Consider
$$h(x, y) = (x + y) \sin\left(\frac{y}{x^2 + y^2}\right), \quad (x, y) \neq (0, 0).$$
Since
$$|\sin t| \leq 1,$$
we have
$$|h(x, y)| \leq |x| + |y|.$$
Therefore
$$(x, y) \to (0, 0) \implies h(x, y) \to 0.$$
For vector-valued mappings, limits can be checked coordinate by coordinate.

**Proposition 3.4 — Coordinatewise Limits**
Let
$$f = (f_1, \dots, f_m) : D \to \mathbb{R}^m$$
and
$$b = (b_1, \dots, b_m).$$
Then
$$\lim_{x \to a} f(x) = b$$
if and only if
$$\lim_{x \to a} f_i(x) = b_i, \quad i = 1, \dots, m.$$

<!-- page 45 -->

**Proof**
If
$$f(x) \to b,$$
then
$$|f_i(x) - b_i| \leq \|f(x) - b\|,$$
so every coordinate converges.
Conversely,
$$\|f(x) - b\| \leq \sqrt{m} \max_{1 \leq i \leq m} |f_i(x) - b_i|.$$
Since there are only finitely many coordinates, convergence of every coordinate implies
$$\|f(x) - b\| \to 0.$$
The usual algebra of limits follows immediately. For example, if
$$f(x) \to b, \quad g(x) \to c,$$
then
$$\lambda f(x) + \mu g(x) \to \lambda b + \mu c.$$
For real-valued functions,
$$f(x)g(x) \to bc,$$
and if $c \neq 0$,
$$\frac{f(x)}{g(x)} \to \frac{b}{c}.$$
These statements can be proved either directly or by applying the corresponding results for convergent sequences.

### 3.2 Continuous Mappings
A limit compares the values of a mapping near a point with some candidate value $b$. Continuity requires this candidate value to be the actual value of the mapping at the point.

**Definition 3.5 — Continuity at a Point**
Let
$$f : D \subseteq \mathbb{R}^n \to \mathbb{R}^m$$
and let $a \in D$.

<!-- page 46 -->

The mapping $f$ is **continuous at $a$** if, for every $\varepsilon > 0$, there exists $\delta > 0$ such that
$$x \in D, \quad \|x - a\| < \delta$$
imply
$$\|f(x) - f(a)\| < \varepsilon.$$
The mapping is **continuous on $D$** if it is continuous at every point of $D$.

If $a$ is a limit point of $D$, this is equivalent to
$$\lim_{x \to a} f(x) = f(a).$$
The direct definition has the advantage that it also applies to isolated points of the domain. If $a$ is isolated in $D$, then every mapping
$$f : D \to \mathbb{R}^m$$
is automatically continuous at $a$.
The sequential characterization of limits gives an equally useful criterion for continuity.

**Theorem 3.6 — Sequential Characterization of Continuity**
A mapping
$$f : D \to \mathbb{R}^m$$
is continuous at $a \in D$ if and only if
$$x_k \in D, \quad x_k \to a$$
imply
$$f(x_k) \to f(a).$$
Thus a continuous mapping preserves limits of convergent sequences:
$$x_k \to a \implies f(x_k) \to f(a).$$
For a vector-valued mapping,
$$f = (f_1, \dots, f_m),$$
continuity is again coordinatewise.

<!-- page 47 -->

**Proposition 3.7 — Coordinatewise Continuity**
The mapping
$$f = (f_1, \dots, f_m) : D \to \mathbb{R}^m$$
is continuous at $a$ if and only if every coordinate function
$$f_i : D \to \mathbb{R}$$
is continuous at $a$.

The elementary operations preserve continuity. If $f$ and $g$ are continuous real-valued functions, then
$$f + g, \quad fg, \quad \lambda f$$
are continuous, and
$$\frac{f}{g}$$
is continuous at every point where
$$g \neq 0.$$
Likewise, sums and scalar multiples of continuous vector-valued mappings are continuous.
For real-valued functions, continuity also preserves strict inequalities locally.

**Proposition 3.8 — Local Sign Preservation**
Let $f : D \to \mathbb{R}$ be continuous at $a \in D$. If $f(a) > 0$, then there exists $\delta > 0$ such that
$$x \in D, \quad \|x - a\| < \delta \implies f(x) > 0.$$
The analogous statement holds when $f(a) < 0$.

**Proof**
Suppose $f(a) > 0$ and take
$$\varepsilon = \frac{f(a)}{2}.$$
Continuity gives $\delta > 0$ such that
$$\|x - a\| < \delta \implies |f(x) - f(a)| < \frac{f(a)}{2}.$$
Hence
$$f(x) > \frac{f(a)}{2} > 0.$$

<!-- page 48 -->

One of the most important closure properties is composition.

**Theorem 3.9 — Continuity of Compositions**
Let
$$g : D \subseteq \mathbb{R}^n \to U \subseteq \mathbb{R}^m$$
and
$$f : U \to \mathbb{R}^p.$$
If $g$ is continuous at $a \in D$ and $f$ is continuous at
$$g(a),$$
then
$$f \circ g$$
is continuous at $a$.

**Proof**
Let
$$x_k \to a.$$
Since $g$ is continuous at $a$,
$$g(x_k) \to g(a).$$
Since $f$ is continuous at $g(a)$,
$$f(g(x_k)) \to f(g(a)).$$
Therefore
$$(f \circ g)(x_k) \to (f \circ g)(a),$$
and the sequential criterion implies that
$$f \circ g$$
is continuous at $a$.

This theorem makes it unnecessary to return to the $\varepsilon$-$\delta$ definition every time we encounter a new function.
For example, the coordinate projections
$$\pi_i : \mathbb{R}^n \to \mathbb{R}, \quad \pi_i(x_1, \dots, x_n) = x_i,$$
are continuous. It follows from the algebra of continuous functions and composition that every

<!-- page 49 -->

polynomial
$$p : \mathbb{R}^n \to \mathbb{R}$$
is continuous.
Similarly,
$$x \mapsto \|x\|$$
is continuous, since the reverse triangle inequality gives
$$\|\|x\| - \|y\|\| \leq \|x - y\|.$$
More generally, for fixed $a \in \mathbb{R}^n$, the distance function
$$x \mapsto \|x - a\|$$
is continuous.

### 3.3 Continuity and the Topology of Euclidean Space
The $\varepsilon$-$\delta$ definition describes continuity locally: points sufficiently close to $a$ are mapped sufficiently close to $f(a)$.
There is an equivalent formulation that describes continuity in terms of open sets. It is one of the main links between analysis and topology.
Recall that if
$$f : D \to \mathbb{R}^m$$
and
$$A \subseteq \mathbb{R}^m,$$
the inverse image or preimage of $A$ is
$$f^{-1}(A) = \{x \in D : f(x) \in A\}.$$
Notice that $f^{-1}(A)$ is a subset of the domain $D$. Consequently, openness and closedness below are understood relative to $D$.

**Theorem 3.10 — Topological Characterization of Continuity**
Let
$$f : D \subseteq \mathbb{R}^n \to \mathbb{R}^m.$$
The following are equivalent:
(1) $f$ is continuous on $D$;

<!-- page 50 -->

(2) for every open set
$$U \subseteq \mathbb{R}^m,$$
the inverse image
$$f^{-1}(U)$$
is open relative to $D$;
(3) for every closed set
$$F \subseteq \mathbb{R}^m,$$
the inverse image
$$f^{-1}(F)$$
is closed relative to $D$.

**Proof**
Suppose first that $f$ is continuous and let
$$U \subseteq \mathbb{R}^m$$
be open.
Take
$$a \in f^{-1}(U).$$
Then
$$f(a) \in U.$$
Since $U$ is open, there exists $\varepsilon > 0$ such that
$$B_\varepsilon(f(a)) \subseteq U.$$
By continuity of $f$ at $a$, there exists $\delta > 0$ such that
$$x \in D, \quad \|x - a\| < \delta$$
imply
$$f(x) \in B_\varepsilon(f(a)) \subseteq U.$$
Hence
$$B_\delta(a) \cap D \subseteq f^{-1}(U).$$
Thus $f^{-1}(U)$ is open relative to $D$.
Conversely, suppose inverse images of open sets are open relative to $D$. Fix $a \in D$ and $\varepsilon > 0$.
The set
$$B_\varepsilon(f(a))$$

<!-- page 51 -->

is open, so
$$f^{-1}(B_\varepsilon(f(a)))$$
is open relative to $D$ and contains $a$. Therefore there exists $\delta > 0$ such that
$$B_\delta(a) \cap D \subseteq f^{-1}(B_\varepsilon(f(a))).$$
Hence
$$x \in D, \quad \|x - a\| < \delta$$
imply
$$\|f(x) - f(a)\| < \varepsilon.$$
Thus $f$ is continuous at $a$.
The equivalence with inverse images of closed sets follows from
$$f^{-1}(A^c) = D \setminus f^{-1}(A)$$
and the equivalence between openness and closedness under complements.

Continuity is naturally expressed through *inverse images*, not images.
A continuous mapping does not generally send open sets to open sets, nor does it generally send closed sets to closed sets.
The theorem gives a convenient way to recognize many important sets as open or closed.
Suppose
$$g : D \to \mathbb{R}$$
is continuous. Then
$$\{x \in D : g(x) < c\} = g^{-1}((-\infty, c))$$
is open relative to $D$, while
$$\{x \in D : g(x) \leq c\} = g^{-1}((-\infty, c])$$
is closed relative to $D$.
Similarly,
$$\{x \in D : g(x) = c\} = g^{-1}(\{c\})$$
is closed relative to $D$.
For example, since
$$x \mapsto \|x - a\|$$
is continuous,
$$B_r(a) = \{x : \|x - a\| < r\}$$

<!-- page 52 -->

is open,
$$\overline{B}_r(a) = \{x : \|x - a\| \leq r\}$$
is closed, and the sphere
$$S_r(a) = \{x : \|x - a\| = r\}$$
is closed.
This gives a second way of obtaining facts about open and closed sets that we previously proved directly from the definitions.

### 3.4 Continuous Mappings on Compact Sets
Continuity is a local property: its definition concerns the behavior of a mapping near one point.
Compactness allows us to turn these local properties into global ones.
The first fundamental result is that continuous mappings preserve compactness.

**Theorem 3.11 — Continuous Images of Compact Sets**
Let
$$K \subseteq \mathbb{R}^n$$
be compact and let
$$f : K \to \mathbb{R}^m$$
be continuous. Then
$$f(K)$$
is compact.

**Proof**
Let
$$\{y_k\} \subseteq f(K)$$
be any sequence. Choose $x_k \in K$ such that
$$f(x_k) = y_k.$$
Since $K$ is compact, corollary 2.19 gives a subsequence
$$x_{k_j} \to x \quad \text{for some } x \in K.$$
By continuity,
$$y_{k_j} = f(x_{k_j}) \to f(x) \in f(K).$$

<!-- page 53 -->

Thus every sequence in $f(K)$ has a subsequence converging to a point of $f(K)$. By corollary 2.19, $f(K)$ is compact.

Since compact subsets of Euclidean space are bounded, we immediately obtain:

**Corollary 3.12 — Boundedness on Compact Sets**
If
$$K \subseteq \mathbb{R}^n$$
is compact and
$$f : K \to \mathbb{R}^m$$
is continuous, then $f$ is bounded on $K$.
That is, there exists $M < \infty$ such that
$$\|f(x)\| \leq M \quad \forall x \in K.$$

For real-valued functions, compactness yields something stronger: the bounds are actually attained.

**Theorem 3.13 — Extreme Value Theorem**
Let
$$K \subseteq \mathbb{R}^n$$
be nonempty and compact, and let
$$f : K \to \mathbb{R}$$
be continuous.
Then there exist points
$$x_{\min}, x_{\max} \in K$$
such that
$$f(x_{\min}) \leq f(x) \leq f(x_{\max}) \quad \forall x \in K.$$
Equivalently,
$$f(x_{\max}) = \max_{x \in K} f(x), \quad f(x_{\min}) = \min_{x \in K} f(x).$$

**Proof**
Since $f$ is continuous on the compact set $K$, corollary 3.12 shows that $f$ is bounded. Hence
$$M := \sup_{x \in K} f(x)$$

<!-- page 54 -->

exists by completeness of $\mathbb{R}$.
For each $k \in \mathbb{N}$, the defining property of the supremum gives a point $x_k \in K$ such that
$$M - \frac{1}{k} < f(x_k) \leq M.$$
Thus
$$f(x_k) \to M.$$
Compactness of $K$ gives a subsequence
$$x_{k_j} \to x^* \quad \text{for some } x^* \in K.$$
By continuity,
$$f(x_{k_j}) \to f(x^*).$$
The same subsequence also satisfies $f(x_{k_j}) \to M$, so uniqueness of limits implies
$$f(x^*) = M.$$
Hence
$$f(x^*) = \max_{x \in K} f(x).$$
The minimum is obtained by the same argument using
$$m := \inf_{x \in K} f(x).$$

The proof is worth reading as a chain of earlier results. Continuity sends the compact set $K$ to a compact, hence bounded, subset of $\mathbb{R}$; completeness gives its supremum and infimum; compactness then supplies convergent maximizing and minimizing subsequences, and continuity passes their limits through $f$.
The distinction is important. On the open interval
$$K = (0, 1),$$
the continuous function
$$f(x) = x$$
satisfies
$$\sup_{x \in (0,1)} f(x) = 1,$$
but there is no
$$x_{\max} \in (0, 1)$$
for which
$$f(x_{\max}) = 1.$$

<!-- page 55 -->

Similarly,
$$f(x) = \frac{1}{x}$$
is continuous on $(0, 1)$ but is not even bounded there.
Thus continuity alone does not give global boundedness or attainment. Compactness of the domain is the crucial additional ingredient.

### 3.5 Semicontinuity and Existence
Continuity is stronger than is needed for many existence arguments. When the objective is being maximized, it is enough to rule out sudden upward jumps along nearby sequences; for minimization the corresponding requirement rules out sudden downward jumps. These one-sided notions are called semicontinuity.

**Definition 3.14 — Upper and Lower Semicontinuity**
Let $f : D \to \mathbb{R}$ and $a \in D$.
The function $f$ is **upper semicontinuous at $a$** if, for every $\varepsilon > 0$, there exists $\delta > 0$ such that
$$x \in D, \quad \|x - a\| < \delta \implies f(x) < f(a) + \varepsilon.$$
It is **lower semicontinuous at $a$** if, for every $\varepsilon > 0$, there exists $\delta > 0$ such that
$$x \in D, \quad \|x - a\| < \delta \implies f(x) > f(a) - \varepsilon.$$
The function is upper or lower semicontinuous on $D$ if the corresponding property holds at every point.

Upper semicontinuity permits a value at a point to sit above nearby values, but not below them by a fixed amount. Lower semicontinuity permits the mirror-image behavior. A function is continuous exactly when it is both upper and lower semicontinuous.
The level-set formulation is often more useful in applications.

**Proposition 3.15 — Semicontinuity and Level Sets**
For $f : D \to \mathbb{R}$:
(1) $f$ is upper semicontinuous if and only if every superlevel set
$$\{x \in D : f(x) \geq c\}$$
is closed relative to $D$;

<!-- page 56 -->

(2) $f$ is lower semicontinuous if and only if every sublevel set
$$\{x \in D : f(x) \leq c\}$$
is closed relative to $D$.

The reason semicontinuity matters in economics is that it preserves the part of Weierstrass's theorem appropriate for optimization.

**Theorem 3.16 — Semicontinuous Extreme-Value Theorem**
Let $K \subseteq \mathbb{R}^n$ be nonempty and compact.
(1) If $f : K \to \mathbb{R}$ is upper semicontinuous, then $f$ attains a maximum on $K$.
(2) If $f : K \to \mathbb{R}$ is lower semicontinuous, then $f$ attains a minimum on $K$.

**Proof**
We prove the statement for an upper semicontinuous function $f$.
First we show that $f$ is bounded above on $K$. For each $x \in K$, upper semicontinuity with $\varepsilon = 1$ gives $\delta_x > 0$ such that
$$y \in K, \quad \|y - x\| < \delta_x \implies f(y) < f(x) + 1.$$
The ambient open balls $\{B_{\delta_x}(x) : x \in K\}$ cover $K$. Compactness gives a finite subcover centered at
$$x_1, \dots, x_N.$$
Therefore every $y \in K$ belongs to some $B_{\delta_{x_i}}(x_i)$ and hence
$$f(y) < \max_{1 \leq i \leq N} (f(x_i) + 1).$$
Thus $f$ is bounded above, so
$$M := \sup_{x \in K} f(x)$$
is a finite real number.
Choose a maximizing sequence $\{x_k\} \subseteq K$ satisfying
$$M - \frac{1}{k} < f(x_k) \leq M.$$
Since $K$ is compact, some subsequence $x_{k_j}$ converges to a point $x^* \in K$.

<!-- page 57 -->

We claim that $f(x^*) = M$. If instead $f(x^*) < M$, choose $\varepsilon > 0$ such that
$$f(x^*) + \varepsilon < M.$$
Upper semicontinuity at $x^*$ gives a relative neighborhood $V$ of $x^*$ in $K$ on which
$$f(x) < f(x^*) + \varepsilon < M.$$
For all sufficiently large $j$, however, $x_{k_j} \in V$, while
$$f(x_{k_j}) > M - \frac{1}{k_j} \to M.$$
For large enough $j$ these two inequalities are incompatible. Hence
$$f(x^*) = M,$$
so $f$ attains its maximum.
If $f$ is lower semicontinuous, then $-f$ is upper semicontinuous. Applying the first part to $-f$ shows that $f$ attains its minimum.

**Example 3.17 — A Discontinuous Objective with an Attained Maximum**
Define $f : [-1, 1] \to \mathbb{R}$ by
$$f(x) = \begin{cases} 1, & x = 0, \\ 0, & x \neq 0. \end{cases}$$
The function is not continuous at 0, but it is upper semicontinuous. Its maximum is attained at 0. This simple example shows why upper semicontinuity, rather than full continuity, is the natural one-sided condition for maximization.

[Figure 6: Upper semicontinuity allows an isolated upward jump. Such a jump does not threaten existence of a maximizer on a compact domain.]

<!-- page 58 -->

### 3.6 Pointwise and Uniform Convergence of Functions
Later we will pass limits through integrals and derivatives. For sequences of functions, the way convergence is measured matters.

**Definition 3.18 — Pointwise and Uniform Convergence**
Let $f_k : D \to \mathbb{R}^m$ and $f : D \to \mathbb{R}^m$.
The sequence $f_k$ converges **pointwise** to $f$ on $D$ if, for every fixed $x \in D$,
$$f_k(x) \to f(x).$$
It converges **uniformly** to $f$ on $D$ if, for every $\varepsilon > 0$, there exists $N$ such that
$$k \geq N \implies \|f_k(x) - f(x)\| < \varepsilon \quad \text{for every } x \in D.$$
Equivalently,
$$\sup_{x \in D} \|f_k(x) - f(x)\| \to 0.$$

The order of the quantifiers is the distinction. Under pointwise convergence, the index $N$ may depend on $x$; under uniform convergence, one $N$ works over the whole domain. When the functions are bounded, this is exactly convergence in the sup norm
$$\|g\|_\infty := \sup_{x \in D} \|g(x)\| : \quad f_k \to f \text{ uniformly} \iff \|f_k - f\|_\infty \to 0.$$
Geometrically, uniform convergence means that, for every $\varepsilon > 0$, the entire graph of $f_k$ eventually lies inside the same $\varepsilon$-tube around the graph of $f$.

**Example 3.19 — Pointwise but Not Uniform Convergence**
On $D = [0, 1]$, let
$$f_k(x) = x^k.$$
For every fixed $x < 1$, we have $x^k \to 0$, while $f_k(1) = 1$ for every $k$. Thus the pointwise limit is
$$f(x) = \begin{cases} 0, & 0 \leq x < 1, \\ 1, & x = 1. \end{cases}$$
The convergence cannot be uniform: each $f_k$ is continuous, whereas the pointwise limit is discontinuous. More directly,
$$\sup_{x \in [0,1]} |f_k(x) - f(x)| = 1$$
for every $k$.

<!-- page 59 -->

[Figure 7: The sequence $f_k(x) = x^k$ converges pointwise on $[0, 1]$, but the convergence is not uniform. The discrepancy is squeezed into an increasingly thin neighborhood of $x = 1$ without becoming uniformly small.]

A useful way to recognize uniform convergence is to avoid guessing the limit first and instead ask whether the sequence is uniformly Cauchy.

**Theorem 3.20 — Uniform Cauchy Criterion**
A sequence $f_k : D \to \mathbb{R}^m$ converges uniformly on $D$ if and only if, for every $\varepsilon > 0$, there exists $N$ such that
$$k, \ell \geq N \implies \|f_k(x) - f_\ell(x)\| < \varepsilon \quad \text{for every } x \in D.$$

**Proof**
Suppose first that $f_k \to f$ uniformly. Given $\varepsilon > 0$, choose $N$ such that
$$\|f_k(x) - f(x)\| < \frac{\varepsilon}{2} \quad \text{for every } x \in D$$
whenever $k \geq N$. Then, for $k, \ell \geq N$,
$$\|f_k(x) - f_\ell(x)\| \leq \|f_k(x) - f(x)\| + \|f_\ell(x) - f(x)\| < \varepsilon$$
for every $x \in D$.
Conversely, suppose the uniform Cauchy condition holds. For each fixed $x \in D$, the sequence $\{f_k(x)\}$ is Cauchy in the complete space $\mathbb{R}^m$, so there is a point $f(x) \in \mathbb{R}^m$ such that
$$f_k(x) \to f(x).$$
Fix $\varepsilon > 0$ and choose $N$ from the uniform Cauchy condition with $\varepsilon/2$ in place of $\varepsilon$. Thus, for

<!-- page 60 -->

$$k, \ell \geq N,$$
$$\|f_k(x) - f_\ell(x)\| < \frac{\varepsilon}{2} \quad \text{for every } x \in D.$$
Fix $k \geq N$ and let $\ell \to \infty$. Continuity of the norm gives
$$\|f_k(x) - f(x)\| \leq \frac{\varepsilon}{2} < \varepsilon \quad \text{for every } x \in D.$$
The same index $N$ works for every $x$, so $f_k \to f$ uniformly.

**Theorem 3.21 — Uniform Limit of Continuous Functions**
Suppose each $f_k : D \to \mathbb{R}^m$ is continuous and $f_k \to f$ uniformly on $D$. Then $f$ is continuous on $D$.

**Proof**
Fix $a \in D$ and $\varepsilon > 0$. Choose $N$ so that
$$\|f_N(x) - f(x)\| < \frac{\varepsilon}{3} \quad \text{for every } x \in D.$$
Continuity of $f_N$ at $a$ gives $\delta > 0$ such that, for $x \in D$,
$$\|x - a\| < \delta \implies \|f_N(x) - f_N(a)\| < \frac{\varepsilon}{3}.$$
Then
$$\|f(x) - f(a)\| \leq \|f(x) - f_N(x)\| + \|f_N(x) - f_N(a)\| + \|f_N(a) - f(a)\|$$
$$< \varepsilon.$$

Pointwise convergence alone does not preserve all the operations we would like to perform.

**Example 3.22 — A Moving Spike**
For $k \geq 2$ and $x \in [0, 1]$, define
$$f_k(x) = k \max\{1 - k|x - 1/k|, 0\}.$$
Each $f_k$ is continuous. For every fixed $x \in [0, 1]$, eventually $x$ lies outside the shrinking support of the spike, so
$$f_k(x) \to 0.$$

<!-- page 61 -->

The convergence is not uniform, since
$$\sup_{x \in [0,1]} f_k(x) = k.$$
Moreover, each graph is a triangle of base $2/k$ and height $k$, so
$$\int_0^1 f_k(x) \, dx = 1 \quad \text{for every } k,$$
while the pointwise limit has integral 0. Thus pointwise convergence by itself does not justify interchanging a limit and an integral.

The two examples isolate the role of uniformity. Pointwise convergence controls each $x$ separately; uniform convergence controls the whole domain at once. That stronger control is why continuity survives a uniform limit and why, later, uniform convergence will allow limits to pass through a Riemann integral.

### 3.7 Uniform Continuity and Connectedness

The Extreme Value Theorem is one global consequence of continuity on a compact set. Another is uniform continuity.
Continuity at a point $a$ says that for every $\varepsilon > 0$, there exists a $\delta > 0$ that may depend on both $\varepsilon$ and the point $a$:
$$\delta = \delta(\varepsilon, a).$$
Uniform continuity requires a single $\delta$ to work simultaneously at every point of the domain.

**Definition 3.23 — Uniform Continuity**
A mapping
$$f : D \subseteq \mathbb{R}^n \to \mathbb{R}^m$$
is **uniformly continuous** on $D$ if for every $\varepsilon > 0$ there exists $\delta > 0$ such that, for all $x, y \in D$,
$$\|x - y\| < \delta$$
implies
$$\|f(x) - f(y)\| < \varepsilon.$$

The difference in the order of the quantifiers is essential.
Ordinary continuity says
$$\forall a \in D \quad \forall \varepsilon > 0 \quad \exists \delta > 0 \quad \dots,$$
where $\delta$ may depend on $a$.

<!-- page 62 -->

Uniform continuity says
$$\forall \varepsilon > 0 \quad \exists \delta > 0 \quad \forall x, y \in D \quad \dots.$$
Every uniformly continuous mapping is continuous, but the converse need not hold.
For example,
$$f(x) = \frac{1}{x}$$
is continuous on
$$(0, 1),$$
but is not uniformly continuous there.
Compactness eliminates this problem.

**Theorem 3.24 — Uniform Continuity on Compact Sets**
Let
$$K \subseteq \mathbb{R}^n$$
be compact. If
$$f : K \to \mathbb{R}^m$$
is continuous, then $f$ is uniformly continuous on $K$.

**Proof**
Suppose, to the contrary, that $f$ is not uniformly continuous.
Then there exists $\varepsilon_0 > 0$ such that for every $k \in \mathbb{N}$ there exist
$$x_k, y_k \in K$$
satisfying
$$\|x_k - y_k\| < \frac{1}{k}$$
but
$$\|f(x_k) - f(y_k)\| \geq \varepsilon_0.$$
Since $K$ is compact, the sequence $\{x_k\}$ has a convergent subsequence
$$x_{k_j} \to x$$
for some
$$x \in K.$$
Moreover,
$$\|y_{k_j} - x\| \leq \|y_{k_j} - x_{k_j}\| + \|x_{k_j} - x\|.$$

<!-- page 63 -->

The right-hand side tends to zero, so
$$y_{k_j} \to x.$$
By continuity of $f$,
$$f(x_{k_j}) \to f(x) \quad \text{and} \quad f(y_{k_j}) \to f(x).$$
Therefore
$$\|f(x_{k_j}) - f(y_{k_j})\| \to 0,$$
contradicting
$$\|f(x_{k_j}) - f(y_{k_j})\| \geq \varepsilon_0.$$
Hence $f$ is uniformly continuous.

We now return to connectedness.
Recall that a set
$$D \subseteq \mathbb{R}^n$$
is connected if it cannot be written as the union of two disjoint, nonempty sets that are open relative to $D$.
Continuity preserves this global property.

**Theorem 3.25 — Continuous Images of Connected Sets**
Let
$$D \subseteq \mathbb{R}^n$$
be connected and let
$$f : D \to \mathbb{R}^m$$
be continuous. Then
$$f(D)$$
is connected.

**Proof**
Suppose, to the contrary, that $f(D)$ is disconnected. Then there exist nonempty disjoint sets
$$U, V \subseteq f(D),$$
both open relative to $f(D)$, such that
$$f(D) = U \cup V.$$

<!-- page 64 -->

Because $U$ and $V$ are open relative to $f(D)$, there exist open sets $O_U, O_V \subseteq \mathbb{R}^m$ such that
$$U = f(D) \cap O_U, \quad V = f(D) \cap O_V.$$
Hence
$$f^{-1}(U) = f^{-1}(O_U), \quad f^{-1}(V) = f^{-1}(O_V),$$
and continuity of $f$ implies that both sets are open relative to $D$.
They are disjoint, nonempty, and
$$D = f^{-1}(U) \cup f^{-1}(V).$$
Thus $D$ is disconnected, contradicting the hypothesis.

Connected subsets of the real line have a particularly simple form.

**Proposition 3.26 — Connected Subsets of the Real Line**
A subset
$$I \subseteq \mathbb{R}$$
is connected if and only if it is an interval, possibly consisting of a single point.

**Proof**
By proposition 2.23, every interval is connected.
Conversely, suppose $I$ is connected and let
$$a, b \in I, \quad a < b.$$
If there were some $c \in (a, b)$ with $c \notin I$, then
$$I \cap (-\infty, c) \quad \text{and} \quad I \cap (c, \infty)$$
would be two nonempty, disjoint sets, both open relative to $I$, whose union is $I$. This would contradict connectedness.
Therefore every point between any two points of $I$ also belongs to $I$. Hence $I$ is an interval.

Combining this fact with the preceding theorem gives a general intermediate-value result.

<!-- page 65 -->

**Corollary 3.27 — Intermediate Value Principle**
Let
$$D \subseteq \mathbb{R}^n$$
be connected and let
$$f : D \to \mathbb{R}$$
be continuous.
If
$$a, b \in D$$
and $c$ lies between $f(a)$ and $f(b)$, then there exists
$$x \in D$$
such that
$$f(x) = c.$$

Indeed, $f(D)$ is connected and therefore is an interval. Since it contains $f(a)$ and $f(b)$, it must contain every value between them.
Finally, continuity allows us to formulate a stronger geometric notion of connectedness.

**Definition 3.28 — Path Connectedness**
A set
$$D \subseteq \mathbb{R}^n$$
is path connected if for every $x, y \in D$ there exists a continuous mapping
$$\gamma : [0, 1] \to D$$
such that
$$\gamma(0) = x, \quad \gamma(1) = y.$$
The mapping $\gamma$ is called a path from $x$ to $y$.

Path connectedness implies connectedness.

**Proposition 3.29 — Path Connectedness Implies Connectedness**
Every path-connected subset of $\mathbb{R}^n$ is connected.

<!-- page 66 -->

**Proof**
Suppose that $D$ is path connected but disconnected. Then
$$D = U \cup V,$$
where $U$ and $V$ are nonempty, disjoint, and open relative to $D$.
Choose
$$x \in U, \quad y \in V.$$
Since $D$ is path connected, there exists a continuous path
$$\gamma : [0, 1] \to D$$
with
$$\gamma(0) = x, \quad \gamma(1) = y.$$
Because $U$ and $V$ are open relative to $D$, write
$$U = D \cap O_U, \quad V = D \cap O_V,$$
with $O_U, O_V$ open in $\mathbb{R}^n$. Since $\gamma(t) \in D$,
$$\gamma^{-1}(U) = \gamma^{-1}(O_U), \quad \gamma^{-1}(V) = \gamma^{-1}(O_V).$$
Continuity of $\gamma$ therefore implies that these inverse images are open relative to $[0, 1]$. Thus
$$\gamma^{-1}(U) \quad \text{and} \quad \gamma^{-1}(V)$$
are nonempty, disjoint, relatively open subsets of $[0, 1]$ whose union is $[0, 1]$.
This contradicts the connectedness of the interval $[0, 1]$.

**Proposition 3.30 — Convex Sets Are Path Connected**
Every convex subset of $\mathbb{R}^n$ is path connected, and therefore connected.

**Proof**
Let $C \subseteq \mathbb{R}^n$ be convex and let $x, y \in C$. Define
$$\gamma : [0, 1] \to C, \quad \gamma(t) = (1 - t)x + ty.$$

<!-- page 67 -->

Convexity guarantees that $\gamma(t) \in C$ for every $t \in [0, 1]$. Moreover,
$$\|\gamma(t) - \gamma(s)\| = |t - s| \|y - x\|,$$
so $\gamma$ is continuous. Finally,
$$\gamma(0) = x, \quad \gamma(1) = y.$$
Thus $C$ is path connected. By proposition 3.29, it is connected.

Therefore
$$\text{convex} \implies \text{path connected} \implies \text{connected}.$$

An open connected subset of $\mathbb{R}^n$ is often called a domain.
The compact-image and connected-image theorems are the two global continuity results used most often below.

### 4 One-Dimensional Calculus: A Refresher

Before differentiating mappings $f : \mathbb{R}^n \to \mathbb{R}^m$, recall what a derivative means in one dimension. The number $f'(a)$ is more than the slope of a tangent line: multiplication by $f'(a)$ gives the first-order change in the function. This interpretation, together with the mean-value theorem, Taylor's theorem, and the Fundamental Theorem of Calculus, is what carries over to several variables.

### 4.1 Derivatives and Linear Approximation

Let $I \subseteq \mathbb{R}$ be an interval and let $a$ be an interior point of $I$.

**Definition 4.1 — Derivative**
A function
$$f : I \to \mathbb{R}$$
is differentiable at $a$ if the limit
$$f'(a) = \lim_{h \to 0} \frac{f(a + h) - f(a)}{h}$$
exists.

The definition can be rewritten in the form that is most useful later. Define
$$r(h) := f(a + h) - f(a) - f'(a)h.$$

<!-- page 68 -->

Then differentiability is equivalent to
$$\frac{r(h)}{|h|} \to 0,$$
or, using little-$o$ notation,
$$f(a + h) = f(a) + f'(a)h + o(|h|).$$
Thus the derivative is not merely a slope. It is the coefficient of the best first-order linear approximation to the increment of the function.
If we write the displacement $h$ as $dx$, the corresponding differential notation is
$$df = f'(x) \, dx.$$
Here $dx$ denotes a displacement in the input. It should not be treated as an independent infinitesimal number.

**Proposition 4.2 — Differentiability Implies Continuity**
If $f$ is differentiable at $a$, then $f$ is continuous at $a$.

**Proof**
From differentiability,
$$f(a + h) - f(a) = f'(a)h + o(|h|).$$
Both terms on the right converge to zero as $h \to 0$. Hence
$$f(a + h) \to f(a).$$

The familiar differentiation rules can all be understood as rules for these first-order approximations.

**Proposition 4.3 — Basic One-Dimensional Differentiation Rules**
Suppose $f$ and $g$ are differentiable at $x$.
(1) For constants $\alpha, \beta \in \mathbb{R}$,
$$(\alpha f + \beta g)'(x) = \alpha f'(x) + \beta g'(x).$$
(2)
$$(fg)'(x) = f'(x)g(x) + f(x)g'(x).$$
(3) If $g(x) \neq 0$,
$$\left(\frac{f}{g}\right)'(x) = \frac{f'(x)g(x) - f(x)g'(x)}{g(x)^2}.$$

<!-- page 69 -->

(4) If $g$ is differentiable at $x$ and $f$ is differentiable at $g(x)$, then
$$(f \circ g)'(x) = f'(g(x))g'(x).$$
The last formula is the one-dimensional chain rule. In differential notation,
$$d(f \circ g) = f'(g(x)) \, dg = f'(g(x))g'(x) \, dx.$$
The multivariable chain rule will have exactly the same structure, except that multiplication of derivatives will become composition of linear maps.

### 4.2 Mean-Value Theorems, Monotonicity, and Convexity

The derivative is local: it describes what happens for an arbitrarily small change. The mean-value theorem connects this local information to a finite change over an interval.

**Proposition 4.4 — Fermat's Theorem**
Suppose $f$ is differentiable at an interior point $a$ of its domain. If $a$ is a local maximum or a local minimum of $f$, then
$$f'(a) = 0.$$

**Proof**
Suppose, for example, that $a$ is a local maximum. For sufficiently small $h > 0$,
$$\frac{f(a + h) - f(a)}{h} \leq 0,$$
whereas for sufficiently small $h < 0$,
$$\frac{f(a + h) - f(a)}{h} \geq 0.$$
If the two-sided derivative exists, these one-sided inequalities can have the same limit only if that limit is zero. The argument for a local minimum is the same with the inequalities reversed.

**Theorem 4.5 — Rolle's Theorem**
Let $a < b$, and let $f : [a, b] \to \mathbb{R}$ be continuous on $[a, b]$ and differentiable on $(a, b)$. If
$$f(a) = f(b),$$

<!-- page 70 -->

then there exists $\xi \in (a, b)$ such that
$$f'(\xi) = 0.$$

**Proof**
By the Extreme Value Theorem, $f$ attains a maximum and a minimum on $[a, b]$. If both are equal, then $f$ is constant and every interior point works. Otherwise at least one of the extrema is attained at an interior point, because the two endpoint values are equal. Fermat's theorem then gives $f'(\xi) = 0$ at that interior extremum.

The geometric idea is simple: if a differentiable graph starts and ends at the same height, then somewhere in between it has a horizontal tangent. Rolle's theorem gives the standard mean-value theorem as an immediate consequence.

**Theorem 4.6 — Lagrange Mean-Value Theorem**
Let $a < b$, and let $f : [a, b] \to \mathbb{R}$ be continuous on $[a, b]$ and differentiable on $(a, b)$. Then there exists $\xi \in (a, b)$ such that
$$f(b) - f(a) = f'(\xi)(b - a).$$
Equivalently,
$$\frac{f(b) - f(a)}{b - a} = f'(\xi).$$

**Proof**
Subtract the secant line. Define
$$g(x) = f(x) - f(a) - \frac{f(b) - f(a)}{b - a}(x - a).$$
Then
$$g(a) = g(b) = 0.$$
By Rolle's theorem there exists $\xi \in (a, b)$ such that $g'(\xi) = 0$. Hence
$$f'(\xi) = \frac{f(b) - f(a)}{b - a}.$$
The mean-value identity immediately yields several qualitative consequences.

<!-- page 71 -->

[Image: A graph showing a curve $f(x)$ between $a$ and $b$. A secant line connects $(a, f(a))$ and $(b, f(b))$. A tangent line at $\xi$ is parallel to the secant line.]
Figure 8: For $f(x) = x^2$ on $[1, 3]$, the secant slope is 4. At $\xi = 2$, the tangent slope is also $f'(2) = 4$, illustrating the mean-value theorem.

**Corollary 4.7 — Derivative Sign and Monotonicity**
Let $f$ be differentiable on an interval $I$.
(1) If $f'(x) \geq 0$ for every $x \in I$, then $f$ is nondecreasing.
(2) If $f'(x) > 0$ for every interior point $x \in I$, then $f$ is strictly increasing.
(3) If $f'(x) = 0$ throughout $I$, then $f$ is constant.
Analogous statements hold with the inequalities reversed.

For example, if $x < y$, the mean-value theorem gives
$$f(y) - f(x) = f'(\xi)(y - x)$$
for some $\xi \in (x, y)$. The sign conclusions are immediate.
The same theorem gives a quantitative estimate.

**Corollary 4.8 — Bounded Derivative Implies Lipschitz Continuity**
Suppose $f$ is differentiable on an interval $I$ and
$$|f'(x)| \leq L \quad \text{for every } x \in I.$$
Then
$$|f(y) - f(x)| \leq L|y - x| \quad \text{for all } x, y \in I.$$

<!-- page 72 -->

This estimate is the one-dimensional prototype for the derivative bounds used later in contraction arguments.
A second important consequence concerns convexity.

**Definition 4.9 — Convex Function on an Interval**
Let $I \subseteq \mathbb{R}$ be an interval. A function $f : I \to \mathbb{R}$ is convex if
$$f((1 - t)x + ty) \leq (1 - t)f(x) + tf(y)$$
for all $x, y \in I$ and $t \in [0, 1]$.

For differentiable functions, convexity is equivalent to the graph lying above every tangent line.

**Theorem 4.10 — First-Order Characterization of Convexity**
Let $f : I \to \mathbb{R}$ be differentiable on an open interval $I$. Then $f$ is convex if and only if
$$f(y) \geq f(x) + f'(x)(y - x) \quad \text{for all } x, y \in I.$$
Equivalently, $f$ is convex if and only if $f'$ is nondecreasing on $I$.

**Proof**
Suppose first that $f$ is convex. Fix $x, y \in I$ with $x \neq y$. For $t \in (0, 1)$, convexity gives
$$f(x + t(y - x)) \leq (1 - t)f(x) + tf(y).$$
Subtracting $f(x)$ and dividing by $t > 0$,
$$\frac{f(x + t(y - x)) - f(x)}{t} \leq f(y) - f(x).$$
Letting $t \downarrow 0$, the left-hand side converges to
$$f'(x)(y - x).$$
Thus
$$f(y) \geq f(x) + f'(x)(y - x)$$
for all $x, y \in I$.
Conversely, suppose the tangent-line inequality holds. For $x, y \in I$ and $t \in [0, 1]$, set
$$z = (1 - t)x + ty.$$

<!-- page 73 -->

The cases $t = 0$ and $t = 1$ are immediate, so assume $t \in (0, 1)$. Applying the tangent-line inequality with base point $z$ once to $x$ and once to $y$ gives
$$f(x) \geq f(z) + f'(z)(x - z), \quad f(y) \geq f(z) + f'(z)(y - z).$$
Multiplying the first inequality by $1 - t$, the second by $t$, and adding, the derivative terms cancel because
$$(1 - t)(x - z) + t(y - z) = 0.$$
Hence
$$(1 - t)f(x) + tf(y) \geq f(z),$$
which is precisely convexity.
It remains to connect this condition with monotonicity of $f'$. If the tangent-line inequality holds and $x < y$, then
$$f'(x) \leq \frac{f(y) - f(x)}{y - x} \leq f'(y),$$
so $f'$ is nondecreasing.
Conversely, suppose $f'$ is nondecreasing. If $x < y$, the mean-value theorem gives some $\xi \in (x, y)$ such that
$$\frac{f(y) - f(x)}{y - x} = f'(\xi) \geq f'(x),$$
and therefore
$$f(y) \geq f(x) + f'(x)(y - x).$$
If $y < x$, apply the mean-value theorem on $[y, x]$ to obtain
$$\frac{f(x) - f(y)}{x - y} = f'(\xi) \leq f'(x)$$
for some $\xi \in (y, x)$, which rearranges to the same tangent-line inequality. The tangent-line characterization already proved then implies that $f$ is convex.

A convenient smooth sufficient condition is therefore
$$f''(x) \geq 0 \quad \text{on } I.$$
Similarly, $f'' \leq 0$ implies concavity.
The mean-value theorem also gives a simple local inverse result that will later be generalized to mappings between Euclidean spaces.

<!-- page 74 -->

### Proposition 4.11 — One-Dimensional Local Inverse
Let $f$ be continuously differentiable on a neighborhood of $a$, and suppose
$$f'(a) \neq 0.$$
Then there are intervals $U$ containing $a$ and $V$ containing $f(a)$ such that
$$f : U \to V$$
is one-to-one and onto. Its inverse $g : V \to U$ is differentiable and
$$g'(y) = \frac{1}{f'(g(y))}.$$
In particular,
$$g'(f(a)) = \frac{1}{f'(a)}.$$

### Proof
Because $f'(a) \neq 0$ and $f'$ is continuous, there is an open interval
$$U = (a - r, a + r)$$
contained in the neighborhood on which $f$ is $C^1$, and a constant $c > 0$, such that either
$$f'(x) \geq c \quad \text{for every } x \in U,$$
or
$$f'(x) \leq -c \quad \text{for every } x \in U.$$
By the mean-value theorem, $f$ is strictly monotone on $U$ and hence one-to-one.
Its image
$$V = f(U)$$
is an open interval. To see openness, fix $x_0 \in U$ and choose $x_- < x_0 < x_+$ with $x_-, x_+ \in U$. If $f$ is increasing, then
$$f(x_-) < f(x_0) < f(x_+),$$
so an open interval around $f(x_0)$ lies in $V$; the decreasing case is the same with the inequalities reversed.
Let
$$g : V \to U$$

<!-- page 75 -->

be the inverse. It is continuous. Indeed, fix $y_0 = f(x_0) \in V$ and $\varepsilon > 0$ small enough that
$$x_0 - \varepsilon, x_0 + \varepsilon \in U.$$
In the increasing case,
$$f(x_0 - \varepsilon) < y_0 < f(x_0 + \varepsilon).$$
Hence every $y$ sufficiently close to $y_0$ lies between these two values, and monotonicity gives
$$x_0 - \varepsilon < g(y) < x_0 + \varepsilon.$$
The decreasing case is analogous.
Now fix $y_0 \in V$ and put $x_0 = g(y_0)$. For $y \neq y_0$ near $y_0$, set $x = g(y)$. The mean-value theorem gives some $\xi$ between $x$ and $x_0$ such that
$$y - y_0 = f(x) - f(x_0) = f'(\xi)(x - x_0).$$
Therefore
$$\frac{g(y) - g(y_0)}{y - y_0} = \frac{1}{f'(\xi)}.$$
As $y \to y_0$, continuity of $g$ gives $x \to x_0$, and hence $\xi \to x_0$. Continuity of $f'$ yields
$$g'(y_0) = \frac{1}{f'(x_0)} = \frac{1}{f'(g(y_0))}.$$
Since $f'$ and $g$ are continuous and $f'$ stays away from zero on $U$, this derivative is continuous in $y_0$. Thus $g \in C^1(V)$.

### 4.3 Taylor’s Theorem in One Variable
Linear approximation uses only the first derivative. If more derivatives are available, we can systematically improve the approximation.
For $k \geq 0$, the degree-$k$ Taylor polynomial of $f$ at $a$ is
$$T_k f(a; h) := \sum_{j=0}^k \frac{f^{(j)}(a)}{j!} h^j.$$
Here $f^{(0)} = f$.

### Theorem 4.12 — Taylor’s Theorem with Lagrange Remainder
Suppose $f \in C^{k+1}(I)$ on an open interval $I$ containing the segment between $a$ and $a + h$. Then

<!-- page 76 -->

there exists $\xi$ between $a$ and $a + h$ such that
$$f(a + h) = \sum_{j=0}^k \frac{f^{(j)}(a)}{j!} h^j + \frac{f^{(k+1)}(\xi)}{(k+1)!} h^{k+1}.$$
The cases $k = 0$ and $k = 1$ are especially important. For $k = 0$, Taylor’s theorem is the mean-value theorem. For $k = 1$,
$$f(a + h) = f(a) + f'(a)h + \frac{1}{2}f''(\xi)h^2.$$
Thus the error in linear approximation is second order whenever $f''$ is locally bounded.
A local form that is often cleaner for theory is the Peano form.

### Corollary 4.13 — Peano Form of Taylor’s Theorem
If $f$ is of class $C^k$ near $a$, then
$$f(a + h) = \sum_{j=0}^k \frac{f^{(j)}(a)}{j!} h^j + o(|h|^k) \quad \text{as } h \to 0.$$
In particular, if $f \in C^2$ near $a$,
$$f(a + h) = f(a) + f'(a)h + \frac{1}{2}f''(a)h^2 + o(h^2).$$
At a critical point $a$, where $f'(a) = 0$, the quadratic term becomes the first nonzero local approximation in the generic case:
$$f(a + h) - f(a) = \frac{1}{2}f''(a)h^2 + o(h^2).$$
Hence $f''(a) > 0$ gives a strict local minimum and $f''(a) < 0$ gives a strict local maximum. The multivariable analogue will replace the scalar $f''(a)$ by the Hessian matrix.

### 4.4 The Fundamental Theorem of Calculus
Differentiation and integration are inverse operations. We assume the standard Riemann integral on a closed interval and record the form of the fundamental theorem that will be used later.

### Theorem 4.14 — Fundamental Theorem of Calculus
Let $f : [a, b] \to \mathbb{R}$ be continuous and define
$$F(x) = \int_a^x f(t) \, dt.$$

<!-- page 77 -->

Then $F$ is differentiable on $(a, b)$ and
$$F'(x) = f(x).$$
Conversely, if $G$ is differentiable on $[a, b]$ with $G' = f$, then
$$\int_a^b f(x) \, dx = G(b) - G(a).$$
The first assertion explains why integration produces primitives. The second is the Newton–Leibniz formula used to evaluate definite integrals.
Two standard consequences will be used repeatedly in multivariable integration.

### Proposition 4.15 — Substitution and Integration by Parts
Suppose the functions below have the regularity needed for the displayed expressions.
(1) If $\phi : [\alpha, \beta] \to \mathbb{R}$ is continuously differentiable and $f$ is continuous on an interval containing $\phi([\alpha, \beta])$, then
$$\int_\alpha^\beta f(\phi(t))\phi'(t) \, dt = \int_{\phi(\alpha)}^{\phi(\beta)} f(x) \, dx.$$
(2) If $u, v \in C^1([a, b])$, then
$$\int_a^b u(x)v'(x) \, dx = [u(x)v(x)]_a^b - \int_a^b u'(x)v(x) \, dx.$$
The substitution formula is the one-dimensional model for the change-of-variables theorem in $\mathbb{R}^n$. The factor $\phi'(t)$ records the local stretching of length. In several dimensions it will be replaced by the absolute value of a Jacobian determinant, which records the local stretching of volume.
The expansion
$$f(a + h) = f(a) + f'(a)h + o(|h|)$$
is the template for multivariable differentiation. The only essential change is that multiplication by the scalar $f'(a)$ must be replaced by a linear map.

<!-- page 78 -->

### 5 Differential Calculus in Euclidean Space
For a mapping between Euclidean spaces, the first-order approximation must itself be a linear map,
$$Df(a) : \mathbb{R}^n \to \mathbb{R}^m.$$
A collection of coordinate slopes is not enough: one linear map must approximate the change in $f$ for every small displacement $h$. We first record the linear estimate and remainder notation needed to make this statement precise.

### Proposition 5.1 — Linear Maps Are Lipschitz
Let
$$L : \mathbb{R}^n \to \mathbb{R}^m$$
be linear. Then there exists a constant $C < \infty$ such that
$$\|Lh\| \leq C\|h\| \quad \text{for every } h \in \mathbb{R}^n.$$
Consequently, every linear map between finite-dimensional Euclidean spaces is uniformly continuous.

### Proof
Write
$$h = \sum_{j=1}^n h_j e_j.$$
By linearity and the triangle inequality,
$$\|Lh\| \leq \sum_{j=1}^n |h_j| \|Le_j\| \leq \left( \max_{1 \leq j \leq n} \|Le_j\| \right) \sum_{j=1}^n |h_j|.$$
Since by Cauchy-Schwarz
$$\sum_{j=1}^n |h_j| \leq \sqrt{n} \|h\|,$$
we may take
$$C = \sqrt{n} \max_{1 \leq j \leq n} \|Le_j\|.$$
The continuity statement follows immediately.

<!-- page 79 -->

### Remark 5.2 — Operator Norm
The smallest constant in such an estimate is the operator norm
$$\|L\|_{\text{op}} := \sup_{\|h\|=1} \|Lh\|.$$
Thus
$$\|Lh\| \leq \|L\|_{\text{op}} \|h\|.$$
We will mainly use this inequality rather than the norm itself.

### Definition 5.3 — Little-$o$ Remainders
Let
$$r : V \subseteq \mathbb{R}^n \to \mathbb{R}^m$$
be defined near $0$, with $r(0) = 0$. We write
$$r(h) = o(\|h\|) \quad \text{as } h \to 0$$
if
$$\frac{\|r(h)\|}{\|h\|} \to 0 \quad \text{as } h \to 0, \quad h \neq 0.$$
Thus $r(h)$ is small not merely in absolute size, but relative to the size of the displacement $h$.

### 5.1 Differentiability as Linear Approximation
Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}^m,$$
where $U$ is open, and fix $a \in U$. For a small displacement $h \in \mathbb{R}^n$, define the increment
$$\Delta f(a; h) := f(a + h) - f(a).$$
The question is whether this increment has a linear principal part.

### Definition 5.4 — Differentiability and the Differential
The mapping $f$ is differentiable at $a$ if there exists a linear map
$$L : \mathbb{R}^n \to \mathbb{R}^m$$

<!-- page 80 -->

such that
$$f(a + h) - f(a) = Lh + r(h),$$
where
$$r(h) = o(\|h\|) \quad \text{as } h \to 0.$$
The linear map $L$ is called the differential, total derivative, or simply the derivative of $f$ at $a$, and is denoted
$$Df(a) : \mathbb{R}^n \to \mathbb{R}^m.$$
Equivalently,
$$f(a + h) = f(a) + Df(a)h + o(\|h\|).$$
There are two distinct requirements in this definition. First, the first-order term must be one linear map acting on the whole displacement $h$. Second, the approximation error must vanish faster than $\|h\|$:
$$\frac{\|f(a + h) - f(a) - Df(a)h\|}{\|h\|} \to 0.$$
This second condition is what makes the approximation genuinely first order.
When useful, one may regard $\mathbb{R}^n$ as a copy of the vector space attached at $a$ and write
$$Df(a) : T_a\mathbb{R}^n \to T_{f(a)}\mathbb{R}^m.$$
Nothing new is being added algebraically: the notation only emphasizes that $Df(a)$ maps small displacement vectors at $a$ into first-order displacement vectors at $f(a)$.

Figure 9: Differentiability decomposes the increment into a linear part and a smaller residual: $\Delta f(a; h) = Df(a)h + r(h)$ with $\|r(h)\|/\|h\| \to 0$.

The derivative, if it exists, is not one of many possible linear approximations. It is unique.

### Proposition 5.5 — Uniqueness of the Differential
If $f$ is differentiable at $a$, then the linear map $Df(a)$ is unique.

<!-- page 81 -->

### Proof
Suppose that linear maps $L_1, L_2 : \mathbb{R}^n \to \mathbb{R}^m$ both satisfy the differentiability expansion.
Subtracting the two expansions gives
$$(L_1 - L_2)h = o(\|h\|).$$
Fix $v \in \mathbb{R}^n$. If $v = 0$, then $(L_1 - L_2)v = 0$ trivially. If $v \neq 0$, set $h = tv$. Then
$$t(L_1 - L_2)v = o(|t|\|v\|).$$
Taking norms and dividing by $|t|$ for $t \neq 0$ gives a quantity whose right-hand side tends to zero as $t \to 0$. Hence
$$\|(L_1 - L_2)v\| = 0.$$
Since $v$ was arbitrary,
$$L_1 = L_2.$$
The vector-valued definition is also exactly equivalent to differentiability of each coordinate function.

### Proposition 5.6 — Componentwise Differentiability
Let
$$f = (f_1, \dots, f_m) : U \to \mathbb{R}^m.$$
Then $f$ is differentiable at $a$ if and only if every scalar component $f_i$ is differentiable at $a$. In that case,
$$Df(a)h = \begin{pmatrix} Df_1(a)h \\ \vdots \\ Df_m(a)h \end{pmatrix}.$$

### Proof
Suppose first that
$$f(a + h) - f(a) = Lh + r(h), \quad r(h) = o(\|h\|).$$
Taking the $i$th coordinate gives
$$f_i(a + h) - f_i(a) = L_i h + r_i(h),$$
where $L_i$ is the $i$th coordinate of the linear map $L$. Since
$$|r_i(h)| \leq \|r(h)\|,$$
we have $r_i(h) = o(\|h\|)$, so each $f_i$ is differentiable.

<!-- page 82 -->

Conversely, suppose every $f_i$ is differentiable. Write
$$f_i(a + h) - f_i(a) = L_i h + r_i(h), \quad r_i(h) = o(\|h\|).$$
Define
$$Lh = (L_1 h, \dots, L_m h)^T, \quad r(h) = (r_1(h), \dots, r_m(h))^T.$$
Then $L$ is linear, and because there are only finitely many components,
$$\|r(h)\| \leq \sqrt{m} \max_i |r_i(h)| = o(\|h\|).$$
Hence $f$ is differentiable with derivative $L$.
Differentiability also immediately implies continuity.

### Proposition 5.7 — Differentiability Implies Continuity
If
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}^m$$
is differentiable at $a \in U$, then $f$ is continuous at $a$.

### Proof
By differentiability,
$$f(a + h) - f(a) = Df(a)h + r(h), \quad r(h) = o(\|h\|).$$
By proposition 5.1,
$$\|Df(a)h\| \leq C\|h\|$$
for some $C < \infty$. Hence
$$\|f(a + h) - f(a)\| \leq C\|h\| + \|r(h)\| \to 0$$
as $h \to 0$.
Affine maps are the simplest differentiable mappings.

### Proposition 5.8 — Derivative of an Affine Map
Let
$$F(x) = Ax + b, \quad A : \mathbb{R}^n \to \mathbb{R}^m \text{ linear.}$$

<!-- page 83 -->

Then $F$ is differentiable everywhere and
$$DF(a) = A \quad \text{for every } a \in \mathbb{R}^n.$$
Indeed,
$$F(a + h) - F(a) - Ah = 0.$$
Thus an affine map is already equal to its own first-order approximation.
For a genuinely nonlinear example, let
$$f(x, y) = x^2 + y^2.$$
At $a = (1, 1)$,
$$f(1 + h, 1 + k) = 2 + 2h + 2k + h^2 + k^2.$$
Therefore
$$Df(1, 1)(h, k) = 2h + 2k,$$
while
$$h^2 + k^2 = \|(h, k)\|^2 = o(\|(h, k)\|).$$
The derivative retains exactly the terms that are first order in the increment.

### Example 5.9 — A Local Approximation in Economics
Let output be
$$Y = F(K, L),$$
where $F : \mathbb{R}^2_{++} \to \mathbb{R}$ is differentiable. If capital and labor change by $\Delta K$ and $\Delta L$, then
$$F(K + \Delta K, L + \Delta L) - F(K, L) = F_K(K, L) \Delta K + F_L(K, L) \Delta L + o\left(\sqrt{(\Delta K)^2 + (\Delta L)^2}\right).$$
Thus the familiar “marginal product times input change” calculation is the first-order differential of the production function.

### 5.2 Jacobians and Partial Derivatives
The definition of differentiability is coordinate-free: $Df(a)$ is a linear map. To compute this map, however, we return to coordinates. The relevant objects are partial derivatives and the matrix of the differential.
Let
$$e_1, \dots, e_n$$

<!-- page 84 -->

be the standard basis of $\mathbb{R}^n$.

### Definition 5.10 — Partial Derivative
Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}^m$$
and let $a \in U$. The partial derivative of $f$ with respect to the $j$th variable at $a$ is
$$\frac{\partial f}{\partial x_j}(a) := \lim_{t \to 0} \frac{f(a + te_j) - f(a)}{t},$$
provided the limit exists.
A partial derivative therefore varies one coordinate and freezes the others. If
$$f = (f_1, \dots, f_m),$$
then
$$\frac{\partial f}{\partial x_j}(a) = \begin{pmatrix} \frac{\partial f_1}{\partial x_j}(a) \\ \vdots \\ \frac{\partial f_m}{\partial x_j}(a) \end{pmatrix}.$$
If the full differential exists, the partial derivatives are simply its values on the coordinate directions.

### Proposition 5.11 — Differential and Partial Derivatives
If $f$ is differentiable at $a$, then all partial derivatives of $f$ exist at $a$ and
$$Df(a)e_j = \frac{\partial f}{\partial x_j}(a), \quad j = 1, \dots, n.$$
Consequently, $Df(a)$ is completely determined by the partial derivatives.

### Proof
Set $h = te_j$ in the differentiability expansion:
$$f(a + te_j) - f(a) = tDf(a)e_j + o(|t|).$$
Dividing by $t$ and letting $t \to 0$ gives
$$\frac{\partial f}{\partial x_j}(a) = Df(a)e_j.$$

<!-- page 85 -->

This is exactly the familiar linear-algebra fact that a linear map is determined by its values on a basis.

**Definition 5.12 — Jacobian Matrix**
Suppose
$$f = (f_1, \dots, f_m) : U \subseteq \mathbb{R}^n \to \mathbb{R}^m$$
has all first partial derivatives at $a$. The **Jacobian matrix** of $f$ at $a$ is
$$J_f(a) := \begin{pmatrix} \frac{\partial f_1}{\partial x_1}(a) & \cdots & \frac{\partial f_1}{\partial x_n}(a) \\ \vdots & \ddots & \vdots \\ \frac{\partial f_m}{\partial x_1}(a) & \cdots & \frac{\partial f_m}{\partial x_n}(a) \end{pmatrix}.$$

When $f$ is differentiable, $J_f(a)$ is precisely the matrix of the linear map $Df(a)$ in the standard bases:
$$Df(a)h = J_f(a)h.$$
The $j$th column is
$$Df(a)e_j = \frac{\partial f}{\partial x_j}(a),$$
and the $i$th row records the differential of the scalar component $f_i$. Thus:
the Jacobian is the matrix of the derivative, not a different derivative.

**Remark 5.13 — The Jacobian Determinant**
If $m = n$, the square matrix $J_f(a)$ has determinant
$$\det J_f(a).$$
This is often called the **Jacobian determinant**, and sometimes simply the "Jacobian." We will keep the terminology separate: $J_f(a)$ denotes the matrix, while $\det J_f(a)$ denotes its determinant. The distinction becomes important in the inverse function theorem and in change of variables for multiple integrals.

For example, consider
$$f(x, y) = \begin{pmatrix} x^2y \\ e^{x-y} \end{pmatrix}.$$
Then
$$J_f(x, y) = \begin{pmatrix} 2xy & x^2 \\ e^{x-y} & -e^{x-y} \end{pmatrix}.$$

<!-- page 86 -->

At $a = (1, 0)$,
$$J_f(1, 0) = \begin{pmatrix} 0 & 1 \\ e & -e \end{pmatrix}.$$
Hence, for $h = (h_1, h_2)^T$,
$$f(a + h) = f(a) + J_f(a)h + o(\|h\|),$$
so to first order
$$f(a + h) \approx \begin{pmatrix} 0 \\ e \end{pmatrix} + \begin{pmatrix} h_2 \\ e(h_1 - h_2) \end{pmatrix}.$$
For a scalar-valued function
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R},$$
the Jacobian is the row vector
$$J_f(a) = \begin{pmatrix} \partial_1 f(a) & \cdots & \partial_n f(a) \end{pmatrix},$$
and
$$Df(a)h = \sum_{j=1}^n \partial_j f(a)h_j.$$
If one writes
$$h_j = dx_j,$$
this becomes the traditional total-differential notation
$$df = \frac{\partial f}{\partial x_1} dx_1 + \dots + \frac{\partial f}{\partial x_n} dx_n.$$
Here $dx_j$ should be understood as the $j$th coordinate of the displacement $h$, rather than as a separate "infinitesimal quantity."

**5.3 Criteria for Differentiability**
There is an important logical distinction between partial derivatives and differentiability. Partial derivatives examine the function only along the coordinate axes. Differentiability requires one linear map to approximate the function for *all* small displacements simultaneously.
We have already proved
$$\text{differentiable at } a \implies \text{all partial derivatives exist at } a.$$
The converse is false.

<!-- page 87 -->

Consider
$$f(x, y) = \begin{cases} \frac{xy}{x^2 + y^2}, & (x, y) \neq (0, 0), \\ 0, & (x, y) = (0, 0). \end{cases}$$
Along the coordinate axes,
$$f(t, 0) = f(0, t) = 0,$$
so
$$\partial_x f(0, 0) = \partial_y f(0, 0) = 0.$$
But along $y = x$,
$$f(t, t) = \frac{1}{2},$$
so $f$ is not even continuous at the origin. By proposition 5.7, it cannot be differentiable there.
In smooth applications, the standard sufficient condition is continuity of the first partial derivatives.

**Theorem 5.14 — Continuous Partials Imply Differentiability**
Let $U \subseteq \mathbb{R}^n$ be open and let
$$f : U \to \mathbb{R}^m.$$
Suppose that every first partial derivative
$$\frac{\partial f_i}{\partial x_j}$$
exists in a neighborhood of $a \in U$ and is continuous at $a$. Then $f$ is differentiable at $a$, and
$$Df(a)h = J_f(a)h.$$

**Proof**
By proposition 5.6, it is enough to prove the result for a scalar-valued function
$$f : U \to \mathbb{R}.$$
Because $U$ is open, choose $\rho > 0$ such that
$$B_\rho(a) \subseteq U.$$
Take $h$ sufficiently small that all intermediate points below lie in this ball. Write
$$a = (a_1, \dots, a_n), \quad h = (h_1, \dots, h_n),$$

<!-- page 88 -->

and define
$$a^{(0)} = a, \quad a^{(j)} = (a_1 + h_1, \dots, a_j + h_j, a_{j+1}, \dots, a_n).$$
Then
$$f(a + h) - f(a) = \sum_{j=1}^n [f(a^{(j)}) - f(a^{(j-1)})].$$
For the $j$th term only the $j$th coordinate changes. If $h_j \neq 0$, the one-variable mean-value theorem gives a point $\xi_j$ on that coordinate segment such that
$$f(a^{(j)}) - f(a^{(j-1)}) = \partial_j f(\xi_j)h_j.$$
If $h_j = 0$, the difference is already zero; in that case take $\xi_j = a^{(j-1)}$, and the same formula holds. Hence
$$f(a + h) - f(a) = \sum_{j=1}^n \partial_j f(a)h_j + \sum_{j=1}^n [\partial_j f(\xi_j) - \partial_j f(a)]h_j.$$
The first term is $J_f(a)h$. Moreover,
$$\|\xi_j - a\| \leq \|h\|,$$
so $\xi_j \to a$ as $h \to 0$. Continuity of the partial derivatives at $a$ gives
$$\eta(h) := \max_{1 \leq j \leq n} |\partial_j f(\xi_j) - \partial_j f(a)| \longrightarrow 0.$$
Therefore
$$\left| \sum_{j=1}^n [\partial_j f(\xi_j) - \partial_j f(a)]h_j \right| \leq \eta(h) \sum_{j=1}^n |h_j| \leq \sqrt{n} \eta(h) \|h\| = o(\|h\|).$$
Thus
$$f(a + h) - f(a) = J_f(a)h + o(\|h\|),$$
which is differentiability at $a$.

**Example 5.15 — Using Continuous Partials to Prove Differentiability**
Consider
$$f(x, y) = x^2y + \sin(xy).$$

<!-- page 89 -->

Its first partial derivatives are
$$f_x(x, y) = 2xy + y \cos(xy), \quad f_y(x, y) = x^2 + x \cos(xy),$$
and both are continuous on $\mathbb{R}^2$. Hence $f$ is differentiable everywhere. At $(1, 0)$,
$$Df(1, 0)(h, k) = f_x(1, 0)h + f_y(1, 0)k = 2k.$$
Therefore
$$f(1 + h, k) = f(1, 0) + 2k + o\left(\sqrt{h^2 + k^2}\right).$$
The point of the criterion is that no separate remainder calculation is needed once continuity of the first partial derivatives has been established.

**Definition 5.16 — $C^1$ Mappings**
Let $U \subseteq \mathbb{R}^n$ be open. A mapping
$$f : U \to \mathbb{R}^m$$
is of class $C^1$ if all first partial derivatives exist and are continuous on $U$. We write
$$f \in C^1(U, \mathbb{R}^m).$$
The theorem gives
$$f \in C^1(U, \mathbb{R}^m) \implies f \text{ is differentiable at every point of } U.$$

**Proposition 5.17 — $C^1$ and Continuity of the Derivative**
Suppose $f : U \to \mathbb{R}^m$ is differentiable at every point of the open set $U \subseteq \mathbb{R}^n$. Then
$$f \in C^1(U, \mathbb{R}^m)$$
if and only if the derivative map
$$x \mapsto Df(x)$$
is continuous, after identifying each derivative with its Jacobian matrix.

<!-- page 90 -->

**Proof**
The entries of the matrix $Df(x) = J_f(x)$ are exactly the first partial derivatives
$$\frac{\partial f_i}{\partial x_j}(x).$$
In a finite-dimensional matrix space, convergence of matrices is equivalent to convergence of their finitely many entries. Hence continuity of the Jacobian matrix is equivalent to continuity of all first partial derivatives.

The usual algebraic differentiation rules extend to total derivatives without change in form.

**Proposition 5.18 — Basic Differentiation Rules**
Suppose $f$ and $g$ are differentiable at $a$.
(1) If $f, g : U \to \mathbb{R}^m$ and $\alpha, \beta \in \mathbb{R}$, then
$$D(\alpha f + \beta g)(a) = \alpha Df(a) + \beta Dg(a).$$
(2) If $f, g : U \to \mathbb{R}$, then
$$D(fg)(a) = g(a)Df(a) + f(a)Dg(a).$$
(3) If $f, g : U \to \mathbb{R}$ and $g(a) \neq 0$, then
$$D\left(\frac{f}{g}\right)(a) = \frac{g(a)Df(a) - f(a)Dg(a)}{g(a)^2}.$$

**Proof**
The linear-combination rule follows immediately by adding the differentiability expansions.
For the product rule, write
$$\Delta f = f(a + h) - f(a), \quad \Delta g = g(a + h) - g(a).$$
Then
$$(fg)(a + h) - (fg)(a) = g(a)\Delta f + f(a)\Delta g + \Delta f \Delta g.$$
Differentiability gives
$$\Delta f = Df(a)h + o(\|h\|) = O(\|h\|), \quad \Delta g = Dg(a)h + o(\|h\|) = O(\|h\|).$$
Consequently
$$\Delta f \Delta g = O(\|h\|^2) = o(\|h\|),$$

<!-- page 91 -->

and the linear part of the increment is
$$g(a)Df(a)h + f(a)Dg(a)h.$$
This proves the product rule.
For the quotient rule, it is enough to differentiate the reciprocal. Since $g$ is differentiable, it is continuous at $a$; because $g(a) \neq 0$, we have $g(a + h) \neq 0$ for all sufficiently small $h$. Put
$$\Delta g = g(a + h) - g(a).$$
Then
$$\frac{1}{g(a + h)} - \frac{1}{g(a)} = -\frac{\Delta g}{g(a)g(a + h)}.$$
Since $\Delta g = Dg(a)h + o(\|h\|)$ and $g(a + h) \to g(a)$,
$$\frac{1}{g(a)g(a + h)} = \frac{1}{g(a)^2} + o(\|h\|),$$
and therefore
$$\frac{1}{g(a + h)} - \frac{1}{g(a)} = -\frac{Dg(a)h}{g(a)^2} + o(\|h\|).$$
Hence
$$D\left(\frac{1}{g}\right)(a) = -\frac{Dg(a)}{g(a)^2}.$$
Applying the product rule to $f(1/g)$ gives
$$D\left(\frac{f}{g}\right)(a) = \frac{g(a)Df(a) - f(a)Dg(a)}{g(a)^2}.$$

**Remark 5.19 — The Logical Hierarchy**
For mappings on an open subset of Euclidean space,
$$C^1 \implies \text{differentiable} \implies \text{continuous}.$$
Also,
$$\text{differentiable} \implies \text{all partial derivatives exist.}$$
The reverse implications fail in general. In particular, the existence of all partial derivatives at a point does not by itself produce a total derivative.

<!-- page 92 -->

**5.4 Directional Derivatives and the Gradient**
Partial derivatives only inspect coordinate directions. Given an arbitrary vector $v \in \mathbb{R}^n$, we may instead restrict the function to the line
$$t \mapsto a + tv.$$

**Definition 5.20 — Derivative Along a Vector**
Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}^m, \quad a \in U,$$
and let $v \in \mathbb{R}^n$. The **derivative of $f$ along $v$ at $a$ is**
$$D_v f(a) := \lim_{t \to 0} \frac{f(a + tv) - f(a)}{t},$$
provided the limit exists.
When $v$ is a unit vector, $D_v f(a)$ is usually called the **directional derivative** in the direction $v$.

If the total derivative exists, every directional derivative is already encoded in it.

**Proposition 5.21 — Directional Derivatives from the Differential**
If $f$ is differentiable at $a$, then for every $v \in \mathbb{R}^n$,
$$D_v f(a) = Df(a)v = J_f(a)v.$$

**Proof**
Set $h = tv$. Then
$$f(a + tv) - f(a) = tDf(a)v + o(|t|).$$
Dividing by $t$ and letting $t \to 0$ yields
$$D_v f(a) = Df(a)v.$$
The converse is false, even if directional derivatives exist in every direction. This is a stronger warning than the failure of partial derivatives alone.
Define
$$f(x, y) = \begin{cases} \frac{x^2y}{x^4 + y^2}, & (x, y) \neq (0, 0), \\ 0, & (x, y) = (0, 0). \end{cases}$$
For $v = (h, k)$ with $k \neq 0$,
$$\frac{f(th, tk) - f(0, 0)}{t} = \frac{h^2k}{t^2h^4 + k^2} \to \frac{h^2}{k},$$

<!-- page 93 -->

while for $k = 0$ the derivative is 0. Thus $D_v f(0, 0)$ exists for every $v$. Nevertheless,
$$f(x, x^2) = \frac{1}{2} \quad (x \neq 0),$$
so $f$ is not continuous at the origin and therefore is not differentiable there. Moreover,
$$v \mapsto D_v f(0, 0)$$
is not linear. Differentiability requires exactly this linear coherence among directions.
For scalar-valued functions, the differential is a linear functional. The Euclidean inner product represents that functional by a unique vector.

**Definition 5.22 — Gradient**
Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}$$
be differentiable at $a$. The **gradient** of $f$ at $a$ is the unique vector $\nabla f(a) \in \mathbb{R}^n$ satisfying
$$Df(a)h = \nabla f(a) \cdot h \quad \text{for every } h \in \mathbb{R}^n.$$
In standard coordinates,
$$\nabla f(a) = \begin{pmatrix} \partial_1 f(a) \\ \vdots \\ \partial_n f(a) \end{pmatrix}.$$

Indeed, evaluating the representation at $e_j$ gives
$$\nabla f(a) \cdot e_j = Df(a)e_j = \partial_j f(a).$$
Thus the gradient is the column-vector representation of the scalar differential, whereas $J_f(a)$ is the corresponding row vector.
Consequently,
$$D_v f(a) = \nabla f(a) \cdot v.$$
If $v$ is a unit vector and $\theta$ is the angle between $v$ and $\nabla f(a)$, then
$$D_v f(a) = \|\nabla f(a)\| \cos \theta.$$

<!-- page 94 -->

**Proposition 5.23 — Gradient and Steepest Ascent**
Let $f : U \to \mathbb{R}$ be differentiable at $a$ and suppose
$$\nabla f(a) \neq 0.$$
Among all unit vectors $v$, the directional derivative $D_v f(a)$ is maximized by
$$v = \frac{\nabla f(a)}{\|\nabla f(a)\|},$$
and the maximum value is
$$\|\nabla f(a)\|.$$
The minimum is attained in the opposite direction and equals $-\|\nabla f(a)\|$.

**Proof**
For every unit vector $v$, Cauchy–Schwarz gives
$$D_v f(a) = \nabla f(a) \cdot v \leq \|\nabla f(a)\|.$$
Equality holds precisely when $v$ points in the direction of the gradient. Applying the same argument to $-v$ gives the minimum.

The geometry is particularly transparent on level sets. Consider
$$f(x, y) = x^2 + 4y^2.$$
Its level curves are ellipses and
$$\nabla f(x, y) = (2x, 8y)^T.$$
At $a = (1, \frac{1}{2})$,
$$\nabla f(a) = (2, 4)^T,$$
while $(2, -1)^T$ is tangent to the ellipse through $a$, since
$$(2, 4) \cdot (2, -1) = 0.$$
The picture suggests an orthogonality theorem. We will prove it after introducing differentiable curves.

<!-- page 95 -->

[Image: A graph showing an ellipse centered at the origin with a point $a=(1, 1/2)$ on it. An arrow labeled $\nabla f(a)$ points outward from the ellipse at $a$, and a line labeled "tangent direction" is tangent to the ellipse at $a$.]
Figure 10: For a differentiable scalar function, the gradient is normal to a smooth level curve and points in the direction of steepest local increase.

**5.5 The Chain Rule**
The derivative is a linear map, so composition is especially natural. At first order, composing nonlinear mappings amounts to composing their linear approximations.
Let
$$g : U \subseteq \mathbb{R}^n \to V \subseteq \mathbb{R}^m, \quad f : V \to \mathbb{R}^p,$$
where $U$ and $V$ are open, and set
$$b = g(a).$$

**Theorem 5.24 — Chain Rule**
If $g$ is differentiable at $a$ and $f$ is differentiable at $b = g(a)$, then $f \circ g$ is differentiable at $a$ and
$$D(f \circ g)(a) = Df(g(a)) \circ Dg(a).$$
In matrix form,
$$J_{f \circ g}(a) = J_f(g(a))J_g(a).$$

**Proof**
Write
$$B = Dg(a), \quad A = Df(b).$$
Differentiability of $g$ gives
$$g(a + h) = b + Bh + r(h), \quad r(h) = o(\|h\|).$$

<!-- page 96 -->

Set
$$k(h) = Bh + r(h).$$
By proposition 5.1,
$$\|Bh\| \leq C_B\|h\|,$$
and since $r(h) = o(\|h\|)$, there is a constant $C$ such that, for all sufficiently small $h$,
$$\|k(h)\| \leq C\|h\|.$$
In particular, $k(h) \to 0$.
Differentiability of $f$ at $b$ gives
$$f(b + k) = f(b) + Ak + s(k), \quad s(k) = o(\|k\|).$$
Therefore
$$(f \circ g)(a + h) - (f \circ g)(a) = A(Bh + r(h)) + s(k(h))$$
$$= ABh + Ar(h) + s(k(h)).$$
Again by boundedness of the linear map $A$,
$$Ar(h) = o(\|h\|).$$
It remains to control $s(k(h))$. Given $\varepsilon > 0$, differentiability of $f$ implies that for $k$ sufficiently small,
$$\|s(k)\| \leq \varepsilon \|k\|.$$
Hence, for $h$ sufficiently small,
$$\|s(k(h))\| \leq \varepsilon \|k(h)\| \leq C\varepsilon \|h\|.$$
Since $\varepsilon$ is arbitrary,
$$s(k(h)) = o(\|h\|).$$
Thus
$$(f \circ g)(a + h) - (f \circ g)(a) = ABh + o(\|h\|),$$
which proves
$$D(f \circ g)(a) = AB.$$
The formula should be read from right to left. A displacement $h \in T_a\mathbb{R}^n$ is first transformed into
$$Dg(a)h \in T_{g(a)}\mathbb{R}^m,$$
and then into
$$Df(g(a))Dg(a)h \in T_{f(g(a))}\mathbb{R}^p.$$

<!-- page 97 -->

Thus the order of matrix multiplication is forced by the order of composition.
In coordinates, if
$$g = (g_1, \dots, g_m), \quad f = (f_1, \dots, f_p),$$
then the $(i, j)$ entry of the matrix identity gives
$$\frac{\partial (f_i \circ g)}{\partial x_j}(a) = \sum_{k=1}^m \frac{\partial f_i}{\partial y_k}(g(a)) \frac{\partial g_k}{\partial x_j}(a).$$
For a scalar-valued outer function $f : \mathbb{R}^m \to \mathbb{R}$, the same identity can be written using column gradients as
$$\nabla (f \circ g)(a) = J_g(a)^T \nabla f(g(a)).$$
The transpose appears because the scalar differential is naturally a row vector, while we represent the gradient as a column vector.

Example 5.25 — Reading the Jacobian Chain Rule
Let
$$g(x, y) = \begin{pmatrix} x + y \\ xy \end{pmatrix}, \quad \phi(u, v) = u^2 + e^v.$$
Then
$$J_g(x, y) = \begin{pmatrix} 1 & 1 \\ y & x \end{pmatrix}, \quad \nabla \phi(u, v) = \begin{pmatrix} 2u \\ e^v \end{pmatrix}.$$
Therefore
$$\nabla (\phi \circ g)(x, y) = J_g(x, y)^T \nabla \phi(g(x, y)),$$
so
$$\nabla (\phi \circ g)(x, y) = \begin{pmatrix} 1 & y \\ 1 & x \end{pmatrix} \begin{pmatrix} 2(x + y) \\ e^{xy} \end{pmatrix} = \begin{pmatrix} 2(x + y) + ye^{xy} \\ 2(x + y) + xe^{xy} \end{pmatrix}.$$
The matrix dimensions also check the order of multiplication.

5.6 Differentiable Curves and Tangent Directions
A path was defined earlier as a continuous mapping from an interval into Euclidean space. Differentiability adds a first-order direction of motion.

Definition 5.26 — Differentiable Curve and Velocity
Let $I \subseteq \mathbb{R}$ be an interval and let $t_0$ be an interior point of $I$. A curve
$$\gamma : I \to \mathbb{R}^n$$

<!-- page 98 -->

is differentiable at $t_0$ if
$$\gamma'(t_0) := \lim_{h \to 0} \frac{\gamma(t_0 + h) - \gamma(t_0)}{h}$$
exists.
If
$$\gamma = (\gamma_1, \dots, \gamma_n),$$
then
$$\gamma'(t_0) = \begin{pmatrix} \gamma_1'(t_0) \\ \vdots \\ \gamma_n'(t_0) \end{pmatrix}.$$
The vector $\gamma'(t_0)$ is the velocity vector or tangent vector of the curve at $\gamma(t_0)$.

Differentiability means
$$\gamma(t_0 + h) = \gamma(t_0) + h\gamma'(t_0) + o(|h|).$$
When $\gamma'(t_0) \neq 0$, the tangent line is
$$\ell(s) = \gamma(t_0) + s\gamma'(t_0).$$

[Image: A curve in the $x_1, x_2$ plane with a tangent line at $\gamma(t_0)$ pointing in the direction $\gamma'(t_0)$.]

Figure 11: A differentiable curve is approximated to first order by its tangent line.

Combining differentiable curves with the chain rule gives one of the most useful formulas in multivariable calculus.

Proposition 5.27 — Derivative Along a Curve
Let
$$\gamma : I \to U \subseteq \mathbb{R}^n$$

<!-- page 99 -->

be differentiable at an interior point $t_0 \in I$, and let
$$f : U \to \mathbb{R}^m$$
be differentiable at $\gamma(t_0)$. Then
$$\left. \frac{d}{dt} f(\gamma(t)) \right|_{t=t_0} = Df(\gamma(t_0))\gamma'(t_0).$$
If $f$ is scalar-valued,
$$\left. \frac{d}{dt} f(\gamma(t)) \right|_{t=t_0} = \nabla f(\gamma(t_0)) \cdot \gamma'(t_0).$$

Proof
Apply theorem 5.24 to the composition
$$t \mapsto \gamma(t) \mapsto f(\gamma(t)).$$
Since the derivative of $\gamma$ is the linear map
$$s \mapsto s\gamma'(t_0),$$
the chain rule gives the stated formula.

This gives a useful interpretation for dynamic models. If a state vector $x(t)$ evolves over time and $f(x)$ is a scalar quantity associated with the state, then
$$\frac{d}{dt} f(x(t)) = \nabla f(x(t)) \cdot \dot{x}(t).$$
The gradient describes the local sensitivity of the quantity in every direction; the velocity $\dot{x}(t)$ tells us which direction the state actually takes.

We can now prove the geometric statement suggested by figure 10.

Proposition 5.28 — Gradient Orthogonality to Level Sets
Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}$$
be differentiable, and suppose a differentiable curve
$$\gamma : I \to U$$

<!-- page 100 -->

lies in the level set
$$f(x) = c.$$
Then, at every interior point $t_0 \in I$,
$$\nabla f(\gamma(t_0)) \cdot \gamma'(t_0) = 0.$$
Thus the gradient is orthogonal to every tangent direction generated by a differentiable curve contained in the level set.

Proof
Since
$$f(\gamma(t)) = c$$
is constant in $t$,
$$0 = \left. \frac{d}{dt} f(\gamma(t)) \right|_{t=t_0} = \nabla f(\gamma(t_0)) \cdot \gamma'(t_0)$$
by proposition 5.27.

If $\nabla f(a) \neq 0$, this identifies the natural candidate for the tangent hyperplane to the level set $f(x) = f(a)$ at $a$:
$$T_a = \{a + h : \nabla f(a) \cdot h = 0\}.$$
The Implicit Function Theorem will later give conditions ensuring that the level set is locally a smooth surface and that this candidate is indeed its tangent space.

For the graph of a differentiable scalar function
$$z = f(x_1, \dots, x_n),$$
the first-order expansion
$$f(a + h) = f(a) + \nabla f(a) \cdot h + o(\|h\|)$$
gives the tangent hyperplane
$$z - f(a) = \nabla f(a) \cdot (x - a).$$
For $n = 2$ this is the familiar tangent plane to the graph of $z = f(x, y)$.

The chain rule and the curve calculation complete the first-order picture: the same derivative $Df(a)$ appears whether we compute in coordinates, move along a curve, or compose mappings. Higher-order analysis begins by asking how this first-order approximation changes from point to point.

<!-- page 101 -->

6 Mean-Value Theorems and Higher-Order Approximation
Differentiability describes an infinitesimal change. To control a finite move from $a$ to $a + h$, restrict the function to the line segment
$$t \mapsto a + th, \quad 0 \leq t \leq 1.$$
One-variable mean-value and Taylor theorems can then be applied to this restricted function. This simple device is the main tool throughout the section.

6.1 Mean-Value Theorems and Estimates
Let $a, b \in \mathbb{R}^n$ and write
$$h = b - a.$$
The line segment from $a$ to $b$ is
$$[a, b] = \{a + th : 0 \leq t \leq 1\}.$$
For a scalar-valued function $f$, define
$$\phi(t) = f(a + th).$$
By the chain rule,
$$\phi'(t) = Df(a + th)h = \nabla f(a + th) \cdot h.$$
Applying theorem 4.6 to this restriction immediately gives the multivariable result.

Theorem 6.1 — Mean-Value Theorem for Scalar Functions
Let $U \subseteq \mathbb{R}^n$ be open, let $a, b \in U$, and suppose
$$[a, b] \subseteq U.$$
If $f : U \to \mathbb{R}$ is continuous on $[a, b]$ and differentiable on the open segment $(a, b)$, then there exists
$$\xi = a + \theta(b - a), \quad 0 < \theta < 1,$$
such that
$$f(b) - f(a) = Df(\xi)(b - a) = \nabla f(\xi) \cdot (b - a).$$

Proof
Set
$$\phi(t) = f(a + t(b - a)), \quad 0 \leq t \leq 1.$$

<!-- page 102 -->

Theorem 4.6 gives some $\theta \in (0, 1)$ such that
$$\phi(1) - \phi(0) = \phi'(\theta).$$
The chain rule gives
$$\phi'(\theta) = Df(a + \theta(b - a))(b - a).$$
Taking $\xi = a + \theta(b - a)$ proves the claim.

By Cauchy-Schwarz,
$$|f(b) - f(a)| \leq \|\nabla f(\xi)\| \|b - a\|.$$
Hence, if the gradient is bounded on the segment,
$$|f(b) - f(a)| \leq \sup_{x \in [a, b]} \|\nabla f(x)\| \|b - a\|.$$
This inequality is often more useful than the exact equality.

The exact equality, however, is special to scalar-valued functions. It need not hold for a mapping $F : U \to \mathbb{R}^m$ with $m > 1$. For example,
$$F(t) = (\cos t, \sin t), \quad 0 \leq t \leq 2\pi,$$
satisfies
$$F(2\pi) - F(0) = 0,$$
while $F'(t) \neq 0$ for every $t$. Thus there is no single intermediate point that reproduces the whole vector increment.

What does survive is the norm estimate.

Theorem 6.2 — Mean-Value Estimate for Mappings
Let $U \subseteq \mathbb{R}^n$ be open, let $a, b \in U$, and suppose
$$[a, b] \subseteq U.$$
If $F : U \to \mathbb{R}^m$ is continuously differentiable on a neighborhood of $[a, b]$, then
$$\|F(b) - F(a)\| \leq \|b - a\| \max_{x \in [a, b]} \|DF(x)\|_{\text{op}}.$$

<!-- page 103 -->

Proof
If $F(b) = F(a)$, the result is immediate. Otherwise set
$$u = \frac{F(b) - F(a)}{\|F(b) - F(a)\|}$$
and consider the scalar function
$$\phi(t) = u \cdot F(a + t(b - a)).$$
For some $\theta \in (0, 1)$, the scalar mean-value theorem gives
$$\phi(1) - \phi(0) = \phi'(\theta).$$
The left-hand side is $\|F(b) - F(a)\|$. If
$$\xi = a + \theta(b - a),$$
then
$$\phi'(\theta) = u \cdot DF(\xi)(b - a).$$
Therefore
$$\|F(b) - F(a)\| \leq \|DF(\xi)(b - a)\|$$
$$\leq \|DF(\xi)\|_{\text{op}} \|b - a\|,$$
which gives the stated estimate.

Corollary 6.3 — Bounded Derivative Implies Lipschitz
Let $U \subseteq \mathbb{R}^n$ be convex and open, and let $F : U \to \mathbb{R}^m$ be continuously differentiable. If
$$\|DF(x)\|_{\text{op}} \leq M \quad \text{for all } x \in U,$$
then
$$\|F(x) - F(y)\| \leq M\|x - y\| \quad \text{for all } x, y \in U.$$
The same estimate also quantifies the first-order error. Applying the theorem to
$$G(x) = F(x) - DF(a)x$$
gives
$$\|F(a + h) - F(a) - DF(a)h\| \leq \|h\| \max_{0 \leq t \leq 1} \|DF(a + th) - DF(a)\|_{\text{op}}.$$
(1)

<!-- page 104 -->

If $DF$ is continuous at $a$, the factor on the right tends to zero with $h$. Thus (1) recovers
$$F(a + h) - F(a) - DF(a)h = o(\|h\|).$$

6.2 Second and Higher-Order Derivatives
For first derivatives, there is only one differentiation to perform. Beginning with second derivatives, a new issue appears: there are several variables, so we must keep track of the order in which differentiation is carried out.

Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}.$$
If the partial derivative $\partial_i f$ is itself differentiable with respect to $x_j$, we write
$$f_{ij}(a) := \frac{\partial}{\partial x_j} \left( \frac{\partial f}{\partial x_i} \right)(a).$$
Thus $f_{ij}$ means: first differentiate with respect to $x_i$, then with respect to $x_j$. Equivalently,
$$f_{ij}(a) = \frac{\partial^2 f}{\partial x_j \partial x_i}(a).$$
At this stage one should not assume that $f_{ij} = f_{ji}$. The equality of mixed partial derivatives requires an additional regularity condition and will be proved in the next subsection.

Higher-order partial derivatives are defined recursively. For indices $i_1, \dots, i_r \in \{1, \dots, n\}$, write
$$f_{i_1 \dots i_r} := \partial_{i_r} \dots \partial_{i_2} \partial_{i_1} f.$$
For example,
$$f_{123} = \frac{\partial}{\partial x_3} \left( \frac{\partial}{\partial x_2} \left( \frac{\partial f}{\partial x_1} \right) \right).$$

Definition 6.4 — $C^k$ Functions
Let $U \subseteq \mathbb{R}^n$ be open. A scalar function $f : U \to \mathbb{R}$ is of class $C^k$ if every partial derivative of order at most $k$ exists and is continuous on $U$.
A mapping $F : U \to \mathbb{R}^m$ is of class $C^k$ if each component function is of class $C^k$.

The notation $C^k$ is useful because continuous mixed partials can be reordered. That fact is what makes the formulas below much simpler.

<!-- page 105 -->

6.3 The Hessian and Symmetry of Second Derivatives
Consider first a function of two variables. Suppose both $f_{xy}$ and $f_{yx}$ exist near $(x_0, y_0)$. There is no purely formal reason for them to be equal. The equality follows from continuity.

Theorem 6.5 — Equality of Mixed Second Partial Derivatives
Let $f$ be defined in a neighborhood of $(x_0, y_0) \in \mathbb{R}^2$. Suppose $f_{xy}$ and $f_{yx}$ exist in that neighborhood and are continuous at $(x_0, y_0)$. Then
$$f_{xy}(x_0, y_0) = f_{yx}(x_0, y_0).$$

Proof
It is enough to prove the result for two coordinates. Choose $h$ and $k$ sufficiently small that the rectangle with vertices
$$a, \quad a + he_i, \quad a + ke_j, \quad a + he_i + ke_j$$
lies in the neighborhood on which the two mixed partials are continuous. Define the rectangular increment
$$\Delta(h, k) = f(a + he_i + ke_j) - f(a + he_i) - f(a + ke_j) + f(a).$$
First take the difference in the $e_i$ direction. Applying the one-dimensional mean-value theorem to
$$s \mapsto f(a + se_i + ke_j) - f(a + se_i)$$
between $0$ and $h$ gives some $\xi$ between $0$ and $h$ such that
$$\Delta(h, k) = h[\partial_i f(a + \xi e_i + ke_j) - \partial_i f(a + \xi e_i)].$$
Applying the mean-value theorem once more, now in the $e_j$ direction, gives some $\eta$ between $0$ and $k$ such that
$$\Delta(h, k) = hk \partial_j \partial_i f(a + \xi e_i + \eta e_j).$$
Repeating the same argument in the opposite order gives numbers $\tilde{\xi}$ between $0$ and $h$ and $\tilde{\eta}$ between $0$ and $k$ such that
$$\Delta(h, k) = hk \partial_i \partial_j f(a + \tilde{\xi} e_i + \tilde{\eta} e_j).$$
For $hk \neq 0$ we may divide by $hk$. Letting $(h, k) \to (0, 0)$ and using continuity of the two mixed partials at $a$ yields
$$\partial_{ji} f(a) = \partial_{ij} f(a).$$
The two-variable theorem immediately gives the general result: freeze all coordinates except $x_i$ and $x_j$.

<!-- page 106 -->

Corollary 6.6 — Symmetry of Mixed Partials
If $f \in C^2(U)$, then
$$f_{ij}(a) = f_{ji}(a) \quad \text{for every } a \in U \text{ and every } i, j.$$
More generally, if $f \in C^k(U)$, then a partial derivative of order $r \leq k$ is unchanged when the order of differentiation is permuted.

For a $C^2$ function, the second partial derivatives can therefore be collected into a symmetric matrix.

Definition 6.7 — Hessian Matrix
Let $f \in C^2(U)$. The Hessian matrix of $f$ at $a \in U$ is
$$H_f(a) := \begin{pmatrix} f_{11}(a) & \dots & f_{1n}(a) \\ \vdots & \ddots & \vdots \\ f_{n1}(a) & \dots & f_{nn}(a) \end{pmatrix}.$$
By corollary 6.6,
$$H_f(a)^T = H_f(a).$$

Given a displacement $h = (h_1, \dots, h_n)$, the associated quadratic form is
$$h^T H_f(a) h = \sum_{i=1}^n \sum_{j=1}^n f_{ij}(a) h_i h_j.$$
For a twice differentiable scalar function, this is exactly the second differential evaluated twice in the direction $h$:
$$D^2 f(a)[h, h] = h^T H_f(a) h.$$
We will see this expression arise automatically when we differentiate $t \mapsto f(a + th)$ twice.

6.4 Taylor’s Theorem
The most transparent route to Taylor’s theorem is to return to the line restriction
$$\phi(t) = f(a + th), \quad 0 \leq t \leq 1.$$
The first derivative is
$$\phi'(t) = \sum_{i=1}^n f_i(a + th)h_i.$$

<!-- page 107 -->

Differentiating again gives
$$\phi''(t) = \sum_{i=1}^n \sum_{j=1}^n f_{ij}(a + th)h_i h_j = h^T H_f(a + th)h.$$
The pattern continues.

Proposition 6.8 — Derivatives Along a Line
Let $f \in C^k(U)$ and suppose $[a, a + h] \subseteq U$. Define
$$\phi(t) = f(a + th).$$
Then, for $1 \leq r \leq k$,
$$\phi^{(r)}(t) = \sum_{i_1=1}^n \dots \sum_{i_r=1}^n f_{i_1 \dots i_r}(a + th) h_{i_1} \dots h_{i_r}.$$

Proof
The formula for $r = 1$ is the chain rule. Suppose it holds for some $r < k$. Differentiate with respect to $t$. Since the factors $h_{i_1}, \dots, h_{i_r}$ are constant,
$$\phi^{(r+1)}(t) = \sum_{i_1, \dots, i_r} \frac{d}{dt} f_{i_1 \dots i_r}(a + th) h_{i_1} \dots h_{i_r}$$
$$= \sum_{i_1, \dots, i_r} \sum_{i_{r+1}=1}^n f_{i_1 \dots i_{r+1}}(a + th) h_{i_1} \dots h_{i_r} h_{i_{r+1}}.$$
This is the desired formula for $r + 1$.

Now apply theorem 4.12 to $\phi$ between 0 and 1.

Theorem 6.9 — Taylor’s Theorem
Let $f \in C^{k+1}(U)$ and suppose $[a, a + h] \subseteq U$. Then there exists
$$\xi = a + \theta h, \quad 0 < \theta < 1,$$

<!-- page 108 -->

such that
$$f(a + h) = f(a) + \sum_i f_i(a) h_i$$
$$+ \frac{1}{2!} \sum_{i, j} f_{ij}(a) h_i h_j + \dots$$
$$+ \frac{1}{k!} \sum_{i_1, \dots, i_k} f_{i_1 \dots i_k}(a) h_{i_1} \dots h_{i_k}$$
$$+ \frac{1}{(k+1)!} \sum_{i_1, \dots, i_{k+1}} f_{i_1 \dots i_{k+1}}(\xi) h_{i_1} \dots h_{i_{k+1}}.$$
Every index in each displayed sum runs from 1 to $n$.

Proof
Apply theorem 4.12 to
$$\phi(t) = f(a + th)$$
at $t = 0$, evaluated at $t = 1$. For some $\theta \in (0, 1)$,
$$\phi(1) = \sum_{r=0}^k \frac{\phi^{(r)}(0)}{r!} + \frac{\phi^{(k+1)}(\theta)}{(k+1)!}.$$
Substitute the formulas from proposition 6.8. Since $\phi(1) = f(a + h)$, the stated expansion follows.

Repeated index sums quickly become cumbersome. Multi-index notation compresses them without changing the underlying calculation.

Definition 6.10 — Multi-Index Notation
A multi-index is
$$\alpha = (\alpha_1, \dots, \alpha_n) \in \mathbb{N}_0^n.$$
We write
$$|\alpha| = \alpha_1 + \dots + \alpha_n, \quad \alpha! = \alpha_1! \dots \alpha_n!,$$
$$h^\alpha = h_1^{\alpha_1} \dots h_n^{\alpha_n}, \quad \partial^\alpha f = \frac{\partial^{|\alpha|} f}{\partial x_1^{\alpha_1} \dots \partial x_n^{\alpha_n}}.$$
Because mixed partials of a $C^k$ function can be permuted, terms in the repeated sums can be grouped according to how many times each coordinate appears. The multinomial coefficient gives
$$\frac{1}{r!} \sum_{i_1, \dots, i_r} f_{i_1 \dots i_r}(a) h_{i_1} \dots h_{i_r} = \sum_{|\alpha|=r} \frac{\partial^\alpha f(a)}{\alpha!} h^\alpha.$$

<!-- page 109 -->

Hence Taylor's polynomial through order $k$ can be written compactly as
$$T_k f(a; h) = \sum_{|\alpha| \le k} \frac{\partial^\alpha f(a)}{\alpha!} h^\alpha.$$
When the same direction $h$ is repeated, it is convenient to abbreviate
$$D^r f(x)[h^r] := \sum_{i_1, \dots, i_r} f_{i_1 \dots i_r}(x) h_{i_1} \cdots h_{i_r}.$$
The integral form of the remainder links Taylor approximation directly to the Fundamental Theorem of Calculus.

::: {.theorem}
**Theorem 6.11 — Taylor's Theorem with Integral Remainder**

Let $f \in C^{k+1}(U)$ and suppose $[a, a + h] \subseteq U$. Then
$$f(a + h) = \sum_{r=0}^k \frac{1}{r!} D^r f(a)[h^r] + \frac{1}{k!} \int_0^1 (1 - t)^k D^{k+1} f(a + th)[h^{k+1}] \, dt,$$
where $D^0 f(a)[h^0]$ means $f(a)$.
:::

::: {.proof}
Set
$$\phi(t) = f(a + th), \quad 0 \le t \le 1.$$
By the line-derivative formula,
$$\phi^{(r)}(t) = D^r f(a + th)[h^r].$$
We first recall the one-variable integral-remainder identity. Repeated integration by parts gives
$$\frac{1}{k!} \int_0^1 (1 - t)^k \phi^{(k+1)}(t) \, dt = \phi(1) - \sum_{r=0}^k \frac{\phi^{(r)}(0)}{r!}.$$
Indeed, one integration by parts lowers the derivative order by one and produces the boundary term $\phi^{(k)}(0)/k!$; iterating this operation down to $\phi'$ yields the displayed identity.
Rearranging and substituting
$$\phi(1) = f(a + h), \quad \phi^{(r)}(0) = D^r f(a)[h^r],$$
:::

<!-- page 110 -->

gives
$$f(a + h) = \sum_{r=0}^k \frac{1}{r!} D^r f(a)[h^r] + \frac{1}{k!} \int_0^1 (1 - t)^k D^{k+1} f(a + th)[h^{k+1}] \, dt.$$
This form is often preferable for estimates: instead of an unknown intermediate point $\xi$, the remainder is an average of the $(k+1)$st directional derivative along the whole segment from $a$ to $a + h$.

For local analysis, the most useful form is the Peano remainder.

::: {.theorem}
**Theorem 6.12 — Taylor's Theorem with Peano Remainder**

If $f \in C^k$ in a neighborhood of $a$, then, as $h \to 0$,
$$f(a + h) = \sum_{|\alpha| \le k} \frac{\partial^\alpha f(a)}{\alpha!} h^\alpha + o(\|h\|^k).$$
:::

::: {.proof}
For $k = 1$, the statement is the definition of differentiability. Assume $k \ge 2$. Apply the Lagrange form of Taylor's theorem one order lower. For all sufficiently small $h$, there is a point
$$\xi = a + \theta h, \quad \theta \in (0, 1),$$
such that
$$f(a + h) = \sum_{|\alpha| \le k-1} \frac{\partial^\alpha f(a)}{\alpha!} h^\alpha + \sum_{|\alpha| = k} \frac{\partial^\alpha f(\xi)}{\alpha!} h^\alpha.$$
Add and subtract the order-$k$ terms evaluated at $a$. The remainder becomes
$$R(h) = \sum_{|\alpha| = k} \frac{\partial^\alpha f(\xi) - \partial^\alpha f(a)}{\alpha!} h^\alpha.$$
Since $|h_i| \le \|h\|$, every multi-index with $|\alpha| = k$ satisfies
$$|h^\alpha| \le \|h\|^k.$$
Therefore
$$\frac{|R(h)|}{\|h\|^k} \le \sum_{|\alpha| = k} \frac{|\partial^\alpha f(\xi) - \partial^\alpha f(a)|}{\alpha!}.$$
There are only finitely many multi-indices of order $k$, and $\xi = a + \theta h \to a$ as $h \to 0$. Because
:::

<!-- page 111 -->

$f \in C^k$, every term on the right tends to zero. Hence
$$R(h) = o(\|h\|^k).$$
The case $k = 2$ is the formula used most often:
$$f(a + h) = f(a) + \nabla f(a) \cdot h + \frac{1}{2} h^T H_f(a) h + o(\|h\|^2). \quad (2)$$
This is the exact second-order analogue of differentiability.

::: {.example}
**Example 6.13 — Second-Order Expansion in Two Variables**

Let
$$f(x, y) = e^x \cos y.$$
At $(0, 0)$,
$$f(0, 0) = 1, \quad \nabla f(0, 0) = \begin{pmatrix} 1 \\ 0 \end{pmatrix}, \quad H_f(0, 0) = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}.$$
Therefore, as $(x, y) \to (0, 0)$,
$$e^x \cos y = 1 + x + \frac{1}{2}(x^2 - y^2) + o(x^2 + y^2).$$
The linear term gives the first-order slope; the quadratic term records the leading correction in each direction.
:::

### 6.5 Local Quadratic Approximation
Equation (2) says that near $a$ the function is approximated by
$$Q_a(h) = f(a) + \nabla f(a) \cdot h + \frac{1}{2} h^T H_f(a) h.$$
The linear term describes the local slope. The quadratic term describes how that slope changes as we move away from $a$.
For a two-variable function this takes the familiar form
$$f(a_1 + h_1, a_2 + h_2) = f(a) + f_1(a)h_1 + f_2(a)h_2 + \frac{1}{2} [f_{11}(a)h_1^2 + 2f_{12}(a)h_1h_2 + f_{22}(a)h_2^2] + o(\|h\|^2).$$
The cross term has coefficient $2f_{12}$ because $f_{12} = f_{21}$.
At an interior local extremum, the linear term must disappear.

<!-- page 112 -->

::: {.proposition}
**Proposition 6.14 — First-Order Necessary Condition**

Let $U \subseteq \mathbb{R}^n$ be open and let $f : U \to \mathbb{R}$ be differentiable at $a \in U$. If $a$ is a local maximum or local minimum of $f$, then
$$\nabla f(a) = 0.$$
:::

::: {.proof}
Fix a coordinate direction $e_i$ and define
$$\phi_i(t) = f(a + te_i).$$
Because $a$ is a local extremum of $f$, $t = 0$ is a local extremum of $\phi_i$. Hence
$$0 = \phi_i'(0) = \partial_i f(a).$$
This holds for every $i$, so $\nabla f(a) = 0.$
:::

::: {.definition}
**Definition 6.15 — Critical Point**

A point $a$ at which
$$\nabla f(a) = 0$$
is called a **critical point** or **stationary point** of $f$.
:::

At a critical point, (2) simplifies to
$$f(a + h) - f(a) = \frac{1}{2} h^T H_f(a) h + o(\|h\|^2).$$
Thus, whenever the quadratic form $h^T H_f(a) h$ has a definite sign, it determines the local behavior.

::: {.theorem}
**Theorem 6.16 — Second-Order Test at a Critical Point**

Let $f \in C^2(U)$ and suppose $\nabla f(a) = 0$.
(i) If $H_f(a)$ is positive definite, then $a$ is a strict local minimum.
(ii) If $H_f(a)$ is negative definite, then $a$ is a strict local maximum.
(iii) If $H_f(a)$ is indefinite, then $a$ is neither a local minimum nor a local maximum.
:::

<!-- page 113 -->

::: {.proof}
Suppose first that $H_f(a)$ is positive definite. Consider the quadratic form
$$q(u) = u^T H_f(a) u$$
on the unit sphere
$$S^{n-1} = \{u \in \mathbb{R}^n : \|u\| = 1\}.$$
Since $q$ is continuous and strictly positive on the compact set $S^{n-1}$, there exists $c > 0$ such that
$$u^T H_f(a) u \ge c \quad \text{for every } \|u\| = 1.$$
Hence, for every $h \ne 0$,
$$h^T H_f(a) h = \|h\|^2 \left( \frac{h}{\|h\|} \right)^T H_f(a) \left( \frac{h}{\|h\|} \right) \ge c\|h\|^2.$$
Because $\nabla f(a) = 0$, the second-order expansion gives
$$f(a + h) - f(a) = \frac{1}{2} h^T H_f(a) h + o(\|h\|^2).$$
Therefore
$$f(a + h) - f(a) \ge \frac{c}{2} \|h\|^2 + o(\|h\|^2) = \|h\|^2 \left( \frac{c}{2} + o(1) \right).$$
For all sufficiently small nonzero $h$, the term in parentheses is positive. Thus
$$f(a + h) > f(a),$$
so $a$ is a strict local minimum.
The negative-definite case follows by applying the same argument to $-f$.
Finally, suppose $H_f(a)$ is indefinite. Then there exist vectors $u$ and $v$ such that
$$u^T H_f(a) u > 0, \quad v^T H_f(a) v < 0.$$
Along $h = tu$,
$$f(a + tu) - f(a) = \frac{t^2}{2} u^T H_f(a) u + o(t^2) > 0$$
for all sufficiently small nonzero $t$, whereas along $h = tv$,
$$f(a + tv) - f(a) = \frac{t^2}{2} v^T H_f(a) v + o(t^2) < 0.$$
Hence arbitrarily close to $a$ there are points at which $f$ is both larger and smaller than $f(a)$.
Therefore $a$ is neither a local minimum nor a local maximum.
:::

<!-- page 114 -->

::: {.example}
**Example 6.17 — Reading the Hessian**

Consider
$$f(x, y) = x^2 + xy + y^2.$$
The origin is a critical point and
$$H_f(0, 0) = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix}.$$
Its eigenvalues are 1 and 3, so the Hessian is positive definite. The second-order test therefore gives a strict local minimum at the origin. In this example the conclusion is global because
$$f(x, y) = \frac{1}{2}(x + y)^2 + \frac{1}{2}(x^2 + y^2) \ge 0.$$
By contrast,
$$g(x, y) = x^2 - y^2$$
has Hessian $\text{diag}(2, -2)$ at the origin. The quadratic form is positive along the $x$-axis and negative along the $y$-axis, so the origin is a saddle point.
:::

![Figure 12: Level sets of the quadratic term $h^T Hh$. A positive-definite Hessian produces nested ellipses around the critical point; an indefinite Hessian produces hyperbolic level sets and a saddle.](figure12.png)

::: {.remark}
**Remark 6.18 — Semidefinite Hessians Are Inconclusive**

If the Hessian is only positive semidefinite or negative semidefinite, the quadratic term can vanish in some directions. Higher-order terms may then decide the local behavior. For example,
$$x^4, \quad -x^4, \quad x^3$$
all have first and second derivatives equal to zero at 0, but 0 is, respectively, a strict local minimum, a strict local maximum, and neither.
:::

<!-- page 115 -->

For later use, the main approximation to remember is
$$f(a + h) = f(a) + \nabla f(a) \cdot h + \frac{1}{2} h^T H_f(a) h + o(\|h\|^2).$$

### 7 Fixed Points and Local Solvability
Approximation becomes useful only when it leads to an actual solution. Two tools do this here. A contraction turns an equation into an iteration that converges, while an invertible derivative allows a nonlinear mapping to be inverted locally. The Banach fixed-point theorem supplies the first tool; the inverse and implicit function theorems supply the second. In fact, the proof of the inverse function theorem below is itself a contraction argument.

### 7.1 Lipschitz and Contraction Mappings
Continuity says that nearby points have nearby images. For fixed-point arguments we need a quantitative version of this idea.

::: {.definition}
**Definition 7.1 — Lipschitz Mapping**

Let $D \subseteq \mathbb{R}^n$. A mapping
$$T : D \to \mathbb{R}^m$$
is **Lipschitz** on $D$ if there exists a constant $L \ge 0$ such that
$$\|T(x) - T(y)\| \le L\|x - y\| \quad \text{for all } x, y \in D.$$
Any such $L$ is called a **Lipschitz constant** for $T$.
:::

A Lipschitz mapping is automatically uniformly continuous. Indeed, if $L > 0$, then
$$\|x - y\| < \frac{\varepsilon}{L}$$
implies
$$\|T(x) - T(y)\| < \varepsilon.$$
The important point is that the same constant $L$ controls the mapping throughout the entire set $D$.
The derivative gives a convenient way to obtain such a bound.

::: {.proposition}
**Proposition 7.2 — Derivative Bound Implies Lipschitz Continuity**

Let $C \subseteq \mathbb{R}^n$ be convex, let $U \supseteq C$ be open, and let
$$T : U \to \mathbb{R}^m$$
:::

<!-- page 116 -->

be of class $C^1$. If
$$\|DT(x)\| \le L \quad \text{for every } x \in C,$$
then
$$\|T(x) - T(y)\| \le L\|x - y\| \quad \text{for all } x, y \in C.$$
:::

::: {.proof}
For $x, y \in C$, the whole line segment $[x, y]$ lies in $C$. The vector-valued mean-value estimate from theorem 6.2 gives
$$\|T(y) - T(x)\| \le \|y - x\| \sup_{z \in [x, y]} \|DT(z)\|.$$
The derivative bound therefore yields
$$\|T(y) - T(x)\| \le L\|y - x\|.$$
:::

The special case $L < 1$ is much stronger. Such a mapping strictly reduces distances.

::: {.definition}
**Definition 7.3 — Contraction Mapping and Fixed Point**

Let $D \subseteq \mathbb{R}^n$ and let
$$T : D \to D.$$
The mapping $T$ is a **contraction** if there exists a number
$$0 \le q < 1$$
such that
$$\|T(x) - T(y)\| \le q\|x - y\| \quad \text{for all } x, y \in D.$$
The number $q$ is called a **contraction constant**.
A point $x^* \in D$ is a **fixed point** of $T$ if
$$T(x^*) = x^*.$$
:::

The requirement $T : D \to D$ matters. A mapping may shrink distances but still move points outside the set on which we want to iterate it. In applications one therefore checks two separate facts:
$$T(D) \subseteq D \quad \text{and} \quad \|T(x) - T(y)\| \le q\|x - y\|, \quad q < 1.$$
A useful practical criterion follows immediately from proposition 7.2.

<!-- page 117 -->

::: {.corollary}
**Corollary 7.4 — Derivative Criterion for a Contraction**

Let $C \subseteq \mathbb{R}^n$ be convex and let $T : C \to C$ extend to a $C^1$ mapping on a neighborhood of $C$. If
$$\sup_{x \in C} \|DT(x)\| \le q < 1,$$
then $T$ is a contraction on $C$.
:::

### 7.2 The Banach Fixed-Point Theorem
A contraction does more than merely suggest where a fixed point might be. On a complete set it forces a unique fixed point, and repeated iteration converges to it from any starting point.
In Euclidean space, every closed subset is complete. Thus the result below can be stated directly for closed subsets of $\mathbb{R}^n$.

::: {.theorem}
**Theorem 7.5 — Banach Fixed-Point Theorem**

Let $D \subseteq \mathbb{R}^n$ be nonempty and closed, and let
$$T : D \to D$$
be a contraction with contraction constant $q \in [0, 1)$. Then:
(i) $T$ has a unique fixed point $x^* \in D$;
(ii) for every starting point $x_0 \in D$, the iteration
$$x_{k+1} = T(x_k), \quad k = 0, 1, 2, \dots,$$
converges to $x^*$;
(iii) the error satisfies
$$\|x^* - x_k\| \le \frac{q^k}{1 - q} \|x_1 - x_0\|.$$
:::

::: {.proof}
Start from any $x_0 \in D$ and define
$$x_{k+1} = T(x_k).$$
Because $T$ is a contraction,
$$\|x_{k+1} - x_k\| \le q\|x_k - x_{k-1}\|.$$
:::

<!-- page 118 -->

Iterating this inequality gives
$$\|x_{k+1} - x_k\| \le q^k \|x_1 - x_0\|.$$
Now let $m > k$. By the triangle inequality,
$$\|x_m - x_k\| \le \sum_{j=k}^{m-1} \|x_{j+1} - x_j\|$$
$$\le \sum_{j=k}^{m-1} q^j \|x_1 - x_0\|$$
$$\le \frac{q^k}{1 - q} \|x_1 - x_0\|.$$
The right-hand side tends to zero as $k \to \infty$, so $\{x_k\}$ is a Cauchy sequence. Since $D$ is closed in the complete space $\mathbb{R}^n$, there exists $x^* \in D$ such that
$$x_k \to x^*.$$
A contraction is Lipschitz and therefore continuous. Hence
$$T(x^*) = T\left( \lim_{k \to \infty} x_k \right) = \lim_{k \to \infty} T(x_k) = \lim_{k \to \infty} x_{k+1} = x^*.$$
Thus $x^*$ is a fixed point.
If $y^*$ is another fixed point, then
$$\|x^* - y^*\| = \|T(x^*) - T(y^*)\| \le q\|x^* - y^*\|.$$
Since $q < 1$, this is possible only if $x^* = y^*$.
Finally, letting $m \to \infty$ in the preceding Cauchy estimate yields
$$\|x^* - x_k\| \le \frac{q^k}{1 - q} \|x_1 - x_0\|.$$
The geometric-series estimate is the mechanism behind convergence:
$$\|x_{k+1} - x_k\| \le q^k \|x_1 - x_0\|.$$
The total distance still left to travel is therefore bounded by the tail of a geometric series.

<!-- page 119 -->

::: {.example}
**Example 7.6 — Solving $x = \cos x$ by Iteration**

Consider
$$T(x) = \cos x$$
on the interval $D = [0, 1]$. Since
$$\cos 1 \le \cos x \le 1,$$
we have $T(D) \subseteq D$. Moreover,
$$|T'(x)| = |\sin x| \le \sin 1 < 1 \quad \text{for } x \in [0, 1].$$
Thus $T$ is a contraction on $[0, 1]$. The equation
$$x = \cos x$$
therefore has a unique solution $x^* \in [0, 1]$, and the iteration
$$x_{k+1} = \cos x_k$$
converges to $x^*$ from every $x_0 \in [0, 1]$.
:::

![Figure 13: Cobweb iteration for $x_{k+1} = \cos x_k$. Alternating vertical moves to $y = T(x)$ and horizontal moves to $y = x$ make the contraction toward the unique fixed point visible.](figure13.png)

The error can also be bounded using two successive iterates. Starting the geometric-series estimate

<!-- page 120 -->

at step $k$ gives
$$\|x^* - x_k\| \le \sum_{j=k}^{\infty} \|x_{j+1} - x_j\|$$
$$\le \frac{1}{1 - q} \|x_{k+1} - x_k\|$$
$$\le \frac{q}{1 - q} \|x_k - x_{k-1}\|.$$
This *a posteriori* bound is useful computationally because every quantity on the right is observed during the iteration.
For $x_{k+1} = \cos x_k$ with $x_0 = 1$, the first few iterates are

| $k$ | $x_k$ |
| :--- | :--- |
| 0 | 1.000000 |
| 1 | 0.540302 |
| 2 | 0.857553 |
| 3 | 0.654290 |
| 4 | 0.793480 |
| 5 | 0.701369 |

The sequence oscillates, but the contraction estimate guarantees that the oscillations shrink geometrically and that the iterates converge to the unique fixed point.

### 7.3 The Inverse Function Theorem
For a linear map
$$A : \mathbb{R}^n \to \mathbb{R}^n,$$
solving
$$Ax = y$$
for $x$ is possible for every $y$ exactly when $A$ is invertible. The inverse function theorem says that the same principle survives locally for nonlinear mappings: if the derivative is invertible at a point, then the nonlinear mapping itself is invertible near that point.
Before stating the theorem, it is important to emphasize the word *locally*. A mapping can have an invertible derivative at every point and still fail to be globally one-to-one.
For example,
$$f(x, y) = \begin{pmatrix} x^2 - y^2 \\ 2xy \end{pmatrix}$$
has
$$\det Df(x, y) = 4(x^2 + y^2),$$

<!-- page 121 -->

which is nonzero away from the origin. Nevertheless,
$$f(x, y) = f(-x, -y),$$
so $f$ is not globally one-to-one on $\mathbb{R}^2 \setminus \{0\}$. The theorem asserts invertibility only on a sufficiently small neighborhood of each nonzero point.

**Theorem 7.7 — Inverse Function Theorem**
Let $U \subseteq \mathbb{R}^n$ be open, let
$$f : U \to \mathbb{R}^n$$
be of class $C^1$, and let $a \in U$. Suppose
$$Df(a)$$
is invertible, equivalently
$$\det Df(a) \neq 0.$$
Set $b = f(a)$. Then there exist open neighborhoods
$$U_0 \ni a, \quad V_0 \ni b,$$
such that
$$f : U_0 \to V_0$$
is one-to-one and onto. Its inverse
$$g = f^{-1} : V_0 \to U_0$$
is of class $C^1$, and
$$Dg(y) = [Df(g(y))]^{-1}.$$
In particular,
$$Dg(b) = [Df(a)]^{-1}.$$

**Proof**
Let
$$A = Df(a), \quad b = f(a).$$
Since $A$ is invertible, translate the point $a$ to the origin and normalize the derivative by defining
$$W := \{h \in \mathbb{R}^n : a + h \in U\}, \quad \tilde{f}(h) = A^{-1}(f(a + h) - b).$$
The set $W$ is open and contains 0, while
$$\tilde{f}(0) = 0, \quad D\tilde{f}(0) = I.$$

<!-- page 122 -->

Define the nonlinear remainder
$$R(h) = h - \tilde{f}(h).$$
Then $R(0) = 0$ and $DR(0) = 0$. By continuity of $DR$, choose $r > 0$ so that
$$\bar{B}_r(0) \subset W$$
and
$$\|DR(h)\| \leq \frac{1}{2} \quad \text{for every } h \in \bar{B}_r(0).$$
Because the closed ball is convex, the derivative bound implies
$$\|R(h_1) - R(h_2)\| \leq \frac{1}{2}\|h_1 - h_2\| \quad (h_1, h_2 \in \bar{B}_r(0)).$$
In particular,
$$\|\tilde{f}(h_1) - \tilde{f}(h_2)\| = \|(h_1 - h_2) - (R(h_1) - R(h_2))\|$$
$$\geq \frac{1}{2}\|h_1 - h_2\|. \quad (1)$$
Thus $\tilde{f}$ is one-to-one on $\bar{B}_r(0)$. The same derivative estimate also shows that, for every $h \in \bar{B}_r(0)$ and every $v \in \mathbb{R}^n$,
$$\|D\tilde{f}(h)v\| = \|v - DR(h)v\| \geq \frac{1}{2}\|v\|.$$
Hence $D\tilde{f}(h)$ is injective, and therefore invertible because it is a linear map from $\mathbb{R}^n$ to itself.
We next show that the image contains a neighborhood of the origin. Let
$$V = B_{r/2}(0).$$
For $\eta \in V$, define
$$T_\eta(h) = \eta + R(h), \quad h \in \bar{B}_r(0).$$
For such $h$,
$$\|T_\eta(h)\| \leq \|\eta\| + \|R(h) - R(0)\| < \frac{r}{2} + \frac{1}{2}r = r,$$
so $T_\eta$ maps $\bar{B}_r(0)$ into itself. Moreover,
$$\|T_\eta(h_1) - T_\eta(h_2)\| \leq \frac{1}{2}\|h_1 - h_2\|.$$
The Banach fixed-point theorem therefore gives a unique $h \in \bar{B}_r(0)$ satisfying
$$h = T_\eta(h).$$
Since $T_\eta$ actually takes values in the open ball $B_r(0)$, this fixed point lies in $B_r(0)$. The fixed-point

<!-- page 123 -->

equation is equivalent to
$$\tilde{f}(h) = \eta.$$
Set
$$W_0 = B_r(0) \cap \tilde{f}^{-1}(V).$$
This is an open neighborhood of 0. By the preceding existence result and the injectivity in (1),
$$\tilde{f} : W_0 \to V$$
is a bijection. Returning to the original coordinates, define
$$U_0 = a + W_0, \quad V_0 = b + AV.$$
Both sets are open neighborhoods of $a$ and $b$, respectively, and
$$f : U_0 \to V_0$$
is a bijection.
It remains to prove that the inverse is $C^1$. Let $g = f^{-1}$. From (1), if $y_i = f(x_i)$ with $x_i \in U_0$, then
$$\|x_1 - x_2\| \leq 2\|A^{-1}\|\|y_1 - y_2\|. \quad (2)$$
Thus $g$ is locally Lipschitz, in fact Lipschitz on $V_0$ with the displayed constant.
Fix $y \in V_0$ and put $x = g(y)$. For small $k$ with $y + k \in V_0$, write
$$g(y + k) = x + h.$$
By (2),
$$\|h\| = O(\|k\|).$$
Since $f(x + h) - f(x) = k$, differentiability of $f$ at $x$ gives
$$k = Df(x)h + r(h), \quad r(h) = o(\|h\|).$$
The derivative $Df(x) = A D\tilde{f}(x - a)$ is invertible by the estimate above. Therefore
$$h = Df(x)^{-1}k - Df(x)^{-1}r(h).$$
Because $\|h\| = O(\|k\|)$,
$$r(h) = o(\|h\|) = o(\|k\|),$$
and hence
$$g(y + k) - g(y) = Df(x)^{-1}k + o(\|k\|).$$

<!-- page 124 -->

Thus $g$ is differentiable at $y$ and
$$Dg(y) = Df(g(y))^{-1}.$$
Finally, $g$ is continuous by (2), $Df$ is continuous because $f \in C^1$, and matrix inversion is continuous on the set of nonsingular matrices. Hence $Dg$ is continuous, so $g \in C^1$.

The proof also gives a constructive interpretation. In normalized coordinates, the inverse value solving
$$\tilde{f}(h) = y$$
can be obtained from
$$h_{k+1} = y + h_k - \tilde{f}(h_k).$$
Thus local inversion is itself a problem of successive approximation.

**Remark 7.8 — Higher Smoothness of the Inverse**
If $f$ is of class $C^k$, $k \geq 1$, then the local inverse is also of class $C^k$. The starting point is
$$Dg(y) = [Df(g(y))]^{-1}.$$
Repeated differentiation, together with smoothness of matrix inversion on the set of nonsingular matrices, gives the higher-order result.

**Remark 7.9 — Invertible Derivative versus Mere Invertibility**
The hypothesis $\det Df(a) \neq 0$ guarantees a local inverse that is itself differentiable. It is not necessary for mere one-to-one invertibility. For example,
$$f(x) = x^3$$
is globally one-to-one, but $f'(0) = 0$, and its inverse $y \mapsto y^{1/3}$ is not differentiable at 0.

**7.4 The Implicit Function Theorem**
Many equations do not arrive in the explicit form
$$y = f(x).$$
Instead, the variables are linked by a relation
$$F(x, y) = 0.$$

<!-- page 125 -->

The implicit function theorem gives conditions under which this relation can be solved locally for $y$ as a function of $x$.
The simplest example is the unit circle,
$$F(x, y) = x^2 + y^2 - 1 = 0.$$
Near $(0, 1)$, the equation determines the upper branch
$$y = \sqrt{1 - x^2}.$$
The relevant derivative is
$$F_y(0, 1) = 2 \neq 0.$$
By contrast, at $(1, 0)$ we have $F_y(1, 0) = 0$: the circle cannot be represented there as a differentiable graph $y = \phi(x)$, although it can be represented as $x = \psi(y)$. Which variables can be solved for is therefore encoded in the appropriate partial derivative.

[Diagram showing a circle centered at origin, with a point $(0,1)$ labeled $F_y \neq 0: \text{solve } y = \phi(x)$ and a point $(1,0)$ labeled $F_y = 0: \text{vertical tangent}$]

Figure 14: For the circle $F(x, y) = x^2 + y^2 - 1 = 0$, the upper point has a nonvertical tangent and the relation can be solved locally as $y = \phi(x)$. At the rightmost point the tangent is vertical, so $y$ cannot be a differentiable function of $x$ there.

For the general theorem, split the variables into
$$x \in \mathbb{R}^m, \quad y \in \mathbb{R}^n,$$
and let
$$F : U \subseteq \mathbb{R}^{m+n} \to \mathbb{R}^n.$$
We write
$$D_x F(x, y)$$
for the $n \times m$ derivative matrix with respect to $x$, and
$$D_y F(x, y)$$
for the $n \times n$ derivative matrix with respect to $y$.

<!-- page 126 -->

**Theorem 7.10 — Implicit Function Theorem**
Let $U \subseteq \mathbb{R}^{m+n}$ be open and let
$$F : U \to \mathbb{R}^n$$
be of class $C^1$. Suppose
$$F(a, b) = 0, \quad (a, b) \in U,$$
and suppose
$$D_y F(a, b)$$
is invertible.
Then there exist open neighborhoods
$$A \subseteq \mathbb{R}^m \text{ of } a, \quad B \subseteq \mathbb{R}^n \text{ of } b,$$
and a unique $C^1$ mapping
$$\phi : A \to B$$
such that
$$\phi(a) = b$$
and
$$F(x, y) = 0 \iff y = \phi(x) \quad \text{for every } (x, y) \in A \times B.$$

**Proof**
Define
$$G : U \to \mathbb{R}^{m+n}, \quad G(x, y) = \begin{pmatrix} x \\ F(x, y) \end{pmatrix}.$$
At $(a, b)$,
$$DG(a, b) = \begin{pmatrix} I_m & 0 \\ D_x F(a, b) & D_y F(a, b) \end{pmatrix}.$$
This block-triangular matrix is invertible because $D_y F(a, b)$ is invertible. By the inverse function theorem, there are open neighborhoods
$$W \subseteq U \text{ of } (a, b), \quad Z \subseteq \mathbb{R}^{m+n} \text{ of } (a, 0),$$
such that
$$G : W \to Z$$
is a $C^1$ diffeomorphism.
Let
$$H = G^{-1} : Z \to W.$$

<!-- page 127 -->

If
$$H(u, v) = (x, y),$$
then
$$(u, v) = G(x, y) = (x, F(x, y)).$$
Hence the first component of $H(u, v)$ is necessarily $u$. We may therefore write
$$H(u, v) = \begin{pmatrix} u \\ \Psi(u, v) \end{pmatrix}$$
for a $C^1$ mapping $\Psi$ defined on $Z$.
Because $Z$ is open and contains $(a, 0)$, choose an open neighborhood $A_0$ of $a$ and an open neighborhood $C$ of 0 such that
$$A_0 \times C \subseteq Z.$$
Define
$$\phi(x) = \Psi(x, 0), \quad x \in A_0.$$
Then
$$G(x, \phi(x)) = (x, 0),$$
so
$$F(x, \phi(x)) = 0, \quad \phi(a) = b.$$
To obtain the stated product neighborhood, choose open neighborhoods $A_1$ of $a$ and $B$ of $b$ such that
$$A_1 \times B \subseteq W.$$
Since $\phi$ is continuous and $\phi(a) = b$, shrink the $x$-neighborhood if necessary and set
$$A \subseteq A_0 \cap A_1$$
so that
$$\phi(A) \subseteq B.$$
Now take $(x, y) \in A \times B$. If $F(x, y) = 0$, then
$$G(x, y) = (x, 0).$$
Both $(x, y)$ and $(x, \phi(x))$ lie in $W$, and $G$ is one-to-one on $W$. Therefore
$$y = \phi(x).$$

<!-- page 128 -->

The converse follows from $F(x, \phi(x)) = 0$. Thus
$$F(x, y) = 0 \iff y = \phi(x)$$
throughout $A \times B$. The same equivalence also proves uniqueness of the local mapping $\phi$.

The dimension count is worth noticing. There are $n$ equations and $n$ variables in $y$ to be solved for, while the $m$ variables in $x$ remain free. The invertibility of the $n \times n$ matrix $D_y F(a, b)$ says that, to first order, the equations respond independently enough to changes in the $y$ variables to determine those variables uniquely.

**Remark 7.11 — Higher Smoothness of the Implicit Function**
If $F$ is of class $C^k$, then the implicit mapping $\phi$ is also of class $C^k$. This follows from the corresponding higher-smoothness statement for the inverse function theorem applied to
$$G(x, y) = (x, F(x, y)).$$

**7.5 Differentiating Implicit Functions**
The implicit function theorem establishes existence and local uniqueness. Once the function exists, its derivative is obtained directly from the chain rule. This is often the part of the theorem used most frequently in applications.
Suppose
$$F(x, \phi(x)) = 0.$$
Differentiating both sides with respect to $x$ gives
$$D_x F(x, \phi(x)) + D_y F(x, \phi(x))D\phi(x) = 0.$$
Because $D_y F(a, b)$ is invertible and $D_y F$ is continuous, after shrinking the neighborhoods in the implicit function theorem if necessary, $D_y F(x, \phi(x))$ remains invertible for every $x$ under consideration. We may therefore solve this linear equation for $D\phi(x)$.

**Corollary 7.12 — Derivative of an Implicit Function**
Under the hypotheses of theorem 7.10,
$$D\phi(x) = -[D_y F(x, \phi(x))]^{-1}D_x F(x, \phi(x)).$$
In particular,
$$D\phi(a) = -[D_y F(a, b)]^{-1}D_x F(a, b).$$

<!-- page 129 -->

The dimensions provide a useful check on the formula:
$$\underbrace{D_y F}_{n \times n} \underbrace{D\phi}_{n \times m} + \underbrace{D_x F}_{n \times m} = 0.$$
For one equation in two variables,
$$F(x, y) = 0, \quad F_y \neq 0,$$
the formula reduces to the familiar expression
$$\phi'(x) = -\frac{F_x(x, \phi(x))}{F_y(x, \phi(x))}.$$

**Example 7.13 — The Unit Circle Revisited**
Let
$$F(x, y) = x^2 + y^2 - 1.$$
Near $(0, 1)$, the implicit function theorem gives a function $y = \phi(x)$ with
$$F(x, \phi(x)) = 0.$$
Since
$$F_x = 2x, \quad F_y = 2y,$$
we obtain
$$\phi'(x) = -\frac{x}{\phi(x)}.$$
In particular,
$$\phi'(0) = 0,$$
which agrees with the horizontal tangent to the upper half of the circle at $(0, 1)$.

The formula also shows why the condition $D_y F$ matters. If this matrix is nearly singular, its inverse can be large, so even a small change in $x$ may produce a large change in the implicitly determined $y$.

**7.6 Comparative Statics**
The implicit function theorem is the mathematical foundation of local comparative statics. An equilibrium is often defined not by an explicit formula for the endogenous variables, but by a system of equations.
Let
$$F(z, \theta) = 0,$$

<!-- page 130 -->

where
$$z \in \mathbb{R}^n$$
is a vector of endogenous variables and
$$\theta \in \mathbb{R}^m$$
is a vector of parameters. Suppose
$$F(z_0, \theta_0) = 0$$
and the equilibrium Jacobian
$$D_z F(z_0, \theta_0)$$
is invertible. The implicit function theorem then gives a locally unique equilibrium
$$z = z^*(\theta)$$
for $\theta$ near $\theta_0$.
Differentiating the equilibrium condition
$$F(z^*(\theta), \theta) = 0$$
gives
$$D_z F Dz^*(\theta) + D_\theta F = 0.$$
Hence:

**Proposition 7.14 — Local Comparative Statics Formula**
If
$$F(z_0, \theta_0) = 0$$
and $D_z F(z_0, \theta_0)$ is invertible, then the locally defined equilibrium mapping $z^*(\theta)$ satisfies
$$Dz^*(\theta_0) = -[D_z F(z_0, \theta_0)]^{-1}D_\theta F(z_0, \theta_0).$$
This formula separates two objects. The matrix
$$D_\theta F$$
measures the *direct* effect of a parameter change on the equilibrium conditions, while
$$[D_z F]^{-1}$$
translates that disturbance into the endogenous adjustment required to restore equilibrium.
In the scalar case,
$$F(z, \theta) = 0,$$

<!-- page 131 -->

the formula becomes
$$\frac{dz^*}{d\theta} = -\frac{F_\theta}{F_z}.$$
Thus comparative-static signs can often be determined from the signs of two partial derivatives.

**Example 7.15 — Market-Clearing Comparative Statics**
Suppose an equilibrium price $p^*(\theta)$ is determined by
$$F(p, \theta) = D(p, \theta) - S(p) = 0,$$
where $D$ is demand and $S$ is supply. Assume
$$D_p < 0, \quad S_p > 0, \quad D_\theta > 0.$$
Then
$$F_p = D_p - S_p < 0, \quad F_\theta = D_\theta > 0.$$
Therefore
$$\frac{dp^*}{d\theta} = -\frac{F_\theta}{F_p} > 0.$$
A parameter shift that raises demand at every price therefore raises the local equilibrium price.

Fixed-point models fit the same framework. Suppose an equilibrium is written as
$$z = T(z, \theta).$$
Define
$$F(z, \theta) = z - T(z, \theta).$$
Then
$$D_z F = I - D_z T, \quad D_\theta F = -D_\theta T.$$
Whenever $I - D_z T$ is invertible, the comparative-statics formula becomes
$$Dz^*(\theta) = [I - D_z T(z^*(\theta), \theta)]^{-1}D_\theta T(z^*(\theta), \theta).$$
If $T$ is a contraction in $z$, then
$$\|D_z T\| < 1$$
under the usual differentiability conditions, which in particular rules out a nonzero vector $v$ satisfying
$$D_z T v = v.$$
Thus $I - D_z T$ is invertible. In this way the fixed-point and implicit-function views of equilibrium reinforce one another: contraction gives existence, uniqueness, and an iterative algorithm, while the implicit function theorem gives differentiability of the equilibrium with respect to parameters.

<!-- page 132 -->

The implicit-function formula is local and quantitative: it produces a derivative when smoothness and nonsingularity hold. Economic comparative statics often needs less—only the direction of change—and may involve corners or several optimizers. Order methods provide a different route in those cases.

**8 Monotone Comparative Statics and Topkis’s Theorem**
Derivative-based comparative statics asks how fast a locally unique solution moves. Monotone comparative statics asks a different question: when the parameter rises, can we determine the *direction* in which optimal choices move? This question still makes sense at corners, without differentiability, and when the optimizer is set-valued.
The key condition is complementarity. If a higher parameter raises the payoff to a higher action, the objective has increasing differences. With several choice variables, supermodularity adds complementarity among the choices themselves. These two ideas lead to Topkis’s monotonicity theorem.

**8.1 Order, Lattices, and Increasing Differences**
On $\mathbb{R}^n$ we use the coordinatewise order:
$$x \leq y \iff x_i \leq y_i \text{ for every } i.$$
For two vectors $x, y \in \mathbb{R}^n$, define their coordinatewise join and meet by
$$(x \vee y)_i = \max\{x_i, y_i\}, \quad (x \wedge y)_i = \min\{x_i, y_i\}.$$

**Definition 8.1 — Sublattice**
A set $X \subseteq \mathbb{R}^n$ is a **sublattice** if
$$x, y \in X \implies x \vee y \in X \quad \text{and} \quad x \wedge y \in X.$$
Every interval in $\mathbb{R}$ is a sublattice. In $\mathbb{R}^n$, every rectangle
$$X = [a_1, b_1] \times \dots \times [a_n, b_n]$$
is a compact sublattice.
Now consider an objective
$$u : X \times \Theta \to \mathbb{R},$$
where $x \in X$ is a choice and $\theta \in \Theta$ is a parameter.

<!-- page 133 -->

**Definition 8.2 — Increasing Differences**

The function $u$ has **increasing differences in** $(x, \theta)$ if whenever
$$x' \geq x \quad \text{and} \quad \theta' \geq \theta,$$
we have
$$u(x', \theta') - u(x, \theta') \geq u(x', \theta) - u(x, \theta).$$

The inequality compares the gain from moving from $x$ to a higher action $x'$. Increasing differences says that this gain is larger when the parameter is higher. Thus $x$ and $\theta$ are complements in the objective.

For a scalar choice and scalar parameter, the smooth condition is familiar.

**Proposition 8.3 — Smooth Test for Increasing Differences**

Let $u$ be twice continuously differentiable on a rectangle in $\mathbb{R}^2$. If
$$\frac{\partial^2 u}{\partial x \partial \theta}(x, \theta) \geq 0$$
everywhere, then $u$ has increasing differences in $(x, \theta)$.

**Proof**

Fix $x' \geq x$ and define
$$\Delta(\theta) = u(x', \theta) - u(x, \theta).$$
Then
$$\Delta'(\theta) = u_\theta(x', \theta) - u_\theta(x, \theta)$$
$$= \int_x^{x'} u_{s\theta}(s, \theta) \, \text{ds} \geq 0,$$
where the second equality is the one-dimensional Fundamental Theorem of Calculus applied to $s \mapsto u_\theta(s, \theta)$. Hence $\Delta$ is nondecreasing, which is exactly the increasing-differences inequality.

For vector choices, increasing differences between each choice coordinate and each parameter coordinate provides the same direct complementarity, but we also need a condition describing interactions among the choice coordinates themselves.

<!-- page 134 -->

**Definition 8.4 — Supermodularity**

Let $X \subseteq \mathbb{R}^n$ be a sublattice. A function
$$u : X \to \mathbb{R}$$
is **supermodular** if
$$u(x \vee y) + u(x \wedge y) \geq u(x) + u(y)$$
for every $x, y \in X$.

Supermodularity says that choice coordinates are complementary. For a scalar choice, the condition is automatic because $x \vee y$ and $x \wedge y$ are just $x$ and $y$ in some order.

When $X$ is a rectangle and $u$ is $C^2$, a convenient sufficient condition is
$$\frac{\partial^2 u}{\partial x_i \partial x_j} \geq 0, \quad i \neq j.$$

Thus nonnegative cross-partials among choices encode supermodularity, while nonnegative cross-partials between choices and parameters encode increasing differences.

**8.2 Scalar Monotone Comparative Statics**

The scalar case contains the main economic logic with almost no lattice machinery. Let
$$X \subseteq \mathbb{R}$$
be nonempty and compact, and define the optimizer correspondence
$$X^*(\theta) := \arg \max_{x \in X} u(x, \theta).$$

If $u(\cdot, \theta)$ is continuous, then $X^*(\theta)$ is nonempty and compact. Hence its smallest and largest elements exist. Write
$$x^-(\theta) = \min X^*(\theta), \quad x^+(\theta) = \max X^*(\theta).$$

**Theorem 8.5 — Scalar Monotone Comparative Statics**

Suppose $X \subseteq \mathbb{R}$ is nonempty and compact, $u(\cdot, \theta)$ is continuous for each $\theta$, and $u$ has increasing differences in $(x, \theta)$. Then both extremal optimal selections
$$x^-(\theta) \quad \text{and} \quad x^+(\theta)$$
are nondecreasing in $\theta$.

<!-- page 135 -->

**Proof**

Take $\theta' \geq \theta$. For the largest optimizer, write
$$x = x^+(\theta), \quad y = x^+(\theta').$$
Suppose, toward a contradiction, that $y < x$. Optimality of $x$ at $\theta$ gives
$$u(x, \theta) - u(y, \theta) \geq 0.$$
Since $x > y$, increasing differences implies
$$u(x, \theta') - u(y, \theta') \geq u(x, \theta) - u(y, \theta) \geq 0.$$
Optimality of $y$ at $\theta'$ gives the reverse weak inequality, so equality must hold. Thus $x$ is also optimal at $\theta'$, contradicting the fact that $y$ is the largest optimizer there and $y < x$. Hence
$$x^+(\theta') \geq x^+(\theta).$$
For the smallest optimizer, write
$$x = x^-(\theta), \quad y = x^-(\theta').$$
Again suppose $y < x$. Optimality of $y$ at $\theta'$ gives
$$u(x, \theta') - u(y, \theta') \leq 0.$$
Increasing differences then yields
$$u(x, \theta) - u(y, \theta) \leq u(x, \theta') - u(y, \theta') \leq 0.$$
But $x$ is optimal at $\theta$, so the first difference is also nonnegative. It must therefore equal zero, making $y$ optimal at $\theta$. This contradicts the minimality of $x$ because $y < x$. Thus
$$x^-(\theta') \geq x^-(\theta).$$

No interiority, differentiability, or uniqueness assumption appears in the theorem. Its conclusion therefore survives cases in which first-order-condition comparative statics is unavailable.

**Example 8.6 — Investment and Productivity**

Suppose a firm chooses investment $x \in [0, \bar{x}]$ to maximize
$$u(x, \theta) = \theta v(x) - c(x),$$

<!-- page 136 -->

[Image: A graph showing two concave curves $u(x, \theta_L)$ and $u(x, \theta_H)$ where $\theta_H > \theta_L$. The peak of the $\theta_H$ curve is to the right of the peak of the $\theta_L$ curve, labeled "optimizer moves right".]

Figure 15: A smooth picture of increasing differences. A higher parameter tilts the objective in favor of higher actions, so the maximizing action shifts upward. Topkis's theorem preserves this conclusion without requiring the smooth, interior case drawn here.

where $v$ is nondecreasing. For $x' \geq x$,
$$u(x', \theta') - u(x', \theta) - [u(x, \theta') - u(x, \theta)] = (\theta' - \theta)[v(x') - v(x)] \geq 0.$$
Hence $u$ has increasing differences. The smallest and largest optimal investment levels are therefore nondecreasing in productivity $\theta$.

If the optimum happens to be unique and interior, one could instead differentiate the first-order condition. The monotone result is stronger in a different sense: it continues to apply at corners and when the optimizer is set-valued.

**8.3 Topkis's Monotonicity Theorem**

With several choice variables, increasing differences between $x$ and $\theta$ is not enough by itself. A parameter increase may raise one choice directly but induce another choice to fall, which can feed back negatively. Supermodularity rules out this kind of opposing interaction by making the components of $x$ complements.

<!-- page 137 -->

**Theorem 8.7 — Topkis's Monotonicity Theorem**

Let $X \subseteq \mathbb{R}^n$ be a nonempty compact sublattice and let $\Theta \subseteq \mathbb{R}^m$ be ordered coordinatewise. Suppose
$$u : X \times \Theta \to \mathbb{R}$$
satisfies the following conditions:
(1) $u(\cdot, \theta)$ is continuous on $X$ for every $\theta$;
(2) $u(\cdot, \theta)$ is supermodular on $X$ for every $\theta$;
(3) $u$ has increasing differences in $(x, \theta)$.

Then the optimizer set
$$X^*(\theta) = \arg \max_{x \in X} u(x, \theta)$$
is a nonempty compact sublattice. In particular, it has a smallest optimizer $x^-(\theta)$ and a largest optimizer $x^+(\theta)$, and both extremal selections are nondecreasing in $\theta$.

**Proof**

Fix $\theta$. Continuity of $u(\cdot, \theta)$ and compactness of $X$ imply that
$$X^*(\theta) = \arg \max_{x \in X} u(x, \theta)$$
is nonempty and compact. Let the maximal value be $M$.
If $x, y \in X^*(\theta)$, supermodularity gives
$$u(x \vee y, \theta) + u(x \wedge y, \theta) \geq u(x, \theta) + u(y, \theta) = 2M.$$
Since neither term on the left can exceed $M$, both must equal $M$. Thus $x \vee y$ and $x \wedge y$ are again maximizers, so $X^*(\theta)$ is a sublattice.
We next verify that this compact optimizer sublattice has extremal elements. For each coordinate $i$, compactness gives a point
$$z^i \in X^*(\theta)$$
whose $i$th coordinate is maximal over $X^*(\theta)$. Because the optimizer set is closed under finite joins,
$$z^+ = z^1 \vee \dots \vee z^n$$
also belongs to $X^*(\theta)$. For any $x \in X^*(\theta)$ and every coordinate $i$,
$$x_i \leq z_i^i \leq z_i^+,$$

<!-- page 138 -->

so $x \leq z^+$. Hence $z^+$ is the largest optimizer. The smallest optimizer is obtained analogously by choosing coordinatewise minimizers and taking their finite meet.
Now let $\theta' \geq \theta$ and write
$$x = x^+(\theta), \quad y = x^+(\theta').$$
Optimality of $x$ at $\theta$ gives
$$u(x, \theta) \geq u(x \wedge y, \theta).$$
Supermodularity at $\theta$ then implies
$$u(x \vee y, \theta) - u(y, \theta) \geq u(x, \theta) - u(x \wedge y, \theta) \geq 0.$$
Since $x \vee y \geq y$, increasing differences gives
$$u(x \vee y, \theta') - u(y, \theta') \geq u(x \vee y, \theta) - u(y, \theta) \geq 0.$$
Thus $x \vee y$ is also optimal at $\theta'$. Because $y$ is the largest optimizer at $\theta'$,
$$x \vee y = y,$$
and hence $x \leq y$. Therefore $x^+$ is nondecreasing.
For the smallest optimizer, set
$$x = x^-(\theta), \quad y = x^-(\theta').$$
Optimality of $y$ at $\theta'$ gives
$$u(y, \theta') \geq u(x \vee y, \theta').$$
Supermodularity at $\theta'$ implies
$$u(x \wedge y, \theta') - u(x, \theta') \geq u(y, \theta') - u(x \vee y, \theta') \geq 0.$$
Since $x \geq x \wedge y$, increasing differences yields
$$u(x, \theta) - u(x \wedge y, \theta) \leq u(x, \theta') - u(x \wedge y, \theta') \leq 0.$$
Hence $x \wedge y$ is optimal at $\theta$. Because $x$ is the smallest optimizer there,
$$x \wedge y = x,$$
and again $x \leq y$. Thus $x^-$ is nondecreasing.

<!-- page 139 -->

**Remark 8.8 — Why We State the Stronger Calculus-Friendly Version**

The classical lattice approach is associated with Topkis. The later Milgrom–Shannon theory shows that monotone comparative statics can be developed under weaker ordinal conditions, notably single crossing and quasisupermodularity. For these notes, increasing differences and supermodularity are preferable: they are stronger, but their meaning is transparent and their smooth sufficient conditions are simple cross-partial inequalities.

For a $C^2$ objective on a rectangle, the following checklist is often enough:
$$\frac{\partial^2 u}{\partial x_i \partial x_j} \geq 0 \quad (i \neq j), \quad \frac{\partial^2 u}{\partial x_i \partial \theta_k} \geq 0 \quad \text{for all } i, k.$$

The first group of inequalities captures complementarity among choices; the second captures complementarity between choices and parameters.
The scalar result does not yet show why lattices matter. With several choices, complementarity among the choice coordinates is the additional ingredient.

**Example 8.9 — Two Complementary Investments**

A firm chooses two investments
$$x = (x_1, x_2) \in [0, \bar{x}_1] \times [0, \bar{x}_2]$$
and receives payoff
$$u(x_1, x_2; \theta) = \theta(x_1 + x_2) + \gamma x_1 x_2 - c_1(x_1) - c_2(x_2), \quad \gamma \geq 0.$$
Think of $x_1$ and $x_2$ as two inputs whose returns reinforce one another—for example, a technology investment and the organizational capital needed to use it.
If the cost functions are twice continuously differentiable, then
$$\frac{\partial^2 u}{\partial x_1 \partial x_2} = \gamma \geq 0,$$
so the objective is supermodular in $(x_1, x_2)$. Moreover,
$$\frac{\partial^2 u}{\partial x_1 \partial \theta} = \frac{\partial^2 u}{\partial x_2 \partial \theta} = 1 > 0,$$
so $u$ has increasing differences between the choice vector and $\theta$. Because the feasible set is a compact rectangle, Topkis's theorem implies that the smallest and largest optimal investment vectors are nondecreasing in $\theta$.
No first-order condition is needed for this conclusion. It remains valid when one investment is

<!-- page 140 -->

at a boundary and when several optimal pairs coexist.

**8.4 Monotone Fixed Points and Tarski's Theorem**

Banach obtains a fixed point from a metric condition: distances contract. Order methods replace that condition with monotonicity. An increasing map may have several fixed points and need not be a contraction, yet a lattice structure can still guarantee existence and identify extremal solutions. The basic result is Tarski's fixed-point theorem.

**Definition 8.10 — Complete Lattice**

A partially ordered set $L$ is a **complete lattice** if every subset $A \subseteq L$ has both a supremum and an infimum in $L$.

A rectangle
$$X = [\underline{z}, \bar{z}] \subseteq \mathbb{R}^n$$
with the coordinatewise order is a complete lattice: suprema and infima are computed coordinate by coordinate.

**Theorem 8.11 — Tarski Fixed-Point Theorem**

Let $L$ be a complete lattice and let $T : L \to L$ be increasing. Then the set of fixed points
$$\text{Fix}(T) = \{x \in L : T(x) = x\}$$
is nonempty and is itself a complete lattice. In particular, $T$ has a least fixed point and a greatest fixed point.

The full lattice-theoretic proof is more general than we need. On a Euclidean rectangle, continuity gives a direct constructive version.

**Corollary 8.12 — Monotone Iteration on a Rectangle**

Let
$$X = [\underline{z}, \bar{z}] \subseteq \mathbb{R}^n$$
and let $T : X \to X$ be continuous and increasing. Define
$$z_0^- = \underline{z}, \quad z_{k+1}^- = T(z_k^-),$$
and
$$z_0^+ = \bar{z}, \quad z_{k+1}^+ = T(z_k^+).$$

<!-- page 141 -->

Then $z_k^-$ converges increasingly to the least fixed point of $T$, while $z_k^+$ converges decreasingly to the greatest fixed point.

**Proof**

Because $\underline{z}$ is the least element of $X$,
$$\underline{z} \leq T(\underline{z}) = z_1^-.$$
Monotonicity of $T$ then gives
$$z_0^- \leq z_1^- \leq z_2^- \leq \dots \leq \bar{z}.$$
Each coordinate is an increasing bounded real sequence, so $z_k^- \to z^- \in X$. Continuity gives
$$T(z^-) = T\left(\lim_k z_k^-\right) = \lim_k z_{k+1}^- = z^-.$$
If $y$ is any fixed point, then $z_0^- \leq y$, and induction gives $z_k^- \leq y$ for every $k$. Passing to the limit yields $z^- \leq y$, so $z^-$ is the least fixed point. The argument from $\bar{z}$ is symmetric and gives the greatest fixed point.

**Example 8.13 — Multiple Fixed Points without Contraction**

Let
$$T(z) = z^2, \quad z \in [0, 1].$$
The map is continuous and increasing, with two fixed points:
$$T(0) = 0, \quad T(1) = 1.$$
It is not a contraction on $[0, 1]$ because
$$\sup_{z \in [0,1]} |T'(z)| = 2.$$
Starting the monotone iteration from the least element gives the least fixed point 0, while starting from the greatest element gives the greatest fixed point 1. This is exactly the situation in which Tarski is informative but Banach's theorem does not apply.

Banach and Tarski answer different questions. Banach uses metric contraction and gives a unique fixed point with a geometric error bound. Tarski uses order and allows many fixed points, but identifies extremal equilibria and supplies monotone iterations under the additional continuity used above.

Now reintroduce a parameter. If each $T(\cdot, \theta)$ is a contraction, the fixed point is unique; if $T$ is

<!-- page 142 -->

[Image: A graph showing the curve $T(z) = z^2$ and the line $y = z$ on the interval $[0, 1]$. The intersections at 0 and 1 are labeled "least fixed point" and "greatest fixed point".]

Figure 16: Tarski allows multiple fixed points. For $T(z) = z^2$ on $[0, 1]$, the intersections with the $45^\circ$ line are the least and greatest fixed points, 0 and 1.

also increasing in both the state and the parameter, that unique fixed point inherits the parameter monotonicity.

**Theorem 8.14 — Monotone Comparative Statics of a Contractive Fixed Point**

Let $X \subseteq \mathbb{R}^n$ be nonempty and closed. Suppose that for every parameter $\theta \in \Theta$,
$$T(\cdot, \theta) : X \to X$$
is a contraction with a common contraction constant $q < 1$. Assume also that
$$z' \geq z, \quad \theta' \geq \theta$$
imply
$$T(z', \theta') \geq T(z, \theta).$$
Let $z^*(\theta)$ denote the unique fixed point. Then
$$\theta' \geq \theta \implies z^*(\theta') \geq z^*(\theta).$$

<!-- page 143 -->

**Proof**

Fix $\theta' \geq \theta$ and start the $\theta'$ iteration from
$$z_0 = z^*(\theta).$$
Then
$$z_1 = T(z_0, \theta') \geq T(z_0, \theta) = z_0.$$
Because $T(\cdot, \theta')$ is increasing in $z$,
$$z_2 = T(z_1, \theta') \geq T(z_0, \theta') = z_1,$$
and induction gives a nondecreasing sequence
$$z_0 \leq z_1 \leq z_2 \leq \dots.$$
By the Banach fixed-point theorem, this iteration converges to the unique fixed point $z^*(\theta')$. Passing to the limit coordinatewise yields
$$z^*(\theta) \leq z^*(\theta').$$

Topkis begins with an optimization problem; Tarski-style arguments begin with an order-preserving equilibrium operator. Neither requires differentiating the solution. It is useful to keep the local and order-based approaches side by side:

| local differential method | global order method |
| :--- | :--- |
| implicit/inverse function theorem | increasing differences and supermodularity |
| requires smoothness and nonsingularity | allows corners and multiple optima |
| gives derivatives and local elasticities | gives monotone direction of change |

In applications, the two approaches are complements rather than substitutes.

**9 Integration in Euclidean Space**

Multiple integration adds geometry to the one-dimensional integral. We begin on rectangles, where Riemann sums are direct, and then use Fubini's theorem to reduce many calculations to repeated one-dimensional integration. Change of variables explains how volume changes under a smooth coordinate transformation, while the last part of the section gives conditions for moving limits and derivatives through an integral.

The Riemann framework used here is deliberately modest: it is enough for smooth functions on bounded regions and keeps the focus on the calculus rather than on measure theory.

<!-- page 144 -->

**9.1 Multiple and Iterated Integrals**

A closed rectangle in $\mathbb{R}^n$ is a set of the form
$$Q = [a_1, b_1] \times \dots \times [a_n, b_n].$$
Its volume is
$$|Q| = \prod_{i=1}^n (b_i - a_i).$$
A partition $\mathcal{P}$ divides $Q$ into finitely many smaller rectangles
$$Q_1, \dots, Q_N$$
with pairwise disjoint interiors. Choose a tag $\xi_k \in Q_k$ in each rectangle. For a bounded function $f : Q \to \mathbb{R}$, the associated Riemann sum is
$$R(f, \mathcal{P}, \xi) = \sum_{k=1}^N f(\xi_k)|Q_k|.$$
The mesh of the partition is the largest diameter of one of the subrectangles.

**Definition 9.1 — Riemann Integral on a Rectangle**

A bounded function $f : Q \to \mathbb{R}$ is **Riemann integrable** on $Q$ if there exists a number $I$ such that, for every $\varepsilon > 0$, there exists $\delta > 0$ with the property that
$$|R(f, \mathcal{P}, \xi) - I| < \varepsilon$$
for every tagged partition whose mesh is smaller than $\delta$.
We then write
$$I = \int_Q f(x) \, dx, \quad dx := dx_1 \dots dx_n.$$

The notation $dx$ is compact, but the integral is still a limit of ordinary finite sums. The factors $|Q_k|$ are the multidimensional analogues of the one-dimensional interval lengths $\Delta x_k$.
For a partition $\mathcal{P} = \{Q_1, \dots, Q_N\}$, define
$$m_k = \inf_{x \in Q_k} f(x), \quad M_k = \sup_{x \in Q_k} f(x),$$
and the lower and upper sums
$$L(f, \mathcal{P}) = \sum_{k=1}^N m_k |Q_k|, \quad U(f, \mathcal{P}) = \sum_{k=1}^N M_k |Q_k|.$$

<!-- page 145 -->

Every tagged Riemann sum for the same partition lies between these two numbers. This gives a convenient integrability test.

**Proposition 9.2 — Darboux Criterion**

A bounded function $f : Q \to \mathbb{R}$ is Riemann integrable if and only if, for every $\varepsilon > 0$, there exists a partition $\mathcal{P}$ of $Q$ such that
$$U(f, \mathcal{P}) - L(f, \mathcal{P}) < \varepsilon.$$

The criterion says that integrability is equivalent to making the total oscillation of the function over a sufficiently fine partition arbitrarily small. We use it below rather than repeatedly comparing every possible choice of tags.

Continuity is the principal sufficient condition needed here.

**Theorem 9.3 — Continuous Functions Are Riemann Integrable**

Every continuous function on a closed rectangle $Q \subseteq \mathbb{R}^n$ is Riemann integrable.

**Proof**

The rectangle $Q$ is compact, so $f$ is uniformly continuous. Given $\varepsilon > 0$, choose $\delta > 0$ so that
$$\|x - y\| < \delta \implies |f(x) - f(y)| < \frac{\varepsilon}{|Q| + 1}.$$

Take a partition with mesh smaller than $\delta$. On each subrectangle $Q_k$, continuity gives a maximum $M_k$ and a minimum $m_k$, and uniform continuity gives
$$M_k - m_k < \frac{\varepsilon}{|Q| + 1}.$$

Hence the upper and lower sums satisfy
$$\sum_k M_k |Q_k| - \sum_k m_k |Q_k| < \frac{\varepsilon}{|Q| + 1} \sum_k |Q_k| < \varepsilon.$$

By proposition 9.2, $f$ is Riemann integrable.

For more general bounded domains, it is useful to have a light version of Jordan measurability.

**Definition 9.4 — Jordan-Measurable Region**

A bounded set $D \subseteq \mathbb{R}^n$ is Jordan measurable if its boundary $\partial D$ can, for every $\varepsilon > 0$, be covered by finitely many rectangles whose total volume is smaller than $\varepsilon$.

<!-- page 146 -->

If $D \subseteq Q$ and $f : D \to \mathbb{R}$ is bounded, we define
$$\int_D f(x) \, dx$$
by extending $f$ by zero outside $D$ and integrating the resulting function over $Q$, whenever that extension is Riemann integrable.

Rectangles, balls, and the usual bounded regions with piecewise smooth boundary are Jordan measurable. Continuous functions on compact Jordan-measurable regions are Riemann integrable. We write
$$|D| := \int_D 1 \, dx$$
for the volume of a Jordan-measurable region $D$.

The usual algebraic and order properties carry over directly from one dimension.

**Proposition 9.5 — Basic Properties of the Multiple Integral**

Let $D$ be a compact Jordan-measurable region and let $f, g$ be Riemann integrable on $D$.
(1) For $\alpha, \beta \in \mathbb{R}$,
$$\int_D (\alpha f + \beta g) \, dx = \alpha \int_D f \, dx + \beta \int_D g \, dx.$$
(2) If $f \le g$ on $D$, then
$$\int_D f \, dx \le \int_D g \, dx.$$
(3)
$$\left| \int_D f(x) \, dx \right| \le \int_D |f(x)| \, dx \le |D| \sup_{x \in D} |f(x)|.$$

These estimates will be used repeatedly below, especially when a limit or a parameter is moved through an integral.

Fubini's theorem turns this definition into a practical method of calculation.

**Theorem 9.6 — Fubini's Theorem for Continuous Functions**

Let
$$Q = [a_1, b_1] \times \dots \times [a_n, b_n]$$
and let $f : Q \to \mathbb{R}$ be continuous. Then the multiple integral can be computed by iterated one-dimensional integration, in any order. For example,
$$\int_Q f(x) \, dx = \int_{a_1}^{b_1} \dots \int_{a_n}^{b_n} f(x_1, \dots, x_n) \, dx_n \dots dx_1.$$

<!-- page 147 -->

All permutations of the order of integration give the same value.

Fubini's theorem is important conceptually because it says that a genuinely multidimensional limit can be evaluated through successive one-dimensional limits. Computationally, it lets us use the fundamental theorem of calculus one coordinate at a time.

For a two-dimensional region of the form
$$D = \{(x, y) : a \le x \le b, \alpha(x) \le y \le \beta(x)\},$$
where $\alpha$ and $\beta$ are continuous and $\alpha \le \beta$, Fubini gives
$$\int_D f(x, y) \, dx \, dy = \int_a^b \left[ \int_{\alpha(x)}^{\beta(x)} f(x, y) \, dy \right] dx.$$

One may instead reverse the order if the same region is more simply described by horizontal slices.

**Example 9.7 — Integrating over a Triangle**

Let
$$D = \{(x, y) : 0 \le x \le 1, 0 \le y \le 1 - x\}.$$
Then
$$\int_D (x + y) \, dx \, dy = \int_0^1 \int_0^{1-x} (x + y) \, dy \, dx.$$
The inner integral is
$$x(1 - x) + \frac{1}{2}(1 - x)^2,$$
so one final one-dimensional integration gives
$$\int_D (x + y) \, dx \, dy = \frac{1}{3}.$$

**Remark 9.8 — Beyond the Riemann Setting**

For Lebesgue integrals, Fubini's theorem extends much further. A standard sufficient condition is absolute integrability of $f$. The probability part of the course will use that more flexible framework. Here we retain the continuous, compact-domain version because it contains the main calculus idea without adding measure-theoretic machinery.

<!-- page 148 -->

**9.2 Change of Variables**

In one dimension, substitution replaces
$$x = \phi(t)$$
and introduces the factor $\phi'(t)$. The reason is geometric: over a small interval, the map stretches lengths approximately by $|\phi'(t)|$.

The same principle holds in $\mathbb{R}^n$. If
$$T : U \subseteq \mathbb{R}^n \to \mathbb{R}^n$$
is differentiable at $u$, then near $u$,
$$T(u + h) - T(u) \approx DT(u)h.$$

The linear map $DT(u)$ changes $n$-dimensional volume by the factor
$$|\det DT(u)|.$$

This is the source of the Jacobian determinant in multivariable substitution.

**Theorem 9.9 — Change-of-Variables Theorem**

Let $A \subseteq \mathbb{R}^n$ be a compact Jordan-measurable set, and suppose
$$T : U \to V$$
is a $C^1$ diffeomorphism between open sets with $A \subseteq U$. If $f$ is continuous on $T(A)$, then
$$\int_{T(A)} f(x) \, dx = \int_A f(T(u)) |\det DT(u)| \, du.$$

The absolute value is essential. The determinant records both local volume scaling and orientation, whereas ordinary volume is nonnegative and therefore uses only the magnitude of the scaling factor.

The theorem is a direct continuation of the linear-approximation theme of these notes. On a sufficiently small piece around $u$, the nonlinear transformation is well approximated by $DT(u)$. A linear transformation multiplies volume by the absolute determinant. Summing these local volume changes and passing to the limit gives the integral formula.

The inverse function theorem explains the nonsingularity condition behind this picture. If
$$\det DT(u) \neq 0,$$
then $T$ is locally invertible near $u$, so nearby pieces are not collapsed into lower-dimensional sets.

<!-- page 149 -->

**Example 9.10 — Polar Coordinates**

Consider
$$T(r, \theta) = (r \cos \theta, r \sin \theta).$$
Strictly speaking, the full rectangle $[0, R] \times [0, 2\pi]$ is not a domain on which $T$ is a diffeomorphism: the angle endpoints are identified and the origin is singular. Apply the theorem first on compact rectangles
$$[\varepsilon, R] \times [\delta, 2\pi - \delta], \quad \varepsilon, \delta > 0,$$
where the polar map is one-to-one and nonsingular, and then let $\varepsilon, \delta \downarrow 0$. The omitted pieces have area tending to zero. Its Jacobian matrix is
$$DT(r, \theta) = \begin{pmatrix} \cos \theta & -r \sin \theta \\ \sin \theta & r \cos \theta \end{pmatrix},$$
so
$$\det DT(r, \theta) = r.$$
Consequently,
$$dx \, dy = r \, dr \, d\theta$$
inside a polar-coordinate integral.

For example, if $g$ depends only on distance from the origin, then
$$\int_{B_R(0)} g(\|x\|) \, dx = \int_0^{2\pi} \int_0^R g(r)r \, dr \, d\theta = 2\pi \int_0^R g(r)r \, dr.$$
Taking $g \equiv 1$ gives
$$|B_R(0)| = \pi R^2.$$

[Image: A diagram showing a rectangular grid in $(r, \theta)$ coordinates mapping to a curved grid in the $(x, y)$ plane, labeled "parameter rectangle" and "annular sector".]

Figure 17: A rectangular grid in $(r, \theta)$ coordinates becomes a curved grid in the plane. A small polar cell has area approximately $r \, dr \, d\theta$, which is the Jacobian factor in polar coordinates.

The same logic produces the usual Jacobian factors in cylindrical and spherical coordinates. Rather

<!-- page 150 -->

than memorizing coordinate factors, compute
$$|\det DT|$$
for the coordinate map being used.

**9.3 Parameter-Dependent Integrals**

Many integrals in economics and probability depend on a parameter. Let
$$D \subseteq \mathbb{R}^n$$
be compact and Jordan measurable, and consider
$$I(\theta) = \int_D f(x, \theta) \, dx, \quad \theta \in \Theta \subseteq \mathbb{R}^m.$$

Before differentiating $I$, we first ask whether it is continuous in the parameter.

**Theorem 9.11 — Continuity of a Parameter-Dependent Integral**

Suppose $D$ is compact and Jordan measurable, $\Theta \subseteq \mathbb{R}^m$ is open, and
$$f : D \times \Theta \to \mathbb{R}$$
is continuous. Then
$$I(\theta) = \int_D f(x, \theta) \, dx$$
is continuous on $\Theta$.

**Proof**

Fix $\theta_0 \in \Theta$. Since $\Theta$ is open, choose $r > 0$ such that
$$\bar{B}_r(\theta_0) \subseteq \Theta.$$
The set
$$D \times \bar{B}_r(\theta_0)$$
is compact, so the continuous function $f$ is uniformly continuous there. Consequently,
$$\sup_{x \in D} |f(x, \theta) - f(x, \theta_0)| \to 0 \quad \text{as } \theta \to \theta_0.$$

<!-- page 151 -->

For $\theta \in B_r(\theta_0)$,
$$|I(\theta) - I(\theta_0)| = \left| \int_D (f(x, \theta) - f(x, \theta_0)) \, dx \right|$$
$$\le |D| \sup_{x \in D} |f(x, \theta) - f(x, \theta_0)|.$$
The right-hand side tends to zero as $\theta \to \theta_0$, proving continuity of $I$ at $\theta_0$. Since $\theta_0$ was arbitrary, $I$ is continuous on $\Theta$.

The proof is an instance of a more general principle: uniform convergence allows limits to pass through a Riemann integral.

**Proposition 9.12 — Uniform Convergence and Integration**

Let $D$ be compact and Jordan measurable. Suppose $f_k$ and $f$ are Riemann integrable on $D$ and
$$f_k \to f$$
uniformly. Then
$$\int_D f_k(x) \, dx \to \int_D f(x) \, dx.$$

**Proof**

We have
$$\left| \int_D f_k(x) \, dx - \int_D f(x) \, dx \right| \le |D| \sup_{x \in D} |f_k(x) - f(x)|,$$
and the right-hand side tends to zero.

This simple estimate is the main technical reason compact parameter domains are so convenient. On unbounded domains, or for improper integrals, pointwise continuity alone is not enough; one needs additional control on the tails.

**9.4 Differentiation Under the Integral Sign**

Differentiation is itself a limit. Therefore differentiating an integral with respect to a parameter is an interchange of two limiting operations. On a compact domain, continuity of the parameter derivative provides a clean sufficient condition.

<!-- page 152 -->

**Theorem 9.13 — Differentiation Under the Integral Sign**

Let $D \subseteq \mathbb{R}^n$ be compact and Jordan measurable, $\Theta \subseteq \mathbb{R}^m$ be open, and let
$$f : D \times \Theta \to \mathbb{R}.$$
Suppose $f$ is continuous and the partial derivatives
$$\frac{\partial f}{\partial \theta_j}$$
exist and are continuous on $D \times \Theta$. Define
$$I(\theta) = \int_D f(x, \theta) \, dx.$$
Then $I$ is continuously differentiable and
$$\frac{\partial I}{\partial \theta_j}(\theta) = \int_D \frac{\partial f}{\partial \theta_j}(x, \theta) \, dx.$$
Equivalently,
$$\nabla_\theta I(\theta) = \int_D \nabla_\theta f(x, \theta) \, dx.$$

**Proof**

Fix $\theta \in \Theta$ and a coordinate $j$. Because $\Theta$ is open, choose $r > 0$ such that
$$\bar{B}_r(\theta) \subseteq \Theta.$$
For $0 < |h| < r$, define
$$q_h(x) = \frac{f(x, \theta + he_j) - f(x, \theta)}{h}.$$
Then
$$\frac{I(\theta + he_j) - I(\theta)}{h} = \int_D q_h(x) \, dx.$$
For each fixed $x$, the one-dimensional mean-value theorem applied to $t \mapsto f(x, \theta + te_j)$ gives a number $\tau_h(x) \in (0, 1)$ such that
$$q_h(x) = \frac{\partial f}{\partial \theta_j}(x, \theta + \tau_h(x)he_j).$$
The function $\partial f / \partial \theta_j$ is continuous on the compact set
$$D \times \bar{B}_r(\theta),$$

<!-- page 153 -->

hence uniformly continuous there. Since
$$\|\tau_h(x)he_j\| \le |h|,$$
uniform continuity implies
$$\sup_{x \in D} \left| q_h(x) - \frac{\partial f}{\partial \theta_j}(x, \theta) \right| \to 0 \quad \text{as } h \to 0.$$
Thus $q_h$ converges uniformly on $D$ to $\partial f / \partial \theta_j(\cdot, \theta)$. By uniform convergence and integration,
$$\frac{\partial I}{\partial \theta_j}(\theta) = \lim_{h \to 0} \int_D q_h(x) \, dx$$
$$= \int_D \frac{\partial f}{\partial \theta_j}(x, \theta) \, dx.$$
Finally, $\partial f / \partial \theta_j$ is continuous on $D \times \Theta$. Applying the parameter-dependent integral theorem to this derivative shows that the function
$$\theta \mapsto \int_D \frac{\partial f}{\partial \theta_j}(x, \theta) \, dx$$
is continuous. Hence every partial derivative of $I$ is continuous, so $I \in C^1(\Theta)$.

If the limits of integration also depend on the parameter, there are additional boundary terms.

**Theorem 9.14 — Leibniz Rule**

Let
$$J(t) = \int_{a(t)}^{b(t)} f(x, t) \, dx,$$
where $a$ and $b$ are $C^1$ and where $f$ and $f_t$ are continuous on a neighborhood of the relevant region. Then
$$J'(t) = f(b(t), t)b'(t) - f(a(t), t)a'(t) + \int_{a(t)}^{b(t)} \frac{\partial f}{\partial t}(x, t) \, dx.$$

The formula separates the change into an upper-boundary term, a lower-boundary term, and the direct change in the integrand. In applications these three terms often have distinct economic interpretations.

<!-- page 154 -->

[Image: A graph showing a function $f(x, t)$ over an interval $[a(t), b(t)]$. Arrows indicate the movement of the boundaries $a'(t)$ and $b'(t)$, and the "current integral" area.]

Figure 18: Leibniz's rule separates three sources of change: movement of the lower boundary, movement of the upper boundary, and a direct change in the integrand inside the interval.

**Example 9.15 — Differentiating an Expected Payoff**

Suppose a density $p(x)$ does not depend on $\theta$ and
$$V(\theta) = \int_D u(x, \theta)p(x) \, dx.$$
If $u$ and its parameter derivative satisfy the conditions of theorem 9.13, then
$$\frac{\partial V}{\partial \theta_j}(\theta) = \int_D \frac{\partial u}{\partial \theta_j}(x, \theta)p(x) \, dx.$$
In expectation notation,
$$\frac{\partial}{\partial \theta_j} \mathbb{E}[u(X, \theta)] = \mathbb{E} \left[ \frac{\partial u}{\partial \theta_j}(X, \theta) \right].$$
The theorem identifies conditions under which the familiar instruction "differentiate inside the expectation" is mathematically justified.

<!-- page 155 -->

**References**

[1] V. A. Zorich, *Mathematical Analysis I*, 2nd ed., Universitext, Springer-Verlag Berlin Heidelberg, 2015.
[2] V. A. Zorich, *Mathematical Analysis II*, 2nd ed., Universitext, Springer-Verlag Berlin Heidelberg, 2016.
[3] C. H. Edwards, Jr., *Advanced Calculus of Several Variables*, Academic Press, 1973.
[4] *ma-3: Mathematical Analysis III*, course lecture notes, 2024.
[5] G. Strang and E. Herman, *Calculus, Volume 1*, OpenStax, Rice University, 2016.
[6] G. Strang and E. Herman, *Calculus, Volume 3*, OpenStax, Rice University, 2016.
[7] D. M. Topkis, "Minimizing a Submodular Function on a Lattice," *Operations Research*, 26(2):305–321, 1978.
[8] P. Milgrom and C. Shannon, "Monotone Comparative Statics," *Econometrica*, 62(1):157–180, 1994.
[9] A. Tarski, "A Lattice-Theoretical Fixpoint Theorem and Its Applications," *Pacific Journal of Mathematics*, 5:285–309, 1955.
[10] D. Q. Nykamp, "Using Cobwebbing as a Graphical Solution Technique for Discrete Dynamical Systems," *Math Insight*, accessed 2026.
[11] K. C. Border, *What to Remember About Metric Spaces*, lecture notes, California Institute of Technology, rev. 2018.
[12] K. C. Border, *Notes on the Implicit Function Theorem*, lecture notes, California Institute of Technology, rev. 2019.
[13] K. C. Border, *Notes on Comparative Statics, the Old-Fashioned Way*, lecture notes, California Institute of Technology, rev. 2018.
[14] K. C. Border, *Differentiating an Integral: Leibniz' Rule*, lecture notes, California Institute of Technology, rev. 2016.
[15] K. C. Border, *Fixed Point Theory*, lecture notes, California Institute of Technology.
[16] K. C. Border, *Preliminary Notes on Lattices*, lecture notes, California Institute of Technology, rev. 2017.
[17] P. J. Healy (ed.), *The Kim C. Border Repository*, Ohio State University, archived collection of K. C. Border's lecture notes.