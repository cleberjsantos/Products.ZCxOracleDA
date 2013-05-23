# -*- coding: UTF-8 -*-

import DA

misc_ = DA.misc_


def initialize(context):

    context.registerClass(
        DA.Connection,
        permission = 'Add Cx_Oracle Database Connections',
        constructors = (DA.manage_addZCxOracleConnectionForm,
                        DA.manage_addZCxOracleConnection),
    )
