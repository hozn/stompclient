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
        try:
            frame = stomp.receive_frame()
            print frame.headers['message-id']
            stomp.ack(frame)
        except KeyboardInterrupt:
            stomp.disconnect()
            break

def test_produce(host,queue):
    try:
        stomp = Stomp(host,61613)
        stomp.connect()
    except:
        print "Cannot connect"
        raise
    for i in xrange(1,1000):
        stomp.send({'destination':queue,
                    'body':'Testing',
                    'persistent':'true'})

    stomp.disconnect()

if __name__ == '__main__':
    dev = 'ag20120.ops.ag.com'
    queue = '/queue/ben_test_stomp'
    #test_produce(dev,queue)
    test_consume(dev,queue)
