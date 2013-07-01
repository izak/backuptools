from setuptools import setup, find_packages

setup(name='backuptools',
      version='6',
      package_data = {'': ['*.xml']},
      description='Upfront Systems\' Backup tools',
      long_description='Includes python and shell scripts used for backup purposes',
      author='Izak Burger',
      author_email='izak@upfrontsystems.co.za',
      url='http://www.upfrontsystems.co.za/Members/izak',
      scripts=('ftpsync.py', 'tarbackup.py', 'decrypt.py'),
      )
