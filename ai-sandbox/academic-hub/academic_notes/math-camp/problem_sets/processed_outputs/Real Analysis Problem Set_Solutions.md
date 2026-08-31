---
source_pdf: Real Analysis Problem Set_Solutions.pdf
folder_category: problem_sets
total_pages: 44
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [real-analysis, optimization]
---

<!-- page 1 -->

Real Analysis Problem Set
Wednesday, August 19, 2026 8:14 PM

# Analysis: Guided Exercises

### Instructions

This problem set develops the main ideas of topology, continuity, and multivariate differential calculus that will be used throughout graduate economics.

Several problems contain guided steps or hints. These are part of the learning process. You should write a complete argument rather than simply answering the individual prompts.

Unless otherwise stated, all norms are Euclidean norms.

## 1 Topology and Continuity in $\mathbb{R}^n$

**Problem 1. Norms and the topology of $\mathbb{R}^n$**

For $x = (x_1, \dots, x_n) \in \mathbb{R}^n$, define

$$\|x\|_2 = \left( \sum_{i=1}^n x_i^2 \right)^{1/2}, \quad \|x\|_\infty = \max_{1 \le i \le n} |x_i|.$$

(a) Prove that

$$\|x\|_\infty \le \|x\|_2 \le \sqrt{n} \|x\|_\infty.$$

(b) Deduce that, for a sequence $\{x_k\} \subseteq \mathbb{R}^n$,

$$\|x_k - x\|_2 \to 0 \iff \|x_k - x\|_\infty \to 0.$$

(c) Show that the two norms generate the same open sets.

*Guidance. For part (c), compare balls. Given $r > 0$, find $r_1, r_2 > 0$ such that*
$$B_{r_1, \|\cdot\|_\infty}(x) \subseteq B_{r, \|\cdot\|_2}(x), \quad B_{r_2, \|\cdot\|_2}(x) \subseteq B_{r, \|\cdot\|_\infty}(x).$$

---

a) For $x = (x_1, \dots, x_n) \in \mathbb{R}^n$

$\|x\|_\infty = \max_{1 \le i \le n} |x_i| = x_m$ scalar

defined as $x_m = |x_j|$

s.t. $|x_j| \ge |x_1|, \dots, |x_j| \ge |x_i|, \dots, |x_j| \ge |x_n|$
including $i = j$

thus $\sum_{i=1}^n |x_i| \ge |x_j| = x_m = \|x\|_\infty$

since $\sum_{i=1}^n |x_i| = \sum_{i=1}^{j-1} |x_i| + |x_j| + \sum_{i=j+1}^n |x_i|$
s.t.

& $\sum_{i=1}^n |x_i| \ge 0$ by def of abs val

thus $\sum_{i=1}^n |x_i| \ge \sum_{i=1}^{j-1} |x_i| + \sum_{i=j+1}^n |x_i| \ge |x_j| \ge 0$

Since $\|x\|_2 = \left(\sum_{i=1}^n x_i^2\right)^{1/2} = (x_1^2 + \dots + x_n^2)^{1/2}$

$x_1^2 \ge 0, \dots, x_n^2 \ge 0$ s.t. $x_1^2 + \dots + x_n^2 \ge 0$

& $x_i^2 = |x_i|^2 \ge 0 \quad \forall x_i$

thus $\sum_{i=1}^n x_i^2 = |x_j|^2 + \sum_{i=1}^{j-1} |x_i|^2 + \sum_{i=j+1}^n |x_i|^2 \ge |x_j|^2$

apply sq root to both sides

$$\left(\sum_{i=1}^n x_i^2\right)^{1/2} \ge \left(|x_j|^2\right)^{1/2}$$

$(1 \text{ & } 2) \quad \|x\|_2 \ge |x_j| = \|x\|_\infty$

to show $\|x\|_2 \le \sqrt{n} \|x\|_\infty$:

$|x_i| \le \|x\|_\infty = \max(|x_i|)$ by def

$|x_i|^2 = x_i^2 \le \|x\|_\infty^2$

Summing over $n$, since true for all $x_i$
$\sum_{i=1}^n x_i^2 \le \sum_{i=1}^n \|x\|_\infty^2 = n \|x\|_\infty^2$

Real_Analysis_PS Page 1

<!-- page 2 -->

Real_Analysis_PS Page 2

<!-- page 3 -->

Summing over $n$, since true for all $x_i$
$$\sum_{i=1}^n x_i^2 \le \sum_{i=1}^n \|x\|_\infty^2 = n \|x\|_\infty^2$$
since $\|x\|_\infty$ not indexed by $i$

sq.rt. both sides
$$(2a2) \left(\sum_{i=1}^n x_i^2\right)^{1/2} = \|x\|_2 \le \sqrt{n} \|x\|_\infty$$

thus, combining $1a1 + 1a2$
$$\|x\|_\infty \le \|x\|_2 \le \sqrt{n} \|x\|_\infty$$

---

**Problem 1. Norms and the topology of $\mathbb{R}^n$**
For $x = (x_1, \dots, x_n) \in \mathbb{R}^n$, define
$$\|x\|_2 = \left( \sum_{i=1}^n x_i^2 \right)^{1/2}, \quad \|x\|_\infty = \max_{1 \le i \le n} |x_i|.$$
(a) Prove that
$$\|x\|_\infty \le \|x\|_2 \le \sqrt{n} \|x\|_\infty.$$
(b) Deduce that, for a sequence $\{x_k\} \subseteq \mathbb{R}^n$,
$$\|x_k - x\|_2 \to 0 \iff \|x_k - x\|_\infty \to 0.$$

---

for seq. $(x_k) \subseteq \mathbb{R}^n$

$\implies) \|x_k - x\|_2 \to 0 \implies \|x_k - x\|_\infty \to 0$

$$x_k = (x_{k1}, \dots, x_{kn})$$
$$x = (x_1, \dots, x_n)$$

define $y_k = (x_{k1} - x_1, \dots, x_{kn} - x_n)$

from a), $\|x\|_\infty \le \|x\|_2 \le \sqrt{n} \|x\|_\infty$

so $\|y_k\|_\infty \le \|y_k\|_2 \le \sqrt{n} \|y_k\|_\infty$

from a) $0 \le \|x\|_\infty \quad \forall x \in \mathbb{R}^n$
thus $0 \le \|y_k\|_\infty \le \|y_k\|_2$

$\therefore 0 \le \|x_k - x\|_\infty \le \|x_k - x\|_2$

in limit, $\lim_{k \to \infty} \|x_k - x\|_2 \to 0$

$$\implies 0 \le \lim_{k \to \infty} \|x_k - x\|_\infty \le 0$$

thus $\lim_{k \to \infty} \|x_k - x\|_\infty = 0$

$\impliedby)$ if $\|x_k - x\|_\infty \to 0$ as $k \to \infty$

from a) $0 \le \|x_k - x\|_2 \le \sqrt{n} \|x_k - x\|_\infty$

in limit,
$$\lim_{k \to \infty} \sqrt{n} \|x_k - x\|_\infty \ge \lim_{k \to \infty} \|x_k - x\|_\infty$$

$$\lim_{k \to \infty} \|x_k - x\|_\infty = 0 \implies \lim_{k \to \infty} \sqrt{n} \|x_k - x\|_\infty = 0$$

$$\lim_{k \to \infty} \|x_k - x\|_\infty \le \lim_{k \to \infty} \|x_k - x\|_2 \le \lim_{k \to \infty} \sqrt{n} \|x_k - x\|_\infty$$

$$0 \le \lim_{k \to \infty} \|x_k - x\|_2 \le 0$$

$$\implies \lim_{k \to \infty} \|x_k - x\|_2 = 0$$

Real_Analysis_PS Page 3

<!-- page 4 -->

Real_Analysis_PS Page 4

<!-- page 5 -->

$$0 \le \lim_{k \to \infty} \|x_k - x\|_2 \le 0$$

$$\implies \lim_{k \to \infty} \|x_k - x\|_2 = 0$$

Thus, $\|x_k - x\|_2 \to 0 \iff \|x_k - x\|_\infty \to 0$$

---

(c) Show that the two norms generate the same open sets.

*Guidance. For part (c), compare balls. Given $r > 0$, find $r_1, r_2 > 0$ such that*
$$B_{r_1, \|\cdot\|_\infty}(x) \subseteq B_{r, \|\cdot\|_2}(x), \quad B_{r_2, \|\cdot\|_2}(x) \subseteq B_{r, \|\cdot\|_\infty}(x)$$

---

For $r \in \mathbb{R} : r > 0$,

let $B_{\infty, r}(x) = \{ y \in \mathbb{R}^n : \|y - x\|_\infty < r \}$

$B_{2, r}(x) = \{ y \in \mathbb{R}^n : \|y - x\|_2 < r \}$

From a) $\|y - x\|_\infty \le \|y - x\|_2 \le \sqrt{n} \|y - x\|_\infty$

To show: $B_{\infty, r_1}(x) \subseteq B_{2, r}(x)$

if $y \in B_{\infty, r_1}(x)$, then $\|y - x\|_\infty < r_1$

$\|y - x\|_2 \le \sqrt{n} \|y - x\|_\infty < \sqrt{n} r_1$

pick $r_1 = \frac{r}{\sqrt{n}}$

$\|y - x\|_2 < \sqrt{n} r_1 = \sqrt{n} \frac{r}{\sqrt{n}} = r$

thus $y \in B_{2, r}(x)$

To show: $B_{2, r_2}(x) \subseteq B_{\infty, r}(x)$

if $y \in B_{2, r_2}(x)$, then $\|y - x\|_2 < r_2$

$\|y - x\|_\infty \le \|y - x\|_2 < r_2$

pick $r_2 = r$

$\|y - x\|_\infty < r$

thus $y \in B_{\infty, r}(x)$

---

> **Finding the Radii $r_1$ and $r_2$ for Part (c)**
> 
> Using the norm equivalence from part (a), $\|y - x\|_\infty \le \|y - x\|_2 \le \sqrt{n} \|y - x\|_\infty$:
> 
> * **Inclusion 1: $B_{\infty, r_1}(x) \subseteq B_{2, r}(x)$**
>   * If $y \in B_{\infty, r_1}(x)$, then $\|y - x\|_\infty < r_1$.
>   * By part (a): $\|y - x\|_2 \le \sqrt{n} \|y - x\|_\infty < \sqrt{n} r_1$.
>   * Setting $\sqrt{n} r_1 = r \implies r_1 = \frac{r}{\sqrt{n}}$ ensures $\|y - x\|_2 < r$, so $y \in B_{2, r}(x)$.
> 
> * **Inclusion 2: $B_{2, r_2}(x) \subseteq B_{\infty, r}(x)$**
>   * If $y \in B_{2, r_2}(x)$, then $\|y - x\|_2 < r_2$.
>   * By part (a): $\|y - x\|_\infty \le \|y - x\|_2 < r_2$.
>   * Setting $r_2 = r$ ensures $\|y - x\|_\infty < r$, so $y \in B_{\infty, r}(x)$.

---

An **open set** and a **closed set** in Euclidean space $\mathbb{R}^n$ are formally defined through neighborhoods (open balls) and complementation, respectively:

1. **Open Set**
   * **Definition:** A set $U \subseteq \mathbb{R}^n$ is **open** if for every point $x \in U$, there exists an $r > 0$ such that the open ball centered at $x$ is contained entirely within $U$:
     $$B_r(x) = \{ y \in \mathbb{R}^n \mid \|y - x\| < r \} \subseteq U$$
   * **Intuition:** Every point in the set has an "envelope" of surrounding space that also belongs to the set, meaning the set contains none of its boundary points.
   * **Examples:**
     * Open intervals $(a, b) \subseteq \mathbb{R}$
     * Open half-spaces $\{ x \in \mathbb{R}^n \mid a^T x < b \}$
     * The interior of an open ball $\{ x \in \mathbb{R}^n \mid \|x - x_0\| < r \}$

2. **Closed Set**
   * **Primary Definition (via Complement):** A set $F \subseteq \mathbb{R}^n$ is **closed** if its complement $F^c = \mathbb{R}^n \setminus F$ is an **open set**.
   * **Equivalent Sequence Characterization:** A set $F$ is closed if and only if it contains all of its limit points. That is, for any sequence $(x_k) \subseteq F$ such that $\lim x_k = x$, the limit satisfies $x \in F$.
   * **Intuition:** The set includes all of its boundary points $\partial F$.
   * **Examples:**
     * Closed intervals $[a, b] \subseteq \mathbb{R}$
     * Closed half-spaces $\{ x \in \mathbb{R}^n \mid a^T x \le b \}$
     * The closed Euclidean ball $\{ x \in \mathbb{R}^n \mid \|x\| \le r \}$

**Key Topological Distinctions**
* **Not Mutually Exclusive:** "Open" and "closed" are not opposite binary states. A set can be:
  * **Both open and closed ("Clopen"):** $\emptyset$ and the whole space $\mathbb{R}^n$.
  * **Neither open nor closed:** Half-open intervals like $[a, b) \subseteq \mathbb{R}$.
* **Continuous Function Characterization:** For a continuous function $f : \mathbb{R}^n \to \mathbb{R}$:
  * The strict sublevel/superlevel set $\{ x \mid f(x) < a \}$ is open.
  * The weak sublevel/superlevel set (such as the upper contour set $U_a = \{ x \mid f(x) \ge a \}$) is closed.

From `<https://gemini.google.com/app/264b755bb013b5de>`

---

**Problem 2. Continuous functions and open or closed sets**

Let $f : \mathbb{R}^n \to \mathbb{R}$ be continuous.

(a) Prove that $\{x \in \mathbb{R}^n : f(x) > c\}$ is open.

To show: Let $S = \{ x \in \mathbb{R}^n : f(x) > c \}, c \in \mathbb{R}$

$\forall x_0 \in S \quad \exists B_\delta(x_0) \subseteq S \quad s.t. f(B_\delta(x_0)) > c$

for any $x_0 \in S$, take $f(x_0)$

$f(x_0) > c$ by def of $S$

let $\epsilon = f(x_0) - c$

$f(x_0) > c \implies f(x_0) - c > 0$

Since $f$ cont at $x_0$, for $\epsilon > 0$,

$\exists \delta > 0$ s.t.

$\forall x \in \mathbb{R}^n$

$\|x - x_0\| < \delta \implies |f(x) - f(x_0)| < \epsilon$

$-\epsilon < f(x) - f(x_0) < \epsilon$

$-(f(x_0) - c) < f(x) - f(x_0) < f(x_0) - c$

---

> **Formal Proof Using the Open Ball Definition**
> Let $S = \{x \in \mathbb{R}^n : f(x) > c\}$. To show that $S$ is open, we must show that for every $x_0 \in S$, there exists an open ball $B_\delta(x_0) \subseteq S$.
> 
> 1. **Choose an arbitrary point:**
>    Let $x_0 \in S$. By definition of the set $S$, $f(x_0) > c$.
> 2. **Define an $\epsilon$-neighborhood in $\mathbb{R}$:**
>    Let $\epsilon = f(x_0) - c$. Since $f(x_0) > c$, we have $\epsilon > 0$.
> 3. **Apply the $(\epsilon, \delta)$-definition of continuity:**
>    Since $f : \mathbb{R}^n \to \mathbb{R}$ is continuous at $x_0$, for this chosen $\epsilon > 0$, there exists a $\delta > 0$ such that for all $x \in \mathbb{R}^n$:
>    $$\|x - x_0\| < \delta \implies |f(x) - f(x_0)| < \epsilon$$
> 4. **Expand the inequality:**
>    The condition $|f(x) - f(x_0)| < \epsilon$ is equivalent to:
>    $$-\epsilon < f(x) - f(x_0) < \epsilon \iff f(x_0) - \epsilon < f(x) < f(x_0) + \epsilon$$
> 5. **Substitute $\epsilon = f(x_0) - c$:**
>    Focusing on the lower bound:
>    $$f(x) > f(x_0) - \epsilon = f(x_0) - (f(x_0) - c) = c$$
> 6. **Establish the subset inclusion:**
>    Thus, for every $x \in B_\delta(x_0) = \{x \in \mathbb{R}^n : \|x - x_0\| < \delta\}$, we have $f(x) > c$, which implies $x \in S$.
>    Therefore, $B_\delta(x_0) \subseteq S$. Since $x_0$ was arbitrary, $S$ is open. $\blacksquare$
> 
> **Alternative Topological Approach (Preimage)**
> In general topology, this is also shown in one step using the topological definition of continuity (the preimage of every open set is open):
> $$S = \{x \in \mathbb{R}^n : f(x) > c\} = f^{-1}((c, \infty))$$
> Since the interval $(c, \infty)$ is an open set in $\mathbb{R}$ and $f$ is continuous, its preimage $f^{-1}((c, \infty))$ is open in $\mathbb{R}^n$.

From `<https://gemini.google.com/app/264b755bb013b5de>`

---

> **Part (a)**
> Let $f : \mathbb{R}^n \to \mathbb{R}$ be continuous and fix $c \in \mathbb{R}$.
> Recall the topological characterization of continuity: a function $f : \mathbb{R}^n \to \mathbb{R}$ is continuous if and only if the preimage $f^{-1}(U)$ of every open set $U \subseteq \mathbb{R}$ is open in $\mathbb{R}^n$.
> The interval $(c, \infty)$ is an open subset of $\mathbb{R}$. Expressing the set as a preimage gives:
> $$\{x \in \mathbb{R}^n : f(x) > c\} = f^{-1}((c, \infty))$$
> Because $(c, \infty)$ is open in $\mathbb{R}$ and $f$ is continuous, the preimage $f^{-1}((c, \infty))$ is open in $\mathbb{R}^n$.

<!-- page 6 -->

Real_Analysis_PS Page 6

<!-- page 7 -->

$-(f(x_0) - c) < f(x) - f(x_0) < f(x_0) - c$

$c < f(x) < 2f(x_0) - c$

thus $\forall x \in B_\delta(x_0)$,

$f(x) > c$,

$B_\delta(x_0) = \{x \in \mathbb{R}^n : \|x - x_0\| < \delta\}$

thus $S$ open $\blacksquare$

$\{x \in \mathbb{R}^n : f(x) > c\} = f^{-1}((c, \infty))$
Because $(c, \infty)$ is open in $\mathbb{R}$ and $f$ is continuous, the
preimage $f^{-1}((c, \infty))$ is open in $\mathbb{R}^n$.

---

**(b) Prove that** $\{x \in \mathbb{R}^n : f(x) \ge c\}$ is closed.

Complement of open set is closed
so if $V = \{x \in \mathbb{R}^n : f(x) \ge c\}$

$V^c = \{x \in \mathbb{R}^n : f(x) < c\}$

using same proof as a),
pick $\epsilon = c - f(x_0)$

$\forall x \in \mathbb{R}^n : f(x) < c$

$f(x) - c < 0$

by continuity at $x_0$, $\forall \epsilon > 0$
$\exists \delta > 0$ s.t. $\forall x \in \mathbb{R}^n$

$\|x - x_0\| < \delta \implies |f(x) - f(x_0)| < \epsilon$

for $x_0 \in V^c$, $f(x_0) < c$

$f(x_0) - c < 0$

multiply by negative $1 \implies -(f(x_0) - c) > 0$
so $\epsilon > 0$ satisfied

$-\epsilon < f(x) - f(x_0) < \epsilon$

$-(c - f(x_0)) < f(x) - f(x_0) < (c - f(x_0))$

add $f(x_0)$

$\forall x \in B_\delta(x_0) = \|x - x_0\| < \delta : f(x) < c$

thus $V^c$ open

$\therefore V$ must be closed $\blacksquare$

---

**Part (b)**
**Method 1 (Closed Preimage):**
The interval $[c, \infty)$ is closed in $\mathbb{R}$ because its complement in
$\mathbb{R}$ is $(-\infty, c)$, which is open. Since the preimage of a closed
set under a continuous map is closed:

$$\{x \in \mathbb{R}^n : f(x) \ge c\} = f^{-1}([c, \infty))$$

Thus, the set is closed in $\mathbb{R}^n$.

**Method 2 (Complement / Result of Part a):**
The complement of $\{x \in \mathbb{R}^n : f(x) \ge c\}$ in $\mathbb{R}^n$ is:

$$\mathbb{R}^n \setminus \{x \in \mathbb{R}^n : f(x) \ge c\} = \{x \in \mathbb{R}^n : f(x) < c\}$$
$$= \{x \in \mathbb{R}^n : -f(x) > -c\}$$

Since $f$ is continuous, $g(x) = -f(x)$ is continuous. By the
result in part (a), the set $\{x \in \mathbb{R}^n : g(x) > -c\}$ is open. As its
complement is open, $\{x \in \mathbb{R}^n : f(x) \ge c\}$ is closed.

---

**(c) Use these results, rather than returning directly to the definitions, to classify the following sets as open or closed:**

$$A = \{x \in \mathbb{R}^n : \|x\|^2 < 1\},$$
$$B = \{x \in \mathbb{R}^n : x^T Q x \le 1\},$$

*where $Q$ is a fixed symmetric $n \times n$ matrix, and*

$$C = \{(x, y) \in \mathbb{R}^2 : y = x^2\}.$$

*Guidance. Try to express each set as the inverse image of an open or closed subset of $\mathbb{R}$ under a continuous scalar-valued function.*

---

**Part (c)**
* **Set $A = \{x \in \mathbb{R}^n : \|x\|^2 < 1\}$**
  * Define $g : \mathbb{R}^n \to \mathbb{R}$ by $g(x) = -\|x\|^2 = -\sum_{i=1}^n x_i^2$.
  * The function $g$ is a polynomial in the coordinates of $x$, hence continuous.
  * Rewriting the inequality:
    $$\|x\|^2 < 1 \iff -\|x\|^2 > -1 \iff g(x) > -1$$
  * Thus, $A = \{x \in \mathbb{R}^n : g(x) > -1\}$. By part (a), $A$ **is open**.

* **Set $B = \{x \in \mathbb{R}^n : x^T Q x \le 1\}$**
  * Define $h : \mathbb{R}^n \to \mathbb{R}$ by $h(x) = -x^T Q x = -\sum_{i=1}^n \sum_{j=1}^n q_{ij} x_i x_j$.
  * Because $h(x)$ is a quadratic form (a homogeneous polynomial of degree 2), it is continuous on $\mathbb{R}^n$.
  * Rewriting the inequality:
    $$x^T Q x \le 1 \iff -x^T Q x \ge -1 \iff h(x) \ge -1$$
  * Thus, $B = \{x \in \mathbb{R}^n : h(x) \ge -1\}$. By part (b), $B$ **is closed**.

* **Set $C = \{(x, y) \in \mathbb{R}^2 : y = x^2\}$**
  * Define $k : \mathbb{R}^2 \to \mathbb{R}$ by $k(x, y) = y - x^2$, which is continuous on $\mathbb{R}^2$.
  * Express the equality $y = x^2$ as the intersection of two weak inequalities:
    $$y = x^2 \iff (y - x^2 \ge 0) \text{ and } (y - x^2 \le 0)$$
  * Applying this to $C$:
    $$C = \{(x, y) \in \mathbb{R}^2 : k(x, y) \ge 0\} \cap \{(x, y) \in \mathbb{R}^2 : -k(x, y) \ge 0\}$$
  * By part (b), both $\{(x, y) \in \mathbb{R}^2 : k(x, y) \ge 0\}$ and $\{(x, y) \in \mathbb{R}^2 : -k(x, y) \ge 0\}$ are closed sets.
  * Since the intersection of two closed sets is closed, $C$ **is closed**.

<!-- page 8 -->

Real_Analysis_PS Page 8

<!-- page 9 -->

**Problem 3. Closed sets and convergent sequences**

Prove that $A \subseteq \mathbb{R}^n$ is closed if and only if

$$x_k \in A, \quad x_k \to x \implies x \in A.$$

*Guided proof.*

*First suppose that $A$ is closed and*
$$x_k \in A, \quad x_k \to x.$$
*Assume, toward a contradiction, that $x \notin A$. Since $A^c$ is open, there exists some $\epsilon > 0$ such that*
$$B_\epsilon(x) \subseteq A^c.$$
*Use convergence of $x_k$ to obtain a contradiction.*

*For the converse, suppose the sequential property holds but $A$ is not closed. Then $A^c$ is not open. Show that there exists $x \in A^c$ such that, for every $k$,*
$$B_{1/k}(x) \cap A \neq \emptyset.$$
*Choose*
$$x_k \in B_{1/k}(x) \cap A$$
*and finish the argument.*

*Proof technique to remember. When a neighborhood property fails, try to construct a sequence.*

---

$A$ closed $\implies$ if $\exists x_k \subseteq A$, $\lim_{k \to \infty} x_k \to x^*$, then $x^* \in A$

(1) Suppose $A$ not closed, then $A^c$ not open.

$\exists$ point $x \in A^c$ such that every neighborhood $A^c$ and $x$ intersects $A$.

$\forall \delta > 0$, $B_\delta(x) \cap A \neq \emptyset$

Take $\delta_k = \frac{1}{k} \implies B_{1/k}(x) \cap A \neq \emptyset \quad \forall k$.

This gives $\{x_k\} \subseteq A \cap B_{1/k}(x)$ as $k \to \infty$, $x_k \to x \in A$ contradiction.

$\implies$) Suppose $x^* \notin A$, by def $x^* \in A^c$.

$A$ closed by supposition, so $A^c$ open. Thus $\exists \delta_0 : B_{\delta_0}(x^*) \subseteq A^c$.

For points $\|x - x^*\| \le \delta_0$, $x \in A^c$.

For $\{x_k\}$ since $x_k \to x^*$,

$\forall \epsilon$, $\exists K \in \mathbb{N}$ s.t. $\forall k > K$,
$$\|x_k - x^*\| < \epsilon.$$

Take $\epsilon = \delta_0$, then there are infinitely many points
$$\|x_k - x^*\| < \delta_0 :$$
$$\forall x_k : k > K.$$

But $\{x_k\} \subseteq A$. Contradiction.

---

### **Part 1: Obtaining the Contradiction ($\implies$)**

**Given Setup:**
* $A \subseteq \mathbb{R}^n$ is closed, so $A^c$ is open.
* A sequence $(x_k) \subseteq A$ satisfies $x_k \to x$.
* Assume, for contradiction, that $x \notin A$ (i.e., $x \in A^c$).
* Since $A^c$ is open, there exists an open ball $B_\epsilon(x) \subseteq A^c$ for some $\epsilon > 0$.

**Deriving the Contradiction:**

1. **Apply the definition of sequence convergence:**
   Since $x_k \to x$, for the chosen $\epsilon > 0$, there exists an integer $K \in \mathbb{N}$ such that:
   $$\|x_k - x\| < \epsilon \quad \text{for all } k \ge K$$

2. **Map terms to the open ball:**
   The condition $\|x_k - x\| < \epsilon$ means that for all $k \ge K$, the sequence elements lie in the ball:
   $$x_k \in B_\epsilon(x)$$

3. **Establish the set-theoretic contradiction:**
   * Because $B_\epsilon(x) \subseteq A^c$, it follows that $x_k \in A^c$ for all $k \ge K$.
   * However, the sequence is defined such that $x_k \in A$ for all $k \in \mathbb{N}$.
   * Thus, for any $k \ge K$, we have $x_k \in A \cap A^c = \emptyset$, which is a direct contradiction.

Therefore, the assumption $x \notin A$ must be false, concluding that $x \in A$. $\blacksquare$

---

### **Part 2: The Converse via Sequence Construction ($\impliedby$)**

**Question:** *For the second part, would we also use a sequence?*
**Answer:** Yes. When a topological neighborhood condition fails (i.e., $A^c$ fails to be open), you construct a sequence indexed by $k$ using shrinking open balls $B_{1/k}(x)$ to exploit the sequential hypothesis.

**Formal Argument:**

1. **Assume the sequential property holds:**
   Whenever $(x_k) \subseteq A$ and $x_k \to x$, then $x \in A$.

2. **Assume toward contradiction that $A$ is not closed:**
   If $A$ is not closed, then its complement $A^c$ is **not open**.

3. **Negate the definition of an open set for $A^c$:**
   $A^c$ is open if for every $x \in A^c$, there exists $\epsilon > 0$ such that $B_\epsilon(x) \subseteq A^c$.
   The negation states: there exists some point $x \in A^c$ such that **no** open ball around $x$ is fully contained in $A^c$:
   $$B_\epsilon(x) \not\subseteq A^c \quad \text{for every } \epsilon > 0$$
   This means that for every $\epsilon > 0$, the ball must intersect $A$:
   $$B_\epsilon(x) \cap A \neq \emptyset$$

4. **Construct the sequence:**
   For each integer $k \in \{1, 2, 3, \dots\}$, set $\epsilon = \frac{1}{k}$. Since $B_{1/k}(x) \cap A \neq \emptyset$, we can choose a point:
   $$x_k \in B_{1/k}(x) \cap A$$

5. **Verify properties of $(x_k)$:**
   * **Inclusion:** $x_k \in A$ for all $k$ by construction.
   * **Convergence:** Since $x_k \in B_{1/k}(x)$, the Euclidean distance satisfies $\|x_k - x\| < \frac{1}{k}$. Taking the limit as $k \to \infty$:
     $$\lim_{k \to \infty} \|x_k - x\| \le \lim_{k \to \infty} \frac{1}{k} = 0 \implies x_k \to x$$

6. **Reach the contradiction:**
   * By our initial sequential hypothesis, because $(x_k) \subseteq A$ and $x_k \to x$, we must have $x \in A$.
   * But $x$ was initially chosen such that $x \in A^c$ ($x \notin A$).
   * This yields $x \in A \cap A^c = \emptyset$, a contradiction.

Hence, $A^c$ must be open, which proves that $A$ is closed. $\blacksquare$

---

## **2 Compactness and Its Consequences**

**Problem 4. A closed subset of a compact set**

Suppose $K \subseteq \mathbb{R}^n$ is compact and $F \subseteq K$ is closed. Prove that $F$ is compact.

*Guidance. Take an arbitrary sequence*
$$(x_k) \subseteq F.$$
*Since it is also a sequence in $K$, compactness gives a convergent subsequence*
$$x_{k_j} \to x.$$
*Which assumption guarantees that $x \in F$?*
*In your proof, make clear the distinct roles played by compactness and closedness.*

$K \subset \mathbb{R}^n$ compact

---

### **Sequential Definition of Compactness**
A subset $K$ of a topological space (or metric space $(\mathbb{X}, d)$) is **sequentially compact** if every sequence $(x_n)_{n=1}^\infty$ in $K$ has a subsequence $(x_{n_k})_{k=1}^\infty$ that converges to a limit $x \in K$:

$$\forall (x_n) \subseteq K, \ \exists (x_{n_k}) \subseteq (x_n) \text{ and } \exists x \in K \text{ such that } \lim_{k \to \infty} x_{n_k} = x$$

*(In metric spaces such as $\mathbb{R}^n$, sequential compactness is strictly equivalent to topological compactness defined via open covers, as well as to being closed and bounded by the Heine-Borel theorem.)*

### **Guarantee of Convergence Within the Closed Subset**
Let $K \subset \mathbb{R}^n$ be compact, and let $F \subset K$ be a closed subset of $K$. Let $(x_n)_{n=1}^\infty$ be a sequence in $F$.

<!-- page 10 -->

1. **Sequence elements in $K$:** Since $F \subset K$, every element of the sequence $(x_n)_{n=1}^\infty$ is also an element of $K$.
2. **Subsequence extraction via Compactness of $K$:** Because $K$ is compact, there exists a subsequence $(x_{n_k})_{k=1}^\infty$ that converges to a limit $x^* \in K$:
   $$\lim_{k \to \infty} x_{n_k} = x^*$$
3. **Limit membership in $F$ via Closedness of $F$:** The subsequence $(x_{n_k})_{k=1}^\infty$ is entirely contained within $F$. A set $F$ is closed if and only if it contains all of its sequential limit points (Problem 3). Since $F$ is closed and $(x_{n_k}) \subseteq F$ converges to $x^*$, it must hold that:
   $$x^* \in F$$

Since an arbitrary sequence $(x_n)$ in $F$ contains a subsequence that converges to a point $x^* \in F$, $F$ is sequentially compact. $\blacksquare$

<!-- page 11 -->

Which assumption guarantees that $x^* \in F$?

In your proof, make clear the distinct roles played by compactness and closedness.

$K \subset \mathbb{R}^n$ compact

$F \subseteq K$ closed

wts $F$ compact

using sequential compactness,

$F$ compact if $\forall \{x_n\}_{n=1}^\infty \subseteq F$,

$\exists \{x_{n_k}\}_{k=1}^\infty \subseteq \{x_n\}_n : x_{n_k} \to x^* \in F$

Define arbitrary $\{x_n\}_{n=1}^\infty \subseteq F$

$\{x_n\}_{n=1}^\infty \subseteq K$ since $F \subseteq K$

since $K$ compact,

$\exists \{x_{n_k}\}_{k=1}^\infty \to x^* \in K$

need to show that $x^* \in F$

$$\lim_{k \to \infty} x_{n_k} = x^*$$

Since $F$ is closed, it must contain its limit points s.t. $\forall \{y_k\}_{k=1}^\infty \subseteq F$,

$$\lim_{k \to \infty} y_k = y^* \in F$$

Since $x_{n_k}$ is convergent seq contained in $F$ as limit point $x^*$, $x^*$ must be in $F$

Thus all convergent seq. in $F$ have a subsequence which converges to a point in $F$
$\implies F$ must be compact

---

equivalent to topological compactness defined via open covers, as well as to being closed and bounded by the Heine-Borel theorem.)

**Guarantee of Convergence Within the Closed Subset**
Let $K \subset \mathbb{R}^n$ be compact, and let $F \subset K$ be a closed subset of $K$. Let $(x_n)_{n=1}^\infty$ be a sequence in $F$.

The guarantee that the limit point belongs to $F$ follows from a two-step mechanism: **compactness of the ambient set $K$ guarantees the existence of a convergent subsequence**, and the **closedness of $F$ guarantees containment of the limit**.

From `<https://gemini.google.com/app/486e8cbd141d0bef>`

**Step-by-Step Analytical Proof**
1. **Existence of the Subsequential Limit via Compactness:**
   Since $F \subseteq K$, any sequence $(x_n)_{n=1}^\infty \subseteq F$ is also a sequence in the compact set $K$. By the sequential compactness of $K$, there exists a subsequence $(x_{n_k})_{k=1}^\infty$ and a point $x \in K$ such that:
   $$\lim_{k \to \infty} x_{n_k} = x$$
2. **Containment in the Closed Set via Topological Closure:**
   A set $F \subseteq \mathbb{R}^n$ is closed if and only if it contains all of its sequential limit points. That is:
   $$\overline{F} = F \iff (\forall (y_k) \subseteq F \text{ with } \lim_{k \to \infty} y_k = y \implies y \in F)$$
   Because $(x_{n_k})$ is entirely contained in $F$ and converges to $x$, $x$ is a limit point (and closure point) of $F$. Therefore, $x \in \overline{F} = F$.

**Clarification on Arbitrary Sequences vs. Convergent Sequences**
* **If the sequence $(x_n)$ is already assumed to converge to some $x$ in $\mathbb{R}$:**
  The compactness of $K$ is not even required. The topological closedness of $F$ alone ensures $x \in F$, because:
  $$x \in \overline{F} = F$$
* **If the sequence $(x_n)$ is arbitrary (not assumed a priori to converge):**
  Compactness of $K$ guarantees the *existence* of at least one accumulation point $x$ and a convergent subsequence $x_{n_k} \to x$, while the closedness of $F$ ensures that every such accumulation point resides in $F$.

From `<https://gemini.google.com/app/486e8cbd141d0bef>`

---

**Problem 5. Continuous images of compact sets**

Suppose $K \subseteq \mathbb{R}^n$ is compact and
$$f : K \to \mathbb{R}^m$$
is continuous.

(a) Prove that $f(K)$ is compact.
(b) Deduce that if $m = 1$, then $f$ attains both a maximum and a minimum on $K$.
(c) Construct examples showing that the conclusion in part (b) can fail if:
    (i) the domain is bounded but not closed;
    (ii) the domain is closed but unbounded;
    (iii) the domain is compact but $f$ is not continuous.

*Guidance for part (a). Take a sequence*
$$y_k \in f(K).$$
*Choose $x_k \in K$ such that*
$$f(x_k) = y_k.$$
*Now use compactness and continuity in that order.*

---

5) $f : K \to \mathbb{R}^m$ cont

$\& \quad K \subseteq \mathbb{R}^n$ compact

a) wts $f(K)$ compact

define $\{x_n\}_{n=1}^\infty \subseteq K$

since $K$ compact

$$\exists \{x_{n_k}\}_{k=1}^\infty : \lim_{k \to \infty} x_{n_k} = x^* \in K$$

$\dots \ \& \ \dots$ all elements of $\{x_n\}_1^\infty$

---

**Formal Proof of Part (a)**
**Proposition:** Let $K \subseteq \mathbb{R}^n$ be compact and $f : K \to \mathbb{R}^m$ be continuous. Then $f(K)$ is compact.

**Proof via Sequential Compactness:**
Let $(y_k)_{k=1}^\infty$ be an arbitrary sequence in $f(K)$.

1. **Preimage Selection:** By definition of the image $f(K)$, for each $k \in \mathbb{N}$, there exists $x_k \in K$ such that $f(x_k) = y_k$. This constructs a sequence $(x_k)_{k=1}^\infty \subseteq K$.
2. **Sequential Compactness of Domain:** Because $K$ is compact, it is sequentially compact. Therefore, there exists a subsequence $(x_{k_j})_{j=1}^\infty \subseteq (x_k)_{k=1}^\infty$ and a limit point $x^* \in K$ such that:
   $$\lim_{j \to \infty} x_{k_j} = x^*$$
3. **Application of Continuity:** The function $f$ is continuous on $K$, hence sequentially continuous at $x^*$. Passing limits through continuous maps yields:
   $$\lim_{j \to \infty} f(x_{k_j}) = f\left(\lim_{j \to \infty} x_{k_j}\right) = f(x^*)$$
4. **Convergence in Image:** Define the corresponding subsequence of $(y_k)$ by $y_{k_j} = f(x_{k_j})$. It follows that:
   $$\lim_{j \to \infty} y_{k_j} = f(x^*)$$
   Since $x^* \in K$, $f(x^*) \in f(K)$. Thus, the arbitrary sequence $(y_k)$ in $f(K)$ has a subsequence $(y_{k_j})$ converging to a limit in $f(K)$. Hence, $f(K)$ is compact. $\blacksquare$

<!-- page 12 -->

**Formal Proof of Part (a)**
**Proposition:** Let $K \subseteq \mathbb{R}^n$ be compact and $f : K \to \mathbb{R}^m$ be continuous. Then $f(K)$ is compact.

**Proof via Sequential Compactness:**
Let $(y_k)_{k=1}^\infty$ be an arbitrary sequence in $f(K)$.

1. **Preimage Selection:** By definition of the image $f(K)$, for each $k \in \mathbb{N}$, there exists $x_k \in K$ such that $f(x_k) = y_k$. This constructs a sequence $(x_k)_{k=1}^\infty \subseteq K$.
2. **Sequential Compactness of Domain:** Because $K$ is compact, it is sequentially compact. Therefore, there exists a subsequence $(x_{k_j})_{j=1}^\infty \subseteq (x_k)_{k=1}^\infty$ and a limit point $x^* \in K$ such that:
$$\lim_{j \to \infty} x_{k_j} = x^*$$
3. **Application of Continuity:** The function $f$ is continuous on $K$, hence sequentially continuous at $x^* \in K$. Passing limits through continuous maps yields:
$$\lim_{j \to \infty} f(x_{k_j}) = f\left(\lim_{j \to \infty} x_{k_j}\right) = f(x^*)$$
4. **Convergence in Image:** Define the corresponding subsequence of $(y_k)_{k=1}^\infty$ by $y_{k_j} = f(x_{k_j})$. It follows that:
$$\lim_{j \to \infty} y_{k_j} = f(x^*)$$

Real_Analysis_PS Page 12

<!-- page 13 -->

Choose $x_k \in K$ such that
$$f(x_k) = y_k.$$
Now use compactness and continuity in that order.

$$\exists \{x_{n_k}\}_{k=1}^\infty : \lim_{k \to \infty} x_{n_k} = x^* \in K$$

apply $f$ to all elements of $\{x_{n_k}\}_{k=1}^\infty$

$$\lim_{k \to \infty} f(x_{n_k}) = \lim_{k \to \infty} f(x_{n_k}) = f\left(\lim_{k \to \infty} x_{n_k}\right) \text{ by cont. at } A$$

$$f(x^*) \in K \quad = f(x^*)$$

thus $\lim_{k \to \infty} f(y_{n_k}) = f(x^*)$

so $\{f(x_{n_k})\}_{k=1}^\infty \to f(x^*) \in K$

$f(\{x_{n_k}\}_{n=1}^\infty) \subseteq K$ thus for
all convergent sequences in $K$,
$\exists$ convergent subsequence
$f(\{x_{n_k}\}_{k=1}^\infty)$ w/ limit point
$f(x^*) \in K$, so $K$ compact

b) if $m=1$ s.t. $f: K \to \mathbb{R}$
wts $f$ attains max & min on $K$

$f(K)$ is compact by part (a)

since $f(K) \subseteq \mathbb{R}$, by
Heine-Borel $f(K)$ is closed
& bounded s.t. $\exists m, M \in \mathbb{R}$

$$\forall y \in f(K), \quad m \le y \le M$$

since $f(K)$ closed, $m, M \in f(K)$

thus $f$ attains max $M$
& min $m$ on $\mathbb{R}$

c) Part (b) can fail if $K$ bounded but not closed

ex: let $K = (0, 1) \subseteq \mathbb{R}$
& $f(x) = x$

$\max(f(K)) = 1$ but $1 \notin f(K)$

---

> **Proposition:** Let $K \subseteq \mathbb{R}^n$ be compact and $f : K \to \mathbb{R}$ be continuous (i.e., $m = 1$). Then $f$ attains both a maximum and a minimum on $K$ (The Extreme Value Theorem).
>
> **Proof:**
> 1. **Compactness of the Image:**
>    By the result of part (a), the image set $f(K) \subseteq \mathbb{R}$ is compact.
> 2. **Heine-Borel Characterization:**
>    By the Heine-Borel Theorem in Euclidean space, $f(K)$ is closed and bounded in $\mathbb{R}$.
> 3. **Existence of Supremum and Infimum:**
>    Because $K$ is non-empty, $f(K)$ is a non-empty, bounded subset of $\mathbb{R}$. By the Completeness Axiom (Least Upper Bound Property) of $\mathbb{R}$, the supremum and infimum exist as finite real numbers:
>    $$M = \sup f(K) = \sup_{x \in K} f(x), \quad m = \inf f(K) = \inf_{x \in K} f(x)$$
> 4. **Attainment via Closedness:**
>    By definition of the supremum, for every $\epsilon > 0$, there exists an element $y \in f(K)$ such that $M - \epsilon < y \le M$. Hence, $M$ is an adherent point of $f(K)$, meaning $M \in \overline{f(K)}$.
>    Since $f(K)$ is closed, it contains all its accumulation and limit points, so $\overline{f(K)} = f(K)$.
>    Therefore:
>    $$M \in f(K)$$
>    By identical reasoning for the infimum, $m \in \overline{f(K)} = f(K)$.
> 5. **Conclusion:**
>    Since $M, m \in f(K)$, there exist points $x_{\max}, x_{\min} \in K$ such that:
>    $$f(x_{\max}) = M = \sup_{x \in K} f(x) \quad \text{and} \quad f(x_{\min}) = m = \inf_{x \in K} f(x)$$
>    Thus, $f$ attains its global maximum at $x_{\max}$ and its global minimum at $x_{\min}$ on $K$. $\blacksquare$

---

> **Counterexamples for Part (c)**
> * **(i) Domain is bounded but not closed ($K$ not compact)**
>   * Let $K = (0, 1) \subset \mathbb{R}$, which is bounded but open.
>   * Define $f : (0, 1) \to \mathbb{R}$ by $f(x) = \frac{1}{x}$.
>   * The function $f$ is continuous on $(0, 1)$, but $\sup_{x \in (0,1)} f(x) = \infty$, so $f$ is unbounded above and fails to attain a maximum.
>   * *Bounded alternative:* $f(x) = x$ on $(0,1)$ is bounded with $\sup f(K) = 1$ and $\inf f(K) = 0$, yet neither the supremum nor the infimum is attained on $(0,1)$.

Real_Analysis_PS Page 13

<!-- page 14 -->

$$f(x_{k_j}) = f\left( \lim_{j \to \infty} x_{k_j} \right) = f(x^*)$$

**Convergence in Image:** Define the corresponding subsequence of $(y_k)_{k=1}^\infty$ by $y_{k_j} = f(x_{k_j})$. It follows that:

$$\lim_{j \to \infty} y_{k_j} = f(x^*)$$

Since $x^* \in K$, the limit point satisfies $f(x^*) \in f(K)$.
Every arbitrary sequence $(y_k)_{k=1}^\infty \subseteq f(K)$ has a subsequence $(y_{k_j})_{j=1}^\infty$ converging to an element in $f(K)$. Thus, $f(K)$ is sequentially compact, and consequently compact in $\mathbb{R}^m$. ■

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

**Proposition:** Let $K \subseteq \mathbb{R}^n$ be compact and $f : K \to \mathbb{R}$ be continuous (i.e., $m = 1$). Then $f$ attains both a maximum and a minimum on $K$ (The Extreme Value Theorem).

1. **Compactness of the Image:**
   By the result of part (a), the image set $f(K) \subseteq \mathbb{R}$ is compact.
2. **Heine-Borel Characterization:**
   By the Heine-Borel Theorem in Euclidean space, $f(K)$ is closed and bounded in $\mathbb{R}$.
3. **Existence of Supremum and Infimum:**
   Because $K$ is non-empty, $f(K)$ is a non-empty, bounded subset of $\mathbb{R}$. By the Completeness Axiom (Least Upper Bound Property) of $\mathbb{R}$, the supremum and infimum exist as finite real numbers:
   $$M = \sup f(K) = \sup_{x \in K} f(x), \quad m = \inf f(K) = \inf_{x \in K} f(x)$$
4. **Attainment via Closedness:**
   By definition of the supremum, for every $\epsilon > 0$, there exists an element $y \in f(K)$ such that $M - \epsilon < y \le M$. Hence, $M$ is an adherent point of $f(K)$, meaning $M \in \overline{f(K)}$.
   Since $f(K)$ is closed, it contains all its accumulation and limit points, so $\overline{f(K)} = f(K)$.
   Therefore:
   $$M \in f(K)$$
   By identical reasoning for the infimum, $m \in \overline{f(K)} = f(K)$.
5. **Conclusion:**
   Since $M, m \in f(K)$, there exist points $x_{\max}, x_{\min} \in K$ such that:
   $$f(x_{\max}) = M = \sup_{x \in K} f(x) \quad \text{and} \quad f(x_{\min}) = m = \inf_{x \in K} f(x)$$
   Thus, $f$ attains its global maximum at $x_{\max}$ and its global minimum at $x_{\min}$ on $K$. ■

---

*(i) Domain is bounded but not closed ($K$ not compact)*
Let $K = (0, 1) \subset \mathbb{R}$, which is bounded but open.
Define $f : (0, 1) \to \mathbb{R}$ by $f(x) = \frac{1}{x}$.
The function $f$ is continuous on $(0, 1)$, but $\sup_{x \in (0,1)} f(x) = \infty$, so $f$ is unbounded above and fails to attain a maximum.

*Bounded alternative:* $f(x) = x$ on $(0, 1)$ is bounded with $\sup f(K) = 1$ and $\inf f(K) = 0$, yet neither the supremum nor the infimum is attained on $(0, 1)$.

Real_Analysis_PS Page 14

<!-- page 15 -->

$$\max(f(K)) = 1 \quad \text{but} \quad 1 \notin f(K)$$
$$\min(f(K)) = 0 \quad \text{but} \quad 0 \notin f(K)$$

C.ii) Part (b) fails if $K$ closed but not bounded

ex: let $K = [0, \infty) \quad \& \quad f(x) = x \cdot \sin(x)$

$K$ closed as $K^c = (-\infty, 0)$ is open

$$\sup(f(K)) = \infty \quad \text{but} \quad \text{max and min do not exist}$$
$$\inf(f(K)) = -\infty$$

C.iii) Part (b) fails if $K$ compact but $f$ not cont

ex let $K = [0, 1] \quad \& \quad f(x) = \begin{cases} \frac{1}{x} & \text{if } x \neq 0 \\ 0 & \text{if } x = 0 \end{cases}$

$$\inf f(K) = 0$$

$$\text{but } 0 \notin f(K)$$

$$\text{thus } f \text{ never attains its min}$$

```
    f(x)
 2  o
    |
 1  o  .
    | / 
--o-+---+--> 
  0 | 1 
    |
```

6)

---

**Problem 6. Continuous bijections from compact sets**

Let $K \subseteq \mathbb{R}^n$ be compact, and suppose

$$f : K \to Y \subseteq \mathbb{R}^m$$

is a continuous bijection.

Prove that

$$f^{-1} : Y \to K$$

is continuous.

*Guided contradiction argument. Take a sequence*

$$y_k \to y$$

*and define*

$$x_k = f^{-1}(y_k), \quad x = f^{-1}(y).$$

*Suppose that $x_k \not\to x$. Show that there exist $\epsilon > 0$ and a subsequence $(x_{k_j})$ such that*

$$\|x_{k_j} - x\| \ge \epsilon.$$

---

$$K \subseteq \mathbb{R}^n \text{ compact}$$

$$f : K \to Y \subseteq \mathbb{R}^m$$

$$\text{cont bijection}$$

---

*   **(ii) Domain is closed but unbounded ($K$ not compact)**
    *   Let $K = [0, \infty) \subset \mathbb{R}$, which is closed in $\mathbb{R}$ but unbounded.
    *   Define $f : [0, \infty) \to \mathbb{R}$ by $f(x) = x$.
    *   The function $f$ is continuous on $[0, \infty)$, but $\sup_{x \in [0,\infty)} f(x) = \infty$, so it attains no maximum.
    *   *Bounded alternative:* $f(x) = 1 - e^{-x}$ on $[0, \infty)$ is bounded and continuous with $\sup_{x \ge 0} f(x) = 1$, but $f(x) < 1$ for all $x \in [0, \infty)$, so the maximum is never attained.

*   **(iii) Domain is compact but $f$ is not continuous**
    *   Let $K = [0, 1] \subset \mathbb{R}$, which is compact (closed and bounded).
    *   Define $f : [0, 1] \to \mathbb{R}$ by:
        $$f(x) = \begin{cases} \frac{1}{x} & \text{if } x \in (0, 1] \\ 0 & \text{if } x = 0 \end{cases}$$
    *   $f$ is discontinuous at $x = 0$, unbounded on $[0, 1]$, and has no maximum.
    *   *Bounded alternative:* Define $g : [0, 1] \to \mathbb{R}$ by:
        $$g(x) = \begin{cases} x & \text{if } x \in [0, 1) \\ 0 & \text{if } x = 1 \end{cases}$$
    *   $g$ is bounded with $\sup_{x \in [0, 1]} g(x) = 1$, but $g(x) < 1$ for all $x \in [0, 1]$, so $g$ attains no maximum on $K$.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

Real_Analysis_PS Page 15

<!-- page 16 -->

**(ii) Domain is closed but unbounded ($K$ not compact)**
Let $K = [0, \infty)$, which is closed in $\mathbb{R}$ but unbounded.
Define $f : [0, \infty) \to \mathbb{R}$ by $f(x) = x$.
The function $f$ is continuous on $[0, \infty)$, but $\sup_{x \in [0,\infty)} f(x) = \infty$, so it attains no maximum.

*Bounded alternative:* $f(x) = 1 - e^{-x}$ on $[0, \infty)$ is bounded and continuous with $\sup_{x \ge 0} f(x) = 1$, but $f(x) < 1$ for all $x \in [0, \infty)$, so the maximum is never attained.

**(iii) Domain is compact but $f$ is not continuous**
Let $K = [0, 1]$, which is compact (closed and bounded).
Define $f : [0, 1] \to \mathbb{R}$ by:

$$f(x) = \begin{cases} \frac{1}{x} & \text{if } x \in (0, 1] \\ 0 & \text{if } x = 0 \end{cases}$$

$f$ is discontinuous at $x = 0$, unbounded on $[0, 1]$, and has no maximum.

*Bounded alternative:* Define $g : [0, 1] \to \mathbb{R}$ by:

$$g(x) = \begin{cases} x & \text{if } x \in [0, 1) \\ 0 & \text{if } x = 1 \end{cases}$$

$g$ is bounded with $\sup_{x \in [0, 1]} g(x) = 1$, but $g(x) < 1$ for all $x \in [0, 1]$, so $g$ attains no maximum on $K$.

---

**Problem 6: Continuous Bijections from Compact Sets**

**Proposition:** Let $K \subseteq \mathbb{R}^n$ be compact, $Y \subseteq \mathbb{R}^m$, and suppose $f : K \to Y$ is a continuous bijection. Then the inverse map $f^{-1} : Y \to K$ is continuous.

*Proof via Guided Contradiction:*
To show that $f^{-1} : Y \to K$ is continuous, it suffices to prove sequential continuity on $Y$.

Let $(y_k)_{k=1}^\infty \subseteq Y$ be an arbitrary sequence converging to $y \in Y$, i.e., $y_k \to y$.

Define:

$$x_k = f^{-1}(y_k) \in K \quad \text{and} \quad x = f^{-1}(y) \in K$$

Real_Analysis_PS Page 16

<!-- page 17 -->

$$y_k \to y$$

and define

$$x_k = f^{-1}(y_k), \quad x = f^{-1}(y).$$

Suppose that $x_k \not\to x$. Show that there exist $\epsilon > 0$ and a subsequence $(x_{k_j})$ such that

$$\|x_{k_j} - x\| \ge \epsilon$$

for every $j$.

Use compactness to extract a further convergent subsequence

$$x_{k_{j_l}} \to x^*.$$

Now compare

$$f(x_{k_{j_l}}) \to f(x^*)$$

with

$$f(x_{k_{j_l}}) = y_{k_{j_l}} \to y.$$

Identify where uniqueness of limits is used and where injectivity of $f$ is used.

---

$$\text{cont bijection}$$

$$\text{WTS } f^{-1} : Y \to K$$

$$\text{is continuous}$$

$f^{-1}$ is continuous at point $x^*$ if every seq. $\{x_n\}_{n=1}^\infty$ converging to $x^*$ maps to seq. $\{f^{-1}(x_n)\}_{n=1}^\infty$ converging to $f^{-1}(x^*)$

let $y_k \to y$ be a seq. in $Y$

s.t. $x_k = f^{-1}(y_k) \quad \& \quad x = f^{-1}(y)$

For contradiction, suppose $x_k \not\to x$

since $\{x_k\}_{k=1}^\infty \subseteq K$ is a seq. in $K$ & $K$ compact,

$\exists \{x_{k_j}\}_{j=1}^\infty \to x \quad \text{a convergent subseq. in } K$

thus $\lim_{j \to \infty} x_{k_j} = x$ implies that $\forall \epsilon > 0$,

$$\|x_{k_j} - x\| \ge \epsilon \quad \text{for all } j \in \mathbb{N}$$

since $x_{k_j}$ is itself a seq.

there must exist another convergent subseq. $x_{k_{j_l}} \subseteq K$

$$\text{s.t. } x_{k_{j_l}} \to x^*$$

<!-- page 18 -->

We wish to show that $x_k \to x$.

**1. Negation of Convergence:**
Assume, for contradiction, that $x_k \not\to x$.
The definition of convergence states: $\forall \epsilon > 0, \exists N \in \mathbb{N}$ such that $\forall k \ge N, \|x_k - x\| < \epsilon$.

**2. Negating this statement yields:**

$\exists \epsilon_0 > 0$ such that $\forall N \in \mathbb{N}, \exists k \ge N$ with $\|x_k - x\| \ge \epsilon_0$

This condition allows the inductive construction of a strictly increasing sequence of indices $k_1 < k_2 < k_3 < \dots$ defining a subsequence $(x_{k_j})_{j=1}^\infty$ such that:

$\|x_{k_j} - x\| \ge \epsilon_0 \quad \forall j \in \mathbb{N}$

**3. Extraction of a Convergent Subsequence:**
Because $(x_{k_j})_{j=1}^\infty \subseteq K$ and $K$ is compact (hence sequentially compact), there exists a further subsequence $(x_{k_{j_\ell}})_{\ell=1}^\infty$ that converges to some limit $x^* \in K$:

$\lim_{\ell \to \infty} x_{k_{j_\ell}} = x^*$

**4. Comparison of Limits in the Image:**
*   **Via Continuity of $f$:** Since $f$ is continuous on $K$, it is sequentially continuous at $x^*$. Therefore:

    $\lim_{\ell \to \infty} f(x_{k_{j_\ell}}) = f(x^*)$

*   **Via the Original Convergent Sequence:** By definition, $f(x_{k_{j_\ell}}) = y_{k_{j_\ell}}$. Since $(y_{k_{j_\ell}})_{\ell=1}^\infty$ is a subsequence of the convergent sequence $y_k \to y$, every subsequence must converge to the same limit:

    $\lim_{\ell \to \infty} f(x_{k_{j_\ell}}) = \lim_{\ell \to \infty} y_{k_{j_\ell}} = y$

**5. Applying Uniqueness of Limits and Injectivity:**
*   **Uniqueness of Limits in $\mathbb{R}^m$:** Because $\mathbb{R}^m$ is a metric space (Hausdorff), limit points of convergent sequences are unique. Equating the two limits gives:
    $f(x^*) = y$

*   **Injectivity of $f$:** We already have $f(x) = y$. Thus $f(x^*) = f(x)$. Because $f$ is injective (since $f$ is a bijection):

    $x^* = x$

**6. Contradiction:**
Since $x_{k_{j_\ell}} \to x^* = x$, it follows by the definition of the limit that:

$\lim_{\ell \to \infty} \|x_{k_{j_\ell}} - x\| = 0$

However, by construction, every element of the initial subsequence satisfies:

$\|x_{k_{j_\ell}} - x\| \ge \epsilon_0 > 0 \quad \forall \ell \in \mathbb{N}$

Taking the limit as $\ell \to \infty$ yields $0 \ge \epsilon_0 > 0$, a contradiction.

Thus, the assumption that $x_k \not\to x$ is false. It follows that $x_k \to x$, which implies $\lim_{k \to \infty} f^{-1}(y_k) = f^{-1}(y)$. Therefore, $f^{-1}$ is sequentially continuous, and hence continuous on $Y$. $\blacksquare$

From <https://gemini.google.com/app/06b7ab97dac5cbbb>

Real_Analysis_PS Page 18

<!-- page 19 -->

## 3 Differentiability as Linear Approximation

**Problem 7. The derivative is unique**

Suppose $f : \mathbb{R}^n \to \mathbb{R}^m$ satisfies

$$f(x+h) = f(x) + Ah + r_A(h)$$

and also

$$f(x+h) = f(x) + Bh + r_B(h),$$

where $A, B : \mathbb{R}^n \to \mathbb{R}^m$ are linear maps and

$$\frac{\|r_A(h)\|}{\|h\|} \to 0, \quad \frac{\|r_B(h)\|}{\|h\|} \to 0.$$

Prove that

$$A = B.$$

*Guidance. Fix an arbitrary $v \in \mathbb{R}^n$ and set*

$$h = tv.$$

Compare the two approximations and divide by $t \neq 0$. Then let $t \to 0$.

Why does showing

$$(A - B)v = 0$$

for every $v$ imply $A = B$?

---

$$\text{7) Derivative is unique}$$

$$\text{Suppose } f : \mathbb{R}^n \to \mathbb{R}^m \text{ is defined as}$$

$$f(x+h) = f(x) + Ah + r_A(h)$$

$$\text{and } f(x+h) = f(x) + Bh + r_B(h)$$

$$\text{where } A, B : \mathbb{R}^n \to \mathbb{R}^m \text{ are linear maps}$$

$$\text{and } \frac{\|r_A(h)\|}{\|h\|} \to 0, \quad \frac{\|r_B(h)\|}{\|h\|} \to 0$$

---

$$s.t. \quad x_{k_{j_l}} \to x^*$$

$$\text{since } f \text{ is cont \& injective}$$

$$f(x_{k_{j_l}}) \to f(x^*)$$

$$\text{each term in } x_{k_{j_l}} \text{ maps to}$$

$$\text{some } y_{k_{j_l}} \in Y \quad \& \quad f(x^*) = y$$

$$\text{thus } f^{-1}(y) = x \quad \& \quad f^{-1}(y_{k_{j_l}}) = x_{k_{j_l}}$$

$$\text{and } x_{k_{j_l}} \to x \in K, \quad \text{thus the}$$

$$\text{seq. } x_k \to x \quad \text{since } x_{k_{j_l}} \subseteq x_k$$

$$\text{but by assumption } x_k \not\to x, \text{ contradiction!}$$

$$\text{so } x_k \not\to x \text{ must be false}$$

$$\text{and } f^{-1} \text{ must be continuous}$$

<!-- page 20 -->

**Problem 7: The Derivative is Unique**
**Proposition:** Suppose $f : \mathbb{R}^n \to \mathbb{R}^m$ satisfies

$$f(x+h) = f(x) + Ah + r_A(h) \quad \text{and} \quad f(x+h) = f(x) + Bh + r_B(h)$$

where $A, B : \mathbb{R}^n \to \mathbb{R}^m$ are linear maps and $\lim_{h \to 0} \frac{\|r_A(h)\|}{\|h\|} = 0$, $\lim_{h \to 0} \frac{\|r_B(h)\|}{\|h\|} = 0$. Then $A = B$.

**Proof:**

**1. Equating the Linear Approximations:**
Subtracting the two expressions for $f(x+h)$ gives:

$$(f(x) + Ah + r_A(h)) - (f(x) + Bh + r_B(h)) = 0$$

$$(A - B)h = r_B(h) - r_A(h)$$

**2. Evaluating Along a Direction:**
Fix an arbitrary vector $v \in \mathbb{R}^n$.
* If $v = 0$, then by linearity $(A - B)0 = 0$.
* If $v \neq 0$, let $h = tv$ for a scalar $t \in \mathbb{R} \setminus \{0\}$.
  Substituting $h = tv$ into the equation and utilizing the linearity of $(A - B)$:

$$(A - B)(tv) = r_B(tv) - r_A(tv)$$

$$t(A - B)v = r_B(tv) - r_A(tv)$$

**3. Taking the Limit as $t \to 0$:**
Dividing both sides by $t \neq 0$ and applying the Euclidean norm on $\mathbb{R}^m$:

$$\|(A - B)v\| = \left\| \frac{r_B(tv) - r_A(tv)}{t} \right\|$$

Applying the triangle inequality:

$$\|(A - B)v\| \le \frac{\|r_B(tv)\|}{|t|} + \frac{\|r_A(tv)\|}{|t|}$$

Since $\|tv\| = |t| \|v\|$, we rewrite this in terms of the remainder limits by multiplying and dividing by $\|v\| > 0$:

$$\|(A - B)v\| \le \|v\| \left( \frac{\|r_B(tv)\|}{\|tv\|} + \frac{\|r_A(tv)\|}{\|tv\|} \right)$$

<!-- page 21 -->

$$\sigma \frac{\dots}{\|h\|} \to 0 \quad \frac{\dots}{\|h\|} \to 0$$

$$\text{wts that } A = B \text{ must be true}$$

$$\text{let } v \in \mathbb{R}^n \text{ be arbitrary vector}$$

$$\& \quad \text{define } h = tv \text{ for } t \in \mathbb{R}$$
$$\text{s.t. } t \neq 0$$

$$\text{Assume } A \neq B \text{ for contradiction}$$

$$f(x+h) = f(x) + Ah + r_A(h) = f(x) + Av + \dots$$

$$\text{dividing by } t:$$

$$\frac{f(x+tv)}{t} = \frac{f(x)}{t} + Av + \dots$$

$$\text{since } A \neq B,$$

$$Ah \neq Bh$$

$$Atv \neq Btv$$

$$f(x) + Atv \neq f(x) + Btv$$

$$\frac{f(x)}{t} + Av \neq \frac{f(x)}{t} + Bv$$

$$\text{thus } \frac{\|r_A(tv)\|}{\|tv\|}$$

$$\text{so } \frac{f(x+tv)}{t} = \dots$$

$$\frac{f(x+tv)}{t} = \dots$$

$$\text{thus } \frac{f(x)}{t} \dots$$

$$\text{but this } \dots$$
$$\text{assumption}$$

<!-- page 22 -->

`...` $\le \frac{|t|}{|t|}$

Since $\|tv\| = |t|\|v\|$, we rewrite this in terms of the remainder limits by multiplying
and dividing by $\|v\| > 0$:

$$\|(A - B)v\| \le \|v\| \left( \frac{\|r_B(tv)\|}{\|tv\|} + \frac{\|r_A(tv)\|}{\|tv\|} \right)$$

As $t \to 0$, $h = tv \to 0$. Taking the limit of both sides as $t \to 0$:

$$\|(A - B)v\| \le \|v\| \left( \lim_{t \to 0} \frac{\|r_B(tv)\|}{\|tv\|} + \lim_{t \to 0} \frac{\|r_A(tv)\|}{\|tv\|} \right) = \|v\|(0 + 0) = 0$$

Since the norm is non-negative, $\|(A - B)v\| = 0$, which implies:

$$(A - B)v = 0$$

**Why $(A - B)v = 0$ for all $v$ implies $A = B$**
* **Definition of Operator Equality:** Two functions (or linear transformations) $A, B : \mathbb{R}^n \to \mathbb{R}^m$ are defined to be equal if and only if they agree on their entire domain:
  $$Av = Bv \quad \forall v \in \mathbb{R}^n$$
  Since $(A - B)v = 0 \iff Av = Bv$ holds for every arbitrary $v \in \mathbb{R}^n$, the linear operators $A$ and $B$ are identical.
* **Basis Representation:** In terms of standard coordinates, if $(A - B)e_j = 0$ for each standard basis vector $e_j \in \mathbb{R}^n (j = 1, \dots, n)$, every column of the matrix representation of $(A - B)$ is the zero vector in $\mathbb{R}^m$, establishing that $A - B = 0_{m \times n} \implies A = B$. $\blacksquare$

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

$\frac{r_A(tv)}{t}$

$\frac{r_A(tv)}{t}$

$\frac{f(v)}{t} \ge 0$

$\frac{f(x)}{t} + Av$

$\frac{f(x)}{t} + Bv$

$\text{by same}$

$\text{steps}$

$Av = \frac{f(x)}{t} + Bv$

$Av = Bv$

$Av - Bv = 0$

$(A - B)v = 0$

$\text{contradicts}$

$A \neq B,$

$A - B$

Real_Analysis_PS Page 22

<!-- page 23 -->

**Problem 8. Directional derivatives are not enough**

Consider

$$f(x, y) = \begin{cases} \frac{x^2 y}{x^2 + y^2}, & (x, y) \neq (0, 0), \\ 0, & (x, y) = (0, 0). \end{cases}$$

(a) Prove that $f$ is continuous at $(0, 0)$.

(b) Compute
$$f_x(0, 0), \quad f_y(0, 0).$$

(c) For an arbitrary direction $v = (a, b)$, compute
$$D_v f(0, 0).$$

(d) Show that every directional derivative at the origin exists.

(e) Is the map
$$v \longmapsto D_v f(0, 0)$$
linear?

(f) Deduce that $f$ is not differentiable at the origin.

Conclude by explaining, in your own words, the distinction among
$$\text{partial derivatives}, \quad \text{directional derivatives}, \quad \text{the derivative } Df(x).$$

---

8)
$$f(x, y) = \begin{cases} \frac{x^2 y}{x^2 + y^2} & (x, y) \neq 0 \\ 0 & (x, y) = 0 \end{cases} \quad f : \mathbb{R}^2 \to \mathbb{R}$$

a) wts $f$ is continuous at $(0, 0)$

if $f$ is cont, then $\forall \epsilon > 0$,
$\exists \delta > 0$ s.t. if $|(x, y) - L| < \delta$
then $|f(x, y) - f(L)| < \epsilon$

$f(x, y) = 0$. pick $\delta = (\epsilon, \epsilon)$

if $|(0, 0) - (0, 0)| < \delta = (\epsilon, \epsilon)$

$(0, 0) < \delta = (\epsilon, \epsilon)$

then $|f(0, 0) - f(0, 0)| < \epsilon$

$0 < \epsilon$

$L = (0, 0)$ s.he $\lim_{(x, y) \to (0, 0)} \frac{x^2 y}{x^2 + y^2} = 0$
by L'Hopital's

b) $f_x(0, 0)$ partial deriv. the

$$f_x(x, y) = \begin{cases} \frac{2xy(x^2 + y^2) - (2x)(x^2 y)}{(x^2 + y^2)^2} = \frac{2x^3 y + 2xy^3 - 2x^3 y}{(x^2 + y^2)^2} = \frac{2xy^3}{(x^2 + y^2)^2} & \text{if } (x, y) \neq (0, 0) \\ 0 & \text{if } (x, y) = (0, 0) \end{cases}$$

<!-- page 24 -->

**Critique of Handwritten Attempt**
* **Invalid Choice of $\delta$:** In a metric space $(\mathbb{R}^2, \|\cdot\|)$, the radius $\delta$ must be a strictly positive real scalar ($\delta > 0$), not a 2D vector like $(\epsilon, \epsilon)$.
* **Circular / Trivialized Evaluation:** Substituting $(x, y) = (0, 0)$ directly into the distance condition reduces the statement to testing $|0 - 0| < \epsilon$, which only checks that $f(0,0)$ equals itself. A continuity proof must establish that $|f(x, y) - f(0, 0)| < \epsilon$ for *all* $(x, y)$ in a punctured neighborhood $0 < \sqrt{x^2 + y^2} < \delta$.
* **Misapplication of L'Hôpital's Rule:** L'Hôpital's rule is valid only for single-variable limits. Multivariable limits $\lim_{(x, y) \to (0, 0)}$ cannot be evaluated by taking standard single-variable quotients of derivatives.
* **Target Value Conflation:** The function maps to $\mathbb{R}$ ($m = 1$), so the limit value is the scalar $L = 0$, not the vector $(0, 0)$.

---

**Formal Proof of Part (a)**
**Proposition:** The function $f : \mathbb{R}^2 \to \mathbb{R}$ defined by

$$f(x, y) = \begin{cases} \frac{x^2 y}{x^2 + y^2}, & (x, y) \neq (0, 0) \\ 0, & (x, y) = (0, 0) \end{cases}$$

is continuous at $(0, 0)$.

*Proof via $\epsilon$-$\delta$ and Squeeze Argument:*
To show continuity at $(0, 0)$, we must prove:

$$\lim_{(x, y) \to (0, 0)} f(x, y) = f(0, 0) = 0$$

which requires showing that for every $\epsilon > 0$, there exists $\delta > 0$ such that:

$$0 < \|(x, y) - (0, 0)\| = \sqrt{x^2 + y^2} < \delta \implies |f(x, y) - 0| < \epsilon$$

1. **Bounding the Function:**
   For any $(x, y) \neq (0, 0)$, observe that $x^2 \le x^2 + y^2$ (since $y^2 \ge 0$). Thus:

   $$\frac{x^2}{x^2 + y^2} \le 1$$

2. **Estimating the Error:**
   Using this bound:

   $$|f(x, y) - 0| = \left| \frac{x^2 y}{x^2 + y^2} \right| = \frac{x^2}{x^2 + y^2} |y| \le 1 \cdot |y| = |y|$$

   Furthermore, $|y| = \sqrt{y^2} \le \sqrt{x^2 + y^2} = \|(x, y)\|$. Therefore:

   $$|f(x, y)| \le \|(x, y)\|$$

3. **Selection of $\delta$:**
   Given any $\epsilon > 0$, choose $\delta = \epsilon$.
   If $0 < \|(x, y)\| < \delta$, then:

   $$|f(x, y) - 0| \le \|(x, y)\| < \delta = \epsilon$$

---

To evaluate partial and directional derivatives at a piecewise point like $(0,0)$, do not differentiate the algebraic expression for $(x, y) \neq (0, 0)$ via the quotient rule. Instead, apply the **limit definition of the derivative** directly at the base point.

**Part (b): Compute $f_x(0,0)$ and $f_y(0,0)$**

Using the difference quotient definition of partial derivatives at $(0,0)$:

* **Partial with respect to $x$:**

  $$f_x(0,0) = \lim_{h \to 0} \frac{f(0 + h, 0) - f(0,0)}{h} = \lim_{h \to 0} \frac{f(h, 0) - 0}{h}$$

  For $h \neq 0$, the function value along the x-axis is:

  $$f(h, 0) = \frac{h^2 \cdot 0}{h^2 + 0^2} = 0$$

<!-- page 25 -->

$$f_x(0,0) = 0$$

$$f_y(0,0) = 0 \quad \text{by symmetry}$$

c) for arbitrary $v = (a, b)$

$$D_v f(0,0) = (a, b) \quad ?$$

d) WTS every directional derivative at the origin exists

isn't that just part (c)?

e) let $v \longrightarrow D_v f(0,0)$

be a map $G$ from arbitrary vector $v$ to the directional derivative at the vector at the origin

$G$ is not a linear mapping since $\dots$

f) $f$ is not differentiable at the origin since

g) partial derivatives are the approx of the change in a funct in

<!-- page 26 -->

Therefore:

$$f_x(0,0) = \lim_{h \to 0} \frac{0}{h} = \lim_{h \to 0} 0 = 0$$

*   **Partial with respect to $y$:**

    $$f_y(0,0) = \lim_{k \to 0} \frac{f(0, 0 + k) - f(0,0)}{k} = \lim_{k \to 0} \frac{f(0, k) - 0}{k}$$

    For $k \neq 0$, the function value along the y-axis is:

    $$f(0, k) = \frac{0^2 \cdot k}{0^2 + k^2} = 0$$

Therefore:

$$f_y(0,0) = \lim_{k \to 0} \frac{0}{k} = \lim_{k \to 0} 0 = 0$$

**Part (c): Compute $D_v f(0,0)$ for an arbitrary direction $v = (a, b)$**

Let $v = (a, b) \in \mathbb{R}^2$ be an arbitrary vector. The directional derivative at $(0,0)$ in direction $v$ is given by:

$$D_v f(0,0) = \lim_{t \to 0} \frac{f((0,0) + t(a, b)) - f(0,0)}{t} = \lim_{t \to 0} \frac{f(ta, tb)}{t}$$

*   **Case 1:** $v = (0,0)$

    $$D_{(0,0)} f(0,0) = \lim_{t \to 0} \frac{f(0,0)}{t} = 0$$

*   **Case 2:** $v = (a, b) \neq (0,0)$

    For $t \neq 0$, $(ta, tb) \neq (0,0)$. Evaluating $f(ta, tb)$:

    $$f(ta, tb) = \frac{(ta)^2 (tb)}{(ta)^2 + (tb)^2} = \frac{t^3 a^2 b}{t^2(a^2 + b^2)} = t \frac{a^2 b}{a^2 + b^2}$$

    Substituting this into the limit:

    $$D_v f(0,0) = \lim_{t \to 0} \frac{t \frac{a^2 b}{a^2 + b^2}}{t} = \lim_{t \to 0} \frac{a^2 b}{a^2 + b^2} = \frac{a^2 b}{a^2 + b^2}$$

Combining both cases (since $\frac{a^2 b}{a^2 + b^2}$ evaluates to $0$ if $a = 0$ or $b = 0$):

$$D_v f(0,0) = \begin{cases} \frac{a^2 b}{a^2 + b^2}, & (a, b) \neq (0,0) \\ 0, & (a, b) = (0,0) \end{cases}$$

**Part (d): Show that every directional derivative at the origin exists**

*   For the zero vector $v = (0,0)$, $D_{(0,0)} f(0,0) = 0 \in \mathbb{R}$.
*   For every non-zero direction $v = (a, b) \in \mathbb{R}^2 \setminus \{(0,0)\}$, $a^2 + b^2 = \|v\|^2 > 0$. The expression $\frac{a^2 b}{a^2 + b^2}$ is a well-defined real number with no dependence on $t$.

Because the difference quotient limit converges to a finite real number for every vector $v \in \mathbb{R}^2$, the directional derivative $D_v f(0,0)$ exists for all directions $v \in \mathbb{R}^2$.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

**Part (e): Linearity of the Directional Derivative Map**

The map $T : \mathbb{R}^2 \to \mathbb{R}$ defined by $T(v) = D_v f(0,0)$ is **not linear**.

To verify linearity, $T$ must satisfy additivity: $T(u + w) = T(u) + T(w)$ for all $u, v \in \mathbb{R}^2$.

*   Let $u = (1,0)$ and $w = (0,1)$.

    $$T(u) = D_{(1,0)} f(0,0) = \frac{1^2 \cdot 0}{1^2 + 0^2} = 0$$

    $$T(w) = D_{(0,1)} f(0,0) = \frac{0^2 \cdot 1}{0^2 + 1^2} = 0$$

    $$T(u) + T(w) = 0 + 0 = 0$$

*   Consider the sum $u + w = (1,1)$:

    $$T(u + w) = D_{(1,1)} f(0,0) = \frac{1^2 \cdot 1}{1^2 + 1^2} = \frac{1}{2}$$

Because $T(u + w) = \frac{1}{2} \neq 0 = T(u) + T(w)$, additivity fails, and the map $v \mapsto D_v f(0,0)$ is non-linear.

---

**Part (f): Deducing Non-Differentiability at the Origin**

**Theorem:** If a function $f : \mathbb{R}^n \to \mathbb{R}^m$ is differentiable at $x_0$, then for every direction $v \in \mathbb{R}^n$, the directional derivative $D_v f(x_0)$ exists and satisfies:

$$D_v f(x_0) = Df(x_0) \cdot v$$

where $Df(x_0)$ is the total derivative (a linear transformation / Jacobian matrix). Consequently, the map $v \mapsto D_v f(x_0)$ **must be linear**.

*   **Deduction:** From Part (e), the directional derivative operator $v \mapsto D_v f(0,0)$ is non-linear. By contraposition, $f$ cannot be differentiable at $(0,0)$.
*   **Direct Verification via Remainder:** If $f$ were differentiable at $(0,0)$, its total derivative candidate would be $A = \nabla f(0,0) = (f_x(0,0), f_y(0,0)) = (0,0)$. The linear approximation error is:

    $$r(h) = f(h_1, h_2) - f(0,0) - Ah = \frac{h_1^2 h_2}{h_1^2 + h_2^2} - 0 - 0 = \frac{h_1^2 h_2}{h_1^2 + h_2^2}$$

    Taking $h = (t, t)$ along the diagonal as $t \to 0^+$:

    $$\frac{\|r(h)\|}{\|h\|} = \frac{\frac{t^3}{2t^2}}{\sqrt{t^2 + t^2}} = \frac{\frac{t}{2}}{t \sqrt{2}} = \frac{1}{2\sqrt{2}} \neq 0$$

    Since $\lim_{h \to 0} \frac{\|r(h)\|}{\|h\|} \neq 0$, $f$ is not differentiable at $(0,0)$.

Real_Analysis_PS Page 26

<!-- page 27 -->

g) partial derivatives are
of the change in a funct in
the direction of an axis
according to the basis

directional der. are approximations
of the funct in any arbitrary
direction, not just axes

the total derivative $Df(x)$ describes
a linear approximation in any dir

---

### **Problem 9. Continuous partial derivatives imply differentiability**

Suppose
$$f : \mathbb{R}^2 \to \mathbb{R}$$
has partial derivatives in a neighborhood of $(a, b)$, and suppose $f_x$ and $f_y$ are continuous at $(a, b)$.
Prove that $f$ is differentiable at $(a, b)$.

Begin by writing
$$f(a+h, b+k) - f(a, b) = [f(a+h, b+k) - f(a, b+k)]$$
$$+ [f(a, b+k) - f(a, b)].$$

1. Apply the one-dimensional mean value theorem to the two differences.

2. Show that, for suitable intermediate points $\xi$ and $\eta$,
$$f(a+h, b+k) - f(a, b) = f_x(\xi, b+k)h + f_y(a, \eta)k.$$

3. Subtract
$$f_x(a, b)h + f_y(a, b)k.$$

4. Bound the absolute value of the remaining remainder by
$$|f_x(\xi, b+k) - f_x(a, b)||h| + |f_y(a, \eta) - f_y(a, b)||k|.$$

5. Divide by
$$\sqrt{h^2 + k^2}$$
and complete the proof.

Indicate precisely where continuity of the partial derivatives is used.

---

9) Cont partial derivatives imply differentiability

$f : \mathbb{R}^2 \to \mathbb{R}$
has partial derivatives in neighb of $(a, b)$
& $f_x, f_y$ cont at $(a, b)$

wts $f$ is differentiable at $(a, b)$

For small perturbation of $(a, b)$
by $(h, k) \in \mathbb{R}^2$,

$$f(a+h, b+k) - f(a, b) = [f(a+h, b+k) - f(a, b+k)]$$
$$+ [f(a, b+k) - f(a, b)]$$

<!-- page 28 -->

$$\frac{\|r(h)\|}{\|h\|} = \frac{\frac{t^3}{2t^2}}{\sqrt{t^2 + t^2}} = \frac{\frac{t}{2}}{t\sqrt{2}} = \frac{1}{2\sqrt{2}} \neq 0$$

Since $\lim_{h \to 0} \frac{\|r(h)\|}{\|h\|} \neq 0$, $f$ is not differentiable at $(0,0)$.

### **Distinction Among Partial Derivatives, Directional Derivatives, and the Derivative $Df(x)$**
* **Partial Derivatives ($f_{x_i}(x)$):** 1-dimensional rates of change restricted exclusively along the standard coordinate axes (the basis vectors $e_i$). They provide purely axis-aligned information and ignore behavior along all other trajectories.
* **Directional Derivatives ($D_v f(x)$):** 1-dimensional rates of change along an arbitrary straight-line vector $v$. While they capture directional variation along all straight lines through $x$, they remain isolated 1D limits and do not enforce any uniform coordination across different directions.
* **The Derivative ($Df(x)$):** A global, $n$-dimensional **linear map** (represented by the Jacobian matrix) that provides a uniform first-order tangent hyperplane approximation to the graph:

$$\lim_{h \to 0} \frac{\|f(x+h) - f(x) - Df(x)h\|}{\|h\|} = 0$$

Differentiability requires that the error vanishes uniformly from *all* paths approaching $x$ (curved or straight), binding all directional derivatives together into a single coherent linear operator.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

The equation decomposes a 2D diagonal displacement $(h, k)$ into two 1D, axis-aligned steps:

$$f(a+h, b+k) - f(a, b) = \underbrace{[f(a+h, b+k) - f(a, b+k)]}_{\text{Step 1: vary } x \text{ with } y \text{ held fixed at } b+k} + \underbrace{[f(a, b+k) - f(a, b)]}_{\text{Step 2: vary } y \text{ with } x \text{ held fixed at } a}$$

This is powerful because the **1D Mean Value Theorem (MVT)** can only be applied when one variable changes at a time. Breaking the joint increment into sequential 1-variable steps converts the 2D problem into two standard single-variable calculus problems, directly linking the global increment to partial derivatives.

### **Step-by-Step Proof of Problem 9**
**Proposition:** If $f : \mathbb{R}^2 \to \mathbb{R}$ has partial derivatives in an open neighborhood $U$ of $(a, b)$, and $f_x, f_y$ are continuous at $(a, b)$, then $f$ is differentiable at $(a, b)$.

*Proof:*

1. **Applying the 1D Mean Value Theorem:**
   Choose $(h, k) \neq (0,0)$ sufficiently small such that the rectangular path from $(a, b)$ to $(a+h, b+k)$ remains entirely within $U$.
   * Define the single-variable function $g(t) = f(t, b+k)$ on the interval between $a$ and $a+h$. Since $g$ is differentiable on this interval, the 1D MVT guarantees the existence of an intermediate point $\xi$ strictly between $a$ and $a+h$ such that:
     $$f(a+h, b+k) - f(a, b+k) = g(a+h) - g(a) = g'(\xi)h = f_x(\xi, b+k)h$$
   * Define $u(s) = f(a, s)$ on the interval between $b$ and $b+k$. By the 1D MVT, there exists an intermediate point $\eta$ strictly between $b$ and $b+k$ such that:
     $$f(a, b+k) - f(a, b) = u(b+k) - u(b) = u'(\eta)k = f_y(a, \eta)k$$

2. **Summing the Increments:**
   Substituting these into the identity:
   $$f(a+h, b+k) - f(a, b) = f_x(\xi, b+k)h + f_y(a, \eta)k$$

3. **Defining the Remainder Term:**
   To establish differentiability with candidate linear map $A = \begin{pmatrix} f_x(a, b) & f_y(a, b) \end{pmatrix}$, subtract $f_x(a, b)h + f_y(a, b)k$ from both sides:
   $$r(h, k) = f(a+h, b+k) - f(a, b) - [f_x(a, b)h + f_y(a, b)k]$$

   $$r(h, k) = [f_x(\xi, b+k) - f_x(a, b)]h + [f_y(a, \eta) - f_y(a, b)]k$$

4. **Bounding the Remainder:**
   Taking the absolute value and applying the triangle inequality:
   $$|r(h, k)| \le |f_x(\xi, b+k) - f_x(a, b)||h| + |f_y(a, \eta) - f_y(a, b)||k|$$

5. **Dividing by $\|(h, k)\| = \sqrt{h^2 + k^2}$ and Taking the Limit:**
   Since $|h| \le \sqrt{h^2 + k^2}$ and $|k| \le \sqrt{h^2 + k^2}$, we have $\frac{|h|}{\sqrt{h^2 + k^2}} \le 1$ and $\frac{|k|}{\sqrt{h^2 + k^2}} \le 1$:
   $$\frac{|r(h, k)|}{\sqrt{h^2 + k^2}} \le |f_x(\xi, b+k) - f_x(a, b)| + |f_y(a, \eta) - f_y(a, b)|$$

   As $(h, k) \to (0,0)$:
   * $\xi \to a$ and $(b+k) \to b \implies (\xi, b+k) \to (a, b)$
   * $\eta \to b \implies (a, \eta) \to (a, b)$

   **Where continuity is used:**
   Because $f_x$ and $f_y$ are **continuous at $(a, b)$**:
   $$\lim_{(h,k) \to (0,0)} f_x(\xi, b+k) = f_x(a, b) \implies |f_x(\xi, b+k) - f_x(a, b)| \to 0$$
   $$\lim_{(h,k) \to (0,0)} f_y(a, \eta) = f_y(a, b) \implies |f_y(a, \eta) - f_y(a, b)| \to 0$$

   Therefore, $\lim_{(h,k) \to (0,0)} \frac{|r(h, k)|}{\sqrt{h^2 + k^2}} = 0$, proving that $f$ is differentiable at $(a, b)$. $\blacksquare$

<!-- page 29 -->

## 4 Restricting Multivariate Problems to Lines

**Problem 10. The multivariate mean-value idea**

Let

$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}$$

be differentiable, and suppose the entire line segment joining $a$ and $b$ lies in $U$.

Define

$$g(t) = f(a + t(b - a)), \quad 0 \le t \le 1.$$

(a) Prove that

$$g'(t) = Df(a + t(b - a))(b - a).$$

```
[Handwritten marginalia at top of page]
Applying mvt theorem in each dim
if f(a,b) cont. then \forall a_0, a_1 \frac{f(a_1) - f(a_0)}{f(a_1) - f(a_0)}
w/ a_0 \le a_1
if a_t \in [a_0, a_1],
f(a_t) \in [f(a_0), f(a_1)]
holding b constant
thus for intermediate points \xi + \eta
f(a+h, b+k) - f(a,b) = f_x(\xi, b+d)...
```

---

> **Approach 1: Using the Chain Rule**
> Define the affine curve $\gamma : [0, 1] \to \mathbb{R}^n$ by:
> $$\gamma(t) = a + t(b - a)$$
> * The map $\gamma$ is differentiable on $(0, 1)$ with derivative (velocity vector):
>   $$\gamma'(t) = b - a$$
> * Since $g(t) = (f \circ \gamma)(t)$ and $f$ is differentiable on $U$, the multivariable chain rule applies directly:
>   $$g'(t) = Df(\gamma(t)) \cdot \gamma'(t) = Df(a + t(b - a))(b - a)$$
> 
> **Approach 2: From First Principles (Linear Approximation / Remainder Definition)**
> Fix $t \in (0, 1)$ and let $x(t) = a + t(b - a)$. For any non-zero scalar increment $\Delta t$, the perturbed point is:
> $$x(t + \Delta t) = a + (t + \Delta t)(b - a) = x(t) + \Delta t(b - a)$$
> Let $h = \Delta t(b - a) \in \mathbb{R}^n$. Because $f$ is differentiable at $x(t)$, we expand $f(x(t) + h)$ using its linear approximation:
> $$f(x(t) + h) - f(x(t)) = Df(x(t))h + r(h)$$
> where $\lim_{h \to 0} \frac{|r(h)|}{\|h\|} = 0$.
> 
> 1. **Substitute $h = \Delta t(b - a)$:**
>    $$g(t + \Delta t) - g(t) = Df(x(t))(\Delta t(b - a)) + r(\Delta t(b - a))$$
> 2. **Apply Linearity of the Operator $Df(x(t))$:**
>    $$g(t + \Delta t) - g(t) = \Delta t \cdot Df(x(t))(b - a) + r(\Delta t(b - a))$$
> 3. **Form the Difference Quotient:**
>    Divide through by $\Delta t \neq 0$:
>    $$\frac{g(t + \Delta t) - g(t)}{\Delta t} = Df(x(t))(b - a) + \frac{r(\Delta t(b - a))}{\Delta t}$$
> 4. **Evaluate the Limit as $\Delta t \to 0$:**
>    Examine the error term:
>    $$\left| \frac{r(\Delta t(b - a))}{\Delta t} \right| = \|b - a\| \cdot \frac{|r(\Delta t(b - a))|}{\|\Delta t(b - a)\|}$$
>    Since $\Delta t \to 0 \implies h = \Delta t(b - a) \to 0$, the differentiability of $f$ ensures:
>    $$\lim_{\Delta t \to 0} \frac{|r(\Delta t(b - a))|}{\|\Delta t(b - a)\|} = 0$$
>    Therefore:
>    $$g'(t) = \lim_{\Delta t \to 0} \frac{g(t + \Delta t) - g(t)}{\Delta t} = Df(x(t))(b - a) = Df(a + t(b - a))(b - a) \quad \blacksquare$$

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

(b) Apply the one-dimensional mean value theorem to show that there exists a point $c$ on the segment from $a$ to $b$ such that

$$f(b) - f(a) = Df(c)(b - a).$$

---

> **Part (b): Mean Value Theorem on the Segment**
> 1. **Check MVT Hypotheses:**
>    * The single-variable function $g(t) = f(a + t(b - a))$ is continuous on $[0, 1]$ (composition of continuous maps).
>    * From part (a), $g$ is differentiable on $(0, 1)$.
> 2. **Apply 1D Mean Value Theorem:**
>    There exists some $\tau \in (0, 1)$ such that:
>    $$g(1) - g(0) = g'(\tau)(1 - 0)$$
>    Evaluating $g$ at the endpoints:
>    $$g(1) = f(a + 1(b - a)) = f(b)$$
>    $$g(0) = f(a + 0(b - a)) = f(a)$$
>    Substituting $g'(\tau)$ from part (a):
>    $$f(b) - f(a) = Df(a + \tau(b - a))(b - a)$$
>    Define $c = a + \tau(b - a)$. Since $\tau \in (0, 1)$, $c$ lies strictly on the line segment joining $a$ and $b$. Thus:
>    $$f(b) - f(a) = Df(c)(b - a) \quad \blacksquare$$

<!-- page 30 -->

As $(h,k) \to (0,0)$:
$\circ$ $\xi \to a$ and $(b+k) \to b \implies (\xi, b+k) \to (a, b)$
$\circ$ $\eta \to b \implies (a, \eta) \to (a, b)$
**Where continuity is used:**
Because $f_x$ and $f_y$ are **continuous at $(a, b)$**:
$$\lim_{(h,k)\to(0,0)} |f_x(\xi, b+k) - f_x(a, b)| = 0 \quad \text{and} \quad \lim_{(h,k)\to(0,0)} |f_y(a, \eta) - f_y(a, b)| = 0$$

Therefore:
$$\lim_{(h,k)\to(0,0)} \frac{|r(h, k)|}{\sqrt{h^2 + k^2}} = 0$$

This satisfies the definition of total differentiability, proving $f$ is differentiable at $(a, b)$ with derivative $Df(a, b) = (f_x(a, b), \ f_y(a, b))$. $\blacksquare$

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

<!-- page 31 -->

(c) Deduce the bound

$$|f(b) - f(a)| \le \sup_{z \in [a, b]} \|Df(z)\| \|b - a\|.$$

---

(d) Suppose now that $U$ is convex and

$$Df(x) = 0 \quad \text{for every } x \in U.$$

Prove that $f$ is constant on $U$.

*Proof technique to remember. A useful strategy in multivariate calculus is*

$$\text{multivariate problem} \longrightarrow \text{restrict to a line} \longrightarrow \text{apply one-variable calculus.}$$

---

**Problem 11. If the Hessian vanishes, the function is affine**

Let $U \subseteq \mathbb{R}^n$ be open and convex. Suppose

$$f : U \to \mathbb{R}$$

is $C^2$ and

$$H_f(x) = 0 \quad \text{for every } x \in U.$$

Prove that there exist $a \in \mathbb{R}^n$ and $b \in \mathbb{R}$ such that

$$f(x) = a^T x + b \quad \text{for every } x \in U.$$

*Guidance. Treat*

$$\nabla f : U \to \mathbb{R}^n$$

as a function in its own right.
What is

$$D(\nabla f)(x)?$$

Use the previous problem to show that $\nabla f$ is constant. Then consider

$$g(x) = f(x) - a^T x.$$

---

$$g(1) - g(0) = g'(\tau)(1 - 0)$$

3. **Substitute Definitions:**
   $\circ$ $g(1) = f(a + 1(b - a)) = f(b)$
   $\circ$ $g(0) = f(a + 0(b - a)) = f(a)$
   $\circ$ From part (a), $g'(\tau) = Df(a + \tau(b - a))(b - a)$

4. **Define the Intermediate Point:**
   Set $c = a + \tau(b - a)$. Since $\tau \in (0, 1)$, $c$ is a point lying strictly on the open line segment joining $a$ and $b$ (denoted $c \in (a, b)$).
   Substituting these in yields:

$$f(b) - f(a) = Df(c)(b - a)$$

**Part (c): Deducing the Upper Bound**

1. **Take the Absolute Value:**
   From part (b), for the point $c \in [a, b]$:

$$|f(b) - f(a)| = |Df(c)(b - a)|$$

2. **Apply the Operator Norm Inequality:**
   For any linear map $A : \mathbb{R}^n \to \mathbb{R}$ and vector $v \in \mathbb{R}^n$, the operator norm $\|A\| = \sup_{\|u\|=1} |Au|$ satisfies:

$$|Av| \le \|A\| \|v\|$$

Applying this with $A = Df(c)$ and $v = b - a$:

$$|Df(c)(b - a)| \le \|Df(c)\| \|b - a\|$$

3. **Bound by the Supremum Over the Segment:**
   Because $c \in [a, b]$, the quantity $\|Df(c)\|$ is bounded by the supremum over all points $z$ on the line segment $[a, b]$:

$$\|Df(c)\| \le \sup_{z \in [a, b]} \|Df(z)\|$$

Combining these inequalities gives:

$$|f(b) - f(a)| \le \sup_{z \in [a, b]} \|Df(z)\| \|b - a\| \quad \blacksquare$$

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

To establish the claim:
1. Let $a, b \in U$ be arbitrary points.
2. Because $U$ is convex, the entire line segment $[a, b] = \{a + t(b - a) : t \in [0, 1]\}$ is contained in $U$.
3. Since $f$ is differentiable on $U$, it is differentiable at every point along the segment $[a, b]$. By Part (b), there exists some intermediate point $c \in (a, b) \subseteq U$ such that:

$$f(b) - f(a) = Df(c)(b - a)$$

4. By assumption, $Df(x) = 0$ (the zero linear operator) for every $x \in U$. Since $c \in U$, we have $Df(c) = 0$.
5. Applying the zero transformation to $(b - a)$ gives:

$$f(b) - f(a) = 0(b - a) = 0 \implies f(b) = f(a)$$

6. Since $a$ and $b$ were chosen arbitrarily in $U$, fixing a base point $x_0 \in U$ yields $f(x) = f(x_0)$ for all $x \in U$. Hence, $f$ is constant on $U$.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

To solve Problem 11, apply the result of Problem 10(d) twice in succession: first to the vector-valued gradient map $\nabla f$, and second to the scalar-valued adjusted function $g(x)$.

**Step 1: Relate the Hessian to the Derivative of the Gradient**
Define the gradient mapping:

$$F : U \to \mathbb{R}^n, \quad F(x) = \nabla f(x) = \begin{pmatrix} \frac{\partial f}{\partial x_1}(x) \\ \vdots \\ \frac{\partial f}{\partial x_n}(x) \end{pmatrix}$$

Because $f$ is $C^2$, each coordinate function $F_i(x) = \frac{\partial f}{\partial x_i}(x)$ is $C^1$ and therefore differentiable on $U$. The total derivative of this vector-valued function $F$ is its Jacobian matrix, which is precisely the Hessian of $f$:

$$D(\nabla f)(x) = J_F(x) = H_f(x)$$

By assumption, $H_f(x) = 0_{n \times n}$ for all $x \in U$. Applying Problem 10(d) component-wise to each $F_i$ (or directly to the vector map on the convex domain $U$) gives:

$$D(F_i)(x) = 0 \implies F_i(x) \text{ is constant on } U \quad \forall i = 1, \dots, n$$

Thus, the entire gradient vector is constant across $U$:

$$\nabla f(x) = a \quad \text{for some fixed vector } a \in \mathbb{R}^n$$

**Step 2: Construct the Auxiliary Function $g(x)$**
Consider the function suggested in the guidance:

$$g : U \to \mathbb{R}, \quad g(x) = f(x) - a^T x$$

Compute the total derivative (or gradient) of $g$:

$$Dg(x) = Df(x) - a^T$$

In gradient terms:

$$\nabla g(x) = \nabla f(x) - a$$

Since $\nabla f(x) = a$ for all $x \in U$:

$$\nabla g(x) = a - a = 0 \quad \forall x \in U$$

**Step 3: Apply Problem 10(d) to $g(x)$**
Since $U$ is convex and $Dg(x) = 0$ everywhere on $U$, Problem 10(d) implies that $g(x)$ must be constant on $U$:

$$\exists b \in \mathbb{R} \quad \text{such that} \quad g(x) = b \quad \forall x \in U$$

Substituting $g(x) = f(x) - a^T x$ yields:

$$f(x) - a^T x = b \implies f(x) = a^T x + b \quad \forall x \in U \quad \blacksquare$$

Real_Analysis_PS Page 31

<!-- page 32 -->

Real_Analysis_PS Page 32

<!-- page 33 -->

$$g(x) = b \quad \text{for some constant scalar } b \in \mathbb{R}$$
Substituting back into the definition of $g(x)$:
$$f(x) - a^T x = b \implies f(x) = a^T x + b \quad \forall x \in U \quad \blacksquare$$

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

**Problem 12. Taylor's theorem in several variables**

Let
$$f : U \subseteq \mathbb{R}^n \to \mathbb{R}$$
be $C^2$, and suppose that the line segment from $x$ to $x + h$ lies entirely in $U$.
Define
$$g(t) = f(x + th), \quad 0 \le t \le 1.$$

(a) Show that
$$g'(t) = \nabla f(x + th)^T h.$$

(b) Show that
$$g''(t) = h^T H_f(x + th)h.$$

(c) Apply the one-dimensional Taylor theorem to $g$ between $0$ and $1$ to prove that, for some $\theta \in (0, 1)$,
$$f(x + h) = f(x) + \nabla f(x)^T h + \frac{1}{2} h^T H_f(x + \theta h)h.$$

Why does the second-order term involve the scalar quadratic form
$$h^T H_f h$$
rather than merely the vector $H_f h$?

**Why the Gradient and Hessian Act on $h$**
The perturbation $h \in \mathbb{R}^n$ is not acting as an affine coordinate translation; it represents the **fixed direction and displacement vector** parameterizing the line segment $\gamma(t) = x + th$.
* **First Derivative / Linear Term:** Differentiating along the line $\gamma(t)$ projects the gradient $\nabla f$ onto the velocity vector $\gamma'(t) = h$, producing the scalar directional rate of change:
  $$g'(t) = \nabla f(\gamma(t))^T h$$
* **Second Derivative / Quadratic Term:** Differentiating $g'(t)$ a second time measures how this directional rate of change varies as you continue along that exact same vector $h$:
  $$g''(t) = \frac{d}{dt} \left[ \sum_{i=1}^n \frac{\partial f}{\partial x_i}(x + th)h_i \right] = \sum_{i=1}^n \sum_{j=1}^n \frac{\partial^2 f}{\partial x_j \partial x_i}(x + th)h_j h_i = h^T H_f(x + th)h$$

**Step-by-Step Proof of Problem 12**

**Part (a): Compute $g'(t)$**
Define $\gamma : [0, 1] \to U$ by $\gamma(t) = x + th$. Then $\gamma'(t) = h$.
By the chain rule:
$$g'(t) = Df(\gamma(t))\gamma'(t) = \nabla f(x + th)^T h = \sum_{i=1}^n \frac{\partial f}{\partial x_i}(x + th)h_i$$

**Part (b): Compute $g''(t)$**
Differentiating $g'(t)$ with respect to $t$:
$$g''(t) = \frac{d}{dt} \left( \sum_{i=1}^n \frac{\partial f}{\partial x_i}(x + th)h_i \right)$$
Applying the chain rule to each component map $x \mapsto \frac{\partial f}{\partial x_i}(x)$:
$$g''(t) = \sum_{i=1}^n \left( \sum_{j=1}^n \frac{\partial^2 f}{\partial x_j \partial x_i}(x + th)h_j \right) h_i = \sum_{i=1}^n \sum_{j=1}^n h_i \left[ H_f(x + th) \right]_{ij} h_j$$
In compact matrix notation:
$$g''(t) = h^T H_f(x + th)h$$

**Part (c): Apply 1D Taylor's Theorem to $g$**
The single-variable function $g : [0, 1] \to \mathbb{R}$ is $C^2$ on $[0, 1]$. By the single-variable Taylor Theorem with Lagrange remainder expanded around $t = 0$ and evaluated at $t = 1$, there exists some $\theta \in (0, 1)$ such that:
$$g(1) = g(0) + g'(0)(1 - 0) + \frac{1}{2} g''(\theta)(1 - 0)^2$$
Substituting the expressions for $g(t)$, $g'(t)$, and $g''(t)$:
* $g(1) = f(x + h)$
* $g(0) = f(x)$
* $g'(0) = \nabla f(x)^T h$
* $g''(\theta) = h^T H_f(x + \theta h)h$

Yields the multivariate Taylor expansion:
$$f(x + h) = f(x) + \nabla f(x)^T h + \frac{1}{2} h^T H_f(x + \theta h)h \quad \blacksquare$$

**Why the Second-Order Term is the Scalar Quadratic Form $h^T H_f h$ rather than $H_f h$**
* **Dimensional Consistency:** The function $f : U \to \mathbb{R}$ is scalar-valued. Thus, the quantity $f(x + h) - f(x)$ is a scalar in $\mathbb{R}$. The first-order term $\nabla f(x)^T h$ is an inner product (scalar).
  * $H_f(x)$ is an $n \times n$ matrix (the Hessian operator).
  * The product $H_f h$ is an $n \times 1$ vector (measuring the rate of change of the gradient vector $\nabla f$). You cannot add a vector $H_f h \in \mathbb{R}^n$ to a scalar $f(x) \in \mathbb{R}$.
* **Bilinear Form Mechanics:** The second total differential $D^2 f(x)$ is intrinsically a symmetric bilinear form $D^2 f(x) : \mathbb{R}^n \times \mathbb{R}^n \to \mathbb{R}$. Evaluating this bilinear form along the perturbation pair $(h, h)$ yields the quadratic form $D^2 f(x)(h, h) = h^T H_f(x)h \in \mathbb{R}$.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

* **Dimension Reduction ($\mathbb{R}^n \to \mathbb{R}$):** Proving Taylor's Theorem directly in $\mathbb{R}^n$ requires juggling multivariable limits and mixed partial derivatives simultaneously. The parameterized line $\gamma(t) = x + th$ restricts the $n$-dimensional scalar field $f(x)$ to a 1-dimensional slice, producing a standard single-variable function $g(t) = f(x + th)$.
* **Enabling Single-Variable Theorems:** Once the problem is reduced to the single-variable function $g$, you can immediately invoke classical 1D results—such as the 1D Mean Value Theorem and 1D Taylor Theorem with Lagrange remainder—which are already proven from single-variable real analysis.
* **Rigorous Application of the Chain Rule:** Viewing $\gamma(t)$ as an explicit curve from $\mathbb{R}$ into $\mathbb{R}^n$ allows you to apply the multivariate Chain Rule cleanly:
  $$g'(t) = Df(\gamma(t))\gamma'(t)$$
  Because $\gamma'(t) = h$ is the constant velocity vector of the path, the chain rule systematically pulls out the direction $h$ at each derivative order.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

## 5 Inverse and Implicit Functions

**Problem 13. Local versus global invertibility**

Consider

$$F(x, y) = \begin{pmatrix} e^x \cos y \\ e^x \sin y \end{pmatrix}.$$

**Problem 13: Local Versus Global Invertibility**
Let $F : \mathbb{R}^2 \to \mathbb{R}^2$ be defined by:
$$F(x, y) = \begin{pmatrix} F_1(x, y) \\ F_2(x, y) \end{pmatrix} = \begin{pmatrix} e^x \cos y \\ e^x \sin y \end{pmatrix}$$
*(Note: Identifying $\mathbb{R}^2 \cong \mathbb{C}$ with $z = x + iy$, this mapping represents the complex exponential $f(z) = e^z = e^x(\cos y + i \sin y)$).*

**Part (a): Compute $DF(x, y)$**
The total derivative matrix (Jacobian) is formed by the partial derivatives of the coordinate functions:

<!-- page 34 -->

**Dimension Reduction ($nD \to 1D$):** Proving Taylor's Theorem directly in $\mathbb{R}^n$ requires juggling multivariable limits and mixed partial derivatives simultaneously. The parameterized line $\gamma(t) = x + th$ restricts the $n$-dimensional scalar field $f : U \subseteq \mathbb{R}^n \to \mathbb{R}$ to a 1-dimensional slice, producing a standard single-variable function $g = f \circ \gamma : [0,1] \to \mathbb{R}$.

**Enabling Single-Variable Theorems:** Once the problem is reduced to the single-variable function $g(t)$, you can immediately invoke classical 1D results—such as the 1D Mean Value Theorem and 1D Taylor Theorem with Lagrange remainder—which are already proven from single-variable real analysis.

**Rigorous Application of the Chain Rule:** Viewing $\gamma(t)$ as an explicit curve from $[0,1]$ into $U$ allows you to apply the multivariate Chain Rule cleanly:

$$g'(t) = D(f \circ \gamma)(t) = Df(\gamma(t)) \cdot \gamma'(t)$$

Because $\gamma'(t) = \frac{d}{dt}(x + th) = h$ is the constant velocity vector of the path, the chain rule systematically pulls out the direction $h$ at each derivative order.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

**The Core Philosophy: Local Invertibility of Nonlinear Maps**
At this level, the **Inverse Function Theorem (IFT)** and the **Implicit Function Theorem** address a fundamental question: *When does the local behavior of a nonlinear mapping mirror the behavior of its linear approximation (the derivative operator)?*

If a linear transformation $T : \mathbb{R}^n \to \mathbb{R}^n$ (represented by an $n \times n$ matrix $A$) has $\det(A) \neq 0$, then $T$ is a global bijection with a continuous linear inverse $T^{-1}$. The IFT generalizes this principle locally to $C^1$ nonlinear mappings.

**The Inverse Function Theorem (IFT)**
**Statement:**
Let $U \subseteq \mathbb{R}^n$ be an open set, and let $f : U \to \mathbb{R}^n$ be a $C^1$-mapping. Suppose at a point $x_0 \in U$, the total derivative operator:

$$D f(x_0) : \mathbb{R}^n \to \mathbb{R}^n$$

---

**Inverse Function Theorem (IFT)**
* **Setting & Core Condition:** Let $f : U \subseteq \mathbb{R}^n \to \mathbb{R}^n$ be $C^1$ on open $U$. If $x_0 \in U$ satisfies:

  $$\det D f(x_0) \neq 0 \quad (\text{or } D f(x_0) \text{ is invertible})$$

  then there exist open neighborhoods $V \ni x_0$ and $W \ni f(x_0)$ such that $f : V \to W$ is a $C^1$-diffeomorphism.

* **Inverse Derivative Formula:** For $y \in W$ and $x = f^{-1}(y) \in V$:

<!-- page 35 -->

$$F(x,y) = \begin{pmatrix} F_1(x,y) \\ F_2(x,y) \end{pmatrix} = \begin{pmatrix} e^x \cos y \\ e^x \sin y \end{pmatrix}$$

*(Note: Identifying $\mathbb{R}^2 \cong \mathbb{C}$ with $z = x + iy$, this mapping represents the complex exponential $f(z) = e^z = e^x(\cos y + i \sin y)$).*

**Part (a): Compute $DF(x, y)$**

The total derivative matrix (Jacobian) is formed by the partial derivatives of the coordinate functions:

$$DF(x, y) = \begin{pmatrix} \frac{\partial F_1}{\partial x} & \frac{\partial F_1}{\partial y} \\[1ex] \frac{\partial F_2}{\partial x} & \frac{\partial F_2}{\partial y} \end{pmatrix} = \begin{pmatrix} e^x \cos y & -e^x \sin y \\ e^x \sin y & e^x \cos y \end{pmatrix}$$

**Part (b): Show that $\det DF(x, y) \neq 0$ for every $(x, y) \in \mathbb{R}^2$**

Compute the determinant:

$$\det DF(x, y) = (e^x \cos y)(e^x \cos y) - (-e^x \sin y)(e^x \sin y)$$

$$\det DF(x, y) = e^{2x} \cos^2 y + e^{2x} \sin^2 y = e^{2x}(\cos^2 y + \sin^2 y) = e^{2x}$$

Since the exponential function satisfies $e^{2x} > 0$ for all real $x \in \mathbb{R}$:

$$\det DF(x, y) = e^{2x} > 0 \quad \forall (x, y) \in \mathbb{R}^2$$

Thus, $\det DF(x, y) \neq 0$ everywhere on $\mathbb{R}^2$.

**Part (c): Precise Implication of the Inverse Function Theorem**

Because $F \in C^1(\mathbb{R}^2)$ and $\det DF(x_0, y_0) \neq 0$ at every point $(x_0, y_0) \in \mathbb{R}^2$, the Inverse Function Theorem guarantees that:

For every $(x_0, y_0) \in \mathbb{R}^2$, there exists an open neighborhood $U \subset \mathbb{R}^2$ containing $(x_0, y_0)$ and an open neighborhood $V \subset \mathbb{R}^2$ containing $F(x_0, y_0)$ such that the restricted map:

$$F|_U : U \to V$$

is a **$C^1$-diffeomorphism** (a bijective mapping with a continuously differentiable inverse $(F|_U)^{-1} : V \to U$).

**Part (d): Show that $F(x, y + 2\pi) = F(x, y)$**

Using the $2\pi$-periodicity of sine and cosine:

$$F(x, y + 2\pi) = \begin{pmatrix} e^x \cos(y + 2\pi) \\ e^x \sin(y + 2\pi) \end{pmatrix} = \begin{pmatrix} e^x \cos y \\ e^x \sin y \end{pmatrix} = F(x, y)$$

**Part (e): Global Injectivity and Consistency with the IFT**
* **Global Injectivity:** $F$ is **not** globally one-to-one (not injective). By Part (d), distinct points in $\mathbb{R}^2$ that differ by integer multiples of $2\pi$ in their second coordinate map to the exact same output:

$$F(0, 0) = \begin{pmatrix} 1 \\ 0 \end{pmatrix} = F(0, 2\pi), \quad \text{yet } (0, 0) \neq (0, 2\pi)$$

* **Resolution / Consistency with the IFT:** This does **not** contradict the Inverse Function Theorem. The Inverse Function Theorem is strictly a **local** result. It guarantees the existence of small open neighborhoods (e.g., of radius smaller than $\pi$) on which $F$ is locally one-to-one. Non-zero Jacobian determinant everywhere $\det DF(x) \neq 0$ is a necessary condition for local invertibility, but it is **not sufficient** to guarantee global invertibility across the entire domain.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

**Part (f): Why $f'(0) = 0$ for $f(x) = x^3$ Does Not Contradict the IFT**

The function $f : \mathbb{R} \to \mathbb{R}$ defined by $f(x) = x^3$ is strictly increasing, bijective, and hence globally one-to-one, yet its derivative is $f'(x) = 3x^2 \implies f'(0) = 0$.

This does **not** contradict the Inverse Function Theorem because:
* **The IFT is a Conditional Guarantee (Sufficient, Not Necessary for Invertibility):** The theorem states that *if* $f'(x_0) \neq 0$, *then* $f$ has a local $C^1$ inverse near $x_0$. It does not state that non-zero derivative is necessary for a function to be invertible in a purely set-theoretic (or continuous) sense.
* **The IFT Pertains to Smooth ($C^1$) Inverses:** What fails when $f'(0) = 0$ is not the *existence* of a local inverse, but rather the *differentiability* of that inverse at the image point $f(0) = 0$.

**Part (g): Inverse Function and Differentiability at $0$**
* **The Inverse Function:**
  Solving $y = x^3$ for $x$ yields:

$$f^{-1}(y) = y^{1/3} \quad (\text{or } f^{-1}(x) = x^{1/3})$$

  $f^{-1}$ is continuous everywhere on $\mathbb{R}$.
* **Differentiability at $0$:**
  Evaluating the difference quotient for $f^{-1}$ at $y = 0$:

$$\lim_{y \to 0} \frac{f^{-1}(y) - f^{-1}(0)}{y - 0} = \lim_{y \to 0} \frac{y^{1/3} - 0}{y - 0} = \lim_{y \to 0} \frac{1}{y^{2/3}} = \infty$$

  Because this limit diverges to $+\infty$, $f^{-1}$ **is not differentiable at $0$** (the graph of $f^{-1}$ exhibits a vertical tangent at the origin).

**Synthesis: Distinctions Between Local vs. Global and Sufficient vs. Necessary**
* **Local vs. Global:**
  * **Local Properties:** The condition $\det DF(x) \neq 0$ describes the infinitesimal behavior of $F$ in an arbitrarily small neighborhood of a point. By Problem 13(a–e), having $\det DF(x) \neq 0$ everywhere guarantees that the function is a $local$ diffeomorphism around every point, but it fails to prevent distinct, distant regions of the domain from mapping to the same output (e.g., $2\pi$-periodicity in the complex exponential). Global invertibility requires additional topological conditions (such as properness and simple connectivity via Hadamard's Global Inversion Theorem).
  * **Global Properties:** A function can be globally one-to-one over its entire domain (like $f(x) = x^3$) even if its derivative degenerates at isolated critical points.
* **Sufficient vs. Necessary Conditions:**
  * **Sufficient for a $C^1$ Local Inverse:** $\det DF(x_0) \neq 0$ is a **sufficient** condition to guarantee that a local inverse exists and is continuously differentiable ($C^1$).
  * **Not Necessary for Topological Invertibility:** $\det DF(x_0) \neq 0$ is **not necessary** for a function to have a continuous local inverse $f^{-1}$ (as demonstrated by $f(x) = x^3$, where $f^{-1}(y) = y^{1/3}$ is a well-defined homeomorphism).
  * **Necessary for a Differentiable Inverse:** Differentiating the identity $f^{-1}(f(x)) = x$ via the chain rule yields $D(f^{-1})(f(x)) \cdot Df(x) = I$. Taking determinants gives $\det D(f^{-1})(f(x)) \cdot \det Df(x) = 1$. Hence, $\det DF(x_0) \neq 0$ is **strictly necessary** if the inverse map $f^{-1}$ is to be differentiable at $f(x_0)$.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

## **Problem 14: What Can Be Solved for Implicitly?**

Consider the function $F(x, y, z) = x^2 + y^2 + z^2 - 1$ at the point $p = (0,0,1)$ on the unit sphere $S^2$.

The gradient of $F$ at an arbitrary point is:

$$\nabla F(x, y, z) = \begin{pmatrix} F_x \\ F_y \\ F_z \end{pmatrix} = \begin{pmatrix} 2x \\ 2y \\ 2z \end{pmatrix}$$

Evaluating at $p = (0,0,1)$:

$$\nabla F(0,0,1) = \begin{pmatrix} 0 \\ 0 \\ 2 \end{pmatrix}$$

**Part (a): Solving Locally in the Form $z = g(x, y)$**
* **Answer:** **Yes**, the equation can locally be solved for $z$ as a $C^1$ function $z = g(x, y)$ near $(0,0)$.
* **Determining Partial Derivative:** The relevant partial derivative is $F_z(x, y, z) = \frac{\partial F}{\partial z}$.
* **Justification:**
  * $F(0,0,1) = 0^2 + 0^2 + 1^2 - 1 = 0$.
  * $F_z(0,0,1) = 2(1) = 2 \neq 0$.
  By the Implicit Function Theorem, because the partial derivative with respect to the target variable $z$ is non-zero (invertible in $\mathbb{R}^1$), there exists an open neighborhood containing $(0,0)$ and a unique $C^1$ function $g(x, y)$ satisfying the equation.

<!-- page 36 -->

**The Inverse Function Theorem (IFT)**

**Statement:**

Let $U \subseteq \mathbb{R}^n$ be an open set, and let $f : U \to \mathbb{R}^n$ be a $C^1$-mapping. Suppose at a point $x_0 \in U$, the total derivative operator:

$$Df(x_0) : \mathbb{R}^n \to \mathbb{R}^n$$

is invertible (i.e., the Jacobian determinant $\det Df(x_0) \neq 0$).

Then:

1. **Local Diffeomorphism:** There exists an open neighborhood $V \subseteq U$ containing $x_0$ and an open neighborhood $W \subseteq \mathbb{R}^n$ containing $f(x_0)$ such that $f : V \to W$ is a **bijective homeomorphism** (one-to-one, onto, with continuous inverse).
2. **Differentiability of the Inverse:** The inverse mapping $f^{-1} : W \to V$ is also $C^1$.
3. **Derivative of the Inverse:** For every $y \in W$ with $y = f(x)$, the derivative of the inverse is the matrix inverse of the forward derivative:

$$D(f^{-1})(y) = [Df(x)]^{-1}$$

*   **Proof Mechanism (The Contraction Mapping Principle):**
    To solve $f(x) = y$ locally for $x$, define the auxiliary operator:

$$\phi_y(x) = x + [Df(x_0)]^{-1} (y - f(x))$$

    *   A fixed point $\phi_y(x) = x$ occurs if and only if $f(x) = y$.
    *   The derivative $D\phi_y(x) = I - [Df(x_0)]^{-1} Df(x)$. Since $Df$ is continuous, $D\phi_y(x_0) = 0$, so $\|D\phi_y(x)\| \le \frac{1}{2}$ in a sufficiently small closed ball around $x_0$.
    *   By the Mean Value Inequality, $\phi_y$ is a strict contraction on a complete metric space ($\overline{B}(x_0, r)$), guaranteeing a unique local solution $x = f^{-1}(y)$ via the **Banach Fixed-Point Theorem**.

---

**The Implicit Function Theorem**

While the IFT handles invertible maps between spaces of the same dimension ($n \to n$), the Implicit Function Theorem handles underdetermined nonlinear systems $F(x, y) = 0$, where $F : \mathbb{R}^n \times \mathbb{R}^k \to \mathbb{R}^k$. It determines when a system of $k$ equations can be locally solved explicitly for $k$ endogenous variables in terms of $n$ exogenous parameters.

**Statement:**

Let $U \subseteq \mathbb{R}^n \times \mathbb{R}^k$ be open, and let $F : U \to \mathbb{R}^k$ be a $C^1$ mapping. Denote points in $U$ as $(x, y)$ with $x \in \mathbb{R}^n$ and $y \in \mathbb{R}^k$.

Suppose at $(x_0, y_0) \in U$:

1. $F(x_0, y_0) = 0$
2. The partial Jacobian with respect to the $y$-variables, $D_y F(x_0, y_0) \in \mathcal{L}(\mathbb{R}^k, \mathbb{R}^k)$, is **invertible** (i.e., $\det \left[ \frac{\partial F_i}{\partial y_j} (x_0, y_0) \right] \neq 0$).

Then:

*   **Existence of Local Explicit Function:** There exists an open neighborhood $V \subseteq \mathbb{R}^n$ of $x_0$, an open neighborhood $W \subseteq \mathbb{R}^k$ of $y_0$, and a unique $C^1$ mapping $g : V \to W$ such that:

$$g(x_0) = y_0 \quad \text{and} \quad F(x, g(x)) = 0 \quad \forall x \in V$$

*   **Total Derivative of the Implicit Solution:** Differentiating the identity $F(x, g(x)) = 0$ via the multivariate chain rule gives:

$$D_x F(x, g(x)) + D_y F(x, g(x)) \cdot Dg(x) = 0$$

Since $D_y F(x, g(x))$ remains invertible near $(x_0, y_0)$:

$$Dg(x) = -[D_y F(x, g(x))]^{-1} D_x F(x, g(x))$$

---

### Structural Comparison

| Feature | Inverse Function Theorem | Implicit Function Theorem |
| :--- | :--- | :--- |
| **Domain & Codomain** | $f : \mathbb{R}^n \to \mathbb{R}^n$ | $F : \mathbb{R}^n \times \mathbb{R}^k \to \mathbb{R}^k$ |
| **Core Condition** | $\det Df(x_0) \neq 0$ | $\det D_y F(x_0, y_0) \neq 0$ |
| **Geometric Output** | Local diffeomorphism (coordinate chart transformation) | Level set $\{F(x, y) = 0\}$ is locally the graph of a $C^1$ manifold $y = g(x)$ |
| **Derivative Formula** | $D(f^{-1})(y) = [Df(x)]^{-1}$ | $Dg(x) = -[D_y F]^{-1} D_x F$ |

The two theorems are mathematically equivalent: the Implicit Function Theorem is proved by augmenting $F$ into an $(n+k) \to (n+k)$ map $H(x, y) = (x, F(x, y))$ and applying the Inverse Function Theorem.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

---

then there exist open neighborhoods $V \ni x_0$ and $W \ni f(x_0)$ such that $f : V \to W$ is a $C^1$-diffeomorphism.

*   **Inverse Derivative Formula:** For $y \in W$ and $x = f^{-1}(y) \in V$:

$$D(f^{-1})(y) = [Df(x)]^{-1} = \left[ Df(f^{-1}(y)) \right]^{-1}$$

*   **Determinant Relation:**

$$\det D(f^{-1})(y) = \frac{1}{\det Df(x)}$$

---

### Implicit Function Theorem (Implicit Function Form)

*   **System Setup:** Let $F : U \subseteq \mathbb{R}^n \times \mathbb{R}^k \to \mathbb{R}^k$ be $C^1$, with $x \in \mathbb{R}^n$ (exogenous parameters) and $y \in \mathbb{R}^k$ (endogenous variables). Suppose $F(x_0, y_0) = 0$.
*   **Rank / Invertibility Condition:** The partial Jacobian with respect to $y$ must be non-singular:

$$\det D_y F(x_0, y_0) = \det \left[ \frac{\partial F_i}{\partial y_j} (x_0, y_0) \right]_{k \times k} \neq 0$$

*   **Implicit Map Existence:** There exists an open set $V \ni x_0$ and a unique $C^1$ map $g : V \to \mathbb{R}^k$ such that $g(x_0) = y_0$ and $F(x, g(x)) \equiv 0$ for all $x \in V$.
*   **Master Derivative Formula ($k \times n$ Jacobian Matrix):**

$$Dg(x) = -[D_y F(x, g(x))]^{-1} D_x F(x, g(x))$$

---

### Theoretical Traps & Boundary Rules

*   **Local $\neq$ Global:** $\det Df(x) \neq 0$ everywhere ensures local invertibility around every point, but does not guarantee global injectivity (e.g., $F(x, y) = (e^x \cos y, e^x \sin y)$).
*   **Sufficiency vs. Necessity:** $\det Df(x_0) \neq 0$ is sufficient for a *differentiable* inverse, but not necessary for a continuous topological inverse (e.g., $f(x) = x^3$).

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

<!-- page 37 -->

(a) Can the equation locally be solved in the form
$$z = g(x, y)?$$

Which partial derivative determines the answer?

(b) Can it locally be solved in the form
$$x = h(y, z)?$$

Explain.

Now consider the point
$$q = (1, 0, 0).$$

(c) Repeat parts (a)–(b) at $q$.

(d) Explain geometrically why the answers change as we move from $p$ to $q$.

(e) Suppose that near $p$,
$$z = g(x, y).$$

Starting from
$$F(x, y, g(x, y)) = 0,$$

derive formulas for
$$g_x(x, y), \quad g_y(x, y)$$

using the chain rule.

Do not begin by quoting a memorized implicit differentiation formula.

<!-- page 38 -->

(a) Can the equation locally be solved in the form
$$z = g(x, y)?$$

Which partial derivative determines the answer?

(b) Can it locally be solved in the form
$$x = h(y, z)?$$

Explain.

Now consider the point
$$q = (1, 0, 0).$$

(c) Repeat parts (a)–(b) at $q$.

(d) Explain geometrically why the answers change as we move from $p$ to $q$.

(e) Suppose that near $p$,
$$z = g(x, y).$$

Starting from
$$F(x, y, g(x, y)) = 0,$$

derive formulas for
$$g_x(x, y), \quad g_y(x, y)$$

using the chain rule.

Do not begin by quoting a memorized implicit differentiation formula.

<!-- page 39 -->

## 6 Comprehension Check

**Problem 15. Diagnose the statement**

If it is true, give a short proof or cite the appropriate result and explain why its hypotheses are satisfied. If it is false, give a counterexample and explain which implication fails.

(a) If $f$ is differentiable at $x$, then $f$ is continuous at $x$.

(b) If all partial derivatives of $f$ exist at $x$, then $f$ is differentiable at $x$.

(c) If every directional derivative of $f$ exists at $x$, then $f$ is differentiable at $x$.

(d) If all first partial derivatives exist in a neighborhood of $x$ and are continuous at $x$, then $f$ is differentiable at $x$.

(e) A continuous image of a compact set is compact.

(f) A continuous image of a closed set is closed.

(g) A closed subset of a compact set is compact.

(h) If $Df(x)$ is invertible, then $f$ is globally one-to-one.

(i) If $Df(x)$ is singular, then $f$ cannot possess a differentiable local inverse at $x$.

(j) If $Df(x)$ is singular, then $f$ cannot be locally one-to-one near $x$.

---

**Problem 15: Diagnose the Statement**
* **(a) If $f$ is differentiable at $x$, then $f$ is continuous at $x$.**
  * **Verdict: True**
  * **Proof:** By definition of differentiability, $f(x+h) - f(x) = Df(x)h + r(h)$, where $\lim_{h \to 0} \frac{\|r(h)\|}{\|h\|} = 0$. Taking norms and applying the triangle inequality:
    $$\|f(x+h) - f(x)\| \le \|Df(x)\|\|h\| + \|r(h)\|$$
    As $h \to 0$, $\|Df(x)\|\|h\| \to 0$ and $\|r(h)\| = \frac{\|r(h)\|}{\|h\|}\|h\| \to 0 \cdot 0 = 0$. Thus, $\lim_{h \to 0} f(x+h) = f(x)$, proving $f$ is continuous at $x$.

* **(b) If all partial derivatives of $f$ exist at $x$, then $f$ is differentiable at $x$.**
  * **Verdict: False**
  * **Counterexample:** Consider $f : \mathbb{R}^2 \to \mathbb{R}$ defined by:
    $$f(x, y) = \begin{cases} 1, & \text{if } x = 0 \text{ or } y = 0 \\ 0, & \text{otherwise} \end{cases}$$
    At $(0,0)$, $f_x(0,0) = \lim_{h \to 0} \frac{f(h,0) - f(0,0)}{h} = \lim_{h \to 0} \frac{1 - 1}{h} = 0$, and similarly $f_y(0,0) = 0$. Both partial derivatives exist, but $f$ is not even continuous at $(0,0)$ along diagonal paths (e.g., along $y = x$, $f(t, t) = 0 \neq 1$), so by part (a) it cannot be differentiable.

* **(c) If every directional derivative of $f$ exists at $x$, then $f$ is differentiable at $x$.**
  * **Verdict: False**
  * **Counterexample:** Consider $f : \mathbb{R}^2 \to \mathbb{R}$ from Problem 8:
    $$f(x, y) = \begin{cases} \frac{x^2 y}{x^2 + y^2}, & (x, y) \neq (0, 0) \\ 0, & (x, y) = (0, 0) \end{cases}$$
    Every directional derivative $D_v f(0,0) = \frac{a^2 b}{a^2 + b^2}$ exists at the origin for $v = (a, b) \neq 0$. However, the directional derivative map $v \mapsto D_v f(0,0)$ is non-linear ($D_{(1,1)} f(0,0) = \frac{1}{2} \neq D_{(1,0)} f(0,0) + D_{(0,1)} f(0,0) = 0$), which violates the necessary linear structure $D_v f(x) = Df(x)v$ of differentiable functions.

* **(d) If all first partial derivatives exist in a neighborhood of $x$ and are continuous at $x$, then $f$ is differentiable at $x$.**
  * **Verdict: True**
  * **Citation / Proof:** This is the **Continuous Differentiability ($C^1$) Theorem** proven in Problem 9. Using the 1D Mean Value Theorem along coordinate axes increments:
    $$f(x + h) - f(x) - \sum_{i=1}^n f_{x_i}(x)h_i = \sum_{i=1}^n [f_{x_i}(\xi_i) - f_{x_i}(x)]h_i$$
    Dividing by $\|h\|$ and using the continuity of each $f_{x_i}$ at $x$ ensures that $\lim_{h \to 0} \frac{\|r(h)\|}{\|h\|} = 0$, establishing total differentiability.

* **(e) A continuous image of a compact set is compact.**
  * **Verdict: True**
  * **Citation / Proof:** This is the general topological result proven in Problem 5(a). Let $K$ be compact and $f$ be continuous. For any sequence $(y_k) \subseteq f(K)$, choose $x_k \in K$ with $f(x_k) = y_k$. By sequential compactness of $K$, there is a subsequence $x_{k_j} \to x^* \in K$. By sequential continuity of $f$, $y_{k_j} = f(x_{k_j}) \to f(x^*) \in f(K)$, showing that every sequence in $f(K)$ has a subsequence converging to a point in $f(K)$.

From <https://gemini.google.com/app/06b7ab97dac5cbbb>

---

**Problem 15 (Continued)**

* **(f) A continuous image of a closed set is closed.**
  * **Verdict: False**
  * **Counterexample:** Let $F = [1, \infty) \subseteq \mathbb{R}$, which is a closed set. Define the continuous function $f : [1, \infty) \to \mathbb{R}$ by $f(x) = \frac{1}{x}$. The image is $f(F) = (0, 1]$, which is not closed in $\mathbb{R}$ because it fails to contain its limit point $0$.

* **(g) A closed subset of a compact set is compact.**
  * **Verdict: True**
  * **Proof:** Let $K \subseteq \mathbb{R}^n$ be compact and $C \subseteq K$ be closed. Let $(x_k)_{k=1}^\infty$ be an arbitrary sequence in $C$. Since $C \subseteq K$, $(x_k)$ is also a sequence in the compact set $K$. By sequential compactness of $K$, there exists a subsequence $(x_{k_j})$ converging to some limit $x^* \in K$. Because $C$ is closed, it contains all of its limit points, so $x^* \in C$. Thus, every sequence in $C$ possesses a subsequence converging to a point in $C$, proving $C$ is compact.

* **(h) If $Df(x)$ is invertible, then $f$ is globally one-to-one.**
  * **Verdict: False**
  * **Counterexample:** Consider $F : \mathbb{R}^2 \to \mathbb{R}^2$ given by $F(x, y) = (e^x \cos y, e^x \sin y)$ from Problem 13. The Jacobian determinant satisfies $\det DF(x, y) = e^{2x} > 0$ for all $(x, y) \in \mathbb{R}^2$, meaning $DF(x)$ is everywhere invertible. However, $F$ is periodic with $F(x, y + 2\pi) = F(x, y)$, so $F(0,0) = (1,0) = F(0, 2\pi)$, showing $F$ is not globally one-to-one.

* **(i) If $Df(x)$ is singular, then $f$ cannot possess a differentiable local inverse at $x$.**
  * **Verdict: True**
  * **Proof:** Suppose for contradiction that $f$ has a local inverse $g = f^{-1}$ defined near $y = f(x)$ that is differentiable at $y$. Then $g(f(x)) = x$. Differentiating both sides via the multivariate chain rule gives:
    $$Dg(f(x)) \cdot Df(x) = I_n$$
    Taking determinants of both sides yields:
    $$\det Dg(f(x)) \cdot \det Df(x) = \det(I_n) = 1$$
    If $Df(x)$ is singular, then $\det Df(x) = 0$, leading to $0 = 1$, a contradiction. Therefore, no differentiable local inverse can exist at $x$.

* **(j) If $Df(x)$ is singular, then $f$ cannot be locally one-to-one near $x$.**
  * **Verdict: False**
  * **Counterexample:** Consider $f : \mathbb{R} \to \mathbb{R}$ defined by $f(x) = x^3$ at $x = 0$. The derivative is $f'(0) = 3(0)^2 = 0$ (the $1 \times 1$ Jacobian is singular). However, $f$ is strictly monotonically increasing on all of $\mathbb{R}$, which means $f$ is strictly injective (one-to-one) on every open neighborhood around $0$.

Real_Analysis_PS Page 39

<!-- page 40 -->

Real_Analysis_PS Page 40

<!-- page 41 -->

admitting the continuous local inverse $f^{-1}(y) = y^{1/3}$.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

(k) If $U \subseteq \mathbb{R}^n$ is convex and $Df(x) = 0$ for every $x \in U$, then $f$ is constant on $U$.

(l) If $U \subseteq \mathbb{R}^n$ is convex and $H_f(x) = 0$ for every $x \in U$, then $f$ is affine on $U$.

**Problem 15 (Continued)**
* **(k) If $U \subseteq \mathbb{R}^n$ is convex and $Df(x) = 0$ for every $x \in U$, then $f$ is constant on $U$.**
  * **Verdict: True**
  * **Proof:** Let $a, b \in U$ be arbitrary. Because $U$ is convex, the line segment $[a, b] = \{a + t(b - a) : t \in [0, 1]\}$ is contained entirely in $U$. By the Mean Value Theorem on line segments (Problem 10(b)), there exists a point $c \in (a, b) \subseteq U$ such that:
    $$f(b) - f(a) = Df(c)(b - a)$$
    Since $Df(x) = 0$ for all $x \in U$, we have $Df(c) = 0$. Therefore, $f(b) - f(a) = 0(b - a) = 0 \implies f(b) = f(a)$. Since $a$ and $b$ were arbitrary, $f$ is constant on $U$.

* **(l) If $U \subseteq \mathbb{R}^n$ is convex and $H_f(x) = 0$ for every $x \in U$, then $f$ is affine on $U$.**
  * **Verdict: True** (assuming $f : U \to \mathbb{R}$ is $C^2$ with $U$ open)
  * **Proof:** The Jacobian matrix of the gradient map $F(x) = \nabla f(x)$ is the Hessian matrix: $DF(x) = D(\nabla f)(x) = H_f(x)$. Since $H_f(x) = 0$ everywhere on the convex set $U$, applying statement (k) component-wise to $F$ implies that $\nabla f$ is constant on $U$, so $\nabla f(x) = a$ for some fixed vector $a \in \mathbb{R}^n$.
    Now define the auxiliary function $g(x) = f(x) - a^T x$. Its derivative is $Dg(x) = Df(x) - a^T = 0$ for all $x \in U$. By statement (k), $g(x)$ is constant on $U$, so $g(x) = b$ for some scalar $b \in \mathbb{R}$. Thus, $f(x) = a^T x + b$, which is affine on $U$.

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

**Optional Extensions**

The following problems are not required. They provide additional proof practice and connect the topology developed above with later results in multivariate calculus.

**Extension 1. Nested compact sets**

Suppose
$$K_1 \supseteq K_2 \supseteq K_3 \supseteq \dots$$

is a decreasing sequence of nonempty compact subsets of $\mathbb{R}^n$.

Prove that
$$\bigcap_{k=1}^\infty K_k \neq \emptyset.$$

*Guidance. Choose*
$$x_k \in K_k.$$

*All of these points belong to $K_1$, so extract a convergent subsequence.*

*If*
$$x_{k_j} \to x,$$

*fix an arbitrary $N$. For sufficiently large $j$,*
$$k_j \ge N.$$

*Use the nestedness of the sets and closedness of $K_N$.*

**Extension 1: Nested Compact Sets (Cantor's Intersection Theorem)**
**Proposition:** Let $K_1 \supseteq K_2 \supseteq K_3 \supseteq \dots$ be a decreasing sequence of non-empty compact subsets of $\mathbb{R}^n$. Then:
$$\bigcap_{k=1}^\infty K_k \neq \emptyset$$

*Proof via Guided Subsequential Extraction:*
1. **Construct a Sequence:**
   Since each set $K_k$ is non-empty, use the axiom of choice to select an element $x_k \in K_k$ for each $k \in \mathbb{N} = \{1, 2, 3, \dots\}$. This defines a sequence $(x_k)_{k=1}^\infty$.
2. **Containment in the Ambient Set $K_1$:**
   Because the sequence of sets is nested ($K_1 \supseteq K_2 \supseteq K_3 \supseteq \dots$), we have $K_k \subseteq K_1$ for all $k \ge 1$. Consequently, every term of the sequence satisfies:
   $$x_k \in K_1 \quad \forall k \in \mathbb{N}$$
3. **Extract a Convergent Subsequence:**
   The set $K_1 \subset \mathbb{R}^n$ is compact, hence sequentially compact. Therefore, there exists a subsequence $(x_{k_j})_{j=1}^\infty$ and a limit point $x \in K_1$ such that:
   $$\lim_{j \to \infty} x_{k_j} = x$$
4. **Show $x \in K_N$ for an Arbitrary $N$:**
   Fix an arbitrary index $N \in \mathbb{N}$.
   * Since $k_1 < k_2 < k_3 < \dots$ is a strictly increasing sequence of positive integers, $k_j \to \infty$ as $j \to \infty$. Thus, there exists an integer $J \in \mathbb{N}$ such that for all $j \ge J$:
     $$k_j \ge N$$
   * By nestedness, $K_{k_j} \subseteq K_N$ whenever $k_j \ge N$. Since $x_{k_j} \in K_{k_j}$, it follows that:
     $$x_{k_j} \in K_N \quad \forall j \ge J$$
   * The tail of the subsequence $(x_{k_j})_{j=J}^\infty$ lies entirely within $K_N$. Because $K_N$ is compact in $\mathbb{R}^n$, it is closed. A closed set contains all of its sequential limit points:
     $$x = \lim_{j \to \infty} x_{k_j} \in K_N$$
5. **Conclusion:**
   Because the choice of $N \in \mathbb{N}$ was arbitrary, $x \in K_N$ holds for every $N \ge 1$. Therefore:
   $$x \in \bigcap_{N=1}^\infty K_N \implies \bigcap_{k=1}^\infty K_k \neq \emptyset \quad \blacksquare$$

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

**Extension 2. Invertible matrices form an open set**

Identify the space of $n \times n$ real matrices with $\mathbb{R}^{n^2}$, and define
$$GL_n(\mathbb{R}) = \{A \in \mathbb{R}^{n \times n} : \det A \neq 0\}.$$

(a) Prove that $GL_n(\mathbb{R})$ is open.

(b) Suppose $f : \mathbb{R}^n \to \mathbb{R}^n$ is $C^1$ and $Df(x^*)$ is invertible. Prove that there exists $\epsilon > 0$ such that $Df(x)$ remains invertible whenever
$$\|x - x^*\| < \epsilon.$$

*Guidance. Regard*

**Extension 2: Invertible Matrices Form an Open Set**
**Part (a): Prove that $GL_n(\mathbb{R})$ is open**
*Proof:*
1. **Continuity of the Determinant:**
   Identify $\mathbb{R}^{n \times n} \cong \mathbb{R}^{n^2}$. The determinant map:
   $$\det : \mathbb{R}^{n \times n} \to \mathbb{R}$$
   is given by the Leibniz formula:
   $$\det(A) = \sum_{\sigma \in S_n} \operatorname{sgn}(\sigma) \prod_{i=1}^n A_{i, \sigma(i)}$$
   Because $\det(A)$ is a multilinear polynomial in the $n^2$ matrix entries $A_{ij}$, it is a polynomial function from $\mathbb{R}^{n^2}$ to $\mathbb{R}$, and hence is **continuous**.
2. **Preimage of an Open Set:**
   By definition:

<!-- page 42 -->

$$GL_n(\mathbb{R}) = \{A \in \mathbb{R}^{n \times n} : \det(A) \neq 0\} = \det{}^{-1}(\mathbb{R} \setminus \{0\})$$
   The set $\mathbb{R} \setminus \{0\} = (-\infty, 0) \cup (0, \infty)$ is an open subset of $\mathbb{R}$.
   Because the determinant function is continuous and $GL_n(\mathbb{R})$ is the inverse image (preimage) of an open set under a continuous map, $GL_n(\mathbb{R})$ is an **open set** in $\mathbb{R}^{n \times n}$. $\blacksquare$

---

**Part (b): Openness of Invertibility for Derivatives**
*Proposition:* Let $f : \mathbb{R}^n \to \mathbb{R}^n$ be $C^1$, and suppose $Df(x^*)$ is invertible. Then there exists $\epsilon > 0$ such that $Df(x)$ is invertible for all $x \in B_\epsilon(x^*)$.

*Proof:*
1. **Composition of Continuous Maps:**
   Because $f$ is $C^1$, its derivative map $Df : \mathbb{R}^n \to \mathbb{R}^{n \times n}$ is continuous as a function from $\mathbb{R}^n$ to $\mathbb{R}^{n^2}$.
   The composite function:
   $$g : \mathbb{R}^n \to \mathbb{R}, \quad g(x) = \det(Df(x)) = (\det \circ Df)(x)$$
   is the composition of two continuous mappings ($\det$ and $Df$), and is therefore continuous at $x^*$.
2. **Persistence of Non-Zero Value:**
   By assumption, $Df(x^*)$ is invertible, so $g(x^*) = \det(Df(x^*)) \neq 0$.
   Let $\delta = |g(x^*)| > 0$. By the definition of continuity at $x^*$, for $\epsilon_0 = \frac{\delta}{2} > 0$, there exists $\epsilon > 0$ such that:
   $$\|x - x^*\| < \epsilon \implies |g(x) - g(x^*)| < \frac{|g(x^*)|}{2}$$
   By the reverse triangle inequality, $|g(x)| \ge |g(x^*)| - |g(x) - g(x^*)| > \frac{|g(x^*)|}{2} > 0$.
3. **Conclusion:**
   Thus, for every $x \in B_\epsilon(x^*)$, we have $\det(Df(x)) \neq 0$, which implies that $Df(x) \in GL_n(\mathbb{R})$ (i.e., $Df(x)$ is invertible). $\blacksquare$

---

**Extension 3. A fixed-point theorem**

Suppose
$$K \subseteq \mathbb{R}^n$$
is non-empty, closed, and bounded (hence compact), and let
$$f : K \to K$$
satisfy
$$\|f(x) - f(y)\| < \|x - y\| \quad \text{for all } x \neq y \in K.$$

(a) Show that the function
$$\phi(x) = \|f(x) - x\|$$
is continuous on $K$.

(b) Deduce that $\phi$ attains a minimum at some $x^* \in K$.

(c) Prove that $x^*$ is a fixed point, i.e.,
$$f(x^*) = x^*.$$

(d) Show that the fixed point is unique.

*Notice that $f$ is strictly weak-contractive, but we do not assume a uniform contraction factor $L < 1$. Compactness replaces the contraction constant.*

---

**Extension 3: A Fixed-Point Theorem for Weak Contractions on Compact Sets**

**Part (a): Prove that $\phi(x) = \|f(x) - x\|$ is continuous on $K$**
*Proof:*
1. **Continuity of $f(x)$:**
   The hypothesis $\|f(x) - f(y)\| < \|x - y\|$ for $x \neq y$ implies that $f$ is $1$-Lipschitz (non-expansive), so $f$ is continuous on $K$.
2. **Continuity of $g(x) = f(x) - x$:**
   Since $f(x)$ and the identity map $i(x) = x$ are continuous on $K$, their vector difference $g(x) = f(x) - x$ is continuous on $K$.
3. **Continuity of the Norm:**
   The norm function $\|\cdot\| : \mathbb{R}^n \to \mathbb{R}$ is continuous by the reverse triangle inequality: $|\|u\| - \|v\|| \le \|u - v\|$.
4. **Composition:**
   The function $\phi(x) = \|g(x)\| = \|f(x) - x\|$ is the composition of continuous functions, hence **continuous on $K$**. $\blacksquare$

---

**Part (b): Deduce that $\phi$ attains a minimum at some $x^* \in K$**
*Proof:*
Since $K \subseteq \mathbb{R}^n$ is non-empty and compact (closed and bounded), and $\phi : K \to \mathbb{R}$ is continuous on $K$, the **Extreme Value Theorem** (Problem 5(b)) guarantees that $\phi$ attains its global minimum on $K$. That is, there exists some $x^* \in K$ such that:
$$\phi(x^*) = \inf_{x \in K} \phi(x) = \min_{x \in K} \|f(x) - x\| \quad \blacksquare$$

---

**Part (c): Prove that $x^*$ is a fixed point, i.e., $f(x^*) = x^*$**
*Proof by Contradiction:*
1. **Assume $x^*$ is not a fixed point:**
   Suppose $f(x^*) \neq x^*$. Then $\phi(x^*) = \|f(x^*) - x^*\| > 0$.
2. **Evaluate $\phi$ at the Image Point $f(x^*)$:**
   Since $f : K \to K$, $f(x^*) \in K$, so we can evaluate $\phi(f(x^*))$:
   $$\phi(f(x^*)) = \|f(f(x^*)) - f(x^*)\|$$
3. **Apply the Weak Contraction Property:**
   Since $x^* \neq f(x^*)$, apply the strict inequality $\|f(u) - f(v)\| < \|u - v\|$ with $u = f(x^*)$ and $v = x^*$:
   $$\phi(f(x^*)) = \|f(f(x^*)) - f(x^*)\| < \|f(x^*) - x^*\| = \phi(x^*)$$
4. **Contradiction:**
   We have found a point $y = f(x^*) \in K$ such that $\phi(y) < \phi(x^*)$.
   This contradicts the assumption that $x^*$ is a global minimizer of $\phi$ on $K$.
   Therefore, the assumption $f(x^*) \neq x^*$ must be false, concluding that $f(x^*) = x^*$. $\blacksquare$

---

**Part (d): Show that the fixed point is unique**
*Proof by Contradiction:*
Suppose $x^*, y^* \in K$ are two distinct fixed points of $f$, so $x^* \neq y^*$ with $f(x^*) = x^*$ and $f(y^*) = y^*$.
1. Compute the distance between them:
   $$\|x^* - y^*\| = \|f(x^*) - f(y^*)\|$$
2. Apply the strict weak contraction inequality for $x^* \neq y^*$:
   $$\|f(x^*) - f(y^*)\| < \|x^* - y^*\|$$
3. Combining these gives $\|x^* - y^*\| < \|x^* - y^*\|$, a direct contradiction ($a < a$).
Thus, the fixed point $x^* \in K$ must be unique. $\blacksquare$

<!-- page 43 -->

Because $\det(A)$ is a multilinear polynomial in the $n^2$ matrix entries $A_{ij}$, it is a polynomial function from $\mathbb{R}^{n^2}$ to $\mathbb{R}$, and hence is **continuous**.

**2. Preimage of an Open Set:**
By definition:
$$GL_n(\mathbb{R}) = \{A \in \mathbb{R}^{n \times n} : \det A \neq 0\} = \det{}^{-1}(\mathbb{R} \setminus \{0\})$$
The target set $\mathbb{R} \setminus \{0\} = (-\infty, 0) \cup (0, \infty)$ is open in $\mathbb{R}$.
Because the preimage of an open set under a continuous map is open, $GL_n(\mathbb{R}) = \det{}^{-1}(\mathbb{R} \setminus \{0\})$ is an open subset of $\mathbb{R}^{n \times n} \cong \mathbb{R}^{n^2}$. $\blacksquare$

**Part (b): Open Neighborhood Preservation of Invertibility for $Df(x)$**
*Proof:*
**1. Continuity of the Derivative Map:**
Because $f : \mathbb{R}^n \to \mathbb{R}^n$ is $C^1$, each partial derivative $\frac{\partial f_i}{\partial x_j}(x)$ is continuous on $\mathbb{R}^n$. Consequently, the total derivative operator:
$$Df : \mathbb{R}^n \to \mathbb{R}^{n \times n}, \quad x \mapsto Df(x)$$
is a continuous mapping from $\mathbb{R}^n$ into the matrix space $\mathbb{R}^{n^2}$.

**2. Preimage of $GL_n(\mathbb{R})$:**
From Part (a), $GL_n(\mathbb{R})$ is an open subset of $\mathbb{R}^{n \times n}$. By continuity of the map $Df$, the preimage:
$$U = (Df)^{-1}(GL_n(\mathbb{R})) = \{x \in \mathbb{R}^n : Df(x) \in GL_n(\mathbb{R})\}$$
is an **open set** in $\mathbb{R}^n$.

**3. Existence of the $\epsilon$-Ball:**
By hypothesis, $Df(x^*)$ is invertible, which means $Df(x^*) \in GL_n(\mathbb{R})$. Therefore, $x^* \in U$.
Because $U$ is an open subset of the metric space $(\mathbb{R}^n, \|\cdot\|)$, every point in $U$ is an interior point. Thus, there exists a radius $\epsilon > 0$ such that the open ball $B(x^*, \epsilon) \subseteq U$:
$$B(x^*, \epsilon) = \{x \in \mathbb{R}^n : \|x - x^*\| < \epsilon\} \subseteq U$$
Hence, for every $x \in \mathbb{R}^n$ satisfying $\|x - x^*\| < \epsilon$, we have $x \in U \implies Df(x) \in GL_n(\mathbb{R})$, so $Df(x)$ remains invertible. $\blacksquare$

From `<https://gemini.google.com/app/06b7ab97dac5cbbb>`

<!-- page 44 -->

Real_Analysis_PS Page 44