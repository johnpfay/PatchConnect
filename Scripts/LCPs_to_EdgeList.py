#LCPs_to_EdgeList.py
#
# Converts a set of least cost paths (located in a provided geodatabase)
# into an edge list
#
# Spring 2022
# John.Fay@duke.edu

#Import packages
import os
import arcpy
import numpy as np
import pandas as pd

#Get Inputs
LCP_geodatabase = arcpy.GetParameterAsText(0)
Output_EdgeList = arcpy.GetParameterAsText(1)

#Get a list of the feature classes
arcpy.env.workspace = LCP_geodatabase
arcpy.AddMessage('Reading in LCP feature classes')
LCPS = arcpy.ListFeatureClasses()
arcpy.AddMessage(f'{len(LCPS)} paths returned')

#Iterate through each and build a dataframe 
arcpy.AddMessage('Converting data to dataframes')
theDFs = []
for fc in LCPS:
    FromID = int(fc[5:])
    #Convert to numpy array
    arr = arcpy.da.FeatureClassToNumPyArray(fc, ['DestID','PathCost'])
    #Convert to dataframe, selecting rows where the DestID >= From ID
    df = pd.DataFrame(arr).query(f'DestID > {FromID}')
    #Add From ID column
    df['FromID'] = FromID
    #Add to the collection
    theDFs.append(df)
    
#Merge and export data
arcpy.AddMessage('Merging dataframes')
outDF = pd.concat(theDFs)

arcpy.AddMessage(f'Exporting to {Output_EdgeList}')
outDF[['FromID','DestID','PathCost']].to_csv(Output_EdgeList,index=False)