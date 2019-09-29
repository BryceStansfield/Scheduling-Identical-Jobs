# -*- coding: utf-8 -*-
"""
Created on Fri Sep 13 14:34:57 2019

@author: Joel
"""

from gurobipy import *
import time
import networkx as nx
import random


def AddPair(machine,job):
    if (machine,job) in X:
        print('************Duplicate',machine,job)
    else:
        X[machine,job] = m.addVar()
        m.chgCoeff(JobsOnMachine[i],X[machine,job],1)
        m.chgCoeff(JobsHappen[machine,job])
        for k in G[machine]:
            m.chgCoeff(GraphConstr[machine][k][job], X[machine,job],-1)
    if (machine) not in M:
        M[machine] = m.addVar()
        m.chgCoeff(JobsOnMachine[i],M[i],1)
        m.chgCoeff(CMaxConstr[i],M[i],1/speeds[i])

def MakeMInteger():
    for i in M:
        M[i].vtype = GRB.INTEGER
        
def MakeXBinary():
    for i,j in X:
        X[i,j].vtype = GRB.BINARY

def RemoveBounds():
    for i,j in X:
        X[i,j].LB = 0
        X[i,j].UB = GRB.INFINITY

def emptyMax(array):
    if len(array) == 0:
        return 0
    else:
        return max(array)
    
gen_m = 20                              # "Number of machines"
I = range(0, gen_m)
gen_n = 1000                          # Number of jobs
J = range(0, gen_n)

print("generating speeds")
speeds = sorted([random.uniform(1, 2*gen_m) for j in range(0, gen_m)])
print("speeds ready, generating Graph")
run_time = time.time()
G = nx.fast_gnp_random_graph(gen_n, 2*gen_m/(gen_n * (1+1/gen_m)))
run_time = time.time() - run_time
print('Graph Ready took:', run_time)

EdgeDictionary = {}
TotalEdgeConstr = 0

for n1 in G:
    for n2 in G[n1]:
        if n2 <= n1:
            if (n1,n2) not in EdgeDictionary:
                EdgeDictionary[n1,n2] = True
                TotalEdgeConstr += gen_m

## SMALL MODEL

SP = Model("Small Problem")
SP.setParam("BranchDir", 1)
SP.setParam('GURO_PAR_MINBPFORBID', 1)
#m.setParam('OutPutFlag', 0)

## VARIABLES BUT NOT ALL OF 'EM

SM = {i: SP.addVar(vtype = GRB.INTEGER) for i in I}

CMAXLOWBOUND = SP.addVar()

SP.setObjective(CMAXLOWBOUND)

for i in I:
    SP.addConstr(CMAXLOWBOUND - SM[i]/speeds[i] >= 0)
    
SP.addConstr(quicksum(SM[i] for i in I) == gen_n)

SP.optimize()




## BIG MODEL

BP = Model("Big Problem")
BP.setParam("BranchDir", 1)
BP.setParam('GURO_PAR_MINBPFORBID', 1)

FP = Model("Final Problem")
BP.setParam("BranchDir", 1)
BP.setParam('GURO_PAR_MINBPFORBID', 1)

#Jobs Machine Assignment Pairs
X = {(i,j): BP.addVar() for i in I for j in J}
#Number of jobs Assigned
M = {(i,n): BP.addVar(vtype = GRB.BINARY) for i in I for n in range(0, gen_n)}

for i in I:
    BP.addConstr(quicksum(M[i,n] for n in range(0, gen_n))==1)
    for n in range(0, gen_n):
        M[i,n].BranchPriority = gen_n**2 - i
    for j in J:
        X[i,j].BranchPriority = len(list(G.neighbors(j))) + 1
        #X[i,j].set(speeds[i]/sum(speeds))
        
        
print("Branch Priorities Set")

#C_max Variable
C_max = BP.addVar()

# Constraints
#FURST CUT
FirstLowerBound = BP.addConstr(C_max >= CMAXLOWBOUND.x)

# Each job happens once (or more...)
JobsHappen = {j: BP.addConstr(quicksum(X[i,j] for i in I) >= 1) for j in J}
print("Jobs Happen Constr")

# Jobs on Machines
JobsOnMAchine = {i: BP.addConstr(quicksum(n*M[i,n] for n in range(0,n)) - quicksum(X[i,j] for j in J) >= 0) for i in I}

# C_max constr:
CMaxConstr = {i: BP.addConstr(C_max - M[i]/speeds[i] >= 0) for i in I}

# Graph constraints
GraphConstr = {i: {j: {k: BP.addConstr(X[i,j] + X[i,k] <= 1) for k in G[j] if k<=j} for j in J} for i in I}

# Objective
BP.setObjective(C_max)

BP.optimize()

BP.addConstr(C_max >= C_max.x)

##### FinalProblem
FP = Model("Final Problem")
FP.setParam("BranchDir", 1)
FP.setParam('GURO_PAR_MINBPFORBID', 1)
FP.setParam("LazyConstraints", 1)

#Jobs Machine Assignment Pairs
FX = {(i,j): FP.addVar(vtype = GRB.BINARY) for i in I for j in J}

FBranchDict = {}

threshold = .89999
while threshold > .59999:
    found = 0
    for (i,j) in X:
        if X[i,j].x > threshold and X[i,j].LB != 1:
            FBranchDict[i,j] = True
            FX[i,j].BranchPriority = len(list(G.neighbors(j)))**2 + 1
            X[i,j].LB = 1
            found += 1
#        if X[i,j].x < .0001:
#            X[i,j].UB = 0
    
    if found > 0:
        print('############### found:{} at threshold:{} #################\n'.format(found, threshold))
        BP.optimize()
    else:
        threshold -= .05

print('Making X Binary')
MakeXBinary()

BP.optimize()

print("############## Cut: {}\n".format(C_max.x))


##### FinalProblem

#Itterative Graph Constraints
ItterGraphConstr = {}

#Number of jobs Assigned
FM = {i: FP.addVar(vtype = GRB.INTEGER) for i in I}
for i in I:
    FM[i].BranchPriority = gen_n - 1
    for j in J:
        if (i,j) in FBranchDict:
            FX[i,j].BranchPriority = len(list(G.neighbors(j))) + 1
        #X[i,j].set(speeds[i]/sum(speeds))
print("Branch Priorities Set")


#FC_max Variable
FC_max = FP.addVar()

# Constraints
#FURST CUT
FirstLowerBound = FP.addConstr(FC_max >= CMAXLOWBOUND.x)

#Cut from the last sollution
FP.addConstr(FC_max <= C_max.x)

# Each job happens once (or more...)
JobsHappen = {j: FP.addConstr(quicksum(FX[i,j] for i in I) >= 1) for j in J}
print("Jobs Happen Constr")

# Jobs on Machines
JobsOnMAchine = {i: FP.addConstr(FM[i] - quicksum(FX[i,j] for j in J) >= 0) for i in I}

# C_max constr:
CMaxConstr = {i: FP.addConstr(FC_max - FM[i]/speeds[i] >= 0) for i in I}

print("graph constr")
# Graph constraints
GraphConstr = {i: {j: {k: FP.addConstr(FX[i,j] + FX[i,k] <= 1) for k in G[j] if k<=j} for j in J} for i in I}
print("done\n")

# Objective
FP.setObjective(FC_max)

#TotalLazyConstraintsAdded = 0
#        #### REWRITE THIS TO ADD GRAPH CONSTR THAT VIOLATE THE CURRENT SOLLUTION
#def Callback(model, where):
#    if where==GRB.Callback.MIPSOL:
#        added = 0
#        XV = {k: v for (k,v) in zip(FX.keys(), FP.cbGetSolution(FX.values()))}
#        for edge in EdgeDictionary:
#            for i in I:
#                if (edge,i) not in ItterGraphConstr:
#                    if XV[i,edge[0]] + XV[i,edge[1]] > 1:
#                        ItterGraphConstr[edge, i] = 1
#                        FP.cbLazy(FX[i,edge[0]] + FX[i,edge[1]] <= 1)
#                        added += 1
#        if added > 0:
#            print("############ Lazy Constraint Added {} constraints\n".format(added))

FP.optimize()

#print('#### REMOVING BOUNDS')
#RemoveBounds()
#print('#### solving')
#BP.optimize()
print("Edge Constraints",TotalEdgeConstr)
for i in I:
    #print("Comp{}({}) : {}; ({})".format(i,round(speeds[i],1), [j for j in J if X[i,j].x == 1], sum(X[i,j].x for j in J)/speeds[i]))
    print("Comp{} speed({}) assigned({}) constr({}) took({})".format(i,round(speeds[i],1), FM[i].x, emptyMax([len(G[j]) for j in J if FX[i,j].x == 1]), sum(FX[i,j].x for j in J)/speeds[i]))


## Graph constraints
#GraphConstr = {i: {j: {k: BP.addConstr(X[i,j] + X[i,k] <= 1) for k in G[j] if k<=j} for j in J} for i in I}
#print("Graph Constr")