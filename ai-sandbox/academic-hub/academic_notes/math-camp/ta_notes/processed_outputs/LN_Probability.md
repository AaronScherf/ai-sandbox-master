---
source_pdf: LN_Probability.pdf
folder_category: ta_notes
total_pages: 86
routing: gemini_batched
model: gemini-3.1-flash-lite
pages_repaired: 30
repaired_pages: [8, 10, 11, 12, 17, 19, 23, 25, 30, 33, 44, 49, 50, 51, 52, 60, 62, 64, 65, 67, 68, 72, 73, 75, 76, 77, 79, 81, 85, 86]
tags: [probability-theory-notes]
---

<!-- page 1 -->

Part IV: Probability Theory$^\dagger$

Hao Jiang$^*$

2026 PhD Math Camp

Updated on August 24, 2026

__________________________________________________________________
$^*$All remaining errors are my own.
$^\dagger$Typesetting and visual design are informed by public mathematical lecture-note templates, including Gilles
Castel’s lecture notes, rafisics’ lecture-notes template, and Jack’s Math Notes Template with Color Box.

1

<!-- page 2 -->

Contents

Introduction . . . 6

1 Probability Spaces and Events . . . 7
1.1 Outcomes, sample spaces, and events . . . 7
1.2 Event algebra and basic probability identities . . . 8
1.3 Sigma-algebras . . . 9
1.4 Generated sigma-algebras and Borel sets . . . 10
1.5 Probability measures . . . 11
1.6 Continuity of probability . . . 12
1.7 Conditional probability, total probability, and Bayes’ rule . . . 12
1.8 Equally likely outcomes and counting . . . 14
1.9 Inclusion–exclusion, partitions, and multinomial counting . . . 16
1.10 Independence . . . 17
1.11 Limsup events and Borel–Cantelli . . . 18
1.12 Product spaces and infinite sequences . . . 19
1.13 Tail events and Kolmogorov’s zero–one law . . . 20

2 Random Variables and Distributions . . . 20
2.1 From outcomes to numerical random variables . . . 21
2.2 Random variables as measurable maps . . . 21
2.3 Indicators: events as random variables . . . 22
2.4 The law as a pushforward measure . . . 22
2.5 CDFs . . . 23
2.6 Discrete, continuous, and mixed distributions . . . 24
2.7 Quantiles and inverse transforms . . . 26
2.8 Transformations of random variables . . . 26
2.9 Joint, marginal, and conditional distributions . . . 28

3 Expectation, Integration, and Moments . . . 29
3.1 Elementary expectation: weighted averages . . . 29
3.2 Expectation as an integral . . . 30
3.3 LOTUS . . . 31

2

<!-- page 3 -->

3.4 Linearity and moments . . . 32
3.5 Variance, covariance, correlation, and standardized moments . . . 32
3.6 Convergence theorems for expectations . . . 33
3.7 Inequalities . . . 35
3.8 $L^p$ spaces and Hölder inequalities . . . 35
3.9 Tail-integral formulas . . . 36
3.10 Tonelli and Fubini . . . 36

4 Conditional Expectation and Information 37
4.1 Elementary conditional expectation . . . 37
4.2 Conditioning on a sigma-algebra . . . 37
4.3 Core properties . . . 38
4.4 Conditional expectation as an $L^2$ projection . . . 39
4.5 Best prediction and Gaussian conditioning . . . 39
4.6 Conditional distributions as random probability measures . . . 40
4.7 A change-of-measure viewpoint . . . 40
4.8 Conditional variance and variance decomposition . . . 41

5 Common Distributions, Transformations, and Transforms 41
5.1 Discrete families . . . 41
5.2 Continuous families . . . 42
5.3 Normal and multivariate normal distributions . . . 43
5.4 Relations among the basic families . . . 44
5.5 A compact distribution table . . . 45
5.6 Convolution . . . 45
5.7 Moment-generating and characteristic functions . . . 46

6 Random Vectors, Sampling, and Order Statistics 47
6.1 Joint PMFs and PDFs: the computational layer . . . 47
6.2 Random vectors and covariance matrices . . . 48
6.3 Multivariate changes of variables . . . 49
6.4 Random samples and statistics . . . 49
6.5 Order statistics . . . 50
6.6 Sample mean and sample variance . . . 51

3

<!-- page 4 -->

6.7 Normal samples, chi-square, and Student’s $t$ . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 52

6.8 Empirical measures . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 52

7 Modes of Stochastic Convergence 53

7.1 Four notions of convergence . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 53

7.2 A counterexample to probability implying almost sure . . . . . . . . . . . . . . . . . . . . . . . . . 55

7.3 Subsequence characterization of convergence in probability . . . . . . . . . . . . . . . . . . . . . 56

7.4 Continuous Mapping Theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 56

7.5 Slutsky’s theorem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 57

7.6 Convergence of expectations and uniform integrability . . . . . . . . . . . . . . . . . . . . . . . . . 57

7.7 Stochastic order notation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 58

7.8 Weak convergence and the Portmanteau viewpoint . . . . . . . . . . . . . . . . . . . . . . . . . . . . 59

7.9 Cramér–Wold device . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 59

8 Laws of Large Numbers 60

8.1 Sample averages . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 60

8.2 Weak law via Chebyshev . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 60

8.3 Strong law . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 61

8.4 Exponential concentration: Chernoff and Hoeffding bounds . . . . . . . . . . . . . . . . . . . . 61

8.5 Sample moments . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 62

8.6 Empirical distribution and Glivenko–Cantelli . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 62

8.7 Beyond iid: what changes? . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 63

9 Central Limit Theory and Asymptotic Calculus 63

9.1 Why the $\sqrt{n}$ scaling appears . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 63

9.2 Lindeberg–Lévy CLT . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 64

9.3 Characteristic-function proof . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 64

9.4 Multivariate CLT . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 65

9.5 Delta method . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 65

9.6 Asymptotic linearization . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 66

9.7 Studentization and plug-in variance estimation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 67

9.8 Estimating equations: LLN + Taylor + CLT . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 67

9.9 Berry–Esseen and rates . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 68

4

<!-- page 5 -->

10 Stochastic Processes: Martingales and Markov Chains . . . 68
10.1 Stochastic processes and filtrations . . . 68
10.2 Martingales . . . 69
10.3 Markov chains . . . 69
10.4 Stationarity and an ergodic LLN . . . 70

11 Further Distributional Tools for Economists . . . 70
11.1 Joint moment-generating and characteristic functions . . . 70
11.2 Linear combinations, portfolios, and covariance accounting . . . 72
11.3 The $F$ distribution and ratios of quadratic forms . . . 72
11.4 Mixture distributions and latent heterogeneity . . . 73

12 Sampling Distributions and Finite-Sample Calculations . . . 74
12.1 Population, random sample, statistic, and sampling distribution . . . 74
12.2 Exact sampling distribution of a sample proportion . . . 75
12.3 Exact sampling distributions closed under summation . . . 75
12.4 Standard deviation, standard error, and estimated standard error . . . 76
12.5 Normal samples: the exact $z$, $\chi^2$, $t$, and $F$ structure . . . 77
12.6 Simple random sampling without replacement . . . 77
12.7 Normal approximation to the binomial and continuity correction . . . 78
12.8 When to use an exact distribution and when to use an asymptotic one . . . 79

13 Hazards, Poisson Arrivals, and Simulation . . . 79
13.1 Survival functions and hazard rates . . . 79
13.2 Competing exponential clocks . . . 81
13.3 The Poisson process . . . 82
13.4 Superposition and thinning of Poisson processes . . . 82
13.5 Probability integral transform . . . 83
13.6 Inverse-transform simulation . . . 83
13.7 Monte Carlo integration . . . 84
13.8 Importance sampling: a change-of-measure identity . . . 85

14 References and Further Reading . . . 85

5

<!-- page 6 -->

# Introduction

Probability theory enters economics both as a language for uncertainty and as a theory of approximation. At the computational level, we manipulate events, conditional probabilities, random variables, densities, expectations, and familiar distribution families. At the rigorous level, the same objects are probability measures, measurable maps, integrals, conditional expectations relative to information, and modes of convergence. The aim of this part is to develop both levels together.

The organizing progression is

$$\text{probability spaces} \longrightarrow \text{random variables} \longrightarrow \text{expectation and conditioning} \longrightarrow \text{sampling}$$
$$\longrightarrow \text{stochastic convergence} \longrightarrow \text{LLN and CLT.}$$

The elementary and rigorous treatments should reinforce one another. For instance,

$$\mathbb{E}[X] = \sum_{x} x \mathbb{P}(X = x) \quad \text{and} \quad \mathbb{E}[X] = \int_{\mathbb{R}} x f_X(x) \, dx$$

are both special cases of

$$\mathbb{E}[X] = \int_{\Omega} X(\omega) \, d\mathbb{P}(\omega).$$

Likewise, a conditional mean such as

$$\mathbb{E}[Y \mid X = x]$$

is the computational version of the conditional-expectation object

$$\mathbb{E}[Y \mid \sigma(X)],$$

and the statement that sample averages “settle down” separates into several distinct notions of stochastic convergence.

[Diagram: A grid of boxes with arrows]
*   **events and conditioning** $\longrightarrow$ **random variables and laws** $\longrightarrow$ **expectation and integration**
*   **random vectors and sampling** $\longrightarrow$ **conditional expectation** $\longrightarrow$ **stochastic convergence**
*   **laws of large numbers** $\longrightarrow$ **central limit theory** $\longrightarrow$ **asymptotic calculus**

Figure 1: A roadmap for Part IV. The computational layer and the measure-theoretic layer are developed together, then used to organize sampling and asymptotic arguments.

6

<!-- page 7 -->

The notes are deliberately selective about proofs. Proofs are included when they reveal a reusable argument: continuity of probability measures, the convergence theorems for expectations, basic implications among modes of convergence, the weak law, continuous mapping, Slutsky, and the delta method. Deep existence theorems such as Carathéodory extension and Radon–Nikodym are stated and used rather than reproved in full.

**Reading map.** The computational core draws especially on Yongmiao Hong, *Probability and Statistics for Economists*, Bertsekas and Tsitsiklis, *Introduction to Probability*, and Blitzstein and Hwang, *Introduction to Probability*. Hong is particularly useful for the sequence from counting and conditional probability through random variables, transformations, moments, standard distributions, and multivariate probability before asymptotic theory begins. Williams, *Probability with Martingales*, provides a concise rigorous route from probability spaces through integration and conditional expectation to convergence and martingales. Klenke, *Probability Theory: A Comprehensive Course*, is the main reference for the measure-theoretic layer. Durrett and Billingsley supply complementary graduate treatments of limit theory. Hansen, *Probability and Statistics for Economists*, is used to keep the sampling and asymptotic material aligned with the needs of first-year economics PhD courses, while van der Vaart, *Asymptotic Statistics*, points toward the econometric theory that follows.

# 1 Probability Spaces and Events

**Sources.** The elementary sequence in this section follows the emphasis of Yongmiao Hong, especially event algebra, methods of counting, conditional probability, Bayes’ theorem, and independence; the computational treatment is supplemented by Bertsekas–Tsitsiklis and Blitzstein–Hwang. The measure-theoretic formulation, independence of sigma-algebras, Borel–Cantelli lemmas, and product-space viewpoint follow the standard graduate development in Williams, Klenke, and Durrett.

## 1.1 Outcomes, sample spaces, and events

A probability model begins with a set $\Omega$ of possible outcomes. An event is a collection of outcomes whose probability we wish to discuss.

**Example 1.1 — Two coin tosses**

Let
$$\Omega = \{HH, HT, TH, TT\}.$$
The event “exactly one head” is
$$A = \{HT, TH\}.$$

7

<!-- page 8 -->

The event “the first toss is a head” is
$B = \{HH, HT\}$.
Then
$A \cap B = \{HT\}$, $\quad A \cup B = \{HH, HT, TH\}$, $\quad B^c = \{TH, TT\}$.

For finite models, one could assign probabilities to every subset of $\Omega$. On an uncountable sample space, that is generally too much to ask. We therefore specify which subsets count as measurable events.

### 1.2 Event algebra and basic probability identities

Before introducing sigma-algebras, it is useful to be completely fluent with the algebra of events. If $A, B \subseteq \Omega$, then
$A^c = \Omega \setminus A$, $\quad A \setminus B = A \cap B^c$.

The events $A \cup B$ and $A \cap B$ mean, respectively, “at least one of $A$ or $B$ occurs” and “both $A$ and $B$ occur.” De Morgan’s laws are
$(A \cup B)^c = A^c \cap B^c$, $\quad (A \cap B)^c = A^c \cup B^c$.

For a sequence of events,
$\left( \bigcup_{n=1}^{\infty} A_n \right)^c = \bigcap_{n=1}^{\infty} A_n^c$, $\quad \left( \bigcap_{n=1}^{\infty} A_n \right)^c = \bigcup_{n=1}^{\infty} A_n^c$.

The most useful finite probability identities are
$\mathbb{P}(A^c) = 1 - \mathbb{P}(A)$,
$\mathbb{P}(A \cup B) = \mathbb{P}(A) + \mathbb{P}(B) - \mathbb{P}(A \cap B)$,
and, if $A \cap B = \emptyset$,
$\mathbb{P}(A \cup B) = \mathbb{P}(A) + \mathbb{P}(B)$.

**Example 1.2 — Translating words into events**
Let $A$ denote “a household is liquidity constrained” and $B$ denote “the household is unemployed.” Then
$A \cup B$

8

<!-- page 9 -->

means that at least one condition holds,
$$A \cup B$$
means both conditions hold,
$$A \cap B$$
means constrained but employed, and
$$(A \cap B)^c = A^c \cup B^c$$
means that at least one of the two conditions fails.
A surprisingly large fraction of elementary probability mistakes occur before any probability
is calculated: the event itself has been translated incorrectly.

### Example 1.3 — Two dice
Roll two fair six-sided dice. The natural sample space is
$$\Omega = \{(i, j) : i, j \in \{1, \dots, 6\}\}, \quad |\Omega| = 36.$$
Let
$$A = \{(i, j) : i + j = 7\}, \quad B = \{(i, j) : i = j\}.$$
Then
$$|A| = 6, \quad |B| = 6, \quad A \cap B = \emptyset,$$
so
$$\mathbb{P}(A \cup B) = \frac{12}{36} = \frac{1}{3}.$$
The point of the example is methodological: first specify the elementary outcomes, then
identify the event, and only then count.

## 1.3 Sigma-algebras

### Definition 1.4 — Sigma-algebra
A collection $\mathcal{F} \subseteq 2^\Omega$ is a sigma-algebra if
1. $\Omega \in \mathcal{F}$;
2. $A \in \mathcal{F} \Rightarrow A^c \in \mathcal{F}$;

9

<!-- page 10 -->

3. if $A_1, A_2, \dots \in \mathcal{F}$, then
$$\bigcup_{n=1}^{\infty} A_n \in \mathcal{F}.$$
The pair $(\Omega, \mathcal{F})$ is called a measurable space.

Closure under complements and countable unions implies closure under countable intersections by De Morgan’s law:
$$\bigcap_{n=1}^{\infty} A_n = \left( \bigcup_{n=1}^{\infty} A_n^c \right)^c.$$

The insistence on *countable* operations is essential. Limits of sequences are central in probability, and events such as
$$\{X_n \to X\}$$
are built from countable unions and intersections.

**Example 1.5 — Sigma-algebra generated by a partition**

Suppose $\Omega = \{1, 2, 3, 4\}$ and the only distinction an observer can make is whether the outcome lies in $\{1, 2\}$ or $\{3, 4\}$. Then the natural information set is
$$\mathcal{F} = \{\emptyset, \{1, 2\}, \{3, 4\}, \Omega\}.$$
This is a sigma-algebra. It records exactly the events that can be decided from the observer’s information.

### 1.4 Generated sigma-algebras and Borel sets

Given a family $\mathcal{C} \subseteq 2^\Omega$, the sigma-algebra generated by $\mathcal{C}$ is
$$\sigma(\mathcal{C}) = \bigcap \{\mathcal{F} : \mathcal{F} \text{ is a sigma-algebra and } \mathcal{C} \subseteq \mathcal{F}\}.$$
It is the smallest sigma-algebra containing $\mathcal{C}$.

On $\mathbb{R}$, the most important sigma-algebra is the Borel sigma-algebra
$$\mathcal{B}(\mathbb{R}) = \sigma(\{(-\infty, x] : x \in \mathbb{R}\}).$$
Equivalently, it is generated by the open sets. On $\mathbb{R}^k$, we write $\mathcal{B}(\mathbb{R}^k)$.

10

<!-- page 11 -->

**Remark 1.6 — Rigorous layer: Why Borel sets are enough for most economics**

A random variable taking values in $\mathbb{R}^k$ will be required to be measurable with respect to $\mathcal{B}(\mathbb{R}^k)$. This guarantees that familiar events such as $\{X \leq x\}$, $\{a < X < b\}$, and $\{X \in C\}$ for open or closed $C$ are measurable. One rarely needs to manipulate exotic non-Borel sets directly.

### 1.5 Probability measures

**Definition 1.7 — Probability measure**

A probability measure on $(\Omega, \mathcal{F})$ is a function
$$\mathbb{P} : \mathcal{F} \to [0, 1]$$
satisfying
1. $\mathbb{P}(\Omega) = 1$;
2. if $A_1, A_2, \dots \in \mathcal{F}$ are pairwise disjoint, then
$$\mathbb{P}\left(\bigcup_{n=1}^{\infty} A_n\right) = \sum_{n=1}^{\infty} \mathbb{P}(A_n).$$

The triple $(\Omega, \mathcal{F}, \mathbb{P})$ is a probability space.

Immediate consequences include
$$\mathbb{P}(\emptyset) = 0, \quad \mathbb{P}(A^c) = 1 - \mathbb{P}(A),$$
$$A \subseteq B \implies \mathbb{P}(A) \leq \mathbb{P}(B),$$
and
$$\mathbb{P}(A \cup B) = \mathbb{P}(A) + \mathbb{P}(B) - \mathbb{P}(A \cap B).$$

More generally, Boole’s inequality gives
$$\mathbb{P}\left(\bigcup_{n=1}^{\infty} A_n\right) \leq \sum_{n=1}^{\infty} \mathbb{P}(A_n).$$

11

<!-- page 12 -->

1.6 Continuity of probability

**Proposition 1.8 — Continuity from below**

If
$$A_1 \subseteq A_2 \subseteq \dots, \quad A = \bigcup_{n=1}^{\infty} A_n,$$
then
$$\mathbb{P}(A_n) \to \mathbb{P}(A).$$

**Proof**

Write
$$B_1 = A_1, \quad B_n = A_n \setminus A_{n-1} \quad (n \geq 2).$$
The $B_n$ are disjoint and
$$A_n = \bigcup_{j=1}^{n} B_j, \quad A = \bigcup_{j=1}^{\infty} B_j.$$
Hence
$$\mathbb{P}(A_n) = \sum_{j=1}^{n} \mathbb{P}(B_j) \to \sum_{j=1}^{\infty} \mathbb{P}(B_j) = \mathbb{P}(A).$$

**Proposition 1.9 — Continuity from above**

If
$$A_1 \supseteq A_2 \supseteq \dots, \quad A = \bigcap_{n=1}^{\infty} A_n,$$
then
$$\mathbb{P}(A_n) \to \mathbb{P}(A).$$

This follows by applying continuity from below to the complements.

**1.7 Conditional probability, total probability, and Bayes’ rule**

Conditioning changes the relevant population. If $\mathbb{P}(B) > 0$, then among the outcomes for which $B$ occurs, the fraction for which $A$ also occurs is
$$\mathbb{P}(A \mid B) = \frac{\mathbb{P}(A \cap B)}{\mathbb{P}(B)}.$$

12

<!-- page 13 -->

Equivalently, the *multiplication rule* is
$$\mathbb{P}(A \cap B) = \mathbb{P}(A \mid B)\mathbb{P}(B) = \mathbb{P}(B \mid A)\mathbb{P}(A).$$
More generally,
$$\mathbb{P}(A_1 \cap \dots \cap A_n) = \mathbb{P}(A_1) \prod_{j=2}^n \mathbb{P}(A_j \mid A_1 \cap \dots \cap A_{j-1}),$$
whenever the conditioning events have positive probability.

**Example 1.10 — Cards without replacement**
Draw two cards without replacement from a standard 52-card deck. Let $A$ be the event that the first card is an ace and $B$ the event that the second card is an ace. Then
$$\mathbb{P}(A) = \frac{4}{52}, \quad \mathbb{P}(B \mid A) = \frac{3}{51}.$$
Hence
$$\mathbb{P}(A \cap B) = \frac{4}{52} \frac{3}{51} = \frac{1}{221}.$$
The events are not independent: observing an ace on the first draw changes the probability of an ace on the second draw.

Suppose $B_1, \dots, B_m$ form a partition of $\Omega$ with $\mathbb{P}(B_j) > 0$. Then
$$A = (A \cap B_1) \cup \dots \cup (A \cap B_m)$$
is a disjoint union, so the *law of total probability* is
$$\mathbb{P}(A) = \sum_{j=1}^m \mathbb{P}(A \mid B_j)\mathbb{P}(B_j).$$
Combining this identity with the multiplication rule yields Bayes' formula:
$$\mathbb{P}(B_j \mid A) = \frac{\mathbb{P}(A \mid B_j)\mathbb{P}(B_j)}{\sum_{\ell=1}^m \mathbb{P}(A \mid B_\ell)\mathbb{P}(B_\ell)}.$$

**Example 1.11 — A screening problem**
Suppose 2% of a population has a condition. A test has sensitivity 95% and false-positive probability 5%:
$$\mathbb{P}(+ \mid D) = 0.95, \quad \mathbb{P}(+ \mid D^c) = 0.05, \quad \mathbb{P}(D) = 0.02.$$

<!-- page 14 -->

The unconditional positive-test probability is
$$\mathbb{P}(+) = 0.95(0.02) + 0.05(0.98) = 0.068.$$
Therefore
$$\mathbb{P}(D \mid +) = \frac{0.95(0.02)}{0.068} \approx 0.279.$$
A highly accurate signal need not imply a high posterior when the prior event is rare. This is the same prior-likelihood-posterior logic used throughout Bayesian economics.

For fixed $B$, the map $A \mapsto \mathbb{P}(A \mid B)$ is itself a probability measure.

**Example 1.12 — Signal extraction**
Suppose a high type occurs with prior probability $\pi$. A signal $S \in \{0, 1\}$ satisfies
$$\mathbb{P}(S = 1 \mid H) = q_H, \quad \mathbb{P}(S = 1 \mid L) = q_L.$$
Then the posterior probability of the high type after observing $S = 1$ is
$$\mathbb{P}(H \mid S = 1) = \frac{q_H \pi}{q_H \pi + q_L(1 - \pi)}.$$
This is the discrete prototype of Bayesian updating and filtering.

**1.8 Equally likely outcomes and counting**
Many basic probability calculations reduce to counting. The basic tool is the *multiplication principle*: if a procedure has $m$ possible outcomes at the first stage and, for each of these, $n$ possible outcomes at the second stage, then there are $mn$ possible ordered outcomes in total. Iterating gives
$$n_1 n_2 \dots n_k$$
possibilities for a $k$-stage procedure with $n_j$ choices at stage $j$.
Three formulas should be immediately recognizable:
$$\underbrace{n^k}_{\substack{\text{ordered draws} \\ \text{with replacement}}}, \quad \underbrace{\frac{n!}{(n-k)!}}_{\substack{\text{ordered draws} \\ \text{without replacement}}}, \quad \underbrace{\binom{n}{k}}_{\substack{\text{unordered draws} \\ \text{without replacement}}}.$$
When $n$ objects contain repeated types with multiplicities $n_1, \dots, n_r$, $\sum_j n_j = n$, the number of distinct orderings is
$$\frac{n!}{n_1! \dots n_r!}.$$

<!-- page 15 -->

**Example 1.13 — A committee problem**
A class has 12 students, of whom 5 are first-year and 7 are second-year. A three-person committee is chosen uniformly from all three-person subsets. The number of committees is
$$\binom{12}{3} = 220.$$
The number with exactly two first-year students is
$$\binom{5}{2} \binom{7}{1} = 70,$$
so
$$\mathbb{P}(\text{exactly two first-years}) = \frac{70}{220} = \frac{7}{22}.$$

**Remark 1.14 — With or without replacement? Ordered or unordered?**
Before writing a factorial or binomial coefficient, ask:
1. Are outcomes equally likely?
2. Does order matter?
3. Is sampling with or without replacement?
4. Are repeated types distinguishable?
Most counting errors are resolved by answering these questions before manipulating formulas.

When the sample space is finite and each outcome is equally likely,
$$\mathbb{P}(A) = \frac{|A|}{|\Omega|}.$$
Probability then reduces to a counting problem.
For $n$ distinct objects,
$$n!$$
is the number of possible orderings. The number of ordered selections of $k$ distinct objects is
$$\frac{n!}{(n-k)!}$$
while the number of unordered $k$-element subsets is
$$\binom{n}{k} = \frac{n!}{k!(n-k)!}.$$

<!-- page 16 -->

The binomial identity
$$(a + b)^n = \sum_{k=0}^n \binom{n}{k} a^k b^{n-k}$$
is the algebraic reason the binomial PMF sums to one.

**Example 1.15 — Sampling without replacement**
A population contains $N$ objects, of which $K$ are labeled "success." Draw $n$ objects without replacement and let $X$ be the number of successes. Then
$$\mathbb{P}(X = x) = \frac{\binom{K}{x} \binom{N-K}{n-x}}{\binom{N}{n}},$$
for feasible $x$. This is the hypergeometric distribution.
The numerator counts samples with exactly $x$ successes; the denominator counts all samples of size $n$.

**Example 1.16 — Birthday collisions**
With $m$ people and 365 equally likely birthdays, the probability of no shared birthday is
$$\frac{365}{365} \cdot \frac{364}{365} \dots \frac{365 - m + 1}{365}.$$
Therefore
$$\mathbb{P}(\text{at least one collision}) = 1 - \prod_{j=0}^{m-1} \left(1 - \frac{j}{365}\right).$$
The complement is much easier to count than the event itself. This is a useful general strategy.

**1.9 Inclusion–exclusion, partitions, and multinomial counting**
For two events,
$$\mathbb{P}(A \cup B) = \mathbb{P}(A) + \mathbb{P}(B) - \mathbb{P}(A \cap B).$$
For three events,
$$\mathbb{P}(A \cup B \cup C) = \mathbb{P}(A) + \mathbb{P}(B) + \mathbb{P}(C)$$
$$- \mathbb{P}(A \cap B) - \mathbb{P}(A \cap C) - \mathbb{P}(B \cap C) + \mathbb{P}(A \cap B \cap C).$$
The general inclusion–exclusion principle alternates sums over intersections of one, two, three, and more events. In practice the two- and three-event formulas are the ones most often used directly.

<!-- page 17 -->

If a population of size $n$ is split into labeled groups of sizes $n_1, \dots, n_k$ with
$$\sum_{j=1}^k n_j = n,$$
then the number of allocations is the multinomial coefficient
$$\binom{n}{n_1, \dots, n_k} = \frac{n!}{n_1! \dots n_k!}.$$
Correspondingly,
$$(x_1 + \dots + x_k)^n = \sum_{n_1 + \dots + n_k = n} \binom{n}{n_1, \dots, n_k} \prod_{j=1}^k x_j^{n_j}.$$
This identity is the normalization behind the multinomial distribution.

**Example 1.17 — Multinomial counts**
Suppose $n$ independent observations fall into $k$ categories with probabilities $p_1, \dots, p_k$, $\sum_j p_j = 1$. If $N_j$ is the count in category $j$, then
$$\mathbb{P}(N_1 = n_1, \dots, N_k = n_k) = \frac{n!}{n_1! \dots n_k!} \prod_{j=1}^k p_j^{n_j}.$$
The counts satisfy $\sum_j N_j = n$, so the covariance matrix is singular. In fact,
$$\text{Var}(N_j) = np_j(1 - p_j), \quad \text{Cov}(N_j, N_\ell) = -np_j p_\ell \quad (j \neq \ell).$$

**1.10 Independence**
**Definition 1.18 — Independence of events**
Events $A, B \in \mathcal{F}$ are independent if
$$\mathbb{P}(A \cap B) = \mathbb{P}(A)\mathbb{P}(B).$$
A family $\{A_i\}_{i \in I}$ is mutually independent if for every finite collection of distinct indices $i_1, \dots, i_m$,
$$\mathbb{P}\left(\bigcap_{j=1}^m A_{i_j}\right) = \prod_{j=1}^m \mathbb{P}(A_{i_j}).$$
Pairwise independence is weaker than mutual independence.

<!-- page 18 -->

**Example 1.19 — Pairwise but not mutually independent**
Let two fair coin tosses be $(U, V) \in \{0, 1\}^2$, and define
$$A = \{U = 1\}, \quad B = \{V = 1\}, \quad C = \{U \oplus V = 1\}.$$
Each pair is independent, but $A \cap B \cap C = \emptyset$, so the three events are not mutually independent.

Independence can also be written as a statement about conditioning. If $\mathbb{P}(B) > 0$, then
$$A \perp B \iff \mathbb{P}(A \mid B) = \mathbb{P}(A).$$
Thus independence means that learning whether $B$ occurred provides no information about $A$.
Conditional independence is different. Events $A$ and $B$ are conditionally independent given $C$ if
$$\mathbb{P}(A \cap B \mid C) = \mathbb{P}(A \mid C)\mathbb{P}(B \mid C).$$
Two variables can be dependent unconditionally but independent after conditioning on a common state, or the reverse. This distinction becomes central in econometrics and graphical models.

**Remark 1.20 — Rigorous layer: Independence of sigma-algebras**
Sigma-algebras $\mathcal{F}_1, \dots, \mathcal{F}_m$ are independent if
$$\mathbb{P}(A_1 \cap \dots \cap A_m) = \prod_{j=1}^m \mathbb{P}(A_j)$$
for all $A_j \in \mathcal{F}_j$. This is the right definition for random variables and stochastic processes: random variables $X_1, \dots, X_m$ are independent precisely when $\sigma(X_1), \dots, \sigma(X_m)$ are independent.

**1.11 Limsup events and Borel–Cantelli**
For events $A_n$, define
$$\limsup_{n \to \infty} A_n = \bigcap_{N=1}^\infty \bigcup_{n \ge N} A_n.$$
An outcome lies in $\limsup A_n$ exactly when infinitely many $A_n$ occur. We often write
$$\{A_n \text{ i.o.}\} = \limsup A_n.$$

<!-- page 19 -->

**Theorem 1.21 — First Borel–Cantelli lemma**
If
$$\sum_{n=1}^\infty \mathbb{P}(A_n) < \infty,$$
then
$$\mathbb{P}(A_n \text{ i.o.}) = 0.$$

**Proof**
For every $N$,
$$\mathbb{P}\left(\bigcup_{n \ge N} A_n\right) \le \sum_{n \ge N} \mathbb{P}(A_n).$$
The right side tends to zero. Since the sets $\cup_{n \ge N} A_n$ decrease to $\limsup A_n$, continuity from above yields the result.

**Remark 1.22 — Rigorous layer: Second Borel–Cantelli lemma**
If $A_1, A_2, \dots$ are independent and
$$\sum_{n=1}^\infty \mathbb{P}(A_n) = \infty,$$
then
$$\mathbb{P}(A_n \text{ i.o.}) = 1.$$
Thus, under independence, summability separates events that occur only finitely often from events that occur infinitely often almost surely.

**1.12 Product spaces and infinite sequences**
Many probability models concern a sequence $(X_1, X_2, \dots)$. Formally, repeated sampling is naturally represented on a product space. For two probability spaces
$$(\Omega_1, \mathcal{F}_1, \mathbb{P}_1), \quad (\Omega_2, \mathcal{F}_2, \mathbb{P}_2),$$
the product sigma-algebra $\mathcal{F}_1 \otimes \mathcal{F}_2$ is generated by measurable rectangles $A_1 \times A_2$, and the product probability measure is characterized by
$$(\mathbb{P}_1 \otimes \mathbb{P}_2)(A_1 \times A_2) = \mathbb{P}_1(A_1)\mathbb{P}_2(A_2).$$
Independence is therefore built into product probability.

<!-- page 20 -->

**Remark 1.23 — Rigorous layer: Existence of an iid sequence**
Given any probability law $\mu$ on $(\mathbb{R}, \mathcal{B}(\mathbb{R}))$, there exists a probability measure on the infinite product space $\mathbb{R}^\mathbb{N}$ under which the coordinate maps
$$X_j(\omega) = \omega_j$$
are iid with common law $\mu$. The full construction uses a consistency/extension theorem. For this course, the important point is that the familiar phrase "let $X_1, X_2, \dots$ be iid" has a rigorous probability-space realization.

**1.13 Tail events and Kolmogorov’s zero–one law**
For independent random variables $X_1, X_2, \dots$, define the tail sigma-algebra
$$\mathcal{T} = \bigcap_{n=1}^\infty \sigma(X_n, X_{n+1}, \dots).$$
A tail event is unaffected by changing any finite number of coordinates. Examples include convergence of $\sum_n X_n$, the event $\{X_n \text{ exceeds a threshold infinitely often}\}$, and long-run limiting events.

**Remark 1.24 — Rigorous layer: Kolmogorov zero–one law**
If $X_1, X_2, \dots$ are independent, then every tail event $A \in \mathcal{T}$ satisfies
$$\mathbb{P}(A) \in \{0, 1\}.$$
Thus many asymptotic events generated by independent sequences cannot have an intermediate probability. This result is one reason almost-sure limit theory is often sharper than a naive finite-sample interpretation suggests.

**2 Random Variables and Distributions**
**Sources.** Hong is the main guide for the basic sequence from random variables to CDFs, discrete and continuous laws, transformations, expectations, moments, quantiles, MGFs, and characteristic functions; for additional problems and transformations, compare Blitzstein–Hwang and Bertsekas–Tsitsiklis. For measurable maps, pushforward laws, and the Borel structure on Euclidean spaces, the main rigorous references are Williams and Klenke.

<!-- page 21 -->

**2.1 From outcomes to numerical random variables**
In elementary probability, a random variable is first encountered as a numerical summary of an uncertain outcome. For example, with two coin tosses,
$$\Omega = \{HH, HT, TH, TT\},$$
define $X$ to be the number of heads:
$$X(HH) = 2, \quad X(HT) = X(TH) = 1, \quad X(TT) = 0.$$
If the coins are fair and independent, then
$$\mathbb{P}(X = 0) = \frac{1}{4}, \quad \mathbb{P}(X = 1) = \frac{1}{2}, \quad \mathbb{P}(X = 2) = \frac{1}{4}.$$
Thus the original outcome $\omega$ may be complicated, while $X(\omega)$ extracts the numerical feature relevant for the question at hand.
For a discrete random variable, its support is
$$\text{supp}(X) = \{x : \mathbb{P}(X = x) > 0\},$$
and its probability mass function is
$$p_X(x) = \mathbb{P}(X = x).$$
The normalization condition is
$$\sum_{x \in \text{supp}(X)} p_X(x) = 1.$$
The rigorous definition below adds one condition—measurability—which guarantees that events generated by the numerical summary have well-defined probabilities.

**2.2 Random variables as measurable maps**
A random variable is not itself random in the mathematical definition: it is a function on the sample space. Randomness enters through the probability measure on outcomes.

**Definition 2.1 — Random variable**
A function
$$X : (\Omega, \mathcal{F}) \to (\mathbb{R}, \mathcal{B}(\mathbb{R}))$$
is a random variable if it is measurable, meaning
$$X^{-1}(B) = \{\omega : X(\omega) \in B\} \in \mathcal{F}$$

<!-- page 22 -->

for every Borel set $B \subseteq \mathbb{R}$.
It is enough to verify
$$\{X \le x\} \in \mathcal{F} \quad \forall x \in \mathbb{R}.$$
A random vector $X : \Omega \to \mathbb{R}^k$ is defined similarly using $\mathcal{B}(\mathbb{R}^k)$.

**2.3 Indicators: events as random variables**
For an event $A \in \mathcal{F}$, define its indicator
$$\mathbf{1}_A(\omega) = \begin{cases} 1, & \omega \in A, \\ 0, & \omega \notin A. \end{cases}$$
Then
$$\mathbb{E}[\mathbf{1}_A] = \mathbb{P}(A).$$
Indicators convert set operations into algebra. For example,
$$\mathbf{1}_{A \cap B} = \mathbf{1}_A \mathbf{1}_B, \quad \mathbf{1}_{A^c} = 1 - \mathbf{1}_A.$$
Also,
$$\mathbf{1}_{\cup_{j=1}^m A_j} \le \sum_{j=1}^m \mathbf{1}_{A_j},$$
which yields the union bound after taking expectations.
Indicators are one of the most useful devices in probability. Counting a random number of events often reduces to summing indicators:
$$N = \sum_{j=1}^m \mathbf{1}_{A_j}, \quad \mathbb{E}[N] = \sum_{j=1}^m \mathbb{P}(A_j).$$
No independence is required for this expectation formula.

**2.4 The law as a pushforward measure**
**Definition 2.2 — Distribution or law**
The law of $X$ is the probability measure $\mathcal{L}(X)$ on $\mathbb{R}$ defined by
$$\mathcal{L}(X)(B) = \mathbb{P}(X \in B) = \mathbb{P}(X^{-1}(B)).$$

<!-- page 23 -->

We also write
$$\mathbb{P}_X = \mathbb{P} \circ X^{-1}.$$
This viewpoint cleanly separates the underlying sample space from the observable distribution of $X$. Two random variables defined on different probability spaces can have the same law.

**2.5 CDFs**
**Definition 2.3 — Cumulative distribution function**
The CDF of $X$ is
$$F_X(x) = \mathbb{P}(X \le x).$$
Every CDF satisfies
1. $F_X$ is nondecreasing;
2. $F_X$ is right-continuous;
3. $F_X(x) \to 0$ as $x \to -\infty$;
4. $F_X(x) \to 1$ as $x \to +\infty$.
Conversely, every function with these four properties is the CDF of some probability distribution.
The jump at $x$ equals the point mass:
$$F_X(x) - F_X(x^-) = \mathbb{P}(X = x).$$

**Example 2.4 — CDF of a Bernoulli variable**
If $X \sim \text{Bern}(p)$, then
$$F_X(x) = \begin{cases} 0, & x < 0, \\ 1 - p, & 0 \le x < 1, \\ 1, & x \ge 1. \end{cases}$$
The jump sizes are exactly the point probabilities.

**Example 2.5 — CDF determines probabilities**
For any $a < b$,
$$\mathbb{P}(a < X \le b) = F_X(b) - F_X(a).$$
If $F_X$ is continuous,
$$\mathbb{P}(a \le X \le b) = F_X(b) - F_X(a),$$

<!-- page 24 -->

because the endpoints have zero mass.

**Proposition 2.6 — Characterization of distribution functions**
A function $F : \mathbb{R} \to [0, 1]$ is the CDF of some real-valued random variable if and only if
1. $F$ is nondecreasing;
2. $F$ is right-continuous;
3. $\lim_{x \to -\infty} F(x) = 0$ and $\lim_{x \to \infty} F(x) = 1$.

**Remark 2.7 — Rigorous layer: The probability measure induced by a CDF**
Every CDF $F$ defines a unique probability measure $\mu_F$ on $(\mathbb{R}, \mathcal{B}(\mathbb{R}))$ satisfying
$$\mu_F((a, b]) = F(b) - F(a).$$
Conversely, every probability measure on $\mathbb{R}$ has a CDF. This is the precise sense in which a one-dimensional law can be represented either as a measure or as a distribution function.

**2.6 Discrete, continuous, and mixed distributions**
If $X$ is discrete with support $\{x_j\}$, its PMF is
$$p_X(x_j) = \mathbb{P}(X = x_j), \quad \sum_j p_X(x_j) = 1.$$
Then
$$F_X(x) = \sum_{x_j \le x} p_X(x_j).$$
If $X$ has a density $f_X$, then
$$\mathbb{P}(X \in A) = \int_A f_X(x) \, dx, \quad f_X(x) \ge 0, \quad \int_{-\infty}^\infty f_X(x) \, dx = 1,$$
and
$$F_X(x) = \int_{-\infty}^x f_X(t) \, dt.$$
Where $F_X$ is differentiable,
$$f_X(x) = F_X'(x).$$

<!-- page 25 -->

Remark 2.8 — Warning: A density is not a probability
For continuous $X$,
$$\mathbb{P}(X = x) = 0$$
for every point $x$, while $f_X(x)$ can exceed one. Probability is obtained by integrating density over a set.

A mixed distribution can have both atoms and a continuous component. The CDF remains the universal object.

Example 2.9 — Constructing a PMF from a normalization condition
Suppose
$$\mathbb{P}(X = x) = c(x + 1), \quad x \in \{0, 1, 2, 3\}.$$
Normalization gives
$$1 = c(1 + 2 + 3 + 4) = 10c,$$
so $c = 1/10$. Hence, for example,
$$\mathbb{P}(X \geq 2) = \frac{3}{10} + \frac{4}{10} = \frac{7}{10}.$$

Example 2.10 — Constructing a density
Suppose
$$f_X(x) = cx^2 \mathbf{1}_{[0,2]}(x).$$
The density must integrate to one:
$$1 = \int_0^2 cx^2 \, \mathrm{d}x = \frac{8c}{3},$$
so $c = 3/8$. The CDF is therefore
$$F_X(x) = \begin{cases} 0, & x < 0, \\ \frac{x^3}{8}, & 0 \leq x \leq 2, \\ 1, & x > 2. \end{cases}$$
Consequently,
$$\mathbb{P}(1 < X \leq 3/2) = F_X(3/2) - F_X(1) = \frac{27}{64} - \frac{1}{8} = \frac{19}{64}.$$

<!-- page 26 -->

2.7 Quantiles and inverse transforms
For $u \in (0, 1)$, define the generalized inverse
$$F^{-1}(u) = \inf\{x : F(x) \geq u\}.$$
If $U \sim \text{Unif}(0, 1)$, then
$$X = F^{-1}(U)$$
has CDF $F$. This is the inverse-transform principle.

Example 2.11 — Median and quantiles
If $X \sim \text{Exp}(\lambda)$, then
$$F_X(x) = 1 - e^{-\lambda x}, \quad x \geq 0.$$
The $u$-quantile solves
$$u = 1 - e^{-\lambda q_u},$$
so
$$q_u = -\frac{1}{\lambda} \log(1 - u).$$
In particular, the median is
$$q_{1/2} = \frac{\log 2}{\lambda},$$
which is below the mean $1/\lambda$ because the exponential distribution is right-skewed.

2.8 Transformations of random variables
There are two basic approaches to transformations.

CDF method. For any function $g$,
$$F_Y(y) = \mathbb{P}(g(X) \leq y).$$
Rewrite the event in terms of $X$, evaluate it using $F_X$, and differentiate if a density is desired. This method works even when $g$ is not one-to-one.

Change-of-variables method. If $g$ is one-to-one and differentiable, use the inverse map and the Jacobian. In one dimension, if $g$ is strictly monotone and $h = g^{-1}$,
$$f_Y(y) = f_X(h(y))|h'(y)|.$$

<!-- page 27 -->

Example 2.12 — Affine transformation
If
$$Y = a + bX, \quad b \neq 0,$$
then
$$\mathbb{E}[Y] = a + b\mathbb{E}[X], \quad \text{Var}(Y) = b^2 \text{Var}(X).$$
If $b > 0$,
$$F_Y(y) = F_X\left(\frac{y - a}{b}\right),$$
while for $b < 0$ the inequality reverses. In particular, if
$$X \sim \mathcal{N}(\mu, \sigma^2),$$
then
$$\frac{X - \mu}{\sigma} \sim \mathcal{N}(0, 1).$$

If $Y = g(X)$, then the law of $Y$ is the pushforward of the law of $X$:
$$\mathcal{L}(Y) = \mathcal{L}(X) \circ g^{-1}.$$
For a strictly increasing differentiable $g$, with inverse $h = g^{-1}$,
$$f_Y(y) = f_X(h(y))|h'(y)|.$$
For a smooth one-to-one map $T : \mathbb{R}^k \to \mathbb{R}^k$,
$$Y = T(X)$$
has density
$$f_Y(y) = f_X(T^{-1}(y)) |\det DT^{-1}(y)|.$$

Example 2.13 — Squaring a symmetric variable
Let $Y = X^2$, where $X$ has a continuous density. For $y > 0$,
$$\mathbb{P}(Y \leq y) = \mathbb{P}(-\sqrt{y} \leq X \leq \sqrt{y}) = F_X(\sqrt{y}) - F_X(-\sqrt{y}).$$
Differentiating gives
$$f_Y(y) = \frac{f_X(\sqrt{y}) + f_X(-\sqrt{y})}{2\sqrt{y}}.$$
The one-dimensional inverse formula must sum over all inverse branches when the transformation is not one-to-one.

<!-- page 28 -->

Example 2.14 — A two-dimensional Jacobian
Suppose
$$U = X + Y, \quad V = Y,$$
with inverse
$$X = U - V, \quad Y = V.$$
Then
$$\left| \det \frac{\partial(x, y)}{\partial(u, v)} \right| = \left| \det \begin{pmatrix} 1 & -1 \\ 0 & 1 \end{pmatrix} \right| = 1.$$
Hence
$$f_{U,V}(u, v) = f_{X,Y}(u - v, v).$$
Marginalizing over $v$ yields the convolution formula for $U = X + Y$.

2.9 Joint, marginal, and conditional distributions
For a random vector $(X, Y)$, the joint CDF is
$$F_{X,Y}(x, y) = \mathbb{P}(X \leq x, Y \leq y).$$
If a joint density exists,
$$f_X(x) = \int f_{X,Y}(x, y) \, \mathrm{d}y, \quad f_Y(y) = \int f_{X,Y}(x, y) \, \mathrm{d}x.$$
The conditional density of $Y$ given $X = x$, when $f_X(x) > 0$, is
$$f_{Y|X}(y | x) = \frac{f_{X,Y}(x, y)}{f_X(x)}.$$

Definition 2.15 — Independence of random variables
Random variables $X$ and $Y$ are independent if
$$\mathbb{P}(X \in A, Y \in B) = \mathbb{P}(X \in A)\mathbb{P}(Y \in B)$$
for all Borel sets $A, B$.

When a joint density exists, independence is equivalent to
$$f_{X,Y}(x, y) = f_X(x)f_Y(y)$$
almost everywhere.

<!-- page 29 -->

Example 2.16 — A discrete joint distribution
Suppose $(X, Y)$ has joint PMF
$$\begin{array}{c|cc} & Y = 0 & Y = 1 \\ \hline X = 0 & 0.20 & 0.10 \\ X = 1 & 0.30 & 0.40 \end{array}$$
The marginal probabilities are obtained by summing rows or columns:
$$\mathbb{P}(X = 1) = 0.30 + 0.40 = 0.70, \quad \mathbb{P}(Y = 1) = 0.10 + 0.40 = 0.50.$$
Hence
$$\mathbb{P}(Y = 1 | X = 1) = \frac{0.40}{0.70} = \frac{4}{7}.$$
Independence fails because
$$\mathbb{P}(X = 1, Y = 1) = 0.40 \neq (0.70)(0.50) = 0.35.$$
This row-sum/column-sum/renormalize procedure is the discrete analogue of integrating a joint density to obtain marginals and dividing by a marginal density to obtain a conditional density.

3 Expectation, Integration, and Moments
Sources. The elementary expectation formulas are standard; the integration layer follows Williams and Klenke. Tonelli, Fubini, monotone convergence, Fatou, dominated convergence, and the $L^p$ inequalities are included because they recur constantly in econometric and macroeconomic arguments.

3.1 Elementary expectation: weighted averages
For a discrete random variable,
$$\mathbb{E}[X] = \sum_{x \in \text{supp}(X)} x\mathbb{P}(X = x),$$
provided the sum is absolutely convergent. For a continuous random variable with density $f_X$,
$$\mathbb{E}[X] = \int_{-\infty}^{\infty} x f_X(x) \, \mathrm{d}x,$$
whenever the integral is well defined.

<!-- page 30 -->

More generally, for a function $g$,
$$\mathbb{E}[g(X)] = \sum_{x} g(x)p_X(x)$$
in the discrete case and
$$\mathbb{E}[g(X)] = \int g(x)f_X(x) \, \mathrm{d}x$$
in the continuous case. One does not need to derive the distribution of $g(X)$ merely to compute its expectation.

Example 3.1 — Expected payoff
A project pays 10 with probability 0.2, pays 3 with probability 0.5, and loses 2 with probability 0.3. If $X$ is the payoff,
$$\mathbb{E}[X] = 10(0.2) + 3(0.5) - 2(0.3) = 2.9.$$
Expected value is a probability-weighted average, not necessarily a feasible realized payoff.

Example 3.2 — Expectation by indicators
Suppose $N$ counts how many of events $A_1, \dots, A_m$ occur. Then
$$N = \sum_{j=1}^m \mathbf{1}_{A_j},$$
so by linearity,
$$\mathbb{E}[N] = \sum_{j=1}^m \mathbb{P}(A_j).$$
No independence assumption is needed. This device is often much easier than deriving the entire distribution of $N$.

The integral formulation below unifies the discrete and continuous formulas and allows expectations to be defined for arbitrary probability laws.

3.2 Expectation as an integral
For a discrete random variable,
$$\mathbb{E}[X] = \sum_{x} x\mathbb{P}(X = x),$$
provided the sum is well-defined. For a continuous random variable with density,
$$\mathbb{E}[X] = \int_{-\infty}^{\infty} x f_X(x) \, \mathrm{d}x.$$

<!-- page 31 -->

These are special cases of integration with respect to a probability measure.

Remark 3.3 — Rigorous layer: Lebesgue construction in three steps
For a nonnegative simple random variable
$$X = \sum_{j=1}^m a_j \mathbf{1}_{A_j}, \quad a_j \geq 0,$$
define
$$\mathbb{E}[X] = \sum_{j=1}^m a_j \mathbb{P}(A_j).$$
For a general nonnegative measurable $X$, choose simple $X_n \uparrow X$ and set
$$\mathbb{E}[X] = \lim_{n \to \infty} \mathbb{E}[X_n].$$
For a signed $X$, write
$$X = X^+ - X^-, \quad X^+ = \max\{X, 0\}, \quad X^- = \max\{-X, 0\},$$
and define $\mathbb{E}[X] = \mathbb{E}[X^+] - \mathbb{E}[X^-]$ whenever at least one side is finite. The random variable is integrable if
$$\mathbb{E}|X| < \infty.$$

3.3 LOTUS
If $g$ is measurable and the expectation exists,
$$\mathbb{E}[g(X)] = \int g(x) \, \mathrm{d}F_X(x).$$
Thus, if $X$ is discrete,
$$\mathbb{E}[g(X)] = \sum_{x} g(x)p_X(x),$$
and if $X$ has density,
$$\mathbb{E}[g(X)] = \int g(x)f_X(x) \, \mathrm{d}x.$$
There is no need to first derive the distribution of $g(X)$.

<!-- page 32 -->

3.4 Linearity and moments
Whenever expectations exist,
$$\mathbb{E}[aX + bY] = a\mathbb{E}[X] + b\mathbb{E}[Y].$$
Independence is not required for linearity.
The $k$-th raw moment is $\mathbb{E}[X^k]$. The variance is
$$\text{Var}(X) = \mathbb{E}[(X - \mathbb{E}X)^2] = \mathbb{E}[X^2] - (\mathbb{E}X)^2.$$
For random variables $X, Y$,
$$\text{Cov}(X, Y) = \mathbb{E}[(X - \mathbb{E}X)(Y - \mathbb{E}Y)] = \mathbb{E}[XY] - \mathbb{E}[X]\mathbb{E}[Y].$$
Then
$$\text{Var}(aX + bY) = a^2 \text{Var}(X) + b^2 \text{Var}(Y) + 2ab \text{Cov}(X, Y).$$
For a vector $X \in \mathbb{R}^k$,
$$\mu = \mathbb{E}[X], \quad \Sigma = \mathbb{E}[(X - \mu)(X - \mu)^\top].$$
For any $a \in \mathbb{R}^k$,
$$\text{Var}(a^\top X) = a^\top \Sigma a \geq 0,$$
so every covariance matrix is positive semidefinite.

3.5 Variance, covariance, correlation, and standardized moments
Variance measures dispersion around the mean:
$$\text{Var}(X) = \mathbb{E}[(X - \mathbb{E}[X])^2].$$
Expanding the square gives the computational identity
$$\text{Var}(X) = \mathbb{E}[X^2] - \mathbb{E}[X]^2.$$
For constants $a, b$,
$$\text{Var}(a + bX) = b^2 \text{Var}(X).$$
For random variables $X, Y$ with finite second moments,
$$\text{Cov}(X, Y) = \mathbb{E}[(X - \mathbb{E}[X])(Y - \mathbb{E}[Y])] = \mathbb{E}[XY] - \mathbb{E}[X]\mathbb{E}[Y].$$
Hence
$$\text{Var}(X + Y) = \text{Var}(X) + \text{Var}(Y) + 2\text{Cov}(X, Y),$$

<!-- page 33 -->

and more generally
$$\text{Var}\left(\sum_{i=1}^n a_i X_i\right) = \sum_{i=1}^n \sum_{j=1}^n a_i a_j \text{Cov}(X_i, X_j).$$
If the variables are independent, all off-diagonal covariance terms vanish.
Correlation normalizes covariance:
$$\text{Corr}(X, Y) = \frac{\text{Cov}(X, Y)}{\sqrt{\text{Var}(X) \text{Var}(Y)}} \in [-1, 1]$$
when both variances are positive. Independence implies zero covariance when second moments exist, but zero covariance does not generally imply independence.
The $k$-th raw moment is
$$\mathbb{E}[X^k],$$
while the $k$-th central moment is
$$\mathbb{E}[(X - \mathbb{E}[X])^k].$$
Skewness and kurtosis are standardized third and fourth central moments. They are useful summaries of shape but do not, in general, determine a distribution.

Example 3.4 — Variance of a Bernoulli variable
If $X \sim \text{Bern}(p)$, then $X^2 = X$, so
$$\mathbb{E}[X^2] = p.$$
Therefore
$$\text{Var}(X) = p - p^2 = p(1 - p).$$
If $S_n = \sum_{i=1}^n X_i$ for independent Bernoulli variables, then
$$\mathbb{E}[S_n] = np, \quad \text{Var}(S_n) = np(1 - p),$$
which gives the mean and variance of the binomial distribution without summing its PMF directly.

3.6 Convergence theorems for expectations
The main difficulty in probability is often not computing an expectation, but justifying an interchange of limit and expectation:
$$\lim_n \mathbb{E}[X_n] \stackrel{?}{=} \mathbb{E}[\lim_n X_n].$$
The following three theorems organize when this is legitimate.

<!-- page 34 -->

Theorem 3.5 — Monotone Convergence Theorem
If
$$0 \leq X_1 \leq X_2 \leq \dots, \quad X_n \to X \quad a.s.,$$
then
$$\mathbb{E}[X_n] \uparrow \mathbb{E}[X].$$

Theorem 3.6 — Fatou’s lemma
If $X_n \geq 0$, then
$$\mathbb{E}\left[ \liminf_{n \to \infty} X_n \right] \leq \liminf_{n \to \infty} \mathbb{E}[X_n].$$

Theorem 3.7 — Dominated Convergence Theorem
Suppose
$$X_n \to X \quad a.s.$$
and there exists an integrable $Y$ such that
$$|X_n| \leq Y \quad a.s. \quad \forall n.$$
Then $X$ is integrable and
$$\mathbb{E}|X_n - X| \to 0, \quad \mathbb{E}[X_n] \to \mathbb{E}[X].$$

Remark 3.8 — Why DCT matters
Differentiating an expected payoff, passing a parameter limit through an expectation, and proving continuity of a value function under uncertainty all reduce to variants of dominated convergence. The domination assumption is the probabilistic version of controlling tails uniformly.

<!-- page 35 -->

3.7 Inequalities
Proposition 3.9 — Markov’s inequality
If $X \geq 0$ and $a > 0$, then
$$\mathbb{P}(X \geq a) \leq \frac{\mathbb{E}[X]}{a}.$$

Proof
Since
$$X \geq a\mathbf{1}_{\{X \geq a\}},$$
taking expectations gives
$$\mathbb{E}[X] \geq a\mathbb{P}(X \geq a).$$

Applying Markov to $(X - \mathbb{E}X)^2$ gives Chebyshev:
$$\mathbb{P}(|X - \mathbb{E}X| \geq \varepsilon) \leq \frac{\text{Var}(X)}{\varepsilon^2}.$$
For convex $\phi$, Jensen’s inequality states
$$\phi(\mathbb{E}[X]) \leq \mathbb{E}[\phi(X)].$$
For concave $u$,
$$u(\mathbb{E}X) \geq \mathbb{E}[u(X)].$$
Cauchy–Schwarz gives
$$|\mathbb{E}[XY]| \leq \sqrt{\mathbb{E}[X^2]\mathbb{E}[Y^2]}.$$
Consequently,
$$|\text{Cov}(X, Y)| \leq \sqrt{\text{Var}(X) \text{Var}(Y)},$$
so $|\text{Corr}(X, Y)| \leq 1$.

3.8 $L^p$ spaces and Hölder inequalities
For $1 \leq p < \infty$, define
$$L^p = \{X : \mathbb{E}|X|^p < \infty\}, \quad \|X\|_p = (\mathbb{E}|X|^p)^{1/p}.$$
For $p = 2$, the inner product
$$\langle X, Y \rangle = \mathbb{E}[XY]$$
turns $L^2$ into a Hilbert space after identifying random variables that are equal almost surely.

<!-- page 36 -->

If $p, q > 1$ satisfy
$$\frac{1}{p} + \frac{1}{q} = 1,$$
Hölder’s inequality states
$$\mathbb{E}|XY| \leq \|X\|_p \|Y\|_q.$$
Cauchy–Schwarz is the case $p = q = 2$.
Minkowski’s inequality gives
$$\|X + Y\|_p \leq \|X\|_p + \|Y\|_p.$$
These inequalities are the functional-analytic foundation behind moment bounds used throughout asymptotic theory.

3.9 Tail-integral formulas
If $X \geq 0$, then
$$X = \int_0^\infty \mathbf{1}_{\{X > t\}} \, \mathrm{d}t.$$
Tonelli therefore yields
$$\mathbb{E}[X] = \int_0^\infty \mathbb{P}(X > t) \, \mathrm{d}t.$$
More generally, for $p > 0$,
$$\mathbb{E}[X^p] = p \int_0^\infty t^{p-1} \mathbb{P}(X > t) \, \mathrm{d}t.$$
These identities connect moment conditions directly to tail decay.

3.10 Tonelli and Fubini
If $g(x, y) \geq 0$, Tonelli’s theorem permits iterated integration without a prior integrability check:
$$\iint g(x, y) \, \mathrm{d}\mu(x) \, \mathrm{d}\nu(y) = \iint g(x, y) \, \mathrm{d}\nu(y) \, \mathrm{d}\mu(x).$$
If $\iint |g| < \infty$, Fubini’s theorem gives the same conclusion for signed $g$.
For independent $X, Y$ and integrable products,
$$\mathbb{E}[g(X)h(Y)] = \mathbb{E}[g(X)]\mathbb{E}[h(Y)].$$
In particular,
$$X \perp Y \implies \text{Cov}(X, Y) = 0,$$
provided second moments exist. The converse is false in general.

<!-- page 37 -->

# 4 Conditional Expectation and Information

**Sources.** Williams gives the cleanest concise development of conditional expectation as a random variable measurable with respect to an information set. Klenke supplies the measure-theoretic existence theory; Hansen provides the econometric interpretation through prediction, projection, and conditional moments.

## 4.1 Elementary conditional expectation

If $X$ is discrete,
$$\mathbb{E}[Y \mid X = x] = \sum_{y} y \mathbb{P}(Y = y \mid X = x).$$
If $(X, Y)$ has a joint density,
$$\mathbb{E}[Y \mid X = x] = \int y f_{Y|X}(y \mid x) \, \mathrm{d}y.$$
In both cases, the conditional mean is a function of $x$. Evaluating it at the random variable $X$ gives another random variable:
$$m(X) = \mathbb{E}[Y \mid X].$$

## 4.2 Conditioning on a sigma-algebra

A sigma-algebra $\mathcal{G} \subseteq \mathcal{F}$ represents information. A random variable $Z$ is $\mathcal{G}$-measurable when its value can be determined from that information.

> **Definition 4.1 — Conditional expectation**
>
> Let $Y$ be integrable and let $\mathcal{G} \subseteq \mathcal{F}$ be a sub-sigma-algebra. A random variable $Z$ is a version of $\mathbb{E}[Y \mid \mathcal{G}]$ if
> 1. $Z$ is $\mathcal{G}$-measurable;
> 2. for every $G \in \mathcal{G}$,
> $$\int_G Z \, \mathrm{d}\mathbb{P} = \int_G Y \, \mathrm{d}\mathbb{P}.$$

The first condition says the conditional expectation uses only the available information. The second says it preserves averages on every event that can be distinguished using that information.

> **Remark 4.2 — Rigorous layer: Existence and uniqueness**
>
> If $Y \in L^1$, then $\mathbb{E}[Y \mid \mathcal{G}]$ exists and is unique almost surely. Existence is an application of the

<!-- page 38 -->

Radon–Nikodym theorem to the signed measure
$$\nu(G) = \int_G Y \, \mathrm{d}\mathbb{P}, \quad G \in \mathcal{G}.$$
For math camp, the Radon–Nikodym theorem itself can be stated rather than proved. The important point is that conditional expectation is not merely notation based on a conditional density; it exists far more generally.

When $\mathcal{G} = \sigma(X)$, Doob–Dynkin implies that
$$\mathbb{E}[Y \mid \sigma(X)] = m(X)$$
for some measurable function $m$. This is the rigorous content of $\mathbb{E}[Y \mid X]$.

> **Example 4.3 — Conditioning on a finite partition**
>
> Suppose $\mathcal{G}$ is generated by a finite partition $A_1, \dots, A_m$, with $\mathbb{P}(A_j) > 0$. Then
> $$\mathbb{E}[Y \mid \mathcal{G}] = \sum_{j=1}^m \mathbb{E}[Y \mid A_j] \mathbf{1}_{A_j}.$$
> The conditional expectation is constant on each information cell. This is the simplest concrete model of "conditioning on information."

## 4.3 Core properties

Whenever the expressions are integrable:
$$\mathbb{E}[aX + bY \mid \mathcal{G}] = a\mathbb{E}[X \mid \mathcal{G}] + b\mathbb{E}[Y \mid \mathcal{G}],$$
$$X \leq Y \Rightarrow \mathbb{E}[X \mid \mathcal{G}] \leq \mathbb{E}[Y \mid \mathcal{G}],$$
$$X \text{ is } \mathcal{G}\text{-measurable} \Rightarrow \mathbb{E}[X \mid \mathcal{G}] = X,$$
$$Z \text{ is } \mathcal{G}\text{-measurable} \Rightarrow \mathbb{E}[ZX \mid \mathcal{G}] = Z\mathbb{E}[X \mid \mathcal{G}],$$
$$\mathbb{E}[\mathbb{E}[X \mid \mathcal{G}]] = \mathbb{E}[X].$$
If $\mathcal{H} \subseteq \mathcal{G} \subseteq \mathcal{F}$, then the tower property gives
$$\mathbb{E}[\mathbb{E}[X \mid \mathcal{G}] \mid \mathcal{H}] = \mathbb{E}[X \mid \mathcal{H}].$$
In the familiar notation,
$$\mathbb{E}[\mathbb{E}[Y \mid X, Z] \mid X] = \mathbb{E}[Y \mid X].$$

<!-- page 39 -->

If $X$ is independent of $\mathcal{G}$, then
$$\mathbb{E}[X \mid \mathcal{G}] = \mathbb{E}[X] \quad a.s.$$

## 4.4 Conditional expectation as an $L^2$ projection

Suppose $Y \in L^2$. Consider the closed subspace
$$L^2(\mathcal{G}) = \{Z \in L^2 : Z \text{ is } \mathcal{G}\text{-measurable}\}.$$
Then
$$\mathbb{E}[Y \mid \mathcal{G}]$$
is the orthogonal projection of $Y$ onto $L^2(\mathcal{G})$.
In particular,
$$\mathbb{E}[(Y - \mathbb{E}[Y \mid \mathcal{G}])Z] = 0 \quad \forall Z \in L^2(\mathcal{G}).$$
Therefore
$$\mathbb{E}[Y \mid \mathcal{G}] \in \arg \min_{Z \in L^2(\mathcal{G})} \mathbb{E}[(Y - Z)^2].$$

> **Example 4.4 — Conditional mean and regression error**
>
> Let
> $$m(X) = \mathbb{E}[Y \mid X], \quad u = Y - m(X).$$
> Then
> $$\mathbb{E}[u \mid X] = 0.$$
> Hence for every square-integrable function $h(X)$,
> $$\mathbb{E}[uh(X)] = 0.$$
> This is much stronger than $\mathbb{E}[uX] = 0$: the conditional-mean residual is orthogonal to every square-integrable transformation of the conditioning variables.

## 4.5 Best prediction and Gaussian conditioning

The projection result says that among all measurable predictors based on $X$, the conditional mean
$$m(X) = \mathbb{E}[Y \mid X]$$
minimizes mean squared prediction error:
$$\mathbb{E}[(Y - m(X))^2] \leq \mathbb{E}[(Y - g(X))^2]$$

<!-- page 40 -->

for every square-integrable $g(X)$.
For jointly Gaussian variables,
$$\begin{pmatrix} Y \\ X \end{pmatrix} \sim \mathcal{N} \left( \begin{pmatrix} \mu_Y \\ \mu_X \end{pmatrix}, \begin{pmatrix} \Sigma_{YY} & \Sigma_{YX} \\ \Sigma_{XY} & \Sigma_{XX} \end{pmatrix} \right),$$
the conditional distribution is again Gaussian:
$$Y \mid X = x \sim \mathcal{N} (\mu_Y + \Sigma_{YX}\Sigma_{XX}^{-1}(x - \mu_X), \Sigma_{YY} - \Sigma_{YX}\Sigma_{XX}^{-1}\Sigma_{XY}).$$
Thus the conditional expectation is linear in $x$ for jointly Gaussian vectors.

## 4.6 Conditional distributions as random probability measures

For discrete variables, conditioning on $X = x$ is straightforward. In continuous models, the event $\{X = x\}$ usually has probability zero, so the ratio definition of conditional probability cannot be used literally. A conditional density
$$f_{Y|X}(y \mid x)$$
should instead be understood as a version of a *regular conditional distribution*: for each $x$, it is a probability law in $y$, while for each measurable set $A$, the map
$$x \mapsto \mathbb{P}(Y \in A \mid X = x)$$
is measurable and satisfies the appropriate averaging identity.

> **Remark 4.5 — Rigorous layer: Existence caveat**
>
> Regular conditional distributions exist on the standard Borel spaces used in essentially all conventional economic applications, including Euclidean spaces and countable state spaces. They need not exist on completely arbitrary measurable spaces. This is one reason probability theory often works on well-behaved state spaces rather than maximal generality.

## 4.7 A change-of-measure viewpoint

If $Q$ is another probability measure satisfying $Q \ll P$, the Radon–Nikodym theorem gives a nonnegative random variable
$$L = \frac{\mathrm{dQ}}{\mathrm{dP}}$$
such that
$$Q(A) = \mathbb{E}_P[L\mathbf{1}_A].$$
Therefore, for integrable $X$,
$$\mathbb{E}_Q[X] = \mathbb{E}_P[LX].$$

<!-- page 41 -->

Likelihood ratios, importance sampling, Bayesian updating, and asset-pricing changes of measure all use this same mathematical device.

## 4.8 Conditional variance and variance decomposition

Define
$$\text{Var}(Y \mid \mathcal{G}) = \mathbb{E}[(Y - \mathbb{E}[Y \mid \mathcal{G}])^2 \mid \mathcal{G}].$$
Then
$$\text{Var}(Y) = \mathbb{E}[\text{Var}(Y \mid \mathcal{G})] + \text{Var}(\mathbb{E}[Y \mid \mathcal{G}]).$$
The first term is average residual uncertainty; the second is variation in predictable conditional means.
A related law of total covariance is
$$\text{Cov}(Y, Z) = \mathbb{E}[\text{Cov}(Y, Z \mid \mathcal{G})] + \text{Cov}(\mathbb{E}[Y \mid \mathcal{G}], \mathbb{E}[Z \mid \mathcal{G}]).$$

# 5 Common Distributions, Transformations, and Transforms

**Sources.** The distributional calculations draw on Blitzstein–Hwang and Bertsekas–Tsitsiklis, while Hansen is used to emphasize the families and transforms most useful in econometrics.

## 5.1 Discrete families

**Bernoulli.** If $X \sim \text{Bern}(p)$, then
$$\mathbb{P}(X = 1) = p, \quad \mathbb{P}(X = 0) = 1 - p,$$
$$\mathbb{E}[X] = p, \quad \text{Var}(X) = p(1 - p).$$
**Binomial.** If $X = \sum_{i=1}^n B_i$ with $B_i \overset{\text{iid}}{\sim} \text{Bern}(p)$, then
$$X \sim \text{Bin}(n, p), \quad \mathbb{P}(X = k) = \binom{n}{k} p^k (1 - p)^{n-k}.$$
Moreover,
$$\mathbb{E}[X] = np, \quad \text{Var}(X) = np(1 - p).$$
**Geometric.** If $X$ counts trials until the first success,
$$\mathbb{P}(X = k) = (1 - p)^{k-1}p, \quad k = 1, 2, \dots$$

<!-- page 42 -->

with
$$\mathbb{E}[X] = \frac{1}{p}.$$
It is memoryless:
$$\mathbb{P}(X > m + n \mid X > m) = \mathbb{P}(X > n).$$
**Poisson.** If $X \sim \text{Pois}(\lambda)$,
$$\mathbb{P}(X = k) = e^{-\lambda} \frac{\lambda^k}{k!}, \quad \mathbb{E}[X] = \text{Var}(X) = \lambda.$$
Independent Poisson variables add:
$$X \sim \text{Pois}(\lambda), \quad Y \sim \text{Pois}(\mu), \quad X \perp Y \Rightarrow X + Y \sim \text{Pois}(\lambda + \mu).$$
**Negative binomial.** Let $X$ count the number of trials needed to obtain the $r$-th success, with success probability $p$. Then
$$\mathbb{P}(X = k) = \binom{k-1}{r-1} p^r (1 - p)^{k-r}, \quad k = r, r+1, \dots$$
and
$$\mathbb{E}[X] = \frac{r}{p}, \quad \text{Var}(X) = \frac{r(1 - p)}{p^2}.$$
It is the sum of $r$ independent geometric waiting times.
**Multinomial.** If $(N_1, \dots, N_k) \sim \text{Multinomial}(n; p_1, \dots, p_k)$, then
$$\mathbb{P}(N_1 = n_1, \dots, N_k = n_k) = \frac{n!}{n_1! \dots n_k!} \prod_{j=1}^k p_j^{n_j},$$
for nonnegative counts summing to $n$.

## 5.2 Continuous families

**Uniform.** If $X \sim \text{Unif}(a, b)$,
$$f_X(x) = \frac{1}{b - a} \mathbf{1}_{[a, b]}(x), \quad \mathbb{E}[X] = \frac{a + b}{2}.$$
**Exponential.** If $X \sim \text{Exp}(\lambda)$,
$$f_X(x) = \lambda e^{-\lambda x} \mathbf{1}_{\{x \geq 0\}}, \quad \mathbb{E}[X] = \frac{1}{\lambda}.$$

<!-- page 43 -->

It is the continuous memoryless distribution:
$$\mathbb{P}(X > s + t \mid X > s) = \mathbb{P}(X > t).$$
**Gamma.** For shape $\alpha > 0$ and rate $\lambda > 0$,
$$f_X(x) = \frac{\lambda^\alpha}{\Gamma(\alpha)} x^{\alpha-1} e^{-\lambda x} \mathbf{1}_{\{x > 0\}}.$$
Then
$$\mathbb{E}[X] = \frac{\alpha}{\lambda}, \quad \text{Var}(X) = \frac{\alpha}{\lambda^2}.$$
**Beta.** For $\alpha, \beta > 0$,
$$f_X(x) = \frac{x^{\alpha-1}(1 - x)^{\beta-1}}{B(\alpha, \beta)} \mathbf{1}_{(0, 1)}(x).$$
Then
$$\mathbb{E}[X] = \frac{\alpha}{\alpha + \beta}.$$

## 5.3 Normal and multivariate normal distributions

If $X \sim \mathcal{N}(\mu, \sigma^2)$,
$$f_X(x) = \frac{1}{\sqrt{2\pi\sigma^2}} \exp \left( -\frac{(x - \mu)^2}{2\sigma^2} \right).$$
Standardization gives
$$Z = \frac{X - \mu}{\sigma} \sim \mathcal{N}(0, 1).$$
A random vector $X \in \mathbb{R}^k$ is multivariate normal with mean $\mu$ and covariance $\Sigma$, written
$$X \sim \mathcal{N}_k(\mu, \Sigma),$$
if every linear combination $a^\top X$ is univariate normal. Then
$$a^\top X \sim \mathcal{N}(a^\top \mu, a^\top \Sigma a).$$
If $A$ and $b$ are deterministic,
$$AX + b \sim \mathcal{N}(A\mu + b, A\Sigma A^\top).$$

> **Proposition 5.1 — Zero covariance implies independence for jointly Gaussian variables**
>
> If $(X, Y)$ is jointly Gaussian and
> $$\text{Cov}(X, Y) = 0,$$

<!-- page 44 -->

then $X$ and $Y$ are independent.

This implication is special to the Gaussian family.

**Chi-square.** If $Z_1, \dots, Z_\nu \overset{\text{iid}}{\sim} \mathcal{N}(0, 1)$, then
$$Q = \sum_{j=1}^\nu Z_j^2 \sim \chi^2_\nu.$$
This is a gamma distribution with shape $\nu/2$ and rate $1/2$:
$$\mathbb{E}[Q] = \nu, \quad \text{Var}(Q) = 2\nu.$$
**Student's $t$.** If $Z \sim \mathcal{N}(0, 1)$, $Q \sim \chi^2_\nu$, and $Z \perp Q$, then
$$T = \frac{Z}{\sqrt{Q/\nu}} \sim t_\nu.$$
The $t$ distribution has heavier tails than a standard normal and converges to $\mathcal{N}(0, 1)$ as $\nu \to \infty$.

## 5.4 Relations among the basic families

The named distributions are easier to remember when organized by the experiments that generate them.
* **Bernoulli:** one success/failure trial.
* **Binomial:** number of successes in a fixed number of independent Bernoulli trials.
* **Geometric:** waiting time until the first Bernoulli success.
* **Negative binomial:** waiting time until the $r$-th Bernoulli success.
* **Poisson:** count of arrivals in a fixed interval under a constant-rate arrival model.
* **Exponential:** waiting time to the first Poisson arrival.
* **Gamma:** waiting time to the $r$-th Poisson arrival when the shape is an integer.

For small success probabilities, the binomial has the Poisson approximation
$$X_n \sim \text{Bin}(n, p_n), \quad np_n \to \lambda,$$
under which
$$\mathbb{P}(X_n = k) \to e^{-\lambda} \frac{\lambda^k}{k!} \quad (k = 0, 1, \dots).$$
Thus Poisson counts arise naturally as a rare-event limit.

<!-- page 45 -->

If $X \sim \text{Exp}(\lambda)$, its survival function is
$$\mathbb{P}(X > x) = e^{-\lambda x}.$$
The memoryless property follows immediately:
$$\mathbb{P}(X > s + t \mid X > s) = \frac{e^{-\lambda(s+t)}}{e^{-\lambda s}} = e^{-\lambda t}.$$
The geometric distribution is the discrete analogue.

## 5.5 A compact distribution table

| Distribution | Support | Mean | Variance |
| :--- | :--- | :--- | :--- |
| $\text{Bern}(p)$ | $\{0, 1\}$ | $p$ | $p(1 - p)$ |
| $\text{Bin}(n, p)$ | $0, \dots, n$ | $np$ | $np(1 - p)$ |
| $\text{Pois}(\lambda)$ | $\mathbb{N}_0$ | $\lambda$ | $\lambda$ |
| $\text{Unif}(a, b)$ | $[a, b]$ | $(a + b)/2$ | $(b - a)^2/12$ |
| $\text{Exp}(\lambda)$ | $[0, \infty)$ | $1/\lambda$ | $1/\lambda^2$ |
| $\text{Gamma}(\alpha, \lambda)$ | $(0, \infty)$ | $\alpha/\lambda$ | $\alpha/\lambda^2$ |
| $\text{Beta}(\alpha, \beta)$ | $(0, 1)$ | $\alpha/(\alpha + \beta)$ | $\alpha\beta/[(\alpha + \beta)^2(\alpha + \beta + 1)]$ |
| $\mathcal{N}(\mu, \sigma^2)$ | $\mathbb{R}$ | $\mu$ | $\sigma^2$ |

## 5.6 Convolution

If $X, Y$ are independent with densities, then $S = X + Y$ has density
$$f_S(s) = \int_{-\infty}^\infty f_X(x) f_Y(s - x) \, \mathrm{d}x = (f_X * f_Y)(s).$$
Convolution is the distributional counterpart of adding independent random variables.

> **Example 5.2 — Sum of independent exponentials**
>
> Let $X, Y \overset{\text{iid}}{\sim} \text{Exp}(\lambda)$. Then for $s > 0$,
> $$f_{X+Y}(s) = \int_0^s \lambda e^{-\lambda x} \lambda e^{-\lambda(s-x)} \, \mathrm{d}x = \lambda^2 s e^{-\lambda s}.$$
> Thus
> $$X + Y \sim \text{Gamma}(2, \lambda).$$
> Repeated convolution gives the gamma distribution as the waiting time for multiple Poisson arrivals.

<!-- page 46 -->

## 5.7 Moment-generating and characteristic functions

For a nonnegative integer-valued random variable, the *probability generating function* is
$$G_X(s) = \mathbb{E}[s^X] = \sum_{k=0}^\infty s^k \mathbb{P}(X = k),$$
for values of $s$ where the series converges. It packages the entire PMF and is especially convenient for sums and branching/counting models. For independent nonnegative integer-valued $X, Y$,
$$G_{X+Y}(s) = G_X(s)G_Y(s).$$
For example,
$$G_{\text{Bin}(n, p)}(s) = (1 - p + ps)^n, \quad G_{\text{Pois}(\lambda)}(s) = \exp\{\lambda(s - 1)\}.$$
The moment-generating function is
$$M_X(t) = \mathbb{E}[e^{tX}],$$
where finite. If it exists on an open interval around zero, it determines the distribution and
$$M_X^{(k)}(0) = \mathbb{E}[X^k].$$
For independent $X, Y$,
$$M_{X+Y}(t) = M_X(t)M_Y(t).$$
The characteristic function is
$$\varphi_X(t) = \mathbb{E}[e^{itX}].$$
Unlike an MGF, it always exists because $|e^{itX}| = 1$. It uniquely determines the law. For independent sums,
$$\varphi_{X+Y}(t) = \varphi_X(t)\varphi_Y(t).$$
Characteristic functions will be our main transform for the central limit theorem.
Useful transforms include
$$M_{\text{Bern}(p)}(t) = 1 - p + pe^t,$$
$$M_{\text{Pois}(\lambda)}(t) = \exp\{\lambda(e^t - 1)\},$$
$$M_{\mathcal{N}(\mu, \sigma^2)}(t) = \exp \left( \mu t + \frac{\sigma^2 t^2}{2} \right),$$
and
$$\varphi_{\mathcal{N}(\mu, \sigma^2)}(t) = \exp \left( i\mu t - \frac{\sigma^2 t^2}{2} \right).$$

<!-- page 47 -->

# 6 Random Vectors, Sampling, and Order Statistics

**Sources.** Hansen is the main economics-facing reference for random vectors, sampling, sample moments, and exact Gaussian sampling theory. Blitzstein–Hwang is especially useful for transformations and order statistics.
The preceding chapters introduced joint distributions and multivariate normality. For econometrics, it is useful to collect the main multivariate and sampling facts in one place.

## 6.1 Joint PMFs and PDFs: the computational layer

For discrete $(X, Y)$, the joint PMF is
$$p_{X,Y}(x, y) = \mathbb{P}(X = x, Y = y).$$
Marginal PMFs are obtained by summing out the other variable:
$$p_X(x) = \sum_y p_{X,Y}(x, y), \quad p_Y(y) = \sum_x p_{X,Y}(x, y).$$
When $p_X(x) > 0$,
$$p_{Y|X}(y \mid x) = \frac{p_{X,Y}(x, y)}{p_X(x)}.$$
For continuous $(X, Y)$ with joint density $f_{X,Y}$,
$$f_X(x) = \int_{-\infty}^\infty f_{X,Y}(x, y) \, \mathrm{d}y, \quad f_Y(y) = \int_{-\infty}^\infty f_{X,Y}(x, y) \, \mathrm{d}x,$$
and
$$f_{Y|X}(y \mid x) = \frac{f_{X,Y}(x, y)}{f_X(x)}.$$
The integration limits must respect the support of the joint density; they need not be $(-\infty, \infty)$ after the support restrictions are imposed.

> **Example 6.1 — A triangular joint density**
>
> Suppose
> $$f_{X,Y}(x, y) = 2, \quad 0 < y < x < 1,$$
> and zero otherwise. The density integrates to one because
> $$\int_0^1 \int_0^x 2 \, \mathrm{d}y \, \mathrm{d}x = \int_0^1 2x \, \mathrm{d}x = 1.$$

<!-- page 48 -->

The marginal density of $X$ is
$$f_X(x) = \int_0^x 2 \, \mathrm{d}y = 2x, \quad 0 < x < 1,$$
while the marginal density of $Y$ is
$$f_Y(y) = \int_y^1 2 \, \mathrm{d}x = 2(1 - y), \quad 0 < y < 1.$$
The conditional density of $Y$ given $X = x$ is
$$f_{Y|X}(y \mid x) = \frac{2}{2x} = \frac{1}{x}, \quad 0 < y < x.$$
Thus
$$Y \mid X = x \sim \text{Unif}(0, x).$$
The geometry of the support is as important as the algebra.

## 6.2 Random vectors and covariance matrices

For a random vector $X = (X_1, \dots, X_k)^\top$, define
$$\mu = \mathbb{E}[X], \quad \Sigma = \text{Var}(X) = \mathbb{E}[(X - \mu)(X - \mu)^\top].$$
The $(i, j)$-entry is $\text{Cov}(X_i, X_j)$. For any deterministic matrix $A$ and vector $b$,
$$\mathbb{E}[AX + b] = A\mu + b, \quad \text{Var}(AX + b) = A\Sigma A^\top.$$
Because
$$a^\top \Sigma a = \text{Var}(a^\top X) \geq 0,$$
every covariance matrix is positive semidefinite.

> **Remark 6.2 — Correlation is not a substitute for dependence**
>
> Zero covariance means only linear uncorrelatedness. It does not generally imply independence. Joint Gaussianity is the important exception: for a jointly Gaussian vector, zero cross-covariance between subvectors is equivalent to independence.

<!-- page 49 -->

6.3 Multivariate changes of variables

Let $X \in \mathbb{R}^k$ have density $f_X$, and let $Y = T(X)$, where $T$ is one-to-one and continuously differentiable with inverse $x = T^{-1}(y)$. Then

$$f_Y(y) = f_X(T^{-1}(y)) \left| \det DT^{-1}(y) \right|.$$

The determinant measures local volume distortion.

::: {.example}
**Example 6.3 — Sum and share transformation**

Let $X, Y > 0$, and define
$$S = X + Y, \quad U = \frac{X}{X + Y}.$$
The inverse transformation is
$$X = US, \quad Y = (1 - U)S,$$
with $s > 0, 0 < u < 1$. The Jacobian is
$$\left| \det \frac{\partial(x, y)}{\partial(s, u)} \right| = s.$$
Hence
$$f_{S,U}(s, u) = f_{X,Y}(us, (1 - u)s)s.$$
This transformation is central in beta–gamma calculations and is a useful template for deriving distributions of totals and shares.
:::

6.4 Random samples and statistics

A random sample of size $n$ from a law $F$ is a collection
$$X_1, \dots, X_n \stackrel{\text{iid}}{\sim} F.$$
A statistic is any measurable function of the sample,
$$T_n = T(X_1, \dots, X_n),$$
that does not depend on unknown parameters except through the data-generating law.
The sample mean and sample variance are
$$\bar{X}_n = \frac{1}{n} \sum_{i=1}^n X_i, \quad S_n^2 = \frac{1}{n - 1} \sum_{i=1}^n (X_i - \bar{X}_n)^2.$$

<!-- page 50 -->

If $\mathbb{E}[X_i] = \mu$ and $\text{Var}(X_i) = \sigma^2 < \infty$, then
$$\mathbb{E}[\bar{X}_n] = \mu, \quad \text{Var}(\bar{X}_n) = \frac{\sigma^2}{n},$$
and
$$\mathbb{E}[S_n^2] = \sigma^2.$$
The divisor $n - 1$ rather than $n$ corrects the finite-sample downward bias created by estimating the mean.

::: {.proposition}
**Proposition 6.4 — Variance decomposition for a sample**

For any numbers $x_1, \dots, x_n$ and any $a \in \mathbb{R}$,
$$\sum_{i=1}^n (x_i - a)^2 = \sum_{i=1}^n (x_i - \bar{x})^2 + n(\bar{x} - a)^2.$$
Setting $a = \mu$ and taking expectations gives $\mathbb{E}[S_n^2] = \sigma^2$ under iid sampling with finite second moments.
:::

6.5 Order statistics

Write the ordered sample as
$$X_{(1)} \leq X_{(2)} \leq \dots \leq X_{(n)}.$$
If the common distribution is continuous with CDF $F$ and density $f$, then the density of the $k$-th order statistic is
$$f_{X_{(k)}}(x) = \frac{n!}{(k - 1)!(n - k)!} F(x)^{k-1} [1 - F(x)]^{n-k} f(x).$$
The logic is combinatorial: one observation lies near $x$, exactly $k - 1$ lie below it, and $n - k$ lie above it.
For the minimum and maximum,
$$\mathbb{P}(X_{(1)} > x) = [1 - F(x)]^n,$$
so
$$F_{X_{(1)}}(x) = 1 - [1 - F(x)]^n,$$
and
$$F_{X_{(n)}}(x) = F(x)^n.$$

<!-- page 51 -->

::: {.example}
**Example 6.5 — Uniform order statistics**

If $U_1, \dots, U_n \stackrel{\text{iid}}{\sim} \text{Unif}(0, 1)$, then
$$U_{(k)} \sim \text{Beta}(k, n + 1 - k).$$
Consequently,
$$\mathbb{E}[U_{(k)}] = \frac{k}{n + 1}.$$
This explains why empirical quantiles are naturally associated with order statistics.
:::

6.6 Sample mean and sample variance

If $X_1, \dots, X_n$ are iid with
$$\mathbb{E}[X_i] = \mu, \quad \text{Var}(X_i) = \sigma^2 < \infty,$$
the sample mean is
$$\bar{X}_n = \frac{1}{n} \sum_{i=1}^n X_i.$$
By linearity and independence,
$$\mathbb{E}[\bar{X}_n] = \mu, \quad \text{Var}(\bar{X}_n) = \frac{\sigma^2}{n}.$$
This $1/n$ variance reduction is the elementary calculation behind the $\sqrt{n}$ scaling of statistical asymptotics.
The sample variance is
$$S_n^2 = \frac{1}{n - 1} \sum_{i=1}^n (X_i - \bar{X}_n)^2.$$
The denominator $n - 1$ makes the estimator unbiased:
$$\mathbb{E}[S_n^2] = \sigma^2.$$
A useful identity is
$$\sum_{i=1}^n (X_i - \bar{X}_n)^2 = \sum_{i=1}^n (X_i - \mu)^2 - n(\bar{X}_n - \mu)^2.$$
Taking expectations gives
$$\mathbb{E} \left[ \sum_{i=1}^n (X_i - \bar{X}_n)^2 \right] = (n - 1)\sigma^2.$$

<!-- page 52 -->

6.7 Normal samples, chi-square, and Student's $t$

Suppose
$$X_1, \dots, X_n \stackrel{\text{iid}}{\sim} N(\mu, \sigma^2).$$
Then
$$\bar{X}_n \sim N\left(\mu, \frac{\sigma^2}{n}\right).$$
Moreover,
$$\frac{(n - 1)S_n^2}{\sigma^2} \sim \chi^2_{n-1},$$
and $\bar{X}_n$ is independent of $S_n^2$. Hence
$$T = \frac{\sqrt{n}(\bar{X}_n - \mu)}{S_n} \sim t_{n-1}.$$
These are exact finite-sample results, unlike the asymptotic normal approximation supplied by the CLT.

::: {.remark}
**Remark 6.6 — Rigorous layer: Why normal sampling is exceptional**

For a generic population, $\bar{X}_n$ and $S_n^2$ need not be independent, and the studentized mean does not have an exact Student $t$ distribution. Normality turns an orthogonal decomposition of the sample vector into independence because orthogonal Gaussian components are independent.
:::

6.8 Empirical measures

The empirical measure is
$$\mathbb{P}_n = \frac{1}{n} \sum_{i=1}^n \delta_{X_i}.$$
For a measurable function $g$,
$$\mathbb{P}_n g := \int g \, d\mathbb{P}_n = \frac{1}{n} \sum_{i=1}^n g(X_i).$$
The population counterpart is
$$Pg := \mathbb{E}[g(X)].$$
This notation makes the LLN and empirical-process viewpoint especially compact:
$$\mathbb{P}_n g \to Pg, \quad \sqrt{n}(\mathbb{P}_n - P)g$$
is the centered empirical fluctuation. It is the natural language behind modern asymptotic econometrics.

<!-- page 53 -->

7 Modes of Stochastic Convergence

**Sources.** The rigorous hierarchy of almost-sure, probability, $L^p$, and distributional convergence follows Klenke, Durrett, and Billingsley. Hansen and van der Vaart motivate the stochastic-order notation and asymptotic manipulations used later.

7.1 Four notions of convergence

Let $X_n, X$ be random variables.

::: {.definition}
**Definition 7.1 — Almost-sure convergence**

We write
$$X_n \xrightarrow{a.s.} X$$
if
$$\mathbb{P}\{\omega : X_n(\omega) \to X(\omega)\} = 1.$$
:::

::: {.definition}
**Definition 7.2 — Convergence in probability**

We write
$$X_n \xrightarrow{p} X$$
if for every $\varepsilon > 0$,
$$\mathbb{P}(|X_n - X| > \varepsilon) \to 0.$$
:::

::: {.definition}
**Definition 7.3 — $L^p$ convergence**

For $p \geq 1$,
$$X_n \xrightarrow{L^p} X$$
if
$$\mathbb{E}|X_n - X|^p \to 0.$$
:::

::: {.definition}
**Definition 7.4 — Convergence in distribution**

We write
$$X_n \xrightarrow{d} X$$
if
$$F_{X_n}(x) \to F_X(x)$$
:::

<!-- page 54 -->

at every continuity point $x$ of $F_X$.

The main implication structure is
$$X_n \xrightarrow{a.s.} X \implies X_n \xrightarrow{p} X \implies X_n \xrightarrow{d} X,$$
and
$$X_n \xrightarrow{L^p} X \implies X_n \xrightarrow{p} X.$$
The reverse arrows fail in general.

::: {.proof}
To see that $L^p$ convergence implies convergence in probability, apply Markov's inequality:
$$\mathbb{P}(|X_n - X| > \varepsilon) = \mathbb{P}(|X_n - X|^p > \varepsilon^p) \leq \frac{\mathbb{E}|X_n - X|^p}{\varepsilon^p} \to 0.$$
:::

::: {.proposition}
**Proposition 7.5 — Almost sure convergence implies convergence in probability**

If
$$X_n \xrightarrow{a.s.} X,$$
then
$$X_n \xrightarrow{p} X.$$
:::

::: {.proof}
Fix $\varepsilon > 0$ and define
$$A_N = \bigcup_{n \geq N} \{|X_n - X| > \varepsilon\}.$$
Then $A_N \downarrow A$, where
$$A \subseteq \{X_n \not\to X\}.$$
Almost-sure convergence gives $\mathbb{P}(A) = 0$. By continuity from above,
$$\mathbb{P}(A_N) \to 0.$$
Since
$$\mathbb{P}(|X_N - X| > \varepsilon) \leq \mathbb{P}(A_N),$$
convergence in probability follows.
:::

<!-- page 55 -->

::: {.proposition}
**Proposition 7.6 — Convergence in probability implies convergence in distribution**

If
$$X_n \xrightarrow{p} X,$$
then
$$X_n \xrightarrow{d} X.$$
:::

A convenient proof uses the inequalities, for every $\varepsilon > 0$,
$$\mathbb{P}(X_n \leq x) \leq \mathbb{P}(X \leq x + \varepsilon) + \mathbb{P}(|X_n - X| > \varepsilon),$$
and
$$\mathbb{P}(X_n \leq x) \geq \mathbb{P}(X \leq x - \varepsilon) - \mathbb{P}(|X_n - X| > \varepsilon).$$
At continuity points of $F_X$, first let $n \to \infty$, then $\varepsilon \downarrow 0$.

::: {.remark}
**Remark 7.7 — Rigorous layer: Subsequence characterization**

A useful theorem states:
$$X_n \xrightarrow{p} X$$
if and only if every subsequence $\{X_{n_k}\}$ contains a further subsequence $\{X_{n_{k_j}}\}$ such that
$$X_{n_{k_j}} \xrightarrow{a.s.} X.$$
Convergence in probability is therefore exactly the mode of convergence whose every subsequence has an almost-surely convergent refinement.
:::

7.2 A counterexample to probability implying almost sure

Let $\Omega = [0, 1]$ with Lebesgue probability and let $X_n$ be indicators of intervals that sweep repeatedly across $[0, 1]$ with lengths tending to zero. Then
$$\mathbb{P}(X_n = 1) \to 0,$$
so $X_n \xrightarrow{p} 0$, while one can arrange for every $\omega$ to belong to infinitely many intervals, so $X_n(\omega)$ does not converge to zero. This illustrates that convergence in probability controls each $n$ separately, while almost-sure convergence controls the whole path of the sequence.

<!-- page 56 -->

7.3 Subsequence characterization of convergence in probability

A useful bridge between convergence in probability and almost-sure convergence is the following.

::: {.proposition}
**Proposition 7.8 — Almost-sure subsequences**

The sequence $X_n$ converges to $X$ in probability if and only if every subsequence $X_{n_k}$ contains a further subsequence $X_{n_{k_j}}$ such that
$$X_{n_{k_j}} \xrightarrow{a.s.} X.$$
:::

The forward direction is obtained by selecting a further subsequence for which
$$\mathbb{P}(|X_{n_{k_j}} - X| > 2^{-j}) \leq 2^{-j}$$
and applying Borel–Cantelli. This principle is extremely useful when one wants to prove a statement for convergence in probability by first proving it along almost-surely convergent subsequences.

7.4 Continuous Mapping Theorem

::: {.theorem}
**Theorem 7.9 — Continuous Mapping Theorem**

If
$$X_n \xrightarrow{d} X$$
and $g$ is continuous at every point in a set $C$ with $\mathbb{P}(X \in C) = 1$, then
$$g(X_n) \xrightarrow{d} g(X).$$
The same statement holds with convergence in probability or almost surely in place of convergence in distribution.
:::

Typical consequences include
$$X_n \xrightarrow{p} c \implies X_n^2 \xrightarrow{p} c^2, \quad X_n \xrightarrow{p} c \neq 0 \implies \frac{1}{X_n} \xrightarrow{p} \frac{1}{c}.$$

<!-- page 57 -->

7.5 Slutsky's theorem

::: {.theorem}
**Theorem 7.10 — Slutsky**

If
$$X_n \xrightarrow{d} X, \quad Y_n \xrightarrow{p} c,$$
then
$$X_n + Y_n \xrightarrow{d} X + c,$$
$$X_n Y_n \xrightarrow{d} cX,$$
and if $c \neq 0$,
$$\frac{X_n}{Y_n} \xrightarrow{d} \frac{X}{c}.$$
:::

Slutsky is the standard device for replacing unknown constants by consistent estimators in asymptotic distributions.

7.6 Convergence of expectations and uniform integrability

Convergence in probability or distribution alone does not imply convergence of expectations. Rare but extremely large realizations can disappear in probability while still dominating the mean.

::: {.example}
**Example 7.11 — Convergence in probability without convergence of means**

Let
$$X_n = n\mathbf{1}_{A_n}, \quad \mathbb{P}(A_n) = \frac{1}{n}.$$
Then for every $\varepsilon > 0$,
$$\mathbb{P}(|X_n| > \varepsilon) = \frac{1}{n} \to 0,$$
so $X_n \xrightarrow{p} 0$. But
$$\mathbb{E}[X_n] = 1$$
for every $n$.
:::

A family $\{X_n\}$ is uniformly integrable if
$$\lim_{K \to \infty} \sup_n \mathbb{E} \left[ |X_n| \mathbf{1}_{\{|X_n| > K\}} \right] = 0.$$
A useful theorem is:
$$X_n \xrightarrow{p} X \quad \text{and} \quad \{X_n\} \text{ uniformly integrable} \implies \mathbb{E}|X_n - X| \to 0.$$

<!-- page 58 -->

A simple sufficient condition is a uniform higher-moment bound: if for some $\delta > 0$,
$$\sup_n \mathbb{E}|X_n|^{1+\delta} < \infty,$$
then $\{X_n\}$ is uniformly integrable.

7.7 Stochastic order notation

Econometric asymptotics compress repeated probability bounds into the symbols $o_p$ and $O_p$.

::: {.definition}
**Definition 7.12 — Little-$o_p$**

We write
$$X_n = o_p(a_n)$$
if
$$\frac{X_n}{a_n} \xrightarrow{p} 0.$$
:::

::: {.definition}
**Definition 7.13 — Big-$O_p$**

We write
$$X_n = O_p(a_n)$$
if $X_n/a_n$ is bounded in probability: for every $\varepsilon > 0$, there exist $M < \infty$ and $N$ such that
$$\mathbb{P}\left( \left| \frac{X_n}{a_n} \right| > M \right) < \varepsilon \quad \forall n \geq N.$$
:::

Examples:
$$X_n \xrightarrow{p} c \implies X_n = O_p(1),$$
and if
$$\sqrt{n}(T_n - \theta) \xrightarrow{d} Z,$$
then
$$T_n - \theta = O_p(n^{-1/2}).$$
The familiar algebra is valid under mild conditions:
$$o_p(1) + o_p(1) = o_p(1), \quad O_p(1)o_p(1) = o_p(1),$$
$$O_p(a_n)O_p(b_n) = O_p(a_n b_n).$$

<!-- page 59 -->

7.8 Weak convergence and the Portmanteau viewpoint

For probability measures $\mu_n, \mu$ on $\mathbb{R}^k$, weak convergence $\mu_n \Rightarrow \mu$ means
$$\int f \, d\mu_n \to \int f \, d\mu$$
for every bounded continuous $f$. For random variables,
$$X_n \xrightarrow{d} X$$
is equivalent to weak convergence of their laws.

::: {.remark}
**Remark 7.14 — Rigorous layer: Portmanteau theorem — selected equivalences**

The following are equivalent:
1. $X_n \xrightarrow{d} X$;
2. $\mathbb{E}[f(X_n)] \to \mathbb{E}[f(X)]$ for every bounded continuous $f$;
3. for every closed $F$,
$$\limsup_n \mathbb{P}(X_n \in F) \leq \mathbb{P}(X \in F);$$
4. for every open $G$,
$$\liminf_n \mathbb{P}(X_n \in G) \geq \mathbb{P}(X \in G).$$
:::

7.9 Cramér–Wold device

For random vectors $X_n, X \in \mathbb{R}^k$,
$$X_n \xrightarrow{d} X$$
if and only if
$$a^\top X_n \xrightarrow{d} a^\top X \quad \forall a \in \mathbb{R}^k.$$
This reduces multivariate weak convergence to one-dimensional weak convergence and is the key bridge from the scalar CLT to the multivariate CLT.

<!-- page 60 -->

8 Laws of Large Numbers

**Sources.** Klenke and Durrett are the principal references for the weak and strong laws and their probability-theoretic proofs. Hansen motivates sample-moment applications, while the concentration material is included as a modern complement to classical LLN arguments.

8.1 Sample averages

Let $X_1, X_2, \dots$ be iid with mean $\mu$. Define
$$\bar{X}_n = \frac{1}{n} \sum_{i=1}^n X_i.$$
The law of large numbers states that the random sample average becomes close to the population mean as $n$ grows.

8.2 Weak law via Chebyshev

::: {.theorem}
**Theorem 8.1 — Weak Law of Large Numbers, finite-variance version**

If $X_i$ are iid with
$$\mathbb{E}[X_i] = \mu, \quad \text{Var}(X_i) = \sigma^2 < \infty,$$
then
$$\bar{X}_n \xrightarrow{p} \mu.$$
:::

::: {.proof}
By independence,
$$\text{Var}(\bar{X}_n) = \frac{1}{n^2} \sum_{i=1}^n \text{Var}(X_i) = \frac{\sigma^2}{n}.$$
Therefore Chebyshev gives
$$\mathbb{P}(|\bar{X}_n - \mu| > \varepsilon) \leq \frac{\sigma^2}{n\varepsilon^2} \to 0.$$
:::

The proof shows the division of labor:
$$\text{independence} \implies \text{Var}(\bar{X}_n) = O(n^{-1}),$$
and concentration follows from Chebyshev.

<!-- page 61 -->

## 8.3 Strong law

::: {.infobox}
**Theorem 8.2 — Kolmogorov Strong Law for iid variables**

If $X_1, X_2, \dots$ are iid and
$$\mathbb{E}|X_1| < \infty,$$
then
$$\bar{X}_n \xrightarrow{a.s.} \mathbb{E}[X_1].$$
:::

The full proof requires more machinery than the weak law. Its importance is conceptual: with probability one, a realized infinite sample path has sample averages converging to the population mean.

::: {.infobox}
**Remark 8.3 — Rigorous layer: A Borel-Cantelli proof under stronger moments**

Suppose $X_i$ are iid with $\mathbb{E}[X_i] = 0$ and $\mathbb{E}[X_i^4] < \infty$. One can show
$$\mathbb{E}[S_n^4] = O(n^2), \quad S_n = \sum_{i=1}^n X_i.$$
Hence
$$\mathbb{P}\left(\left|\frac{S_n}{n}\right| > \varepsilon\right) \leq \frac{\mathbb{E}[S_n^4]}{n^4 \varepsilon^4} = O(n^{-2}).$$
The probabilities are summable, so Borel-Cantelli implies
$$\frac{S_n}{n} \to 0 \quad a.s.$$
This is not the sharpest strong law, but it reveals the logic: a summable tail bound upgrades probabilistic concentration to an almost-sure statement.
:::

## 8.4 Exponential concentration: Chernoff and Hoeffding bounds

Chebyshev's inequality uses only a second moment and therefore gives polynomial tail bounds. If moment-generating functions are controlled, exponentially small tail probabilities are often available.
For any $t > 0$, Markov's inequality gives
$$\mathbb{P}(S_n \geq a) = \mathbb{P}(e^{tS_n} \geq e^{ta}) \leq e^{-ta}\mathbb{E}[e^{tS_n}].$$
If $X_1, \dots, X_n$ are independent,
$$\mathbb{E}[e^{tS_n}] = \prod_{i=1}^n \mathbb{E}[e^{tX_i}].$$
Optimizing over $t$ yields a Chernoff bound.

<!-- page 62 -->

::: {.infobox}
**Theorem 8.4 — Hoeffding inequality, bounded iid case**

If $X_1, \dots, X_n$ are independent with $a \leq X_i \leq b$ almost surely and $\mathbb{E}[X_i] = \mu_i$, then for $\bar{X}_n = n^{-1} \sum_i X_i$ and $\bar{\mu}_n = n^{-1} \sum_i \mu_i$,
$$\mathbb{P}(|\bar{X}_n - \bar{\mu}_n| \geq \varepsilon) \leq 2 \exp\left( -\frac{2n\varepsilon^2}{(b-a)^2} \right).$$
:::

Unlike Chebyshev's $O(n^{-1})$ bound for fixed $\varepsilon$, Hoeffding gives exponential decay in $n$. Concentration inequalities are finite-sample counterparts to laws of large numbers and are increasingly important in modern statistics and econometrics.

## 8.5 Sample moments

If $\mathbb{E}|X|^k < \infty$, the LLN gives
$$\frac{1}{n} \sum_{i=1}^n X_i^k \xrightarrow{p} \mathbb{E}[X^k].$$
Thus
$$\frac{1}{n} \sum_{i=1}^n (X_i - \bar{X}_n)^2 \xrightarrow{p} \text{Var}(X)$$
under finite second moments. More generally, sample moment conditions
$$\frac{1}{n} \sum_{i=1}^n g(W_i, \theta)$$
converge to population moments
$$\mathbb{E}[g(W, \theta)]$$
under appropriate LLN conditions. This is the probabilistic foundation of method-of-moments and GMM estimation.

## 8.6 Empirical distribution and Glivenko-Cantelli

Given iid observations $X_1, \dots, X_n$, define the empirical CDF
$$F_n(x) = \frac{1}{n} \sum_{i=1}^n \mathbf{1}_{\{X_i \leq x\}}.$$
For each fixed $x$, the LLN gives
$$F_n(x) \xrightarrow{p} F(x).$$

<!-- page 63 -->

A much stronger result is the Glivenko-Cantelli theorem:
$$\sup_{x \in \mathbb{R}} |F_n(x) - F(x)| \xrightarrow{a.s.} 0.$$
Thus the empirical distribution converges uniformly to the population distribution.
The Dvoretzky-Kiefer-Wolfowitz inequality gives a finite-sample bound:
$$\mathbb{P}\left(\sup_{x} |F_n(x) - F(x)| > \varepsilon\right) \leq 2e^{-2n\varepsilon^2}.$$
This is an early example of a uniform law of large numbers.

## 8.7 Beyond iid: what changes?

Independence is sufficient, not necessary. Many economic data are dependent over time or within groups. Laws of large numbers continue to hold under weak dependence, mixing, martingale-difference, ergodic, or cluster structures, but the required conditions differ. The core lesson is that one needs a mechanism preventing dependence from accumulating too quickly.

# 9 Central Limit Theory and Asymptotic Calculus

**Sources.** The classical and multivariate CLTs follow the standard treatments in Billingsley, Klenke, and Durrett. The delta method, stochastic expansions, studentization, and estimating-equation template are organized with Hansen and van der Vaart in mind.

## 9.1 Why the $\sqrt{n}$ scaling appears

Under iid sampling with variance $\sigma^2$,
$$\text{Var}(\bar{X}_n) = \frac{\sigma^2}{n}.$$
Thus
$$\sqrt{n}(\bar{X}_n - \mu)$$
has variance $\sigma^2$, which does not vanish. The central limit theorem identifies its limiting distribution.

<!-- page 64 -->

## 9.2 Lindeberg-Lévy CLT

::: {.infobox}
**Theorem 9.1 — Classical Central Limit Theorem**

If $X_1, X_2, \dots$ are iid with
$$\mathbb{E}[X_i] = \mu, \quad 0 < \text{Var}(X_i) = \sigma^2 < \infty,$$
then
$$\frac{\sqrt{n}(\bar{X}_n - \mu)}{\sigma} \xrightarrow{d} N(0, 1).$$
Equivalently,
$$\sqrt{n}(\bar{X}_n - \mu) \xrightarrow{d} N(0, \sigma^2).$$
:::

The LLN says the error vanishes; the CLT says the error is typically of order $n^{-1/2}$ and describes its shape after rescaling.

## 9.3 Characteristic-function proof

Let
$$Y_i = \frac{X_i - \mu}{\sigma}, \quad \mathbb{E}[Y_i] = 0, \quad \mathbb{E}[Y_i^2] = 1.$$
For small $t$, the characteristic function satisfies
$$\varphi_Y(t) = 1 - \frac{t^2}{2} + o(t^2).$$
The characteristic function of
$$Z_n = \frac{1}{\sqrt{n}} \sum_{i=1}^n Y_i$$
is, by independence,
$$\varphi_{Z_n}(t) = \left[ \varphi_Y\left( \frac{t}{\sqrt{n}} \right) \right]^n.$$
Using the local expansion,
$$\varphi_Y\left( \frac{t}{\sqrt{n}} \right) = 1 - \frac{t^2}{2n} + o(n^{-1}),$$
so
$$\varphi_{Z_n}(t) \to \exp\left( -\frac{t^2}{2} \right),$$
which is the characteristic function of $N(0, 1)$. Lévy's continuity theorem then yields
$$Z_n \xrightarrow{d} N(0, 1).$$

<!-- page 65 -->

::: {.infobox}
**Remark 9.2 — Rigorous layer: What Lévy's continuity theorem contributes**

Characteristic functions uniquely determine probability laws. Lévy's continuity theorem strengthens uniqueness into a convergence statement: pointwise convergence of characteristic functions to a function continuous at zero and itself a characteristic function implies weak convergence of the associated probability measures.
:::

## 9.4 Multivariate CLT

Let $X_i \in \mathbb{R}^k$ be iid with
$$\mathbb{E}[X_i] = \mu, \quad \text{Var}(X_i) = \Sigma < \infty.$$
Then
$$\sqrt{n}(\bar{X}_n - \mu) \xrightarrow{d} N_k(0, \Sigma).$$

::: {.infobox}
**Proof**

For every $a \in \mathbb{R}^k$,
$$a^\top \sqrt{n}(\bar{X}_n - \mu) = \sqrt{n} \left( \frac{1}{n} \sum_{i=1}^n a^\top X_i - a^\top \mu \right).$$
The scalar CLT gives
$$a^\top \sqrt{n}(\bar{X}_n - \mu) \xrightarrow{d} N(0, a^\top \Sigma a).$$
By Cramér-Wold, the vector converges to $N_k(0, \Sigma)$.
:::

## 9.5 Delta method

::: {.infobox}
**Theorem 9.3 — Scalar Delta Method**

Suppose
$$\sqrt{n}(T_n - \theta) \xrightarrow{d} N(0, V),$$
and $g$ is differentiable at $\theta$. Then
$$\sqrt{n}(g(T_n) - g(\theta)) \xrightarrow{d} N(0, [g'(\theta)]^2 V).$$
:::

::: {.infobox}
**Proof**

Differentiability gives
$$g(T_n) - g(\theta) = g'(\theta)(T_n - \theta) + r_n,$$
:::

<!-- page 66 -->

where
$$\frac{r_n}{T_n - \theta} \xrightarrow{p} 0.$$
Since $T_n \xrightarrow{p} \theta$,
$$\sqrt{n}r_n = \sqrt{n}(T_n - \theta) \frac{r_n}{T_n - \theta} \xrightarrow{p} 0.$$
Therefore
$$\sqrt{n}(g(T_n) - g(\theta)) = g'(\theta)\sqrt{n}(T_n - \theta) + o_p(1),$$
and Slutsky completes the proof.

For $T_n \in \mathbb{R}^k, g : \mathbb{R}^k \to \mathbb{R}^m$, and Jacobian $Dg(\theta)$,
$$\sqrt{n}(T_n - \theta) \xrightarrow{d} N_k(0, V)$$
implies
$$\sqrt{n}(g(T_n) - g(\theta)) \xrightarrow{d} N_m(0, Dg(\theta)VDg(\theta)^\top).$$

## 9.6 Asymptotic linearization

Many estimators admit an expansion
$$\sqrt{n}(\widehat{\theta}_n - \theta_0) = \frac{1}{\sqrt{n}} \sum_{i=1}^n \psi(W_i) + o_p(1),$$
where
$$\mathbb{E}[\psi(W_i)] = 0.$$
If
$$\text{Var}(\psi(W_i)) = \Omega < \infty,$$
the CLT and Slutsky imply
$$\sqrt{n}(\widehat{\theta}_n - \theta_0) \xrightarrow{d} N(0, \Omega).$$
This representation is the generic architecture behind smooth method-of-moments estimators, maximum likelihood estimators, and influence-function methods. The difficult part of a new econometric problem is often to identify the correct first-order term $\psi$ and show that the remainder is $o_p(1)$.

<!-- page 67 -->

## 9.7 Studentization and plug-in variance estimation

Suppose
$$\sqrt{n}(T_n - \theta) \xrightarrow{d} N(0, V),$$
and $\widehat{V}_n \xrightarrow{p} V > 0$. Then
$$\frac{\sqrt{n}(T_n - \theta)}{\sqrt{\widehat{V}_n}} \xrightarrow{d} N(0, 1)$$
by Slutsky. This is the generic logic behind asymptotic $t$-statistics.

## 9.8 Estimating equations: LLN + Taylor + CLT

Suppose an estimator $\widehat{\theta}_n$ solves
$$0 = \frac{1}{n} \sum_{i=1}^n g(W_i, \widehat{\theta}_n),$$
while the population parameter solves
$$\mathbb{E}[g(W_i, \theta_0)] = 0.$$
A Taylor expansion around $\theta_0$ gives, schematically,
$$0 = \frac{1}{n} \sum_{i=1}^n g(W_i, \theta_0) + G_n(\widetilde{\theta}_n)(\widehat{\theta}_n - \theta_0),$$
where
$$G_n(\theta) = \frac{1}{n} \sum_{i=1}^n \frac{\partial g(W_i, \theta)}{\partial \theta^\top}.$$
Hence
$$\sqrt{n}(\widehat{\theta}_n - \theta_0) = -G_n(\widetilde{\theta}_n)^{-1} \frac{1}{\sqrt{n}} \sum_{i=1}^n g(W_i, \theta_0).$$
If an LLN gives
$$G_n(\widetilde{\theta}_n) \xrightarrow{p} G,$$
and a CLT gives
$$\frac{1}{\sqrt{n}} \sum_{i=1}^n g(W_i, \theta_0) \xrightarrow{d} N(0, \Omega),$$
then Slutsky yields
$$\sqrt{n}(\widehat{\theta}_n - \theta_0) \xrightarrow{d} N(0, G^{-1}\Omega(G^{-1})^\top).$$
This LLN–Taylor–CLT architecture is one of the main reasons probability limit theory is taught before first-year econometrics.

<!-- page 68 -->

## 9.9 Berry-Esseen and rates

The CLT is qualitative. Under a finite third absolute moment, Berry-Esseen gives a uniform error bound of order $n^{-1/2}$:
$$\sup_{x} \left| \mathbb{P}\left( \frac{\sqrt{n}(\bar{X}_n - \mu)}{\sigma} \leq x \right) - \Phi(x) \right| \leq \frac{C\mathbb{E}|X - \mu|^3}{\sigma^3 \sqrt{n}}$$
for a universal constant $C$. This clarifies why a CLT can be asymptotically correct but inaccurate in small samples when tails are heavy or skewness is large.

::: {.infobox}
**Remark 9.4 — Rigorous layer: Triangular arrays and Lindeberg-Feller**

In many estimators the summands depend on $n$. A triangular-array CLT considers independent mean-zero variables $X_{n1}, \dots, X_{nk_n}$ with total variance
$$s_n^2 = \sum_{j=1}^{k_n} \text{Var}(X_{nj}).$$
A Lindeberg condition such as
$$\frac{1}{s_n^2} \sum_j \mathbb{E}\left[ X_{nj}^2 \mathbf{1}_{\{|X_{nj}| > \varepsilon s_n\}} \right] \to 0 \quad \forall \varepsilon > 0$$
prevents any single large term from dominating. Under suitable variance normalization,
$$\frac{\sum_j X_{nj}}{s_n} \xrightarrow{d} N(0, 1).$$
This is a more useful template for modern asymptotic theory than the iid CLT alone.
:::

# 10 Stochastic Processes: Martingales and Markov Chains

**Sources.** This bridge chapter follows Williams and Durrett for martingales and Markov chains, with MIT 6.436 as a model for how these objects naturally follow a first rigorous probability course. This chapter is not necessary for a minimal probability block, but it provides the natural bridge to macroeconomics, finance, and dynamic econometrics.

## 10.1 Stochastic processes and filtrations

A stochastic process is a family $\{X_t\}_{t \in T}$ of random variables on a common probability space. A filtration
$$\mathcal{F}_0 \subseteq \mathcal{F}_1 \subseteq \dots$$
represents the accumulation of information over time. A process is adapted if $X_t$ is $\mathcal{F}_t$-measurable.

<!-- page 69 -->

## 10.2 Martingales

::: {.infobox}
**Definition 10.1 — Martingale**

An integrable adapted process $\{M_t\}$ is a martingale with respect to $\{\mathcal{F}_t\}$ if
$$\mathbb{E}[M_{t+1} | \mathcal{F}_t] = M_t \quad a.s.$$
:::

If $X_t$ are iid with mean zero and
$$M_t = \sum_{s=1}^t X_s,$$
then $M_t$ is a martingale under the natural filtration.
A martingale difference sequence $u_t$ satisfies
$$\mathbb{E}[u_t | \mathcal{F}_{t-1}] = 0.$$
Then
$$M_t = \sum_{s=1}^t u_s$$
is a martingale. This is the time-series analogue of a mean-zero regression error conditional on past information.

## 10.3 Markov chains

A discrete-time process $X_t$ is Markov if
$$\mathbb{P}(X_{t+1} \in A | X_t, X_{t-1}, \dots) = \mathbb{P}(X_{t+1} \in A | X_t).$$
For a finite state space, the transition matrix $P$ has entries
$$P_{ij} = \mathbb{P}(X_{t+1} = j | X_t = i).$$
If $\pi_t$ is the row vector of state probabilities, then
$$\pi_{t+1} = \pi_t P.$$
A stationary distribution satisfies
$$\pi = \pi P.$$
Under irreducibility and aperiodicity in a finite chain, the distribution converges to the unique stationary distribution.

<!-- page 70 -->

## 10.4 Stationarity and an ergodic LLN

A process $\{X_t\}$ is strictly stationary if
$$(X_{t_1}, \dots, X_{t_k}) \stackrel{d}{=} (X_{t_1+h}, \dots, X_{t_k+h})$$
for every finite collection of dates and every admissible shift $h$. Stationarity alone does not imply that time averages converge to population means; an additional ergodicity condition rules out persistent random components that never average away.

::: {.infobox}
**Remark 10.2 — Rigorous layer: Birkhoff’s ergodic theorem, probability form**

For a stationary ergodic process with $\mathbb{E}|X_0| < \infty$,
$$\frac{1}{T} \sum_{t=1}^T X_t \xrightarrow{a.s.} \mathbb{E}[X_0].$$
This is the dependent-data analogue of the strong law most directly relevant for stationary time series and dynamic economic models.
:::

::: {.infobox}
**Remark 10.3 — Why this belongs at the end**

The earlier chapters provide all the ingredients: sigma-algebras describe information, conditional expectations describe forecasts, and convergence theorems describe long-run behavior. Martingales and Markov chains simply organize these ingredients over time.
:::

# 11 Further Distributional Tools for Economists

**Sources.** This section fills several gaps between the standard univariate distribution material and the multivariate calculations used in econometrics. The organization follows the emphasis in Hong on joint transforms, implications of independence, and sampling distributions, with Hansen as a complementary economics-facing reference.

## 11.1 Joint moment-generating and characteristic functions

For a random vector
$$X = (X_1, \dots, X_k)^\top,$$
the joint moment-generating function is
$$M_X(t) = \mathbb{E}[e^{t^\top X}], \quad t \in \mathbb{R}^k,$$

<!-- page 71 -->

whenever the expectation is finite in a neighborhood of the origin. The joint characteristic function is
$$\varphi_X(t) = \mathbb{E}[e^{it^\top X}], \quad t \in \mathbb{R}^k,$$
and always exists.
The joint transform contains both marginal and cross-moment information. For example,
$$\left. \frac{\partial M_X(t)}{\partial t_j} \right|_{t=0} = \mathbb{E}[X_j],$$
and, when the second moments exist,
$$\left. \frac{\partial^2 M_X(t)}{\partial t_j \partial t_\ell} \right|_{t=0} = \mathbb{E}[X_j X_\ell].$$
Thus the covariance matrix can be recovered from the Hessian of the joint MGF at the origin.

::: {.infobox}
**Proposition 11.1 — Factorization under independence**

If $X_1, \dots, X_k$ are independent and their MGFs exist near zero, then
$$M_X(t_1, \dots, t_k) = \prod_{j=1}^k M_{X_j}(t_j).$$
The analogous factorization holds for characteristic functions without any moment assumptions:
$$\varphi_X(t_1, \dots, t_k) = \prod_{j=1}^k \varphi_{X_j}(t_j).$$
Conversely, factorization of the joint characteristic function into the marginal characteristic functions implies independence.
:::

::: {.infobox}
**Example 11.2 — Independent Poisson counts and their sum**

Suppose
$$X \sim \text{Pois}(\lambda), \quad Y \sim \text{Pois}(\mu), \quad X \perp Y.$$
Then
$$M_{X,Y}(s, t) = \exp\{\lambda(e^s - 1)\} \exp\{\mu(e^t - 1)\}.$$
Setting $s = t = u$ gives the MGF of $X + Y$:
$$M_{X+Y}(u) = \exp\{(\lambda + \mu)(e^u - 1)\},$$
:::

<!-- page 72 -->

so
$$X + Y \sim \text{Pois}(\lambda + \mu).$$

## 11.2 Linear combinations, portfolios, and covariance accounting

For any random vector $X \in \mathbb{R}^k$ with covariance matrix $\Sigma$ and any deterministic vector $a \in \mathbb{R}^k$,
$$\text{Var}(a^\top X) = a^\top \Sigma a.$$
In coordinates,
$$\text{Var}\left( \sum_{j=1}^k a_j X_j \right) = \sum_{j=1}^k a_j^2 \text{Var}(X_j) + 2 \sum_{j < \ell} a_j a_\ell \text{Cov}(X_j, X_\ell).$$
The covariance terms disappear under pairwise uncorrelatedness, not because variance is linear.

::: {.infobox}
**Example 11.3 — Two-asset portfolio**

Let
$$R_p = wR_1 + (1 - w)R_2.$$
Then
$$\mathbb{E}[R_p] = w\mathbb{E}[R_1] + (1 - w)\mathbb{E}[R_2],$$
and
$$\text{Var}(R_p) = w^2\sigma_1^2 + (1 - w)^2\sigma_2^2 + 2w(1 - w)\rho\sigma_1\sigma_2.$$
Diversification is therefore a statement about covariance as well as individual variances. If $\rho < 1$, an interior portfolio can have lower variance than a simple weighted average of the two individual variances.
:::

## 11.3 The $F$ distribution and ratios of quadratic forms

The normal, chi-square, $t$, and $F$ distributions form a tightly connected family.

::: {.infobox}
**Definition 11.4 — $F$ distribution**

Let
$$Q_1 \sim \chi^2_{\nu_1}, \quad Q_2 \sim \chi^2_{\nu_2}, \quad Q_1 \perp Q_2.$$
Then
$$F = \frac{Q_1/\nu_1}{Q_2/\nu_2}$$
:::

<!-- page 73 -->

has an $F$ distribution with $(\nu_1, \nu_2)$ degrees of freedom, written
$$F \sim F_{\nu_1, \nu_2}.$$
If
$$T \sim t_\nu,$$
then
$$T^2 \sim F_{1, \nu}.$$
This identity explains the equivalence between a two-sided $t$ test and a one-restriction $F$ test in the Gaussian linear model.
If two independent normal samples satisfy
$$X_1, \dots, X_m \overset{\text{iid}}{\sim} \mathcal{N}(\mu_X, \sigma_X^2), \quad Y_1, \dots, Y_n \overset{\text{iid}}{\sim} \mathcal{N}(\mu_Y, \sigma_Y^2),$$
then
$$\frac{S_X^2 / \sigma_X^2}{S_Y^2 / \sigma_Y^2} \sim F_{m-1, n-1}.$$
Thus the $F$ distribution appears naturally when comparing independent variance estimates.

### 11.4 Mixture distributions and latent heterogeneity
Economic populations are often heterogeneous. A convenient probability model introduces a latent group variable $G$. Suppose
$$\mathbb{P}(G = g) = \pi_g, \quad \sum_{g=1}^G \pi_g = 1,$$
and conditional on $G = g$, the variable $X$ has CDF $F_g$ and density $f_g$. Then the unconditional law is the mixture
$$F_X(x) = \sum_{g=1}^G \pi_g F_g(x), \quad f_X(x) = \sum_{g=1}^G \pi_g f_g(x).$$
The law of iterated expectations gives
$$\mathbb{E}[X] = \sum_{g=1}^G \pi_g \mu_g, \quad \mu_g = \mathbb{E}[X \mid G = g],$$
and the law of total variance gives
$$\text{Var}(X) = \sum_{g=1}^G \pi_g \sigma_g^2 + \sum_{g=1}^G \pi_g (\mu_g - \mu)^2.$$

<!-- page 74 -->

Hence aggregate variation decomposes into *within-group* and *between-group* variation.

**Example 11.5 — A two-type income mixture**
Suppose
$$X \mid G = 0 \sim \mathcal{N}(0, 1), \quad X \mid G = 1 \sim \mathcal{N}(3, 1), \quad \mathbb{P}(G = 1) = \pi.$$
Then
$$\mathbb{E}[X] = 3\pi,$$
and
$$\text{Var}(X) = 1 + 9\pi(1 - \pi).$$
Even though each type has variance one, latent heterogeneity raises the unconditional variance through the between-type component.

**Remark 11.6 — Mixtures need not inherit the shape of their components**
A mixture of normal distributions is generally not normal. It may be skewed, heavy-tailed, or multimodal. This is one reason why aggregate cross-sectional distributions can look very different from the conditional distributions faced by homogeneous subgroups.

## 12 Sampling Distributions and Finite-Sample Calculations
**Sources.** Hong's sampling chapter emphasizes the distinction between a population, a random sample, a statistic, and the statistic's sampling distribution. This section makes that distinction explicit and collects the finite-sample calculations that students use repeatedly before asymptotic theory takes over.

### 12.1 Population, random sample, statistic, and sampling distribution
**Definition 12.1 — Sampling distribution**
Let
$$X_1, \dots, X_n \overset{\text{iid}}{\sim} F$$
be a random sample from a population law $F$, and let
$$T_n = T(X_1, \dots, X_n)$$
be a statistic. The **sampling distribution** of $T_n$ is the probability law induced on $T_n$ by repeated random sampling from $F$.

<!-- page 75 -->

The population law $F$ describes individual observations. The sampling distribution describes a function of an entire sample. These are different objects. For example, even when the $X_i$ are Bernoulli,
$$X_i \in \{0, 1\},$$
the sample mean
$$\bar{X}_n \in \left\{0, \frac{1}{n}, \dots, 1\right\}$$
has a different distribution.
A statistic is random before observing the data and numerical after observing the data. Thus
$$\bar{X}_n$$
is a random variable ex ante, whereas a realized sample produces a number
$$\bar{x}_n.$$

### 12.2 Exact sampling distribution of a sample proportion
Let
$$X_1, \dots, X_n \overset{\text{iid}}{\sim} \text{Bern}(p), \quad \widehat{p} = \bar{X}_n.$$
Then
$$n\widehat{p} = \sum_{i=1}^n X_i \sim \text{Bin}(n, p).$$
Therefore
$$\mathbb{P}\left(\widehat{p} = \frac{k}{n}\right) = \binom{n}{k} p^k (1 - p)^{n-k}, \quad k = 0, \dots, n,$$
with
$$\mathbb{E}[\widehat{p}] = p, \quad \text{Var}(\widehat{p}) = \frac{p(1 - p)}{n}.$$
The standard deviation of the sampling distribution is
$$\text{se}(\widehat{p}) = \sqrt{\frac{p(1 - p)}{n}}.$$

### 12.3 Exact sampling distributions closed under summation
Some families are stable under addition, making sample statistics particularly easy to analyze.
If
$$X_1, \dots, X_n \overset{\text{iid}}{\sim} \text{Pois}(\lambda),$$

<!-- page 76 -->

then
$$\sum_{i=1}^n X_i \sim \text{Pois}(n\lambda),$$
and hence
$$\bar{X}_n = \frac{1}{n} \text{Pois}(n\lambda)$$
in the sense that $n\bar{X}_n$ has the Poisson law above. Therefore
$$\mathbb{E}[\bar{X}_n] = \lambda, \quad \text{Var}(\bar{X}_n) = \frac{\lambda}{n}.$$
If
$$X_1, \dots, X_n \overset{\text{iid}}{\sim} \mathcal{N}(\mu, \sigma^2),$$
then exactly, for every $n$,
$$\bar{X}_n \sim \mathcal{N}\left(\mu, \frac{\sigma^2}{n}\right).$$
No central limit approximation is needed.

### 12.4 Standard deviation, standard error, and estimated standard error
The *standard deviation* of a population variable is a property of its population law. The *standard error* of a statistic is the standard deviation of its sampling distribution.
For the sample mean,
$$\text{se}(\bar{X}_n) = \sqrt{\text{Var}(\bar{X}_n)} = \frac{\sigma}{\sqrt{n}}.$$
If $\sigma$ is unknown, we estimate this standard error by
$$\widehat{\text{se}}(\bar{X}_n) = \frac{S_n}{\sqrt{n}}.$$
These three quantities should not be conflated:
$$\sigma, \quad \frac{\sigma}{\sqrt{n}}, \quad \frac{S_n}{\sqrt{n}}.$$

**Remark 12.2 — Why standard errors shrink at the square-root rate**
Averaging $n$ independent observations divides variance by $n$:
$$\text{Var}(\bar{X}_n) = \frac{\sigma^2}{n}.$$
Taking square roots therefore divides uncertainty by $\sqrt{n}$. To cut a standard error in half, one

<!-- page 77 -->

generally needs roughly four times as many independent observations.

### 12.5 Normal samples: the exact $z, \chi^2, t$, and $F$ structure
Suppose
$$X_1, \dots, X_n \overset{\text{iid}}{\sim} \mathcal{N}(\mu, \sigma^2).$$
Then
$$Z = \frac{\sqrt{n}(\bar{X}_n - \mu)}{\sigma} \sim \mathcal{N}(0, 1),$$
$$Q = \frac{(n - 1)S_n^2}{\sigma^2} \sim \chi_{n-1}^2,$$
and $\bar{X}_n$ is independent of $S_n^2$. Consequently,
$$T = \frac{\sqrt{n}(\bar{X}_n - \mu)}{S_n} = \frac{Z}{\sqrt{Q/(n - 1)}} \sim t_{n-1}.$$
The distinction between $Z$ and $T$ is operationally important:
$$\text{known } \sigma \implies Z,$$
whereas
$$\text{unknown } \sigma \text{ replaced by } S_n \implies T.$$
For two independent normal samples, the ratio of normalized sample variances gives the $F$ distribution described in the previous section.

### 12.6 Simple random sampling without replacement
The iid framework corresponds naturally to sampling with replacement from an idealized population law. Finite-population sampling introduces a useful correction when observations are drawn without replacement.
Consider fixed population values
$$y_1, \dots, y_N,$$
with finite-population mean and variance
$$\mu_N = \frac{1}{N} \sum_{i=1}^N y_i, \quad S_N^2 = \frac{1}{N - 1} \sum_{i=1}^N (y_i - \mu_N)^2.$$
Draw a simple random sample of size $n$ without replacement and let $\bar{Y}_s$ be the sample mean. Then
$$\mathbb{E}[\bar{Y}_s] = \mu_N,$$

<!-- page 78 -->

and
$$\text{Var}(\bar{Y}_s) = \frac{S_N^2}{n} \left(1 - \frac{n}{N}\right).$$
The factor
$$1 - \frac{n}{N}$$
is the *finite-population correction*. When the sampling fraction $n/N$ is negligible, the iid variance formula is an excellent approximation. When a large fraction of the population is observed, sampling uncertainty is smaller because observations are negatively dependent under sampling without replacement.

### 12.7 Normal approximation to the binomial and continuity correction
For
$$X \sim \text{Bin}(n, p),$$
with $np$ and $n(1 - p)$ not too small, the standardized variable
$$\frac{X - np}{\sqrt{np(1 - p)}}$$
is approximately standard normal. Thus
$$X \approx \mathcal{N}(np, np(1 - p)).$$
Because the binomial is discrete and the normal is continuous, a continuity correction often improves the approximation. For example,
$$\mathbb{P}(X \leq k) \approx \Phi\left(\frac{k + 1/2 - np}{\sqrt{np(1 - p)}}\right).$$
Similarly,
$$\mathbb{P}(X \geq k) \approx 1 - \Phi\left(\frac{k - 1/2 - np}{\sqrt{np(1 - p)}}\right).$$

**Example 12.3 — A binomial probability by normal approximation**
Suppose
$$X \sim \text{Bin}(100, 0.4).$$
Then
$$\mathbb{E}[X] = 40, \quad \text{sd}(X) = \sqrt{24}.$$

<!-- page 79 -->

To approximate $\mathbb{P}(X \leq 45)$, use
$$\mathbb{P}(X \leq 45) \approx \Phi\left(\frac{45.5 - 40}{\sqrt{24}}\right).$$
The 0.5 adjustment matches the discrete cutoff at 45 to the corresponding interval under the continuous approximation.

### 12.8 When to use an exact distribution and when to use an asymptotic one
A useful hierarchy is:
$$\text{exact finite-sample distribution available}$$
$$\Downarrow$$
$$\text{use it}$$
$$\text{otherwise}$$
$$\Downarrow$$
$$\text{look for a useful approximation: Poisson, normal, or CLT.}$$
For example:
* Bernoulli sums have an exact binomial law;
* independent Poisson counts have an exact Poisson sum;
* Gaussian sample means are exactly Gaussian;
* generic sample means are approximately Gaussian for large $n$ under CLT conditions.

The word *approximately* is doing mathematical work: asymptotic theory describes an approximation whose quality generally improves with sample size but need not be exact at any finite $n$.

## 13 Hazards, Poisson Arrivals, and Simulation
**Sources.** The first half of this section develops the probability tools behind duration models, search models, default risk, and arrival processes. The second half uses the probability integral transform together with the LLN and CLT to explain simulation and Monte Carlo approximation.

### 13.1 Survival functions and hazard rates
Let $T \geq 0$ be a continuously distributed duration with CDF $F$ and density $f$. The *survival function* is
$$S(t) = \mathbb{P}(T > t) = 1 - F(t).$$

<!-- page 80 -->

The *hazard rate* is
$$h(t) = \lim_{\Delta \downarrow 0} \frac{\mathbb{P}(t \leq T < t + \Delta \mid T \geq t)}{\Delta} = \frac{f(t)}{S(t)},$$
whenever $S(t) > 0$.
Define the cumulative hazard
$$H(t) = \int_0^t h(s) \text{d}s.$$
Since
$$S'(t) = -f(t) = -h(t)S(t),$$
we obtain
$$S(t) = e^{-H(t)}, \quad F(t) = 1 - e^{-H(t)}, \quad f(t) = h(t)e^{-H(t)}.$$
Thus a hazard function determines the entire duration distribution.

**Example 13.1 — Exponential duration and constant hazard**
If
$$T \sim \text{Exp}(\lambda),$$
then
$$S(t) = e^{-\lambda t}, \quad h(t) = \lambda, \quad H(t) = \lambda t.$$
The constant hazard is equivalent to memorylessness.

**Weibull benchmark.** A flexible one-parameter departure from constant hazard uses
$$S(t) = \exp\left[ -\left( \frac{t}{\lambda} \right)^k \right], \quad t \geq 0,$$
which implies
$$h(t) = \frac{k}{\lambda} \left( \frac{t}{\lambda} \right)^{k-1}.$$
Hence
$$k > 1$$
gives increasing hazard,
$$k = 1$$
gives the exponential case, and
$$k < 1$$
gives decreasing hazard.

<!-- page 81 -->

### 13.2 Competing exponential clocks
Suppose
$$T_j \sim \text{Exp}(\lambda_j), \quad j = 1, \dots, J,$$
are independent waiting times for different events. Let
$$T = \min_j T_j.$$
Then
$$\mathbb{P}(T > t) = \prod_{j=1}^J \mathbb{P}(T_j > t) = \exp\left( -t \sum_{j=1}^J \lambda_j \right),$$
so
$$T \sim \text{Exp}\left( \sum_{j=1}^J \lambda_j \right).$$
Moreover,
$$\mathbb{P}(T_j = T) = \frac{\lambda_j}{\sum_{\ell=1}^J \lambda_\ell}.$$
Thus independent hazards add, and the probability that event $j$ occurs first equals its share of the total hazard.

**Example 13.2 — Job finding versus exit from the labor force**
Suppose an unemployed worker receives job offers at Poisson rate $\lambda$ and exits the labor force at rate $\delta$, with independent exponential clocks. The time until the unemployment spell ends is
$$T \sim \text{Exp}(\lambda + \delta),$$
so
$$\mathbb{E}[T] = \frac{1}{\lambda + \delta}.$$
Conditional on the spell ending, the probability that it ends in employment is
$$\frac{\lambda}{\lambda + \delta},$$
and the probability of labor-force exit is
$$\frac{\delta}{\lambda + \delta}.$$
This is the basic probability calculation behind continuous-time competing-risks models.

<!-- page 82 -->

### 13.3 The Poisson process
A counting process $\{N(t) : t \geq 0\}$ is a homogeneous Poisson process with rate $\lambda > 0$ if
$$N(0) = 0,$$
it has independent increments, and for $0 \leq s < t$,
$$N(t) - N(s) \sim \text{Pois}(\lambda(t - s)).$$
In particular,
$$N(t) \sim \text{Pois}(\lambda t), \quad \mathbb{E}[N(t)] = \text{Var}(N(t)) = \lambda t.$$
Let $T_1$ be the time of the first arrival. Then
$$\mathbb{P}(T_1 > t) = \mathbb{P}(N(t) = 0) = e^{-\lambda t},$$
so
$$T_1 \sim \text{Exp}(\lambda).$$
The independent-increments property implies that successive interarrival times are iid exponential random variables. Hence the time of the $r$-th arrival,
$$T_r = W_1 + \dots + W_r, \quad W_j \overset{\text{iid}}{\sim} \text{Exp}(\lambda),$$
has the gamma distribution
$$T_r \sim \text{Gamma}(r, \lambda).$$
This unifies the Poisson, exponential, and gamma families through one arrival-process model.

### 13.4 Superposition and thinning of Poisson processes
If $N_1(t)$ and $N_2(t)$ are independent Poisson processes with rates $\lambda_1$ and $\lambda_2$, then
$$N(t) = N_1(t) + N_2(t)$$
is a Poisson process with rate
$$\lambda_1 + \lambda_2.$$
This is the process-level analogue of the fact that independent Poisson random variables add.
Conversely, suppose each arrival of a Poisson process with rate $\lambda$ is independently classified as type 1 with probability $p$ and type 2 with probability $1 - p$. Then the type-specific counting processes are independent Poisson processes with rates
$$p\lambda \quad \text{and} \quad (1 - p)\lambda.$$

<!-- page 83 -->

This *thinning property* is useful whenever a common arrival stream is randomly divided into destinations, types, or outcomes.

### 13.5 Probability integral transform
**Proposition 13.3 — Probability integral transform**
If $X$ has a continuous CDF $F$, then
$$U = F(X) \sim \text{Unif}(0, 1).$$
Conversely, if $U \sim \text{Unif}(0, 1)$ and $F^{-1}$ is the generalized inverse CDF, then
$$X = F^{-1}(U)$$
has CDF $F$.

For the forward direction, if $0 < u < 1$ and $F$ is strictly increasing,
$$\mathbb{P}(F(X) \leq u) = \mathbb{P}(X \leq F^{-1}(u)) = u.$$
The generalized-inverse formulation extends the result beyond the strictly increasing case.

### 13.6 Inverse-transform simulation
The probability integral transform gives a general simulation recipe:
$$U \sim \text{Unif}(0, 1), \quad X = F^{-1}(U).$$

**Example 13.4 — Simulating an exponential random variable**
For $X \sim \text{Exp}(\lambda)$,
$$F(x) = 1 - e^{-\lambda x}, \quad x \geq 0.$$
Set $U = F(X)$ and solve for $X$:
$$U = 1 - e^{-\lambda X} \implies X = -\frac{1}{\lambda} \log(1 - U).$$
Since $1 - U \sim \text{Unif}(0, 1)$ as well, one usually writes
$$X = -\frac{1}{\lambda} \log U.$$

<!-- page 84 -->

### 13.7 Monte Carlo integration
Suppose the target quantity can be written as
$$\theta = \mathbb{E}[g(X)].$$
If we can simulate iid draws
$$X^{(1)}, \dots, X^{(M)} \overset{\text{iid}}{\sim} F,$$
then the Monte Carlo estimator is
$$\widehat{\theta}_M = \frac{1}{M} \sum_{m=1}^M g(X^{(m)}).$$
If $\mathbb{E}|g(X)| < \infty$, the LLN gives
$$\widehat{\theta}_M \xrightarrow{a.s.} \theta.$$
If additionally
$$\text{Var}(g(X)) = \tau^2 < \infty,$$
the CLT gives
$$\sqrt{M}(\widehat{\theta}_M - \theta) \xrightarrow{d} \mathcal{N}(0, \tau^2).$$
Therefore the Monte Carlo standard error is approximately
$$\frac{\tau}{\sqrt{M}},$$
and can be estimated by
$$\widehat{\text{se}}_{MC} = \frac{s_g}{\sqrt{M}},$$
where $s_g^2$ is the sample variance of the simulated values $g(X^{(m)})$.

**Remark 13.5 — Simulation error versus sampling error**
Monte Carlo error comes from using a finite number of simulated draws to approximate a mathematical expectation. Sampling error comes from observing a finite amount of real data. They are conceptually different. In a computational exercise both may be present, and increasing the number of simulations reduces Monte Carlo error without creating additional empirical information.

<!-- page 85 -->

### 13.8 Importance sampling: a change-of-measure identity

Sometimes $X \sim P$ is difficult to simulate efficiently, or the important region of the state space is rare under $P$. If $P$ has density $p$ and another distribution $Q$ has density $q$ with

$$p(x) > 0 \implies q(x) > 0,$$

then

$$\mathbb{E}_P[g(X)] = \int g(x)p(x) \, dx = \int g(x)\frac{p(x)}{q(x)}q(x) \, dx = \mathbb{E}_Q\left[g(X)\frac{p(X)}{q(X)}\right].$$

Thus one may simulate from $Q$ and reweight by the likelihood ratio

$$w(x) = \frac{p(x)}{q(x)}.$$

This is the basic probability identity behind importance sampling and many likelihood-ratio arguments.

## 14 References and Further Reading

This draft was revised by comparing the organization and emphasis of several probability texts and graduate lecture-note sequences. Different sources play different roles.

* Y. Hong, *Probability and Statistics for Economists*. Particularly useful for the basic economics-facing sequence: methods of counting; conditional probability, Bayes' theorem, and independence; random variables, CDFs, PMFs and PDFs; transformations; expectations, moments, quantiles, MGFs and characteristic functions; named distributions; and multivariate probability before sampling and limit theory.
* D. Bertsekas and J. Tsitsiklis, *Introduction to Probability*. Best used for the computational core: conditioning, random variables, expectation, transforms, and finite-state stochastic models.
* J. Blitzstein and J. Hwang, *Introduction to Probability*, together with Harvard Statistics 110 materials. Especially useful for elementary problem-solving, conditioning, named distributions, joint laws, transformations, order statistics, and conditional expectation.
* G. Grimmett and D. Stirzaker, *Probability and Random Processes*. A broad bridge between elementary probability and rigorous convergence/stochastic-process material; useful for the sequencing from events and random variables to generating functions, Markov chains, convergence, and martingales.
* Y. Polyanskiy, MIT 6.436J/15.085J *Fundamentals of Probability* lecture notes. A model for interleaving elementary probability with abstract integration, product measures, multivariate Gaussian theory, convergence, uniform integrability, Markov chains, and martingales.
* D. Williams, *Probability with Martingales*. A concise rigorous source for measurable random variables, integration, conditional expectation, convergence, characteristic functions, and martingale

85

<!-- page 86 -->

methods.
* A. Klenke, *Probability Theory: A Comprehensive Course*. The main reference for the measure-theoretic layer: measure and integration, independence, $L^p$ spaces, Radon–Nikodym, conditional expectation, convergence of probability measures, product spaces, characteristic functions, and the CLT.
* R. Durrett, *Probability: Theory and Examples*. A standard graduate reference for rigorous limit theory, independent sums, martingales, Markov chains, and further probabilistic techniques.
* P. Billingsley, *Probability and Measure*. Classical reference for measure-theoretic foundations, characteristic functions, and weak convergence.
* B. Hansen, *Probability and Statistics for Economists*. The economics-facing guide for random variables, parametric and multivariate distributions, sampling, LLN, CLT, and advanced asymptotic theory.
* A. W. van der Vaart, *Asymptotic Statistics*. A natural next reference once the probability foundations here are used for estimator asymptotics, delta methods, stochastic orders, and empirical-process arguments.

86