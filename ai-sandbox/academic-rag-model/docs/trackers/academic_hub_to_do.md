# Pending Improvements for the Academic Hub by Subproject


## Textbook Conversion
Things to fix in post-processing?
- subscripts and superscripts seem to get mixed up a lot (Hansen)
- internal links are not preserved (Hansen)
- Table of Contents does not link to anything
- Some complex Latex contains errors (Hansen)
- Inline latex equations often yield bad formatting in output
	- Dropping some hats from estimators
- Could add internal links to obsidian when figures or sections are mentioned



Example from Hansen:

Latex Error:

Q_{XX}^{-1} = \begin{bmatrix} Q_{11} & Q_{12} \\ Q_{21} & Q_{22} \end{bmatrix}^{-1} \stackrel{\text{def}}}{=} \begin{bmatrix} Q_{11}^{-1} & Q_{12}^{-1} \\ Q_{21}^{-1} & Q_{22}^{-1} \end{bmatrix} = \begin{bmatrix} Q_{11}^{-1} & -Q_{11}^{-1} Q_{12}^{-1} Q_{22}^{-1} \\ -Q_{22}^{-1} Q_{21} Q_{11}^{-1} & Q_{22}^{-1} \end{bmatrix} \quad (2.43)



#### 2.24 OMITTED VARIABLE BIAS

Again, let the regressors be partitioned as in [\(2.41\)](#page-76-0). Consider the projection of *Y* on *X*<sup>1</sup> only. Perhaps this is done because the variables *X*<sup>2</sup> are not observed. This is the equation

$$Y = X'_1 \gamma_1 + u \quad (2.45)$$

$$\mathbb{E} [X_1 u] = 0.$$

Notice that we have written the coefficient as γ<sup>1</sup> rather than β<sup>1</sup> and the error as *u* rather than *e*. This is because (2.45) is different than [\(2.42\)](#page-76-0). Goldberger (1991) introduced the catchy labels **long regression** for [\(2.42\)](#page-76-0) and **short regression** for (2.45) to emphasize the distinction.

Typically,  $\beta_1 \neq \gamma_1$ , except in special cases. To see this, we calculate

$$\begin{aligned} n_1 &= (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 Y] \\ &= (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 (X'_1 \beta_1 + X'_2 \beta_2 + \epsilon)] \\ &= \beta_1 + (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 X'_2] \beta_2 \\ &= \beta_1 + \Gamma_{12} \beta_2 \end{aligned}$$

where <sup>12</sup> = *<sup>Q</sup>*−<sup>1</sup> <sup>11</sup> *Q*<sup>12</sup> is the coefficient matrix from a projection of *X*<sup>2</sup> on *X*1, where we use the notation from Section [2.22.](#page-76-0)

Observe that γ<sup>1</sup> = β<sup>1</sup> + 12β<sup>2</sup> = β<sup>1</sup> unless <sup>12</sup> = 0 or β<sup>2</sup> = 0. Thus the short and long regressions have different coefficients. They are the same only under one of two conditions. First, if the projection of *X*<sup>2</sup> on *X*<sup>1</sup> yields a set of zero coefficients (they are uncorrelated), or second, if the coefficient on *X*<sup>2</sup> in [\(2.42\)](#page-76-0) is zero. The difference 12β<sup>2</sup> between γ<sup>1</sup> and β<sup>1</sup> is known as **omitted variable bias**. It is the consequence of the omission of a relevant correlated variable.




Another example:

In general, many parameters of interest can be written as a function of moments of  $Y$ . Notationally,  $\beta = g(\mu)$  and  $\mu = \mathbb{E}[h(Y)]$ . Here, the  $Y$  are the random variables,  $h(Y)$  are functions (transformations) of the random variables, and  $\mu$  is the expectation of these functions.  $\beta$  is the parameter of interest, and is the (nonlinear) function  $g(\cdot)$  of these expectations.

In this context, a natural estimator of  $\beta$  is obtained by replacing  $\mu$  with  $\hat{\mu}$ . Thus  $\hat{\beta} = g(\hat{\mu})$ . The estimator  $\hat{\beta}$  is often called a **plug-in estimator**. We also call  $\hat{\beta}$  a moment, or moment-based, estimator of  $\beta$ , since it is a natural extension of the moment estimator  $\hat{\mu}$ .

natural extension of the moment estimator  $\hat{\mu}$ .  
Take the example of the variance  $\sigma^2 = \text{var} [Y]$ . Its moment estimator is

$$\hat{\sigma}^2 = \hat{\mu_2 - \hat{\mu}_1^2 = \frac{1}{n} \sum_{i=1}^n Y_i^2 - \left( \frac{1}{n} \sum_{i=1}^n Y_i \right)^2.$$

This is not the only possible estimator for  $\sigma^2$  (there is also the well-known bias-corrected estimator), but  $\hat{\sigma}^2$  is a straightforward and simple choice.





Formatting:

Technically, the estimator β in [\(3.7\)](#page-99-0) only exists if the denominator is nonzero. Since it is a sum of squares, it is necessarily nonnegative. Thus β exists if *<sup>n</sup> <sup>i</sup>*=<sup>1</sup> *<sup>X</sup>*<sup>2</sup> *<sup>i</sup>* > 0.


Inline formatting drops hats that are present in nearby equations, should be easy to fix.
#### 3.8 LEAST SQUARES RESIDUALS

As a by-product of estimation, we define the **fitted value** *Yi* <sup>=</sup> *<sup>X</sup> i* β and the **residual**

$$\hat{e}_i = Y_i - \hat{Y}_i = Y_i - X'_i \hat{\beta}. \quad (3.14)$$

Sometimes *Yi* is called the predicted value, but this is a misleading label. The fitted value *Yi* is a function of the entire sample, including *Yi*, and thus cannot be interpreted as a valid prediction of *Yi*. It is thus more accurate to describe *Yi* as a *fitted* rather than a *predicted* value.

Note that *Yi* <sup>=</sup> *Yi* <sup>+</sup> *ei*, and

$$Y_i = X'_i \hat{\beta} + \hat{e}_i. \quad (3.15)$$

We make a distinction between the **error** *ei* and the **residual** *ei*. The error *ei* is unobservable, while the residual *ei* is an estimator. These two variables are frequently mislabeled, which can cause confusion.




Confusing letters in script form:

<span id="page-106-0"></span>When *Xi* contains a constant, an implication of [\(3.16\)](#page-105-0) is

$$\frac{1}{n} \sum_{i=1}^n \hat{c}_i = 0. \quad (3.17)$$

Thus the residuals have a sample mean of 0 and the sample correlation between the regressors and the residual is 0. These are algebraic results and hold true for all linear regression estimates.
