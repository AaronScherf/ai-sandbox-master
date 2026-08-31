---
source_pdf: Math_Camp_Recitation_2 with solution.pdf
folder_category: recitation_slides
total_pages: 8
routing: gemini_batched
model: gemini-3.1-flash-lite
pages_repaired: 2
repaired_pages: [5, 8]
tags: [linear-algebra]
---

<!-- page 1 -->

### Exercise 5 — Change of basis

Let $\mathcal{B} = \{v_1, v_2\}$ with $v_1 = (1, 1)^\top$, $v_2 = (3, -2)^\top$, and let $\mathcal{E}$ be the standard basis of $\mathbb{R}^2$. For a basis $\mathcal{B}$, write $[x]_\mathcal{B}$ for the *coordinate vector* of $x$: the unique scalars $(c_1, c_2)$ with $x = c_1 v_1 + c_2 v_2$ (uniqueness is Proposition 8).

**(a)** Show $\mathcal{B}$ is a basis of $\mathbb{R}^2$ and compute $[x]_\mathcal{B}$ for $x = (5, 0)^\top$.

**(b)** Let $P = [v_1 \ v_2]$. Show that $P[x]_\mathcal{B} = x$ for every $x$, so $P$ is the transition matrix from $\mathcal{B}$-coordinates to standard coordinates and $P^{-1}$ goes the other way. Why must $P$ be invertible?

**(c)** Let $T : \mathbb{R}^2 \to \mathbb{R}^2$ have standard matrix $A = \begin{pmatrix} 0.5 & 0.3 \\ 0.2 & 0.6 \end{pmatrix}$, i.e. $[T(x)]_\mathcal{E} = A[x]_\mathcal{E}$. Show that the matrix representing $T$ in $\mathcal{B}$-coordinates is $P^{-1}AP$, and compute it. What have you just re-derived?

**(d)** Now let $\mathcal{C} = \{(1, 0)^\top, (1, 1)^\top\}$ with $Q = [c_1 \ c_2]$. Find the matrix taking $\mathcal{B}$-coordinates directly to $\mathcal{C}$-coordinates, and verify it by converting $v_1$ and $v_2$ by hand.

**(e)** Explain why $\operatorname{tr}(P^{-1}AP) = \operatorname{tr}(A)$ and $\det(P^{-1}AP) = \det(A)$ for *any* invertible $P$.

<!-- page 2 -->

### Exercise 5 — Solution

**(a)** $\det[v_1 \ v_2] = -5 \neq 0$, so the vectors are L.I.; two L.I. vectors in a 2-dimensional space form a basis. Solving $c_1 v_1 + c_2 v_2 = (5, 0)^\top$ gives $[x]_\mathcal{B} = (2, 1)^\top$.

**(b)** By the definition of matrix–vector multiplication, $Pc = c_1 v_1 + c_2 v_2$, which equals $x$ when $c = [x]_\mathcal{B}$. $P$ is invertible because its columns are L.I. (Summary slide, statements 3 and 4). Note this is the same computation as **(a)**: $P^{-1}x = (2, 1)^\top$.

**(c)** Given $[x]_\mathcal{B}$, recover $x = P[x]_\mathcal{B}$, apply $T$ to get $AP[x]_\mathcal{B}$, then convert back:
$$[T(x)]_\mathcal{B} = P^{-1}AP [x]_\mathcal{B}.$$

Here $AP = [0.8v_1 \ 0.3v_2] = P\Lambda$, so $P^{-1}AP = \Lambda = \begin{pmatrix} 0.8 & 0 \\ 0 & 0.3 \end{pmatrix}$.

This is diagonalization, read as a change of basis: $A = P\Lambda P^{-1}$ says $A$ and $\Lambda$ are the same linear map written in two bases, and in the eigenbasis the map is independent scaling along each axis. That is why $A^t = P\Lambda^t P^{-1}$ works — change coordinates, iterate trivially, change back.

<!-- page 3 -->

### Exercise 5 — Solution (cont’d)

**(d)** Since $[x]_\mathcal{C} = Q^{-1}x$ and $x = P[x]_\mathcal{B}$, the matrix is $Q^{-1}P$:
$$Q^{-1}P = \begin{pmatrix} 1 & -1 \\ 0 & 1 \end{pmatrix} \begin{pmatrix} 1 & 3 \\ 1 & -2 \end{pmatrix} = \begin{pmatrix} 0 & 5 \\ 1 & -2 \end{pmatrix}.$$

Check: $v_1 = (1, 1)^\top = 0 \cdot c_1 + 1 \cdot c_2$, giving first column $(0, 1)^\top$; and $v_2 = (3, -2)^\top = 5c_1 - 2c_2$, giving second column $(5, -2)^\top$.

**(e)** For the trace, use cyclicity (slide 7):
$$\operatorname{tr}(P^{-1}AP) = \operatorname{tr}(APP^{-1}) = \operatorname{tr}(A).$$

For the determinant, use multiplicativity together with $|P^{-1}| = 1/|P|$ (Propositions 3.4 and 6.7):
$$|P^{-1}AP| = |P^{-1}| |A| |P| = |A|.$$

So trace and determinant are properties of the map itself, not of the basis it is written in — which is why Proposition 12 can express both in terms of the eigenvalues alone.

<!-- page 4 -->

### Exercise 6 — Inner product spaces

Let
$$M = \begin{pmatrix} 2 & 1 \\ 1 & 1 \end{pmatrix}, \quad \langle u, v \rangle_M := u^\top M v \quad \text{on } \mathbb{R}^2.$$

**(a)** Verify $M$ is positive definite. Then show $\langle \cdot, \cdot \rangle_M$ satisfies the three inner product axioms, and identify exactly which property of $M$ each axiom requires. What goes wrong if $M$ is symmetric but only positive *semi*-definite?

**(b)** Compute $\|e_1\|_M$, $\|e_2\|_M$ and $\langle e_1, e_2 \rangle_M$ for the standard basis vectors. Are $e_1, e_2$ orthogonal in this space? Verify the Cauchy–Schwarz inequality for this pair.

**(c)** Apply Gram–Schmidt to $\{e_1, e_2\}$ with respect to $\langle \cdot, \cdot \rangle_M$ to produce an $M$-orthonormal basis $\{u_1, u_2\}$. Recall
$$w_2 = e_2 - \frac{\langle e_2, w_1 \rangle_M}{\langle w_1, w_1 \rangle_M} w_1.$$

**(d)** Let $R = [u_1 \ u_2]$. Compute $R^\top MR$. What have you found, and how does it relate to Theorems 10 and 11 on the last slide of the notes?

<!-- page 5 -->

### Exercise 6 — Solution

**(a)** Sylvester: $\det M_1 = 2 > 0$ and $\det M_2 = 1 > 0$, so $M$ is positive definite.

*   *Commutativity* needs $M = M^\top$: the scalar $u^\top M v$ equals its own transpose $v^\top M^\top u$, which is $\langle v, u \rangle_M$ only when $M$ is symmetric.
*   *Linearity* holds for any $M$, since $u \mapsto u^\top M v$ is linear.
*   *Positive definiteness* of the inner product is literally the definiteness of $M$: $\langle u, u \rangle_M = u^\top M u > 0$ for $u \neq 0$.

If $M$ is only positive semi-definite, axiom (3) fails in its “equality iff $u = 0$” half: some $u \neq 0$ has $u^\top M u = 0$ (Exercise **4(b)** produced exactly such a vector). The induced norm then assigns length zero to a nonzero vector, so condition (1) of Definition 16 fails as well.

**(b)** $\langle e_1, e_1 \rangle_M = m_{11} = 2$, so $\|e_1\|_M = \sqrt{2}$; $\langle e_2, e_2 \rangle_M = m_{22} = 1$, so $\|e_2\|_M = 1$; and $\langle e_1, e_2 \rangle_M = m_{12} = 1 \neq 0$, so $e_1$ and $e_2$ are *not* orthogonal here, though they are under the dot product. In general $\langle e_i, e_j \rangle_M = m_{ij}$: the matrix is the table of inner products of the standard basis. Cauchy–Schwarz: $|1| \le \sqrt{2} \cdot 1$, strict because the vectors are not parallel.

<!-- page 6 -->

### Exercise 6 — Solution (cont’d)

**(c)** Take $w_1 = e_1 = (1, 0)^\top$. Then
$$w_2 = e_2 - \frac{1}{2}w_1 = \left(-\frac{1}{2}, 1\right)^\top, \quad \langle w_1, w_2 \rangle_M = 0.$$

Since $\langle w_2, w_2 \rangle_M = \frac{1}{2}$, normalizing gives
$$u_1 = \left(\frac{1}{\sqrt{2}}, 0\right)^\top, \quad u_2 = \left(-\frac{1}{\sqrt{2}}, \sqrt{2}\right)^\top.$$

**(d)** $R^\top MR = I$. The columns of $R$ are $M$-orthonormal, and that statement written in matrix form is exactly $R^\top MR = I$ — the same way $A^\top A = I$ encodes ordinary orthonormality (slide 45).

<!-- page 7 -->

### Exercise 6 — Solution: the connection to Cholesky

Rearranging $R^\top M R = I$ gives

$$M = (R^{-1})^\top R^{-1} = L L^\top, \quad L = (R^{-1})^\top,$$

which is the Cholesky decomposition of $M$. Concretely,

$$M = L D L^\top, \quad L = \begin{pmatrix} 1 & 0 \\ \frac{1}{2} & 1 \end{pmatrix}, \quad D = \operatorname{diag}\left(2, \frac{1}{2}\right),$$

and the entries $2$ and $\frac{1}{2}$ are precisely the squared norms $\langle w_1, w_1 \rangle_M$ and $\langle w_2, w_2 \rangle_M$ computed in **(c)**. Gram–Schmidt in the $M$-inner product and the Cholesky factorization of $M$ are the same computation.

Theorem 11 asserts that $M$ is positive definite iff a Cholesky factor exists. Part **(a)** shows positive definiteness is equivalent to $M$ defining an inner product, and **(c)**–**(d)** show that an inner product always yields an orthonormal basis. That is one direction of Theorem 11, assembled from pieces already available.

<!-- page 8 -->

### Exercise 7 — Idempotent matrices and projection

Let $\iota = (1, 1, 1)^\top \in \mathbb{R}^3$ and

$$P = \frac{\iota \iota^\top}{\iota^\top \iota} = \frac{1}{3} \begin{pmatrix} 1 & 1 & 1 \\ 1 & 1 & 1 \\ 1 & 1 & 1 \end{pmatrix}, \quad M = I_3 - P.$$

**(a)** Show $P$ is symmetric and idempotent, and that $M$ is too. Compute $PM$.

**(b)** Find $\rho(P)$ and $\operatorname{tr}(P)$. Find all eigenvalues of $P$ with their algebraic and geometric multiplicities, and describe the eigenspaces geometrically. Is $P$ diagonalizable?

**(c)** Prove in general: if $A$ is idempotent then its only possible eigenvalues are 0 and 1, $A$ is diagonalizable, and $\rho(A) = \operatorname{tr}(A)$.

**(d)** Compute $Px$ and $Mx$ for $x = (2, 5, 8)^\top$. Is $P$ positive definite, positive semi-definite, or indefinite? Justify your answer using the spectrum rather than Sylvester's criterion.