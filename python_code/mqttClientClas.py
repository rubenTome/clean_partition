import paho.mqtt.client as mqtt
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score
import partitionfunctions_python as partf
import numpy as np
import csv
from prettytable import PrettyTable
import pandas as pd
from io import StringIO
import sys

#los clientes se subscriben a su particion y publican los resultados
#ARRANCAR PRIMERO LOS CLASIFICADORES

 #CLASIFICADORES

def knn(partition, ds):#partition es un pandas.DataFrame
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    clf = KNeighborsClassifier(n_neighbors = 2)
    clf.fit(trainset, trainclasses)
    score = clf.score(ds["testset"].to_numpy(), ds["testclasses"].to_numpy().flatten())
    if(len(np.unique(trainclasses)) == 2):
        av = "binary"
    else:
        av = "weighted"
    precision = precision_score(ds["testclasses"].to_numpy().flatten(), 
                                clf.predict(ds["testset"].to_numpy()), average=av)
    recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                        clf.predict(ds["testset"].to_numpy()), average=av)

    return [score, precision, recall]

def rf(partition, ds):
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    rfc = RandomForestClassifier()
    rfc.fit(trainset, trainclasses)
    scores = rfc.score(ds["testset"].to_numpy(), ds["testclasses"].to_numpy().flatten())
    if(len(np.unique(trainclasses)) == 2):
        av = "binary"
    else:
        av = "weighted"
    precision = precision_score(ds["testclasses"].to_numpy().flatten(), 
                                rfc.predict(ds["testset"].to_numpy()), average=av)
    recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                        rfc.predict(ds["testset"].to_numpy()), average=av)
    return [scores, precision, recall]

def xgb(partition, ds):
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    gbc = GradientBoostingClassifier()
    gbc.fit(trainset, trainclasses)
    scores = gbc.score(ds["testset"].to_numpy(), ds["testclasses"].to_numpy().flatten())
    if(len(np.unique(trainclasses)) == 2):
        av = "binary"
    else:
        av = "weighted"
    precision = precision_score(ds["testclasses"].to_numpy().flatten(), 
                                gbc.predict(ds["testset"].to_numpy()), average=av)
    recall = recall_score(ds["testclasses"].to_numpy().flatten(), 
                          gbc.predict(ds["testset"].to_numpy()), average=av)
    return [scores, precision, recall]


#PARAMETROS 

totalresults = None

#numero de cifras decimales
NDECIMALS = 2

#generar tablas con los resultados (+legible)
generateTables = True

classifiers = [knn, rf, xgb]

#names for printing them
namesclassifiers = ["KNN", "RF", "XGB"] 

#debe ser el nombre o ip
BROKER_IP = "192.168.1.143"

CLASSIFIERID = sys.argv[1]

#CREACION DE CLASIFICADORES

#partitions: datos de la particion asignada
#Pset: numero de particiones que queremos crear
#partition: numero de particion dentro del Pset
#dataset: nombre del dataset usado para la particion
#ds: conjunto total de todos los datos seleccionados del dataset
def classifier(partitions, Pset, partition, dataset, ds):
    classifAcc = {}
    for c in range(len(classifiers)):
        classifAcc[namesclassifiers[c] + "_" + Pset + "_" + partition] = (
        classifiers[c](partitions, ds))

    #guardamos en un csv la informacion de cada clasificador en classifAcc
    splitedPath = dataset.split("/")
    name = splitedPath[len(splitedPath) - 1]
    file = open("rdos_python/rdos_" + name, "w")
    if generateTables:
        fileTable = open("rdos_python/tabla_rdos_" + name.split(".")[0] + ".txt", "w")
        headers = PrettyTable(["classifier", "npartitions", "partition", "accurancy", "precision", "recall", "energy"])
        headers.align = "l"
    writer = csv.writer(file)
    writer.writerow(["classifier", "npartitions", "partition", "accurancy", "precision", "recall", "energy"])
    for t in range(len(classifAcc)):
        label = list(classifAcc)[t]
        classifier = classifAcc[label]
        splitedName = label.split("_")
        actualData = partitions.to_numpy()
        actualData = actualData[:, np.arange(np.shape(actualData)[1] - 1)]
        energyDist = partf.end(actualData, ds["trainset"].values.tolist(), True)
        if generateTables:
            headers.add_row([splitedName[0], splitedName[1], splitedName[2], 
                            round(classifier[0], NDECIMALS), round(classifier[1], NDECIMALS), 
                            round(classifier[2], NDECIMALS), round(energyDist, NDECIMALS)])
        writer.writerow([splitedName[0], splitedName[1], splitedName[2], 
                        round(classifier[0], NDECIMALS), round(classifier[1], NDECIMALS), 
                        round(classifier[2], NDECIMALS), round(energyDist, NDECIMALS)])
    if generateTables:
        fileTable.write(str(headers))

    file.close()
    return open("rdos_python/rdos_" + name, "r").read()

def extractData(message):
    message = message.replace("\\n", "\n")
    splitedMsg = message.split("$")
    partitions = pd.read_csv(StringIO(splitedMsg[0][2:]))
    distance = float(splitedMsg[1])
    dsName = splitedMsg[2][:-1]
    return partitions, distance, dsName

def classify(partition, distance, dsName):
    return "RESULTADOS" + "_" + CLASSIFIERID + "_" +  dsName 

#MQTT
#se llama al conectarse al broker
def on_connect(client, userdata, flags, rc):
    print("Connected classification client with result code " + str(rc))
    #nos subscribimos a este tema
    client.subscribe("partition/" + CLASSIFIERID)
    print("\nSubscribed to partition/" + CLASSIFIERID)

#se llama al obtener un mensaje del broker
def on_message(client, userdata, msg):
    partition, distance, dsName = extractData(str(msg.payload))
    classifiedData = classify(partition, distance, dsName)
    client.publish("results/" + CLASSIFIERID + "." + dsName, classifiedData)

client = mqtt.Client("clas_client_" + CLASSIFIERID)
client.on_connect = on_connect
client.on_message = on_message

#conectamos con el broker
client.connect(BROKER_IP, 1883)

client.loop_forever()