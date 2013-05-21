# -*- coding: utf-8 -*-

from Shared.DC.ZRDB.TM import TM
import cx_Oracle

import string
import sys
from string import strip, split
from time import time

failures = 0
calls = 0
last_call_time = time()


class DB(TM):

    Database_Error = cx_Oracle.DatabaseError

    def __init__(self, connection):
        info = str(connection[ : int( connection.find('@'))]).split(':')
        self.tns = str(connection[ int(connection.find('@')+1): ])
        if len(info)==2:
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
                min=5,
                max=10,
                increment=1,
                connectiontype=cx_Oracle.Connection,
                threaded=False,
                getmode=cx_Oracle.SPOOL_ATTRVAL_NOWAIT,
                homogeneous=True)

            self.pool.timeout = 50
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
                self.con.clientinfo = '%s %s' % ('python', str(sys.version))
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
            else:
                # if you're done with procession you can return session
                # back to the pool
                self.cur.close()
                self.pool.release(self.con)
                print "Session released back to the pool..."

    def str(self, v, StringType=type('')):
        if v is None: return ''
        r=str(v)
        if r[-1:]=='L' and type(v) is not StringType: r=r[:-1]
        return r

    def _finish(self, *ignored):
        self.con.commit()
        self.con.close()

    def _abort(self, *ignored):
        self.con.close()
        self.pool.release(self.con)

    def tables(self, rdb=0, _care=('TABLE', 'VIEW')):
        r=[]
        a=r.append
        for name, typ in self.db.objects():
            if typ in _care:
                a({'TABLE_NAME': name, 'TABLE_TYPE': typ})
        return r

    def columns(self, table_name):
        try:
            r=self.cur.execute('select * from %s' % table_name)
        except:
            return ()
        desc=self.cur.description
        r=[]
        a=r.append
        for name, type, width, ds, p, scale, null_ok in desc:
            if type=='NUMBER' and scale==0: type='INTEGER'
            a({ 'Name': name,
                'Type': type,
                'Precision': p,
                'Scale': scale,
                'Nullable': null_ok,
                })
        return r

    def query(self, query_string, max_rows=9999999):
        global failures, calls, last_call_time
        calls=calls+1
        desc=None
        result=()
        self._register()
        try:
            for qs in filter(None, map(strip,split(query_string, '\0'))):
                r=self.cur.execute(qs)
                if r is None:
                    if desc is not None:
                        if self.cur.description != desc:
                            raise 'Query Error', (
                                'Multiple select schema are not allowed'
                                )
                        if 'append' not in dir(result):
                            result = list(result)
                        if max_rows:
                            for row in self.cur.fetchmany(max_rows-len(result)):
                                result.append(row)
                    else:
                        desc=self.cur.description
                        if max_rows:
                            if max_rows==1:
                                result=(self.cur.fetchone(),)
                            else:
                                result=self.cur.fetchmany(max_rows)

            failures=0
            last_call_time=time()
        except self.Database_Error, mess:
            failures=failures+1
            if (failures > 1000 or time()-last_call_time > 600):
                # Hm. maybe the db is hosed.  Let's try again.
                failures=0
                last_call_time=time()
                return self.query(query_string, max_rows)
            else: raise sys.exc_type, sys.exc_value, sys.exc_traceback

        if desc is None:
            return (),()

        # Above, fetchmany returns None for empty result sets.  Maybe it
        # should return (), but it doesn't and Zope expects () so we'll fix
        # that here
        if result is None:
            result=()

        items=[]
        for name, type, length in desc:
            if type=='NUMBER':
                type='n'
            elif type=='DATE':
                type='d'
            else: type='s'
            items.append({
                'name': name,
                'type': type,})
        return items, result
