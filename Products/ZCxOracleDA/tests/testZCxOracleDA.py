# -*- coding: UTF-8 -*-

###########################################################################
# ZCxOracleDA tests
###########################################################################

"""
Tests for ZCxOracleDA
"""

import sys
import os
import unittest
from Testing import ZopeTestCase

import transaction
from Products.ZSQLMethods.SQL import manage_addZSQLMethod

try:
    from Products.ZCxOracleDA.DA import Connection
except ImportError:
    print >>sys.stderr, 'Failed to import ZCxOracleDA'
else:
    ZopeTestCase.installProduct('ZCxOracleDA', 1)


class TestBase(ZopeTestCase.ZopeTestCase):

    def createDA(self, **kw):
        factory = self.app.manage_addProduct['ZCxOracleDA']
        factory.manage_addZCxOracleConnection('da', 'MyDATest',
                                              self.connection_string,
                                              **kw)
        return self.app['da']


class ZCxOracleDATests(TestBase):

    def afterSetUp(self):
        self.connection_string = 'testuser:testpass@testtns'

    def testConnectionString(self):
        da = self.createDA()
        info = str(self.connection_string[:int( self.connection_string.find('@'))]).split(':')
        tns = str(self.connection_string[int(self.connection_string.find('@')+1): ])

        self.assertEqual(len(info), 2)
        self.assertEqual(info[0], 'testuser')
        self.assertEqual(info[1], 'testpass')
        self.assertEqual(tns, 'testtns')

    def testSimpleSelect(self):
        da = self.createDA()
        rows = da.query('select sysdate from dual')
        self.assertEqual(len(rows), 1)


class ZCxOracleDAFunctionalTests(TestBase, ZopeTestCase.FunctionalTestCase):

    def afterSetUp(self):
        self.folder_path = '/' + self.folder.absolute_url(1)

    def testZsqlSelect(self):
        da = self.createDA()
        template = "SELECT SYSDATE FROM DUAL"
        manage_addZSQLMethod(self.app, 'zsql_id', 'title', 'da', '', template)
        self.app['zsql_id']()
        self.publish(self.folder_path)
        # Go on


def test_suite():
    s = unittest.TestSuite()
    s.addTests([unittest.makeSuite(ZCxOracleDATests),
               unittest.makeSuite(ZCxOracleDAFunctionalTests)])
    return s


def main():
    unittest.TextTestRunner().run(test_suite())


def debug():
    test_suite().debug()


def pdebug():
    import pdb
    pdb.run('debug()')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        globals()[sys.argv[1]]()
    else:
        main()
