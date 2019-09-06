from gurobipy import *
import networkx as nx
import random
import json
import time
from tabulate import tabulate           # Since I'm bad at formatting outputs

times = []
def solve(seed, mps, time_limit=300, output_on = 0):
        start = time.time()
        m = Model("Machine stuff")
        m.setParam("OutputFlag", output_on)
        m.setParam("TimeLimit", time_limit)
        m.setParam("BranchDir", 1)
        

        gen_m = 20                              # "Number of machines"
        J = range(0, gen_m)
        gen_n = 1000                            # Number of nodes
        I = range(0, gen_n)

        speeds = sorted([random.uniform(1, 2*gen_m) for i in range(0, gen_m)])

        G = nx.erdos_renyi_graph(gen_n, gen_m/(gen_n * (1+1/gen_m)), seed=seed)

        if output_on:
                print('Graph Ready')
        
        # Variables
        X = {(i,j): m.addVar(vtype=GRB.BINARY) for i in I for j in J}
        for i in I:
                for j in J:
                        X[i,j].BranchPriority = len(list(G.neighbors(i)))*mps['alpha'] + mps['beta'] * j
        if output_on:
                print("Branch Priorities Set")

        C_max = m.addVar()

        # Constraints
        # Each job happens once (or more...)
        JobsHappen = {i: m.addConstr(quicksum(X[i,j] for j in J) >= 1) for i in I}
        if output_on:
                print("Jobs Happen Constr")

        # Graph constraints
        GraphConsts = {i: {k: {j: m.addConstr(X[i,j] + X[k,j] <= 1) for j in J} for k in G[i] if k<=i} for i in I}
        if output_on:
                print("Graph Constr")

        # C_max constr:
        CMaxWorks = {j: m.addConstr(C_max >= quicksum(X[i,j] for i in I)/speeds[j]) for j in J}
        if output_on:
                print("CMaxWorks Constr")


        # Objective
        m.setObjective(C_max)

        m.optimize()

        if m.status == GRB.OPTIMAL:
                if output_on:
                        # Output:
                        print("The following jobs were assigned to the following computers:")
                        for j in J:
                                print("Comp {}: {}; ({})".format(j, [i for i in I if X[i,j].x == 1], sum(X[i,j].x for i in I)/speeds[j]))

                        print("With a total runtime of {}".format(C_max.x))

                end = time.time()
                return(end-start)
        else:
                return(float("inf"))
        return

settings = [{'alpha':0,'beta':0}, {'alpha':10,'beta':0}, {'alpha':10,'beta':1}]
times = []
for i in range(0, len(settings)):
        times.append([])
        print(i)
        for seed in range(0, 20):
                times[i].append(solve(seed, settings[i]))
                print(seed, times[i][seed])

# Really shitty printing code
print(tabulate([[i]+[sum(times[i][j] > times[k][j] for j in range(0, len(settings))) for k in range(0, len(settings))] for i in range(0, len(settings))]), headers=['Settings']+[i for i in range(0,len(settings))])

