##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
'''Inserting values with the 'sqlvar' tag

    The 'sqlvar' tag is used to type-safely insert values into SQL
    text.  The 'sqlvar' tag is similar to the 'var' tag, except that
    it replaces text formatting parameters with SQL type information.

    The sqlvar tag has the following attributes:

      name -- The name of the variable to insert. As with other
              DTML tags, the 'name=' prefix may be, and usually is,
              ommitted.

      type -- The data type of the value to be inserted.  This
              attribute is required and may be one of 'string',
              'int', 'float', or 'nb'.  The 'nb' data type indicates a
              string that must have a length that is greater than 0.

      optional -- A flag indicating that a value is optional.  If a
                  value is optional and is not provided (or is blank
                  when a non-blank value is expected), then the string
                  'null' is inserted.

    For example, given the tag::

      <dtml-sqlvar x type=nb optional>

    if the value of 'x' is::

      Let\'s do it

    then the text inserted is:

      'Let''s do it'

    however, if x is ommitted or an empty string, then the value
    inserted is 'null'.

    original: https://github.com/MordicusEtCubitus/ZcxOracleDA/blob/master/dtmlsql.py
'''
__rcs_id__='$Id: sqlvar.py 40218 2005-11-18 14:39:19Z andreasjung $'

############################################################################
#     Copyright
#
#       Copyright 1996 Digital Creations, L.C., 910 Princess Anne
#       Street, Suite 300, Fredericksburg, Virginia 22401 U.S.A. All
#       rights reserved.
#
############################################################################
__version__='$Revision: 1.15 $'[11:-2]

import sys
from logging import getLogger
from DocumentTemplate.DT_Util import ParseError, parse_params, name_param
from string import find, split, join, atoi, atof
from types import ListType, TupleType, StringType

StringType=type('')

str=__builtins__['str']

logger = getLogger("dtmlsql")

class SQLVar:
    name='sqlvar'

    def __init__(self, args):
        args = parse_params(args, name='', expr='', type=None, optional=1)

        name,expr=name_param(args,'sqlvar',1)
        #logger.info('Name is %s, Expr is %s' % (name, expr))
        
        if expr is None: expr=name
        else: expr=expr.eval
        self.__name__, self.expr = name, expr

        self.args=args
        if not args.has_key('type'):
            raise ParseError, ('the type attribute is required', 'dtvar')
        t=args['type']
        if not valid_type(t):
            raise ParseError, ('invalid type, %s' % t, 'dtvar')

    def render(self, md):
        name=self.__name__
        args=self.args
        t=args['type']
        try:
            expr=self.expr
            if type(expr) is type(''): v=md[expr]
            else: v=expr(md)
        except:
            if args.has_key('optional') and args['optional']:
                return 'null'
            if type(expr) is not type(''):
                raise
            raise ValueError, 'Missing input variable, <em>%s</em>' % name

        if v is None:
            return 'null'

        if not v: 
            if t in ('int', 'float', 'nb') and args.has_key('optional') and args['optional']:
                return 'null'
            else:
                
                if not isinstance(v, (str, unicode)):
                    v=str(v)
                if not v and t=='nb':
                    if args.has_key('optional') and args['optional']:
                        return 'null'
                    else:
                        raise ValueError, (
                            'Invalid empty string value for <em>%s</em>' % name)

        #logger.info("SQLVAR returns :%s" % name)
        # We add a space after the name
        # This is beacause when creating query_data dictionnary which must
        # only contains keys for used parameters, no one more
        # we are checking if a parameter exists by finding its name in the query
        # returned after DTML evaluation
        # so param 'dummy' whill be checked as contained if 'dummy_2' is contained
        # Thus, adding a space will allwo to search on '%(name)s " to check
        # if param must be added to query data
        return ':%s ' % name

    __call__=render

valid_type={'int':1, 'float':1, 'string':1, 'nb': 1}.has_key



'''Inserting optional tests with 'sqlgroup'

    It is sometimes useful to make inputs to an SQL statement
    optinal.  Doing so can be difficult, because not only must the
    test be inserted conditionally, but SQL boolean operators may or
    may not need to be inserted depending on whether other, possibly
    optional, comparisons have been done.  The 'sqlgroup' tag
    automates the conditional insertion of boolean operators.

    The 'sqlgroup' tag is a block tag that has no attributes. It can
    have any number of 'and' and 'or' continuation tags.

    Suppose we want to find all people with a given first or nick name
    and optionally constrain the search by city and minimum and
    maximum age.  Suppose we want all inputs to be optional.  We can
    use DTML source like the following::

      <dtml-sqlgroup>
        <dtml-sqlgroup>
          <dtml-sqltest name column=nick_name type=nb multiple optional>
        <dtml-or>
          <dtml-sqltest name column=first_name type=nb multiple optional>
        </dtml-sqlgroup>
      <dtml-and>
        <dtml-sqltest home_town type=nb optional>
      <dtml-and>
        <dtml-if minimum_age>
           age >= <dtml-sqlvar minimum_age type=int>
        </dtml-if>
      <dtml-and>
        <dtml-if maximum_age>
           age <= <dtml-sqlvar maximum_age type=int>
        </dtml-if>
      </dtml-sqlgroup>

    This example illustrates how groups can be nested to control
    boolean evaluation order.  It also illustrates that the grouping
    facility can also be used with other DTML tags like 'if' tags.

    The 'sqlgroup' tag checks to see if text to be inserted contains
    other than whitespace characters.  If it does, then it is inserted
    with the appropriate boolean operator, as indicated by use of an
    'and' or 'or' tag, otherwise, no text is inserted.

'''



class SQLTest:
    name='sqltest'
    optional=multiple=None

    def __init__(self, args):
        args = parse_params(args, name='', expr='', type=None, column=None,
                            multiple=1, optional=1, op=None)
        name,expr = name_param(args,'sqlvar',1)

        if expr is None:
            expr=name
        else: expr=expr.eval
        self.__name__, self.expr = name, expr

        self.args=args
        if not args.has_key('type'):
            raise ParseError, ('the type attribute is required', 'sqltest')

        self.type=t=args['type']
        if not valid_type(t):
            raise ParseError, ('invalid type, %s' % t, 'sqltest')

        if args.has_key('optional'): self.optional=args['optional']
        if args.has_key('multiple'): self.multiple=args['multiple']
        if args.has_key('column'):
            self.column=args['column']
        elif self.__name__ is None:
            err = ' the column attribute is required if an expression is used'
            raise ParseError, (err, 'sqltest')
        else:
            self.column=self.__name__

        # Deal with optional operator specification
        op = '='                        # Default
        if args.has_key('op'):
            op = args['op']
            # Try to get it from the chart, otherwise use the one provided
            op = comparison_operators.get(op, op)
        self.op = op

    def render(self, md):
        name=self.__name__

        t=self.type
        args=self.args
        try:
            expr=self.expr
            if type(expr) is type(''):
                v=md[expr]
            else:
                v=expr(md)
        except KeyError:
            if args.has_key('optional') and args['optional']:
                return ''
            raise ValueError, 'Missing input variable, <em>%s</em>' % name

        if type(v) in (ListType, TupleType):
            if len(v) > 1 and not self.multiple:
                raise ValueError, (
                    'multiple values are not allowed for <em>%s</em>'
                    % name)
        else: v=[v]

        vs=[]
        for v in v:
            if not v and type(v) is StringType and t != 'string': continue
            if t=='int':
                try:
                    if type(v) is StringType:
                        if v[-1:]=='L':
                            v=v[:-1]
                        atoi(v)
                    else: v=str(int(v))
                except ValueError:
                    raise ValueError, (
                        'Invalid integer value for <em>%s</em>' % name)
            elif t=='float':
                if not v and type(v) is StringType: continue
                try:
                    if type(v) is StringType: atof(v)
                    else: v=str(float(v))
                except ValueError:
                    raise ValueError, (
                        'Invalid floating-point value for <em>%s</em>' % name)

            else:
                if not isinstance(v, (str, unicode)):
                    v = str(v)
                v=md.getitem('sql_quote__',0)(v)
                #if find(v,"\'") >= 0: v=join(split(v,"\'"),"''")
                #v="'%s'" % v
            vs.append(v)

        if not vs and t=='nb':
            if args.has_key('optional') and args['optional']:
                return ''
            else:
                err = 'Invalid empty string value for <em>%s</em>' % name
                raise ValueError, err


        if not vs:
            if self.optional: return ''
            raise ValueError, (
                'No input was provided for <em>%s</em>' % name)

        # Arrays cannot be precompiled, so still expanded to full value
        if len(vs) > 1:
            vs=join(map(str,vs),', ')
            if self.op == '<>':
                ## Do the equivalent of 'not-equal' for a list,
                ## "a not in (b,c)"
                return "%s not in (%s)" % (self.column, vs)
            else:
                ## "a in (b,c)"
                return "%s in (%s)" % (self.column, vs)
            
        # Only changes for single values
        # Space after name is required to prevent from issue
        # see dtml-sqlvar comment for explanation
        return "%s %s :%s " % (self.column, self.op, name)

    __call__=render

valid_type={'int':1, 'float':1, 'string':1, 'nb': 1}.has_key

comparison_operators = { 'eq': '=', 'ne': '<>',
                         'lt': '<', 'le': '<=', 'lte': '<=',
                         'gt': '>', 'ge': '>=', 'gte': '>=' }
