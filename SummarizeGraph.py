#-------------------------------------------------------------------------------------------
# SummarizeGraph.py
#
# Description: Summarizes a least cost paths graph by examining how many subgraphs
#          are created using different cost thresholds and what their diameters are.
#          Results are returned as a text file.
#
# Requires: DU_GraphTools99.py script in same folder as this one
#
# Usage: SummarizeGraph.py <LCP edge list> <Min Threshold> <Max Threshold> <interval> <output>
#
#-------------------------------------------------------------------------------------------

import sys, os, arcgisscripting
import networkx as nx
import DU_GraphTools99 as gt
gp = arcgisscripting.create()

def msg(msgText): print (msgText); gp.AddMessage(msgText); return

#--INPUT VARIABLES--
edgeFile = sys.argv[1]
minThresh = int(sys.argv[2])
maxThresh = int(sys.argv[3])
threshInt = int(sys.argv[4])
outFile = sys.argv[5]

# Build graph from edgelist
msg("Building graph from %s" %edgeFile)
G = nx.Graph()
edgeList = open(edgeFile, 'r')
lineText = edgeList.readline()
# Check whether the first line is a header line
if (lineText.split(",")[0]).isalpha:
    lineText = edgeList.readline()
while lineText:
    lineData = lineText.split(",")
    u = int(lineData[0])
    v = int(lineData[1])
    w = float(lineData[2][:-1])
    if w <= maxThresh:
        G.add_edge(u,v,weight = w)
    lineText = edgeList.readline()
edgeList.close()

msg("Creating thresholded graphs")
gts = gt.edge_threshold_sequence(G,minThresh,maxThresh,threshInt)
msg("Calculating graph properties")
gcs = gt.graph_comp_sequence(gts)
msg("Writing data to %s" %outFile)
gt.write_graph_comp_sequence(gcs,outFile)

