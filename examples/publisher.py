import time
import logging
import pickle
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from stompclient import PublishClient

client = PublishClient('127.0.0.1', 61613)
client.connect()

try:
    payload = {'key': 'value', 'counter': 0, 'list': ['a', 'b', 'c'], 'date': datetime.now()}
    while True:
        logger.debug("Sending message: {0}".format(payload))
        client.send('/queue/example', pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))
        time.sleep(1.0)
        payload['counter'] += 1
        payload['date'] = datetime.now()
finally:
    client.disconnect()