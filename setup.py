from setuptools import setup, find_packages

setup(name='stomp',
      version='0.1',
      description='Implementation of the STOMP protocol in Python.',
      author='Benjamin W. Smith',
      author_email='benjaminwarfield@just-another.net',
      packages = ['stomp'],
      license='BSD',
      url='http://just-another.net/python-stomp',
      keywords='stomp activemq jms messaging',
      classifiers=["Development Status :: 2 - Pre-Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Topic :: Software Development :: Libraries",
                   ],
     )
