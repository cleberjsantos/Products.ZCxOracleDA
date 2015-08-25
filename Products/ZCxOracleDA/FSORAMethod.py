##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Customizable ZSQL methods that come from the filesystem. 
    Modified from CMFCore/FSZSQLMethod.py for Oracle database

$Id: FSZSQLMethod.py $
Original: https://github.com/MordicusEtCubitus/ZcxOracleDA/blob/master/FSORAMethod.py 
"""

import logging
from time import time

import Globals
from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from AccessControl.Permissions import use_database_methods
from AccessControl.DTML import RestrictedDTML

from Acquisition import ImplicitAcquisitionWrapper

from Products.ZSQLMethods.SQL import SQL
from Products.CMFCore.DirectoryView import registerFileExtension
from Products.CMFCore.DirectoryView import registerMetaType
from Products.CMFCore.FSObject import FSObject
from Products.CMFCore.permissions import View
from Products.CMFCore.permissions import ViewManagementScreens
from Products.CMFCore.utils import _dtmldir
from Shared.DC.ZRDB.DA import SQLMethodTracebackSupplement
from Shared.DC.ZRDB.Results import Results
from Shared.DC.ZRDB.sqlgroup import SQLGroup
import DocumentTemplate
import ExtensionClass

from App.class_init import InitializeClass
from App.special_dtml import DTMLFile

from dtmlsql import SQLVar, SQLTest

logger = logging.getLogger('ZcxOracleDA.FSORAMethod')

class nvSQL(DocumentTemplate.HTML):
    # Non-validating SQL Template for use by SQLFiles.
    commands={}
    for k, v in DocumentTemplate.HTML.commands.items(): commands[k]=v
    commands['sqlvar' ]=SQLVar
    commands['sqltest']=SQLTest
    commands['sqlgroup' ]=SQLGroup

    _proxy_roles=()


class zoraSQL(RestrictedDTML, ExtensionClass.Base, nvSQL):
    # Validating SQL template for Zope SQL Methods.
    pass



class FSORAMethod(SQL, FSObject):

    """FSORAMethods act like Z SQL Methods but are not directly
    modifiable from the management interface."""

    meta_type = 'Filesystem ORA Method'

    manage_options = ({'label':'Customize', 'action':'manage_customise'},
                      {'label':'Test', 'action':'manage_testForm',
                       'help':('ORAMethods','Z-SQL-Oracle-Method_Test.stx')},
                     )

    security = ClassSecurityInfo()
    security.declareObjectProtected(View)

    # Make mutators private
    security.declarePrivate('manage_main')
    security.declarePrivate('manage_edit')
    security.declarePrivate('manage_advanced')
    security.declarePrivate('manage_advancedForm')
    manage=None

    security.declareProtected(ViewManagementScreens, 'manage_customise')
    manage_customise = DTMLFile('custzsql', _dtmldir)
    
    template_class=zoraSQL

    def __init__(self, id, filepath, fullname=None, properties=None):
        FSObject.__init__(self, id, filepath, fullname, properties)

    def _createZODBClone(self):
        """Create a ZODB (editable) equivalent of this object."""
        # I guess it's bad to 'reach inside' ourselves like this,
        # but Z SQL Methods don't have accessor methdods ;-)
        s = SQL(self.id,
                self.title,
                self.connection_id,
                self.arguments_src,
                self.src)
        s.manage_advanced(self.max_rows_,
                          self.max_cache_,
                          self.cache_time_,
                          self.class_name_,
                          self.class_file_,
                          connection_hook=self.connection_hook,
                          direct=self.allow_simple_one_argument_traversal)
        return s

    def _readFile(self, reparse):
        """Read the data from the filesystem.
        """
        #logger.info('Reading ZORA Method: %s' % self._filepath)
        file = open(self._filepath, 'r') # not 'rb', as this is a text file!
        try:
            data = file.read()
        finally:
            file.close()

        # parse parameters
        parameters={}
        start = data.find('<dtml-comment>')
        end   = data.find('</dtml-comment>')
        if start==-1 or end==-1 or start>end:
            raise ValueError,'Could not find parameter block'
        block = data[start+14:end]

        for line in block.split('\n'):
            pair = line.split(':',1)
            if len(pair)!=2:
                continue
            parameters[pair[0].strip().lower()]=pair[1].strip()

        # check for required parameters
        try:
            connection_id =   ( parameters.get('connection id', '') or
                                parameters['connection_id'] )
        except KeyError,e:
            raise ValueError("The '%s' parameter is required "
                             "but was not supplied" % e)

        # Optional parameters
        title =           parameters.get('title','')
        arguments =       parameters.get('arguments','')
        max_rows =        parameters.get('max_rows',1000)
        max_cache =       parameters.get('max_cache',100)
        cache_time =      parameters.get('cache_time',0)
        class_name =      parameters.get('class_name','')
        class_file =      parameters.get('class_file','')
        connection_hook = parameters.get('connection_hook',None)
        direct = parameters.get('allow_simple_one_argument_traversal', None)

        self.manage_edit(title, connection_id, arguments, template=data)

        self.manage_advanced(max_rows,
                             max_cache,
                             cache_time,
                             class_name,
                             class_file,
                             connection_hook=connection_hook,
                             direct=direct)

    def _cached_result(self, DB__, query, max_rows, conn_id, query_data):
        # Try to fetch a result from the cache.
        # Compute and cache the result otherwise.
        # Also maintains the cache and ensures stale entries
        # are never returned and that the cache never gets too large.

        # NB: Correct cache behavior is predicated on Bucket.keys()
        #     returning a sequence ordered from smalled number
        #     (ie: the oldest cache entry) to largest number
        #     (ie: the newest cache entry). Please be careful if you
        #     change the class instantied below!

        # get hold of a cache
        caches = getattr(self,'_v_cache',None)
        if caches is None:
            caches = self._v_cache = {}, Bucket()
        cache, tcache = caches

        # the key for caching
        query_data_key = ''
        for key in query_data:
            query_data_key = '%s_%s=%s' % (query_data,key,query_data[key])
            
        cache_key = query,max_rows,conn_id,query_data_key
        # the maximum number of result sets to cache
        max_cache=self.max_cache_
        # the current time
        now=time()
        # the oldest time which is not stale
        t=now-self.cache_time_
        
        # if the cache is too big, we purge entries from it
        if len(cache) >= max_cache:
            keys=tcache.keys()
            # We also hoover out any stale entries, as we're
            # already doing cache minimisation.
            # 'keys' is ordered, so we purge the oldest results
            # until the cache is small enough and there are no
            # stale entries in it
            while keys and (len(keys) >= max_cache or keys[0] < t):
                key=keys[0]
                q=tcache[key]
                try:
                    del tcache[key]
                    del cache[q]
                    del keys[0]
                except KeyError, err:
                    log.warn('Cannot delete key cache, it may already have been deleted by another thread: %s' % err)

        # okay, now see if we have a cached result
        if cache.has_key(cache_key):
            k, r = cache[cache_key]
            # the result may still be stale, as we only hoover out
            # stale results above if the cache gets too large.
            if k > t:
                # yay! a cached result returned!
                return r
            else:
                # delete stale cache entries
                del cache[cache_key]
                try:
                    del tcache[k]
                except KeyError, err:
                    log.warn('Cannot delete key cache, it may already have been deleted by another thread: %s' % err)

        # call the pure query
        result=DB__.query(query,max_rows, query_data)

        # When a ZSQL method is handled by one ZPublisher thread twice in
        # less time than it takes for time.time() to return a different
        # value, the SQL generated is different, then this code will leak
        # an entry in 'cache' for each time the ZSQL method generates
        # different SQL until time.time() returns a different value.
        #
        # On Linux, you would need an extremely fast machine under extremely
        # high load, making this extremely unlikely. On Windows, this is a
        # little more likely, but still unlikely to be a problem.
        #
        # If it does become a problem, the values of the tcache mapping
        # need to be turned into sets of cache keys rather than a single
        # cache key.
        tcache[now]=cache_key
        cache[cache_key]= now, result

        return result


        # do we need to do anything on reparse?
    security.declareProtected(use_database_methods, '__call__')
    def __call__(self, REQUEST=None, __ick__=None, src__=0, test__=0, **kw):
        """Call the database method

        The arguments to the method should be passed via keyword
        arguments, or in a single mapping object. If no arguments are
        given, and if the method was invoked through the Web, then the
        method will try to acquire and use the Web REQUEST object as
        the argument mapping.

        The returned value is a sequence of record objects.
        """

        __traceback_supplement__ = (SQLMethodTracebackSupplement, self)

        #logger.info('REQUEST is %s' % REQUEST)
        #logger.info('kw is %s' % kw)
        #if hasattr(self, 'REQUEST'):
        #    logger.info('self.REQUEST.form is %s' % self.REQUEST.form)
        

        if REQUEST is None:
            if kw: REQUEST=kw
            else:
                if hasattr(self, 'REQUEST'): REQUEST=self.REQUEST
                else: REQUEST={}

        # connection hook
        c = self.connection_id
        # for backwards compatability
        hk = self.connection_hook
        # go get the connection hook and call it
        if hk: c = getattr(self, hk)()
           
        try: dbc=getattr(self, c)
        except AttributeError:
            raise AttributeError, (
                "The database connection <em>%s</em> cannot be found." % (
                c))

        try: DB__=dbc()
        except: raise Exception, (
            '%s is not connected to a database' % self.id)

        if hasattr(self, 'aq_parent'):
            p=self.aq_parent
            if self._isBeingAccessedAsZClassDefinedInstanceMethod():
                p=p.aq_parent
        else: p=None

        #logger.info('Args are : %s' % self._arg.items())
        argdata=self._argdata(REQUEST)
        argdata['sql_delimiter']='\0'
        argdata['sql_quote__']=dbc.sql_quote__

        security=getSecurityManager()
        security.addContext(self)
        try:
            try:     query=apply(self.template, (p,), argdata)
            except TypeError, msg:
                msg = str(msg)
                if msg.find('client') >= 0:
                    raise NameError("'client' may not be used as an " +
                        "argument name in this context: %s" % msg)
                else: raise
        finally: security.removeContext(self)

        if src__: return query

        # Query data must ONLY constains keys used in query, no more key, 
        # else error is raised
        query_data = {}
        query = '%s ' % query
        
        for key in self._arg.keys():
            # Do not include key in query data if not in query
            if query.find(':%s ' % key) != -1 or query.find(':%s\n' % key) != -1 or query.find(':%s\r' % key) != -1:
                
                # Getting value for key
                if argdata.has_key(key):
                    value = argdata[key]
                else:
                    logger.warn('Key %s not found in argdata:\n%s' % (key, argdata))
                
                if type(value) == type([]) or type(value) == type((1,2)) and len(value) == 1:
                    value = value[0]
                    
                if type(value) != type(1) and type(value) != type(1.2) and type(value) != type('') and type(value) != type(None):
                    value = str(value)
                
                query_data[key] = value

        #logger.info("Query data is ---%s---" % query_data)
        #logger.info("Query is ---%s---" % query)

        if self.cache_time_ > 0 and self.max_cache_ > 0:
            try:
                result=self._cached_result(DB__, query, self.max_rows_, c, query_data)
            except Exception, err:
                logger.error('Erro while looking in cache for query: %s\nArgs:%s\nQuery data:%s\nQuery:%s' % (err, self._arg.items(), query_data, query))
                result=DB__.query('%s' % query, self.max_rows_, query_data)
        else:
            #logger.info("Query is %s" % query)
            result=DB__.query('%s' % query, self.max_rows_, query_data)

        if hasattr(self, '_v_brain'): brain=self._v_brain
        else:
            brain=self._v_brain=getBrain(self.class_file_, self.class_name_)

        zc=self._zclass
        if zc is not None: zc=zc._zclass_

        if type(result) is type(''):
            f=StringIO()
            f.write(result)
            f.seek(0)
            result=RDB.File(f,brain,p, zc)
        else:
            result=Results(result, brain, p, zc)
        columns=result._searchable_result_columns()
        if test__ and columns != self._col: self._col=columns

        # If run in test mode, return both the query and results so
        # that the template doesn't have to be rendered twice!
        if test__: return query, result

        return result


    if Globals.DevelopmentMode:
        # Provide an opportunity to update the properties.
        def __of__(self, parent):
            try:
                self = ImplicitAcquisitionWrapper(self, parent)
                self._updateFromFS()
                return self
            except:
                logger.exception("Error during __of__")
                raise

InitializeClass(FSORAMethod)

registerFileExtension('zora', FSORAMethod)
registerMetaType('Oracle Method', FSORAMethod)
