global root "${dropbox}/columbia/first-year/metrics-III/ps4"

eststo clear 

use "${root}/lowbirth", clear

egen id = group(state)

xtset id year

* Random effects model
eststo re : xtreg lowbrth d90 afdcprc lphypc lbedspc lpcinc lpopul, re vce(conventional)

* Fixed effects model
eststo fe : xtreg lowbrth d90 afdcprc lphypc lbedspc lpcinc lpopul, fe vce(conventional)

* Fixed effects model, cluster
eststo fec : xtreg lowbrth d90 afdcprc lphypc lbedspc lpcinc lpopul, fe vce(cluster id)


* Table
esttab using "${root}/regs.tex", se nocons b(3) ///
	coeflabels( ///
		d90 "$ \vb{1}(t = 1990)$" ///
		afdcprc " Pop. AFDC" ///
		lphypc "$ \log(\text{phypc})$" ///
		lbedspc "$ \log(\text{bedspc})$" ///
		lpcinc "$ \log(\text{pcinc})$" ///
		lpopul "$ \log(\text{pop})$") ///
		mtitles("\bf{Random Effects}" "\bf{Fixed Effects}" "\bf{Fixed Effects, Clustered (State)}") ///
		replace booktabs ///
		substitute(_ _)