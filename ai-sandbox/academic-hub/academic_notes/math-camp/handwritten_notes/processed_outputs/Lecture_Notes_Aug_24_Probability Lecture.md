---
source_pdf: Lecture_Notes_Aug_24_Probability Lecture.pdf
folder_category: handwritten_notes
total_pages: 5
routing: gemini_accumulating
model: gemini-3.6-flash
tags: [foundational-mathematics, mathematical-foundations]
---

<!-- page 1 -->

Probability Lecture
Monday, August 24, 2026 9:05 AM

Probability $\mathbb{P} : \mathcal{F} \to [0,1]$
1) $\mathbb{P}(\Omega) = 1$
2) $\{A_i\}_{i=1}^\infty \quad A_i \cap A_j = \emptyset \quad i \neq j$
$\mathbb{P}\left(\bigcup_{i=1}^\infty A_i\right) = \sum_{i=1}^\infty \mathbb{P}(A_i)$  
$\text{for all events?}$  
$\text{or assuming independent?}$

---

Conditional Probability
Restrict total outcome space from $\Omega$ to $B$
$\mathbb{P}(B) > 0$,
$\mathbb{P}(A \mid B) = \frac{\mathbb{P}(A \cap B)}{\mathbb{P}(B)}$

$\Updownarrow$

$\mathbb{P}(A \mid B)\mathbb{P}(B) = \mathbb{P}(A \cap B)$

$\mathbb{P}(A \mid B^c)\mathbb{P}(B^c) = \mathbb{P}(A \cap B^c)$

$\mathbb{P}(A \cap B) + \mathbb{P}(A \cap B^c) = \mathbb{P}(A)$

$\mathbb{P}(A \mid B)\mathbb{P}(B) + \mathbb{P}(A \mid B^c)\mathbb{P}(B^c) = \mathbb{P}(A)$

Law of total probability

$\mathbb{P}(A) = \sum_{i=1}^n \mathbb{P}(A \mid B_i)\mathbb{P}(B_i)$

$\text{if } \{B_i\} \text{ pairwise disjoint}$
$\text{and } \bigcup_{i=1}^n B_i = \Omega$

$\text{for infinite prob space as } n \to \infty,$
$\text{switch to } \int$

Bayes Rule
$\mathbb{P}(B_k \mid A) \dots$

---

### 1. Probability Measure and Axioms
A probability space is a measure space $(\Omega, \mathcal{F}, \mathbb{P})$ with total mass 1:
* $\Omega$ is the sample space.
* $\mathcal{F} \subseteq 2^\Omega$ is a $\sigma$-algebra of measurable events.
* $\mathbb{P} : \mathcal{F} \to [0,1]$ is the probability measure satisfying the Kolmogorov axioms:

#### 1. Normalization:
$\mathbb{P}(\Omega) = 1$

#### 2. Countable Additivity ($\sigma$-additivity):
For any countable collection of pairwise disjoint events $\{A_i\}_{i=1}^\infty \subset \mathcal{F}$ where $A_i \cap A_j = \emptyset$ for all $i \neq j$:
$$\mathbb{P}\left(\bigcup_{i=1}^\infty A_i\right) = \sum_{i=1}^\infty \mathbb{P}(A_i)$$

> **Sidebar Query:** *For all events? Or assuming independence?*  
> **Clarification:** This holds for **pairwise disjoint (mutually exclusive) events**, not independent events. Mutual exclusivity ($A_i \cap A_j = \emptyset$) means the events cannot occur simultaneously. Independence ($\mathbb{P}(A \cap B) = \mathbb{P}(A)\mathbb{P}(B)$) is an orthogonal concept; if two non-trivial events are mutually exclusive ($\mathbb{P}(A \cap B) = 0$), they are fundamentally **dependent** because knowing one occurred guarantees the other did not.

---

### 2. Conditional Probability
Conditioning on an event $B \in \mathcal{F}$ with $\mathbb{P}(B) > 0$ restricts the effective sample space from $\Omega$ to $B$, rescaling the measure so that $\mathbb{P}(B \mid B) = 1$:

$$\mathbb{P}(A \mid B) = \frac{\mathbb{P}(A \cap B)}{\mathbb{P}(B)}$$

$$\Updownarrow$$

$$\mathbb{P}(A \cap B) = \mathbb{P}(A \mid B)\mathbb{P}(B)$$

Similarly, for the complement $B^c = \Omega \setminus B$:
$$\mathbb{P}(A \cap B^c) = \mathbb{P}(A \mid B^c)\mathbb{P}(B^c)$$

Since $A = (A \cap B) \cup (A \cap B^c)$ and $(A \cap B) \cap (A \cap B^c) = \emptyset$, additivity implies:
$$\mathbb{P}(A) = \mathbb{P}(A \cap B) + \mathbb{P}(A \cap B^c)$$
$$\mathbb{P}(A) = \mathbb{P}(A \mid B)\mathbb{P}(B) + \mathbb{P}(A \mid B^c)\mathbb{P}(B^c)$$

---

### 3. Law of Total Probability
Let $\{B_i\}_{i=1}^n$ form a measurable partition of $\Omega$, meaning $B_i \cap B_j = \emptyset$ for $i \neq j$, $\bigcup_{i=1}^n B_i = \Omega$, and $\mathbb{P}(B_i) > 0$ for all $i$. Then:

$$\mathbb{P}(A) = \sum_{i=1}^n \mathbb{P}(A \mid B_i)\mathbb{P}(B_i)$$

---

### 4. Bayes' Rule
For an arbitrary partition element $B_k$ and an event $A$ with $\mathbb{P}(A) > 0$:

$$\mathbb{P}(B_k \mid A) = \frac{\mathbb{P}(A \cap B_k)}{\mathbb{P}(A)}$$

$$\mathbb{P}(B_k \mid A) = \frac{\mathbb{P}(A \mid B_k)\mathbb{P}(B_k)}{\sum_{i=1}^n \mathbb{P}(A \mid B_i)\mathbb{P}(B_i)}$$

> **Sidebar Query:** *For infinite prob space as $n \to \infty$, switch to $\int$ rather than $\sum$?*  
> **Clarification:**  
> 1. **Countably Infinite Partitions:** If the partition is countably infinite ($\{B_i\}_{i=1}^\infty$ with $\bigcup_{i=1}^\infty B_i = \Omega$), the discrete summation still applies directly via monotone convergence / $\sigma$-additivity:  
> $$\mathbb{P}(A) = \sum_{i=1}^\infty \mathbb{P}(A \mid B_i)\mathbb{P}(B_i)$$  
> 2. **Continuous State Spaces (Uncountable):** When conditioning on a continuous random variable $\Theta$ with probability density function $f_\Theta(\theta)$, discrete conditioning $\mathbb{P}(\cdot \mid \Theta = \theta)$ fails because $\mathbb{P}(\Theta = \theta) = 0$. In this regime, the summation transitions to an integral using Radon-Nikodym derivatives / regular conditional probabilities:  
> $$\mathbb{P}(A) = \int_{\mathbb{R}} \mathbb{P}(A \mid \Theta = \theta)f_\Theta(\theta) \, d\theta$$  
> and the continuous Bayes' formula for the posterior density $f_{\Theta \mid X}(\theta \mid x)$ becomes:  
> $$f_{\Theta \mid X}(\theta \mid x) = \frac{f_{X \mid \Theta}(x \mid \theta)f_\Theta(\theta)}{\int_{\mathbb{R}} f_{X \mid \Theta}(x \mid u)f_\Theta(u) \, du}$$

From <https://gemini.google.com/app/f8cbc2c68511d345>

Aug_24_26 Page 1

<!-- page 2 -->

Bayes Rule

$$\mathbb{P}(B_i \mid A) = \frac{\mathbb{P}(A \cap B_i)}{\mathbb{P}(A)}$$

$$\mathbb{P}(B_i \mid A) = \frac{\mathbb{P}(A \mid B_i)\mathbb{P}(B_i)}{\sum_{i=1}^n \mathbb{P}(A \mid B_i)\mathbb{P}(B_i)}$$

$$\begin{color}{#1E90FF}{\text{prob space}}\end{color}$$
$$\begin{color}{#1E90FF}{\text{as } n \to \infty,}\end{color}$$
$$\begin{color}{#1E90FF}{\text{switch to}}\{color}$$
$$\begin{color}{#1E90FF}{\int \text{ rather than } \sum}\end{color}$$

---

Independence

if $A$ & $B$ independent events

$$\mathbb{P}(A \cap B) = \mathbb{P}(A)\mathbb{P}(B)$$

$$\frac{\mathbb{P}(A \cap B)}{\mathbb{P}(B)} = \mathbb{P}(A) = \mathbb{P}(A \mid B)$$

$B$ gives no new info on $A$

$$A^c \cap B^c$$
$$\text{is complem.}$$
$$\text{to } A \cup B$$

```
   _____      _____
  /     \    /     \
 /   A   \  /   B   \
 \_______/  \_______/
```

---

Random Variables

measurable Functions $\Omega \to \mathbb{R}$

takes event $A$ & assigns a value

$$\begin{color}{#1E90FF}{\text{Like}}\end{color}$$
$$\begin{color}{#1E90FF}{\text{counting}}\end{color}$$
$$\begin{color}{#1E90FF}{\text{number}}\end{color}$$
$$\begin{color}{#1E90FF}{\text{of heads}}\end{color}$$
$$\begin{color}{#1E90FF}{\text{in coin tosses?}}\end{color}$$
$$\begin{color}{#1E90FF}{\text{or combined}}\end{color}$$
$$\begin{color}{#1E90FF}{\text{value of dice?}}\end{color}$$

```
   _____                
  /     \               
 (   w   ) -----> • ------>
  \_____/    X(w)   R
    Ω
```

---

CDF

$$F_X(x) = \mathbb{P}(X \le x)$$

non-decreasing
right continuous

$$F_X(x) \to 0 \quad \text{as } x \to -\infty$$

$$F_X(x) \to 1 \quad \text{as } x \to \infty$$

---

Discrete Random Variable

$f_X \quad X \text{ taking values in } \{x_i\}_{i=1}^N$

$$F_X(x) = \mathbb{P}(X \le x) = \sum_{x_i \le x} \mathbb{P}(X = x_i)$$

Continuous Random Variable

---

### 1. Independence of Events
Two events $A, B \in \mathcal{F}$ are statistically independent if and only if:

$$\mathbb{P}(A \cap B) = \mathbb{P}(A)\mathbb{P}(B)$$

Assuming $\mathbb{P}(B) > 0$, this definition is equivalent to:

$$\frac{\mathbb{P}(A \cap B)}{\mathbb{P}(B)} = \mathbb{P}(A) \iff \mathbb{P}(A \mid B) = \mathbb{P}(A)$$

Conditioning on $B$ yields no informational gain regarding the realization of $A$.

> **Sidebar Annotation Note:** *"$A^c \cap B^c$ is complement to $A \cup B$" and the Venn diagram with disjoint circles.*  
> **Clarification:** By De Morgan's Laws, $(A \cup B)^c = A^c \cap B^c$ is true. However, the accompanying sketch of two non-overlapping circles depicts **disjoint/mutually exclusive** sets ($A \cap B = \emptyset$), not independent sets. As established, if $\mathbb{P}(A) > 0$ and $\mathbb{P}(B) > 0$, disjoint events can **never** be independent because $\mathbb{P}(A \cap B) = 0 \neq \mathbb{P}(A)\mathbb{P}(B)$.

---

### 2. Random Variables
Formally, a random variable $X$ defined on a probability space $(\Omega, \mathcal{F}, \mathbb{P})$ is a **measurable function**:

$$X : \Omega \to \mathbb{R}$$

such that the preimage of any Borel set $B \in \mathcal{B}(\mathbb{R})$ is $\mathcal{F}$-measurable:

$$X^{-1}(B) = \{\omega \in \Omega : X(\omega) \in B\} \in \mathcal{F}$$

> **Sidebar Query:** *Like counting number of heads in coin tosses? Or combined value of dice?*  
> **Clarification:** Yes, precisely:  
> * For $n$ coin tosses, the sample space is $\Omega = \{H, T\}^n$, and $X(\omega) = \sum_{i=1}^n \mathbf{1}_{\{\omega_i = H\}}$ maps each sequence $\omega$ to the integer count of heads in $\{0, 1, \dots, n\}$.  
> * For rolling two dice, $\Omega = \{(i,j) : 1 \le i, j \le 6\}$, and $X(i,j) = i + j$ maps each pair to an integer sum in $\{2, \dots, 12\}$.

---

### 3. Cumulative Distribution Function (CDF)
The Cumulative Distribution Function $F_X : \mathbb{R} \to [0,1]$ completely characterizes the induced probability measure of $X$:

$$F_X(x) = \mathbb{P}(X \le x) = \mathbb{P}(\{\omega \in \Omega : X(\omega) \le x\})$$

#### Fundamental Properties:
* **Monotonicity:** $F_X(x_1) \le F_X(x_2)$ whenever $x_1 \le x_2$.
* **Right-continuity:** $\lim_{h \to 0^+} F_X(x + h) = F_X(x)$ for all $x \in \mathbb{R}$.
* **Asymptotic Limits:**
$$\lim_{x \to -\infty} F_X(x) = 0 \quad \text{and} \quad \lim_{x \to \infty} F_X(x) = 1$$

---

### 4. Discrete and Continuous Random Variables

#### Discrete Random Variables:
If the support of $X$ is a countable or finite set $\{x_i\}_{i=1}^N \subset \mathbb{R}$, the CDF is a step function:

$$F_X(x) = \mathbb{P}(X \le x) = \sum_{x_i \le x} \mathbb{P}(X = x_i)$$

#### Continuous Random Variables:
If $F_X(x)$ is absolutely continuous with respect to the Lebesgue measure, there exists a non-negative, integrable probability density function (PDF) $f_X : \mathbb{R} \to [0,\infty)$ such that:

$$F_X(x) = \mathbb{P}(X \le x) = \int_{-\infty}^x f_X(t) \, dt$$

By the Fundamental Theorem of Calculus (almost everywhere):

Aug_24_26 Page 2

<!-- page 3 -->

$$\begin{color}{#1E90FF}{x_i \le x}\end{color}$$
$\text{Continuous Random Variable}$
$$F_X(x) = \mathbb{P}(X \le x) = \int_{-\infty}^x f_X(t) \, dt$$
$$f_X'(x) = f_X(t)$$
$\text{Joint CDF } (x,y)$
$$F_{X,Y}(x,y) = \mathbb{P}(X \le x, Y \le y)$$
$$\text{If } F_{X,Y}(x,y) = \int_{[-\infty,x] \times [-\infty,y]} f_{X,Y}(x,y) \, dx \, dy$$
$$\text{then marginal density}$$
$$f_X(x) = \int f_{X,Y} \, dy$$
$$f_Y(y) = \int f_{X,Y} \, dx$$
$\text{Independence of Random Variables}$
$$\mathbb{P}(X \in A, Y \in B) = \mathbb{P}(X \in A)\mathbb{P}(Y \in B)$$

---

$\text{Expectation of Random Variable}$
$\text{Discrete}$
$$\mathbb{E}[X] = \sum_x x \mathbb{P}[X = x] = \sum_x x P_X(x)$$
$\text{Continuous}$
$$\mathbb{E}[X] = \int x f_X(x) \, dx$$

$$\mathbb{E}[g(x)] = \mathbb{E} g(x) P_X(x)$$
$$\text{or } = \int g(x) f_X(x) \, dx$$

$$\text{Variance is special case of } g(x)$$
$$\mathbb{E}[(X - \mathbb{E}[X])^2] \quad \begin{array}{l} \text{Second centered} \\ \text{moment } \dots \end{array}$$

---

$$F_X(x) = \mathbb{P}(X \le x) = \int_{-\infty}^x f_X(t) \, dt$$
By the Fundamental Theorem of Calculus (almost everywhere):

$$f_X(x) = F_X'(x) = \frac{d}{dx} F_X(x)$$

### 5. Joint Distributions and Marginal Densities
For a random vector $(X, Y) \in \mathbb{R}^2$, the **Joint CDF** is:

$$F_{X,Y}(x,y) = \mathbb{P}(X \le x, Y \le y)$$

If $(X, Y)$ is jointly continuous with joint density $f_{X,Y}(x,y)$:

$$F_{X,Y}(x,y) = \iint_{(-\infty,x] \times (-\infty,y]} f_{X,Y}(u, v) \, du \, dv = \int_{-\infty}^x \int_{-\infty}^y f_{X,Y}(u, v) \, dv \, du$$

#### Marginal Densities:
Integrating out the nuisance variable gives the marginal densities:

$$f_X(x) = \int_{-\infty}^\infty f_{X,Y}(x, y) \, dy$$

$$f_Y(y) = \int_{-\infty}^\infty f_{X,Y}(x, y) \, dx$$

### 6. Independence of Random Variables
Two random variables $X$ and $Y$ are independent if and only if their generated $\sigma$-algebras $\sigma(X)$ and $\sigma(Y)$ are independent:

$$\mathbb{P}(X \in A, Y \in B) = \mathbb{P}(X \in A)\mathbb{P}(Y \in B) \quad \forall A, B \in \mathcal{B}(\mathbb{R})$$

Equivalently, in terms of CDFs and PDFs:

$$F_{X,Y}(x,y) = F_X(x)F_Y(y) \quad \forall x, y \in \mathbb{R}$$

$$f_{X,Y}(x,y) = f_X(x)f_Y(y) \quad \text{a.e.}$$

From <https://gemini.google.com/app/f8cbc2c68511d345>

---

### 1. Expectation of a Random Variable
The mathematical expectation (first raw moment) represents the probability-weighted average of all possible realizations of a random variable $X$:

* **Discrete Case:**
$$\mathbb{E}[X] = \sum_x x \, \mathbb{P}(X = x) = \sum_x x \, p_X(x)$$

* **Continuous Case:**
$$\mathbb{E}[X] = \int_{-\infty}^\infty x \, f_X(x) \, dx$$

#### Law of the Unconscious Statistician (LOTUS):
For any measurable function $g : \mathbb{R} \to \mathbb{R}$:

$$\mathbb{E}[g(X)] = \sum_x g(x) \, p_X(x) \quad \text{or} \quad \mathbb{E}[g(X)] = \int_{-\infty}^\infty g(x) f_X(x) \, dx$$

---

### 2. Variance and Covariance

#### Variance:
Variance measures the expected squared deviation from the mean, defined as the special case $g(X) = (X - \mathbb{E}[X])^2$:

$$\text{Var}(X) = \mathbb{E}[(X - \mathbb{E}[X])^2] = \mathbb{E}[X^2] - (\mathbb{E}[X])^2$$

> **Sidebar Annotation:** *Second centered moment from MGF.*  
> **Deeper Context & Derivation:** The Moment-Generating Function (MGF) is defined as $M_X(t) = \mathbb{E}[e^{tX}]$.

Aug_24_26 Page 3

<!-- page 4 -->

$$E[(X - E[X])^2]$$
$$= E[X^2] - (E[X])^2$$

Covariance
$$E[(X - E[X])(Y - E[Y])]$$
$$\text{Cov}(X,Y) = E[XY] - E[X]E[Y]$$

$$\text{If } X+Y \text{ independent}$$
$$\text{Var}(X+Y) = \text{Var}(X) + \text{Var}(Y)$$

$$\text{if not independent}$$
$$\text{Var}(X+Y) = \text{Var}(X) + \text{Var}(Y)$$
$$+ 2 \text{ Cov}(X,Y)$$

---

Conditional Expectation
$$E[X \mid Y=y] = \sum_x x \mathbb{P}[X=x \mid Y=y]$$
$$= \int x f_{X \mid Y}(x \mid Y=y) \, dx$$

$$\text{by averaging at } x, \text{ cnd exp}$$
$$E[X \mid Y=y] \text{ is function of}$$
$$y \text{ being the realization at } Y$$

$$\text{once we take conditional,}$$
$$\text{variability is driven by } y$$

$$E[X \mid Y] \text{ is random variable}$$
$$\text{by law of iterated expectations,}$$

$$E[E[X \mid Y]] = E[X]$$

---

**Sidebar Annotation:** *Second centered moment from MGF.*  
**Deeper Context & Derivation:** The Moment-Generating Function (MGF) is defined as $M_X(t) = \mathbb{E}[e^{tX}]$.
* The raw moments are obtained by differentiating evaluated at $t = 0$:
$$\mathbb{E}[X^k] = \left. \frac{d^k M_X(t)}{dt^k} \right|_{t=0}$$
* The variance is the **second central moment** $\mu_2 = \mathbb{E}[(X - \mu)^2]$. It can be extracted directly via the **Cumulant Generating Function** $K_X(t) = \ln M_X(t)$:
$$\text{Var}(X) = K_X''(0) = \left. \frac{d^2 \ln M_X(t)}{dt^2} \right|_{t=0}$$
$$= \frac{M_X''(0)M_X(0) - [M_X'(0)]^2}{[M_X(0)]^2} = \mathbb{E}[X^2] - (\mathbb{E}[X])^2$$

**Covariance:**  
Covariance measures the joint linear association between two random variables:
$$\text{Cov}(X,Y) = \mathbb{E}[(X - \mathbb{E}[X])(Y - \mathbb{E}[Y])] = \mathbb{E}[XY] - \mathbb{E}[X]\mathbb{E}[Y]$$

**Variance of Sums:**
* **General Case:**
$$\text{Var}(X + Y) = \text{Var}(X) + \text{Var}(Y) + 2\text{Cov}(X,Y)$$
* **If $X$ and $Y$ are independent** (or simply uncorrelated, $\text{Cov}(X,Y) = 0$):
$$\text{Var}(X + Y) = \text{Var}(X) + \text{Var}(Y)$$

### 3. Conditional Expectation
For a given realization $Y = y$, the conditional expectation $\mathbb{E}[X \mid Y = y]$ is a **deterministic scalar constant**:
* **Discrete Case:**
$$\mathbb{E}[X \mid Y = y] = \sum_x x \, \mathbb{P}(X = x \mid Y = y)$$
* **Continuous Case:**
$$\mathbb{E}[X \mid Y = y] = \int_{-\infty}^\infty x \, f_{X \mid Y}(x \mid y) \, dx$$
where $f_{X \mid Y}(x \mid y) = \frac{f_{X,Y}(x,y)}{f_Y(y)}$.

By integrating (or summing) out $x$, $\mathbb{E}[X \mid Y = y]$ becomes a deterministic function of the fixed value $y$, written as $h(y)$.

### 4. Conditional Expectation as a Random Variable & Tower Property
When conditioning on the random variable $Y$ rather than a specific realized value $y$, the object:
$$\mathbb{E}[X \mid Y] = h(Y)$$
is itself a **random variable** measurable with respect to the $\sigma$-algebra $\sigma(Y)$. Its randomness is completely driven by $Y$.

**Law of Iterated Expectations (Tower Property):**
$$\mathbb{E}[\mathbb{E}[X \mid Y]] = \mathbb{E}[X]$$

#### Deeper Context & Measure-Theoretic View:
1. **Underlying Mechanism:** The tower property is the expectation-level equivalent of the Law of Total Probability:
$$\mathbb{E}[\mathbb{E}[X \mid Y]] = \int_{-\infty}^\infty \left( \int_{-\infty}^\infty x f_{X \mid Y}(x \mid y) \, dx \right) f_Y(y) \, dy$$
$$= \int_{-\infty}^\infty x \left( \int_{-\infty}^\infty f_{X,Y}(x,y) \, dy \right) dx = \int_{-\infty}^\infty x f_X(x) \, dx = \mathbb{E}[X]$$
2. **General Conditioning:** For any sub-$\sigma$-algebra $\mathcal{G} \subseteq \mathcal{F}$,

Aug_24_26 Page 4

<!-- page 5 -->

$$\mathbb{E}[\mathbb{E}[X \mid Y]] = \mathbb{E}[X]$$

Towering property  
uses law of total probability

---

$$= \int_{-\infty}^\infty x \left( \int_{-\infty}^\infty f_{X,Y}(x,y) \, dy \right) dx = \int_{-\infty}^\infty x f_X(x) \, dx = \mathbb{E}[X]$$

**2. General Conditioning:** For any sub-$\sigma$-algebra $\mathcal{G} \subseteq \mathcal{F}$, $\mathbb{E}[X \mid \mathcal{G}]$ is defined as the unique $\mathcal{G}$-measurable random variable satisfying:

$$\int_G \mathbb{E}[X \mid \mathcal{G}] \, d\mathbb{P} = \int_G X \, d\mathbb{P} \quad \forall G \in \mathcal{G}$$

Setting $G = \Omega$ yields $\mathbb{E}[\mathbb{E}[X \mid \mathcal{G}]] = \mathbb{E}[X]$.

**3. Tower Hierarchy:** If $\mathcal{H} \subseteq \mathcal{G} \subseteq \mathcal{F}$, coarser information dominates:

$$\mathbb{E}[\mathbb{E}[X \mid \mathcal{G}] \mid \mathcal{H}] = \mathbb{E}[X \mid \mathcal{H}]$$

From <https://gemini.google.com/app/f8cbc2c68511d345>