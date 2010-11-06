"""
An example desmontrating a publish-subscribe usage of stompclient.

In this example it is necessary to start a thread listener loop to receive the
frames from the server.  When the listener loop is running other "response" 
frames, such as the CONNECTED frame, will also be returned by the 
PublishSubscribeClient.
"""
import threading
import logging
import time
import pickle

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from stompclient import PublishSubscribeClient

def frame_received(frame):
    # Do something with the frame!
    payload = pickle.loads(frame.body)
    logger.info("Received data: {0!r}".format(payload))

client = PublishSubscribeClient('127.0.0.1', 61613)
listener = threading.Thread(target=client.listen_forever, name='Frame-Receiver')
listener.start()

# For our example, we want to wait until the server is actually listening
client.listening_event.wait()

try:
    result = client.connect()
    logger.info("Got session response from connect: {0}".format(result.session))
    client.subscribe("/queue/example", frame_received)
    
    while True:
        time.sleep(1.0)
            
finally:
    client.shutdown_event.set()
    listener.join()