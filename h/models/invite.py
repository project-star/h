# -*- coding: utf-8 -*-

import datetime
import re

import sqlalchemy as sa
from sqlalchemy.ext.hybrid import Comparator, hybrid_property

from h._compat import text_type
from h.db import Base
from h.security import password_context
from h.util.user import split_user

EMAIL_MAX_LENGTH = 100

class Invite(Base):
    __tablename__ = 'invite'
    __table_args__ = (
        sa.UniqueConstraint('email'),
    )

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

    email = sa.Column(sa.UnicodeText(), nullable=False)


    # Activation foreign key
    invitation_id = sa.Column(sa.Integer, sa.ForeignKey('invitation.id'))
    invitation = sa.orm.relationship('Invitation', backref='invite')

    @property
    def is_accepted(self):
        if self.invitation_id is None:
            return True

        return False

    def accepted(self):
        """Activate the user by deleting any activation they have."""
        session = sa.orm.object_session(self)
        session.delete(self.invitation)

    @sa.orm.validates('email')
    def validate_email(self, key, email):
        if len(email) > EMAIL_MAX_LENGTH:
            raise ValueError('email must be less than {max} characters '
                             'long'.format(max=EMAIL_MAX_LENGTH))
        return email

    @classmethod
    def get_by_email(cls, session, email):
        """Fetch a invite by email address."""
        return session.query(cls).filter(
            sa.func.lower(cls.email) == email.lower()
        ).first()

    @classmethod
    def get_by_invitation(cls, session, invitation):
        """Fetch a invite by invitation instance."""
        invite = session.query(cls).filter(
            cls.invitation_id == invitation.id
        ).first()

        return invite


    def __repr__(self):
        return '<Invite: %s>' % self.email


