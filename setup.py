from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='couchdb-session',
      version=version,
      description="Automatic, \"atomic\" on top for couchdb-python.",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Matt Goodall',
      author_email='matt.goodall@gmail.com',
      url='',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'couchdb',
          'PEAK-Rules',
          'ProxyTypes',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      test_suite='couchdbsession.tests',
      )
