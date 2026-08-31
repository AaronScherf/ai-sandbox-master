---
source_pdf: Math_Camp_Recitation_2.pdf
folder_category: recitation_slides
total_pages: 15
routing: hybrid
model: gemini-3.1-flash-lite
pages_repaired: 1
repaired_pages: [1]
tags: [linear-algebra]
---

<!-- page 1 -->

**Exercise 6 — Basis for Column Space and Kernel**

Given a matrix,
$$A = \begin{bmatrix} 1 & 2 & 2 & 1 \\ 2 & 4 & 6 & 0 \\ 3 & 6 & 8 & 1 \end{bmatrix}$$

**(a)** Find a basis for the column space.  
**(b)** Find a basis for the kernel.

<!-- page 2 -->

**Exercise 5 — Solution**

<!-- page 3 -->

**Exercise 5 — Solution**

<!-- page 4 -->

Exercise 5 — Solution

<!-- page 5 -->

Exercise 5 — Solution

<!-- page 6 -->

### Exercise 6 — Change of basis

Let $\mathcal{B} = \{v_1, v_2\}$ with $v_1 = (1, 1)^\top, v_2 = (3, -2)^\top$, and let $\mathcal{E}$ be the standard basis of $\mathbb{R}^2$. For a basis $\mathcal{B}$, write $[x]_\mathcal{B}$ for the *coordinate vector* of $x$: the unique scalars $(c_1, c_2)$ with $x = c_1 v_1 + c_2 v_2$ (uniqueness is Proposition 8).

**(a)** Show $\mathcal{B}$ is a basis of $\mathbb{R}^2$ and compute $[x]_\mathcal{B}$ for $x = (5, 0)^\top$.

**(b)** Let $P = [v_1 \ v_2]$. Show that $P[x]_\mathcal{B} = x$ for every $x$, so $P$ is the transition matrix from $\mathcal{B}$-coordinates to standard coordinates and $P^{-1}$ goes the other way. Why must $P$ be invertible?

**(c)** Let $T : \mathbb{R}^2 \to \mathbb{R}^2$ have standard matrix $A = \begin{pmatrix} 0.5 & 0.3 \\ 0.2 & 0.6 \end{pmatrix}$, i.e. $[T(x)]_\mathcal{E} = A[x]_\mathcal{E}$. Show that the matrix representing $T$ in $\mathcal{B}$-coordinates is $P^{-1}AP$, and compute it. What have you just re-derived?

**(d)** Now let $\mathcal{C} = \{(1, 0)^\top, (1, 1)^\top\}$ with $Q = [c_1 \ c_2]$. Find the matrix taking $\mathcal{B}$-coordinates directly to $\mathcal{C}$-coordinates, and verify it by converting $v_1$ and $v_2$ by hand.

**(e)** Explain why $\text{tr}(P^{-1}AP) = \text{tr}(A)$ and $\det(P^{-1}AP) = \det(A)$ for *any* invertible $P$.

<!-- page 7 -->

Exercise 6 — Solution

<!-- page 8 -->

Exercise 6 — Solution

<!-- page 9 -->

Exercise 6 — Solution

<!-- page 10 -->

Exercise 6 — Solution

<!-- page 11 -->

### Exercise 7 — Inner product spaces

Let
$$M = \begin{pmatrix} 2 & 1 \\ 1 & 1 \end{pmatrix}, \quad \langle u, v \rangle_M := u^\top M v \quad \text{on } \mathbb{R}^2.$$

**(a)** Verify $M$ is positive definite. Then show $\langle \cdot, \cdot \rangle_M$ satisfies the three inner product axioms, and identify exactly which property of $M$ each axiom requires. What goes wrong if $M$ is symmetric but only positive *semi*-definite?

**(b)** Compute $\|e_1\|_M$, $\|e_2\|_M$ and $\langle e_1, e_2 \rangle_M$ for the standard basis vectors. Are $e_1, e_2$ orthogonal in this space? Verify the Cauchy–Schwarz inequality for this pair.

**(c)** Apply Gram–Schmidt to $\{e_1, e_2\}$ with respect to $\langle \cdot, \cdot \rangle_M$ to produce an $M$-orthonormal basis $\{u_1, u_2\}$. Recall
$$w_2 = e_2 - \frac{\langle e_2, w_1 \rangle_M}{\langle w_1, w_1 \rangle_M} w_1.$$

**(d)** Let $R = [u_1 \ u_2]$. Compute $R^\top M R$. What have you found, and how does it relate to Theorems 10 and 11 on the last slide of Bruno's notes?

<!-- page 12 -->

Exercise 7 — Solution

<!-- page 13 -->

Exercise 7 — Solution

<!-- page 14 -->

Exercise 7 — Solution

<!-- page 15 -->

Exercise 7 — Solution