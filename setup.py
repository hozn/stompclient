"""
stompclient is a STOMP message client written in Python.

stompclient supports bot simplex (publisher-only) and duplex (publish-subscribe)
communication with STOMP servers. This project started as a fork of the stompy
project by Benjamin W. Smith U{https://bitbucket.org/asksol/python-stomp} but 
has evolved into a very distinct codebase, which combines a few  aspects of 
stompy with features from Stomper and CoilMQ.
"""
from setuptools import setup, find_packages

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2010 Hans Lellelid"

setup(name='stompclient',
      version="0.2.1",
      description=__doc__,
      author="Hans Lellelid",
      author_email="hans@xmpl.org",
      packages = find_packages(exclude=['tests', 'ez_setup.py', '*.tests.*', 'tests.*', '*.tests']),
      license='Apache',
      url="http://bitbucket.org/hozn/stompclient",
      keywords='stomp client',
      test_suite="nose.collector",
      setup_requires=['nose>=0.11', 'mock'],
      classifiers=["Development Status :: 2 - Pre-Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Apache Software License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 2.6",
                   "Programming Language :: Python :: 2.7",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   ],
     )
