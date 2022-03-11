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


#%% SET UP

#Import libraries
import arcpy
import numpy as np
import pandas as pd
from skimage import graph
from arcgis import GIS, GeoAccessor, geometry

#Initialize the ArcGIS API "GIS" object
gis = GIS('home')

# Get input datasets: Patches and CostSurface
debug = False
if debug:
    orig_patchRaster = '..\\Data\\ENH_LCP_ModelInputs_Final2019.gdb\\S_Patches_60ha'
    orig_costRaster = '..\\Data\\ENH_LCP_ModelInputs_Final2019.gdb\\S_CostSurface'
    edgeListFN = '..\\Scratch\\edgelist4.csv'
    lcp_featureclass = edgeListFN.replace('.csv','.shp')
    arcpy.env.overwriteOutput = True

else:
    orig_patchRaster = arcpy.GetParameterAsText(0)
    orig_costRaster = arcpy.GetParameterAsText(1)
    edgeListFN = arcpy.GetParameterAsText(2)
    lcp_featureclass = arcpy.GetParameterAsText(3)

# Subset the cost raster to match dimensions of the patch raster
arcpy.env.cellSize = orig_patchRaster
arcpy.env.extent = orig_patchRaster
arcpy.env.snapRaster = orig_patchRaster


#%% FUNCTIONS

#Message function: shows messages locally and in ArcGIS Pro
def msg(txt):
    print(txt)
    arcpy.AddMessage(txt)
    return

#Convert row-column values to geographic coordinates
def to_xy(row,col):
    x_geom = extent.upperLeft.X + (col * cellSize) 
    y_geom = extent.upperLeft.Y - (row * cellSize) 
    return [x_geom,y_geom]

#%% Subset the cost raster to match the patch raster
msg("Subsetting rasters")
costRaster = arcpy.sa.ExtractByRectangle(orig_costRaster, orig_patchRaster, "INSIDE")
patchRaster= arcpy.sa.ExtractByRectangle(orig_patchRaster, costRaster, "INSIDE")

#%% Get the spatial reference, extent, and lower left coordinates
sr = arcpy.Describe(patchRaster).spatialReference
cellSize = arcpy.Describe(patchRaster).meanCellWidth
extent = arcpy.Describe(patchRaster).extent
llCorner = extent.lowerLeft

#%% Create arrays of the patch and core rasters
msg("Converting rasters to NumPy arrays")
arrPatch = arcpy.RasterToNumPyArray(patchRaster,
                                    lower_left_corner=llCorner,
                                    nodata_to_value=-9999)

arrCost = arcpy.RasterToNumPyArray(costRaster,
                                   lower_left_corner=llCorner,
                                   nodata_to_value=-9999)
                                   

#Check that arrays are the same size
if arrPatch.shape != arrCost.shape:
    msg("Input rasters must be of same size")
    sys.exit[0]

#%% Create a list of patchIDs
patchIDs = np.unique(arrPatch).tolist()
patchIDs.remove(-9999)
msg(f"{len(patchIDs)} patches to process")

#%% Initialize the output dataframe and CostDistArrays list
df_patches = pd.DataFrame(columns = ['FROM_ID','TO_ID','COST','geometry'])
costDistArrays = []

#%% Initialize the progressor
step = 0
steps = len(patchIDs)
arcpy.SetProgressor("step", "Computing Cost Distances...",step,steps,1)

#%% Loop through each patch and compute its cost distance to all other patches
for patchID in patchIDs:
    step += 1
    arcpy.SetProgressorLabel("Patch {} of {} ".format(step,steps))

    #Reclassify cost in source patch cells to zero & set no data to high cost
    arrCostMod = arrCost.copy()
    arrCostMod[arrPatch == patchID] = 0
    #arrCostMod[arrCostMod == -9999] = arrCostMod.max() * 10000

    #Create the MCP object (Geometric accounts for diagonals)
    cost_graph = graph.MCP_Geometric(arrCostMod, sampling=(cellSize, cellSize))

    #Get the index of a cell in the current patch ID
    i,j = np.where(arrPatch == patchID)
    startCells = list(zip(i,j))

    #Compute cost distance and traceback arrays from a source
    cd_array = cost_graph.find_costs(starts=startCells)[0]
    
    #Process all the to-patches
    for toID in patchIDs:
        if toID > patchID:
            print(".",end="")
            #--Extract the cost distance between patches--
            least_cost_distance = cd_array[arrPatch == toID].min()
            
            #--Skip if no LCP was found
            if least_cost_distance == float('inf'): continue
            
            #--Compute the least cost path polyline--
            #Step 1. Find the cell[s] with the lowest cost
            rowMin,colMin = np.where(cd_array == least_cost_distance)
            
            ###---IF LCP FEATURES ARE REQUESTED---
            if lcp_featureclass:
                #Step 2. Compute the least cost path (traceback) from this cell
                lcp_coords = cost_graph.traceback((rowMin[0],colMin[0]))
                #Step 3. Convert image coords to geographic coords
                lcp_coords_geog = [to_xy(r,c) for r,c in lcp_coords]
                #Step 4. Construct a linestring from the coordinates
                the_linestring = {"paths":[lcp_coords_geog],
                                  "spatialReference":{"wkid":sr.factoryCode}}
                #Step 5. Construct a PolyLine geometry from the linestring
                the_polyline = geometry.Polyline(the_linestring)
                
                #--Add the data to the dataframe
                df_patches = df_patches.append({
                    'FROM_ID': patchID, 
                    'TO_ID': toID,
                    'COST': least_cost_distance,
                    'geometry': the_polyline},ignore_index=True)
            else:
                #--Add the data to the dataframe,w/o geometry
                df_patches = df_patches.append({
                    'FROM_ID': patchID, 
                    'TO_ID': toID,
                    'COST': least_cost_distance},ignore_index=True)
            
    #Add arrays to arrLists
    costDistArrays.append(cd_array)
    arcpy.SetProgressorPosition()

#%% Clean up

#Convert dataframe to spatial dataframe
try:
    if lcp_featureclass:
        arcpy.SetProgressor("default","Converting features to a spatial dataframe")
        print("Converting to spatial dataframe")
        sdf_patches = GeoAccessor.from_df(df_patches, geometry_column='geometry')
except:
    msg("Error creating spatial dataframe")

    
try:    
        #Save as a feature class
        arcpy.SetProgressor("default",f"Saving least cost paths to {lcp_featureclass}")
        print(f"Saving least cost paths to {lcp_featureclass}")
        sdf_patches.spatial.to_featureclass(lcp_featureclass)
except:
    msg("Error saving least cost paths")

#Write the edges to the edgeListFN
try:
    msg(f"Saving Edges to {edgeListFN}")
    df_patches[['FROM_ID','TO_ID','COST']].to_csv(edgeListFN,float_format=("%2.4f"),index=False)
except:
    msg("Error saving edge to csv")

#Write out cost surface arrays
try:
    msg("Stacking arrays")
    arrStack = np.stack(costDistArrays)

    msg(f"Saving Cost Distance Arrays to {edgeListFN}")
    np.save(edgeListFN.replace("csv","npy"),arrStack)
except:
    msg("Error saving cost stack")
