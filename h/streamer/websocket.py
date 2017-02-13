# -*- coding: utf-8 -*-

from collections import namedtuple
import json
import logging
import weakref

from gevent.queue import Full
import jsonschema
from ws4py.websocket import WebSocket as _WebSocket

from memex import storage
from h.streamer import filter

log = logging.getLogger(__name__)

# An incoming message from a WebSocket client.
Message = namedtuple('Message', ['socket', 'payload','user'])


class WebSocket(_WebSocket):
    # All instances of WebSocket, allowing us to iterate over open websockets
    instances = weakref.WeakSet()
    origins = []

    # Instance attributes
    client_id = None
    filter = None
    query = None

    def __init__(self, sock, protocols=None, extensions=None, environ=None):
        super(WebSocket, self).__init__(sock,
                                        protocols=protocols,
                                        extensions=extensions,
                                        environ=environ,
                                        heartbeat_freq=30.0)

        self.authenticated_userid = environ['h.ws.authenticated_userid']
        self.effective_principals = environ['h.ws.effective_principals']
        self.registry = environ['h.ws.registry']
        print "++++in wesocket before figuring userid++++"
        print self.authenticated_userid

        self._work_queue = environ['h.ws.streamer_work_queue']

    def __new__(cls, *args, **kwargs):
        instance = super(WebSocket, cls).__new__(cls, *args, **kwargs)
        cls.instances.add(instance)
        return instance

    def received_message(self, msg):
        print "++++msg++++"
        print msg
        print self.authenticated_userid
        try:
            self._work_queue.put(Message(socket=self, payload=msg.data,user=self.authenticated_userid),
                                 timeout=0.1)
        except Full:
            log.warn('Streamer work queue full! Unable to queue message from '
                     'WebSocket client having waited 0.1s: giving up.')

    def closed(self, code, reason=None):
        try:
            self.instances.remove(self)
        except KeyError:
            pass

    def send_json(self, payload):
        if not self.terminated:
            self.send(json.dumps(payload))


def handle_message(message, session=None):
    """
    Handle an incoming message from a client websocket.

    Receives a :py:class:`~h.streamer.websocket.Message` instance, which holds
    references to the :py:class:`~h.streamer.websocket.WebSocket` instance
    associated with the client connection, as well as the message payload.

    It updates state on the :py:class:`~h.streamer.websocket.WebSocket`
    instance in response to the message content.

    It may also passed a database session which *must* be used for any
    communication with the database.
    """
    socket = message.socket
    user = message.user
    data = json.loads(message.payload)
    print "+++++in streamer websocket ++++ message received++++"
    print session
    print data
    print user
   # socket.send("true12345")
    try:
        msg_type = data.get('messageType', 'filter')
        print msg_type
        if msg_type == 'filter':
            payload = data['filter']

            # Let's try to validate the schema
            jsonschema.validate(payload, filter.SCHEMA)

            if session is not None:
                # Add backend expands for clauses
                _expand_clauses(session, payload)

            socket.filter = filter.FilterHandler(payload)
        elif msg_type == 'client_id':
            socket.client_id = data.get('value')
        elif msg_type == 'metrics_data':
            user = message.user
            event = data.get("eventName")
            _send_notification(socket,user)
            _update_metricsdb(session,user,event)
            print event
        elif msg_type == 'notification_update':
            user = message.user
            event = data.get("eventName")
            if event == "sharingNotified":
                _update_notification(socket,user,"sharing")
            _update_metricsdb(session,user,event)
    except:
        # TODO: clean this up, catch specific errors, narrow the scope
        log.exception("Parsing filter: %s", data)
        socket.close()
        raise


def _expand_clauses(session, payload):
    for clause in payload['clauses']:
        if clause['field'] == '/uri':
            _expand_uris(session, clause)


def _expand_uris(session, clause):
    uris = clause['value']
    expanded = set()

    if not isinstance(uris, list):
        uris = [uris]

    for item in uris:
        expanded.update(storage.expand_uri(session, item))

    clause['value'] = list(expanded)

def _update_metricsdb(session,user,event):
    if user is not None:
        storage.updatemetrics(session,user,event)


def _send_notification(socket,user):
    msg = {}
    entries=storage.get_notification(user)
    msg["purpose"] = "notification"
    for items in entries:
        print "++++while retrieving the notification entries++++"
        print items
        if items["notificationName"] == "sharing":
            msg["type"]="sharing"
            msg["shareCount"] = items["sharecount"]
            msg["value"] = "You have " + str(items["sharecount"]) + " unread ReNotes in sharing tab. Visit https://renoted.com/shared for further info"
            socket.send_json(msg)
    if (entries.count() == 0):
        msg["type"]="clearsharing"
        socket.send_json(msg)       
def _update_notification(socket,user,type):  
    storage.update_notification(user,type)
