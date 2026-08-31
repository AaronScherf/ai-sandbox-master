---
source_pdf: Math_Camp_Recitation_1.pdf
folder_category: recitation_slides
total_pages: 18
routing: hybrid
model: gemini-3.1-flash-lite
pages_repaired: 1
repaired_pages: [14]
tags: [linear-algebra]
---

<!-- page 1 -->

## Exercise 1 — Rank, systems, and Rouché–Capelli

Consider the system in $x, y, z$, with parameters $a, b \in \mathbb{R}$:

$$\begin{aligned}
x + 2y + z &= 1 \\
2x + 4y + az &= 2 \\
x + ay + z &= b
\end{aligned}$$

**(a)** Compute $\det(A)$ for the coefficient matrix and determine for which $a$ the matrix is invertible.

**(b)** Using Gauss–Jordan on the augmented matrix, classify the solution set for every pair $(a, b)$.

**(c)** In the case with infinitely many solutions, give the dimension of the solution set and an explicit parametrization.

<!-- page 2 -->

## Exercise 1 — Solution

<!-- page 3 -->

## Exercise 1 — Solution

<!-- page 4 -->

## Exercise 1 — Solution

<!-- page 5 -->

## Exercise 2 — Subspaces, span, and basis

Work in $V = M_{2 \times 2}(\mathbb{R})$ with the usual matrix addition and scalar multiplication (you may assume this is a vector space).

**(a)** Let $W = \{A \in V : \text{tr}(A) = 0\}$. Verify the three subspace conditions and produce a basis. What is $\dim W$?

**(b)** Let $S = \{A \in V : A = A^\top\}$. Show $S$ is a subspace and find $\dim S$.

**(c)** Find a basis for $W \cap S$. (Any intersection of vector subspaces is a vector subspace.)

**(d)** Let $U = \{A \in V : A \text{ is invertible}\}$. Show $U$ is *not* a subspace in two different ways.

<!-- page 6 -->

## Exercise 2 — Solution

<!-- page 7 -->

## Exercise 2 — Solution

<!-- page 8 -->

## Exercise 2 — Solution

<!-- page 9 -->

## Exercise 3 — Diagonalization and a linear dynamic system

Let
$$A = \begin{pmatrix} 0.5 & 0.3 \\ 0.2 & 0.6 \end{pmatrix}, \quad x_t = A x_{t-1}, \quad x_0 = \begin{pmatrix} 5 \\ 0 \end{pmatrix}.$$

**(a)** Find the characteristic polynomial and the spectrum. Verify Proposition 12: $\det A = \prod_k \lambda_k^{a_k}$ and $\operatorname{tr} A = \sum_k a_k \lambda_k$.

**(b)** Find eigenvectors, construct $P$ and $\Lambda$ with $A = P \Lambda P^{-1}$, and derive a closed form for $x_t$. What is $\lim_{t \to \infty} x_t$, and which eigenvalue governs the rate of convergence?

**(c)** Now let $B = \begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix}$. Show $B$ is not diagonalizable by comparing algebraic and geometric multiplicity. Does $B^t x_0 \to 0$? What does this say about the converse of the stability argument in **(b)**?

<!-- page 10 -->

## Exercise 3 — Solution

<!-- page 11 -->

## Exercise 3 — Solution

<!-- page 12 -->

## Exercise 3 — Solution

<!-- page 13 -->

## Exercise 3 — Solution

<!-- page 14 -->

## Exercise 4 — Definiteness, Sylvester, and a caveat

Let

$$A(a) = \begin{pmatrix} 2 & 1 & 0 \\ 1 & a & 1 \\ 0 & 1 & 2 \end{pmatrix}, \quad a \in \mathbb{R}.$$

**(a)** Use Sylvester's criterion to find all $a$ for which $A(a)$ is positive definite.

**(b)** At the critical value of $a$, show $A$ is positive semi-definite and find a nonzero $x$ with $x^\top A x = 0$. Relate this vector to the spectrum of $A$.

**(c)** Suppose $A(a)$ is the Hessian of $f : \mathbb{R}^3 \to \mathbb{R}$ at a critical point. For which $a$ is that point a strict local minimum? A strict local maximum?

**(d)** Consider $M = \begin{pmatrix} 0 & 0 \\ 0 & -1 \end{pmatrix}$. Compute its *leading* principal minors and check them against clause 3 of Theorem 9 on slide 50. Then compute $x^\top M x$ directly. What is the correct semi-definiteness criterion?

<!-- page 15 -->

## Exercise 4 — Solution

<!-- page 16 -->

## Exercise 4 — Solution

<!-- page 17 -->

## Exercise 4 — Solution

<!-- page 18 -->

## Exercise 4 — Solution