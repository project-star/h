# -*- coding: utf-8 -*-
"""
Annotation storage API.

This module provides the core API with access to basic persistence functions
for storing and retrieving annotations. Data passed to these functions is
assumed to be validated.
"""

from datetime import datetime

from pyramid import i18n
from memex import schemas
from memex import models
from h import models as hmod
from memex.db import types
from memex.events import AnnotationEvent
from memex.presenters import AnnotationJSONPresenter
_ = i18n.TranslationStringFactory(__package__)
import time

def fetch_annotation(session, id_):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    try:
        val = session.query(models.Annotation).get(id_)
        print val
        return session.query(models.Annotation).get(id_)
    except types.InvalidUUID:
        return None

def fetch_url(session, id_):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    try:
        val = session.query(hmod.Page).get(id_)
        print val
        return session.query(hmod.Page).get(id_)
    except types.InvalidUUID:
        return None
def fetch_sharedannotation(session, id_):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    try:
        val = session.query(hmod.Sharedannotation).get(id_)
        print val
        return session.query(hmod.Sharedannotation).get(id_)
    except types.InvalidUUID:
        return None
def fetch_sharedurl(session, id_):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    print "++++++++in fetch_url function+++++   "
    val = session.query(hmod.Sharedpage).get(id_)
    print val
    return session.query(hmod.Sharedpage).get(id_)

def fetch_urls(session,userid):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    print "++++++++in fetch_url function+++++   "
    val = session.query(hmod.Page).filter(hmod.Page.userid==userid).all()
    print val
    return val


def fetch_allsharedannotations(session):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    try:
        val = session.query(hmod.Sharedannotation).all()
        print val
        return session.query(hmod.Sharedannotation).all()
    except types.InvalidUUID:
        return None

def fetch_uri(session, uriaddress, userid, isbookmark):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    try:
        return session.query(hmod.Page).filter(hmod.Page.uriaddress==uriaddress).filter(hmod.Page.userid==userid).filter(hmod.Page.isbookmark==isbookmark)
    except types.InvalidUUID:
        return None
def fetch_uri_id(request,data):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
 
    """
    uriaddress=data["url"]
    userid=request.authenticated_userid
    try:
        val = request.db.query(hmod.Page).filter(hmod.Page.uriaddress==uriaddress).filter(hmod.Page.userid==userid)
        
        return val
    except types.InvalidUUID:
        return None

def fetch_ordered_annotations(session, ids, query_processor=None):
    """
    Fetch all annotations with the given ids and order them based on the list
    of ids.

    The optional `query_processor` parameter allows for passing in a function
    that can change the query before it is run, especially useful for
    eager-loading certain data. The function will get the query as an argument
    and has to return a query object again.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param ids: the list of annotation ids
    :type ids: list

    :param query_processor: an optional function that takes the query and
                            returns an updated query
    :type query_processor: callable

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    if not ids:
        return []

    ordering = {x: i for i, x in enumerate(ids)}

    query = session.query(models.Annotation).filter(models.Annotation.id.in_(ids))
    if query_processor:
        query = query_processor(query)

    anns = sorted(query, key=lambda a: ordering.get(a.id))
    return anns

def fetch_sharedordered_annotations(session, ids):
    """
    Fetch all annotations with the given ids and order them based on the list
    of ids.

    The optional `query_processor` parameter allows for passing in a function
    that can change the query before it is run, especially useful for
    eager-loading certain data. The function will get the query as an argument
    and has to return a query object again.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param ids: the list of annotation ids
    :type ids: list

    :param query_processor: an optional function that takes the query and
                            returns an updated query
    :type query_processor: callable

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    if not ids:
        return []

    ordering = {x: i for i, x in enumerate(ids)}

    query = session.query(hmod.Sharedannotation).filter(hmod.Sharedannotation.id.in_(ids))

    anns = sorted(query, key=lambda a: ordering.get(a.id))
    return anns

def fetch_ordered_sharedannotations(session, uri_id):
    """
    Fetch all annotations with the given ids and order them based on the list
    of ids.

    The optional `query_processor` parameter allows for passing in a function
    that can change the query before it is run, especially useful for
    eager-loading certain data. The function will get the query as an argument
    and has to return a query object again.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param ids: the list of annotation ids
    :type ids: list

    :param query_processor: an optional function that takes the query and
                            returns an updated query
    :type query_processor: callable

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """


    query = session.query(hmod.Sharedannotation).filter(hmod.Sharedannotation.uri_id==uri_id).all()
    return query
   

def create_uri(request, data):
    """
    Create an annotation from passed data.

    :param request: the request object
    :type request: pyramid.request.Request

    :param data: a dictionary of annotation properties
    :type data: dict

    :returns: the created annotation
    :rtype: dict
    """
    print data["userid"]
    print data["uriaddress"]
    count= request.db.query(hmod.Page).filter(hmod.Page.uriaddress==data["uriaddress"]).filter(hmod.Page.userid==data["userid"]).filter(hmod.Page.isbookmark==data["isbookmark"]).count()
    print count

    page = hmod.Page(**data)
    if (count < 1):
        request.db.add(page)
    else:
        request.db.query(hmod.Page).filter(hmod.Page.uriaddress==data["uriaddress"]).filter(hmod.Page.userid==data["userid"]).filter(hmod.Page.isbookmark==data["isbookmark"]).update({hmod.Page.updated:datetime.utcnow()})

    # We need to flush the db here so that annotation.created and
    # annotation.updated get created.
    request.db.flush()


    return page

def create_shareduri(request, data):
    """
    Create an annotation from passed data.

    :param request: the request object
    :type request: pyramid.request.Request

    :param data: a dictionary of annotation properties
    :type data: dict

    :returns: the created annotation
    :rtype: dict
    """
    print data["userid"]
    print data["uriaddress"]
    count= request.db.query(hmod.Sharedpage).filter(hmod.Sharedpage.uriaddress==data["uriaddress"]).filter(hmod.Sharedpage.userid==data["userid"]).count()
    print count

    sharedpage = hmod.Sharedpage(**data)
    if (count < 1):
        request.db.add(sharedpage)
    else:
        request.db.query(hmod.Sharedpage).filter(hmod.Sharedpage.uriaddress==data["uriaddress"]).filter(hmod.Sharedpage.userid==data["userid"]).update({hmod.Sharedpage.updated:datetime.utcnow()})
        sharedpage = request.db.query(hmod.Sharedpage).filter(hmod.Sharedpage.uriaddress==data["uriaddress"]).filter(hmod.Sharedpage.userid==data["userid"]).all()[0]
    # We need to flush the db here so that annotation.created and
    # annotation.updated get created.
    request.db.flush()


    return sharedpage

def create_sharing(request, data):
    """
    Create an annotation from passed data.

    :param request: the request object
    :type request: pyramid.request.Request

    :param data: a dictionary of annotation properties
    :type data: dict

    :returns: the created annotation
    :rtype: dict
    """
    count= request.db.query(hmod.Sharing).filter(hmod.Sharing.sharedtoemail==data["sharedtoemail"]).filter(hmod.Sharing.annotationid==data["annotationid"]).count()
    print count

    sharing = hmod.Sharing(**data)
    if (count < 1):
        request.db.add(sharing)
    else:
        request.db.query(hmod.Sharing).filter(hmod.Sharing.sharedtoemail==data["sharedtoemail"]).filter(hmod.Sharing.annotationid==data["annotationid"]).update({hmod.Sharing.updated:datetime.utcnow()})
        sharing = request.db.query(hmod.Sharing).filter(hmod.Sharing.sharedtoemail==data["sharedtoemail"]).filter(hmod.Sharing.annotationid==data["annotationid"]).all()[0]

    # We need to flush the db here so that annotation.created and
    # annotation.updated get created.
    request.db.flush()
    return sharing


def create_sharedannotation(request, data):
    """
    Create an annotation from passed data.

    :param request: the request object
    :type request: pyramid.request.Request

    :param data: a dictionary of annotation properties
    :type data: dict

    :returns: the created annotation
    :rtype: dict
    """
    count= request.db.query(hmod.Sharedannotation).filter(hmod.Sharedannotation.sharingid==data["sharingid"]).count()
    print count

    sharedannotation = hmod.Sharedannotation(**data)
    if (count < 1):
        request.db.add(sharedannotation)
    else:
        sharedannotation=request.db.query(hmod.Sharedannotation).filter(hmod.Sharedannotation.sharingid==data["sharingid"]).all()[0]
        sharedannotation.updated = datetime.utcnow()
        for key, value in data.items():
            setattr(sharedannotation, key, value)
        
    # We need to flush the db here so that annotation.created and
    # annotation.updated get created.
    request.db.flush()
    return sharedannotation

def create_annotation(request, data):
    """
    Create an annotation from passed data.

    :param request: the request object
    :type request: pyramid.request.Request

    :param data: a dictionary of annotation properties
    :type data: dict

    :returns: the created annotation
    :rtype: dict
    """
    document_uri_dicts = data['document']['document_uri_dicts']
    document_meta_dicts = data['document']['document_meta_dicts']
    del data['document']

    # Replies must have the same group as their parent.
    if data['references']:
        top_level_annotation_id = data['references'][0]
        top_level_annotation = fetch_annotation(request.db,
                                                top_level_annotation_id)
        if top_level_annotation:
            data['groupid'] = top_level_annotation.groupid
        else:
            raise schemas.ValidationError(
                'references.0: ' +
                _('Annotation {id} does not exist').format(
                    id=top_level_annotation_id)
            )

    # The user must have permission to create an annotation in the group
    # they've asked to create one in.
    if data['groupid'] != '__world__':
        group_principal = 'group:{}'.format(data['groupid'])
        if group_principal not in request.effective_principals:
            raise schemas.ValidationError('group: ' +
                                          _('You may not create annotations '
                                            'in groups you are not a member '
                                            'of!'))
    print data["target_uri"] 
    print data["userid"]
    uri = fetch_uri(request.db, data["target_uri"], data["userid"], "False")
    print uri[0].uriaddress
    data["extra"]["uri_id"] = uri[0].id
    annotation = models.Annotation(**data)
    val = request.db.query(models.Annotation).get(uri[0].id)
    #if val is None:
    #    print "++++adding fake annotation+++++"
    #    fake_annotation=create_fake_annotation(request,data,document_meta_dicts, document_uri_dicts)
    #    time.sleep(1)
    #    print fake_annotation
    #    print "+++++ending fake annotation++++"
    # We need to flush the db here so that annotation.created and
    # annotation.updated get created.
    request.db.add(annotation)
    request.db.flush()

    models.update_document_metadata(
        request.db, annotation, document_meta_dicts, document_uri_dicts)

    return annotation
def create_fake_annotation(request, data,document_meta_dicts, document_uri_dicts):
    """
    Create an annotation from passed data.

    :param request: the request object
    :type request: pyramid.request.Request

    :param data: a dictionary of annotation properties
    :type data: dict

    :returns: the created annotation
    :rtype: dict
    """
    print data["target_uri"] 
    print data["userid"]
    uri = fetch_uri(request.db, data["target_uri"], data["userid"], "False")
    print uri[0].uriaddress
    data["extra"]["uri_id"] = uri[0].id
    data["id"]=uri[0].id
    data['text'] = u''
    data['tags'] = []
    data['groupid'] = u'__world__'
    data['target_selectors']=[]
    annotation = models.Annotation(**data)
    request.db.add(annotation)      
    # We need to flush the db here so that annotation.created and
    # annotation.updated get created.
    request.db.flush()

    models.update_document_metadata(
        request.db, annotation, document_meta_dicts, document_uri_dicts)
    _publish_annotation_event(request, annotation, 'create')
    _publish_annotation_event(request, annotation, 'update')
    return annotation

def update_annotation(session, id_, data):
    """
    Update an existing annotation and its associated document metadata.

    Update the annotation identified by id_ with the given
    data. Create, delete and update document metadata as appropriate.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the ID of the annotation to be updated, this is assumed to be a
        validated ID of an annotation that does already exist in the database
    :type id_: string

    :param data: the validated data with which to update the annotation
    :type data: dict

    :returns: the updated annotation
    :rtype: memex.models.Annotation

    """
    # Remove any 'document' field first so that we don't try to save it on the
    # annotation object.
    document = data.pop('document', None)
    annotation = session.query(models.Annotation).get(id_)
    annotation.updated = datetime.utcnow()

    annotation.extra.update(data.pop('extra', {}))

    for key, value in data.items():
        setattr(annotation, key, value)

    if document:
        document_uri_dicts = document['document_uri_dicts']
        document_meta_dicts = document['document_meta_dicts']
        models.update_document_metadata(
            session, annotation, document_meta_dicts, document_uri_dicts)

    return annotation


def update_uri(session, annotation):
    """
    Update an existing annotation and its associated document metadata.

    Update the annotation identified by id_ with the given
    data. Create, delete and update document metadata as appropriate.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the ID of the annotation to be updated, this is assumed to be a
        validated ID of an annotation that does already exist in the database
    :type id_: string

    :param data: the validated data with which to update the annotation
    :type data: dict

    :returns: the updated annotation
    :rtype: memex.models.Annotation

    """
    # Remove any 'document' field first so that we don't try to save it on the
    # annotation object.
    print "+++ in update_uri +++"
    print annotation.extra
    id_ = annotation.extra['uri_id']
    session.query(hmod.Page).filter_by(id=id_).update({hmod.Page.updated:datetime.utcnow()})
    session.flush()
    return "success"

def update_shareduri(session, sharedannotation):
    """
    Update an existing annotation and its associated document metadata.

    Update the annotation identified by id_ with the given
    data. Create, delete and update document metadata as appropriate.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the ID of the annotation to be updated, this is assumed to be a
        validated ID of an annotation that does already exist in the database
    :type id_: string

    :param data: the validated data with which to update the annotation
    :type data: dict

    :returns: the updated annotation
    :rtype: memex.models.Annotation

    """
    # Remove any 'document' field first so that we don't try to save it on the
    # annotation object.
    print "+++ in update_uri +++"
    id_ = sharedannotation.uri_id
    session.query(hmod.Sharedpage).filter_by(id=id_).update({hmod.Sharedpage.updated:datetime.utcnow()})
    session.flush()
    return "success"

def update_URL(session, id_, data):
    """
    Update an existing annotation and its associated document metadata.

    Update the annotation identified by id_ with the given
    data. Create, delete and update document metadata as appropriate.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the ID of the annotation to be updated, this is assumed to be a
        validated ID of an annotation that does already exist in the database
    :type id_: string

    :param data: the validated data with which to update the annotation
    :type data: dict

    :returns: the updated annotation
    :rtype: memex.models.Annotation

    """
    # Remove any 'document' field first so that we don't try to save it on the
    # annotation object.
    url = session.query(hmod.Page).get(id_)
    url.updated = datetime.utcnow()


    for key, value in data.items():
        setattr(url, key, value)
    return url

def update_SharedURL(session, id_, data):
    """
    Update an existing annotation and its associated document metadata.

    Update the annotation identified by id_ with the given
    data. Create, delete and update document metadata as appropriate.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the ID of the annotation to be updated, this is assumed to be a
        validated ID of an annotation that does already exist in the database
    :type id_: string

    :param data: the validated data with which to update the annotation
    :type data: dict

    :returns: the updated annotation
    :rtype: memex.models.Annotation

    """
    # Remove any 'document' field first so that we don't try to save it on the
    # annotation object.
    url = session.query(hmod.Sharedpage).get(id_)
    url.updated = datetime.utcnow()


    for key, value in data.items():
        setattr(url, key, value)
    return url



def delete_annotation(session, id_):
    """
    Delete the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str
    """
    session.query(models.Annotation).filter_by(id=id_).delete()

def delete_sharedannotation(session, id_):
    """
    Delete the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str
    """
    session.query(hmod.Sharedannotation).filter_by(id=id_).delete()

def delete_url(session, id_):
    """
    Delete the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str
    """
    session.query(hmod.Page).filter_by(id=id_).delete()


def delete_sharedurl(session, id_):
    """
    Delete the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str
    """
    session.query(hmod.Sharedpage).filter_by(id=id_).delete()

def delete_sharing(session, id_):
    """
    Delete the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str
    """
    session.query(hmod.Sharing).filter_by(id=id_).delete()

def fetch_shared_urls(session,userid):
    """
    Fetch the annotation with the given id.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param id_: the annotation ID
    :type id_: str

    :returns: the annotation, if found, or None.
    :rtype: memex.models.Annotation, NoneType
    """
    print "++++++++in fetch_url function+++++   "
    val = session.query(hmod.Sharedpage).filter(hmod.Sharedpage.userid==userid).all()
    print val
    return val


def get_user_by_email(session,email):
    val = session.query(hmod.User).filter(hmod.User.email==email).all()
    print val
    return val
def get_user_by_username(session,username):
    val = session.query(hmod.User).filter(hmod.User.username==username).all()
    print val
    return val


def fetch_title_by_uriaddress(target_uri,userid,session):
    val = session.query(hmod.Page).filter(hmod.Page.uriaddress==target_uri).filter(hmod.Page.userid==userid).all()
    return val

def fetch_title_by_shareduriaddress(target_uri,userid,session):
    val = session.query(hmod.Sharedpage).filter(hmod.Sharedpage.uriaddress==target_uri).filter(hmod.Sharedpage.userid==userid).all()
    return val

def expand_uri(session, uri):
    """
    Return all URIs which refer to the same underlying document as `uri`.

    This function determines whether we already have "document" records for the
    passed URI, and if so returns the set of all URIs which we currently
    believe refer to the same document.

    :param session: the database session
    :type session: sqlalchemy.orm.session.Session

    :param uri: a URI associated with the document
    :type uri: str

    :returns: a list of equivalent URIs
    :rtype: list
    """
    doc = models.Document.find_by_uris(session, [uri]).one_or_none()

    if doc is None:
        return [uri]

    # We check if the match was a "canonical" link. If so, all annotations
    # created on that page are guaranteed to have that as their target.source
    # field, so we don't need to expand to other URIs and risk false positives.
    docuris = doc.document_uris
    for docuri in docuris:
        if docuri.uri == uri and docuri.type == 'rel-canonical':
            return [uri]

    return [docuri.uri for docuri in docuris]

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
