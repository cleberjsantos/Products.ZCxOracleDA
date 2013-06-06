# -*- coding: utf-8 -*-

import cx_Oracle

import sys
from string import strip, split
import Shared.DC.ZRDB.THUNK
from config import (CX_POOL_SESSION_MIN,
                    CX_POOL_SESSION_MAX,
                    CX_POOL_SESSION_INCREMENT,
                    CX_POOL_CONNECT_TIMEOUT)


class DB(Shared.DC.ZRDB.THUNK.THUNKED_TM):

    Database_Error = cx_Oracle.DatabaseError

    def __init__(self, connection):
        info = str(connection[:int( connection.find('@'))]).split(':')
        self.tns = str(connection[int(connection.find('@')+1): ])
        if len(info) == 2:
            self.user = info[0]
            self.password = info[1]
        else:
            raise self.Database_Error, ('Invalid connection string, <code>%s</code>')

        try:
            # Let's create session pool with
            # five initial sessions (min=5),
            # limit maximum session to 10,
            # increment # of sessions by 1,
            # connectiontype = [not documented?]
            # threaded = False (by default,
            # search cx_Oracle docs for OCI_THREADED)
            # getmode = [cx_Oracle.SPOOL_ATTRVAL_NOWAIT |
            #           cx_Oracle.SPOOL_ATTRVAL_WAIT   |
            #           cx_Oracle.SPOOL_ATTRVAL_FORCEGET]
            # homogeneous = True (according to cx_Oracle
            # docs, if pool is not homogeneous then different
            # authentication can be used for each connection
            # "pulled" from the pool)
            self.pool = cx_Oracle.SessionPool(
                user=self.user,
                password=self.password,
                dsn=self.tns,
                min=CX_POOL_SESSION_MIN,
                max=CX_POOL_SESSION_MAX,
                increment=CX_POOL_SESSION_INCREMENT,
                connectiontype=cx_Oracle.Connection,
                threaded=False,
                getmode=cx_Oracle.SPOOL_ATTRVAL_NOWAIT,
                homogeneous=True)

            self.pool.timeout = CX_POOL_CONNECT_TIMEOUT
            self.con = self.pool.acquire()

        except cx_Oracle.DatabaseError, exception:
            error, = exception
            # Check if code return (ORA-12154 TNS:could not resolve the connect identifier specified)
            tns_notresolve = 12154
            if error.code == tns_notresolve:
                raise self.Database_Error, ('<code>%s</code> More details http://ora-%s.ora-code.com/') %(error.message, error.code)

        if self.con:
            try:
                # Make sure you intrument your code with clientinfo,
                # module and action attributes - this is especially
                # important if you're using SessionPool.
                # TODO. If you uncomment this line, the error occurs
                # ORA-01722: invalid number (http://ora-ora-01722.ora-code.com/)
                # self.con.clientinfo = '%s %s' % ('python', str(sys.version))
                self.con.module = 'Z CxOracleDA SessionPool'
                self.cur = self.con.cursor()
            except cx_Oracle.DatabaseError, exception:
                error, = exception
                # check if session was killed (ORA-00028)
                session_killed = 28
                if error.code == session_killed:
                    #
                    # drop session from the pool in case
                    # your session has been killed!
                    # Otherwise pool.busy and pool.opened
                    # will report wrong counters.
                    #
                    self.pool.drop(self.con)
                    raise self.Database_Error, ('Session droped from the pool... <code>%s</code> More details http://ora-%s.ora-code.com/') %(error.message, error.code)

    def str(self, v, StringType=type('')):
        if v is None: return ''
        r = str(v)
        if r[-1:]=='L' and type(v) is not StringType: r=r[:-1]
        return r

    def query(self, query_string, max_rows=99999):
        self._begin()
        c = self.cur
        queries = filter(None, map(strip, split(query_string, '\0')))
        if not queries: raise 'Query Error', 'empty query'
        desc = None
        result = []
        for qs in queries:
            c.execute(qs)
            d = c.description
            if d is None: continue
            if desc is None: desc=d
            elif d != desc:
                raise QueryError, (
                    'Multiple incompatible selects in '
                    'multiple sql-statement query'
                    )

            if max_rows:
                if not result: result=c.fetchmany(max_rows)
                elif len(result) < max_rows:
                    result=result+c.fetchmany(max_rows-len(result))
            else:
                result = c.fetchall()

        self._finish()
        if desc is None: return (), ()

        items = []
        for name, type, width, ds, p, scale, null_ok in desc:
            if type == 'NUMBER':
                if scale==0: type='i'
                else: type='n'
            elif type=='DATE':
                type='d'
            else: type='s'
            items.append({
                'name': name,
                'type': type,
                'width': width,
                'null': null_ok,
            })

        return items, result

    def _begin(self):
        pass

    def _finish(self):
        self.con.commit()

    def _abort(self):
        con.db.rollback()
