---
cssclasses: cheat-sheet-compact
---

## I. Linear Algebra

### Core Properties & Subspaces
*   **Linear Independence:** $v_1,\dots,v_k$ indep. iff $c_1v_1+\cdots+c_kv_k=0\Rightarrow c_1=\cdots=c_k=0$ (no nontrivial combo $=0$).
*   **Invertibility Equivalence:** $A$ ($n\times n$) invertible $\iff \det A\neq0 \iff Ax=0$ has only trivial sol. $\iff Ax=b$ unique $\forall b \iff$ cols indep. $\iff$ cols span $\mathbb{R}^n \iff$ full rank $\iff 0$ not an eigenvalue.
*   **Determinant ($3 \times 3$):** $\det(A) = a_{11}(a_{22}a_{33} - a_{23}a_{32}) - a_{12}(a_{21}a_{33} - a_{23}a_{31}) + a_{13}(a_{21}a_{32} - a_{22}a_{31})$.
*   **Det. Properties:** $\det(AB)=\det A\det B$; $\det A^\top=\det A$; $\det A^{-1}=1/\det A$; $\det(cA)=c^n\det A$. Row swap flips sign; scaling a row by $c$ scales $\det$ by $c$; row addition: no change. Triangular: $\det=\prod$ diag.
*   **Cramer's Rule / Inverse:** $x_i=\det(A_i)/\det(A)$, $A_i=A$ w/ col $i\to b$. $2\times2$: $A^{-1}=\frac1{\det A}\begin{pmatrix}d&-b\\-c&a\end{pmatrix}$.
*   **Transpose/Inverse of Product:** $(AB)^\top=B^\top A^\top$; $(AB)^{-1}=B^{-1}A^{-1}$ (order reverses in both).
*   **Inverse ($3\times3$):** $A^{-1}=\frac{1}{\det A}\text{adj}(A)$ ($\text{adj}=C^\top$, cofactors). For $A=\begin{pmatrix}a&b&c\\d&e&f\\g&h&i\end{pmatrix}$: $A^{-1}=\frac1{\det A}\begin{pmatrix}ei-fh&ch-bi&bf-ce\\fg-di&ai-cg&cd-af\\dh-eg&bg-ah&ae-bd\end{pmatrix}$.
*   **Solution Parameterization:** $Ax=b$ consistent $\Rightarrow x=x_p+x_h$ ($x_p$ particular, $x_h\in\text{Null}(A)$, free vars).
*   **Rank-Nullity:** $\dim(V)=\dim(\text{Im }T)+\dim(\text{Ker }T)$, $T:V\to W$.
*   **Subspace Bases:** Col space basis = pivot columns of $A$ (original, not RREF). Null space basis: solve $Ax=0$, parameterize free vars.
*   **Surjective/Injective Maps:** $T:V\to W$ surjective iff $\text{Im }T=W$; injective iff $\text{Ker }T=\{0\}$. $\dim V<\infty$, $T:V\to V$: injective $\iff$ surjective $\iff$ invertible.
*   **Rank 1 Matrices:** $A\neq0$ ($m\times n$) has rank 1 iff $A=cd^\top$, $c\in\mathbb{R}^m,d\in\mathbb{R}^n$.
*   **Direct Sum:** $V=U\oplus W$ iff $V=U+W$ & $U\cap W=\{0\}$ (unique decomp. $v=u+w$); $\dim V=\dim U+\dim W$.

### Eigendecomposition & Orthogonality
*   **Eigenvalues & Eigenvectors:** $Av=\lambda v$ ($v\neq0$). $\lambda$: roots of $\det(A-\lambda I)=0$. $\text{tr}(A)=\sum\lambda_i$, $\det(A)=\prod\lambda_i$. $2\times2$ shortcut: $\lambda^2-\text{tr}(A)\lambda+\det(A)=0$.
*   **Alg. vs. Geo. Multiplicity:** Alg. mult. = mult. as root of char. poly; geo. mult. = $\dim\text{Ker}(A-\lambda I)$. $1\le$ geo $\le$ alg. Diagonalizable iff geo=alg $\forall\lambda$ (else e.g. Jordan blocks).
*   **Diagonalization:** $A=XDX^{-1}$: $X$ = indep. eigenvectors, $D$ = eigenvalues (diag).
*   **Matrix Powers:** $A^k=XD^kX^{-1}$. All $|\lambda_i|<1\Rightarrow D^k\to0\Rightarrow A^k\to0$.
*   **Spectral Theorem:** $A=A^\top\Rightarrow A=Q\Lambda Q^\top$ ($Q^\top Q=I$). Eigenvalues real; eigenvectors of distinct $\lambda$'s orthogonal.
*   **Orthogonal Matrices:** $Q^\top Q=I \iff Q^{-1}=Q^\top$. $\det Q=\pm1$; preserves norms/inner products.
*   **Quadratic Forms & Definiteness:** $Q(x)=x^\top Ax$ ($A$ symmetric). PD: $>0\ \forall x\neq0$; ND: $<0$; PSD/NSD: $\ge0/\le0$; indefinite: both signs. (Tests: see Optimization.)
*   **Rayleigh Quotient:** $A$ symmetric: $\max_{\|u\|=1}u^\top Au=\lambda_{\max}$, $\min_{\|u\|=1}u^\top Au=\lambda_{\min}$; more gen. $\lambda_{\min}\|x\|^2\le x^\top Ax\le\lambda_{\max}\|x\|^2$.
*   **Similarity Transformations:** $S$ invertible $\Rightarrow T,S^{-1}TS$ same eigenvalues; $Tv=\lambda v\Rightarrow S^{-1}TS(S^{-1}v)=\lambda(S^{-1}v)$.
*   **Gram-Schmidt:** $e_1=v_1/\|v_1\|$; $u_k=v_k-\sum_{j=1}^{k-1}\langle v_k,e_j\rangle e_j$, $e_k=u_k/\|u_k\|$.
*   **Idempotent Matrices:** $P^2=P$. Eigenvalues $\in\{0,1\}$ only (since $\lambda^2=\lambda$). Projection $P=X(X^\top X)^{-1}X^\top$ ($X$: $n\times k$), $\text{tr}(P)=k$; residual $M=I_n-P$, $\text{tr}(M)=n-k$.
*   **Norms & Inner Products:** $\langle u,v\rangle=0\iff\|u\|\le\|u+av\|\ \forall a$. Norms: $\|x\|_2=(\sum x_i^2)^{1/2}$, $\|x\|_\infty=\max|x_i|$, $\|x\|_1=\sum|x_i|$. Reverse triangle ineq.: $\big|\|u\|-\|v\|\big|\le\|u-v\|$.
*   **Involutions:** $T^2=I$ ($T$ = own inverse). Eigenvalues: $\lambda=\pm1$ only.
*   **Nilpotency:** $A^k=0$ some $k$. All eigenvalues $=0$; never invertible, never diagonalizable (unless $A=0$). Neumann: $(I-N)^{-1}=I+N+\cdots+N^{k-1}$; $(I+N)^{-1}=I-N+\cdots+(-1)^{k-1}N^{k-1}$.
*   **Invariant Subspace:** $W\subseteq V$ invariant under $T$ iff $T(W)\subseteq W$. E.g. eigenspaces $\text{Ker}(A-\lambda I)$.

## II. Real Analysis

### Topology & Metric Spaces

#### Sets, Compactness & Boundedness
*   **Set Operations & De Morgan's Laws:** Commutative: $A\cup B=B\cup A$, $A\cap B=B\cap A$. Distributive: $A\cap(B\cup C)=(A\cap B)\cup(A\cap C)$, $A\cup(B\cap C)=(A\cup B)\cap(A\cup C)$. **De Morgan:** $(A\cup B)^c=A^c\cap B^c$, $(A\cap B)^c=A^c\cup B^c$; gen. (incl. infinite): $\left(\bigcup_i A_i\right)^c=\bigcap_i A_i^c$, $\left(\bigcap_i A_i\right)^c=\bigcup_i A_i^c$.
*   **Sup/Inf & Completeness:** $\sup S$=least upper bd., $\inf S$=greatest lower bd. Completeness: $S\subseteq\mathbb{R}$ bdd above $\Rightarrow \sup S$ exists (distinguishes $\mathbb{R}$ from $\mathbb{Q}$) $\Rightarrow$ Archimedean: $\forall x\ \exists n\in\mathbb{N}, n>x$.
*   **Bolzano-Weierstrass:** Bounded seq. in $\mathbb{R}^n \Rightarrow$ convergent subsequence exists (via completeness + nested-interval bisection).
*   **Open and Closed Sets:** $U$ open: $\forall p\in U\ \exists r>0, B_r(p)\subseteq U$. Closed: complement open (= contains all limit pts). Cont. preimages preserve open/closed.
*   **Closure of a Set:** $\overline S=S\cup\{\text{limit pts.}\}$ = smallest closed set $\supseteq S$. $S$ closed iff $S=\overline S$.
*   **Open Balls:** $B_\epsilon(x)=\{y\in\mathbb{R}^n:\|y-x\|<\epsilon\}$. $U$ open iff $\forall x\in U\ \exists\epsilon, B_\epsilon(x)\subseteq U$.
*   **Compactness (Heine-Borel):** In $\mathbb{R}^n$: compact $\iff$ closed+bounded $\iff$ every open cover has finite subcover $\iff$ every seq. has convergent subseq.
*   **Nested Compact Sets:** $K_1\supseteq K_2\supseteq\cdots$ non-empty compact $\Rightarrow \bigcap K_k\neq\varnothing$.
*   **Bounded Set:** $S$ bounded iff $\sup_{x,y\in S}d(x,y)<\infty$ iff $S\subseteq B_M(x_0)$ some $x_0,M$.
*   **Limit Point:** $a$ limit pt. of $S$: every $B_r(a)$ contains infinitely many pts of $S$. Closed sets contain all their limit pts.
*   **Separation of Hyperplanes:** Disjoint convex $C_1,C_2\subseteq\mathbb{R}^n$ (one compact, other closed) $\Rightarrow \exists p\neq0,c$: $p^\top x\le c\le p^\top y\ \forall x\in C_1,y\in C_2$.

#### Convergence, Contraction & Fixed Points
*   **Convergence & Cauchy:** $x_n\to L$: $\forall\epsilon\ \exists N,\forall n\ge N,\ d(x_n,L)<\epsilon$. Cauchy: $d(x_n,x_m)<\epsilon$ for large $n,m$.
*   **Contraction Maps:** $d(Tx,Ty)\le k\,d(x,y)$, $k\in[0,1)$.
*   **Banach Fixed Point:** $(X,d)$ complete, $T$ contraction $\Rightarrow$ unique fixed pt $x^*=Tx^*$; $x_{n+1}=Tx_n\to x^*$ from any $x_0$ (e.g. Bellman eqns).

#### Continuity & Functions
*   **Continuous ($\epsilon$-$\delta$):** $f$ cont. at $c$: $\forall\epsilon\ \exists\delta,\ d_X(x,c)<\delta\Rightarrow d_Y(f(x),f(c))<\epsilon$.
*   **Sequential Continuity:** $f$ cont. at $c$ iff $\forall x_n\to c,\ f(x_n)\to f(c)$ (equiv. to $\epsilon$-$\delta$; easiest way to disprove continuity).
*   **Uniform Continuity:** $\delta$ depends only on $\epsilon$, not the point. Cont. on compact domain $\Rightarrow$ unif. cont. (not conversely; e.g. $x^2$ on $\mathbb{R}$).
*   **Topological Continuity:** $f$ cont. iff $f^{-1}(U)$ open $\forall$ open $U$.
*   **IVT:** $f$ cont. on $[a,b]$, $y$ between $f(a),f(b)\Rightarrow\exists c\in[a,b]$, $f(c)=y$.
*   **Extreme Value Theorem:** $f$ cont., $K$ non-empty compact $\Rightarrow f$ attains max & min on $K$ (existence argument for optima).
*   **Well-Defined Function:** Each domain elt. maps to a unique codomain elt. Cont. transforms (e.g. $|\cdot|$) preserve well-definedness.
*   **Surjective/Injective Functions:** $f:X\to Y$: **injective** iff $f(x_1)=f(x_2)\Rightarrow x_1=x_2$; **surjective** iff $f(X)=Y$; **bijective** iff both (inverse $f^{-1}$ exists). Composition preserves injectivity/surjectivity.

#### Metric Spaces, Norms & Inner Products
*   **Metric Space:** $(X,d)$: $d:X\times X\to\mathbb{R}_+$ s.t. $d(x,y)=0\iff x=y$; symmetric; $d(x,z)\le d(x,y)+d(y,z)$.
*   **Discrete Metric:** $\rho(x,y)=1$ if $x\neq y$, else $0$. All subsets clopen & bounded; infinite sets not compact; seqs. converge only if eventually constant.
*   **Norms, Inner Products, Distance:** Inner product: symmetric, bilinear, pos-def. Induces norm $\|x\|=\sqrt{\langle x,x\rangle}$; **Cauchy-Schwarz**: $|\langle x,y\rangle|\le\|x\|\|y\|\Rightarrow$ triangle ineq. Norm induces metric $d(x,y)=\|x-y\|$ (not conversely).
*   **Norm Equivalence:** All norms on $\mathbb{R}^n$ equiv.: $\exists c,C>0$, $c\|x\|_a\le\|x\|_b\le C\|x\|_a\ \forall x$ (e.g. $\|x\|_\infty\le\|x\|_2\le\sqrt n\|x\|_\infty$). Conv./open/compact don't depend on norm choice.

### Calculus & Differentiation
*   **Derivative Definition:** $f(x+h)=f(x)+Df(x)h+r(h)$, $\lim_{h\to0}\|r(h)\|/\|h\|=0$. Cont. partials in nbhd. $\Rightarrow$ diff'ble.
*   **Basic Derivative Formulae:** Product: $(fg)'=f'g+fg'$. Quotient: $(f/g)'=\frac{gf'-fg'}{g^2}$. Chain: $\frac{d}{dx}f(g(x))=f'(g(x))g'(x)$. $\ln'(x)=1/x$, $(e^x)'=e^x$. $\sin'=\cos$, $\cos'=-\sin$, $\tan'=\sec^2$.
*   **Taylor Approximation (Multivariate):** $f(x+h)=f(x)+\nabla f(x)^\top h+\frac12h^\top H_f(x)h+o(\|h\|^2)$ as $h\to0$. **Drop remainder:** $f(x+h)\approx f(x)+\nabla f(x)^\top h+\frac12h^\top H_f(x)h$ — safe when $\|h\|$ small (local approx.; error vanishes faster than $\|h\|^2$), not for large $h$.
*   **Rolle's Theorem:** $f$ cont. $[a,b]$, diff. $(a,b)$, $f(a)=f(b)\Rightarrow\exists c\in(a,b)$, $f'(c)=0$.
*   **Scalar Mean Value Theorem:** $f(b)-f(a)=Df(c)(b-a)$, $c$ on segment $[a,b]$.
*   **L'Hôpital:** $\frac00$ or $\frac{\infty}{\infty}\Rightarrow\lim f/g=\lim f'/g'$ (if latter exists).
*   **Convex Sets & Concave/Convex Functions:** $C$ convex: $tx+(1-t)y\in C\ \forall t\in[0,1]$. $f$ **concave**: $f(tx+(1-t)y)\ge tf(x)+(1-t)f(y)$ (convex: reverse). Twice-diff.: concave iff $H_f$ NSD (convex iff PSD); strict definiteness $\Rightarrow$ strict (not $\Leftarrow$).
*   **Integrals:** **FTC**: $\int_a^b f\,dx=F(b)-F(a)$ ($F'=f$). **By parts**: $\int u\,dv=uv-\int v\,du$. **Sub**: $\int f(g(x))g'(x)dx=\int f(u)du$. **Leibniz**: $\frac{d}{dt}\int_{a(t)}^{b(t)}f(x,t)dx=f(b(t),t)b'(t)-f(a(t),t)a'(t)+\int_{a(t)}^{b(t)}f_t\,dx$. **Fubini**: $\iint_R f\,dA=\int_a^b\int_c^d f\,dy\,dx$. **Improper**: $\int_a^\infty f\,dx=\lim_{b\to\infty}\int_a^b f\,dx$.

## Multivariable Differential Calculus

*   **Partial and Total Derivatives:** $Df(x)$: linear op. s.t. $f(x+h)=f(x)+Df(x)h+r(h)$, $\|r(h)\|/\|h\|\to0$. Cont. partials in nbhd. $\Rightarrow$ diff'ble; $Df(x)=$ Jacobian.
*   **Multivariate Derivative Rules:** Chain rule: $D(h\circ g\circ f)=Dh\cdot Dg\cdot Df$. Directional deriv.: $D_vf(x)=\nabla f(x)^\top v$. $\nabla(fg)=g\nabla f+f\nabla g$. $\nabla(x^\top Ax)=(A+A^\top)x$ ($=2Ax$ if symmetric). $\nabla f\perp$ level set $\{f=c\}$; points toward steepest increase.
*   **Multivariate Mean Value Theorem:** Scalar $f$: $f(b)-f(a)=\nabla f(c)^\top(b-a)$, $c\in[a,b]$. Vector-valued ($m>1$): no exact $c$; only $\|f(b)-f(a)\|\le\sup_{[a,b]}\|Df\|\,\|b-a\|$.
*   **Implicit Function Theorem:** $F(x,y)=0$, $F_y\neq0 \Rightarrow$ locally $y=g(x)$, $g_x=-F_x/F_y$. $F(x,y,z)=0$, $F_z\neq0 \Rightarrow z=g(x,y)$, $g_x=-F_x/F_z$, $g_y=-F_y/F_z$.
*   **Implicit Fn. Thm. — Steps:** (1) Check $F(x_0,y_0)=0$. (2) Compute $D_yF$ (Jacobian in endog. vars $y$), verify $\det D_yF(x_0,y_0)\neq0$ (scalar: $F_y\neq0$). (3) Conclude: unique $C^1$ $y=g(x)$ near $x_0$, $g(x_0)=y_0$, $F(x,g(x))\equiv0$. (4) Chain rule on identity: $D_xF+D_yF\,Dg=0\Rightarrow Dg=-[D_yF]^{-1}D_xF$ (scalar: $g_x=-F_x/F_y$). (5) Plug in $(x_0,y_0)$ for numeric slope; differentiate again for 2nd-order/Taylor terms.
*   **Inverse Function Theorem:** $F\in C^1$, $\det DF(x)\neq0 \Rightarrow$ local diffeomorphism (diff'ble local inverse). Sufficient for local, not global, invertibility.
*   **Inverse Fn. Thm. — Steps:** (1) Confirm $f\in C^1$ near $x_0$. (2) Compute $Df(x_0)$, verify $\det Df(x_0)\neq0$. (3) Conclude: nbhds $V\ni x_0,W\ni f(x_0)$ with $f:V\to W$ a $C^1$-diffeomorphism (bijective, $C^1$ inverse). (4) $D(f^{-1})(y)=[Df(x)]^{-1}$, $x=f^{-1}(y)$ — invert the Jacobian (e.g. $2\times2$ formula). (5) Local only: $\det DF\neq0$ everywhere $\not\Rightarrow$ global injectivity — check separately (e.g. periodicity).

## III. Optimization & Economic Applications

*   **First and Second Order Conditions:** Local optimum: $\nabla f(x)=0$ (necessary). $H_f$ PD $\Rightarrow$ strict min; ND $\Rightarrow$ strict max; indefinite $\Rightarrow$ saddle.
*   **Definiteness Testing:** $A$ symmetric. **Eigenvalue test**: PD iff all $\lambda>0$; ND iff all $<0$; PSD/NSD iff all $\ge0/\le0$; indefinite iff mixed signs. **Leading minors** $D_k$: PD iff $D_k>0\ \forall k$; ND iff $(-1)^kD_k>0\ \forall k$. (Semidefiniteness needs **all** principal minors, not just leading.)
*   **Lagrangian Formulation:** $g(x)\ge0,h(x)=0$: $\mathcal{L}=f(x)-\lambda^\top h(x)+\mu^\top g(x)$. $\lambda$ (equality) free in sign; $\mu$ (inequality) $\ge0$.
*   **KKT Conditions:** At optimum $x^*$ (w/ CQ): (i) **Stationarity** $\nabla_x\mathcal{L}=0$; (ii) **Primal feas.** $g\ge0,h=0$; (iii) **Dual feas.** $\mu\ge0$; (iv) **Compl. slackness** $\mu_ig_i(x^*)=0\ \forall i$.
*   **Solving a Lagrangian — Steps:** (1) $\mathcal{L}=f(x)-\lambda^\top h(x)+\mu^\top g(x)$. (2) FOC: $\nabla_x\mathcal{L}=0$. (3) Guess slack ($\mu=0$) for constraints expected non-binding; solve, check $g(x)\ge0$. (4) If infeasible, set binding $g_i(x)=0$, re-solve treating $\mu_i$ unknown. (5) Verify compl. slack. $\mu_ig_i=0$, dual feas. $\mu\ge0$, primal feas. $g\ge0,h=0$. (6) Confirm optimum: bordered Hessian / SOC, or concavity+Slater $\Rightarrow$ KKT suff.
*   **Constraint Qualifications:** **LICQ**: binding constraint grads. lin. indep. $\Rightarrow$ KKT necessary. **Slater** (convex probs): $\exists\hat x$, $g_j(\hat x)>0\ \forall j$, $h_i(\hat x)=0$ (weaker).
*   **Bordered Hessian (Constrained SOC):** $n$ vars, $m$ eq. constraints: $\bar H=\begin{pmatrix}0&Dh^\top\\Dh&H_{\mathcal L}\end{pmatrix}$. Last $n-m$ leading minors (orders $2m{+}1..n{+}m$): **max** alternate from $(-1)^{m+1}$; **min** all sign $(-1)^m$.
*   **Envelope Theorem:** $\frac{dV}{dm}=\frac{\partial\mathcal{L}}{\partial m}$ (value fn.'s marginal change = Lagrangian's partial).
*   **Homogeneous & Homothetic Functions:** $f(tx)=t^kf(x)$: homog. degree $k$. Homothetic = monotonic transform of homog. fn.
*   **Quasi-concavity:** $\{f\ge\alpha\}$ convex $\forall\alpha$ (iff $f(tx+(1-t)y)\ge\min\{f(x),f(y)\}$). Weaker than concave (concave $\Rightarrow$ QC, not conversely; e.g. utility fns.).
*   **Additivity & Divisibility:** $f(x+y)\ge f(x)+f(y)$ & $f(tx)\ge tf(x)\ \forall t\in[0,1] \Rightarrow f$ concave & homog. degree 1.
*   **Log-Linearization:** $\hat z=(z-z^*)/z^*$ (% deviation from steady state).
*   **Correspondences (Set-Valued Maps):** Key properties: upper/lower hemicontinuity; closed/compact/convex-valued. Compact graph $\Rightarrow$ compact-valued (not conversely).

## IV. Probability

*   **Kolmogorov's Probability Axioms:** $\Omega$ arbitrary sample space; $\mathcal{F} \subseteq 2^\Omega$: $\sigma$-algebra (closed under complement, countable union); $P: \mathcal{F} \to [0,1]$ countably additive, $P(\Omega) = 1$.
*   **Derived / Required Properties:** **Null**: $P(\emptyset) = 0$; **Norm.**: $P(\Omega) = 1$; **Complement**: $P(A^c) = 1 - P(A)$; **Countable additivity**: disjoint $\{A_i\}$: $P\left(\bigcup_{i=1}^{\infty} A_i\right) = \sum_{i=1}^{\infty} P(A_i)$; **Translation inv.**: $P(x+A)=P(A)$; **Union**: $P(A\cup B)=P(A)+P(B)-P(A\cap B)$; **Monotone**: $A\subseteq B\Rightarrow P(A)\le P(B)$.
*   **CDF and PMF/PDF:** Discrete: PMF $p(x)=P(X=x)$. Continuous: PDF $f\ge0$, $P(a\le X\le b)=\int_a^bf\,dx$. CDF $F(x)=P(X\le x)$: non-decr., right-cont., $F(-\infty)=0,F(\infty)=1$, $F'=f$.
*   **Conditional Probability:** $P(A\mid B)=\dfrac{P(A\cap B)}{P(B)}$, $P(B)>0$.
*   **Bayes' Rule:** $P(A\mid B)=\dfrac{P(B\mid A)P(A)}{P(B)}$.
*   **Law of Total Probability:** $\{B_i\}$ partition of $\Omega$: $P(A)=\sum_iP(A\mid B_i)P(B_i)$.
*   **Independence:** $A,B$ indep. iff $P(A\cap B)=P(A)P(B)$ iff $P(A\mid B)=P(A)$. For $\ge3$ events: pairwise indep. $\nRightarrow$ mutual indep.
*   **Independence of Random Variables:** $X,Y$ indep. iff joint = product of marginals ($F_{X,Y}=F_XF_Y$) $\Rightarrow E[XY]=E[X]E[Y]$, $\text{Cov}(X,Y)=0$ (converse false).
*   **Expectation:** $E[X]=\sum xp(x)$ (discrete) or $\int xf(x)dx$ (cont.); linear: $E[aX+bY]=aE[X]+bE[Y]$.
*   **Conditional Expectation:** $E[X\mid Y=y]=\sum xp(x\mid y)$. 
*   **LIE**: $E[X]=E[E[X\mid Y]]$. **Law of total variance:** $\text{Var}(X)=E[\text{Var}(X\mid Y)]+\text{Var}(E[X\mid Y])$.
*   **Variance and Covariance:** $\text{Var}(X)=E[X^2]-E[X]^2$. $\text{Cov}(X,Y)=E[XY]-E[X]E[Y]$. $\text{Var}(aX+bY)=a^2\text{Var}(X)+b^2\text{Var}(Y)+2ab\,\text{Cov}(X,Y)$.
*   **Correlation:** $\rho(X,Y)=\text{Cov}(X,Y)/(\sigma_X\sigma_Y)\in[-1,1]$; $|\rho|=1\iff Y$ affine in $X$ a.s.
*   **Jensen's Inequality:** $g$ convex $\Rightarrow E[g(X)]\ge g(E[X])$ (concave: reverse). E.g. $E[X^2]\ge(E[X])^2$.
*   **Sample Variance:** $S_n^2=\frac1{n-1}\sum(X_i-\bar X_n)^2$ unbiased: $E[S_n^2]=\sigma^2$ ($n-1$ corrects for est. $\mu$ by $\bar X_n$).
*   **Markov's Inequality:** $X\ge0,a>0$: $P(X\ge a)\le E[X]/a$.
*   **Chebyshev's Inequality:** $P(|X-E[X]|\ge k)\le\text{Var}(X)/k^2$.
*   **Law of Large Numbers:** i.i.d. $X_i$, mean $\mu$: $\bar X_n\to\mu$ (WLLN: in prob.; SLLN: a.s.).
*   **Central Limit Theorem:** i.i.d. $X_i$, mean $\mu$, var $\sigma^2$: $\sqrt n(\bar X_n-\mu)\xrightarrow{d}N(0,\sigma^2)$.
