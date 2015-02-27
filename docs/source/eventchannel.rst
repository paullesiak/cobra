.. _Using Cobra to receive event notifications:

******************************************
Using Cobra to receive event notifications
******************************************

The following section describes how to use Cobra to receive notifications of events that occur on APIC, including changes to classes, individual objects or a combination of both.


Prerequisites for Event Notification
====================================

The cobra.eventchannel package must be imported and available

	import cobra.eventchannel

A standard directory object using a LoginSession must first be established, before you can begin to receive events.
.. note:: As of the time of writing, CertSession support for EventChannels in Cobra is unavailable due to CSCur12715


Instantiating an EventChannel
=============================

A cobra.eventchannel.EventChannel object is used for subscribing to events and receiving notifications from the event channel. The instantiation references the directory object.

    ec = cobra.eventchannel.EventChannel(moDir)

Subscribing to Events
=====================

After an EventChannel object has been created, you can begin to subscribe to events on that EventChannel, using the existing ClassQuery and DnQuery objects. For example, to subscribe to all events that occur on a fvTenant object:

	tenantQuery = cobra.mit.request.ClassQuery('fvTenant')
	subscription = ec.subscribe(tenantQuery)
	print 'Subscription ID is {0}'.format(subscription.subid)

Refreshing Subscriptions
========================

By default, a subscription must be refreshed every 60 seconds. If you wish to unsubscribe to an event, the supported mechanism for doing this is to simply allow the subscription to lapse. If you wish to refresh a subscription, you can use the refresh() method before the 60 seconds has expired. For example:

	subscription.refresh()

Receiving Events from the EventChannel
======================================

Events can be read from the EventChannel using the getevent() method. This method will return an array of Mo objects, containing the changes to the object. getevent() is a blocking call, and will return once an event has been received on the websocket or after the timeout value defined by socket.getdefaulttimeout().

	mos = ec.getevent()
	for mo in mos:
		print 'Event received for {0}'.format(mo.dn)


