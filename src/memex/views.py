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
import base64
import uuid
import datetime
from memex import cors
from memex import models
from memex.events import AnnotationEvent
from memex.events import StackEvent
from memex.presenters import AnnotationJSONPresenter
from memex.presenters import AnnotationSharedJSONPresenter
from memex.renotedpresenters import UrlJSONPresenter
from memex.renotedpresenters import SimpleUrlJSONPresenter
from memex.renotedpresenters import SimpleSharedUrlJSONPresenter
from memex.renotedpresenters import SimpleSharingJSONPresenter
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
    sharingannot_url = request.route_url('api.sharedannotation', id='123')\
                            .replace('123', ':id')
    sharing_url = request.route_url('api.sharedurl', id='123')\
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
            'sharing': {
                'create': {
                    'method': 'POST',
                    'url': request.route_url('api.sharings'),
                    'desc': "Create new sharings"
                },
               'read': {
                    'method': 'GET',
                    'url': request.route_url('api.sharings'),
                    'desc': "Get your shared urls"
                },
               'urldelete': {
                     'method': 'DELETE',
                     'url': sharing_url,
                     'desc': "Delete a sharedurl"
                },
                'annotdelete': {
                     'method': 'DELETE',
                     'url': sharingannot_url,
                     'desc': "Delete a sharedannotation"
                }
            },
            'stack': {
               'update': {
                     'method': 'POST',
                     'url': request.route_url('api.stacks'),
                     'desc': "Update stacks"
                },
                'read': {
                    'method': 'GET',
                    'url': request.route_url('api.stacks'),
                    'desc': "Get your shared urls"
                },
               'edit': {
                     'method': 'PUT',
                     'url': request.route_url('api.stacks'),
                     'desc': "Update stack name"
                },
                'delete': {
                    'method': 'PUT',
                    'url': request.route_url('api.stacksdelete'),
                    'desc': "Delete a stack name"
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
            },
            'ontopArchive': {
                  'method': 'POST',
                  'url': request.route_url('api.ontop.archive'),
                  'desc': "Make annotations/stacks Archived"
            },
            'ontopDearchive': {
                  'method': 'POST',
                  'url': request.route_url('api.ontop.dearchive'),
                  'desc': "Make annotations/stacks Archived"
            },
            'ontopDelete': {
                  'method': 'POST',
                  'url': request.route_url('api.ontop.delete'),
                  'desc': "Make annotations/stacks Deleted"
            },
            'stackService': {
                  'method': 'GET',
                  'url': request.route_url('api.stackservice.read'),
                  'desc': "Read Stacks"
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
    print ("+++++ search result as returned by elastic search +++++++")
    print result
    out = {
        'total': result.total,
        'rows': _present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map)
    }
    uri = params.pop('uri','')
    if uri:
        uri_id = storage.fetch_title_by_shareduriaddress(uri,request.authenticated_userid,request.db)
        if len(uri_id)>0:
            params.add("uri_id",uri_id[0].id)
            resultshare = search_lib.Sharedsearch(request, separate_replies=separate_replies).run(params)
            outshare = {
                'total': resultshare.total,
                'rows': _present_sharedannotations_withscore(request, resultshare.annotation_ids, resultshare.annotation_ids_map)
             }
        else:
            resultshare=False
    if separate_replies:
        out['replies'] = _present_annotations(request, result.reply_ids)
    if resultshare:
        returnout = {
                 'total': result.total + resultshare.total,
                 'rows': out["rows"] + outshare["rows"]
             }
        return returnout
    else:   
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


@api_config(route_name='api.stacks',
            request_method='POST',
            effective_principals=security.Authenticated)
def get_updatestacks(request):
    value=(_json_payload(request))
    if "uriaddress" not in value:
        uriaddress = "againsomething"
    else:
        if value["uriaddress"]:
            uriaddress = value["uriaddress"]
        else:
            uriaddress = "againsomething"
    if "stacks" not in value:
        val = storage.get_urlstack(uriaddress,request.authenticated_userid)
        return val
    else:
        storage.update_urlstack(uriaddress,request.authenticated_userid,value["stacks"])
        val = storage.get_urlstack(uriaddress,request.authenticated_userid)
        return val

@api_config(route_name='api.stacks',
            request_method='PUT',
            effective_principals=security.Authenticated)
def put_updatestacks(request):
    
    value=(_json_payload(request))
    print value["oldname"]
    print value["newname"]
    oldstack=[]
    newstack=[]
    oldstack.append(value["oldname"])
    newstack.append(value["newname"])
    username = request.authenticated_userid;
    db=get_db()
    db.userstack.update({"user": username},{'$pull':{"allstacks" : value["oldname"]}},multi=True)
    db.userstack.update({"user": username},{'$addToSet':{"allstacks" : value["newname"]}},multi=True)
    db.urlstack.update({ "user": username, "stacks":oldstack},{'$set': {'stacks': newstack}},multi=True)
    return "success"
  #  if "uriaddress" not in value:
  #      uriaddress = "againsomething"
  #  else:
  #      if value["uriaddress"]:
  #          uriaddress = value["uriaddress"]
  #      else:
  #          uriaddress = "againsomething"
  #  if "stacks" not in value:
  #      val = storage.get_urlstack(uriaddress,request.authenticated_userid)
  #      return val
  #  else:
  #      storage.update_urlstack(uriaddress,request.authenticated_userid,value["stacks"])
  #      val = storage.get_urlstack(uriaddress,request.authenticated_userid)
  #      return val


@api_config(route_name='api.stacksdelete',
            request_method='PUT',
            effective_principals=security.Authenticated)
def delete_updatestacks(request):
    value=(_json_payload(request))
    print value["name"]
    oldstack=[]
    newstack=[]
    oldstack.append(value["name"])
    username = request.authenticated_userid;
    db=get_db()
    db.userstack.update({"user": username},{'$pull':{"allstacks" : value["name"]}})
    db.urlstack.update({ "user": username, "stacks":oldstack},{'$set': {'stacks': newstack}})
    return "success"
  #  if "uriaddress" not in value:
  #      uriaddress = "againsomething"
  #  else:
  #      if value["uriaddress"]:
  #          uriaddress = value["uriaddress"]
  #      else:
  #          uriaddress = "againsomething"
  #  if "stacks" not in value:
  #      val = storage.get_urlstack(uriaddress,request.authenticated_userid)
  #      return val
  #  else:
  #      storage.update_urlstack(uriaddress,request.authenticated_userid,value["stacks"])
  #      val = storage.get_urlstack(uriaddress,request.authenticated_userid)
  #      return val




@api_config(route_name='api.sharings',
            request_method='POST',
            effective_principals=security.Authenticated)
def createSharing(request):
    """Create an annotation from the POST payload."""
    value= (_json_payload(request))
    retvalue={}
    retvalue["total"]=0
    sharings=[]
    sharedtousername = value["sharedtoemail"]
    sharedtouser = storage.get_user_by_username(request.db,sharedtousername)
    if len(sharedtouser) ==0:
        retvalue["status"] = 'failure'
        retvalue["reason"] = 'Invalid User Id'
        return retvalue
    else:
        sharedtoemail = sharedtouser[0].email
        retvalue["status"] = 'success'
    sharedtofulluserid = "acct:"+sharedtouser[0].username + "@"+sharedtouser[0].authority
    print "++++to check if data collection is right++"
    print sharedtofulluserid
    storage.make_sharing_notification_entry(sharedtofulluserid,len(value["annotation_ids"]))
    print value["annotation_ids"]
    for item in value["annotation_ids"]:
        sharedpage = _sharedpage(item,sharedtoemail,request)
        result = _createannotationwisesharing(item,sharedtoemail,sharedpage.id,request)
        print result
        retvalue["total"] = retvalue["total"] +1 
        sharings.append(result)
    retvalue["sharings"] = sharings; 
    #uriappstruct = urischema.validate(_json_payload(request))
    #uri = storage.create_uri(request, uriappstruct)
    #schema = schemas.CreateAnnotationSchema(request)
    #appstruct = schema.validate(_json_payload(request))
    #annotation = storage.create_annotation(request, appstruct)

    #_publish_annotation_event(request, annotation, 'create')

    #links_service = request.find_service(name='links')
    #presenter = AnnotationJSONPresenter(annotation, links_service)
    return retvalue

@api_config(route_name='api.urls',
            request_method='GET',
            effective_principals=security.Authenticated)
def readannotatedurls(request):
    """Get the list of annotated urls from the user."""
    params = request.params.copy()
    valueparams = request.params.copy()
    print ("+++ in urls params ++++")
    print params
    type = valueparams.pop('type','all')
    print type 
    print (type == 'all')
    urllist=[]
    retval={}
    allstacklist = _getallstacklist(request.authenticated_userid)
    if len(params) > 0 and type == 'all':
        print ("+++params is not none+++")
        result = search_lib.Search(request) \
        .run(params)

        out = {
            'total': result.total,
            'rows': _sort_annotations(_present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map))
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
                    item1["typeFilter"] = _getfiltertype(request.authenticated_userid,urlwiseannots[str(searchurlid)])
                    item1["allannotation"] = _renotedread_allannotations(item1["id"],request)["annotations"]
                    item1["relevance"] = _max_relevance_perurl(item1["annotation"])
                    item1["allstackslist"] = allstacklist
        retval["total"] = len(urllist)
        retval["urllist"] = urllist
        return retval
    elif (type != 'all') and len(params) == 1:
        print ("+++params is  of type+++")
        urlsdata = storage.fetch_urls(request.db,request.authenticated_userid)
        urllist=[]
        retval={}
        for item in urlsdata:
            params=MultiDict([(u'uri_id', item.id),(u'limit', 1),(u'type',type)])
            result = search_lib.Search(request) \
            .run(params)
            urlstruct=SimpleUrlJSONPresenter(item)
            urlstructannot = urlstruct.asdict()
            urlstructannot["allannotation"] = _renotedread_allannotations(item.id,request)["annotations"]
            
            urlstructannot["annotation"] = _present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map)
            urlstructannot["relevance"] = _max_relevance_perurl(urlstructannot["annotation"])      
            if (len(result.annotation_ids) > 0):
                urlstructannot["typeFilter"] = _getfiltertype(request.authenticated_userid,urlstructannot["annotation"])
                urlstructannot["allstackslist"]=allstacklist
                urllist.append(urlstructannot)
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
            urlstructannot["annotation"] = _present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map)
            urlstructannot["relevance"] = _max_relevance_perurl(urlstructannot["annotation"])
            if (len(result.annotation_ids) > 0):
                urlstructannot["typeFilter"] = _getfiltertype(request.authenticated_userid,urlstructannot["annotation"])
                urlstructannot["allstackslist"]=allstacklist
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
        'annotations': _sort_annotations(_present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map))
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
        'annotations': _present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map)
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


@api_config(route_name='api.sharedannotation',
            request_method='DELETE',
            permission='delete')
def shareddelete(annotation, request):
    """Delete the specified annotation."""
    uri = storage.update_shareduri(request.db, annotation)
    storage.delete_sharedannotation(request.db, annotation.id)
    storage.delete_sharing(request.db, annotation.sharingid)
    # N.B. We publish the original model (including all the original annotation
    # fields) so that queue subscribers have context needed to decide how to
    # process the delete event. For example, the streamer needs to know the
    # target URLs of the deleted annotation in order to know which clients to
    # forward the delete event to.
    _publish_annotation_event(
        request,
        annotation,
        'shareddelete')

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

@api_config(route_name='api.sharedurl',
            request_method='DELETE',
            permission='delete')
def sharedurldelete(url, request):
    """Delete the specified annotation."""
    params=MultiDict([(u'uri_id', url.id)])
    print params
    result = search_lib.Sharedsearch(request) \
        .run(params)
    out = {
            'total': result.total,
            'rows': _present_sharedannotations_withscore(request, result.annotation_ids,result.annotation_ids_map)
        }

    for item in out["rows"]:
        print item
        print item["id"]
        storage.delete_sharedannotation(request.db, item["id"])
        storage.delete_sharing(request.db, item["sharingid"])
        event = AnnotationEvent(request, item["id"], 'shareddelete', item)
        request.notify_after_commit(event)
    storage.delete_sharedurl(request.db, url.id)

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

def _present_sharedannotations(request, uri_id):

    annotations = storage.fetch_ordered_sharedannotations(request.db, uri_id)
    links_service = request.find_service(name='links')
    return [AnnotationSharedJSONPresenter(ann, links_service).asdict()
            for ann in annotations]


def _present_annotations_withscore(request, ids, ids_map):
    """Load annotations by id from the database and present them along with their scores obtained from search"""
    def eager_load_documents(query):
        return query.options(
            subqueryload(models.Annotation.document))

    annotations = storage.fetch_ordered_annotations(request.db, ids,
                                                    query_processor=eager_load_documents)
    links_service = request.find_service(name='links')
    return [AnnotationJSONPresenter(ann, links_service).asdict(ids_map)
            for ann in annotations]

def _present_sharedannotations_withscore(request, ids, ids_map):
    """Load annotations by id from the database and present them along with their scores obtained from search"""

    annotations = storage.fetch_sharedordered_annotations(request.db, ids)
    links_service = request.find_service(name='links')
    return [AnnotationSharedJSONPresenter(ann, links_service).asdict(ids_map)
            for ann in annotations]


def _max_relevance_perurl(annotationlist):
    max_score=0.0
    for item in annotationlist:
         max_score=max(max_score,item['relevance'])
    return max_score
            
def _sort_annotations_old(annotationlist):
    returnedannotationlist =[]
    unsorted=[]
    sortedval=[]
    for item in annotationlist:
        print item
        if not('selector'  in item["target"][0]) or len(item["target"][0]["selector"]) < 2:
            print "+++ this is a video annotated url+++"
            unsortedat={}
            print ('viddata' in item)
            if ('viddata' in item):
                unsortedat["id"]=item["id"]
                unsortedat["start"]=float(item["viddata"][0]["starttime"])
            elif ('auddata' in item):
                unsortedat["id"]=item["id"]
                unsortedat["start"]=float(item["auddata"][0]["starttime"])
            else:
                unsortedat["id"]=item["id"]
                unsortedat["start"] = 0
        else: 
            unsortedat={}
            print "+++ this is a text annotated url+++"
            for selectors in item["target"][0]["selector"]:
                if selectors["type"]=="TextPositionSelector":
                    unsortedat["id"]=item["id"]
                    unsortedat["start"]=selectors["start"]
                else:
                    unsortedat["id"] = item["id"]
                    unsortedat["start"]=0
               
        unsorted.append(unsortedat)
    print unsorted
    sortedval = sorted(unsorted, key=lambda k: k['start'])
    print sortedval
    for item in sortedval:
        for item1 in annotationlist:
            if (item1["id"] == item["id"]):
                returnedannotationlist.append(item1)    
    return returnedannotationlist


def _sort_annotations(annotationlist):
    returnedannotationlist =[]
    unsorted=[]
    sortedval=[]
    for item in annotationlist:
        print item
        unsortedat={}
        unsortedat["id"] = item["id"]
        unsortedat["start"]=0
        if ('viddata' in item):
            print "+++ this is a video annotated url+++"
            unsortedat["id"]=item["id"]
            unsortedat["start"]=float(item["viddata"][0]["starttime"])
        elif ('auddata' in item):
            print "+++ this is an audio annotated url+++"
            unsortedat["id"]=item["id"]
            unsortedat["start"]=float(item["auddata"][0]["starttime"])
        elif ('selector' in item["target"][0]): 
            for selectors in item["target"][0]["selector"]:
                if selectors["type"]=="TextPositionSelector":
                    print "+++ this is a text annotated url+++"
                    unsortedat["id"]=item["id"]
                    unsortedat["start"]=selectors["start"]
        else:
            unsortedat["id"] = item["id"]
            unsortedat["start"]=0
               
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
    print event.annotation_id
    print event.action
    request.notify_after_commit(event)

def _publish_stack_event(request,
                              stack_id,
                              action):
    """Publish an event to the stacks queue for this stack action."""
    stack_dict = None

    event = StackEvent(request, stack_id, action, stack_dict)
    print event.stack_id
    print event.action
    request.notify_after_commit(event)


def _renotedread_allannotations(urlid, request):
    """Return the annotation (simply how it was stored in the database)."""
    params=MultiDict([(u'uri_id', urlid)])
    print params
    result = search_lib.Search(request) \
        .run(params)

    out = {
        'total': result.total,
        'annotations': _sort_annotations(_present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map))
    }

    return out

def _renotedread_allsharedannotations(urlid, request):
    """Return the annotation (simply how it was stored in the database)."""
    params=MultiDict([(u'uri_id', urlid)])
    print params
    result = search_lib.Sharedsearch(request) \
        .run(params)

    out = {
        'total': result.total,
        'annotations': _sort_annotations(_present_sharedannotations_withscore(request, result.annotation_ids, result.annotation_ids_map))
    }

    return out

@api_config(route_name='api.sharings',
            request_method='GET',
            effective_principals=security.Authenticated)
def readsharedurls(request):
    """Get the list of annotated urls from the user."""
    params = request.params.copy()
    valueparams = request.params.copy()
    print ("+++ in urls params ++++")
    print params
    type = valueparams.pop('type','all')
    print type 
    print (type == 'all')
    urllist=[]
    retval={}
    allstacklist = _getallstacklist(request.authenticated_userid)
    if len(params) > 0 and type == 'all':
        print ("+++params is not none+++")
        result = search_lib.Sharedsearch(request) \
        .run(params)

        out = {
            'total': result.total,
            'rows': _sort_annotations(_present_sharedannotations_withscore(request, result.annotation_ids, result.annotation_ids_map))
        }
        print out["rows"]
        preexistingurl_id = []
        urlwiseannots={}
        for item in out["rows"]:
            searchurlid = item["uri_id"]
            urlsingledata = storage.fetch_sharedurl(request.db,searchurlid)
            urlstruct=SimpleSharedUrlJSONPresenter(urlsingledata)
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
                    item1["typeFilter"] = _getfiltertype(request.authenticated_userid,urlwiseannots[str(searchurlid)])
                    item1["allannotation"] = _renotedread_allsharedannotations(item1["id"],request)["annotations"]
                    item1["relevance"] = _max_relevance_perurl(item1["annotation"])
                    item1["allstackslist"]=allstacklist
        retval["total"] = len(urllist)
        retval["urllist"] = urllist
        return retval
    elif (type != 'all') and len(params) == 1:
        print ("+++params is  of type+++")
        urlsdata = storage.fetch_shared_urls(request.db,request.authenticated_userid)
        urllist=[]
        retval={}
        for item in urlsdata:
            params=MultiDict([(u'uri_id', item.id),(u'limit', 1),(u'type',type)])
            result = search_lib.Sharedsearch(request) \
            .run(params)
            urlstruct=SimpleSharedUrlJSONPresenter(item)
            urlstructannot = urlstruct.asdict()
            urlstructannot["allannotation"] = _renotedread_allsharedannotations(item.id,request)["annotations"]
            
            urlstructannot["annotation"] = _present_sharedannotations_withscore(request, result.annotation_ids, result.annotation_ids_map)
            urlstructannot["relevance"] = _max_relevance_perurl(urlstructannot["annotation"])      
            if (len(result.annotation_ids) > 0):
                urlstructannot["typeFilter"] = _getfiltertype(request.authenticated_userid,urlstructannot["annotation"])
                urlstructannot["allstackslist"]=allstacklist
                urllist.append(urlstructannot)
        retval["total"] = len(urllist)
        retval["urllist"] = urllist
        return retval
    else:
        retval = {}
        userid = request.authenticated_userid
        sharedpages = storage.fetch_shared_urls(request.db,userid)
        retval["total"] = len(sharedpages)
        retval["urllist"] = []
        for item in sharedpages:
            urlstruct=SimpleSharedUrlJSONPresenter(item)
            urlstruct_ret=urlstruct.asdict()
            urlstruct_ret["allannotation"] = _sort_annotations(_present_sharedannotations(request, item.id))
            urlstruct_ret["annotation"] = []
            if (len(urlstruct_ret["allannotation"])>0):
                urlstruct_ret["annotation"].append(urlstruct_ret["allannotation"][0])
                urlstruct_ret["typeFilter"] = _getfiltertype(request.authenticated_userid,urlstruct_ret["annotation"])
                urlstruct_ret["allstackslist"]=allstacklist
            retval["urllist"].append(urlstruct_ret)

        return retval    


@api_config(route_name='api.stacks',
            request_method='GET',
            effective_principals=security.Authenticated)
def readstackurls(request):
    """Get the list of annotated urls from the user."""
    params = request.params.copy()
    valueparams = request.params.copy()
    print ("+++ in urls params ++++")
    print params
    stackName = params.pop('stackName','')
    if stackName:
        print "++++we have a stackName+++++"
        print stackName
    else:
        print "we don't have a stackname"
    print params
    filtereduriids=_geturiidsbystackname(stackName,request)
    type = valueparams.pop('type','all')
    print type 
    print (type == 'all')
    urllist=[]
    retval={}
    if len(params) > 0 and type == 'all':
        print ("+++params is not none+++")
        result = search_lib.Search(request) \
        .run(params)

        out = {
            'total': result.total,
            'rows': _sort_annotations(_present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map))
        }
        print out["rows"]
        preexistingurl_id = []
        urlwiseannots={}
        for item in out["rows"]:
            if (item["uri_id"] in filtereduriids):
                searchurlid = item["uri_id"]
            
                urlsingledata = storage.fetch_url(request.db,searchurlid)
                urlstruct=SimpleUrlJSONPresenter(urlsingledata)
                if (searchurlid not in preexistingurl_id):
                    urlwiseannots[str(searchurlid)]=[]
                    urllist.append(urlstruct.asdict())
                    preexistingurl_id.append(searchurlid)
                urlwiseannots[str(searchurlid)].append(item)
                print urlwiseannots[searchurlid]
                print urllist
                for item1 in urllist:
                    if item1["id"] == searchurlid:
                        item1["annotation"] = urlwiseannots[str(searchurlid)]
                        item1["allannotation"] = _renotedread_allannotations(item1["id"],request)["annotations"]
                        item1["relevance"] = _max_relevance_perurl(item1["annotation"])
        retval["total"] = len(urllist)
        retval["urllist"] = urllist
        return retval
    elif (type != 'all') and len(params) == 1:
        print ("+++params is  of type+++")
        urlsdata = storage.fetch_urls(request.db,request.authenticated_userid)
        urllist=[]
        retval={}
        for item in urlsdata:
            if (item.id in filtereduriids):
                params=MultiDict([(u'uri_id', item.id),(u'limit', 1),(u'type',type)])
                result = search_lib.Search(request) \
                .run(params)
                urlstruct=SimpleUrlJSONPresenter(item)
                urlstructannot = urlstruct.asdict()
                urlstructannot["allannotation"] = _renotedread_allannotations(item.id,request)["annotations"]
            
                urlstructannot["annotation"] = _present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map)
                urlstructannot["relevance"] = _max_relevance_perurl(urlstructannot["annotation"])      
                if (len(result.annotation_ids) > 0):
                    urllist.append(urlstructannot)
        retval["total"] = len(urllist)
        retval["urllist"] = urllist
        return retval
    else:
        print ("+++params is  none+++")
        urlsdata = storage.fetch_urls(request.db,request.authenticated_userid)
        urllist=[]
        retval={}
        for item in urlsdata:
            if (item.id in filtereduriids):
                params=MultiDict([(u'uri_id', item.id),(u'limit', 1)])
                result = search_lib.Search(request) \
                .run(params)
                urlstruct=SimpleUrlJSONPresenter(item)
                urlstructannot = urlstruct.asdict()
                urlstructannot["allannotation"] = _renotedread_allannotations(item.id,request)["annotations"]
                urlstructannot["annotation"] = _present_annotations_withscore(request, result.annotation_ids, result.annotation_ids_map)
                urlstructannot["relevance"] = _max_relevance_perurl(urlstructannot["annotation"])
                if (len(result.annotation_ids) > 0):
                    urllist.append(urlstructannot)
        retval["total"] = len(urllist)
        retval["urllist"] = urllist
        return retval

def _getfiltertype(username,annotationlist):
    print "++++in get filter type++++"
    print annotationlist[0]["type"]
    retval = ["all"]
    if ('audio' in annotationlist[0]["type"]):
        retval.append("audio")
    elif ('video' in annotationlist[0]["type"]):
        retval.append("video")
    else:
        retval.append("text")
    uri = annotationlist[0]["uri"]
    stackval = _getstacklist(username,uri,retval)
    return stackval


def _getstacklist(username,uri,retval):
    
    retval.append("serversideaddedstack")
    db=get_db()
    mongostackentries = db.urlstack.find({"user":username,"uri_id":uri})
    for item in mongostackentries:
        print "++++++++uri contains stack entries++++++"
        for item1 in item["stacks"]:
            retval.append(item1)
    return retval

def _getallstacklist(username):
    db = get_db()
    retval = []
    userstackentries = db.userstack.find({"user":username})
    for item in userstackentries:
        retval = item["allstacks"]
    return retval
def _createannotationwisesharing(item,sharedtoemail,sharedpageid,request):
    data= {}
    data["sharedtousername"] = _getsharedtouser(request,sharedtoemail)[0].username
    data["sharedtoemail"] = sharedtoemail
    data["sharedbyuserid"] = request.authenticated_userid
    data["annotationid"] = item
    data["uri_id"] = sharedpageid
    sharing = storage.create_sharing(request, data)
    sharedannotation = _createsharedannotationentry(item,sharedtoemail,sharedpageid,sharing.id,request)
    if (sharedannotation.id):
        presenter = SimpleSharingJSONPresenter(sharing)
        return presenter.asdict()
    else:
        return "failure"

def _sharedpage(item,sharedtoemail,request):
    data={}
    sharedtouser = _getsharedtouser(request,sharedtoemail)
    sharedtousername = sharedtouser[0].username
    sharedtoauthority = sharedtouser[0].authority
    data["userid"] = "acct:"+sharedtousername+"@"+sharedtoauthority
    annotation = _getannotation(request, item)
    data["title"] = _getmainuri(request,annotation.target_uri)[0].title
    urischema=schemas.CreateSharedURI(request)
    uriappstruct = urischema.validate(data,annotation)
    shareduri = storage.create_shareduri(request, uriappstruct)
    return shareduri

def _getannotation(request, annotationid):
    annotation = storage.fetch_annotation(request.db, annotationid)
    if annotation is None:
        raise KeyError()
    return annotation

def _getsharedtouser(request,sharedtoemail):
    user = storage.get_user_by_email(request.db,sharedtoemail)
    return user

def _getmainuri(request,target_uri):
    sharedbyuserid = request.authenticated_userid
    mainuri = storage.fetch_title_by_uriaddress(target_uri,sharedbyuserid,request.db)
    return mainuri


def _createsharedannotationentry(item,sharedtoemail,sharedpageid,sharingid,request):
    data = {}
    sharedtouser = _getsharedtouser(request,sharedtoemail)
    sharedtousername = sharedtouser[0].username
    sharedtoauthority = sharedtouser[0].authority
    data["userid"] = "acct:"+sharedtousername+"@"+sharedtoauthority
    data["sharedbyuserid"] = request.authenticated_userid
    data["uri_id"] = sharedpageid
    annotation = _getannotation(request, item)
    data["title"] = _getmainuri(request,annotation.target_uri)[0].title
    data["sharingid"] = sharingid
    if ('viddata' in annotation.extra):
        data["type"] = 'video'
    elif ('auddata' in annotation.extra):
        data["type"] = 'audio'
    else:
        data["type"] = 'text'
    data["text"] = annotation.text
    data["text_rendered"] = annotation.text_rendered
    data["tags"] = annotation.tags
    data["target_selectors"] = annotation.target_selectors
    data["target_uri"] = annotation.target_uri
    data["target_uri_normalized"] =annotation.target_uri_normalized
    data["extra"] = annotation.extra
    print data
    sharedannotation = storage.create_sharedannotation(request, data)
    _publish_annotation_event(request, sharedannotation, 'sharedcreate')
    return sharedannotation



def _geturiidsbystackname(stack,request):
    retval = []
    db = get_db()
    mongovalues = db.urlstack.find({"user":request.authenticated_userid,"stacks":stack})
    for item in mongovalues:
        print item["uri_id"]
        sqlurientry = _getmainuri(request,item["uri_id"])
        if len(sqlurientry) > 0:
            retval.append(sqlurientry[0].id)
    print retval
    return retval
  
def get_db():
    client = MongoClient('0.0.0.0:27017')
    db = client.renoted
    return db


def get_db_client():
    client = MongoClient('0.0.0.0:27017')
    return client

#######################OnTopService###################################
@api_config(route_name='api.ontop.archive',
            request_method='POST',
            effective_principals=security.Authenticated)
def onTopArchive(request):
    value=(_json_payload(request))
    if "stacks" in value:
        print (value["stacks"])    
        db_stacks = get_db_client().stackservice
        for stack in value["stacks"]:
            count = db_stacks.stackdetails.find( { "user": request.authenticated_userid, "stackname": stack}).count()
            if count > 0:
                db_stacks.stackdetails.update( { "user": request.authenticated_userid, "stackname": stack},{'$set':{"archived": True, "updated":datetime.datetime.utcnow()}})
                stackdata= db_stacks.stackdetails.find( { "user": request.authenticated_userid, "stackname": stack})
               
                stack_id= convert_uuid_to_urlsafe(stackdata[0]["stack_id"])
                _publish_stack_event(request,stack_id,"stackarchive")
                db=get_db()
                db.userstack.update({"user": request.authenticated_userid},{'$pull':{"allstacks" : stack}})
            else:
                stack_id = create_uuid()
                db_stacks.stackdetails.insert( { "user": request.authenticated_userid, "stackname": stack, "stack_id":stack_id,"archived":False, "deleted": False, "created":datetime.datetime.utcnow(),"updated":datetime.datetime.utcnow(),"deletedat":""})
                db_stacks.stackdetails.update( { "user": request.authenticated_userid, "stackname": stack},{'$set':{"archived": True, "updated":datetime.datetime.utcnow()}})
                stackdata= db_stacks.stackdetails.find( { "user": request.authenticated_userid, "stackname": stack})

                stack_id= convert_uuid_to_urlsafe(stackdata[0]["stack_id"])
                _publish_stack_event(request,stack_id,"stackarchive")
                db=get_db()
                db.userstack.update({"user": request.authenticated_userid},{'$pull':{"allstacks" : stack}})         
        return "success in on top archive service"

    
    elif "annotations" in value:
        print (value["annotations"])
        return "success in on top archive service"
    else:
        return "Please provide an array of stacks or annotations to be archived."

@api_config(route_name='api.ontop.dearchive',
            request_method='POST',
            effective_principals=security.Authenticated)
def onTopDearchive(request):
    value=(_json_payload(request))
    if "stacks" in value:
        print (value["stacks"])
        db_stacks = get_db_client().stackservice
        for stack in value["stacks"]:
            count = db_stacks.stackdetails.find( { "user": request.authenticated_userid, "stackname": stack}).count()
            if count > 0:
                db_stacks.stackdetails.update( { "user": request.authenticated_userid, "stackname": stack},{'$set':{"archived": False, "updated":datetime.datetime.utcnow()}})
                stackdata= db_stacks.stackdetails.find( { "user": request.authenticated_userid, "stackname": stack})

                stack_id= convert_uuid_to_urlsafe(stackdata[0]["stack_id"])
                _publish_stack_event(request,stack_id,"stackdearchive")
                db=get_db()
                db.userstack.update({"user": request.authenticated_userid},{'$push':{"allstacks" : stack}})
            else:
                stack_id = create_uuid()
                db_stacks.stackdetails.insert( { "user": request.authenticated_userid, "stackname": stack, "stack_id":stack_id,"archived":False, "deleted": False, "created":datetime.datetime.utcnow(),"updated":datetime.datetime.utcnow(),"deletedat":""})
                db_stacks.stackdetails.update( { "user": request.authenticated_userid, "stackname": stack},{'$set':{"archived": False, "updated":datetime.datetime.utcnow()}})
                stackdata= db_stacks.stackdetails.find( { "user": request.authenticated_userid, "stackname": stack})

                stack_id= convert_uuid_to_urlsafe(stackdata[0]["stack_id"])
                _publish_stack_event(request,stack_id,"stackdearchive")
                db=get_db()
                db.userstack.update({"user": request.authenticated_userid},{'$push':{"allstacks" : stack}})
        return "success in on top Dearchive service"


    elif "annotations" in value:
        print (value["annotations"])
        return "success in on top Dearchive service"
    else:
        return "Please provide an array of stacks or annotations to be dearchived."


@api_config(route_name='api.ontop.delete',
            request_method='POST',
            effective_principals=security.Authenticated)
def onTopDelete(request):
    
    return "success in on top delete service"


######################StacksService##########################
@api_config(route_name='api.stackservice.read',
            request_method='GET',
            effective_principals=security.Authenticated)
def onStackServiceRead(request):
    db_stacks = get_db_client().stackservice
    toret = {}
    toretstacklist = []
    stackdata= db_stacks.stackdetails.find( { "user": request.authenticated_userid})
    for item in stackdata:
        toretstackwise={}
        toretstackwise["name"]=item["stackname"]
        toretstackwise["archived"] = item["archived"]
        toretstacklist.append(toretstackwise)
    toret["stacks"] = toretstacklist
    toret["total"] = len(toretstacklist)         
    return toret


def create_uuid():
    value= uuid.uuid4()
    return value

def convert_uuid_to_urlsafe(value):
    encoded= base64.urlsafe_b64encode(value.bytes)[0:22]
    return encoded

def convert_urlsafe_to_uuid(urlsafe):
    decoded = base64.urlsafe_b64decode(urlsafe+"==")
    return  uuid.UUID(bytes=decoded)


def includeme(config):
    config.scan(__name__)
