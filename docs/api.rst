.. _api:

API
***

Clients
=======

This part of the documentation covers the primary API for interacting with Strava.

Simplex
-------

.. automodule::  stompclient.simplex
   :synopsis: A simple (publish-only) STOMP client.
   :members:
   :inherited-members:
   :show-inheritance:

Duplex
------

.. automodule::  stompclient.duplex
   :synopsis: Publish-subscribe STOMP client implementations.
   :members:
   :inherited-members:
   :show-inheritance:

Connections
===========

.. automodule:: stompclient.connection
   :synopsis: Connections and connection pools.
   :members:
   :show-inheritance:

Errors
======

The exception classes raised by the library.

.. automodule:: stompclient.exceptions
   :synopsis: The exception classes raised by the library.
   :members:
   :inherited-members:
   :show-inheritance:

Under-the-Hood
==============

Message Frames
--------------

.. automodule:: stompclient.frame
   :synopsis: Frame structures.
   :members:
   :inherited-members:
   :show-inheritance:

.. automodule:: stompclient.util
   :synopsis: Frame parsing utilities.
   :members:
   :inherited-members:
   :show-inheritance: