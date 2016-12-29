#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import pandas as pd
import numpy as np
from sklearn import svm
from sklearn.externals import joblib
from pathlib import Path
import sys,logging

if len(sys.argv) > 2:
	host = sys.argv[1]
	basepath = Path(sys.argv[2])
else:
	print("A host and path are required. Eg: {} hostname /path/to/themachine".format(sys.argv[0]))
	print("Optionally takes a port number as the 3rd argument")
	sys.exit()

port = 1883
if len(sys.argv) > 3:
    port = sys.argv[3]

if not (basepath.is_dir()):
	print("{} either does not exist or is not a directory".format(basepath))


def main():
    proc_name = Path(sys.argv[0])
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        filename=basepath.joinpath(proc_name.stem + ".log").as_posix(), 
        level=logging.INFO
    )
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, 60)
    client.loop_forever()


def learn(payload):
    try:
        (location,item,state,inTemp,inHum,outTemp,outHum) = payload.split(",")
    except ValueError:
        logging.error("Incorrect learn payload: {}".format(payload))
        return

    logging.info("Learn: {}".format(payload))

    loc_path = basepath.joinpath(location)
    loc_path.mkdir(exist_ok=True)
    train_file = loc_path.joinpath(item + ".csv")
    pkl_file = loc_path.joinpath(item + ".pkl")

    if not train_file.is_file():
        data = "state,inTemp,inHum,outTemp,outHum"
        train_file.write_text(data)
    
    df = pd.read_csv(train_file)
    state_num = 1 if state == "ON" else 0
    df.loc[len(df)] = [state_num,inTemp,inHum,outTemp,outHum]
    df.to_csv(str(train_file), index=False)

    df = df.drop(df.columns[[2,4]], axis=1) # simplify model initially
    train_labels = df.state
    labels = list(set(train_labels))
    train_labels = np.array([labels.index(x) for x in train_labels])
    train_features = df.iloc[:,1:]
    train_features = np.array(train_features)

    # Classiefier will fail until there are positive/negative datapoints
    # Let it fail without barfing until it can.
    try:
        classifier = svm.SVC()
        classifier.fit(train_features, train_labels)
        joblib.dump(classifier, pkl_file)
    except Exception:
        pass


def change(payload,client):
    try:
        (location,inTemp,inHum,outTemp,outHum) = payload.split(",")
    except ValueError:
        logging.error("Incorrect change payload: {}".format(payload))
        return
    
    logging.info("Change: {}".format(payload))
    loc_path = basepath.joinpath(location)
    if not (loc_path.is_dir()):
        return
    
    for pkl in list(Path(loc_path).glob('*.pkl')):
        classifier = joblib.load(pkl.name)
        decide = classifier.decision_function([[ inTemp, outTemp ]])[0] * 100

        if (decide > 95):
            client.publish("/themachine/{}/{}".format(location,pkl.stem), "ON")
            logging.info("I'm {0:.2f}% sure you wanted the {1} on".format(decide,pkl.stem))

        if (decide < -95):
            client.publish("/themachine/{}/{}".format(location,pkl.stem), "OFF")
            logging.info("I'm {0:.2f}% sure you wanted the {1} off".format(decide * -1,pkl.stem))


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("/themachine/learn")
    client.subscribe("/themachine/change")


def on_message(client, userdata, msg):
    payload_string = str(msg.payload,'utf-8')

    if (msg.topic.endswith("learn")):
        learn(payload_string)
    
    if (msg.topic.endswith("change")):
        change(payload_string,client)
    

if __name__ == '__main__':
      main()
