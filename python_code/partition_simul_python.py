from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score
import partitionfunctions_python as partf
#import fine_analisis_python as fan
import numpy as np
import csv

#1º knn3, 2º rf, 3º xgb, 4º mult
#import de partitionfunctions_python muy lento -> DEBIDO A IMPORT DE DCOR
#recall y accurancy tienen siempre el mismo valor

#CLASIFICADORES

def knn(partition):#partition es un pandas.DataFrame
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    clf = KNeighborsClassifier(n_neighbors = 2)
    clf.fit(trainset, trainclasses)
    score = clf.score(ds["testset"].to_numpy(), ds["testclasses"].to_numpy().flatten())
    #revisar parametro average
    precision = precision_score(ds["testclasses"].to_numpy().flatten(), 
                                clf.predict(ds["testset"].to_numpy()), average="weighted")
    if(len(np.unique(trainclasses)) == 2):
        recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                              clf.predict(ds["testset"].to_numpy()), average="binary")
    else:
        recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                              clf.predict(ds["testset"].to_numpy()), average="weighted")
    return [score, precision, recall]

def rf(partition):
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    rfc = RandomForestClassifier()
    rfc.fit(trainset, trainclasses)
    scores = rfc.score(ds["testset"].to_numpy(), ds["testclasses"].to_numpy().flatten())
    precision = precision_score(ds["testclasses"].to_numpy().flatten(), 
                                rfc.predict(ds["testset"].to_numpy()), average="weighted")
    if(len(np.unique(trainclasses)) == 2):
        recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                              rfc.predict(ds["testset"].to_numpy()), average="binary")
    else:
        recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                              rfc.predict(ds["testset"].to_numpy()), average="weighted")
    return [scores, precision, recall]

def xgb(partition):
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    gbc = GradientBoostingClassifier()
    gbc.fit(trainset, trainclasses)
    scores = gbc.score(ds["testset"].to_numpy(), ds["testclasses"].to_numpy().flatten())
    precision = precision_score(ds["testclasses"].to_numpy().flatten(), 
                                gbc.predict(ds["testset"].to_numpy()), average="weighted")
    if(len(np.unique(trainclasses)) == 2):
        recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                              gbc.predict(ds["testset"].to_numpy()), average="binary")
    else:
        recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                              gbc.predict(ds["testset"].to_numpy()), average="weighted")
    return [scores, precision, recall]


#PARAMETROS 

totalresults = None

#numero de cifras decimales
NDECIMALS = 5
#how many reps per experiment
NREP = 5
#size of the total dataset (subsampple)
NSET = 1000
#size of the train set, thse size of the test set will be NSET - NTRAIN
NTRAIN = 500

#number of partitions
Pset = [4]

is_balanced = False

datasets = ["../scenariosimul/scenariosimulC2D2G3STDEV0.15.csv", 
            "../scenariosimul/scenariosimulC8D3G3STDEV0.05.csv"]

#some datasets are split into train and test, because of concept drift
testdatasets= [""]

classifiers = [knn, rf, xgb]

#names for printing them
namesclassifiers = ["KNN", "RF", "XGB"] 


#SIMULACION
for d in range(len(datasets)):
    
    ds = partf.load_dataset(datasets[d], NSET, NSET - NTRAIN)

    #creamos las particiones segun parametro is_balanced
    if is_balanced:
        partitionFun = partf.create_random_partition
    else:
        partitionFun = partf.create_perturbated_partition
    partitions = [[] for _ in range(len(Pset))]
    for p in range(len(Pset)):
            partitions[p] = partitionFun(ds["trainset"], ds["trainclasses"], Pset[p])

    #creamos los clasificadores con cada una de las particiones
    classifAcc = {}
    for ps in range(len(Pset)):
        for c in range(len(classifiers)):
            for pa in range(len(partitions[ps])):
                classifAcc[namesclassifiers[c] + "_" + str(Pset[ps]) + "_" + str(pa + 1)] = (
                classifiers[c](partitions[ps][pa]))

    #guardamos en un csv la informacion de cada clasificador en classifAcc
    splitedPath = datasets[d].split("/")
    name = splitedPath[len(splitedPath) - 1]
    file = open("rdos_python/rdos_" + name, "w")
    writer = csv.writer(file)
    writer.writerow(["classifier", "npartitions", "partition", "accurancy", "precision", "recall"])
    for t in range(len(classifAcc)):
        label = list(classifAcc)[t]
        classifier = classifAcc[label]
        splitedName = label.split("_")
        writer.writerow([splitedName[0], splitedName[1], splitedName[2], round(classifier[0], NDECIMALS), 
                        round(classifier[1], NDECIMALS), round(classifier[2], NDECIMALS)])