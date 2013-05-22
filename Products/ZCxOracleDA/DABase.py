# -*- coding: UTF-8 -*-

import Shared.DC.ZRDB.Connection
from logging import getLogger
from AccessControl.Permissions import open_close_database_connection
from AccessControl.SecurityInfo import ClassSecurityInfo

LOG = getLogger('ZRDB.Connection')

class Connection(Shared.DC.ZRDB.Connection.Connection):
    _isAnSQLConnection = 1
    security = ClassSecurityInfo()

    manage_options = Shared.DC.ZRDB.Connection.Connection.manage_options

    security.declareProtected(open_close_database_connection,
                              'manage_close_connection')
    def manage_close_connection(self, REQUEST=None):
        " "
        try:
            if hasattr(self,'_v_database_connection'):
		if self._v_connected == '':
        	        self._v_database_connection.con.close()
		else:
			pass
        except:
            LOG.error('Error closing relational database connection.',
                      exc_info=True)
        self._v_connected=''
        if REQUEST is not None:
            return self.manage_main(self, REQUEST)

