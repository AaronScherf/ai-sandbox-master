/*
Econometrics III - Problem Set 2
Danny Onorato, 2022-02-22
*/

global root "${dropbox}/columbia/first-year/metrics-III/ps3"

* ------------------------------------------------------------------------------
* Question 2
* ------------------------------------------------------------------------------

clear all 
set seed 2222022
loc i = 0

foreach alpha in 0.10 0.98 -0.10 -0.98 {
	
	clear
	set obs 100 
	
	loc ++i 
		
	scalar alpha = `alpha' 

	gen e = 0
	gen y = .
	gen t = _n 	
	
	tsset t

	replace e = 1 if t == 1
	replace y = e if t == 1 

	replace y = alpha*L.y + e if t > 1

	tw connected y t, name("IR_`i'", replace) nodraw msize(small) title("Alpha: `alpha'", size(small) color(gray)) 

	replace e = rnormal(0,1)
	replace y = e if t == 1
	replace y = alpha*L.y + e if t > 1

	tw connected y t, name("normal_`i'", replace) msize(small) title("Alpha: `alpha'", size(small) color(gray))

	ac y, lags(20) ciopts(color(none)) note("") name("acf_`i'", replace) title("Alpha: `alpha'", size(small) color(gray))
}
 
foreach pre in IR normal acf { 
	graph combine `pre'_1 `pre'_2 `pre'_3 `pre'_4 
	graph export "${root}/`pre'.pdf", replace
}


* ------------------------------------------------------------------------------
* Question 3
* ------------------------------------------------------------------------------

* Load data 
import delimited using "${root}/GDPC1.csv", clear

* Generate Stata native date variable
gen t = date(date, "YMD")
* Generate a quarter variable using the date variable
gen q = qofd(t)
* Format the variables to look human readable
format t %td
format q %tq

* Set the time series structure, use q for quarterly data
tsset q

* Growth
gen gdp_growth = (gdpc1 - L.gdpc1) / L.gdpc1

* Sample restrictions
keep if inrange(q, qofd(mdy(1,1,1960)), qofd(mdy(10,1,2019)))

* AR
forval i=0/4 {
	local M = ceil(0.75*(_N-`i')^(1/3))
	eststo AR`i': newey L(0/`i').gdp_growth, lag(`M')
	estadd local M "`M'": AR`i'
}

* Table
esttab using "${root}/newey_west.tex", se nonum b(3) ///
	coeflabels( ///
		L.gdp_growth "$ y_{t-1}$" ///
		L2.gdp_growth "$ y_{t-2}$" ///
		L3.gdp_growth "$ y_{t-3}$" ///
		L4.gdp_growth "$ y_{t-4}$" ///
		_cons "constant") ///
		mtitles("AR(0)" "AR(1)" "AR(2)" "AR(3)" "AR(4)") ///
		stats(N M, labels("\textit{N}" "Newey-West \textit{M}") fmt(0 0)) ///
		replace booktabs ///
		substitute(_ _)
	
* AR, robust errors only
forval i=0/4 {
	eststo AR`i': regress L(0/`i').gdp_growth, robust
	estat ic
	local aic : di %3.0f r(S)[1,"AIC"]
}	


* Table
esttab using "${root}/aic.tex", se nonum b(3) ///
	coeflabels( ///
		L.gdp_growth "$ y_{t-1}$" ///
		L2.gdp_growth "$ y_{t-2}$" ///
		L3.gdp_growth "$ y_{t-3}$" ///
		L4.gdp_growth "$ y_{t-4}$" ///
		_cons "constant") ///
		mtitles("AR(0)" "AR(1)" "AR(2)" "AR(3)" "AR(4)") ///
		stats(N aic, labels("\textit{N}" "AIC") fmt(0 1)) ///
		booktabs replace ///
		substitute(_ _)
		