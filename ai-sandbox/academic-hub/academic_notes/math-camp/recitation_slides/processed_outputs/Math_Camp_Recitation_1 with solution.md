---
source_pdf: Math_Camp_Recitation_1 with solution.pdf
folder_category: recitation_slides
total_pages: 8
routing: gemini_batched
model: gemini-3.1-flash-lite
pages_repaired: 2
repaired_pages: [2, 7]
tags: [linear-algebra]
---

<!-- page 1 -->

**Exercise 1 — Rank, systems, and Rouché–Capelli**

Consider the system in $x, y, z$, with parameters $a, b \in \mathbb{R}$:
$$
\begin{aligned}
x + 2y + z &= 1 \\
2x + 4y + az &= 2 \\
x + ay + z &= b
\end{aligned}
$$

**(a)** Compute $\det(A)$ for the coefficient matrix and determine for which $a$ the matrix is invertible.  
**(b)** Using Gauss–Jordan on the augmented matrix, classify the solution set for every pair $(a, b)$.  
**(c)** In the case with infinitely many solutions, give the dimension of the solution set and an explicit parametrization.

<!-- page 2 -->

**Exercise 1 — Solution**

**(a)** Cofactor expansion along the first row:
$$\det(A) = (4 - a^2) - 2(2 - a) + (2a - 4) = -(a - 2)^2,$$
so $A$ is invertible if and only if $a \neq 2$.

**(b)** Applying $R_2 - 2R_1$ and $R_3 - R_1$ to $[A \mid b]$:
$$\begin{bmatrix} 1 & 2 & 1 & \mid & 1 \\ 0 & 0 & a - 2 & \mid & 0 \\ 0 & a - 2 & 0 & \mid & b - 1 \end{bmatrix}$$

* $a \neq 2$: swap rows 2 and 3 for echelon form. $\rho(A^*) = \rho(C^*) = 3 = n$, so there is a unique solution: $z = 0, y = \frac{b-1}{a-2}, x = 1 - \frac{2(b-1)}{a-2}$.
* $a = 2, b \neq 1$: $\rho(A^*) = 1 < \rho(C^*) = 2$, so there is no solution.
* $a = 2, b = 1$: $\rho(A^*) = \rho(C^*) = 1 < 3$, so there are infinitely many solutions.

**(c)** The solution set is $\{(1 - 2s - t, s, t) : s, t \in \mathbb{R}\}$, of dimension $n - \rho = 3 - 1 = 2$.

<!-- page 3 -->

**Exercise 2 — Subspaces, span, and basis**

Work in $V = M_{2 \times 2}(\mathbb{R})$ with the usual matrix addition and scalar multiplication (you may assume this is a vector space).

**(a)** Let $W = \{A \in V : \operatorname{tr}(A) = 0\}$. Verify the three subspace conditions and produce a basis. What is $\dim W$?

**(b)** Let $S = \{A \in V : A = A^\top\}$. Show $S$ is a subspace and find $\dim S$.

**(c)** Find a basis for $W \cap S$. (You proved in class that any intersection of vector subspaces is a vector subspace — use it rather than reverifying.)

**(d)** Let $U = \{A \in V : A \text{ is invertible}\}$. Show $U$ is *not* a subspace in two different ways.

<!-- page 4 -->

**Exercise 2 — Solution**

**(a)** $\operatorname{tr}$ is linear, so $W$ is the kernel of a linear map: it contains $0$ and is closed under addition and scalar multiplication. A basis is
$$\begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}, \quad \begin{pmatrix} 0 & 1 \\ 0 & 0 \end{pmatrix}, \quad \begin{pmatrix} 0 & 0 \\ 1 & 0 \end{pmatrix}, \qquad \dim W = 3.$$

**(b)** Symmetry is preserved by sums and scalar multiples, and $0$ is symmetric. A basis is
$$\begin{pmatrix} 1 & 0 \\ 0 & 0 \end{pmatrix}, \quad \begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix}, \quad \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}, \qquad \dim S = 3.$$

**(c)** Traceless and symmetric: $\begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}, \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$, so $\dim(W \cap S) = 2$. Note $3 + 3 - 2 = 4 = \dim V$, so $W + S = V$.

**(d)** $U$ fails the zero-vector condition, since $0 \notin U$. It also fails closure under addition: $I$ and $-I$ are both invertible but $I + (-I) = 0$ is not, while $\begin{pmatrix} 1 & 0 \\ 0 & 0 \end{pmatrix} + \begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix} = I$ is invertible though neither summand is.

<!-- page 5 -->

**Exercise 3 — Diagonalization and a linear dynamic system**

Let
$$A = \begin{pmatrix} 0.5 & 0.3 \\ 0.2 & 0.6 \end{pmatrix}, \qquad x_t = A x_{t-1}, \qquad x_0 = \begin{pmatrix} 5 \\ 0 \end{pmatrix}.$$

**(a)** Find the characteristic polynomial and the spectrum. Verify Proposition 12: $\det A = \prod_k \lambda_k^{a_k}$ and $\operatorname{tr} A = \sum_k a_k \lambda_k$.

**(b)** Find eigenvectors, construct $P$ and $\Lambda$ with $A = P \Lambda P^{-1}$, and derive a closed form for $x_t$. What is $\lim_{t \to \infty} x_t$, and which eigenvalue governs the rate of convergence?

**(c)** Now let $B = \begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix}$. Show $B$ is not diagonalizable by comparing algebraic and geometric multiplicity. Does $B^t x_0 \to 0$? What does this say about the converse of the stability argument in **(b)**?

<!-- page 6 -->

### Exercise 3 — Solution

**(a)** $P_A(\lambda) = \lambda^2 - 1.1\lambda + 0.24$, with roots $\lambda_1 = 0.8$ and $\lambda_2 = 0.3$. Check:  
$0.8 \times 0.3 = 0.24 = \det A$ and $0.8 + 0.3 = 1.1 = \operatorname{tr} A$.

**(b)** Eigenvectors $v_1 = (1, 1)^\top$ and $v_2 = (3, -2)^\top$. Distinct eigenvalues, so $A$ is diagonalizable by Proposition 13. With $P = \begin{bmatrix} v_1 & v_2 \end{bmatrix}$ we have $P^{-1}x_0 = (2, 1)^\top$, hence

$$x_t = 2(0.8)^t \begin{pmatrix} 1 \\ 1 \end{pmatrix} + (0.3)^t \begin{pmatrix} 3 \\ -2 \end{pmatrix} \longrightarrow 0.$$

The $(0.3)^t$ term dies quickly; convergence is asymptotically at rate 0.8 — the dominant eigenvalue — along the direction $(1, 1)^\top$.

**(c)** $P_B(\lambda) = (1 - \lambda)^2$, so $a_1 = 2$, but $\ker(B - I) = \operatorname{span}\{(1, 0)^\top\}$ gives $g_1 = 1 < a_1$: not diagonalizable. Since $\lambda = 1$, $B^t = \begin{pmatrix} 1 & t \\ 0 & 1 \end{pmatrix}$ diverges for any $x_0$ with nonzero second coordinate. Stability is a statement about the spectral radius; diagonalizability is what makes the $P\Lambda^t P^{-1}$ shortcut available, not what makes the system stable.

<!-- page 7 -->

**Exercise 4 — Definiteness, Sylvester, and a caveat**

Let
$$A(a) = \begin{pmatrix} 2 & 1 & 0 \\ 1 & a & 1 \\ 0 & 1 & 2 \end{pmatrix}, \qquad a \in \mathbb{R}.$$

**(a)** Use Sylvester's criterion to find all $a$ for which $A(a)$ is positive definite.

**(b)** At the critical value of $a$, show $A$ is positive semi-definite and find a nonzero $x$ with $x^\top A x = 0$. Relate this vector to the spectrum of $A$.

**(c)** Suppose $A(a)$ is the Hessian of $f : \mathbb{R}^3 \to \mathbb{R}$ at a critical point. For which $a$ is that point a strict local minimum? A strict local maximum?

**(d)** Consider $M = \begin{pmatrix} 0 & 0 \\ 0 & -1 \end{pmatrix}$. Compute its *leading* principal minors and check them against clause 3 of Theorem 9 on slide 50. Then compute $x^\top M x$ directly. What is the correct semi-definiteness criterion?

<!-- page 8 -->

**Exercise 4 — Solution**

**(a)** $\det A_1 = 2$, $\det A_2 = 2a - 1$, $\det A_3 = 4a - 4$. All strictly positive if and only if $a > 1$.

**(b)** At $a = 1$ all *principal* minors (not just the leading ones) are non-negative — the $2 \times 2$ ones are $1, 4, 1$, and $\det A_3 = 0$ — so $A$ is positive semi-definite. Solving $Ax = 0$ gives $x = (1, -2, 1)^\top$, the eigenvector for $\lambda = 0$. This is consistent with Theorem 8: positive semi-definite with a zero eigenvalue.

**(c)** Strict local minimum if and only if the Hessian is positive definite, i.e. $a > 1$. A strict local maximum requires negative definiteness, hence $\det A_1 < 0$; but $\det A_1 = 2$, so no value of $a$ gives a local maximum.

**(d)** $\det M_1 = 0 \ge 0$ and $\det M_2 = 0 \ge 0$, so the criterion as stated on slide 50 would call $M$ positive semi-definite. But $x^\top M x = -x_2^2 \le 0$, so $M$ is negative semi-definite and *not* positive semi-definite. Leading principal minors characterize *definiteness* only; for semi-definiteness all $2^n - 1$ principal minors must be non-negative, not just the leading ones.