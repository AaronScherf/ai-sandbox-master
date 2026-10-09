* Set root directory 
global root "${dropbox}/columbia/first-year/metrics-III/ps2"

* Load data
use "${root}/AJR2001", clear

* Cleared stored results 
eststo clear 

* Run OLS regression 
eststo A : reg loggdp risk latitude asia africa other 

* Run first stage, obtain residuals 
reg risk logmort0 latitude asia africa other
predict first_stage_res, res

* Run control function regression 
eststo B : reg loggdp risk latitude asia africa other first_stage_res 
* Run 2SLS 
eststo C : ivregress 2sls loggdp latitude asia africa other (risk  = logmort0), vce(unadjusted)

* Run first stage, obtain predicted values 
reg risk logmort0 latitude asia africa other
predict risk_hat, xb
* Run second stage 
eststo D : reg loggdp risk_hat latitude asia africa other 

* Table 1
esttab A B C D using "${root}/regression_table.tex", se ///
	nocons ///
	coeflabels(	risk "Risk" ///
				latitude "Latitude" ///
				asia "Asia" ///
				africa "Africa" ///
				other "Other" ///
				logmort0 "$log(\text{mortality})$" ///
				first_stage_res "First Stage Residuals" ///
				risk_hat "$\widehat{\text{risk}}$" ) ///
	mtitles("OLS" "Control Function" "2SLS" "Manual 2SLS") ///
	booktabs replace
	
* Quadratic mortality 
gen logmort0_sq = logmort0^2

* Run 2SLS and efficient GMM, homoskedastic
eststo A : ivregress 2sls loggdp (risk  = logmort0), vce(unadjusted)
eststo B : ivregress gmm loggdp (risk  = logmort0), wmatrix(unadjusted)

* Run 2SLS and efficient GMM, homoskedastic, include quadratic instrument 
eststo C : ivregress 2sls loggdp (risk  = logmort0 logmort0_sq), vce(unadjusted)
eststo D : ivregress gmm loggdp (risk  = logmort0 logmort0_sq), wmatrix(unadjusted)
estat overid // get j-test 

* Store j-test and p-value for table 
estadd local jstat "`: di %4.2f r(HansenJ)' (`: di %4.2f r(p_HansenJ)')": D

* Table 2 
esttab A B C D using "${root}/gmm_table.tex", se ///
	nocons ///
	coeflabels(	risk "Risk" ///
				logmort0 "$log(\text{mortality})$" ///
				logmort0_sq "$log(\text{mortality})^2$") ///
	mtitles("2SLS" "GMM" "2SLS" "GMM") ///
	stats(jstat N, labels("\textit{J}-statistic" "\textit{N}")) ///
	mgroups("No Quadratic Term" "Quadratic Term", pattern(1 0 1 0) ///
	prefix(\multicolumn{@span}{c}{) suffix(}) ///
	span erepeat(\cmidrule(lr){@span})) ///
	replace ///
	booktabs