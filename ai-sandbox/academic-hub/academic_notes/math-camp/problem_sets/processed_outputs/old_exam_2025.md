<!-- page 1 -->

1. (15 points) Let $\mathcal{C}_{[0,1]} := \{f : [0,1] \to \mathbb{R} : f \text{ is continuous}\}$ and $d_\infty : \mathcal{C}_{[0,1]} \times \mathcal{C}_{[0,1]} \to \mathbb{R}_+$ be defined as
$$d_\infty(f,g) := \max_{t \in [0,1]} |f(t) - g(t)|.$$

(a) (2 pts) For $f,g,h : [0,1] \to \mathbb{R}$ with $f(x) = x$, $g(x) = x^2$ and $h(x) = 0.5x^2$, find $d_\infty(f,g)$ and $d_\infty(f,h)$.

(b) (3 pts) Argue that $d_\infty$ is a well-defined function. (Hint: You can use as fact that the absolute value is a continuous transformation.)

(c) (10 pts) Show that $(\mathcal{C}_{[0,1]}, d_\infty)$ is a metric space.

---

a)
i.) $d_\infty(f,g) = \max_{t \in [0,1]} |t - t^2|$
$= \max_{t \in [0,1]} t - t^2$

$t > t^2 \quad \text{for } (0,1)$

$t - t^2 > 0 \quad \text{for } (0,1)$

Let $j(t) = t - t^2$
$j'(t) = 1 - 2t = 0 \implies 1 = 2t$
$\text{s.t. } t = 1/2 \text{ crit. point}$
$j''(t) = -2 \text{ s.t. } t = 1/2 \text{ is argmax}$

Thus $d_\infty(f,g) = \max_{t \in [0,1]} |t - t^2| = |0.5 - 0.5^2| = 0.25$

ii) $d_\infty(f,h) = \max_{t \in [0,1]} |t - 0.5t^2|$

$\forall t \in [0,1]$
$t \ge 0.5t$
$t \ge 0.5t^2$
$t - 0.5t^2 \ge 0$

Let $h(t) = t - 0.5t^2$
$h'(t) = 1 - t = 0 \implies 1 - t = 0$
$t = 1 \text{ crit point}$
$h''(t) = -1 \implies t = 1 \text{ max}$

$d_\infty(f,h) = |1 - 0.5(1)^2| = 1 - 0.5 = 0.5$

<!-- page 2 -->

1. (15 points) Let $\mathcal{C}_{[0,1]} := \{f : [0,1] \to \mathbb{R} : f \text{ is continuous}\}$ and $d_\infty : \mathcal{C}_{[0,1]} \times \mathcal{C}_{[0,1]} \to \mathbb{R}_+$ be defined as
$$d_\infty(f,g) := \max_{t \in [0,1]} |f(t) - g(t)|.$$

(a) (2 pts) For $f,g,h : [0,1] \to \mathbb{R}$ with $f(x) = x$, $g(x) = x^2$ and $h(x) = 0.5x^2$, find $d_\infty(f,g)$ and $d_\infty(f,h)$.

(b) (3 pts) Argue that $d_\infty$ is a well-defined function. (Hint: You can use as fact that the absolute value is a continuous transformation.)

(c) (10 pts) Show that $(\mathcal{C}_{[0,1]}, d_\infty)$ is a metric space.

<!-- page 3 -->

1. (15 points) Let $\mathcal{C}_{[0,1]} := \{f : [0,1] \to \mathbb{R} : f \text{ is continuous}\}$ and $d_\infty : \mathcal{C}_{[0,1]} \times \mathcal{C}_{[0,1]} \to \mathbb{R}_+$ be defined as
$$d_\infty(f,g) := \max_{t \in [0,1]} |f(t) - g(t)|.$$

(a) (2 pts) For $f,g,h : [0,1] \to \mathbb{R}$ with $f(x) = x$, $g(x) = x^2$ and $h(x) = 0.5x^2$, find $d_\infty(f,g)$ and $d_\infty(f,h)$.

(b) (3 pts) Argue that $d_\infty$ is a well-defined function. (Hint: You can use as fact that the absolute value is a continuous transformation.)

(c) (10 pts) Show that $(\mathcal{C}_{[0,1]}, d_\infty)$ is a metric space.

b)

<!-- page 4 -->

1. (15 points) Let $\mathcal{C}_{[0,1]} := \{f : [0,1] \to \mathbb{R} : f \text{ is continuous}\}$ and $d_\infty : \mathcal{C}_{[0,1]} \times \mathcal{C}_{[0,1]} \to \mathbb{R}_+$ be defined as
$$d_\infty(f,g) := \max_{t \in [0,1]} |f(t) - g(t)|.$$

(a) (2 pts) For $f,g,h : [0,1] \to \mathbb{R}$ with $f(x) = x$, $g(x) = x^2$ and $h(x) = 0.5x^2$, find $d_\infty(f,g)$ and $d_\infty(f,h)$.

(b) (3 pts) Argue that $d_\infty$ is a well-defined function. (Hint: You can use as fact that the absolute value is a continuous transformation.)

(c) (10 pts) Show that $(\mathcal{C}_{[0,1]}, d_\infty)$ is a metric space.

c)

<!-- page 5 -->

2. (25 points) Let $\rho : \mathbb{R} \times \mathbb{R} \to \{0, 1\}$ be the discrete metric, i.e.
$$\rho(x,y) := \begin{cases} 1, & \text{if } x \neq y \\ 0, & \text{if } x = y \end{cases}$$

(a) (5 pts) Show that any singleton in $\mathbb{R}$ (i.e. any set made up of a single point $\{x\} \subset \mathbb{R}$) is open in $(\mathbb{R}, \rho)$.

(b) (5 pts) Show that any subset of $\mathbb{R}$ is open in $(\mathbb{R}, \rho)$.

(c) (5 pts) Show that any subset of $\mathbb{R}$ is closed in $(\mathbb{R}, \rho)$.

(d) (5 pts) Show that any subset of $\mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$.

(e) (5 pts) Show that $[0, 1]$ is not compact in $(\mathbb{R}, \rho)$.

(f) (**Bonus:** 5 pts) Show that the sequence $(1/n)$ does not converge to $0$ in $(\mathbb{R}, \rho)$.

---

a) For singleton $\{x\} \subset \mathbb{R}$ to be open in $(\mathbb{R}, \rho)$
it must not contain its limit points
under the metric $\rho$

since for any $y \neq x \in \mathbb{R}$, $\rho(x,y) = 1$,
$(B_\rho(x) \setminus \{x\}) \cap \mathbb{R} = \emptyset$

---

**Part (a): Any singleton $\{x\} \subset \mathbb{R}$ is open in $(\mathbb{R}, \rho)$**

* **Definition:** A set $U \subseteq \mathbb{R}$ is open in $(\mathbb{R}, \rho)$ if for every point $p \in U$, there exists a radius $r > 0$ such that the open ball $B_r(p) \subseteq U$, where:
$$B_r(p) = \{y \in \mathbb{R} : \rho(p,y) < r\}$$

* **Proof:**
Let $x \in \mathbb{R}$ be arbitrary and consider the singleton $\{x\}$.
Choose radius $r = \frac{1}{2}$ (or any $r \in (0,1]$).
The open ball of radius $\frac{1}{2}$ centered at $x$ is:
$$B_{1/2}(x) = \{y \in \mathbb{R} : \rho(x,y) < 1/2\}$$

Under the discrete metric, $\rho(x,y) \in \{0, 1\}$ for all $y$. Thus:
$$\rho(x,y) < 1/2 \iff \rho(x,y) = 0 \iff y = x$$

Therefore:
$$B_{1/2}(x) = \{x\} \subseteq \{x\}$$

Since $\{x\}$ contains an open ball around its only element, $\{x\}$ is an open set in $(\mathbb{R}, \rho)$.

<!-- page 6 -->

2. (25 points) Let $\rho : \mathbb{R} \times \mathbb{R} \to \{0,1\}$ be the discrete metric, i.e.
$$\rho(x,y) := \begin{cases} 1, & \text{if } x \neq y \\ 0, & \text{if } x = y \end{cases}$$

(a) (5 pts) Show that any singleton in $\mathbb{R}$ (i.e. any set made up of a single point $\{x\} \subset \mathbb{R}$) is open in $(\mathbb{R}, \rho)$.

(b) (5 pts) Show that any subset of $\mathbb{R}$ is open in $(\mathbb{R}, \rho)$.

(c) (5 pts) Show that any subset of $\mathbb{R}$ is closed in $(\mathbb{R}, \rho)$.

(d) (5 pts) Show that any subset of $\mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$.

(e) (5 pts) Show that $[0, 1]$ is not compact in $(\mathbb{R}, \rho)$.

(f) (**Bonus:** 5 pts) Show that the sequence $(1/n)$ does not converge to $0$ in $(\mathbb{R}, \rho)$.

---

**Part (b): Any subset of $\mathbb{R}$ is open in $(\mathbb{R}, \rho)$**

* **Proof:**
Let $A \subseteq \mathbb{R}$ be an arbitrary subset.

* If $A = \emptyset$, the empty set is open by the topological axioms.

* If $A \neq \emptyset$, express $A$ as the union of its individual elements:
$$A = \bigcup_{x \in A} \{x\}$$

* By Part (a), each singleton $\{x\}$ is an open set in $(\mathbb{R}, \rho)$.

* Because the arbitrary union of open sets is open, the union $\bigcup_{x \in A} \{x\} = A$ is open in $(\mathbb{R}, \rho)$.

*(Direct Ball Alternative)*: For any $x \in A$, choose $r = \frac{1}{2}$. Then $B_{1/2}(x) = \{x\} \subseteq A$, proving that every point of $A$ is an interior point.

<!-- page 7 -->

2. (25 points) Let $\rho : \mathbb{R} \times \mathbb{R} \to \{0,1\}$ be the discrete metric, i.e.
$$\rho(x,y) := \begin{cases} 1, & \text{if } x \neq y \\ 0, & \text{if } x = y \end{cases}$$

(a) (5 pts) Show that any singleton in $\mathbb{R}$ (i.e. any set made up of a single point $\{x\} \subset \mathbb{R}$) is open in $(\mathbb{R}, \rho)$.

(b) (5 pts) Show that any subset of $\mathbb{R}$ is open in $(\mathbb{R}, \rho)$.

(c) (5 pts) Show that any subset of $\mathbb{R}$ is closed in $(\mathbb{R}, \rho)$.

(d) (5 pts) Show that any subset of $\mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$.

(e) (5 pts) Show that $[0, 1]$ is not compact in $(\mathbb{R}, \rho)$.

(f) (**Bonus:** 5 pts) Show that the sequence $(1/n)$ does not converge to $0$ in $(\mathbb{R}, \rho)$.

---

**Part (c): Any subset of $\mathbb{R}$ is closed in $(\mathbb{R}, \rho)$**

* **Proof:**
Let $A \subseteq \mathbb{R}$ be an arbitrary subset.

* By definition, $A$ is closed in $(\mathbb{R}, \rho)$ if and only if its complement $A^c = \mathbb{R} \setminus A$ is open in $(\mathbb{R}, \rho)$.

* The complement $A^c$ is itself a subset of $\mathbb{R}$.

* By Part (b), **every** subset of $\mathbb{R}$ is open in $(\mathbb{R}, \rho)$, which implies $A^c$ is open.

* Since $A^c$ is open, its complement $(A^c)^c = A$ is closed in $(\mathbb{R}, \rho)$.

<!-- page 8 -->

2. (25 points) Let $\rho : \mathbb{R} \times \mathbb{R} \to \{0,1\}$ be the discrete metric, i.e.
$$\rho(x,y) := \begin{cases} 1, & \text{if } x \neq y \\ 0, & \text{if } x = y \end{cases}$$

(a) (5 pts) Show that any singleton in $\mathbb{R}$ (i.e. any set made up of a single point $\{x\} \subset \mathbb{R}$) is open in $(\mathbb{R}, \rho)$.

(b) (5 pts) Show that any subset of $\mathbb{R}$ is open in $(\mathbb{R}, \rho)$.

(c) (5 pts) Show that any subset of $\mathbb{R}$ is closed in $(\mathbb{R}, \rho)$.

(d) (5 pts) Show that any subset of $\mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$.

(e) (5 pts) Show that $[0, 1]$ is not compact in $(\mathbb{R}, \rho)$.

(f) (**Bonus:** 5 pts) Show that the sequence $(1/n)$ does not converge to $0$ in $(\mathbb{R}, \rho)$.

---

**Part (d): Show that any subset of $\mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$**

* **Definition:** A set $S \subseteq \mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$ if its diameter is finite, or equivalently, if there exists a point $x_0 \in \mathbb{R}$ and a radius $M > 0$ such that $S \subseteq B_M(x_0)$.

* **Proof:**
Let $S \subseteq \mathbb{R}$ be an arbitrary subset.

  * If $S = \emptyset$, it is trivially bounded.

  * If $S \neq \emptyset$, choose any fixed point $x_0 \in S$.

  * By definition of the discrete metric, for every $x \in S$:
$$\rho(x, x_0) \le 1 < 2$$

  * Thus, $S \subseteq B_2(x_0) = \{x \in \mathbb{R} : \rho(x, x_0) < 2\} = \mathbb{R}$.

  * Furthermore, the diameter satisfies $\text{diam}(S) = \sup_{x,y \in S} \rho(x, y) \le 1 < \infty$.

  * Therefore, every subset of $\mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$.

<!-- page 9 -->

2. (25 points) Let $\rho : \mathbb{R} \times \mathbb{R} \to \{0, 1\}$ be the discrete metric, i.e.
$$\rho(x,y) := \begin{cases} 1, & \text{if } x \neq y \\ 0, & \text{if } x = y \end{cases}$$

(a) (5 pts) Show that any singleton in $\mathbb{R}$ (i.e. any set made up of a single point $\{x\} \subset \mathbb{R}$) is open in $(\mathbb{R}, \rho)$.

(b) (5 pts) Show that any subset of $\mathbb{R}$ is open in $(\mathbb{R}, \rho)$.

(c) (5 pts) Show that any subset of $\mathbb{R}$ is closed in $(\mathbb{R}, \rho)$.

(d) (5 pts) Show that any subset of $\mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$.

(e) (5 pts) Show that $[0, 1]$ is not compact in $(\mathbb{R}, \rho)$.

(f) (**Bonus:** 5 pts) Show that the sequence $(1/n)$ does not converge to $0$ in $(\mathbb{R}, \rho)$.

---

**Part (e): Show that $[0, 1]$ is not compact in $(\mathbb{R}, \rho)$**

* **Proof via Open Cover:**

  * By Part (a), every singleton $\{x\}$ is an open set in $(\mathbb{R}, \rho)$.

  * Consider the collection of open singletons:
$$\mathcal{U} = \{\{x\} : x \in [0, 1]\}$$

  * $\mathcal{U}$ is an open cover of $[0, 1]$ since $[0, 1] \subseteq \bigcup_{x \in [0,1]} \{x\}$.

  * Any finite subcollection $\{\{x_1\}, \{x_2\}, \dots, \{x_k\}\}$ covers only a finite number of points $\{x_1, \dots, x_k\}$, whereas the interval $[0, 1]$ is uncountable (infinite).

  * Thus, no finite subcollection of $\mathcal{U}$ can cover $[0, 1]$, proving that $[0, 1]$ is not compact in $(\mathbb{R}, \rho)$.

* **Alternative Proof via Sequences:**

  * Consider the sequence $x_n = \frac{1}{n+1} \in [0, 1]$ for $n \in \mathbb{N}$.

  * For any $n \neq m, x_n \neq x_m \implies \rho(x_n, x_m) = 1$.

  * No subsequence $(x_{n_k})$ can be Cauchy (since $\rho(x_{n_j}, x_{n_k}) = 1$ for all $j \neq k$), so no subsequence converges. Hence, $[0, 1]$ is not sequentially compact.

<!-- page 10 -->

2. (25 points) Let $\rho : \mathbb{R} \times \mathbb{R} \to \{0,1\}$ be the discrete metric, i.e.
$$\rho(x,y) := \begin{cases} 1, & \text{if } x \neq y \\ 0, & \text{if } x = y \end{cases}$$

(a) (5 pts) Show that any singleton in $\mathbb{R}$ (i.e. any set made up of a single point $\{x\} \subset \mathbb{R}$) is open in $(\mathbb{R}, \rho)$.

(b) (5 pts) Show that any subset of $\mathbb{R}$ is open in $(\mathbb{R}, \rho)$.

(c) (5 pts) Show that any subset of $\mathbb{R}$ is closed in $(\mathbb{R}, \rho)$.

(d) (5 pts) Show that any subset of $\mathbb{R}$ is bounded in $(\mathbb{R}, \rho)$.

(e) (5 pts) Show that $[0, 1]$ is not compact in $(\mathbb{R}, \rho)$.

(f) (**Bonus:** 5 pts) Show that the sequence $(1/n)$ does not converge to $0$ in $(\mathbb{R}, \rho)$.

---

### Part (f): Show that the sequence $(1/n)_{n=1}^\infty$ does not converge to $0$ in $(\mathbb{R}, \rho)$

* **Definition of Convergence:** The sequence $(1/n)$ converges to $0$ in $(\mathbb{R}, \rho)$ if and only if:
$$\forall \varepsilon > 0, \exists N \in \mathbb{N} \quad \text{such that} \quad \forall n \ge N, \rho\left(\frac{1}{n}, 0\right) < \varepsilon$$

* **Proof:**

  * Choose $\varepsilon = \frac{1}{2}$ (or any $\varepsilon \in (0, 1]$).

  * For every $n \in \mathbb{N}$, $1/n > 0$, so $1/n \neq 0$.

  * Under the discrete metric:
$$\rho\left(\frac{1}{n}, 0\right) = 1 \quad \forall n \in \mathbb{N}$$

  * Therefore, for every $n \in \mathbb{N}$:
$$\rho\left(\frac{1}{n}, 0\right) = 1 \nless \frac{1}{2}$$

  * No such index $N \in \mathbb{N}$ exists, meaning $(1/n)_{n=1}^\infty$ does not converge to $0$ in $(\mathbb{R}, \rho)$.

*(Note: In a discrete metric space, a sequence converges if and only if it is eventually constant).*

<!-- page 11 -->

3. (15 points) Define $\mathbf{1}_n \in \mathbb{R}^n$ as a column vector of size $n$ full of ones, i.e. $\mathbf{1}_n := (1, 1, \dots, 1)$. Now define $\mathbf{S}_n := \mathbf{1}_n \mathbf{1}_n^T$, for any $n \in \mathbb{N}$.

(a) (3 pts) Find the eigenvalues of $\mathbf{S}_2$ and $\mathbf{S}_3$.
(b) (7 pts) Find $\sigma(\mathbf{S}_n)$ for $n > 3$. (Hint: Find a pattern from your answer to part (a), and use row operations that preserve determinant.)
(c) (5 pts) In general, is $\mathbf{S}_n$ diagonalizable in $\mathbb{R}$? If so, propose a spectral decomposition; that is, find an invertible matrix $P$ and diagonal matrix $D$ such that $A = PDP^{-1}$. (Note: You do *not* have to compute $P^{-1}$.)

Next, a bonus question about vectors unrelated to (a)-(c):

(d) (**Bonus:** 5 pts) If $\boldsymbol{v}_1, \boldsymbol{v}_2, \boldsymbol{v}_3$ are L.I. non-zero vectors in some vector space $(V, +, \cdot)$, is $\{\boldsymbol{v}_1, 2\boldsymbol{v}_1 + \boldsymbol{v}_3, 4\boldsymbol{v}_2 + 2\boldsymbol{v}_3\}$ a basis of $span(\boldsymbol{v}_1, \boldsymbol{v}_2, \boldsymbol{v}_3)$?

<!-- page 12 -->

4. (10 points) Define $f : \mathbb{R}^3 \to \mathbb{R}^2$, $g : \mathbb{R}^2 \to \mathbb{R}^2$ and $h : \mathbb{R}^2 \to \mathbb{R}$ with

$$f(u_1, u_2, u_3) = \begin{bmatrix} \ln(u_1 + u_2^2 + u_3^3) \\ u_1^2 \end{bmatrix}, \quad g(v_1, v_2) = \begin{bmatrix} e^{v_1} \\ \sqrt{v_2} \end{bmatrix}, \quad h(w_1, w_2) = w_1^2 - w_2^2.$$

(a) (2 pts) Compute the Jacobian matrices of $f$, $g$ and $h$.
(b) (3 pts) Compute the partial derivatives:

$$\frac{\partial h \circ g \circ f}{\partial u_i}$$

for $i = 1, 2, 3$.
(c) (5 pts) Approximate the value of $h \circ g \circ f(1.1, 1.9, -0.8)$ using a first order Taylor approximation. (Hint: Use $(1,2,-1)$ as reference point.)
(d) (**Bonus:** 5 pts) Approximate the value of $h \circ g \circ f(1.1, 1.9, -0.8)$ using a second order Taylor approximation.

<!-- page 13 -->

5. (15 points) Find the maximizers of the following problem:

$$\max_{(x,y,z) \in \mathbb{R}^3} f(x,y,z) = -x^2 + 2x - y^2 + 4y - z^2 + 6z \quad \text{subject to} \quad x \le 2, y + 2z \ge 12.$$

<!-- page 14 -->

6. (20 points) Let $(X, d_X), (Y, d_Y)$ be metric spaces. We say $F : \mathbb{R} \rightrightarrows Y$ has a compact graph iff the graph of $F$ is a compact set in metric space $(X \times Y, d_{X \times Y})$ where

$$d_{X \times Y}((x, y), (x', y')) := \sqrt{d_X(x, x')^2 + d_Y(y, y')^2}$$

Use as given the fact that $x_n$ converges to $x$ in $(X, d_X)$ and $y_n$ converges to $y$ in $(Y, d_Y)$ if and only if $(x_n, y_n)$ converges to $(x, y)$ in $(X \times Y, d_{X \times Y})$

(a) (5 pts) Show that if $F$ has a compact graph then $F$ is compact-valued.
(b) (5 pts) Show that the converse may not hold, i.e. $F$ maybe compact-valued but still not have a compact graph.
(c) (5 pts) Show that if $F$ has a compact graph then $F$ is locally bounded at any $x_0 \in X$.
(d) (5 pts) If $F$ has a compact graph, is it true that $F$ would be uhc? Explain.