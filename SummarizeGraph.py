#-------------------------------------------------------------------------------------------
# SummarizeGraph.py
#
# Description: Summarizes a least cost paths graph by examining how many subgraphs
#          are created using different cost thresholds and what their diameters are.
#          Results are returned as a text file.
#
# Usage: SummarizeGraph.py <LCP edge list> <Min Threshold> <Max Threshold> <interval> <output>
#
#-------------------------------------------------------------------------------------------
# Updated for Python 3.5 (Spring 2018, John.Fay@duke.edu)

import sys, os, arcpy
import networkx as nx
#import DU_GraphTools99 as gt
# C:\check\PatchConnect\EdgeList.csv 300000 1500000 300000 C:\check\PatchConnect\GraphSummary.csv

#--Messaging function--
def msg(msgText): print (msgText); arcpy.AddMessage(msgText); return

#--DLU Functions---
#   Assess graph connectivity in terms of a threshold distance (edge
#   weight) or sequence of these, to look at how a graph connects
#   as the threshold distance is systematically increased.
#
#   Contains 4 functions, as they would be used in sequence, 
#   along with some helper functions.
#
def edge_threshold(G, max_wt):
   """
   Accepts a (dense) weighted graph (XGraph) and a threshold weight,
   returnsa new graph with only edges for which the weight is
   less than the threshold.  The weights are general but this has been
   designed for (and tested with) distances.

   Usage:  if G is a XGraph with edges < 5000 m,
   >>> G2 = edge_threshold(G, 3000)
   returns a new graph with edges < 3000 m.

   DL Urban (22 Feb 2007)
   Added NetworkX version checking - 26 May 2009; JP Fay
   """
   tG = nx.Graph()
   G_edges = G.edges(data=True)
     
   nbunch = G.nodes()
   tG.add_nodes_from(nbunch)   # copy the nodes

   for edge in G_edges:
       (tn, fn, w) = edge
       if w <= max_wt:
           tG.add_edge(tn, fn, weight=w)
   return tG


def edge_threshold_sequence(G, min_wt, max_wt, winc):
   """
   Accepts a (dense) graph and systematically redefine its
   edges by edge-thresholding it in a loop of calls to
   edge_threshold (above), the loop provided by a min, max,
   and increment.  Note (below) that the increment is added to
   the max_wt to make sure max_wt is included in the range
   (this is because of the way python does loops).
   Returns a dictionary of graphs keyed by the threshold weights.

   Usage:  if G is a dense XGraph with edge weights <= 10000 m,
   >>> Gts = edge_threshold_sequence(G,1000,10000,1000)
   returns a dictionary of of 10 new graphs keyed by the numbers
   1000-10000.  To grab one:
   >>> G4000 = Gts[4000]

   DL Urban (22 Feb 2007)
   Added NetworkX version checking - 26 May 2009; JP Fay
   """
   Gts = {}
   nbunch = G.nodes()
   edges = G.edges(data=True)

   for wt in range(min_wt, max_wt+winc, winc):
       tGw = nx.Graph()
       tGw.add_nodes_from(nbunch)
       for e in edges:
           (n1, n2, w) = e
           if w['weight'] <= wt:
               tGw.add_edge(n1, n2, weight=w)
       Gts[wt] = tGw
   return Gts


#   Assess a dictionary of graphs keyed by dispersal distance
#   threshold, in terms of number of components and diameter.
def graph_comp_sequence(Gts):
   """
   Gts is a graph thresholding sequence, a dictionary of graphs
   keyed by threshold distance, see edge_threshold_sequence().
   This function takes that sequence and returns the number of
   components in each graph, along with the diameter of the
   largest component in each graph. The output is a dictionary of
   tuples (NC, D(G)) keyed by threshold distance.

   Requires:  x_diameter(G), local function.

   Usage:  The output is intended to be printed to a file (see
   write_table.txt for syntax), so that a plot can be constructed
   that illustrates the number of components and graph diameter
   as a function of distance.

   DL Urban (22 Feb 2007)
   """
   seq = Gts.keys()
   gcs = {}
   for d in seq:
       #msg("Working on {}".format(d))
       g = Gts[d]
       if nx.is_connected(g):
           nc = 1
           diam = x_diameter(g)
       else:
           nc = nx.number_connected_components(g)
           gc = max(nx.connected_component_subgraphs(g), key=len)# nx.connected_component_subgraphs(g)[0]
           diam = x_diameter(gc)
       gcs[d] = (nc, diam)
       msg("{0}:\tnc={1}\tdiam={2:2.4f}".format(d,nc,diam))
       if nc == 1: break
   return gcs


#   Write these out to a file:

def write_graph_comp_sequence(gcs, path):
   """
   Accept a graph component sequence from edge-thresholding, and
   write the output as a table to a file.

   Usage:
   >>> Gts = edge_threshold_sequence(G, min, max, inc),
   >>> gcs = graph_conn_sequence(Gts)
   >>> write_graph_conn_sequence(gcs, path)

   DL Urban (22 Feb 2007)
   """
   f = open(path, 'w')
   f.write('%s\n' % 'Distance, NComps, Diameter')
   for k,v in gcs.items():
       (nc, diam) = v
       f.write('%4d, %5d, %10.3f\n' % (k, nc, diam))
   f.close() 

# x_eccentricity and x_diameter correspond to the NX functions
# but use weighted edges instead of tallying the number of links.

def x_diameter(G, e=None):
    """Return the diameter of the graph G.

    The diameter is the maximum of all pairs shortest path.
    This version calls x_eccentricity (above).
    """
    if e is None:
        e=x_eccentricity(G,with_labels=True)
        #e = nx.eccentricity(G)
    #return max(list(e.values()))
    return max(e.values())

def x_eccentricity(G, v=None, sp=None, with_labels=False):
    """
    Return the eccentricity of node v in G (or all nodes if v is None).
    The eccentricity is the maximum of shortest paths to all other nodes. 

    This X version is the same as the original eccentricity and related
    functions, but replaces the call to the single_source functions with
    calls to the corresponding Diijkstra functions.  
    Note the native functions are for unweighted graphs, while the
    Dijkstra functions are for weighted graphs.  Even so, the
    edge weights should be non-negative and not floating point. 
    (copied and altered by DL Urban, Feb 2007)

    The optional keyword sp must be a dict of dicts of
    shortest_path_length keyed by source and target.
    That is, sp[v][t] is the length from v to t.
       
    If with_labels=True 
    return dict of eccentricities keyed by vertex.
    """
    nodes=[]
    if v is None:              # none, use entire graph 
        nodes=G.nodes() 
    elif isinstance(v, list):  # check for a list
        nodes=v
    else:                      # assume it is a single value
        nodes=[v]

    e={}
    for v in nodes:
        if sp is None:
            length=single_source_dijkstra_path_length(G,v,weight='weight')
        else:
            length=sp[v]
        try:
            assert len(length)==G.number_of_nodes()
        except:
            #raise nx.NetworkXError,\
            msg("Graph not connected: infinite path length")
            
        e[v]=max(length.values())

    if with_labels:
        return e
    else:
        if len(e)==1: return e.values()[0] # return single value
        return e.values()


# Sensi_diameter computes the change in graph diameter
# on the removal of each node--a way to find cut-nodes 
# that are also central to the graph.
# Its helper function (following) writes the output.

def sensi_diameter(G):
    
    """
    Compute graph sensitivity to node removal, in terms of
    the difference in graph diameter on the removal of each
    node in turn.
     
    This uses local function x_diameter(G), which is modified
    from networkx.diamter(G) to work on XGraphs.
    
    DL Urban (9 Feb 2007)
    """
    
    # Starting diameter for full graph:
    
    if nx.is_connected(G):
        d0 = x_diameter(G)
    else:
        G0 = nx.connected_component_subgraphs(G) [0] # the largest subgraph
        d0 = x_diameter(G0)
        nc = nx.number_connected_components(G)	     # how many are there?
    
    sensi = {}
    
    for node in G.nodes():
        ex = G.edges(node) 		# a set of edges adjacent to node; 
        G.delete_edges_from(ex)		# remove all of these,
        G.delete_node(node)		# and then kill the node, too
        if nx.is_connected(G):
            dx = x_diameter(G)
            cuts = 0
        else:
            Gx = nx.connected_component_subgraphs(G) [0]	# the biggest
            ncx = nx.number_connected_components(G)
            if nc == ncx:
                cuts = 0
            else:
                cuts = 1
            dx = x_diameter(Gx)
        delta = d0 - dx
        G.add_node(node)		# put the node and edges back again
        G.add_edges_from(ex)
        sensi[node] = (cuts, delta)
 
    # create and return a tuple (cuts, delta)
    return sensi


#   Write this output to a CSV file:
def write_sensi_diameter(sensi, path):
    f = open(path, 'w')
    f.write('Node, Cuts, deltaD\n')
    for k,v in sensi.items():
        (cuts, delta) = v
        f.write('%4d, %3d, %10.2f\n' % (k, cuts, delta))
    f.close()

def multi_source_dijkstra_path_length(G, sources, cutoff=None,
                                      weight='weight'):
    
    if not sources:
        raise ValueError('sources must not be empty')
    weight = _weight_function(G, weight)
    return _dijkstra_multisource(G, sources, weight, cutoff=cutoff)

def single_source_dijkstra_path_length(G, source, cutoff=None, weight='weight'):
    return multi_source_dijkstra_path_length(G, {source}, cutoff=cutoff, weight=weight)
   
def _weight_function(G, weight):
    if callable(weight):
        return weight
    if G.is_multigraph():
        return lambda u, v, d: min(attr.get(weight, 1) for attr in d.values())
    return lambda u, v, data: data.get(weight, 1)
   
def _dijkstra_multisource(G, sources, weight, pred=None, paths=None,cutoff=None, target=None):
    G_succ = G._succ if G.is_directed() else G._adj
    from heapq import heappush, heappop
    from itertools import count
    push = heappush
    pop = heappop
    dist = {}  # dictionary of final distances
    seen = {}
    # fringe is heapq with 3-tuples (distance,c,node)
    # use the count c to avoid comparing nodes (may not be able to)
    c = count()
    fringe = []
    for source in sources:
        seen[source] = 0
        push(fringe, (0, next(c), source))
    while fringe:
        (d, _, v) = pop(fringe)
        if v in dist:
            continue  # already searched this node.
        dist[v] = d
        if v == target:
            break
        for u, e in G_succ[v].items():
            cost = weight(v, u, e)
            if type(cost) is dict: cost = cost['weight']
            if cost is None:
                continue
            vu_dist = dist[v] + cost#['weight']
            if cutoff is not None:
                if vu_dist > cutoff:
                    continue
            if u in dist:
                if vu_dist < dist[u]:
                    raise ValueError('Contradictory paths found:',
                                     'negative weights?')
            elif u not in seen or vu_dist < seen[u]:
                seen[u] = vu_dist
                push(fringe, (vu_dist, next(c), u))
                if paths is not None:
                    paths[u] = paths[v] + [u]
                if pred is not None:
                    pred[u] = [v]
            elif vu_dist == seen[u]:
                if pred is not None:
                    pred[u].append(v)

    # The optional predecessor and path dictionaries can be accessed
    # by the caller via the pred and paths objects passed as arguments.
    return dist

    return _dijkstra(G, source, get_weight, cutoff=cutoff)
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
gts = edge_threshold_sequence(G,minThresh,maxThresh,threshInt)
msg("Calculating graph properties")
gcs = graph_comp_sequence(gts)
msg("Writing data to %s" %outFile)
write_graph_comp_sequence(gcs,outFile)

