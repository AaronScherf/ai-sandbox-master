---
source_pdf: Part I Linear Algebra 08.13 (1).pdf
folder_category: ta_notes
total_pages: 7
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [linear-algebra]
---

<!-- page 1 -->

Part I: Linear Algebra 08.13
Thursday, August 13, 2026 8:56 PM

- Cauchy-Schwarz Inequality:
$$|\langle u, v \rangle| \leq \|u\| \|v\| \quad \text{"=" iff } u, v \text{ lin. dep.}$$

- From C-S, we get the triangle inequality for $\|\cdot\|$:
$$\text{For all } u, v \in V$$
$$\|u+v\| \leq \|u\| + \|v\|. \quad (|a+b| \leq |a| + |b|, a, b \in \mathbb{R})$$

$\text{Proof.}$
$$\begin{aligned} \|u+v\|^2 &= \langle u+v, u+v \rangle \\ &= \langle u, u \rangle + \langle v, v \rangle + \langle u, v \rangle + \langle v, u \rangle \\ &= \|u\|^2 + \|v\|^2 + \langle u, v \rangle + \overline{\langle u, v \rangle} \\ &= \|u\|^2 + \|v\|^2 + 2\text{Re}\langle u, v \rangle \quad \left[\begin{aligned} z &= a+bi \\ \oplus \; \bar{z} &= a-bi \\ \hline z+\bar{z} &= 2a = 2\text{Re}z \end{aligned}\right] \\ &\leq \|u\|^2 + \|v\|^2 + 2|\langle u, v \rangle| \quad \left[\substack{\text{C-S : }\land \\ |z|=\sqrt{a^2+b^2} \geq |a| \geq \text{Re}z}\right] \\ \text{(C-S)} &\leq \|u\|^2 + \|v\|^2 + 2\|u\|\|v\| \\ &= (\|u\| + \|v\|)^2 \end{aligned}$$
$\text{Take sqrt on both sides.}$ $\square$

- Orthonormal Basis:
$$\text{A basis for } (V, +, \cdot, \langle \cdot, \cdot \rangle) \quad e_1, \dots, e_n \text{ is orthogonal}$$
$$\text{If } \langle e_i, e_j \rangle = 0 \quad \text{when } i \neq j$$

$$\text{They are orthonormal if}$$
$$\langle e_i, e_j \rangle = \begin{cases} 0 & \text{if } i \neq j \\ 1 & \text{if } i = j \end{cases} \iff \|e_i\| = 1 \quad \text{for all } i.$$

$\text{Example : Standard basis in } \mathbb{R}^n:$
$$e_1 = \begin{pmatrix} 1 \\ 0 \\ \vdots \\ 0 \end{pmatrix}, e_2 = \begin{pmatrix} 0 \\ 1 \\ \vdots \\ 0 \end{pmatrix}, \dots, e_n = \begin{pmatrix} 0 \\ 0 \\ \vdots \\ 1 \end{pmatrix}.$$

<!-- page 2 -->

$$\begin{matrix} |0/ & |0/ & |1/ \end{matrix}$$

$\text{Claim: Orthonormal } \Rightarrow \text{Lin. indep. (Easy to visualize)}$

- $\text{Finding an orthonormal basis from a given basis.}$
$(\text{Gram-Schmidt Procedure}):$

  $\mathbb{R}^2:$
  $$\begin{aligned} &e_1 := \frac{v_1}{\|v_1\|} \qquad w_2 = v_2 - \langle v_2, e_1 \rangle e_1 \qquad e_2 = \frac{w_2}{\|w_2\|} \end{aligned}$$

$\text{Generally. The process of } (v_1, \dots, v_n) \xrightarrow{\text{G-S}} (e_1, \dots, e_n) \text{ goes:}$

$$\text{Step 1: Define } w_1 = v_1, \quad e_1 = \frac{w_1}{\|w_1\|}$$

$$\text{Step 2: Define } w_2 = v_2 - \langle v_2, e_1 \rangle e_1, \quad e_2 = \frac{w_2}{\|w_2\|}$$

$$\text{Step 3: Define } w_3 = v_3 - \langle v_3, e_1 \rangle e_1 - \langle v_3, e_2 \rangle e_2, \quad e_3 = \frac{w_3}{\|w_3\|}$$

$$\vdots$$

$$\text{Step } k: \text{ Define } w_k = v_k - \sum_{j=1}^{k-1} \langle v_k, e_j \rangle e_j, \quad e_k = \frac{w_k}{\|w_k\|}$$

$$\vdots$$

$$\text{Step } n: \text{ Define } w_n = v_n - \sum_{j=1}^{n-1} \langle v_n, e_j \rangle e_j, \quad e_n = \frac{w_n}{\|w_n\|}.$$

$$\rightsquigarrow (e_1, \dots, e_n) \quad \text{orthonormal.}$$

- $\text{Orthonormal matrix.}$

  $\text{Take an orthonormal basis in } \mathbb{R}^n, (q_1, \dots, q_n), q_i \in \mathbb{R}^n.$

  $$Q = \begin{bmatrix} | & | & & | \\ q_1 & q_2 & \dots & q_n \\ | & | & & | \end{bmatrix}_{n \times n}$$

<!-- page 3 -->

$$Q = \begin{bmatrix} | & | & & | \\ q_1 & q_2 & \dots & q_n \\ | & | & & | \end{bmatrix}_{n \times n}$$

Look at $Q^T Q = \begin{bmatrix} \text{---} & q_1^T & \text{---} \\ \text{---} & q_2^T & \text{---} \\ & \vdots & \\ \text{---} & q_n^T & \text{---} \end{bmatrix} \begin{bmatrix} | & | & & | \\ q_1 & q_2 & \dots & q_n \\ | & | & & | \end{bmatrix}$

$$= \begin{bmatrix} 1 & 0 & 0 & \dots & 0 \\ 0 & 1 & 0 & \dots & 0 \\ \vdots & \vdots & \ddots & \vdots & \vdots \\ 0 & 0 & \dots & \dots & 1 \end{bmatrix} = I_n$$

Similarly you can check $Q Q^T = I_n$.
That is $Q^T = Q^{-1}$. This is called an orthonormal matrix.

- Recall diagonalization gives $A = P^{-1} D P$, $D$ diagonal.
  here $P$ invertible.

  ? : Can we find $Q$ orthonormal ($Q Q^T = Q^T Q = I_n$) such that
  $$A = Q^{-1} D Q = Q^T D Q \quad, D \text{ diagonal. ?}$$

  $\text{Ans: Spectral Theorem (for real symmetric matrices)}$

  $\text{For } A \in \mathbb{R}^{n \times n} \text{ symmetric } A^T = A$

  $\text{YES : } \exists Q \text{ orthonormal : } A = Q^{-1} D Q = Q^T D Q, D \text{ diagonal.}$

  $\text{Proof : Induction. (Long)}$

Spectral Theorem :

$$A \in \mathbb{R}^{n \times n}, A^T = A \xrightarrow{Q : Q^T Q = Q Q^T = I_n} \begin{aligned} A &= Q^{-1} D Q = Q^T D Q \quad, D \text{ diagonal} \\ \Leftrightarrow D &= Q A Q^{-1} = Q A Q^T = \text{diag}\{\lambda_1, \dots, \lambda_n\}. \end{aligned}$$

- What is $Q$?

<!-- page 4 -->

- What is $Q$?

  ANS: $Q = \begin{bmatrix} | & & | \\ q_1 & \cdots & q_n \\ | & & | \end{bmatrix}$ is the eigenvectors for $A$ that are orthonormal.

- Fact (Not hard to prove).
  For symmetric matrices: Eigenvectors associated with distinct eigenvalues are orthogonal.

  $$\begin{array}{c} \begin{matrix} \perp & \perp & \perp \end{matrix} \\ \begin{array}{|c|c|c|c|} \hline E_{\lambda_1} & E_{\lambda_2} & \cdots & E_{\lambda_s} \\ \text{G-S} & \text{G-S} & & \text{G-S} \\ \hline \end{array} \end{array} \overset{\lor}{\longrightarrow} Q$$

- Eigenvalues of real matrices might be complex.

  Example: $\mathbb{R}^{2 \times 2} : A = \begin{bmatrix} 0 & 1 \\ -1 & 0 \end{bmatrix} \quad \det(A - \lambda I_2) = \begin{vmatrix} -\lambda & -1 \\ 1 & -\lambda \end{vmatrix} = \lambda^2 + 1$

  This matrix has only imaginary eigenvalues $\pm i$

- Claim: Eigenvalues of symmetric matrices are all real numbers.

  Proof: We have $A \in \mathbb{R}^{n \times n}$, $A^T = A$

  Let $\lambda \in \mathbb{C}$ be an eigenvalue of $A$, and the associated eigenvector $z \in \mathbb{C}^n$. Write

  $$z = \begin{bmatrix} z_1 \\ z_2 \\ \vdots \\ z_n \end{bmatrix} = \begin{bmatrix} x_1 + i y_1 \\ x_2 + i y_2 \\ \vdots \\ x_n + i y_n \end{bmatrix} = \begin{bmatrix} x_1 \\ x_2 \\ \vdots \\ x_n \end{bmatrix} + i \begin{bmatrix} y_1 \\ y_2 \\ \vdots \\ y_n \end{bmatrix} = x + i y, \quad x, y \in \mathbb{R}^n$$

  Write $\lambda = a + i b, \quad a, b \in \mathbb{R}$

  Then: $Az = A(x + iy) \underset{\Delta}{=} (a + ib)(x + iy)$

  $$Ax + iAy = (ax - by) + i(bx + ay)$$

  $$\Rightarrow \begin{aligned} Ax = ax - by &\xrightarrow{y^T} y^T Ax = ay^T x - b y^T y = ax^T y - b \|y\|^2 \quad (*) \\ Au = bx + ay &\xrightarrow{x^T} x^T Au - bx^T x + ax^T u = b \|x\|^2 + ax^T u \quad (**) \end{aligned}$$

<!-- page 5 -->

$$\begin{aligned}
\Rightarrow \quad Ax = ax - by &\quad \Rightarrow \quad y^T Ax = ay^T x - b y^T y = ax^T y - b \|y\|^2 \quad (*) \\
Ay = bx + ay &\quad \xrightarrow{\times x^T} x^T Ay = b x^T x + a x^T y = b \|x\|^2 + a x^T y \quad (**)
\end{aligned}$$

Since $A$ real symmetric $y^T Ax = x^T Ay$

because $y^T Ax \in \mathbb{R} \quad (y^T Ax)^T = y^T Ax$. Write out $(y^T Ax)^T$

Now combine $(*)$ $(**)$ : $b (\|x\|^2 + \|y\|^2) = 0$

Since $z = x + iy$ is an eigenvector, $z \neq 0_{\mathbb{C}^n}$ then
$$\|x\|^2 + \|y\|^2 > 0$$

This means $b = 0_{\mathbb{R}} \quad \Rightarrow \quad \lambda = a + ib = a \in \mathbb{R}$

---

- Quadratic Forms over $\mathbb{R}$

  - Quadratic forms are generalization of $ax^2 \in \mathbb{R}$
  - A quadratic form is a function:
    $$q(x) = x^T Ax, \quad x \in \mathbb{R}^n, \quad A \text{ real symmetric.}$$
  Example: $q(x_1, x_2) = 2x_1^2 + 6x_1 x_2 + 4x_2^2$
  $$= (x_1, x_2) \underbrace{\begin{pmatrix} 2 & 3 \\ 3 & 4 \end{pmatrix}}_{A = A^T} \begin{pmatrix} x_1 \\ x_2 \end{pmatrix}$$

- Application of Spectral Theorem: Simplifying $x^T Ax$.
  - We want to eliminate the cross-terms $x_i x_j \ (i \neq j)$
  - Spectral Theorem says: $Q^T AQ = D = \text{diag}\{\lambda_1, \dots, \lambda_n\}$.
    Let $x = Qy$ then:
    $$q(x) = x^T AX = (Qy)^T A (Qy) = y^T \underbrace{Q^T AQ}_D y$$
    $$q(Qy) =: \tilde{q}(y) = y^T \begin{bmatrix} \lambda_1 & & \\ & \lambda_2 & \\ & & \ddots & \\ & & & \lambda_n \end{bmatrix} y = \lambda_1 y_1^2 + \lambda_2 y_2^2 + \dots + \lambda_n y_n^2$$
  - By using Spectral Theorem, a quadratic form can be reduced to just the square terms.

<!-- page 6 -->

- By using Spectral Theorem, a quadratic form can be reduced to just the square terms.

- Why is useful?
  1. If $\lambda_1 > 0, \lambda_2 > 0, \dots, \lambda_n > 0$. Then $\tilde{q}(y) > 0$ for all $y \neq 0_{\mathbb{R}^n}$
     $\Leftrightarrow q(x) > 0$ for all $x \neq 0_{\mathbb{R}^n}$ since $\begin{aligned} \forall y &\neq 0_{\mathbb{R}^n} \\ x &= Qy \neq 0_{\mathbb{R}^n} \end{aligned}$
     We call $q(x) = x^T Ax$ positive definite
     if $q(x) = x^T Ax > 0$ for all $x \neq 0_{\mathbb{R}^n}$.
     Write $A > 0$.
     $$A > 0 \Leftrightarrow \lambda_1, \dots, \lambda_n > 0$$

  2. If $\lambda_1 < 0, \dots, \lambda_n < 0 \Rightarrow \tilde{q}(y) < 0 \quad \forall y \neq 0_{\mathbb{R}^n}$.
     Negative definite: $A < 0$
     $$A < 0 \Leftrightarrow \lambda_1, \dots, \lambda_n < 0$$

  3. Semidefiniteness: If $q(x) \ge 0 \quad \forall x \in \mathbb{R}^n \Leftrightarrow \lambda_1, \dots, \lambda_n \ge 0$
     $A \text{ Positive semidefinite}$

     If $q(x) \le 0 \quad \forall x \in \mathbb{R}^n \Leftrightarrow \lambda_1, \dots, \lambda_n \le 0$
     $A \text{ Negative semidefinite}$.

  4. Indefinite: $\begin{aligned} \text{Some } x \in \mathbb{R}^n \ q(x) > 0 \\ \text{Some } x \in \mathbb{R}^n \ q(x) < 0 \end{aligned} \Rightarrow \begin{aligned} A \\ \text{Indefinite.} \end{aligned} \Leftrightarrow \begin{aligned} \text{Some } \lambda_i > 0 \\ \text{Some } \lambda_i < 0 \end{aligned}$.

Criteria for definiteness without knowing $\lambda_i$'s
(Principal Minor Criteria)

- $A = \begin{pmatrix} a_{11} & a_{12} & \dots & a_{1n} \\ a_{21} & a_{22} & \dots & a_{2n} \\ \vdots & \vdots & \ddots & \vdots \\ a_{n1} & a_{n2} & \dots & a_{nn} \end{pmatrix}_k^k \quad \begin{aligned} \Delta_1 &= a_{11} \\ \Delta_2 &= \begin{vmatrix} a_{11} & a_{12} \\ a_{21} & a_{22} \end{vmatrix} \\ &\vdots \\ \Delta_k &= \begin{vmatrix} a_{11} & \dots & a_{1k} \\ a_{21} & \dots & a_{2k} \\ \vdots & \ddots & \vdots \\ a_{k1} & \dots & a_{kk} \end{vmatrix} \\ &\vdots \\ \Delta_n &= \det(A) \end{aligned}$

<!-- page 7 -->

- $A > 0 \Leftrightarrow \Delta_1, \Delta_2, \dots, \Delta_n > 0$

- $A < 0 \Leftrightarrow \Delta_1 < 0, \Delta_2 > 0, \Delta_3 < 0 \dots$ with alternating sign.

- Way to remember this:
  $$D = \begin{bmatrix} \lambda_1 & & \\ & \lambda_2 & \\ & & \ddots & \\ & & & \lambda_n \end{bmatrix} \begin{aligned} &\cdot \text{If } \lambda_1 \dots \lambda_n > 0 \Rightarrow \Delta_k^D > 0. \\ &\cdot \text{If } \lambda_1 \dots \lambda_n < 0 \Rightarrow \Delta_k^D \text{ alternating sign.} \end{aligned}$$

- Remark: This Principal Minor Criteria only holds for strict definiteness.

?: Is it true that $A \ge 0 \Leftrightarrow \Delta_1, \Delta_2 \dots, \Delta_n \ge 0$

Ans: $\Rightarrow$ is true but $\Leftarrow$ fails.

$$A = \begin{pmatrix} 0 & 0 & 0 \\ 0 & -1 & 0 \\ 0 & 0 & -1 \end{pmatrix} \quad \Delta_1 = \Delta_2 = \Delta_3 = 0$$

$$x^T Ax = -x_2^2 - x_3^2 \quad \text{is NOT positive semidefinite.}$$

- Things for you to refresh:

  - $AB \neq BA$ usually.

  - $A^{-1}$ doesn't always exist.

  - Solving $Ax = b$.