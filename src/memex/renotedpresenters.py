
# -*- coding: utf-8 -*-
"""
Presenters for API data.
"""

import collections
import copy


class UrlBasePresenter(object):
    def __init__(self, urldata, annotations):
        self.urldata = urldata
        self.annotations = annotations
    @property
    def created(self):
        if self.urldata.created:
            return utc_iso8601(self.urldata.created)

    @property
    def updated(self):
        if self.urldata.updated:
            return utc_iso8601(self.urldata.updated)


class UrlJSONPresenter(UrlBasePresenter):

    """Present a url in the JSON format returned by API requests."""
    def asdict(self):
        annotation=[]
        
        base = {
            'id': self.urldata.id,
            'created': self.created,
            'updated': self.updated,
            'title': self.urldata.title,
            'uriaddress': self.urldata.uriaddress,
            'user': self.urldata.userid,
            'tags': self.urldata.tags,
            'isbookmark': self.urldata.isbookmark,
            'isdeleted': self.urldata.isdeleted,
            'rows': self.annotations
        }
        urldata = {}
        urldata.update(base)
        return urldata

class SimpleUrlPresenter(object):
    def __init__(self, urldata):
        self.urldata = urldata

    @property
    def created(self):
        if self.urldata.created:
            return utc_iso8601(self.urldata.created)

    @property
    def updated(self):
        if self.urldata.updated:
            return utc_iso8601(self.urldata.updated)

class SimpleUrlJSONPresenter(SimpleUrlPresenter):

    """Present a url in the JSON format returned by API requests."""
    def asdict(self):

        base = {
            'id': self.urldata.id,
            'created': self.created,
            'updated': self.updated,
            'title': self.urldata.title,
            'uriaddress': self.urldata.uriaddress,
            'user': self.urldata.userid,
            'tags': self.urldata.tags,
            'isbookmark': self.urldata.isbookmark,
            'isdeleted': self.urldata.isdeleted
        }
        urldata = {}
        urldata.update(base)
        return urldata




class RenotedDocumentJSONPresenter(object):
    def __init__(self, document):
        self.document = document

    def asdict(self):
        if not self.document:
            return {}

        d = {}
        title = self.document.title
        if title:
            d['title'] = [title]

        return d


def utc_iso8601(datetime):
    return datetime.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
