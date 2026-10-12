%RADIATION.M
%A vertical column box model of atmospheric radiation, s. hsiang 
%(smh2137@columbia.edu), aug, 2007

%note: the percentage symbol '%' means that a line is just a comment and 
%tells matlab that anything after the symbol is not important. Don't 
%transcribe commented lines, but insert your own comments where you find 
%it useful to do so.

%this is going to be the vector where we solve for the incidence at the top 
%of each box. we start with a 1 at the top of the atmosphere since we 
%normalize the solar constant to 1. There are ten zeros after it becasue 
%we haven't solved for the incidence at the other laysers yet. The last 
%zero is for incidence at the surface.

incident = [1, zeros(1,10)]';

%trapped is the vector that will store how much of the radiation gets "trapped" 
%in each layer through absorbtion. all zeros right now.

trapped = zeros(10,1);

%escaping is the vector storing how much radiation comes out the bottom of 
%each box

escaping = zeros(10,1);

%this for loop is going to going to count from 1 to 10, each time it 
%begins the loop, it assigns to i the current number of that count. we 
%solve the model from the top of the atmosphere, by looking at how much 
%gets absorbed (trapped) in each layer, then figuring out how much escapes 
%out the bottom, and then note that everything that comes out of the bottom 
%of one layer must go into the top of the next.

for i = 1:10;
    trapped(i) = incident(i) * absorb(i); 
    escaping(i) = incident(i) - trapped(i); 
    incident(i+1) = escaping(i);
end

%after the program completes, we can know we're done by printing something
%in the command window that tells us that we're done.

disp('done. that was super easy.')