# -*- coding: utf-8 -*-

from DateTime import DateTime
import datetime
import sys, os
from logging import getLogger

from six.moves import _thread as thread
import cx_Oracle
from string import strip, split, find
import Shared.DC.ZRDB.THUNK
from Shared.DC.ZRDB.TM import TM

from config import (CX_POOL_SESSION_MIN,
                    CX_POOL_SESSION_MAX,
                    CX_POOL_SESSION_INCREMENT,
                    CX_POOL_CONNECT_TIMEOUT,
                    CX_POOL_THREADED,
                    CONN_TYPE,
                    CONVERSION_TIMEZONE)

logger = getLogger("Products.ZcxOracleDA.db")

#class DB(Shared.DC.ZRDB.THUNK.THUNKED_TM):
class DB(TM):

    _p_oid = _p_changed = _registered = None
    Database_Error = cx_Oracle.DatabaseError

    def _get_pool(self, *args, **kwargs):
        """ Get the connection pool or create it if it doesnt exist
            Add thread lock to prevent server initial heavy load creating multiple pools

            Let's create session pool with
            five initial sessions (min=5),
            limit maximum session to 10,
            increment # of sessions by 1,
            connectiontype = [not documented?]
            threaded = False (by default,
            search cx_Oracle docs for OCI_THREADED)
            getmode = [cx_Oracle.SPOOL_ATTRVAL_NOWAIT |
                      cx_Oracle.SPOOL_ATTRVAL_WAIT   |
                      cx_Oracle.SPOOL_ATTRVAL_FORCEGET]
            homogeneous = True (according to cx_Oracle
            docs, if pool is not homogeneous then different
            authentication can be used for each connection
            "pulled" from the pool)

            WARNING The threaded argument is expected to be
            a boolean expression which indicates whether or not
            Oracle should use the mode OCI_THREADED to wrap accesses
            to connections with a mutex. Doing so in single threaded
            applications imposes a performance penalty of about 10-15%
            which is why the default is False.
        """

        pool_name = '_pool_%s' % getattr(self, 'alias', 'common')

        if not hasattr (self.__class__, pool_name):
            lock = thread.allocate_lock()
            lock.acquire()

            try:
                pool = cx_Oracle.SessionPool(
                    user=self.user,
                    password=self.password,
                    dsn=self.tns,
                    min=CX_POOL_SESSION_MIN,
                    max=CX_POOL_SESSION_MAX,
                    increment=CX_POOL_SESSION_INCREMENT,
                    connectiontype=cx_Oracle.Connection,
                    threaded=CX_POOL_THREADED,
                    getmode=cx_Oracle.SPOOL_ATTRVAL_NOWAIT,
                    homogeneous=True)
            except Exception as err:
                pool = None

            if pool:
                pool.timeout = CX_POOL_CONNECT_TIMEOUT
                setattr(self.__class__, pool_name, pool)
            else:
               msg = """ ### Database login failed or database not found ### """
               raise self.Database_Error, ('%s') %(msg)

            lock.release()

        return getattr(self.__class__, pool_name)
   
    def pool(self):
        """
         Get a connection from the connection pool.  
         Make sure it's a valid connection (using ping()) before returning it.
        """
        connection_ok = False
        sanity_check = 0
        sanity_threshold = 10

        while connection_ok == False:
            conn = self._get_pool().acquire()

            try:
                conn.ping()
                connection_ok = True
            except cx_Oracle.DatabaseError, exception:
                error, = exception

                # Check if code return (ORA-12154 TNS:could not resolve the connect identifier specified)
                tns_notresolve = 12154

                if error.code == tns_notresolve:
                    raise self.Database_Error, ('%s More details http://ora-%s.ora-code.com/') %(error.message, error.code)
                else:
                    sanity_check += 1
                    if sanity_check > sanity_threshold:
                        raise self.Database_Error, ('Session droped from the pool... %s More details http://ora-%s.ora-code.com/') %(error.message, error.code)

                    logger.warning("Found a dead connection.  Dropping from pool.")
                    pool.drop(conn)

            conn.autocommit = 1 # This read-write attribute determines whether autocommit mode is on or off.

        return conn

    def nopool(self, *args, **kwargs):
        """ Get the connection No pool """
        nopool = None
        try:
            nopool = cx_Oracle.connect('{0}/{1}@{2}'.format(self.user, self.password, self.tns))
        except cx_Oracle.DatabaseError, exception:
            error, = exception

            # Check if code return (ORA-12154 TNS:could not resolve the connect identifier specified)
            tns_notresolve = 12154

            if error.code == tns_notresolve:
                raise self.Database_Error, ('%s More details http://ora-%s.ora-code.com/' %(error.message, error.code) )
            else:
                raise self.Database_Error, ('%s More details http://ora-%s.ora-code.com/' %(error.message, error.code) )

        return nopool

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
            raise self.Database_Error, ('Invalid connection string, %s' %( info ) )

        try:
            setattr(self, 'generic_func', getattr(self, CONN_TYPE.lower()) )
        except:
            setattr(self, 'generic_func', getattr(self, 'pool') )
        self.conn = self.generic_func()

    def _cursor(self):
        """ Get a cursor from the connection """
        cursor = self.conn.cursor()

        return cursor

    def str(self, v, StringType=type('')):
        if v is None: return ''
        r = str(v)
        if r[-1:]=='L' and type(v) is not StringType: r=r[:-1]
        return r


    def query(self, query_string, max_rows=99999, query_data=None, restarted=False):
        self._begin()
        self._register()

        cur = self._cursor()
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

            #logger.info('SQL Query: %s' % qs)

            try:
                if query_data:
                    #logger.info("Query data used: %s" % query_data)
                    rs = cur.execute(qs, query_data)
                else:
                    rs = cur.execute(qs)
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
            d = cur.description
            if d is None: continue
            if desc is None: desc=d
            elif d != desc:
                raise QueryError, (
                    'Multiple incompatible selects in '
                    'multiple sql-statement query'
                    )

            if max_rows:
                if not result: result=cur.fetchmany(max_rows)
                elif len(result) < max_rows:
                    result=result+cur.fetchmany(max_rows-len(result))
            else:
                result = cur.fetchall()

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
        self.conn.commit()

    def _abort(self, restarted=False):
        try:
            self.conn.rollback()
        except:
            pass

    def close(self):
        try:
            self.conn.close()
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
