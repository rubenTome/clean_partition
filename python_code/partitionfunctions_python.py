import rpy2.robjects as ro
from numpy import array, asarray, arange, unique, floor, flip, sum, append, delete
from numpy.random import uniform
from scipy.spatial import distance_matrix
#from scipy.stats import energy_distance
import random
from pandas import DataFrame, concat, read_csv
import sys
from math import exp
from dcor import energy_distance

# ditancia "energy" energy.stat
energy_r = ro.r('''
    energy_r = function (X , Y ) {
    X = as.matrix(X)
    Y = as.matrix(Y)
    energy::eqdist.e(rbind(X,Y), c(nrow(X), nrow(Y))) / var(as.vector(rbind(X,Y)))
    }
''')

#x e y son del tipo list
def end_R(x, y):
    x = array(x)
    y = array(y)
    return float(asarray(energy_r(ro.r.matrix(ro.FloatVector(x.flatten(order="F")), nrow=x.shape[0]),
                                  ro.r.matrix(ro.FloatVector(y.flatten(order="F")), nrow=y.shape[0]))))

def end_P(x, y):
    return (energy_distance(x, y))

def sample_n_from_csv(filename:str, n:int=100, total_rows:int=None) -> DataFrame:
    if total_rows==None:
        with open(filename,"r") as fh:
            total_rows = sum(1 for row in fh)
    if(n>total_rows):
        print("Error: n > total_rows", file=sys.stderr) 
    skip_rows =  random.sample(range(1,total_rows+1), total_rows-n)
    return read_csv(filename, skiprows=skip_rows)

#TODO revisar funcionamiento de load_dataset 
def load_dataset(filename, trainsize, testsize, testfilename = "", classesList=[]):
    dataset = {
        "trainset": None,
        "trainclasses": None,
        "testset": None,
        "testclasses": None
    }
    extra = 1
    if len(classesList > 0):
        extra += 0.5
    if testfilename == "":
        samp = sample_n_from_csv(filename, round((trainsize + testsize) * extra)).sample(frac = 1)
    else:
        samp = sample_n_from_csv(filename, round(trainsize * extra)).sample(frac = 1)
    sampShape = samp.shape
    if (len(classesList) > 0):
        #calculamos clases eliminadas
        uniqueClasses = unique(samp["classes"])
        if (len(uniqueClasses) < len(classesList)):
            exit("ERROR: invalid classes number ", classesList)
        deletedClasses = list(set(uniqueClasses) ^ set(classesList))
        #eliminamos esas clases de todo el dataset
        for i in range(len(deletedClasses)):
            samp = samp.drop(samp[samp["classes"] == deletedClasses[i]].index)
    #indices de filas en trainset y testset son secuenciales no aleatorios
    dataset["trainset"] = samp.iloc[:trainsize, arange(sampShape[1] - 1)]
    dataset["trainclasses"] = samp.iloc[:trainsize].loc[:, "classes"]

    if testfilename == "":
        dataset["testset"] = samp.iloc[trainsize:trainsize + testsize, arange(sampShape[1] - 1)]
        dataset["testclasses"] = samp.iloc[trainsize:trainsize + testsize].loc[:, "classes"]
    else:
        print("selected file for testing: ", testfilename)
        testSamp = sample_n_from_csv(testfilename, round(testsize * extra)).sample(frac = 1)
        if (len(classesList) > 0):
            for i in range(len(deletedClasses)):
                testSamp = testSamp.drop(testSamp[testSamp["classes"] == deletedClasses[i]].index)
        testSampShape = testSamp.shape
        dataset["testset"] = testSamp.iloc[:testsize, arange(testSampShape [1] - 1)]
        dataset["testclasses"] = testSamp.iloc[:testsize].loc[:, "classes"]
    return dataset   

#classesDist: matriz, cada fila un nodo, cada elemento una clase
#TODO crear una version desbalanceada de create_selected_partition
def create_selected_partition(trainset, trainclasses, npartitions, classesDist):
    if (npartitions != len(classesDist)):
        #classesDist debe tener npartitions filas
        exit("Error in create_selected_partition: classesDist not valid")

    classes, count = unique(trainclasses, return_counts=True)
    print("counts per class in train: ", count)
    classesLen = len(classes)
    joined = concat([trainset, trainclasses.reindex(trainset.index)], axis=1)
    groups = joined.groupby(["classes"], group_keys=True).apply(lambda x: x)
    groupsList = [DataFrame() for _ in range(classesLen)]
    partitions = [DataFrame() for _ in range(npartitions)]

    for i in range(classesLen):
        groupsList[i] = groups.xs(classes[i], level = "classes").reset_index(drop=True)
    
    for i in range(len(classesDist)):
        for j in range(len(classesDist[i])):
            for k in range(len(groupsList)):
                if(len(groupsList[k]) > 0 and 
                   groupsList[k].at[0, "classes"] == classesDist[i][j]):
                        partitions[i] = concat([partitions[i], groupsList[k]])

    return partitions
    
def create_random_partition(trainset, trainclasses, npartitions):
    classes, count = unique(trainclasses, return_counts=True)
    print("counts per class: ", count)
    classesLen = len(classes)
    joined = concat([trainset, trainclasses.reindex(trainset.index)], axis=1)
    groups = joined.groupby(["classes"], group_keys=True).apply(lambda x: x)

    #groupsList es una lista con 1 dataframe por clase
    groupsList = [DataFrame() for _ in range(classesLen)]
    for i in range(classesLen):
        groupsList[i] = groups.xs(classes[i], level = "classes")

    #groupListPart es una lista que subdivide cada dataframe de groupList npartition veces
    groupsListPart = [DataFrame() for _ in range(classesLen * npartitions)]
    for i in range(classesLen):
        gListShape = groupsList[i].shape
        for j in range(npartitions):
            groupsListPart[i * npartitions + j] = groupsList[i].sample(
                                                    n = floor(gListShape[0] / npartitions).astype(int), replace = True)
    
    #partition es el resultado de create_random_partition() 
    partitions = [DataFrame() for _ in range(npartitions)]
    for i in range(npartitions):
        #TODO ERROR CON MNIST ???
        partitions[i] = groupsListPart[i]
        for j in range(1, classesLen):
            partitions[i] = concat([partitions[i].reset_index(drop = True), 
                                groupsListPart[i + j * npartitions]])
    
    return partitions

def tablef(list, trainclasses):
    classes = unique(trainclasses)
    table = [0 for _ in range(len(classes))]
    for i in range(len(classes)):
        for j in range(len(list)):
            if classes[i] == list[j]:
                table[i] += 1
    return table

def whichf(arr, n):
    indexes = []
    for i in range(len(arr)):
        if arr[i] == n:
            indexes.append(i)
    return indexes

def deleteRowsDf(dataframe, rows):
    rows.sort()
    rows = flip(rows)
    for i in range(len(rows)):
        dataframe.drop([dataframe.index[rows[i]]], inplace=True)
    return dataframe

def create_perturbated_partition(trainset, trainclasses, npartitions):
    listRes = [[] for _ in range(npartitions)]

    remainingset = DataFrame(trainset)
    remainingclasses = array(trainclasses)
    uniqueTC = unique(trainclasses)
    C = len(uniqueTC)
    partitions = []
    partitionclasses = [[] for _ in range(npartitions - 1)]

    for i in range(npartitions-1):
        N = len(remainingclasses)
        P = npartitions - i
        prop = array(tablef(remainingclasses, trainclasses)) / N
        dev = prop * uniform(0.1, 0.9, C)
        dev = dev / sum(dev)
        
        if i == 0:
            dev = prop

        observations = floor(dev * (N / P))
        partitions.append(DataFrame())
        
        for j in range(C):
            rem = whichf(remainingclasses, uniqueTC[j])

            if (len(rem) == 0):
                exit("ERROR NO ELEMENTS  OF CLASS " + str(j))

            nobs = observations[j]

            if ((nobs == [0]).all()):
                nobs = 1

            nremclass = len(rem) - 1 #menos uno ?
            nobs = int(min(nobs, nremclass))
            selectedobs = array(random.sample(rem, nobs))

            if (len(rem) == 1):
                selectedobs = rem

            partitions[i] = concat([partitions[i], remainingset.iloc[selectedobs]], ignore_index = True)

            partitionclasses[i] = append(partitionclasses[i], remainingclasses[selectedobs]).astype("int")

            if((tablef(remainingclasses, trainclasses)[j] - nobs) < 1):
                toadd = nobs
                remainingset = concat([remainingset, remainingset.iloc[rem[:toadd]]])
                remainingclasses = append(remainingclasses, [remainingclasses[i] for i in rem[:toadd]])  

            remainingset = deleteRowsDf(remainingset, selectedobs)
            remainingclasses = delete(remainingclasses, selectedobs)

    partitions.append(remainingset)
    partitionclasses.append(remainingclasses)
    for i in range(npartitions):        
        lenPartClass = len(partitionclasses[i])
        lenPart = partitions[i].shape[0]
        while (lenPart != lenPartClass):
            partitionclasses[i] = delete(partitionclasses[i], lenPartClass - 1)
        
        partitions[i]["classes"] = partitionclasses[i]
        listRes[i] = partitions[i]

    return listRes

def distancef(x, y):
    arrXY = concat([x, y])
    distances = distance_matrix(arrXY, arrXY)
    dshape = distances.shape
    for i in range(dshape[0]):
        for j in range(dshape[1]):
            distances[i][j] = exp(- distances[i][j])
    return DataFrame(distances)

def energy_wheights_sets(trainset, testset, bound=4):
    result = {
        "weights": None,
        "val": None
    }
    n = trainset.shape[0]
    distances = distancef(trainset, testset)
    K = distances.iloc[0:n, 0:n]
    k = distances.iloc[0:n, n:n + testset.shape[0]]
    WB = distances.iloc[n:n + testset.shape[0], n:n + testset.shape[0]]
    k = k.mean(axis = 1)
    B = 0
    c = array(-k)
    H = K
    H =  H.to_numpy().flatten(order="F")
    A = zeros((n, n))
    for i in range(A.shape[1]):
        A[0][i] = 1
    A = A.flatten(order="F")
    b = zeros(n)
    r = ones(n)
    l = zeros(n)
    u = ones(n)
    bound = bound

    ipopf = ro.r('''
    ipopf = function (c, H, A, b, l, u, r, bound) {
        library(kernlab)
        primal(ipop(c, H, A, b, l, u, r, sigf=4, maxiter = 45, bound=bound, margin = 0.01, verb=FALSE))
    }''')

    result["weights"] = ipopf(ro.vectors.FloatVector(c),
                            ro.r.matrix(ro.FloatVector(H), nrow=n),
                            ro.r.matrix(ro.IntVector(A), nrow=n),
                            ro.vectors.IntVector(b),
                            ro.vectors.IntVector(l),
                            ro.vectors.IntVector(u),
                            ro.vectors.IntVector(r),
                            bound)
    result["val"] = (matmul(-2 * array(k), result["weights"]) + 
                     matmul(matmul(result["weights"], K), result["weights"]) + 
                     WB.stack().mean())

    return result

#no usada
def kfun(x, y):
    return -sum(power(subtract(x, y), 2)) + sum(power(x, 2)) + sum(power(y, 2))