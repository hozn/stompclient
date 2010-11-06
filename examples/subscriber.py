"""
An example demonstrating running stompclient in subscribe-only mode.

stompclient can be used without a separate listener thread if you only want to 
subscribe to incoming messages (and don't need to get fancy in how you handle
the received frames).
"""
import logging
import pickle

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
from stompclient import PublishSubscribeClient

def frame_received(frame):
    # Do something with the frame!
    payload = pickle.loads(frame.body)
    logger.info("Received data: {0!r}".format(payload))

client = PublishSubscribeClient('127.0.0.1', 61613)
client.connect()
client.subscribe("/queue/example", frame_received)
client.listen_forever()
