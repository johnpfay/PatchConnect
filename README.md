---
Title: PatchConnect
Version: 2.0
Author: John Fay (John.Fay@duke.edu)
Date: Spring 2021
---

# Patch Connect

> **REQUIREMENTS**:
>
> * ArcGIS Pro 2.6.3 or above
> * SciKit Image package installed

This is an ArcGIS Pro (v2.6.3) workspace that includes a toolbox and Python scripts to compute centrality metrics for patches in a provided patch raster and a cost surface raster. The general workflow includes:

#### Step 1: Computing the edge list for all patch pairs

* Subsetting both the patch and cost rasters to their intersecting areas (so each are the same size).

* Converting them to NumPy arrays

* Iterating through each source patch, and in each iteration:

  * Computing a [SciKit-Image MCP-geographic](https://scikit-image.org/docs/0.7.0/api/skimage.graph.mcp.html) graph object connecting each pixel to that source patch

  * Iterating through each destination patch, and in each iteration:

    * Computing the minimum cost between patches

      **Note: some patch pairs may not have viable connections are dropped from the outputs*

    * Creating a polyline feature of the least cost path [optional] 

* On processing all patch pair combinations, the following outputs are created:

  * An **edge list csv file** listing each patch pair and the least cost between them.
  * An optional **edge feature class** containing all the polyline least cost paths between patches
  * A **stacked numpy export file (.npy)** file containing cost distance arrays for each source patch

#### Step 2. Summarizing the graph and computing the threshold distance of maximum connectivity

* Iterate through a sequence of cost distance thresholds (user sets minimum, maximum, and step). 

* At each distance threshold, the number of connected components and the diameter of the largest component is computed

* From the resulting table, the user plots diameter vs distance threshold, looking for an inflection point. *This inflection point indicates the point of maximum connectivity*.

  > **Why does the inflection point indicate maximum connectivity?**
  >
  > At very low cost distance thresholds, diameter is low because most components are very small, made up of just a few nodes. As the threshold increases, more nodes are connected and the diameter grows. However, once the cost threshold reaches a certain point new connections are made to nodes that are already connected, albeit by longer paths. Thus the diameter starts to *decrease*. At this decrease, we are simply making shortcuts, not connecting more nodes. 

#### Step 3. Computing patch connectivity attributes

* Patch connections (edges) above the threshold identified above are discarded and a graph is created with the remaining ones.
* The following graph centrality attributes are computed for each node/patch:
  * **Degree Centrality**: The number of patches connected to the patch. The likelihood that the patch will be visited based on its connectivity to other patches.
  * **Betweenness Centrality**:  The relative frequency among least cost paths in which the patch is found. An indication of the patch's importance in maintaining overall connectivity among patch pairs. 
  * **Closeness Centrality**:  The relative closeness the patch is to all other patches.
  * **Connected Area**: The sum area of all patches connected to the current patch.
  * **IDW Area**: The sum area *discounted by distance* from the current patch.
* These are output as a CSV file with a row for each patch. 

---

### How to use this tool

1. Download to your local machine.

2. Place your patch and cost rasters in the `Data` folder.

3. Open the ArcGIS Pro Project file (`PatchConnect.aprx`)

   * ArcGIS Pro must be version 2.6.3 or greater for this to open successfully.
   * You must have the `SciKit Image` package installed in your Python environment.

4. Open the `Patch Connect Workflow` tool

5. Update the `Patch Raster` and `Cost Raster` inputs in the "1. Compute the edge list for each patch pair" section and run the tool.

   > This tool can take a long time to run, proportional to the number of patches in your dataset, possibly on the order of hours if you have > 300 patches. 
   >
   > By default, it's set to also produce a feature class of least cost path polylines. **To speed up analysis you can clear the `Edges.shp` output**. Of course, you then won't have the least cost path features.

6. Examine the resulting edge list produced, noting the range of costs. 

7. When complete, run the "2. Evaluate costs and enter appropriate cost step", entering reasonable values for the minimum and maximum costs as well as step interval. 

   > What are "reasonable" values for minimum and maximum costs? 
   >
   > This takes a bit of trial and error, knowing that each cost threshold evaluated consumes time. I recommend an initial run with perhaps a minimum slightly above the minimum cost seen in the edge list and a maximum at about 75% the maximum of the edge list and use a very large step interval. If no clear inflection point is found, lower the minimum and increase the maximum. 
   >
   > When an infection point is found, move the minimum and maximum closer to that distance and decrease the step interval to get a more precise distance value. You probably don't need to get too precise as you likely have some uncertainty in your overall cost values...

8. When complete, add the resulting `GraphSummary.csv` file to your map and plot Diameter vs Distance. Look for an inflection point and note the distance where it occurs. 

9. Finally, run the "3. After examining the plot of diameter v distance, select a cost threshold" tool. Enter the distance found in the previous step. 

10. Optionally, join the CSV table to your patch raster attribute table and view patches by their connectivity metrics.

