**stompclient** is a python 2.6+ client for interacting with  [STOMP](http://stomp.codehaus.org/) servers (aka brokers).

It supports both a "simplex" (publish-only) client, for use in situations where you just need to send messages to a
server (e.g. from the context of a request in a web application) and a "duplex" (publish-subscribe) implementation that
supports receiving frames from the server.

This project was motivated by the same "why-is-there-no-decent-python-solution?" sentiment of
[CoilMQ](http://github.com/hozn/coilmq/).  Currently this product should be considered **beta**-quality.  There's a
good start to testing, but more tests need to be written.  And it is possible that the API will need to change.

See the [Online Documentation](http://packages.python.org/stompclient) for more.

# Quickstart

The package is avialable on PyPI to be installed using easy_install or pip:

```
shell$ pip install stompclient
```

Import & start using it:

```python
from stompclient import PublishClient

client = PublishClient('127.0.0.1', 61613)
client.connect()
client.send('/queue/testing', 'This is the body.')
client.disconnect()
```

See https://pythonhosted.org/stompclient/ for more documentation.
