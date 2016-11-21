
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


class UrlJSONPresenter(UrlBasePresenter):

    """Present a url in the JSON format returned by API requests."""
    def asdict(self):
        base = {
            'id': self.urldata.id,
            'uriaddress': self.urldata.uriaddress,
            'user': self.urldata.userid,
            'tags': self.urldata.tags,
            'isbookmark': self.urldata.isbookmark,
            'rows': self.annotations
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


