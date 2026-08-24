<!-- page 1 -->

# 1 Multivariate Calculus and Convexity

1. For each of the following functions, state if the function is homogeneous (if so, state its degree of homogeneity) and state whether it is homothetic. If your answer depends on the parameters, explain how it depends on the parameters. (Optional: prove that all these functions are quasiconcave.)

   (a) $u(x_1, x_2, \dots, x_n) = \prod_{i=1}^n x_i^{\alpha_i}$
   (b) $u(x_1, x_2, \dots, x_n) = \prod_{i=1}^n (x_i - b_i)^{\alpha_i}$
   (c) $u(x_1, x_2, \dots, x_n) = \min\{a_1 x_1, \dots, a_n x_n\}$

<!-- page 2 -->

2. Consider a production function $f : \mathbb{R}_+^n \to \mathbb{R}_+$. $f(x)$ is the amount of the single output good that can be produced using $x_1$ units of the first input, $x_2$ units of the second,..., $x_n$ units of the $n$th input. Let us say $f$ is additive if for any $x, y \in \mathbb{R}_+^n$, $f(x+y) \ge f(x) + f(y)$ (intuitively, if you can produce $f(x)$ with $x$ and $f(y)$ with $y$, you should be able to produce at least $f(x+y)$ when you have both $x$ and $y$). Say $f$ is divisible if for any $t \in [0, 1]$, $x \in \mathbb{R}_+^n$, $f(tx) \ge tf(x)$ (intuitively, if you can produce $f(x)$ with $x$, you should at least be able produce half as much output when you only have half as much of every input). Prove that if a production function $f$ is additive and divisible, then it is concave and homogeneous of degree 1.

<!-- page 3 -->

3. In an economy with $n$ goods with prices $P_n$, we define the aggregate price level $P$ as:

$$P = A(P_1, P_2, \dots, P_n) = \left( \sum_{i=1}^n P_i^{1-\theta_i} \right)^\alpha$$

where $\theta_i \ge 0$ and $\theta_i \ne 1$ for all $i = 1, 2, \dots, n$, and $\alpha \in \mathbb{R}$.

(a) Is $A$ homogeneous for all values of $\alpha$ and the $\theta_i$'s?

From now on, consider the special case where $\theta_i = \theta \ge 0$ for all $i$.

(b) Loglinearize the definition equation of the price level around a point where all prices are the same: $P_1 = P_2 = \dots = P_n = P^*$ (and therefore $P = \left(n (P^*)^{1-\theta}\right)^\alpha$). (Your answer needs to be independent of $P^*$.)

<!-- page 4 -->

From now on, go back to the non-loglinearized aggregator.

(c) For which value of $\alpha$ is $A$ homogeneous of degree 1?  
   From now on, assume that $\alpha$ takes the value such that $A$ is homogeneous of degree 1.

(d) Show that $A$ is quasi-concave.

<!-- page 5 -->

8. Is the function $f : \mathbb{R}^2 \to \mathbb{R}$ given by $f(x, y) = x^2 + y^2$ convex? Is the function $g : \mathbb{R}^2 \to \mathbb{R}$ given by $g(x, y) = x^2 y^2$ convex?

<!-- page 6 -->

9. Consider the function $f : \mathbb{R}^2 \to \mathbb{R}$ defined as
$$f(x_1, x_2) := \frac{x_1 x_2}{x_1^2 + x_2^2 + 1}.$$

(a) For each $x \in \mathbb{R}^2$, calculate the partials $\partial f/\partial x_1(x)$ and $\partial f/\partial x_2(x)$.
(b) Use Theorem 1.7 to argue that $f$ is differentiable at every $x \in \mathbb{R}^2$. What is the total derivative of $f$ for each $x \in \mathbb{R}^2$?

---

a) $\frac{\partial f}{\partial x_1} = \frac{(x_1^2 + x_2^2 + 1)(x_2) - (x_1 x_2)(2x_1)}{(x_1^2 + x_2^2 + 1)^2}$

$= \frac{x_1^2 x_2 + x_2^3 + x_2 - 2x_1^2 x_2}{(x_1^2 + x_2^2 + 1)^2} = \frac{x_2(-x_1^2 + x_2^2 + 1)}{(x_1^2 + x_2^2 + 1)^2}$

$\text{Quot. } \frac{d}{dx}\frac{f(x)}{g(x)} = \frac{g(x)f'(x) - f(x)g'(x)}{g(x)^2}$

$\frac{\partial f}{\partial x_2} = \frac{(x_1^2 + x_2^2 + 1)(x_1) - (x_1 x_2)(2x_2)}{(x_1^2 + x_2^2 + 1)^2} = \frac{x_1(x_1^2 - x_2^2 + 1)}{(x_1^2 + x_2^2 + 1)^2}$

b) $Df(x) = \left[\begin{matrix} \frac{\partial f}{\partial x_1} & \frac{\partial f}{\partial x_2} \end{matrix}\right] = \left[\begin{matrix} \frac{x_2(-x_1^2 + x_2^2 + 1)}{(x_1^2 + x_2^2 + 1)^2} & \frac{x_1(x_1^2 - x_2^2 + 1)}{(x_1^2 + x_2^2 + 1)^2} \end{matrix}\right]$

<!-- page 7 -->

9. Consider the function $f : \mathbb{R}^2 \to \mathbb{R}$ defined as
$$f(x_1, x_2) := \frac{x_1 x_2}{x_1^2 + x_2^2 + 1}.$$

(a) For each $x \in \mathbb{R}^2$, calculate the partials $\partial f / \partial x_1(x)$ and $\partial f / \partial x_2(x)$.
(b) Use Theorem 1.7 to argue that $f$ is differentiable at every $x \in \mathbb{R}^2$. What is the total derivative of $f$ for each $x \in \mathbb{R}^2$?

a) $\frac{\partial f}{\partial x_1}$

$$\text{Quot. } \frac{d}{dx} \frac{f(x)}{g(x)} = \frac{g(x) f'(x)}{g(x)}$$

<!-- page 8 -->

10. (a) Let $f(y) = ye^{-y^2/2}$. Calculate $\int_0^\infty f(y)y^2 dy$ using integration by parts. (You can use the fact that $\int_0^\infty f(y) dy = 1$.)

(b) Let $S := \{(x_1, x_2) \in \mathbb{R}^2 : 1 \le x_1 \le 2, \ 0 \le x_2 \le x_1^3\}$ and function $f : S \to \mathbb{R}$ be defined as $f(x_1, x_2) = x_1 x_2$. Calculate the integral $\int_S f(x) dx$.

(c) Let rectangle $S := \{(x_1, x_2) \in \mathbb{R}^2 : 1 \le x_1 + x_2 \le 5, \ -1 \le x_1 - x_2 \le 1\}$ and function $f : S \to \mathbb{R}$ be defined as $f(x_1, x_2) = x_1^2 + x_2^2 - 1$. Calculate the integral $\int_S f(x) dx$.
(Hint: define
$$\begin{cases} u = x_1 - x_2 \\ v = x_1 + x_2 \end{cases}$$
and use the change of variables trick.)

<!-- page 9 -->

11. Let $f : \mathbb{R}_+ \to \mathbb{R}$ defined as

$$F(x) := \int_{-2x}^{x^2} (x^2 + e^t)^2 dt.$$

Find $F'(x)$ for each $x \in \mathbb{R}_+$.

<!-- page 10 -->

12. Consider the system of linear equations:

$$\begin{cases} x_2 + x_1 y_1 + y_2^2 = 0 \\ x_1 - x_2 y_2 + y_1^2 = 0 \end{cases}$$

Use the implicit function theorem to argue that the system implicitly defines $(y_1, y_2)$ as a function of $(x_1, x_2)$ from an open ball around $(x_1^0, x_2^0) = (-1, 1)$ to an open ball around $(y_1^0, y_2^0) = (1, 0)$. What is the derivative of this implicit function at $(x_1^0, x_2^0) = (-1, 1)$?

<!-- page 11 -->

13. Log-linearize the following equations.
(1) $\sum_{i=1}^n \alpha_i X_i = \sum_{i=1}^n X_i^{\beta_i}$ around $(X_1^*, \dots, X_n^*)$ satisfying this equation, where $\alpha_i > 0$, $\beta_i \neq 0$ for $i = 1, 2, \dots, n$.
(2) $\beta W = (1 - \alpha) \left(\frac{K}{N}\right)^\alpha$ around $(W^*, K^*, N^*)$ satisfying this equation, where $\alpha \in (0, 1)$, $\beta > 0$.
(3) $P^{1-\varepsilon} = \alpha + (1 - \alpha) \left(\frac{Q}{R}\right)^{1-\varepsilon}$ around $(P^*, Q^*, R^*)$ satisfying this equation, where $\varepsilon \neq 1$.

<!-- page 12 -->

14. Suppose $x_{t+1} = \cos x_t$, $x_0 \in [0, 1]$.
    (a) Show $x_\infty := \lim_{t \to \infty} x_t$ exists in $(0, 1)$.
    (b) Log-linearize the equation $x_{t+1} = \cos x_t$ around the point $x_\infty$, and for the approximated equation relating $x_{t+1}$ to $x_t$, show $\lim_{t \to \infty} x_t = x_\infty$.

<!-- page 13 -->

15. In this exercise, you will show Taylor polynomials obey a special property that make them potentially good approximations for a function, namely that they uniquely share all derivatives of orders up to the degree of the polynomial with the function of interest at a particular point.

(a) Suppose $g : \mathbb{R} \to \mathbb{R}$, $g(x) = \frac{(x-c)^k}{k!}$ for $k \in \mathbb{Z}_{>0}$, $c \in \mathbb{R}$. Use induction to show

$$D^j g(x) = \begin{cases} \frac{(x-c)^{k-j}}{(k-j)!} & 0 \le j < k \\ 1 & j = k \\ 0 & j > k \end{cases}$$

where $D^j$ is the $j$-th order derivative, $j \in \mathbb{Z}_{\ge 0}$.

(b) Suppose $f : \mathbb{R} \to \mathbb{R}$ and $f \in C^n$, $n \in \mathbb{Z}_{\ge 0}$. Consider the polynomial $p(x) = \sum_{k=0}^n a_k \frac{(x-c)^k}{k!}$ where $a_k \in \mathbb{R}$. Show that for all $j = 0, \dots, n$, if $p^{(j)}(c) = f^{(j)}(c)$, then $a_j = f^{(j)}(c)$. Note the superscript $(j)$ signifies the $j$-th order derivative.

<!-- page 14 -->

# 2 Linear Algebra

1. Check whether the following sets are subspaces of the $n$-dimensional real vector space $\mathbb{R}^n$.$^1$

   (a) Empty set $\emptyset$.  
   (b) $X := \{x \in \mathbb{R}^n : x = \alpha z \text{, some } \alpha \in \mathbb{R}\}$, where $z \in \mathbb{R}^n$.  
   (c) (when $n = 3$) $S := \{(t - 2s, -s, t) : t, s \in \mathbb{R}\}$.

a) To show: $\emptyset \in \mathbb{R}^n$

### Closed under addition
$$\forall x, y \in \emptyset \implies x + y \in \emptyset \text{ trivially, since } \emptyset = \{\} \text{ so } \forall x, y \in \emptyset \text{ is false}$$

### Closed under scalar multiplication
$$\forall x \in \emptyset, \alpha \in \mathbb{R}, \alpha x \in \emptyset \text{ trivially, since } \emptyset = \{\} \text{ so } \forall x \in \emptyset \text{ is false}$$

### Existence of additive identity 0
$$0 \notin \emptyset \text{ since } \emptyset = \{\}$$
$$\therefore \emptyset \text{ is not a vector subspace of } \mathbb{R}^n$$

b) $X := \{x \in \mathbb{R}^n : x = \alpha z, \alpha \in \mathbb{R}, z \in \mathbb{R}^n\}$

### Closed under Addition
$$\forall x_1, x_2 \in X \implies x_1 + x_2 \in X$$
$$x_1 = \alpha_1 z, \quad x_2 = \alpha_2 z \quad \alpha_1, \alpha_2 \in \mathbb{R}$$
$$z_1, z_2 \in \mathbb{R}^n$$

<!-- page 15 -->

$$x_1 + x_2 = \alpha_1 z_1 + \alpha_2 z_2$$

$$\exists \alpha_3 \in \mathbb{R}, z_3 \in \mathbb{R}^n \text{ s.t.}$$

$$\alpha_1 z_1 + \alpha_2 z_2 = \alpha_3 z_3$$

$$\text{since } \mathbb{R} \text{ and } \mathbb{R}^n \text{ are vector spaces and closed under addition and scalar multiplication}$$

$$\therefore \alpha_3 z_3 = x_3 \in X$$

### Closed under Scalar Multiplication

$$\forall x = \alpha z, \ \alpha \in \mathbb{R} \text{ \& } z \in \mathbb{R}^n$$

$$\exists \beta \in \mathbb{R} \text{ s.t. } \beta x = \beta \alpha z$$

$$\beta \alpha \in \mathbb{R} \text{ by closure of } \mathbb{R}$$

$$\therefore \beta x \in X$$

### Existence of additive identity 0

$$\exists 0 \in \mathbb{R}^n$$

$$\forall \alpha \in \mathbb{R}, \ \alpha 0 = 0$$

$$\therefore 0 \in X$$

All three conditions of a vector subspace are satisfied, therefore X is a vector subspace of $\mathbb{R}^n$

<!-- page 16 -->

c) $S := \{(t - 2s, -s, t) : t, s \in \mathbb{R}\}$
Closure under addition

$$\forall (t_1 - 2s_1, -s_1, t_1), (t_2 - 2s_2, -s_2, t_2) \in S$$
$$\exists \lambda_1, \lambda_2 \in \mathbb{R}, \quad t_3, s_3 \in \mathbb{R}$$

$$\lambda_1 (t_1 - 2s_1) + \lambda_2 (t_2 - 2s_2) = (t_3 - 2s_3)$$
$$\lambda_1 t_1 - 2\lambda_1 s_1 + \lambda_2 t_2 - 2\lambda_2 s_2 = t_3 - 2s_3$$

Grouping terms,

$$\lambda_1 t_1 + \lambda_2 t_2 = t_3 \quad -2\lambda_1 s_1 - 2\lambda_2 s_2 = -2s_3$$
$$\text{sufficient?} \quad -\lambda_1 s_1 - \lambda_2 s_2 = -s_3$$

$$\therefore$$
$$\lambda_1 (t_1 - 2s_1, -s_1, t_1) + \lambda_2 (t_2 - 2s_2, -s_2, t_2)$$
$$= (t_3 - 2s_3, -s_3, t_3) \in S$$

Since S is closed under linear combinations, it is a vector subspace of $\mathbb{R}^3$

<!-- page 17 -->

2. Show that the following $\|\cdot\|$ are valid norms in $\mathbb{R}^n$.

   (a) $\|x\| := \max_{i=1}^n |x_i|$.
   (b) $\|x\| := \sum_{i=1}^n |x_i|$.

<!-- page 18 -->

3. (a) Suppose the vectors $v_1, v_2, \dots, v_n$ are linearly independent. Show that no one of these vectors can be expressed as a linear combination of the other $n - 1$ vectors.
   (b) Prove that the following claim is false: "Suppose the vectors $v_1, v_2, \dots, v_n$ are linearly dependent. Then any one of these vectors can be expressed as a linear combination of the other $n - 1$ vectors."

a) Given $v_1, \dots, v_n \in V$
are linearly independent,
$$c_1 v_1 + \dots + c_n v_n = 0 \quad (*)$$
has only trivial sol. $c_1 = \dots = c_n = 0$

For contradiction, pick $v_i \in V$
assume $v_i = c_1 v_1 + \dots + c_{i-1} v_{i-1} + c_{i+1} v_{i+1} + \dots + c_n v_n$

Subtract $v_i$:
$$0 = c_1 v_1 + \dots + c_{i-1} v_{i-1} + (-1) v_i + c_{i+1} v_{i+1} + \dots + c_n v_n$$

but $(-1)$ is a valid $c_i$ coefficient
and by $(*)$ $\sum_{i=1}^n c_i v_i = 0$ has only trivial solution.

<!-- page 19 -->

Since $c_i = -1 \neq 0$,  
assume at contradiction,  
assumption must be false. $\square$

b) Given $v_1, \dots, v_n$ linearly dep.  
We seek to disprove  
$v_n = c_1 v_1 + \dots + c_{n-1} v_{n-1}$  
for arbitrary $v_n$.

$0 = c_1 v_1 + \dots + c_{n-1} v_{n-1} + c_n v_n \quad (*)$  
has nontrivial solutions  
by linear dependence  
such that not all $c_i = 0$.

Counterexample:  
Let $v_1 = \begin{bmatrix} 0 \\ 1 \end{bmatrix}$, $v_2 = \begin{bmatrix} 0 \\ 0 \end{bmatrix}$

$$0 \begin{bmatrix} 0 \\ 1 \end{bmatrix} + 1 \begin{bmatrix} 0 \\ 0 \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix}$$

<!-- page 20 -->

s.t. $v_1$ & $v_2$ are linearly dep.,
but choosing $v_1$ as $v_n$,
there are no $c_2$ s.t.

$$v_1 = c_2 v_2 \quad \text{since}$$

$$\forall c_2 \in \mathbb{R}, \quad c_2 \begin{bmatrix} 0 \\ 0 \end{bmatrix} = \begin{bmatrix} 0 \\ 0 \end{bmatrix}$$

Therefore $v_1$ cannot be expressed as a linear combination of $v_2$ & the statement is false. $\blacksquare$

<!-- page 21 -->

4. Consider a vector space $(V, +, \cdot)$ over $\mathbb{R}$ with $\dim V = n$.

   (a) Show that $v_1, v_2, \dots, v_n$ are a basis of $V$ iff they are linearly independent.
   (b) Show that $v_1, v_2, \dots, v_n$ are a basis of $V$ iff any vector in $V$ can be represented by a linear combination of them.

a) Basis requires $v_1, \dots, v_n = \operatorname{span} V$
and $v_1, \dots, v_n$ to be linearly ind.

$\Rightarrow$ If $v_1, \dots, v_n$ is a basis of $V$, lin. ind. satisfied by def.

$\Leftarrow$ If $v_1, \dots, v_n$ lin ind,

$$\sum_{i=1}^n c_i v_i = 0 \implies \forall c_i = 0 \text{ is the only sol.}$$

Assume $v_1, \dots, v_n \neq \operatorname{span} V$
s.t. $\exists x \in V : x$ cannot be expressed as linear comb. $\sum_{i=1}^n c_i v_i$, thus $v_1, \dots, v_n, x$ is linearly ind

<!-- page 22 -->

Therefore $c_1 v_1 + \dots + c_n v_n + c_{n+1} x = 0$
$\implies c_1 = \dots = c_n = c_{n+1} = 0$
is the only nontrivial sol.

but $c_1 v_1 + \dots + c_n v_n = -c_{n+1} x$
must be true s.t.
$-\frac{1}{c_{n+1}} \sum_{i=1}^n c_i v_i = x$ $\quad \begin{color}{red}\text{Divide}\end{color}$
$\quad \begin{color}{red}\text{by 0?}\end{color}$

but $x$ cannot be a
linear comb. of $v_i$

so $c_{n+1}$ must be 0,
which means $v_1, \dots, v_n, x$
is a set of $n+1$ lin ind
vectors but $\dim V = n$
$\begin{color}{red}\text{Invoke}\end{color}$
$\begin{color}{red}\text{theorem?}\end{color}$
$\begin{color}{red}\text{or how}\end{color}$
$\begin{color}{red}\text{to prove?}\end{color}$

so there is no $\dim$, $x$ can
exist in independent of $v_1, \dots, v_n$

<!-- page 23 -->

5. Find non-zero $2 \times 2$ matrices $A, B$ such that $AB = 0$.

5) Let $A = \begin{bmatrix} 1 & 1 \\ 1 & 1 \end{bmatrix}$, $B = \begin{bmatrix} -1 & 1 \\ 1 & -1 \end{bmatrix}$

$AB = \begin{bmatrix} 1 & 1 \\ 1 & 1 \end{bmatrix} \begin{bmatrix} -1 & 1 \\ 1 & -1 \end{bmatrix} = \begin{bmatrix} -1+1 & 1-1 \\ -1+1 & 1-1 \end{bmatrix} = \begin{bmatrix} 0 & 0 \\ 0 & 0 \end{bmatrix}$

<!-- page 24 -->

6. Determine the rank of the following matrices:

(a) $\begin{pmatrix} 1 & 3 & 4 \\ 2 & 0 & 1 \end{pmatrix}$

(b) $\begin{pmatrix} 1 & 3 & 0 & 0 \\ 2 & 4 & 0 & -1 \\ 1 & -1 & 2 & 2 \end{pmatrix}$

(c) $\begin{pmatrix} 1 & -2 & -1 & 1 \\ 2 & 1 & 1 & 2 \\ -1 & 1 & -1 & -3 \\ -2 & -5 & -2 & 0 \end{pmatrix}$

---

a) $\begin{pmatrix} 1 & 3 & 4 \\ 2 & 0 & 1 \end{pmatrix} \xrightarrow{-2R_1} \begin{pmatrix} 1 & 3 & 4 \\ 0 & -6 & -7 \end{pmatrix} \quad \text{Rank } 2$

b) $\begin{pmatrix} 1 & 3 & 0 & 0 \\ 2 & 4 & 0 & -1 \\ 1 & -1 & 2 & 2 \end{pmatrix} \xrightarrow{-2R_1} \begin{pmatrix} 1 & 3 & 0 & 0 \\ 0 & -2 & 0 & -1 \\ 1 & -1 & 2 & 2 \end{pmatrix}$

$\xrightarrow{-R_1} \begin{pmatrix} 1 & 3 & 0 & 0 \\ 0 & -2 & 0 & -1 \\ 0 & -4 & 2 & 2 \end{pmatrix} \xrightarrow{-2R_2} \begin{pmatrix} 1 & 3 & 0 & 0 \\ 0 & -2 & 0 & -1 \\ 0 & 0 & 2 & 4 \end{pmatrix}$

$$\text{Rank } 3$$

<!-- page 25 -->

c) $\begin{pmatrix} 1 & -2 & -1 & 1 \\ 2 & 1 & 1 & 2 \\ -1 & 1 & -1 & -3 \\ -2 & -5 & -2 & 0 \end{pmatrix} \xrightarrow{-2R_1} \begin{pmatrix} 1 & -2 & -1 & 1 \\ 0 & 5 & 3 & 0 \\ -1 & 1 & -1 & -3 \\ -2 & -5 & -2 & 0 \end{pmatrix}$

$\xrightarrow{+R_1} \begin{pmatrix} 1 & -2 & -1 & 1 \\ 0 & 5 & 3 & 0 \\ 0 & -1 & -2 & -2 \\ -2 & -5 & -2 & 0 \end{pmatrix} \xrightarrow{+\frac{1}{5}R_2} \begin{pmatrix} 1 & -2 & -1 & 1 \\ 0 & 5 & 3 & 0 \\ 0 & 0 & -1\frac{2}{5} & -2 \\ -2 & -5 & -2 & 0 \end{pmatrix}$

$\xrightarrow{+2R_1} \begin{pmatrix} 1 & -2 & -1 & 1 \\ 0 & 5 & 3 & 0 \\ 0 & 0 & -7/5 & -2 \\ 0 & -9 & -4 & 2 \end{pmatrix} \xrightarrow{+\frac{9}{5}R_2} \begin{pmatrix} 1 & -2 & -1 & 1 \\ 0 & 5 & 3 & 0 \\ 0 & 0 & -7/5 & -2 \\ 0 & 0 & 7/5 & 2 \end{pmatrix}$

$$\frac{27}{5} = 5\frac{2}{5}$$

$\xrightarrow{+R_3} \begin{pmatrix} 1 & -2 & -1 & 1 \\ 0 & 5 & 3 & 0 \\ 0 & 0 & -7/5 & -2 \\ 0 & 0 & 0 & 0 \end{pmatrix}$

$$\text{Rank } 3$$

<!-- page 26 -->

7. Is it possible that the vectors $v_1, v_2, v_3$ are linearly dependent, but the vectors $v_1 + v_2, v_1 + v_3, v_2 + v_3$ are linearly independent?

Let $\{v_1, v_2, v_3\} = D$, a lin dep set
s.t. $\exists c_1, c_2, c_3 \in \mathbb{R}$ not all 0
$\quad c_1 v_1 + c_2 v_2 + c_3 v_3 = 0 \quad (*)$

Assume $D' = \{v_1 + v_2, v_1 + v_3, v_2 + v_3\}$
are lin. ind. s.t.
$c_1' (v_1 + v_2) + c_2' (v_1 + v_3) + c_3' (v_2 + v_3) = 0$
has only the trivial solution $c_1' = c_2' = c_3' = 0$

Then the following linear system cannot hold:

$\begin{color}{red}\text{Stuck}\end{color} \quad \begin{cases} d_1 (v_1 + v_2) = 0 \\ d_2 (v_1 + v_3) = 0 \\ d_3 (v_2 + v_3) = 0 \end{cases} \quad d_1, d_2, d_3 \in \mathbb{R} \text{ not all } 0$

but by $(*)$, $\exists c_1, c_2, c_3 \in \mathbb{R}$ not all 0
s.t. $c_1 v_1 + c_2 v_2 + c_3 v_3 = 0$
multiply both sides by 2
$2 c_1 v_1 + 2 c_2 v_2 + 2 c_3 v_3 = 0$
$c_1 v_1 + c_1 v_1 + c_2 v_2 + c_2 v_2 + c_3 v_3 + c_3 v_3 = 0$

<!-- page 27 -->

7. Is it possible that the vectors $v_1, v_2, v_3$ are linearly dependent, but the vectors $v_1 + v_2, v_1 + v_3, v_2 + v_3$ are linearly independent?

Let $\{v_1, v_2, v_3\} = D$, a lin dep set

s.t. $\exists c_1, c_2, c_3 \in \mathbb{R}$ not all $0$

$\quad d \quad c_1 v_1 + c_2 v_2 + c_3 v_3 = 0 \quad (*)$

To show possibility, w

<!-- page 28 -->

8. Let $X$ be an $n \times k$ real matrix. Define projection matrix $P := X(X^\top X)^{-1}X^\top$ and orthogonal matrix $M := I_n - P$. (You can assume $(X^\top X)^{-1}$ exists.)

   (a) Show that $P$ and $M$ are idempotent.
   (b) Show that $\operatorname{tr}(P) = k$, $\operatorname{tr}(M) = n - k$.

<!-- page 29 -->

9. State whether each of the following statements is true or false. If it is false, please provide a counterexample.

   (a) No system of linear equations can have exactly $k$ solutions for any $k \ge 2$.
   (b) If $Ax = 0$ has a solution, then $Ax = b$ has a solution;
   (c) If an $n \times n$ matrix $A$ is full rank, then $Ax = b$ has a solution;
   (d) If an $n \times n$ matrix $A$ has rank less than $n$, then $Ax = b$ has no solution;
   (e) If an $n \times n$ matrix $A$ is full rank, all its eigenvalues are distinct.
   (f) Every diagonal real matrix has real eigenvalues.
   (g) An $n \times n$ matrix $A$ has a zero eigenvalue if and only if it has rank less than $n$.

a) False, a linear system with free variables has infinite solutions.

Take $A = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 0 \end{bmatrix}$ and $b = \begin{bmatrix} 1 \\ 1 \\ 0 \end{bmatrix}$

$$Ax = b \implies \begin{bmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 0 \end{bmatrix} \begin{bmatrix} x_1 \\ x_2 \\ x_3 \end{bmatrix} = \begin{bmatrix} 1 \\ 1 \\ 0 \end{bmatrix}$$

$$\begin{aligned} x_1 &= 1 \\ x_2 &= 1 \\ x_3 &\quad \text{free} \end{aligned} \quad \text{has infinite solutions}$$

b) False,

$Ax = 0$ has the trivial solution $x = 0$, but for $b \neq 0$, $Ax = b$ is not guaranteed a solution

<!-- page 30 -->

9. State whether each of the following statements is true or false. If it is false, please provide a counterexample.

   (a) No system of linear equations can have exactly $k$ solutions for any $k \ge 2$.
   (b) If $Ax = 0$ has a solution, then $Ax = b$ has a solution;
   (c) If an $n \times n$ matrix $A$ is full rank, then $Ax = b$ has a solution;
   (d) If an $n \times n$ matrix $A$ has rank less than $n$, then $Ax = b$ has no solution;
   (e) If an $n \times n$ matrix $A$ is full rank, all its eigenvalues are distinct.
   (f) Every diagonal real matrix has real eigenvalues.
   (g) An $n \times n$ matrix $A$ has a zero eigenvalue if and only if it has rank less than $n$.

c) True, $\text{full rank} \implies \text{invertible}$
so $x = A^{-1} b$

d) False, let $A_{3 \times 3} = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 0 \end{bmatrix}$ with rank 2
$$2 < 3 = n$$

for $b = \begin{bmatrix} 1 \\ 1 \\ b_3 \end{bmatrix}$, $Ax = b$

$$\begin{bmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 0 \end{bmatrix} \begin{bmatrix} x_1 \\ x_2 \\ x_3 \end{bmatrix} = \begin{bmatrix} 1 \\ 1 \\ b_3 \end{bmatrix}$$

$$\begin{aligned} x_1 &= 1 \\ x_2 &= 1 \\ x_3 &= b_3 \end{aligned} \quad \text{has infinite solutions}$$

e) False, let $A = \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix}$, $\text{rank} = 2$

$$\det(A - \lambda I) = \det \begin{bmatrix} 1 - \lambda & 0 \\ 0 & 1 - \lambda \end{bmatrix} = (1 - \lambda)^2 = 0$$

$$\lambda_1 = \lambda_2 = 1$$

<!-- page 31 -->

9. State whether each of the following statements is true or false. If it is false, please provide a counterexample.

   (a) No system of linear equations can have exactly $k$ solutions for any $k \ge 2$.
   (b) If $Ax = 0$ has a solution, then $Ax = b$ has a solution;
   (c) If an $n \times n$ matrix $A$ is full rank, then $Ax = b$ has a solution;
   (d) If an $n \times n$ matrix $A$ has rank less than $n$, then $Ax = b$ has no solution;
   (e) If an $n \times n$ matrix $A$ is full rank, all its eigenvalues are distinct.
   (f) Every diagonal real matrix has real eigenvalues.
   (g) An $n \times n$ matrix $A$ has a zero eigenvalue if and only if it has rank less than $n$.

f) True, for diag matrices, eigenvalues are given by the diagonal entries. If all real, eigenvalues are real.

g) True, let $\lambda=0$ be an eigenvalue of $A$ & $v$ the eigenvector,

$$Av = \lambda v = 0v = 0 \quad \text{so} \quad v \in \operatorname{null}(A)$$

$$\det(A - \lambda I) = 0 \implies \det(A - 0) = \det(A) = 0$$

so $A$ singular, thus $\operatorname{rank}(A) < n$

<!-- page 32 -->

10. (a) Is the matrix
$$A = \begin{bmatrix} -1 & -2/3 \\ 3 & 5/3 \end{bmatrix}$$
diagonalizable in $\mathbb{C}$? Is it diagonalizable in $\mathbb{R}$? If so, diagonalize it, i.e. find a $2 \times 2$ invertible matrix $P$ such that $P^{-1}AP = \Lambda$, where $\Lambda$ is a diagonal matrix.
Consider a $2 \times 2$ real matrix as a vector in $\mathbb{R}^4$, and use $d_2$ on $\mathbb{R}^4$ to measure distance between two $2 \times 2$ real matrices. Find $\lim_{n \to \infty} A^n$.

(b) Is the matrix
$$A = \begin{bmatrix} 0 & 1 \\ -1 & 0 \end{bmatrix}$$
diagonalizable in $\mathbb{C}$? If so, diagonalize it.

<!-- page 33 -->

11. Let $(V, +, \cdot, \|\cdot\|)$ be a normed vector space, and $S_1$ and $S_2$ two subsets of $V$. Define

$$S_1 + S_2 := \{x \in V \mid x = x_1 + x_2, \ x_1 \in S_1, \ x_2 \in S_2\}.$$

Consider the distance induced by the norm.

(a) Assume $S_1$ and $S_2$ are bounded; is $S_1 + S_2$ bounded?
(b) Assume $S_1$ and $S_2$ are closed; is $S_1 + S_2$ closed?
(c) Assume $S_1$ and $S_2$ are compact; is $S_1 + S_2$ compact?

<!-- page 34 -->

12. Solve the following systems of linear equations (find all real solutions). Write the answers in the vector form.

(a)

$$\begin{cases} x_1 + 2x_2 - x_3 = -1 \\ 2x_1 + 2x_2 + x_3 = 1 \\ 3x_1 + 5x_2 - 2x_3 = -1 \end{cases}$$

(b)

$$\begin{cases} x_1 - 2x_2 - x_3 = 1 \\ 2x_1 - 3x_2 + x_3 = 6 \\ 3x_1 - 5x_2 = 7 \\ x_1 + 5x_3 = 9 \end{cases}$$

---

a) $A = \begin{bmatrix} 1 & 2 & -1 \\ 2 & 2 & 1 \\ 3 & 5 & -2 \end{bmatrix} \quad b = \begin{bmatrix} -1 \\ 1 \\ -1 \end{bmatrix}$

by GE

$$\begin{bmatrix} 1 & 2 & -1 & \mid & -1 \\ 2 & 2 & 1 & \mid & 1 \\ 3 & 5 & -2 & \mid & -1 \end{bmatrix} \xrightarrow{-2R_1} \begin{bmatrix} 1 & 2 & -1 & \mid & -1 \\ 0 & -2 & 3 & \mid & 3 \\ 3 & 5 & -2 & \mid & -1 \end{bmatrix}$$

$$\xrightarrow{-3R_1} \begin{bmatrix} 1 & 2 & -1 & \mid & -1 \\ 0 & -2 & 3 & \mid & 3 \\ 0 & -1 & 1 & \mid & 2 \end{bmatrix} \xrightarrow{-\frac{1}{2}R_2} \begin{bmatrix} 1 & 2 & -1 & \mid & -1 \\ 0 & -2 & 3 & \mid & 3 \\ 0 & 0 & -\frac{1}{2} & \mid & 1/2 \end{bmatrix}$$

$$\begin{aligned} x_1 + 2x_2 - x_3 &= -1 \\ -2x_2 + 3x_3 &= 3 \\ -\frac{1}{2} x_3 &= 1/2 \implies x_3 = -1 \end{aligned}$$

$$-2x_2 - 3 = 3 \implies -2x_2 = 6 \implies x_2 = -3$$

$$x_1 - 6 + 1 = -1 \implies x_1 = 4$$

$$X = \begin{bmatrix} 4 \\ -3 \\ -1 \end{bmatrix}$$

Check
$$\begin{aligned} x_1 + 2x_2 - x_3 &= -1 \implies 4 - 6 + 1 = -1 \\ 2x_1 + 2x_2 + x_3 &= 1 \implies 8 - 6 - 1 = 1 \\ 3x_1 + 5x_2 - 2x_3 &= -1 \implies 12 - 15 + 2 = -1 \end{aligned}$$

<!-- page 35 -->

12. Solve the following systems of linear equations (find all real solutions). Write the answers in the vector form.

(a)
$$\begin{cases} x_1 + 2x_2 - x_3 = -1 \\ 2x_1 + 2x_2 + x_3 = 1 \\ 3x_1 + 5x_2 - 2x_3 = -1 \end{cases}$$

(b)
$$\begin{cases} x_1 - 2x_2 - x_3 = 1 \\ 2x_1 - 3x_2 + x_3 = 6 \\ 3x_1 - 5x_2 = 7 \\ x_1 + 5x_3 = 9 \end{cases}$$

<!-- page 36 -->

12. Solve the following systems of linear equations (find all real solutions). Write the answers in the vector form.

(a)

$$\begin{cases} x_1 + 2x_2 - x_3 = -1 \\ 2x_1 + 2x_2 + x_3 = 1 \\ 3x_1 + 5x_2 - 2x_3 = -1 \end{cases}$$

(b)

$$\begin{cases} x_1 - 2x_2 - x_3 = 1 \\ 2x_1 - 3x_2 + x_3 = 6 \\ 3x_1 - 5x_2 = 7 \\ x_1 + 5x_3 = 9 \end{cases}$$

---

b) $x_1 = 9 - 5x_3$

$$3x_1 = 7 + 5x_2$$
$$x_1 = 7/3 + 5/3 x_2$$

$$9 - 5x_3 = 7/3 + 5/3 x_2$$
$$27 - 15x_3 - 7 = 5x_2$$
$$\frac{20 - 15x_3}{5} = x_2 = 4 - 3x_3$$

4 eq in 3 unkn
over determined,
free variable.

$$x = \begin{bmatrix} 9 - 5x_3 \\ 4 - 3x_3 \\ x_3 \end{bmatrix}$$

Part. sol.
let $x_3 = 1$

$$x_p = \begin{bmatrix} 4 \\ 1 \\ 1 \end{bmatrix}$$

Check

$$4 - 2 - 1 = 1$$
$$8 - 3 + 1 = 6$$
$$12 - 5 = 7$$
$$4 + 5 = 9$$

<!-- page 37 -->

(c)

$$\begin{cases} x_1 + 2x_2 + 2x_4 = 6 \\ 3x_1 + 5x_2 - x_3 + 6x_4 = 17 \\ 2x_1 + 4x_2 + x_3 + 2x_4 = 12 \\ 2x_1 - 7x_3 + 11x_4 = 7 \end{cases}$$

(d)

$$\begin{cases} x_1 - 4x_2 - x_3 + 3x_4 = 2 \\ 2x_1 - 8x_2 + x_3 - 4x_4 = 9 \\ -x_1 + 4x_2 - 2x_3 + 5x_4 = -6 \end{cases}$$

<!-- page 38 -->

13. For each of the matrices, check if it is diagonalizable over $\mathbb{C}$. Do the same over $\mathbb{R}$. If it is diagonalizable, then find invertible $P$ and diagonal $\Lambda$ so that $A = P\Lambda P^{-1}$. It may help to check your computation with your geometric understanding of eigenvalues and eigenvectors. Also, what is the definiteness of $A$ (equivalently, the quadratic form associated with $A$), e.g. positive definite, positive semidefinite, etc.?

(a) $A = \begin{pmatrix} 0 & 1 \\ -1/2 & 0 \end{pmatrix}$

(b) $A = \begin{pmatrix} 1 & -2 \\ 0 & 1 \end{pmatrix}$

(c) $A = \begin{pmatrix} -1 & 0 \\ 0 & 1 \end{pmatrix}$

(d) $A = \begin{pmatrix} 1/2 & 1/2 \\ 1/2 & 1/2 \end{pmatrix}$

For (d), please also compute $\lim_{n \to \infty} A^n$, the limit taken with respect to the $d_2$ metric (considering $A$ as an element of $\mathbb{R}^4$).