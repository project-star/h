# -*- coding: utf-8 -*-

from memex import storage

class AnnotationFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, id):
        annotation = storage.fetch_annotation(self.request.db, id)
        print id
        if annotation is None:
            raise KeyError()
        return annotation
class SharedannotationFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, id):
        annotation = storage.fetch_sharedannotation(self.request.db, id)
        print id
        if annotation is None:
            raise KeyError()
        return annotation


class URLFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, id):
        print id
        urldata = storage.fetch_url(self.request.db, id)
        print id
        if urldata is None:
            raise KeyError()
        return urldata
class SharedURLFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, id):
        print id
        urldata = storage.fetch_sharedurl(self.request.db, id)
        print id
        if urldata is None:
            raise KeyError()
        return urldata
class URLSFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self):
        print "++ in factory++"
        urlsdata = storage.fetch_urls(self.request.db,self.request.authenticated_userid)
        print urlsdata
        if urlsdata is None:
            raise KeyError()
        return urlsdata

class RECALLFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, id):
        print id
        urldata = storage.fetch_url(self.request.db, id)
        print id
        if urldata is None:
            raise KeyError()
        return urldata


