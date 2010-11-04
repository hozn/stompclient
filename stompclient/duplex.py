"""
Clients that support both sending and receiving messages (produce & consume).
"""
import abc
import threading
import warnings
from copy import copy
from Queue import Queue, Empty

from stompclient import frame
from stompclient.simplex import BaseClient
from stompclient.exceptions import NotConnectedError

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
    
    This client uses the L{listen_forever} method to receive frames from the server.  Typically,
    this would be run in its own thread::
        
        listener_thread = threading.Thread(target=client.listen_forever)
        listener_thread.start()
        client.listening_event.wait()
    
    @ivar listening_event: A threading event that will be set when the listening loop is running,
                            meaning that client is receiving frames.
    @type listening_event: C{threading.Event}
    
    @ivar shutdown_event: An event that will be set when the listening loop should terminate.  This 
                            is set internally by the L{disconnect} method.
    @type shutdown_event: C{threading.Event}
    
    @ivar subscribed_destinations: A C{dict} of subscribed destinations (only keys are required in base impl).
    @type subscribed_destinations: C{dict} of C{str} to C{bool}
    
    @ivar subscription_lock: A C{threading.RLock} used to guard access to L{subscribed_destionations} property.
    @type subscription_lock: C{threading.RLock}
    """
    __metaclass__ = abc.ABCMeta
    
    debug = False
    
    def __init__(self, host, port=61613, socket_timeout=3.0, connection_pool=None):
        super(BaseBlockingDuplexClient, self).__init__(host, port=port, socket_timeout=socket_timeout, connection_pool=connection_pool)
        self.shutdown_event = threading.Event()
        self.listening_event = threading.Event()
        self.subscription_lock = threading.RLock()
        self.subscribed_destinations = {}
        
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
        try:
            while not self.shutdown_event.is_set():
                frame = self.connection.read()
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
        Sends DISCONNECT frame and disconnect from the server.
        """
        try:
            if self.connection.connected:
                with self.subscription_lock:
                    # Need a copy since unsubscribe() removes the destination from the collection.
                    subcpy = copy(self.subscribed_destinations)
                    for destination in subcpy:
                        self.unsubscribe(destination)
                disconnect = frame.DisconnectFrame(extra_headers=extra_headers)
                result = self.send_frame(disconnect)
                try:
                    self.connection.disconnect()
                except NotConnectedError:
                    pass
                return result
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
    
    @ivar queue_timeout: How long should calls block on fetching frames from queue before timeout and exception?
    @type queue_timeout: C{float}  
    """
    
    def __init__(self, host, port=61613, socket_timeout=3.0, connection_pool=None, queue_timeout=5.0):
        super(QueueingDuplexClient, self).__init__(host, port=port, socket_timeout=socket_timeout, connection_pool=connection_pool)
        self.connected_queue = Queue()
        self.message_queue = Queue()
        self.receipt_queue = Queue()
        self.error_queue = Queue()
        
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
            with self.subscription_lock:
                if frame.destination in self.subscribed_destinations:
                    enqueue = True
                else:
                    enqueue = False
                    if self.debug:
                        self.log.debug("Ignoring frame for unsubscribed destination: %s" % frame)
            if enqueue:
                self.message_queue.put(frame)
        elif frame.command == 'ERROR':
            self.error_queue.put(frame)
        elif frame.command == 'CONNECTED':
            self.connected_queue.put(frame)
        else:
            self.log.info("Ignoring frame from server: %s" % frame)
    
    def connect(self, login=None, passcode=None, extra_headers=None):
        """
        Send CONNECT frame to the STOMP server and return CONNECTED frame (if possible). 
        
        This method will issue a warning (C{warnings.warn}) if the listener loop
        is not running.
        
        @return: The CONNECTED frame from the server.
        @rtype: L{stompclient.frame.Frame}
        """
        connect = frame.ConnectFrame(login, passcode, extra_headers=extra_headers)
        self.send_frame(connect)
        if not self.listening_event.is_set():
            self.log.warning("Cannot deliver connection response; listening loop is not running.")
            warnings.warn("Cannot deliver connection response; listening loop is not running.")
        else:
            try:
                return self.connected_queue.get(timeout=self.queue_timeout)
            except Empty:
                raise Exception("Expected CONNECTED frame, but none received.")
        
    def subscribe(self, destination, ack=None, extra_headers=None):
        """
        Subscribe to a given destination.
        
        @param destination: The destination "path" to subscribe to.
        @type destination: C{str}
        
        @param ack: If set to 'client' will require clients to explicitly L{ack} any 
                    frames received (in order for server to consider them delivered).
        @type ack: C{str}
        """
        subscribe = frame.SubscribeFrame(destination, ack=ack, extra_headers=extra_headers)
        res = self.send_frame(subscribe)
        with self.subscription_lock:
            self.subscribed_destinations[destination] = True
        return res
        
    def unsubscribe(self, destination, extra_headers=None):
        """
        Unsubscribe from a given destination (or id).
        
        One of the 'destination' or 'id' parameters must be specified.
        
        @param destination: The destination to subscribe to.
        @type destination: C{str}
        
        @raise ValueError: Underlying code will raise if neither destination nor id 
                            params are specified. 
        """
        unsubscribe = frame.UnsubscribeFrame(destination, extra_headers=extra_headers)
        res = self.send_frame(unsubscribe)
        with self.subscription_lock:
            self.subscribed_destinations.pop(destination)
        return res

    def send_frame(self, frame):
        """
        Send a frame to the STOMP server.
        
        This implementation *does* support the 'receipt' header, blocking on the
        receipt queue until a receipt frame is received.
        
        This implementation does NOT attempt to disconnect/reconnect if connection error
        received, because disconnecting the socket royally pisses off the listen_forever blocking
        loop.
        
        @param frame: The frame instance to send.
        @type frame: L{stomp.frame.Frame}
        
        @raise NotImplementedError: If the frame includes a 'receipt' header, since this implementation
                does not support receiving data from the STOMP broker.
        """
        need_receipt = ('receipt' in frame.headers) 
        if need_receipt and not self.listening_event.is_set():
            raise Exception("Receipt requested, but cannot deliver; listening loop is not running.")
        
        self.connection.send(frame)
        
        if need_receipt:
            try:
                return self.receipt_queue.get(timeout=self.queue_timeout)
            except Empty:
                raise Exception("Expected RECEIPT response frame, but none received.")
        

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
            with self.subscription_lock:
                if frame.destination in self.subscribed_destinations:
                    handler = self.subscribed_destinations[frame.destination]
                else:
                    handler = lambda f: None
                    if self.debug:
                        self.log.debug("Ignoring frame for unsubscribed destination: %s" % frame)
            handler(frame)
        elif frame.command == 'ERROR':
            self.error_queue.put(frame)
        elif frame.command == 'CONNECTED':
            self.connected_queue.put(frame)
        else:
            self.log.info("Ignoring frame from server: %s" % frame)
    
    def subscribe(self, destination, callback, ack=None, extra_headers=None):
        """
        Subscribe to a given destination with specified callback function.
        
        The callable will be passed the received L{stompclient.frame.Frame} object. 
        
        @param destination: The destination "path" to subscribe to.
        @type destination: C{str}
        
        @param callback: The callable that will be sent frames received at 
                            specified destination.
        @type callback: C{callable} 
        
        @param ack: If set to 'client' will require clients to explicitly L{ack} any 
                    frames received (in order for server to consider them delivered).
        @type ack: C{str} 
        """
        subscribe = frame.SubscribeFrame(destination, ack=ack, extra_headers=extra_headers)
        res = self.send_frame(subscribe)
        with self.subscription_lock:
            self.subscribed_destinations[destination] = callback
        return res