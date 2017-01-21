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




class Sharing(Base):
    __tablename__ = 'sharing'
 
    id = sa.Column(types.URLSafeUUID,
                   server_default=sa.func.uuid_generate_v1mc(),
                   primary_key=True)

    annotationid = sa.Column(types.URLSafeUUID,
                             nullable=False)

    sharedtousername = sa.Column(sa.UnicodeText,
                       nullable=False,
                       index=True)
    sharedbyuserid = sa.Column(sa.UnicodeText,
                       nullable=False,
                       index=True)


    sharedtoemail = sa.Column(sa.UnicodeText(), nullable=False) 
    

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
    isshared = sa.Column(sa.Boolean,
                      default=True,
                      nullable=False)

    

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
        return '<Sharing %s>' % self.id
    
