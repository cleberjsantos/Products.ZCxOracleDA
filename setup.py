# -*- coding:utf-8 -*-

from setuptools import setup, find_packages
import os

version = '1.0.dev0'
long_description = open("README.rst").read() + "\n" + \
                   open(os.path.join("docs", "INSTALL.txt")).read() + "\n" + \
                   open(os.path.join("docs", "CREDITS.txt")).read() + "\n" + \
                   open(os.path.join("docs", "HISTORY.txt")).read()

setup(name='Products.ZCxOracleDA',
      version=version,
      description="Z Cx_Oracle Database Connections for Zope2",
      long_description=long_description,
      classifiers=[
        "Environment :: Web Environment",
        "Framework :: Zope2",
        "Framework :: Plone",
        "Framework :: Plone :: 4.2",
        "Framework :: Plone :: 4.3",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Topic :: Database :: Oracle",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='plone database oracle da connection simples_consultoria',
      author='Cleber J Santos',
      author_email='cleber@simplesconsultoria.com.br',
      url='https://bitbucket.org/simplesconsultoria/products.zcxoracleda',
      license='GPLv2',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Products.ZSQLMethods',
          'cx_Oracle',
      ],
      extras_require={
        'test': ['Zope2'],
        },
      )
