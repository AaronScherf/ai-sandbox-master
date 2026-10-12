 %SOURCEADVECTION.M
 
%advection of substance with a source, s. hsiang 
%(smh2137@columbia.edu), aug, 2007

timelimit = 30;
ct = c;
u = 1;

%source is at the 10th gridcell
%sourcelocation = [zeros(1,40), ones(1,5), zeros(1,55)];

for i = 1:timelimit;
    dcdx = diff( [0, ct(i,:)] );
    %here we now have dc/dt is not zero, but equal to the source term
    DcDt = .05 * sourcelocation - u * dcdx;
    newc = ct(i,:) + DcDt;
    ct = [ct; newc];
end
