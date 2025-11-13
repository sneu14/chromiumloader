import paho.mqtt.client as mqtt
import sys
import websocket
import json
import requests
import configparser
import socket
import logging
import time

# Logging einrichten
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class URLSetter:
    def __init__(self, broker_address="localhost", broker_port=1883):
        self.broker_address = broker_address
        self.broker_port = broker_port
        
        self.instance = 0
        self.debugger_port = 9222
        self.mqtt_prefix = "chromium"
        
        self.instancestate_topic = "/___HOSTNAME___/___INSTANCE___/state/instance"
        self.instanceurl_topic = "/___HOSTNAME___/___INSTANCE___/state/url"
        
        # MQTT Client mit aktueller API-Version initialisieren
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self._setDefaultTopics()
        
    def mqtt_setport(self, port):
        self.broker_port = port
        
    def mqtt_user_pw_set(self, u,p):
        self.client.username_pw_set(u,p)
        
    def mqtt_setprefix(self, p):
        self.mqtt_prefix = p
        logger.info("Setting MQTT-Prefix to: " + self.mqtt_prefix)

    def setInstance(self, i):
        try:
            self.instance = int(i)
            self._setDefaultTopics()
        except:
            logger.warning("Invalid Instance ID: " + i)
            
    def setDebuggerPort(self, i):
        try:
            self.debugger_port = int(i)
            logger.info("Setting Debugger Port to" + self.debugger_port)
        except:
            logger.warning("Invalid Debugger Port: " + i)
            
    def addURLTopic(self, t):
        self.url_topics.append(t)
        
    def clearURLTopics(self):
        self.url_topics = []
        
    def setInstanceStateTopic(self, t):
        self.instancestate_topic = t
        logger.info("Topic for Instancestate: " + self.instancestate_topic)
        
    def connect(self):
        try:
            it = self._replaceVars(self.mqtt_prefix + self.instancestate_topic, self.instance)
            logging.info("Setting LWT to: " + it)
            self.client.will_set(it, payload="offline",qos=0, retain=True)
            self.client.connect(self.broker_address, int(self.broker_port), 60)
            self.client.publish(self._replaceVars(self.mqtt_prefix + self.instancestate_topic, self.instance),"online",0,True)
            self.client.loop_start()
            logger.info(f"Connected sucessfully to MQTT-Broker {self.broker_address}:{self.broker_port}")
            return True
        except Exception as e:
            logger.error(f"Unable to connect to MQTT Broker: {e}")
            return False
        
    def on_connect(self, client, userdata, flags, rc, properties=None):
        for x in self.url_topics:
            t = self._replaceVars(self.mqtt_prefix + x, self.instance)
            try:
                client.subscribe(t)
                logger.info("Subscription to to topic: " + t + " successful")
            except:
                logger.error("Subscription to to topic: " + t + " failed")
            
    def on_message(self, client, userdata, msg, properties=None):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        logger.info(f"Received message: {topic}: {payload}")
        
        for x in self.url_topics:
            if topic == self._replaceVars(self.mqtt_prefix + x, self.instance):
                self.load_url_in_chromium(payload)            

    def get_debugger_url(self):
        try:
            response = requests.get("http://localhost:" + str(self.debugger_port) + "/json")
            response.raise_for_status()
            debugger_info = response.json()
            return debugger_info[0]["webSocketDebuggerUrl"]
        except (requests.RequestException, IndexError, KeyError):
            print("Fehler beim Abrufen der Debugger-URL.")
            return None

    def load_url_in_chromium(self, url):
        websocket_url = self.get_debugger_url()
        if not websocket_url:
            print("Unable to connect to Chromium. Make sure that Chromium ist started with the option --remote-debugging-port=" + debugger_port)
            return
        
        try:
            ws = websocket.create_connection(websocket_url)
            ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
            
            ws.send(json.dumps({
                "id": 2,
                "method": "Page.navigate",
                "params": {"url": url}
            }))
            logging.info(f"Loading URL {url}")
            tabs = requests.get("http://localhost:" + str(self.debugger_port) + "/json").json()
            if len(tabs) > 0:
                self.client.publish(self._replaceVars(self.mqtt_prefix + self.urlstate_topic,self.instance),tabs[0].get('url'),0,True)
                logging.info("Loaded URL: " + tabs[0].get('url'))
            
            ws.close()
        except Exception as e:
            print(f"Failed to connect to Chromium: {e}")
            
    def _setDefaultTopics(self):
        self.instancestate_topic = "chromium/___HOSTNAME___/___INSTANCE___/state/instance"
        self.urlstate_topic = "chromium/___HOSTNAME___/___INSTANCE___/state/url"
        self.url_topics = [
             "chromium/___HOSTNAME___/___INSTANCE___/url",
            "chromium/all/___INSTANCE___/url",
            "chromium/___HOSTNAME___/all/url",
            "chromium/all/all/url"
            ]
            
    def _replaceVars(self, value, mvalue):
            return value.replace("___HOSTNAME___",socket.gethostname()).replace("___INSTANCE___",str(mvalue))


if __name__ == "__main__":
    try:
        configFile = "config.ini"
        if len(sys.argv) >= 2:
            configFile = sys.argv[1]

        config = configparser.ConfigParser()
        logger.info("Verwende Configdatei: " + configFile)
        
        config.read(configFile)
        try:
            BROKER_ADDRESS = config['Connection']['Broker']
        except:
            BROKER_ADDRESS = "localhost"
        
        try:
            BROKER_PORT = int(config['Connection']['Port'])
        except:
            BROKER_PORT = 1883
            
            
        urlsetter = URLSetter(BROKER_ADDRESS)
        
        try:
            urlsetter.mqtt_user_pw_set(config['Connection']['Username'], config['Connection']['Password'])
        except:
            logger.info("Keine Zugangsdaten für MQTT-Broker gesetzt")
            
        try:
            urlsetter.mqtt_setport(config['Connection']['Port'])
        except:
            logger.info("Verwende 1833 als MQTT-Port")
            
        t = "0"
        try:
            t = config['General']['Instance']
            urlsetter.setInstance(int(t))
        except:
            logger.info("Unable to read Instance from config. Using default")
            
        t = ""
        try:
            t = config['Connection']['TopicPrefix']
            urlsetter.mqtt_setprefix(t)
        except:
            logger.info("Unable to read MQTT-Prefix.")
        
        t = ""
        try:
            t = config['Instance-Topics']['State']
            urlsetter.setInstanceStateTopic(str(t))
        except:
            logger.info("Topic für Instanz Status: " + str(t))
        
        t = ""
        try:
            t = config['Instance-Topics']['URL']
            urlsetter.setURLStateTopic(t)
        except:
            logger.info("Topic für URL Status: " + t)
            
        section = "URL-Topics"
        if config.has_section(section):
            urlsetter.clearURLTopics()    
            for x in dict(config.items(section)):
                urlsetter.addURLTopic(config[section][x])
                
        if config.has_option('Chromium', 'Debugger-Port'):
            try:
                urlsetter.setDebuggerPort(int(config['Chromium']['Debugger-Port']))
            except:
                logger.info("Invalid Debugger Port in config. Using 9222")

                
        if ( not urlsetter.connect()):
            exit(1)
        
        # Endlosschleife um das Programm am Laufen zu halten
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Programm durch Benutzer beendet")
            
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e.with_traceback()}")