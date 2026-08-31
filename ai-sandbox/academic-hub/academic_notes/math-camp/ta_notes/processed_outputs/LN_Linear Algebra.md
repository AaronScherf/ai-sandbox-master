---
source_pdf: LN_Linear Algebra.pdf
folder_category: ta_notes
total_pages: 294
routing: gemini_batched
model: gemini-3.1-flash-lite
pages_repaired: 82
repaired_pages: [7, 8, 11, 22, 23, 24, 26, 28, 36, 38, 41, 42, 43, 44, 45, 50, 53, 74, 79, 83, 84, 90, 93, 98, 110, 112, 118, 119, 128, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 143, 144, 145, 146, 147, 148, 149, 150, 151, 153, 162, 163, 164, 166, 168, 169, 170, 171, 172, 174, 175, 178, 179, 181, 182, 194, 203, 212, 215, 217, 232, 233, 234, 238, 239, 241, 242, 250, 251, 265, 289, 290, 293]
tags: []
---

<!-- page 1 -->

# Part I: Linear Algebra$^\dagger$

**Hao Jiang$^*$**

2026 PhD Math Camp

**Updated on August 18, 2026**

---

$^*$All remaining errors are my own.
$^\dagger$Typesetting and visual design are informed by public mathematical lecture-note templates, including Gilles Castel's lecture notes, rafisics' lecture-notes template, and Jack's Math Notes Template with Color Box.

1

<!-- page 2 -->

# Contents

**Introduction** **4**

**1 Vector Spaces and Linear Relations of Vectors** **5**
1.1 Vector Spaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
1.2 Linear Combinations of Vectors . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
1.3 Linear Independence . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
1.4 Basis . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
1.5 Change of Basis . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23

**2 Linear Maps and Matrices** **27**
2.1 Linear Maps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27
2.2 The Vector Space of Linear Maps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 29
2.3 Composition of Linear Maps . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31
2.4 Matrix of a Linear Map . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 35
2.5 Composition as Matrix Multiplication . . . . . . . . . . . . . . . . . . . . . . . . . . . 39
2.6 Four Ways to Understand Matrix Multiplication . . . . . . . . . . . . . . . . . . . . . 42
2.7 Inverse Maps and Inverse Matrices . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 45
2.8 Matrix Transpose . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 50
2.9 Symmetric and Skew-Symmetric Matrices . . . . . . . . . . . . . . . . . . . . . . . . . 53

**3 Rank of a Linear Map and a Matrix** **56**
3.1 Kernel and Image . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 56
3.2 The Rank–Nullity Theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 62
3.3 Applications of the Rank–Nullity Theorem . . . . . . . . . . . . . . . . . . . . . . . . 65
3.4 Rank of a Matrix . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 82
3.5 Change of Bases for a Linear Map . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 88
3.6 Row Rank and the Rank Normal Form . . . . . . . . . . . . . . . . . . . . . . . . . . . 91

**4 Sums, Direct Sums, and Invariant Subspaces** **106**
4.1 Intersections and Sums of Subspaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . 106
4.2 The Dimension Formula . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 110
4.3 Direct Sums . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 114

2

<!-- page 3 -->

4.4 Invariant Subspaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 120
4.5 Invariant Subspaces and the Matrix of a Linear Transformation . . . . . . . . . . . . 123

**5 Determinants** **128**
5.1 The Determinant and Its Defining Properties . . . . . . . . . . . . . . . . . . . . . . . 128
5.2 Basic Properties of Determinants . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 136
5.3 Multiplicativity and Invertibility . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 147
5.4 Minors, Cofactors, and Cofactor Expansion . . . . . . . . . . . . . . . . . . . . . . . . 162
5.5 The Adjugate Matrix and Cramer’s Rule . . . . . . . . . . . . . . . . . . . . . . . . . . 170
5.6 Geometric Meaning of the Determinant . . . . . . . . . . . . . . . . . . . . . . . . . . 177

**6 Eigenvalues, Eigenvectors, and Diagonalization** **182**
6.1 Eigenvalues and Eigenvectors . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 182
6.2 Eigenspaces . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 191
6.3 Eigenvalues and the Characteristic Polynomial . . . . . . . . . . . . . . . . . . . . . . 200
6.4 Diagonalization . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 209

**7 Inner Product Spaces and Quadratic Forms** **223**
7.1 Inner Products, Norms, and Orthogonality . . . . . . . . . . . . . . . . . . . . . . . . 223
7.2 Orthonormal Bases and the Gram–Schmidt Process . . . . . . . . . . . . . . . . . . . 230
7.3 Orthogonal Complements and Orthogonal Projections . . . . . . . . . . . . . . . . . 241
7.4 Adjoints, Self-Adjoint Operators, and the Spectral Theorem . . . . . . . . . . . . . . . 254
7.5 Quadratic Forms and Congruence . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 267
7.6 Definiteness of Quadratic Forms . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 275
7.7 Inertia and the Leading Principal Minor Criterion . . . . . . . . . . . . . . . . . . . . 283

3

<!-- page 4 -->

# Introduction

Linear algebra is one of the basic mathematical languages of economics. Equilibrium conditions, linear approximations, least-squares projections, dynamic systems, Markov processes, and quadratic optimization all rely on linear-algebraic structure. For this reason, linear algebra will appear repeatedly throughout graduate microeconomics, macroeconomics, and econometrics.

Most of you have already worked with matrices, systems of linear equations, determinants, and eigenvalues. Our objective here is not simply to review these calculations. Instead, we will develop the structural ideas that explain why the calculations work and how the different parts of linear algebra fit together.

A central theme is the distinction between a mathematical object and its representation in coordinates. Vectors need not be columns of numbers, and linear maps need not be matrices. Once a basis is chosen, however, vectors acquire coordinates and linear maps acquire matrix representations. Thus we will repeatedly move between
$$\text{abstract linear structure} \longleftrightarrow \text{matrix representation.}$$

This perspective allows many familiar matrix operations to be understood as manifestations of more general properties of linear maps.

We begin with vector spaces, linear combinations, linear independence, bases, and dimension. We then introduce linear maps and their matrix representations, followed by kernels, images, rank, and systems of linear equations. From there we study determinants, invariant subspaces, eigenvalues, eigenvectors, and diagonalization. Finally, inner products add geometric structure—length, orthogonality, and projection—and lead to the spectral theorem and quadratic forms.

4

<!-- page 5 -->

# 1 Vector Spaces and Linear Relations of Vectors

## 1.1 Vector Spaces

The central object of linear algebra is the concept of vector spaces.

> **Definition 1.1 — Vector spaces**
> 
> Let $\mathbb{K}$ be a field. A **vector space over $\mathbb{K}$** (or a **$\mathbb{K}$-vector space**) is a set $V$ equipped with two operations,
> $$+ : V \times V \to V, \quad \cdot : \mathbb{K} \times V \to V,$$
> called **vector addition** and **scalar multiplication**, respectively, such that for all $u, v, w \in V$ and all $\lambda, \mu \in \mathbb{K}$, the following eight axioms hold:
> 
> (1) **Associativity of vector addition:**
> $$(u + v) + w = u + (v + w).$$
> 
> (2) **Commutativity of vector addition:**
> $$u + v = v + u.$$
> 
> (3) **Existence of a zero vector:** there exists an element $0_V \in V$ such that
> $$u + 0_V = 0_V + u = u.$$
> 
> (4) **Existence of additive inverses:** for every $u \in V$, there exists an element $-u \in V$ such that
> $$u + (-u) = (-u) + u = 0_V.$$
> 
> (5) **Compatibility of scalar multiplication with multiplication in $\mathbb{K}$:**
> $$(\lambda\mu)u = \lambda(\mu u).$$
> 
> (6) **Identity element of scalar multiplication:**
> $$1_\mathbb{K} u = u,$$
> where $1_\mathbb{K}$ denotes the multiplicative identity of $\mathbb{K}$.
> 
> (7) **Distributivity with respect to vector addition:**
> $$\lambda(u + v) = \lambda u + \lambda v.$$

5

<!-- page 6 -->

(8) **Distributivity with respect to scalar addition:**
$$(\lambda + \mu)u = \lambda u + \mu u.$$

We will not dive into the formal treatment of a field, for the interested audience, see the following remark.

> **Remark 1.2 — What is a field?**
> 
> A **scalar field** is a set of elements (think of them as numbers) on which we can perform the usual arithmetic operations
> $$+, \quad -, \quad \times, \quad \div,$$
> and still remain within the set.
> 
> A field is usually denoted by $\mathbb{K}$ (from the German *Körper*) or by $\mathbb{F}$ (for *field*). For our purposes, it will suffice to take
> $$\mathbb{K} = \mathbb{R} \quad \text{or} \quad \mathbb{K} = \mathbb{C}.$$

For a vector space $(V, +, \cdot)$, a subset $W$ is called a **vector subspace** of $(V, +, \cdot)$ if $(W, +|_W, \cdot|_W)$ is a vector space, where $+|_W$ and $\cdot|_W$ are $+$ and $\cdot$ defined for $V$ restricted in $W$.

> **Definition 1.3 — Vector subspaces**
> 
> Let $V$ be a vector space over a field $\mathbb{K}$, and let $W \subseteq V$. We say that $W$ is a **vector subspace** of $V$, and write
> $$W \le V,$$
> if $W$, equipped with the vector addition and scalar multiplication inherited from $V$, is itself a vector space over $\mathbb{K}$.
> 
> Equivalently, $W \le V$ if and only if:
> 
> (1) $0_V \in W$;
> 
> (2) $W$ is **closed under vector addition:**
> $$u, v \in W \implies u + v \in W;$$
> 
> (3) $W$ is **closed under scalar multiplication:**
> $$u \in W, \lambda \in \mathbb{K} \implies \lambda u \in W.$$

Let us examine some examples of vector spaces.

6

<!-- page 7 -->

> **Example 1.4 — Examples of vector spaces.**
> 
> Let $\mathbb{K}$ be a field. The following are standard examples of vector spaces over $\mathbb{K}$.
> 
> (1) **Finite-dimensional coordinate spaces.**
> 
> The space
> $$\mathbb{K}^n = \left\{ \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix} : x_1, \dots, x_n \in \mathbb{K} \right\}$$
> of $n$-dimensional column vectors is a vector space over $\mathbb{K}$.
> Likewise, if we denote the space of row vectors by
> $$\mathbb{K}_n = \left\{ \begin{pmatrix} x_1 & \cdots & x_n \end{pmatrix} : x_1, \dots, x_n \in \mathbb{K} \right\},$$
> then $\mathbb{K}_n$ is also a vector space over $\mathbb{K}$.
> Addition and scalar multiplication are defined componentwise. For example,
> $$(x_1, \dots, x_n) + (y_1, \dots, y_n) = (x_1 + y_1, \dots, x_n + y_n),$$
> and
> $$\lambda(x_1, \dots, x_n) = (\lambda x_1, \dots, \lambda x_n).$$
> 
> (2) **The space of sequences.**
> 
> The set
> $$\mathbb{K}^\mathbb{N} = \left\{ (x_1, x_2, \dots) : x_i \in \mathbb{K} \text{ for every } i \in \mathbb{N} \right\}$$
> of all sequences with values in $\mathbb{K}$ is a vector space over $\mathbb{K}$, with addition and scalar multiplication defined coordinatewise:
> $$(x_i)_{i \in \mathbb{N}} + (y_i)_{i \in \mathbb{N}} = (x_i + y_i)_{i \in \mathbb{N}},$$
> and
> $$\lambda(x_i)_{i \in \mathbb{N}} = (\lambda x_i)_{i \in \mathbb{N}}.$$
> 
> (3) **Polynomial spaces.**
> 
> The set
> $$\mathbb{K}[x] = \{a_0 + a_1 x + \dots + a_n x^n : n \in \mathbb{N},\ a_0, \dots, a_n \in \mathbb{K}\}$$
> of all polynomials with coefficients in $\mathbb{K}$ is a vector space over $\mathbb{K}$.
> For any $n \in \mathbb{N}$, the subset
> $$\mathbb{K}_n[x] = \{a_0 + a_1 x + \dots + a_n x^n : a_0, \dots, a_n \in \mathbb{K}\}$$
> of polynomials of degree at most $n$ is a vector subspace of $\mathbb{K}[x]$.
> 
> (4) **Continuous functions.**

7

<!-- page 8 -->

The set
$$C([0,1], \mathbb{K}) = \{f : [0,1] \to \mathbb{K} : f \text{ is continuous}\}$$
is a vector space over $\mathbb{K}$, where
$$(f + g)(x) = f(x) + g(x)$$
and
$$(\lambda f)(x) = \lambda f(x).$$

(5) **Matrix spaces.**

The set
$$\mathbb{K}^{m \times n} = \{A = (a_{ij})_{i=1,\dots,m;\ j=1,\dots,n} : a_{ij} \in \mathbb{K}\}$$
of all $m \times n$ matrices with entries in $\mathbb{K}$ is a vector space over $\mathbb{K}$. Addition and scalar multiplication are defined entrywise:
$$(A + B)_{ij} = a_{ij} + b_{ij}, \quad (\lambda A)_{ij} = \lambda a_{ij}.$$

> **Proposition 1.5 — Elementary properties of vector spaces**
> 
> Let $V$ be a vector space over a field $\mathbb{K}$. Then:
> 
> (1) The zero vector $0_V$ is unique.
> 
> (2) For every $v \in V$, the additive inverse $-v$ is unique.
> 
> (3) For every $v \in V$ and $\lambda \in \mathbb{K}$,
> $$0_\mathbb{K} v = 0_V, \quad \lambda 0_V = 0_V.$$
> 
> (4) For every $v \in V$,
> $$(-1_\mathbb{K})v = -v.$$
> Hence vector subtraction may be defined by
> $$u - v := u + (-v).$$
> 
> (5) For every $\lambda \in \mathbb{K}$ and $v \in V$,
> $$\lambda v = 0_V \implies \lambda = 0_\mathbb{K} \text{ or } v = 0_V.$$

> **Proof.**
> 
> **(1)** Suppose $0_V$ and $\widetilde{0}_V$ are both zero vectors. Then
> $$0_V = 0_V + \widetilde{0}_V = \widetilde{0}_V.$$

8

<!-- page 9 -->

**(2)** Suppose $w_1$ and $w_2$ are both additive inverses of $v$. Then
$$w_1 = w_1 + (v + w_2) = (w_1 + v) + w_2 = 0_V + w_2 = w_2.$$

**(3)** By distributivity,
$$0_\mathbb{K} v = (0_\mathbb{K} + 0_\mathbb{K}) v = 0_\mathbb{K} v + 0_\mathbb{K} v.$$
Cancelling $0_\mathbb{K} v$ gives
$$0_\mathbb{K} v = 0_V.$$
Similarly,
$$\lambda 0_V = \lambda(0_V + 0_V) = \lambda 0_V + \lambda 0_V,$$
and therefore
$$\lambda 0_V = 0_V.$$

**(4)** Since
$$v + (-1_\mathbb{K})v = (1_\mathbb{K} - 1_\mathbb{K})v = 0_\mathbb{K} v = 0_V,$$
the vector $(-1_\mathbb{K})v$ is the additive inverse of $v$. By uniqueness,
$$(-1_\mathbb{K})v = -v.$$

**(5)** Suppose $\lambda v = 0_V$. If $\lambda = 0_\mathbb{K}$, we are done. If $\lambda \neq 0_\mathbb{K}$, then $\lambda^{-1}$ exists because $\mathbb{K}$ is a field. Hence
$$v = 1_\mathbb{K} v = \lambda^{-1}(\lambda v) = \lambda^{-1} 0_V = 0_V.$$
Therefore either $\lambda = 0_\mathbb{K}$ or $v = 0_V$.

## 1.2 Linear Combinations of Vectors

The vector-space axioms allow us to add vectors and multiply them by scalars. By repeatedly applying these two operations, starting from a collection of vectors $v_1, \dots, v_n \in V$, we can construct vectors of the form
$$\lambda_1 v_1 + \lambda_2 v_2 + \dots + \lambda_n v_n, \quad \lambda_1, \dots, \lambda_n \in \mathbb{K}.$$
Such vectors are called **linear combinations** of $v_1, \dots, v_n$.

> **Definition 1.6 — Linear combination**
> 
> Let $V$ be a vector space over a field $\mathbb{K}$, and let
> $$v_1, \dots, v_n \in V.$$

9

<!-- page 10 -->

A vector $v \in V$ is called a **linear combination** of $v_1, \dots, v_n$ if there exist scalars
$$\lambda_1, \dots, \lambda_n \in \mathbb{K}$$
such that
$$v = \lambda_1 v_1 + \dots + \lambda_n v_n = \sum_{i=1}^n \lambda_i v_i.$$
The scalars $\lambda_1, \dots, \lambda_n$ are called the **coefficients** of the linear combination.

We now ask what happens when the coefficients are allowed to vary over *all* possible values in $\mathbb{K}$. The resulting collection of vectors is called the **span** of $v_1, \dots, v_n$.

> **Definition 1.7 — Span**
> 
> Let $V$ be a vector space over a field $\mathbb{K}$, and let $v_1, \dots, v_n \in V$. The **span** of $v_1, \dots, v_n$ is the set of all their linear combinations:
> $$\text{Span}(v_1, \dots, v_n) = \left\{ \lambda_1 v_1 + \dots + \lambda_n v_n = \sum_{i=1}^n \lambda_i v_i : \lambda_1, \dots, \lambda_n \in \mathbb{K} \right\}.$$
> 
> If
> $$\text{Span}(v_1, \dots, v_n) = V,$$
> we say that $v_1, \dots, v_n$ **span** $V$, or that they **generate** $V$.

The following proposition gives an equivalent definition of the span. Its proof uses a common technique used to establish set equality.

> **Proposition 1.8 — Span as the smallest subspace**
> 
> Let $V$ be a vector space over a field $\mathbb{K}$, and let $v_1, \dots, v_n \in V$. Then
> $$\text{Span}(v_1, \dots, v_n) = \bigcap_{\substack{W \le V \\ v_1, \dots, v_n \in W}} W,$$
> where $W \le V$ means that $W$ is a vector subspace of $V$.
> 
> Equivalently, $\text{Span}(v_1, \dots, v_n)$ is the smallest vector subspace of $V$ that contains $v_1, \dots, v_n$.

> **Proof.**
> 
> Let
> $$\mathcal{W} = \{W \le V : v_1, \dots, v_n \in W\}$$

<!-- page 11 -->

be the collection of all subspaces of $V$ that contain $v_1, \dots, v_n$.

We prove the equality by showing both inclusions.

**Left $\subseteq$ Right:** Take
$$x \in \text{Span}(v_1, \dots, v_n).$$

By definition of span, there exist $\lambda_1, \dots, \lambda_n \in \mathbb{K}$ such that
$$x = \lambda_1 v_1 + \dots + \lambda_n v_n.$$

Now let $W \in \mathcal{W}$ be any subspace containing $v_1, \dots, v_n$. Since a subspace is closed under linear combinations,
$$\lambda_1 v_1 + \dots + \lambda_n v_n \in W.$$

Hence $x \in W$.

Because this is true for every $W \in \mathcal{W}$, we have
$$x \in \bigcap_{W \in \mathcal{W}} W.$$

Therefore,
$$\text{Span}(v_1, \dots, v_n) \subseteq \bigcap_{W \in \mathcal{W}} W.$$

**Left $\supseteq$ Right:** The span
$$\text{Span}(v_1, \dots, v_n)$$
is itself a subspace of $V$ containing $v_1, \dots, v_n$. Therefore it is one of the subspaces in $\mathcal{W}$. But the intersection of all sets in $\mathcal{W}$ must be contained in each particular set in $\mathcal{W}$. Hence
$$\bigcap_{W \in \mathcal{W}} W \subseteq \text{Span}(v_1, \dots, v_n).$$

Combining the two inclusions,
$$\text{Span}(v_1, \dots, v_n) = \bigcap_{W \in \mathcal{W}} W.$$

Equipped with the above proposition, it is clear that the span of $v_1, \dots, v_n$ is a vector subspace.

Let’s see some examples.

11

<!-- page 12 -->

> **Example 1.9 — Examples of spans**
> 
> (1) **The span of one nonzero vector in $\mathbb{R}^2$.**
> Let
> $$v = \begin{pmatrix} 1 \\ 2 \end{pmatrix}.$$
> Then
> $$\text{Span}(v) = \left\{ \lambda \begin{pmatrix} 1 \\ 2 \end{pmatrix} : \lambda \in \mathbb{R} \right\}.$$
> Thus $\text{Span}(v)$ is the line through the origin in the direction of $v$.
> 
> (2) **Two vectors that span $\mathbb{R}^2$.**
> Let
> $$v_1 = \begin{pmatrix} 1 \\ 0 \end{pmatrix}, \quad v_2 = \begin{pmatrix} 0 \\ 1 \end{pmatrix}.$$
> Then
> $$\text{Span}(v_1, v_2) = \{\lambda_1 v_1 + \lambda_2 v_2 : \lambda_1, \lambda_2 \in \mathbb{R}\}.$$
> Since
> $$\lambda_1 v_1 + \lambda_2 v_2 = \begin{pmatrix} \lambda_1 \\ \lambda_2 \end{pmatrix},$$
> we obtain
> $$\text{Span}(v_1, v_2) = \mathbb{R}^2.$$
> 
> (3) **Two vectors that do not generate a larger space.**
> Let
> $$v_1 = \begin{pmatrix} 1 \\ 2 \end{pmatrix}, \quad v_2 = \begin{pmatrix} 2 \\ 4 \end{pmatrix}.$$
> Since
> $$v_2 = 2v_1,$$
> every linear combination satisfies
> $$\lambda_1 v_1 + \lambda_2 v_2 = (\lambda_1 + 2\lambda_2)v_1.$$
> Hence
> $$\text{Span}(v_1, v_2) = \text{Span}(v_1).$$
> So adding $v_2$ does not enlarge the span.
> 
> (4) **Polynomial spaces.**
> In $\mathbb{K}[x]$,
> $$\text{Span}(1, x, x^2) = \{a_0 + a_1 x + a_2 x^2 : a_0, a_1, a_2 \in \mathbb{K}\}.$$

12

<!-- page 13 -->

Therefore,
$$\text{Span}(1, x, x^2) = \mathbb{K}_2[x].$$
More generally,
$$\text{Span}(1, x, \dots, x^n) = \mathbb{K}_n[x].$$

(5) **A span of functions.**
In $C([0, 1], \mathbb{R})$, consider the functions
$$f_1(x) = 1, \quad f_2(x) = x.$$
Then
$$\text{Span}(f_1, f_2) = \{a + bx : a, b \in \mathbb{R}\}.$$
Thus the span consists of all affine functions on $[0, 1]$.

### 1.3 Linear Independence
The span of a collection of vectors tells us which vectors can be generated from them by taking linear combinations. A different question is whether those representations are *unique*.

Suppose that a vector $v$ has two representations,
$$v = \lambda_1 v_1 + \dots + \lambda_n v_n = \mu_1 v_1 + \dots + \mu_n v_n.$$
Subtracting the two representations gives
$$(\lambda_1 - \mu_1)v_1 + \dots + (\lambda_n - \mu_n)v_n = 0_V.$$
Thus, uniqueness of the coefficients is determined entirely by the ways in which the zero vector can be represented as a linear combination of $v_1, \dots, v_n$. This motivates the notion of linear independence.

**Definition 1.10 — Linear independence**
Let $V$ be a vector space over a field $\mathbb{K}$, and let $v_1, \dots, v_n \in V$.
The vectors $v_1, \dots, v_n$ are said to be **linearly independent** if
$$\lambda_1 v_1 + \dots + \lambda_n v_n = 0_V$$
implies
$$\lambda_1 = \dots = \lambda_n = 0_{\mathbb{K}}.$$
Otherwise, $v_1, \dots, v_n$ are said to be **linearly dependent**. Equivalently, they are linearly

<!-- page 14 -->

dependent if there exist scalars $\lambda_1, \dots, \lambda_n \in \mathbb{K}$, not all zero, such that
$$\lambda_1 v_1 + \dots + \lambda_n v_n = 0_V.$$
Linear independence therefore means that none of the vectors carries information that can be reproduced by the others. The following proposition shows that it is also exactly the condition under which linear-combination representations are unique.

**Proposition 1.11 — Uniqueness of representation**
The vectors $v_1, \dots, v_n \in V$ are linearly independent if and only if every vector in
$$\text{Span}(v_1, \dots, v_n)$$
has a unique representation as a linear combination of $v_1, \dots, v_n$.

**Proof.**
Suppose first that $v_1, \dots, v_n$ are linearly independent, and that
$$\lambda_1 v_1 + \dots + \lambda_n v_n = \mu_1 v_1 + \dots + \mu_n v_n.$$
Moving everything to one side gives
$$(\lambda_1 - \mu_1)v_1 + \dots + (\lambda_n - \mu_n)v_n = 0_V.$$
By linear independence,
$$\lambda_i - \mu_i = 0_{\mathbb{K}} \quad \text{for every } i,$$
so
$$\lambda_i = \mu_i \quad \text{for every } i.$$
Hence the representation is unique.
Conversely, suppose every vector in the span has a unique representation. In particular, $0_V$ has the representation
$$0_V = 0_{\mathbb{K}}v_1 + \dots + 0_{\mathbb{K}}v_n.$$
If there were a nontrivial linear combination
$$\lambda_1 v_1 + \dots + \lambda_n v_n = 0_V,$$
then $0_V$ would have two different representations. Thus all $\lambda_i$ must be zero, and $v_1, \dots, v_n$ are linearly independent.

There is another useful way to understand linear dependence: a dependent collection contains a

<!-- page 15 -->

redundant vector.

**Proposition 1.12 — Characterization of linear dependence**
The vectors $v_1, \dots, v_n$ are linearly dependent if and only if at least one of them can be written as a linear combination of the others;
that is, for some $i$,
$$v_i \in \text{Span}(v_1, \dots, v_{i-1}, v_{i+1}, \dots, v_n).$$
Moreover, removing such a vector does not change the span.

**Proof.**
Suppose first that $v_1, \dots, v_n$ are linearly dependent. Then there exist $\lambda_1, \dots, \lambda_n \in \mathbb{K}$, not all zero, such that
$$\lambda_1 v_1 + \dots + \lambda_n v_n = 0_V.$$
Choose an index $i$ for which $\lambda_i \neq 0_{\mathbb{K}}$. Because $\mathbb{K}$ is a field, $\lambda_i^{-1}$ exists, and we can solve for $v_i$:
$$v_i = -\sum_{j \neq i} \frac{\lambda_j}{\lambda_i} v_j.$$
Thus $v_i$ is a linear combination of the other vectors.
Conversely, suppose that for some $i$,
$$v_i = \sum_{j \neq i} \lambda_j v_j.$$
Then
$$v_i - \sum_{j \neq i} \lambda_j v_j = 0_V$$
is a nontrivial linear relation, since the coefficient on $v_i$ is 1. Hence the vectors are linearly dependent.
Finally, because $v_i$ can already be generated by the remaining vectors, including $v_i$ cannot enlarge their span. Therefore,
$$\text{Span}(v_1, \dots, v_n) = \text{Span}(v_1, \dots, v_{i-1}, v_{i+1}, \dots, v_n).$$
The previous proposition formalizes the idea that linear dependence is *redundancy*. This leads to a fundamental counting principle: a collection generated by $n$ vectors cannot contain more than $n$ linearly independent directions.

<!-- page 16 -->

**Theorem 1.13 — Counting principle**
Let
$$u_1, \dots, u_m, \quad v_1, \dots, v_n$$
be vectors in $V$. Suppose that
$$u_i \in \text{Span}(v_1, \dots, v_n) \quad \text{for every } i.$$
If
$$m > n,$$
then $u_1, \dots, u_m$ are linearly dependent.

**Proof.**
Suppose, toward a contradiction, that
$$u_1, \dots, u_m$$
are linearly independent.
Let
$$W = \text{Span}(v_1, \dots, v_n).$$
By assumption, every $u_i$ belongs to $W$.
We now successively replace the vectors $v_j$ by the vectors $u_i$ without changing the span.
Because $u_1 \in W$, we can write
$$u_1 = a_1 v_1 + \dots + a_n v_n.$$
Since $u_1 \neq 0_V$, at least one coefficient is nonzero. Relabeling the $v_j$ if necessary, suppose $a_1 \neq 0$. We can solve for $v_1$:
$$v_1 = \frac{1}{a_1} (u_1 - a_2 v_2 - \dots - a_n v_n).$$
Hence
$$W = \text{Span}(u_1, v_2, \dots, v_n).$$
Now consider $u_2$. Since $u_2 \in W$,
$$u_2 = b_1 u_1 + b_2 v_2 + \dots + b_n v_n.$$
Because $u_1, u_2$ are linearly independent, $u_2$ cannot belong to $\text{Span}(u_1)$. Therefore at least one of
$$b_2, \dots, b_n$$
must be nonzero. We can solve for the corresponding $v_j$ and replace it by $u_2$. Thus, after

<!-- page 17 -->

relabeling if necessary,
$$W = \text{Span}(u_1, u_2, v_3, \dots, v_n).$$
Continuing in this way, after $n$ steps we obtain
$$W = \text{Span}(u_1, \dots, u_n).$$
But $m > n$, so $u_{n+1}$ exists. Because $u_{n+1} \in W$,
$$u_{n+1} \in \text{Span}(u_1, \dots, u_n).$$
By Proposition 1.3.2, this means that
$$u_1, \dots, u_n, u_{n+1}$$
are linearly dependent, contradicting our assumption.
Therefore $u_1, \dots, u_m$ must be linearly dependent.

**Remark 1.14**
Theorem 1.3.1 can be summarized informally as:
*"more independent vectors cannot be generated by fewer vectors."*
If $m$ vectors are all generated by $n$ vectors and $m > n$, some redundancy among the $m$ vectors is unavoidable.

### 1.4 Basis
We have now developed two complementary ideas.
A collection of vectors that *spans* a space is large enough to generate every vector in that space. A collection of vectors that is *linearly independent* contains no redundancy: none of its vectors can be generated from the others.
A **basis** combines these two requirements. It is a collection that generates the whole space while containing no redundant vectors. As a consequence, a basis gives every vector in the space a unique system of coordinates.

**Definition 1.15 — Basis**
Let $W \leq V$ be a vector subspace. A finite collection
$$v_1, \dots, v_n \in W$$

<!-- page 18 -->

is called a **basis** of $W$ if
(1) $v_1, \dots, v_n$ are linearly independent;
(2) $v_1, \dots, v_n$ span $W$, that is,
$$W = \text{Span}(v_1, \dots, v_n).$$
Do different bases have the same size? The answer is yes for finite basis by the following theorem.

**Theorem 1.16 — All finite bases have the same size**
Let $W$ be a vector space. If
$$u_1, \dots, u_m \quad \text{and} \quad v_1, \dots, v_n$$
are two finite bases of $W$, then
$$m = n.$$

**Proof**
Because
$$u_1, \dots, u_m$$
are linearly independent and
$$v_1, \dots, v_n$$
span $W$, theorem 1.13 implies
$$m \leq n.$$
Reversing the roles of the two bases, $v_1, \dots, v_n$ are linearly independent and $u_1, \dots, u_m$ span $W$. Hence
$$n \leq m.$$
Therefore,
$$m = n.$$
Theorem 1.16 shows that although a vector space may have many different bases, every finite basis contains the same number of vectors. This makes the following definition unambiguous.

**Definition 1.17 — Dimension**
Let $W$ be a vector space that has a finite basis. The **dimension** of $W$, denoted by
$$\dim W,$$
is the number of vectors in any basis of $W$.

<!-- page 19 -->

Thus, if
$$v_1, \dots, v_n$$
is a basis of $W$, then
$$\dim W = n.$$
If $W$ has no finite basis, we say that $W$ is **infinite-dimensional**.

There are two useful ways to recognize a basis. Starting from a linearly independent collection, a basis is one to which no new vector can be added without creating dependence. Starting from a spanning collection, a basis is one from which no vector can be removed without losing the spanning property.

**Proposition 1.18 — Basis as a maximal linearly independent collection**
Let
$$v_1, \dots, v_n \in W$$
be linearly independent. Then $v_1, \dots, v_n$ form a basis of $W$ if and only if they are **maximal linearly independent**: no vector in $W$ can be added to $v_1, \dots, v_n$ without making the resulting collection linearly dependent.

**Proof**
Suppose first that $v_1, \dots, v_n$ form a basis of $W$.
For every $w \in W$,
$$w \in \text{Span}(v_1, \dots, v_n).$$
Therefore
$$v_1, \dots, v_n, w$$
are linearly dependent. Hence no additional vector can be added while preserving linear independence.
Conversely, suppose $v_1, \dots, v_n$ are maximal linearly independent. If they did not span $W$, there would exist
$$w \in W \setminus \text{Span}(v_1, \dots, v_n).$$
But then
$$v_1, \dots, v_n, w$$
would still be linearly independent, contradicting maximality.
Therefore
$$W = \text{Span}(v_1, \dots, v_n),$$

<!-- page 20 -->

so $v_1, \dots, v_n$ form a basis of $W$.

**Proposition 1.19 — Basis as a minimal spanning collection**
Let
$$v_1, \dots, v_n$$
span $W$. Then $v_1, \dots, v_n$ form a basis of $W$ if and only if they are **minimal spanning**: removing any one of the vectors causes the remaining vectors to no longer span $W$.

**Proof**
Suppose first that $v_1, \dots, v_n$ form a basis of $W$.
If one vector, say $v_i$, could be removed without changing the span, then
$$v_i \in \text{Span}(v_1, \dots, v_{i-1}, v_{i+1}, \dots, v_n).$$
Hence $v_i$ would be a linear combination of the other vectors, contradicting linear independence.
Conversely, suppose $v_1, \dots, v_n$ span $W$ and are minimal spanning.
If they were linearly dependent, one of the vectors could be expressed as a linear combination of the others. That vector could then be removed without changing the span, contradicting minimality.
Hence $v_1, \dots, v_n$ are linearly independent. Since they also span $W$, they form a basis.

**Remark 1.20 — Maximal versus maximum**
The word **maximal** in proposition 1.18 means that the collection cannot be enlarged while retaining linear independence. It does not mean that we first compare the cardinalities of all linearly independent collections and choose one with the largest size.
Similarly, **minimal spanning** means that no vector can be removed while preserving the span.

Once the dimension of a vector space is known, checking that a collection is a basis becomes particularly easy. If we already have exactly the right number of vectors, it is enough to check either linear independence or spanning; we do not need to verify both.

**Proposition 1.21 — The right number of vectors is enough**
Suppose
$$\dim W = n.$$

<!-- page 21 -->

Then:
(1) any $n$ linearly independent vectors in $W$ form a basis of $W$;
(2) any $n$ vectors that span $W$ form a basis of $W$.

**Proof**
For (1), let
$$v_1, \dots, v_n$$
be linearly independent.
If they did not span $W$, there would exist
$$w \in W \setminus \text{Span}(v_1, \dots, v_n).$$
Then
$$v_1, \dots, v_n, w$$
would be $n + 1$ linearly independent vectors in $W$.
But any basis of $W$ contains only $n$ vectors, contradicting theorem 1.13. Therefore
$$W = \text{Span}(v_1, \dots, v_n),$$
so the vectors form a basis.
For (2), let
$$v_1, \dots, v_n$$
span $W$.
If they were linearly dependent, one of them could be removed without changing the span.
We would then have a spanning collection containing only $n - 1$ vectors.
But a basis of $W$ contains $n$ linearly independent vectors, again contradicting theorem 1.13.
Therefore $v_1, \dots, v_n$ are linearly independent and hence form a basis.

**Remark 1.22 — Rank of a set**
If one wishes to define the rank of an arbitrary subset $S \subseteq V$, the natural definition is
$$\text{Rank}(S) := \dim \text{Span}(S),$$
provided that $\text{Span}(S)$ is finite-dimensional.
Thus the rank measures the number of linearly independent directions generated by $S$.

<!-- page 22 -->

**Example 1.23 — Standard bases**
(1) **Coordinate space.**
The vectors
$$e_1 = \begin{pmatrix} 1 \\ 0 \\ \vdots \\ 0 \end{pmatrix}, \quad e_2 = \begin{pmatrix} 0 \\ 1 \\ \vdots \\ 0 \end{pmatrix}, \quad \dots, \quad e_n = \begin{pmatrix} 0 \\ 0 \\ \vdots \\ 1 \end{pmatrix}$$
form the **canonical basis** of $\mathbb{K}^n$.
Hence
$$\dim \mathbb{K}^n = n.$$
(2) **Polynomial space.**
The polynomials
$$1, x, x^2, \dots, x^n$$
form a basis of
$$\mathbb{K}_n[x].$$
Therefore,
$$\dim \mathbb{K}_n[x] = n + 1.$$
(3) **Matrix space.**
For
$$1 \leq i \leq m, \quad 1 \leq j \leq n,$$
let $E_{ij}$ denote the $m \times n$ matrix whose $(i, j)$-entry is 1 and whose other entries are zero.
Then
$$\{E_{ij} : 1 \leq i \leq m, 1 \leq j \leq n\}$$
is a basis of $\mathbb{K}^{m \times n}$.
Hence
$$\dim \mathbb{K}^{m \times n} = mn.$$
(4) **An infinite-dimensional space.**
The polynomial space
$$\mathbb{K}[x]$$
is infinite-dimensional.
Indeed, for every $n$,
$$1, x, x^2, \dots, x^n$$
are linearly independent. Thus $\mathbb{K}[x]$ contains linearly independent collections of arbitrarily large finite size, so it cannot have a finite basis.

<!-- page 23 -->

### 1.5 Change of Basis
A basis is a coordinate system for a vector space. The coordinate is unique for each vector by proposition 1.11.

**Definition 1.24 — Coordinate vector.**
Let
$$\mathcal{B} = (v_1, \dots, v_n)$$
be a basis of an $n$-dimensional vector space $V$ over $\mathbb{K}$.
For every $x \in V$, there exist unique scalars $x_1, \dots, x_n \in \mathbb{K}$ such that
$$x = x_1 v_1 + \dots + x_n v_n.$$
The vector
$$[x]_{\mathcal{B}} = \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix}$$
is called the **coordinate vector** of $x$ with respect to $\mathcal{B}$.

Now suppose that
$$\mathcal{E} = (e_1, \dots, e_n) \quad \text{and} \quad \mathcal{F} = (f_1, \dots, f_n)$$
are two bases of an $n$-dimensional vector space $V$.
Because $\mathcal{E}$ is a basis, each vector $f_j$ can be written uniquely as a linear combination of $e_1, \dots, e_n$.
Thus there exist scalars $p_{ij} \in \mathbb{K}$ such that
$$\begin{cases} f_1 = p_{11}e_1 + p_{21}e_2 + \dots + p_{n1}e_n, \\ f_2 = p_{12}e_1 + p_{22}e_2 + \dots + p_{n2}e_n, \\ \vdots \\ f_n = p_{1n}e_1 + p_{2n}e_2 + \dots + p_{nn}e_n. \end{cases}$$
Collecting these equations into matrix form gives
$$(f_1, \dots, f_n) = (e_1, \dots, e_n) \begin{pmatrix} p_{11} & p_{12} & \dots & p_{1n} \\ p_{21} & p_{22} & \dots & p_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ p_{n1} & p_{n2} & \dots & p_{nn} \end{pmatrix}.$$

<!-- page 24 -->

Denote the matrix above by
$$P = \begin{pmatrix} p_{11} & p_{12} & \dots & p_{1n} \\ p_{21} & p_{22} & \dots & p_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ p_{n1} & p_{n2} & \dots & p_{nn} \end{pmatrix}.$$
Then the change of basis can be written simply as
$$(f_1, \dots, f_n) = (e_1, \dots, e_n)P.$$

**Definition 1.25 — Transition matrix**
Let
$$\mathcal{E} = (e_1, \dots, e_n) \quad \text{and} \quad \mathcal{F} = (f_1, \dots, f_n)$$
be two bases of $V$.
If
$$(f_1, \dots, f_n) = (e_1, \dots, e_n)P,$$
then $P$ is called the **transition matrix from the basis $\mathcal{E}$ to the basis $\mathcal{F}$**.

The meaning of $P$ is particularly simple. Its $j$-th column is the coordinate vector of $f_j$ with respect to the basis $\mathcal{E}$:
$$P = ([f_1]_{\mathcal{E}}, [f_2]_{\mathcal{E}}, \dots, [f_n]_{\mathcal{E}}).$$
Thus, to find the transition matrix from $\mathcal{E}$ to $\mathcal{F}$, we express each vector of the new basis $\mathcal{F}$ in terms of the old basis $\mathcal{E}$, and place the resulting coordinate vectors into the columns of $P$.

**Proposition 1.26 — The transition matrix is invertible**
The transition matrix between two bases is invertible. Moreover, if
$$(f_1, \dots, f_n) = (e_1, \dots, e_n)P,$$
then
$$(e_1, \dots, e_n) = (f_1, \dots, f_n)P^{-1}.$$
Hence the transition matrix from $\mathcal{F}$ back to $\mathcal{E}$ is $P^{-1}$.

**Proof**
Since $f_1, \dots, f_n$ form a basis of $V$, each $e_j$ can be written uniquely as a linear combination of

<!-- page 25 -->

$f_1, \dots, f_n$. Therefore, there exists an $n \times n$ matrix $Q$ such that
$$(e_1, \dots, e_n) = (f_1, \dots, f_n)Q.$$
Using
$$(f_1, \dots, f_n) = (e_1, \dots, e_n)P,$$
we obtain
$$(e_1, \dots, e_n) = (e_1, \dots, e_n)PQ.$$
Write
$$PQ = (a_{ij})_{i,j=1}^n.$$
Then the $j$-th column of the equation above gives
$$e_j = a_{1j}e_1 + \dots + a_{nj}e_n.$$
But since $e_1, \dots, e_n$ are linearly independent, the representation of $e_j$ in this basis is unique.
Hence
$$a_{ij} = \begin{cases} 1, & i = j, \\ 0, & i \neq j. \end{cases}$$
Therefore,
$$PQ = I_n.$$
Similarly, substituting
$$(e_1, \dots, e_n) = (f_1, \dots, f_n)Q$$
into
$$(f_1, \dots, f_n) = (e_1, \dots, e_n)P$$
gives
$$(f_1, \dots, f_n) = (f_1, \dots, f_n)QP.$$
By uniqueness of representation with respect to the basis $f_1, \dots, f_n$,
$$QP = I_n.$$
Thus
$$Q = P^{-1}.$$
Hence $P$ is invertible, and
$$(e_1, \dots, e_n) = (f_1, \dots, f_n)P^{-1}.$$
We now turn from the change of the basis vectors to the corresponding change of the coordinates of a vector.

<!-- page 26 -->

Let $x \in V$. Suppose that the coordinates of $x$ with respect to $\mathcal{E}$ and $\mathcal{F}$ are
$$X = \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix}, \quad Y = \begin{pmatrix} y_1 \\ \vdots \\ y_n \end{pmatrix},$$
respectively. Thus
$$x = x_1e_1 + \dots + x_ne_n = y_1f_1 + \dots + y_nf_n.$$
In matrix notation,
$$x = (e_1, \dots, e_n)X$$
and
$$x = (f_1, \dots, f_n)Y.$$
Since
$$(f_1, \dots, f_n) = (e_1, \dots, e_n)P,$$
we have
$$(e_1, \dots, e_n)X = (e_1, \dots, e_n)PY.$$
Because $e_1, \dots, e_n$ are linearly independent,
$$X = PY.$$
Equivalently,
$$Y = P^{-1}X.$$

**Proposition 1.27 — Coordinate transformation formula**
Suppose
$$(f_1, \dots, f_n) = (e_1, \dots, e_n)P.$$
If a vector $x \in V$ has coordinate vectors
$$X = [x]_{\mathcal{E}}, \quad Y = [x]_{\mathcal{F}},$$
then
$$X = PY, \quad Y = P^{-1}X.$$

<!-- page 27 -->

**Remark 1.28 — Basis vectors and coordinates move in opposite directions**
It is important to distinguish the change of the basis from the change of coordinates.
The basis transformation is
$$(f_1, \dots, f_n) = (e_1, \dots, e_n)P,$$
whereas the coordinates satisfy
$$[x]_{\mathcal{E}} = P[x]_{\mathcal{F}}.$$
Therefore, when we change from the $\mathcal{E}$-basis to the $\mathcal{F}$-basis, the coordinate vector transforms by the inverse matrix:
$$[x]_{\mathcal{F}} = P^{-1}[x]_{\mathcal{E}}.$$

# 2 Linear Maps and Matrices
So far, we have studied the structure of a vector space itself: linear combinations, subspaces, linear independence, bases, and coordinates. A choice of basis allows us to describe abstract vectors by coordinate vectors in $\mathbb{K}^n$.
We now turn from studying *vectors* to studying *maps between vector spaces*.
Among all possible maps between vector spaces, the ones that are compatible with the vector-space structure are the **linear maps**. As we will see, once bases are chosen, every linear map can be represented by a matrix. Conversely, every matrix describes a linear map between coordinate spaces.
Thus there are two equivalent ways of describing the same object:
$$\boxed{\text{linear map between vector spaces (abstract / geometric description)}} \longleftrightarrow \boxed{\text{matrix (coordinate / algebraic description)}}$$
The bridge between these two descriptions is the choice of bases.

## 2.1 Linear Maps
We first define what it means for a map to preserve the linear structure of vector spaces.
Let $V$ and $W$ be vector spaces over the same field $\mathbb{K}$. A general map
$$T : V \to W$$
assigns to every vector $v \in V$ a vector $T(v) \in W$.
For such a map to respect the vector-space structure, it should be compatible with the two operations that define a vector space: vector addition and scalar multiplication.

<!-- page 28 -->

**Definition 2.1 — Linear map**
Let $V$ and $W$ be vector spaces over the same field $\mathbb{K}$. A map
$$T : V \to W$$
is called a **linear map** if, for every $u, v \in V$ and every $\lambda \in \mathbb{K}$,
$$T(u + v) = T(u) + T(v)$$
and
$$T(\lambda v) = \lambda T(v).$$
Equivalently, $T$ is linear if and only if
$$T(\lambda u + \mu v) = \lambda T(u) + \mu T(v)$$
for every $u, v \in V$ and every $\lambda, \mu \in \mathbb{K}$.

**Example 2.2 — Examples of linear maps**
Let $V$ and $W$ be vector spaces over the same field $\mathbb{K}$.
(1) **Zero map.**
$$0 : V \to W, \quad v \mapsto 0_W.$$
(2) **Identity map.**
$$I_V : V \to V, \quad v \mapsto v.$$
(3) **Scaling.**
Fix $c \in \mathbb{K}$. Define
$$T : V \to V, \quad T(v) = cv.$$
(4) **A linear map between coordinate spaces.**
Define
$$T : \mathbb{R}^2 \to \mathbb{R}^3$$
by
$$T\begin{pmatrix} x \\ y \end{pmatrix} = \begin{pmatrix} x + y \\ 2x - y \\ 3y \end{pmatrix}.$$
For
$$u = \begin{pmatrix} x_1 \\ y_1 \end{pmatrix}, \quad v = \begin{pmatrix} x_2 \\ y_2 \end{pmatrix},$$

<!-- page 29 -->

we have
$$T(\lambda u + \mu v) = \lambda T(u) + \mu T(v),$$
so $T$ is linear.

**Remark 2.3 — Linear transformation**
A linear map
$$T : V \to V$$
from a vector space to itself is called a **linear transformation** of $V$.
Thus the zero map $0 : V \to V$, the identity map $I_V$, and the scaling map
$$v \mapsto cv$$
are all linear transformations of $V$.

**Proposition 2.4 — Linear maps preserve linear combinations**
If $T : V \to W$ is linear, then for any $v_1, \dots, v_n \in V$ and $\lambda_1, \dots, \lambda_n \in \mathbb{K}$,
$$T(\lambda_1 v_1 + \dots + \lambda_n v_n) = \lambda_1 T(v_1) + \dots + \lambda_n T(v_n).$$

**Proof**
Follow the definition and use induction.

## 2.2 The Vector Space of Linear Maps
Once $V$ and $W$ are fixed, we can consider not just one linear map $T : V \to W$, but the collection of *all* linear maps from $V$ to $W$. This collection itself has a natural vector-space structure.

**Definition 2.5 — The space $\mathcal{L}(V, W)$**
Let $V$ and $W$ be vector spaces over the same field $\mathbb{K}$. We denote by
$$\mathcal{L}(V, W)$$
the set of all linear maps from $V$ to $W$:
$$\mathcal{L}(V, W) = \{T : V \to W : T \text{ is linear}\}.$$

<!-- page 30 -->

For $S, T \in \mathcal{L}(V, W)$ and $\lambda \in \mathbb{K}$, define addition and scalar multiplication pointwise by
$$(S + T)(v) := S(v) + T(v), \quad v \in V,$$
and
$$(\lambda T)(v) := \lambda T(v), \quad v \in V.$$
The word *pointwise* means that to add two linear maps, we simply apply both maps to the same vector and add the resulting vectors in $W$.

**Proposition 2.6 — $\mathcal{L}(V, W)$ is a vector space**
With the operations defined above,
$$\mathcal{L}(V, W)$$
is a vector space over $\mathbb{K}$.

**Proof**
We first check that the operations stay inside $\mathcal{L}(V, W)$.
Let $S, T \in \mathcal{L}(V, W)$. For $u, v \in V$ and $\alpha, \beta \in \mathbb{K}$,
$$(S + T)(\alpha u + \beta v) = S(\alpha u + \beta v) + T(\alpha u + \beta v)$$
$$= \alpha S(u) + \beta S(v) + \alpha T(u) + \beta T(v)$$
$$= \alpha(S + T)(u) + \beta(S + T)(v).$$
Thus $S + T$ is linear.
Similarly, for $\lambda \in \mathbb{K}$,
$$(\lambda T)(\alpha u + \beta v) = \lambda T(\alpha u + \beta v)$$
$$= \alpha(\lambda T)(u) + \beta(\lambda T)(v),$$
so $\lambda T$ is also linear.
The remaining vector-space axioms follow pointwise from the corresponding axioms in $W$.
For example,
$$((R + S) + T)(v) = R(v) + S(v) + T(v) = (R + (S + T))(v)$$
for every $v \in V$.
The zero vector of $\mathcal{L}(V, W)$ is the **zero map**
$$0 : V \to W, \quad 0(v) = 0_W,$$

<!-- page 31 -->

and the additive inverse of $T$ is the map $-T$ defined by
$$(-T)(v) = -T(v).$$
Hence $\mathcal{L}(V, W)$ is a vector space.

Let's see an example.

**Example 2.7 — Linear combinations of linear maps**
Consider $S, T : \mathbb{R}^2 \to \mathbb{R}^2$ defined by
$$S(x, y) = (x, 0), \quad T(x, y) = (0, y).$$
Both are linear.
For $\alpha, \beta \in \mathbb{R}$,
$$(\alpha S + \beta T)(x, y) = \alpha S(x, y) + \beta T(x, y) = (\alpha x, \beta y).$$
Thus varying $\alpha$ and $\beta$ generates a family of linear maps in $\mathcal{L}(\mathbb{R}^2, \mathbb{R}^2)$.

## 2.3 Composition of Linear Maps
Besides adding and scaling linear maps, we can also apply one linear map after another.
Suppose
$$T : U \to V, \quad S : V \to W$$
are linear maps. Starting from $u \in U$, we first apply $T$ and then apply $S$:
$$u \mapsto T(u) \mapsto S(T(u)).$$
Graphically,
$$U \xrightarrow{T} V \xrightarrow{S} W.$$
$$ST$$

**Definition 2.8 — Composition of linear maps**
Let
$$T : U \to V, \quad S : V \to W$$
be linear maps. Their **composition** is the map
$$S \circ T : U \to W$$

<!-- page 32 -->

defined by
$$(S \circ T)(u) = S(T(u)).$$
We will also use the product notation
$$ST := S \circ T.$$
Thus,
$$(ST)(u) = S(T(u)).$$

**Proposition 2.9 — Composition preserves linearity**
If
$$T : U \to V, \quad S : V \to W$$
are linear, then
$$ST : U \to W$$
is linear.

**Proof**
For $u, v \in U$ and $\lambda, \mu \in \mathbb{K}$,
$$(ST)(\lambda u + \mu v) = S(T(\lambda u + \mu v))$$
$$= S(\lambda T(u) + \mu T(v))$$
$$= \lambda S(T(u)) + \mu S(T(v))$$
$$= \lambda(ST)(u) + \mu(ST)(v).$$
Hence $ST$ is linear.

Composition of linear maps behaves much like multiplication: it is associative and distributes over addition, but it is generally not commutative.

**Proposition 2.10 — Properties of composition**
Whenever the compositions are well-defined:
(1) **Associativity:** if
$$T : U \to V, \quad S : V \to W, \quad R : W \to X,$$
then
$$R(ST) = (RS)T.$$

<!-- page 33 -->

(2) **Distributivity:**
$$(S_1 + S_2)T = S_1T + S_2T,$$
and
$$S(T_1 + T_2) = ST_1 + ST_2.$$
(3) **Compatibility with scalar multiplication:**
$$(\lambda S)T = \lambda(ST) = S(\lambda T).$$
(4) **Identity:**
$$I_V T = T = TI_U.$$

**Remark 2.11 — Composition is not commutative**
The order of composition matters.
For general maps
$$T : U \to V, \quad S : V \to W,$$
the composition
$$ST : U \to W$$
is defined, whereas $TS$ need not even be defined.
Even when
$$S, T : V \to V,$$
so that both compositions exist, in general
$$ST \neq TS.$$

**Example 2.12 — Composition need not commute**
Define
$$S, T : \mathbb{R}^2 \to \mathbb{R}^2$$
by
$$T(x, y) = (x, 0), \quad S(x, y) = (y, x).$$
Then
$$(ST)(x, y) = S(T(x, y)) = S(x, 0) = (0, x),$$
whereas
$$(TS)(x, y) = T(S(x, y)) = T(y, x) = (y, 0).$$

<!-- page 34 -->

Hence
$$ST \neq TS.$$
The difference can be seen directly from the order in which the maps are applied:
$$(x, y) \xrightarrow{T} (x, 0) \xrightarrow{S} (0, x)$$
whereas
$$(x, y) \xrightarrow{S} (y, x) \xrightarrow{T} (y, 0).$$

**Remark 2.13 — The algebra of linear transformations**
When the domain and codomain are the same vector space,
$$\mathcal{L}(V, V),$$
usually abbreviated as
$$\mathcal{L}(V),$$
has two kinds of structure.
First, $\mathcal{L}(V)$ is a vector space under addition and scalar multiplication. Second, any two linear transformations
$$S, T \in \mathcal{L}(V)$$
can be composed, giving
$$ST \in \mathcal{L}(V).$$
Composition is associative and distributes over addition:
$$R(ST) = (RS)T,$$
$$(S + T)R = SR + TR, \quad R(S + T) = RS + RT.$$
It is also compatible with scalar multiplication, and the identity map $I_V$ serves as a multiplicative identity.
Thus,
$$\mathcal{L}(V) \text{ is an associative algebra over } \mathbb{K}.$$
In general this algebra is not commutative, since one may have
$$ST \neq TS.$$

<!-- page 35 -->

## 2.4 Matrix of a Linear Map
A linear map is completely determined by what it does to a basis.
Indeed, let
$$T : V \to W$$
be linear, and let
$$\mathcal{E} = (e_1, \dots, e_n)$$
be a basis of $V$. Every vector $v \in V$ can be written uniquely as
$$v = x_1e_1 + \dots + x_ne_n.$$
By linearity,
$$T(v) = x_1T(e_1) + \dots + x_nT(e_n).$$
Thus, once we know
$$T(e_1), \dots, T(e_n),$$
we know $T(v)$ for every $v \in V$.

**Proposition 2.14 — A linear map is determined by its values on a basis**
Let $\mathcal{E} = (e_1, \dots, e_n)$ be a basis of $V$.
If two linear maps
$$S, T : V \to W$$
satisfy
$$S(e_i) = T(e_i), \quad i = 1, \dots, n,$$
then
$$S = T.$$

**Proof**
Take any $v \in V$. Since $\mathcal{E}$ is a basis, there exist unique scalars $x_1, \dots, x_n \in \mathbb{K}$ such that
$$v = x_1e_1 + \dots + x_ne_n.$$
By linearity,
$$S(v) = x_1S(e_1) + \dots + x_nS(e_n),$$
and
$$T(v) = x_1T(e_1) + \dots + x_nT(e_n).$$

<!-- page 36 -->

Since $S(e_i) = T(e_i)$ for every $i$,
$$S(v) = T(v).$$
Because this holds for every $v \in V$, we conclude that
$$S = T.$$

This observation suggests a simple way to record a linear map. We only need to record the images of the basis vectors of $V$.
Let
$$\mathcal{E} = (e_1, \dots, e_n)$$
be a basis of $V$, and let
$$\mathcal{F} = (f_1, \dots, f_m)$$
be a basis of $W$.
Since $T(e_i) \in W$, each $T(e_i)$ can be written uniquely in the basis $\mathcal{F}$. Thus
$$\begin{cases} T(e_1) = a_{11}f_1 + a_{21}f_2 + \dots + a_{m1}f_m, \\ T(e_2) = a_{12}f_1 + a_{22}f_2 + \dots + a_{m2}f_m, \\ \vdots \\ T(e_n) = a_{1n}f_1 + a_{2n}f_2 + \dots + a_{mn}f_m. \end{cases}$$
Collecting the coefficients and taking the transpose gives
$$A = \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1n} \\ a_{21} & a_{22} & \dots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ a_{m1} & a_{m2} & \dots & a_{mn} \end{pmatrix}.$$
Equivalently, the entire system can be written compactly as
$$(T(e_1), \dots, T(e_n)) = (f_1, \dots, f_m)A.$$

**Definition 2.15 — Matrix of a linear map**
Let
$$T : V \to W$$
be linear, with
$$\mathcal{E} = (e_1, \dots, e_n)$$

<!-- page 37 -->

a basis of $V$ and
$$\mathcal{F} = (f_1, \dots, f_m)$$
a basis of $W$.
If
$$(T(e_1), \dots, T(e_n)) = (f_1, \dots, f_m)A,$$
then the $m \times n$ matrix $A$ is called the **matrix of $T$ with respect to the bases $\mathcal{E}$ and $\mathcal{F}$**.
We denote it by
$$[T]_{\mathcal{F} \leftarrow \mathcal{E}}$$
or simply by $[T]$ when the bases are clear from context.

The construction is worth remembering column by column:
$$j\text{-th column of } [T]_{\mathcal{F} \leftarrow \mathcal{E}} = [T(e_j)]_{\mathcal{F}}.$$

Thus the number of columns is determined by the dimension of the domain, while the number of rows is determined by the dimension of the codomain:
$$T: V^n \to W^m \implies [T]_{\mathcal{F} \leftarrow \mathcal{E}} \text{ is } m \times n.$$

**Example 2.16 — A map from $\mathbb{R}^2$ to $\mathbb{R}^3$**

Let
$$T: \mathbb{R}^2 \to \mathbb{R}^3$$
be defined by
$$T(x, y) = (x + 3y, 2x + 5y, 7x + 9y).$$
Take the standard bases
$$\mathcal{E} = (e_1, e_2)$$
of $\mathbb{R}^2$ and
$$\mathcal{F} = (f_1, f_2, f_3)$$
of $\mathbb{R}^3$.
We have
$$T(e_1) = T(1, 0) = (1, 2, 7) = f_1 + 2f_2 + 7f_3,$$
and
$$T(e_2) = T(0, 1) = (3, 5, 9) = 3f_1 + 5f_2 + 9f_3.$$

<!-- page 38 -->

Therefore,
$$(T(e_1), T(e_2)) = (f_1, f_2, f_3) \begin{pmatrix} 1 & 3 \\ 2 & 5 \\ 7 & 9 \end{pmatrix},$$
and hence
$$[T]_{\mathcal{F} \leftarrow \mathcal{E}} = \begin{pmatrix} 1 & 3 \\ 2 & 5 \\ 7 & 9 \end{pmatrix}.$$

So far the matrix records what $T$ does to the basis vectors. The important point is that, because $T$ is linear, the same matrix tells us what $T$ does to every vector.
Let
$$v = x_1 e_1 + \dots + x_n e_n,$$
and write
$$X = [v]_{\mathcal{E}} = \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix}.$$
Then
$$T(v) = x_1 T(e_1) + \dots + x_n T(e_n).$$
Using
$$(T(e_1), \dots, T(e_n)) = (f_1, \dots, f_m)A,$$
we obtain
$$T(v) = (T(e_1), \dots, T(e_n)) \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix}$$
$$= (f_1, \dots, f_m)A \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix}$$
$$= (f_1, \dots, f_m)[T]_{\mathcal{F} \leftarrow \mathcal{E}}[v]_{\mathcal{E}}.$$
Therefore the coordinate vector of $T(v)$ in the basis $\mathcal{F}$ is
$$[T(v)]_{\mathcal{F}} = [T]_{\mathcal{F} \leftarrow \mathcal{E}}[v]_{\mathcal{E}}.$$
We consolidate the above discussion into a proposition.

<!-- page 39 -->

**Proposition 2.17 — A linear map acts by matrix multiplication**

Let
$$T: V \to W$$
be linear, let $\mathcal{E}$ be a basis of $V$, and let $\mathcal{F}$ be a basis of $W$. Then, for every $v \in V$,
$$[T(v)]_{\mathcal{F}} = [T]_{\mathcal{F} \leftarrow \mathcal{E}}[v]_{\mathcal{E}}.$$

**Remark 2.18 — What the matrix represents**

The linear map $T$ and its matrix are not the same object.
The map
$$T: V \to W$$
is defined independently of any choice of basis. The matrix
$$[T]_{\mathcal{F} \leftarrow \mathcal{E}}$$
is a coordinate representation of $T$ after bases have been chosen for $V$ and $W$.
Thus,
$$\text{linear map} + \text{choice of bases} \implies \text{matrix.}$$
Changing the bases generally changes the matrix, but does not change the underlying linear map.

**2.5 Composition as Matrix Multiplication**

We now ask how the matrix representation behaves under composition.
Let
$$T: U \to V, \quad S: V \to W$$
be linear maps, and choose bases
$$\mathcal{E} = (e_1, \dots, e_n)$$
of $U$,
$$\mathcal{F} = (f_1, \dots, f_m)$$
of $V$, and
$$\mathcal{G} = (g_1, \dots, g_p)$$
of $W$.

<!-- page 40 -->

Suppose the matrices of $T$ and $S$ with respect to these bases are
$$A \in \mathbb{K}^{m \times n}, \quad B \in \mathbb{K}^{p \times m}.$$
By definition,
$$(T(e_1), \dots, T(e_n)) = (f_1, \dots, f_m)A,$$
and
$$(S(f_1), \dots, S(f_m)) = (g_1, \dots, g_p)B.$$
Now consider the composition
$$ST: U \to W.$$
Applying $S$ to the first relation gives
$$(ST(e_1), \dots, ST(e_n)) = S(T(e_1), \dots, T(e_n))$$
$$= S((f_1, \dots, f_m)A).$$
Because $S$ is linear, the coefficients in $A$ pass through $S$:
$$S((f_1, \dots, f_m)A) = (S(f_1), \dots, S(f_m))A.$$
Using
$$(S(f_1), \dots, S(f_m)) = (g_1, \dots, g_p)B,$$
we therefore obtain
$$(ST(e_1), \dots, ST(e_n)) = (S(f_1), \dots, S(f_m))A$$
$$= (g_1, \dots, g_p)BA.$$
Hence the matrix of the composition $ST$ is
$$[ST]_{\mathcal{G} \leftarrow \mathcal{E}} = [S]_{\mathcal{G} \leftarrow \mathcal{F}}[T]_{\mathcal{F} \leftarrow \mathcal{E}}.$$
In the shorter notation
$$[T] = A, \quad [S] = B,$$
this becomes
$$[ST] = BA.$$
Visually
$$U \xrightarrow{T} V \xrightarrow{S} W$$
$$U \xrightarrow{\quad \quad ST \quad \quad} W$$

<!-- page 41 -->

$$\mathbb{K}^n \xrightarrow{A} \mathbb{K}^m \xrightarrow{B} \mathbb{K}^p$$
$$\mathbb{K}^n \xrightarrow{\quad \quad BA \quad \quad} \mathbb{K}^p$$
What lives inside the product matrix? What do the elements of the product matrix look like?
Let
$$A = (a_{kj}) \in \mathbb{K}^{m \times n}, \quad B = (b_{ik}) \in \mathbb{K}^{p \times m}.$$
The $j$-th column of $A$ gives the coordinates of $T(e_j)$ in the basis $\mathcal{F}$. Thus
$$T(e_j) = \sum_{k=1}^m a_{kj}f_k.$$
Applying $S$,
$$ST(e_j) = S\left(\sum_{k=1}^m a_{kj}f_k\right) = \sum_{k=1}^m a_{kj}S(f_k).$$
But the $k$-th column of $B$ gives the coordinates of $S(f_k)$ in the basis $\mathcal{G}$, so
$$S(f_k) = \sum_{i=1}^p b_{ik}g_i.$$
Therefore,
$$ST(e_j) = \sum_{k=1}^m a_{kj} \left(\sum_{i=1}^p b_{ik}g_i\right)$$
$$= \sum_{i=1}^p \left(\sum_{k=1}^m b_{ik}a_{kj}\right)g_i.$$
Hence the coefficient of $g_i$ in $ST(e_j)$ is
$$\sum_{k=1}^m b_{ik}a_{kj}.$$
Thus, if
$$C = [ST] = BA,$$
then
$$c_{ij} = \sum_{k=1}^m b_{ik}a_{kj}.$$
This motivates the definition of matrix multiplication.
If
$$B \in \mathbb{K}^{p \times m}, \quad A \in \mathbb{K}^{m \times n},$$

<!-- page 42 -->

then their product
$$BA \in \mathbb{K}^{p \times n}$$
is defined by
$$(BA)_{ij} = \sum_{k=1}^m b_{ik}a_{kj}.$$
Thus the $(i, j)$-entry of $BA$ is obtained by multiplying the $i$-th row of $B$ by the $j$-th column of $A$:
$$(BA)_{ij} = \begin{pmatrix} b_{i1} & \dots & b_{im} \end{pmatrix} \begin{pmatrix} a_{1j} \\ \vdots \\ a_{mj} \end{pmatrix}.$$
The dimensions also explain why the matrices can be multiplied:
$$U \xrightarrow{T} V \xrightarrow{S} W$$
with
$$\dim U = n, \quad \dim V = m, \quad \dim W = p$$
corresponds to
$$\mathbb{K}^n \xrightarrow{A} \mathbb{K}^m \xrightarrow{B} \mathbb{K}^p,$$
where
$$A: m \times n, \quad B: p \times m.$$
The two occurrences of $m$ correspond to the intermediate space $V$. They are exactly the two dimensions that must match in order for the product
$$BA$$
to be defined.

**2.6 Four Ways to Understand Matrix Multiplication**

Let
$$A \in \mathbb{K}^{m \times n}, \quad B \in \mathbb{K}^{n \times p},$$
and write
$$C = AB \in \mathbb{K}^{m \times p}.$$
There are several equivalent ways to understand the product $AB$. Each viewpoint emphasizes a different part of the structure of matrix multiplication.

<!-- page 43 -->

**1. Row by column, element-wise**
The most familiar interpretation computes the entries of $C$ one at a time.
Write
$$A = \begin{pmatrix} a_{11} & \dots & a_{1n} \\ \vdots & & \vdots \\ a_{m1} & \dots & a_{mn} \end{pmatrix}, \quad B = \begin{pmatrix} b_{11} & \dots & b_{1p} \\ \vdots & & \vdots \\ b_{n1} & \dots & b_{np} \end{pmatrix}.$$
Then the $(i, j)$-entry of $C = AB$ is
$$c_{ij} = \sum_{k=1}^n a_{ik}b_{kj}.$$
Equivalently,
$$c_{ij} = \begin{pmatrix} a_{i1} & a_{i2} & \dots & a_{in} \end{pmatrix} \begin{pmatrix} b_{1j} \\ b_{2j} \\ \vdots \\ b_{nj} \end{pmatrix}.$$
Thus,
$$(i, j)\text{-entry of } AB = i\text{-th row of } A \times j\text{-th column of } B.$$
This viewpoint is useful when we want to compute a particular entry of a matrix product.

**2. Matrix by columns**
Instead of computing $AB$ entry by entry, we may compute it one column at a time.
Write the columns of $B$ as
$$B = \begin{pmatrix} | & | & & | \\ b_1 & b_2 & \dots & b_p \\ | & | & & | \end{pmatrix}, \quad b_j \in \mathbb{K}^n.$$
Then
$$AB = \begin{pmatrix} | & | & & | \\ Ab_1 & Ab_2 & \dots & Ab_p \\ | & | & & | \end{pmatrix}.$$
In other words,
$$j\text{-th column of } AB = A(j\text{-th column of } B).$$
Thus multiplying $B$ on the left by $A$ means that $A$ acts separately on every column of $B$.
This is precisely the viewpoint that arises naturally when matrices are viewed as representations of linear maps.

<!-- page 44 -->

**3. Rows by matrix**
There is a completely analogous row-wise interpretation.
Write the rows of $A$ as
$$A = \begin{pmatrix} - & r_1 & - \\ - & r_2 & - \\ & \vdots & \\ - & r_m & - \end{pmatrix}, \quad r_i \in \mathbb{K}^{1 \times n}.$$
Then
$$AB = \begin{pmatrix} - & r_1B & - \\ - & r_2B & - \\ & \vdots & \\ - & r_mB & - \end{pmatrix}.$$
Hence
$$i\text{-th row of } AB = (i\text{-th row of } A)B.$$
Thus multiplying $A$ on the right by $B$ means that each row of $A$ is multiplied by $B$.

**4. Column by row, then add**
Finally, matrix multiplication can be viewed as a sum of column-by-row products.
Write $A$ in terms of its columns,
$$A = \begin{pmatrix} | & | & & | \\ a_1 & a_2 & \dots & a_n \\ | & | & & | \end{pmatrix}, \quad a_k \in \mathbb{K}^m,$$
and write $B$ in terms of its rows,
$$B = \begin{pmatrix} - & s_1 & - \\ - & s_2 & - \\ & \vdots & \\ - & s_n & - \end{pmatrix}, \quad s_k \in \mathbb{K}^{1 \times p}.$$
Then
$$AB = a_1s_1 + a_2s_2 + \dots + a_ns_n = \sum_{k=1}^n a_ks_k.$$
Each product
$$a_ks_k$$
is an $m \times p$ matrix: it is obtained by multiplying one column of $A$ by the corresponding row of $B$.

<!-- page 45 -->

Indeed,
$$a_ks_k = \begin{pmatrix} a_{1k} \\ a_{2k} \\ \vdots \\ a_{mk} \end{pmatrix} \begin{pmatrix} b_{k1} & b_{k2} & \dots & b_{kp} \end{pmatrix} = \begin{pmatrix} a_{1k}b_{k1} & \dots & a_{1k}b_{kp} \\ a_{2k}b_{k1} & \dots & a_{2k}b_{kp} \\ \vdots & & \vdots \\ a_{mk}b_{k1} & \dots & a_{mk}b_{kp} \end{pmatrix}.$$
Adding these $n$ matrices gives
$$AB = \sum_{k=1}^n \begin{pmatrix} a_{1k}b_{k1} & \dots & a_{1k}b_{kp} \\ \vdots & & \vdots \\ a_{mk}b_{k1} & \dots & a_{mk}b_{kp} \end{pmatrix}.$$
The $(i, j)$-entry of this sum is therefore
$$\sum_{k=1}^n a_{ik}b_{kj},$$
which is exactly the usual row-by-column formula.
These four viewpoints describe exactly the same matrix product. Which viewpoint is most useful depends on the question being asked. You will likely come back to this when you study the algebra of OLS in Econometrics I.

**2.7 Inverse Maps and Inverse Matrices**

We have seen that composition of linear maps corresponds to multiplication of their matrices. This immediately raises a natural question: when can the effect of a linear transformation be undone?
Let
$$T: V \to V$$
be a linear transformation. We seek another linear transformation that reverses the action of $T$.

**Definition 2.19 — Invertible linear transformation**

A linear transformation
$$T: V \to V$$
is called **invertible** if there exists a linear transformation
$$S: V \to V$$
such that
$$ST = I_V \quad \text{and} \quad TS = I_V,$$
where $I_V$ denotes the identity transformation on $V$.

<!-- page 46 -->

If such an $S$ exists, it is called the **inverse** of $T$ and is denoted by
$$T^{-1}.$$
Thus,
$$T^{-1}T = I_V, \quad TT^{-1} = I_V.$$
The meaning is simple. If
$$v \xrightarrow{T} T(v),$$
then applying $T^{-1}$ brings us back to the original vector:
$$v \xrightarrow{T} T(v) \xrightarrow{T^{-1}} v.$$
Similarly,
$$v \xrightarrow{T^{-1}} T^{-1}(v) \xrightarrow{T} v.$$

**Proposition 2.20 — The inverse is unique**

If a linear transformation
$$T: V \to V$$
is invertible, then its inverse is unique.

**Proof**
Suppose that both $S_1$ and $S_2$ are inverses of $T$. Then
$$S_1T = I_V, \quad TS_2 = I_V.$$
Using associativity of composition,
$$S_1 = S_1I_V$$
$$= S_1(TS_2)$$
$$= (S_1T)S_2$$
$$= I_VS_2$$
$$= S_2.$$
Therefore the inverse of $T$ is unique.

Hence it is unambiguous to write the inverse of $T$ as
$$T^{-1}.$$

<!-- page 47 -->

Now comes the matrix counterpart of the inverse map.

**Definition 2.21 — Invertible matrix**

A square matrix
$$A \in \mathbb{K}^{n \times n}$$
is called **invertible** if there exists a matrix
$$B \in \mathbb{K}^{n \times n}$$
such that
$$AB = I_n \quad \text{and} \quad BA = I_n,$$
where $I_n$ is the $n \times n$ identity matrix.
If such a matrix $B$ exists, it is called the **inverse** of $A$ and is denoted by
$$A^{-1}.$$
Thus,
$$AA^{-1} = I_n, \quad A^{-1}A = I_n.$$

**Proposition 2.22 — The matrix of an inverse transformation**

Let $T: V \to V$ be an invertible linear transformation, and let $\mathcal{E}$ be a basis of the finite-dimensional vector space $V$.
If
$$A = [T]_{\mathcal{E}},$$
then $A$ is invertible and
$$[T^{-1}]_{\mathcal{E}} = A^{-1}.$$
Equivalently,
$$[T^{-1}]_{\mathcal{E}} = ([T]_{\mathcal{E}})^{-1}.$$

**Proof**
Since
$$T^{-1}T = I_V \quad \text{and} \quad TT^{-1} = I_V,$$
composition as matrix multiplication gives
$$[T^{-1}]_{\mathcal{E}}[T]_{\mathcal{E}} = [I_V]_{\mathcal{E}} = I_n,$$

<!-- page 48 -->

and
$$[T]_{\mathcal{E}}[T^{-1}]_{\mathcal{E}} = [I_V]_{\mathcal{E}} = I_n.$$
Therefore $[T^{-1}]_{\mathcal{E}}$ is the inverse of $[T]_{\mathcal{E}}$. Hence
$$[T^{-1}]_{\mathcal{E}} = ([T]_{\mathcal{E}})^{-1}.$$

**Remark 2.23 — Inverse maps and inverse matrices**

The inverse matrix is the coordinate representation of the inverse linear transformation.
If
$$T \longleftrightarrow A,$$
then
$$T^{-1} \longleftrightarrow A^{-1}.$$
Thus matrix inversion is not a separate operation introduced merely for computation. It arises naturally from reversing an invertible linear transformation.

We have talked about composition of linear maps, what about their inverses if such exist?

**Proposition 2.24 — Inverse of a composition**

Let
$$S, T: V \to V$$
be invertible linear transformations. Then $ST$ is invertible and
$$(ST)^{-1} = T^{-1}S^{-1}.$$

**Proof**
We verify that $T^{-1}S^{-1}$ is an inverse of $ST$.
Using associativity of composition,
$$(T^{-1}S^{-1})(ST) = T^{-1}(S^{-1}S)T$$
$$= T^{-1}I_VT$$
$$= T^{-1}T$$
$$= I_V.$$

<!-- page 49 -->

Similarly,
$$
\begin{aligned}
(ST)(T^{-1}S^{-1}) &= S(TT^{-1})S^{-1} \\
&= SI_VS^{-1} \\
&= SS^{-1} \\
&= I_V.
\end{aligned}
$$
Therefore,
$$
(ST)^{-1} = T^{-1}S^{-1}.
$$
Translating this into the matrix world, we have the following

**Corollary 2.25 — Inverse of a matrix product**

If $A$ and $B$ are invertible $n \times n$ matrices, then $BA$ is invertible and
$$
(BA)^{-1} = A^{-1}B^{-1}.
$$

**Proof**

Choose invertible linear transformations $T$ and $S$ represented by $A$ and $B$, respectively. Since
$$
[ST] = BA
$$
and
$$
(ST)^{-1} = T^{-1}S^{-1},
$$
we obtain
$$
(BA)^{-1} = A^{-1}B^{-1}.
$$

**Remark 2.26 — Why the order reverses**

The reversal of order in
$$
(ST)^{-1} = T^{-1}S^{-1}
$$
is natural.
The transformation $ST$ first applies $T$ and then applies $S$:
$$
v \longmapsto T(v) \longmapsto S(T(v)).
$$
To return to $v$, we must undo these operations in the reverse order: first apply $S^{-1}$ and then apply $T^{-1}$.

<!-- page 50 -->

## 2.8 Matrix Transpose

We now introduce another basic operation on matrices. Unlike the inverse, which exists only for certain square matrices, the transpose is defined for every matrix.

**Definition 2.27 — Transpose of a matrix**

Let
$$
A = (a_{ij}) \in \mathbb{K}^{m \times n}.
$$
The **transpose** of $A$, denoted by
$$
A^\top,
$$
is the $n \times m$ matrix obtained by interchanging the rows and columns of $A$.
Equivalently,
$$
(A^\top)_{ij} = a_{ji}.
$$

Thus the rows of $A$ become the columns of $A^\top$, and the columns of $A$ become the rows of $A^\top$.

**Example 2.28 — Transpose of a matrix**

If
$$
A = \begin{pmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \end{pmatrix},
$$
then
$$
A^\top = \begin{pmatrix} 1 & 4 \\ 2 & 5 \\ 3 & 6 \end{pmatrix}.
$$
Notice that $A$ is a $2 \times 3$ matrix, whereas $A^\top$ is a $3 \times 2$ matrix.

Here are some basic properties of the matrix transpose.

**Proposition 2.29 — Properties of the transpose**

Let $A$ and $B$ be matrices of compatible dimensions and let $\lambda \in \mathbb{K}$. Then
$$
\begin{aligned}
(A^\top)^\top &= A, \\
(A + B)^\top &= A^\top + B^\top, \\
(\lambda A)^\top &= \lambda A^\top,
\end{aligned}
$$
and
$$
(AB)^\top = B^\top A^\top.
$$

<!-- page 51 -->

**Proof**

The first three identities follow directly from the definition of the transpose. We verify the product identity.
Suppose
$$
A \in \mathbb{K}^{m \times n}, \quad B \in \mathbb{K}^{n \times p}.
$$
For every $i$ and $j$,
$$
\begin{aligned}
((AB)^\top)_{ij} &= (AB)_{ji} \\
&= \sum_{k=1}^n a_{jk}b_{ki} \\
&= \sum_{k=1}^n (B^\top)_{ik}(A^\top)_{kj} \\
&= (B^\top A^\top)_{ij}.
\end{aligned}
$$
Hence
$$
(AB)^\top = B^\top A^\top.
$$

**Remark 2.30 — The order reverses under transposition**

The identity
$$
(AB)^\top = B^\top A^\top
$$
resembles the inverse-of-a-product formula
$$
(AB)^{-1} = B^{-1}A^{-1}.
$$
In both cases, applying the operation to a product reverses the order of the factors.

**Proposition 2.31 — Transpose and inverse identities**

Let $A$ and $B$ be square matrices of the same size. Whenever the corresponding inverses exist, the following identities hold:
$$
\begin{aligned}
(A^\top)^\top &= A, \\
(AB)^\top &= B^\top A^\top, \\
(AB)^{-1} &= B^{-1}A^{-1},
\end{aligned}
$$
and
$$
(A^\top)^{-1} = (A^{-1})^\top.
$$
In particular, $A$ is invertible if and only if $A^\top$ is invertible.

<!-- page 52 -->

**Proof**

The first identity follows immediately from the definition of the transpose, and the second was established above.
For the inverse of a product, observe that
$$
(B^{-1}A^{-1})(AB) = B^{-1}(A^{-1}A)B = B^{-1}B = I,
$$
and similarly,
$$
(AB)(B^{-1}A^{-1}) = A(BB^{-1})A^{-1} = AA^{-1} = I.
$$
Hence
$$
(AB)^{-1} = B^{-1}A^{-1}.
$$
Now suppose $A$ is invertible. Since
$$
AA^{-1} = I,
$$
taking transposes gives
$$
(AA^{-1})^\top = I^\top.
$$
Using the transpose-of-a-product rule,
$$
(A^{-1})^\top A^\top = I.
$$
Similarly, transposing
$$
A^{-1}A = I
$$
gives
$$
A^\top (A^{-1})^\top = I.
$$
Thus $(A^{-1})^\top$ is the inverse of $A^\top$, and therefore
$$
(A^\top)^{-1} = (A^{-1})^\top.
$$
Hence $A$ invertible implies $A^\top$ invertible. Applying the same argument to $A^\top$, together with
$$
(A^\top)^\top = A,
$$
gives the converse.

<!-- page 53 -->

## 2.9 Symmetric and Skew-Symmetric Matrices

Transpose allows us to distinguish two important classes of square matrices: those that remain unchanged under transposition, and those that change sign.

**Definition 2.32 — Symmetric and skew-symmetric matrices**

Let
$$
A \in \mathbb{K}^{n \times n}.
$$
The matrix $A$ is called **symmetric** if
$$
A^\top = A.
$$
The matrix $A$ is called **skew-symmetric** (or **antisymmetric**) if
$$
A^\top = -A.
$$

In terms of entries, $A$ is symmetric if
$$
a_{ij} = a_{ji}
$$
for every $i, j$, whereas $A$ is skew-symmetric if
$$
a_{ij} = -a_{ji}.
$$

Thus a symmetric matrix is reflected unchanged across the main diagonal, while a skew-symmetric matrix is reflected across the main diagonal and changes sign.

**Example 2.33 — Symmetric and skew-symmetric matrices**

A typical symmetric $3 \times 3$ matrix has the form
$$
\begin{pmatrix} a & b & c \\ b & d & e \\ c & e & f \end{pmatrix}.
$$
A typical skew-symmetric $3 \times 3$ matrix has the form
$$
\begin{pmatrix} 0 & a & b \\ -a & 0 & c \\ -b & -c & 0 \end{pmatrix}.
$$
Why are the diagonals zero for skew-symmetric matrices?

<!-- page 54 -->

**Proposition 2.34 — Diagonal entries of a skew-symmetric matrix**

If $A$ is skew-symmetric, then every diagonal entry of $A$ is zero.

**Proof**

If $A$ is skew-symmetric, then
$$
a_{ii} = -a_{ii}
$$
for every $i$. Hence
$$
2a_{ii} = 0.
$$
therefore
$$
a_{ii} = 0.
$$

**Proposition 2.35 — Symmetric-skew-symmetric decomposition**

Every square matrix
$$
A \in \mathbb{K}^{n \times n}
$$
can be written uniquely as
$$
A = S + K,
$$
where $S$ is symmetric and $K$ is skew-symmetric.
More precisely,
$$
S = \frac{A + A^\top}{2}, \quad K = \frac{A - A^\top}{2}.
$$

**Proof**

We first show that such a decomposition exists. Define
$$
S = \frac{A + A^\top}{2}, \quad K = \frac{A - A^\top}{2}.
$$
Then
$$
\begin{aligned}
S^\top &= \left( \frac{A + A^\top}{2} \right)^\top \\
&= \frac{A^\top + (A^\top)^\top}{2} \\
&= \frac{A^\top + A}{2} \\
&= S,
\end{aligned}
$$
so $S$ is symmetric.

<!-- page 55 -->

Similarly,
$$
\begin{aligned}
K^\top &= \left( \frac{A - A^\top}{2} \right)^\top \\
&= \frac{A^\top - A}{2} \\
&= -\frac{A - A^\top}{2} \\
&= -K,
\end{aligned}
$$
so $K$ is skew-symmetric.
Moreover,
$$
S + K = \frac{A + A^\top}{2} + \frac{A - A^\top}{2} = A.
$$
Thus the decomposition exists.
To prove uniqueness, suppose also that
$$
A = S_1 + K_1,
$$
where $S_1$ is symmetric and $K_1$ is skew-symmetric. Taking transposes,
$$
A^\top = S_1^\top + K_1^\top = S_1 - K_1.
$$
Adding the two equations gives
$$
A + A^\top = 2S_1,
$$
so
$$
S_1 = \frac{A + A^\top}{2} = S.
$$
Subtracting them gives
$$
A - A^\top = 2K_1,
$$
so
$$
K_1 = \frac{A - A^\top}{2} = K.
$$
Hence the decomposition is unique.

**Remark 2.36 — A note on the scalar field**

The decomposition
$$
A = \frac{A + A^\top}{2} + \frac{A - A^\top}{2}
$$
requires that the scalar 2 be invertible in the underlying field $\mathbb{K}$.
Thus, technically, the result does not hold over an arbitrary field: it can fail in fields of

<!-- page 56 -->

characteristic 2. (If you don't know what characteristic is, don't worry. This is almost never used in economics. But if you do know an application of this concept somewhere in economics, do let me know since I am curious.)
For our purposes, however, we work primarily over
$$
\mathbb{R} \quad \text{or} \quad \mathbb{C},
$$
where $2 \neq 0$ and division by 2 is always valid. Hence the decomposition above applies throughout our discussion.

## 3 Rank of a Linear Map and a Matrix

The rank of a linear map measures how many independent directions remain after the map is applied. To understand this precisely, we first study two subspaces naturally associated with every linear map: its *kernel*, which records the directions that are collapsed to zero, and its *image*, which records the directions that can actually be reached.

### 3.1 Kernel and Image

Let
$$
T : V \to W
$$
be a linear map. There are two natural questions we can ask:
* Which vectors in $V$ are sent to zero?
* Which vectors in $W$ can actually be obtained as outputs of $T$?

The answers give the kernel and the image of $T$.

**Definition 3.1 — Kernel and image**

Let
$$
T : V \to W
$$
be a linear map.
The **kernel** of $T$ is
$$
\ker T = \{v \in V : T(v) = 0_W\}.
$$
The **image** of $T$ is
$$
\text{Im} T = \{T(v) : v \in V\}.
$$

<!-- page 57 -->

Equivalently,
$$
\text{Im} T = \{w \in W : w = T(v) \text{ for some } v \in V\}.
$$
Thus,
$$
\ker T \subseteq V, \quad \text{Im} T \subseteq W.
$$
The kernel is therefore a subset of the *domain*, whereas the image is a subset of the *codomain*.
These two sets are vector subspaces.

**Proposition 3.2 — Kernel and image are subspaces**

Let
$$
T : V \to W
$$
be a linear map. Then
$$
\ker T \leq V \quad \text{and} \quad \text{Im} T \leq W.
$$

**Proof**

We first consider the kernel.
Because $T$ is linear,
$$
T(0_V) = 0_W,
$$
so
$$
0_V \in \ker T.
$$
Now let $u, v \in \ker T$ and let $\lambda, \mu \in \mathbb{K}$. Then
$$
T(u) = T(v) = 0_W,
$$
and hence
$$
\begin{aligned}
T(\lambda u + \mu v) &= \lambda T(u) + \mu T(v) \\
&= \lambda 0_W + \mu 0_W \\
&= 0_W.
\end{aligned}
$$
Thus
$$
\lambda u + \mu v \in \ker T.
$$
By the subspace test,
$$
\ker T \leq V.
$$
Now consider the image. Since
$$
T(0_V) = 0_W,
$$

<!-- page 58 -->

we have
$$
0_W \in \text{Im} T.
$$
Let $w_1, w_2 \in \text{Im} T$. Then there exist $v_1, v_2 \in V$ such that
$$
w_1 = T(v_1), \quad w_2 = T(v_2).
$$
For any $\lambda, \mu \in \mathbb{K}$,
$$
\begin{aligned}
\lambda w_1 + \mu w_2 &= \lambda T(v_1) + \mu T(v_2) \\
&= T(\lambda v_1 + \mu v_2).
\end{aligned}
$$
Therefore
$$
\lambda w_1 + \mu w_2 \in \text{Im} T.
$$
Again by the subspace test,
$$
\text{Im} T \leq W.
$$
See the following remark for an interpretation of these two subspaces.

**Remark 3.3 — What the kernel and image measure**

The kernel measures what the linear map *loses*:
$$
v \in \ker T \iff T(v) = 0_W.
$$
Thus vectors in the kernel are directions that are completely collapsed by $T$.
The image measures what the linear map can *produce*:
$$
w \in \text{Im} T \iff w = T(v) \text{ for some } v \in V.
$$
Thus $\text{Im} T$ is the set of all attainable outputs of $T$.

To see the use of these two subspaces, let's see the following characterization of injectivity and surjectivity of linear maps.

**Proposition 3.4 — Injectivity and the kernel**

Let
$$
T : V \to W
$$
be a linear map. Then
$$
T \text{ is injective} \iff \ker T = \{0_V\}.
$$

<!-- page 59 -->

**Proof**

Suppose first that $T$ is injective. If
$$
v \in \ker T,
$$
then
$$
T(v) = 0_W = T(0_V).
$$
Since $T$ is injective,
$$
v = 0_V.
$$
Therefore
$$
\ker T = \{0_V\}.
$$
Conversely, suppose
$$
\ker T = \{0_V\}.
$$
If
$$
T(u) = T(v),
$$
then by linearity,
$$
T(u - v) = T(u) - T(v) = 0_W.
$$
Hence
$$
u - v \in \ker T.
$$
Because $\ker T = \{0_V\}$,
$$
u - v = 0_V,
$$
and therefore
$$
u = v.
$$
Thus $T$ is injective.

**Proposition 3.5 — Surjectivity and the image**

Let
$$
T : V \to W
$$
be a linear map. Then
$$
T \text{ is surjective} \iff \text{Im} T = W.
$$
This is simply the definition of surjectivity: every vector in the codomain must be attained as an output of $T$.
One thing to note is that surjectivity depends on the choice of the codomain.

<!-- page 60 -->

**Remark 3.6 — The image and the codomain are not the same thing**

For a linear map
$$
T : V \to W,
$$
we always have
$$
\text{Im} T \subseteq W,
$$
but equality need not hold.
The codomain $W$ is part of the specification of the map, whereas $\text{Im} T$ consists only of those vectors in $W$ that are actually reached.
Thus
$$
T \text{ is surjective} \iff \text{Im} T = W.
$$
Let's see an example.

**Example 3.7 — Kernel and image of a linear map**

Let
$$
T : \mathbb{R}^3 \to \mathbb{R}^2
$$
be defined by
$$
T(x, y, z) = (x + y, y + z).
$$
To find the kernel, solve
$$
T(x, y, z) = (0, 0).
$$
Thus
$$
x + y = 0, \quad y + z = 0,
$$
so
$$
x = -y, \quad z = -y.
$$
Writing $y = t$ gives
$$
(x, y, z) = t(-1, 1, -1).
$$
Hence
$$
\ker T = \text{Span}\{(-1, 1, -1)\}.
$$
For the image, observe that
$$
\begin{aligned}
T(x, y, z) &= (x + y, y + z) \\
&= x(1, 0) + y(1, 1) + z(0, 1).
\end{aligned}
$$
Therefore
$$
\text{Im} T = \text{Span}\{(1, 0), (1, 1), (0, 1)\}.
$$

<!-- page 61 -->

Since
$$(1,0) \quad \text{and} \quad (0,1)$$
already form a basis of $\mathbb{R}^2$,
$$\text{Im}\, T = \mathbb{R}^2.$$
Thus this map has a one-dimensional kernel and a two-dimensional image.

How "big" are these two subspaces? Recall that we have discussed the dimension of a subspace, which leads to the following definitions.

### Definition 3.8 — Rank and nullity of a linear map
Let
$$T : V \to W$$
be a linear map, with $V$ finite-dimensional.
The **nullity** of $T$ is the dimension of its kernel:
$$\text{nullity}(T) = \dim \ker T.$$
The **rank** of $T$ is the dimension of its image:
$$\text{Rank}(T) = \dim \text{Im}\, T.$$

### Remark 3.9 — Rank and nullity as dimensions
The nullity and rank measure two different aspects of the action of $T$:
$$\text{nullity}(T) = \dim \ker T$$
measures the number of independent directions that are collapsed to zero, whereas
$$\text{Rank}(T) = \dim \text{Im}\, T$$
measures the number of independent directions that remain visible in the output.
The rank–nullity theorem will show that these two quantities account for the entire dimension of the domain.

<!-- page 62 -->

## 3.2 The Rank-Nullity Theorem
How are the rank and nullity of a linear map related? To study this, we need a proposition as a tool.

### Proposition 3.10 — Basis extension
Let $V$ be a finite-dimensional vector space. Every linearly independent list
$$v_1, \dots, v_k$$
in $V$ can be extended to a basis of $V$.

### Proof
Let
$$v_1, \dots, v_k$$
be linearly independent in $V$.
If these vectors already span $V$, then they form a basis and there is nothing to prove.
Otherwise, choose
$$v_{k+1} \notin \text{Span}(v_1, \dots, v_k).$$
Then
$$v_1, \dots, v_k, v_{k+1}$$
is linearly independent.
If these vectors still do not span $V$, choose another vector outside their span and repeat the argument.
Because $V$ is finite-dimensional, this process must terminate after finitely many steps. The resulting linearly independent list spans $V$ and therefore forms a basis of $V$.

Now we are ready to dive into the main result of this subsection and in my opinion, a fundamental theorem in linear algebra.

### Theorem 3.11 — Rank-nullity theorem
Let
$$T : V \to W$$
be a linear map, where $V$ is finite-dimensional. Then $\text{Im}\, T$ is finite-dimensional and
$$\dim V = \dim \ker T + \dim \text{Im}\, T.$$

<!-- page 63 -->

Equivalently,
$$\dim V = \text{nullity}(T) + \text{Rank}(T).$$

### Proof
Let
$$u_1, \dots, u_k$$
be a basis of $\ker T$. Thus
$$\dim \ker T = k.$$
By the basis extension theorem, extend this list to a basis of $V$:
$$u_1, \dots, u_k, v_1, \dots, v_r.$$
Hence
$$\dim V = k + r.$$
We will show that
$$T(v_1), \dots, T(v_r)$$
is a basis of $\text{Im}\, T$.
First, we show that these vectors span $\text{Im}\, T$.
Take any
$$w \in \text{Im}\, T.$$
By definition of the image, there exists $v \in V$ such that
$$w = T(v).$$
Because
$$u_1, \dots, u_k, v_1, \dots, v_r$$
is a basis of $V$, we can write
$$v = a_1 u_1 + \dots + a_k u_k + b_1 v_1 + \dots + b_r v_r.$$
Applying $T$ gives
$$w = T(v)$$
$$= a_1 T(u_1) + \dots + a_k T(u_k) + b_1 T(v_1) + \dots + b_r T(v_r).$$
Since
$$u_1, \dots, u_k \in \ker T,$$

<!-- page 64 -->

we have
$$T(u_1) = \dots = T(u_k) = 0.$$
Therefore
$$w = b_1 T(v_1) + \dots + b_r T(v_r).$$
Thus
$$T(v_1), \dots, T(v_r)$$
spans $\text{Im}\, T$.
Next, we show that these vectors are linearly independent.
Suppose
$$c_1 T(v_1) + \dots + c_r T(v_r) = 0.$$
By linearity,
$$T(c_1 v_1 + \dots + c_r v_r) = 0.$$
Hence
$$c_1 v_1 + \dots + c_r v_r \in \ker T.$$
Because
$$u_1, \dots, u_k$$
is a basis of $\ker T$, there exist scalars $d_1, \dots, d_k$ such that
$$c_1 v_1 + \dots + c_r v_r = d_1 u_1 + \dots + d_k u_k.$$
Therefore
$$d_1 u_1 + \dots + d_k u_k - c_1 v_1 - \dots - c_r v_r = 0.$$
But
$$u_1, \dots, u_k, v_1, \dots, v_r$$
is a basis of $V$, and hence is linearly independent. Therefore
$$c_1 = \dots = c_r = 0.$$
Thus
$$T(v_1), \dots, T(v_r)$$
is linearly independent.
Consequently,
$$T(v_1), \dots, T(v_r)$$
is a basis of $\text{Im}\, T$. In particular, $\text{Im}\, T$ is finite-dimensional and
$$\dim \text{Im}\, T = r.$$

<!-- page 65 -->

Therefore,
$$\dim V = k + r = \dim \ker T + \dim \text{Im}\, T.$$

## 3.3 Applications of the Rank-Nullity Theorem
The rank-nullity theorem is especially useful when a problem can be expressed in terms of a linear map
$$T : V \to W.$$
Instead of solving the problem directly, we can often study the simpler homogeneous problem
$$T(v) = 0.$$
When the domain and codomain have the same finite dimension, this is particularly powerful: showing that the zero vector is the only vector mapped to zero is enough to obtain both existence and uniqueness.

### Proposition 3.12 — Zero-kernel criterion for bijectivity
Let
$$T : V \to W$$
be a linear map between finite-dimensional vector spaces satisfying
$$\dim V = \dim W.$$
Then the following statements are equivalent:
$$\ker T = \{0\},$$
$$T \text{ is injective},$$
$$T \text{ is surjective},$$
and
$$T \text{ is bijective}.$$

### Proof
We already know that
$$T \text{ is injective} \iff \ker T = \{0\}.$$
Suppose now that
$$\ker T = \{0\}.$$

<!-- page 66 -->

By the rank-nullity theorem,
$$\dim V = \dim \ker T + \dim \text{Im}\, T = \dim \text{Im}\, T.$$
Since
$$\dim V = \dim W,$$
we obtain
$$\dim \text{Im}\, T = \dim W.$$
But $\text{Im}\, T$ is a subspace of $W$, so
$$\text{Im}\, T = W.$$
Thus $T$ is surjective. Hence $T$ is both injective and surjective, and therefore bijective.
Conversely, if $T$ is bijective, then in particular it is injective, so
$$\ker T = \{0\}.$$

### Remark 3.13 — The homogeneous-problem principle
Suppose
$$\dim V = r$$
and a problem with $r$ pieces of data can be represented by a linear map
$$\Phi : V \to \mathbb{K}^r.$$
Because the domain and codomain have the same dimension, to prove that every possible data vector has a unique solution, it is enough to prove
$$\ker \Phi = \{0\}.$$
In other words,
$$\text{zero data have only the zero solution}$$
implies
$$\text{arbitrary data have a unique solution.}$$
This simple principle is the key to many interpolation problems.

**Application 1: Linear systems**
Consider a matrix
$$A \in \mathbb{K}^{m \times n}$$

<!-- page 67 -->

and the associated linear map
$$T_A : \mathbb{K}^n \to \mathbb{K}^m, \quad T_A(x) = Ax.$$
The system of linear equations
$$Ax = b$$
is therefore the equation
$$T_A(x) = b.$$
The kernel of $T_A$ consists precisely of the solutions of the corresponding homogeneous system
$$Ax = 0.$$

### Proposition 3.14 — Solutions of a linear system
Suppose
$$Ax = b$$
has a particular solution $x_p$. Then $x$ solves $Ax = b$ if and only if
$$x = x_p + z$$
for some
$$z \in \ker T_A.$$

### Proof
Suppose first that $x$ is another solution. Then
$$Ax = Ax_p = b,$$
and therefore
$$A(x - x_p) = 0.$$
Thus
$$x - x_p \in \ker T_A.$$
Writing
$$z = x - x_p$$
gives
$$x = x_p + z.$$

<!-- page 68 -->

Conversely, if
$$x = x_p + z \quad \text{with} \quad z \in \ker T_A,$$
then
$$Ax = A(x_p + z) = Ax_p + Az = b + 0 = b.$$
Hence $x$ is a solution.

If the system is consistent, that is, there exists a solution to the linear system, the freedom in its solutions is exactly the freedom contained in the kernel.
By rank-nullity,
$$n = \dim \ker T_A + \text{Rank}(T_A),$$
and therefore
$$\dim \ker T_A = n - \text{Rank}(T_A).$$
Thus the nullity measures the number of independent degrees of freedom remaining in a consistent linear system.

### Corollary 3.15 — Variables, equations, and solutions
Let
$$A \in \mathbb{K}^{m \times n}.$$
(i) If $n > m$, then the homogeneous system
$$Ax = 0$$
has a nonzero solution.
(ii) If $m > n$, then there exist vectors
$$b \in \mathbb{K}^m$$
for which
$$Ax = b$$
has no solution.
(iii) If $m = n$, then
$$Ax = b$$
has a unique solution for every $b \in \mathbb{K}^n$ if and only if
$$Ax = 0$$
has only the zero solution.

<!-- page 69 -->

### Proof
If $n > m$, then
$$\dim \text{Im}\, T_A \leq m < n.$$
Rank-nullity therefore implies
$$\dim \ker T_A = n - \dim \text{Im}\, T_A > 0.$$
Hence the kernel contains a nonzero vector.
If $m > n$, then
$$\dim \text{Im}\, T_A \leq n < m,$$
so
$$\text{Im}\, T_A \neq \mathbb{K}^m.$$
Thus there exist right-hand sides $b$ that are not in the image of $T_A$, and for such $b$ the system $Ax = b$ has no solution.
Finally, if $m = n$, then $T_A$ maps between vector spaces of the same finite dimension. The result therefore follows from proposition 3.12.

**Polynomial spaces**
For a positive integer $r$, let
$$\mathbb{R}_{r-1}[x] = \text{Span}(1, x, x^2, \dots, x^{r-1})$$
denote the vector space of real polynomials of degree at most $r-1$, including the zero polynomial.
The list
$$1, x, x^2, \dots, x^{r-1}$$
is a basis, and hence
$$\dim \mathbb{R}_{r-1}[x] = r.$$
Before studying polynomial interpolation, we collect several elementary facts about roots of polynomials. These results will allow us to establish that the interpolation maps below have trivial kernels.

### Proposition 3.16 — Factor theorem
Let
$$p \in \mathbb{R}[x]$$
and let $a \in \mathbb{R}$. Then
$$p(a) = 0 \iff (x - a) \text{ divides } p(x), \text{ written as } (x - a) \mid p(x).$$

<!-- page 70 -->

### Proof
Suppose first that
$$(x - a) \mid p(x).$$
Then
$$p(x) = (x - a)q(x)$$
for some polynomial $q$, and therefore
$$p(a) = 0.$$
Conversely, suppose
$$p(a) = 0.$$
Write
$$p(x) = c_0 + c_1 x + \dots + c_n x^n.$$
Then
$$p(x) - p(a) = \sum_{k=1}^n c_k(x^k - a^k).$$
For every $k \geq 1$,
$$x^k - a^k = (x - a)(x^{k-1} + x^{k-2}a + \dots + xa^{k-2} + a^{k-1}).$$
Hence $x - a$ divides $p(x) - p(a)$. Since $p(a) = 0$,
$$p(x) = p(x) - p(a),$$
and therefore
$$(x - a) \mid p(x).$$

### Definition 3.17 — Multiplicity of a root
Let
$$p \in \mathbb{R}[x],$$
and suppose $p \neq 0$.
A number $a \in \mathbb{R}$ is called a **root of multiplicity** $m$ of $p$ if
$$(x - a)^m \mid p(x)$$
but
$$(x - a)^{m+1} \nmid p(x).$$

<!-- page 71 -->

More generally, we say that $a$ is a root of multiplicity at least $m$ if
$$(x - a)^m \mid p(x).$$
There is a nice link between the multiplicity of roots and derivatives.

### Proposition 3.18 — Multiplicity and derivatives
Let
$$p \in \mathbb{R}[x], \quad a \in \mathbb{R},$$
and let $m \geq 1$. Then
$$(x - a)^m \mid p(x)$$
if and only if
$$p(a) = p'(a) = \dots = p^{(m-1)}(a) = 0.$$

### Proof
We prove the result by induction on $m$.
For $m = 1$, the statement is exactly the factor theorem:
$$(x - a) \mid p(x) \iff p(a) = 0.$$
Now suppose the result holds for $m - 1$.
We first record a useful identity. If
$$p(x) = (x - a)q(x),$$
then for every $j \geq 1$,
$$p^{(j)}(x) = (x - a)q^{(j)}(x) + j q^{(j-1)}(x).$$
Indeed, the case $j = 1$ follows from the product rule,
$$p'(x) = q(x) + (x - a)q'(x),$$
and the general formula follows by repeated differentiation.
In particular, evaluating at $x = a$ gives
$$p^{(j)}(a) = j q^{(j-1)}(a).$$
Suppose first that
$$(x - a)^m \mid p(x).$$

<!-- page 72 -->

Then
$$p(x) = (x - a)q(x),$$
where
$$(x - a)^{m-1} \mid q(x).$$
By the induction hypothesis,
$$q(a) = q'(a) = \dots = q^{(m-2)}(a) = 0.$$
Also $p(a) = 0$, and for $j = 1, \dots, m - 1$,
$$p^{(j)}(a) = j q^{(j-1)}(a) = 0.$$
Thus
$$p(a) = p'(a) = \dots = p^{(m-1)}(a) = 0.$$
Conversely, suppose
$$p(a) = p'(a) = \dots = p^{(m-1)}(a) = 0.$$
Since $p(a) = 0$, the factor theorem gives
$$p(x) = (x - a)q(x)$$
for some polynomial $q$.
For $j = 1, \dots, m - 1$,
$$0 = p^{(j)}(a) = j q^{(j-1)}(a).$$
Since $j \neq 0$ in $\mathbb{R}$, we obtain
$$q(a) = q'(a) = \dots = q^{(m-2)}(a) = 0.$$
By the induction hypothesis,
$$(x - a)^{m-1} \mid q(x).$$
Therefore
$$(x - a)^m \mid p(x).$$

### Proposition 3.19 — Roots counted with multiplicity
Let
$$p \in \mathbb{R}[x]$$

<!-- page 73 -->

be a nonzero polynomial. Suppose that
$$a_1, \dots, a_s$$
are distinct roots of $p$ with multiplicities at least
$$m_1, \dots, m_s,$$
respectively. Then
$$\deg p \geq m_1 + \dots + m_s.$$

### Proof
Since $a_i$ is a root of multiplicity at least $m_i$,
$$(x - a_i)^{m_i} \mid p(x)$$
for every $i$.
Because the numbers
$$a_1, \dots, a_s$$
are distinct, these are distinct linear factors. Repeatedly factoring them out gives
$$p(x) = \left[ \prod_{i=1}^s (x - a_i)^{m_i} \right] q(x)$$
for some polynomial $q$.
Therefore
$$\deg p = \sum_{i=1}^s m_i + \deg q \geq \sum_{i=1}^s m_i.$$

### Corollary 3.20 — Number of roots of a polynomial
A nonzero polynomial of degree $d$ has at most $d$ distinct roots.
More generally, it has at most $d$ roots when roots are counted according to their multiplicities.

### Proof
Apply proposition 3.19. If the distinct roots have multiplicities
$$m_1, \dots, m_s,$$

<!-- page 74 -->

then
$$m_1 + \dots + m_s \leq \deg p = d.$$
Since every multiplicity is at least one,
$$s \leq d.$$

**Application 2: Interpolation at fixed points**
Let
$$x_1, \dots, x_r$$
be $r$ distinct real numbers. Suppose that we are given arbitrary values
$$y_1, \dots, y_r \in \mathbb{R}$$
and want to find a polynomial
$$p \in \mathbb{R}_{r-1}[x]$$
such that
$$p(x_i) = y_i, \quad i = 1, \dots, r.$$
Define the **evaluation map**
$$E : \mathbb{R}_{r-1}[x] \to \mathbb{R}^r$$
by
$$E(p) = \begin{pmatrix} p(x_1) \\ p(x_2) \\ \vdots \\ p(x_r) \end{pmatrix}.$$
The map $E$ is linear, and the interpolation problem is precisely the equation
$$E(p) = \begin{pmatrix} y_1 \\ \vdots \\ y_r \end{pmatrix}.$$

### Theorem 3.21 — Polynomial interpolation at distinct points
Let
$$x_1, \dots, x_r$$
be distinct real numbers. For every
$$y_1, \dots, y_r \in \mathbb{R},$$

<!-- page 75 -->

there exists a unique polynomial
$$p \in \mathbb{R}_{r-1}[x]$$
such that
$$p(x_i) = y_i, \quad i = 1, \dots, r.$$

### Proof
Because
$$\dim \mathbb{R}_{r-1}[x] = r = \dim \mathbb{R}^r,$$
it is enough to show that
$$\ker E = \{0\}.$$
Suppose
$$p \in \ker E.$$
Then
$$p(x_1) = p(x_2) = \dots = p(x_r) = 0.$$
Thus $p$ has $r$ distinct roots.
But a nonzero polynomial in $\mathbb{R}_{r-1}[x]$ has degree at most $r - 1$ and therefore cannot have $r$ distinct roots. Indeed, by corollary 3.20, a nonzero polynomial with $r$ distinct roots must have degree at least $r$.
Hence
$$p = 0.$$
Thus
$$\ker E = \{0\}.$$
By proposition 3.12, $E$ is bijective. Therefore every vector
$$(y_1, \dots, y_r) \in \mathbb{R}^r$$
corresponds to exactly one polynomial
$$p \in \mathbb{R}_{r-1}[x].$$

### Remark 3.22 — Existence and uniqueness without constructing the polynomial
The argument above proves existence and uniqueness without explicitly constructing the interpolating polynomial.
What is then this interpolating polynomial? Valid question. The *Lagrange interpolation formula*

<!-- page 76 -->

gives an explicit expression for that polynomial. This is beyond the scope of this course. The key point is that: Rank-nullity explains why such a unique polynomial must exist in the first place.

**Application 3: Hermite interpolation**
Ordinary polynomial interpolation prescribes the value of a polynomial at several distinct points. A natural generalization is to prescribe not only the value of the polynomial, but also some of its derivatives.
Let
$$x_1, \dots, x_s$$
be distinct real numbers, and let
$$m_1, \dots, m_s$$
be positive integers satisfying
$$m_1 + \dots + m_s = r.$$
At the point $x_i$, we prescribe
$$p(x_i), p'(x_i), \dots, p^{(m_i-1)}(x_i).$$
Thus the point $x_i$ contributes $m_i$ pieces of data, and altogether there are
$$m_1 + \dots + m_s = r$$
pieces of data.

### Theorem 3.23 — Hermite interpolation
Let
$$x_1, \dots, x_s$$
be distinct real numbers, and let
$$m_1 + \dots + m_s = r, \quad m_i \geq 1.$$
For arbitrary prescribed values
$$y_{i,j} \in \mathbb{R}, \quad i = 1, \dots, s, \quad j = 0, \dots, m_i - 1,$$
there exists a unique polynomial
$$p \in \mathbb{R}_{r-1}[x]$$

<!-- page 77 -->

such that
$$p^{(j)}(x_i) = y_{i,j}$$
for every $i$ and $j$.

### Proof
Define the linear map
$$H : \mathbb{R}_{r-1}[x] \to \mathbb{R}^r$$
by
$$H(p) = (p(x_1), p'(x_1), \dots, p^{(m_1-1)}(x_1); \dots; p(x_s), p'(x_s), \dots, p^{(m_s-1)}(x_s)).$$
Because differentiation and evaluation at a fixed point are linear, $H$ is a linear map.
Moreover,
$$\dim \mathbb{R}_{r-1}[x] = r = \dim \mathbb{R}^r.$$
By proposition 3.12, it is therefore enough to show that
$$\ker H = \{0\}.$$
Suppose
$$p \in \ker H.$$
Then, for every $i$,
$$p(x_i) = p'(x_i) = \dots = p^{(m_i-1)}(x_i) = 0.$$
By proposition 3.18, this implies that $x_i$ is a root of $p$ of multiplicity at least $m_i$.
Thus $p$ has roots whose total multiplicity is at least
$$m_1 + \dots + m_s = r.$$
By proposition 3.19, if $p$ were nonzero, then
$$\deg p \geq r.$$
But
$$p \in \mathbb{R}_{r-1}[x],$$
so
$$\deg p \leq r - 1.$$
This is impossible unless
$$p = 0.$$

<!-- page 78 -->

Hence
$$\ker H = \{0\}.$$
Since the domain and codomain of $H$ have the same finite dimension, proposition 3.12 implies that $H$ is bijective.
Therefore, for every collection of prescribed values
$$y_{i,j},$$
there exists a unique polynomial
$$p \in \mathbb{R}_{r-1}[x]$$
satisfying all the interpolation conditions.

### Remark 3.24 — Lagrange and Taylor interpolation as special cases
Hermite interpolation contains several familiar interpolation problems as special cases.
If
$$m_1 = \dots = m_r = 1,$$
then only function values are prescribed, and we recover ordinary interpolation at $r$ distinct points.
At the other extreme, if
$$s = 1, \quad m_1 = r,$$
then we prescribe
$$p(x_1), p'(x_1), \dots, p^{(r-1)}(x_1),$$
which is the finite-dimensional algebraic structure underlying Taylor interpolation.
In each case the proof is the same: zero data force sufficiently many zeros, counted with multiplicity, to make a nonzero polynomial of degree at most $r - 1$ impossible.

**Application 4: Interpolation from interval averages**
The data used in an interpolation problem need not consist of values at individual points. We can instead prescribe averages of the polynomial over intervals.
Let
$$I_i = [a_i, b_i], \quad i = 1, \dots, r,$$
where
$$a_i < b_i,$$

<!-- page 79 -->

and suppose the interiors of the intervals are pairwise disjoint:
$$(a_i, b_i) \cap (a_j, b_j) = \varnothing \quad \text{whenever } i \neq j.$$
Suppose we are given prescribed average values
$$\mu_1, \dots, \mu_r \in \mathbb{R}$$
and seek
$$p \in \mathbb{R}_{r-1}[x]$$
such that
$$\frac{1}{b_i - a_i} \int_{a_i}^{b_i} p(x) dx = \mu_i, \quad i = 1, \dots, r.$$
Define the linear map
$$\mathcal{A} : \mathbb{R}_{r-1}[x] \to \mathbb{R}^r$$
by
$$\mathcal{A}(p) = \begin{pmatrix} \frac{1}{b_1 - a_1} \int_{a_1}^{b_1} p(x) dx \\ \vdots \\ \frac{1}{b_r - a_r} \int_{a_r}^{b_r} p(x) dx \end{pmatrix}.$$

### Theorem 3.25 — Interpolation from averages over disjoint intervals
Let
$$I_1, \dots, I_r$$
be non-degenerate intervals with pairwise disjoint interiors.
For every collection of prescribed averages
$$\mu_1, \dots, \mu_r \in \mathbb{R},$$
there exists a unique polynomial
$$p \in \mathbb{R}_{r-1}[x]$$
satisfying
$$\frac{1}{b_i - a_i} \int_{a_i}^{b_i} p(x) dx = \mu_i, \quad i = 1, \dots, r.$$

<!-- page 80 -->

### Proof
Because
$$\dim \mathbb{R}_{r-1}[x] = r = \dim \mathbb{R}^r,$$
it is enough to prove
$$\ker \mathcal{A} = \{0\}.$$
Suppose
$$p \in \ker \mathcal{A}.$$
Then
$$\int_{a_i}^{b_i} p(x) dx = 0 \quad \text{for every } i.$$
Let $P$ be an antiderivative of $p$. Then
$$P(b_i) - P(a_i) = \int_{a_i}^{b_i} p(x) dx = 0.$$
Hence
$$P(a_i) = P(b_i).$$
By Rolle's theorem, there exists
$$\xi_i \in (a_i, b_i)$$
such that
$$P'(\xi_i) = 0.$$
Since
$$P' = p,$$
we obtain
$$p(\xi_i) = 0.$$
Because the interiors of the intervals are pairwise disjoint, the points
$$\xi_1, \dots, \xi_r$$
are distinct. Thus $p$ has at least $r$ distinct roots.
But
$$p \in \mathbb{R}_{r-1}[x],$$
so a nonzero $p$ can have at most $r - 1$ distinct roots. Therefore
$$p = 0.$$

<!-- page 81 -->

Hence
$$\ker \mathcal{A} = \{0\}.$$
By proposition 3.12, $\mathcal{A}$ is bijective, proving existence and uniqueness.

### Remark 3.26 — One principle behind all four applications
The preceding applications have the same mathematical structure.
We begin with a finite-dimensional space of unknown objects and construct a linear map that records the available data:
$$\text{unknown object} \longmapsto \text{observed data.}$$
For example,
$$x \longmapsto Ax$$
records linear equations,
$$p \longmapsto (p(x_1), \dots, p(x_r))$$
records point values,
$$p \longmapsto (p(x_i), p'(x_i), \dots)$$
records values and derivatives, and
$$p \longmapsto \left( \frac{1}{|I_i|} \int_{I_i} p \right)_{i=1}^r$$
records interval averages.
When the unknown space and the data space have the same finite dimension, rank-nullity reduces the entire existence-and-uniqueness question to the homogeneous problem:
$$\ker T = \{0\}.$$
Thus a recurring strategy in linear algebra is:
1. formulate the problem as a linear transformation;
2. study what zero data imply;
3. prove that the kernel is trivial;
4. use rank-nullity to conclude that the map is bijective.

<!-- page 82 -->

## 3.4 Rank of a Matrix
We have defined the rank of a linear map
$$T : V \to W$$
intrinsically by
$$\text{Rank}(T) = \dim \text{Im } T.$$
We now connect this definition with the matrix representing $T$.

### Proposition 3.27 — The image is generated by the images of a basis
Let
$$T : V \to W$$
be a linear map, and let
$$\mathcal{E} = (e_1, \dots, e_n)$$
be a basis of $V$. Then
$$\text{Im } T = \text{Span}(T(e_1), \dots, T(e_n)).$$

### Proof
Every vector $v \in V$ can be written as
$$v = x_1 e_1 + \dots + x_n e_n.$$
By linearity,
$$T(v) = x_1 T(e_1) + \dots + x_n T(e_n).$$
Hence every vector in $\text{Im } T$ belongs to
$$\text{Span}(T(e_1), \dots, T(e_n)).$$
Thus
$$\text{Im } T \subseteq \text{Span}(T(e_1), \dots, T(e_n)).$$
Conversely, each $T(e_j)$ belongs to $\text{Im } T$, and $\text{Im } T$ is a subspace of $W$. Therefore every linear combination of
$$T(e_1), \dots, T(e_n)$$
also belongs to $\text{Im } T$. Hence
$$\text{Span}(T(e_1), \dots, T(e_n)) \subseteq \text{Im } T.$$

<!-- page 83 -->

Therefore
$$\text{Im } T = \text{Span}(T(e_1), \dots, T(e_n)).$$
Now let
$$\mathcal{F} = (f_1, \dots, f_m)$$
be a basis of $W$, and let
$$A = [T]_{\mathcal{F} \leftarrow \mathcal{E}} \in \mathbb{K}^{m \times n}.$$
Recall that
$$T(e_j) = \sum_{i=1}^m a_{ij} f_i.$$
Therefore the $j$th column of $A$ is exactly the coordinate vector:
If
$$A = \begin{pmatrix} | & & | \\ a_1 & \dots & a_n \\ | & & | \end{pmatrix},$$
then
$$a_j = [T(e_j)]_{\mathcal{F}}.$$

### Definition 3.28 — Column space and rank of a matrix
Let
$$A = \begin{pmatrix} | & & | \\ a_1 & \dots & a_n \\ | & & | \end{pmatrix} \in \mathbb{K}^{m \times n},$$
where
$$a_1, \dots, a_n \in \mathbb{K}^m$$
are the columns of $A$.
The **column space** of $A$ is
$$\text{Col}(A) = \text{Span}(a_1, \dots, a_n) \leq \mathbb{K}^m.$$
The **rank** of $A$ is the dimension of its column space:
$$\text{Rank}(A) = \dim \text{Col}(A).$$

<!-- page 84 -->

### Remark 3.29 — What the column space represents
If
$$A = \begin{pmatrix} | & & | \\ a_1 & \dots & a_n \\ | & & | \end{pmatrix}$$
and
$$x = \begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix},$$
then
$$Ax = x_1 a_1 + \dots + x_n a_n.$$
Hence
$$\{Ax : x \in \mathbb{K}^n\} = \text{Col}(A).$$
Thus the column space is exactly the set of vectors that can be produced by multiplication by $A$.

### Proposition 3.30 — Rank of a linear map and rank of its matrix
Let
$$T : V \to W$$
be a linear map between finite-dimensional vector spaces. Let
$$\mathcal{E} = (e_1, \dots, e_n)$$
and
$$\mathcal{F} = (f_1, \dots, f_m)$$
be bases of $V$ and $W$, respectively, and let
$$A = [T]_{\mathcal{F} \leftarrow \mathcal{E}}.$$
Then
$$\text{Rank}(T) = \text{Rank}(A).$$

### Proof
By proposition 3.27,
$$\text{Im } T = \text{Span}(T(e_1), \dots, T(e_n)).$$

<!-- page 85 -->

The columns of
$$A = [T]_{\mathcal{F} \leftarrow \mathcal{E}}$$
are
$$[T(e_1)]_{\mathcal{F}}, \dots, [T(e_n)]_{\mathcal{F}}.$$
Therefore
$$\text{Col}(A) = \text{Span}([T(e_1)]_{\mathcal{F}}, \dots, [T(e_n)]_{\mathcal{F}}).$$
Passing from a vector in $W$ to its coordinate vector with respect to $\mathcal{F}$ is a linear bijection
$$W \longrightarrow \mathbb{K}^m.$$
Hence it preserves linear independence, spanning, and dimension. (Check this statement as an exercise. Search "Linear Isomorphism" online for hints.)
Therefore
$$\dim \text{Im} T = \dim \text{Col}(A).$$
By the definitions of rank,
$$\text{Rank}(T) = \text{Rank}(A).$$

**Remark 3.31 — The column space is the image in coordinates**

If
$$A = [T]_{\mathcal{F} \leftarrow \mathcal{E}},$$
then
$$\text{Col}(A)$$
is the coordinate representation, with respect to $\mathcal{F}$, of
$$\text{Im} T.$$
Thus
$$\text{Im} T \quad \text{and} \quad \text{Col}(A)$$
represent the same collection of outputs, one intrinsically in $W$ and the other in coordinates in $\mathbb{K}^m$.

Now let's turn the rank-nullity theorem into the world of matrices.

<!-- page 86 -->

**Definition 3.32 — Kernel and nullity of a matrix**

Let
$$A \in \mathbb{K}^{m \times n}.$$
The **kernel** or **null space** of $A$ is
$$\text{ker} A = \{x \in \mathbb{K}^n : Ax = 0\}.$$
Its dimension is called the **nullity** of $A$:
$$\text{nullity}(A) = \dim \text{ker} A.$$

**Corollary 3.33 — Rank-nullity for matrices**

Let
$$A \in \mathbb{K}^{m \times n}.$$
Then
$$n = \text{Rank}(A) + \text{nullity}(A).$$
Equivalently,
$$n = \text{Rank}(A) + \dim \text{ker} A.$$

**Proof**

Consider the linear map
$$T_A : \mathbb{K}^n \to \mathbb{K}^m, \quad T_A(x) = Ax.$$
Its kernel is
$$\text{ker} T_A = \{x \in \mathbb{K}^n : Ax = 0\} = \text{ker} A,$$
and its image is the column space of $A$:
$$\text{Im} T_A = \text{Col}(A).$$
Hence
$$\text{Rank}(T_A) = \text{Rank}(A).$$
Applying the rank-nullity theorem to $T_A$ gives
$$\dim \mathbb{K}^n = \dim \text{ker} T_A + \text{Rank}(T_A).$$
Therefore
$$n = \dim \text{ker} A + \text{Rank}(A).$$

<!-- page 87 -->

**Remark 3.34 — Why the number of columns appears in rank-nullity**

For
$$A \in \mathbb{K}^{m \times n},$$
the matrix represents a linear map
$$\mathbb{K}^n \to \mathbb{K}^m.$$
Thus the domain has dimension $n$, which is exactly the number of columns of $A$.
This is why the matrix rank-nullity formula is
$$\text{Rank}(A) + \text{nullity}(A) = n,$$
rather than $m$.

As a useful corollary, we obtain the following bound on the rank of a matrix.

**Corollary 3.35 — Basic bounds on matrix rank**

If
$$A \in \mathbb{K}^{m \times n},$$
then
$$0 \leq \text{Rank}(A) \leq \min\{m, n\}.$$

**Proof**

Because
$$\text{Col}(A) \leq \mathbb{K}^m,$$
we have
$$\text{Rank}(A) = \dim \text{Col}(A) \leq m.$$
Also,
$$\text{Col}(A)$$
is spanned by the $n$ columns of $A$, so
$$\text{Rank}(A) \leq n.$$
Therefore
$$\text{Rank}(A) \leq \min\{m, n\}.$$

There are all sorts of other rank inequalities for matrices. We will not touch upon those in this course.

<!-- page 88 -->

**Remark 3.36 — Rank does not depend on the choice of bases**

The matrix representing a linear map depends on the chosen bases, but its rank does not.
Indeed, if
$$A = [T]_{\mathcal{F} \leftarrow \mathcal{E}},$$
then
$$\text{Rank}(A) = \text{Rank}(T) = \dim \text{Im} T.$$
The quantity on the right is defined entirely in terms of the linear map $T$ and does not involve any choice of coordinates.
Consequently, every matrix representation of the same linear map has the same rank.
Thus the entries of a matrix depend on the choice of coordinates, but its rank measures an intrinsic property of the underlying linear map.

**3.5 Change of Bases for a Linear Map**

We have already seen how the coordinate vector of a vector changes when the basis is changed. We now apply the same idea to the matrix representing a linear map.
Let
$$T : V \to W$$
be linear. Let
$$\mathcal{E} = (e_1, \dots, e_n), \quad \mathcal{E}' = (e'_1, \dots, e'_n)$$
be bases of $V$, and let
$$\mathcal{F} = (f_1, \dots, f_m), \quad \mathcal{F}' = (f'_1, \dots, f'_m)$$
be bases of $W$.
Suppose
$$(e'_1, \dots, e'_n) = (e_1, \dots, e_n)P$$
and
$$(f'_1, \dots, f'_m) = (f_1, \dots, f_m)Q,$$
where $P$ and $Q$ are invertible.
Recall that
$$[v]_{\mathcal{E}} = P[v]_{\mathcal{E}'}$$
for every $v \in V$, and
$$[w]_{\mathcal{F}} = Q[w]_{\mathcal{F}'}$$
for every $w \in W$.

<!-- page 89 -->

Equivalently,
$$P = [I_V]_{\mathcal{E} \leftarrow \mathcal{E}'}, \quad Q = [I_W]_{\mathcal{F} \leftarrow \mathcal{F}'}.$$

**Proposition 3.37 — Change of bases for a linear map**

Let
$$A = [T]_{\mathcal{F} \leftarrow \mathcal{E}}, \quad B = [T]_{\mathcal{F}' \leftarrow \mathcal{E}'}.$$
Then
$$B = Q^{-1}AP.$$

**Proof**

For every $v \in V$,
$$[T(v)]_{\mathcal{F}} = A[v]_{\mathcal{E}}.$$
Since
$$[v]_{\mathcal{E}} = P[v]_{\mathcal{E}'},$$
we have
$$[T(v)]_{\mathcal{F}} = AP[v]_{\mathcal{E}'}.$$
On the other hand,
$$[T(v)]_{\mathcal{F}'} = B[v]_{\mathcal{E}'},$$
and because
$$[T(v)]_{\mathcal{F}} = Q[T(v)]_{\mathcal{F}'},$$
we obtain
$$[T(v)]_{\mathcal{F}} = QB[v]_{\mathcal{E}'}.$$
Hence
$$AP[v]_{\mathcal{E}'} = QB[v]_{\mathcal{E}'}$$
for every $v \in V$. Since the coordinate vectors $[v]_{\mathcal{E}'}$ range over all of $\mathbb{K}^n$,
$$AP = QB.$$
Therefore
$$B = Q^{-1}AP.$$

<!-- page 90 -->

**Remark 3.38 — How to read the change-of-bases formula**

The formula
$$[T]_{\mathcal{F}' \leftarrow \mathcal{E}'} = Q^{-1}[T]_{\mathcal{F} \leftarrow \mathcal{E}}P$$
reflects the order of the coordinate changes:
$$[v]_{\mathcal{E}'} \xrightarrow{P} [v]_{\mathcal{E}} \xrightarrow{[T]_{\mathcal{F} \leftarrow \mathcal{E}}} [T(v)]_{\mathcal{F}} \xrightarrow{Q^{-1}} [T(v)]_{\mathcal{F}'}.$$
Thus changing the basis of the domain acts on the right of the matrix, whereas changing the basis of the codomain acts on the left.

**Corollary 3.39 — Change of basis for a linear operator**

Let
$$T : V \to V$$
be a linear transformation, and suppose
$$\mathcal{E}' = \mathcal{E}P.$$
Then
$$[T]_{\mathcal{E}' \leftarrow \mathcal{E}'} = P^{-1}[T]_{\mathcal{E} \leftarrow \mathcal{E}}P.$$

**Definition 3.40 — Similar matrices**

Two square matrices $A$ and $B$ are called **similar** if there exists an invertible matrix $P$ such that
$$B = P^{-1}AP.$$

**Remark 3.41 — One basis change versus two**

For a linear transformation
$$T : V \to V,$$
using the same basis for the domain and codomain leads to similarity:
$$B = P^{-1}AP.$$
For a general linear map
$$T : V \to W,$$

<!-- page 91 -->

the bases of $V$ and $W$ may be chosen independently, giving
$$B = Q^{-1}AP.$$
This greater freedom will allow us to choose bases adapted to the kernel and image of $T$ and obtain the rank normal form
$$[T]_{\mathcal{F}' \leftarrow \mathcal{E}'} = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}, \quad r = \text{Rank}(T).$$
Equivalently, every matrix $A$ of rank $r$ can be transformed by invertible matrices on the left and right into this form. Coming in the next subsection!

**3.6 Row Rank and the Rank Normal Form**

We have defined the rank of a matrix using its columns: if
$$A \in \mathbb{K}^{m \times n},$$
then
$$\text{Rank}(A) = \dim \text{Col}(A).$$
There is an analogous space generated by the rows of $A$. At first, there is no obvious reason why the dimensions of these two spaces should be the same. We will prove, however, that they are equal.

**Definition 3.42 — Row space and row rank**

Let
$$A \in \mathbb{K}^{m \times n},$$
and let
$$\rho_1, \dots, \rho_m \in \mathbb{K}_n$$
denote the rows of $A$.
The **row space** of $A$ is
$$\text{Row}(A) = \text{Span}(\rho_1, \dots, \rho_m) \leq \mathbb{K}_n.$$
The **row rank** of $A$ is
$$\dim \text{Row}(A).$$
At this point we therefore have two quantities:
$$\underbrace{\dim \text{Col}(A)}_{\text{column rank}} \quad \text{and} \quad \underbrace{\dim \text{Row}(A)}_{\text{row rank}}.$$

<!-- page 92 -->

Our definition of $\text{Rank}(A)$ is the first of these. We will show below that the second always has exactly the same value.

**A basis adapted to a linear map**

The rank-nullity theorem gives more than a dimension formula. Its proof shows how to choose bases of the domain and codomain that reveal the structure of a linear map particularly clearly.

**Proposition 3.43 — Adapted-basis form of a linear map**

Let
$$T : V \to W$$
be a linear map between finite-dimensional vector spaces, and suppose
$$\dim V = n, \quad \dim W = m, \quad \text{Rank}(T) = r.$$
Then there exist bases
$$\mathcal{E}' = (v_1, \dots, v_r, u_1, \dots, u_{n-r})$$
of $V$ and
$$\mathcal{F}' = (T(v_1), \dots, T(v_r), w_{r+1}, \dots, w_m)$$
of $W$ such that
$$[T]_{\mathcal{F}' \leftarrow \mathcal{E}'} = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}.$$

**Proof**

Choose a basis
$$u_1, \dots, u_{n-r}$$
of $\text{ker} T$. By rank-nullity,
$$\dim \text{ker} T = n - r.$$
By the basis extension theorem, extend this basis of $\text{ker} T$ to a basis of $V$. After reordering the basis vectors, write this basis as
$$\mathcal{E}' = (v_1, \dots, v_r, u_1, \dots, u_{n-r}).$$
As we proved in the rank-nullity theorem,
$$T(v_1), \dots, T(v_r)$$
is a basis of $\text{Im} T$.

<!-- page 93 -->

Since $\text{Im} T$ is a subspace of $W$, extend this basis of $\text{Im} T$ to a basis of $W$:
$$\mathcal{F}' = (T(v_1), \dots, T(v_r), w_{r+1}, \dots, w_m).$$
Now consider the matrix of $T$ with respect to these bases.
For $j = 1, \dots, r$,
$$T(v_j)$$
is the $j$th vector of the basis $\mathcal{F}'$. Hence
$$[T(v_j)]_{\mathcal{F}'} = \begin{pmatrix} 0 \\ \vdots \\ 1 \\ \vdots \\ 0 \end{pmatrix},$$
with the 1 in position $j$.
Thus the first $r$ columns of
$$[T]_{\mathcal{F}' \leftarrow \mathcal{E}'}$$
form the block
$$\begin{pmatrix} I_r \\ 0 \end{pmatrix}.$$
For the remaining basis vectors,
$$u_j \in \text{ker} T,$$
and hence
$$T(u_j) = 0.$$
Therefore all the remaining columns are zero.
Consequently,
$$[T]_{\mathcal{F}' \leftarrow \mathcal{E}'} = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}.$$

**Remark 3.44 — What the adapted-basis form means**

The matrix
$$\begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}$$
shows the essential structure of a rank-$r$ linear map.

<!-- page 94 -->

After suitable choices of coordinates,
$$T$$
keeps $r$ independent directions and sends the remaining $n - r$ independent directions to zero.
Thus, up to independent choices of bases in the domain and codomain, the integer
$$r = \text{Rank}(T)$$
is the only information needed to describe the basic structure of the linear map.

**The rank normal form**

We now translate the preceding statement about linear maps into a statement about matrices.
Recall that if
$$A = [T]_{\mathcal{F} \leftarrow \mathcal{E}}$$
and we change the bases in the domain and codomain, then
$$[T]_{\mathcal{F}' \leftarrow \mathcal{E}'} = Q^{-1}AP$$
for suitable invertible change-of-basis matrices $P$ and $Q$.

**Theorem 3.45 — Rank normal form**

Let
$$A \in \mathbb{K}^{m \times n}$$
and suppose
$$\text{Rank}(A) = r.$$
Then there exist invertible matrices
$$P \in \mathbb{K}^{m \times m}, \quad Q \in \mathbb{K}^{n \times n}$$
such that
$$PAQ = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}.$$

**Proof**

Regard $A$ as the matrix of the associated linear map
$$T_A : \mathbb{K}^n \to \mathbb{K}^m, \quad T_A(x) = Ax,$$

<!-- page 95 -->

with respect to the standard bases.
We have already shown that
$$\text{Rank}(T_A) = \text{Rank}(A) = r.$$
By proposition 3.43, there exist bases $\mathcal{E}'$ of $\mathbb{K}^n$ and $\mathcal{F}'$ of $\mathbb{K}^m$ such that
$$[T_A]_{\mathcal{F}' \leftarrow \mathcal{E}'} = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}.$$
By the change-of-bases formula, there exist invertible matrices $Q_0 \in \mathbb{K}^{n \times n}$ and $P_0 \in \mathbb{K}^{m \times m}$ such that
$$[T_A]_{\mathcal{F}' \leftarrow \mathcal{E}'} = P_0^{-1}AQ_0.$$
Therefore
$$P_0^{-1}AQ_0 = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}.$$
Setting
$$P = P_0^{-1}, \quad Q = Q_0,$$
gives
$$PAQ = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}.$$

**Remark 3.46 — The rank normal form is a change-of-basis statement**

The rank normal form should not be viewed merely as a matrix simplification procedure.
Left multiplication by an invertible matrix corresponds to changing coordinates in the codomain, while right multiplication by an invertible matrix corresponds to changing coordinates in the domain.
Thus
$$PAQ = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}$$
is the matrix version of the statement that every rank-$r$ linear map takes the same simple form after suitable choices of bases.

**Behavior of the row space under invertible multiplication**

To compare row rank with column rank, we first record how the row space behaves when a matrix is multiplied by invertible matrices.

<!-- page 96 -->

**Proposition 3.47 — Row rank is preserved by invertible multiplication**

Let
$$A \in \mathbb{K}^{m \times n},$$
and let
$$P \in \mathbb{K}^{m \times m}, \quad Q \in \mathbb{K}^{n \times n}$$
be invertible. Then
$$\dim \text{Row}(PAQ) = \dim \text{Row}(A).$$

**Proof**

Write
$$P = (p_{ij})_{i,j=1}^m,$$
and denote the rows of $A$ by
$$A_{1, \cdot}, \dots, A_{m, \cdot} \in \mathbb{K}_n.$$
We consider left and right multiplication separately.
First consider left multiplication by $P$.
By the rule for matrix multiplication, the $i$th row of $PA$ is
$$(PA)_{i, \cdot} = \sum_{j=1}^m p_{ij}A_{j, \cdot}.$$
Indeed, for each column $k$,
$$(PA)_{ik} = \sum_{j=1}^m p_{ij}a_{jk},$$
which is precisely the $k$th entry of the row vector
$$\sum_{j=1}^m p_{ij}A_{j, \cdot}.$$
Thus every row of $PA$ is a linear combination of the rows of $A$. Therefore
$$\text{Row}(PA) \subseteq \text{Row}(A).$$
To obtain the reverse inclusion, use the invertibility of $P$. Since
$$A = P^{-1}(PA),$$

<!-- page 97 -->

write
$$P^{-1} = (c_{ij})_{i,j=1}^m.$$
Applying the same row formula gives
$$A_{i, \cdot} = \sum_{j=1}^m c_{ij}(PA)_{j, \cdot}.$$
Hence every row of $A$ is a linear combination of the rows of $PA$. Therefore
$$\text{Row}(A) \subseteq \text{Row}(PA).$$
Combining the two inclusions,
$$\text{Row}(PA) = \text{Row}(A).$$
In particular,
$$\dim \text{Row}(PA) = \dim \text{Row}(A).$$
Now consider right multiplication by $Q$.
For each $i = 1, \dots, m$, the $i$th row of $AQ$ is
$$(AQ)_{i, \cdot} = A_{i, \cdot}Q.$$
Thus right multiplication by $Q$ applies the same linear transformation
$$R_Q : \mathbb{K}_n \to \mathbb{K}_n, \quad R_Q(x) = xQ,$$
to every row of $A$.
We now show that
$$\text{Row}(AQ) = R_Q(\text{Row}(A)).$$
Take any vector
$$y \in \text{Row}(AQ).$$
Then $y$ is a linear combination of the rows of $AQ$, so for some scalars $\lambda_1, \dots, \lambda_m$,
$$y = \sum_{i=1}^m \lambda_i(AQ)_{i, \cdot}.$$
Using
$$(AQ)_{i, \cdot} = A_{i, \cdot}Q,$$

<!-- page 98 -->

we obtain
$$y = \sum_{i=1}^m \lambda_i(A_{i, \cdot}Q)$$
$$= \left( \sum_{i=1}^m \lambda_i A_{i, \cdot} \right) Q.$$
Since
$$\sum_{i=1}^m \lambda_i A_{i, \cdot} \in \text{Row}(A),$$
we have
$$y \in R_Q(\text{Row}(A)).$$
Hence
$$\text{Row}(AQ) \subseteq R_Q(\text{Row}(A)).$$
Conversely, take
$$y \in R_Q(\text{Row}(A)).$$
Then
$$y = xQ$$
for some
$$x \in \text{Row}(A).$$
Write
$$x = \sum_{i=1}^m \lambda_i A_{i, \cdot}.$$
Then
$$y = \left( \sum_{i=1}^m \lambda_i A_{i, \cdot} \right) Q$$
$$= \sum_{i=1}^m \lambda_i(A_{i, \cdot}Q)$$
$$= \sum_{i=1}^m \lambda_i(AQ)_{i, \cdot}.$$
Therefore
$$y \in \text{Row}(AQ).$$
Thus
$$\text{Row}(AQ) = R_Q(\text{Row}(A)).$$
Because $Q$ is invertible, the map
$$R_Q : x \mapsto xQ$$

<!-- page 99 -->

is a linear bijection, with inverse
$$R_{Q^{-1}} : x \mapsto xQ^{-1}.$$
A linear bijection preserves dimension, so
$$\dim \text{Row}(AQ) = \dim \text{Row}(A).$$
Finally, apply these two results successively:
$$\dim \text{Row}(PAQ) = \dim \text{Row}(AQ) = \dim \text{Row}(A).$$
Therefore
$$\dim \text{Row}(PAQ) = \dim \text{Row}(A).$$

Equality of row rank and column rank
We can now prove one of the fundamental facts about matrix rank.

Theorem 3.48 — Row rank equals column rank
For every matrix
$$A \in \mathbb{K}^{m \times n},$$
the dimension of the row space equals the dimension of the column space:
$$\dim \text{Row}(A) = \dim \text{Col}(A).$$
Hence
$$\dim \text{Row}(A) = \text{Rank}(A).$$

Proof
Let
$$r = \text{Rank}(A) = \dim \text{Col}(A).$$
By the rank normal form theorem, there exist invertible matrices $P$ and $Q$ such that
$$PAQ = R,$$
where
$$R = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}.$$

<!-- page 100 -->

By proposition 3.47,
$$\dim \text{Row}(A) = \dim \text{Row}(R).$$
The matrix $R$ has exactly $r$ nonzero rows, namely
$$(1, 0, \dots, 0), \quad (0, 1, \dots, 0), \quad \dots, \quad (0, \dots, 1, 0, \dots, 0),$$
and these rows are linearly independent. Therefore
$$\dim \text{Row}(R) = r.$$
Hence
$$\dim \text{Row}(A) = r.$$
But
$$r = \dim \text{Col}(A).$$
Therefore
$$\dim \text{Row}(A) = \dim \text{Col}(A).$$

Remark 3.49 — The two meanings of matrix rank
We originally defined
$$\text{Rank}(A) = \dim \text{Col}(A).$$
The preceding theorem shows that we may equally write
$$\text{Rank}(A) = \dim \text{Row}(A).$$
Thus
$$\text{Rank}(A) = \text{number of independent columns} = \text{number of independent rows}.$$

Corollary 3.50 — Rank of the transpose
For every matrix
$$A \in \mathbb{K}^{m \times n},$$
we have
$$\text{Rank}(A^\top) = \text{Rank}(A).$$

<!-- page 101 -->

Proof
The columns of $A^\top$ are precisely the transposes of the rows of $A$. Hence
$$\dim \text{Col}(A^\top) = \dim \text{Row}(A).$$
By the equality of row rank and column rank,
$$\dim \text{Row}(A) = \text{Rank}(A).$$
Therefore
$$\text{Rank}(A^\top) = \dim \text{Col}(A^\top) = \text{Rank}(A).$$

Matrix equivalence
The rank normal form also gives a complete classification of matrices under independent changes of coordinates in the domain and codomain.

Definition 3.51 — Equivalent matrices
Two matrices
$$A, B \in \mathbb{K}^{m \times n}$$
are called equivalent if there exist invertible matrices
$$P \in \mathbb{K}^{m \times m}, \quad Q \in \mathbb{K}^{n \times n}$$
such that
$$B = PAQ.$$

Remark 3.52 — Equivalence versus similarity
Matrix equivalence should be distinguished from matrix similarity.
Similarity has the form
$$B = P^{-1}AP$$
and corresponds to changing the basis of a linear transformation
$$T : V \to V$$
in the same way in both the domain and codomain.
Matrix equivalence has the more general form
$$B = PAQ,$$

<!-- page 102 -->

where the two invertible matrices are independent. It corresponds to changing bases independently in the domain and codomain of a linear map
$$T : V \to W.$$

Corollary 3.53 — Rank is invariant under matrix equivalence
If
$$B = PAQ,$$
where $P$ and $Q$ are invertible, then
$$\text{Rank}(B) = \text{Rank}(A).$$

Proof
By the equality of row rank and column rank,
$$\text{Rank}(B) = \dim \text{Row}(B).$$
Since
$$B = PAQ,$$
proposition 3.47 gives
$$\dim \text{Row}(B) = \dim \text{Row}(A).$$
Hence
$$\text{Rank}(B) = \text{Rank}(A).$$

Theorem 3.54 — Rank classifies matrices up to equivalence
Let
$$A, B \in \mathbb{K}^{m \times n}.$$
Then $A$ and $B$ are equivalent if and only if
$$\text{Rank}(A) = \text{Rank}(B).$$

Proof
Suppose first that $A$ and $B$ are equivalent. Then
$$B = PAQ$$

<!-- page 103 -->

for some invertible $P$ and $Q$. By corollary 3.53,
$$\text{Rank}(B) = \text{Rank}(A).$$
Conversely, suppose
$$\text{Rank}(A) = \text{Rank}(B) = r.$$
By the rank normal form theorem, there exist invertible matrices $P_A, Q_A, P_B, Q_B$ such that
$$P_A A Q_A = \begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix} = P_B B Q_B.$$
Therefore
$$B = P_B^{-1} P_A A Q_A Q_B^{-1}.$$
Both
$$P_B^{-1} P_A \quad \text{and} \quad Q_A Q_B^{-1}$$
are invertible. Hence $A$ and $B$ are equivalent.

Remark 3.55 — Rank as the complete invariant of matrix equivalence
For matrices of a fixed size,
$$\text{Rank}(A) = r$$
completely determines the equivalence class of $A$.
Indeed, every $m \times n$ matrix of rank $r$ is equivalent to the same matrix
$$\begin{pmatrix} I_r & 0 \\ 0 & 0 \end{pmatrix}.$$
Thus, after arbitrary choices of bases in both the domain and codomain, all matrices of the same rank represent the same basic linear-map structure.

Full-rank matrices
The equality of row rank and column rank also gives useful terminology for matrices whose rows or columns are as independent as their dimensions allow.

Definition 3.56 — Full row rank and full column rank
Let
$$A \in \mathbb{K}^{m \times n}.$$

<!-- page 104 -->

We say that $A$ has full row rank if
$$\text{Rank}(A) = m,$$
and that $A$ has full column rank if
$$\text{Rank}(A) = n.$$
Thus full row rank means that the $m$ rows of $A$ are linearly independent, whereas full column rank means that the $n$ columns of $A$ are linearly independent.

Square matrices as a special class of matrices have the following corollary.

Corollary 3.57 — Rank and invertibility of a square matrix
Let
$$A \in \mathbb{K}^{n \times n}.$$
Then the following statements are equivalent:
(i) $A$ is invertible;
(ii) $\text{Rank}(A) = n$;
(iii) the columns of $A$ form a basis of $\mathbb{K}^n$;
(iv) the rows of $A$ form a basis of $\mathbb{K}^n$;
(v) $\ker A = \{0\}$.

Proof
We prove the equivalences by linking each statement to the rank condition
$$\text{Rank}(A) = n.$$
First, we show that
(i) $\implies$ (v).
Suppose $A$ is invertible and
$$x \in \ker A.$$
Then
$$Ax = 0.$$
Multiplying by $A^{-1}$ gives
$$x = A^{-1}Ax = A^{-1}0 = 0.$$
Hence
$$\ker A = \{0\}.$$

<!-- page 105 -->

Next, by the matrix form of the rank-nullity theorem, corollary 3.33,
$$n = \text{Rank}(A) + \dim \ker A.$$
Therefore,
$$\ker A = \{0\} \iff \dim \ker A = 0 \iff \text{Rank}(A) = n.$$
Thus
(v) $\iff$ (ii).
Now consider the columns of $A$.
By definition 3.28,
$$\text{Rank}(A) = \dim \text{Col}(A),$$
where $\text{Col}(A)$ is the span of the $n$ columns of $A$. Hence
$$\text{Rank}(A) = n$$
means that the column space has dimension $n$.
Since
$$\text{Col}(A) \subseteq \mathbb{K}^n \quad \text{and} \quad \dim \mathbb{K}^n = n,$$
we must have
$$\text{Col}(A) = \mathbb{K}^n.$$
Thus the $n$ columns of $A$ span $\mathbb{K}^n$.
By proposition 1.21, $n$ vectors that span an $n$-dimensional vector space form a basis. Therefore,
$$\text{Rank}(A) = n \iff \text{the columns of } A \text{ form a basis of } \mathbb{K}^n.$$
Hence
(ii) $\iff$ (iii).
For the rows, theorem 3.48 gives
$$\dim \text{Row}(A) = \text{Rank}(A).$$
Therefore
$$\text{Rank}(A) = n \iff \dim \text{Row}(A) = n.$$
Since the row space is a subspace of $\mathbb{K}_n$, which has dimension $n$, this is equivalent to
$$\text{Row}(A) = \mathbb{K}_n.$$
Thus the $n$ rows of $A$ span $\mathbb{K}_n$.

<!-- page 106 -->

Again, by proposition 1.21, the $n$ rows therefore form a basis of $\mathbb{K}_n$. Hence
(ii) $\iff$ (iv).
It remains to close the implication back to invertibility.
Suppose
$$\text{Rank}(A) = n.$$
By the rank normal form theorem, theorem 3.45, there exist invertible matrices $P, Q \in \mathbb{K}^{n \times n}$ such that
$$PAQ = (I_n) = I_n.$$
Hence
$$A = P^{-1}Q^{-1}.$$
Since $P^{-1}$ and $Q^{-1}$ are invertible, their product is invertible. Therefore $A$ is invertible.
Thus
(ii) $\implies$ (i).
Combining the implications,
(i) $\iff$ (ii) $\iff$ (iii) $\iff$ (iv) $\iff$ (v).

4 Sums, Direct Sums, and Invariant Subspaces
We have studied individual subspaces of a vector space. We now study how different subspaces are related to one another.

4.1 Intersections and Sums of Subspaces
Let $U$ and $W$ be subspaces of a vector space $V$.

Definition 4.1 — Intersection and sum of subspaces
The intersection of $U$ and $W$ is
$$U \cap W = \{v \in V : v \in U \text{ and } v \in W\}.$$
The sum of $U$ and $W$ is
$$U + W = \{u + w : u \in U, w \in W\}.$$
The intersection consists of those vectors belonging to both subspaces. The sum consists of all vectors that can be obtained by taking one vector from each subspace and adding them.

<!-- page 107 -->

Proposition 4.2 — Intersection and sum are subspaces
Let $U$ and $W$ be subspaces of $V$. Then
$$U \cap W \quad \text{and} \quad U + W$$
are both subspaces of $V$.
Moreover:
(1) $U \cap W$ is the largest subspace contained in both $U$ and $W$;
(2) $U + W$ is the smallest subspace containing both $U$ and $W$.

Proof
We first consider the intersection.
Because $U$ and $W$ are subspaces,
$$0 \in U \quad \text{and} \quad 0 \in W,$$
so
$$0 \in U \cap W.$$
If
$$x, y \in U \cap W,$$
then
$$x, y \in U \quad \text{and} \quad x, y \in W.$$
Since both $U$ and $W$ are subspaces,
$$x + y \in U \quad \text{and} \quad x + y \in W.$$
Therefore
$$x + y \in U \cap W.$$
Similarly, if
$$c \in \mathbb{K} \quad \text{and} \quad x \in U \cap W,$$
then
$$cx \in U \quad \text{and} \quad cx \in W,$$
so
$$cx \in U \cap W.$$
Hence $U \cap W$ is a subspace.

<!-- page 108 -->

Now consider the sum. Since
$$0 = 0 + 0, \quad 0 \in U, \quad 0 \in W,$$
we have
$$0 \in U + W.$$
Suppose
$$x = u_1 + w_1, \quad y = u_2 + w_2$$
belong to $U + W$, where
$$u_1, u_2 \in U, \quad w_1, w_2 \in W.$$
Then
$$x + y = (u_1 + u_2) + (w_1 + w_2).$$
Because
$$u_1 + u_2 \in U, \quad w_1 + w_2 \in W,$$
we have
$$x + y \in U + W.$$
Similarly, for $c \in \mathbb{K}$,
$$cx = c(u_1 + w_1) = cu_1 + cw_1,$$
where
$$cu_1 \in U, \quad cw_1 \in W.$$
Thus
$$cx \in U + W.$$
Hence $U + W$ is also a subspace.
It remains to verify the two extremal properties.
Clearly,
$$U \cap W \subseteq U \quad \text{and} \quad U \cap W \subseteq W.$$
If $S$ is any subspace satisfying
$$S \subseteq U \quad \text{and} \quad S \subseteq W,$$
then every vector of $S$ belongs to both $U$ and $W$. Hence
$$S \subseteq U \cap W.$$
Thus $U \cap W$ is the largest subspace contained in both.

<!-- page 109 -->

For the sum, observe that
$$u = u + 0 \in U + W \quad \text{for every } u \in U,$$
and similarly
$$w = 0 + w \in U + W \quad \text{for every } w \in W.$$
Thus
$$U \subseteq U + W, \quad W \subseteq U + W.$$
Now suppose $S$ is any subspace containing both $U$ and $W$. If
$$x \in U + W,$$
then
$$x = u + w$$
for some
$$u \in U, \quad w \in W.$$
Since
$$U, W \subseteq S$$
and $S$ is closed under addition,
$$u + w \in S.$$
Therefore
$$U + W \subseteq S.$$
Hence $U + W$ is the smallest subspace containing both $U$ and $W$.

### Remark 4.3 — Sum versus union
In general,
$$U \cup W$$
is not a subspace. If
$$u \in U \setminus W \quad \text{and} \quad w \in W \setminus U,$$
then typically
$$u + w \notin U \cup W.$$
The sum $U + W$ repairs this problem by including all linear combinations generated jointly by the two subspaces.
Indeed,
$$U + W = \text{Span}(U \cup W).$$

<!-- page 110 -->

(Try to prove this, it should not be too hard.)

### Example 4.4 — Intersection and sum in $\mathbb{R}^3$
Let
$$U = \left\{ \begin{pmatrix} x \\ y \\ 0 \end{pmatrix} : x, y \in \mathbb{R} \right\}$$
be the $xy$-plane, and let
$$W = \left\{ \begin{pmatrix} 0 \\ y \\ z \end{pmatrix} : y, z \in \mathbb{R} \right\}$$
be the $yz$-plane.
A vector belongs to both $U$ and $W$ precisely when its first and third coordinates are zero.
Hence
$$U \cap W = \left\{ \begin{pmatrix} 0 \\ y \\ 0 \end{pmatrix} : y \in \mathbb{R} \right\},$$
which is the $y$-axis.
On the other hand,
$$U + W = \mathbb{R}^3.$$
Indeed, for every
$$\begin{pmatrix} x \\ y \\ z \end{pmatrix} \in \mathbb{R}^3,$$
we may write
$$\begin{pmatrix} x \\ y \\ z \end{pmatrix} = \begin{pmatrix} x \\ y \\ 0 \end{pmatrix} + \begin{pmatrix} 0 \\ 0 \\ z \end{pmatrix},$$
where the first vector belongs to $U$ and the second belongs to $W$.

## 4.2 The Dimension Formula
The dimensions of the sum and intersection are related by an important counting formula.

<!-- page 111 -->

### Theorem 4.5 — Dimension formula for two subspaces
Let $U$ and $W$ be subspaces of a finite-dimensional vector space $V$. Then
$$\dim(U + W) = \dim U + \dim W - \dim(U \cap W).$$

### Proof
Let
$$v_1, \dots, v_r$$
be a basis of
$$U \cap W.$$
Thus
$$\dim(U \cap W) = r.$$
Because
$$v_1, \dots, v_r$$
is linearly independent in $U$, by proposition 3.10 we may extend it to a basis
$$v_1, \dots, v_r, u_1, \dots, u_p$$
of $U$.
Similarly, extend the same basis of $U \cap W$ to a basis
$$v_1, \dots, v_r, w_1, \dots, w_q$$
of $W$.
We claim that
$$v_1, \dots, v_r, u_1, \dots, u_p, w_1, \dots, w_q$$
is a basis of $U + W$.
First, this list spans $U + W$. Indeed, every
$$x \in U + W$$
can be written as
$$x = u + w, \quad u \in U, \quad w \in W.$$
Since the first extended list is a basis of $U$ and the second is a basis of $W$, both $u$ and $w$ are linear combinations of vectors in the displayed list. Hence so is $x$.
It remains to prove linear independence.

<!-- page 112 -->

Suppose
$$\sum_{i=1}^r a_i v_i + \sum_{j=1}^p b_j u_j + \sum_{k=1}^q c_k w_k = 0.$$
Rearranging,
$$\sum_{k=1}^q c_k w_k = -\sum_{i=1}^r a_i v_i - \sum_{j=1}^p b_j u_j.$$
The right-hand side belongs to $U$, whereas the left-hand side belongs to $W$. Therefore
$$\sum_{k=1}^q c_k w_k \in U \cap W.$$
Because
$$v_1, \dots, v_r$$
is a basis of $U \cap W$, there exist scalars $d_1, \dots, d_r$ such that
$$\sum_{k=1}^q c_k w_k = \sum_{i=1}^r d_i v_i.$$
Hence
$$\sum_{i=1}^r d_i v_i - \sum_{k=1}^q c_k w_k = 0.$$
But
$$v_1, \dots, v_r, w_1, \dots, w_q$$
is a basis of $W$, and therefore is linearly independent. Thus
$$c_1 = \dots = c_q = 0.$$
The original relation now reduces to
$$\sum_{i=1}^r a_i v_i + \sum_{j=1}^p b_j u_j = 0.$$
Since
$$v_1, \dots, v_r, u_1, \dots, u_p$$
is a basis of $U$, all the remaining coefficients are zero.
Thus the displayed list is linearly independent and hence is a basis of $U + W$.
Consequently,
$$\dim(U + W) = r + p + q.$$

<!-- page 113 -->

At the same time,
$$\dim U = r + p, \quad \dim W = r + q, \quad \dim(U \cap W) = r.$$
Therefore
$$\dim(U + W) = r + p + q$$
$$= (r + p) + (r + q) - r$$
$$= \dim U + \dim W - \dim(U \cap W).$$

### Remark 4.6 — Analogy with inclusion-exclusion
The formula
$$\dim(U + W) = \dim U + \dim W - \dim(U \cap W)$$
is the vector-space analogue of the counting identity
$$\#(A \cup B) = \#A + \#B - \#(A \cap B)$$
for finite sets.
The common part must be subtracted once because it has been counted in both subspaces.

### Corollary 4.7 — Dimension bound for a sum
Under the assumptions of theorem 4.5,
$$\dim(U + W) \leq \dim U + \dim W,$$
with equality if and only if
$$U \cap W = \{0\}.$$

### Proof
By theorem 4.5,
$$\dim(U + W) = \dim U + \dim W - \dim(U \cap W).$$
Since
$$\dim(U \cap W) \geq 0,$$
the inequality follows.
Equality holds precisely when
$$\dim(U \cap W) = 0,$$

<!-- page 114 -->

which is equivalent to
$$U \cap W = \{0\}.$$

## 4.3 Direct Sums
Every vector in $U + W$ can be written as
$$u + w, \quad u \in U, \quad w \in W.$$
In general, however, this representation need not be unique.
Direct sums are precisely the case in which it is unique.

### Definition 4.8 — Direct sum
Let
$$V_1, \dots, V_m$$
be subspaces of $V$.
Their sum
$$V_1 + \dots + V_m$$
is called a **direct sum** if every vector in the sum has a unique representation
$$v = v_1 + \dots + v_m, \quad v_i \in V_i.$$
In this case we write
$$V_1 \oplus \dots \oplus V_m.$$
Looking at the representation of every vector in a sum to determine whether this sum is direct is simply not feasible. We therefore seek some characterizations of a direct sum.

### Theorem 4.9 — Characterizations of a direct sum
Let
$$V_1, \dots, V_m$$
be finite-dimensional subspaces of $V$, and let
$$S = V_1 + \dots + V_m.$$
Then the following statements are equivalent:
(i)
$$S = V_1 \oplus \dots \oplus V_m.$$

<!-- page 115 -->

(ii) If
$$v_1 + \dots + v_m = 0, \quad v_i \in V_i,$$
then
$$v_1 = \dots = v_m = 0.$$
(iii) For every
$$i = 2, \dots, m,$$
we have
$$V_i \cap (V_1 + \dots + V_{i-1}) = \{0\}.$$
(iv)
$$\dim S = \dim V_1 + \dots + \dim V_m.$$
(v) If $\mathcal{B}_i$ is a basis of $V_i$ for each $i$, then concatenating the lists
$$\mathcal{B}_1, \dots, \mathcal{B}_m$$
gives a basis of $S$.

### Proof
We show the equivalences in several steps.
**(i) $\iff$ (ii).**
Suppose first that the sum is direct. The zero vector already has the representation
$$0 = 0 + \dots + 0.$$
By uniqueness, any representation
$$0 = v_1 + \dots + v_m, \quad v_i \in V_i,$$
must therefore satisfy
$$v_1 = \dots = v_m = 0.$$
Conversely, suppose (ii) holds. Let
$$v = v_1 + \dots + v_m$$
and
$$v = u_1 + \dots + u_m$$

<!-- page 116 -->

be two representations of the same vector, where
$$v_i, u_i \in V_i.$$
Subtracting gives
$$0 = (v_1 - u_1) + \dots + (v_m - u_m).$$
Because
$$v_i - u_i \in V_i,$$
condition (ii) implies
$$v_i - u_i = 0 \quad \text{for every } i.$$
Thus
$$v_i = u_i \quad \text{for every } i,$$
so the representation is unique.
**(ii) $\iff$ (iii).**
Assume (ii). Let
$$x \in V_i \cap (V_1 + \dots + V_{i-1})$$
for some $i \geq 2$. Then
$$x = v_1 + \dots + v_{i-1}$$
for some
$$v_j \in V_j.$$
Hence
$$v_1 + \dots + v_{i-1} - x = 0,$$
where
$$-x \in V_i.$$
By (ii), all these vectors are zero. In particular,
$$x = 0.$$
Thus (iii) holds.
Conversely, assume (iii), and suppose
$$v_1 + \dots + v_m = 0, \quad v_i \in V_i.$$
Then
$$v_m = -(v_1 + \dots + v_{m-1}).$$
Thus
$$v_m \in V_m \cap (V_1 + \dots + V_{m-1}).$$

<!-- page 117 -->

By (iii),
$$v_m = 0.$$
Repeating the same argument with
$$v_1 + \dots + v_{m-1} = 0$$
shows successively that
$$v_{m-1} = 0, \dots, v_1 = 0.$$
Hence (ii) holds.
**(iii) $\iff$ (v).**
For each $i$, let
$$\mathcal{B}_i$$
be a basis of $V_i$. The concatenated list always spans
$$S = V_1 + \dots + V_m.$$
Assume (iii). Suppose a linear combination of the vectors in the concatenated list equals zero. Grouping the terms according to the subspaces gives
$$v_1 + \dots + v_m = 0, \quad v_i \in V_i.$$
By (iii), and hence by (ii),
$$v_1 = \dots = v_m = 0.$$
Because each $\mathcal{B}_i$ is linearly independent, every coefficient in the original linear combination must be zero. Thus the concatenated list is linearly independent and hence is a basis of $S$.
Conversely, if the concatenated list is a basis, suppose
$$v_1 + \dots + v_m = 0, \quad v_i \in V_i.$$
Express each $v_i$ in the basis $\mathcal{B}_i$. This gives a linear combination of the concatenated basis equal to zero. Linear independence then implies that all coefficients are zero, and hence
$$v_i = 0 \quad \text{for every } i.$$
Thus (ii), and therefore (iii), holds.
**(iv) $\iff$ (v).**
The concatenated list
$$\mathcal{B}_1, \dots, \mathcal{B}_m$$

<!-- page 118 -->

spans $S$ and contains exactly
$$\dim V_1 + \dots + \dim V_m$$
vectors.
If (iv) holds, this number equals $\dim S$. By proposition 1.21, a spanning list containing exactly $\dim S$ vectors is a basis of $S$. Thus (v) holds.
Conversely, if the concatenated list is a basis of $S$, the number of vectors in that basis equals $\dim S$. Hence
$$\dim S = \dim V_1 + \dots + \dim V_m.$$
Therefore all five conditions are equivalent.

One common case is the (direct) sum of two subspaces, see the following corollary.

### Corollary 4.10 — Direct sum of two subspaces
Let $U$ and $W$ be subspaces of $V$. Then
$$U + W$$
is a direct sum if and only if
$$U \cap W = \{0\}.$$
Thus
$$U + W = U \oplus W \iff U \cap W = \{0\}.$$

### Proof
This is the case $m = 2$ of theorem 4.9.

### Example 4.11 — A direct-sum decomposition of $\mathbb{R}^3$
Let
$$U = \left\{ \begin{pmatrix} x \\ y \\ 0 \end{pmatrix} : x, y \in \mathbb{R} \right\}, \quad W = \left\{ \begin{pmatrix} 0 \\ 0 \\ z \end{pmatrix} : z \in \mathbb{R} \right\}.$$
Then
$$U + W = \mathbb{R}^3.$$
Moreover,
$$U \cap W = \{0\}.$$

<!-- page 119 -->

Hence, by corollary 4.10,
$$\mathbb{R}^3 = U \oplus W.$$
Thus every vector has the unique decomposition
$$\begin{pmatrix} x \\ y \\ z \end{pmatrix} = \begin{pmatrix} x \\ y \\ 0 \end{pmatrix} + \begin{pmatrix} 0 \\ 0 \\ z \end{pmatrix}.$$

### Definition 4.12 — Complementary subspace
Let $U$ be a subspace of $V$.
A subspace $W$ of $V$ is called a **complement** of $U$ if
$$V = U \oplus W.$$

### Proposition 4.13 — Every subspace has a complement
Let $V$ be finite-dimensional and let $U$ be a subspace of $V$. Then $U$ has a complement in $V$.

### Proof
Let
$$u_1, \dots, u_r$$
be a basis of $U$.
By proposition 3.10, extend this basis to a basis
$$u_1, \dots, u_r, w_1, \dots, w_s$$
of $V$.
Define
$$W = \text{Span}(w_1, \dots, w_s).$$
Because the displayed list spans $V$,
$$V = U + W.$$
Suppose
$$x \in U \cap W.$$

<!-- page 120 -->

Then $x$ can be written both as a linear combination of
$$u_1, \dots, u_r$$
and as a linear combination of
$$w_1, \dots, w_s.$$
Subtracting these two representations gives a linear relation among
$$u_1, \dots, u_r, w_1, \dots, w_s.$$
Since this list is a basis of $V$, it is linearly independent. Hence all coefficients are zero, so
$$x = 0.$$
Therefore
$$U \cap W = \{0\}.$$
By corollary 4.10,
$$V = U \oplus W.$$
Thus $W$ is a complement of $U$.

### Remark 4.14 — Complements are generally not unique
A subspace may have many different complements. The proposition asserts existence, not uniqueness.

## 4.4 Invariant Subspaces
Direct sums allow us to decompose a vector space into smaller pieces. For a linear transformation
$$T : V \to V,$$
we would like these pieces to be compatible with $T$.
This leads to the notion of an invariant subspace.

### Definition 4.15 — Invariant subspace
Let
$$T : V \to V$$
be a linear transformation.

<!-- page 121 -->

A subspace $U$ of $V$ is called **invariant under $T$**, or **$T$-invariant**, if
$$T(u) \in U \quad \text{for every } u \in U.$$
Equivalently,
$$T(U) \subseteq U.$$

If $U$ is invariant under $T$, then the restriction
$$T|_U : U \to U$$
is itself a linear transformation on the smaller vector space $U$. Thus we can study part of the behavior of $T$ by studying the simpler operator $T|_U$.

**Proposition 4.16 — Basic invariant subspaces**
Let
$$T : V \to V$$
be a linear transformation. Then each of the following is invariant under $T$:
$$\{0\}, \quad V, \quad \ker T, \quad \operatorname{Im} T.$$

**Proof**
The subspaces $\{0\}$ and $V$ are immediate.
If
$$u \in \ker T,$$
then
$$T(u) = 0.$$
Since
$$0 \in \ker T,$$
we have
$$T(u) \in \ker T.$$
Thus $\ker T$ is invariant.
Now let
$$u \in \operatorname{Im} T.$$
Then there exists some $v \in V$ such that
$$u = T(v).$$

<!-- page 122 -->

Hence
$$T(u) = T(T(v)).$$
This is itself the image under $T$ of the vector $T(v) \in V$, so
$$T(u) \in \operatorname{Im} T.$$
Therefore $\operatorname{Im} T$ is invariant.

**Example 4.17 — Differentiation and polynomial subspaces**
Let
$$T : \mathbb{R}[x] \to \mathbb{R}[x]$$
be differentiation:
$$T(p) = p'.$$
For every nonnegative integer $n$, the subspace
$$\mathbb{R}_n[x]$$
is invariant under $T$, because
$$p \in \mathbb{R}_n[x] \implies p' \in \mathbb{R}_n[x].$$
Thus differentiation on the infinite-dimensional space $\mathbb{R}[x]$ can be restricted to a linear transformation
$$T|_{\mathbb{R}_n[x]} : \mathbb{R}_n[x] \to \mathbb{R}_n[x].$$

**Proposition 4.18 — Sums and intersections of invariant subspaces**
Let
$$T : V \to V$$
be a linear transformation, and let $U$ and $W$ be invariant under $T$. Then
$$U \cap W \quad \text{and} \quad U + W$$
are also invariant under $T$.

<!-- page 123 -->

**Proof**
Let
$$x \in U \cap W.$$
Since $U$ and $W$ are both invariant,
$$T(x) \in U \quad \text{and} \quad T(x) \in W.$$
Therefore
$$T(x) \in U \cap W.$$
Thus $U \cap W$ is invariant.
Now let
$$x \in U + W.$$
Then
$$x = u + w$$
for some
$$u \in U, \quad w \in W.$$
By linearity,
$$T(x) = T(u) + T(w).$$
Because $U$ and $W$ are invariant,
$$T(u) \in U, \quad T(w) \in W.$$
Hence
$$T(x) \in U + W.$$
Thus $U + W$ is invariant.

**4.5 Invariant Subspaces and the Matrix of a Linear Transformation**
The usefulness of invariant subspaces becomes especially clear when we choose a basis adapted to them.

**Proposition 4.19 — Invariant subspace and block upper-triangular form**
Let
$$T : V \to V$$
be a linear transformation on a finite-dimensional vector space, and let $U$ be invariant under $T$.

<!-- page 124 -->

Let
$$u_1, \dots, u_r$$
be a basis of $U$, and extend it, using proposition 3.10, to a basis
$$\mathcal{E} = (u_1, \dots, u_r, w_1, \dots, w_s)$$
of $V$.
Then the matrix of $T$ with respect to $\mathcal{E}$ has the block form
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}} = \begin{pmatrix} A & B \\ 0 & C \end{pmatrix},$$
where
$$A = [T|_U]_{(u_1, \dots, u_r) \leftarrow (u_1, \dots, u_r)}.$$

**Proof**
Because $U$ is invariant under $T$,
$$T(u_j) \in U \quad \text{for } j = 1, \dots, r.$$
Hence each $T(u_j)$ is a linear combination only of
$$u_1, \dots, u_r.$$
Therefore the coordinate vectors
$$[T(u_j)]_{\mathcal{E}}, \quad j = 1, \dots, r,$$
have zero entries in their last $s$ positions.
Recall that these coordinate vectors form the first $r$ columns of
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}}.$$
Hence the lower-left block is zero, and the matrix has the form
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}} = \begin{pmatrix} A & B \\ 0 & C \end{pmatrix}.$$
The upper-left block records the action of $T$ on the basis
$$u_1, \dots, u_r$$

<!-- page 125 -->

of $U$, and hence it is precisely the matrix of the restricted transformation
$$T|_U : U \to U.$$
If the whole space decomposes into invariant subspaces, the matrix simplifies further.

**Corollary 4.20 — Invariant direct sums and block-diagonal matrices**
Suppose
$$V = U \oplus W$$
and both $U$ and $W$ are invariant under
$$T : V \to V.$$
Choose bases
$$\mathcal{B}_U = (u_1, \dots, u_r)$$
of $U$ and
$$\mathcal{B}_W = (w_1, \dots, w_s)$$
of $W$.
Then
$$\mathcal{E} = (u_1, \dots, u_r, w_1, \dots, w_s)$$
is a basis of $V$, and
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}} = \begin{pmatrix} [T|_U]_{\mathcal{B}_U \leftarrow \mathcal{B}_U} & 0 \\ 0 & [T|_W]_{\mathcal{B}_W \leftarrow \mathcal{B}_W} \end{pmatrix}.$$

**Proof**
By theorem 4.9, concatenating bases of $U$ and $W$ gives a basis of $V$.
Since $U$ is invariant, the lower-left block is zero by proposition 4.19.
Since $W$ is also invariant,
$$T(w_j) \in W \quad \text{for every } j,$$
so the coordinates of $T(w_j)$ along
$$u_1, \dots, u_r$$
are zero. Hence the upper-right block is also zero.
Therefore the matrix is block diagonal.

<!-- page 126 -->

**Remark 4.21 — Why invariant decompositions matter**
If
$$V = U \oplus W$$
with both $U$ and $W$ invariant under $T$, then the study of $T$ splits into two smaller problems:
$$T|_U : U \to U \quad \text{and} \quad T|_W : W \to W.$$
The block-diagonal matrix
$$\begin{pmatrix} A & 0 \\ 0 & C \end{pmatrix}$$
is the coordinate expression of this decomposition.
More generally, if
$$V = V_1 \oplus \dots \oplus V_m$$
and every $V_i$ is invariant under $T$, then a basis obtained by concatenating bases of the $V_i$ gives a block-diagonal matrix for $T$.

The simplest nonzero invariant subspaces are one-dimensional.

**Proposition 4.22 — One-dimensional invariant subspaces**
Let
$$T : V \to V$$
be a linear transformation and let
$$v \in V, \quad v \neq 0.$$
Then the one-dimensional subspace
$$\operatorname{Span}(v)$$
is invariant under $T$ if and only if there exists a scalar
$$\lambda \in \mathbb{K}$$
such that
$$T(v) = \lambda v.$$

**Proof**
Suppose first that
$$\operatorname{Span}(v)$$

<!-- page 127 -->

is invariant under $T$. Then
$$T(v) \in \operatorname{Span}(v).$$
By the definition of span, there exists
$$\lambda \in \mathbb{K}$$
such that
$$T(v) = \lambda v.$$
Conversely, suppose
$$T(v) = \lambda v.$$
Every vector in $\operatorname{Span}(v)$ has the form
$$cv$$
for some $c \in \mathbb{K}$. By linearity,
$$T(cv) = cT(v) = c\lambda v \in \operatorname{Span}(v).$$
Hence
$$\operatorname{Span}(v)$$
is invariant under $T$.

**Remark 4.23 — From invariant subspaces to eigenvalues**
The equation
$$T(v) = \lambda v, \quad v \neq 0,$$
says that $T$ does not change the direction spanned by $v$: it only rescales vectors along that direction.
Thus one-dimensional invariant subspaces are exactly the directions on which $T$ acts by scalar multiplication.
This observation leads directly to the concepts of **eigenvalues** and **eigenvectors**, which we study later in the course.

<!-- page 128 -->

**5 Determinants**
Before going into eigenvalues and eigen vectors, let us turn back to square matrices for a moment. We have already developed several ways to understand the structure of a square matrix. In particular, by corollary 3.57, for
$$A \in \mathbb{K}^{n \times n},$$
the following conditions are equivalent:
$$A \text{ is invertible}, \quad \operatorname{Rank}(A) = n, \quad \ker A = \{0\}.$$
We now introduce another quantity associated with a square matrix: a single scalar
$$\det(A) \in \mathbb{K}$$
called its **determinant**.
The determinant will eventually give another criterion for invertibility:
$$A \text{ is invertible} \iff \det(A) \neq 0.$$
It will also play a central role in the study of eigenvalues, where we will encounter expressions of the form
$$\det(A - \lambda I).$$
Rather than beginning with a complicated formula, we first ask: *what properties should the determinant have?*

**5.1 The Determinant and Its Defining Properties**
Let
$$A = \begin{pmatrix} | & & | \\ a_1 & \dots & a_n \\ | & & | \end{pmatrix} \in \mathbb{K}^{n \times n},$$
where
$$a_1, \dots, a_n \in \mathbb{K}^n$$
are the columns of $A$.
We will often write
$$\det(A) = \det(a_1, \dots, a_n)$$
to emphasize that the determinant is a function of the columns of the matrix.
The determinant is characterized by three fundamental properties: linearity in each column, alternation, and normalization.

<!-- page 129 -->

**Definition 5.1 — Multilinear and alternating functions**
Let
$$D : (\mathbb{K}^n)^n \to \mathbb{K}$$
be a function of $n$ vector arguments.
We say that $D$ is **multilinear** if it is linear in each argument when all the other arguments are held fixed. Thus, for every $j = 1, \dots, n$,
$$D(a_1, \dots, a_{j-1}, \alpha u + \beta v, a_{j+1}, \dots, a_n)$$
$$= \alpha D(a_1, \dots, a_{j-1}, u, a_{j+1}, \dots, a_n)$$
$$+ \beta D(a_1, \dots, a_{j-1}, v, a_{j+1}, \dots, a_n).$$
We say that $D$ is **alternating** if the value of $D$ is zero whenever any two of its arguments are equal.
More precisely, if
$$a_i = a_j$$
for some distinct indices
$$i, j \in \{1, \dots, n\}, \quad i \neq j,$$
then
$$D(a_1, \dots, a_n) = 0.$$
The following proposition is a direct consequence of alternation.

**Proposition 5.2 — Alternation implies sign change under interchange**
Let
$$D : (\mathbb{K}^n)^n \to \mathbb{K}$$
be multilinear and alternating. Interchanging two arguments changes the sign of $D$.
More precisely, if $i \neq j$, then
$$D(a_1, \dots, a_i, \dots, a_j, \dots, a_n) = -D(a_1, \dots, a_j, \dots, a_i, \dots, a_n).$$

**Proof**
It is enough to focus on the two positions being interchanged and keep all other arguments fixed.
Because $D$ is alternating, putting the same vector $a_i + a_j$ into both positions gives
$$D(\dots, a_i + a_j, \dots, a_i + a_j, \dots) = 0.$$

<!-- page 130 -->

By multilinearity,
$$0 = D(\dots, a_i, \dots, a_i, \dots) + D(\dots, a_i, \dots, a_j, \dots)$$
$$+ D(\dots, a_j, \dots, a_i, \dots) + D(\dots, a_j, \dots, a_j, \dots).$$
The first and last terms vanish because $D$ is alternating. Therefore
$$D(\dots, a_i, \dots, a_j, \dots) + D(\dots, a_j, \dots, a_i, \dots) = 0.$$
Hence
$$D(\dots, a_i, \dots, a_j, \dots) = -D(\dots, a_j, \dots, a_i, \dots).$$
Thus alternation captures the familiar idea that interchanging two columns reverses the sign of the determinant.
To state an explicit formula for the determinant, we need a small amount of notation concerning permutations.

**Definition 5.3 — Permutations and their signs**
A **permutation** of
$$\{1, \dots, n\}$$
is a bijection
$$\sigma : \{1, \dots, n\} \to \{1, \dots, n\}.$$
The set of all such permutations is denoted by
$$S_n.$$
An **inversion** of $\sigma$ is a pair
$$i < j$$
such that
$$\sigma(i) > \sigma(j).$$
If $\operatorname{inv}(\sigma)$ denotes the number of inversions of $\sigma$, the **sign** of $\sigma$ is
$$\operatorname{sgn}(\sigma) = (-1)^{\operatorname{inv}(\sigma)}.$$
Thus
$$\operatorname{sgn}(\sigma) = \begin{cases} 1, & \sigma \text{ has an even number of inversions}, \\ -1, & \sigma \text{ has an odd number of inversions}. \end{cases}$$

<!-- page 131 -->

For example, the identity permutation
$$\sigma(i) = i$$
has no inversions, so
$$\operatorname{sgn}(\sigma) = 1.$$
Interchanging two elements of a permutation changes its sign. Thus, if $\tau$ is obtained from $\sigma$ by interchanging two positions, then
$$\operatorname{sgn}(\tau) = -\operatorname{sgn}(\sigma).$$
We can now state the fundamental theorem that defines the determinant.

**Theorem 5.4 — Existence and uniqueness of the determinant**
There exists a unique function
$$\det : (\mathbb{K}^n)^n \to \mathbb{K}$$
satisfying the following three properties:
(1) **Multilinearity.**
The determinant is linear in each column separately.
(2) **Alternation.**
If two columns are equal, then
$$\det(a_1, \dots, a_n) = 0.$$
(3) **Normalization.**
For the standard basis
$$e_1, \dots, e_n$$
of $\mathbb{K}^n$,
$$\det(e_1, \dots, e_n) = 1.$$
Equivalently,
$$\det(I_n) = 1.$$
For
$$A = (a_{ij}) \in \mathbb{K}^{n \times n},$$
this unique function is given explicitly by
$$\det(A) = \sum_{\sigma \in S_n} \operatorname{sgn}(\sigma) \prod_{j=1}^n a_{\sigma(j), j}.$$

<!-- page 132 -->

**Proof**
We prove existence and uniqueness separately.
**Existence.**
For
$$A = (a_{ij}) \in \mathbb{K}^{n \times n},$$
define
$$D(A) = \sum_{\sigma \in S_n} \operatorname{sgn}(\sigma) \prod_{j=1}^n a_{\sigma(j), j}.$$
We verify that $D$ has the three stated properties.
First, $D$ is multilinear in the columns.
Fix a column $j$. In every term
$$\operatorname{sgn}(\sigma) \prod_{k=1}^n a_{\sigma(k), k},$$
exactly one factor,
$$a_{\sigma(j), j},$$
comes from column $j$.
Thus, if the $j$th column is replaced by
$$\alpha u + \beta v,$$
each term in the sum separates linearly into an $\alpha$-term and a $\beta$-term. Therefore
$$D(a_1, \dots, \alpha u + \beta v, \dots, a_n)$$
$$= \alpha D(a_1, \dots, u, \dots, a_n) + \beta D(a_1, \dots, v, \dots, a_n).$$
Hence $D$ is multilinear.
Second, $D$ is alternating.
Suppose columns $r$ and $s$, with $r \neq s$, are equal.
For every permutation $\sigma \in S_n$, let $\tau$ be the permutation obtained by interchanging the values of $\sigma$ at positions $r$ and $s$. Then
$$\operatorname{sgn}(\tau) = -\operatorname{sgn}(\sigma).$$
Because columns $r$ and $s$ are equal, the products associated with $\sigma$ and $\tau$ are identical:
$$\prod_{j=1}^n a_{\sigma(j), j} = \prod_{j=1}^n a_{\tau(j), j}.$$

<!-- page 133 -->

Their contributions to $D(A)$ therefore cancel:
$$\text{sgn}(\sigma) \prod_{j=1}^n a_{\sigma(j),j} + \text{sgn}(\tau) \prod_{j=1}^n a_{\tau(j),j} = 0.$$
The permutations can be paired in this way, so
$$D(A) = 0.$$
Thus $D$ is alternating.
Third, consider the identity matrix
$$I_n.$$
In the sum
$$D(I_n) = \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n (I_n)_{\sigma(j),j},$$
the product is nonzero only when
$$\sigma(j) = j \quad \text{for every } j.$$
Thus only the identity permutation contributes.
Since the identity permutation has sign 1,
$$D(I_n) = 1.$$
Therefore a function satisfying the three required properties exists.

**Uniqueness.**
Now suppose
$$D : (\mathbb{K}^n)^n \to \mathbb{K}$$
is any multilinear, alternating function satisfying
$$D(e_1, \dots, e_n) = 1.$$
Let
$$A = \begin{pmatrix} | & & | \\ a_1 & \dots & a_n \\ | & & | \end{pmatrix},$$
where
$$a_j = \sum_{i=1}^n a_{ij}e_i.$$

<!-- page 134 -->

Using multilinearity in every column,
$$D(a_1, \dots, a_n) = D\left(\sum_{i_1=1}^n a_{i_1 1}e_{i_1}, \dots, \sum_{i_n=1}^n a_{i_n n}e_{i_n}\right)$$
$$= \sum_{i_1=1}^n \dots \sum_{i_n=1}^n a_{i_1 1} \dots a_{i_n n} D(e_{i_1}, \dots, e_{i_n}).$$
If two of the indices
$$i_1, \dots, i_n$$
are equal, then two arguments of $D$ are equal. By alternation,
$$D(e_{i_1}, \dots, e_{i_n}) = 0.$$
Therefore the only nonzero terms are those for which
$$i_1, \dots, i_n$$
are all distinct.
Because there are $n$ distinct indices chosen from
$$\{1, \dots, n\},$$
such a choice must be a permutation of
$$1, \dots, n.$$
Hence there exists
$$\sigma \in S_n$$
such that
$$i_j = \sigma(j) \quad \text{for } j = 1, \dots, n.$$
Thus
$$D(a_1, \dots, a_n) = \sum_{\sigma \in S_n} \left(\prod_{j=1}^n a_{\sigma(j),j}\right) D(e_{\sigma(1)}, \dots, e_{\sigma(n)}).$$
By proposition 5.2, every interchange of two arguments changes the sign of $D$. Therefore, rearranging
$$e_{\sigma(1)}, \dots, e_{\sigma(n)}$$
into
$$e_1, \dots, e_n$$

<!-- page 135 -->

gives
$$D(e_{\sigma(1)}, \dots, e_{\sigma(n)}) = \text{sgn}(\sigma)D(e_1, \dots, e_n).$$
Since
$$D(e_1, \dots, e_n) = 1,$$
we obtain
$$D(e_{\sigma(1)}, \dots, e_{\sigma(n)}) = \text{sgn}(\sigma).$$
Consequently,
$$D(A) = \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n a_{\sigma(j),j}.$$
Thus every function satisfying multilinearity, alternation, and normalization must equal the function constructed above. Hence the determinant is unique.

**Definition 5.5 — Determinant**
Let
$$A = \begin{pmatrix} | & & | \\ a_1 & \dots & a_n \\ | & & | \end{pmatrix} \in \mathbb{K}^{n \times n}.$$
The **determinant** of $A$, denoted by
$$\det(A) \quad \text{or simply} \quad \det A,$$
is the unique scalar-valued function of the columns of $A$ that
(1) multilinear;
(2) alternating;
(3) normalized by
$$\det(I_n) = 1.$$
Equivalently,
$$\det(A) = \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n a_{\sigma(j),j}.$$
Although the explicit permutation formula gives a complete formula for the determinant, in practice we will rarely compute determinants directly from this formula. Its main role is to establish the existence of the determinant.
The three defining properties—multilinearity, alternation, and normalization—are much more useful for understanding and manipulating determinants.

<!-- page 136 -->

**Example 5.6 — Determinants in dimensions one and two**
For a $1 \times 1$ matrix
$$A = (a),$$
there is only one permutation, so
$$\det(A) = a.$$
For a $2 \times 2$ matrix
$$A = \begin{pmatrix} a & b \\ c & d \end{pmatrix},$$
there are two permutations of $\{1, 2\}$.
The identity permutation contributes
$$ad,$$
whereas the permutation that interchanges 1 and 2 contributes
$$-bc.$$
Therefore
$$\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc.$$

**5.2 Basic Properties of Determinants**
The defining properties of the determinant immediately imply a number of useful computational rules.
Let
$$A = \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1n} \\ a_{21} & a_{22} & \dots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ a_{n1} & a_{n2} & \dots & a_{nn} \end{pmatrix} = \begin{pmatrix} | & | & & | \\ a_1 & a_2 & \dots & a_n \\ | & | & & | \end{pmatrix} \in \mathbb{K}^{n \times n}.$$
Thus
$$\det(A) = \det(a_1, \dots, a_n).$$
We begin with the consequences of multilinearity.

**Proposition 5.7 — Linearity in each column**
Fix all columns of a determinant except the $j$th column. Then the determinant is linear in the $j$th column. In particular:

<!-- page 137 -->

(1) If the $j$th column is multiplied by a scalar $c \in \mathbb{K}$, then the determinant is multiplied by $c$:
$$\det(a_1, \dots, ca_j, \dots, a_n) = c \det(a_1, \dots, a_j, \dots, a_n).$$
In matrix form,
$$\det \begin{pmatrix} a_{11} & \dots & ca_{1j} & \dots & a_{1n} \\ a_{21} & \dots & ca_{2j} & \dots & a_{2n} \\ \vdots & & \vdots & & \vdots \\ a_{n1} & \dots & ca_{nj} & \dots & a_{nn} \end{pmatrix} = c \det \begin{pmatrix} a_{11} & \dots & a_{1j} & \dots & a_{1n} \\ a_{21} & \dots & a_{2j} & \dots & a_{2n} \\ \vdots & & \vdots & & \vdots \\ a_{n1} & \dots & a_{nj} & \dots & a_{nn} \end{pmatrix}.$$
(2) If the $j$th column is the sum of two vectors,
$$a_j = u + v,$$
then the determinant splits as
$$\det(a_1, \dots, u + v, \dots, a_n) = \det(a_1, \dots, u, \dots, a_n) + \det(a_1, \dots, v, \dots, a_n).$$
Writing
$$u = \begin{pmatrix} u_1 \\ u_2 \\ \vdots \\ u_n \end{pmatrix}, \quad v = \begin{pmatrix} v_1 \\ v_2 \\ \vdots \\ v_n \end{pmatrix},$$
this becomes
$$\det \begin{pmatrix} a_{11} & \dots & u_1 + v_1 & \dots & a_{1n} \\ a_{21} & \dots & u_2 + v_2 & \dots & a_{2n} \\ \vdots & & \vdots & & \vdots \\ a_{n1} & \dots & u_n + v_n & \dots & a_{nn} \end{pmatrix}$$
$$= \det \begin{pmatrix} a_{11} & \dots & u_1 & \dots & a_{1n} \\ a_{21} & \dots & u_2 & \dots & a_{2n} \\ \vdots & & \vdots & & \vdots \\ a_{n1} & \dots & u_n & \dots & a_{nn} \end{pmatrix} + \det \begin{pmatrix} a_{11} & \dots & v_1 & \dots & a_{1n} \\ a_{21} & \dots & v_2 & \dots & a_{2n} \\ \vdots & & \vdots & & \vdots \\ a_{n1} & \dots & v_n & \dots & a_{nn} \end{pmatrix}.$$
(3) If the $j$th column is the zero vector, then the determinant is zero:
$$\det(a_1, \dots, 0, \dots, a_n) = 0.$$

<!-- page 138 -->

In matrix form,
$$\det \begin{pmatrix} a_{11} & \dots & 0 & \dots & a_{1n} \\ a_{21} & \dots & 0 & \dots & a_{2n} \\ \vdots & & \vdots & & \vdots \\ a_{n1} & \dots & 0 & \dots & a_{nn} \end{pmatrix} = 0.$$

**Proof**
The first two statements are precisely the multilinearity property in theorem 5.4.
For the third statement, write the zero column as
$$0 = 0_{\mathbb{K}}a_j.$$
By linearity in the $j$th column,
$$\det(a_1, \dots, 0, \dots, a_n) = 0_{\mathbb{K}} \det(a_1, \dots, a_j, \dots, a_n) = 0.$$

**Remark 5.8 — The determinant is not linear in the whole matrix**
Linearity in each column separately does *not* mean that
$$\det(A + B) = \det(A) + \det(B).$$
For example, take
$$A = B = I_2.$$
Then
$$A + B = 2I_2 = \begin{pmatrix} 2 & 0 \\ 0 & 2 \end{pmatrix},$$
so
$$\det(A + B) = \det \begin{pmatrix} 2 & 0 \\ 0 & 2 \end{pmatrix} = 4,$$
whereas
$$\det(A) + \det(B) = 1 + 1 = 2.$$
Thus
$$\det(A + B) \neq \det(A) + \det(B)$$
in general.
Multilinearity means that the determinant is linear when *one column at a time* is varied while all other columns are held fixed.

<!-- page 139 -->

We now turn to the consequences of alternation.

**Proposition 5.9 — Interchanging two columns**
If two columns of a matrix are interchanged, then the determinant changes sign.
More precisely, if the $i$th and $j$th columns are interchanged, where $i \neq j$, then
$$\det(a_1, \dots, a_i, \dots, a_j, \dots, a_n) = -\det(a_1, \dots, a_j, \dots, a_i, \dots, a_n).$$
For example,
$$\det \begin{pmatrix} a_{11} & a_{12} & a_{13} & \dots & a_{1n} \\ a_{21} & a_{22} & a_{23} & \dots & a_{2n} \\ \vdots & \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & a_{n3} & \dots & a_{nn} \end{pmatrix}$$
becomes, after interchanging the first two columns,
$$\det \begin{pmatrix} a_{12} & a_{11} & a_{13} & \dots & a_{1n} \\ a_{22} & a_{21} & a_{23} & \dots & a_{2n} \\ \vdots & \vdots & \vdots & & \vdots \\ a_{n2} & a_{n1} & a_{n3} & \dots & a_{nn} \end{pmatrix},$$
and
$$\det \begin{pmatrix} a_{12} & a_{11} & a_{13} & \dots & a_{1n} \\ a_{22} & a_{21} & a_{23} & \dots & a_{2n} \\ \vdots & \vdots & \vdots & & \vdots \\ a_{n2} & a_{n1} & a_{n3} & \dots & a_{nn} \end{pmatrix} = -\det \begin{pmatrix} a_{11} & a_{12} & a_{13} & \dots & a_{1n} \\ a_{21} & a_{22} & a_{23} & \dots & a_{2n} \\ \vdots & \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & a_{n3} & \dots & a_{nn} \end{pmatrix}.$$

**Proof**
This is exactly proposition 5.2, applied to the determinant, which is alternating and multilinear by theorem 5.4.

**Corollary 5.10 — Equal or proportional columns**
If two columns of a square matrix are equal, then its determinant is zero.
More generally, if two columns are proportional, then its determinant is zero.

<!-- page 140 -->

**Proof**
Suppose first that
$$a_i = a_j$$
for some $i \neq j$. Then the alternating property in theorem 5.4 gives immediately
$$\det(A) = 0.$$
Now suppose that the two columns are proportional:
$$a_j = ca_i$$
for some $c \in \mathbb{K}$.
By proposition 5.7,
$$\det(a_1, \dots, a_i, \dots, ca_i, \dots, a_n) = c \det(a_1, \dots, a_i, \dots, a_i, \dots, a_n)$$
$$= 0,$$
because the determinant on the right has two equal columns.
For example,
$$\det \begin{pmatrix} a_{11} & ca_{11} & a_{13} & \dots & a_{1n} \\ a_{21} & ca_{21} & a_{23} & \dots & a_{2n} \\ \vdots & \vdots & \vdots & & \vdots \\ a_{n1} & ca_{n1} & a_{n3} & \dots & a_{nn} \end{pmatrix} = 0.$$
The combination of multilinearity and alternation gives another especially important rule.

**Proposition 5.11 — Adding a multiple of one column to another**
Adding a scalar multiple of one column to a different column does not change the determinant.
More precisely, if
$$i \neq j$$
and $c \in \mathbb{K}$, then
$$\det(a_1, \dots, a_j + ca_i, \dots, a_n) = \det(a_1, \dots, a_j, \dots, a_n).$$
In matrix form, for example, adding $c$ times the first column to the second column gives
$$\det \begin{pmatrix} a_{11} & a_{12} + ca_{11} & a_{13} & \dots & a_{1n} \\ a_{21} & a_{22} + ca_{21} & a_{23} & \dots & a_{2n} \\ \vdots & \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} + ca_{n1} & a_{n3} & \dots & a_{nn} \end{pmatrix} = \det \begin{pmatrix} a_{11} & a_{12} & a_{13} & \dots & a_{1n} \\ a_{21} & a_{22} & a_{23} & \dots & a_{2n} \\ \vdots & \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & a_{n3} & \dots & a_{nn} \end{pmatrix}.$$

<!-- page 141 -->

**Proof**
By multilinearity in the $j$th column,
$$\det(a_1, \dots, a_j + ca_i, \dots, a_n)$$
$$= \det(a_1, \dots, a_j, \dots, a_n) + c \det(a_1, \dots, a_i, \dots, a_i, \dots, a_n).$$
The second determinant contains the same column $a_i$ in two different positions. By the alternating property in theorem 5.4, it is zero. Hence
$$\det(a_1, \dots, a_j + ca_i, \dots, a_n) = \det(a_1, \dots, a_j, \dots, a_n).$$
The preceding result has an important strengthening. It is not only proportional columns that force the determinant to vanish; any linear dependence among the columns does so.

**Proposition 5.12 — Linearly dependent columns imply zero determinant**
If the columns
$$a_1, \dots, a_n$$
of a square matrix $A$ are linearly dependent, then
$$\det(A) = 0.$$

**Proof**
Suppose
$$a_1, \dots, a_n$$
are linearly dependent. By proposition 1.12, one of the columns can be written as a linear combination of the others.
Without loss of generality, suppose
$$a_n = c_1 a_1 + \dots + c_{n-1} a_{n-1}.$$
Then
$$A = \begin{pmatrix} | & | & & | \\ a_1 & a_2 & \dots & a_n \\ | & | & & | \end{pmatrix} = \begin{pmatrix} | & | & & | \\ a_1 & a_2 & \dots & c_1 a_1 + \dots + c_{n-1} a_{n-1} \\ | & | & & | \end{pmatrix}.$$

<!-- page 142 -->

By multilinearity in the last column,
$$\det(A) = c_1 \det(a_1, a_2, \dots, a_{n-1}, a_1)$$
$$+ c_2 \det(a_1, a_2, \dots, a_{n-1}, a_2)$$
$$+ \dots + c_{n-1} \det(a_1, a_2, \dots, a_{n-1}, a_{n-1}).$$
Every determinant on the right contains two equal columns. Hence, by the alternating property,
$$\det(a_1, a_2, \dots, a_{n-1}, a_j) = 0 \quad \text{for every } j = 1, \dots, n-1.$$
Therefore
$$\det(A) = 0.$$

**Remark 5.13 — What has been proved so far**
We have proved the implication
$$a_1, \dots, a_n \text{ linearly dependent} \implies \det(A) = 0.$$
Equivalently,
$$\det(A) \neq 0 \implies a_1, \dots, a_n \text{ are linearly independent.}$$
We will later prove the converse and obtain the fundamental equivalence
$$\det(A) \neq 0 \iff \text{Rank}(A) = n \iff A \text{ is invertible.}$$
So far the defining properties have been stated in terms of columns. The next result shows that the determinant treats rows and columns symmetrically.

**Theorem 5.14 — Determinant of the transpose**
For every square matrix
$$A \in \mathbb{K}^{n \times n},$$
we have
$$\det(A^\top) = \det(A).$$

**Proof**
Let
$$A = (a_{ij}).$$

<!-- page 143 -->

By the explicit determinant formula in theorem 5.4,
$$\det(A^\top) = \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n (A^\top)_{\sigma(j),j}.$$
Since
$$(A^\top)_{\sigma(j),j} = a_{j,\sigma(j)},$$
we obtain
$$\det(A^\top) = \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n a_{j,\sigma(j)}.$$
Now set
$$\tau = \sigma^{-1}.$$
As $\sigma$ ranges over $S_n$, so does $\tau$.
Moreover,
$$\text{sgn}(\sigma^{-1}) = \text{sgn}(\sigma).$$
Indeed, the inversions of $\sigma$ are in one-to-one correspondence with the inversions of $\sigma^{-1}$: if
$$i < j \quad \text{and} \quad \sigma(i) > \sigma(j),$$
then
$$\sigma(j) < \sigma(i)$$
and
$$\sigma^{-1}(\sigma(j)) = j > i = \sigma^{-1}(\sigma(i)).$$
Hence $\sigma$ and $\sigma^{-1}$ have the same number of inversions and therefore the same sign.
Finally, using
$$\tau = \sigma^{-1},$$
we can reindex the product:
$$\prod_{j=1}^n a_{j,\sigma(j)} = \prod_{k=1}^n a_{\tau(k),k}.$$
Therefore
$$\det(A^\top) = \sum_{\tau \in S_n} \text{sgn}(\tau) \prod_{k=1}^n a_{\tau(k),k}$$
$$= \det(A),$$
where the final equality again follows from theorem 5.4.
The transpose theorem allows every property proved for columns to be translated immediately into the corresponding property for rows.

<!-- page 144 -->

**Corollary 5.15 — The corresponding row properties**
Let
$$A \in \mathbb{K}^{n \times n}.$$
Then:
(1) If one row is zero, then
$$\det(A) = 0.$$
(2) Multiplying one row by $c \in \mathbb{K}$ multiplies the determinant by $c$.
Thus, for example,
$$\det \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1n} \\ \vdots & \vdots & & \vdots \\ ca_{i1} & ca_{i2} & \dots & ca_{in} \\ \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & \dots & a_{nn} \end{pmatrix} = c \det \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1n} \\ \vdots & \vdots & & \vdots \\ a_{i1} & a_{i2} & \dots & a_{in} \\ \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & \dots & a_{nn} \end{pmatrix}.$$
(3) Interchanging two rows changes the sign of the determinant.
For example,
$$\det \begin{pmatrix} a_{21} & a_{22} & \dots & a_{2n} \\ a_{11} & a_{12} & \dots & a_{1n} \\ a_{31} & a_{32} & \dots & a_{3n} \\ \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & \dots & a_{nn} \end{pmatrix} = -\det \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1n} \\ a_{21} & a_{22} & \dots & a_{2n} \\ a_{31} & a_{32} & \dots & a_{3n} \\ \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & \dots & a_{nn} \end{pmatrix}.$$
(4) If two rows are equal or proportional, then
$$\det(A) = 0.$$
(5) Adding a scalar multiple of one row to another row does not change the determinant.
For example,
$$\det \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1n} \\ a_{21} + ca_{11} & a_{22} + ca_{12} & \dots & a_{2n} + ca_{1n} \\ a_{31} & a_{32} & \dots & a_{3n} \\ \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & \dots & a_{nn} \end{pmatrix} = \det \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1n} \\ a_{21} & a_{22} & \dots & a_{2n} \\ a_{31} & a_{32} & \dots & a_{3n} \\ \vdots & \vdots & & \vdots \\ a_{n1} & a_{n2} & \dots & a_{nn} \end{pmatrix}.$$

<!-- page 145 -->

**Proof**

By theorem 5.14,
$$\det(A^\top) = \det(A).$$
The rows of $A$ are the columns of $A^\top$. Therefore each statement follows by applying the corresponding column result to $A^\top$ and then transposing back.
Specifically, the assertions follow from propositions 5.7, 5.9 and 5.11 and corollary 5.10.

We conclude with an important class of matrices whose determinant can be read directly from their entries.

**Theorem 5.16 — Determinant of a triangular matrix**

Let
$$A = \begin{pmatrix} a_{11} & a_{12} & \cdots & a_{1n} \\ 0 & a_{22} & \cdots & a_{2n} \\ \vdots & \ddots & \ddots & \vdots \\ 0 & \cdots & 0 & a_{nn} \end{pmatrix}$$
be an upper-triangular matrix. Then
$$\det(A) = a_{11}a_{22} \cdots a_{nn}.$$
The same conclusion holds for a lower-triangular matrix.

**Proof**

Suppose first that $A$ is upper triangular. Thus
$$a_{ij} = 0 \quad \text{whenever } i > j.$$
By the explicit determinant formula from theorem 5.4,
$$\det(A) = \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n a_{\sigma(j),j}.$$
Consider a permutation
$$\sigma \neq \text{id}.$$
We claim that there must exist some $j$ such that
$$\sigma(j) > j.$$

<!-- page 146 -->

Indeed, if
$$\sigma(j) \leq j \quad \text{for every } j,$$
then
$$\sum_{j=1}^n \sigma(j) \leq \sum_{j=1}^n j.$$
But because $\sigma$ is a permutation,
$$\sum_{j=1}^n \sigma(j) = \sum_{j=1}^n j.$$
Thus equality must hold at every position:
$$\sigma(j) = j \quad \text{for every } j,$$
contradicting
$$\sigma \neq \text{id}.$$
Hence every nonidentity permutation has some $j$ satisfying
$$\sigma(j) > j.$$
Because $A$ is upper triangular,
$$a_{\sigma(j),j} = 0.$$
Therefore
$$\prod_{j=1}^n a_{\sigma(j),j} = 0$$
for every nonidentity permutation.
Thus the only nonzero contribution to the determinant formula comes from the identity permutation. Since
$$\text{sgn}(\text{id}) = 1,$$
we obtain
$$\det(A) = a_{11}a_{22} \cdots a_{nn}.$$
Now suppose $A$ is lower triangular. Then $A^\top$ is upper triangular. By theorem 5.14,
$$\det(A) = \det(A^\top).$$
Applying the result just proved to $A^\top$ gives
$$\det(A^\top) = a_{11}a_{22} \cdots a_{nn}.$$

<!-- page 147 -->

Therefore
$$\det(A) = a_{11}a_{22} \cdots a_{nn}.$$

**Corollary 5.17 — Determinant of a diagonal matrix**

If
$$A = \begin{pmatrix} \lambda_1 & 0 & \cdots & 0 \\ 0 & \lambda_2 & \cdots & 0 \\ \vdots & \vdots & \ddots & \vdots \\ 0 & 0 & \cdots & \lambda_n \end{pmatrix},$$
then
$$\det(A) = \lambda_1 \lambda_2 \cdots \lambda_n.$$

**Proof**

A diagonal matrix is both upper triangular and lower triangular, so the result follows immediately from theorem 5.16.

**Remark 5.18 — Three elementary operations and the determinant**

The preceding results can be summarized in terms of the three elementary row operations:

| row operation | effect on the determinant |
| :--- | :--- |
| $R_i \leftrightarrow R_j$ | $\det \mapsto -\det$ |
| $R_i \mapsto cR_i$ | $\det \mapsto c \det$ |
| $R_j \mapsto R_j + cR_i, \quad i \neq j$ | $\det \mapsto \det$ |

Exactly the same rules hold for elementary column operations. Just look at the transpose.

**5.3 Multiplicativity and Invertibility**

The properties established in the previous subsection describe how the determinant changes when individual rows or columns of a matrix are modified. We now study how the determinant interacts with matrix multiplication.
The central result is
$$\det(AB) = \det(A) \det(B).$$
Because matrix multiplication represents composition of linear transformations, this property connects the determinant directly to the algebra of linear maps. It will also give a simple characterization

<!-- page 148 -->

of invertible matrices in terms of a single scalar.
We first record a consequence of the uniqueness argument used in theorem 5.4.

**Proposition 5.19 — Alternating multilinear functions are multiples of the determinant**

Let
$$D : (\mathbb{K}^n)^n \to \mathbb{K}$$
be an alternating multilinear function. Then, for all
$$a_1, \dots, a_n \in \mathbb{K}^n,$$
we have
$$D(a_1, \dots, a_n) = D(e_1, \dots, e_n) \det(a_1, \dots, a_n),$$
where
$$e_1, \dots, e_n$$
denotes the standard basis of $\mathbb{K}^n$, defined by
$$e_j = \begin{pmatrix} 0 \\ \vdots \\ 0 \\ 1 \\ 0 \\ \vdots \\ 0 \end{pmatrix},$$
where the $1$ appears in the $j$th position and all other entries are zero.
Thus every alternating multilinear function on $n$ vectors in $\mathbb{K}^n$ is a scalar multiple of the determinant.

**Proof**

Write each vector $a_j$ in the standard basis:
$$a_j = \sum_{i=1}^n a_{ij}e_i, \quad j = 1, \dots, n.$$

<!-- page 149 -->

By multilinearity,
$$D(a_1, \dots, a_n) = D\left( \sum_{i_1=1}^n a_{i_1 1}e_{i_1}, \dots, \sum_{i_n=1}^n a_{i_n n}e_{i_n} \right)$$
$$= \sum_{i_1=1}^n \cdots \sum_{i_n=1}^n a_{i_1 1} \cdots a_{i_n n} D(e_{i_1}, \dots, e_{i_n}).$$
If two of the indices
$$i_1, \dots, i_n$$
are equal, then two arguments of $D$ are equal. Since $D$ is alternating,
$$D(e_{i_1}, \dots, e_{i_n}) = 0.$$
Hence only those terms for which
$$i_1, \dots, i_n$$
are all distinct can remain. Such a choice of indices is a permutation of
$$1, \dots, n.$$
Therefore
$$D(a_1, \dots, a_n) = \sum_{\sigma \in S_n} \left( \prod_{j=1}^n a_{\sigma(j),j} \right) D(e_{\sigma(1)}, \dots, e_{\sigma(n)}).$$
By proposition 5.2, interchanging two arguments changes the sign of $D$. Consequently,
$$D(e_{\sigma(1)}, \dots, e_{\sigma(n)}) = \text{sgn}(\sigma) D(e_1, \dots, e_n).$$
Substituting this into the preceding expression gives
$$D(a_1, \dots, a_n) = D(e_1, \dots, e_n) \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n a_{\sigma(j),j}.$$
By the determinant formula in theorem 5.4,
$$\sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n a_{\sigma(j),j} = \det(a_1, \dots, a_n).$$
Therefore
$$D(a_1, \dots, a_n) = D(e_1, \dots, e_n) \det(a_1, \dots, a_n).$$
This characterization makes the proof of multiplicativity particularly transparent.

<!-- page 150 -->

**Theorem 5.20 — Multiplicativity of the determinant**

Let
$$A, B \in \mathbb{K}^{n \times n}.$$
Then
$$\det(AB) = \det(A) \det(B).$$

**Proof**

Fix the matrix
$$A \in \mathbb{K}^{n \times n}.$$
Write the columns of $B$ as
$$B = \begin{pmatrix} | & | & & | \\ b_1 & b_2 & \cdots & b_n \\ | & | & & | \end{pmatrix}.$$
Recall that multiplication by $A$ acts separately on the columns of $B$. Thus
$$AB = \begin{pmatrix} | & | & & | \\ Ab_1 & Ab_2 & \cdots & Ab_n \\ | & | & & | \end{pmatrix}.$$
Define
$$D_A : (\mathbb{K}^n)^n \to \mathbb{K}$$
by
$$D_A(b_1, \dots, b_n) = \det(Ab_1, \dots, Ab_n).$$
We first show that $D_A$ is multilinear.
Fix every argument except the $j$th one. For
$$u, v \in \mathbb{K}^n \quad \text{and} \quad \alpha, \beta \in \mathbb{K},$$
linearity of the map
$$x \mapsto Ax$$
gives
$$A(\alpha u + \beta v) = \alpha Au + \beta Av.$$

<!-- page 151 -->

Hence, by the multilinearity of the determinant,
$$D_A(b_1, \dots, \alpha u + \beta v, \dots, b_n)$$
$$= \det(Ab_1, \dots, A(\alpha u + \beta v), \dots, Ab_n)$$
$$= \det(Ab_1, \dots, \alpha Au + \beta Av, \dots, Ab_n)$$
$$= \alpha \det(Ab_1, \dots, Au, \dots, Ab_n)$$
$$+ \beta \det(Ab_1, \dots, Av, \dots, Ab_n)$$
$$= \alpha D_A(b_1, \dots, u, \dots, b_n) + \beta D_A(b_1, \dots, v, \dots, b_n).$$
Thus $D_A$ is multilinear.
Next, suppose two arguments are equal:
$$b_i = b_j, \quad i \neq j.$$
Then
$$Ab_i = Ab_j.$$
Therefore the matrix
$$\begin{pmatrix} | & & | \\ Ab_1 & \cdots & Ab_n \\ | & & | \end{pmatrix}$$
has two equal columns, and by the alternating property of the determinant,
$$D_A(b_1, \dots, b_n) = 0.$$
Thus $D_A$ is alternating.
We may therefore apply proposition 5.19. It gives
$$D_A(b_1, \dots, b_n) = D_A(e_1, \dots, e_n) \det(b_1, \dots, b_n).$$
Now
$$Ae_1, \dots, Ae_n$$
are precisely the columns of $A$. Hence
$$D_A(e_1, \dots, e_n) = \det(Ae_1, \dots, Ae_n) = \det(A).$$
Also,
$$\det(b_1, \dots, b_n) = \det(B).$$
Therefore
$$D_A(b_1, \dots, b_n) = \det(A) \det(B).$$

<!-- page 152 -->

But by definition,
$$D_A(b_1, \dots, b_n) = \det(AB).$$
Consequently,
$$\det(AB) = \det(A) \det(B).$$
Multiplicativity immediately gives several useful consequences.

**Corollary 5.21 — Determinant of powers**

Let
$$A \in \mathbb{K}^{n \times n}.$$
For every positive integer $k$,
$$\det(A^k) = (\det(A))^k.$$

**Proof**

By repeated application of theorem 5.20,
$$\det(A^k) = \det(\underbrace{A \cdots A}_{k \text{ factors}})$$
$$= \underbrace{\det(A) \cdots \det(A)}_{k \text{ factors}}$$
$$= (\det(A))^k.$$

**Corollary 5.22 — Determinant of an inverse**

Let
$$A \in \mathbb{K}^{n \times n}$$
be invertible. Then
$$\det(A) \neq 0$$
and
$$\det(A^{-1}) = \frac{1}{\det(A)}.$$

**Proof**

Because $A$ is invertible,
$$AA^{-1} = I_n.$$

<!-- page 153 -->

Taking determinants and using theorem 5.20,
$$\det(A) \det(A^{-1}) = \det(I_n).$$
By the normalization property in theorem 5.4,
$$\det(I_n) = 1.$$
Hence
$$\det(A) \det(A^{-1}) = 1.$$
Therefore
$$\det(A) \neq 0,$$
and solving for $\det(A^{-1})$ gives
$$\det(A^{-1}) = \frac{1}{\det(A)}.$$
We can now connect the determinant to the rank and invertibility theory developed in the previous section.

**Theorem 5.23 — Determinant criterion for invertibility**

Let
$$A \in \mathbb{K}^{n \times n}.$$
Then
$$A \text{ is invertible} \iff \det(A) \neq 0.$$

**Proof**

Suppose first that $A$ is invertible.
By corollary 5.22,
$$\det(A) \det(A^{-1}) = 1.$$
Therefore
$$\det(A) \neq 0.$$
Conversely, suppose
$$\det(A) \neq 0.$$
Write the columns of $A$ as
$$A = \begin{pmatrix} | & | & & | \\ a_1 & a_2 & \cdots & a_n \\ | & | & & | \end{pmatrix}.$$

<!-- page 154 -->

By proposition 5.12, if
$$a_1, \dots, a_n$$
were linearly dependent, then
$$\det(A) = 0.$$
Because
$$\det(A) \neq 0,$$
the columns
$$a_1, \dots, a_n$$
must therefore be linearly independent.
By the definition of matrix rank in definition 3.28,
$$\text{Rank}(A) = \dim \text{Span}(a_1, \dots, a_n).$$
Since $a_1, \dots, a_n$ are $n$ linearly independent vectors,
$$\text{Rank}(A) = n.$$
Finally, by corollary 3.57,
$$\text{Rank}(A) = n \iff A \text{ is invertible}.$$
Thus
$$A \text{ is invertible} \iff \det(A) \neq 0.$$

**Definition 5.24 — Singular and nonsingular matrices**

Let
$$A \in \mathbb{K}^{n \times n}.$$
The matrix $A$ is called **nonsingular** if it is invertible.
It is called **singular** if it is not invertible.

**Corollary 5.25 — Equivalent characterizations of nonsingularity**

Let
$$A \in \mathbb{K}^{n \times n}.$$
Then the following statements are equivalent:

<!-- page 155 -->

(i) $A$ is invertible;
(ii) $A$ is nonsingular;
(iii)
$$\det(A) \neq 0;$$
(iv)
$$\text{Rank}(A) = n;$$
(v)
$$\ker A = \{0\};$$
(vi) the columns of $A$ form a basis of $\mathbb{K}^n$;
(vii) the rows of $A$ form a basis of $\mathbb{K}_n$.
Equivalently,
$$A \text{ is singular} \iff \det(A) = 0 \iff \text{Rank}(A) < n.$$

**Proof**

By theorem 5.23,
$$A \text{ is invertible} \iff \det(A) \neq 0.$$
By corollary 3.57, invertibility is equivalent to
$$\text{Rank}(A) = n, \quad \ker A = \{0\},$$
and to the columns and rows of $A$ forming bases of their respective coordinate spaces.
Finally, "nonsingular" is simply another name for "invertible" by definition 5.24.
Thus all the stated conditions are equivalent.

**Remark 5.26 — What the determinant detects**

For a square matrix, the determinant detects whether the associated linear transformation loses a dimension.
If
$$\det(A) \neq 0,$$
then
$$\text{Rank}(A) = n,$$
so the transformation
$$x \mapsto Ax$$

<!-- page 156 -->

preserves $n$ independent directions.
If
$$\det(A) = 0,$$
then
$$\text{Rank}(A) < n,$$
so the image lies in a proper subspace of $\mathbb{K}^n$.
Thus
$$\det(A) = 0$$
is precisely the algebraic signal that the transformation collapses at least one independent direction.

The determinant criterion also gives a short proof of an important fact about products of square matrices.

**Corollary 5.27 — Invertibility of a product**

Let
$$A, B \in \mathbb{K}^{n \times n}.$$
Then
$$AB \text{ is invertible} \iff A \text{ and } B \text{ are both invertible.}$$

**Proof**

By theorem 5.23,
$$AB \text{ is invertible} \iff \det(AB) \neq 0.$$
By theorem 5.20,
$$\det(AB) = \det(A) \det(B).$$
Since $\mathbb{K}$ is a field,
$$\det(A) \det(B) \neq 0$$
if and only if
$$\det(A) \neq 0 \quad \text{and} \quad \det(B) \neq 0.$$
Applying theorem 5.23 once more,
$$\det(A) \neq 0 \iff A \text{ is invertible},$$
and similarly for $B$.

<!-- page 157 -->

Therefore
$$AB \text{ is invertible} \iff A \text{ and } B \text{ are both invertible.}$$

A useful consequence is that, for square matrices, a one-sided inverse is automatically a two-sided inverse.

::: {.proof-box title="Corollary 5.28 — A one-sided inverse is an inverse"}
Let
$$A, B \in \mathbb{K}^{n \times n}.$$
If
$$AB = I_n,$$
then
$$BA = I_n$$
and
$$B = A^{-1}.$$
Similarly, if
$$BA = I_n,$$
then
$$AB = I_n$$
and again
$$B = A^{-1}.$$
:::

::: {.proof-box title="Proof"}
Suppose
$$AB = I_n.$$
Taking determinants and using theorem 5.20,
$$\det(A) \det(B) = \det(I_n) = 1.$$
Hence
$$\det(A) \neq 0.$$
By theorem 5.23, $A$ is invertible. Multiplying
$$AB = I_n$$
:::

<!-- page 158 -->

on the left by $A^{-1}$ gives
$$A^{-1}AB = A^{-1}I_n,$$
and therefore
$$B = A^{-1}.$$
Consequently,
$$BA = A^{-1}A = I_n.$$
The case
$$BA = I_n$$
is proved analogously.

We now connect the determinant with the change-of-basis theory developed earlier.

::: {.proof-box title="Corollary 5.29 — Determinant is invariant under similarity"}
Let
$$A, B \in \mathbb{K}^{n \times n}.$$
If $A$ and $B$ are similar, so that
$$B = P^{-1}AP$$
for some invertible matrix
$$P \in \mathbb{K}^{n \times n},$$
then
$$\det(B) = \det(A).$$
:::

::: {.proof-box title="Proof"}
By theorem 5.20,
$$\det(B) = \det(P^{-1}AP)$$
$$= \det(P^{-1}) \det(A) \det(P).$$
By corollary 5.22,
$$\det(P^{-1}) = \frac{1}{\det(P)}.$$
Therefore
$$\det(B) = \frac{1}{\det(P)} \det(A) \det(P)$$
$$= \det(A).$$
:::

<!-- page 159 -->

::: {.proof-box title="Remark 5.30 — Similarity versus matrix equivalence"}
Recall that similarity has the special form
$$B = P^{-1}AP,$$
and therefore preserves the value of the determinant:
$$\det(B) = \det(A).$$
For the more general matrix equivalence
$$B = PAQ,$$
where $P$ and $Q$ are independently chosen invertible matrices, multiplicativity gives
$$\det(B) = \det(P) \det(A) \det(Q).$$
Thus matrix equivalence does not in general preserve the numerical value of the determinant. It does, however, preserve whether the determinant is zero, because
$$\det(P) \neq 0, \quad \det(Q) \neq 0.$$
Hence
$$\det(B) = 0 \iff \det(A) = 0.$$
:::

The invariance of the determinant under similarity allows us to define the determinant of an abstract linear transformation without referring to any particular coordinate system.

::: {.proof-box title="Definition 5.31 — Determinant of a linear transformation"}
Let
$$T : V \to V$$
be a linear transformation on a finite-dimensional vector space $V$, and let
$$\mathcal{E}$$
be any basis of $V$.
The **determinant of $T$** is defined by
$$\det(T) := \det([T]_{\mathcal{E} \leftarrow \mathcal{E}}).$$
:::

We must verify that this definition does not depend on the chosen basis.

<!-- page 160 -->

::: {.proof-box title="Proposition 5.32 — The determinant of a linear transformation is basis-independent"}
Let
$$T : V \to V$$
be a linear transformation on a finite-dimensional vector space.
If $\mathcal{E}$ and $\mathcal{E}'$ are two bases of $V$, then
$$\det([T]_{\mathcal{E} \leftarrow \mathcal{E}}) = \det([T]_{\mathcal{E}' \leftarrow \mathcal{E}'}).$$
Therefore definition 5.31 is well-defined.
:::

::: {.proof-box title="Proof"}
Suppose the transition matrix from $\mathcal{E}$ to $\mathcal{E}'$ is $P$, so that
$$\mathcal{E}' = \mathcal{E}P.$$
By the change-of-basis formula for linear transformations, corollary 3.39,
$$[T]_{\mathcal{E}' \leftarrow \mathcal{E}'} = P^{-1}[T]_{\mathcal{E} \leftarrow \mathcal{E}}P.$$
Thus the two matrices representing $T$ are similar. By corollary 5.29,
$$\det([T]_{\mathcal{E}' \leftarrow \mathcal{E}'}) = \det([T]_{\mathcal{E} \leftarrow \mathcal{E}}).$$
Hence the value of the determinant is independent of the chosen basis.
:::

::: {.proof-box title="Proposition 5.33 — Properties of the determinant of a linear transformation"}
Let
$$S, T : V \to V$$
be linear transformations on a finite-dimensional vector space $V$. Then:
(1)
$$\det(I_V) = 1.$$
(2)
$$\det(ST) = \det(S) \det(T).$$
(3)
$$T \text{ is invertible} \iff \det(T) \neq 0.$$
:::

<!-- page 161 -->

(4) If $T$ is invertible, then
$$\det(T^{-1}) = \frac{1}{\det(T)}.$$

::: {.proof-box title="Proof"}
Choose any basis
$$\mathcal{E}$$
of $V$.
For (1), the matrix of the identity transformation is
$$[I_V]_{\mathcal{E} \leftarrow \mathcal{E}} = I_n.$$
Hence, by the normalization property in theorem 5.4,
$$\det(I_V) = \det(I_n) = 1.$$
For (2), composition of linear transformations corresponds to matrix multiplication:
$$[ST]_{\mathcal{E} \leftarrow \mathcal{E}} = [S]_{\mathcal{E} \leftarrow \mathcal{E}}[T]_{\mathcal{E} \leftarrow \mathcal{E}}.$$
Therefore, by theorem 5.20,
$$\det(ST) = \det([ST]_{\mathcal{E} \leftarrow \mathcal{E}})$$
$$= \det([S]_{\mathcal{E} \leftarrow \mathcal{E}}[T]_{\mathcal{E} \leftarrow \mathcal{E}})$$
$$= \det([S]_{\mathcal{E} \leftarrow \mathcal{E}}) \det([T]_{\mathcal{E} \leftarrow \mathcal{E}})$$
$$= \det(S) \det(T).$$
For (3), by the correspondence between invertibility of a linear transformation and invertibility of its matrix, together with theorem 5.23,
$$T \text{ is invertible} \iff [T]_{\mathcal{E} \leftarrow \mathcal{E}} \text{ is invertible}$$
$$\iff \det([T]_{\mathcal{E} \leftarrow \mathcal{E}}) \neq 0$$
$$\iff \det(T) \neq 0.$$
Finally, if $T$ is invertible, then
$$T^{-1}T = I_V.$$
Using (1) and (2),
$$1 = \det(I_V) = \det(T^{-1}T) = \det(T^{-1}) \det(T).$$
:::

<!-- page 162 -->

Therefore
$$\det(T^{-1}) = \frac{1}{\det(T)}.$$

::: {.proof-box title="Remark 5.34 — The determinant is intrinsic"}
A matrix representing a linear transformation depends on the choice of basis:
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}} \neq [T]_{\mathcal{E}' \leftarrow \mathcal{E}'}$$
in general.
The determinant does not:
$$\det([T]_{\mathcal{E} \leftarrow \mathcal{E}}) = \det([T]_{\mathcal{E}' \leftarrow \mathcal{E}'}).$$
Thus
$$\det(T)$$
is an intrinsic property of the linear transformation $T$.
:::

## 5.4 Minors, Cofactors, and Cofactor Expansion

The explicit permutation formula for the determinant is useful theoretically, but it quickly becomes cumbersome for computation. A more practical recursive formula expresses the determinant of an $n \times n$ matrix in terms of determinants of $(n-1) \times (n-1)$ matrices.

The basic objects in this formula are minors and cofactors.

::: {.proof-box title="Definition 5.35 — Minors and cofactors"}
Let
$$A = \begin{pmatrix} a_{11} & a_{12} & \cdots & a_{1n} \\ a_{21} & a_{22} & \cdots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ a_{n1} & a_{n2} & \cdots & a_{nn} \end{pmatrix} \in \mathbb{K}^{n \times n}.$$
For
$$1 \leq i, j \leq n,$$
delete the $i$th row and the $j$th column of $A$. The resulting $(n-1) \times (n-1)$ matrix is denoted by
$$A(i|j).$$
:::

<!-- page 163 -->

The **minor** of the entry $a_{ij}$ is
$$M_{ij} := \det A(i|j).$$
The **cofactor** of $a_{ij}$ is
$$C_{ij} := (-1)^{i+j} M_{ij} = (-1)^{i+j} \det A(i|j).$$

For example, if
$$A = \begin{pmatrix} a_{11} & a_{12} & a_{13} \\ a_{21} & a_{22} & a_{23} \\ a_{31} & a_{32} & a_{33} \end{pmatrix},$$
then deleting the second row and third column gives
$$A(2|3) = \begin{pmatrix} a_{11} & a_{12} \\ a_{31} & a_{32} \end{pmatrix}.$$
Hence
$$M_{23} = \det \begin{pmatrix} a_{11} & a_{12} \\ a_{31} & a_{32} \end{pmatrix},$$
and
$$C_{23} = (-1)^{2+3} M_{23} = -\det \begin{pmatrix} a_{11} & a_{12} \\ a_{31} & a_{32} \end{pmatrix}.$$
Thus the signs of the cofactors follow the checkerboard pattern
$$\begin{pmatrix} + & - & + & \cdots \\ - & + & - & \cdots \\ + & - & + & \cdots \\ \vdots & \vdots & \vdots & \ddots \end{pmatrix}.$$

We first consider a determinant whose one column has only one nonzero entry.

::: {.proof-box title="Proposition 5.36 — A column with a single nonzero entry"}
Suppose the $j$th column of
$$A \in \mathbb{K}^{n \times n}$$
:::

<!-- page 164 -->

has only one possibly nonzero entry, namely $a_{ij}$:
$$A = \begin{pmatrix} a_{11} & \cdots & 0 & \cdots & a_{1n} \\ \vdots & & \vdots & & \vdots \\ a_{i1} & \cdots & a_{ij} & \cdots & a_{in} \\ \vdots & & \vdots & & \vdots \\ a_{n1} & \cdots & 0 & \cdots & a_{nn} \end{pmatrix}.$$
Then
$$\det(A) = a_{ij}C_{ij} = (-1)^{i+j} a_{ij}M_{ij}.$$
:::

::: {.proof-box title="Proof"}
We move the entry $a_{ij}$ to the $(1, 1)$ position.
First, move the $j$th column to the first column. This requires
$$j - 1$$
successive column interchanges. By proposition 5.9, each interchange changes the sign of the determinant. Hence this contributes the factor
$$(-1)^{j-1}.$$
Next, move the $i$th row to the first row. This requires
$$i - 1$$
successive row interchanges.
To see the effect of a row interchange, note that interchanging two rows of a matrix $A$ is equivalent, after transposition, to interchanging the corresponding two columns of $A^\top$. By theorem 5.14 and proposition 5.9, each row interchange also changes the sign of the determinant.
Hence these row interchanges contribute the factor
$$(-1)^{i-1}.$$
After these operations, we obtain a matrix of the form
$$B = \begin{pmatrix} a_{ij} & * & \cdots & * \\ 0 & & & \\ \vdots & & A(i|j) & \\ 0 & & & \end{pmatrix},$$
:::

<!-- page 165 -->

where the lower-right $(n-1) \times (n-1)$ block is exactly the matrix $A(i|j)$ obtained by deleting row $i$ and column $j$ from $A$.
The total number of interchanges is
$$(i - 1) + (j - 1) = i + j - 2.$$
Therefore
$$\det(A) = (-1)^{i+j-2} \det(B) = (-1)^{i+j} \det(B).$$
It remains to compute $\det(B)$. In the first column of $B$, the only nonzero entry is $a_{ij}$. Using the explicit determinant formula from theorem 5.4, every nonzero term in $\det(B)$ must select the entry $a_{ij}$ from the first column. The remaining factors then form exactly one of the terms in
$$\det A(i|j).$$
Hence
$$\det(B) = a_{ij} \det A(i|j) = a_{ij}M_{ij}.$$
Consequently,
$$\det(A) = (-1)^{i+j} a_{ij}M_{ij}.$$
By the definition of the cofactor,
$$C_{ij} = (-1)^{i+j} M_{ij},$$
so
$$\det(A) = a_{ij}C_{ij}.$$
:::

We can now expand a determinant along any column.

::: {.proof-box title="Theorem 5.37 — Cofactor expansion along a column"}
Let
$$A = (a_{ij}) \in \mathbb{K}^{n \times n}.$$
Fix a column
$$j \in \{1, \dots, n\}.$$
Then
$$\det(A) = \sum_{i=1}^n a_{ij}C_{ij}.$$
In full,
$$\det(A) = a_{1j}C_{1j} + a_{2j}C_{2j} + \dots + a_{nj}C_{nj}.$$
:::

<!-- page 166 -->

Equivalently,
$$\det(A) = \sum_{i=1}^n (-1)^{i+j} a_{ij}M_{ij}.$$

::: {.proof-box title="Proof"}
Write the $j$th column as
$$\begin{pmatrix} a_{1j} \\ a_{2j} \\ \vdots \\ a_{nj} \end{pmatrix} = a_{1j}e_1 + a_{2j}e_2 + \dots + a_{nj}e_n,$$
where
$$e_1, \dots, e_n$$
is the standard basis of $\mathbb{K}^n$.
By linearity of the determinant in the $j$th column, proposition 5.7,
$$\det(A) = \sum_{i=1}^n a_{ij} \det(A_i),$$
where $A_i$ is obtained from $A$ by replacing its $j$th column with $e_i$.
The $j$th column of $A_i$ has exactly one nonzero entry, equal to 1 in row $i$. Therefore, by proposition 5.36,
$$\det(A_i) = C_{ij}.$$
Consequently,
$$\det(A) = \sum_{i=1}^n a_{ij}C_{ij}.$$
:::

For example, expansion along the first column gives
$$\det \begin{pmatrix} a_{11} & a_{12} & \cdots & a_{1n} \\ a_{21} & a_{22} & \cdots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ a_{n1} & a_{n2} & \cdots & a_{nn} \end{pmatrix} = a_{11}C_{11} + a_{21}C_{21} + \dots + a_{n1}C_{n1}.$$
For a $3 \times 3$ matrix,
$$A = \begin{pmatrix} a_{11} & a_{12} & a_{13} \\ a_{21} & a_{22} & a_{23} \\ a_{31} & a_{32} & a_{33} \end{pmatrix},$$

<!-- page 167 -->

expansion along the first column gives
$$\det(A) = a_{11} \det \begin{pmatrix} a_{22} & a_{23} \\ a_{32} & a_{33} \end{pmatrix}$$
$$- a_{21} \det \begin{pmatrix} a_{12} & a_{13} \\ a_{32} & a_{33} \end{pmatrix}$$
$$+ a_{31} \det \begin{pmatrix} a_{12} & a_{13} \\ a_{22} & a_{23} \end{pmatrix}.$$

Because the determinant is unchanged by transposition, the corresponding row formula follows immediately.

::: {.proof-box title="Corollary 5.38 — Cofactor expansion along a row"}
Let
$$A = (a_{ij}) \in \mathbb{K}^{n \times n}.$$
Fix a row
$$i \in \{1, \dots, n\}.$$
Then
$$\det(A) = \sum_{j=1}^n a_{ij}C_{ij}.$$
Thus
$$\det(A) = a_{i1}C_{i1} + a_{i2}C_{i2} + \dots + a_{in}C_{in}.$$
:::

::: {.proof-box title="Proof"}
By theorem 5.14,
$$\det(A) = \det(A^\top).$$
The $i$th row of $A$ is the $i$th column of $A^\top$.
Applying theorem 5.37 to that column of $A^\top$ gives
$$\det(A^\top) = \sum_{j=1}^n a_{ij}C_{ij}.$$
Therefore
$$\det(A) = \sum_{j=1}^n a_{ij}C_{ij}.$$
:::

<!-- page 168 -->

::: {.proof-box title="Remark 5.39 — Which row or column should be used?"}
A determinant may be expanded along *any* row or *any* column.
For computation, one should usually choose a row or column containing as many zeros as possible, because every zero entry contributes
$$0 \cdot C_{ij} = 0$$
to the expansion.
:::

::: {.proof-box title="Example 5.40 — Expansion along a sparse column"}
Consider
$$A = \begin{pmatrix} 2 & 0 & 1 \\ 0 & 3 & 0 \\ 4 & 0 & 5 \end{pmatrix}.$$
The second column contains only one nonzero entry, so expanding along that column gives
$$\det(A) = 3C_{22}.$$
Since
$$C_{22} = (-1)^{2+2} \det \begin{pmatrix} 2 & 1 \\ 4 & 5 \end{pmatrix},$$
we obtain
$$\det(A) = 3 \det \begin{pmatrix} 2 & 1 \\ 4 & 5 \end{pmatrix}$$
$$= 3(10 - 4)$$
$$= 18.$$
:::

Cofactor expansion also gives an identity that will be useful when we construct the inverse of a matrix.

::: {.proof-box title="Proposition 5.41 — Cofactor orthogonality"}
Let
$$A = (a_{ij}) \in \mathbb{K}^{n \times n}.$$
For a fixed column $r$,
$$\sum_{i=1}^n a_{ir}C_{ir} = \det(A).$$
:::

<!-- page 169 -->

If
$$r \neq s,$$
then
$$\sum_{i=1}^n a_{ir}C_{is} = 0.$$
Similarly, for rows,
$$\sum_{j=1}^n a_{rj}C_{rj} = \det(A),$$
whereas for
$$r \neq s,$$
$$\sum_{j=1}^n a_{rj}C_{sj} = 0.$$

**Proof**
The first and third identities are precisely the column and row cofactor expansions from theorem 5.37 and corollary 5.38.
Now let
$$r \neq s.$$
Form a new matrix $B$ by replacing column $s$ of $A$ with column $r$ of $A$.
Then columns $r$ and $s$ of $B$ are equal. Hence, by the alternating property of the determinant,
$$\det(B) = 0.$$
Expand $\det(B)$ along column $s$. The entries of that column are
$$a_{1r}, \dots, a_{nr}.$$
Moreover, deleting column $s$ in forming the corresponding cofactors removes the replaced column, so those cofactors are exactly
$$C_{1s}, \dots, C_{ns}$$
from the original matrix $A$.
Therefore
$$0 = \det(B) = \sum_{i=1}^n a_{ir}C_{is}.$$
The corresponding row identity follows either by the same argument or by applying the

<!-- page 170 -->

column identity to $A^\top$ and using theorem 5.14.

### 5.5 The Adjugate Matrix and Cramer’s Rule
The cofactor identities from the previous subsection can be assembled into a matrix identity. This leads to an explicit formula for the inverse of a nonsingular matrix and, as a consequence, to Cramer’s rule for solving square linear systems.

**Definition 5.42 — Cofactor matrix and adjugate**
Let
$$A = (a_{ij}) \in \mathbb{K}^{n \times n},$$
and let
$$C_{ij} = (-1)^{i+j}M_{ij}$$
be the cofactor of the entry $a_{ij}$, as defined in definition 5.35.
The **cofactor matrix** of $A$ is
$$C(A) = \begin{pmatrix} C_{11} & C_{12} & \cdots & C_{1n} \\ C_{21} & C_{22} & \cdots & C_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ C_{n1} & C_{n2} & \cdots & C_{nn} \end{pmatrix}.$$
The **adjugate matrix** of $A$ is the transpose of the cofactor matrix:
$$\text{adj}(A) = C(A)^\top.$$
Thus
$$\text{adj}(A) = \begin{pmatrix} C_{11} & C_{21} & \cdots & C_{n1} \\ C_{12} & C_{22} & \cdots & C_{n2} \\ \vdots & \vdots & \ddots & \vdots \\ C_{1n} & C_{2n} & \cdots & C_{nn} \end{pmatrix},$$
so that
$$(\text{adj}(A))_{ij} = C_{ji}.$$
The transpose in the definition is important. It places the cofactors in precisely the positions needed for ordinary matrix multiplication.

<!-- page 171 -->

**Theorem 5.43 — Adjugate identity**
For every
$$A \in \mathbb{K}^{n \times n},$$
we have
$$A \text{adj}(A) = \text{adj}(A)A = \det(A)I_n.$$

**Proof**
We first compute
$$A \text{adj}(A).$$
Because
$$(\text{adj}(A))_{kj} = C_{jk},$$
the $(i, j)$ entry of the product is
$$(A \text{adj}(A))_{ij} = \sum_{k=1}^n a_{ik}(\text{adj}(A))_{kj}$$
$$= \sum_{k=1}^n a_{ik}C_{jk}.$$
Consider first the diagonal case
$$i = j.$$
Then
$$(A \text{adj}(A))_{ii} = \sum_{k=1}^n a_{ik}C_{ik}.$$
By the cofactor expansion along row $i$ in corollary 5.38,
$$\sum_{k=1}^n a_{ik}C_{ik} = \det(A).$$
Hence
$$(A \text{adj}(A))_{ii} = \det(A).$$
Now suppose
$$i \neq j.$$
By the row version of the cofactor orthogonality identity in proposition 5.41,
$$\sum_{k=1}^n a_{ik}C_{jk} = 0.$$

<!-- page 172 -->

Therefore
$$(A \text{adj}(A))_{ij} = 0 \quad (i \neq j).$$
Thus
$$A \text{adj}(A) = \begin{pmatrix} \det(A) & 0 & \cdots & 0 \\ 0 & \det(A) & \cdots & 0 \\ \vdots & \vdots & \ddots & \vdots \\ 0 & 0 & \cdots & \det(A) \end{pmatrix} = \det(A)I_n.$$
The identity in the opposite order is proved similarly. Since
$$(\text{adj}(A))_{ik} = C_{ki},$$
we have
$$(\text{adj}(A)A)_{ij} = \sum_{k=1}^n C_{ki}a_{kj}.$$
If
$$i = j,$$
the cofactor expansion along column $i$ gives
$$\sum_{k=1}^n a_{ki}C_{ki} = \det(A).$$
If
$$i \neq j,$$
the column version of proposition 5.41 gives
$$\sum_{k=1}^n a_{kj}C_{ki} = 0.$$
Hence
$$\text{adj}(A)A = \det(A)I_n.$$
Therefore
$$A \text{adj}(A) = \text{adj}(A)A = \det(A)I_n.$$
The adjugate identity immediately gives an explicit inverse formula.

<!-- page 173 -->

**Corollary 5.44 — Inverse formula using the adjugate**
Let
$$A \in \mathbb{K}^{n \times n}$$
satisfy
$$\det(A) \neq 0.$$
Then
$$A^{-1} = \frac{1}{\det(A)} \text{adj}(A).$$

**Proof**
By theorem 5.43,
$$A \text{adj}(A) = \text{adj}(A)A = \det(A)I_n.$$
Because
$$\det(A) \neq 0,$$
we may divide by $\det(A)$. Hence
$$A \left( \frac{1}{\det(A)} \text{adj}(A) \right) = I_n$$
and
$$\left( \frac{1}{\det(A)} \text{adj}(A) \right) A = I_n.$$
Therefore
$$\frac{1}{\det(A)} \text{adj}(A)$$
is the inverse of $A$, and thus
$$A^{-1} = \frac{1}{\det(A)} \text{adj}(A).$$

**Example 5.45 — Inverse of a $2 \times 2$ matrix**
Let
$$A = \begin{pmatrix} a & b \\ c & d \end{pmatrix}.$$
Its cofactors are
$$C_{11} = d, \quad C_{12} = -c, \quad C_{21} = -b, \quad C_{22} = a.$$

<!-- page 174 -->

Hence the cofactor matrix is
$$C(A) = \begin{pmatrix} d & -c \\ -b & a \end{pmatrix},$$
and therefore
$$\text{adj}(A) = \begin{pmatrix} d & -b \\ -c & a \end{pmatrix}.$$
Since
$$\det(A) = ad - bc,$$
if
$$ad - bc \neq 0,$$
then
$$A^{-1} = \frac{1}{ad - bc} \begin{pmatrix} d & -b \\ -c & a \end{pmatrix}.$$

**Remark 5.46 — The adjugate formula is mainly theoretical**
The formula
$$A^{-1} = \frac{1}{\det(A)} \text{adj}(A)$$
gives an explicit expression for the inverse in terms of determinants.
For a large matrix, however, computing all $n^2$ cofactors is generally inefficient.

We now apply the inverse formula to a square system of linear equations.
Consider
$$Ax = b,$$
where
$$A = \begin{pmatrix} a_{11} & a_{12} & \cdots & a_{1n} \\ a_{21} & a_{22} & \cdots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ a_{n1} & a_{n2} & \cdots & a_{nn} \end{pmatrix}, \quad x = \begin{pmatrix} x_1 \\ x_2 \\ \vdots \\ x_n \end{pmatrix}, \quad b = \begin{pmatrix} b_1 \\ b_2 \\ \vdots \\ b_n \end{pmatrix}.$$
For each
$$j = 1, \dots, n,$$

<!-- page 175 -->

let $A_j(b)$ denote the matrix obtained from $A$ by replacing its $j$th column by $b$:
$$A_j(b) = \begin{pmatrix} a_{11} & \cdots & a_{1,j-1} & b_1 & a_{1,j+1} & \cdots & a_{1n} \\ a_{21} & \cdots & a_{2,j-1} & b_2 & a_{2,j+1} & \cdots & a_{2n} \\ \vdots & & \vdots & \vdots & \vdots & & \vdots \\ a_{n1} & \cdots & a_{n,j-1} & b_n & a_{n,j+1} & \cdots & a_{nn} \end{pmatrix}.$$

**Theorem 5.47 — Cramer’s rule**
Let
$$A \in \mathbb{K}^{n \times n}$$
and suppose
$$\det(A) \neq 0.$$
Then, for every
$$b \in \mathbb{K}^n,$$
the system
$$Ax = b$$
has a unique solution. Its components are
$$x_j = \frac{\det A_j(b)}{\det A}, \quad j = 1, \dots, n.$$

**Proof**
Because
$$\det(A) \neq 0,$$
theorem 5.23 implies that $A$ is invertible. Hence
$$Ax = b$$
has the unique solution
$$x = A^{-1}b.$$
By corollary 5.44,
$$x = \frac{1}{\det(A)} \text{adj}(A)b.$$
The $j$th row of $\text{adj}(A)$ is
$$(C_{1j}, C_{2j}, \dots, C_{nj}).$$

<!-- page 176 -->

Therefore the $j$th component of $x$ is
$$x_j = \frac{1}{\det(A)} \sum_{i=1}^n C_{ij}b_i.$$
Now consider the matrix $A_j(b)$ obtained by replacing the $j$th column of $A$ by $b$.
Expand its determinant along the $j$th column. By theorem 5.37,
$$\det A_j(b) = \sum_{i=1}^n b_i \widetilde{C}_{ij},$$
where $\widetilde{C}_{ij}$ denotes the cofactor of the $(i, j)$ entry of $A_j(b)$.
Deleting row $i$ and column $j$ removes the replaced column entirely. Thus the matrix used to compute $\widetilde{C}_{ij}$ is exactly the same as the matrix used to compute $C_{ij}$ in $A$. Hence
$$\widetilde{C}_{ij} = C_{ij}.$$
Therefore
$$\det A_j(b) = \sum_{i=1}^n b_i C_{ij}.$$
Substituting this identity into the formula for $x_j$ gives
$$x_j = \frac{\det A_j(b)}{\det A}.$$
Since this holds for every
$$j = 1, \dots, n,$$
we obtain
$$x_j = \frac{\det A_j(b)}{\det A}, \quad j = 1, \dots, n.$$

**Example 5.48 — Cramer’s rule for a $2 \times 2$ system**
Consider
$$ax + by = r,$$
$$cx + dy = s,$$
or equivalently,
$$\begin{pmatrix} a & b \\ c & d \end{pmatrix} \begin{pmatrix} x \\ y \end{pmatrix} = \begin{pmatrix} r \\ s \end{pmatrix}.$$

<!-- page 177 -->

Suppose
$$ad - bc \neq 0.$$
Then
$$A_1(b) = \begin{pmatrix} r & b \\ s & d \end{pmatrix}, \quad A_2(b) = \begin{pmatrix} a & r \\ c & s \end{pmatrix}.$$
By theorem 5.47,
$$x = \frac{\det \begin{pmatrix} r & b \\ s & d \end{pmatrix}}{\det \begin{pmatrix} a & b \\ c & d \end{pmatrix}} = \frac{rd - bs}{ad - bc},$$
and
$$y = \frac{\det \begin{pmatrix} a & r \\ c & s \end{pmatrix}}{\det \begin{pmatrix} a & b \\ c & d \end{pmatrix}} = \frac{as - cr}{ad - bc}.$$

**Remark 5.49 — What Cramer’s rule tells us**
Cramer’s rule gives an explicit formula for each component of the solution:
$$x_j = \frac{\det A_j(b)}{\det A}.$$
Its main importance is theoretical rather than computational. For large systems, Gaussian elimination is far more efficient. (You should have seen this in your undergraduate linear algebra course).

### 5.6 Geometric Meaning of the Determinant
So far, we have studied the determinant algebraically: through its multilinearity, its alternating property, its multiplicativity, and its relation to invertibility. We now explain its geometric meaning.
The key idea is that the determinant measures how a linear transformation changes size. In dimension 2, it measures the scaling of area; in dimension 3, it measures the scaling of volume. Its sign records whether orientation is preserved or reversed.

<!-- page 178 -->

**The Determinant in $\mathbb{R}^2$** Let
$$A = \begin{pmatrix} a & b \\ c & d \end{pmatrix} = \begin{pmatrix} | & | \\ u & v \\ | & | \end{pmatrix}, \quad u = \begin{pmatrix} a \\ c \end{pmatrix}, \quad v = \begin{pmatrix} b \\ d \end{pmatrix}.$$
Then the two columns $u$ and $v$ span a parallelogram in $\mathbb{R}^2$.
The determinant
$$\det(A) = ad - bc$$
is the *signed area* of this parallelogram. In particular,
$$|\det(A)| = \text{the area of the parallelogram spanned by } u \text{ and } v.$$
Thus the determinant gives more than just area: its sign also carries orientation information.

**Orientation in $\mathbb{R}^2$.** The standard basis
$$e_1 = \begin{pmatrix} 1 \\ 0 \end{pmatrix}, \quad e_2 = \begin{pmatrix} 0 \\ 1 \end{pmatrix}$$
determines the standard counterclockwise orientation of the plane.
* If
$$\det(A) > 0,$$
then the ordered pair $(u, v)$ has the same orientation as $(e_1, e_2)$.
* If
$$\det(A) < 0,$$
then the orientation is reversed.
* If
$$\det(A) = 0,$$
then $u$ and $v$ are linearly dependent, so the parallelogram collapses to a line segment and its area is zero.

A useful way to think about this is to start from the unit square. The matrix $A$ sends the unit square to the parallelogram spanned by its two columns, and the area changes by the factor $|\det(A)|$.
Therefore a linear map
$$A : \mathbb{R}^2 \to \mathbb{R}^2$$
scales all areas by the factor
$$|\det(A)|.$$

<!-- page 179 -->

[Image: A unit square with area 1, with vectors e1 and e2, is transformed by A into a parallelogram with area |det(A)|, with vectors u and v.]
Figure 1: In $\mathbb{R}^2$, the determinant measures signed area.

**Examples.**
1. If
$$A = \begin{pmatrix} 2 & 0 \\ 0 & 3 \end{pmatrix},$$
then
$$\det(A) = 6.$$
So the unit square is stretched to a rectangle of area 6.
2. If
$$A = \begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix},$$
then
$$\det(A) = 1.$$
This is a shear: it changes the shape, but not the area.
3. If
$$A = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix},$$
then
$$\det(A) = -1.$$
Thus area is preserved, but orientation is reversed.

**The Determinant in $\mathbb{R}^3$** Now let
$$A = \begin{pmatrix} | & | & | \\ u & v & w \\ | & | & | \end{pmatrix} \in \mathbb{R}^{3 \times 3},$$

<!-- page 180 -->

where
$$u, v, w \in \mathbb{R}^3.$$
These three vectors span a parallelepiped in $\mathbb{R}^3$.
The determinant
$$\det(A)$$
is the *signed volume* of this parallelepiped. Hence
$$|\det(A)| = \text{the volume of the parallelepiped spanned by } u, v, w.$$
As in dimension 2, the sign records orientation.
* If
$$\det(A) > 0,$$
then the ordered triple $(u, v, w)$ has the same orientation as the standard basis of $\mathbb{R}^3$.
* If
$$\det(A) < 0,$$
then the orientation is reversed.
* If
$$\det(A) = 0,$$
then $u, v, w$ are linearly dependent, so the parallelepiped collapses into a lower-dimensional object and has zero volume.

There is also a familiar vector formula:
$$\det(u, v, w) = u \cdot (v \times w).$$
Thus the determinant in $\mathbb{R}^3$ is exactly the scalar triple product.
Geometrically, one may think of this as
$$\text{volume} = \text{base area} \times \text{height}.$$
Indeed, the magnitude of
$$v \times w$$
is the area of the base parallelogram spanned by $v$ and $w$, and then taking the dot product with $u$ extracts the signed height in the normal direction.
Therefore a linear map
$$A : \mathbb{R}^3 \to \mathbb{R}^3$$
scales all volumes by the factor
$$|\det(A)|.$$

<!-- page 181 -->

![Figure 2: In $\mathbb{R}^3$, the determinant measures signed volume.](figure_2.png)

**Examples.**

1. If
$$A = \begin{pmatrix} 2 & 0 & 0 \\ 0 & 3 & 0 \\ 0 & 0 & 4 \end{pmatrix},$$
then
$$\det(A) = 24.$$
So volumes are multiplied by 24.

2. If two columns of $A$ are equal, then
$$\det(A) = 0,$$
and the parallelepiped collapses.

3. If
$$A = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & -1 \end{pmatrix},$$
then
$$\det(A) = -1.$$
Thus volume is preserved, but orientation is reversed.

**General Rule** The two- and three-dimensional pictures suggest the general rule:

The determinant of a linear map measures the scaling of oriented volume.

In dimension $n$, if
$$A \in \mathbb{R}^{n \times n},$$

<!-- page 182 -->

then
$$|\det(A)|$$
is the factor by which $A$ scales $n$-dimensional volume, and the sign of $\det(A)$ records whether orientation is preserved or reversed.

This geometric interpretation explains many of the algebraic properties proved earlier:

* If
$$\det(A) = 0,$$
then volume collapses, so $A$ cannot be invertible.

* If
$$\det(AB) = \det(A) \det(B),$$
then the total scaling under a composition is the product of the two individual scalings.

* If two columns are swapped, orientation reverses, so the determinant changes sign.

* If one column is replaced by itself plus a multiple of another, the spanned area or volume does not change (you can verify this with a plot), which explains why the determinant is unchanged under such an operation.

# 6 Eigenvalues, Eigenvectors, and Diagonalization

## 6.1 Eigenvalues and Eigenvectors

In proposition 4.22, we saw that a one-dimensional subspace
$$\text{Span}(v), \quad v \neq 0,$$
is invariant under a linear transformation
$$T : V \to V$$
if and only if there exists a scalar $\lambda \in \mathbb{K}$ such that
$$T(v) = \lambda v.$$
Thus, on the one-dimensional subspace $\text{Span}(v)$, the transformation $T$ acts simply by multiplication by the scalar $\lambda$.

This observation leads to the fundamental notions of eigenvalues and eigenvectors.

<!-- page 183 -->

**Definition 6.1 — Eigenvalues and eigenvectors**

Let
$$T : V \to V$$
be a linear transformation. A scalar
$$\lambda \in \mathbb{K}$$
is called an **eigenvalue** of $T$ if there exists a nonzero vector
$$v \in V$$
such that
$$T(v) = \lambda v.$$
Any nonzero vector $v$ satisfying
$$T(v) = \lambda v$$
is called an **eigenvector** of $T$ corresponding to the eigenvalue $\lambda$.

The condition
$$v \neq 0$$
is essential. Indeed, the zero vector satisfies
$$T(0) = 0 = \lambda 0$$
for every scalar $\lambda \in \mathbb{K}$. Thus allowing $v = 0$ would make every scalar an eigenvalue of every linear transformation.

**Remark 6.2 — Geometric meaning of an eigenvector**

An eigenvector is a nonzero vector whose direction is preserved by the linear transformation. If
$$T(v) = \lambda v,$$
then $T(v)$ lies on the same line
$$\text{Span}(v)$$
as $v$.
The scalar $\lambda$ describes what $T$ does along that direction:
* if
$$\lambda > 1,$$

<!-- page 184 -->

the vector is stretched;
* if
$$0 < \lambda < 1,$$
the vector is contracted;
* if
$$\lambda < 0,$$
the direction is reversed as well as rescaled;
* if
$$\lambda = 0,$$
then
$$T(v) = 0.$$
Thus eigenvectors identify directions on which a linear transformation acts in the simplest possible way: by scalar multiplication.

**Example 6.3 — A simple example**

Consider
$$T : \mathbb{R}^2 \to \mathbb{R}^2$$
defined by
$$T \begin{pmatrix} x \\ y \end{pmatrix} = \begin{pmatrix} 2x \\ 3y \end{pmatrix}.$$
For
$$e_1 = \begin{pmatrix} 1 \\ 0 \end{pmatrix},$$
we have
$$T(e_1) = \begin{pmatrix} 2 \\ 0 \end{pmatrix} = 2e_1.$$
Hence
$$2$$
is an eigenvalue of $T$, and $e_1$ is a corresponding eigenvector.
Similarly,
$$T(e_2) = \begin{pmatrix} 0 \\ 3 \end{pmatrix} = 3e_2,$$
so
$$3$$

<!-- page 185 -->

is an eigenvalue and $e_2$ is a corresponding eigenvector.
More generally, every nonzero vector on the $x$-axis is an eigenvector corresponding to 2, and every nonzero vector on the $y$-axis is an eigenvector corresponding to 3.

The eigenvalue equation can be rewritten in a form that connects it directly to the kernel and invertibility theory developed earlier.
Starting from
$$T(v) = \lambda v,$$
we have
$$T(v) - \lambda v = 0.$$
Since
$$\lambda v = (\lambda I_V)(v),$$
this is equivalent to
$$(T - \lambda I_V)(v) = 0.$$
Thus finding eigenvectors corresponding to $\lambda$ amounts to finding nonzero vectors in the kernel of
$$T - \lambda I_V.$$

**Theorem 6.4 — Equivalent conditions for an eigenvalue**

Let $V$ be finite-dimensional, let
$$T : V \to V$$
be a linear transformation, and let
$$\lambda \in \mathbb{K}.$$
Then the following statements are equivalent:
(i) $\lambda$ is an eigenvalue of $T$;
(ii) there exists a nonzero vector $v \in V$ such that
$$(T - \lambda I_V)(v) = 0;$$
(iii)
$$\ker(T - \lambda I_V) \neq \{0\};$$
(iv) $T - \lambda I_V$ is not injective;
(v) $T - \lambda I_V$ is not surjective;
(vi) $T - \lambda I_V$ is not invertible.

<!-- page 186 -->

**Proof**

By definition 6.1, $\lambda$ is an eigenvalue of $T$ if and only if there exists
$$v \neq 0$$
such that
$$T(v) = \lambda v.$$
But
$$T(v) = \lambda v$$
if and only if
$$T(v) - \lambda v = 0,$$
which is equivalent to
$$(T - \lambda I_V)(v) = 0.$$
Hence
(i) $\iff$ (ii).
Statement (ii) says precisely that the kernel of $T - \lambda I_V$ contains a nonzero vector. Thus
(ii) $\iff$ (iii).
By the criterion for injectivity established earlier,
$$T - \lambda I_V \text{ is injective} \iff \ker(T - \lambda I_V) = \{0\}.$$
Therefore
(iii) $\iff$ (iv).
Finally,
$$T - \lambda I_V : V \to V$$
is a linear transformation from a finite-dimensional vector space to itself. Because the domain and codomain have the same dimension, the equivalence between injectivity, surjectivity, and invertibility proved earlier gives
(iv) $\iff$ (v) $\iff$ (vi).
Hence all six statements are equivalent.

We now translate the preceding discussion into matrix language.
Let
$$\mathcal{E} = (e_1, \dots, e_n)$$

<!-- page 187 -->

be a basis of $V$, and let
$$A = [T]_{\mathcal{E} \leftarrow \mathcal{E}}.$$
If
$$v \in V$$
has coordinate vector
$$x = [v]_{\mathcal{E}},$$
then
$$[T(v)]_{\mathcal{E}} = Ax.$$
Hence the eigenvalue equation
$$T(v) = \lambda v$$
is equivalent to
$$Ax = \lambda x.$$
Equivalently,
$$(A - \lambda I_n)x = 0.$$

**Definition 6.5 — Eigenvalues and eigenvectors of a matrix**

Let
$$A \in \mathbb{K}^{n \times n}.$$
A scalar
$$\lambda \in \mathbb{K}$$
is an **eigenvalue** of $A$ if there exists a nonzero vector
$$x \in \mathbb{K}^n$$
such that
$$Ax = \lambda x.$$
Such a nonzero vector $x$ is called an **eigenvector** of $A$ corresponding to $\lambda$.

Thus
$$Ax = \lambda x$$
if and only if
$$(A - \lambda I_n)x = 0.$$
Consequently, $\lambda$ is an eigenvalue of $A$ precisely when the homogeneous system
$$(A - \lambda I_n)x = 0$$

<!-- page 188 -->

has a nonzero solution.

**Proposition 6.6 — Matrix criterion for an eigenvalue**

Let
$$A \in \mathbb{K}^{n \times n}$$
and let
$$\lambda \in \mathbb{K}.$$
Then the following statements are equivalent:
(i) $\lambda$ is an eigenvalue of $A$;
(ii)
$$\ker(A - \lambda I_n) \neq \{0\};$$
(iii)
$$\text{Rank}(A - \lambda I_n) < n;$$
(iv) $A - \lambda I_n$ is not invertible;
(v)
$$\det(A - \lambda I_n) = 0.$$

**Proof**

By definition 6.5, $\lambda$ is an eigenvalue of $A$ if and only if there exists
$$x \neq 0$$
such that
$$Ax = \lambda x.$$
Equivalently,
$$(A - \lambda I_n)x = 0.$$
Thus
(i) $\iff$ (ii).
By the matrix form of the rank-nullity theorem,
$$n = \text{Rank}(A - \lambda I_n) + \dim \ker(A - \lambda I_n).$$
Therefore
$$\ker(A - \lambda I_n) \neq \{0\}$$
if and only if
$$\text{Rank}(A - \lambda I_n) < n.$$

<!-- page 189 -->

Hence
(ii) $\iff$ (iii).
By corollary 3.57,
$$\text{Rank}(A - \lambda I_n) = n \iff A - \lambda I_n \text{ is invertible}.$$
Thus
(iii) $\iff$ (iv).
Finally, by the determinant criterion for invertibility, theorem 5.23,
$$A - \lambda I_n \text{ is invertible} \iff \det(A - \lambda I_n) \neq 0.$$
Therefore
(iv) $\iff$ (v).
Hence all five statements are equivalent.

The final condition,
$$\det(A - \lambda I_n) = 0,$$
is particularly important. It converts the search for eigenvalues into the problem of solving a scalar polynomial equation. We will formalize this observation when we introduce the characteristic polynomial.

**Example 6.7 — Finding eigenvalues of a $2 \times 2$ matrix**

Consider
$$A = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix}.$$
A scalar $\lambda$ is an eigenvalue precisely when
$$\det(A - \lambda I_2) = 0.$$
Now
$$A - \lambda I_2 = \begin{pmatrix} 2 - \lambda & 1 \\ 1 & 2 - \lambda \end{pmatrix},$$

<!-- page 190 -->

so
$$\det(A - \lambda I_2) = \det \begin{pmatrix} 2 - \lambda & 1 \\ 1 & 2 - \lambda \end{pmatrix}$$
$$= (2 - \lambda)^2 - 1$$
$$= \lambda^2 - 4\lambda + 3$$
$$= (\lambda - 1)(\lambda - 3).$$
Thus the eigenvalues are
$$\lambda = 1 \quad \text{and} \quad \lambda = 3.$$
For $\lambda = 3$, we solve
$$(A - 3I_2)x = 0 :$$
$$\begin{pmatrix} -1 & 1 \\ 1 & -1 \end{pmatrix} \begin{pmatrix} x_1 \\ x_2 \end{pmatrix} = \begin{pmatrix} 0 \\ 0 \end{pmatrix}.$$
Hence
$$x_1 = x_2.$$
Thus every nonzero vector of the form
$$\begin{pmatrix} t \\ t \end{pmatrix}, \quad t \neq 0,$$
is an eigenvector corresponding to $\lambda = 3$.
For $\lambda = 1$,
$$(A - I_2)x = 0$$
becomes
$$\begin{pmatrix} 1 & 1 \\ 1 & 1 \end{pmatrix} \begin{pmatrix} x_1 \\ x_2 \end{pmatrix} = \begin{pmatrix} 0 \\ 0 \end{pmatrix},$$
so
$$x_1 = -x_2.$$
Hence every nonzero vector of the form
$$\begin{pmatrix} t \\ -t \end{pmatrix}, \quad t \neq 0,$$
is an eigenvector corresponding to $\lambda = 1$.

<!-- page 191 -->

## 6.2 Eigenspaces

For a fixed eigenvalue $\lambda$, there are usually many corresponding eigenvectors. Because scalar multiples and sums of eigenvectors corresponding to the same eigenvalue remain associated with that eigenvalue, it is natural to collect them into a subspace.
Recall from theorem 6.4 that
$$T(v) = \lambda v$$
is equivalent to
$$(T - \lambda I_V)(v) = 0.$$
Thus the relevant subspace is the kernel of $T - \lambda I_V$.

**Definition 6.8 — Eigenspace**

Let
$$T : V \to V$$
be a linear transformation and let
$$\lambda \in \mathbb{K}.$$
The **eigenspace** of $T$ corresponding to $\lambda$ is
$$E_\lambda(T) := \ker(T - \lambda I_V).$$
Equivalently,
$$E_\lambda(T) = \{v \in V : T(v) = \lambda v\}.$$

Because $E_\lambda(T)$ is a kernel, it is automatically a subspace of $V$ by the earlier result that kernels of linear maps are subspaces.
Notice an important distinction:
$$E_\lambda(T)$$
contains the zero vector, whereas an eigenvector is required to be nonzero.
Thus, if $\lambda$ is an eigenvalue,
$$E_\lambda(T) \setminus \{0\}$$
is precisely the set of eigenvectors corresponding to $\lambda$.

**Proposition 6.9 — Eigenvalues and nonzero eigenspaces**

Let
$$T : V \to V$$

<!-- page 192 -->

be linear and let
$$\lambda \in \mathbb{K}.$$
Then
$$\lambda \text{ is an eigenvalue of } T \iff E_\lambda(T) \neq \{0\}.$$

**Proof**

By definition 6.1, $\lambda$ is an eigenvalue of $T$ if and only if there exists a nonzero vector $v \in V$ such that
$$T(v) = \lambda v.$$
By definition 6.8, this is equivalent to the existence of a nonzero vector
$$v \in E_\lambda(T).$$
Hence
$$\lambda \text{ is an eigenvalue} \iff E_\lambda(T) \neq \{0\}.$$

**Proposition 6.10 — An eigenspace is invariant**

Let
$$T : V \to V$$
be linear and let $\lambda \in \mathbb{K}$. Then
$$E_\lambda(T)$$
is invariant under $T$.
Moreover, the restriction of $T$ to $E_\lambda(T)$ is simply scalar multiplication by $\lambda$:
$$T|_{E_\lambda(T)} = \lambda I_{E_\lambda(T)}.$$

**Proof**

Let
$$v \in E_\lambda(T).$$
By definition 6.8,
$$T(v) = \lambda v.$$
Because $E_\lambda(T)$ is a subspace and $v \in E_\lambda(T)$,
$$\lambda v \in E_\lambda(T).$$

<!-- page 193 -->

Hence
$$T(v) \in E_\lambda(T).$$
Therefore $E_\lambda(T)$ is invariant under $T$.
Furthermore, for every
$$v \in E_\lambda(T),$$
we have
$$T(v) = \lambda v.$$
Thus, on this subspace,
$$T|_{E_\lambda(T)} = \lambda I_{E_\lambda(T)}.$$

Thus an eigenspace is a subspace on which the transformation has the simplest possible form: it acts as multiplication by a single scalar.

**Example 6.11 — Eigenspaces of a matrix**

Consider again
$$A = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix}.$$
In example 6.7, we found the eigenvalues
$$\lambda = 3 \quad \text{and} \quad \lambda = 1.$$
For $\lambda = 3$,
$$E_3(A) = \ker(A - 3I_2).$$
Since
$$A - 3I_2 = \begin{pmatrix} -1 & 1 \\ 1 & -1 \end{pmatrix},$$
the equation
$$(A - 3I_2)x = 0$$
implies
$$x_1 = x_2.$$
Therefore
$$E_3(A) = \text{Span}\left(\begin{pmatrix} 1 \\ 1 \end{pmatrix}\right).$$
Similarly,
$$E_1(A) = \ker(A - I_2),$$

<!-- page 194 -->

and
$$A - I_2 = \begin{pmatrix} 1 & 1 \\ 1 & 1 \end{pmatrix}.$$
Thus
$$x_1 = -x_2,$$
and hence
$$E_1(A) = \text{Span}\left(\begin{pmatrix} 1 \\ -1 \end{pmatrix}\right).$$
In this example,
$$\mathbb{R}^2 = E_3(A) \oplus E_1(A).$$

The last equation in the example illustrates a general phenomenon: eigenspaces corresponding to distinct eigenvalues do not overlap except at the zero vector.

**Proposition 6.12 — Distinct eigenspaces intersect trivially**

Let
$$T : V \to V$$
be linear, and let
$$\lambda, \mu \in \mathbb{K}, \quad \lambda \neq \mu.$$
Then
$$E_\lambda(T) \cap E_\mu(T) = \{0\}.$$

**Proof**

Let
$$v \in E_\lambda(T) \cap E_\mu(T).$$
Then
$$T(v) = \lambda v$$
and
$$T(v) = \mu v.$$
Therefore
$$\lambda v = \mu v,$$
so
$$(\lambda - \mu)v = 0.$$

<!-- page 195 -->

Because
$$\lambda \neq \mu,$$
we have
$$\lambda - \mu \neq 0.$$
Since $\mathbb{K}$ is a field, it follows that
$$v = 0.$$
Hence
$$E_\lambda(T) \cap E_\mu(T) = \{0\}.$$

By corollary 4.10, we immediately obtain
$$E_\lambda(T) + E_\mu(T) = E_\lambda(T) \oplus E_\mu(T)$$
whenever
$$\lambda \neq \mu.$$

For more than two eigenspaces, pairwise trivial intersections alone are not sufficient to establish that the whole sum is direct. Nevertheless, distinct eigenspaces satisfy the stronger condition required for a direct sum.

**Theorem 6.13 — Eigenspaces corresponding to distinct eigenvalues form a direct sum**

Let
$$T : V \to V$$
be a linear transformation, and let
$$\lambda_1, \dots, \lambda_m$$
be distinct eigenvalues of $T$.
Then
$$E_{\lambda_1}(T) + \dots + E_{\lambda_m}(T)$$
is a direct sum. Thus
$$E_{\lambda_1}(T) \oplus \dots \oplus E_{\lambda_m}(T).$$

**Proof**

By theorem 4.9, it is enough to prove that the only way to write
$$0 = v_1 + \dots + v_m, \quad v_i \in E_{\lambda_i}(T),$$

<!-- page 196 -->

is with
$$v_1 = \dots = v_m = 0.$$
We prove this by induction on $m$.
For
$$m = 1,$$
the result is immediate.
Now suppose the result holds for $m - 1$ distinct eigenvalues, and suppose
$$v_1 + \dots + v_m = 0, \quad v_i \in E_{\lambda_i}(T).$$
Apply the linear transformation
$$T - \lambda_m I_V$$
to both sides. We obtain
$$(T - \lambda_m I_V)(v_1) + \dots + (T - \lambda_m I_V)(v_m) = 0.$$
Because
$$v_i \in E_{\lambda_i}(T),$$
we have
$$T(v_i) = \lambda_i v_i.$$
Hence
$$(T - \lambda_m I_V)(v_i) = (\lambda_i - \lambda_m)v_i.$$
For $i = m$,
$$(\lambda_m - \lambda_m)v_m = 0.$$
Therefore
$$(\lambda_1 - \lambda_m)v_1 + \dots + (\lambda_{m-1} - \lambda_m)v_{m-1} = 0.$$
For each
$$i = 1, \dots, m - 1,$$
the vector
$$(\lambda_i - \lambda_m)v_i$$
belongs to $E_{\lambda_i}(T)$ because $E_{\lambda_i}(T)$ is a subspace.
The eigenvalues
$$\lambda_1, \dots, \lambda_{m-1}$$

<!-- page 197 -->

are distinct. By the induction hypothesis,
$$(\lambda_i - \lambda_m)v_i = 0 \quad \text{for every } i = 1, \dots, m - 1.$$
Since the eigenvalues are all distinct,
$$\lambda_i - \lambda_m \neq 0.$$
Thus
$$v_i = 0, \quad i = 1, \dots, m - 1.$$
Returning to
$$v_1 + \dots + v_m = 0,$$
we obtain
$$v_m = 0.$$
Hence
$$v_1 = \dots = v_m = 0.$$
By theorem 4.9, the sum is direct.

This theorem gives two important consequences.

**Corollary 6.14 — Eigenvectors corresponding to distinct eigenvalues are linearly independent**

Let
$$v_1, \dots, v_m$$
be eigenvectors of $T$ corresponding to distinct eigenvalues
$$\lambda_1, \dots, \lambda_m.$$
Then
$$v_1, \dots, v_m$$
are linearly independent.

**Proof**

Suppose
$$c_1 v_1 + \dots + c_m v_m = 0.$$
For each $i$,
$$c_i v_i \in E_{\lambda_i}(T).$$

<!-- page 198 -->

By theorem 6.13, the representation of the zero vector as a sum of vectors from the distinct eigenspaces is unique. Hence
$$c_i v_i = 0 \quad \text{for every } i.$$
Because each $v_i$ is nonzero,
$$c_i = 0 \quad \text{for every } i.$$
Therefore
$$v_1, \dots, v_m$$
are linearly independent.

**Corollary 6.15 — Number and dimensions of distinct eigenspaces**

Suppose $V$ is finite-dimensional and
$$\lambda_1, \dots, \lambda_m$$
are distinct eigenvalues of $T$. Then
$$\dim E_{\lambda_1}(T) + \dots + \dim E_{\lambda_m}(T) \leq \dim V.$$
In particular,
$$m \leq \dim V.$$
Thus a linear transformation on an $n$-dimensional vector space has at most $n$ distinct eigenvalues.

**Proof**

By theorem 6.13,
$$E_{\lambda_1}(T) + \dots + E_{\lambda_m}(T) = E_{\lambda_1}(T) \oplus \dots \oplus E_{\lambda_m}(T).$$
Therefore, by the dimension characterization of a direct sum in theorem 4.9,
$$\dim (E_{\lambda_1}(T) + \dots + E_{\lambda_m}(T)) = \sum_{i=1}^m \dim E_{\lambda_i}(T).$$
The sum is a subspace of $V$, so
$$\dim (E_{\lambda_1}(T) + \dots + E_{\lambda_m}(T)) \leq \dim V.$$
Hence
$$\sum_{i=1}^m \dim E_{\lambda_i}(T) \leq \dim V.$$

<!-- page 199 -->

Because each $\lambda_i$ is an eigenvalue,
$$E_{\lambda_i}(T) \neq \{0\}$$
by proposition 6.9. Thus
$$\dim E_{\lambda_i}(T) \geq 1.$$
Therefore
$$m \leq \sum_{i=1}^m \dim E_{\lambda_i}(T) \leq \dim V.$$

For a matrix, the same construction takes a particularly concrete form.

**Definition 6.16 — Eigenspace of a matrix**

Let
$$A \in \mathbb{K}^{n \times n}$$
and let $\lambda \in \mathbb{K}$.
The eigenspace of $A$ corresponding to $\lambda$ is
$$E_\lambda(A) = \ker(A - \lambda I_n).$$
Thus
$$E_\lambda(A) = \{x \in \mathbb{K}^n : Ax = \lambda x\}.$$

If $\lambda$ is an eigenvalue, then
$$\dim E_\lambda(A) = \dim \ker(A - \lambda I_n).$$
By the matrix rank–nullity theorem,
$$\dim E_\lambda(A) = n - \text{Rank}(A - \lambda I_n).$$
Thus the dimension of an eigenspace can be computed directly from the rank of
$$A - \lambda I_n.$$

**Remark 6.17 — The role of eigenspaces**

An eigenspace is more than a collection of eigenvectors plus the zero vector. It is an invariant subspace on which $T$ acts as scalar multiplication:
$$T|_{E_\lambda(T)} = \lambda I.$$

<!-- page 200 -->

Moreover, eigenspaces corresponding to distinct eigenvalues combine without overlap:
$$E_{\lambda_1}(T) \oplus \dots \oplus E_{\lambda_m}(T).$$
The central question for diagonalization will therefore be whether these eigenspaces are large enough, collectively, to fill the entire vector space:
$$V \stackrel{?}{=} \bigoplus_\lambda E_\lambda(T).$$

**6.3 Eigenvalues and the Characteristic Polynomial**

In proposition 6.6, we showed that a scalar $\lambda \in \mathbb{K}$ is an eigenvalue of
$$A \in \mathbb{K}^{n \times n}$$
if and only if
$$A - \lambda I_n$$
is singular. By the determinant criterion for invertibility, theorem 5.23, this is equivalent to
$$\det(A - \lambda I_n) = 0.$$
Thus the eigenvalues of $A$ can be found by studying the determinant
$$\det(A - \lambda I_n)$$
as a polynomial in $\lambda$.

**Definition 6.18 — Characteristic polynomial and characteristic equation**

Let
$$A \in \mathbb{K}^{n \times n}.$$
The **characteristic polynomial** of $A$ is
$$\chi_A(\lambda) := \det(A - \lambda I_n).$$
The equation
$$\chi_A(\lambda) = 0,$$
that is,
$$\det(A - \lambda I_n) = 0,$$

<!-- page 201 -->

is called the **characteristic equation** of $A$.

**Proposition 6.19 — Degree and leading term of the characteristic polynomial**

Let
$$A \in \mathbb{K}^{n \times n}.$$
Then $\chi_A(\lambda)$ is a polynomial of degree $n$, with leading coefficient $(-1)^n$.
Thus
$$\chi_A(\lambda) = (-1)^n \lambda^n + c_{n-1} \lambda^{n-1} + \dots + c_1 \lambda + c_0$$
for some
$$c_0, \dots, c_{n-1} \in \mathbb{K}.$$
Moreover,
$$c_0 = \det(A).$$

**Proof**

By definition,
$$\chi_A(\lambda) = \det(A - \lambda I_n).$$
Using the permutation formula from theorem 5.4,
$$\chi_A(\lambda) = \sum_{\sigma \in S_n} \text{sgn}(\sigma) \prod_{j=1}^n (A - \lambda I_n)_{\sigma(j), j}.$$
Consider first the term corresponding to the identity permutation. It is
$$(a_{11} - \lambda)(a_{22} - \lambda) \dots (a_{nn} - \lambda).$$
Its highest-degree term is
$$(-\lambda)^n = (-1)^n \lambda^n.$$
Now consider a nonidentity permutation $\sigma$. Then for at least one $j$,
$$\sigma(j) \neq j.$$
The corresponding factor
$$(A - \lambda I_n)_{\sigma(j), j} = a_{\sigma(j), j}$$
is an off-diagonal entry and therefore contains no $\lambda$. Consequently, every term arising from a nonidentity permutation has degree at most $n - 1$.

<!-- page 202 -->

Hence
$$\deg \chi_A = n$$
and its leading coefficient is
$$(-1)^n.$$
Finally, evaluating at $\lambda = 0$ gives
$$\chi_A(0) = \det(A - 0I_n) = \det(A).$$
Thus the constant term is
$$c_0 = \det(A).$$

The characteristic polynomial is important because its roots are exactly the eigenvalues.

**Theorem 6.20 — Eigenvalues are roots of the characteristic polynomial**

Let
$$A \in \mathbb{K}^{n \times n}$$
and let
$$\lambda \in \mathbb{K}.$$
Then
$$\lambda \text{ is an eigenvalue of } A \iff \chi_A(\lambda) = 0.$$

**Proof**

See the beginning discussion of this subsection.

Thus finding the eigenvalues of a matrix can be separated into two steps:
$$A \longrightarrow \chi_A(\lambda) = \det(A - \lambda I_n) \longrightarrow \chi_A(\lambda) = 0.$$
Once an eigenvalue $\lambda$ has been found, the corresponding eigenspace is obtained by solving
$$(A - \lambda I_n)x = 0 :$$
$$E_\lambda(A) = \ker(A - \lambda I_n).$$

<!-- page 203 -->

**Example 6.21 — Characteristic polynomial of a $2 \times 2$ matrix**

Let
$$A = \begin{pmatrix} a & b \\ c & d \end{pmatrix}.$$
Then
$$A - \lambda I_2 = \begin{pmatrix} a - \lambda & b \\ c & d - \lambda \end{pmatrix},$$
and therefore
$$\chi_A(\lambda) = \det \begin{pmatrix} a - \lambda & b \\ c & d - \lambda \end{pmatrix}$$
$$= (a - \lambda)(d - \lambda) - bc$$
$$= \lambda^2 - (a + d)\lambda + (ad - bc).$$
Since
$$\text{tr}(A) = a + d$$
and
$$\det(A) = ad - bc,$$
we obtain
$$\chi_A(\lambda) = \lambda^2 - \text{tr}(A)\lambda + \det(A).$$
Thus the eigenvalues of $A$ are precisely the roots of
$$\lambda^2 - \text{tr}(A)\lambda + \det(A) = 0.$$

**Example 6.22 — A $3 \times 3$ example**

Consider
$$A = \begin{pmatrix} 2 & 1 & 0 \\ 0 & 3 & 0 \\ 0 & 0 & 4 \end{pmatrix}.$$
Then
$$A - \lambda I_3 = \begin{pmatrix} 2 - \lambda & 1 & 0 \\ 0 & 3 - \lambda & 0 \\ 0 & 0 & 4 - \lambda \end{pmatrix}.$$
Because this matrix is upper triangular, theorem 5.16 gives
$$\chi_A(\lambda) = \det(A - \lambda I_3)$$
$$= (2 - \lambda)(3 - \lambda)(4 - \lambda).$$

<!-- page 204 -->

Thus the eigenvalues are
$$2, \quad 3, \quad 4.$$
Notice that the leading term is
$$-\lambda^3,$$
as predicted by proposition 6.19.

The characteristic polynomial should depend only on the linear transformation represented by a matrix, not on the particular basis used to represent it. The next result verifies this fact.

**Proposition 6.23 — Similar matrices have the same characteristic polynomial**

Let
$$A, B \in \mathbb{K}^{n \times n}.$$
If $A$ and $B$ are similar, then
$$\chi_A(\lambda) = \chi_B(\lambda).$$

**Proof**

Suppose
$$B = P^{-1}AP$$
for some invertible matrix
$$P \in \mathbb{K}^{n \times n}.$$
Then
$$B - \lambda I_n = P^{-1}AP - \lambda I_n$$
$$= P^{-1}AP - \lambda P^{-1}P$$
$$= P^{-1}(A - \lambda I_n)P.$$
Hence
$$B - \lambda I_n$$
is similar to
$$A - \lambda I_n.$$
By corollary 5.29,
$$\det(B - \lambda I_n) = \det(A - \lambda I_n).$$
Therefore
$$\chi_B(\lambda) = \chi_A(\lambda).$$

This similarity invariance allows us to define the characteristic polynomial of an abstract linear transformation.

<!-- page 205 -->

**Definition 6.24 — Characteristic polynomial of a linear transformation**

Let
$$T : V \to V$$
be a linear transformation on an $n$-dimensional vector space $V$.
Choose any basis
$$\mathcal{E}$$
of $V$, and let
$$A = [T]_{\mathcal{E} \leftarrow \mathcal{E}}.$$
The **characteristic polynomial** of $T$ is defined by
$$\chi_T(\lambda) := \chi_A(\lambda) = \det(A - \lambda I_n).$$

**Proposition 6.25 — The characteristic polynomial is basis-independent**

The definition in definition 6.24 does not depend on the chosen basis of $V$.

**Proof**

Let
$$\mathcal{E} \quad \text{and} \quad \mathcal{E}'$$
be two bases of $V$.
By the change-of-basis formula,
$$[T]_{\mathcal{E}' \leftarrow \mathcal{E}'} = P^{-1}[T]_{\mathcal{E} \leftarrow \mathcal{E}} P$$
for some invertible matrix $P$.
Thus the two matrices representing $T$ are similar. By proposition 6.23, they have the same characteristic polynomial.

**Corollary 6.26 — Eigenvalues of a linear transformation**

Let $V$ be finite-dimensional and let
$$T : V \to V$$
be linear. Then
$$\lambda \in \mathbb{K}$$

<!-- page 206 -->

is an eigenvalue of $T$ if and only if
$$\chi_T(\lambda) = 0.$$

**Proof**

Choose a basis, and then invoke theorem 6.20 and definition 6.24.

**Remark 6.27 — The characteristic polynomial and the scalar field**

The characteristic polynomial may fail to have a root in the scalar field over which the vector space is defined.
For example,
$$A = \begin{pmatrix} 0 & -1 \\ 1 & 0 \end{pmatrix}$$
has
$$\chi_A(\lambda) = \det \begin{pmatrix} -\lambda & -1 \\ 1 & -\lambda \end{pmatrix}$$
$$= \lambda^2 + 1.$$
Over $\mathbb{R}$, the equation
$$\lambda^2 + 1 = 0$$
has no solution. Thus $A$ has no real eigenvalues.
Over $\mathbb{C}$, however,
$$\lambda^2 + 1 = (\lambda - i)(\lambda + i),$$
so the eigenvalues are
$$i \quad \text{and} \quad -i.$$
Thus the existence of eigenvalues depends on the scalar field.

**Corollary 6.28 — Existence of an eigenvalue over $\mathbb{C}$**

Let $V$ be a nonzero finite-dimensional complex vector space and let
$$T : V \to V$$
be linear. Then $T$ has at least one eigenvalue.

<!-- page 207 -->

**Proof**

Let
$$n = \dim V \geq 1.$$
By proposition 6.19,
$$\chi_T(\lambda)$$
is a polynomial of degree $n$, and hence is nonconstant.
By the Fundamental Theorem of Algebra, every nonconstant polynomial with complex coefficients has a complex root. Thus there exists
$$\lambda \in \mathbb{C}$$
such that
$$\chi_T(\lambda) = 0.$$
By corollary 6.26, $\lambda$ is an eigenvalue of $T$.

We also need to distinguish how many times an eigenvalue occurs as a root of the characteristic polynomial from the dimension of its eigenspace.

**Definition 6.29 — Algebraic and geometric multiplicity**

Let
$$T : V \to V$$
be a linear transformation on a finite-dimensional vector space, and let $\lambda_0$ be an eigenvalue of $T$.
The **algebraic multiplicity** of $\lambda_0$ is its multiplicity as a root of the characteristic polynomial
$$\chi_T(\lambda).$$
More precisely, the algebraic multiplicity is the largest positive integer $m$ such that
$$(\lambda - \lambda_0)^m$$
divides $\chi_T(\lambda)$.
The **geometric multiplicity** of $\lambda_0$ is the dimension of the corresponding eigenspace:
$$\dim E_{\lambda_0}(T) = \dim \ker(T - \lambda_0 I_V).$$

<!-- page 208 -->

**Example 6.30 — Algebraic multiplicity need not determine the eigenspace**

Consider the two matrices
$$A = \begin{pmatrix} 2 & 0 \\ 0 & 2 \end{pmatrix}, \quad B = \begin{pmatrix} 2 & 1 \\ 0 & 2 \end{pmatrix}.$$
For both matrices,
$$\chi(\lambda) = \det \begin{pmatrix} 2 - \lambda & * \\ 0 & 2 - \lambda \end{pmatrix} = (2 - \lambda)^2.$$
Thus 2 has algebraic multiplicity 2 for both $A$ and $B$.
For $A$,
$$A - 2I_2 = 0,$$
so
$$E_2(A) = \mathbb{R}^2$$
and
$$\dim E_2(A) = 2.$$
For $B$,
$$B - 2I_2 = \begin{pmatrix} 0 & 1 \\ 0 & 0 \end{pmatrix},$$
so
$$E_2(B) = \ker(B - 2I_2) = \text{Span} \left( \begin{pmatrix} 1 \\ 0 \end{pmatrix} \right),$$
and therefore
$$\dim E_2(B) = 1.$$
Thus the same characteristic polynomial can correspond to different eigenspace dimensions.

**Remark 6.31 — Algebraic versus geometric multiplicity**

For every eigenvalue $\lambda_0$, its geometric multiplicity is at least one:
$$\dim E_{\lambda_0}(T) \geq 1.$$
We will shortly prove the stronger inequality
$$1 \leq \dim E_{\lambda_0}(T) \leq \text{algebraic multiplicity of } \lambda_0.$$
The relation between these two multiplicities is central to diagonalization.

<!-- page 209 -->

**6.4 Diagonalization**

The natural question in this section is whether the entire vector space can be decomposed into such directions.
Equivalently:
*Does $V$ have a basis consisting entirely of eigenvectors of $T$?*

If the answer is yes, then the matrix of $T$ in that basis is diagonal. Recall the form of a diagonal matrix from corollary 5.17.

**Definition 6.32 — Diagonalizable linear transformation**

Let
$$T : V \to V$$
be a linear transformation on a finite-dimensional vector space.
We say that $T$ is **diagonalizable** if there exists a basis $\mathcal{E}$ of $V$ such that
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}}$$
is diagonal.

The definition is equivalent to the existence of a basis of eigenvectors.

**Theorem 6.33 — Diagonalization and eigenvector bases**

Let
$$T : V \to V$$
be a linear transformation on an $n$-dimensional vector space.
Then $T$ is diagonalizable if and only if $V$ has a basis
$$v_1, \dots, v_n$$
consisting of eigenvectors of $T$.
More precisely, if
$$T(v_i) = \lambda_i v_i, \quad i = 1, \dots, n,$$
then with respect to the basis
$$\mathcal{E} = (v_1, \dots, v_n),$$
the matrix
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}}$$

<!-- page 210 -->

is diagonal, with diagonal entries
$$\lambda_1, \dots, \lambda_n.$$

**Proof**

Suppose first that
$$\mathcal{E} = (v_1, \dots, v_n)$$
is a basis consisting of eigenvectors, with
$$T(v_i) = \lambda_i v_i.$$
Then
$$[T(v_i)]_{\mathcal{E}} = \lambda_i [v_i]_{\mathcal{E}}.$$
Thus the $i$th column of
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}}$$
has $\lambda_i$ in the $i$th position and zeros elsewhere. Hence the matrix is diagonal.
Conversely, suppose
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}}$$
is diagonal for some basis
$$\mathcal{E} = (v_1, \dots, v_n).$$
If its $i$th diagonal entry is $\lambda_i$, then its $i$th column gives
$$[T(v_i)]_{\mathcal{E}} = \lambda_i [v_i]_{\mathcal{E}}.$$
Therefore
$$T(v_i) = \lambda_i v_i.$$
Thus every vector in $\mathcal{E}$ is an eigenvector of $T$.

Hence diagonalization has a simple geometric interpretation:
diagonalization = choosing a basis along eigenvector directions.

We can now express this in terms of the eigenspaces introduced earlier.

**Theorem 6.34 — Equivalent characterizations of diagonalizability**

Let
$$T : V \to V$$

<!-- page 211 -->

be a linear transformation on a finite-dimensional vector space, and let
$$\lambda_1, \dots, \lambda_m$$
be the distinct eigenvalues of $T$.
Then the following statements are equivalent:
(i) $T$ is diagonalizable;
(ii) $V$ has a basis consisting of eigenvectors of $T$;
(iii)
$$V = E_{\lambda_1}(T) \oplus \dots \oplus E_{\lambda_m}(T);$$
(iv)
$$\dim V = \dim E_{\lambda_1}(T) + \dots + \dim E_{\lambda_m}(T).$$

**Proof**

The equivalence
(i) $\iff$ (ii)
is theorem 6.33.
Suppose (ii) holds. Every vector in an eigenvector basis belongs to one of the eigenspaces
$$E_{\lambda_1}(T), \dots, E_{\lambda_m}(T).$$
Hence
$$V = E_{\lambda_1}(T) + \dots + E_{\lambda_m}(T).$$
By theorem 6.13, this sum is direct. Therefore
(ii) $\implies$ (iii).
If (iii) holds, then the dimension formula for a direct sum gives
$$\dim V = \sum_{i=1}^m \dim E_{\lambda_i}(T),$$
so
(iii) $\implies$ (iv).
Finally, suppose (iv) holds. For each $i$, choose a basis $\mathcal{B}_i$ of $E_{\lambda_i}(T)$. Since distinct eigenspaces form a direct sum, the concatenation
$$\mathcal{B}_1, \dots, \mathcal{B}_m$$

<!-- page 212 -->

is linearly independent by theorem 4.9.
By (iv), this list contains exactly $\dim V$ vectors. Hence, by proposition 1.21, it is a basis of $V$.
Every vector in the list is an eigenvector, and therefore
(iv) $\implies$ (ii).

Thus all four statements are equivalent.

The matrix formulation follows immediately from the linear transformation associated with a square matrix.

**Corollary 6.35 — Diagonalization of a matrix**

Let
$$A \in \mathbb{K}^{n \times n},$$
and define
$$T_A : \mathbb{K}^n \to \mathbb{K}^n, \quad T_A(x) = Ax.$$
Then $A$ is similar to a diagonal matrix if and only if $\mathbb{K}^n$ has a basis consisting of eigenvectors of $A$.
In particular, suppose
$$v_1, \dots, v_n$$
is such a basis, with
$$Av_i = \lambda_i v_i.$$
Let
$$P = \begin{pmatrix} | & | & & | \\ v_1 & v_2 & \dots & v_n \\ | & | & & | \end{pmatrix},$$
and let $D$ be the diagonal matrix whose diagonal entries are
$$\lambda_1, \dots, \lambda_n$$
in the corresponding order.
Then
$$P^{-1}AP = D.$$

**Proof**

The matrix of $T_A$ in the standard basis is $A$.

<!-- page 213 -->

By theorem 6.33, the basis
$$(v_1, \dots, v_n)$$
gives a diagonal matrix $D$ for the same linear transformation.
The change-of-basis formula in corollary 3.39 therefore gives
$$D = P^{-1}AP.$$

**Corollary 6.36 — Distinct eigenvalues imply diagonalizability**

Let
$$T : V \to V$$
be linear and suppose
$$\dim V = n.$$
If $T$ has $n$ distinct eigenvalues, then $T$ is diagonalizable.

**Proof**

Choose one eigenvector corresponding to each of the $n$ distinct eigenvalues.
By corollary 6.14, these $n$ eigenvectors are linearly independent. Since
$$\dim V = n,$$
they form a basis by proposition 1.21.
Hence $T$ is diagonalizable by theorem 6.33.

The converse is false. A diagonalizable transformation need not have $\dim V$ distinct eigenvalues.
What matters is the number of *linearly independent eigenvectors*, or equivalently, the dimensions of the eigenspaces.
This brings us back to the two notions of multiplicity introduced in definition 6.29.

**Theorem 6.37 — Geometric multiplicity is at most algebraic multiplicity**

Let
$$T : V \to V$$
be linear on a finite-dimensional vector space, and let $\lambda$ be an eigenvalue of $T$.
Then
$$1 \leq \dim E_{\lambda}(T) \leq m_a(\lambda),$$

<!-- page 214 -->

where
$$m_a(\lambda)$$
denotes the algebraic multiplicity of $\lambda$.
Thus
$$1 \leq m_g(\lambda) \leq m_a(\lambda).$$

**Proof**

Because $\lambda$ is an eigenvalue,
$$E_{\lambda}(T) \neq \{0\},$$
so
$$\dim E_{\lambda}(T) \geq 1.$$
Let
$$r = \dim E_{\lambda}(T),$$
and choose a basis
$$v_1, \dots, v_r$$
of $E_{\lambda}(T)$. They are linearly independent in $V$. By the basis extension result, proposition 3.10, we may extend this list to a basis
$$\mathcal{E} = (v_1, \dots, v_r, v_{r+1}, \dots, v_n)$$
of $V$.
Write
$$A = [T]_{\mathcal{E} \leftarrow \mathcal{E}}.$$
For
$$i = 1, \dots, r,$$
we have
$$T(v_i) = \lambda v_i.$$
Hence the first $r$ columns of $A$ have $\lambda$ in their corresponding diagonal positions and zero elsewhere.
Now consider
$$A - \mu I_n.$$
For each
$$i = 1, \dots, r,$$

<!-- page 215 -->

its $i$th column has the single nonzero entry
$$\lambda - \mu$$
in position $i$.
Because
$$v_1, \dots, v_r$$
belong to $E_{\lambda}(T)$, we have
$$T(v_i) = \lambda v_i, \quad i = 1, \dots, r.$$
Therefore, with respect to the basis
$$\mathcal{E} = (v_1, \dots, v_r, v_{r+1}, \dots, v_n),$$
the first $r$ columns of
$$A = [T]_{\mathcal{E} \leftarrow \mathcal{E}}$$
are
$$\lambda e_1, \dots, \lambda e_r.$$
Thus $A - \mu I_n$ has the form
$$A - \mu I_n = \left( \begin{array}{cccc|ccc} \lambda - \mu & 0 & \dots & 0 & * & \dots & * \\ 0 & \lambda - \mu & \dots & 0 & * & \dots & * \\ \vdots & \vdots & \ddots & \vdots & \vdots & & \vdots \\ 0 & 0 & \dots & \lambda - \mu & * & \dots & * \\ \hline 0 & 0 & \dots & 0 & & & \\ \vdots & \vdots & & \vdots & & B - \mu I_{n-r} & \\ 0 & 0 & \dots & 0 & & & \end{array} \right).$$
The vertical line separates the first $r$ columns, corresponding to the basis vectors
$$v_1, \dots, v_r,$$
from the remaining columns.
Now expand the determinant along the first column. Since its only nonzero entry is
$$\lambda - \mu,$$
we obtain one factor
$$\lambda - \mu.$$

<!-- page 216 -->

Continuing in this way through the first $r$ columns gives
$$\det(A - \mu I_n) = (\lambda - \mu)^r \det(B - \mu I_{n-r}).$$
Hence
$$\det(A - \mu I_n) = (\lambda - \mu)^r q(\mu),$$
where
$$q(\mu) = \det(B - \mu I_{n-r}).$$
Thus $\lambda$ is a root of the characteristic polynomial with multiplicity at least $r$. Therefore
$$m_a(\lambda) \geq r = \dim E_{\lambda}(T).$$

We immediately obtain the main multiplicity criterion for diagonalizability.

**Theorem 6.38 — Diagonalizability and multiplicities**

Let
$$T : V \to V$$
be linear on an $n$-dimensional vector space. Suppose its characteristic polynomial splits completely over $\mathbb{K}$.
Let
$$\lambda_1, \dots, \lambda_m$$
be distinct eigenvalues.
Then $T$ is diagonalizable if and only if
$$m_g(\lambda_i) = m_a(\lambda_i) \quad \text{for every } i = 1, \dots, m.$$

**Proof**

Because the characteristic polynomial has degree $n$ and splits over $\mathbb{K}$,
$$\sum_{i=1}^m m_a(\lambda_i) = n.$$
By theorem 6.37,
$$m_g(\lambda_i) \leq m_a(\lambda_i) \quad \text{for every } i.$$
Suppose first that
$$m_g(\lambda_i) = m_a(\lambda_i) \quad \text{for every } i.$$

<!-- page 217 -->

Then
$$\sum_{i=1}^m \dim E_{\lambda_i}(T) = \sum_{i=1}^m m_g(\lambda_i) = \sum_{i=1}^m m_a(\lambda_i) = n.$$
By theorem 6.34, $T$ is diagonalizable.
Conversely, suppose $T$ is diagonalizable. Then
$$\sum_{i=1}^m m_g(\lambda_i) = \sum_{i=1}^m \dim E_{\lambda_i}(T) = n.$$
But also
$$\sum_{i=1}^m m_a(\lambda_i) = n$$
and
$$m_g(\lambda_i) \leq m_a(\lambda_i)$$
for every $i$.
Therefore equality must hold term by term:
$$m_g(\lambda_i) = m_a(\lambda_i) \quad \text{for every } i.$$

**Remark 6.39 — What prevents diagonalization**
When the characteristic polynomial splits, failure of diagonalizability has a precise meaning.
For some eigenvalue $\lambda$,
$$m_g(\lambda) < m_a(\lambda).$$
Thus the characteristic polynomial says that $\lambda$ occurs several times algebraically, but its eigenspace does not contain enough independent eigenvectors to account for all of those occurrences.

There is another, very compact way to characterize this failure. It is based on the minimal polynomial.

**Definition 6.40 — Polynomial of a linear transformation**
Let
$$p(t) = a_0 + a_1 t + \dots + a_k t^k \in \mathbb{K}[t].$$
For
$$T: V \to V,$$
define
$$p(T) = a_0 I_V + a_1 T + \dots + a_k T^k.$$

<!-- page 218 -->

**Definition 6.41 — Minimal polynomial**
Let $V$ be finite-dimensional and let
$$T: V \to V$$
be linear.
The **minimal polynomial** of $T$, denoted
$$m_T(t),$$
is the unique monic polynomial of smallest degree such that
$$m_T(T) = 0.$$

Such a polynomial exists. Indeed, if
$$n = \dim V,$$
then
$$I_V, T, T^2, \dots, T^{n^2}$$
are $n^2 + 1$ elements of the $n^2$-dimensional vector space $\mathcal{L}(V)$, and hence are linearly dependent.
Thus some nonzero polynomial $p$ satisfies
$$p(T) = 0.$$
After dividing by its leading coefficient, we obtain a monic annihilating polynomial, and among all such polynomials we choose one of smallest degree.
Uniqueness follows because the difference of two distinct monic annihilating polynomials of the same smallest degree would be a nonzero annihilating polynomial of smaller degree.

**Proposition 6.42 — The minimal polynomial divides every annihilating polynomial**
Let
$$p \in \mathbb{K}[t].$$
If
$$p(T) = 0,$$
then
$$m_T(t) \mid p(t).$$

<!-- page 219 -->

**Proof**
By polynomial division, write
$$p(t) = q(t)m_T(t) + r(t),$$
where either $r = 0$ or
$$\deg r < \deg m_T.$$
Applying this identity to $T$ gives
$$0 = p(T) = q(T)m_T(T) + r(T) = r(T).$$
If $r \neq 0$, then after dividing $r$ by its leading coefficient we would obtain a monic annihilating polynomial of degree smaller than $m_T$, contradicting the definition of the minimal polynomial.
Hence
$$r = 0,$$
so
$$m_T \mid p.$$

The minimal polynomial contains exactly the obstruction to diagonalizability.

**Theorem 6.43 — Minimal-polynomial criterion for diagonalizability**
Let
$$T: V \to V$$
be linear on a finite-dimensional vector space.
Then $T$ is diagonalizable over $\mathbb{K}$ if and only if its minimal polynomial splits over $\mathbb{K}$ into distinct linear factors:
$$m_T(t) = (t - \lambda_1) \cdots (t - \lambda_m),$$
where
$$\lambda_1, \dots, \lambda_m$$
are distinct.

**Proof**
Suppose first that $T$ is diagonalizable, and let
$$\lambda_1, \dots, \lambda_m$$
be its distinct eigenvalues.

<!-- page 220 -->

Define
$$p(t) = (t - \lambda_1) \cdots (t - \lambda_m).$$
Because $V$ has a basis consisting of eigenvectors, it is enough to evaluate $p(T)$ on an eigenvector $v$ corresponding to some $\lambda_i$. We obtain
$$p(T)v = p(\lambda_i)v = 0.$$
Hence
$$p(T) = 0.$$
By proposition 6.42,
$$m_T \mid p.$$
On the other hand, every eigenvalue $\lambda_i$ must be a root of $m_T$. Indeed, if
$$T(v) = \lambda_i v, \quad v \neq 0,$$
then
$$0 = m_T(T)v = m_T(\lambda_i)v,$$
which implies
$$m_T(\lambda_i) = 0.$$
Thus each factor
$$t - \lambda_i$$
divides $m_T$. Since the $\lambda_i$ are distinct,
$$p \mid m_T.$$
Both polynomials are monic, so
$$m_T(t) = (t - \lambda_1) \cdots (t - \lambda_m).$$
Conversely, suppose
$$m_T(t) = (t - \lambda_1) \cdots (t - \lambda_m)$$
with the $\lambda_i$ distinct.
For each $i$, define the following polynomial (also called the Lagrange polynomial)
$$\ell_i(t) = \prod_{j \neq i} \frac{t - \lambda_j}{\lambda_i - \lambda_j}.$$

<!-- page 221 -->

Then
$$\ell_i(\lambda_j) = \begin{cases} 1, & j = i, \\ 0, & j \neq i. \end{cases}$$
Hence, by polynomial interpolation,
$$\ell_1(t) + \dots + \ell_m(t) = 1.$$
Applying this identity to $T$ gives
$$I_V = \ell_1(T) + \dots + \ell_m(T).$$
Therefore every
$$v \in V$$
can be written as
$$v = \ell_1(T)v + \dots + \ell_m(T)v.$$
Moreover,
$$(t - \lambda_i)\ell_i(t)$$
is a scalar multiple of $m_T(t)$. Hence
$$(T - \lambda_i I_V)\ell_i(T) = 0.$$
Therefore
$$\ell_i(T)v \in E_{\lambda_i}(T).$$
It follows that
$$V = E_{\lambda_1}(T) + \dots + E_{\lambda_m}(T).$$
By theorem 6.13, this sum is direct:
$$V = E_{\lambda_1}(T) \oplus \dots \oplus E_{\lambda_m}(T).$$
Hence $T$ is diagonalizable by theorem 6.34.

**Remark 6.44 — Three views of diagonalizability**
When the characteristic polynomial splits over $\mathbb{K}$, we now have three ways to recognize diagonalizability:

<!-- page 222 -->

$$T \text{ is diagonalizable} \iff V \text{ has a basis of eigenvectors,}$$
$$\iff m_g(\lambda) = m_a(\lambda) \text{ for every eigenvalue } \lambda,$$
$$\iff m_T(t) \text{ has no repeated linear factor.}$$
The first condition is geometric, the second compares the eigenspaces with the characteristic polynomial, and the third records the same information compactly in the minimal polynomial.

**Example 6.45 — Repeated eigenvalues: two different possibilities**
Consider
$$A = \begin{pmatrix} 2 & 0 \\ 0 & 2 \end{pmatrix}, \quad B = \begin{pmatrix} 2 & 1 \\ 0 & 2 \end{pmatrix}.$$
Both matrices have characteristic polynomial
$$(2 - \lambda)^2.$$
Thus 2 has algebraic multiplicity 2 in both cases.
For $A$,
$$E_2(A) = \mathbb{K}^2,$$
so
$$m_g(2) = 2 = m_a(2).$$
Moreover,
$$m_A(t) = t - 2.$$
Hence $A$ is diagonalizable.
For $B$,
$$E_2(B) = \text{Span}\left(\begin{pmatrix} 1 \\ 0 \end{pmatrix}\right),$$
so
$$m_g(2) = 1 < 2 = m_a(2).$$
Its minimal polynomial is
$$m_B(t) = (t - 2)^2.$$
Hence $B$ is not diagonalizable.
Thus a repeated root of the characteristic polynomial does not by itself prevent diagonalization. The issue is whether there are enough independent eigenvectors, or equivalently, whether the corresponding factor is repeated in the minimal polynomial.

<!-- page 223 -->

**Remark 6.46 — Why diagonalization is useful**
If
$$A = PDP^{-1}$$
with $D$ diagonal, then for every positive integer $k$,
$$A^k = PD^k P^{-1}.$$
Powers of a diagonal matrix are immediate to compute: each diagonal entry is simply raised to the $k$th power.
Thus diagonalization converts repeated application of a complicated linear transformation into repeated scalar multiplication along its eigenvector directions.

# 7 Inner Product Spaces and Quadratic Forms
So far, our study of vector spaces has been primarily algebraic. We can add vectors, multiply them by scalars, choose bases, and study linear transformations between them. What is still missing is the geometric structure familiar from $\mathbb{R}^2$ and $\mathbb{R}^3$: length, angle, and perpendicularity.
An *inner product* equips a vector space with this geometry.

## 7.1 Inner Products, Norms, and Orthogonality
For vectors
$$x = (x_1, \dots, x_n), \quad y = (y_1, \dots, y_n)$$
in $\mathbb{R}^n$, recall the Euclidean dot product
$$x^\top y = x_1 y_1 + \dots + x_n y_n.$$
It contains geometric information that the vector-space operations alone do not provide. In particular,
$$x^\top x = x_1^2 + \dots + x_n^2$$
is the square of the Euclidean length of $x$, while
$$x^\top y = 0$$
means that $x$ and $y$ are perpendicular.
An inner product abstracts the essential properties of this operation.

<!-- page 224 -->

**Definition 7.1 — Inner product**
Let $V$ be a vector space over
$$\mathbb{K} = \mathbb{R} \quad \text{or} \quad \mathbb{K} = \mathbb{C}.$$
An **inner product** on $V$ is a function
$$\langle \cdot, \cdot \rangle : V \times V \to \mathbb{K}$$
such that, for all
$$u, v, w \in V, \quad \alpha, \beta \in \mathbb{K},$$
the following properties hold:
(i) **Linearity in the first argument:**
$$\langle \alpha u + \beta v, w \rangle = \alpha \langle u, w \rangle + \beta \langle v, w \rangle.$$
(ii) **Conjugate symmetry:**
$$\langle u, v \rangle = \overline{\langle v, u \rangle}.$$
(iii) **Positive definiteness:**
$$\langle v, v \rangle \geq 0,$$
with
$$\langle v, v \rangle = 0 \iff v = 0.$$
A vector space equipped with an inner product is called an **inner product space**.

When
$$\mathbb{K} = \mathbb{R},$$
complex conjugation has no effect, so conjugate symmetry becomes ordinary symmetry:
$$\langle u, v \rangle = \langle v, u \rangle.$$
Linearity in the first argument and conjugate symmetry determine how the inner product behaves in the second argument.

**Proposition 7.2 — Basic properties of an inner product**
For all
$$u, v, w \in V, \quad \alpha, \beta \in \mathbb{K},$$
we have
$$\langle u, \alpha v + \beta w \rangle = \bar{\alpha} \langle u, v \rangle + \bar{\beta} \langle u, w \rangle.$$

<!-- page 225 -->

In particular,
$$\langle 0, v \rangle = \langle v, 0 \rangle = 0.$$

**Proof**
By conjugate symmetry and linearity in the first argument,
$$\langle u, \alpha v + \beta w \rangle = \overline{\langle \alpha v + \beta w, u \rangle}$$
$$= \overline{\alpha \langle v, u \rangle + \beta \langle w, u \rangle}$$
$$= \bar{\alpha} \overline{\langle v, u \rangle} + \bar{\beta} \overline{\langle w, u \rangle}$$
$$= \bar{\alpha} \langle u, v \rangle + \bar{\beta} \langle u, w \rangle.$$
Also, linearity gives
$$\langle 0, v \rangle = \langle 0 + 0, v \rangle = \langle 0, v \rangle + \langle 0, v \rangle,$$
so
$$\langle 0, v \rangle = 0.$$
Conjugate symmetry then gives
$$\langle v, 0 \rangle = 0.$$

**Example 7.3 — Examples of inner products**
The standard inner product on $\mathbb{R}^n$ is
$$\langle x, y \rangle = x^\top y = \sum_{i=1}^n x_i y_i.$$
More generally, if
$$c_1, \dots, c_n > 0,$$
then
$$\langle x, y \rangle = \sum_{i=1}^n c_i x_i y_i$$
defines another inner product on $\mathbb{R}^n$.
Inner products are not restricted to coordinate vectors. For example, on the vector space $C[a, b]$ of continuous real-valued functions on $[a, b]$,
$$\langle f, g \rangle = \int_a^b f(t)g(t) \, dt$$
defines an inner product.

<!-- page 226 -->

Thus a vector space can carry different inner products. The underlying linear structure determines which combinations of vectors are allowed; the inner product determines the geometry imposed on that space.
Every inner product induces a notion of length.

**Definition 7.4 — Norm induced by an inner product**
For
$$v \in V,$$
the **norm** of $v$ induced by the inner product is
$$\|v\| = \sqrt{\langle v, v \rangle}.$$
For the standard inner product on $\mathbb{R}^n$,
$$\|x\| = \sqrt{x_1^2 + \dots + x_n^2},$$
so this definition reproduces ordinary Euclidean length.

**Proposition 7.5 — Basic properties of the induced norm**
For every
$$v \in V, \quad \alpha \in \mathbb{K},$$
we have
$$\|v\| \geq 0,$$
$$\|v\| = 0 \iff v = 0,$$
and
$$\| \alpha v \| = |\alpha| \|v\|.$$

**Proof**
The first two statements follow immediately from positive definiteness.
For the last statement,
$$\|\alpha v\|^2 = \langle \alpha v, \alpha v \rangle$$
$$= \alpha \bar{\alpha} \langle v, v \rangle$$
$$= |\alpha|^2 \|v\|^2.$$
Taking square roots gives
$$\|\alpha v\| = |\alpha| \|v\|.$$
The inner product also generalizes perpendicularity.

<!-- page 227 -->

**Definition 7.6 — Orthogonal vectors**
Two vectors
$$u, v \in V$$
are called **orthogonal**, written
$$u \perp v,$$
if
$$\langle u, v \rangle = 0.$$
By conjugate symmetry,
$$u \perp v \iff v \perp u.$$
Orthogonality gives the familiar Pythagorean identity.

**Proposition 7.7 — Pythagorean theorem**
If
$$u \perp v,$$
then
$$\|u + v\|^2 = \|u\|^2 + \|v\|^2.$$

**Proof**
Since
$$u \perp v,$$
we have
$$\langle u, v \rangle = \langle v, u \rangle = 0.$$
Therefore
$$\|u + v\|^2 = \langle u + v, u + v \rangle$$
$$= \langle u, u \rangle + \langle u, v \rangle + \langle v, u \rangle + \langle v, v \rangle$$
$$= \|u\|^2 + \|v\|^2.$$
A particularly important idea is to decompose one vector into a component parallel to another vector and a component orthogonal to it. Let
$$v \neq 0.$$
If we seek
$$u = cv + w, \quad w \perp v,$$
then
$$0 = \langle u - cv, v \rangle = \langle u, v \rangle - c\|v\|^2.$$

<!-- page 228 -->

Hence the coefficient $c$ is forced to be
$$c = \frac{\langle u, v \rangle}{\|v\|^2}.$$

**Proposition 7.8 — Orthogonal decomposition along one direction**
Let
$$u, v \in V, \quad v \neq 0.$$
Then
$$u = \frac{\langle u, v \rangle}{\|v\|^2}v + w,$$
where
$$w = u - \frac{\langle u, v \rangle}{\|v\|^2}v$$
satisfies
$$w \perp v.$$

**Proof**
We compute
$$\langle w, v \rangle = \left\langle u - \frac{\langle u, v \rangle}{\|v\|^2}v, v \right\rangle$$
$$= \langle u, v \rangle - \frac{\langle u, v \rangle}{\|v\|^2}\langle v, v \rangle$$
$$= 0.$$
Thus
$$w \perp v.$$
This simple decomposition gives one of the fundamental inequalities of linear algebra.

**Theorem 7.9 — Cauchy-Schwarz inequality**
For all
$$u, v \in V,$$
$$|\langle u, v \rangle| \leq \|u\| \|v\|.$$
Equality holds if and only if $u$ and $v$ are linearly dependent.

<!-- page 229 -->

**Proof**

If
$$v = 0,$$
the result is immediate.
Suppose
$$v \neq 0.$$
By proposition 7.8, write
$$u = \frac{\langle u, v \rangle}{\|v\|^2} v + w, \quad w \perp v.$$
Using proposition 7.7,
$$\begin{aligned} \|u\|^2 &= \left\| \frac{\langle u, v \rangle}{\|v\|^2} v \right\|^2 + \|w\|^2 \\ &= \frac{|\langle u, v \rangle|^2}{\|v\|^2} + \|w\|^2 \\ &\geq \frac{|\langle u, v \rangle|^2}{\|v\|^2}. \end{aligned}$$
Multiplying by $\|v\|^2$ gives
$$|\langle u, v \rangle|^2 \leq \|u\|^2 \|v\|^2,$$
and taking square roots yields
$$|\langle u, v \rangle| \leq \|u\| \|v\|.$$
Equality holds exactly when
$$\|w\| = 0,$$
that is, when
$$u = \frac{\langle u, v \rangle}{\|v\|^2} v.$$
Thus equality holds exactly when $u$ and $v$ are linearly dependent.

**Remark 7.10 — Angles in a real inner product space**

When $V$ is a real inner product space and
$$u, v \neq 0,$$
the Cauchy–Schwarz inequality guarantees that
$$-1 \leq \frac{\langle u, v \rangle}{\|u\| \|v\|} \leq 1.$$

229

<!-- page 230 -->

We can therefore define the angle $\theta \in [0, \pi]$ between $u$ and $v$ by
$$\cos \theta = \frac{\langle u, v \rangle}{\|u\| \|v\|}.$$
In particular,
$$u \perp v \iff \theta = \frac{\pi}{2}.$$
The Cauchy–Schwarz inequality also implies that the induced norm satisfies the ordinary triangle inequality.

**Theorem 7.11 — Triangle inequality**

For all
$$u, v \in V,$$
$$\|u + v\| \leq \|u\| + \|v\|.$$

**Proof**

We have
$$\begin{aligned} \|u + v\|^2 &= \langle u + v, u + v \rangle \\ &= \|u\|^2 + \|v\|^2 + \langle u, v \rangle + \overline{\langle u, v \rangle} \\ &= \|u\|^2 + \|v\|^2 + 2 \operatorname{Re} \langle u, v \rangle \\ &\leq \|u\|^2 + \|v\|^2 + 2|\langle u, v \rangle| \\ &\leq \|u\|^2 + \|v\|^2 + 2\|u\| \|v\| \\ &= (\|u\| + \|v\|)^2, \end{aligned}$$
where the second inequality follows from theorem 7.9. Taking square roots gives
$$\|u + v\| \leq \|u\| + \|v\|.$$
Thus an inner product recovers the familiar Euclidean notions of length, perpendicularity, and angle, while making them meaningful in general vector spaces. The next step is to construct bases adapted to this geometry: orthonormal bases.

**7.2 Orthonormal Bases and the Gram–Schmidt Process**

An arbitrary basis gives coordinates for vectors, but finding those coordinates may require solving a system of linear equations. Inner product spaces admit a particularly convenient class of bases for which the coordinates can instead be recovered directly from inner products.
We begin with orthogonal and orthonormal lists.

230

<!-- page 231 -->

**Definition 7.12 — Orthogonal and orthonormal lists**

A list of vectors
$$e_1, \dots, e_m$$
in an inner product space $V$ is called **orthogonal** if
$$\langle e_i, e_j \rangle = 0 \quad \text{whenever } i \neq j.$$
The list is called **orthonormal** if it is orthogonal and
$$\|e_i\| = 1 \quad \text{for every } i.$$
Equivalently,
$$\langle e_i, e_j \rangle = \begin{cases} 1, & i = j, \\ 0, & i \neq j. \end{cases}$$
An orthonormal list that is also a basis of $V$ is called an **orthonormal basis**.

For example, the standard basis
$$e_1, \dots, e_n$$
of $\mathbb{K}^n$, equipped with the standard inner product, is an orthonormal basis.
Orthogonal vectors behave especially simply under linear combinations.

**Proposition 7.13 — Norm of an orthonormal linear combination**

If
$$e_1, \dots, e_m$$
is an orthonormal list and
$$a_1, \dots, a_m \in \mathbb{K},$$
then
$$\|a_1 e_1 + \dots + a_m e_m\|^2 = |a_1|^2 + \dots + |a_m|^2.$$

231

<!-- page 232 -->

**Proof**

Using orthonormality,
$$\begin{aligned} \left\| \sum_{i=1}^m a_i e_i \right\|^2 &= \left\langle \sum_{i=1}^m a_i e_i, \sum_{j=1}^m a_j e_j \right\rangle \\ &= \sum_{i=1}^m \sum_{j=1}^m a_i \overline{a_j} \langle e_i, e_j \rangle \\ &= \sum_{i=1}^m |a_i|^2. \end{aligned}$$
All cross terms vanish because
$$\langle e_i, e_j \rangle = 0 \quad \text{for } i \neq j.$$
An immediate consequence is that orthonormal lists can never contain linear redundancy.

**Corollary 7.14 — Orthonormal lists are linearly independent**

Every orthonormal list is linearly independent.

**Proof**

Suppose
$$a_1 e_1 + \dots + a_m e_m = 0.$$
Then by proposition 7.13,
$$0 = \|a_1 e_1 + \dots + a_m e_m\|^2 = |a_1|^2 + \dots + |a_m|^2.$$
Hence
$$a_1 = \dots = a_m = 0.$$
Thus the list is linearly independent.

**Corollary 7.15 — An orthonormal list of the right length is a basis**

Let $V$ be finite-dimensional. If
$$e_1, \dots, e_n$$
is an orthonormal list and
$$n = \dim V,$$

232

<!-- page 233 -->

then
$$e_1, \dots, e_n$$
is an orthonormal basis of $V$.

**Proof**

By corollary 7.14, the list is linearly independent. Since it contains exactly
$$\dim V$$
vectors, proposition 1.21 implies that it is a basis of $V$.

The main computational advantage of an orthonormal basis is that its coordinate coefficients can be read off directly from the inner product.

**Theorem 7.16 — Coordinates in an orthonormal basis**

Let
$$\mathcal{E} = (e_1, \dots, e_n)$$
be an orthonormal basis of $V$. Then, for every
$$v \in V,$$
$$v = \sum_{i=1}^n \langle v, e_i \rangle e_i.$$
Thus
$$[v]_\mathcal{E} = \begin{pmatrix} \langle v, e_1 \rangle \\ \vdots \\ \langle v, e_n \rangle \end{pmatrix}.$$
Moreover,
$$\|v\|^2 = \sum_{i=1}^n |\langle v, e_i \rangle|^2,$$
and, for all $u, v \in V$,
$$\langle u, v \rangle = \sum_{i=1}^n \langle u, e_i \rangle \overline{\langle v, e_i \rangle}.$$

233

<!-- page 234 -->

**Proof**

Because
$$e_1, \dots, e_n$$
is a basis, there exist unique scalars
$$a_1, \dots, a_n$$
such that
$$v = a_1 e_1 + \dots + a_n e_n.$$
Taking the inner product with $e_k$ gives
$$\begin{aligned} \langle v, e_k \rangle &= \left\langle \sum_{i=1}^n a_i e_i, e_k \right\rangle \\ &= \sum_{i=1}^n a_i \langle e_i, e_k \rangle \\ &= a_k. \end{aligned}$$
Therefore
$$a_k = \langle v, e_k \rangle,$$
which proves
$$v = \sum_{i=1}^n \langle v, e_i \rangle e_i.$$
Applying proposition 7.13 to this representation gives
$$\|v\|^2 = \sum_{i=1}^n |\langle v, e_i \rangle|^2.$$
Finally, writing both $u$ and $v$ in the orthonormal basis gives
$$\begin{aligned} \langle u, v \rangle &= \left\langle \sum_{i=1}^n \langle u, e_i \rangle e_i, \sum_{j=1}^n \langle v, e_j \rangle e_j \right\rangle \\ &= \sum_{i=1}^n \langle u, e_i \rangle \overline{\langle v, e_i \rangle}. \end{aligned}$$

234

<!-- page 235 -->

**Remark 7.17 — Parseval’s identity**

The identity
$$\|v\|^2 = \sum_{i=1}^n |\langle v, e_i \rangle|^2$$
is called **Parseval’s identity**.
It shows that relative to an orthonormal basis, an abstract $n$-dimensional inner product space behaves exactly like $\mathbb{K}^n$ with its standard inner product: the quantities
$$\langle v, e_1 \rangle, \dots, \langle v, e_n \rangle$$
play the role of the ordinary coordinates of $v$.

The usefulness of orthonormal bases raises a natural question:
*Given an arbitrary basis, can we construct an orthonormal basis from it?*

The idea is simple. Suppose first that
$$v_1, v_2$$
are linearly independent.
Normalize the first vector:
$$e_1 = \frac{v_1}{\|v_1\|}.$$
The vector $v_2$ generally has a component in the direction $e_1$. By proposition 7.8, that component is
$$\langle v_2, e_1 \rangle e_1.$$
Subtracting it gives
$$w_2 = v_2 - \langle v_2, e_1 \rangle e_1,$$
which satisfies
$$w_2 \perp e_1.$$
We then normalize:
$$e_2 = \frac{w_2}{\|w_2\|}.$$
For the next vector $v_3$, we remove its components in both of the directions already constructed:
$$w_3 = v_3 - \langle v_3, e_1 \rangle e_1 - \langle v_3, e_2 \rangle e_2.$$
The resulting vector is orthogonal to both $e_1$ and $e_2$.
Continuing in this way gives the Gram–Schmidt process.

235

<!-- page 236 -->

**Theorem 7.18 — Gram–Schmidt process**

Let
$$v_1, \dots, v_m$$
be a linearly independent list in an inner product space $V$.
Define
$$w_1 = v_1, \quad e_1 = \frac{w_1}{\|w_1\|},$$
and, recursively for
$$k = 2, \dots, m,$$
define
$$w_k = v_k - \sum_{j=1}^{k-1} \langle v_k, e_j \rangle e_j, \quad e_k = \frac{w_k}{\|w_k\|}.$$
Then
$$e_1, \dots, e_m$$
is an orthonormal list. Moreover, for every
$$k = 1, \dots, m,$$
$$\operatorname{Span}(v_1, \dots, v_k) = \operatorname{Span}(e_1, \dots, e_k).$$

**Proof**

We proceed by induction on $k$.
For
$$k = 1,$$
we have
$$e_1 = \frac{v_1}{\|v_1\|}.$$
Thus
$$\|e_1\| = 1$$
and
$$\operatorname{Span}(v_1) = \operatorname{Span}(e_1).$$
Now suppose that
$$e_1, \dots, e_{k-1}$$
is orthonormal and that
$$\operatorname{Span}(v_1, \dots, v_{k-1}) = \operatorname{Span}(e_1, \dots, e_{k-1}).$$

236

<!-- page 237 -->

First, we show that
$$w_k \neq 0.$$
If
$$w_k = 0,$$
then
$$v_k = \sum_{j=1}^{k-1} \langle v_k, e_j \rangle e_j \in \operatorname{Span}(e_1, \dots, e_{k-1}).$$
By the induction hypothesis,
$$v_k \in \operatorname{Span}(v_1, \dots, v_{k-1}),$$
contradicting the linear independence of
$$v_1, \dots, v_m.$$
Hence
$$w_k \neq 0,$$
so $e_k$ is well defined and
$$\|e_k\| = 1.$$
Next, for
$$i < k,$$
we have
$$\begin{aligned} \langle w_k, e_i \rangle &= \left\langle v_k - \sum_{j=1}^{k-1} \langle v_k, e_j \rangle e_j, e_i \right\rangle \\ &= \langle v_k, e_i \rangle - \sum_{j=1}^{k-1} \langle v_k, e_j \rangle \langle e_j, e_i \rangle \\ &= \langle v_k, e_i \rangle - \langle v_k, e_i \rangle \\ &= 0. \end{aligned}$$
Thus
$$w_k \perp e_i \quad \text{for every } i < k.$$
Since $e_k$ is a nonzero scalar multiple of $w_k$,
$$e_k \perp e_i \quad \text{for every } i < k.$$
Hence
$$e_1, \dots, e_k$$
is orthonormal.

237

<!-- page 238 -->

It remains to verify the equality of spans.
From the definition of $w_k$,
$$w_k = v_k - \sum_{j=1}^{k-1} \langle v_k, e_j \rangle e_j.$$
By the induction hypothesis,
$$e_1, \dots, e_{k-1} \in \operatorname{Span}(v_1, \dots, v_{k-1}),$$
so
$$w_k \in \operatorname{Span}(v_1, \dots, v_k).$$
Hence
$$e_k \in \operatorname{Span}(v_1, \dots, v_k),$$
and therefore
$$\operatorname{Span}(e_1, \dots, e_k) \subseteq \operatorname{Span}(v_1, \dots, v_k).$$
Conversely, rearranging the defining equation gives
$$v_k = w_k + \sum_{j=1}^{k-1} \langle v_k, e_j \rangle e_j.$$
Because $w_k$ is a scalar multiple of $e_k$,
$$v_k \in \operatorname{Span}(e_1, \dots, e_k).$$
Together with the induction hypothesis, this gives
$$\operatorname{Span}(v_1, \dots, v_k) \subseteq \operatorname{Span}(e_1, \dots, e_k).$$
Thus
$$\operatorname{Span}(v_1, \dots, v_k) = \operatorname{Span}(e_1, \dots, e_k).$$
The result follows by induction.

The construction is worth seeing once explicitly.

**Example 7.19 — Gram–Schmidt in $\mathbb{R}^3$**

Consider
$$v_1 = \begin{pmatrix} 1 \\ 1 \\ 0 \end{pmatrix}, \quad v_2 = \begin{pmatrix} 1 \\ 0 \\ 1 \end{pmatrix}.$$

238

<!-- page 239 -->

First,
$$\|v_1\| = \sqrt{2},$$
so
$$e_1 = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 \\ 1 \\ 0 \end{pmatrix}.$$
Next,
$$\langle v_2, e_1 \rangle = \frac{1}{\sqrt{2}}.$$
Therefore
$$\begin{aligned} w_2 &= v_2 - \langle v_2, e_1 \rangle e_1 \\ &= \begin{pmatrix} 1 \\ 0 \\ 1 \end{pmatrix} - \frac{1}{2} \begin{pmatrix} 1 \\ 1 \\ 0 \end{pmatrix} \\ &= \begin{pmatrix} 1/2 \\ -1/2 \\ 1 \end{pmatrix}. \end{aligned}$$
Since
$$\|w_2\| = \sqrt{\frac{3}{2}} = \frac{\sqrt{6}}{2},$$
we obtain
$$e_2 = \frac{1}{\sqrt{6}} \begin{pmatrix} 1 \\ -1 \\ 2 \end{pmatrix}.$$
Thus
$$e_1, e_2$$
is an orthonormal list and
$$\operatorname{Span}(v_1, v_2) = \operatorname{Span}(e_1, e_2).$$

The Gram–Schmidt process immediately gives existence and extension results for orthonormal bases.

**Corollary 7.20 — Existence of orthonormal bases**

Every finite-dimensional inner product space has an orthonormal basis.

239

<!-- page 240 -->

**Proof**

Choose any basis
$$v_1, \dots, v_n$$
of $V$. Applying theorem 7.18 produces an orthonormal list
$$e_1, \dots, e_n.$$
Since
$$\operatorname{Span}(e_1, \dots, e_n) = \operatorname{Span}(v_1, \dots, v_n) = V,$$
the resulting list is an orthonormal basis.

**Corollary 7.21 — Extension to an orthonormal basis**

Let $V$ be finite-dimensional. Every orthonormal list
$$e_1, \dots, e_m$$
in $V$ can be extended to an orthonormal basis of $V$.

**Proof**

By corollary 7.14, the list
$$e_1, \dots, e_m$$
is linearly independent.
By the basis extension result, proposition 3.10, we may extend it to a basis
$$e_1, \dots, e_m, v_{m+1}, \dots, v_n$$
of $V$.
Apply the Gram–Schmidt process to this basis. Because the first $m$ vectors are already orthonormal, Gram–Schmidt leaves them unchanged: for each
$$k \leq m,$$
all projections onto the preceding vectors are zero and
$$\|e_k\| = 1.$$

240

<!-- page 241 -->

The resulting orthonormal basis therefore has the form
$$e_1, \dots, e_m, f_{m+1}, \dots, f_n,$$
and hence extends the original orthonormal list.

***

**Remark 7.22 — What Gram–Schmidt preserves**

Gram–Schmidt changes the vectors, but it does not change the successive subspaces they generate:
$$\text{Span}(v_1, \dots, v_k) = \text{Span}(e_1, \dots, e_k) \quad \text{for every } k.$$
Thus the procedure does more than produce an orthonormal basis of the same final space. It preserves the entire nested sequence
$$\text{Span}(v_1) \subseteq \text{Span}(v_1, v_2) \subseteq \dots \subseteq \text{Span}(v_1, \dots, v_m).$$
This property will be useful when we study orthogonal complements and orthogonal projections in the next section.

## 7.3 Orthogonal Complements and Orthogonal Projections

We previously saw that a subspace $U$ of a finite-dimensional vector space $V$ always has a complement:
$$V = U \oplus W.$$
Such a complement is generally not unique.
Once $V$ is equipped with an inner product, however, there is a distinguished choice of complement: the vectors perpendicular to $U$.

**Definition 7.23 — Orthogonal complement**

Let $U$ be a subspace of an inner product space $V$. The **orthogonal complement** of $U$ is
$$U^\perp = \{v \in V : \langle v, u \rangle = 0 \text{ for every } u \in U\}.$$

For example, in $\mathbb{R}^3$, if
$$U = \text{Span}\left( \begin{pmatrix} a \\ b \\ c \end{pmatrix} \right),$$

<!-- page 242 -->

then
$$U^\perp = \left\{ \begin{pmatrix} x \\ y \\ z \end{pmatrix} : ax + by + cz = 0 \right\}.$$
Thus the orthogonal complement of a line through the origin is the plane through the origin perpendicular to that line.

**Proposition 7.24 — Basic properties of the orthogonal complement**

Let $U$ be a subspace of an inner product space $V$. Then
$$U^\perp$$
is a subspace of $V$, and
$$U \cap U^\perp = \{0\}.$$
Moreover, if
$$U \subseteq W,$$
then
$$W^\perp \subseteq U^\perp.$$

**Proof**

First, $0 \in U^\perp$. Suppose
$$v, w \in U^\perp$$
and
$$\alpha, \beta \in \mathbb{K}.$$
For every
$$u \in U,$$
we have
$$\langle \alpha v + \beta w, u \rangle = \alpha \langle v, u \rangle + \beta \langle w, u \rangle$$
$$= 0.$$
Hence
$$\alpha v + \beta w \in U^\perp,$$
so $U^\perp$ is a subspace.
If
$$v \in U \cap U^\perp,$$
then
$$\langle v, v \rangle = 0,$$

<!-- page 243 -->

and positive definiteness gives
$$v = 0.$$
Thus
$$U \cap U^\perp = \{0\}.$$
Finally, if
$$U \subseteq W$$
and
$$v \in W^\perp,$$
then $v$ is orthogonal to every vector in $W$, and therefore to every vector in $U$. Hence
$$v \in U^\perp.$$
Thus
$$W^\perp \subseteq U^\perp.$$

The main structural result is that the orthogonal complement is not merely a complement: it gives a canonical direct-sum decomposition.

**Theorem 7.25 — Orthogonal decomposition**

Let $V$ be a finite-dimensional inner product space and let
$$U \subseteq V$$
be a subspace. Then
$$V = U \oplus U^\perp.$$
Equivalently, every
$$v \in V$$
can be written uniquely as
$$v = u + w, \quad u \in U, \quad w \in U^\perp.$$

**Proof**

By corollary 7.20, choose an orthonormal basis
$$e_1, \dots, e_r$$
of $U$.

<!-- page 244 -->

For
$$v \in V,$$
define
$$u = \sum_{i=1}^r \langle v, e_i \rangle e_i$$
and
$$w = v - u.$$
Clearly,
$$u \in U.$$
For every
$$j = 1, \dots, r,$$
we have
$$\langle w, e_j \rangle = \left\langle v - \sum_{i=1}^r \langle v, e_i \rangle e_i, e_j \right\rangle$$
$$= \langle v, e_j \rangle - \sum_{i=1}^r \langle v, e_i \rangle \langle e_i, e_j \rangle$$
$$= 0.$$
Hence $w$ is orthogonal to every basis vector of $U$, and therefore to every vector in $U$. Thus
$$w \in U^\perp.$$
We have shown that
$$V = U + U^\perp.$$
By proposition 7.24,
$$U \cap U^\perp = \{0\}.$$
Therefore, by corollary 4.10,
$$V = U \oplus U^\perp.$$
Uniqueness follows from the direct-sum property.

**Remark 7.26 — The orthogonal complement is a canonical complement**

Without an inner product, a subspace $U$ may have many different complements $W$ satisfying
$$V = U \oplus W.$$

<!-- page 245 -->

The inner product singles out one geometrically distinguished complement:
$$U^\perp.$$

**Corollary 7.27 — Dimension and double orthogonal complement**

Let $V$ be finite-dimensional and let $U$ be a subspace of $V$. Then
$$\dim U^\perp = \dim V - \dim U$$
and
$$(U^\perp)^\perp = U.$$

**Proof**

By theorem 7.25,
$$V = U \oplus U^\perp.$$
Hence
$$\dim V = \dim U + \dim U^\perp,$$
which gives
$$\dim U^\perp = \dim V - \dim U.$$
Also, every vector in $U$ is orthogonal to every vector in $U^\perp$, so
$$U \subseteq (U^\perp)^\perp.$$
But
$$\dim (U^\perp)^\perp = \dim V - \dim U^\perp$$
$$= \dim U.$$
Thus the two subspaces have the same dimension, and therefore
$$(U^\perp)^\perp = U.$$

The orthogonal decomposition also gives another proof that orthonormal bases can be extended.

**Corollary 7.28 — Extension of an orthonormal basis of a subspace**

Let $U$ be a subspace of a finite-dimensional inner product space $V$. If
$$e_1, \dots, e_r$$

<!-- page 246 -->

is an orthonormal basis of $U$, then it can be extended to an orthonormal basis of $V$.

**Proof**

By theorem 7.25,
$$V = U \oplus U^\perp.$$
Choose an orthonormal basis
$$f_1, \dots, f_s$$
of $U^\perp$.
Then
$$e_1, \dots, e_r, f_1, \dots, f_s$$
is orthonormal because vectors from $U$ are orthogonal to vectors from $U^\perp$.
Moreover, the list spans
$$U + U^\perp = V.$$
Hence it is an orthonormal basis of $V$.

The same idea extends naturally to several mutually orthogonal subspaces.

**Definition 7.29 — Orthogonal direct sum**

Let
$$V_1, \dots, V_m$$
be subspaces of an inner product space $V$.
They are called **pairwise orthogonal** if
$$\langle v_i, v_j \rangle = 0$$
for every
$$v_i \in V_i, \quad v_j \in V_j, \quad i \neq j.$$
If
$$V = V_1 + \dots + V_m$$
and the subspaces are pairwise orthogonal, we write
$$V = V_1 \perp \dots \perp V_m$$
and call this an **orthogonal direct sum**.

<!-- page 247 -->

Pairwise orthogonality automatically implies that the sum is direct. Indeed, if
$$v_i = -\sum_{j \neq i} v_j, \quad v_i \in V_i,$$
then taking the inner product with $v_i$ gives
$$\|v_i\|^2 = 0,$$
so
$$v_i = 0.$$
Thus every component in such a decomposition is uniquely determined.
We now use this uniqueness to define projection.

**Definition 7.30 — Orthogonal projection**

Let $V$ be finite-dimensional and let
$$U \subseteq V$$
be a subspace.
By theorem 7.25, every
$$v \in V$$
can be written uniquely as
$$v = u + w, \quad u \in U, \quad w \in U^\perp.$$
The **orthogonal projection of $v$ onto $U$** is
$$P_U v := u.$$
Thus
$$P_U : V \to V$$
extracts the $U$-component of $v$.

For a one-dimensional subspace
$$U = \text{Span}(u), \quad u \neq 0,$$
the formula from proposition 7.8 becomes
$$P_U v = \frac{\langle v, u \rangle}{\|u\|^2} u.$$
If $u$ is a unit vector, this simplifies to
$$P_U v = \langle v, u \rangle u.$$

<!-- page 248 -->

**Proposition 7.31 — Algebraic properties of orthogonal projection**

Let $U$ be a subspace of a finite-dimensional inner product space $V$. Then $P_U$ is linear and
$$\text{Im}(P_U) = U, \quad \text{ker}(P_U) = U^\perp.$$
Moreover,
$$P_U^2 = P_U,$$
$$P_U P_{U^\perp} = P_{U^\perp} P_U = 0,$$
and
$$P_U + P_{U^\perp} = I_V.$$

**Proof**

Write
$$v = u + w, \quad u \in U, \quad w \in U^\perp.$$
Then
$$P_U v = u \quad \text{and} \quad P_{U^\perp} v = w.$$
The uniqueness of the decomposition immediately implies linearity: if
$$v_1 = u_1 + w_1, \quad v_2 = u_2 + w_2,$$
then
$$\alpha v_1 + \beta v_2 = (\alpha u_1 + \beta u_2) + (\alpha w_1 + \beta w_2),$$
so
$$P_U(\alpha v_1 + \beta v_2) = \alpha P_U v_1 + \beta P_U v_2.$$
Because $P_U v \in U$ and every $u \in U$ satisfies
$$P_U u = u,$$
we obtain
$$\text{Im}(P_U) = U.$$
Similarly,
$$P_U v = 0$$
if and only if the $U$-component of $v$ is zero, that is,
$$v \in U^\perp.$$

<!-- page 249 -->

Hence
$$\text{ker}(P_U) = U^\perp.$$
Since
$$P_U v \in U,$$
we have
$$P_U(P_U v) = P_U v,$$
and therefore
$$P_U^2 = P_U.$$
Also,
$$P_U v \in U^\perp,$$
so
$$P_U P_{U^\perp} = 0.$$
Similarly,
$$P_{U^\perp} P_U = 0.$$
Finally,
$$v = P_U v + P_{U^\perp} v$$
for every $v \in V$, and hence
$$P_U + P_{U^\perp} = I_V.$$

If we know an orthonormal basis of $U$, the projection can be written explicitly.

**Theorem 7.32 — Projection formula**

Let
$$e_1, \dots, e_r$$
be an orthonormal basis of $U$. Then for every
$$v \in V,$$
$$P_U v = \sum_{i=1}^r \langle v, e_i \rangle e_i.$$

<!-- page 250 -->

**Proof**

In the proof of theorem 7.25, we showed that
$$u = \sum_{i=1}^r \langle v, e_i \rangle e_i$$
satisfies
$$u \in U$$
and
$$v - u \in U^\perp.$$
By uniqueness of the orthogonal decomposition,
$$u = P_U v.$$

For Euclidean spaces, the projection formula has a convenient matrix representation.

**Proposition 7.33 — Matrix of an orthogonal projection**

Let
$$U \subseteq \mathbb{R}^n$$
have orthonormal basis
$$q_1, \dots, q_r,$$
and define
$$Q = \begin{pmatrix} | & & | \\ q_1 & \dots & q_r \\ | & & | \end{pmatrix}.$$
Then
$$Q^\top Q = I_r$$
and
$$P_U x = QQ^\top x.$$
Thus the matrix of the orthogonal projection onto $U$ is
$$QQ^\top.$$

<!-- page 251 -->

**Proof**

We have
$$Q^\top x = \begin{pmatrix} \langle x, q_1 \rangle \\ \vdots \\ \langle x, q_r \rangle \end{pmatrix}.$$
Therefore
$$QQ^\top x = \sum_{i=1}^r \langle x, q_i \rangle q_i.$$
By theorem 7.32, this equals
$$P_U x.$$

In particular,
$$(QQ^\top)^\top = QQ^\top$$
and
$$(QQ^\top)^2 = QQ^\top.$$
Thus the matrix of an orthogonal projection is symmetric and idempotent.
There is an intrinsic version of this symmetry that will become useful when we study adjoints.

**Proposition 7.34 — Symmetry of orthogonal projection**

For every
$$x, y \in V,$$
$$\langle P_U x, y \rangle = \langle x, P_U y \rangle.$$

**Proof**

Write
$$x = u_1 + w_1, \quad y = u_2 + w_2,$$
where
$$u_1, u_2 \in U$$
and
$$w_1, w_2 \in U^\perp.$$
Then
$$P_U x = u_1, \quad P_U y = u_2.$$

<!-- page 252 -->

Hence
$$\langle P_U x, y \rangle = \langle u_1, u_2 + w_2 \rangle$$
$$= \langle u_1, u_2 \rangle,$$
because
$$u_1 \perp w_2.$$
Similarly,
$$\langle x, P_U y \rangle = \langle u_1 + w_1, u_2 \rangle$$
$$= \langle u_1, u_2 \rangle.$$
Therefore
$$\langle P_U x, y \rangle = \langle x, P_U y \rangle.$$

The orthogonal decomposition also gives a useful geometric inequality.

**Theorem 7.35 — Bessel's inequality**

Let
$$v_1, \dots, v_m$$
be pairwise orthogonal nonzero vectors in an inner product space $V$. Then for every
$$y \in V,$$
$$\sum_{k=1}^m \frac{|\langle y, v_k \rangle|^2}{\|v_k\|^2} \leq \|y\|^2.$$
Equality holds if and only if
$$y \in \text{Span}(v_1, \dots, v_m).$$

**Proof**

Let
$$U = \text{Span}(v_1, \dots, v_m).$$
Because the $v_k$ are pairwise orthogonal,
$$P_U y = \sum_{k=1}^m \frac{\langle y, v_k \rangle}{\|v_k\|^2} v_k.$$

<!-- page 253 -->

The vectors in this sum are pairwise orthogonal, so
$$\begin{aligned} \|P_U y\|^2 &= \left\| \sum_{k=1}^m \frac{\langle y, v_k \rangle}{\|v_k\|^2} v_k \right\|^2 \\ &= \sum_{k=1}^m \frac{|\langle y, v_k \rangle|^2}{\|v_k\|^2}. \end{aligned}$$
Now
$$y = P_U y + (y - P_U y),$$
where
$$P_U y \in U$$
and
$$y - P_U y \in U^\perp.$$
Hence, by proposition 7.7,
$$\|y\|^2 = \|P_U y\|^2 + \|y - P_U y\|^2 \geq \|P_U y\|^2.$$
Therefore
$$\sum_{k=1}^m \frac{|\langle y, v_k \rangle|^2}{\|v_k\|^2} \leq \|y\|^2.$$
Equality holds if and only if
$$y - P_U y = 0,$$
which is equivalent to
$$y \in U = \text{Span}(v_1, \dots, v_m).$$

**Remark 7.36 — Projection as orthogonal decomposition**
The central picture of projection is
$$v = P_U v + P_{U^\perp} v,$$
with
$$P_U v \in U, \quad P_{U^\perp} v \in U^\perp.$$
Thus the direct-sum decomposition
$$V = U \oplus U^\perp$$
becomes a geometric decomposition into mutually perpendicular components.

<!-- page 254 -->

### 7.4 Adjoints, Self-Adjoint Operators, and the Spectral Theorem
At the end of the previous subsection, we saw that an orthogonal projection satisfies
$$\langle P_U x, y \rangle = \langle x, P_U y \rangle.$$
This suggests a more general question. Given a linear map $T$, can we transfer $T$ from one side of an inner product to the other?
The resulting transformation is called the adjoint.

**Definition 7.37 — Adjoint**
Let $V$ and $W$ be finite-dimensional inner product spaces, and let
$$T : V \to W$$
be linear.
The **adjoint** of $T$ is the linear map
$$T^* : W \to V$$
satisfying
$$\langle Tv, w \rangle = \langle v, T^* w \rangle$$
for every
$$v \in V, \quad w \in W.$$
The notation $T^*$ should not be confused with the adjugate matrix introduced earlier. The two notions are different.
We first verify that the adjoint always exists and is uniquely determined.

**Theorem 7.38 — Existence and uniqueness of the adjoint**
Let
$$T : V \to W$$
be linear between finite-dimensional inner product spaces. Then $T$ has a unique adjoint
$$T^* : W \to V.$$
Moreover, let
$$\mathcal{E} = (e_1, \dots, e_n)$$
be an orthonormal basis of $V$ and
$$\mathcal{F} = (f_1, \dots, f_m)$$

<!-- page 255 -->

an orthonormal basis of $W$. If
$$A = [T]_{\mathcal{F} \leftarrow \mathcal{E}},$$
then
$$[T^*]_{\mathcal{E} \leftarrow \mathcal{F}} = A^*,$$
where
$$A^* := \overline{A}^\top$$
is the conjugate transpose of $A$.

**Proof**
Because $\mathcal{E}$ and $\mathcal{F}$ are orthonormal bases, choose the linear map
$$S : W \to V$$
whose matrix is
$$[S]_{\mathcal{E} \leftarrow \mathcal{F}} = A^*.$$
Let
$$x = [v]_{\mathcal{E}}, \quad y = [w]_{\mathcal{F}}.$$
Since the bases are orthonormal, $\langle v, w \rangle$ is computed from coordinates by the standard inner product.
Now
$$[Tv]_{\mathcal{F}} = Ax,$$
so
$$\langle Tv, w \rangle = (Ax)^\top \overline{y} = x^\top A^\top \overline{y}.$$
On the other hand,
$$[Sw]_{\mathcal{E}} = A^* y,$$
and therefore
$$\langle v, Sw \rangle = x^\top \overline{A^* y} = x^\top A^\top \overline{y}.$$
Hence
$$\langle Tv, w \rangle = \langle v, Sw \rangle$$

<!-- page 256 -->

for every $v$ and $w$. Thus
$$S = T^*.$$
This proves existence and also gives
$$[T^*]_{\mathcal{E} \leftarrow \mathcal{F}} = A^*.$$
For uniqueness, suppose
$$S_1, S_2 : W \to V$$
both satisfy the defining identity. Then, for every
$$v \in V, \quad w \in W,$$
$$\langle v, S_1 w \rangle = \langle Tv, w \rangle = \langle v, S_2 w \rangle.$$
Hence
$$\langle v, (S_1 - S_2)w \rangle = 0$$
for every $v \in V$.
Taking
$$v = (S_1 - S_2)w$$
gives
$$\|(S_1 - S_2)w\|^2 = 0.$$
Thus
$$S_1 w = S_2 w$$
for every $w$, so
$$S_1 = S_2.$$
Over $\mathbb{R}$, conjugation has no effect, so the matrix formula simplifies to
$$[T^*]_{\mathcal{E} \leftarrow \mathcal{F}} = [T]_{\mathcal{F} \leftarrow \mathcal{E}}^\top.$$
Thus the adjoint is the intrinsic inner-product analogue of the transpose.

**Proposition 7.39 — Basic properties of the adjoint**
Let
$$S, T : V \to V$$
be linear and let
$$\alpha \in \mathbb{K}.$$

<!-- page 257 -->

Then
$$(S + T)^* = S^* + T^*,$$
$$(\alpha T)^* = \bar{\alpha} T^*,$$
$$(ST)^* = T^* S^*,$$
$$(T^*)^* = T,$$
and
$$I_V^* = I_V.$$

**Proof**
These identities follow from the defining property of the adjoint and its uniqueness.
For example,
$$\langle (S + T)v, w \rangle = \langle Sv, w \rangle + \langle Tv, w \rangle = \langle v, S^* w \rangle + \langle v, T^* w \rangle = \langle v, (S^* + T^*)w \rangle.$$
Hence
$$(S + T)^* = S^* + T^*.$$
Similarly,
$$\langle \alpha Tv, w \rangle = \alpha \langle Tv, w \rangle = \alpha \langle v, T^* w \rangle = \langle v, \bar{\alpha} T^* w \rangle,$$
so
$$(\alpha T)^* = \bar{\alpha} T^*.$$
For the product,
$$\langle STv, w \rangle = \langle Tv, S^* w \rangle = \langle v, T^* S^* w \rangle.$$
Therefore
$$(ST)^* = T^* S^*.$$
Finally,
$$\langle T^* v, w \rangle = \overline{\langle w, T^* v \rangle} = \overline{\langle Tw, v \rangle} = \langle v, Tw \rangle,$$
so
$$(T^*)^* = T.$$
The identity $I_V^* = I_V$ follows immediately from
$$\langle I_V v, w \rangle = \langle v, I_V w \rangle.$$

<!-- page 258 -->

We now focus on operators that coincide with their adjoints.

**Definition 7.40 — Self-adjoint operator**
Let
$$T : V \to V$$
be linear on an inner product space.
The operator $T$ is called **self-adjoint** if
$$T^* = T.$$
Equivalently,
$$\langle Tv, w \rangle = \langle v, Tw \rangle$$
for all
$$v, w \in V.$$
Orthogonal projections provide an immediate example. By proposition 7.34,
$$\langle P_U v, w \rangle = \langle v, P_U w \rangle,$$
and hence
$$P_U^* = P_U.$$
The matrix description of self-adjointness is particularly simple when we use an orthonormal basis.

**Proposition 7.41 — Matrix of a self-adjoint operator**
Let
$$\mathcal{E} = (e_1, \dots, e_n)$$
be an orthonormal basis of $V$, and let
$$A = [T]_{\mathcal{E} \leftarrow \mathcal{E}}.$$
Then
$$T \text{ is self-adjoint} \iff A^* = A.$$
In particular, over $\mathbb{R}$,
$$T \text{ is self-adjoint} \iff A^\top = A.$$

<!-- page 259 -->

**Proof**
By theorem 7.38,
$$[T^*]_{\mathcal{E} \leftarrow \mathcal{E}} = A^*.$$
Therefore
$$T^* = T$$
if and only if
$$A^* = A.$$
Over $\mathbb{R}$,
$$A^* = A^\top,$$
which gives the second statement.

Thus self-adjoint operators on real inner product spaces are precisely the operators represented by symmetric matrices in orthonormal coordinates. Over $\mathbb{C}$, matrices satisfying
$$A^* = A$$
are called **Hermitian**.
A remarkable feature of self-adjoint operators is that their eigenstructure is compatible with the geometry of the inner product.

**Theorem 7.42 — Eigenvalues and eigenvectors of self-adjoint operators**
Let
$$T : V \to V$$
be self-adjoint.
Then every eigenvalue of $T$ is real.
Moreover, eigenvectors corresponding to distinct eigenvalues are orthogonal. Equivalently, if
$$\lambda \neq \mu,$$
then
$$E_\lambda(T) \perp E_\mu(T).$$

**Proof**
Suppose
$$Tv = \lambda v, \quad v \neq 0.$$

<!-- page 260 -->

Then
$$\lambda \|v\|^2 = \langle \lambda v, v \rangle = \langle Tv, v \rangle = \langle v, Tv \rangle = \langle v, \lambda v \rangle = \bar{\lambda} \|v\|^2.$$
Since
$$\|v\|^2 > 0,$$
we obtain
$$\lambda = \bar{\lambda}.$$
Thus $\lambda$ is real.
Now suppose
$$Tv = \lambda v, \quad Tw = \mu w, \quad \lambda \neq \mu.$$
Since both eigenvalues are real,
$$\lambda \langle v, w \rangle = \langle Tv, w \rangle = \langle v, Tw \rangle = \mu \langle v, w \rangle.$$
Hence
$$(\lambda - \mu) \langle v, w \rangle = 0.$$
Since
$$\lambda \neq \mu,$$
it follows that
$$\langle v, w \rangle = 0.$$
Therefore
$$v \perp w.$$
For a general linear transformation, invariance of a subspace does not usually imply invariance of its orthogonal complement. For a self-adjoint operator, however, it does.

**Proposition 7.43 — Orthogonal complements of invariant subspaces**
Let
$$T : V \to V$$
be self-adjoint, and let
$$U \subseteq V$$
be invariant under $T$.

<!-- page 261 -->

Then
$$U^\perp$$
is also invariant under $T$.
Moreover, the restrictions
$$T|_U : U \to U$$
and
$$T|_{U^\perp} : U^\perp \to U^\perp$$
are self-adjoint on their respective inner product spaces.

**Proof**
Let
$$w \in U^\perp.$$
To show that
$$Tw \in U^\perp,$$
take any
$$u \in U.$$
Because $U$ is invariant under $T$,
$$Tu \in U.$$
Thus
$$\langle Tw, u \rangle = \langle w, Tu \rangle = 0,$$
because
$$w \in U^\perp.$$
Hence
$$Tw \in U^\perp.$$
The restrictions are self-adjoint because for vectors in either subspace the identity
$$\langle Tx, y \rangle = \langle x, Ty \rangle$$
is inherited directly from $T$.

We can now strengthen the diagonalization theorem from the previous section. A general diagonalizable operator has a basis of eigenvectors; a self-adjoint operator has an *orthonormal* basis of eigenvectors.

<!-- page 262 -->

**Theorem 7.44 — Real spectral theorem**
Let $V$ be a finite-dimensional real inner product space and let
$$T : V \to V$$
be linear.
Then the following statements are equivalent:
(i) $T$ is self-adjoint;
(ii) $V$ has an orthonormal basis consisting of eigenvectors of $T$;
(iii) $T$ has a diagonal matrix with respect to some orthonormal basis of $V$.

**Proof**
The equivalence
$$(ii) \iff (iii)$$
follows from theorem 6.33.
We first prove
$$(i) \implies (ii)$$
by induction on
$$n = \dim V.$$
If
$$n = 1,$$
the result is immediate.
Now suppose
$$n > 1$$
and that the result holds for all real inner product spaces of dimension smaller than $n$.
Choose an orthonormal basis of $V$, and let
$$A = [T]_{\mathcal{E} \leftarrow \mathcal{E}}.$$
By proposition 7.41,
$$A^\top = A.$$
Regard the same real matrix $A$ as a complex matrix acting on $\mathbb{C}^n$. By corollary 6.28, it has a complex eigenvalue $\lambda$.
Because
$$A^* = A,$$

<!-- page 263 -->

the corresponding operator on $\mathbb{C}^n$ is self-adjoint. Hence, by theorem 7.42,
$$\lambda \in \mathbb{R}.$$
Let
$$z = x + iy \in \mathbb{C}^n, \quad z \neq 0,$$
be an eigenvector corresponding to $\lambda$. Since $A$ and $\lambda$ are real,
$$A(x + iy) = \lambda(x + iy)$$
implies
$$Ax = \lambda x, \quad Ay = \lambda y.$$
At least one of $x$ and $y$ is nonzero. Thus $T$ has a nonzero real eigenvector.
Normalize such an eigenvector and call it
$$e_1.$$
Let
$$U = \text{Span}(e_1).$$
Then $U$ is invariant under $T$ by proposition 4.22.
By proposition 7.43,
$$U^\perp$$
is also invariant under $T$, and
$$T|_{U^\perp}$$
is self-adjoint.
By theorem 7.25,
$$V = U \oplus U^\perp,$$
and
$$\dim U^\perp = n - 1.$$
By the induction hypothesis, $U^\perp$ has an orthonormal basis
$$e_2, \dots, e_n$$
consisting of eigenvectors of
$$T|_{U^\perp}.$$
Because
$$e_1 \perp U^\perp,$$

<!-- page 264 -->

the list
$$e_1, e_2, \dots, e_n$$
is an orthonormal basis of $V$, and every vector in this basis is an eigenvector of $T$.
Thus
$$(i) \implies (ii).$$
Finally, suppose (iii) holds. Let $\mathcal{E}$ be an orthonormal basis such that
$$[T]_{\mathcal{E} \leftarrow \mathcal{E}} = D$$
is diagonal.
Because $D$ is a real diagonal matrix,
$$D^\top = D.$$
By proposition 7.41,
$$T = T^*.$$
Hence
$$(iii) \implies (i).$$
Therefore all three statements are equivalent.

The matrix form of the spectral theorem is particularly important.
A real square matrix $Q$ is called **orthogonal** if
$$Q^\top Q = I.$$
For a square matrix this is equivalent to
$$Q^{-1} = Q^\top.$$
Its columns therefore form an orthonormal basis of $\mathbb{R}^n$.

**Corollary 7.45 — Orthogonal diagonalization of a symmetric matrix**
Let
$$A \in \mathbb{R}^{n \times n}.$$
Then
$$A^\top = A$$
if and only if there exist an orthogonal matrix $Q$ and a real diagonal matrix $D$ such that
$$Q^\top AQ = D.$$

<!-- page 265 -->

Equivalently,
$$A = QDQ^\top.$$
The columns of $Q$ can be chosen to be an orthonormal basis of eigenvectors of $A$, and the corresponding diagonal entries of $D$ are the eigenvalues of $A$.

**Proof**
Suppose first that
$$A^\top = A.$$
Consider
$$T_A : \mathbb{R}^n \to \mathbb{R}^n, \quad T_A(x) = Ax,$$
with the standard inner product.
By proposition 7.41, $T_A$ is self-adjoint. Hence theorem 7.44 gives an orthonormal basis
$$q_1, \dots, q_n$$
of $\mathbb{R}^n$ consisting of eigenvectors of $A$.
Let
$$Q = \begin{pmatrix} | & & | \\ q_1 & \cdots & q_n \\ | & & | \end{pmatrix}.$$
Because the columns of $Q$ are orthonormal,
$$Q^\top Q = I_n,$$
so
$$Q^{-1} = Q^\top.$$
In the basis
$$(q_1, \dots, q_n),$$
the matrix of $T_A$ is diagonal. By the change-of-basis formula, corollary 3.39,
$$D = Q^{-1}AQ = Q^\top AQ.$$
Conversely, suppose
$$Q^\top AQ = D,$$
where $Q$ is orthogonal and $D$ is diagonal. Then
$$A = QDQ^\top.$$

<!-- page 266 -->

Taking transposes gives
$$A^\top = QD^\top Q^\top.$$
Since
$$D^\top = D,$$
we obtain
$$A^\top = A.$$

**Example 7.46 — Orthogonal diagonalization**
Consider
$$A = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix}.$$
We previously found the eigenvalues
$$3 \quad \text{and} \quad 1,$$
with corresponding eigenvectors
$$\begin{pmatrix} 1 \\ 1 \end{pmatrix}, \quad \begin{pmatrix} 1 \\ -1 \end{pmatrix}.$$
These eigenvectors are orthogonal. After normalization, define
$$q_1 = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 \\ 1 \end{pmatrix}, \quad q_2 = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 \\ -1 \end{pmatrix}.$$
Let
$$Q = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}.$$
Then
$$Q^\top Q = I_2,$$
and
$$Q^\top AQ = \begin{pmatrix} 3 & 0 \\ 0 & 1 \end{pmatrix}.$$
Thus the diagonalization can be performed by an orthonormal change of coordinates.

<!-- page 267 -->

**Remark 7.47 — Why the spectral theorem is stronger than diagonalization**
For a general diagonalizable real matrix, we have
$$A = PDP^{-1}$$
for some invertible matrix $P$.
For a real symmetric matrix, the spectral theorem gives the stronger representation
$$A = QDQ^\top,$$
where
$$Q^{-1} = Q^\top.$$
Thus the eigenvectors can be chosen not merely to form a basis, but to form an orthonormal basis.

### 7.5 Quadratic Forms and Congruence
We now turn from linear transformations to a closely related class of functions. A linear transformation is represented by an expression of the form
$$x \longmapsto Ax.$$
A quadratic form is represented instead by a scalar-valued expression of the form
$$x \longmapsto x^\top Ax.$$
Quadratic forms arise naturally whenever the leading variation of an object is second order. They will later provide the language for curvature and second-order conditions in multivariable optimization.
Throughout this subsection, we work over $\mathbb{R}$.

**Definition 7.48 — Quadratic form**
A **quadratic form** on $\mathbb{R}^n$ is a function
$$q : \mathbb{R}^n \to \mathbb{R}$$
of the form
$$q(x_1, \dots, x_n) = \sum_{i=1}^n a_{ii}x_i^2 + 2 \sum_{1 \le i < j \le n} a_{ij}x_ix_j$$

<!-- page 268 -->

where
$$a_{ij} \in \mathbb{R}.$$
Equivalently, if
$$A = (a_{ij}) \in \mathbb{R}^{n \times n}$$
is symmetric, then
$$q(x) = x^\top Ax.$$
The symmetric matrix $A$ is called the **matrix associated with the quadratic form**.

For example, the quadratic form
$$q(x_1, x_2) = 2x_1^2 + 6x_1x_2 + 4x_2^2$$
has associated symmetric matrix
$$A = \begin{pmatrix} 2 & 3 \\ 3 & 4 \end{pmatrix},$$
because
$$x^\top Ax = \begin{pmatrix} x_1 & x_2 \end{pmatrix} \begin{pmatrix} 2 & 3 \\ 3 & 4 \end{pmatrix} \begin{pmatrix} x_1 \\ x_2 \end{pmatrix}$$
$$= 2x_1^2 + 6x_1x_2 + 4x_2^2.$$
Notice that the coefficient of the cross term $x_ix_j$ is twice the corresponding off-diagonal entry of the symmetric matrix.

**Proposition 7.49 — Every quadratic form has a unique symmetric matrix**
For every quadratic form
$$q : \mathbb{R}^n \to \mathbb{R},$$
there exists a unique symmetric matrix
$$A \in \mathbb{R}^{n \times n}$$
such that
$$q(x) = x^\top Ax \quad \text{for every } x \in \mathbb{R}^n.$$

<!-- page 269 -->

**Proof**
Existence follows directly from definition 7.48: if
$$q(x) = \sum_{i=1}^n a_{ii}x_i^2 + 2 \sum_{i < j} a_{ij}x_ix_j,$$
define the symmetric matrix $A$ by
$$A_{ii} = a_{ii}, \quad A_{ji} = A_{ij} = a_{ij} \quad (i < j).$$
Then
$$q(x) = x^\top Ax.$$
For uniqueness, suppose $A$ and $B$ are symmetric and
$$x^\top Ax = x^\top Bx \quad \text{for every } x.$$
Set
$$C = A - B.$$
Then $C$ is symmetric and
$$x^\top Cx = 0 \quad \text{for every } x.$$
Taking
$$x = e_i$$
gives
$$c_{ii} = 0.$$
Taking
$$x = e_i + e_j, \quad i \neq j,$$
gives
$$0 = (e_i + e_j)^\top C(e_i + e_j) = c_{ii} + 2c_{ij} + c_{jj} = 2c_{ij}.$$
Hence
$$c_{ij} = 0$$
for every $i, j$. Thus
$$C = 0,$$
and therefore
$$A = B.$$
More generally, even if we begin with a matrix that is not symmetric, only its symmetric part contributes to the quadratic expression.

<!-- page 270 -->

**Proposition 7.50 — Only the symmetric part matters**
For every
$$B \in \mathbb{R}^{n \times n}$$
and every
$$x \in \mathbb{R}^n,$$
$$x^\top Bx = x^\top \left( \frac{B + B^\top}{2} \right) x.$$

**Proof**
Write
$$B = \frac{B + B^\top}{2} + \frac{B - B^\top}{2}.$$
The first matrix is symmetric and the second is skew-symmetric.
Let
$$K = \frac{B - B^\top}{2}.$$
Then
$$K^\top = -K.$$
Because $x^\top Kx$ is a scalar,
$$x^\top Kx = (x^\top Kx)^\top = x^\top K^\top x = -x^\top Kx.$$
Hence
$$x^\top Kx = 0.$$
Therefore
$$x^\top Bx = x^\top \left( \frac{B + B^\top}{2} \right) x.$$
Thus there is no loss of generality in representing quadratic forms by symmetric matrices.
There is also a natural bilinear object associated with a quadratic form.

**Proposition 7.51 — Associated symmetric bilinear form**
Let
$$q(x) = x^\top Ax, \quad A^\top = A.$$
Define
$$b(x, y) = x^\top Ay.$$

<!-- page 271 -->

Then $b$ is a symmetric bilinear form and
$$q(x) = b(x, x).$$
Moreover,
$$b(x, y) = \frac{1}{2} [q(x + y) - q(x) - q(y)].$$
Thus the quadratic form uniquely determines its associated symmetric bilinear form.

**Proof**
Bilinearity follows immediately from matrix multiplication.
Because
$$A^\top = A,$$
we have
$$b(y, x) = y^\top Ax = (y^\top Ax)^\top = x^\top A^\top y = x^\top Ay = b(x, y).$$
Thus $b$ is symmetric.
Also,
$$b(x, x) = x^\top Ax = q(x).$$
Finally,
$$q(x + y) = (x + y)^\top A(x + y)$$
$$= x^\top Ax + x^\top Ay + y^\top Ax + y^\top Ay$$
$$= q(x) + q(y) + 2x^\top Ay,$$
where symmetry of $A$ gives
$$x^\top Ay = y^\top Ax.$$
Hence
$$b(x, y) = x^\top Ay = \frac{1}{2} [q(x + y) - q(x) - q(y)].$$
We now ask how a quadratic form changes when we change coordinates.
Let
$$x = Cy,$$
where
$$C \in \mathbb{R}^{n \times n}$$
is invertible. Then
$$q(x) = x^\top Ax$$
$$= (Cy)^\top A(Cy)$$
$$= y^\top C^\top ACy.$$

<!-- page 272 -->

Thus the same quadratic form has matrix
$$C^\top AC$$
in the new coordinates.

**Definition 7.52 — Congruent matrices**
Two real symmetric matrices
$$A, B \in \mathbb{R}^{n \times n}$$
are called **congruent** if there exists an invertible matrix
$$C$$
such that
$$B = C^\top AC.$$

Congruence is therefore the matrix relation naturally associated with a change of variables in a quadratic form.

**Remark 7.53 — Similarity and congruence**
It is important to distinguish congruence from the similarity relation used for linear transformations.
For a linear transformation, a change of basis gives
$$A \longmapsto C^{-1}AC.$$
For a quadratic form, a change of variables gives
$$A \longmapsto C^\top AC.$$
Thus
$$\text{linear transformations} \longleftrightarrow \text{similarity},$$
whereas
$$\text{quadratic forms} \longleftrightarrow \text{congruence}.$$
The basic simplification problem for a quadratic form is therefore to find an invertible change of variables that removes all cross terms.
In matrix language, we seek $C$ such that
$$C^\top AC$$
is diagonal.
Because the associated matrix $A$ is symmetric, the spectral theorem gives much more: $C$ can be

<!-- page 273 -->

chosen to be orthogonal.

**Theorem 7.54 — Principal-axis theorem for quadratic forms**
Let
$$q(x) = x^\top Ax, \quad A = A^\top \in \mathbb{R}^{n \times n}.$$
Let
$$\lambda_1, \dots, \lambda_n$$
be the eigenvalues of $A$, counted with algebraic multiplicity.
Then there exists an orthogonal matrix $Q$ such that, under the orthogonal change of variables
$$x = Qy,$$
the quadratic form becomes
$$q(x) = \lambda_1 y_1^2 + \dots + \lambda_n y_n^2.$$

**Proof**
By corollary 7.45, there exists an orthogonal matrix $Q$ such that
$$Q^\top AQ = D,$$
where $D$ is diagonal and its diagonal entries are
$$\lambda_1, \dots, \lambda_n.$$
Set
$$x = Qy.$$
Then
$$q(x) = x^\top Ax$$
$$= (Qy)^\top A(Qy)$$
$$= y^\top Q^\top AQy$$
$$= y^\top Dy$$
$$= \lambda_1 y_1^2 + \dots + \lambda_n y_n^2.$$
The theorem gives a geometric interpretation of the eigenvectors of the associated matrix. The columns of $Q$ form an orthonormal basis of eigenvectors of $A$. These directions are called the **principal axes** of the quadratic form.
In the original coordinates, cross terms such as
$$x_ix_j$$

<!-- page 274 -->

describe interaction between coordinate directions. In principal-axis coordinates, these cross terms disappear:
$$q(x) = \lambda_1 y_1^2 + \dots + \lambda_n y_n^2.$$
The behavior of the quadratic form is therefore completely separated across mutually orthogonal directions.

**Example 7.55 — Removing a cross term by orthogonal diagonalization**
Consider
$$q(x_1, x_2) = 2x_1^2 + 2x_1x_2 + 2x_2^2.$$
Its associated matrix is
$$A = \begin{pmatrix} 2 & 1 \\ 1 & 2 \end{pmatrix}.$$
$A$ has eigenvalues
$$3 \quad \text{and} \quad 1$$
with corresponding orthonormal eigenvectors
$$q_1 = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 \\ 1 \end{pmatrix}, \quad q_2 = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 \\ -1 \end{pmatrix}.$$
Thus, with
$$Q = \frac{1}{\sqrt{2}} \begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix},$$
we have
$$Q^\top AQ = \begin{pmatrix} 3 & 0 \\ 0 & 1 \end{pmatrix}.$$
Under the change of variables
$$x = Qy,$$
that is,
$$x_1 = \frac{y_1 + y_2}{\sqrt{2}}, \quad x_2 = \frac{y_1 - y_2}{\sqrt{2}},$$
the quadratic form becomes
$$q = 3y_1^2 + y_2^2.$$
Thus the cross term in the original coordinates disappears after rotating the coordinate system to the eigenvector directions.

<!-- page 275 -->

**Remark 7.56 — Two notions of diagonalization**
The same symmetric matrix $A$ appears in two related but conceptually different diagonalization problems.
As a linear transformation, the spectral theorem gives
$$Q^{-1}AQ = Q^\top AQ = D.$$
As the matrix of a quadratic form, the change of variables
$$x = Qy$$
gives
$$A \longmapsto Q^\top AQ = D.$$
These formulas coincide because $Q$ is orthogonal:
$$Q^{-1} = Q^\top.$$
For a general change of coordinates, however, similarity and congruence are different operations.

### 7.6 Definiteness of Quadratic Forms
Once a real quadratic form has been written in principal-axis coordinates, its sign is particularly easy to understand.
Indeed, if
$$A = A^\top$$
and the spectral theorem gives
$$Q^\top AQ = D,$$
where the diagonal entries of $D$ are
$$\lambda_1, \dots, \lambda_n,$$
then under the orthogonal change of variables
$$x = Qy$$
we have
$$x^\top Ax = \lambda_1 y_1^2 + \dots + \lambda_n y_n^2.$$
Thus the signs of the eigenvalues determine whether the quadratic form is positive, negative, or changes sign.

<!-- page 276 -->

**Definition 7.57 — Definiteness of a quadratic form**
Let
$$A = A^\top \in \mathbb{R}^{n \times n}.$$
The quadratic form
$$x^\top Ax$$
is called:
(i) **positive definite** if
$$x^\top Ax > 0 \quad \text{for every } x \neq 0;$$
(ii) **negative definite** if
$$x^\top Ax < 0 \quad \text{for every } x \neq 0;$$
(iii) **positive semidefinite** if
$$x^\top Ax \ge 0 \quad \text{for every } x;$$
(iv) **negative semidefinite** if
$$x^\top Ax \le 0 \quad \text{for every } x;$$
(v) **indefinite** if there exist vectors $x, y \in \mathbb{R}^n$ such that
$$x^\top Ax > 0$$
and
$$y^\top Ay < 0.$$
The symmetric matrix $A$ is called positive definite, negative definite, positive semidefinite, negative semidefinite, or indefinite, respectively.

We use the standard notation
$$A > 0, \quad A \ge 0, \quad A < 0, \quad A \le 0$$
for positive definite, positive semidefinite, negative definite, and negative semidefinite matrices, respectively.

**Example 7.58 — Definite, semidefinite, and indefinite forms**
Consider first
$$A = \begin{pmatrix} 2 & 0 \\ 0 & 3 \end{pmatrix}.$$
Then
$$x^\top Ax = 2x_1^2 + 3x_2^2 > 0$$

<!-- page 277 -->

for every
$$x \neq 0.$$
Thus
$$A > 0.$$
Next, let
$$B = \begin{pmatrix} 2 & 0 \\ 0 & 0 \end{pmatrix}.$$
Then
$$x^\top Bx = 2x_1^2 \geq 0$$
for every $x$, but
$$\begin{pmatrix} 0 & 1 \end{pmatrix} B \begin{pmatrix} 0 \\ 1 \end{pmatrix} = 0.$$
Thus
$$B \geq 0$$
but
$$B \not> 0.$$
Finally, let
$$C = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}.$$
Then
$$\begin{pmatrix} 1 & 0 \end{pmatrix} C \begin{pmatrix} 1 \\ 0 \end{pmatrix} = 1 > 0,$$
whereas
$$\begin{pmatrix} 0 & 1 \end{pmatrix} C \begin{pmatrix} 0 \\ 1 \end{pmatrix} = -1 < 0.$$
Hence $C$ is indefinite.

The distinction between positive definite and positive semidefinite is therefore the distinction between strict and weak positivity.
In particular,
$$A \geq 0$$
allows nonzero directions $x$ for which
$$x^\top Ax = 0,$$
whereas
$$A > 0$$
does not.

<!-- page 278 -->

The spectral theorem gives the fundamental characterization of all these cases.

**Theorem 7.59 — Eigenvalue criterion for definiteness**
Let
$$A = A^\top \in \mathbb{R}^{n \times n},$$
and let
$$\lambda_1, \dots, \lambda_n$$
be the eigenvalues of $A$, counted with multiplicity.
Then:
(i)
$$A > 0 \iff \lambda_i > 0 \text{ for every } i;$$
(ii)
$$A \geq 0 \iff \lambda_i \geq 0 \text{ for every } i;$$
(iii)
$$A < 0 \iff \lambda_i < 0 \text{ for every } i;$$
(iv)
$$A \leq 0 \iff \lambda_i \leq 0 \text{ for every } i;$$
(v) $A$ is indefinite if and only if $A$ has at least one positive eigenvalue and at least one negative eigenvalue.

**Proof**
By corollary 7.45, there exists an orthogonal matrix $Q$ such that
$$Q^\top AQ = D,$$
where
$$D$$
is diagonal with diagonal entries
$$\lambda_1, \dots, \lambda_n.$$
For every
$$x \in \mathbb{R}^n,$$
write
$$x = Qy.$$

<!-- page 279 -->

Because $Q$ is invertible,
$$x \neq 0 \iff y \neq 0.$$
Then
$$x^\top Ax = y^\top Q^\top AQy$$
$$= y^\top Dy$$
$$= \lambda_1 y_1^2 + \dots + \lambda_n y_n^2.$$
Suppose first that
$$\lambda_i > 0 \quad \text{for every } i.$$
If
$$y \neq 0,$$
then at least one $y_i$ is nonzero, and therefore
$$\lambda_1 y_1^2 + \dots + \lambda_n y_n^2 > 0.$$
Hence
$$A > 0.$$
Conversely, suppose
$$A > 0.$$
If $v_i$ is an eigenvector corresponding to $\lambda_i$, then
$$Av_i = \lambda_i v_i.$$
Hence
$$v_i^\top Av_i = \lambda_i \|v_i\|^2.$$
Because
$$v_i \neq 0$$
and $A$ is positive definite,
$$\lambda_i \|v_i\|^2 > 0.$$
Thus
$$\lambda_i > 0.$$
This proves (i).
The proof of (ii) is identical with strict inequalities replaced by weak inequalities.
Statements (iii) and (iv) follow by applying (i) and (ii) to $-A$.
Finally, if $A$ has a positive eigenvalue $\lambda$ with eigenvector $v$ and a negative eigenvalue $\mu$ with eigenvector $w$, then
$$v^\top Av = \lambda \|v\|^2 > 0$$

<!-- page 280 -->

and
$$w^\top Aw = \mu \|w\|^2 < 0.$$
Hence $A$ is indefinite.
Conversely, if all eigenvalues were nonnegative, then (ii) would imply that $A$ is positive semidefinite. If all eigenvalues were nonpositive, then (iv) would imply that $A$ is negative semidefinite. Thus an indefinite symmetric matrix must have eigenvalues of both signs.

**Corollary 7.60 — Definiteness and invertibility**
Let
$$A = A^\top \in \mathbb{R}^{n \times n}.$$
If
$$A > 0 \quad \text{or} \quad A < 0,$$
then $A$ is invertible.
If
$$A \geq 0,$$
then
$$A > 0 \iff A \text{ is invertible.}$$
Similarly, if
$$A \leq 0,$$
then
$$A < 0 \iff A \text{ is invertible.}$$

**Proof**
By theorem 7.59, a positive or negative definite matrix has no zero eigenvalue and is therefore invertible.
If
$$A \geq 0,$$
all its eigenvalues are nonnegative. Thus $A$ is invertible if and only if none of these eigenvalues is zero, which is equivalent to all of them being strictly positive. By theorem 7.59, this is equivalent to
$$A > 0.$$
The negative semidefinite case is analogous.

Positive semidefinite matrices also have a useful property concerning the directions on which the

<!-- page 281 -->

quadratic form vanishes.

**Proposition 7.61 — Zero directions of a positive semidefinite matrix**
Let
$$A = A^\top \geq 0.$$
Then
$$x^\top Ax = 0 \iff Ax = 0.$$

**Proof**
If
$$Ax = 0,$$
then clearly
$$x^\top Ax = 0.$$
Conversely, by the spectral theorem, write
$$A = QDQ^\top,$$
where
$$D$$
has nonnegative diagonal entries
$$\lambda_1, \dots, \lambda_n.$$
Set
$$y = Q^\top x.$$
Then
$$x^\top Ax = \sum_{i=1}^n \lambda_i y_i^2.$$
If
$$x^\top Ax = 0,$$
then every term in this sum is nonnegative, so
$$\lambda_i y_i^2 = 0 \quad \text{for every } i.$$
Hence
$$\lambda_i y_i = 0 \quad \text{for every } i,$$
which means
$$Dy = 0.$$

<!-- page 282 -->

Therefore
$$Ax = QDQ^\top x = QDy = 0.$$
The preceding spectral characterization also gives a particularly simple description under congruence.

**Corollary 7.62 — Canonical forms for definite and semidefinite matrices**
Let
$$A = A^\top \in \mathbb{R}^{n \times n}$$
and let
$$r = \text{Rank}(A).$$
Then:
(i)
$$A > 0$$
if and only if $A$ is congruent to $I_n$;
(ii)
$$A < 0$$
if and only if $A$ is congruent to $-I_n$;
(iii)
$$A \geq 0$$
if and only if $A$ is congruent to a diagonal matrix whose first $r$ diagonal entries are 1 and whose remaining diagonal entries are 0;
(iv)
$$A \leq 0$$
if and only if $A$ is congruent to a diagonal matrix whose first $r$ diagonal entries are $-1$ and whose remaining diagonal entries are 0.

**Proof**
We prove the positive semidefinite case; the others are analogous.
Suppose
$$A \geq 0.$$
By theorem 7.59, all eigenvalues are nonnegative. After reordering them, write
$$\lambda_1, \dots, \lambda_r > 0, \quad \lambda_{r+1} = \dots = \lambda_n = 0.$$

<!-- page 283 -->

By the spectral theorem,
$$Q^\top AQ$$
is diagonal with these eigenvalues on the diagonal.
Now rescale the first $r$ coordinates by
$$\frac{1}{\sqrt{\lambda_1}}, \dots, \frac{1}{\sqrt{\lambda_r}}.$$
The resulting invertible congruence transformation changes the nonzero diagonal entries to 1, giving a diagonal matrix with $r$ ones and $n - r$ zeros.
Conversely, an invertible change of variables does not change whether the expression
$$x^\top Ax$$
is nonnegative for every $x$. Hence any matrix congruent to this diagonal matrix is positive semidefinite.

**Remark 7.63 — What semidefiniteness means geometrically**
For a positive definite matrix,
$$x^\top Ax > 0$$
in every nonzero direction.
For a positive semidefinite matrix, the expression is still never negative, but it may be flat along a nontrivial subspace. By proposition 7.61, those flat directions are exactly
$$\ker(A).$$
Thus
$$\dim \ker(A)$$
measures the number of directions in which the quadratic form has zero curvature.

**7.7 Inertia and the Leading Principal Minor Criterion**
In the previous subsection, we classified a symmetric matrix according to the sign of
$$x^\top Ax.$$
We now ask which aspects of this sign structure are preserved when we make an arbitrary invertible change of variables.

<!-- page 284 -->

Recall that if
$$x = Cy, \quad C \text{ invertible},$$
then
$$x^\top Ax = y^\top C^\top ACy.$$
Thus changes of variables correspond to congruence transformations
$$A \longmapsto C^\top AC.$$
By the principal-axis theorem, a real symmetric matrix can first be orthogonally diagonalized. Rescaling the nonzero coordinates then shows that every real symmetric matrix is congruent to a particularly simple diagonal matrix.

**Proposition 7.64 — Canonical form under congruence**
Let
$$A = A^\top \in \mathbb{R}^{n \times n}.$$
Then there exists an invertible matrix $C$ such that
$$C^\top AC = \text{diag}(\underbrace{1, \dots, 1}_{p}, \underbrace{-1, \dots, -1}_{r}, \underbrace{0, \dots, 0}_{s}),$$
where
$$p + r + s = n.$$

**Proof**
By corollary 7.45, there exists an orthogonal matrix $Q$ such that
$$Q^\top AQ = \text{diag}(\lambda_1, \dots, \lambda_n).$$
Reorder the eigenvalues so that the positive eigenvalues come first, followed by the negative eigenvalues and then the zero eigenvalues:
$$\lambda_1, \dots, \lambda_p > 0,$$
$$\lambda_{p+1}, \dots, \lambda_{p+r} < 0,$$
and
$$\lambda_{p+r+1} = \dots = \lambda_n = 0.$$
For every nonzero eigenvalue, rescale the corresponding coordinate by the reciprocal of the

<!-- page 285 -->

square root of its absolute value. Thus there is an invertible diagonal matrix $S$ such that
$$S^\top \text{diag}(\lambda_1, \dots, \lambda_n)S = \text{diag}(\underbrace{1, \dots, 1}_{p}, \underbrace{-1, \dots, -1}_{r}, \underbrace{0, \dots, 0}_{s}).$$
Taking
$$C = QS$$
gives the desired congruence.

The important fact is that the numbers of positive, negative, and zero terms in this canonical form do not depend on the particular congruence transformation used.

**Definition 7.65 — Inertia**
Let
$$A = A^\top \in \mathbb{R}^{n \times n}.$$
The number of positive entries in a congruence canonical form of $A$ is called the **positive inertia index** of $A$ and is denoted by
$$n_+(A).$$
The number of negative entries is called the **negative inertia index** and is denoted by
$$n_-(A).$$
The number of zero entries is denoted by
$$n_0(A).$$
The triple
$$(n_+(A), n_-(A), n_0(A))$$
is called the **inertia** of $A$.
The difference
$$n_+(A) - n_-(A)$$
is sometimes called the **signature** of $A$.

Because the canonical form can be obtained from the eigenvalue decomposition,
$$n_+(A), \quad n_-(A), \quad n_0(A)$$
are precisely the numbers of positive, negative, and zero eigenvalues of $A$, counted with multiplicity.
We now show that these numbers really are invariants under congruence.

<!-- page 286 -->

**Theorem 7.66 — Sylvester's law of inertia**
Let
$$A, B \in \mathbb{R}^{n \times n}$$
be symmetric matrices. If $A$ and $B$ are congruent, then
$$n_+(A) = n_+(B),$$
$$n_-(A) = n_-(B),$$
and
$$n_0(A) = n_0(B).$$
Thus the numbers of positive, negative, and zero squares in the canonical form are independent of the change of variables used to obtain that form.

**Proof**
Suppose
$$B = C^\top AC$$
for some invertible matrix $C$. Then
$$y^\top By = (Cy)^\top A(Cy).$$
Thus the invertible map
$$y \longmapsto Cy$$
preserves the sign of the corresponding quadratic expressions.
We first characterize the positive inertia index geometrically.
Suppose $A$ has canonical form
$$D = \text{diag}(\underbrace{1, \dots, 1}_{p}, \underbrace{-1, \dots, -1}_{r}, \underbrace{0, \dots, 0}_{s}).$$
On the $p$-dimensional subspace
$$U_+ = \text{Span}(e_1, \dots, e_p),$$
we have
$$y^\top Dy = y_1^2 + \dots + y_p^2 > 0$$
for every nonzero
$$y \in U_+.$$

<!-- page 287 -->

Hence there exists a $p$-dimensional subspace on which the quadratic expression is positive definite.
We claim that no subspace of dimension greater than $p$ can have this property.
Let $W$ be a subspace such that
$$y^\top Dy > 0 \quad \text{for every nonzero } y \in W.$$
Consider the projection
$$\pi : W \to \mathbb{R}^p$$
onto the first $p$ coordinates.
If
$$\pi(y) = 0,$$
then
$$y_1 = \dots = y_p = 0,$$
and therefore
$$y^\top Dy = -y_{p+1}^2 - \dots - y_{p+r}^2 \leq 0.$$
The assumed positivity on $W$ therefore implies
$$y = 0.$$
Hence $\pi$ is injective on $W$, so
$$\dim W \leq p.$$
Thus $p$ is intrinsically characterized as the largest possible dimension of a subspace on which the quadratic expression is positive definite. Because an invertible congruence transformation maps subspaces bijectively and preserves the sign of the quadratic expression, this number is invariant under congruence.
Therefore
$$n_+(A) = n_+(B).$$
Applying the same argument to $-A$ and $-B$ gives
$$n_-(A) = n_-(B).$$
Finally,
$$n_0(A) = n - n_+(A) - n_-(A),$$
and similarly for $B$. Hence
$$n_0(A) = n_0(B).$$

<!-- page 288 -->

**Corollary 7.67 — Congruence classification of real symmetric matrices**
Two real symmetric matrices of the same size are congruent if and only if they have the same inertia.

**Proof**
If the matrices are congruent, they have the same inertia by theorem 7.66.
Conversely, if two symmetric matrices have the same inertia
$$(p, r, s),$$
then by proposition 7.64 both are congruent to
$$\text{diag}(\underbrace{1, \dots, 1}_{p}, \underbrace{-1, \dots, -1}_{r}, \underbrace{0, \dots, 0}_{s}).$$
Hence they are congruent to each other.

**Remark 7.68 — Inertia and definiteness**
The sign classifications from the previous subsection can now be read directly from the inertia:
$$A > 0 \iff (n_+(A), n_-(A), n_0(A)) = (n, 0, 0),$$
$$A \geq 0 \iff n_-(A) = 0,$$
$$A < 0 \iff (n_+(A), n_-(A), n_0(A)) = (0, n, 0),$$
and
$$A \text{ is indefinite} \iff n_+(A) > 0 \text{ and } n_-(A) > 0.$$
The eigenvalue criterion gives a conceptually transparent test for definiteness. There is also a useful criterion involving only determinants of successively larger submatrices.

**Definition 7.69 — Leading principal minors**
Let
$$A = (a_{ij}) \in \mathbb{R}^{n \times n}.$$

<!-- page 289 -->

For
$$k = 1, \dots, n,$$
let
$$A_k = \begin{pmatrix} a_{11} & a_{12} & \cdots & a_{1k} \\ a_{21} & a_{22} & \cdots & a_{2k} \\ \vdots & \vdots & \ddots & \vdots \\ a_{k1} & a_{k2} & \cdots & a_{kk} \end{pmatrix}$$
be the upper-left $k \times k$ submatrix of $A$.
The determinants
$$\Delta_k := \det(A_k), \quad k = 1, \dots, n,$$
are called the **leading principal minors** of $A$.

Thus
$$\Delta_1 = a_{11},$$
$$\Delta_2 = \det \begin{pmatrix} a_{11} & a_{12} \\ a_{21} & a_{22} \end{pmatrix},$$
and
$$\Delta_n = \det(A).$$

**Theorem 7.70 — Sylvester's criterion**
Let
$$A = A^\top \in \mathbb{R}^{n \times n}.$$
Then
$$A > 0$$
if and only if
$$\Delta_1 > 0, \quad \Delta_2 > 0, \quad \dots, \quad \Delta_n > 0.$$

**Proof**
We first prove necessity.
Suppose
$$A > 0.$$
For every
$$k = 1, \dots, n,$$
consider the leading principal submatrix $A_k$.

<!-- page 290 -->

For any nonzero
$$z = \begin{pmatrix} z_1 \\ \vdots \\ z_k \end{pmatrix} \in \mathbb{R}^k,$$
define
$$x = \begin{pmatrix} z_1 \\ \vdots \\ z_k \\ 0 \\ \vdots \\ 0 \end{pmatrix} \in \mathbb{R}^n.$$
Then
$$x^\top A x = z^\top A_k z.$$
Because
$$A > 0$$
and
$$x \neq 0,$$
we have
$$z^\top A_k z > 0.$$
Thus
$$A_k > 0.$$
By corollary 7.62, there exists an invertible matrix $B_k$ such that
$$B_k^\top A_k B_k = I_k.$$
Taking determinants gives
$$\det(B_k)^2 \det(A_k) = 1.$$
Hence
$$\det(A_k) > 0.$$
Therefore
$$\Delta_k > 0 \quad \text{for every } k.$$
We now prove sufficiency by induction on $n$.
For
$$n = 1,$$
the result is immediate.

<!-- page 291 -->

Suppose the result holds for symmetric matrices of size $n-1$, and let
$$A = \begin{pmatrix} A_{n-1} & a \\ a^\top & a_{nn} \end{pmatrix}$$
be a symmetric $n \times n$ matrix satisfying
$$\Delta_1, \dots, \Delta_n > 0.$$
The first $n-1$ leading principal minors of $A_{n-1}$ are positive. Hence, by the induction hypothesis,
$$A_{n-1} > 0.$$
By corollary 7.62, there exists an invertible matrix $B$ such that
$$B^\top A_{n-1} B = I_{n-1}.$$
Define
$$C = \begin{pmatrix} B & 0 \\ 0 & 1 \end{pmatrix}.$$
Then
$$C^\top A C = \begin{pmatrix} I_{n-1} & c \\ c^\top & d \end{pmatrix}$$
for some
$$c \in \mathbb{R}^{n-1}, \quad d \in \mathbb{R}.$$
Now define
$$R = \begin{pmatrix} I_{n-1} & -c \\ 0 & 1 \end{pmatrix}.$$
A direct multiplication gives
$$R^\top \begin{pmatrix} I_{n-1} & c \\ c^\top & d \end{pmatrix} R = \begin{pmatrix} I_{n-1} & 0 \\ 0 & d - c^\top c \end{pmatrix}.$$
Hence $A$ is congruent to
$$\text{diag}(1, \dots, 1, \gamma), \quad \gamma = d - c^\top c.$$
Taking determinants,
$$\det(A)$$
and $\gamma$ have the same sign, because all congruence matrices used above are invertible and
$$\det(C^\top A C) = \det(C)^2 \det(A).$$

<!-- page 292 -->

Since
$$\Delta_n = \det(A) > 0,$$
we obtain
$$\gamma > 0.$$
Therefore $A$ is congruent to $I_n$. By corollary 7.62,
$$A > 0.$$
The corresponding criterion for negative definiteness follows immediately.

**Corollary 7.71 — Leading principal minor criterion for negative definiteness**
Let
$$A = A^\top \in \mathbb{R}^{n \times n}.$$
Then
$$A < 0$$
if and only if
$$(-1)^k \Delta_k > 0 \quad \text{for } k = 1, \dots, n.$$
Equivalently,
$$\Delta_1 < 0, \quad \Delta_2 > 0, \quad \Delta_3 < 0, \quad \dots$$
with alternating signs.

**Proof**
We have
$$A < 0 \iff -A > 0.$$
The $k$th leading principal minor of $-A$ is
$$\det(-A_k) = (-1)^k \det(A_k) = (-1)^k \Delta_k.$$
The result therefore follows from theorem 7.70.

**Remark 7.72 — Leading principal minors and semidefiniteness**
The strict criterion in theorem 7.70 does *not* extend to positive semidefiniteness merely by replacing
$$\Delta_k > 0$$

<!-- page 293 -->

with
$$\Delta_k \geq 0.$$
For example,
$$A = \begin{pmatrix} 0 & 0 & 0 \\ 0 & -1 & 0 \\ 0 & 0 & -1 \end{pmatrix}$$
has
$$\Delta_1 = \Delta_2 = \Delta_3 = 0,$$
yet
$$x^\top A x = -x_2^2 - x_3^2$$
is not positive semidefinite.
For a real symmetric matrix, positive semidefiniteness is instead equivalent to the nonnegativity of *all* principal minors, not only the leading principal minors.

**Example 7.73 — Using Sylvester's criterion**
Consider
$$A = \begin{pmatrix} 1 & t & -1 & 0 \\ t & 4 & 2 & 0 \\ -1 & 2 & 4 & 0 \\ 0 & 0 & 0 & 3 \end{pmatrix}.$$
Its leading principal minors are
$$\Delta_1 = 1,$$
$$\Delta_2 = \det \begin{pmatrix} 1 & t \\ t & 4 \end{pmatrix} = 4 - t^2,$$
$$\Delta_3 = \det \begin{pmatrix} 1 & t & -1 \\ t & 4 & 2 \\ -1 & 2 & 4 \end{pmatrix} = -4(t - 1)(t + 2),$$
and
$$\Delta_4 = -12(t - 1)(t + 2).$$
By theorem 7.70, $A$ is positive definite precisely when all four quantities are positive.
The first condition is automatic. The remaining conditions reduce to
$$4 - t^2 > 0$$

<!-- page 294 -->

and
$$-4(t - 1)(t + 2) > 0.$$
Thus
$$-2 < t < 1.$$

**Remark 7.74 — Eigenvalues versus principal minors**
For a real symmetric matrix, we now have two complementary tests for positive definiteness:
$$A > 0 \iff \text{all eigenvalues of } A \text{ are positive,}$$
and
$$A > 0 \iff \Delta_1, \dots, \Delta_n > 0.$$
The eigenvalue criterion follows naturally from the spectral theorem.
Sylvester's criterion avoids computing eigenvalues and reduces the question instead to a sequence of determinant calculations.