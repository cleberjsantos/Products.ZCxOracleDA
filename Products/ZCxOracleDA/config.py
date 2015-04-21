# -*- coding: UTF-8 -*-

import os

# By default we create a session pool with five initial
# sessions (min=5), limit maximum session to 10, increment
# of sessions by 1, but, we can change this values setting
# with environ variable.

os.environ['CX_POOL_SESSION_MIN'] = '{0}'.format( int(os.environ.get('CX_POOL_SESSION_MIN', 5)) )
os.environ['CX_POOL_SESSION_MAX'] = '{0}'.format( int(os.environ.get('CX_POOL_SESSION_MAX', 10)) )
os.environ['CX_POOL_SESSION_INCREMENT'] = '{0}'.format( int(os.environ.get('CX_POOL_SESSION_INCREMENT', 1)) )
os.environ['CX_POOL_CONNECT_TIMEOUT'] = '{0}'.format( int(os.environ.get('CX_POOL_CONNECT_TIMEOUT', 50)) )

os.environ['INTANCE_HOME'] = '{0}'.format(os.environ.get('ZOPE_HOME', os.environ.get('OLDPWD', os.environ.get('INSTANCE_HOME','') ) ))
os.environ['ORACLE_HOME'] = '{0}'.format(os.environ.get('ORACLE_HOME', ''))
os.environ['TNS_ADMIN'] = '{0}/etc'.format(os.environ.get('INSTANCE_HOME',''))
os.environ['NLS_DATE_FORMAT'] = '{0}'.format(os.environ.get('NLS_DATE_FORMAT','DD/MM/YYYY')) # Default value Derived from NLS_TERRITORY
os.environ['NLS_LANG'] = '{0}'.format(os.environ.get('NLS_LANG','BRAZILIAN PORTUGUESE_BRAZIL.UTF8'))

_environ = dict(environ)
os.environ.clear()
os.environ.update(_environ)
