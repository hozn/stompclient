#!/usr/bin/env python
import sys
sys.path.append('../')
from stomp import Stomp

def test_consume(host,queue):
    try:
        stomp = Stomp(host,61613)
        stomp.connect()
    except:
        print "Cannot connect"
        raise
    
    stomp.subscribe({'destination':queue,
                     'ack':'client'})
    while True:
        frame = stomp.receive_frame()
        print frame.headers['message-id']
        stomp.ack(frame)

    stomp.disconnect()

def test_produce(host,queue):
    stomp = Stomp(host,61613)
    stomp.connect()
    for i in xrange(1,1000):
        stomp.send({'destination':queue,
                    'body':'Testing',
                    'persistent':'true'})

    stomp.disconnect()

dev = 'ag20120.ops.ag.com'
queue = '/queue/ben_test_stomp'
test_produce(dev,queue)
test_consume(dev,queue)
