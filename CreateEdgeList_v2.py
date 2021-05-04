'''
Create Edge List
Spring 2021 - John.Fay@duke.edu

This script takes two datasets - a patch raster and a cost raster
and compute an edge list comprised of the least cost distances 
between all patch pairs.

Optionally it will also produce a 3D stacked numpy array comprised
of a layer for each patch (D1) and the least cost distance to
that patch for each pixel (D2/3)

Spring 2021 - John.Fay@duke.edu
'''


#%%Import libraries
import arcpy
import numpy as np
from skimage import graph

arcpy.env.overwriteOutput = True

#%% Get input datasets: Patches and CostSurface
debug = True
if debug:
    patchRaster = '..\\Data\\ENH_LCP_ModelInputs_Final2019.gdb\\S_Patches_60ha'
    orig_costRaster = '..\\Data\\ENH_LCP_ModelInputs_Final2019.gdb\\S_CostSurface'
    edgeListFN = '..\\Scratch\\edgelist.csv'
else:
    patchRaster = arcpy.GetParameterAsText(0)
    orig_costRaster = arcpy.GetParameterAsText(1)
    edgeListFN = arcpy.GetParameterAsText(2)


#%% Message function
def msg(txt):
    print(txt)
    arcpy.AddMessage(txt)
    return

#%% Subset the cost raster to match dimensions of the patch raster
arcpy.env.cellSize = patchRaster
arcpy.env.extent = patchRaster
arcpy.env.snapRaster = patchRaster

msg("Subsetting cost raster")
costRaster = arcpy.sa.ExtractByRectangle(orig_costRaster, patchRaster, "INSIDE")

#%% Get the spatial reference, extent, and lower left coordinates
sr = arcpy.Describe(costRaster).spatialReference
cellSize = arcpy.Describe(costRaster).meanCellWidth
extent = arcpy.Describe(costRaster).extent
llCorner = extent.lowerLeft

#%% Create arrays of the patch and core rasters
arrPatch = arcpy.RasterToNumPyArray(patchRaster,
                                    lower_left_corner=llCorner,
                                    nodata_to_value=-9999)

arrCost = arcpy.RasterToNumPyArray(costRaster,
                                   lower_left_corner=llCorner,
                                   nodata_to_value=-9999)

#%% Create a list of patchIDs
patchIDs = np.unique(arrPatch).tolist()
patchIDs.remove(-9999)

#%% Initialize the progressor
step = 0
steps = len(patchIDs)
arcpy.SetProgressor("step", "Computing Cost Distances...",step,steps,1)

#%% Initialize the arrayList and edgeList lists
arrList = []
tracebackList = []
edgeList = []

#%% Loop through each patch and compute its cost distance to all other patches
for patchID in patchIDs[:1]:
    arcpy.SetProgressorLabel("Patch {} of {}".format(patchID,steps))

    #Reclassify cost in source patch cells to zero
    arrCostMod = arrCost.copy()
    arrCostMod[arrPatch == patchID] = 0
    arrCostMod[arrCostMod == -9999] = 100000

    #Create the MCP object (Geometric accounts for diagonals)
    lg = graph.MCP_Geometric(arrCostMod, sampling=(cellSize, cellSize))

    #Get the index of a cell in the current patch ID
    i,j = np.where(arrPatch == patchID)
    startCells = list(zip(i,j))

    #Compute cost distance and traceback arrays from a source
    cd_array, tb_array = lg.find_costs(starts=startCells)
    
#Write the output to the edgelist
    for toID in patchIDs:
        if toID > patchID:
            edgeList.append((patchID, toID, cd_array[arrPatch == toID].min()))

    #Add arrays to arrLists
    arrList.append(cd_array)
    arcpy.SetProgressorPosition()

#Write the edges to the edgeListFN
arcpy.SetProgressor("default", "Saving Edges to {}".format(edgeListFN))
np.savetxt(edgeListFN,np.asarray(edgeList),
           comments='',
           delimiter=",", 
           fmt='%d,%d,%2.4f', 
           header=("From,To,Cost"))

#Write out cost surface arrays
arcpy.SetProgressor("default", "Stacking arrays")
arrStack = np.stack(arrList)

arcpy.SetProgressor("default", "Saving Cost Distance Arrays to {}".format(edgeListFN))
np.save(edgeListFN.replace("csv","npy"),arrStack)
