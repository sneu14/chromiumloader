import paho.mqtt.client as mqtt
import websocket
import json
import requests
import configparser
import socket

mqtt_host = ""
mqtt_port = 0
mqtt_user = ""
mqtt_pasword = ""
state_topic = ""
topic1 = ""
topic2 = ""
debugger_port = 0


def readConfig(configFile):
    global mqtt_host
    global mqtt_port
    global mqtt_user
    global mqtt_password
    global topic1
    global topic2
    global state_topic
    global debugger_port
    config = configparser.ConfigParser()
    config.read(configFile)
    mqtt_host = config['Connection']['Broker']
    mqtt_port = int(config['Connection']['Port'])
    mqtt_user = config['Connection']['Username']
    mqtt_password = config['Connection']['Password']
    topic1 = config['Topics']['URL-Topic1'].replace("___HOSTNAME___",socket.gethostname())
    topic2 = config['Topics']['URL-Topic2'].replace("___HOSTNAME___",socket.gethostname())
    state_topic = config['Topics']['State'].replace("___HOSTNAME___",socket.gethostname())
    debugger_port = int(config['Chromium']['Debugger-Port'])

def get_debugger_url():
    try:
        response = requests.get("http://localhost:" + str(debugger_port) + "/json")
        response.raise_for_status()
        debugger_info = response.json()
        return debugger_info[0]["webSocketDebuggerUrl"]
    except (requests.RequestException, IndexError, KeyError):
        print("Fehler beim Abrufen der Debugger-URL.")
        return None

def load_url_in_chromium(url):
    websocket_url = get_debugger_url()
    if not websocket_url:
        print("Unable to connect to Chromium. Make sure that Chromium ist started with the option --remote-debugging-port=" + debugger_port)
        return
    
    try:
        ws = websocket.create_connection(websocket_url)
        ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
        print("Page-Domain activated.")
        
        ws.send(json.dumps({
            "id": 2,
            "method": "Page.navigate",
            "params": {"url": url}
        }))
        print(f"Loaded URL {url}")
        
        ws.close()
    except Exception as e:
        print(f"Failed to connect to Chromium: {e}")
        
def on_connect(client, userdata, flags, reason_code, properties):
    global topic1
    global topic2
    print(f"Connected with result code {reason_code}")
    if ( topic1 != "" ):
        print("Subscribing to: " + topic1)
        client.subscribe(topic1)
    if ( topic2 != "" ):
        print("Subscribing to: " + topic2)
        client.subscribe(topic2)
    client.publish(state_topic,"online",0,True)

def on_message(client, userdata, msg):
    global url_to_load
    url_to_load = str(msg.payload.decode("utf-8"))
    load_url_in_chromium(url_to_load)


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

readConfig('config.ini')

mqttc.username_pw_set(mqtt_user,mqtt_password)
mqttc.will_set(state_topic, payload="offline",qos=0, retain=True)
print("Connecting to MQTT-Broker: " + mqtt_host + ":" + str(mqtt_port))
mqttc.connect(mqtt_host,mqtt_port, 10)
mqttc.publish(state_topic,"online",0,True)

mqttc.loop_forever()
