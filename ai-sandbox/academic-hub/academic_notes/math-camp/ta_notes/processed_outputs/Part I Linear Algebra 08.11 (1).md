---
source_pdf: Part I Linear Algebra 08.11 (1).pdf
folder_category: ta_notes
total_pages: 13
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [linear-algebra]
---

<!-- page 1 -->

Part I: Linear Algebra 08.11

Once basis chosen:

$$\begin{CD}
V @>T>> W \\
@V{\text{Coordinate}}VV @VV{\text{Coordinate}}V \\
\begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix} @>A>> \begin{pmatrix} y_1 \\ \vdots \\ y_m \end{pmatrix} \\
\mathbb{K}^n @>>> \mathbb{K}^m
\end{CD}$$

$$\begin{aligned}
v &\longmapsto T(v) \\
\begin{pmatrix} x_1 \\ \vdots \\ x_n \end{pmatrix} &\stackrel{A}{\longmapsto} \begin{pmatrix} y_1 \\ \vdots \\ y_m \end{pmatrix}
\end{aligned}$$

---

- **Basis Extension Lemma**:

  $(V, +, \cdot)$ vec. space. and $v_1, \dots, v_k$ Lin. indep.
  
  Suppose $n = \dim V$ and $n > k$. ($n < \infty$)
  
  Then we can find $v_{k+1}, v_{k+2}, \dots, v_n \in V$ Lin. indep.
  
  and $v_1, \dots, v_k, v_{k+1}, \dots, v_n$ form a basis of $V$.

  *Proof.* is by an iterative argument.

  *Example*: $\mathbb{R}^3$:

  $$\begin{aligned}
  e_1 &= \begin{pmatrix} 1 \\ 0 \\ 0 \end{pmatrix} \\
  e_2 &= \begin{pmatrix} 0 \\ 1 \\ 0 \end{pmatrix} \\
  e_3 &= \begin{pmatrix} 0 \\ 0 \\ 1 \end{pmatrix}
  \end{aligned}$$

---

- **Invariant Subspace of a linear transformation**:

  $T \in \mathcal{L}(V)$ ($T \colon V \longrightarrow V$, linear)

  A subspace $W \le V$ is invariant if

  $$T(W) = \{T(w) : w \in W\} \subseteq W.$$

  $$\begin{CD}
  V @>T>> V
  \end{CD}$$

  Clearly $V$ is an invariant

<!-- page 2 -->

Clearly $V$ is an invariant subspace for any $T \in \mathcal{L}(V)$, and $\{0_V\}$ as well.

$$\begin{CD}
V @>T>> V
\end{CD}$$

- Two important invariant subspaces of $T \in \mathcal{L}(V)$
  - $\operatorname{Im} T = \{T(v) : v \in V\}$ $\leftarrow$ What's the output of $T$
  - $\ker T = \{v \in V : T(v) = 0_V\}$ $\leftarrow$ What's being lossed under $T$.
  
  $\text{\underline{ARE SUBSPACES}}$

  *Claim*: For any $T \in \mathcal{L}(V)$, $\operatorname{Im} T$ and $\ker T$ are invariant.

  *Proof*: Take $w \in \operatorname{Im} T \subseteq V$, apply $T$, $T(w) \in \operatorname{Im} T$ by defn.
  Take $u \in \ker T$, then $T(u) = 0_V$.
  Apply $T$: $T(T(u)) = T(0_V) = 0_V \implies T(u) \in \ker T$.

  $$T(0_V) = T(0_V + 0_V) = T(0_V) + T(0_V) \implies T(0_V) = 0_V.$$

  $$\tag*{$\square$}$$

The above definition of $\operatorname{Im} T$ and $\ker T$ goes also for linear maps $\mathcal{L}(V, W)$ but the concept of invariant subspaces only works for $\mathcal{L}(V)$.

$$\begin{CD}
V @>T>> W
\end{CD}$$

"$T(U) \subseteq U$" doesn't make sense since $T(U) \subseteq W \neq V$.

In this case, $\operatorname{Im} T \le W$ and $\ker T \le V$.

- **Rank, nullity and the rank-nullity Theorem**.

  - $\operatorname{Rank}(T) := \dim \operatorname{Im} T \leftarrow$ How many dimensions in $W$ is the output of $T$?
  - $\operatorname{nullity}(T) := \dim \ker T \leftarrow$ How many dimensions in $V$ is being mapped to $0_W$ by $T$?

  - *Claim*: (1) $T \in \mathcal{L}(V, W)$ is injective $\underset{\text{one-to-one}}{\iff} \ker T = \{0_V\}$

<!-- page 3 -->

- *Claim*: (1) $T \in \mathcal{L}(V, W)$ is injective $\underset{\text{one-to-one}}{\iff} \ker T = \{0_V\}$
  (2) $T \in \mathcal{L}(V, W)$ is surjective $\underset{\text{onto}}{\iff} \operatorname{Im} T = W$

  *Proof*: (2) is obvious.

  (1) $\implies$: Suppose $T$ injective and take $v \in \ker T$
  $$T(v) = 0_W = T(0_V)$$
  By injectivity, $v = 0_V$

  $\impliedby$: Suppose $\ker T = \{0_V\}$.
  If $T(u) = T(v)$, by linearity:
  $$T(u - v) = 0_W \implies u - v \in \ker T = \{0_V\}$$
  This means $u = v$.
  This proves $T$ is injective.
  $$\tag*{$\square$}$$

?: How are $\operatorname{Rank}(T) := \dim \operatorname{Im} T$ and $\operatorname{nullity}(T) := \dim \ker T$ related to each other?

*Ans*: **Rank-Nullity Theorem**:
Let $T \colon V \longrightarrow W$ linear. $(\dim V < \infty, \dim W < \infty)$
Then $\dim V = \dim \operatorname{Im} T + \dim \ker T$.

"The dimensions add up to the dim of the domain."

Equivalently: $\dim V = \operatorname{Rank}(T) + \operatorname{nullity}(T)$.

*Proof*: Let $u_1, \dots, u_k$ be a basis of $\ker T$ thus
$$\dim \ker T = \operatorname{nullity}(T) = k.$$
$$u_1, \dots, u_k \in \ker T \le V.$$
By Basis Extension we can find $v_1, \dots, v_r$ lin indep.
and $\underline{u_1, \dots, u_k, v_1, \dots, v_r}$ is a basis for $V$.

<!-- page 4 -->

and $\underline{u_1, \dots, u_k, v_1, \dots, v_r}$ is a basis for $V$.

So $\operatorname{dim} V = k + r$.

We want to show that $T(v_1), \dots, T(v_r)$ forms a basis for $\operatorname{Im} T$.

First: $T(v_1), \dots, T(v_r)$ span $\operatorname{Im} T$.

Take any $w \in \operatorname{Im} T$, by defn. $\exists v \in V : w = T(v)$.

Since $\underbrace{u_1, \dots, u_k}_{\in \ker T}, v_1, \dots, v_r$ is a basis for $V$
$$v = a_1 u_1 + \dots + a_k u_k + b_1 v_1 + \dots + b_r v_r \quad (*)$$

Apply $T$ to both sides of $(*)$

$$\begin{aligned}
w = T(v) &= T(a_1 u_1 + \dots + a_k u_k + b_1 v_1 + \dots + b_r v_r) \\
&= \underbrace{a_1 T(u_1) + \dots + a_k T(u_k)}_{0_W} + b_1 T(v_1) + \dots + b_r T(v_r) \\
&= \sum_{j=1}^r b_j T(v_j)
\end{aligned}$$

Thus $\operatorname{Im} T \subseteq \operatorname{Span}(T(v_1), \dots, T(v_r))$

$\supseteq$: This is obvious since $T$ is linear.

Therefore $\operatorname{Im} T = \operatorname{Span}(T(v_1), \dots, T(v_r))$.

Now. WTS. (= want to show) $T(v_1), \dots, T(v_r)$ Lin. indep.

Suppose $c_1 T(v_1) + \dots + c_r T(v_r) = 0_W$

By Linearity $0_W = T(c_1 v_1 + \dots + c_r v_r)$

This means $c_1 v_1 + \dots + c_r v_r \in \ker T$.

But recall that $u_1, \dots, u_k$ is a basis for $\ker T$

$$c_1 v_1 + \dots + c_r v_r = d_1 u_1 + \dots + d_k u_k.$$

$$\implies c_1 v_1 + \dots + c_r v_r - d_1 u_1 - \dots - d_k u_k = 0_V$$

Since $v_1, \dots, v_r, u_1, \dots, u_k$ is a basis $V \implies$ Lin. indep.

$$\underbrace{c_1 = \dots = c_r} = d_1 = \dots = d_k = 0_{\mathbb{K}}$$

This shows that $T(v_1), \dots, T(v_r)$ is lin. indep.

$$\text{Lin. indep} + \text{spans } \operatorname{Im} T \implies T(v_1), \dots, T(v_r) \text{ is basis for } \operatorname{Im} T$$

<!-- page 5 -->

$\operatorname{Rank}(T) = \dim \operatorname{Im} T = \# \text{basis elements} = r$.

$\implies \dim V = k + r = \dim \ker T + \dim \operatorname{Im} T$
$= \operatorname{nullity}(T) + \operatorname{Rank}(T)$.

$$\tag*{$\square$}$$

Plan:
1. Take basis for $\ker T$ in $V$
2. Extend it to a full basis of $V$
3. Show that $\{T(\text{added basis element})\}$ forms a basis of $\operatorname{Im} T$
4. Dimension counts follows.

Application:

Let $T \in \mathcal{L}(V, W)$ and $\dim V = \dim W$ ($\mathcal{L}(V)$ is a special case)

Then TFAE (the following are equivalent)

(1) $\ker T = \{0_V\}$
(2) $T$ injective.
(3) $T$ surjective.
(4) $T$ bijective.

If $\ker T = \{0_V\}$, then by R-N:
$\dim V = \dim \operatorname{Im} T + \underbrace{\dim \ker T}_{0} = \dim \operatorname{Im} T$
$\parallel$
$\dim W$. This means $\operatorname{Im} T = W$ because $\operatorname{Im} T \le W$
Then $T$ is surjective

Surjective $\implies \dim W = \dim \operatorname{Im} T$ plug into R-N.
$\implies \dim \ker T = 0 \implies \ker T = \{0_V\}$

- Rank of a matrix:
  - Take $A \in \mathbb{K}^{m \times n}$, then $A$ naturally gives a linear map
    $$\begin{aligned}
    T_A : \mathbb{K}^n &\longrightarrow \mathbb{K}^m \\
    x &\longmapsto Ax
    \end{aligned}$$
  - What is $Ax$? $\downarrow \quad ---- \quad \downarrow$

<!-- page 6 -->

- What is $Ax$? $\downarrow \quad ---- \quad \downarrow$
$$Ax = \begin{pmatrix} a_{11} & \cdots & a_{1n} \\ a_{21} & \cdots & a_{2n} \\ \vdots & & \vdots \\ a_{m1} & \cdots & a_{mn} \end{pmatrix} \begin{pmatrix} x_1 \\ x_2 \\ \vdots \\ x_n \end{pmatrix} = \begin{pmatrix} a_{11}x_1 + \dots + a_{1n}x_n \\ a_{21}x_1 + \dots + a_{2n}x_n \\ \vdots \\ a_{m1}x_1 + \dots + a_{mn}x_n \end{pmatrix}$$
$$= x_1 \begin{pmatrix} a_{11} \\ a_{21} \\ \vdots \\ a_{m1} \end{pmatrix} + x_2 \begin{pmatrix} a_{12} \\ a_{22} \\ \vdots \\ a_{m2} \end{pmatrix} + \dots + x_n \begin{pmatrix} a_{1n} \\ a_{2n} \\ \vdots \\ a_{mn} \end{pmatrix}$$

Then $\operatorname{Im} T_A = \{Ax : x \in \mathbb{K}^n\}$
$$= \left\{ x_1 \begin{pmatrix} a_{11} \\ \vdots \\ a_{m1} \end{pmatrix} + \dots + x_n \begin{pmatrix} a_{1n} \\ \vdots \\ a_{mn} \end{pmatrix} : x_1, \dots, x_n \in \mathbb{K} \right\}$$
$$= \operatorname{Span} \left( \begin{pmatrix} a_{11} \\ \vdots \\ a_{m1} \end{pmatrix}, \dots, \begin{pmatrix} a_{1n} \\ \vdots \\ a_{mn} \end{pmatrix} \right)$$
$$:= \operatorname{Col}(A)$$

Then we define.
$$\begin{aligned}
\operatorname{Rank}(A) = \dim \operatorname{Im} T_A &= \dim \operatorname{Col}(A) \\
&= \# \text{ of independent Columns.}
\end{aligned}$$

- Small note: $\dim \operatorname{Col}(A)$ is technically speaking the column rank of $A$.
  There is an analogous concept: row rank $\dim \operatorname{Row}(A)$ which is the dimension of the $\underbrace{\operatorname{Span} \text{ of the rows of } A}_{\mathbb{K}_n}$

Fact: (Trust me bro!)
$$\dim \operatorname{Col}(A) = \dim \operatorname{Row}(A)$$

<!-- page 7 -->

Fact: (Trust me bro!)
$$\dim \operatorname{Col}(A) = \dim \operatorname{Row}(A)$$
Take: $\mathbb{R}^{2 \times 3} : \begin{pmatrix} 1 & 2 & 3 \\ 1 & 0 & 4 \end{pmatrix}$ for example.

- Rank tells us how many lin indep. rows / columns there are in a matrix. Viewed as a linear map: how many indep. directions are being output.

  Example: $\mathcal{L}(\mathbb{R}^2)$

  ```
  y ^               ^
    |  e_2          |       Ae_2
    |               |      /
    +--->           +---->-- Ae_1
   /   e_1         /
  +------>        +--------> Ae_1
  ```
  $$A = \begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix} (e_1, e_2)$$
  $$\operatorname{rank}(A) = 2$$

  ```
  y ^               ^
    |  e_2          |     / Ae_1
    |               |    /
    +--->           +---/--->
   /   e_1         /   /
  +------>        +---/----> Ae_2
  ```
  $$A = \begin{pmatrix} 1 & -1 \\ 1 & -1 \end{pmatrix} (e_1, e_2)$$

- Change of Basis for a Linear map:

  Domain: $V$ Bases $\mathcal{E} = (e_1, \dots, e_n)$ and $\mathcal{E}' = (e_1', \dots, e_n')$

  Codomain: $W$ Bases $\mathcal{F} = (f_1, \dots, f_m)$ and $\mathcal{F}' = (f_1', \dots, f_m')$

  Change of Basis: $(e_1', \dots, e_n') = (e_1, \dots, e_n) P \quad (\text{in } V)$
  $(f_1', \dots, f_m') = (f_1, \dots, f_m) Q \quad (\text{in } W)$

  $P$ invertible $n \times n$ ; $Q$ invertible $m \times m$

<!-- page 8 -->

$P$ invertible $n \times n$ ; $Q$ invertible $m \times m$

Take $v \in V$: Coor. vector $[v]_\mathcal{E} = P [v]_{\mathcal{E}'} \leftarrow$
$\begin{aligned}
\rightarrow v = (e_1, \dots, e_n) [v]_\mathcal{E} &= (e_1', \dots, e_n') [v]_{\mathcal{E}'} \\
&= (e_1, \dots, e_n) P [v]_{\mathcal{E}'}.
\end{aligned}$

Similarly $[w]_\mathcal{F} = Q [w]_{\mathcal{F}'}$ for any $w \in W$.

Let $A$ be the matrix of $T$ from $\mathcal{E} \to \mathcal{F}$
$B$ "" "" "" "" from $\mathcal{E}' \to \mathcal{F}'$

Then: $B = Q^{-1} A P$.

To see this: for every $v \in V$.
$[T(v)]_\mathcal{F} = A [v]_\mathcal{E} = A P [v]_{\mathcal{E}'} \quad (*)$

On the other hand, do a change of basis for $T(v)$
$[T(v)]_\mathcal{F} = Q [T(v)]_{\mathcal{F}'} = Q B [v]_{\mathcal{E}'} \quad (**)$

Equate $(*)$ and $(**)$:
$$A P [v]_{\mathcal{E}'} = Q B [v]_{\mathcal{E}'}.$$

This holds for all vectors $[v]_{\mathcal{E}'}$ that is
all vectors in $\mathbb{K}^n$ then $A P = Q B$

As $Q$ is invertible: $\underset{m \times n}{B} = \underset{m \times m}{Q^{-1}} \underset{m \times n}{A} \underset{n \times n}{P}$.

<!-- page 9 -->

As $Q$ is invertible: $\underset{m \times n}{B} = \underset{m \times m}{Q^{-1}} \underset{m \times n}{A} \underset{n \times n}{P}$.

- When $B = Q^{-1}AP$ we call $A$ and $B$ are equivalent.
- Fact: Equivalent matrices have the same rank.
  And the rank is the rank of the linear map the matrix encodes.

Corollary: If $T \in \mathcal{L}(V)$ and $\mathcal{E} = (e_1, \dots, e_n)$, $\mathcal{E}' = (e_1', \dots, e_n')$,
and $(e_1', \dots, e_n') = (e_1, \dots, e_n)P$
The matrix of $T$ under $\mathcal{E}$ is $A$
" " of $T$ under $\mathcal{E}'$ is $B$

Then $B = P^{-1}AP$
$\begin{aligned}
[T(v)]_{\mathcal{E}} &= P [T(v)]_{\mathcal{E}'} \\
&= P B [v]_{\mathcal{E}'} \quad \| \\
[T(v)]_{\mathcal{E}} &= A [v]_{\mathcal{E}} = A P [v]_{\mathcal{E}'}
\end{aligned}$
$(e_1', \dots, e_n') = (e_1, \dots, e_n)P$
$\downarrow \text{coord.}$
$[v]_{\mathcal{E}} = P [v]_{\mathcal{E}'}$

When $B = P^{-1}AP$ we say that $A$ and $B$ are similar. Note for $\mathcal{L}(V)$ the matrix is square: Only square matrices of the same size can be tested whether they are Similar.

- $B = Q^{-1}AP$ (Equivalence) for $m \times n$ $A \& B$

<!-- page 10 -->

- $B = Q^{-1}AP$ (Equivalence) for $m \times n$ $A \& B$
- $B = P^{-1}AP$ (Similarity) for $n \times n$ $A \& B$

$\blacktriangleright$ Two matrices are equivalent iff they have the same rank. $\to$ under some given basis.

?: For a matrix $A$ (describing linear map $T: V \to W$)
Can we find alternative bases for $V$ and $W$.
such that $B = Q^{-1}AP$ is as simple as possible?

Ans: Yes! In fact:
$$\exists P \& Q \text{ invertible} : Q^{-1}AP = \begin{array}{c} r \\ m-r \end{array} \overset{\begin{array}{cc} r & n-r \end{array}}{\begin{bmatrix} I_r & 0 \\ 0 & 0 \end{bmatrix}_{m \times n}}$$

$$r = \operatorname{Rank}(A) = \operatorname{Rank}(T).$$

$$\text{Rank Normal Form}$$

??: For square matrices, $A$ and $B$ are similar iff $\underline{\hspace{3cm}}$.

"Ans": There is no simple answer.
We will see a case where for certain matrices $P^{-1}AP = \begin{bmatrix} \lambda_1 & & 0 \\ & \lambda_2 & \\ 0 & & \lambda_n \end{bmatrix}$ (Diagonalization).
In general, the conditions are complicated and it depends on the field $\mathbb{K}$.

Remark: If you are interested, search "Jordan Form" "Frobenius Form" of similar matrices.

<!-- page 11 -->

- Sum and Direct sum of subspaces.
  Take $V_1, \dots, V_k : V_i \le V$ the sum:
  $$V_1 + V_2 + \dots + V_k = \sum_{i=1}^k V_i = \{v_1 + v_2 + \dots + v_k : v_i \in V_i, \forall i=1\dots k\}$$
  If $v \in \sum_{i=1}^k V_i$, the $v = v_1 + v_2 + \dots + v_k$ for some $v_i \in V_i, \forall i$.
  If this representation is unique:
  $$\text{If } v \in \sum_{i=1}^k V_i \text{ then } \exists! \ v_1, \dots, v_k : v = v_1 + v_2 + \dots + v_k$$
  Then we call this sum a direct sum.
  Denote it as $V_1 \oplus V_2 \oplus \dots \oplus V_k = \bigoplus_{i=1}^k V_k$.

Example: $\mathbb{R}^3 = \operatorname{Span} \left\{ \begin{pmatrix} 1 \\ 0 \\ 0 \end{pmatrix}, \begin{pmatrix} 0 \\ 1 \\ 0 \end{pmatrix}, \begin{pmatrix} 0 \\ 0 \\ 1 \end{pmatrix} \right\} = \operatorname{Span} \{e_1, e_2, e_3\}$
For any $v = \mathbb{R}^3 = \begin{pmatrix} x_1 \\ x_2 \\ x_3 \end{pmatrix} =! \ x_1 e_1 + x_2 e_2 + x_3 e_3$
$\mathbb{R}^3 = \operatorname{Span}\{e_1\} \oplus \operatorname{Span}\{e_2\} \oplus \operatorname{Span}\{e_3\}$.

```
  ^ e3
  |
  +----> e2
 /
/ e1
```

But $\mathbb{R}^3 = \operatorname{Span}\{e_1, e_2\} + \operatorname{Span}\{e_2, e_3\}$
(Check this).

Claim: This sum is not direct.
Let's take $e_2 = \begin{pmatrix} 0 \\ 1 \\ 0 \end{pmatrix} = \underbrace{\frac{1}{2} \left[ \begin{pmatrix} 1 \\ 1 \\ 0 \end{pmatrix} + \begin{pmatrix} -1 \\ 1 \\ 0 \end{pmatrix} \right]}_{\operatorname{Span}\{e_1, e_2\}} + \underbrace{\begin{pmatrix} 0 \\ 0 \\ 0 \end{pmatrix}}_{\operatorname{Span}\{e_2, e_3\}}$
$= \underbrace{\begin{pmatrix} 0 \\ 0 \\ 0 \end{pmatrix}}_{\operatorname{Span}\{e_1, e_2\}} + \underbrace{\frac{1}{2} \left[ \begin{pmatrix} 0 \\ 1 \\ 1 \end{pmatrix} + \begin{pmatrix} 0 \\ 1 \\ -1 \end{pmatrix} \right]}_{\operatorname{Span}\{e_2, e_3\}}$

So the rep. of $e_2$ is NOT UNIQUE.
So the sum is not direct by def.

- Why sum?

<!-- page 12 -->

- Why sum?
  Sum of vector spaces forms a vec. space.
  (Check!)

  Union of vec. spaces is usually NOT a vec space.
  Counterexample in $\mathbb{R}^2$: $\operatorname{Span}\{e_1\} \cup \operatorname{Span}\{e_2\}$.
  NOT A Vec. Space!

```
    ^  / (Out of the union.)
    | /
    |/___>
```

- Determinants.
  ! : Determinants only exists for square matrices.

  . What is the determinant?
    Take $T \in \mathcal{L}(\mathbb{R}^n)$.
    $\det(T) = \text{signed volume } T([0,1]^n)$.

  . We've seen det. for $2 \times 2$ matrices.
    $\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc$.

    Consider: $A = \begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix} \quad \det(A) = 1$

```
   ^ e2         A      ^
 1 |----|     ---->  1 |----|
   |    |              |    |
   +---->              +---->
     e1                  Ae1
  O: Positive        O: Preserved
```

    $B = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix} \quad \det(A) = -1$

```
   ^ e2         B      ^ Ae1
 1 |----|     ---->  1 |----|
   |    |              |    |
   +---->              +---->
     e1                  Ae2
  O: Positive        O: Reversed
```

    $C = \begin{pmatrix} 1 & -1 \\ 1 & -1 \end{pmatrix} \quad \det(C) = 0$

<!-- page 13 -->

0.1 Positive
$$C = \begin{pmatrix} 1 & -1 \\ 1 & -1 \end{pmatrix}, \quad \det(C) = 0$$

```
    ^ e2            C             ^ Ae1
    |              --->          /
  --+----> e1                   /
    |                          v
                              Ae2
                                    Area = 0
```

Note that $C$ has lin. dep. columns.
$$1 \begin{pmatrix} 1 \\ 1 \end{pmatrix} + 1 \begin{pmatrix} -1 \\ -1 \end{pmatrix} = \begin{pmatrix} 0 \\ 0 \end{pmatrix}$$

- What's generally true is that if $A_{n \times n}$,
  $$\operatorname{rank}(A) = n \iff \det(A) \neq 0$$
  $$\iff A \text{ invertible.}$$

Take $e_i$ as the standard basis vector
$\to A e_i = i^{\text{th}}$ column of $A$ (Verify)
$A (e_1 \dots e_n) = A I_n = A$

If curious / unclear, watch 3blue1brown on Linear algebra.

---

Today :
- Rank, Nullity, R-N Thm.
- Change of basis for $T \in \mathcal{L}(V, W)$.
- Equivalence & Similarity
- Sum and direct sum
- Determinants

Coming Next : Diagonalization & Inner product spaces.