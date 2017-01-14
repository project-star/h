# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from pyramid.renderers import render

from h.i18n import TranslationString as _


def generate(request, id, email, invitation_code):
    """
    Generate an email for a user signup.

    :param request: the current request
    :type request: pyramid.request.Request
    :param id: the new user's primary key ID
    :type id: int
    :param email: the new user's email address
    :type email: text
    :param invitation_code: the invitation code
    :type invitation_code: text

    :returns: a 4-element tuple containing: recipients, subject, text, html
    """
    context = {
        'invite_link': request.route_url('invitesignup',
                                           id=id,
                                           code=invitation_code),
    }

    subject = _('Welcome to Renoted - Your Digital Mind Palace')

    text = render('h:templates/emails/invite.txt.jinja2',
                  context,
                  request=request)
    html = render('h:templates/emails/invite.html.jinja2',
                  context,
                  request=request)

    return [email], subject, text, html
