import paho.mqtt.client as mqtt
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import precision_score, recall_score
import partitionfunctions_python as partf
import numpy as np
import pandas as pd
from io import StringIO
import sys
import os
import signal

#los clientes se subscriben a su particion y publican los resultados
#ARRANCAR PRIMERO LOS CLASIFICADORES

#CLASIFICADORES

def knn(partition, test):#partition es un pandas.DataFrame
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    clf = KNeighborsClassifier(n_neighbors = 2)
    clf.fit(trainset, trainclasses)
    testClass = clf.predict_proba(test[:].values)
    return testClass

def rf(partition, test):
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    rfc = RandomForestClassifier()
    rfc.fit(trainset, trainclasses)
    testClass = rfc.predict_proba(test[:].values)
    return testClass

def xgb(partition, test):
    partition = partition.to_numpy()
    nVars = np.shape(partition)[1] - 1
    trainset = partition[:, np.arange(nVars)]
    trainclasses = partition[:,[nVars]].flatten()
    gbc = GradientBoostingClassifier()
    gbc.fit(trainset, trainclasses)
    testClass = gbc.predict_proba(test[:].values)
    return testClass

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
BROKER_IP = "192.168.1.140"

CLASSIFIERID = sys.argv[1]

def extractData(message):
    message = message.replace("\\n", "\n")
    splitedMsg = message.split("$")
    partitions = pd.read_csv(StringIO(splitedMsg[0][2:]))
    distance = float(splitedMsg[1])
    test = pd.read_csv(StringIO(splitedMsg[2]))
    dsName = splitedMsg[3][:-1]
    return partitions, distance, test, dsName

#ENTRENAMIENTO Y CLASIFICACION

def classify(partition, distance, test):
    #TEMPORALMENTE SOLO KNN

    #obtenemos belief values
    classifierOutput = knn(partition, test)
    #pesamos los belief values
    for i in range(len(classifierOutput)):
        for j in range(len(classifierOutput[i])):
            classifierOutput[i][j] = classifierOutput[i][j] * distance
    return str(classifierOutput) 

#MQTT
#se llama al conectarse al broker
def on_connect(client, userdata, flags, rc):
    print("Connected classification client with result code " + str(rc))
    #nos subscribimos a este tema
    client.subscribe("partition/" + CLASSIFIERID)
    client.subscribe("exit")
    print("\nSubscribed to partition/" + CLASSIFIERID)

#se llama al obtener un mensaje del broker
def on_message(client, userdata, msg):
    if (msg.topic == "exit"):
        os.kill(os.getppid(), signal.SIGHUP)
    partition, distance, test, dsName = extractData(str(msg.payload))
    classifiedData = classify(partition, distance, test)
    print("pubish weighed belief values:\n", classifiedData)
    client.publish("results/" + CLASSIFIERID + "." + dsName, classifiedData)

client = mqtt.Client("clas_client_" + CLASSIFIERID)
client.on_connect = on_connect
client.on_message = on_message

#conectamos con el broker
client.connect(BROKER_IP, 1883)

client.loop_forever()