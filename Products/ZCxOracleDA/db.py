# -*- coding: utf-8 -*-

from DateTime import DateTime
import datetime
import sys, os
from logging import getLogger

import cx_Oracle
from string import strip, split, find
import Shared.DC.ZRDB.THUNK
from Shared.DC.ZRDB.TM import TM

from config import (CX_POOL_SESSION_MIN,
                    CX_POOL_SESSION_MAX,
                    CX_POOL_SESSION_INCREMENT,
                    CX_POOL_CONNECT_TIMEOUT,
                    CONVERSION_TIMEZONE)

logger = getLogger("Products.ZcxOracleDA.db")

#class DB(Shared.DC.ZRDB.THUNK.THUNKED_TM):
class DB(TM):

    _p_oid = _p_changed = _registered = None
    Database_Error = cx_Oracle.DatabaseError

    def __init__(self, connection):
        info = str(connection[:int( connection.find('@'))]).split(':')
        self.tns = str(connection[int(connection.find('@')+1): ])
        os.environ['ORACLE_HOME'] = '{0}'.format(os.environ.get('ORACLE_HOME', ''))
        os.environ['TNS_ADMIN'] = '{0}/etc'.format(os.environ.get('ZOPE', os.environ.get('ZOPE_HOME', os.environ.get('OLDPWD', os.environ.get('INSTANCE_HOME','') ) )))
        os.environ['NLS_DATE_FORMAT'] = '{0}'.format(os.environ.get('NLS_DATE_FORMAT','DD/MM/YYYY')) # Default value Derived from NLS_TERRITORY
        os.environ['NLS_LANG'] = '{0}'.format(os.environ.get('NLS_LANG','BRAZILIAN PORTUGUESE_BRAZIL.UTF8'))
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

            # WARNING The threaded argument is expected to be
            # a boolean expression which indicates whether or not
            # Oracle should use the mode OCI_THREADED to wrap accesses
            # to connections with a mutex. Doing so in single threaded
            # applications imposes a performance penalty of about 10-15%
            #  which is why the default is False.

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
            self.con.autocommit = 1 # This read-write attribute determines whether autocommit mode is on or off.

        except cx_Oracle.DatabaseError, exception:
            error, = exception
            # Check if code return (ORA-12154 TNS:could not resolve the connect identifier specified)
            tns_notresolve = 12154
            if error.code == tns_notresolve:
                raise self.Database_Error, ('<code>%s</code> More details http://ora-%s.ora-code.com/') %(error.message, error.code)

        try:
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
                    self.Database_Connection = self.cur
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

        except:
            print 'Database Down'
            raise

    def str(self, v, StringType=type('')):
        if v is None: return ''
        r = str(v)
        if r[-1:]=='L' and type(v) is not StringType: r=r[:-1]
        return r


    def query(self, query_string, max_rows=99999, query_data=None, restarted=False):
        self._begin()
        self._register()

        c = self.cur
        queries = filter(None, map(strip, split(query_string, '\0')))
        if not queries: raise 'Query Error', 'empty query'
        desc = None
        result = []
        for qs in queries:
            # !!!! Fix bad windows return carriage for zsql containing called to procedures (BEGIN....END;)
            # Oracle can't compile such a query if it contains CRLF, so replace them by LF
            # Oracle error example :
            #   [...]
            #     Module Shared.DC.ZRDB.DA, line 500, in __call__
            #      - <FSZSQLMethod at /sesame/zsql_method>
            #     Module Products.ZcxOracleDA.db, line 96, in query
            #   DatabaseError: ORA-06550: line 1, column 7:
            #   PLS-00103: Encountered the symbol "" when expecting one of the following:
            # !!!! /Fix bad windows return carriage
            qs = qs.replace("\r\n", "\n")

            logger.info('SQL Query: %s' % qs)

            try:
                if query_data:
                    logger.info("Query data used: %s" % query_data)
                    rs = c.execute(qs, query_data)
                else:
                    rs = c.execute(qs)
            except Exception, e:
                error_msg = '%s' % e
                logger.warning("Error while executing query: %s for query\n%s" % (error_msg, qs))
                # If not connected to Oracle
                if not restarted and (error_msg.find('ORA-03114') != -1 or error_msg.find('ORA-03113') != -1 or error_msg.find('Invalid handle') != -1):
                    # Go back up the chain so that everybody agrees that we are
                    # reconnected.
                    logger.error("Database connection is stale. Reason: %s - Attempting to re-open." % error_msg)

                    # Make sure we don't have more than one level of recursion.
                    # The database may actually be down, not just stale.
                    return self.query(query_string, max_rows, query_data, True) 
                else:
                    logger.error("Failed to reopen stale database connection.")
                    raise e

            if not rs: continue
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

        #self._finish()
        if desc is None: return (), ()

        items = []
        has_datetime = False
        for name, type, width, ds, p, scale, null_ok in desc:
            if type == 'NUMBER' or type == cx_Oracle.NUMBER:
                if scale==0: type='i'
                else: type='n'
            elif type=='DATE' or type == datetime.datetime:
                has_datetime = True
                type='d'
            else: type='s'
            items.append({
                'name': name,
                'type': type,
                'width': width,
                'null': null_ok,
            })

        if has_datetime:
            result = self._munge_datetime_results(items, result)
        return items, result

    def _begin(self):
        pass

    def _finish(self):
        self.con.commit()

    def _abort(self, restarted=False):
        try:
            self.con.rollback()
        except:
            pass

    def close(self):
        try:
            self.con.close()
        except:
            pass


    def _datetime_convert(self, dt, val):
        if dt and val:
            # Currently we don't do timezones. Everything is UTC.
            # Ideally we'd get the current Oracle timezone and use that.
            x = val.timetuple()[:6] + (CONVERSION_TIMEZONE,)
            return DateTime(*x) 
        return val

    def _munge_datetime_results(self, items, results):
        if not results or not items:
            return results
        dtmap = [i['type'] == 'd' for i in items]
        nr = []
        for row in results:
            r = tuple([self._datetime_convert(*r) for r in zip(dtmap, row)])
            nr.append(r)
        return nr
