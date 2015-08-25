# -*- coding: UTF-8 -*-

import os

# By default we create a session pool with five initial
# sessions (min=5), limit maximum session to 10, increment
# of sessions by 1, but, we can change this values setting
# with environ variable.

CX_POOL_SESSION_MIN = int(os.environ.pop('CX_POOL_SESSION_MIN', 5))
CX_POOL_SESSION_MAX = int(os.environ.pop('CX_POOL_SESSION_MAX', 10))
CX_POOL_SESSION_INCREMENT = int(os.environ.pop('CX_POOL_SESSION_INCREMENT', 1))
CX_POOL_CONNECT_TIMEOUT = int(os.environ.pop('CX_POOL_CONNECT_TIMEOUT', 50))
CONVERSION_TIMEZONE = str(os.environ.pop('COVERSION_TZ', 'UTC'))
