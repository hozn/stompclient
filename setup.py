"""
python-stomp is a STOMP message client written in Python.

This project started as a fork of the stompy project by Benjamin W. Smith
U{https://bitbucket.org/asksol/python-stomp} but has evolved into its
own fairly distinctive codebase, which combines aspects of the original project
with features from Stomper and CoilMQ.

The goals of this project are:
  1. To provide a minimal (publisher-only) client API to stomp servers.
  2. To add features such as auto-reconnect and thread-local connection pools (inspired
  by Redis client).
  3. To provide a core set of STOMP model and utility classes (such as Frame and 
  StompBuffer) that can be reused by other projects.
"""
from setuptools import setup, find_packages

__version__ = ".".join(map(str, VERSION))
__authors__ = ['Ricky Iacovou (stomper version)', '"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2009 Benjamin W. Smith, Copyright 2010 Hans Lellelid"

setup(name='python-stomp',
      version="0.1",
      description=__doc__,
      author="Hans Lellelid",
      author_email="hans@xmpl.org",
      packages = ['stomp'],
      license='Apache',
      url="",
      keywords='stomp client',
      test_suite="nose.collector",
      setup_requires=['nose>=0.11'],
      classifiers=["Development Status :: 2 - Pre-Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Apache Software License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Topic :: Software Development :: Libraries",
                   ],
     )
