#!/usr/bin/env python
import sys
import itertools
from stompy import Client as StompClient
from itertools import count
from optparse import OptionParser


def consume(host, port, queue, num=None):
    stomp = StompClient(host, port)
    stomp.connect()

    stomp.subscribe(queue, ack="client")

    def _handle_message(frame):
        print(frame.headers.get("message-id"))
        print(frame.body)
        stomp.ack(frame)

    # if num is not set, iterate forever.
    it = xrange(0, num) if num else itertools.count()

    try:
        for i in it:
            frame = stomp.get()
            _handle_message(frame)
    finally:
        stomp.disconnect()


def produce(host, port, queue, num=1000):
    stomp = StompClient(host, port)
    stomp.connect()

    for i in xrange(0, num):
        print("Message #%d" % i)
        this_frame = stomp.put("Testing %d" % i,
                               destination=queue,
                               persistent=True)
        print("Receipt: %s" % this_frame.headers.get("receipt-id"))

    stomp.disconnect()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-H', '--host', action='store', default="localhost",
                      type='string', dest='host', help='hostname')
    parser.add_option('-p', '--port', action='store',
                      type='int', dest='port', help='port', default=61613)
    parser.add_option('-q', '--queue', action='store',
                      type='string', dest='queue', help='destination queue')
    parser.add_option('-P', '--produce', action='store_true',
                      default=False, dest='produce', help='produce messages')
    parser.add_option('-c', '--consume', action='store_true',
                      default=False, dest='consume', help='consume messages')
    parser.add_option('-n', '--number', action='store',
                      type='int', dest='number', default="100",
                      help='produce or consume NUMBER messages')

    options, args = parser.parse_args()

    if not options.queue:
        print("Queue name is required!")
        parser.print_help()
        sys.exit(1)

    if options.produce:
        print("PRODUCING")
        produce(options.host, options.port, options.queue, options.number)
    elif options.consume:
        consume(options.host, options.port, options.queue, options.number)
