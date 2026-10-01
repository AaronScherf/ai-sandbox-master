%simple plot
gravity = -9.8;
velocity = 15;
time = -2*velocity/gravity;
time_vector = [0:0.01:time+0.5];
height = velocity*time_vector + 0.5*gravity*time_vector.^2;
height(height < 0) = NaN;

figure(1);
clf;
hold on;
plot(time_vector, height);
xlabel('Time (s)');
ylabel('Height (m)');
xlim([0, 4]);
grid on;
hold off;

% extra credit

velocities = [10, 15, 20];
max_velocity = max(velocities);
max_time = -2 * max_velocity / gravity;
max_time = max_time+1;
time_vector = 0:0.05:max_time;

figure(2);
clf;
hold on;

for i = 1:length(velocities)
    v_0 = velocities(i);
    t_root = -2 * v_0 / gravity;
    time_vector_multi = linspace(0, t_root, 100);
    height_multi = (v_0 .* time_vector_multi) + (0.5 * gravity .* (time_vector_multi.^2));
    plot(time_vector_multi, height_multi, 'LineWidth', 1.5, 'DisplayName', sprintf('v_0 = %d m/s', v_0));
end

t_max_global = max(-2 * velocities / gravity);
xlim([0, t_max_global]);
ylim([0, inf]);
xlabel('Time (s)');
ylabel('Height (m)');
grid on;
hold off;

%% hurrican ivan

load hurricane_ivan-1.mat;

figure(3);
clf('reset');
contour(basin, 1, 'k');

figure(4);
clf('reset');
set(gcf, 'Color', 'w');
set(gca, 'Color', 'w');
set(gca, 'XColor', 'k', 'YColor', 'k', 'ZColor', 'k');
set(gca, 'GridColor', 'k', 'GridAlpha', 0.3);
hold on;
contour(basin, 1, 'k');
hold off;

figure(5);
clf('reset');
hold on;
contour(basin_lon, basin_lat, basin, 1, 'r');
xlabel('Longitude');
ylabel('Latitude');
hold off;

figure(6);
clf;
hold on;
plot(ivan_lon, ivan_lat, '+');
xlabel('Longitude');
ylabel('Latitude');
grid on;
hold off;


figure(7);
clf;
hold on;
plot(ivan_windspeed);
xlabel('Time (6 hour increments)');
ylabel('Windspeed (knots)');
grid on;
hold off;


figure(8);
clf;
hold on;
plot3(ivan_lon,ivan_lat,ivan_windspeed);
view(3); 

xlabel('Longitude');
ylabel('Latitude');
zlabel('Windspeed (knots)');
grid on;
hold off;


figure(9);
clf;
hold on;

lon = ivan_lon(:);
lat = ivan_lat(:);
wind = ivan_windspeed(:);

surface([lon lon], [lat lat], [wind wind], [wind wind], ...
    'FaceColor', 'none', ...
    'EdgeColor', 'interp', ...
    'LineWidth', 2);

contour(basin_lon, basin_lat, basin, [1 1], 'r');

colormap(parula);
cb = colorbar;
cb.Label.String = 'Windspeed (knots)';

view(3); 

xlabel('Longitude');
ylabel('Latitude');
zlabel('Windspeed (knots)');
grid on;
hold off;


%% Export figures

fig_handles = findall(0, 'Type', 'figure');

for i = 1:length(fig_handles)
    current_fig = fig_handles(i);

    fig_num = current_fig.Number;
    file_name = sprintf('Figure_%d.png', fig_num);

    exportgraphics(current_fig, file_name, 'Resolution', 300);
end