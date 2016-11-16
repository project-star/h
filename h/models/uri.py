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

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
USERNAME_PATTERN = '(?i)^[A-Z0-9._]+$'
EMAIL_MAX_LENGTH = 100
PASSWORD_MIN_LENGTH = 2




class Uri(Base):
    __tablename__ = 'uri'
 
    __table_args__ = (
        # Tags are stored in an array-type column, and indexed using a
        # generalised inverted index. For more information on the use of GIN
        # indices for array columns, see:
        #
        #   http://www.databasesoup.com/2015/01/tag-all-things.html
        #   http://www.postgresql.org/docs/9.5/static/gin-intro.html
        #
        sa.Index('ix__uri_tags', 'tags', postgresql_using='gin'),
    )

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

    #: Username as chosen by the user on registration
    uriaddress = sa.Column( sa.UnicodeText(), nullable=False)


    #: The display name which will be used when rendering an annotation.
    title = sa.Column(sa.UnicodeText())

    #: A short user description/bio
    description = sa.Column(sa.UnicodeText())

    userid = sa.Column(sa.UnicodeText,
                       nullable=False,
                       index=True)
    #: Is this uri a bookmark?
    isbookmark = sa.Column(sa.Boolean,
                      default=False,
                      nullable=False)



    #: The tags associated with the annotation.
    tags = sa.Column(
        types.MutableList.as_mutable(
            pg.ARRAY(sa.UnicodeText, zero_indexes=True)))
