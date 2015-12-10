# -*- coding: UTF-8 -*-

import os

# By default we create a session pool with five initial
# sessions (min=5), limit maximum session to 10, increment
# of sessions by 1, but, we can change this values setting
# with environ variable.

CX_POOL_SESSION_MIN = int(os.environ.pop('CX_POOL_SESSION_MIN', 4))
CX_POOL_SESSION_MAX = int(os.environ.pop('CX_POOL_SESSION_MAX', 10))
CX_POOL_SESSION_INCREMENT = int(os.environ.pop('CX_POOL_SESSION_INCREMENT', 5))
CX_POOL_CONNECT_TIMEOUT = int(os.environ.pop('CX_POOL_CONNECT_TIMEOUT', 50))
CX_POOL_THREADED = bool(os.environ.pop('CX_POOL_THREADED', True))
CONVERSION_TIMEZONE = str(os.environ.pop('COVERSION_TZ', 'UTC'))
# nopool:
#      Every script has its own database server process.
#      Scripts not doing any database work still hold onto a
#      connection until the connection is closed and the server is terminated
#
# pool:
#     Database Resident Connection Pooling is a new feature of Oracle Database 11g.
#     It is useful for short lived scripts such as typically used by web applications.
#     It allows the number of connections to be scaled as web site usage grows.
#     It allows multiple Apache processes on multiple machines to share a small pool
#     of database server processes.
#     Without DRCP, a Python connection must start and terminate a server process.
CONN_TYPE = str(os.environ.pop('CONN_TYPE', 'POOL'))
