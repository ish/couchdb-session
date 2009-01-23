from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='couchdbx',
      version=version,
      description="Automatic, \"atomic\" updates for couchdb-python.",
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
          'couchdb-python',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
