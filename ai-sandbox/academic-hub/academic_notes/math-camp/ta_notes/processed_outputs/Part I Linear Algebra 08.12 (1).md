---
source_pdf: Part I Linear Algebra 08.12 (1).pdf
folder_category: ta_notes
total_pages: 11
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [linear-algebra]
---

<!-- page 1 -->

Part I: Linear Algebra 08.12
Wednesday, August 12, 2026 8:57 PM

Recall: Invariant Subspace of $T \in \mathcal{L}(V)$
$U \le V$ and $T(U) \subseteq U$.
Then we say $U$ is invariant under $T$
($T$-invariant).

?: What is the matrix of $T$ under a basis of $V$ when $U \le V$ is $T$-invariant?

ANS: Take $u_1, \dots, u_k$ a basis for $U$.
By Basis Extension, we can find $u_{k+1}, \dots, u_n$
such that $(\underbrace{u_1, \dots, u_k}_{\substack{\text{basis of } U \\ T\text{-invariant}}}, u_{k+1}, \dots, u_n)$ is a basis of $V$.

$$T(u_1, \dots, u_k, u_{k+1}, \dots, u_n) = (u_1, \dots, u_k, u_{k+1}, \dots, u_n) \begin{bmatrix} A_{k \times k} & C \\ O & B \end{bmatrix}$$

As a corollary:
If $V = U \oplus W$ and both $U$ and $W$ are $T$-invariant. Then the matrix of $T$ under basis $(\underbrace{u_1, \dots, u_k}_U, \underbrace{w_1, \dots, w_J}_W)$ is $\begin{bmatrix} A & O \\ O & B \end{bmatrix}$

If this is unclear, try writing out
$T(u_1) = a_{11}u_1 + a_{21}u_2 + \dots + a_{k1}u_k + 0w_1 + \dots + 0w_J$
$T(u_2) = a_{12}u_1 + a_{22}u_2 + \dots + a_{k2}u_k + 0w_1 + \dots + 0w_J$
$\vdots$
$T(w_1) = 0u_1 + 0u_2 + \dots + 0u_k + b_{11}w_1 + b_{21}w_2 + \dots + b_{J1}w_J$
$\vdots$
$T(w_J) = 0u_1 + 0u_2 + \dots + 0u_k + b_{1J}w_1 + b_{2J}w_2 + \dots + b_{JJ}w_J$

Collect this in matrix form we have
$$T(u_1, \dots, u_k, w_1, \dots, w_J) = (u_1, \dots, u_k, w_1, \dots, w_J) \begin{bmatrix} A & O \\ O & B \end{bmatrix}$$

?: What is the simplest invariant subspace for a linear transformation? i.e. one-dimensional $T$-invariant subspace.

Note: A one dimensional space is $\operatorname{Span}(v)$.

For $T(\operatorname{Span}(v))$ to be $T$-invariant...

<!-- page 2 -->

Note: A one dimensional space is $\operatorname{Span}(v)$.

ANS: For $\operatorname{Span}(v) \le V$, to be $T$-invariant

It has to be that $T(v) = \lambda v$ for some $\lambda \in \mathbb{K}$.
This leads to the concept of eigenvalues and eigenvectors.

- Eigenvalues and Eigenvectors.

Note: For this section, we require that the field $\mathbb{K}$ is algebraically closed, meaning that any polynomial with coefficients in $\mathbb{K}$ has a root in $\mathbb{K}$.

- $\mathbb{Q}$ is a field, NOT algebraically closed.
  e.g. $x^2 - 2 = 0 \Rightarrow x = \pm\sqrt{2} \notin \mathbb{Q}$

- $\mathbb{R}$ is a field, NOT algebraically closed.
  e.g. $x^2 + 1 = 0 \Rightarrow x = \pm i \notin \mathbb{R}$

- $\mathbb{C}$ is a field, IS algebraically closed.

If you want, take $\mathbb{K} = \mathbb{C}$.

- Definition: $(V, +, \cdot)$, $T \in \mathcal{L}(V)$.

If $v \neq 0_V : T(v) = \lambda v$ for some $\lambda \in \mathbb{K}$.
We call $\lambda$ an eigenvalue of $T$ and $v$ its associated eigenvector.

! : Eigenvectors has to be non-zero.

Definition: $(\mathbb{K}^n, +, \cdot)$, $A \in \mathbb{K}^{n \times n}$

$x \neq 0_{\mathbb{K}^n} : Ax = \lambda x$ for some $\lambda \in \mathbb{K}$
$\lambda$ an eigenvalue of $A$
$x$ its eigenvector.

- Key condition for eigenvalue/vectors:

$$T \in \mathcal{L}(V)$$
$$v \neq 0_V : T(v) = \lambda v \ (= \lambda \mathrm{id}_V(v))$$
$$\Updownarrow$$
$$(T - \lambda \mathrm{id}_V)(v) = 0_V$$
$$\Updownarrow$$

$$A \in \mathbb{K}^{n \times n}$$
$$x \neq 0_{\mathbb{K}^n} : Ax = \lambda x \ (= \lambda I_n x)$$
$$\Updownarrow$$
$$(A - \lambda I_n)x = 0_{\mathbb{K}^n}$$
$$\Updownarrow$$

<!-- page 3 -->

$$(T - \lambda \mathrm{id}_V)(v) = 0_V$$
$$\Updownarrow$$
$$E_\lambda(T) := \operatorname{ker}(T - \lambda \mathrm{id}_V) \neq \{0_V\}$$
$$\Updownarrow$$
$$T - \lambda \mathrm{id}_V \text{ is NOT injective}$$
$$\Updownarrow$$
$$T - \lambda \mathrm{id}_V \text{ is NOT surjective}$$
$$\text{- - - - - - } \text{ NOT bijection}$$
$$\Updownarrow$$
$$T - \lambda \mathrm{id}_V \text{ is NOT invertible}$$
$$\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \searrow$$
$$(A - \lambda I_n)x = 0_{\mathbb{K}^n}$$
$$\Updownarrow$$
$$E_\lambda(A) := \operatorname{ker}(A - \lambda I_n) \neq \{0_{\mathbb{K}^n}\}$$
$$\Updownarrow$$
$$A - \lambda I_n \text{ is NOT injective}$$
$$\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ (\text{viewed as } \mathcal{L}(\mathbb{K}^n))$$
$$\Updownarrow$$
$$A - \lambda I_n \text{ is NOT surjective}$$
$$\text{- - - - - - } \text{ NOT bijection}$$
$$\Updownarrow$$
$$A - \lambda I_n \text{ is NOT invertible.}$$
$$\swarrow$$
$$\det(T - \lambda \mathrm{id}_V) := \det(A - \lambda I_n) = 0$$

- Procedure to find eigenvalue/vectors for $A \in \mathbb{K}^{n \times n}$
$$\Updownarrow$$
for $T \in \mathcal{L}(V)$ whose matrix is $A \in \mathbb{K}^{n \times n}$ under a basis.

1. Calculate $\det(A - \lambda I_n)$.
2. Set $p_A(\lambda) := \det(A - \lambda I_n) = 0$ solve for its roots.
   $\lambda_1, \dots, \lambda_n$ ($\text{Some } \lambda_i \text{s might be the same}$)
3. For every distinct $\lambda_i$, solve linear system
   $$(A - \lambda_i I_n)X = 0_{\mathbb{K}^n}$$
   to get eigenvectors (in $\operatorname{ker}(A - \lambda_i I_n) =: E_{\lambda_i}(A)$) $\leftarrow \text{eigenspace}$.

- Basic properties of Eigenvectors and Eigenspaces.
  - Claim: Eigenvectors associated with distinct eigenvalues are linearly independent.
    Proof: Take $v_1, \dots, v_s$ to be the eigenvectors for $\lambda_1, \dots, \lambda_s$ and $\lambda_i \neq \lambda_j$ for all $i \neq j$.
    Suppose $v_1, \dots, v_s$ is lin. dep.
    $\Delta$ Define $1 \le m \le S$ to be the minimal integer such that
    $\rightarrow C_1 v_1 + C_2 v_2 + \dots + C_m v_m = 0_V$ has nontrivial $C_i$s.
    $$T(0_V) = T(C_1 v_1 + C_2 v_2 + \dots + C_m v_m) = C_1 T(v_1) + C_2 T(v_2) + \dots + C_m T(v_m)$$

Linear Algebra Page 3

<!-- page 4 -->

$$\begin{aligned}
\rightarrow \ & c_1 v_1 + c_2 v_2 + \dots + c_m v_m = 0_V \quad \text{has nontrivial } c_i \text{s.} \\
T(0_V) = T(c_1 v_1 + c_2 v_2 + \dots + c_m v_m) &= c_1 T(v_1) + c_2 T(v_2) + \dots + c_m T(v_m) \\
&= c_1 \lambda_1 v_1 + c_2 \lambda_2 v_2 + \dots + c_m \lambda_m v_m \\
&= 0_V
\end{aligned}$$

$$\begin{aligned}
c_1 \lambda_1 v_1 + c_2 \lambda_2 v_2 + \dots + c_m \lambda_m v_m &= 0_V \quad (\times \lambda_m) \\
\underline{- \ \ c_1 \lambda_m v_1 + c_2 \lambda_m v_2 + \dots + c_m \lambda_m v_m &= 0_V} \\
c_1 (\lambda_m - \lambda_1) v_1 + c_2 (\lambda_m - \lambda_2) v_2 + \dots + c_{m-1}(\lambda_m - \lambda_{m-1}) v_{m-1} &= 0_V \quad (*)
\end{aligned}$$

In $c_1, \dots, c_m$, there must be at least 2 nonzero numbers because $v_i$'s are eigenvectors.
Then $(*)$ finds $m-1$ coefficients, nontrivial such that
the linear combination of $v_1, \dots, v_{m-1} = 0_V$.
This contradicts the minimality of $m$.

$$\square$$

* Claim: If $\lambda, \mu$ eigenvalues and $\lambda \neq \mu$.
$$E_\lambda(T) \cap E_\mu(T) = \{0_V\}$$
Proof: Take $v \in E_\lambda(T) \cap E_\mu(T)$
then $T(v) = \lambda v \underset{*}{\overline{=}} T(v) = \mu v$
thus $(\lambda - \mu) v = 0_V \Rightarrow v = 0_V \text{ since } \lambda \neq \mu$.
$$\square$$

* Note: Eigenspace is all eigenvectors $\cup$ the zero vector.
* Claim: Eigenspace is a subspace. ($\operatorname{ker}(T - \lambda \mathrm{id}_V)$)
  Eigenspace is $T$-invariant. (Easy check).

- Diagonalization:
  Suppose we have $n$ eigenvectors $v_1, \dots, v_n$ for eigenvalues $\lambda_1, \dots, \lambda_n$ (some might be the same) for $T \in \mathcal{L}(V)$
  $v_1, \dots, v_n$ lin. indep. and since $\dim V = n$,
  $v_1, \dots, v_n$ form a basis for $V$.
  Then
  $$T(v_1, \dots, v_n) = (v_1, \dots, v_n) \begin{pmatrix} \lambda_1 & & \\ & \lambda_2 & \\ & & \ddots & \\ & & & \lambda_n \end{pmatrix}$$

<!-- page 5 -->

$$= (v_1, \dots, v_n) \operatorname{diag}\{\lambda_1, \lambda_2, \dots, \lambda_n\}.$$

We call that $T$ is diagonalizable.

In the matrix world: $A \in \mathbb{K}^{n \times n}$, $p_1, \dots, p_n \in \mathbb{K}^n$ eigenvectors, lin. indep.

$$A \begin{pmatrix} | & | & & | \\ p_1 & p_2 & \dots & p_n \\ | & | & & | \end{pmatrix} = \begin{pmatrix} | & | & & | \\ p_1 & p_2 & \dots & p_n \\ | & | & & | \end{pmatrix} \begin{bmatrix} \lambda_1 & & & \\ & \lambda_2 & & \\ & & \ddots & \\ & & & \lambda_n \end{bmatrix}$$

Let $P = \begin{pmatrix} | & | & & | \\ p_1 & p_2 & \dots & p_n \\ | & | & & | \end{pmatrix}$, since $p_1, p_2, \dots, p_n$ are basis,
$P$ has full rank $\Leftrightarrow P$ invertible.

$$P^{-1} A P = \operatorname{diag}\{\lambda_1, \lambda_2, \dots, \lambda_n\}.$$

We say $A$ is diagonalizable.

* The key for $T \in \mathcal{L}(V)$ ($A \in \mathbb{K}^{n \times n}$) to be diagonalizable is that we can find a basis for $V$ from its eigenvectors.

* Remark: Not all matrixes are diagonalizable!
(See assignment 1)

- Why is diagonalization useful?
One reason: Calculate $A^k$. Direct computation is lengthy.
If $A$ is diagonalizable. Then $\exists P$ invertible,
$$D = P^{-1} A P = \begin{bmatrix} \lambda_1 & & \\ & \lambda_2 & \\ & & \ddots & \\ & & & \lambda_n \end{bmatrix} \Leftrightarrow A = P D P^{-1} \text{ where } D = \operatorname{diag}\{\lambda_1, \dots, \lambda_n\}$$

Then $A^k = (P D P^{-1})^k = (P D \underbrace{P^{-1}) (P}_{I_n} D \underbrace{P^{-1}) \dots (P}_{I_n} D P^{-1})$

$$\begin{aligned}
&= P D^k P^{-1} = P \begin{bmatrix} \lambda_1 & & \\ & \lambda_2 & \\ & & \ddots & \\ & & & \lambda_n \end{bmatrix}^k P^{-1} \\
&= P \begin{bmatrix} \lambda_1^k & & \\ & \lambda_2^k & \\ & & \ddots & \\ & & & \lambda_n^k \end{bmatrix} P^{-1}.
\end{aligned}$$

- A Few Notes on Matrix Multiplication.
Matrix multiplication represents composition of

<!-- page 6 -->

- A Few Notes on Matrix Multiplication.
  - Matrix Multiplication represents composition of Linear maps:
$$\begin{array}{ccccccc} & S & & T & \\ V & \longrightarrow & U & \longrightarrow & W \\ & \searrow & & \nearrow & \\ & & T \circ S & & \end{array} \Rightarrow \begin{aligned} S(v_1, \dots, v_n) &= (u_1, \dots, u_l) A \\ T \circ S(v_1, \dots, v_n) &= T(S(v_1, \dots, v_n)) \\ &= T((u_1, \dots, u_l) A) \\ &= [T(u_1, \dots, u_l)] A \\ &= (w_1, w_2, \dots, w_m) BA \end{aligned}$$

$$\begin{array}{ccccccc} & A & & B & \\ \mathbb{K}^n & \longrightarrow & \mathbb{K}^l & \longrightarrow & \mathbb{K}^m \\ & \searrow & & \nearrow & \\ & & BA & & \end{array}$$

  - Four ways of looking at $A_{m \times l} B_{l \times n}$.
$$A = \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1l} \\ a_{21} & a_{22} & \dots & a_{2l} \\ \vdots & \vdots & \ddots & \vdots \\ a_{m1} & a_{m2} & \dots & a_{ml} \end{pmatrix} = \begin{pmatrix} \text{--- } a_1^T \text{ ---} \\ \text{--- } a_2^T \text{ ---} \\ \vdots \\ \text{--- } a_m^T \text{ ---} \end{pmatrix} \quad a_i \in \mathbb{K}^l$$

$$B = \begin{pmatrix} b_{11} & b_{12} & \dots & b_{1n} \\ b_{21} & b_{22} & \dots & b_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ b_{l1} & b_{l2} & \dots & b_{ln} \end{pmatrix} = \begin{pmatrix} | & | & & | \\ b_1 & b_2 & \dots & b_n \\ | & | & & | \end{pmatrix} \quad b_i \in \mathbb{K}^l$$

1. Element-wise: Let $C = AB$
$$c_{ij} = \sum_{k=1}^l a_{ik} b_{kj} \quad i \begin{pmatrix} \text{--- } \end{pmatrix} \begin{pmatrix} | \\ j \\ | \end{pmatrix}$$

2. Matrix by columns: $A_{m \times l} b_i{}_{l \times 1} = m \times 1$
$$\underset{m \times l}{AB} \underset{l \times n}{=} A (b_1, \dots, b_n) = (A b_1, A b_2, \dots, A b_n)_{m \times n}$$

3. Rows by Matrix:
$$AB = \begin{pmatrix} a_1^T \\ a_2^T \\ \vdots \\ a_m^T \end{pmatrix} B = \begin{pmatrix} a_1^T B \\ a_2^T B \\ \vdots \\ a_m^T B \end{pmatrix}_{m \times n} \quad \underset{1 \times l}{a_i^T} \underset{l \times n}{B} = 1 \times n$$

4. Inner product view:
$$AB = \begin{pmatrix} a_1^T \\ a_2^T \\ \vdots \\ a_m^T \end{pmatrix} (b_1, \dots, b_n) = \begin{pmatrix} a_1^T b_1 & a_1^T b_2 & \dots & a_1^T b_n \\ \vdots & \vdots & \ddots & \vdots \\ a_m^T b_1 & a_m^T b_2 & \dots & a_m^T b_n \end{pmatrix} \in \mathbb{K}$$

<!-- page 7 -->

Eigenvectors of distinct eigenvalues are lin indep.
$$\Downarrow$$
If $\lambda_1, \dots, \lambda_n$ are distinct, then diagonalizable.
$$\mathop{\Rightarrow}\limits_{\neq}$$
Note: If $\det(A - \lambda I_3) = (1-\lambda)^2(2-\lambda)$
Then $A$ has 3 eigenvalues: $\lambda_1 = \lambda_2 = 1, \lambda_3 = 2$.
If $\det(B - \lambda I_3) = (1-\lambda)(2-\lambda)(3-\lambda)$.
Then $B$ has 3 distinct eigenvalues $\lambda_1 = 1, \lambda_2 = 2, \lambda_3 = 3$
$\Rightarrow B$ is diagonalizable.

- Procedure for diagonalization of a diagonalizable matrix.
  1. Find eigenvalues and eigenvectors
     For eigenvectors, you solve for $E_\lambda(A)$.
  2. Find basis vectors for $E_{\lambda_i}(A) \quad i = 1, \dots, s$.
  3. Put the basis vectors to $P = \begin{bmatrix} | & | & & | \\ P_1 & P_2 & \dots & P_n \\ | & | & & | \end{bmatrix}$
  4. $D = P^{-1} A P \Leftrightarrow A = P D P^{-1}$
  Computer does this pretty well and fast.

- Inner Product Spaces
  * Motivation:
    So far for $(V, +, \cdot)$ we can $+$, $\cdot$, choose basis and study Linear maps (transformations).
    Missing: Length of a vector.
    Angle between two vectors. $\Big\}$ These are available in $\mathbb{R}^2$, and $\mathbb{R}^3$.
  * Review: Dot product in $\mathbb{R}^n$.
    $x = (x_1, \dots, x_n)^T, \ y = (y_1, \dots, y_n)^T$
    $x \cdot y = x_1 y_1 + x_2 y_2 + \dots + x_n y_n = x^T y = (x_1, \dots, x_n) \begin{pmatrix} y_1 \\ \vdots \\ y_n \end{pmatrix}$
    $x \cdot x = x_1^2 + x_2^2 + \dots + x_n^2 = \|x\|^2 \quad \text{(square of length)}$

<!-- page 8 -->

$$x \cdot y = x_1 y_1 + x_2 y_2 + \dots + x_n y_n = x^T y = (x_1, \dots, x_n) \begin{pmatrix} y_1 \\ \vdots \\ y_n \end{pmatrix}$$
$$x \cdot x = x_1^2 + x_2^2 + \dots + x_n^2 = \|x\|^2 \quad \text{(square of length)}$$

If $x \cdot y = 0$, we know that $x \perp y$.

The concept of Inner Product Spaces generalizes this.

- Definition:
Let $V$ be a vec. space over $\mathbb{R}$ or $\mathbb{C}$.
An inner product on $V$ is a function
$$\langle \cdot, \cdot \rangle : V \times V \longrightarrow \mathbb{K} \ (= \mathbb{R} \text{ or } \mathbb{C})$$
such that for all $u, v, w \in V$ and $\alpha, \beta \in \mathbb{K}$

(1). Linearity in the first argument:
$$\langle \alpha u + \beta v, w \rangle = \alpha \langle u, w \rangle + \beta \langle v, w \rangle$$

(2). Conjugate symmetry:
$$\langle u, v \rangle = \overline{\langle v, u \rangle} \quad \left( \begin{aligned} &\text{Recall if } z \in \mathbb{C}, z = a + bi, a, b \in \mathbb{R} \\ &\text{Conjugate of } z : \bar{z} = a - bi, a, b \in \mathbb{R} \end{aligned} \right)$$

(3). Positive Definiteness:
$$\langle v, v \rangle \ge 0 \quad \text{with } \langle v, v \rangle = 0 \iff v = 0_V$$

A vector space equipped with an inner product is called an inner product space.

$$(V, +, \cdot) \xrightarrow{\text{add } \langle \cdot, \cdot \rangle} (V, +, \cdot, \langle \cdot, \cdot \rangle) \quad \text{an inner product space.}$$

Note: If $\mathbb{K} = \mathbb{R}$, then conjugate symmetry is reduced to symmetry because if $x \in \mathbb{R}, \bar{x} = x$.

$$\langle u, v \rangle = \langle v, u \rangle \quad \text{for real inner product spaces.}$$

Examples of inner product spaces:

1. $\mathbb{R}^n$ with standard dot product:
$$\langle x, y \rangle = x \cdot y = x_1 y_1 + x_2 y_2 + \dots + x_n y_n$$

2. $\mathbb{R}^n$ with an alternative inner prod.
Take $c_1, c_2, \dots, c_n \in \mathbb{R} \quad c_i > 0, \ \forall i$
$$\langle x, y \rangle = c_1 x_1 y_1 + c_2 x_2 y_2 + \dots + c_n x_n y_n$$

3. $C_{[a, b]} = \text{Space of continuous real-valued functions}$

<!-- page 9 -->

3. $C_{[a,b]} = \text{Space of continuous real-valued functions on } [a,b]$.
$$\langle f, g \rangle = \int_a^b f(t) g(t) \, dt$$

- Norm (Length) induced by an inner product:
$$\text{For } v \in V : \|v\| = \sqrt{\langle v, v \rangle}$$

Example: for $\mathbb{R}^n$ take $\cdot$ :
$$\|x\| = \sqrt{x \cdot x} = \sqrt{x_1^2 + x_2^2 + \dots + x_n^2}$$

- Properties of a Norm:
For every $v \in V$, and $\alpha \in \mathbb{K} \ (= \mathbb{R} \text{ or } \mathbb{C})$
We have: $\|v\| \ge 0 \quad \text{and} \quad \|v\| = 0 \iff v = 0$ \quad (1)
and $\| \alpha v \| = |\alpha| \|v\|$. \quad (2)

Note:
(1) Follows from positive definiteness of $\langle \cdot, \cdot \rangle$

(2) $\|\alpha v\|^2 = \langle \alpha v, \alpha v \rangle = \alpha \langle v, \alpha v \rangle \quad \nearrow \quad \overline{z w} = \bar{z} \bar{w} \quad z, w \in \mathbb{C}$
$= \alpha \overline{\langle \alpha v, v \rangle} = \alpha \overline{\alpha \langle v, v \rangle} = \alpha \bar{\alpha} \langle v, v \rangle$
$= \alpha \bar{\alpha} \langle v, v \rangle = |\alpha|^2 \|v\|^2$ \hfill $\square$

- Perpendicularity: Define $u \perp v$ if $\langle u, v \rangle = 0$
$$\Rightarrow \langle v, u \rangle = \overline{\langle u, v \rangle} = \bar{0} = 0 \Rightarrow v \perp u$$

- Pythagorean Theorem:
If $u \perp v$, then $\|u + v\|^2 = \|u\|^2 + \|v\|^2$.

Proof: Since $u \perp v : \langle u, v \rangle = \langle v, u \rangle = 0$. Then
$$\|u + v\|^2 = \langle u + v, u + v \rangle = \langle u, u + v \rangle + \langle v, u + v \rangle$$
$$= \overline{\langle u + v, u \rangle} + \overline{\langle u + v, v \rangle}$$
$$= \overline{\langle u, u \rangle + \langle v, u \rangle} + \overline{\langle u, v \rangle + \langle v, v \rangle}$$

<!-- page 10 -->

$$= \langle u, u \rangle + \langle v, u \rangle + \langle u, v \rangle + \langle v, v \rangle$$
$$\phantom{= \langle u, u \rangle + }\overset{\rotatebox{90}{=}}{0} \phantom{+ \langle u, v \rangle + }\overset{\rotatebox{90}{=}}{0}$$
$$= \|u\|^2 + \|v\|^2$$

- Decomposing a vector along a direction.
  Given $v \neq 0_V$ the direction.
  How can we write $u \in V : \underline{u = c v + w}, \ w \perp v$
  Graphically
  ```
          u
    w   / |
      /   |
    /_____|_____v  "direction."
       cv
  ```
  Since we want $w = u - c v \perp v$
  $$0 = \langle u - c v, v \rangle = \langle u, v \rangle - c \langle v, v \rangle = \langle u, v \rangle - c \|v\|^2$$
  Hence $c = \frac{\langle u, v \rangle}{\|v\|^2}$
  Now we have Let $u, v \in V, \ v \neq 0_V$
  $$u = \frac{\langle u, v \rangle}{\|v\|^2} v + w \quad \text{where } w = u - \frac{\langle u, v \rangle}{\|v\|^2} v \quad \text{and } w \perp v$$

- Cauchy-Schwarz Inequality:
  For all $u, v \in V$.
  $$|\langle u, v \rangle| \le \|u\| \|v\| \quad \text{"=" iff } u, v \text{ are lin. dep.}$$
  $$\qquad\qquad\qquad\qquad\qquad u = k v \text{ for some } k \in \mathbb{K}$$

  Proof: $1^\circ$. If $v = 0_V$ Then $\checkmark$
  $2^\circ$. $v \neq 0$. Then $u = \frac{\langle u, v \rangle}{\|v\|^2} v + w, \quad w \perp v$

  By Pythagorean Them.
  ```
         /|  (top side: \frac{\langle u, v \rangle}{\|v\|^2} v)
        / |
     u /  | w
      /___|
  ```
  $$\|u\|^2 = \left\| \frac{\langle u, v \rangle}{\|v\|^2} v \right\|^2 + \|w\|^2$$
  $$= \frac{|\langle u, v \rangle|^2}{\|v\|^4 2} \|v\|^2 + \|w\|^2$$
  $$= \frac{|\langle u, v \rangle|^2}{\|v\|^2} + \underbrace{\|w\|^2}_{\ge 0} \ge \frac{|\langle u, v \rangle|^2}{\|v\|^2}$$
  $$\|v\|^2 \|u\|^2 \ge |\langle u, v \rangle|^2 \quad \text{then take square root.}$$
  Equality holds iff $\|w\| = 0 \iff w = 0_V$
  Then $u = \frac{\langle u, v \rangle}{\|v\|^2} v$ \hfill $\square$

<!-- page 11 -->

For $\mathbb{K} = \mathbb{R}$:

$$|\langle u, v \rangle| \le \|u\| \|v\| \iff \frac{|\langle u, v \rangle|}{\|u\| \|v\|} \le 1$$
$$\iff -1 \le \frac{\langle u, v \rangle}{\|u\| \|v\|} \le 1$$

Define $\theta \in [0, \pi]$ ($[0^\circ, 180^\circ]$) between $u$ & $v$ by
$$\cos\theta = \frac{\langle u, v \rangle}{\|u\| \|v\|}$$

Well defined.

```
  cos θ ^
        |
      1 +------,
        |       \
        |        \
  ------+---------+--------+-----> θ
        |         | θ      π
        |        π/2
     -1 +
```

In particular $u \perp v \iff \langle u, v \rangle = 0 \iff \cos\theta = 0$
$$\iff \theta = \frac{\pi}{2} \ (90^\circ)$$