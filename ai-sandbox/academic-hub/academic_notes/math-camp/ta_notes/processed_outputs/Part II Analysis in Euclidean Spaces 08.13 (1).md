---
source_pdf: Part II Analysis in Euclidean Spaces 08.13 (1).pdf
folder_category: ta_notes
total_pages: 5
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [real-analysis, mathematical-foundations]
---

<!-- page 1 -->

Part II: Analysis in Euclidean Spaces 08.13

Thursday, August 13, 2026  
10:50 PM

- Analysis and Calculus on $\mathbb{R}^m$.
  - What is analysis?
    - Bound things like $|x_n - a| < \varepsilon$ and so forth.
  - What is calculus?
    - Arithmetics ($+, -, \times, \div$) plus two operations
      - Differentiation: $d$
      - Integration: $\int$
  - What I will go over rather quickly:
    - $\to$ $\sup$, $\inf$, $\lim$, open/closed sets, compact sets.
    - You will see these again in Math Method in the fall.
  - What I will spend more time on:
    - Differential calculus
    - A bit time on: Riemann Integration.

- Bounds and completeness of $\mathbb{R}$.
  - "Completeness" = "No gaps". Real line has no gaps.
  - To talk about completeness, we introduce the language of bounds.
    - $M$ is an upper bound of $A \subseteq \mathbb{R}$ if
      $$x \le M \quad \text{for all } x \in A$$
    - $m$ is a lower bound of $A \subseteq \mathbb{R}$ if
      $$x \ge m \quad \text{for all } x \in A$$

Analysis in Euclidean Spaces Page 1

<!-- page 2 -->

$$x \ge m \quad \text{for all } x \in A$$

$$\overset{m}{[} \quad \underset{A}{(} \quad \underset{\quad}{)} \quad \overset{M}{]} \longrightarrow \mathbb{R}$$

Note: $\text{bounds} \neq \text{maximum}/\text{minimum}$. Precisely, $\begin{matrix} \text{Maximum} \\ \text{minimum} \end{matrix}$ are bounds.

$$a^* \in A \quad \text{max} \quad \text{if } x \le a^* \quad \forall x \in A$$
$$a_* \in A \quad \text{min} \quad \text{if } x \ge a_* \quad \forall x \in A$$

- Supremum and Infimum:
  Let $A \subseteq \mathbb{R}$, $A \neq \emptyset$ (empty set)
  $s = \sup A$ if
  1. $x \le s$ for all $x \in A$
  2. $s$ is the least upper bound:
     For every $s' < s$ there exists $x_0 \in A$ such that $s' < x \le s$

  $\bar{\iota} = \inf A$ if
  1. $x \ge \bar{\iota}$ for all $x \in A$
  2. $\bar{\iota}$ is the greatest lower bound:
     For every $\iota' > \bar{\iota}$, there exists $\tilde{x} \in A$ such that $\iota' > \tilde{x} \ge \bar{\iota}$.

When in doubt, draw a picture:

$$\underset{\inf A}{(} \overset{\iota'}{)} \qquad A \qquad \overset{s'}{(} \underset{\sup A}{)} \longrightarrow \mathbb{R}$$

- $\varepsilon$-Language for $\sup / \inf : A \neq \emptyset$
  If $s = \sup A$, then for every $\varepsilon > 0$:
  There exists some $x_\varepsilon \in A$ such that $\overset{s'}{\overbrace{s - \varepsilon}} < x_\varepsilon \le s$

  If $\bar{\iota} = \inf A$, then for every $\varepsilon > 0$:
  There exists some $x_\varepsilon \in A$ such that $\overset{\iota'}{\overbrace{\bar{\iota} + \varepsilon}} > x_\varepsilon \ge \bar{\iota}$

<!-- page 3 -->

There exists some $x_\varepsilon \in A$ such that $\overset{\iota'}{\overbrace{\bar{\iota} + \varepsilon}} > x_\varepsilon \ge \bar{\iota}$

- Simple Example: $A = [0, 1)$
  $$\begin{aligned}
  \sup A = 1 \notin A & \quad \text{then } 0 = \min A \text{ and } A \text{ has no max.} \\
  \inf A = 0 \in A &
  \end{aligned}$$

- Completeness means that every non-empty subset
  that is bounded above has a unique $\sup$.
  $\Updownarrow$
  that is bounded below has a unique $\inf$.
  $\Big\}$ Completeness Axiom.

- $\mathbb{Q}$ is NOT complete.
  $$\text{Take: } A = \{x \in \mathbb{Q} : x^2 < 2\} \quad \text{bounded} \quad \text{No } \sup / \inf \text{ in } \mathbb{Q}.$$

- Completeness means that $A \neq \emptyset$ bounded in $\mathbb{R}$
  $$\Downarrow$$
  $$\sup A / \inf A \text{ exists in } \mathbb{R}$$

- Archimedean Property:
  1. The natural numbers are not bounded above in $\mathbb{R}$
  2. For every $\varepsilon > 0$, there exists $n_\varepsilon \in \mathbb{N}$ such that
     $$0 < \frac{1}{n_\varepsilon} < \varepsilon$$

$$\underline{\text{Proof: }} 1 \quad \text{By contradiction: Suppose } \mathbb{N} \text{ is bounded above in } \mathbb{R}$$
$$\text{By completeness of } \mathbb{R} \text{ we have } s \in \mathbb{R}$$
$$s = \sup \mathbb{N}.$$
$$\text{(taking } \varepsilon = 1)$$
$$\text{Since } s - 1 < s \quad \text{by the } \varepsilon\text{-language / defn of}$$
$$\text{Supremum: } s - 1 < n \le s$$

<!-- page 4 -->

$$\begin{aligned}
&\text{Since } s - 1 < s \quad \text{by the } \varepsilon\text{-language / defn of} \\
&\text{Supremum: } \underbrace{s - 1 < n} \le s \\
&\text{Then } n + 1 > s \quad \text{but } \underline{n + 1 \in \mathbb{N}} \\
&\text{contradicting that } s \text{ is an upper bound of } \mathbb{N}. \\
2. &\text{ Let } \varepsilon > 0. \text{ Since } \mathbb{N} \text{ is NOT bounded above, there} \\
&\text{exists } n_\varepsilon \in \mathbb{N} \text{ such that} \\
&\qquad \qquad \qquad n_\varepsilon > \frac{1}{\varepsilon} \iff 0 < \frac{1}{n_\varepsilon} < \varepsilon. \qquad \qquad \qquad \sqcap \hskip -0.4em \sqcup
\end{aligned}$$

- **Fact:** Equivalent definitions of completeness:

$$\text{Every Cauchy sequence converges to a limit in } \mathbb{R}$$

$$\left[ \begin{aligned}
&\text{A sequence } \{a_n\}_{n=1}^\infty \text{ is Cauchy if for any } \varepsilon > 0, \\
&\text{there exists } N_\varepsilon \in \mathbb{N} : \forall m, n > N_\varepsilon \\
&\qquad \qquad \qquad |a_m - a_n| < \varepsilon.
\end{aligned} \right]$$

- Norms on $\mathbb{R}^n := \{x = (x_1, \dots, x_n)^T : x_i \in \mathbb{R}\}$
  - Dot product: $x \cdot y = x_1 y_1 + x_2 y_2 + \dots + x_n y_n$.
  - Euclidean Norm ($2$-Norm):
    $$\|x\| = \sqrt{x \cdot x} = \sqrt{x_1^2 + \dots + x_n^2}.$$
  - Euclidean Distance: $d_2(x, y) = \|x - y\|$.
    Triangle Inequality of $\|\cdot\|$ gives $d_2(x, z) \le d_2(x, y) + d_2(y, z)$.

$$\begin{matrix}
\text{General Principle in Analysis:} \\
\text{Inner Product} & \rightsquigarrow & \text{Norm} & \rightsquigarrow & \text{Distance / Metric} \\
\langle \cdot, \cdot \rangle & & \|\cdot\| & & d(x, y) \\
\text{Dot product} & & \text{Euclidean} & & \text{Euclidean Distance}
\end{matrix}$$

<!-- page 5 -->

$$\begin{matrix}
\langle \cdot, \cdot \rangle & & \|\cdot\| & & d(x, y) \\
\mathbb{R}^n : \text{Dot product} & & \text{Euclidean} & & \text{Euclidean Distance} \\
& & \text{Norm} & & 
\end{matrix}$$

- **Convergence in $\mathbb{R}^n$:**
  A sequence $\{x_k\}_{k=1}^\infty \subseteq \mathbb{R}^n$ converges to $a \in \mathbb{R}^n$ if
  $$\|x_k - a\| \to 0 \quad \text{as } k \to \infty$$

  Equivalently: ($\varepsilon$-$N$ Language)
  $$\{x_k\} \text{ converges to } a : \begin{aligned} &\text{if for every } \varepsilon > 0, \text{there exists } \\ &N_\varepsilon \in \mathbb{N} : \text{For all } k > N_\varepsilon \\ &\qquad \qquad \|x_k - a\| < \varepsilon. \end{aligned}$$

  We write $\lim_{k \to \infty} x_k = a$ or $x_k \to a \ (k \to \infty)$.

  If $x_k = (x_k^1, x_k^2, \dots, x_k^n)^T$ and $a = (a^1, a^2, \dots, a^n)$
  $$\text{Then } x_k \to a \iff x_k^i \to a^i \text{ for all } i.$$

  Proof uses: $\forall 1 \le i \le n$:
  $$|x_k^i - a^i| \le \|x_k - a\| \le \sqrt{n} \max_i |x_k^i - a^i| \qquad \square$$

Coming Next: Open/Closed Sets. Compact Sets (Brief).
Continuity
Differentiation.