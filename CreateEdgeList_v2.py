#Import libraries
import arcpy
import numpy as np
from skimage import graph

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

#Initialize the progressor
step = 0
steps = len(patchIDs)
arcpy.SetProgressor("step", "Computing Cost Distances...",step,steps,1)

#Initialize the arrayList and edgeList lists
arrList = []
edgeList = []

#Loop through each patch and compute its cost distance to all other patches
for patchID in patchIDs:
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

    #Compute cost distances away from a source
    lcd = lg.find_costs(starts=startCells)[0]
    
    #Write the output to the edgelist
    for toID in patchIDs:
        if toID > patchID:
            edgeList.append((patchID, toID, lcd[arrPatch == toID].min()))

    #Add array to arrList
    arrList.append(lcd)
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
