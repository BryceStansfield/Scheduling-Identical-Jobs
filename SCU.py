from gurobipy import *
import networkx as nx
import random
import json
import time

#Run Settings
gen_m = 30                             # "Number of machines"
seed = 0
e = 0.00001                            # Permitted error
M = range(0, gen_m)
I = range(0, 2)                        # Initial number of machines in column gen
gen_n = 200                            # Number of nodes
J = range(0, gen_n)
output_on = 1
time_limit = 300
settings = [{'alpha':10,'beta':1}]

times = []
#Specific Informtion per run
machinesUsed = set()                   #A machine has been used
edgeExist = set()                      #A (machine, node) pair exists
G = nx.erdos_renyi_graph(gen_n, gen_m/(gen_n * (1+1/gen_m)), seed=seed)
speeds = sorted([random.uniform(1, 2*gen_m) for i in range(0, gen_m)], reverse=True)

start = time.time()
RMP = Model("Scheduling on Machines")
RMP.setParam("OutputFlag", output_on)
RMP.setParam("TimeLimit", time_limit)
RMP.setParam("BranchDir", 1) 

for i in I:
        machinesUsed.add(i)

# Variables
X = {(i,j): RMP.addVar() for i in J for j in I}
#No need to set branch priorities as this will be manual

C_max = RMP.addVar()

# Constraints
# Each job happens once (or more...)
JobsHappen = {i: RMP.addConstr(quicksum(X[i,j] for j in I) == 1) for i in J}

# Graph constraints
GraphConsts = {i: {k: {j: RMP.addConstr(X[i,j] + X[k,j] <= 1) for j in I} for k in G.neighbors(i) if k < i} for i in J}

# C_max constr:
CMaxWorks = {j: RMP.addConstr(C_max >= quicksum(X[i,j] for i in J)/speeds[j]) for j in I}

#Linear Program Constraints
LP0Constr = {(i, j): RMP.addConstr(X[i, j] <= 1) for i in J for j in I}
LP1Constr = {(i, j): RMP.addConstr(X[i, j] >= 0) for i in J for j in I}

# Objective
RMP.setObjective(C_max)

RMP.optimize()

if RMP.status == GRB.OPTIMAL:
        # Output:
        print("The following jobs were assigned to the following computers:")
        for j in M:
                for i in J:
                        if X[i, j].x > 1 - e:
                                print("Comp {}: Job {};".format(j, i))
                print("Time {}:".format(sum(X[i,j].x for i in J)/speeds[j]))

        print("Worst Case Runtime {}".format(C_max.x))
end = time.time()
print("Program ran for {}".format(end - start))


#Price step
def choose_column():
        delta = [None] * gen_m
        for i in range(1, gen_m):
                delta[i] = 0


#Adds variable X[i, j]
def generate_column(i, j):
        X[i, j] = RMP.addVar()
        RMP.addConstr(X[i, j] <= 1)
        RMP.addConstr(X[i, j] >= 0)

        edgeExist.add((i, j))

        RMP.chgCoeff(JobsHappen, X[i, j], 1)
        for k in G.neighbors(i):
                if edgeExist.contains(k):
                        GraphConsts[i][k][j] = RMP.addConstr(X[i,j] + X[k,j] <= 1)

        if machinesUsed.contains(j):
                RMP.chgCoeff(CMaxWorks[j], X[i, j], 1.0 / speeds[j])
        else:
                CMaxWorks[j] = RMP.addConstr(C_max >= X[i, j]/speeds[j])

