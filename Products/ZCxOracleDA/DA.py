# -*- coding: UTF-8 -*-

database_type = 'CxOracle'

from App.ImageFile import ImageFile
from App.special_dtml import DTMLFile

import os
import os.path
from db import DB
from thread import allocate_lock
from Shared.DC import ZRDB
import DABase
import Shared.DC.ZRDB.Connection
import Globals

manage_addZCxOracleConnectionForm = Globals.HTMLFile('dtml/connectionAdd', globals())


def manage_addZCxOracleConnection(self, id, title,
                                  connection_string,
                                  check=None,
                                  REQUEST=None):
    """Add a DB connection to a folder"""
    self._setObject(id,
                    Connection(id, title, connection_string, check))
    if REQUEST is not None:
        return self.manage_main(self, REQUEST)

_Connection = Shared.DC.ZRDB.Connection.Connection
_connections = {}
_connections_lock = allocate_lock()


class Connection(DABase.Connection):
    """ ZCxOracle Database Adapter Connection.
    """
    database_type = database_type
    id = '%s_database_connection' % database_type
    meta_type = title = 'Z %s Database Connection' % database_type
    icon = 'misc_/Z%sDA/conn' % database_type

    _v_connected = ''

    def __init__(self, id, title, connection_string, check=None):
        self.id = str(id)
        self.edit(title, connection_string, check)

    def factory(self):
        """ Base API. Returns factory method for DB connections.
        """
        return DB

    def edit(self, title, connection_string, check=1):
        self.title = title
        self.connection_string = connection_string
        if check:
            self.connect(connection_string)

    manage_properties = Globals.HTMLFile('dtml/connectionEdit', globals())


classes = ('DA.Connection',)

meta_types = (
    {'name': 'Z %s Database Connection' % database_type,
     'action': 'manage_addZ%sConnectionForm' % database_type,
     },
)

folder_methods = {
    'manage_addZCxOracleConnection':
    manage_addZCxOracleConnection,
    'manage_addZCxOracleConnectionForm':
    manage_addZCxOracleConnectionForm,
}

__ac_permissions__ = (
    ('Add Z CxOracleDA Database Connections',
     ('manage_addZCxOracleConnectionForm',
      'manage_addZCxOracleConnection')),
)

misc_ = {'conn': ImageFile(
    os.path.join(
        os.path.dirname(ZRDB.__file__), 'www', 'DBAdapterFolder_icon.gif')
)}

for icon in ('table', 'view', 'stable', 'what',
             'field', 'text', 'bin', 'int', 'float',
             'date', 'time', 'datetime'):
    misc_[icon] = ImageFile(os.path.join('icons', '%s.gif') % icon, globals())
