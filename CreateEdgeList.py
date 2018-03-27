
#Import libraries
import arcpy
from arcpy.sa import *
import numpy as np
import pandas as pd

# Message function
def msg(txt):
    print(txt)
    arcpy.AddMessage(txt)
    return

#Get input datasets: Patches and CostSurface
patchRaster = arcpy.GetParameterAsText(0)
costSurface = arcpy.GetParameterAsText(1)
maxCostDistance = arcpy.GetParameterAsText(2)
outFile = arcpy.GetParameterAsText(3)

#---Get list of patch IDs---
#Create empty list
patchIDs = []
#Convert values to numpy array
arr = arcpy.da.TableToNumPyArray(patchRaster,"Value")
#Loop through records
for i in arr.tolist():
    patchIDs.append(i[0])

#---Loop through each patch ID---
for patchID in patchIDs[:5]:
    msg("Running patch {}".format(patchID))

    #Get the source patch
    msg("...Isolating source patch...")
    thePatch = Con(patchRaster,patchID,"","VALUE = {}".format(patchID))

    #If a cost distance input is provided compute cost distance
    if costSurface:
        #Calculate cost distance from the patch
        msg("...Computing cost distance...")
        theCostDist = CostDistance(thePatch,costSurface,maxCostDistance)
    else:
        #Calculate Euclidean distance
        msg("...Computing Euclidean distance...")
        theCostDist = EucDistance(thePatch,maxCostDistance)
        
    #Computing LCP distance to other Patches
    msg("...Computing LCP distances to other patches")
    outZTable = "zmin{}".format(patchID)
    zMin = ZonalStatisticsAsTable(patchRaster,"Value",theCostDist,outZTable,"DATA","Minimum")

    ##Convert table to a pandas dataframe
    msg("...Creating table")
    #Convert arcTable to numpy Array
    arrZS = arcpy.da.TableToNumPyArray(outZTable,['VALUE','MIN'])
    #Convert to pandas dataframe
    dfZS = pd.DataFrame(arrZS)
    #Rename columns
    dfZS.columns = ['To_ID','Cost']
    #Add the from ID column
    dfZS['From_ID'] = patchID
    #Rearrange columns
    dfZS = dfZS[["From_ID","To_ID","Cost"]]

    #If first table, make the output df; otherwise append records
    if patchID == patchIDs[0]:
        dfOut = dfZS[dfZS.Cost > 0]
    else:
        msg("...Adding records")
        dfOut = pd.concat([dfOut,dfZS[dfZS.To_ID > dfZS.From_ID]])

#Write the list to csv file
msg("Saving edge list to {}".format(outFile))
dfOut.to_csv(outFile,index=False)

