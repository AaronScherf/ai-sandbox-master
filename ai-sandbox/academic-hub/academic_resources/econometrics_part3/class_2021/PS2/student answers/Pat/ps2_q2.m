clear 
%Preliminaries - Define t, periods, alpha
t = 100;
periods = linspace(1,t);
alpha = [0.1, 0.98, -0.1, -0.98]'; 

%% Shock in time t = 1; create shock, matrix for y
shock1 = zeros(4,t);
shock1(:,1) = 1;
y1 = zeros(4,t);

for per = 1:t
        if (per ==1 )
            y1(:,1) = shock1(:,1);
        else 
            y1(:,per) = alpha.*y1(:,per-1) + shock1(:,per);
        end
end

%Plot
figure(1)
sgtitle("AR(1), one shock")
subplot(2,2,1);
plot(periods, y1(1,:))  
xlabel('t');
title("Alpha=0.1");
subplot(2,2,2);
plot(periods, y1(2,:))  
xlabel('t');
title("Alpha=0.98");
subplot(2,2,3);
plot(periods, y1(3,:))  
xlabel('t');
title("Alpha=-0.1");
subplot(2,2,4);
plot(periods, y1(4,:))  
xlabel('t');
title("Alpha=-0.98");
saveas(gcf,'q2_ar1_oneshock','jpeg')

%% Normally distributed shocks in all periods; create shock, matrix for y
shock2 = normrnd(0,1,1,100);
shock2 = repmat(shock2, 4, 1);
y2 = zeros(4,t);

for per = 1:t
        if (per ==1 )
            y2(:,per) = shock2(:,per);
        else 
            y2(:,per) = alpha.*y2(:,per-1) + shock2(:,per);
        end
end

%Plot
figure(2)
sgtitle("AR(1), many shocks")
subplot(2,2,1);
plot(periods, y2(1,:))  
xlabel('t');
title("Alpha=0.1");
subplot(2,2,2);
plot(periods, y2(2,:))  
xlabel('t');
title("Alpha=0.98");
subplot(2,2,3);
plot(periods, y2(3,:))  
xlabel('t');
title("Alpha=-0.1");
subplot(2,2,4);
plot(periods, y2(4,:))  
xlabel('t');
title("Alpha=-0.98");
saveas(gcf,'q2_ar1_manyshocks','jpeg')

%% Autocorrelations
%Plot autocorrelations
figure(2)
sgtitle("AR(1), autocorrelations, many shocks")
subplot(2,2,1);
autocorr(y2(1,:));
title("Alpha=0.1");
subplot(2,2,2);
autocorr(y2(2,:));
title("Alpha=0.98");
subplot(2,2,3);
autocorr(y2(3,:));
title("Alpha=-0.1");
subplot(2,2,4);
autocorr(y2(4,:));
title("Alpha=-0.98");
saveas(gcf,'q2_ar1_manyshocks_autocorr','jpeg')