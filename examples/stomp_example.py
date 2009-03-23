#!/usr/bin/env python
import sys,time
from stomp import Stomp

def consume(host,port,queue):
    try:
        stomp = Stomp(host,port)
        stomp.connect()
    except:
        print "Cannot connect"
        raise
    
    stomp.subscribe({'destination':queue,
                     'ack':'client'})

    while True:
        try:
            frame = stomp.receive_frame()
            stomp.ack(frame)
            print frame.headers['message-id']
            print frame.body
        except KeyboardInterrupt:
            stomp.disconnect()
            break

def produce(host,port,queue,num=1000):
    try:
        stomp = Stomp(host,port)
        stomp.connect()
    except:
        print "Cannot connect"
        raise
    for i in xrange(0,num):
        print "Message #%d" % i
        start = time.time()
        print stomp.send({'destination':queue,
                          'body':'Testing %d' % i,
                          'persistent':'true'}).headers['receipt-id']
        stop = time.time()
        print (stop - start) * 1000.0

    stomp.disconnect()

if __name__ == '__main__':
    #host  = 'localhost'
    host = 'localhost'
    #queue = '/queue/python_stomp_example'
    queue = '/queue/ben_test_stomp'
    port  = 61613
    if sys.argv[1] == 'produce':
        if len(sys.argv) == 3:
            produce(host,port,queue,num=int(sys.argv[2]))
        else:
            produce(host,port,queue)
    if sys.argv[1] == 'consume':
        consume(host,port,queue)
