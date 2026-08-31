---
source_pdf: Part II Analysis in Euclidean Spaces 08.14.pdf
folder_category: ta_notes
total_pages: 12
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [real-analysis]
---

<!-- page 1 -->

Part II: Analysis in Euclidean Spaces 08.14
Friday, August 14, 2026 8:53 PM

- Before we start:
  - Lecture recording of 08.13: Video is still converting.
  - No office hour this afternoon.

Recall from Yesterday:
$$\lim_{k \to \infty} x_k = a \in \mathbb{R}^n \quad \text{equivalently} \quad x_k \to a \ (k \to \infty) \text{ if}:$$
$$\text{For every } \varepsilon > 0, \text{ there exists } N = N(\varepsilon) \in \mathbb{N} \text{ such that}$$
$$\text{For all } k > N: \quad \|x_k - a\| < \varepsilon$$

- Some consequences of this defn:
  - When limit exists, it's unique:
    Proof: If $x_k \to a$ and $x_k \to b$ as $k \to \infty$
    $$\|a - b\| = \|(x_k - b) - (x_k - a)\| \le \|x_k - b\| + \|x_k - a\| \to 0 \quad \text{as } k \to \infty$$
    This implies
    $$\|a - b\| = 0 \iff a - b = 0 \quad \text{so} \quad a = b.$$

  - Convergent sequence is bounded:
    Proof. Let $x_k \to a$ as $k \to \infty$. Pick $\varepsilon = 1$
    Then by defn. there exists $N \in \mathbb{N}$ such that
    $$\|x_k - a\| < 1 \quad \text{for all } k > N$$
    By $| \|c\| - \|d\| | \le \|c - d\|$ (Check this.)
    $$\|x_k\| - \|a\| \le \|x_k - a\| < 1 \quad \text{for all } k > N$$
    This means:
    $$\|x_k\| < \|a\| + 1 \quad \text{for all } k > N$$

<!-- page 2 -->

This means: $\|x_k\| < \|a\| + 1$ for all $k > N$

Take $M = \max \{\|x_1\|, \|x_2\|, \dots, \|x_N\|, \|a\| + 1\}$

Then $\|x_k\| \le M$ for all $k$.

- $x_k \longrightarrow \infty$ as $k \to \infty$ if:
  For all $M > 0$, there exists $N = N(M) \in \mathbb{N}$ such that:
  For all $k > N$: $\|x_k\| > M$.

- A subsequence of $\{x_k\}$:
  $\{x_{k_j}\}_{j=1}^\infty$ where $k_1 < k_2 < k_3 \dots$

$\begin{array}{lcccccc}
\text{Sequence}: & x_1, & x_2, & x_3, & x_4 & \dots & x_k, & x_{k+1}, & x_{k+2} \dots \\
& \downarrow & \downarrow & \searrow & \swarrow & & \downarrow & \swarrow \\
\text{Subsequence}: & x_{k_1}, & x_{k_2} = x_{k_3} & \dots & x_{k_j}, & x_{k_{j+1}}
\end{array}$

- What does it mean formally that $x_k \not\to a \ (k \to \infty)$.
  There exists $\varepsilon_0 > 0$, for every $N \in \mathbb{N}$
  There exists $k_0 > N$ such that
  $$\|x_{k_0} - a\| \ge \varepsilon_0\ .$$

- Remark: Make yourself very comfortable with the formal definition of convergence!!

- Overview of Point-Set Topology in $\mathbb{R}^n$.
  - Open Ball:
    $$B_r(a) = \{x \in \mathbb{R}^n : \|x - a\| < r\}$$

<!-- page 3 -->

Closed Ball:
$$\overline{B_r(a)} = \{x \in \mathbb{R}^n : \|x - a\| \le r\}$$

$$B_r(a) \subsetneq \overline{B_r(a)}$$

- A set $S \subseteq \mathbb{R}^n$ is bounded if there exists $R > 0$ such that
$$S \subseteq B_R(0)$$
$$\Updownarrow$$
$$\text{There exists } M : \|x\| \le M \quad \forall x \in S$$

- Open Set: A set $U \subseteq \mathbb{R}^n$ open if for every $x \in U$ there exists $\delta > 0$:
$$B_\delta(x) \subseteq U$$

Closed Set: A set $F \subseteq \mathbb{R}^n$ is closed if $F^c = \mathbb{R}^n \setminus F$ is open.

Claim: A potato with skin in $\mathbb{R}^n$ is not open.
Not open
Not closed

- There are sets that are open and closed. $\mathbb{R}^n$.
"Clopen" in topology.

<!-- page 4 -->

- "Clopen" in topology.

By convention: $\mathbb{R}^n$ and $\varnothing$ are clopens.

- Limit Points / Accumulation Points:

  $a$ is a limit point of $S$ if for every $\delta > 0$.
  $$B_\delta(a) \setminus \{a\} \cap S \ne \varnothing.$$

  ```
        .  .
       . x_2 .
      .   .a  .
     . x_1 \in S .
      .       .
        .  .
  ```

  Consequence: $a$ is a limit point
  $$\Updownarrow$$
  there exists $\{x_k\}_{k=1}^\infty \subseteq S : x_k \to a \ (k \to \infty)$$

- Compactness:

  Fact: (Bolzano - Weierstrass Theorem)

  Every bounded sequence in $\mathbb{R}^n$ has convergent subsequence.

  In $\mathbb{R} : a_n = (-1)^n$.

- Compact Set:

  Let $K \subseteq \mathbb{R}^n$

  A collection of open sets $\{U_\alpha\}_{\alpha \in A}$ is an open cover of $K$ if

<!-- page 5 -->

A collection of open sets $\{U_\alpha\}_{\alpha \in A}$ is an **open cover** of $K$ if
$$K \subseteq \bigcup_{\alpha \in A} U_\alpha$$

Note: The index set $A$ might be uncountable.

The set $K$ is **compact** if every open cover of $K$ contains a finite subcover:

Whenever $K \subseteq \bigcup_{\alpha \in A} U_\alpha$, there exists $\alpha_1, \alpha_2, \dots, \alpha_m$, $m$ finite, such that
$$K \subseteq \bigcup_{i=1}^m U_{\alpha_i}.$$

- Why do we need compactness?

  Finite set: $B = \{b_1, b_2, \dots, b_N\} \subseteq \mathbb{R}^n$

  ```
        ( • b_N )
      ( • b_1 )
        ( • b_2 )    Open cover
      ( • b_3 )          ↓
        ( • b_2 )    Finite subcover
  ```

  Compactness is "finitely infinite" for arbitrary sets.

- **Heine-Borel Theorem**:

  $K \subseteq \mathbb{R}^n$ compact $\iff$ Closed and bounded.

  $\mathbb{R}$ is NOT compact: $\{(-n, n)\}_{n=1}^\infty$ open cover for $\mathbb{R}$
  NO Finite Subcover.

<!-- page 6 -->

$\mathbb{R}$ is NOT compact: $\{(-n, n)\}_{n=1}^\infty$
No Finite Subcover.

$(0, 1) \subseteq \mathbb{R}$ is NOT compact: $\left\{\left(0, 1 - \frac{1}{n+1}\right)\right\}_{n=1}^\infty$ open cover for $(0, 1]$

```
       n=1 n=2 n=3
   (---)--)-)--)->
   0           1
```

No finite Subcover. $\lrcorner$

- In $\mathbb{R}^n$, TFAE:
  (1). $K \le \mathbb{R}^n$ is compact.
  (2). (Sequential Compactness):
  Every sequence $\{x_k\} \subseteq K$ has a convergent subsequence whose limit belongs to $K$.
  (3). (Heine-Borel):
  $K$ is closed and bounded.

Fact: Closed sets contain their limit points
(Prove by definition and look at the complement)

- $B = \{b_1, b_2, \dots, b_N\}$ Finite $f : B \to \mathbb{R}$

```
 f(b_1) f(b_2)   f(b_N)
   •      •        •
---+------+--------+--->
  b_1    b_2      b_N
```

$\max_{b \in B} f(b)$  $\checkmark$ : Rank $f(b_1) \dots f(b_N)$.
Since $\{f(b_i)\}_{i=1}^N$ finite.

$$\int$$

$K$ compact $\implies$ $\max_{x \in K} f(x)$ $\checkmark$

Useful for establishing the existence of a maximum

<!-- page 7 -->

Useful for establishing the existence of a maximum

- **Limits and Continuity of Mappings:**

  $$f: D \subseteq \mathbb{R}^n \longrightarrow \mathbb{R}^m.$$

  Let $a$ be a limit point of $D$ and $b \in \mathbb{R}^m$.

  $$f(x) \longrightarrow b \quad \text{as } x \to a$$

  if for every $\varepsilon > 0$, there exists $\delta = \delta(\varepsilon) > 0$ such that

  $$\text{for all } x \in D, \quad 0 < \|x - a\| < \delta \ (\Leftrightarrow x \in B_\delta(a))$$

  we have $\|f(x) - b\| < \varepsilon$.

  This is the $\varepsilon$-$\delta$ language for $\lim_{x \to a} f(x) = b$.

  We can also characterize the limit using sequence.

  **Heine Principle:** Let $a$ be a limit point of $D$.

  Then
  $$\lim_{x \to a} f(x) = b$$
  $$\Updownarrow$$
  For every sequence $\{x_k\} \subseteq D \setminus \{a\}$ such that
  $$x_k \to a \quad (k \to \infty),$$
  we have $f(x_k) \longrightarrow b$.

- **Why is this useful?**

  Example: Show $f(x, y) = \frac{xy}{x^2+y^2} \quad ((x, y) \neq (0, 0))$

  $$\lim_{(x,y) \to (0,0)} f(x, y) \text{ doesn't exist.}$$

<!-- page 8 -->

$$\lim_{(x,y) \to (0,0)} f(x,y) \text{ doesn't exist.}$$

Along the line $y = kx$ we have:
$$f(x,y) = f(x, kx) = \frac{k}{1+k^2}$$

Different values of $k$ will give a different limit. So the limit doesn't exist.

Checking lines like $y = kx$ is NOT always enough.

Example': $g(x,y) = \frac{x^2 y}{x^4 + y^2} \quad ((x,y) \neq (0,0))$

Along any straight line $(x,y) = (\alpha t, \beta t)$
$$g(\alpha t, \beta t) \to 0 \quad \text{as } t \to 0 \iff (x,y) \to (0,0)$$

But if we take $y = x^2$
we have $g(x, x^2) = \frac{1}{2} \neq 0$

So the limit doesn't exist.

- Limits preserves arithmetics when defined.
$+$, $-$, $\cdot$, $\div$ by non-zero. when $f : D \to \mathbb{R}$

- **Continuity of Mappings:**

  Let $f : D \subseteq \mathbb{R}^n \longrightarrow \mathbb{R}^m$, $a \in D$.

  $f$ is continuous at $a$ if for every $\varepsilon > 0$
  there exists $\delta = \delta(\varepsilon) > 0$ such that

<!-- page 9 -->

there exists $\delta = \delta(\varepsilon) > 0$ such that
$$\text{for every } x \in D, \ \|x - a\| < \delta \quad \text{we have}$$
$$\|f(x) - f(a)\| < \varepsilon$$

If $a$ is a limit point of $D$, then by the definition of limits, this is equivalent to
$$\lim_{x \to a} f(x) = f(a) = f\left(\lim_{x \to a} x\right).$$

Note: By convention, if $a$ is isolated, then $f$ is continuous at $a$.

If $f$ is continuous at every point $a \in D$, we say $f$ is continuous on $D$.

If $f : D \to \mathbb{R}$, arithmetics preserves continuity.

- **Local Sign Preservation:**
  Let $f : D \to \mathbb{R}$ continuous at $a \in D$. If $f(a) > 0$, then there exists $\delta > 0$ such that
  $$\text{for all } x \in D, \ \|x - a\| < \delta \implies f(x) > 0.$$

  **Proof:** Take $\varepsilon = \frac{1}{2} f(a)$ by continuity, $\exists \delta > 0 :$
  $$\|x - a\| < \delta \implies |f(x) - f(a)| < \frac{f(a)}{2}$$
  This implies
  $$-\frac{1}{2} f(a) < f(x) - f(a) < \frac{f(a)}{2}$$

<!-- page 10 -->

$$\implies f(x) > \frac{1}{2} f(a) > 0. \quad \square$$

- **Note:** If $a$ is a limit point of $D$ then by the Heine Principle:
$$x_k \to a \quad \text{then} \quad f(x_k) \to f(a) \quad , k \to \infty.$$

- **Composition of continuous maps are continuous:**

$$D \subseteq \mathbb{R}^n \xrightarrow[\text{at } a \in D]{\substack{g \\ \text{cont.}}} U \subseteq \mathbb{R}^m \xrightarrow[\text{at } g(a) \in U]{\substack{f \\ \text{cont.}}} \mathbb{R}^p \qquad \begin{aligned} f \circ g : D &\subseteq \mathbb{R}^n \\ &\downarrow \\ &\mathbb{R}^p \end{aligned}$$

$$\text{then } f \circ g \text{ is continuous at } a$$

**Proof:** Let $x_k \to a$. then $g(x_k) \to g(a)$ by cont. of $g$
then $f(g(x_k)) \to f(g(a))$ by cont. of $f$. $\quad \square$

- **Topological Characterization of continuity.**

  - **Preimage:** $f : D \to \mathbb{R}^m$. Let $A \subseteq \mathbb{R}^m$

    The preimage of $A$ under $f$ is:
    $$f^{-1}(A) = \{x \in D : f(x) \in A\}$$

    $$\begin{aligned}
    &\text{If } T \in \mathcal{L}(\mathbb{R}^n, \mathbb{R}^m), \text{ take } A = \{0_{\mathbb{R}^m}\} \\
    &\ker T = \underbrace{T^{-1}(A)} = \{x \in \mathbb{R}^n : T(x) = 0_{\mathbb{R}^m}\} \\
    &\swarrow \\
    &\text{This does.} \quad \text{This doesn't show up in linear algebra.}
    \end{aligned}$$

<!-- page 11 -->

$$\begin{aligned}
&\swarrow \qquad \qquad \ \searrow \\
&\text{This does.} \quad \text{This doesn't show up in linear algebra.}
\end{aligned}$$
$$\qquad \qquad \qquad \qquad \qquad \qquad \qquad \qquad \qquad \rotatebox[origin=c]{180}{$\curvearrowleft$}$$

- **Fact:** (Check for yourself):
  $$f^{-1}(A^c) = [f^{-1}(A)]^c \quad \text{Hint: Show } \subseteq \text{ and } \supseteq$$

- Let $f : D \subseteq \mathbb{R}^n \longrightarrow \mathbb{R}^m$. TFAE:
  (1) $f$ is continuous on $D$.
  (2) for every open set $U \subseteq \mathbb{R}^m$
      $$\text{the preimage } f^{-1}(U) \text{ is open in } \mathbb{R}^n.$$
  (3) for every closed set $F \subseteq \mathbb{R}^m$
      $$\text{the preimage } f^{-1}(F) \text{ is closed in } \mathbb{R}^n.$$

  "Continuity means that preimage of open set is open."

  **Proof:** $(2) \iff (3)$ by defn. of open/closed sets and fact.

  $(1) \implies (2):$ Take $a \in f^{-1}(U)$. By defn. of preimage,
  $$f(a) \in U.$$
  $U$ is open, there exists $\varepsilon > 0 :$
  $$B_\varepsilon(f(a)) \subseteq U$$
  By continuity of $f$: there exists $\delta = \delta(\varepsilon) > 0$
  $$\text{for all } x \in D, \ \|x - a\| < \delta \quad \text{we have}$$
  $$f(x) \in B_\varepsilon(f(a)) \subseteq U.$$
  $$\text{This } \dots \ \forall x \in B_\delta(a) \quad f(x) \in U$$

<!-- page 12 -->

This means $\forall x \in B_\delta(a), \ f(x) \in U$
Thus $B_\delta(a) \subseteq f^{-1}(U)$. Therefore $f^{-1}(U)$ is open.

$(2) \implies (1):$ Suppose now preimage of open set is open.
Fix $a \in D$ and $\varepsilon > 0$.
$B_\varepsilon(f(a))$ is open, therefore $f^{-1}(B_\varepsilon(f(a)))$ is open and contains $a$.
By openness, there exists $\delta > 0$, such that
$$B_\delta(a) \subseteq f^{-1}(B_\varepsilon(f(a))),$$
Hence for all $x \in D, \ \|x - a\| < \delta$
We have $\|f(x) - f(a)\| < \varepsilon$.
This gives us continuity. $\quad \square$

Coming Next in Person:
- Continuous functions on a compact set.
- Uniform Continuity
- Differentiation.