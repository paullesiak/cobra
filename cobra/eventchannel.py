# *************************************************************************
# Copyright (c) 2013 Cisco Systems, Inc.  All rights reserved.
# *************************************************************************

import websocket
import ssl
import xml.etree.cElementTree as ET
import json
from cobra.mit.request import AbstractQuery, AbstractRequest, RestError
from cobra.mit.session import AbstractSession
from cobra.mit.naming import Dn

from cobra.internal.codec import parseMoClassName
# from cobra.internal.codec.jsoncodec import fromJSONStr, fromJSONDict
# from cobra.internal.codec.xmlcodec import fromXMLStr, _fromXMLRootNode
from cobra.internal.rest.accessimpl import RestAccess


class RefreshSubRequest(AbstractQuery):

    """
    Subscription Refresh Request

    This class is used to generate refresh requests for subscriptions

    Attributes:
      subid (string): The ID for this subscription
    """

    def __init__(self, subid):
        """Creates a new Refresh Request for a subscription object

        Args:
          subid (string): The ID for the subscription to be refreshed
        """

        self.__options = {}
        self.subid = subid
        self.uriBase = "/api/subscriptionRefresh"

    @property
    def options(self):
        return AbstractRequest.makeOptions(self.__options)

    def getUrl(self, session):
        return session.url + self.getUriPathAndOptions(session)

    @property
    def subid(self):
        """The subid is the subscription ID returned by the initial
        subscription request"""
        return self.__options.get('id', None)

    @subid.setter
    def subid(self, value):
        self.__options['id'] = value


class Subscription(object):

    """
    Subscription class

    A subscription represents a subscription to an queriable object with
    an associated subscription ID
    """

    def __init__(self, subid, eventChannel):
        """Creates a new subscription object

        Args:
          subid (string): The subscription ID
          eventChannel (cobra.eventchannel.EventChannel): Event channel
            to which this subscription is associated
        """

        self._subid = subid
        self._eventchannel = eventChannel

    def refresh(self):
        """Subscriptions must be refreshed every 60 seconds as per the 
        APIC REST API definition"""
        self._eventchannel._refresh(self._subid)

    @property
    def subid(self):
        return self._subid


class EventChannel(object):

    def __init__(self, moDir):
        """Initialize a cobra Event Channel

        Args:
          moDir (cobra.mit.access.MoDirectory): the Managed Object directory

        Notes:
          Only LoginSession sessions are currently supported.
            CertSession is not supported
        """
        #  CSCur12715 No way to connect to websocket with certificate session

        self._moDir = moDir

        self._secure = self._moDir.secure

        proto, server = self._moDir.url.split('://')

        if proto == 'https':
            proto = 'wss'
        else:
            proto = 'ws'

        self._wsuri = '{0}://{1}/socket{2}'.format(
            proto, server, self._moDir.cookie)

        if self._secure:
            kwargs = {}
        else:
            kwargs = {'sslopt': {"cert_reqs": ssl.CERT_NONE}}

        self._websocket = websocket.create_connection(self._wsuri, **kwargs)

    def subscribe(self, dnOrClassQuery):
        """Subscribes the event channel to a particular class query or dn query

        Args:
          dnOrClassQuery (cobra.mit.request.ClassQuery): Class Query
            object which will be subscribed
          dnOrClassQuery (cobra.mit.request.DnQuery): Dn Query object
            which will be subscribed

        Returns:
          cobra.eventchannel.Subscription: Object representing the subscription
        """

        dnOrClassQuery.subscription = 'yes'

        rsp = self._moDir._accessImpl._get(dnOrClassQuery)

        fmt = self._moDir._accessImpl._session.formatType
        if fmt == AbstractSession.XML_FORMAT:
            subid = ET.fromstring(rsp.text).get('subscriptionId')
        else:
            subid = rsp.json().get('subscriptionId', None)

        return Subscription(subid, self)

    def _refresh(self, subscriptionId):
        """_refresh() should not be called directly, but instead through
        Subscription.refresh() which will pass the associated subid

        Args:
          subscriptionId (int): Subscription ID that will be refreshed

        Raises:
          RestError: If the subscription refresh returns a
            non-successful code
        """
        refreshRequest = RefreshSubRequest(subscriptionId)
        rsp = self._moDir._accessImpl._get(refreshRequest)
        if rsp.status_code != RestAccess.requests_codes().ok:
            raise RestError(None, 'Error refreshing subscription', rsp.status_code)

    def getEvents(self):
        """Get events from the event channel

        Returns:
          list: List of cobra.eventchannel.AbstractEvent-based objects containing changes that have
            been read off the event Channel
        """
        eventStr = self._websocket.recv()
        return self._parseEvents(eventStr)

    def _parseEvents(self, eventStr):
        """Internal helper method for parsing an incoming event string

        Args:
          event (str): data payload for incoming event

        Returns:
          list: list of event objects containing changes, properties 
            affected and new values
        """
        return AbstractEvent.parseEvents(self, eventStr)


class AbstractEvent(object):

    """
    An abstract event type

    AbstractEvent represents any type of notifiable event that can
      arrive over the event channel. Currently this list includes:
        MoEvent
    """

    def __init__(self):
        pass

    @classmethod
    def parseEvents(cls, eventChannel, eventStr):
        """Indirection method, to allow for more events in future.
        Currently just returns an MoEvent for the eventStr
        """
        return MoEvent.parseMoEventStr(eventChannel, eventStr)


class MoEvent(AbstractEvent):

    """
    A managed object based event

    MoEvent is a base class for any type of event that can be applied
      to a managed object and received over the event channel

    """

    def __init__(self):
        self._moClassName = None
        self._subscription = None
        self._dnStr = None

    @classmethod
    def _createMoEvent(cls, moClassName, moChanges, subId):
        """Creates a managed object event

        Args:
          moClassName (str): type of the class for which the event is
          moChanges (dict): dictionary of changes, with keys representing
            the attribute name and values representing the new value
          subId (cobra.eventchannel.Subscription): subscription object
            representing the subscription that generated this MoEvent

        Returns:
          cobra.eventchannel.MoCreate: For new MO objects being created
          cobra.eventchannel.MoModify: For MOs being modified
          cobra.eventchannel.MoDelete: For Mos being deleted

        """

        dnStr = None
        status = None

        if 'dn' in moChanges:
            dnStr = moChanges['dn']
            del moChanges['dn']
        if 'status' in moChanges:
            status = moChanges['status']
            del moChanges['status']

        if status == 'created':
            return MoCreate(dnStr, moClassName, moChanges, subId)
        elif status == 'modified':
            return MoModify(dnStr, moClassName, moChanges, subId)
        if status == 'deleted':
            return MoDelete(dnStr, moClassName, subId)

    @classmethod
    def parseMoEventStr(cls, eventChannel, eventStr):
        """Returns a list of cobra.eventchannel.MoEvent objects representing the changes
        received within an event channel update

        Args:
          eventChannel (cobra.eventchannel.EventChannel): The Event Channel
            on which this event was received. This is passed down to the
            subscription attribute on the MoEvent
          eventStr (str): Event string (XML or JSON) from the incoming
            event stream

        Returns:
          list: List of cobra.eventchannel.MoEvent objects

        """

        subscription = None
        MoEvents = []

        fmt = eventChannel._moDir._accessImpl._session.formatType
        if fmt == AbstractSession.XML_FORMAT:
            root = ET.fromstring(eventStr)
            subId = root.get('subscriptionId')
            subscription = Subscription(subId, eventChannel)

            for node in root:
                moClassName = node.tag
                moProps = node.attrib
                MoEvents.append(
                    MoEvent._createMoEvent(moClassName, moProps, subscription))

        else:
            rspDict = json.loads(eventStr)
            rootNode = rspDict.get('imdata', None)
            subId = rspDict.get('subscriptionId', None)[0]
            subscription = Subscription(subId, eventChannel)

            for moNode in rootNode:
                moClassName = moNode.keys()[0]
                moProps = moNode[moClassName]['attributes']
                MoEvents.append(
                    MoEvent._createMoEvent(moClassName, moProps, subscription))

        return MoEvents

    @property
    def dn(self):
        return Dn.fromString(self._dnStr)

    @property
    def moClassName(self):
        """
        Returns the MO Class for the Event
        """
        return self._moClassName

    @property
    def subscription(self):
        """
        Returns a Subscription object representing the subscription
        identifier from which this Event came
        """
        return self._subscription

    @property
    def moEventType(self):
        """
        Returns the type of this MoEvent
        """
        return self.__class__.__name__


class MoDelete(MoEvent):

    def __init__(self, dnStr, moClassName, subscription):
        self._dnStr = dnStr
        self._moClassName = moClassName
        self._subscription = subscription


class MoCreate(MoEvent):

    def __init__(self, dnStr, moClassName, changes, subscription):
        self._dnStr = dnStr
        self._moClassName = moClassName
        self._changes = changes
        self._subscription = subscription

    @property
    def changes(self):
        return self._changes


class MoModify(MoEvent):

    def __init__(self, dnStr, moClassName, changes, subscription):
        self._dnStr = dnStr
        self._moClassName = moClassName
        self._changes = changes
        self._subscription = subscription

    @property
    def changes(self):
        return self._changes
