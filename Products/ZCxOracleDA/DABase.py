# -*- coding: UTF-8 -*-

import Shared.DC.ZRDB.Connection
from Globals import HTMLFile
from ExtensionClass import Base
import Acquisition


class Connection(Shared.DC.ZRDB.Connection.Connection):
    _isAnSQLConnection = 1

    manage_options = Shared.DC.ZRDB.Connection.Connection.manage_options + (
        {'label': 'Browse', 'action': 'manage_browse'},
    )

    manage_browse = HTMLFile('browse', globals())

    info = None

    def tpValues(self):
        r = []
        try:
            c = self._v_database_connection
        except AttributeError:
            self.connect(self.connection_string)
            c = self._v_database_connection
        for d in c.tables(rdb=0):
            try:
                name = d['table_name']
                b = TableBrowser()
                b.__name__ = name
                b._d = d
                b._c = c
                b.icon = table_icons.get(d['table_type'], 'text')
                r.append(b)
            except:
                pass
        return r


class Browser(Base):
    def __getattr__(self, name):
        try:
            return self._d[name]
        except KeyError:
            raise AttributeError, name


class values:

    def len(self):
        return 1

    def __getitem__(self, i):
        try:
            return self._d[i]
        except AttributeError:
            pass
        self._d = self._f()
        return self._d[i]


class TableBrowser(Browser, Acquisition.Implicit):
    icon = 'what'
    description = check = ''
    info = HTMLFile('table_info', globals())

    def tpValues(self):
        v = values()
        v._f = self.tpValues_
        return v

    def tpValues_(self):
        r = []
        tname = self.__name__
        for d in self._c.columns(tname):
            b = ColumnBrowser()
            b._d = d
            b.icon = d['icon']
            b.table_name = tname
            r.append(b)
        return r

    def tpId(self):
        return self._d['table_name']

    def tpURL(self):
        return "Table/%s" % self._d['table_name']

    def name(self):
        return self._d['table_name']

    def type(self):
        return self._d['table_type']


class ColumnBrowser(Browser):
    icon = 'field'

    def check(self):
        return ('\t<input type=checkbox name="%s.%s">' %
                (self.table_name, self._d['name']))

    def tpId(self):
        return self._d['name']

    def tpURL(self):
        return "Column/%s" % self._d['name']

    def description(self):
        return " %s" % self._d['description']

table_icons = {
    'table': 'table',
    'view': 'view',
    'system_table': 'stable',
}
