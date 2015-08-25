# -*- coding: UTF-8 -*-
##############################################################################
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
__doc__="ZcxOracle Database Adaptor Registration."
__version__='$Revision: 0.6 $'[11:-2]

import os
import DA
import FSORAMethod
from Shared.DC import ZRDB
import utils

misc_ = DA.misc_


def initialize(context):

    context.registerClass(
        DA.Connection,
        permission = 'Add Cx_Oracle Database Connections',
        constructors = (DA.manage_addZCxOracleConnectionForm,
                        DA.manage_addZCxOracleConnection),
        icon = os.path.join( os.path.dirname(ZRDB.__file__), 'www', 'DBAdapterFolder_icon.gif')
    )

    utils.registerIcon(FSORAMethod.FSORAMethod,
                       'fsoramethod.gif', globals())
