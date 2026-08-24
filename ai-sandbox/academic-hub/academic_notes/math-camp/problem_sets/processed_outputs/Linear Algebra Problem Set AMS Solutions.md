<!-- page 1 -->

# Linear Algebra: Guided Review and Exercises

**Purpose.** This sheet is meant to be a learning document. Some of the computational procedures below were not developed in detail in lecture. Each such topic therefore begins with a short introduction and a worked example, followed by exercises.

Unless otherwise stated, all vector spaces are finite-dimensional over $\mathbb{R}$ or $\mathbb{C}$.

## I. Solving Linear Systems by Elimination

**Mini-lecture.** A linear system is best viewed through its *augmented matrix*. The three elementary row operations are:
(i) interchange two rows;
(ii) multiply a row by a nonzero scalar;
(iii) add a multiple of one row to another row.

These operations do not change the solution set. The practical goal is echelon form: identify pivot variables, free variables, and any contradictory row of the form
$$(0 \cdots 0 \mid c), \quad c \neq 0.$$

A contradictory row means no solution. If every variable is a pivot variable, the solution is unique. If the system is consistent and at least one variable is free, there are infinitely many solutions.

**Worked example.** Consider
$$\begin{aligned}
x + y + z &= 6, \\
2x + y + z &= 8, \\
x + 2y + z &= 9.
\end{aligned}$$

Start from
$$\left(\begin{array}{ccc|c}
1 & 1 & 1 & 6 \\
2 & 1 & 1 & 8 \\
1 & 2 & 1 & 9
\end{array}\right).$$

Use $R_2 \leftarrow R_2 - 2R_1$ and $R_3 \leftarrow R_3 - R_1$:
$$\left(\begin{array}{ccc|c}
1 & 1 & 1 & 6 \\
0 & -1 & -1 & -4 \\
0 & 1 & 0 & 3
\end{array}\right).$$

Swap the last two rows and then add the new second row to the third:
$$\left(\begin{array}{ccc|c}
1 & 1 & 1 & 6 \\
0 & 1 & 0 & 3 \\
0 & 0 & -1 & -1
\end{array}\right).$$

Thus $z = 1$, $y = 3$, and $x = 2$. The point of the procedure is not the arithmetic itself: the pivot structure tells us whether a solution exists and how many degrees of freedom it has.

<!-- page 2 -->

**1. Practice.** For each system below:

(a) write the augmented matrix;

(b) row-reduce to echelon form;

(c) identify pivot and free variables;

(d) state whether the system has a unique solution, no solution, or infinitely many solutions;

(e) if there are infinitely many solutions, parameterize the complete solution set.

(i)
$$\begin{aligned}
2x + 2y &= 5, \\
x - 4y &= 0;
\end{aligned}$$

(ii)
$$\begin{aligned}
x - 3y + z &= 1, \\
x + y + 2z &= 14;
\end{aligned}$$

(iii)
$$\begin{aligned}
-x - y &= 1, \\
-3x - 3y &= 4.
\end{aligned}$$

For every consistent nonunique system, write the solution in the form
$$x = x_p + x_h,$$
where $x_p$ is one particular solution and $x_h$ ranges over the null space of the coefficient matrix.

---

### Handwritten Solutions:

i.
a)
$$\left[\begin{array}{cc|c}
2 & 2 & 5 \\
1 & -4 & 0
\end{array}\right]$$

b)
$$\xrightarrow{-\frac{1}{2}R_1} \left[\begin{array}{cc|c}
2 & 2 & 5 \\
0 & -5 & -2\frac{1}{2}
\end{array}\right]$$

c) $x, y$ pivots

d) unique, $y = 1/2$, $x = 2 \implies \vec{x} = \begin{bmatrix} 2 \\ 1/2 \end{bmatrix}$

e) N/A

<!-- page 3 -->

$$\begin{aligned}
x - 3y + z &= 1, \\
x + y + 2z &= 14;
\end{aligned}$$

ii. a, b)
$$\left[\begin{array}{ccc|c}
1 & -3 & 1 & 1 \\
1 & 1 & 2 & 14
\end{array}\right] \xrightarrow{-R_1} \left[\begin{array}{ccc|c}
1 & -3 & 1 & 1 \\
0 & 4 & 1 & 13
\end{array}\right]$$

c) $x, y$ pivot, $z$ free

d) infinite solutions

e) let $z = t$
$$\implies y = 3t \implies \vec{x} = \begin{bmatrix} 4t \\ 3t \\ t \end{bmatrix}$$
$$x = 4t$$

$$\text{All sol: } t \begin{bmatrix} 4 \\ 3 \\ 1 \end{bmatrix} \text{ for } t \in \mathbb{R}$$

$$\text{for } t=1, \vec{x}_1 = \begin{bmatrix} 4 \\ 3 \\ 1 \end{bmatrix}$$

---

$$\begin{aligned}
-x - y &= 1, \\
-3x - 3y &= 4.
\end{aligned}$$

iii. a, b)
$$\left[\begin{array}{cc|c}
-1 & -1 & 1 \\
-3 & -3 & 4
\end{array}\right] \xrightarrow{-3R_1} \left[\begin{array}{cc|c}
-1 & -1 & 1 \\
0 & 0 & 1
\end{array}\right]$$

c) 1 pivot, 1 free

d) no solution, inconsistent
$$\text{row } 0x + 0y = 1$$

e) N/A

<!-- page 4 -->

**2. A parameter and consistency.** Consider
$$\begin{aligned}
3x + 2y &= 10, \\
6x + 4y &= b.
\end{aligned} \qquad A = \begin{bmatrix} 3 & 2 \\ 6 & 4 \end{bmatrix}$$

(a) Row-reduce the augmented matrix without assigning a value to $b$ at the outset.

(b) For which values of $b$ is the system consistent?

(c) When it is consistent, parameterize all solutions.

(d) Compare the rank of the coefficient matrix with the rank of the augmented matrix in the consistent and inconsistent cases.

---

### Handwritten Solutions:

a)
$$A^* = \left[\begin{array}{cc|c}
3 & 2 & 10 \\
6 & 4 & b
\end{array}\right] \xrightarrow{-2R_1} \left[\begin{array}{cc|c}
3 & 2 & 10 \\
0 & 0 & b - 20
\end{array}\right] = R$$

b)
$$b = 20 \text{ only}$$

c) Let $b = 20 \implies \left[\begin{array}{cc|c}
3 & 2 & 10 \\
0 & 0 & 0
\end{array}\right]$
$$3x + 2y = 10$$
$$\text{Let } y = t \text{ be free variable,}$$
$$x = \frac{10 - 2t}{3} = \frac{10}{3} - \frac{2}{3}t$$

$$\vec{x} = \begin{bmatrix} x \\ y \end{bmatrix} = \begin{bmatrix} \frac{10}{3} - \frac{2}{3}t \\ 0 + 1t \end{bmatrix} = \begin{bmatrix} 10/3 \\ 0 \end{bmatrix} + t \begin{bmatrix} -2/3 \\ 1 \end{bmatrix}$$
$$\vec{x} = \vec{x}_0 + t \vec{v}$$

d)
$$\begin{aligned}
&\text{consistent } b = 20 & &\text{inconsistent } b \neq 20 \\
&\rho(A) = 1, \rho(A^*) = 1; & &\rho(A) = 1, \rho(A^*) = 2
\end{aligned}$$

<!-- page 5 -->

## II. Rank, Column Space, and Null Space

**Mini-lecture.** Row reduction reveals rank and the null space. If the reduced matrix has $r$ pivot columns, then the matrix has rank $r$. To find a basis of the *column space*, use the corresponding pivot columns of the *original* matrix. To find the null space, solve $Ax = 0$ using the reduced system and parameterize by the free variables.

**Worked example.** Let
$$A = \begin{pmatrix} 1 & 2 & 3 \\ 2 & 4 & 6 \\ 1 & 1 & 1 \end{pmatrix}.$$

Row reduction gives
$$A \sim \begin{pmatrix} 1 & 0 & -1 \\ 0 & 1 & 2 \\ 0 & 0 & 0 \end{pmatrix}.$$

Hence $\text{rank } A = 2$. The first two columns are pivot columns, so a basis for the column space is formed by the first two columns of the *original* matrix:
$$\left\{ \begin{pmatrix} 1 \\ 2 \\ 1 \end{pmatrix}, \begin{pmatrix} 2 \\ 4 \\ 1 \end{pmatrix} \right\}.$$

For $Ax = 0$, write $x_3 = t$. Then $x_1 = t$ and $x_2 = -2t$, so
$$\text{Ker } A = \text{span} \left\{ \begin{pmatrix} 1 \\ -2 \\ 1 \end{pmatrix} \right\}.$$

Notice the rank-nullity check: $2 + 1 = 3$, the number of columns of $A$.

<!-- page 6 -->

**3. Practice.** For each matrix below, use row reduction to find:

(a) its rank;

(b) a basis for its column space;

(c) a basis for its null space;

(d) the dimensions predicted by rank-nullity.

$$A = \begin{pmatrix} 1 & 2 & 3 \\ 3 & 1 & 2 \\ 2 & 3 & 1 \end{pmatrix}, \qquad B = \begin{pmatrix} 1 & 2 & -3 \\ -3 & 1 & 2 \\ 2 & -3 & 1 \end{pmatrix}.$$

Finally, explain how your calculations determine whether the columns of each matrix are linearly independent.

---

### Handwritten Solutions:

$$A.\text{ a)} \begin{pmatrix} 1 & 2 & 3 \\ 3 & 1 & 2 \\ 2 & 3 & 1 \end{pmatrix} \xrightarrow{-3R_1} \begin{pmatrix} 1 & 2 & 3 \\ 0 & -5 & -7 \\ 2 & 3 & 1 \end{pmatrix} \xrightarrow{-2R_1} \begin{pmatrix} 1 & 2 & 3 \\ 0 & -5 & -7 \\ 0 & -1 & -5 \end{pmatrix}$$

$$\xrightarrow{R_2 \leftrightarrow R_3} \begin{pmatrix} 1 & 2 & 3 \\ 0 & -1 & -5 \\ 0 & -5 & -7 \end{pmatrix} \xrightarrow{-5R_2} \begin{pmatrix} 1 & 2 & 3 \\ 0 & -1 & -5 \\ 0 & 0 & 18 \end{pmatrix}$$

b) all pivots, all original cols.

$$A_B = \left\{ \begin{bmatrix} 1 \\ 3 \\ 2 \end{bmatrix}, \begin{bmatrix} 2 \\ 1 \\ 3 \end{bmatrix}, \begin{bmatrix} 3 \\ 2 \\ 1 \end{bmatrix} \right\}$$

c) None $(\text{null space} = 0)$

d) $\dim = 3$

<!-- page 7 -->

B. a)
$$\begin{pmatrix} 1 & 2 & -3 \\ -3 & 1 & 2 \\ 2 & -3 & 1 \end{pmatrix} \xrightarrow{+3R_1} \begin{pmatrix} 1 & 2 & -3 \\ 0 & 7 & -7 \\ 2 & -3 & 1 \end{pmatrix}$$

$$\xrightarrow{-2R_1} \begin{pmatrix} 1 & 2 & -3 \\ 0 & 7 & -7 \\ 0 & -7 & 7 \end{pmatrix} \xrightarrow{+R_2} \xrightarrow{R_2/7} \begin{pmatrix} 1 & 2 & -3 \\ 0 & 1 & -1 \\ 0 & 0 & 0 \end{pmatrix}$$

b) 2 pivots, col 1 & 2

$$B_B = \left\{ \begin{bmatrix} 1 \\ -3 \\ 2 \end{bmatrix}, \begin{bmatrix} 2 \\ 1 \\ -3 \end{bmatrix} \right\}$$

c) $B\vec{x} = \vec{0}$

$$\begin{aligned}
x + 2y - 3z &= 0 \\
-3x + y + 2z &= 0 \\
2x - 3y + z &= 0
\end{aligned}$$

$$\text{let } z = t, \quad x = t, \quad y = t$$

$$\text{Ker } B = \text{span} \left\{ \begin{bmatrix} 1 \\ 1 \\ 1 \end{bmatrix} \right\}$$

d) $\dim B = 3 = \dim\text{Col } B + \dim\text{Ker } B$

<!-- page 8 -->

**4. Proof: rank-nullity without coordinates.** Suppose $T : \mathbb{F}^4 \to \mathbb{F}^2$ is linear and
$$\text{Ker } T = \{(x_1, x_2, x_3, x_4) \in \mathbb{F}^4 : x_1 = 5x_2, x_3 = 7x_4\}.$$

Without constructing a matrix for $T$, prove that $T$ is surjective.

---

### Handwritten Solutions:

$\text{Claim: } T \text{ is surjective iff}$
$$\text{Im } T = \mathbb{F}^2, \text{ the entire codomain}$$

$\text{By rank-nullity thm,}$
$$\dim \mathbb{F}^4 = \dim \text{Im } T + \dim \text{Ker } T$$

$\text{Since } \text{Ker } T = \{(5x_2, x_2, 7x_4, x_4)\},$
$T \text{ maps all } x_2 \text{ \& } x_4$
$\text{to the zero vector in } \mathbb{F}^2,$
$$\text{s.t. } \dim \text{Ker } T = 2$$

$$\dim \mathbb{F}^4 = 4 = \dim \text{Im } T + 2$$
$$\text{s.t. } \dim \text{Im } T = 2$$

$\text{since } \dim \mathbb{F}^2 = 2, \text{ Im } T \text{ is}$
$\text{the entire codomain, thus surj. } \square$

<!-- page 9 -->

**5. Proof: spanning and independence as properties of a map.** Let $v_1, \dots, v_m \in V$, and define
$$T : \mathbb{F}^m \to V, \qquad T(z_1, \dots, z_m) = z_1 v_1 + \dots + z_m v_m.$$

Prove directly from the definitions that

(a) $v_1, \dots, v_m$ spans $V$ if and only if $T$ is surjective;

(b) $v_1, \dots, v_m$ is linearly independent if and only if $T$ is injective.

---

### Handwritten Solutions:

a) $\implies$ if $\text{span}(v_1, \dots, v_m) = V$, then
$\forall v \in V, \quad \exists z_i \in \mathbb{F}, \quad v = z_1 v_1 + \dots + z_m v_m$

Since $T(z_1, \dots, z_m) = \sum_{i=1}^m z_i v_i$,

$\text{span}(v_i) = V = z_1 v_1 + \dots + z_m v_m = T(z_i)$

$T$ surj. iff $\text{Im } T = V$

$\text{Im } T = T(z_1, \dots, z_m) = V$
$\implies T$ surj.

$\impliedby$ if $T$ surj. $\text{Im } T = V$
s.t. $T(z_1, \dots, z_m) = V$

$z_1 v_1 + \dots + z_m v_m = v$ for all $v \in V$

$V = \text{Im } T = T(z_1, \dots, z_m) = \text{span}(v_1, \dots, v_m)$

thus $V = \text{span}(v_1, \dots, v_m)$

<!-- page 10 -->

b) ($\implies$) if $v_1, \dots, v_m$ lin ind.,
the only $z_i \in \mathbb{F}$ that solve
$$z_1 v_1 + \dots + z_m v_m = 0 \quad \text{are } z_1 = \dots = z_m = 0$$

therefore the only lin comb $\sum_{i=1}^m z_i v_i = 0$
is $\vec{z} = (0, \dots, 0) = \vec{0}_{\mathbb{F}^m}$

Since $T(z_1, \dots, z_m) = z_1 v_1 + \dots + z_m v_m$
the only $T(\vec{z}) = 0_V$ is $\vec{0}_{\mathbb{F}^m}$

$\implies \ker T = \vec{0}_{\mathbb{F}^m}$

$T$ is inj. iff $\ker T = \{\vec{0}_{\mathbb{F}^m}\}$

$\implies T$ is inj.

($\impliedby$) if $T$ inj, $\ker T = \{\vec{0}_{\mathbb{F}^m}\}$

s.t. $T(\vec{z}) = 0 = z_1 v_1 + \dots + z_m v_m$

only for $z_1 = \dots = z_m = 0$,

since $\vec{0}_{\mathbb{F}^m} = \begin{bmatrix} 0 \\ \vdots \\ 0 \end{bmatrix} = \begin{bmatrix} z_1 \\ \vdots \\ z_m \end{bmatrix}$,

thus the only $\vec{z}$ that solves $v_1, \dots, v_m$
$\sum_{i=1}^m z_i v_i = 0$ is $z_1 = \dots = z_m = 0$, thus lin ind. $\square$

<!-- page 11 -->

**6. Proof: rank one means an outer product.** Let $A$ be a nonzero $m \times n$ matrix. Prove that $\text{rank } A = 1$ if and only if there exist vectors $c \in \mathbb{F}^m$ and $d \in \mathbb{F}^n$ such that
$$A = cd^T.$$

Equivalently, prove that $A_{jk} = c_j d_k$ for all $j, k$.

---

### Handwritten Solutions:

$$\text{Unsure}$$

$(\implies)$ if $\text{rank } A = 1$,

either $m = n = 1$, s.t. $A^{1 \times 1} = a$
$$\text{then } \exists c, d \in \mathbb{F} \text{ s.t. } a = cd$$
$$\text{for all } a \in \mathbb{F} \text{ by}$$
$$\text{closure of a field}$$

or $m > 1, n > 1$,
$$\text{s.t } A^{m \times n} = \begin{bmatrix} a_{11} & \dots & a_{1n} \\ \vdots & \ddots & \vdots \\ a_{m1} & \dots & a_{mn} \end{bmatrix}$$

$$\text{since } \text{rank } A = 1, \text{ w/o loss gen,}$$
$$\dim \text{Col } A = 1 \text{ s.t.}$$
$$\text{Col } A = \text{span}\{a_1, \dots, a_n\}$$
$$\text{is } 1 \text{ dim subspace of } \mathbb{F}^m$$
$$\text{ie a line in } \mathbb{F}^m$$

$$\text{thus } \exists c \in \mathbb{F}^m : c \neq 0 \text{ s.t.}$$
$$\{c\} \text{ is basis for } \text{col } A$$
$$\implies \exists d_i \in \mathbb{F} \text{ s.t. } a_i = d_i c$$

<!-- page 12 -->

let $\vec{d} = \begin{bmatrix} d_1 \\ \vdots \\ d_n \end{bmatrix}$ where $d_i \in \mathbb{F}$

$\implies A = \begin{bmatrix} | & & | \\ a_1 & \dots & a_n \\ | & & | \end{bmatrix} = \begin{bmatrix} | & & | \\ d_1\vec{c} & \dots & d_n\vec{c} \\ | & & | \end{bmatrix}$

$\quad A = \begin{bmatrix} | \\ \vec{c} \\ | \end{bmatrix} \begin{bmatrix} d_1 & \dots & d_n \end{bmatrix} = \vec{c} \vec{d}^T$

thus $A_{jk} = (\vec{c}\vec{d}^T)_{jk} = c_j d_k$

$(\impliedby)$ if $A = \vec{c}\vec{d}^T$, $\vec{c} \neq 0, \vec{d} \neq 0$

since $A \neq 0$,

thus for at least one

$c_j \in \vec{c}$, $d_k \in \vec{d}^T$,

it must hold $c_j \neq 0, d_k \neq 0$

since $A_{jk} = c_j d_k \neq 0$

thus $\text{rank}(A) \geq 1$

<!-- page 13 -->

for any $x \in \mathbb{F}^n$,

$$Ax = \left(c d^T\right) x = c \left(d^T x\right) = \left(d^T x\right) c$$

since $d^T x$ is scalar in $\mathbb{F}$,

$$\text{im } A \subseteq \text{span } \{c\}$$

since $c \neq 0$,

$$\dim(\text{span } \{c\}) = 1,$$

thus $\dim(\text{im } A) \le \dim(\text{span } \{c\}) = 1$

s.t. $\dim(\text{im } A) \le 1$

since $A \neq 0$, $\dim(\text{im } A) > 0$

thus $\dim(\text{im } A) = 1$

$$\text{and } \text{rank } A = 1$$

$$\square$$

<!-- page 14 -->

## III. Linear Maps, Invertibility, and Direct Sums

**Checkpoint.** The next problems are deliberately proof-oriented. They connect the calculations above to the basis-free statements used in lecture.

**7.** Let $A = (A_{jk})$ be an $n \times n$ matrix. Prove that the following are equivalent:

(a) the homogeneous system $Ax = 0$ has only the zero solution;

(b) for every $b \in \mathbb{F}^n$, the system $Ax = b$ has a solution.

Explain why this is the matrix form of the equivalence between injectivity and surjectivity for a linear operator on a finite-dimensional vector space.

---

### Handwritten Solutions:

$\implies$ if a), $Ax = 0$ has only $\vec{x} = \begin{bmatrix} 0 \\ \vdots \\ 0 \end{bmatrix}$ solution

this for $A = \begin{bmatrix} | & & | \\ a_1 & \dots & a_n \\ | & & | \end{bmatrix}$,

$\{a_1, \dots, a_n\}$ is lin ind set

s.t. $x_1 \vec{a}_1 + x_2 \vec{a}_2 + \dots + x_n \vec{a}_n = 0$
only for $x_1 = \dots = x_n = 0$

thus $\text{col } A = \text{span } \{a_1, \dots, a_n\}$

$$\text{im } A = \mathbb{F}^n$$

$\implies \forall \vec{b} \in \mathbb{F}^n, \exists \vec{x} \in \mathbb{F}^n$ s.t.

$$x_1 \vec{a}_1 + \dots + x_n \vec{a}_n = \vec{b}$$

thus $Ax = b$ has solution for any $b \in \mathbb{F}^n$

<!-- page 15 -->

$\impliedby$ if $\forall b \in \mathbb{F}^n, \exists x \in \mathbb{F}^n$
s.t. $Ax = b$,

for a given $x$,
$Ax$ is unique
thus for $b = 0$, there
exists $x_0 \in \mathbb{F}^n$ s.t. $Ax = b = 0$

since $\text{im } A = \text{span } \{a_1, \dots, a_n\}$
$= \mathbb{F}^n$ by the fact
$Ax = b$ has solution
for all $b$,

$\{a_1, \dots, a_n\}$ lin. ind.

thus the sol. $x_0$ is unique
s.t. the only $x$ satisfying $Ax = 0$
is $x_0 = 0$ $\quad \square$

<!-- page 16 -->

Lin operator implies $T(V, V)$

$T$ inj. $\iff \ker T = \{0\}$ one to one

$T$ surj $\iff \text{im } T = V$ onto

if $A_T x = 0$ has only $0$ solution,
only $x$ mapped by $A_T$ to $0$
is $0$, such that $\ker A_T = \{0\}$

if $\forall b \in V, \exists x \in V \text{ s.t. } A_T x = b,$
then entire codomain $V = \text{span}\{b_1, \dots, b_n\}$
is mapped by $A_T x$
s.t. $\text{im } T = V \implies T \text{ surj.}$

<!-- page 17 -->

**8.** Let $P \in \mathcal{L}(V)$ satisfy $P^2 = P$. Prove that
$$V = \operatorname{Ker} P \oplus \operatorname{Im} P.$$

Then, for an arbitrary $v \in V$, find explicit formulas for its component in $\operatorname{Ker} P$ and its component in $\operatorname{Im} P$.

---

### Handwritten Notes & Marginalia:

$$\text{Couldn't solve}$$

$$P : V \to V \qquad P^2 = P \implies P x = P P x$$

$$\operatorname{Ker} P = \{ v \in V : P v = 0 \}$$

$$\operatorname{Im} P = \{ y = P x \quad \forall x \in V \}$$

---

### Printed Solution / Slide Content:

1. **Fixing the Image:** $P$ acts as the identity operator on its own range.
$$\exists u \in V \text{ s.t. } w = P u \implies P w = P(P u) = P^2 u = P u = w$$

2. **Complementary Annihilation:** The identity operator decomposes as $I = (I - P) + P$, where:
$$P(I - P) = P - P^2 = P - P = 0$$

This guarantees that for any $v \in V$, the vector $(I - P)v$ lies in $\operatorname{Ker} P$.

<!-- page 18 -->

**8.** Let $P \in \mathcal{L}(V)$ satisfy $P^2 = P$. Prove that
$$V = \operatorname{Ker} P \oplus \operatorname{Im} P.$$

Then, for an arbitrary $v \in V$, find explicit formulas for its component in $\operatorname{Ker} P$ and its component in $\operatorname{Im} P$.

---

### Handwritten Solutions:

$$\text{Couldn't solve}$$

$$P : V \to V \qquad P^2 = P \implies P x = P P x$$

$$\operatorname{Ker} P = \{ v \in V : P v = 0 \}$$

$$\operatorname{Im} P = \{ y = P x \quad \forall x \in V \}$$

$P$ acts like a projection, s.t.
$$\exists u \in V \text{ s.t. } P u = w$$
$$\implies P P u = P w$$
$$P u = P w$$
$$w = P w \implies \forall w \text{ in image of } P,$$
$$P \text{ acts as } I$$

Compl. Annihilation

$$\forall v \in V, (I - P) v = 0$$

<!-- page 19 -->

**3. Formal Proof:** $V = \text{Ker } P \oplus \text{Im } P$

To establish that $V$ is the internal direct sum of $\text{Ker } P$ and $\text{Im } P$, we must show:

1. $\text{Ker } P \cap \text{Im } P = \{0\}$
2. $V = \text{Ker } P + \text{Im } P$

---

#### Part 1: Trivial Intersection ($\text{Ker } P \cap \text{Im } P = \{0\}$)

Let $v \in \text{Ker } P \cap \text{Im } P$.

* Since $v \in \text{Ker } P$, $Pv = 0$.
* Since $v \in \text{Im } P$, there exists $u \in V$ such that $v = Pu$.

Applying $P$ to $v$:

$$v = Pu = P^2u = P(Pu) = Pv$$

Since $Pv = 0$, it follows directly that:

$$v = 0$$

Hence, $\text{Ker } P \cap \text{Im } P = \{0\}$.

---

### Handwritten Solutions:

$$\text{Claim: } V = \text{Ker } P \oplus \text{Im } P$$

$$\text{To prove:}$$
$$1)\quad \text{Ker } P \cap \text{Im } P = \{0\}$$
$$2)\quad V = \text{Ker } P + \text{Im } P$$

$$1)\quad \text{Let } v \in \text{Ker } P \cap \text{Im } P$$
$$\text{s.t. } v \in \text{Ker } P \implies Pv = 0 \qquad (*)$$

$$\text{Since } v \in \text{Im } P,$$
$$\exists u \in V \text{ s.t.}$$
$$v = Pu$$

$$\implies v = Pu = P^2 u = P(Pu) = Pv$$

$$\text{by } (*), \quad Pv = 0 \implies v = 0$$

$$\text{thus } \text{Ker } P \cap \text{Im } P = \{0\}$$

<!-- page 20 -->

Part 2: Spanning the Space ($V = \text{Ker } P + \text{Im } P$)

Let $v \in V$ be arbitrary. Decompose $v$ algebraically:

$$v = (v - Pv) + Pv$$

We verify the subspace membership for each term:

* **For $Pv$:** By definition, $Pv \in \text{Im } P$.
* **For $v - Pv$:** Applying the linear operator $P$:

$$P(v - Pv) = Pv - P^2 v = Pv - Pv = 0$$

Therefore, $(v - Pv) \in \text{Ker } P$.

Because every $v \in V$ can be expressed as the sum of an element in $\text{Ker } P$ and an element in $\text{Im } P$, we have $V = \text{Ker } P + \text{Im } P$.

Combining Parts 1 and 2 completes the proof:

$$V = \text{Ker } P \oplus \text{Im } P$$

---

### Handwritten Solutions:

2) $\forall v \in V$

$$v = v - Pv + Pv \qquad (*)$$
$$\text{since } Pv - Pv = 0$$

Split into $v - Pv$ and $Pv$

i) by def $Pv \in \text{Im } P$

ii) apply $P$ to $v - Pv$
$$\begin{aligned}
P(v - Pv) &= Pv - P^2 v \\
&= Pv - Pv = 0 \\
\implies P(v - Pv) &= 0 \\
&\text{and } (v - Pv) \in \text{Ker } P
\end{aligned}$$

Since $\forall v \in V$, $V$ is sum of elem
of $\text{Im } P$ & $\text{Ker } P$, $V = \text{Ker } P + \text{Im } P$

Thus by 1 & 2,

$$V = \text{Ker } P \oplus \text{Im } P$$

<!-- page 21 -->

# IV. Eigenvalues and How to Diagonalize a Matrix

**Mini-lecture.** For a square matrix $A$, an eigenvalue $\lambda$ is a scalar for which
$$(A - \lambda I)v = 0$$

has a nonzero solution. For a $2 \times 2$ matrix, the computation can be organized by the characteristic equation
$$\det(A - \lambda I) = 0, \qquad \det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc.$$

Once $\lambda$ is known, find its eigenvectors by row-reducing $A - \lambda I$. If an $n \times n$ matrix has $n$ linearly independent eigenvectors $v_1, \dots, v_n$, place them in the columns of
$$X = \begin{pmatrix} v_1 & \cdots & v_n \end{pmatrix}$$

and put the corresponding eigenvalues on the diagonal of $D$. Then
$$AX = XD, \qquad \text{hence} \qquad A = XDX^{-1}.$$

This is the computational meaning of diagonalization.

**Worked example.** Let
$$A = \begin{pmatrix} 4 & 1 \\ 2 & 3 \end{pmatrix}.$$

The characteristic equation is
$$\det \begin{pmatrix} 4 - \lambda & 1 \\ 2 & 3 - \lambda \end{pmatrix} = (4 - \lambda)(3 - \lambda) - 2 = (\lambda - 5)(\lambda - 2) = 0.$$

Thus the eigenvalues are $5$ and $2$.

For $\lambda = 5$,
$$(A - 5I)v = 0 \implies v \in \text{span}\{(1, 1)^{\text{T}}\}.$$

For $\lambda = 2$,
$$(A - 2I)v = 0 \implies v \in \text{span}\{(1, -2)^{\text{T}}\}.$$

Choose
$$X = \begin{pmatrix} 1 & 1 \\ 1 & -2 \end{pmatrix}, \qquad D = \begin{pmatrix} 5 & 0 \\ 0 & 2 \end{pmatrix}.$$

The columns of $X$ are independent, so $X$ is invertible, and $AX = XD$. Therefore
$$A = XDX^{-1}.$$

This is the pattern to imitate in the next computational problems.

<!-- page 22 -->

**9. First eigenvalue calculation.** Define $T \in \mathcal{L}(\mathbb{F}^2)$ by
$$T(w, z) = (z, w).$$

(a) Write the matrix of $T$ in the standard basis.

(b) Find all eigenvalues.

(c) For each eigenvalue, solve the corresponding homogeneous system to find the eigenspace.

(d) Choose an eigenbasis and write the diagonal matrix of $T$ in that basis.

---

### Handwritten Solutions:

a) swaps $v_1$ & $v_2$ of $\vec{v}$,
$$M_T = A = \begin{bmatrix} 0 & 1 \\ 1 & 0 \end{bmatrix} \implies \begin{bmatrix} 0 & 1 \\ 1 & 0 \end{bmatrix} \begin{bmatrix} w \\ z \end{bmatrix} = \begin{bmatrix} z \\ w \end{bmatrix}$$

b) $|A - \lambda I| = 0 \implies \left| \begin{bmatrix} 0 & 1 \\ 1 & 0 \end{bmatrix} - \begin{bmatrix} \lambda & 0 \\ 0 & \lambda \end{bmatrix} \right| = 0$
$$\left| \begin{bmatrix} -\lambda & 1 \\ 1 & -\lambda \end{bmatrix} \right| = 0$$
$$\lambda^2 - 1 = 0 \implies (\lambda + 1)(\lambda - 1) = 0$$
$$\lambda_1 = 1, \quad \lambda_2 = -1$$

c) 1) $(A - \lambda_1 I)x = 0$
$$\begin{bmatrix} -1 & 1 \\ 1 & -1 \end{bmatrix} \begin{bmatrix} x_1 \\ x_2 \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix} \qquad \begin{aligned} -x_1 + x_2 &= 0 \\ x_1 - x_2 &= 0 \end{aligned}$$
$$x_1 = x_2$$
$$V_1 = \text{span}\{[1, 1]^T\}$$

2) $(A - \lambda_2 I)x = 0$
$$\begin{bmatrix} 1 & 1 \\ 1 & 1 \end{bmatrix} \begin{bmatrix} x_1 \\ x_2 \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix} \qquad \begin{aligned} x_1 + x_2 &= 0 \\ x_1 + x_2 &= 0 \end{aligned}$$
$$x_1 = -x_2$$
$$V_2 = \text{span}\{[1, -1]^T\}$$

<!-- page 23 -->

d) Choose $X = \begin{bmatrix} 1 & 1 \\ 1 & -1 \end{bmatrix}$
$\begin{aligned} \det X &= -1 - 1 = -2 \\ &\neq 0 \end{aligned}$
$X$ is invert.

$D = \begin{bmatrix} 1 & 0 \\ 0 & -1 \end{bmatrix}$

$$AX = XD$$

$$\begin{bmatrix} 0 & 1 \\ 1 & 0 \end{bmatrix} \begin{bmatrix} 1 & 1 \\ 1 & -1 \end{bmatrix} = \begin{bmatrix} 1 & 1 \\ 1 & -1 \end{bmatrix} \begin{bmatrix} 1 & 0 \\ 0 & -1 \end{bmatrix}$$

$$\begin{bmatrix} 1 & -1 \\ 1 & 1 \end{bmatrix} = \begin{bmatrix} 1 & -1 \\ 1 & 1 \end{bmatrix}$$

$$\text{thus } D = X^{-1} A X$$

$$\text{w/} \quad X^{-1} = -\frac{1}{2} \begin{bmatrix} -1 & -1 \\ -1 & 1 \end{bmatrix}$$

$$= \frac{1}{2} \begin{bmatrix} 1 & 1 \\ 1 & -1 \end{bmatrix}$$

<!-- page 24 -->

**10. A matrix that does not have enough eigenvectors.** Define $T \in \mathcal{L}(\mathbb{F}^3)$ by
$$T(z_1, z_2, z_3) = (2z_2, 0, 5z_3).$$

(a) Write the standard matrix $A$ of $T$.

(b) Find all eigenvalues and their eigenspaces.

(c) Count the number of linearly independent eigenvectors that can be obtained.

(d) Decide whether $A$ can be diagonalized, and explain the answer using your calculation rather than quoting a theorem without verification.

---

### Handwritten Solutions:

a)
$$\underset{A}{\begin{bmatrix} 0 & 2 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 5 \end{bmatrix}} \underset{\vec{z}}{\begin{bmatrix} z_1 \\ z_2 \\ z_3 \end{bmatrix}} = \underset{\vec{z}'}{\begin{bmatrix} 2z_2 \\ 0 \\ 5z_3 \end{bmatrix}}$$

b) $\det(A - \lambda I) = 0$
$$\begin{vmatrix} -\lambda & 2 & 0 \\ 0 & -\lambda & 0 \\ 0 & 0 & 5-\lambda \end{vmatrix} = 0$$

$$-\lambda \begin{vmatrix} -\lambda & 0 \\ 0 & 5-\lambda \end{vmatrix} - 2 \begin{vmatrix} 0 & 0 \\ 0 & 5-\lambda \end{vmatrix} + 0 \begin{vmatrix} 0 & -\lambda \\ 0 & 0 \end{vmatrix} = 5\lambda^2 - \lambda^3 = 0$$

$$-\lambda(-\lambda(5-\lambda)) = 0 \implies \lambda^2(5-\lambda) = 0$$
$$-\lambda(\lambda^2 - 5\lambda) = 0 \implies \lambda_1 = 5, \quad \lambda_2 = 0, \quad \lambda_3 = 0$$
$$5\lambda^2 - \lambda^3 = 0$$

c) multiplicity of $2$ for $\lambda_2 = \lambda_3 = 0$
so only $2$ lin ind ev

d) $(A - \lambda I)v = 0$

$$\begin{bmatrix} -5 & 2 & 0 \\ 0 & -5 & 0 \\ 0 & 0 & 0 \end{bmatrix} v = 0$$
$$-5v_1 + 2v_2 = 0 \quad -5v_2 = 0 \implies v_2 = 0 \implies v_1 = 0 \implies v_3 \text{ free}$$

$$\begin{bmatrix} 0 & 2 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 5 \end{bmatrix} v = 0$$
$$\begin{aligned} 2v_2 &= 0 \\ 5v_3 &= 0 \\ v_1 &\text{ free} \end{aligned}$$

$$\begin{bmatrix} 0 \\ 0 \\ v_3 \end{bmatrix}, \qquad \begin{bmatrix} v_1 \\ 0 \\ 0 \end{bmatrix}$$

$$\text{multiplicity of } v_2, v_3 \implies \text{X not lin ind}$$
$$\text{X non-inv, } A \text{ not diag.}$$

<!-- page 25 -->

**11. Diagonalization and powers.** Let
$$A = \begin{pmatrix} 1 & 2 \\ 0 & 3 \end{pmatrix}.$$

(a) Find the eigenvalues of $A$.

(b) Find one eigenvector for each eigenvalue.

(c) Form the eigenvector matrix $X$ and the diagonal matrix $D$.

(d) Verify directly that $AX = XD$, and hence that $A = XDX^{-1}$.

(e) Use
$$A^k = XD^k X^{-1}$$
to derive a closed-form expression for $A^k$.

---

### Handwritten Solutions:

a)
$$\det \begin{pmatrix} 1-\lambda & 2 \\ 0 & 3-\lambda \end{pmatrix} = 0$$

$$(1-\lambda)(3-\lambda) - (2)(0) = 0$$

$$3 - 3\lambda - \lambda + \lambda^2 = 0$$

$$\lambda^2 - 4\lambda + 3 = 0$$

$$(\lambda-1)(\lambda-3) = 0$$

$$\lambda_1 = 1 \qquad \lambda_2 = 3$$

b)
$$\lambda_1) \begin{pmatrix} 1-1 & 2 \\ 0 & 3-1 \end{pmatrix} v = 0$$

$$\begin{pmatrix} 0 & 2 \\ 0 & 2 \end{pmatrix} v = 0$$

$$\begin{aligned} 2v_2 &= 0 \\ 2v_2 &= 0 \end{aligned} \qquad \begin{aligned} &v_1 \text{ free} \\ &v_2 = 0 \end{aligned} \implies X_1 = \begin{bmatrix} v_1 \\ 0 \end{bmatrix} \implies \begin{bmatrix} 1 \\ 0 \end{bmatrix}$$

$$\lambda_2) \begin{pmatrix} 1-3 & 2 \\ 0 & 3-3 \end{pmatrix} v = 0$$

$$\begin{pmatrix} -2 & 2 \\ 0 & 0 \end{pmatrix} v = 0$$

$$-2v_1 + 2v_2 = 0$$

$$v_1 = v_2 \implies X_2 = \begin{bmatrix} v_1 \\ v_1 \end{bmatrix} \implies \begin{bmatrix} 1 \\ 1 \end{bmatrix}$$

<!-- page 26 -->

c)
$$X = \begin{bmatrix} 1 & 1 \\ 0 & 1 \end{bmatrix} \qquad D = \begin{bmatrix} 1 & 0 \\ 0 & 3 \end{bmatrix}$$

d) $AX = XD$

$$\begin{bmatrix} 1 & 2 \\ 0 & 3 \end{bmatrix} \begin{bmatrix} 1 & 1 \\ 0 & 1 \end{bmatrix} = \begin{bmatrix} 1 & 1 \\ 0 & 1 \end{bmatrix} \begin{bmatrix} 1 & 0 \\ 0 & 3 \end{bmatrix}$$

$$\begin{bmatrix} 1 & 3 \\ 0 & 3 \end{bmatrix} = \begin{bmatrix} 1 & 3 \\ 0 & 3 \end{bmatrix}$$

$$\det X = 1, \quad X^{-1} \text{ exists}$$

e)
$$A^k = X D^k X^{-1} \qquad X^{-1} = \frac{1}{1} \begin{bmatrix} 1 & -1 \\ 0 & 1 \end{bmatrix}$$

$$X X^{-1} = \begin{bmatrix} 1 & 1 \\ 0 & 1 \end{bmatrix} \begin{bmatrix} 1 & -1 \\ 0 & 1 \end{bmatrix} = \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$$

$$A^k = \begin{bmatrix} 1 & 1 \\ 0 & 1 \end{bmatrix} \begin{bmatrix} 1^k & 0 \\ 0 & 3^k \end{bmatrix} \begin{bmatrix} 1 & -1 \\ 0 & 1 \end{bmatrix} = \begin{bmatrix} 1^k & 3^k \\ 0 & 3^k \end{bmatrix} \begin{bmatrix} 1 & -1 \\ 0 & 1 \end{bmatrix}$$

$$-1^k + 3^k$$

$$\begin{bmatrix} 1^k & 3^k - 1^k \\ 0 & 3^k \end{bmatrix} = A^k$$

<!-- page 27 -->

**12. Proof: similarity preserves eigenvalues.** Let $T \in \mathcal{L}(V)$ and let $S \in \mathcal{L}(V)$ be invertible.

(a) Prove that $T$ and $S^{-1}TS$ have the same eigenvalues.

(b) If $v$ is an eigenvector of $T$ with eigenvalue $\lambda$, identify an eigenvector of $S^{-1}TS$ with the same eigenvalue.

Explain why changing basis changes the matrix representing a linear operator but not its eigenvalues.

---

### Handwritten Solutions:

a) Let $S^{-1}TS = B$

$\exists v_T, v_B \in V$ eigenvectors w/ $v_T \neq 0, v_B \neq 0$,

s.t. $Tv_T = \lambda_T v_T$ & $B v_B = \lambda_B v_B$

Since $S$ invertible, $S$ surj. & inj.

s.t. $Su = v_T$ for some $u \in V$ (surj)

$\implies u = S^{-1} v_T$

Since $v_T \neq 0$, $u = S^{-1} v_T \neq 0$ (inj.)

Apply $S^{-1}TS$ to $u$:

$$\begin{aligned}
S^{-1}TS u &= S^{-1} T (Su) = S^{-1} T v_T \\
&= S^{-1} \lambda_T v_T = \lambda_T S^{-1} v_T = \lambda_T u \\
\implies S^{-1}TS u &= \lambda_T u \\
Bu &= \lambda_T u \implies \lambda_T \text{ is eigenvalue for } B = S^{-1}TS
\end{aligned}$$

<!-- page 28 -->

Direction 1: If $\lambda$ is an eigenvalue of $T$, then $\lambda$ is an eigenvalue of $S^{-1}TS$

1. Let $\lambda$ be an eigenvalue of $T$. By definition, there exists a non-zero vector $v \in V$ ($v \neq 0$) such that:

$$Tv = \lambda v$$

2. Since $S$ is invertible, $S$ is surjective, so there exists a vector $u \in V$ such that $Su = v$ (or equivalently, define $u = S^{-1}v$).

3. Because $S$ is injective and $v \neq 0$, it follows that:

$$u = S^{-1}v \neq 0$$

4. Apply the operator $S^{-1}TS$ to the vector $u$:

$$(S^{-1}TS)u = S^{-1}T(Su) = S^{-1}(Tv)$$

5. Substitute $Tv = \lambda v$:

$$S^{-1}(Tv) = S^{-1}(\lambda v) = \lambda(S^{-1}v) = \lambda u$$

6. Therefore, $(S^{-1}TS)u = \lambda u$ with $u \neq 0$, proving $\lambda$ is an eigenvalue of $S^{-1}TS$ with corresponding eigenvector $u = S^{-1}v$.

<!-- page 29 -->

Direction 2: If $\lambda$ is an eigenvalue of $S^{-1}TS$, then $\lambda$ is an eigenvalue of $T$

* Let $(S^{-1}TS)w = \lambda w$ with $w \neq 0$.
* Left-multiply by $S$:

$$S(S^{-1}TS)w = S(\lambda w) \implies T(Sw) = \lambda(Sw)$$

* Setting $z = Sw$, since $S$ is invertible and $w \neq 0$, $z \neq 0$.
* Hence $Tz = \lambda z$ with $z \neq 0$, proving $\lambda$ is an eigenvalue of $T$.

$$\operatorname{spec}(T) = \operatorname{spec}(S^{-1}TS)$$

---

### Handwritten Solutions:

$$\text{For } \lambda_B, \quad B v_B = \lambda_B v_B$$

$$S^{-1} T S v_B = \lambda_B v_B \quad \text{for } v_B \neq 0$$

$$\text{left multiply by } S:$$

$$S(S^{-1} T S) v_B = S(\lambda_B v_B) \qquad \text{let } S v_B = z$$

$$T S v_B = \lambda_B S v_B \implies T z = \lambda_B z,$$
$$\text{thus } \lambda_B \text{ is eigenvalue}$$
$$\text{of } T$$

$$\text{Since } \lambda_B \text{ is ev of } T \text{ \& } \lambda_T \text{ is ev of } B,$$

$$\text{both have same evs}$$

<!-- page 30 -->

(b) If $v$ is an eigenvector of $T$ with eigenvalue $\lambda$, identify an eigenvector of $S^{-1}TS$ with the same eigenvalue.

---

### Handwritten Solutions:

$$\text{for } V_T \text{ eigenvector of } T \text{ w/ } \lambda_T$$

$$T v_T = \lambda_T v_T$$

$$\text{find } v_B \text{ for } S^{-1}TS = B \text{ s.t.}$$

$$B v_B = \lambda_T v_B$$

$$\text{by a) all } \lambda_T \text{ are eigenvalues}$$
$$\text{of } B \text{ s.t. } \exists v_B \text{ associated}$$
$$\text{s.t. } B v_B = \lambda_T v_B \text{ w/ } \lambda_T$$

$$\text{thus } v_B \text{ shares } \lambda_T$$
$$\text{w/ } v_T$$

---

Explain why changing basis changes the matrix representing a linear operator but not its eigenvalues.

Matrix composed of vectors w/ coord.
in given basis, changing basis
adjusts coord but maintains
inherent position vectors,
so degree of scaling in the
principal directions is invariant

<!-- page 31 -->

A linear operator $T : V \to V$ is a coordinate-free geometric mapping on a vector space $V$. A matrix representation of $T$ depends explicitly on the choice of basis used to parametrize $V$, whereas the eigenvalues of $T$ are intrinsic algebraic and geometric properties of the operator itself.

### 1. Effect of a Change of Basis on the Matrix Representation

Let $V$ be an $n$-dimensional vector space over a field $\mathbb{F}$, and let $\mathscr{B} = \{v_1, \dots, v_n\}$ and $\mathscr{B}' = \{v'_1, \dots, v'_n\}$ be two distinct ordered bases for $V$.

* The matrix representation of $T$ with respect to $\mathscr{B}$, denoted $[T]_\mathscr{B} = A \in \mathbb{F}^{n \times n}$, is defined such that for any vector $x \in V$:

$$[T(x)]_\mathscr{B} = A[x]_\mathscr{B}$$

where the $j$-th column of $A$ contains the coordinates of $T(v_j)$ relative to $\mathscr{B}$.

* Let $P = [I]_{\mathscr{B}}^{\mathscr{B}'} \in \operatorname{GL}_n(\mathbb{F})$ be the invertible change-of-basis matrix converting $\mathscr{B}'$-coordinates to $\mathscr{B}$-coordinates:

$$[x]_\mathscr{B} = P[x]_{\mathscr{B}'}$$

* Expressing the action of $T$ in the $\mathscr{B}'$ basis yields:

$$[T(x)]_{\mathscr{B}'} = P^{-1}[T(x)]_\mathscr{B} = P^{-1}A[x]_\mathscr{B} = P^{-1}AP[x]_{\mathscr{B}'}$$

* Consequently, the matrix representation with respect to $\mathscr{B}'$ is:

$$B = [T]_{\mathscr{B}'} = P^{-1}AP$$

Because $P \neq I$ in general, $B \neq A$. A change of basis modifies the matrix representation via a similarity transformation.

<!-- page 32 -->

• **Coordinate-Free Geometric Characterization:**
A scalar $\lambda \in \mathbb{F}$ is an eigenvalue of $T$ if and only if there exists a non-zero vector $v \in V$ such that:

$$(T - \lambda I)v = 0$$

This definition relies solely on the action of $T$ on the underlying vector space $V$. Since vectors and linear operators exist independently of coordinate frames, the existence of such a scalar $\lambda$ and invariant subspace $\operatorname{ker}(T - \lambda I)$ does not depend on the choice of basis.

• **Invariance of the Characteristic Polynomial:**
Let $A = [T]_\mathscr{B}$ and $B = P^{-1}AP = [T]_{\mathscr{B}'}$. The characteristic polynomial $p_B(\lambda)$ satisfies:

$$\det(\lambda I - B) = \det(\lambda I - P^{-1}AP) = \det(P^{-1}(\lambda I - A)P)$$

Applying the multiplicativity of the determinant:

$$P) = \frac{1}{\det(P)} \det(\lambda I - A) \det(P) = \det(\lambda I - A) = p_A(\lambda)$$

Because $A$ and $B$ share identical characteristic polynomials, their roots—the eigenvalues $\lambda_i$ along with their algebraic multiplicities—are strictly identical.

• **Explicit Eigenvector Coordinate Transformation:**
If $x \in \mathbb{F}^n \setminus \{0\}$ is an eigenvector of $A$ with eigenvalue $\lambda$, then $Ax = \lambda x$. Transforming $x$ into the coordinate system of $\mathscr{B}'$ via $y = P^{-1}x \neq 0$:

$$By = (P^{-1}AP)(P^{-1}x) = P^{-1}Ax = P^{-1}(\lambda x) = \lambda(P^{-1}x)$$

Thus, $y$ is an eigenvector of $B$ corresponding to the identical eigenvalue $\lambda$, preserving both the eigenvalues and the geometric multiplicity $\operatorname{dim}(\operatorname{ker}(A - \lambda I)) = \operatorname{dim}(\operatorname{ker}(B - \lambda I))$.

<!-- page 33 -->

# V. Orthogonality, Gram–Schmidt, and Projection

**Mini-lecture.** Given linearly independent vectors $v_1, \dots, v_m$, the Gram–Schmidt procedure constructs an orthonormal list spanning the same successive subspaces. For the first two vectors,
$$e_1 = \frac{v_1}{\|v_1\|}, \qquad u_2 = v_2 - \langle v_2, e_1 \rangle e_1, \qquad e_2 = \frac{u_2}{\|u_2\|}.$$

If $e_1, \dots, e_m$ is an orthonormal basis of a subspace $U$, then the orthogonal projection of $b$ onto $U$ is
$$P_U b = \sum_{j=1}^m \langle b, e_j \rangle e_j.$$

The residual $b - P_U b$ is orthogonal to every vector in $U$, which is why $P_U b$ is the closest point in $U$ to $b$.

**Worked example.** Apply Gram–Schmidt to $v_1 = (1, 1)$ and $v_2 = (1, 0)$ in $\mathbb{R}^2$:
$$e_1 = \frac{1}{\sqrt{2}}(1, 1),$$
$$u_2 = (1, 0) - \left\langle (1, 0), \frac{1}{\sqrt{2}}(1, 1) \right\rangle \frac{1}{\sqrt{2}}(1, 1) = \frac{1}{2}(1, -1),$$
so
$$e_2 = \frac{1}{\sqrt{2}}(1, -1).$$

Thus $e_1, e_2$ is an orthonormal basis spanning the same space as $v_1, v_2$.

<!-- page 34 -->

**13.** On $\mathcal{P}_2(\mathbb{R})$ define
$$\langle p, q \rangle = \int_0^1 p(x)q(x) \, dx.$$

Apply the Gram–Schmidt procedure to
$$1, x, x^2$$

to produce an orthonormal basis of $\mathcal{P}_2(\mathbb{R})$. Show every subtraction and normalization step.

---

### Handwritten Solutions:

$$\vec{x} = \begin{bmatrix} 1 \\ x \\ x^2 \end{bmatrix} = \begin{bmatrix} v_1 \\ v_2 \\ v_3 \end{bmatrix} \qquad e_1 = \frac{v_1}{\|v_1\|} = \frac{1}{\sqrt{\langle v_1, v_1 \rangle}} = \frac{1}{\sqrt{\int_0^1 1 \cdot 1 \, dx}} = \frac{1}{\sqrt{1}} = 1$$

$$u_2 = v_2 - \langle v_2, e_1 \rangle e_1 = x - \langle x, 1 \rangle 1 = x - \int_0^1 x \cdot 1 \, dx = x - \left[ \frac{1}{2} x^2 \right]_0^1 = x - \frac{1}{2}$$

$$e_2 = \frac{u_2}{\|u_2\|} = \frac{x - 1/2}{\sqrt{\langle x - \frac{1}{2}, x - \frac{1}{2} \rangle}} = \frac{x - 1/2}{\sqrt{\int_0^1 \left(x - \frac{1}{2}\right)\left(x - \frac{1}{2}\right) \, dx}} = \frac{x - 1/2}{\sqrt{\int_0^1 \left(x^2 - x + \frac{1}{4}\right) \, dx}}$$

$$= \frac{x - 1/2}{\sqrt{\left[ \frac{1}{3}x^3 - \frac{1}{2}x^2 + \frac{1}{4}x \right]_0^1}} = \frac{x - 1/2}{\sqrt{\frac{1}{3} - \frac{1}{2} + \frac{1}{4}}} = \frac{x - 1/2}{\sqrt{1/12}} = \frac{1}{2\sqrt{3}}\left(x - \frac{1}{2}\right)$$

$$u_3 = v_3 - \langle v_3, e_2 \rangle e_2 - \langle v_3, e_1 \rangle e_1$$

$$= x^2 - \left\langle x^2, \frac{x - 1/2}{\sqrt{1/12}} \right\rangle \frac{x - 1/2}{\sqrt{1/12}} - \langle x^2, 1 \rangle 1$$

$$= x^2 - \int_0^1 x^2 \left( \frac{x - 1/2}{\sqrt{1/12}} \right) dx \left( \frac{x - 1/2}{\sqrt{1/12}} \right) - \int_0^1 x^2 \, dx$$

<!-- page 35 -->

$$x^2 - \int_0^1 x^2 \left( \frac{x - 1/2}{\sqrt{1/12}} \right) dx \left( \frac{x - 1/2}{\sqrt{1/12}} \right) - \int_0^1 x^2 \, dx$$

$$x^2 - \frac{x - 1/2}{1/12} \int_0^1 x^3 - \frac{1}{2} x^2 \, dx - \left[ \frac{1}{3} x^3 \right]_0^1$$

$$x^2 - 12\left(x - \frac{1}{2}\right) \left[ \frac{1}{4} x^4 - \frac{1}{6} x^3 \right]_0^1 - \left(\frac{1}{3}\right)$$

$$x^2 - (12x - 6)\left(\frac{1}{4} - \frac{1}{6}\right) - \frac{1}{3} \qquad \frac{3}{2} - 1 - \frac{1}{3}$$

$$x^2 - \left(3x - 2x - \frac{3}{2} + 1\right) - \frac{1}{3} = x^2 - x + \frac{1}{6} = u_3$$

$$e_3 = \frac{u_3}{\|u_3\|} = \frac{x^2 - x + 1/6}{\sqrt{\langle x^2 - x + \frac{1}{6}, x^2 - x + \frac{1}{6} \rangle}}$$

$$= \frac{x^2 - x + 1/6}{\sqrt{\int_0^1 \left(x^2 - x + \frac{1}{6}\right) \left(x^2 - x + \frac{1}{6}\right) dx}}$$

$$= \frac{x^2 - x + \frac{1}{6}}{\sqrt{\int_0^1 x^4 - x^3 + \frac{1}{6}x^2 - x^3 + x^2 - \frac{1}{6}x + \frac{1}{6}x^2 - \frac{1}{6}x + \frac{1}{36}}}$$

$$x^4 - 2x^3 + \frac{4}{3}x^2 - \frac{1}{3}x + 1/36$$

$$\left[ \frac{1}{5}x^5 - \frac{1}{2}x^4 + \frac{4}{9}x^3 - \frac{1}{6}x^2 + \frac{1}{36}x \right]_0^1$$

$$\frac{1}{5} - \frac{1}{2} + \frac{4}{9} - \frac{1}{6} + \frac{1}{36} =$$

<!-- page 36 -->

$$= \frac{x^2 - x + 1/6}{\sqrt{1/180}} = 6\sqrt{5}\left(x^2 - x + \frac{1}{6}\right) = e_3$$
$$= \sqrt{5}\left(6x^2 - 6x + 1\right)$$

$$\begin{aligned} &\text{Orthonormal} \\ &\text{Basis} \end{aligned} = \{e_1, e_2, e_3\} =$$
$$\left\{1, \frac{1}{2\sqrt{3}}\left(x - \frac{1}{2}\right), \sqrt{5}\left(6x^2 - 6x + 1\right)\right\}$$

<!-- page 37 -->

**14.** In $\mathbb{R}^4$, let
$$U = \operatorname{span}\{(1, 1, 0, 0), (1, 1, 1, 2)\}.$$

Find the vector $u \in U$ that minimizes
$$\|u - (1, 2, 3, 4)\|.$$

You may first orthonormalize a basis of $U$. After finding $u$, verify explicitly that the residual $(1, 2, 3, 4) - u$ is orthogonal to both spanning vectors of $U$.

---

### Handwritten Solutions:

a) GS on

$$v_1 = \begin{bmatrix} 1 \\ 1 \\ 0 \\ 0 \end{bmatrix}, \qquad v_2 = \begin{bmatrix} 1 \\ 1 \\ 1 \\ 2 \end{bmatrix}$$

$$e_1 = \frac{v_1}{\|v_1\|_2} = \frac{(1, 1, 0, 0)^T}{\sqrt{1^2 + 1^2 + 0^2 + 0^2}} = \frac{1}{\sqrt{2}} \begin{bmatrix} 1 \\ 1 \\ 0 \\ 0 \end{bmatrix} = \begin{bmatrix} 1/\sqrt{2} \\ 1/\sqrt{2} \\ 0 \\ 0 \end{bmatrix}$$

$$u_2 = v_2 - \langle v_2, e_1 \rangle e_1$$

$$= \begin{bmatrix} 1 \\ 1 \\ 1 \\ 2 \end{bmatrix} - \left(\frac{1}{\sqrt{2}} + \frac{1}{\sqrt{2}} + 0 + 0\right) \begin{bmatrix} 1/\sqrt{2} \\ 1/\sqrt{2} \\ 0 \\ 0 \end{bmatrix} = \begin{bmatrix} 1 \\ 1 \\ 1 \\ 2 \end{bmatrix} - \frac{2}{\sqrt{2}} \begin{bmatrix} 1/\sqrt{2} \\ 1/\sqrt{2} \\ 0 \\ 0 \end{bmatrix} = \begin{bmatrix} 1 - 1 \\ 1 - 1 \\ 1 - 0 \\ 2 - 0 \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \\ 1 \\ 2 \end{bmatrix}$$

$$e_2 = \frac{u_2}{\|u_2\|} = \frac{u_2}{\sqrt{0 + 0 + 1 + 4}} = \frac{1}{\sqrt{5}} \begin{bmatrix} 0 \\ 0 \\ 1 \\ 2 \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \\ 1/\sqrt{5} \\ 2/\sqrt{5} \end{bmatrix}$$

$$\mathcal{B}_e = \left\{ \begin{bmatrix} 1/\sqrt{2} \\ 1/\sqrt{2} \\ 0 \\ 0 \end{bmatrix}, \begin{bmatrix} 0 \\ 0 \\ 1/\sqrt{5} \\ 2/\sqrt{5} \end{bmatrix} \right\}$$

$$\text{let } v = (1, 2, 3, 4) \text{ in original basis } U$$

$$\min u = P_u(v) = \langle v, e_1 \rangle e_1 + \langle v, e_2 \rangle e_2$$

$$\text{by projecting } v \text{ w/ } \mathcal{B}_e$$

<!-- page 38 -->

$$P_U(v) = \langle v, e_1 \rangle e_1 + \langle v, e_2 \rangle e_2$$

$$v = \begin{bmatrix} 1 \\ 2 \\ 3 \\ 4 \end{bmatrix} \quad e_1 = \begin{bmatrix} 1/\sqrt{2} \\ 1/\sqrt{2} \\ 0 \\ 0 \end{bmatrix} \quad e_2 = \begin{bmatrix} 0 \\ 0 \\ 1/\sqrt{5} \\ 2/\sqrt{5} \end{bmatrix}$$

$$\frac{3}{\sqrt{2}} \begin{bmatrix} 1/\sqrt{2} \\ 1/\sqrt{2} \\ 0 \\ 0 \end{bmatrix} + \frac{11}{\sqrt{5}} \begin{bmatrix} 0 \\ 0 \\ 1/\sqrt{5} \\ 2/\sqrt{5} \end{bmatrix}$$

$$\begin{bmatrix} 3/2 \\ 3/2 \\ 0 \\ 0 \end{bmatrix} + \begin{bmatrix} 0 \\ 0 \\ 11/5 \\ 22/5 \end{bmatrix} = \begin{bmatrix} 3/2 \\ 3/2 \\ 11/5 \\ 22/5 \end{bmatrix} = u$$

Verify

$$r = v - u = \begin{bmatrix} 1 \\ 2 \\ 3 \\ 4 \end{bmatrix} - \begin{bmatrix} 3/2 \\ 3/2 \\ 11/5 \\ 22/5 \end{bmatrix} = \begin{bmatrix} -1/2 \\ 1/2 \\ 4/5 \\ -2/5 \end{bmatrix}$$

$$r \perp v_1 = (1, 1, 0, 0)^T \, ?$$

$$\langle r, v_1 \rangle = -1/2 + 1/2 + 0 + 0 = 0 \quad \checkmark$$

$$r \perp v_2 = (1, 1, 1, 2)^T \, ?$$

$$\langle r, v_2 \rangle = -\frac{1}{2} + \frac{1}{2} + \frac{4}{5} - \frac{4}{5} = 0 \quad \checkmark$$

$$u = (3/2, 3/2, 11/5, 22/5)^T$$

<!-- page 39 -->

**15. Proof: orthogonality as a minimization condition.** Suppose $u, v \in V$. Prove that
$$\langle u, v \rangle = 0 \iff \|u\| \le \|u + av\| \quad \text{for every } a \in \mathbb{F}.$$

Interpret the result as the simplest version of the least-squares first-order condition.

---

### Handwritten Solutions:

$\implies$ if $\langle u, v \rangle = 0$,

let $a \in \mathbb{F}$ be some scalar,

by induced norm $\|u\|^2 = \langle u, u \rangle$

we know $\|u + av\|^2 = \langle u + av, u + av \rangle$

$$= \langle u, u + av \rangle + \langle av, u + av \rangle$$

by lin in first arg

$$= \langle u, u \rangle + \bar{a}\langle u, v \rangle + a\langle v, u \rangle + a\bar{a}\langle v, v \rangle$$

by conj-lin in 2nd

this

$$\|u + av\|^2 = \langle u, u \rangle + a\langle v, u \rangle + \bar{a}\langle v, u \rangle + |a|^2 \langle v, v \rangle$$

$$\langle u, u \rangle = \|u\|^2 \quad \& \quad \langle v, v \rangle = \|v\|^2$$

$$\|u + av\|^2 = \|u\|^2 + a\langle v, u \rangle + \bar{a}\langle v, u \rangle + |a|^2 \|v\|^2$$

since $\langle u, v \rangle = 0$,

$$\|u + av\|^2 = \|u\|^2 + |a|^2 \|v\|^2$$

since $|a|^2 \|v\|^2 \ge 0$,

$$\|u + av\|^2 \ge \|u\|^2$$

sqrt both sides

$$\|u + av\| \ge \|u\| \quad \text{for all } a \in \mathbb{F}$$

<!-- page 40 -->

$\Leftarrow$ if $\|u\| \le \|u + av\| \quad \forall a \in \mathbb{F},$
square both sides
$$\|u\|^2 \le \|u + av\|^2$$

$$\|u\|^2 \le \|u\|^2 + 2\bar{a}\langle u, v \rangle + |a|^2 \|v\|^2$$

$$\implies 0 \le 2\bar{a}\langle u, v \rangle + |a|^2 \|v\|^2$$

if $v = 0, \quad \langle u, v \rangle = 0 \quad \text{b/c } u_1(0) + \dots + u_n 0 = 0$

for $v \neq 0, \quad 0 \le |a|^2 \|v\|^2$
$$\implies 0 > -|a| \|v\|^2$$

$$-|a|^2 \|v\|^2 \le 2\bar{a}\langle u, v \rangle$$

$$-|a|^2 \|v\|^2 < 0 \le 2\bar{a}\langle u, v \rangle$$

$$\text{???}$$

$$2\bar{a}\langle u, v \rangle \le 0 \le 2\bar{a}\langle u, v \rangle$$

$$\text{thus } \langle u, v \rangle = 0 \qquad \square$$

<!-- page 41 -->

**2. Non-Trivial Case ($v \neq 0$):**
Assume $v \neq 0$, so $\|v\|^2 > 0$. Expanding the squared norm for any $a \in \mathbb{F}$:

$$\|u + av\|^2 = \langle u + av, u + av \rangle = \|u\|^2 + a\langle v, u \rangle + \bar{a}\langle u, v \rangle + |a|^2\|v\|^2$$

Using $\langle v, u \rangle = \overline{\langle u, v \rangle}$, this becomes:

$$\|u + av\|^2 = \|u\|^2 + 2 \operatorname{Re}(\bar{a}\langle u, v \rangle) + |a|^2\|v\|^2$$

**3. The Missing Step (Choosing $a$):**
Since the inequality $\|u\| \le \|u + av\|$ holds for *all* $a \in \mathbb{F}$, choose the specific scalar:

$$a = -\frac{\langle u, v \rangle}{\|v\|^2}$$

**4. Substitution & Simplification:**
Substitute this choice of $a$ into the expansion:

$$\|u + av\|^2 = \|u\|^2 - \frac{\langle u, v \rangle}{\|v\|^2} \langle v, u \rangle - \frac{\overline{\langle u, v \rangle}}{\|v\|^2} \langle u, v \rangle + \frac{|\langle u, v \rangle|^2}{\|v\|^4} \|v\|^2$$

$$\|u + av\|^2 = \|u\|^2 - \frac{|\langle u, v \rangle|^2}{\|v\|^2} - \frac{|\langle u, v \rangle|^2}{\|v\|^2} + \frac{|\langle u, v \rangle|^2}{\|v\|^2}$$

$$\|u + av\|^2 = \|u\|^2 - \frac{|\langle u, v \rangle|^2}{\|v\|^2}$$

**5. Conclusion:**
The hypothesis $\|u\|^2 \le \|u + av\|^2$ yields:

$$\|u\|^2 \le \|u\|^2 - \frac{|\langle u, v \rangle|^2}{\|v\|^2} \implies \frac{|\langle u, v \rangle|^2}{\|v\|^2} \le 0$$

Because $\|v\|^2 > 0$ and $|\langle u, v \rangle|^2 \ge 0$, it must be that:

$$|\langle u, v \rangle|^2 = 0 \implies \langle u, v \rangle = 0$$

<!-- page 42 -->

### Least-Squares First-Order Condition Interpretation

In the optimization problem:

$$\min_{a \in \mathbb{F}} \|u + av\|^2$$

the objective function $f(a) = \|u\|^2 + 2 \operatorname{Re}(\bar{a}\langle u, v \rangle) + |a|^2 \|v\|^2$ is strictly convex with respect to $a$. The point $a = 0$ is the global minimizer if and only if the directional derivative (gradient) at $0$ vanishes:

$$\nabla f(0) = 2\langle u, v \rangle = 0 \iff \langle u, v \rangle = 0$$

This expresses the classic projection theorem: the error vector $u$ has minimal norm if and only if it is orthogonal to the subspace spanned by $v$.

<!-- page 43 -->

# Optional Exploratory Problem

**16. What failure of diagonalization looks like.** Let $T \in \mathcal{L}(\mathbb{C}^2)$ be defined by
$$T(w, z) = (z, 0).$$

(a) Find all eigenvalues and eigenspaces of $T$.

(b) Is there a basis of $\mathbb{C}^2$ consisting of eigenvectors? Explain.

(c) Compute $T^2$.

(d) Find $v$ such that $Tv \neq 0$ but $T^2v = 0$.

(e) Show that $(Tv, v)$ is a basis and write the matrix of $T$ in this basis.

(f) The resulting matrix is
$$\begin{pmatrix} 0 & 1 \\ 0 & 0 \end{pmatrix}.$$

Explain informally what extra information this matrix records that ordinary eigenvectors miss.

---

### Handwritten Solutions:

$$\begin{aligned}
T(w, z) = (z, 0) = A \begin{bmatrix} w \\ z \end{bmatrix} &= \begin{bmatrix} z \\ 0 \end{bmatrix} \\
\implies A &= \begin{bmatrix} 0 & 1 \\ 0 & 0 \end{bmatrix}
\end{aligned}$$

$$\begin{aligned}
\text{Set } \det(A - \lambda I) = 0 &\implies \det \begin{bmatrix} -\lambda & 1 \\ 0 & -\lambda \end{bmatrix} = 0 \\
&\implies \lambda^2 - 0 = 0 \implies \lambda^2 = 0 \\
&\implies \lambda_1 = \lambda_2 = 0
\end{aligned}$$

$$\begin{aligned}
Av = \lambda v &= 0 \\
\begin{bmatrix} 0 & 1 \\ 0 & 0 \end{bmatrix} \begin{bmatrix} v_1 \\ v_2 \end{bmatrix} &= \begin{bmatrix} 0 \\ 0 \end{bmatrix} \implies \begin{aligned} &v_1 \text{ free} \\ &v_2 = 0 \end{aligned} \implies v = \begin{bmatrix} t \\ 0 \end{bmatrix}
\end{aligned}$$

$$\text{eigenspace} = \operatorname{span}\left\{ \begin{bmatrix} 1 \\ 0 \end{bmatrix} \right\}$$

<!-- page 44 -->

b) No, since all eigenvectors are of form $\begin{bmatrix} t \\ 0 \end{bmatrix}$, they can only span 1 dimension, so cannot form a basis for $\mathbb{C}^2$.

c) $T^2 = T(T(w, z)) = T(z, 0) = (0, 0)$
$$AA \begin{bmatrix} w \\ z \end{bmatrix} = \begin{bmatrix} 0 & 1 \\ 0 & 0 \end{bmatrix} \begin{bmatrix} 0 & 1 \\ 0 & 0 \end{bmatrix} \begin{bmatrix} w \\ z \end{bmatrix}$$
$$= \begin{bmatrix} 0 & 0 \\ 0 & 0 \end{bmatrix} \begin{bmatrix} w \\ z \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix}$$

(d) Find $v$ such that $Tv \neq 0$ but $T^2v = 0$.

(e) Show that $(Tv, v)$ is a basis and write the matrix of $T$ in this basis.

d) $T(v_1, v_2) \neq 0 \quad T^2(v_1, v_2) = 0$
applies for any $v_2 \neq 0$

e) $(Tv, v)$ for $v = \begin{bmatrix} v_1 \\ v_2 \end{bmatrix}$ w/ $v_2 \neq 0$
$$= \left\{ \begin{bmatrix} v_2 \\ 0 \end{bmatrix}, \begin{bmatrix} v_1 \\ v_2 \end{bmatrix} \right\} \quad \begin{aligned} &\text{lin ind} \\ &\& \text{ spans } \mathbb{C}^2 \end{aligned}$$

$$\forall c_1, c_2 \in \mathbb{C}^2, \quad a_1 v_2 + a_2 v_1 = c_1$$
$$a_2 v_2 = c_2$$
$$\exists a_1, a_2 \implies \text{by closure of } \mathbb{C}$$

$$\begin{aligned} &\text{since} \\ &a_1 \begin{bmatrix} v_2 \\ 0 \end{bmatrix} + a_2 \begin{bmatrix} v_1 \\ v_2 \end{bmatrix} \\ &= \begin{bmatrix} a_1 v_2 \\ 0 \end{bmatrix} + \begin{bmatrix} a_2 v_1 \\ a_2 v_2 \end{bmatrix} \\ &= \begin{bmatrix} 0 \\ 0 \end{bmatrix} \\ &\text{only if} \\ &a_2 v_2 = 0 \\ &\implies a_2 = 0 \\ &\& \quad a_1 v_2 = 0 \\ &\implies a_1 = 0 \end{aligned}$$

<!-- page 45 -->

e) Matrix of $T$ in $\left\{ \begin{bmatrix} v_2 \\ 0 \end{bmatrix}, \begin{bmatrix} v_1 \\ v_2 \end{bmatrix} \right\}$
s.t. $T(w,z) = (z, 0)$

$$= \begin{bmatrix} 0 \begin{bmatrix} v_1 \\ v_2 \end{bmatrix}, & 1 \begin{bmatrix} v_2 \\ 0 \end{bmatrix} \end{bmatrix}$$

$$\text{for } v_2 = 1$$
$$v_1 \text{ free}$$

$$= \begin{bmatrix} 0 & 1 \\ 0 & 0 \end{bmatrix}$$

f) The resulting matrix is
$$\begin{pmatrix} 0 & 1 \\ 0 & 0 \end{pmatrix}.$$

Explain informally what extra information this matrix records that ordinary eigenvectors miss.

<!-- page 46 -->

The matrix $\begin{pmatrix} 0 & 1 \\ 0 & 0 \end{pmatrix}$ encodes transient, step-by-step dynamical coupling (a Jordan chain), which pure eigenvectors completely miss because eigenvectors only detect static directions that map strictly into themselves.

The Information Missing from Ordinary Eigenvectors

* **Static Invariance vs. Directional Flow:**

  * An ordinary eigenvector $v_1 = \begin{pmatrix} 1 \\ 0 \end{pmatrix}$ satisfies $Tv_1 = 0 \cdot v_1 = 0$. It only identifies a static 1D subspace (the kernel) where vectors are crushed to zero immediately.

  * The second basis vector $v_2 = \begin{pmatrix} 0 \\ 1 \end{pmatrix}$ is a **generalized eigenvector**. It satisfies $(T - 0I)^2 v_2 = 0$, but $(T - 0I) v_2 \neq 0$.

  * Instead of mapping to a scalar multiple of itself, $v_2$ maps directly to $v_1$:

$$Tv_2 = v_1, \qquad Tv_1 = 0$$

* **Nilpotent Shift Structure:**

  The off-diagonal $1$ records a **chain of progression** (or shift operator):

$$v_2 \xrightarrow{\quad T \quad} v_1 \xrightarrow{\quad T \quad} 0$$

  Ordinary eigenvectors only tell you the "terminal state" ($v_1 \to 0$). The matrix entry $1$ tells you that there is a 1-step "delay" or "queue" before reaching the kernel.

* **Dynamical and Differential Implications:**

  In continuous dynamical systems ($\dot{x} = Ax$), a diagonal matrix produces pure exponential decay or growth ($e^{\lambda t}$). A non-zero superdiagonal $1$ in a Jordan block produces secular polynomial modulation:

<!-- page 47 -->

# Optional Exploratory Problem

**16. What failure of diagonalization looks like.** Let $T \in \mathcal{L}(\mathbb{C}^2)$ be defined by
$$T(w, z) = (z, 0).$$

(a) Find all eigenvalues and eigenspaces of $T$.

(b) Is there a basis of $\mathbb{C}^2$ consisting of eigenvectors? Explain.

(c) Compute $T^2$.

(d) Find $v$ such that $Tv \neq 0$ but $T^2v = 0$.

(e) Show that $(Tv, v)$ is a basis and write the matrix of $T$ in this basis.

(f) The resulting matrix is
$$\begin{pmatrix} 0 & 1 \\ 0 & 0 \end{pmatrix}.$$

Explain informally what extra information this matrix records that ordinary eigenvectors miss.