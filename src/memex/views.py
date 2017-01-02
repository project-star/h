# -*- coding: utf-8 -*-

"""
HTTP/REST API for storage and retrieval of annotation data.

This module contains the views which implement our REST API, mounted by default
at ``/api``. Currently, the endpoints are limited to:

- basic CRUD (create, read, update, delete) operations on annotations
- annotation search
- a handful of authentication related endpoints

It is worth noting up front that in general, authorization for requests made to
each endpoint is handled outside of the body of the view functions. In
particular, requests to the CRUD API endpoints are protected by the Pyramid
authorization system. You can find the mapping between annotation "permissions"
objects and Pyramid ACLs in :mod:`memex.resources`.
"""
from pyramid import i18n
from pyramid import security
from pyramid.view import view_config
from sqlalchemy.orm import subqueryload
from werkzeug.datastructures import MultiDict
from memex import cors
from memex import models
from memex.events import AnnotationEvent
from memex.presenters import AnnotationJSONPresenter
from memex.renotedpresenters import UrlJSONPresenter
from memex.renotedpresenters import SimpleUrlJSONPresenter
from memex.presenters import AnnotationJSONLDPresenter
from memex import search as search_lib
from memex import schemas
from memex import storage
from pymongo import MongoClient
import json
_ = i18n.TranslationStringFactory(__package__)

cors_policy = cors.policy(
    allow_headers=(
        'Authorization',
        'Content-Type',
        'X-Annotator-Auth-Token',
        'X-Client-Id',
    ),
    allow_methods=('HEAD', 'GET', 'POST', 'PUT', 'DELETE'))


class APIError(Exception):

    """Base exception for problems handling API requests."""

    def __init__(self, message, status_code=500):
        self.status_code = status_code
        super(APIError, self).__init__(message)


class PayloadError(APIError):

    """Exception raised for API requests made with missing/invalid payloads."""

    def __init__(self):
        super(PayloadError, self).__init__(
            _('Expected a valid JSON payload, but none was found!'),
            status_code=400
        )


def api_config(**settings):
    """
    A view configuration decorator with defaults.

    JSON in and out. CORS with tokens and client id but no cookie.
    """
    settings.setdefault('accept', 'application/json')
    settings.setdefault('renderer', 'json')
    settings.setdefault('decorator', cors_policy)
    return view_config(**settings)


@api_config(context=APIError)
def error_api(context, request):
    request.response.status_code = context.status_code
    return {'status': 'failure', 'reason': context.message}


@api_config(context=schemas.ValidationError)
def error_validation(context, request):
    request.response.status_code = 400
    return {'status': 'failure', 'reason': context.message}


@api_config(route_name='api.index')
def index(context, request):
    """Return the API descriptor document.

    Clients may use this to discover endpoints for the API.
    """
    # Because request.route_url urlencodes parameters, we can't just pass in
    # ":id" as the id here.
    annotation_url = request.route_url('api.annotation', id='123')\
                            .replace('123', ':id')
    renoted_url = request.route_url('api.url', id='123')\
                            .replace('123', ':id')
    urlupdate_url = request.route_url('api.urlupdate', id='123')\
                            .replace('123', ':id')
    return {
        'message': "Annotator Store API",
        'links': {
            'annotation': {
                'create': {
                    'method': 'POST',
                    'url': request.route_url('api.annotations'),
                    'desc': "Create a new annotation"
                },
                'read': {
                    'method': 'GET',
                    'url': annotation_url,
                    'desc': "Get an existing annotation"
                },
                'update': {
                    'method': 'PUT',
                    'url': annotation_url,
                    'desc': "Update an existing annotation"
                },
                'delete': {
                    'method': 'DELETE',
                    'url': annotation_url,
                    'desc': "Delete an annotation"
                }
            },
            'search': {
                'method': 'GET',
                'url': request.route_url('api.search'),
                'desc': 'Basic search API'
            },
            'url': {
                  'method': 'GET',
                  'url': renoted_url,
                  'desc': "Get an existing annotation"
            },
            'recall': {
                  'method': 'POST',
                  'url': request.route_url('api.recall'),
                  'desc': "Get recalled annotations"
            },
            'urls': {
                  'method': 'GET',
                  'url': request.route_url('api.urls'),
                  'desc': "Get all annotatated urls of a user"
            },
            'urlupdate': {
                  'update': {
                    'method': 'PUT',
                    'url': urlupdate_url,
                    'desc': "Update an existing url"
                },
                  'delete': {
                     'method': 'DELETE',
                     'url': urlupdate_url,
                     'desc': "Delete a url"
                }
            }
        }
    }


@api_config(route_name='api.search')
def search(request):
    """Search the database for annotations matching with the given query."""
    params = request.params.copy()
    print params
    separate_replies = params.pop('_separate_replies', False)
    result = search_lib.Search(request, separate_replies=separate_replies) \
        .run(params)

    out = {
        'total': result.total,
        'rows': _present_annotations(request, result.annotation_ids)
    }

    if separate_replies:
        out['replies'] = _present_annotations(request, result.reply_ids)

    return out


@api_config(route_name='api.annotations',
            request_method='POST',
            effective_principals=security.Authenticated)
def create(request):
    """Create an annotation from the POST payload."""
    urischema=schemas.CreateURI(request)
    print (_json_payload(request))
    uriappstruct = urischema.validate(_json_payload(request))
    uri = storage.create_uri(request, uriappstruct)
    schema = schemas.CreateAnnotationSchema(request)
    appstruct = schema.validate(_json_payload(request))
    annotation = storage.create_annotation(request, appstruct)
    
    _publish_annotation_event(request, annotation, 'create')

    links_service = request.find_service(name='links')
    presenter = AnnotationJSONPresenter(annotation, links_service)
    return presenter.asdict()

@api_config(route_name='api.urls',
            request_method='GET',
            effective_principals=security.Authenticated)
def readannotatedurls(request):
    """Get the list of annotated urls from the user."""
    params = request.params.copy()
    print ("+++ in urls params ++++")
    print params
    urllist=[]
    retval={}
    if len(params) > 0:
        print ("+++params is not none+++")
        result = search_lib.Search(request) \
        .run(params)

        out = {
            'total': result.total,
            'rows': _sort_annotations(_present_annotations(request, result.annotation_ids))
        }
        print out["rows"]
        preexistingurl_id = []
        urlwiseannots={}
        for item in out["rows"]:
            searchurlid = item["uri_id"]
            urlsingledata = storage.fetch_url(request.db,searchurlid)
            urlstruct=SimpleUrlJSONPresenter(urlsingledata)
            if searchurlid not in preexistingurl_id:
                urlwiseannots[str(searchurlid)]=[]
                urllist.append(urlstruct.asdict())
                preexistingurl_id.append(searchurlid)
            urlwiseannots[str(searchurlid)].append(item)
            print urlwiseannots[searchurlid]
            print urllist
            for item1 in urllist:
                if item1["id"] == searchurlid:
                    item1["annotation"] = urlwiseannots[str(searchurlid)]
                    item["allannotation"] = _renotedread_allannotations(searchurlid,request)["annotations"]
        retval["total"] = len(urllist)
        retval["urllist"] = urllist
        return retval
    else:
        print ("+++params is  none+++")
        urlsdata = storage.fetch_urls(request.db,request.authenticated_userid)
        urllist=[]
        retval={}
        for item in urlsdata:
            params=MultiDict([(u'uri_id', item.id),(u'limit', 1)])
            result = search_lib.Search(request) \
            .run(params)
            urlstruct=SimpleUrlJSONPresenter(item)
            urlstructannot = urlstruct.asdict()
            urlstructannot["allannotation"] = _renotedread_allannotations(item.id,request)["annotations"]
            urlstructannot["annotation"] = _present_annotations(request, result.annotation_ids)
            urllist.append(urlstructannot)
        retval["total"] = len(urllist)
        retval["urllist"] = urllist
        return retval

@api_config(route_name='api.annotation',
            request_method='GET',
            permission='read')
def read(annotation, request):
    """Return the annotation (simply how it was stored in the database)."""
    links_service = request.find_service(name='links')
    print links_service

    presenter = AnnotationJSONPresenter(annotation, links_service)
    print presenter
    return presenter.asdict()

@api_config(route_name='api.url',
            request_method='GET',
            permission='read')
def renotedread(urldata, request):
    """Return the annotation (simply how it was stored in the database)."""
    params=MultiDict([(u'uri_id', urldata.id)])
    print params
    result = search_lib.Search(request) \
        .run(params)

    out = {
        'total': result.total,
        'annotations': _sort_annotations(_present_annotations(request, result.annotation_ids))
    }

    print out
    presenter = UrlJSONPresenter(urldata,out)
    print urldata
    return presenter.asdict()


@api_config(route_name='api.recall',
            request_method='POST',
            effective_principals=security.Authenticated)
def renotedrecallapi(request):
    """Return the annotation (simply how it was stored in the database)."""
    data=_json_payload(request)
    print (request.authenticated_userid)
    print data["url"]
    query=" "
    db=get_db()    
    collection=db.annotations.find({"uri": data["url"],"user":request.authenticated_userid})
    for item in collection:
        print item["uri_id"]
        print item["topics"]
        print item["addedtags"]
        for item1 in item["addedtags"]:
            query = query + " " + item1;
    params=MultiDict([(u'any', query)])
    print params
    result = search_lib.Search(request) \
        .run(params)

    out = {
        'total': result.total,
        'annotations': _present_annotations(request, result.annotation_ids)
    }

    print out
    #presenter = UrlJSONPresenter(urldata,out)
    #print urldata
    return out

@api_config(route_name='api.annotation.jsonld',
            request_method='GET',
            permission='read')
def read_jsonld(annotation, request):
    request.response.content_type = 'application/ld+json'
    request.response.content_type_params = {
        'profile': AnnotationJSONLDPresenter.CONTEXT_URL}
    links_service = request.find_service(name='links')
    presenter = AnnotationJSONLDPresenter(annotation, links_service)
    return presenter.asdict()


@api_config(route_name='api.annotation',
            request_method='PUT',
            permission='update')
def update(annotation, request):
    """Update the specified annotation with data from the PUT payload."""
    uri = storage.update_uri(request.db, annotation)
    schema = schemas.UpdateAnnotationSchema(request,
                                            annotation.target_uri,
                                            annotation.groupid)
    appstruct = schema.validate(_json_payload(request))

    annotation = storage.update_annotation(request.db,
                                           annotation.id,
                                           appstruct)

    _publish_annotation_event(request, annotation, 'update')

    links_service = request.find_service(name='links')
    presenter = AnnotationJSONPresenter(annotation, links_service)
    return presenter.asdict()


@api_config(route_name='api.urlupdate',
            request_method='PUT',
            permission='update')
def urlupdate(url, request):
    """Update the specified annotation with data from the PUT payload."""
    print ("++++ in url update ++++")
    print url.tags
    print (_json_payload(request))
    schema = schemas.UpdateURLSchema(request)
    appstruct = schema.validate(_json_payload(request))

    url = storage.update_URL(request.db,url.id,appstruct)

    #_publish_annotation_event(request, annotation, 'update')

    #links_service = request.find_service(name='links')
    presenter = SimpleUrlJSONPresenter(url)
    val= presenter.asdict()
    val["annotation"] = _json_payload(request)["annotation"]
    return val


@api_config(route_name='api.annotation',
            request_method='DELETE',
            permission='delete')
def delete(annotation, request):
    """Delete the specified annotation."""
    uri = storage.update_uri(request.db, annotation)
    storage.delete_annotation(request.db, annotation.id)

    # N.B. We publish the original model (including all the original annotation
    # fields) so that queue subscribers have context needed to decide how to
    # process the delete event. For example, the streamer needs to know the
    # target URLs of the deleted annotation in order to know which clients to
    # forward the delete event to.
    _publish_annotation_event(
        request,
        annotation,
        'delete')

    return {'id': annotation.id, 'deleted': True}


@api_config(route_name='api.urlupdate',
            request_method='DELETE',
            permission='delete')
def urldelete(url, request):
    """Delete the specified annotation."""
    params=MultiDict([(u'uri_id', url.id)])
    print params
    result = search_lib.Search(request) \
        .run(params)
    out = {
            'total': result.total,
            'rows': _present_annotations(request, result.annotation_ids)
        }

    for item in out["rows"]:
        print item
        print item["id"]
        storage.delete_annotation(request.db, item["id"])
        event = AnnotationEvent(request, item["id"], 'delete', item)
        request.notify_after_commit(event)
    #uri = storage.update_uri(request.db, url)
    storage.delete_url(request.db, url.id)

    # N.B. We publish the original model (including all the original annotation
    # fields) so that queue subscribers have context needed to decide how to
    # process the delete event. For example, the streamer needs to know the
    # target URLs of the deleted annotation in order to know which clients to
    # forward the delete event to.
   # _publish_annotation_event(
   #     request,
   #     annotation,
   #     'delete')

    return {'id': url.id, 'deleted': True}



def _json_payload(request):
    """
    Return a parsed JSON payload for the request.

    :raises PayloadError: if the body has no valid JSON body
    """
    try:
        return request.json_body
    except ValueError:
        raise PayloadError()


def _present_annotations(request, ids):
    """Load annotations by id from the database and present them."""
    def eager_load_documents(query):
        return query.options(
            subqueryload(models.Annotation.document))

    annotations = storage.fetch_ordered_annotations(request.db, ids,
                                                    query_processor=eager_load_documents)
    links_service = request.find_service(name='links')
    return [AnnotationJSONPresenter(ann, links_service).asdict()
            for ann in annotations]

def _sort_annotations(annotationlist):
    returnedannotationlist =[]
    unsorted=[]
    sortedval=[]
    for item in annotationlist:
        print item
        if not('selector'  in item["target"][0]) or len(item["target"][0]["selector"]) < 4:
            print "+++ this is a video annotated url+++"
            return annotationlist
        else: 
            unsortedat={}
            print "+++ this is a text annotated url+++"
            for selectors in item["target"][0]["selector"]:
                if selectors["type"]=="TextPositionSelector":
                    unsortedat["id"]=item["id"]
                    unsortedat["start"]=selectors["start"]
               
        unsorted.append(unsortedat)
    print unsorted
    sortedval = sorted(unsorted, key=lambda k: k['start'])
    print sortedval
    for item in sortedval:
        for item1 in annotationlist:
            if (item1["id"] == item["id"]):
                returnedannotationlist.append(item1)    
    return returnedannotationlist


def _publish_annotation_event(request,
                              annotation,
                              action):
    """Publish an event to the annotations queue for this annotation action."""
    links_service = request.find_service(name='links')
    annotation_dict = None
    if action == 'delete':
        presenter = AnnotationJSONPresenter(annotation, links_service)
        annotation_dict = presenter.asdict()

    event = AnnotationEvent(request, annotation.id, action, annotation_dict)
    request.notify_after_commit(event)


def _renotedread_allannotations(urlid, request):
    """Return the annotation (simply how it was stored in the database)."""
    params=MultiDict([(u'uri_id', urlid)])
    print params
    result = search_lib.Search(request) \
        .run(params)

    out = {
        'total': result.total,
        'annotations': _sort_annotations(_present_annotations(request, result.annotation_ids))
    }

    return out


def get_db():
    client = MongoClient('0.0.0.0:27017')
    db = client.renoted
    return db

def includeme(config):
    config.scan(__name__)
