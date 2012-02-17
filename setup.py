"""
lightweight and extensible STOMP messaging client
"""
import os.path
import re
import warnings

from setuptools import setup, find_packages

__authors__ = ['"Hans Lellelid" <hans@xmpl.org>']
__copyright__ = "Copyright 2010 Hans Lellelid"

version = '0.3.2'

news = os.path.join(os.path.dirname(__file__), 'docs', 'news.txt')
news = open(news).read()
parts = re.split(r'([0-9\.]+)\s*\n\r?-+\n\r?', news)
found_news = ''
for i in range(len(parts)-1):
    if parts[i] == version:
        found_news = parts[i+i]
        break
if not found_news:
    warnings.warn('No news for this version found.')

long_description="""
stompclient provides a simple and lighweight STOMP client API for Python. 

stompclient supports both simplex (publisher-only) and duplex (publish-subscribe)
communication with STOMP servers. This project started as a fork of the `stompy
project by Benjamin W. Smith <https://bitbucket.org/asksol/python-stomp>`_) but 
has evolved into a very distinct codebase, which combines a few ideas from 
stompy with features from the Stomper library and CoilMQ broker.
"""

if found_news:
    title = 'Changes in %s' % version
    long_description += "\n%s\n%s\n" % (title, '-'*len(title))
    long_description += found_news
    
setup(name='stompclient',
      version=version,
      description=__doc__,
      long_description=long_description,
      author="Hans Lellelid",
      author_email="hans@xmpl.org",
      packages = find_packages(exclude=['tests', 'ez_setup.py', '*.tests.*', 'tests.*', '*.tests']),
      license='Apache',
      url="http://bitbucket.org/hozn/stompclient",
      keywords='stomp client',
      test_suite="nose.collector",
      tests_require=['nose>=0.11', 'mock'],
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: Apache Software License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python :: 2.6",
                   "Programming Language :: Python :: 2.7",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   ],
     )
