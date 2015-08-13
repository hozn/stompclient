Installation
************

The simplest option is to install **stompclient** using `pip` (or `easy_install` if you have been living under a rock).
This will grab the latest published release PyPI.

.. code-block:: none

   shell$ pip install stompclient


If this is not an option, you can also [[http://bitbucket.org/hozn/stompclient/hozn/downloads|download]] a package and install it the old-fashioned way.

.. code-block:: none

   shell$ tar zxvf stompclient-0.1.tar.gz
   shell$ cd stompclient-0.1
   shell$ python setup.py install


Choosing a Client
*****************

**stompclient** ships with a couple basic client implementations:

1. A :class:`stompclient.simplex.PublishClient` that provides a one-way (client -> server) communication path.
2. A :class:`stompclient.duplex.PublishSubscribeClient` that provides two-way (client <-> server) communication.

Publish-Only Client
===================

The simplest client is the :class:`stompclient.simplex.PublishClient` (also importable directly from top-level :mod:`stompclient` package).  The "simplex" clients support only one-way communication, which means you do not get any server responses.

Notably, the `PublishClient`:
1. does not support the 'receipt' header (you'll get an exception if you specify it),
2. does not return the 'session-id' response in CONNECTED frame (which isn't actually used by the protocol anyway),
3. and won't handle/return server errors.

A simplex client may make perfect sense in a fire-and-forget context, such as sending messages to a queue or topic from
your python web application.  The single-threaded nature of the :class:`PublishClient <stompclient.simplex.PublishClient>`
makes it easy to manage -- and makes it possible to use a
:class:`ThreadLocalConnectionPool <stompclient.connection.ThreadLocalConnectionPool>` (the default for this client
implementation) which may cut down on connection creation for high-traffic applications.

Also, the :class:`PublishClient <stompclient.simplex.PublishClient>` will attempt to reconnect if a connection is
disconnected (which does not work for connections that must be shared with a listener-loop thread).

Publish-Subscribe
=================

It's important to note that unlike protocols like HTTP, the STOMP protocol is not a sequential request-response
protocol.  As a consequence, unlike HTTP clients, STOMP clients that want to receive "responses" must be able to receive
messages from the server at any point and must support the fact that server-initiated messages will include some
"response" messages (e.g. ACK) interleaved with other messages (topic notifications, new queue messages, etc.).
Hopefully this will provide some context for why "duplex" STOMP clients are necessarily more complex to work with than
the publish-only variety mentioned above.

**stompclient** offers a couple publish-subscribe implementations; however, all of them rely on a blocking listener
loop, and as such need to be run using threads.  In short, you need to start a listener loop before you connect to the
server.

The default :class:`stompclient.duplex.PublishSubscribeClient` (also importable from top-level :mod:`stompclient`
package) uses queues (`Queue.Queue`) under the hood to hold received frames, routing messages (MESSAGE frame) to a
*callable* configured in subscription request.

This is probably best illustrated with an example:

.. code-block:: python

    #!python
    import threading
    import logging
    import time

    logging.basicConfig(level=logging.DEBUG)

    from stompclient import PublishSubscribeClient

    def frame_received(frame):
        # Do something with the frame!
        print "----Received Frame----\n%s\n-----" % frame

    client = PublishSubscribeClient('127.0.0.1', 61613)
    listener = threading.Thread(target=client.listen_forever)
    listener.start()

    # For our example, we want to wait until the server is actually listening
    client.listening_event.wait()

    client.connect()
    client.subscribe("/queue/testing", frame_received)
    client.send("/queue/testing", "This is the body of the frame.")
    client.send("/queue/testing", '{"key": "Another frame example."}')

    time.sleep(5) # Inject some sleep so the frames all get picked up before we fire a disconnect message.

    client.disconnect()

General Usage
*************

Connecting to a Server
======================

The STOMP client will attempt to open the socket connection to the server implicitly with any request.  Additionally, it will attempt to reconnect & re-send frame if the socket is disconnected (and raises an appropriate error).

The :meth:`connect() <stompclient.simplex.BaseClient.connect>` method is used to actually send a "CONNECT" frame to the server, which allows the server to deliver frames from/to the client.

The server may also be configured to require authentication.

.. code-block:: python

    client = PublishClient('127.0.0.1', 61613)
    client.connect('user', 'passcode')

In the case of the :class:`PublishSubscribeClient <stompclient.duplex.PublishSubscribeClient>`, you will get a CONNECTED frame back *if the listening loop is running* (otherwise a warning will be issued and `None` will be returned).

.. code-block:: python

    client = PublishSubscribeClient('127.0.0.1', 61613)

    # The listening loop must be started (i.e. in a thread)
    # and client.listening_event.wait() to ensure that it is running
    # before connecting, in order to get the response frame.

    response = client.connect()
    print response.session_id  # session-id is an unused feature of the stomp protocol


Disconnecting
=============

When you want to close down a client connection, you should explicitly call the :meth:`disconnect() <stompclient.simplex.BaseClient.disconnect>` method.  This will send a DISCONNECT frame to the server (so the server knows this client is not available for receiving messages) and close the underlying connection.

.. code-block:: python

    client.connect()
    try:
      # Do stuff
    finally:
      client.disconnect()

Connection Pools
----------------

The STOMP client classes do not keep references to a connection, but instead maintain a reference to a connection pool and request a connection from the pool for each request.

The default connection pool depends on the client being used.

* :class:`PublishClient <stompclient.simplex.PublishClient>` uses a :class:`ThreadLocalConnectionPool <stompclient.connection.ThreadLocalConnectionPool>` by default, which ensures that connections are unique to a thread.
* :class:`PublishSubscribeClient <stompclient.duplex.PublishSubscribeClient>` uses the base :class:`stompclient.connection.ConnectionPool` which does not provide any protection from sharing connections between threads, because the *listener thread must be able to use the same connection socket as the publisher thread (e.g. the main thread)*.

If you would like to exercise more control over the management  You can pass in your own connection pool object.

.. code-block:: python

    pool = ConnectionPool()
    client = PublishClient('127.0.0.1', 61613, pool=pool)

Or implement your own:

.. code-block:: python

    class NoReuseConnectionPool(ConnectionPool):
      """ A connection pool that returns a new connection every time one is requested. """
      def get_connection(self, host, port, socket_timeout):
        """ Returns a new connection for every reqeust. """
        return Connection(host, port, socket_timeout=socket_timeout)

      def get_all_connections():
        raise NotImplementedError()


Timeouts
--------

When creating a STOMP client, you can specify the timeout for the underlying socket.  For the :class:`PublishSubscribeClient <stompclient.duplex.PublishSubscribeClient>` you can also specify the timeout for the blocking queues.

By default the socket_timeout is set to small value (3 seconds), due to expectations that the client is used in a responsive network environment.  Be careful when in creasing the timeout, as the listener loop will only pickup shutdown signals after the socket times out (or the socket reads a full buffer of bytes).

The value is specified as a float and a value of `None` will cause the socket to block indefinitely.

.. code-block:: python

    client = PublishClient('127.0.0.1', 61613, socket_timeout=0.5)

For the :class:`PublishSubscribeClient <stompclient.duplex.PublishSubscribeClient>` you can also change the timeout for the blocking queues (which are filled by frames received on the listener loop).  It is recommended that you keep these non-infinite (`None`), since this could result in hanging your application.

.. code-block:: python

    client = PublishSubscribeClient('127.0.0.1', 61613, socket_timeout=0.5, queue_timeout=0.5)

Sending Messages
================

Sending is pretty straightforward.  You just need to know the destination "path" (usually starting with "/queue/" or "/topic"; how this is interpreted/handled is up to the server).

.. code-block:: python

    client = PublishClient('127.0.0.1', 61613)
    client.send("/queue/a-test-queue", "This is the message.")

The body of the message should be a `bytes`-type object (i.e. not a unicode string).

If your server supports custom headers, you can specify them in the :meth:`send() <stompclient.simplex.BaseClient.send>` command -- or any command -- using the `extra_headers` parameter:

.. code-block:: python

    client.send("/queue/a-test-queue", "The body of the message.",
                extra_headers={'x.custom.header': 'header-value'})


Receiving Messages (Subscribing)
================================

Subscribing to topics or queues ("destinations") is only available with one of the duplex clients.  The default duplex
client is the :class:`PublishSubscribeClient <stompclient.duplex.PublishSubscribeClient>`, which internally uses queues
but passes all received frames to a callable that you specify when you subscribe.

*Remember, you first need to make sure that you have a listener loop running before you subscribe your client to a destination.*

Example of starting the listening loop:

.. code-block:: python

    client = PublishSubscribeClient('127.0.0.1', 61613)
    client.connect()
    listener = threading.Thread(target=client.listen_forever)
    listener.start()
    client.listening_event.wait() # Wait 'till the thread is actually listening before proceeding ...


Subscribing to a destination:

.. code-block:: python

    def message_received(frame):
      """ Do something with a frame we received.
      @param frame: The C{stompclient.frame.Frame} object holding the MESSAGE frame.
      """
      pass
    # Assumes listener loop is running:
    client.subscribe("/queue/testing", frame_received)

Any received MESSAGE frames will be sent to the `message_received` function.  Note that with this implementation, your listener thread will block until the `message_received` function returns.

If you need a higher-performance system for processing threads (e.g. delivering messages to a pool of workers), you will probably want to use the :class:`QueueingDuplexClient <stompclient.duplex.QueueingDuplexClient>` implementation which writes all frames to internal queues.  (And you could have consumer threads reading from `client.message_queue`.)

Reliability/Throttling
----------------------

When a client is subscribed to a destination, an `ack` parameter can be specified.  By default the server assumes 'auto';
however if this is set to "cient", then the client must explicitly send an ACK for any received MESSAGE frames before
the server will send any additional MESSAGE frames.

.. code-block:: python

    def message_received(frame):
      """ Do something with a frame we received.
      @param frame: The C{stompclient.frame.Frame} object holding the MESSAGE frame.
      """
      # Do something.
      client.ack(frame.message_id)

    # Assumes listener loop is running:
    client.subscribe("/queue/testing", frame_received, ack='client')


Transactions
============

STOMP provides basic support for sending multiple messages in a single transaction.

Transactions are managed using :meth:`begin <stompclient.simplex.BaseClient.begin>`,
:meth:`commit <stompclient.simplex.BaseClient.commit>`, and :meth:`abort <stompclient.simplex.BaseClient.abort>` methods
with an arbitrary transaction identifier. Currently the STOMP client implementations do not transparently manage the
transaction identifiers; you have to do that in the calling code.

Non-transaction-management methods that support the `transaction` identifer:

1. :meth:`send <stompclient.simplex.BaseClient.send>`
2. :meth:`ack <stompclient.simplex.BaseClient.ack>`

.. code-block:: python

    import uuid

    # ....

    txid = uuid.uuid4()  # could be any value unique to this client connection

    client.begin(txid)
    try:
      client.send("/queue/dest", "Message 1", transaction=txid)
      client.send("/queue/dest", "Message 2", transaction=txid)
      client.send("/queue/dest", "Message 3", transaction=txid)
      client.commit(txid)
    except:
      client.abort(txid)
      raise


Note that it is possible to interleave transactions or send out-of-transaction frames (which would be sent immediately).

.. code-block:: python

    tx1 = uuid.uuid4()  # could be any value unique to this client connection
    tx2 = uuid.uuid4()

    client.begin(tx1)
    client.begin(tx2)
    try:
      client.send("/queue/dest", "Message 1.0", transaction=tx1)
      client.send("/queue/dest", "Message 2.0", transaction=tx2)
      client.send("/queue/dest", "Message 1.1", transaction=tx1)
      client.send("/queue/dest", "Message 2.1", transaction=tx2)
      client.send("/queue/dest", "not in transaction - sent immediately")
      client.commit(tx1)
      client.commit(tx2)
    except:
      client.abort(tx1)
      client.abort(tx2)
      raise


The example above is very contrived (the two transactions operate essentially the same as a single transaction), but hopefully illustrates the point.
