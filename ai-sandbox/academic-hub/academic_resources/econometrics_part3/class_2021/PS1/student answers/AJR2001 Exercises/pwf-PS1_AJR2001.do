clear
set more off

********************************************************************************
********************************************************************************
*Econometrics - PS1
********************************************************************************
********************************************************************************
*Load directory
cd "C:\Users\Pat\Dropbox\Documents\Columbia\CU - Year 1\Econometrics\Part 3\Problem Sets\PS1\AJR2001"

*Load data
use AJR2001, clear

********************************************************************************
*Q8, part II
********************************************************************************


*B) Regress the above with OLS

	*test regression to match Hansen
	reg loggdp risk

	*regression for part B)
	reg loggdp risk latitude asia africa other


*C) Run the first stage regression with risk as dependent variable

	*test regression to match Hanset
	reg risk logmort0

	*Regression for part C)
	reg risk logmort0 latitude asia africa other

	*Obtain residuals (and predicted value)
	predict resid_fsreg, residuals	
	predict pred_risk
	
*D) Include the residuals obtained in part C) in the structural regression as a control
	reg loggdp risk latitude asia africa other resid_fsreg
	
*E) Obtain 2SLS estimates
	
	*Use stata 2sls command
	ivregress 2sls loggdp (risk = logmort0) latitude asia africa other
	
*F) The predicted value was obtained in part c) after original 1st stage

	*Use fitted values from 1st stage reg
	reg loggdp pred_risk latitude asia africa other

*G) The coeffs are the same but the SEs differ.
	*2sls command is likely doing an appropriate adjustment
	*using the predicted (generated) values alone does not provide accurate standard erros
	*The control function has a similar generated regressor problem
	

********************************************************************************
*Q13, part III
********************************************************************************

*A) run 2sls and GMM

	*2SLS
	ivregress 2sls loggdp (risk = logmort0)
	
	*GMM (2SLS) - test with homoskedastic (should be same as 2SLS)
	ivregress gmm loggdp (risk = logmort0), wmatrix(unadjusted)

	*GMM - efficient weighting needs wmatrix(robust)
	ivregress gmm loggdp (risk = logmort0), wmatrix(robust)
	
	*The coeffs are the same but the SE on GMM are larger
	
*B) Now include logmort0^2 as an additional instrument

	*generate variable
	gen logmort0_sq = logmort0^2
	
	*2SLS
	ivregress 2sls loggdp (risk = logmort0 logmort0_sq)
	
	*GMM
	ivregress gmm loggdp (risk = logmort0 logmort0_sq), wmatrix(robust)
	
	*The coeffs are different (GMM slightly smaller) and SE are smaller for GMM

*C) Report J statistic test of overID
	
	*Post estimation of reg w/ GMM should report J-test
	estat overid
	
	*Value of >0.05 implies over ID'd

