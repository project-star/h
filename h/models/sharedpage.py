# -*- coding: utf-8 -*-

import datetime
import re

import sqlalchemy as sa
from sqlalchemy.ext.hybrid import Comparator, hybrid_property
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.mutable import MutableDict
from h._compat import text_type
from h.db import Base
from h.security import password_context
from h.util.user import split_user
from memex.db import types
from pyramid import security

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
USERNAME_PATTERN = '(?i)^[A-Z0-9._]+$'
EMAIL_MAX_LENGTH = 100
PASSWORD_MIN_LENGTH = 2




class Sharedpage(Base):
    __tablename__ = 'sharedpage'
 
    __table_args__ = (
        # Tags are stored in an array-type column, and indexed using a
        # generalised inverted index. For more information on the use of GIN
        # indices for array columns, see:
        #
        #   http://www.databasesoup.com/2015/01/tag-all-things.html
        #   http://www.postgresql.org/docs/9.5/static/gin-intro.html
        #
        sa.Index('ix__sharedpage_tags', 'tags', postgresql_using='gin'),
    )

    id = sa.Column(types.URLSafeUUID,
                   server_default=sa.func.uuid_generate_v1mc(),
                   primary_key=True)
    #: Username as chosen by the user on registration
    uriaddress = sa.Column( sa.UnicodeText(), nullable=False)

    #: The display name which will be used when rendering an annotation.
    title = sa.Column(sa.UnicodeText())

    #: A short user description/bio
    description = sa.Column(sa.UnicodeText())

    userid = sa.Column(sa.UnicodeText,
                       nullable=False,
                       index=True)

    created = sa.Column(sa.DateTime,
                        default=datetime.datetime.utcnow,
                        server_default=sa.func.now(),
                        nullable=False)

    #: The timestamp when the user edited the annotation last.
    updated = sa.Column(sa.DateTime,
                        server_default=sa.func.now(),
                        default=datetime.datetime.utcnow,
                        nullable=False)
    #: Is this uri a bookmark?
    isbookmark = sa.Column(sa.Boolean,
                      default=False,
                      nullable=False)
    numbershared = sa.Column(sa.Integer,
                      default=0,
                      nullable=False)

    isdeleted = sa.Column(sa.Boolean,
                      default=False,
                      nullable=False)
    
    
    

    #: The tags associated with the annotation.
    tags = sa.Column(
        types.MutableList.as_mutable(
            pg.ARRAY(sa.UnicodeText, zero_indexes=True)))
    def __acl__(self):
        """Return a Pyramid ACL for this annotation."""
        acl = []
        acl.append((security.Allow, self.userid, 'read'))

        for action in ['admin', 'update', 'delete']:
            acl.append((security.Allow, self.userid, action))

        # If we haven't explicitly authorized it, it's not allowed.
        acl.append(security.DENY_ALL)

        return acl
    def __repr__(self):
        return '<Sharedpagedata %s>' % self.id
    
