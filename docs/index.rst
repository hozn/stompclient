.. stompclient documentation master file, created by

Documentation
=============

**stompclient** is a python 2.6+ client for interacting with  `STOMP <http://stomp.codehaus.org/>`_ servers (aka brokers).

It supports both a "simplex" (publish-only) client, for use in situations where you just need to send messages to a server (e.g. from the context of a request in a web application) and a "duplex" (publish-subscribe) implementation that supports receiving frames from the server.

This project was motivated by the same "why-is-there-no-decent-python-solution?" sentiment of `CoilMQ <http://github.com/hozn/coilmq/>`_.  Currently this product should be considered **beta**-quality.  There's a good start to testing, but more tests need to be written.  And it is possible that the API will need to change.

Read on for getting started, jump to :ref:`usage` or browse the online version of the `API Documentation <http://packages.python.org/stompclient>`_.

Changelog
---------

High-level changes in library by version.

.. toctree::
   :maxdepth: 2

   news

Getting Started
---------------

The package is avialable on PyPI to be installed using easy_install or pip:

.. code-block:: none

   shell$ pip install stompclient


Import & start using it:

.. code-block:: python

   #!python
   from stompclient import PublishClient

   client = PublishClient('127.0.0.1', 61613)
   client.connect()
   client.send('/queue/testing', 'This is the body.')
   client.disconnect()


Usage
-----

More detailed documentation to get you started

.. toctree::
   :maxdepth: 2

   usage


API Reference
-------------

In-depth reference guide for developing software with stompclient.

.. toctree::
   :maxdepth: 2

   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
