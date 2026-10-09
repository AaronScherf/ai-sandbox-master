clear 
set more off

cd "C:\Users\Pat\Dropbox\Documents\Columbia\CU - Year 1\Econometrics\Part 3\Problem Sets\PS2"

import delimited "GDPC1.csv"

gen delta_g = .
replace delta_g = ( gdpc1[_n+1] -  gdpc1[_n] ) /  gdpc1[_n]


forval i=1/4 {
gen delta_g_L`i' = delta_g[_n-`i']
}

*Tsset
gen date_my = date(date, "YMD")
format date_my %td
gen date_qy = qofd(date_my)
format date_qy %tq

keep if  date_qy>=q(1960q1) & date_qy<=q(2019q4)
tsset date_qy

*NW std errors
eststo clear

newey delta_g, lag(0)
eststo nw0

newey delta_g delta_g_L1, lag(1)
eststo nw1

newey delta_g delta_g_L1 delta_g_L2, lag(2)
eststo nw2

newey delta_g delta_g_L1 delta_g_L2 delta_g_L3, lag(3)
eststo nw3

newey delta_g delta_g_L1 delta_g_L2 delta_g_L3 delta_g_L4, lag(4)
eststo nw4

esttab using "q3b.tex", cells(b se) replace
eststo clear

*Robust std errors, not NW -- reporting AIC
reg delta_g, r
eststo r0
estat ic

reg delta_g delta_g_L1, r
eststo r1
estat ic

reg delta_g delta_g_L1 delta_g_L2, r
eststo r2
estat ic

reg delta_g delta_g_L1 delta_g_L2 delta_g_L3, r
eststo r3
estat ic

reg delta_g delta_g_L1 delta_g_L2 delta_g_L3 delta_g_L4, r
eststo r4
estat ic

esttab using "q3c.tex", cells(b se) replace
eststo clear
