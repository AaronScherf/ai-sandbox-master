
# Microeconomic Analysis
**Instructor:** Mark Dean  
**Course:** Microeconomic Analysis  
**Assignment:** Homework 1  
**Due Date:** Thursday, September 17th  

---

## Question 1: Some things to clear up from class

1. Come up with a choice correspondence that satisfies property $\alpha$ but not property $\beta$, and another that satisfies $\beta$ but not $\alpha$.
2. Show that if a choice correspondence has a utility representation then it must satisfy $\alpha$ and $\beta$.
3. Prove that a choice correspondence satisfies properties $\alpha$ and $\beta$ if and only if it satisfies $\text{WARP}$
4. Here is an alternative definition of $\text{WARP}$, which we will call $\text{WARP}^*$:

> **Axiom 1 (WARP\*)** For any set $S$, there exists a $b^* \in S$ such that, for any $T$ including $b^*$, if  $C(T) \in S$ then $C(T) = \{b^*\}$.

Show that, if we restrict attention to choice functions (i.e., $C$ is single-valued), a data set satisfies $\text{WARP}^*$ if and only if it satisfies $\text{WARP}$. Is this still the case if we allow for $C$ to be a choice correspondence?

### Question 1 Solution:

**Axiom $\alpha$ (Superset to Subset, contraction consistency)** 

$$\text{If } x \in B \subseteq A \text{ and } x \in C(A), \text{ then } x \in C(B)$$

**Axiom $\beta$** (Subset to superset, expansion consistency)

$$\text{If } x, y \in C(A), \, A \subseteq B \text{ and } y \in C(B) \text{ then } x \in C(B)$$

1. Choice correspondence:
	1.  $\alpha$ but not $\beta$

Let $C(*)$ be a choice correspondence on the finite sets $A,B$ such that  if $x \in B \subseteq A \text{ and } x \in C(A), \text{ then } x \in C(B)$  (Axiom $\alpha$). Informally, this theorem states that if x is chosen out of a larger set A, and x is also an element of a set B which is a subset of A, then x must also be chosen out of the subset B; restricting your options cannot change your top preference. 

For a choice correspondence $C(*)$ to violate Axiom $\beta$ , (flipping the position of the sets to maintain the smaller / larger set labels) then we need that for some $x,y \in C(B)$ with $B \subseteq A$ and $y \in C(A)$ , then $x \notin C(A)$ . This would mean that there are two elements $x,y$ chosen as top preferences from the subset $B$ , with $y$ as one of the top preferences from the larger set $A$ but $x$ is not chosen from the larger set $A$. Since the choice correspondence is the same and $A$ contains $B$, both sets must contain $x$ and $y$ . 

Thus let us consider $X = \{x, y, z\}$ and define the choice correspondence $C$ over all subsets of $X$ by:

- $C(\{x, y, z\}) = \{x\}$
- $C(\{x, y\}) = \{x, y\}$
- $C(\{x, z\}) = \{x\}$
- $C(\{y, z\}) = \{y\}$
- $C(\{x\}) = \{x\}$
- $C(\{y\}) = \{y\}$ 
- $C(\{z\}) = \{z\}$
  
Axiom $\alpha$ states that if $x \in B \subseteq A$ and $x \in C(A)$, then $x \in C(B)$. Let $A = \{x, y, z\}$ such that we have $C(A) = \{x\}$. The only subsets $B \subseteq A$ containing $x$ are $\{x, y\}$, $\{x, z\}$, and $\{x\}$. In every case, $x \in C(B)$. When $A$ is any two-element set, the only proper non-empty subsets $B \subset A$ are singletons, where $x \in C(\{x\}) = \{x\}$ holds trivially. When $A$ is a singleton, there are no non-empty proper subsets. Axiom $\alpha$ holds for every pair $B \subseteq A$.

Axiom $\beta$ states that if $x, y \in C(B)$, $B \subseteq A$, and $x \in C(A)$, then $y \in C(A)$. This time, define $B = \{x, y\}$ and $A = \{x, y, z\}$; clearly $B \subseteq A$ and we have that $x, y \in C(B) = \{x, y\}$ and $x \in C(A) = \{x\}$. However, $y \notin C(A)$, therefore Axiom $\beta$ is violated.

2. $\beta$ but not $\alpha$

Using the same set $X = \{x, y, z\}$, define the choice correspondence $C$ over all subsets of $X$ by:

- $C(\{x, y, z\}) = \{x\}$
- $C(\{x, y\}) = \{y\}$
- $C(\{x, z\}) = \{x\}$
- $C(\{y, z\}) = \{y\}$
- $C(\{x\}) = \{x\}$
- $C(\{y\}) = \{y\}$ 
- $C(\{z\}) = \{z\}$

Since the choice for any subset is a singleton, Axiom $\beta$ holds vacuously, since it requires $x, y \in C(B)$ but there is no subset $C(B)$ that can satisfy having two distinct elements.

To demonstrate that $C(*)$ above violates Axiom $\alpha$, we can use the following counterexample: take $A=\{x,y,z\}$ and $B=\{x,y\}$ such that $B \subseteq A$ . $x \in B$ holds and $C(A)=C(\{x, y, z\}) = \{x\}$ so $x \in C(A)$ but $C(B)=\{y\}$ such that  $x \in C(B)$ is not true. Thus Axiom $\alpha$ is violated.


2. Choice correspondence with utility representation must satisfy $\alpha$ and $\beta$

A choice correspondence $C(*)$ with a utility representation must have a some function $u : X \rightarrow \mathbb{R}$ such that $C(A) = \arg\max_x u(x)$ for $x \in A$. 

To satisfy Axiom $\alpha$, we must have that if $x \in B \subseteq A$ and $x \in C(A)$, then $x \in C(B)$. If  $x \in C(A)$ then $x$ is the argmax of the utility function $u(x)$ for the set $A$ , such that $u(x) >= u(y), \forall y \in A$  with $x \neq y$ . Thus for any subset $B \subseteq A$ it must hold that  $u(x) >= u(y), \forall y \in B$ since all $x,y \in B$ are also contained in $A$, such that $x \in C(B)$. Therefore Axiom $\alpha$ holds.

To satisfy Axiom $\beta$, we must have that if $x, y \in C(B)$, $B \subseteq A$, and $x \in C(A)$, then $y \in C(A)$. By the condition $x, y \in C(B)$, $B \subseteq A$, and $x \in C(A)$, we know that both $x$ and $y$ are argmax for the choice correspondence $C(B)$ and $B$ is contained in $A$, thus $x$ and $y$ are contained in $A$ as well. Therefore, if $x$ is an argmax for the smaller set $B$, then it must be true that $u(x) \geq u(y) , \forall y \in B$ . But since we have that $y \in C(B)$ as well, $u(y) \geq u(x) , \forall x \in B$, which can only be satisfied in the real numbers if $u(x)=u(y)$. Thus, if both $x$ and $y$ are contained in the larger set $A$ and we use the same utility function,  $u(x)=u(y)$ must hold for $A$ as well, thus  if $x \in C(A)$ is true then $y \in C(A)$ must be true as well, and Axiom $\beta$ is satisfied.

3. Choice correspondence satisfies properties $\alpha$ and $\beta$ if and only if it satisfies $\text{WARP}$

If a choice correspondence $C(*)$ satisfies WARP then we have that if $x,y \in A \cap B, x \in C(A)$ and $y \in C(B)$ it must be true that $x \in C(B)$. In other words, if two elements $x,y$ are contained in the intersection of two sets $A$ and $B$ (such that the elements are contained in both sets), if $x$ is chosen from $A$ independently and $y$ is chosen from $B$ independently, then we must also have that $x$ is chosen from $B$.

To show that a correspondence satisfying WARP satisfies Axiom $\alpha$, we must show that if $x \in B \subseteq A$ and $x \in C(A)$, then $x \in C(B)$. If $B \subseteq A$ then $A \cap B = B$, such that for $x \in B$ , if $x \in C(A)$ holds then $x$ must be preferred at least as much as all other choices in the larger set $A$ . Since $B$ is a subset of $A$,  $x \in C(B)$ must hold.

To show that the correspondence satisfies Axiom $\beta$, if $x, y \in C(A)$, $A \subseteq B$ and $y \in C(B)$, then we must show that $x \in C(B)$ holds. Given $A \subseteq B$, take the subset $A$ as the intersection $A \cap B=A$ such that if $x,y \in C(A)$ is true and $y \in C(B)$ is true, we need to show that $x \in C(B)$ follows from WARP. WARP only depends on $x \in C(A)$ and $y \in C(B)$, so our conditions are satisfied since $x \in C(A)$ follows from $x,y \in C(A)$ and we have $y \in C(B)$, thus WARP guarantees that  $x \in C(B)$ and Axiom $\beta$ is satisfied.

In the other direction, if a choice correspondence satisfies $\alpha$ and $\beta$, then we have that if $x \in B \subseteq A$ and $x \in C(A)$, then $x \in C(B)$ (Axiom $\alpha$) and if $x,y \in B \subseteq A$ , then if $x, y \in C(B)$, and $y \in C(A)$, then $x \in C(A)$ (Axiom $\beta$). Thus for any $x,y \in A \cap B$, if $x \in C(A)$ and $y \in C(B)$, we know that $x$ and $y$ must be contained in both $A$ and $B$, so without loss of generality we can take $B \subseteq A$, and by Axiom $\alpha$ we have that $x \in C(B)$, satisfying WARP.

4. Choice **function** satisfies $\text{WARP}^*$ if and only if it satisfies $\text{WARP}$

[First Attempt]

> **WARP\*** For any set $S$, there exists a $b^* \in S$ such that, for any $T$ including $b^*$, if  $C(T) \in S$ then $C(T) = \{b^*\}$.

**WARP:** $$\text{If } x, y \in A \cap B, \, x \in C(A) \text{ and } y \in C(B) \implies x \in C(B)$$
If we restrict attention to choice functions (i.e., $C$ is single-valued), we want to show that a data set satisfies $\text{WARP}^*$ if and only if it satisfies $\text{WARP}$. 

If the choice function satisfies WARP, then for any $x,y \in A \cap B$, if $x \in C(A)$ and $y \in C(B)$, we must have that $x \in C(B)$; if the choice correspondence is single valued then each choice function can only contain a singleton element, such that if $x$ and $y$ are both in both sets $A$ and $B$, for $x$ to be the preferred choice from $A$ and $y$ to be the preferred choice from $B$, then we must have that $x = y$, such that $x \in C(B)$ holds from $y \in C(B)$. 

Thus if the choice function satisfies WARP, then we can show that it satisfies WARP* by defining $S$ as $A$, $T$ as $B$, and $b^{*}$ as $x=y$. Under the new definitions, for any set $A$, we can define an element $x \in A$ such that, for any $B$ that also contains $x$, we know that $x \in A \cap B$. If $C(B) \in A$ then we know that $C(B)$ must be a singleton element in the intersection $A \cap B$, thus if the choice function is single valued, for $x=C(A)$, we must have that $C(B)=x$ as well.

If we allow for $C$ to be a choice correspondence instead of a single valued choice function, WARP is no longer sufficient to prove WARP* since $C(B)$ could equal both $x$ and $y$ with $x \neq y$, so we have no guarantee that $C(B)=x$. 

But if WARP works with choice correspondence, then we can still show WARP implies WARP*, but if we only have WARP* then we cannot imply WARP, since WARP* depends on a singleton $C(T)=\{b^{*}\}$. 

[Revised Rigorous Proof]

Let $X$ be a non-empty set of alternatives, and let $\mathcal{D}$ denote the domain of non-empty choice menus.

First, consider the equivalence of WARP and WARP* for single-valued choice functions.

Assume $C(A)$ is a singleton for every $A \in \mathcal{D}$. With slight abuse of notation for singletons, we write $C(A) = x$ to mean $C(A) = \{x\}$.

Direction 1: $\text{WARP} \implies \text{WARP}^*$

Assume $C$ satisfies $\text{WARP}$:
$\text{If } x, y \in A \cap B, \, x \in C(A) \text{ and } y \in C(B) \implies x \in C(B)$. Take any menu $S \in \mathcal{D}$. Since $C$ is a choice function, $C(S)$ is a singleton; define $b^* \in S$ by: $C(S) = \{b^*\}$

Now consider any menu $T \in \mathcal{D}$ such that: $b^* \in T$,  $C(T) \in S$. Let $y = C(T)$. By condition (2), $y \in S$; and since $y = C(T) \subseteq T$, $y \in T$. Thus, $y \in S \cap T$. Similarly, $b^* \in S$ (by construction) and $b^* \in T$ (by condition 1), so $b^* \in S \cap T$.

We now have $b^*, y \in S \cap T$, $b^* \in C(S)$, $y \in C(T)$. Applying $\text{WARP}$ with $A = S$ and $B = T$ yields $b^* \in C(T)$. Because $C$ is single-valued, $C(T)$ contains only one element. Since $y \in C(T)$ and $b^* \in C(T)$, it must be that $y = b^*$. Therefore, $C(T) = \{b^*\}$, satisfying $\text{WARP}^*$.

Direction 2: $\text{WARP}^{*} \implies \text{WARP}$

Assume $C$ satisfies $\text{WARP}^*$. Let $A, B \in \mathcal{D}$ with $x, y \in A \cap B$ such that $C(A) = \{x\}$ and $C(B) = \{y\}$. We must show that $x \in C(B)$, which for a choice function means showing $x = y$. Consider the binary menu $S = \{x, y\} \in \mathcal{D}$. By $\text{WARP}^*$, there exists some $b^* \in \{x, y\}$ such that for any menu $T$ containing $b^*$, if $C(T) \in \{x, y\}$, then $C(T) = \{b^*\}$.

Without loss of generality, $b^*$ is either $x$ or $y$.

Case 1: $b^{*} = x$. Consider menu $A$: by assumption, $x \in A$ (so $b^* \in A$), and $C(A) = x \in \{x, y\}$. Applying $\text{WARP}^*$ with $T = A$ yields $C(A) = \{x\}$ (consistent). Consider menu $B$: by assumption, $x \in B$ (so $b^* \in B$), and $C(B) = y \in \{x, y\}$. Applying $\text{WARP}^*$ with $T = B$ yields $C(B) = \{b^*\} = \{x\}$. But we were given $C(B) = \{y\}$. Since $C(B)$ is single-valued, $\{y\} = \{x\}$, which implies $x = y$.

Case 2: $b^{*} = y$. Symmetrically, $b^* = y \in A$ and $C(A) = x \in \{x, y\}$. Applying $\text{WARP}^*$ with $T = A$ yields $C(A) = \{b^*\} = \{y\}$. Since $C(A) = \{x\}$, we have $\{x\} = \{y\}$, so $x = y$.

In both cases, $x = y$. Hence $x \in C(B)$, satisfying $\text{WARP}$.

If we allow $C$ to be a multi-valued choice correspondence, however, the equivalence fails. Specifically: $\text{WARP}^{*} \implies \text{WARP}, \quad \text{but} \quad \text{WARP} \not\implies \text{WARP}^{*}$

Consider the following counterexample  where $\text{WARP}$ holds, but $\text{WARP}^*$ fails.

Let $X = \{x, y\}$ and let preferences exhibit indifference: $x \sim y$. The corresponding rational choice correspondence is: $C(\{x\}) = \{x\}$, $C(\{y\}) = \{y\}$, $C(\{x, y\}) = \{x, y\}$.

1. **$\text{WARP}$ is satisfied:** Because $C$ is rationalized by a complete, transitive preference relation, it satisfies $\alpha$, $\beta$, and $\text{WARP}$.
2. **$\text{WARP}^*$ fails:** Set $S = \{x, y\}$. For $\text{WARP}^*$ to hold, there must exist some $b^* \in \{x, y\}$ such that whenever $b^* \in T$ and $C(T) \subseteq S$, $C(T) = \{b^*\}$ must be a **singleton**. Take $T = \{x, y\}$: clearly $b^* \in T$ and $C(T) = \{x, y\} \subseteq S$. However, $C(T) = \{x, y\} \neq \{b^*\}$, because $\vert{}C(T)\vert{} = 2$ while $\{b^*\}$ has cardinality $1$.

Thus, $\text{WARP}^*$ is strictly stronger than $\text{WARP}$ in the presence of correspondences because its conclusion structurally rules out multi-valued choice (indifference between multiple chosen options).

---

## Question 2: Alternative Choice Procedures and Rationality

Utility maximization is not the only choice procedure that is consistent with $\alpha$ and $\beta$. There are also other choice procedures that will satisfy these conditions and so are indistinguishable from rational choice. 

Consider the following decision-making procedures. Prove whether or not they will result in choices that satisfy $\alpha$ and $\beta$. (Feel free to assume that there are a finite number of alternatives in each case). If they are consistent with $\alpha$ and $\beta$, and therefore admit a utility representation, discuss the relationship between such representations and their "true" utility (if the decision-making model has such a thing).

1. **Satisficing:** A decision maker (DM) is choosing between books from a set $B$. They have a utility function $u: B \to \mathbb{R}$, and a "threshold" utility level $u^*$. In any choice set, they search through the books alphabetically by title, and choose the first book that has utility level $u$ that is equal to or above $u^*$. If they have not found any such book by the time they reach the end of the choice set, they will choose the book with the highest utility (to make things simpler you can assume that there is no indifference, i.e., no two books have the same utilities).
2. **Elimination by Aspects:** The DM is choosing between kettles. Each kettle is defined by its price, its energy efficiency (on a scale from $1$ to $5$), and its attractiveness (on a scale of $1$ to $3$). When given a choice set, the DM:
   - (a) Selects all the kettles with the highest attractiveness rating;
   - (b) From those kettles, selects those with the best energy efficiency;
   - (c) From those that remain, they choose the cheapest.
3. The DM ranks the alternatives according to price, then looks at the three cheapest and chooses the one with the highest utility.
4. The DM has a true utility function for kettles based on price, energy efficiency, and attractiveness. However, to save time, they always just buy the cheapest kettle.
5. The DM ranks the alternatives according to a utility function, and in any choice set chooses all median elements (note that if the median has more than one element all are chosen).
6. **Rational Shortlisting:** The DM is choosing between routes to drive home. For some routes they have live transit information and for some they do not. The DM makes decisions in two stages:
   - First, they remove any routes such that there is a quicker available route according to the live transit information.
   - Of the remaining routes, they choose the shortest (in miles).


### Question 2 Solution:

1. Satisficing:
This procedure satisfies Axiom $\alpha$. Defining the larger set of all books as $B$  and the subset of books considered before selection as $A$, we know that if a book $x$ is found that satisfies the threshold before exhausting the list, then we have some $x \in A \subseteq B$ with $x \in C(B)$ , clearly the book also satisfies the threshold for the subset of books considered such that $x \in C(A)$. If no book is found that satisfies the threshold, then $A=B$ and the book with the highest utility is chosen as $x \in C(B)=C(A)$ so Axiom $\alpha$ holds trivially.

This procedure also satisfies Axiom $\beta$ since there cannot be any ties (since we assumed no indifference, the choice correspondence is a choice function), such that if a book is found satisfying the threshold, the initial condition of $x,y \in C(A)$ is always false since $C(A)$ can only contain a single element, thus $x=y$ must be true and $x \in C(B)$ holds.

The satisficing procedure depends on an assumed utility function $u$ and threshold level $u^{*}$ such that the "true" utility of the procedure is either $u^{*}$ if a book is found satisfying the threshold or the max utility possible given the choice set (which is always less than $u^{*}$).

2. Elimination by Aspects:
To test Axiom $\alpha$, from the set of all kettles $A$, consider the set of kettles chosen through the elimination process and define them as $C(A)$. For some subset $B \subseteq A$, if we identify a single kettle that satisfies the elimination such that $x \in C(A)$ holds, if $x \in B$ then that kettle must satisfy the same elimination process for the subset $B$, such that $x \in C(B)$ as well. The elimination process always results in a singleton value so if it holds for an element of a larger set, it will pick the same singleton from a subset if it also contains that singleton.

Axiom $\beta$ holds vacuously again since the elimination is a single-valued choice function, such that we do not have situations where $x,y \in C(A)$ hold without $x=y$ being true, which would always result in $x \in C(A)$ for the larger superset $A$.

[Wait, what if we get ties on cheapest? It doesn't have to be single valued then.]

This procedure admits a utility representation and it is consistent with the "true" utility, which is just the composition of two correspondences (for attractiveness and energy efficiency) and a single valued function on price.

3. Ranks by price, then three cheapest, then highest utility

This procedure **violates Axiom $\alpha$**. Consider a finite universe of four items $X = \{w, x, y, z\}$. Let the price ranking be $p(w) < p(x) < p(y) < p(z)$, and let utilities be $u(w) = 1$, $u(x) = 2$, $u(y) = 3$, and $u(z) = 10$. For the larger set $A = \{w, x, y, z\}$, the three cheapest alternatives are $\{w, x, y\}$. Evaluating utility on this consideration set, $y$ has the highest utility ($u(y) = 3 > 2 > 1$), so $C(A) = \{y\}$. Now consider the subset $B = \{x, y, z\} \subset A$. Here $\vert{}B\vert{} = 3$, so all three elements are evaluated directly according to utility. Because $u(z) = 10 > u(y) > u(x)$, the chosen element is $C(B) = \{z\}$. We have $y \in B \subset A$ and $y \in C(A)$, but $y \notin C(B)$ and thus Axiom $\alpha$ is violated.

Assuming no ties in prices or utilities, the procedure always selects a single element ($\vert{}C(S)\vert{} = 1$ for all $S$). Consequently, the premise $x, y \in C(B)$ with $x \neq y$ is never satisfied, meaning Axiom $\beta$ holds **vacuously**.

[But we can't assume no ties... So beta might not hold.]

Because Axiom $\alpha$ fails, this choice procedure **cannot** be rationalized by any preference relation or utility function. It does not admit a utility representation, despite the DM possessing a true utility function.

4. True utility, but always buy the cheapest kettle

This procedure **satisfies Axiom $\alpha$**. The DM’s choice correspondence is defined by price minimization $C(S) = \arg\min_{x \in S} p(x)$. Let $B \subseteq A$ and suppose $x \in B$ with $x \in C(A)$. Since $x \in C(A)$, $p(x) \le p(z)$ for all $z \in A$. Because $B \subseteq A$, this inequality holds for all $z \in B$, which implies $x \in C(B)$, thus Axiom $\alpha$ holds.

This procedure **satisfies Axiom $\beta$**. Let $x, y \in C(B)$ with $B \subseteq A$, and suppose $y \in C(A)$. $x, y \in C(B)$ implies $p(x) = p(y)$. $y \in C(A)$ implies $p(y) \le p(z)$ for all $z \in A$. Substituting $p(x) = p(y)$, we obtain $p(x) \le p(z)$ for all $z \in A$, which guarantees $x \in C(A)$. Thus, Axiom $\beta$ holds.

Because both $\alpha$ and $\beta$ hold, the procedure admits a standard utility representation $U: X \to \mathbb{R}$. Any strictly decreasing transformation of price—such as $U(x) = -p(x)$—rationalizes the observed choice behavior. The revealed utility representation $U$ is completely **decoupled** from the DM’s "true" multi-attribute utility function $u(\text{price}, \text{efficiency}, \text{attractiveness})$. Revealed preference only captures the decision heuristic (price), rendering the non-price dimensions of true utility unobservable from choice data alone.

5. Utility ranking, choose all median elements

This procedure **violates Axiom $\alpha$**. Let $X = \{x, y, z\}$ with utilities $u(x) = 3$, $u(y) = 2$, and $u(z) = 1$. For the larger menu $A = \{x, y, z\}$, ordering by utility gives $(x, y, z)$. The unique median element is $y$, so $C(A) = \{y\}$. Consider the subset $B = \{x, y\} \subset A$. Since $\vert{}B\vert{} = 2$ is even, both elements constitute the median: $C(B) = \{x, y\}$. Now consider the subset $B' = \{y, z\} \subset A$. Similarly, $C(B') = \{y, z\}$. However, consider the singleton menu containing the winner: $B'' = \{y\} \subset A$. Here $C(\{y\}) = \{y\}$. To see the violation of $\alpha$, consider adding an extreme alternative: take $B = \{w, x, y\}$ where $u(w) = 4 > u(x) = 3 > u(y) = 2$. Here $C(B) = \{x\}$. Now expand to $A = \{w, x, y, z, v\}$ with $u(w)=5, u(x)=4, u(z)=3, u(y)=2, u(v)=1$. In $A$, the median is $z$, so $C(A) = \{z\}$.

This procedure violates Axiom $\beta$. Take $B = \{x_2, x_3\}$ where $u(x_2) > u(x_3)$. Because $\vert{}B\vert{} = 2$, both elements are medians: $C(B) = \{x_2, x_3\}$. Now expand to $A = \{x_1, x_2, x_3\}$ with $B \subset A$ and $u(x_1) > u(x_2) > u(x_3)$. In menu $A$, the unique median is $x_2$, so $C(A) = \{x_2\}$. We have $x_2, x_3 \in C(B)$, $B \subset A$, and $x_2 \in C(A)$, but $x_3 \notin C(A)$. Thus, Axiom $\beta$ is violated.

Because both axioms fail, this procedure cannot be rationalized by any utility function.

6. Rational Shortlisting

[Struggled with this one]

This procedure **violates Axiom $\alpha$**. Let there be three routes $X = \{x, y, z\}$. Let $x$ (no live data, 8 miles), $y$ (live data: 30 mins, 12 miles), $z$ (live data: 15 mins, 20 miles). 

Menu $A = \{x, y, z\}$: In stage 1, $z$ eliminates $y$ (15 mins < 30 mins). Candidates remaining: $\{x, z\}$. In stage 2, comparing mileage: $x$ (8 miles) vs $z$ (20 miles) $\implies C(A) = \{x\}$.

Menu $B = \{x, y\} \subset A$: In stage 1, $z$ is absent, so $y$ is **not** eliminated. Candidates remaining: $\{x, y\}$. In stage 2, comparing mileage: $x$ (8 miles) vs $y$ (12 miles) $\implies C(B) = \{x\}$.

Now flip mileage between $x$ and $y$: let $y$ be 5 miles (30 mins, live data), $x$ be 10 miles (no live data), and $z$ be 20 miles (15 mins, live data).

In menu $A = \{x, y, z\}$: $z$ eliminates $y$ via live data in stage 1. Candidates remaining: $\{x, z\}$. Comparing mileage in stage 2: $x$ (10 miles) vs $z$ (20 miles) $\implies C(A) = \{x\}$.

In menu $B = \{x, y\} \subset A$: With $z$ absent, $y$ is **not** eliminated. Both $\{x, y\}$ survive stage 1. Comparing mileage in stage 2: $y$ (5 miles) vs $x$ (10 miles) $\implies C(B) = \{y\}$.

We have $x \in B \subset A$ and $x \in C(A)$, but $x \notin C(B)$. Thus, Axiom $\alpha$ is violated.

Assuming no ties in transit duration or mileage, choices are single-valued, so Axiom $\beta$ holds **vacuously**.

Because Axiom $\alpha$ fails, rational shortlisting **cannot** be rationalized by a utility function. The presence of an alternative ($z$) alters the survival of other alternatives ($y$) in stage 1, inducing menu-dependent choice reversals that violate WARP.

---

## Question 3: Preference Relations and Choice Functions

Let $\succeq$ be a complete relation on a non-empty set $X$, and for any finite $S \subset X$ define:
$$C(S) = \{x \in S \mid x \succeq y \text{ for all } y \in S\}$$

1. Show that if $\succeq$ is transitive, $C(S)$ is non-empty.
2. We say a binary relation is acyclic if there is no $k$ and set $x_1, \dots, x_k \in X$ such that $x_1 \succ x_2 \succ \dots \succ x_k \succ x_1$. Show that acyclicity is a strictly weaker property than transitivity.
3. Show that if $\succeq$ is acyclic, $C(S)$ is non-empty.
4. Show that if $C(S)$ is non-empty for every finite $S$, then $\succeq$ is acyclic.

### Question 3 Solution:

1. Show that if $\succeq$ is transitive, $C(S)$ is non-empty.

[First Attempt]
If $\succeq$ is transitive then by definition we have that for $x,y,z \in X, \text{ if } x \succeq y \text{ and } y \succeq z \implies x \succeq z$. Since $X$ is non-empty, for any finite and non-empty subset $S \subset X$ we aim to show $C(S)$ is non-empty, in other words that there exists some set $x \in S$ such that $x \succeq y, \forall y \in S$ . 

If $S$ is a subset of a single element, $x$, then $x \succeq x$ holds by the symmetry of the indifference relation $x \sim x$. Therefore $C(S)=\{x\}$ and is non-empty.

If $S$ contains exactly two elements, $x,y \in S$, then by completeness one of $x \succeq y, y \succeq x, \text{ or } x \sim y$ must be true. These cases would, respectively, mean that $C(S)=\{x\}, C(S)=\{y\}, C(S)=\{x\}$, so in any case $C(S)$ is non-empty.

If $S$ contains three or more elements, without loss of generality we can extend the two element case to a third arbitrary element $z$ , for which one of the following must be true: $y \succeq z, z \succeq y, \text{ or } z \sim y$. Thus by transitivity, these cases would result in $x \succeq z, z \succeq x, \text{ or } x \sim z$ and as a result $C(S)=\{x\}, C(S)=\{z\}, \text{ or } C(S)=\{x\}$. 

Since $z$ can be taken as any arbitrary element this process can be applied inductively to any finite set $S$ to proceed from a set of cardinality $k$ to cardinality $k+1$, such that $x$ is either strictly preferred to the $k+1$ element (and $C(S)=\{x\}$), the $k+1$ element is strictly preferred to $x$ so by transitivity is strictly preferred to all preceding $k$ elements (and $C(S)=\{x_{k+1}\}$) or $x \sim x_{k+1}$ (and $C(S)=\{x\}$). Thus $C(S)$ must be non-empty for any non-empty $S$.

[Corrected with proper induction]

**Claim:** If $\succeq$ is complete and transitive, then for any finite, non-empty $S \subseteq X$, $C(S) \neq \emptyset$.

By mathematical induction, we start with the base case (S has one element). Let $S=\{x_1​\}$. By completeness of $\succeq$, we know $x_1​ \succeq x_1$​. Therefore, $x_1​ \succeq y , \forall y \in S$ trivially, which implies $C(S)={x_1​} \neq \emptyset$. Our induction hypothesis is that for any subset $S' \subseteq X$ with more than one element, $C(S') \neq \emptyset$.

The inductive step proceeds as follows: let $S=\{x_1,x_2, \dots , x_k, x_k+1\}$ with cardinality $|S|=k+1$. Consider the subset $S' = \{x_1​,\dots ,x_k\}$. Since $|S'| =k$, by the induction hypothesis there exists at least one element $x^{*} \in C(S')$. By definition $x^{*} \succeq y , \forall y \in S'$. Now compare $x^{*}$ to the remaining element $x_{k+1}$​. By completeness of $\succeq$, either $x^{*} \succeq x_{k+1}​ \text{ or } x_{k+1} ​\succeq x^{*}$ (or both). 

In the case where $x^{*} \succeq x_{k+1}$, since $x^{*} \succeq y$ for all $y \in S'$ and $x^{*} \succeq x_{k+1}$​, it follows that $x^{*} \succeq y , \forall y \in S' \cup \{x_{k+1}\} = S$ . Thus, $x^* \in C(S)$, so $C(S) \neq \emptyset$.

In the case where $x_{k+1}​ \succeq x^{*}$, we can take any arbitrary $y \in S$. If $y = x_{k+1}$​, then $x_{k+1} ​\succeq x_{k+1}$​ by completeness. If $y \in S'$, we have $x_{k+1}​ \succeq x^*$ and $x^{*} \succeq y$. By transitivity of $\succeq$, $x_{k+1}​ \succeq x^*$ and $x^* \succeq y \implies x_{k+1}​ \succeq y$. Thus, $x_{k+1}​ \succeq1 y , \forall y \in S$, which implies $x_{k+1}​ \in C(S)$, so $C(S) \neq \emptyset$.

By mathematical induction, $C(S)$ is non-empty for every finite non-empty $S \subseteq X$.


2. We say a binary relation is acyclic if there is no $k$ and set $x_1, \dots, x_k \in X$ such that $x_1 \succ x_2 \succ \dots \succ x_k \succ x_1$. Show that acyclicity is a strictly weaker property than transitivity.

We claim that acyclicity of $\succ$ is a strictly weaker property than transitivity of $\succeq$. To show this, we prove that transitivity implies acyclicity, but acyclicity does not imply transitivity.

Start by showing transitivity implies acyclicity. Let $\succeq$ be a complete and transitive relation on $X$, with the asymmetric (strict) relation defined by $x \succ y \iff (x \succeq y \text{ and } y \not\succeq x)$. 

We know that if $\succeq$ is transitive, then $\succ$ is transitive, by the following: first suppose $x \succ y$ and $y \succ z$, since $x \succ y \implies x \succeq y$, and $y \succ z \implies y \succeq z$, transitivity of $\succeq$ implies $x \succeq z$. Suppose for contradiction that $z \succeq x$. Then $y \succeq z$ and $z \succeq x$ would imply $y \succeq x$ by transitivity of $\succeq$, which contradicts $x \succ y$. Therefore, $z \not\succeq x$, which establishes that $x \succ z$.

If $\succ$ is transitive, we will now show $\succ$ is acyclic. For the sake of contradiction, assume that a strict cycle exists of the type $x_1 \succ x_2 \succ \dots \succ x_k \succ x_1$. By applying transitivity of $\succ$ repeatedly along the chain, we get  $x_1 \succ x_k$. But the cycle also states $x_k \succ x_1$, contradicting the asymmetry of $\succ$, since $x_1 \succ x_k \implies x_k \not\succ x_1$. Thus, if $\succ$ is transitive, $\succ$ must be acyclic.

Now we will show that acyclicity does not imply transitivity. Consider a counterexample on $X = \{x, y, z\}$ with the complete binary relation $\succeq$ defined by:
- $x \succ y$ ($x \succeq y$ and $y \not\succeq x$)
- $y \succ z$ ($y \succeq z$ and $z \not\succeq y$)
- $x \sim z$ ($x \succeq z$ and $z \succeq x$)

We know reflexivity holds since $w \succeq w$ for all $w \in X$. We can show that acyclicity holds since the only strict pairs are $x \succ y$ and $y \succ z$. Because there is no strict comparison between $x$ and $z$, no closed loop of strict preferences can be formed. Hence, $\succ$ is acyclic. However, we can show that transitivity fails, since we have $z \succeq x$ (since $z \sim x$) and $x \succeq y$ (since $x \succ y$). Transitivity of $\succeq$ would require that $z \succeq x \text{ and } x \succeq y \implies z \succeq y$. However, $y \succ z \implies z \not\succeq y$, directly violating transitivity.

Because transitivity implies acyclicity but the converse fails, acyclicity is strictly weaker than transitivity.


3. Show that if $\succeq$ is acyclic, $C(S)$ is non-empty.

We know that for any finite set $S \subset X$, we have that $C(S) = \{x \in S \mid x \succeq y \text{ for all } y \in S\}$. Because $\succeq$ is complete, the negation of $x \succeq y$ is $y \succ x$. Therefore $x \in C(S) \iff$ there is no $y \in S$ such that  $y \succ x$.

We can construct an algorithm to search for a "max" using pairwise comparison that must be included in $C(S)$ and make $C(S)$ non-empty. 

For the finite non-empty set $S$ with $|S| = n$, we define the following iterative procedure to locate an undominated alternative. First, choose an arbitrary initial element $x_0 \in S$. Then, take a current candidate $x_k \in S$. If there exists no $y \in S$ such that $y \succ x_k$. By completeness of $\succeq$, $x^* \succeq y$ for all $y \in S$, thus we can stop the search and set $x^* = x_k$, such that we have an element that is chosen and $x^* \in C(S)$.

If there does exist some $y \in S$ such that $y \succ x_k$, then select that $y$, set $x_{k+1} = y$, and repeat the process. If the process eventually terminates by encountering an $x^*$, then we again have that $x^* \in C(S)$ and $C(S)$ is non-empty.

Suppose, however, for contradiction that the algorithm never terminates. Because it never terminates, it generates an infinite sequence $\{x_k\}_{k=0}^\infty \subseteq S$ satisfying: $$x_0 \prec x_1 \prec x_2 \prec \dots \prec x_k \prec x_{k+1} \prec \dots$$
Since $S$ is finite ($\vert{}S\vert{} = n$), the infinite sequence must eventually revisit a previously visited state, such that there exist integers $i, j$ with $0 \le i < j$ such that $x_i = x_j$, and thus we have a cyclical sequence like: $$x_i \prec x_{i+1} \prec \dots \prec x_j = x_i$$
This contradicts the foundational assumption that $\succ$ is acyclic, and therefore the initial assumption that the algorithm never terminates. Therefore, the algorithm must identify a maximum $x^*$ that is selected and we again have $C(S)$ is non-empty.


4. Show that if $C(S)$ is non-empty for every finite $S$, then $\succeq$ is acyclic.

We prove the contrapositive: if $\succeq$ is not acyclic, then there exists a finite, non-empty set $S \subset X$ such that $C(S) = \emptyset$.

First, suppose $\succeq$ is not acyclic. By definition, there exists an integer $k \ge 3$ and a set of distinct elements $\{x_1, x_2, \dots, x_k\} \subseteq X$ that form a strict cycle: $x_1 \succ x_2 \succ \dots \succ x_k \succ x_1$. Define the finite set $S = \{x_1, x_2, \dots, x_k\}$. For any candidate element $x \in S$, we check whether $x \in C(S)$:
- If $x = x_1$, the cycle asserts that there is some $x_k \succ x_1$. By asymmetry of $\succ$, $x_k \succ x_1 \implies x_1 \not\succeq x_k$. Thus, $x_1 \notin C(S)$.
- If $x = x_m$ for any $m \in \{2, \dots, k\}$, the cycle asserts that $x_{m-1} \succ x_m$. By asymmetry of $\succ$, $x_m \not\succeq x_{m-1}$. Thus, $x_m \notin C(S)$.

Thus, every element $x \in S$ is strictly dominated by another element in $S$ and no element in $S$ weakly dominates all elements in $S$, which implies that $C(S) = \emptyset$. So we have that if $\succeq$ is not acyclic, then $C(S)$ is empty.

Thus, by the contrapositive, if $C(S)$ is non-empty for every finite set $S$, then $\succeq$ must be acyclic.

---

## Question 4: Choice with Consideration Sets

One popular model of choice behavior in the marketing literature is choice with consideration sets. The basic idea is that, when presented with a choice set $A$, the decision maker only really thinks about a subset of those alternatives $E(A)$ and chooses the best of those.

> **Definition 1** We say a set of choice data can be explained as choice with consideration sets if there is:
> 1. A utility function $u: X \to \mathbb{R}$, and
> 2. A consideration set correspondence $E: 2^X \setminus \{\emptyset\} \to 2^X \setminus \{\emptyset\}$

such that $E(A) \subseteq A$ and  $C(A) = \arg\max_{x \in E(A)} u(x)$

In other words, for each set $A$, $E(A)$ defines the set of alternatives that the decision maker considers. They then choose the best option from $E(A)$ according to $u$.

For simplicity, let's assume that we are dealing with choice functions (not correspondences), that there is no indifference, and that $X$ is finite.

1. Show that, without further restrictions on $E$, a model of choice from consideration sets can explain any choice function.
2. For the remainder of the question, add the restriction:   $$\text{If } x \in B \subset A, \text{ then } x \in E(A) \implies x \in E(B)$$
   This means that consideration gets harder in larger choice sets, so if $x$ is considered in the bigger set $A$, then it should also be considered in the smaller set $B$.  

   Is this restriction implied by each of the following choice procedures?

   - (a) In each choice set, consider the three cheapest cars (or all the cars if there are fewer than three).
   - (b) In each choice set, consider the fastest car and the car with the best safety rating.
   - (c) In each choice set, consider cars that are unusual: count up the number of cars in the choice set which are green, red, brown, etc., and consider only those that are of the least common color.

3. Is the following set of choices consistent with this model?
   $$C(\{x, y, z\}) = x$$
   $$C(\{x, y\}) = y$$

4. Show that the behavior in part 3 implies that $u(y) > u(x)$ if the model is correct.

5. Show that this model does not imply $\text{WARP}$.

6. Consider the following modification of the $\text{WARP}^*$ axiom of Question 1:

> **Axiom 2** For any set $S$, there exists a $b^* \in S$ such that, for any $T$ including $b^*$, if $C(T) \in S$ and $b^* = C(T')$ for some $T' \supset T$, then $C(T) = b^*$.

Show that the consideration set model described above does imply this behavior.

7. Consider the following variant of the above model. Rather than the condition in part 2, we have the condition:
   $$E(A \setminus \{x\}) = E(A) \quad \text{if } x \notin E(A)$$
   In other words, if $x$ is not considered at $A$, then removing it does not change the consideration set. Does the resulting model still satisfy the axiom from part 6?


### Question 4 Solution:

> **Definition 1** We say a set of choice data can be explained as choice with consideration sets if there is:
> 1. A utility function $u: X \to \mathbb{R}$, and
> 2. A consideration set correspondence $E: 2^X \setminus \{\emptyset\} \to 2^X \setminus \{\emptyset\}$

such that $E(A) \subseteq A$ and  $C(A) = \arg\max_{x \in E(A)} u(x)$

In other words, for each set $A$, $E(A)$ defines the set of alternatives that the decision maker considers. They then choose the best option from $E(A)$ according to $u$.

For simplicity, let's assume that we are dealing with choice functions (not correspondences), that there is no indifference, and that $X$ is finite.

1. Show that, without further restrictions on $E$, a model of choice from consideration sets can explain any choice function.

If the choice model explains a choice function $C$ then there exists a pair $(u, E)$ satisfying Definition 1 that generates the observed choices across all menus:

$$C(A) = \arg\max_{x \in E(A)} u(x) \quad \text{for every } A \in \mathcal{D}$$
To show that a model can explain any choice function means that no matter how erratic, contradictory, or cyclical the observed choice data $C: \mathcal{D} \to X$ may be, you can always construct a valid utility function $u: X \to \mathbb{R}$ and a mapping $E: \mathcal{D} \to \mathcal{D}$ that reproduces $C$.

Let $X$ be a finite set of alternatives, and let $C: 2^X \setminus \{\emptyset\} \to X$ be an arbitrary choice function such that $C(A) \in A$ for every set $A$.

To show that this choice data can be explained, we consider a utility function $u: X \to \mathbb{R}$ and a correspondence $E: 2^X \setminus \{\emptyset\} \to 2^X \setminus \{\emptyset\}$ satisfying $E(A) \subseteq A$ and $E(A) \neq \emptyset$, such that $C(A) = \arg\max_{x \in E(A)} u(x)$ for all $A \subseteq X$.

First, we construct $u$ and $E$. We can assign distinct arbitrary values in an enumeration $x_1, \dots, x_n$ with $u(x_i) = i$. For each non-empty set $A \subseteq X$, we define the consideration set $E(A)$ to be the singleton containing only the chosen alternative $E(A) = \{C(A)\}$.

We can verify that the model is:
- Feasible: Because $C$ is a choice function, $C(A) \in A$ for all $A$. Hence, $E(A) = \{C(A)\} \subseteq A$, satisfying the feasibility restriction $E(A) \subseteq A$.
- Non-empty: Since $C(A)$ exists, $|E(A)| = 1$, so $E(A) \neq \emptyset$.
- Optimal: Evaluating the maximization problem over the consideration set $E(A)$, we see that $\arg\max_{x \in E(A)} u(x) = \arg\max_{x \in \{C(A)\}} u(x) = C(A)$

Because $C(A) = \arg\max_{x \in E(A)} u(x)$ holds identically for all menus $A$, the pair $(u, E)$ rationalizes $C$.


2. For the remainder of the question, add the restriction:   $$\text{If } x \in B \subset A, \text{ then } x \in E(A) \implies x \in E(B)$$
   This means that consideration gets harder in larger choice sets, so if $x$ is considered in the bigger set $A$, then it should also be considered in the smaller set $B$.  

   Is this restriction implied by each of the following choice procedures?

   - (a) In each choice set, consider the three cheapest cars (or all the cars if there are fewer than three).

Yes, the restriction is implied. Let $x \in B \subset A$ and suppose $x \in E(A)$. 

If $|A| \le 3$, then $E(A) = A$, which means $x \in A$. Since $B \subset A$, we have $|B| < |A| \le 3$, so $|B| \le 2$. By definition of the procedure, $E(B) = B$. Since $x \in B$, it follows immediately that $x \in E(B)$.

If $|A| > 3$, $x \in E(A)$ means that $x$ is among the three cheapest alternatives in $A$. Formally, the number of alternatives in $A$ that are strictly cheaper than $x$ is at most 2 $|\{z \in A \mid p(z) < p(x)\}| \le 2$. Because $B \subset A$, any item in $B$ cheaper than $x$ must also belong to $A$. 

Thus $\{z \in B \mid p(z) < p(x)\} \subseteq \{z \in A \mid p(z) < p(x)\}$. 

Taking cardinalities gives $|\{z \in B \mid p(z) < p(x)\}| \le \|\{z \in A \mid p(z) < p(x)\}| \le 2$

Therefore, there are at most 2 cars strictly cheaper than $x$ in $B$. Consequently, $x$ remains among the three cheapest cars in $B$ (or all cars if $|B| \le 3$), so $x \in E(B)$.

   - (b) In each choice set, consider the fastest car and the car with the best safety rating.

Yes, the restriction is implied. For any menu $S$, let $F(S) = \arg\max_{z \in S} \text{speed}(z)$ and $S^*(S) = \arg\max_{z \in S} \text{safety}(z)$. The consideration set is $E(S) = F(S) \cup S^*(S)$. Let $x \in B \subset A$ and suppose $x \in E(A)$. Then $x \in F(A)$ or $x \in S^*(A)$ (or both).

 If $x \in F(A)$, then $\text{speed}(x) \ge \text{speed}(z)$ for all $z \in A$. Because $B \subset A$, this inequality holds for all $z \in B$. Since $x \in B$, $x$ maximizes speed over $B$, so $x \in F(B) \subseteq E(B)$.

 If $x \in S^*(A)$, then $\text{safety}(x) \ge \text{safety}(z)$ for all $z \in A$. Because $B \subset A$, this inequality holds for all $z \in B$. Since $x \in B$, $x$ maximizes safety over $B$, so $x \in S^*(B) \subseteq E(B)$.

In either case, $x \in E(B)$, so the restriction holds.

   - (c) In each choice set, consider cars that are unusual: count up the number of cars in the choice set which are green, red, brown, etc., and consider only those that are of the least common color.

No, in this case the restriction does not hold. Consider a menu of cars defined by color, and let $A$ contain 5 cars: 3 green cars: $\{g_1, g_2, g_3\}$ and 2 red cars: $\{r_1, r_2\}$

In menu $A$: green frequency = 3, red frequency = 2, so the least common color in $A$ is Red, so $E(A) = \{r_1, r_2\}$. Thus, $r_1 \in E(A)$.

Now shrink the menu to $B \subset A$ by removing two green cars  $B = \{g_1, r_1, r_2\} \subset A$. Clearly $r_1 \in B$. In menu $B$, green frequency is 1 and red frequency is 2. Thus the least common color in $B$ is now green, so $E(B) = \{g_1\}$.

Since we have $r_1 \in B \subset A$ and $r_1 \in E(A)$, but $r_1 \notin E(B)$, thus the restriction is violated.


3. Is the following set of choices consistent with this model?
   $$C(\{x, y, z\}) = x$$$$C(\{x, y\}) = y$$
The above choices would only be consistent with the model if the set of alternatives being chosen against in $C(A)$ does not actually include y, such that $y \notin C(A)$ even though $y \in A$. $y$ may still be chosen in the smaller subset $B=\{x,y\}$ if it has a higher utility value, such that  $u(y) > u(x)$ in the true utility representation, but when considering the larger set $A=\{x,y,z\}$, somehow $y$ is dropped from the set of alternatives $E(A)$. Choosing $x$ from $\{x, y, z\}$ requires $x \in E(\{x, y, z\})$. By contraction consistency, $x \in E(\{x, y, z\}) \implies x \in E(\{x, y\})$. Since $x$ was chosen from $\{x, y, z\}$ despite $u(y) > u(x)$, $y$ simply must not be considered in the larger set such that $y \notin E(\{x, y, z\})$.


4. Show that the behavior in part 3 implies that $u(y) > u(x)$ if the model is correct.

Since $y$ was chosen from the smaller set $B$ even though $x$ was an available choice, the choice function that maximizes the underlying utility $u$ must ascribe a higher value to $y$ when the two are compared directly, such that $u(y) > u(x)$, holding strictly since the choice function is single valued and there is no indifference between alternatives.

Choosing $x$ from the larger set $A$ as in the case $C(\{x,y,z\})=x$ is still possible if the menu of alternatives drops $y$ from consideration (due to search costs, for example).


5. Show that this model does not imply $\text{WARP}$.

**WARP:** $$\text{If } x, y \in A \cap B, \, x \in C(A) \text{ and } y \in C(B) \implies x \in C(B)$$
Since this model permits choices of elements in subsets $B \subseteq A$ (like $y \in C(B)$ as in the example above) that are not chosen (i.e. $y \notin C(A)$) even though they are available in the superset $A$, then it violates WARP. 

As a counterexample, we again let $A=\{x,y,z\}$ and $B=\{x,y\}$. Take $A \cap B = B$ since the intersection of two nested sets $B \subseteq A$ will equal the subset. We have that $x,y \in A \cap B = B$. Then $C(A)=x$ from above, so $x \in C(A)$, and $C(B)=y$ so $y \in C(B)$ , thus all conditions of WARP are satisfied. However, clearly $x \notin C(B)$ since $C(B)=y$ as a single valued function with no indifference. Thus WARP would be violated since $x \in C(B)$ does not hold, so the model does not imply WARP.



6. Consider the following modification of the $\text{WARP}^*$ axiom of Question 1:

> **Axiom 2** For any set $S$, there exists a $b^* \in S$ such that, for any $T$ including $b^*$, if $C(T) \in S$ and $b^* = C(T')$ for some $T' \supset T$, then $C(T) = b^*$.

Show that the consideration set model described above does imply this behavior.

To remain consistent with our model above, let us redefine Axiom 2. 

To show: For any set A, there exists an $x^* \in A$ such that, for any set $B$ that includes $x^*$ (such that $x^* \in B$), if $C(B) \in A$ and $x^*=C(B')$ for some $B \subset B'$ , then $C(B)=x^*$.

First, let $A$ be an arbitrary non-empty set. Because $X$ is finite and there is no indifference, there exists a unique element that maximizes true utility over $A$ $x^* = \arg\max_{a \in A} u(a)$. Since it was chosen from the set $A$, clearly $x^* \in A$.

Then, let $B$ be any finite set such that $x^* \in B$, by assumption from the conditions. We know that the consideration set model above is single valued with no ties from indifference, such that $C(B)$ must be a single value, which we can call $y$, such that $C(B)=y$. By assumption, the choice must be non-empty such that $y$ must exist for any non-empty $B$.
 
From the conditions, we have that $C(B) \in A$ must hold, such that $y \in A$ is true, and that $x^* = C(B')$ for some superset $B'$ with $B \subset B'$. We aim to show that $y = x^*$.
 
Because $x^* = C(B')$, by Definition 1 we have $x^* \in E(B')$. Applying the contraction restriction ($\text{if } x \in B \subset B', \text{ then } x \in E(B') \implies x \in E(B)$), thus we  know that $x^* \in E(B)$.

Since $y = C(B)$, by Definition 1 $y$ maximizes $u$ over the consideration set $E(B)$, such that $y = \arg\max_{z \in E(B)} u(z)$. Because $x^* \in E(B)$, it must be that $u(y) \ge u(x^*)$. 

However, we know that $y \in A$, and by construction $x^* = \arg\max_{a \in A} u(a)$. Therefore $u(x^*) \ge u(y)$ must hold.

Combining both inequalities yields $u(y) = u(x^*)$. Because the choice function is single valued and there is no indifference, this implies $y = x^*$ and therefore $C(B) = x^*$.


7. Consider the following variant of the above model. Rather than the condition in part 2, we have the condition:
   $$E(A \setminus \{x\}) = E(A) \quad \text{if } x \notin E(A)$$
   In other words, if $x$ is not considered at $A$, then removing it does not change the consideration set. Does the resulting model still satisfy the axiom from part 6?

> **Axiom 2** For any set $S$, there exists a $b^* \in S$ such that, for any $T$ including $b^*$, if $C(T) \in S$ and $b^* = C(T')$ for some $T' \supset T$, then $C(T) = b^*$.

Rewritten again: To show: For any set A, there exists an $x^* \in A$ such that, for any set $B$ that includes $x^*$ (such that $x^* \in B$), if $C(B) \in A$ and $x^*=C(B')$ for some $B \subset B'$ , then $C(B)=x^*$.

In part 6, the contraction principle from the condition in part 2 is what allowed us to show that an element in the exclusion set of the superset will be considered in the exclusion set of a subset (if $x \in B \subset B'$, then  $x \in E(B') \implies x \in E(B)$). If $x^*$ can be considered in a superset $B'$ ($x^* \in E(B')$), but if when contracting from $B'$ down to $B$, we are not guaranteed contraction, then $x^*$ is not necessarily an element of $E(B)$. Thus we lose that $x^* \in E(B)$, such that we cannot say that $u(y) \ge u(x^*)$.