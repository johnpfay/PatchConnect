#---------------------------------------------------------------------------------
# CalculatePatchConnectivityAttributes.py
#
# Description: Creates a table listing each patch and (1) the total patch area
#  within the distance threshold and (2) the inverse distance weighted patch area,
#  i.e. area of further distances are discounted using a decay rate:
#   SUM: exp(ln(0.1) * (patch distance)) * (patch area)
#
# Requires: NetworkX to be stored in script folder (or installed)
#
# Inputs: <Patch raster> <edge list> <maxDistance>
# Output: <Patch connected attribute table (CSV format)>
#  
# June 14, 2012
# John.Fay@duke.edu
#
# Edits: Nathan Walker
# July 5, 2016
# Corrected error in how centrality attributes calculated
# Removed Eigenvector Centrality (prone to error messages for many graphs)
# Added Degree Centrality (included in code before, but not written to final table)
# Made area measurements in decimals
#
#---------------------------------------------------------------------------------

# Import system modules
import sys, string, os, arcpy, math
import arcpy.sa as sa
import networkx as nx

# Check out any necessary licenses
arcpy.CheckOutExtension("spatial")
arcpy.env.overwriteOutput = True

# Input variables
patchRaster = sys.argv[1]   
edgeListFN = sys.argv[2]    
maxDistance = int(sys.argv[3])   
k = math.log(0.1) / maxDistance ##Decay coefficient

# Output variables
outputFN = sys.argv[4]   

##---FUNCTIONS---
def msg(txt): print txt; arcpy.AddMessage(txt); return

##---PROCESSES---
# Create a list of patch IDs and a dictionary of areas
msg("Creating list of patch areas")
patchAreas = {}
cellSize2HA = (arcpy.Raster(patchRaster).meanCellWidth ** 2) / 10000.0
rows = arcpy.SearchCursor(patchRaster)
row = rows.next()
while row:
    patchAreas[row.VALUE] = row.COUNT * cellSize2HA
    row = rows.next()
del row, rows
patchIDs = patchAreas.keys()

# Create a graph from the edge list
msg("Creating graph from nodes < %d from each other" %maxDistance)
G = nx.Graph()
subDict = {}
edgeList = open(edgeListFN,'r')
headerLine = edgeList.readline()
dataLine = edgeList.readline()
while dataLine:
    lineData = dataLine.split(",")
    u = int(lineData[0])
    v = int(lineData[1])
    w = float(lineData[2][:-1])
    if w <= maxDistance:
        G.add_edge(u,v,weight = w)
    dataLine = edgeList.readline()
edgeList.close()

# Calculate degree, betweenness, and closeness centrality - one subgraph at time
subGs = nx.connected_component_subgraphs(G)
msg("There graph contains %d subgraph(s)" %len(subGs))
dG = {}
bG = {}
cG = {}
for subG in subGs:
    #msg("Calculating degree centrality...")
    dG.update(nx.centrality.degree_centrality(subG))
    #msg("Calculating betweenness centrality...")
    bG.update(nx.centrality.betweenness_centrality(subG,normalized=True,weight='weight'))
    #msg("Calculating closeness centrality...")
    cG.update(nx.centrality.closeness_centrality(subG,normalized=True,distance='weight'))

# Create the output file
msg("Writing outputs to %s" %outputFN)
connAreaFileObj = open(outputFN, 'w')
connAreaFileObj.write("patchID, connectedArea, idwArea, degree, betweenness, closeness, degreeCen\n")

# Loop through patch IDs
for patchID in patchIDs:
    if not patchID in G.nodes():
        msg("Patch #%d is isolated" %patchID)
        connAreaFileObj.write("%d, 0.0, 0.0, 0, 0.0, 0.0, 0.0\n" %patchID)
        continue
    # Reset area accumulators
    connArea = 0
    idwArea = 0
    # Get the edges connected to the selected node
    edges = G.edge[patchID]
    # Diameter (number of neighbors)
    degree = len(edges)
    # Loop through each connected patch and tabulate area and IDW area
    for toID in edges.keys():
        distance = edges[toID]['weight']
        connArea += patchAreas[toID]
        idwArea += math.exp(k * distance) * patchAreas[toID]
    between = bG[patchID] * 100.0
    closeness = cG[patchID] * 100.0
    degreeN = dG[patchID] * 100.0

    # Write values to the file
    connAreaFileObj.write("%d, %2.4f, %2.4f, %d, %2.4f, %2.4f, %2.4f\n"
                          %(patchID, connArea, idwArea, degree, between, closeness, degreeN))

# Close the text file
connAreaFileObj.close()

arcpy.CheckInExtension("spatial")
