
# Smart Beneficiary Targeting Validation

Taking the severity of different needs into account, how effective is funding for individual projects for different sectors in countries with many projects? How do projects compare to each other? 


# Why: 
Quantifying spending by project sector to identify projects that made good use of resources, using a global average of projects as a baseline. 

# How did we solve this: 
To quantify the efficacy of project spending, we created an Efficiency Ratio: Expected budget/actual spending. 

Expected budget consisted of the average budget per cluster divided by the budget or allocation per person. Cluster names were gotten from the projects dataset and were matched by name. 

Lower values indicated projects were over-funded, while higher values indicated projects were under-funded, with 1 indicating a perfect balance. We initially wanted to 
add in aggregated severity scores for each project cluster 

# What did we build to solve this?
We built a dashboard showcasing data about the efficiency scores on a project and country basis (across 7 war-torn countries) with multiple projects, showing our efficiency scores  with the factors that were part of our efficiency score, a K-means clustering showcasing the performance of projects within sectors across countries. We also incorporated details for users to get 
