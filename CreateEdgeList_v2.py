#Import libraries
import arcpy
from arcpy.sa import *
import numpy as np
import pandas as pd
from skimage import graph
from matplotlib import pyplot as plt

arcpy.env.overwriteOutput = True

#Get input datasets: Patches and CostSurface
patchRaster = arcpy.GetParameterAsText(0)
costRaster = arcpy.GetParameterAsText(1)
edgeListFN = arcpy.GetParameterAsText(2)


# Message function
def msg(txt):
    print(txt)
    arcpy.AddMessage(txt)
    return

'''#Get input datasets: Patches and CostSurface
patchRaster = 'C:/Workspace/PronghornConnectivity/PronghornConnectivity.gdb/PatchCores'
if not arcpy.Exists(patchRaster):
    print("Cannot locate patch raster")

costRaster = 'C:/Workspace/PronghornConnectivity/PronghornConnectivity.gdb/CostSurface'
if not arcpy.Exists(costRaster):
    print("Cannot locate cost surface raster")

outRaster = 'C:/Workspace/PronghornConnectivity/PronghornConnectivity.gdb/CD{}'
edgeListFN = 'C:/Workspace/PronghornConnectivity/Scratch/EdgeList2.csv'''

#Get the spatial reference, extent, and lower left coordinates
sr = arcpy.Describe(costRaster).spatialReference
cellSize = arcpy.Describe(costRaster).meanCellWidth
extent = arcpy.Describe(costRaster).extent
llCorner = arcpy.Point(extent.XMin,extent.YMin)

#Create arrays of the patch and core rasters
arrPatch = arcpy.RasterToNumPyArray(patchRaster,
                                    lower_left_corner=llCorner,
                                    nodata_to_value=-9999)

arrCost = arcpy.RasterToNumPyArray(costRaster,
                                   lower_left_corner=llCorner,
                                   nodata_to_value=-9999)


#Create a list of patchIDs
patchIDs = np.unique(arrPatch).tolist()
patchIDs.remove(-9999)

#Initialize the arrayList and edgeList lists
arrList = []
edgeList = []

#Loop through each patch and compute its cost distance to all other patches
for patchID in patchIDs:
    msg("{}/{}".format(patchID,patchIDs[-1]))

    #Reclassify cost in source patch cells to zero
    arrCostMod = arrCost.copy()
    arrCostMod[arrPatch == patchID] = 0
    arrCostMod[arrCostMod == -9999] = 100000

    #Create the MCP object (Geometric accounts for diagonals)
    lg = graph.MCP_Geometric(arrCostMod, sampling=(cellSize, cellSize))

    #Get the index of a cell in the current patch ID
    i,j = np.where(arrPatch == patchID)
    startCells = list(zip(i,j))

    #Compute cost distances away from a source
    lcd = lg.find_costs(starts=startCells)[0]
    
    #Write the output to the edgelist
    for toID in patchIDs:
        if toID > patchID:
            edgeList.append((patchID, toID, lcd[arrPatch == toID].min()))

    #Add array to arrList
    #arrList.append(lcd)

#Write the edges to the edgeListFN
msg("Saving edges to {}".format(edgeListFN))
np.savetxt(edgeListFN,np.asarray(edgeList),
           comments='',
           delimiter=",", 
           fmt='%d,%d,%2.4f', 
           header=("From,To,Cost"))
