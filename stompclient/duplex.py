"""
Clients that support both sending and receiving messages (produce & consume).
"""
import abc
import threading
from copy import copy
from Queue import Queue, Empty

from stompclient import frame
from stompclient.simplex import BaseClient
from stompclient.connection import ConnectionError, NotConnectedError

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2010 Hans Lellelid"
__license__ = """Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 
  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

class BaseBlockingDuplexClient(BaseClient):
    """
    Base class for STOMP client that uses listener loop to receive frames.
    """
    __metaclass__ = abc.ABCMeta
    
    debug = False
    
    def __init__(self, host, port=61613, socket_timeout=None, connection_pool=None):
        super(BaseBlockingDuplexClient, self).__init__(host, port=port, socket_timeout=socket_timeout, connection_pool=connection_pool)
        self.shutdown_event = threading.Event()
        self.listening_event = threading.Event()
        
    @abc.abstractmethod
    def dispatch_frame(self, frame):
        """
        Route the frame to the appropriate destination.
        
        @param frame: Received frame.
        @type frame: L{stompclient.frame.Frame}
        """
        
    def listen_forever(self):
        """
        Blocking method that reads from connection socket.
        
        This would typically be started within its own thread, since it will
        block until error or shutdown_event is set.
        """
        self.listening_event.set()
        self.shutdown_event.clear()
        # print "Cleared shutdown event in %s, now=%r" % (threading.current_thread().name, self.shutdown_event.is_set())
        try:
            while not self.shutdown_event.is_set():
                frame = self.connection.read()
                # print "Got frame: %r (thread: %s)" % (frame, threading.current_thread().name) # TODO: Remove this.
                if frame:
                    self.log.debug("Processing frame: %s" % frame)
                    self.dispatch_frame(frame)
        except:
            self.log.exception("Error receiving data; aborting listening loop.")
            raise
        finally:
            self.listening_event.clear()
    
    def disconnect(self, extra_headers=None):
        """
        Disconnect from the server.
        """
        try:
            # Need a copy since unsubscribe() removes the destination from the collection.
            subcpy = copy(self.subscribed_destinations)
            for destination in subcpy:
                self.unsubscribe(destination)
            disconnect = frame.DisconnectFrame(extra_headers=extra_headers)
            result = self.send_frame(disconnect)
            self.connection.disconnect()
            return result
        except NotConnectedError:
            pass
        finally:
            self.shutdown_event.set()
 
class QueueingDuplexClient(BaseBlockingDuplexClient):
    """
    A STOMP client that supports both producer and consumer roles, depositing received
    frames onto thread-safe queues.
    
    This class can be used directly; however, it requires that the calling code
    pull frames from the queues and dispatch them.  More typically, this class can
    be used as a basis for a more convenient frame-dispatching client. 
    
    Because this class must be run in a multi-threaded context (thread for listening 
    loop), it IS NOT thread-safe.  Specifically is must be used with a non-threadsafe
    connecton pool, so that the same connection can be accessed from multipl threads.

    @ivar connected_queue: A queue to hold CONNECTED frames from the server.
    @type connected_queue: C{Queue.Queue}
    
    @ivar message_queue: A queue of all the MESSAGE frames from the server to a
                            destination that has been subscribed to.
    @type message_queue: C{Queue.Queue}
    
    @ivar receipt_queue: A queue of RECEPT frames from the server (these are replies 
                            to requests that included the 'receipt' header).
    @type receipt_queue: C{Queue.Queue} 
    
    @ivar error_queue: A queue of ERROR frames from the server.
    @type error_queue: C{Queue.Queue} 
    
    @ivar subscribed_destinations: A C{dict} of subscribed destinations (only keys are used in this impl).
    @type subscribed_destinations: C{dict} of C{str} to C{bool}
    
    @ivar queue_timeout: How long should calls block on fetching frames from queue before timeout and exception?
    @type queue_timeout: C{float}  
    """
    
    def __init__(self, host, port=61613, socket_timeout=None, connection_pool=None, queue_timeout=3.0):
        super(QueueingDuplexClient, self).__init__(host, port=port, socket_timeout=socket_timeout, connection_pool=connection_pool)
        self.connected_queue = Queue()
        self.message_queue = Queue()
        self.receipt_queue = Queue()
        self.error_queue = Queue()
        self.subscribed_destinations = {}
        self.queue_timeout = queue_timeout
        if isinstance(connection_pool, threading.local):
            raise Exception("Cannot use a thread-local pool for duplex clients.")
    
    def dispatch_frame(self, frame):
        """
        Route the frame to the appropriate destination.
        
        @param frame: Received frame.
        @type frame: L{stompclient.frame.Frame}
        """
        if frame.command == 'RECEIPT':
            self.receipt_queue.put(frame)
        elif frame.command == 'MESSAGE':
            if frame.destination in self.subscribed_destinations:
                self.message_queue.put(frame)
            else:
                if self.debug:
                    self.log.debug("Ignoring frame for unsubscribed destination: %s" % frame)
        elif frame.command == 'ERROR':
            self.error_queue.put(frame)
        elif frame.command == 'CONNECTED':
            self.connected_queue.put(frame)
        else:
            self.log.info("Ignoring frame from server: %s" % frame)
    
    def connect(self, login=None, passcode=None, extra_headers=None):
        """
        Get connection and send CONNECT frame to the STOMP server. 
        
        @return: The CONNECTED frame from the server.
        @rtype: L{stompclient.frame.Frame}
        """
        connect = frame.ConnectFrame(login, passcode, extra_headers=extra_headers)
        self.send_frame(connect)
        return self.connected_queue.get(timeout=self.queue_timeout)
        
    def subscribe(self, destination, extra_headers=None):
        """
        Subscribe to a given destination.
        
        @param destination: The destination "path" to subscribe to.
        @type destination: C{str}
        """
        subscribe = frame.SubscribeFrame(destination, extra_headers=extra_headers)
        res = self.send_frame(subscribe)
        self.subscribed_destinations[destination] = True
        return res
        
    def unsubscribe(self, destination, extra_headers=None):
        """
        Unsubscribe from a given destination (or id).
        
        One of the 'destination' or 'id' parameters must be specified.
        
        @param destination: The destination to subscribe to.
        @type destination: C{str}
        
        @param id: The ID to unsubscribe from (may be used in place of destination).
        @type id: C{str}
        
        @raise ValueError: Underlying code will raise if neither destination nor id 
                            params are specified. 
        """
        unsubscribe = frame.UnsubscribeFrame(destination, extra_headers=extra_headers)
        res = self.send_frame(unsubscribe)
        self.subscribed_destinations.pop(destination)
        return res

    def send_frame(self, frame):
        """
        Send a frame to the STOMP server.
        
        This implementation does support the 'receipt' header, blocking on the
        receipt queue until a receipt frame is received.
        
        @param frame: The frame instance to send.
        @type frame: L{stomp.frame.Frame}
        
        @raise NotImplementedError: If the frame includes a 'receipt' header, since this implementation
                does not support receiving data from the STOMP broker.
        """
        need_receipt = ('receipt' in frame.headers) 
        if need_receipt and not self.listening_event.is_set():
            raise Exception("Receipt requested, but cannot deliver; listening loop is not running.")
        
        try:
            self.connection.send(frame)
        except ConnectionError:
            self.log.warning("Error sending frame, attempting to resend.", exc_info=True)
            self.connection.disconnect()
            self.connection.send(str(frame))
            
        if need_receipt:
            return self.receipt_queue.get(timeout=self.queue_timeout) 
        

class PublishSubscribeClient(QueueingDuplexClient):
    """
    A publish-subscribe client that supports providing callback functions for subscriptions.
    
    @ivar subscribed_destinations: A C{dict} of subscribed destinations to callables.
    @type subscribed_destinations: C{dict} of C{str} to C{callable} 
    """
    
    def dispatch_frame(self, frame):
        """
        Route the frame to the appropriate destination.
        
        @param frame: Received frame.
        @type frame: L{stompclient.frame.Frame}
        """
        if frame.command == 'RECEIPT':
            self.receipt_queue.put(frame)
        elif frame.command == 'MESSAGE':
            if frame.destination in self.subscribed_destinations:
                self.subscribed_destinations[frame.destination](frame)
            else:
                if self.debug:
                    self.log.debug("Ignoring frame for unsubscribed destination: %s" % frame)
        elif frame.command == 'ERROR':
            self.error_queue.put(frame)
        elif frame.command == 'CONNECTED':
            self.connected_queue.put(frame)
        else:
            self.log.info("Ignoring frame from server: %s" % frame)
    
    def subscribe(self, destination, callback, extra_headers=None):
        """
        Subscribe to a given destination with specified callback function.
        
        The callable will be passed the received L{stompclient.frame.Frame} object. 
        
        @param destination: The destination "path" to subscribe to.
        @type destination: C{str}
        
        @param callback: The callable that will be sent frames received at 
                            specified destination.
        @type callback: C{callable} 
        """
        subscribe = frame.SubscribeFrame(destination, extra_headers=extra_headers)
        res = self.send_frame(subscribe)
        self.subscribed_destinations[destination] = callback
        return res