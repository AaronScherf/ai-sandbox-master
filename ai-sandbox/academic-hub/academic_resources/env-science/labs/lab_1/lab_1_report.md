By Aaron Scherf
## Introduction

In this lab, we take a quick introduction to Matlab through basic vector calculations and plotting, then apply these techniques at a more advanced level to a dataset from Hurricane Ivan to form some initial hypotheses about the relationship between hurricane trajectory and wind speed.

describe what you are doing, why (potentially just rephrasing the question), and how you do it. What matters is your reasoning and the description of the analysis, not only the results. Therefore clearly display your derivations and explain your reasoning.
## Matlab "Ball Toss" Plots

For the simple example to become familiar with Matlab, we calculated the height of a ball tossed in the air over time as a function of its initial velocity, using a standard constant for gravity. The plots below summarize the inverse parabolic relationship between height and time as the ball flies up into the air and then back down. The first plot shows the results for a single ball tossed at 15 m/s while the second uses a multi-plot loop to show the results for balls tossed at 5, 10, and 20 m/s. The plots were smoothed by calculating the values for each point in 0.1 second increments along the time axis.

![[lab_1_figures/figure_1.png]]


![[lab_1_figures/figure_2.png]]


## Hurricane Ivan

To analyze the relationship between hurricane trajectory and windspeed, we start by plotting the contours of the map for the approximate geographic area traversed by Ivan.

### Map Plotting

Our first map is quite hard to read, since the default color scale in Matlab is dark gray and the lines print in black.

![[lab_1_figures/figure_3.png]]

We can make the map easier to read (and confirm we are correctly oriented over Central America) by changing the background to white and axes to black.

![[lab_1_figures/figure_4.png]]

We can also view the same map with red contour lines on a black and gray background. Note that the data shifted from arbitrary units to latitude and longitude, since we switched to coordinate variables that are properly projected onto a (presumably Robinson) map surface.

![[lab_1_figures/figure_5.png]]


The plot changed between the first and third figures by switching from a basic contour function to a more sophisticated implementation that specifies the option color as red via the "r" parameter. We also explicitly label the axes and use the "figure" command to ensure that the plot is stored properly.
### Windspeed Data

The second key component of our analysis is windspeed information, to proxy the intensity of the center of the hurricane. We begin by mapping the latitude and longitude coordinates of the max windspeed over time. We are restricted to two variables in a simple plot like this, so we are unable to show windspeed as a continuous variable without further additions. It's also difficult to interpret where the hurricane was without our basemap of seashore contours.

![[lab_1_figures/figure_6.png]]

Another plot of the windspeed data can show the intensity, measured in knots over six hour intervals, to get a sense of when the storm was at its strongest and weakest over the data window.

![[lab_1_figures/figure_7.png]]

The units of the graph had to be inferred from the unlabeled data. By looking up the max windspeed of Ivan and finding it to be approximately 146 knots, the data was consistent with knots as the unit on the y-axis. The six hour increments were given but it was unclear if the x-axis is in hours or number of six hour increments; since most hurricanes do not hover near coastal areas for more than three days, we will assume the unit of measurement is hours, though we leave the 6-hour increment information to properly report the granularity of the data.

Assuming the x-axis is hours, the storm was officially categorized as a hurricane on the Safir-Simpson scale when its peak 1-minute sustained windspeed reached 64 knots, which would have been around hour 10 or 11. Given that a hurricane is classified as Category 4 when it reaches 113 knots, we can see that by around hour 22 the storm was firmly Category 4. Category 5 begins at 137 knots, which the hurricane seemed to reach a few times between hours 28 and 48. The "story" of this storm seems to be that it quickly reached very intense velocities and remained there for almost a full day, before dropping down to below the level of a hurricane around hour 58.

### Ivan Path and Intensity

To better understand the relationship between the path of the storm and its intensity, we plot the windspeed over the latitude and longitude in a three-dimensional figure.

![[lab_1_figures/figure_8.png]]

Interpreting the z-axis of windspeed is rather difficult in this perspective, however, so we first add a color bar for intensity and the contour map of the latitude and longitude of the shoreline to the base of the figure.

![[lab_1_figures/figure_9.png]]


This is helpful but at the current angle it is hard to tell where the storm was at its peak. We rotate the figure so that we are looking directly down onto the XY plane, as with a normal map. The color scale of the intensity helps us interpret the relative values.

From here, we can see that the storm was weaker when it arrived (presumably from the east, though we don't actually have timescale plotted here) but quickly gained strength as it approached the Caribbean, hitting its maximum intensity just south of Cuba. It maintained that Category 4 and 5 intensity as it passed between Cuba and the Yucatan Peninsula, before heading north towards the United States. While the majority of the USA is cut off on our contour map, we can see the southern tip of Florida, so we know the storm must have passed into the Florida / Alabama area before weakening back below the level of hurricane, then circling back around to pass over southern Florida and on towards Texas.

![[lab_1_figures/figure_9_above.png]]


Therefore we see that overlaying map layers and rotating our three dimensional plot can give us significantly more information than any of the isolated maps or two-dimensional intensity figures alone.