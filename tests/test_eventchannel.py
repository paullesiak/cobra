#!/usr/bin/env python
import os
import pytest
import time
import logging
import logging.handlers
import httplib
import random
import string
import cobra.eventchannel
import cobra.mit.access
import cobra.mit.request
import cobra.mit.session
import cobra.model.fv
import cobra.model.pol
import cobra.mit.request
import cobra.mit.session
import cobra.mit.access
import cobra.model.fv
import cobra.model.pol
import cobra.model.infra

httplib.HTTPConnection.debuglevel = 1

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

fh = logging.handlers.RotatingFileHandler(
    '{0}.log'.format(os.path.splitext(__file__)[0]), maxBytes=1000000)

logger.addHandler(fh)
formatter = logging.Formatter('%(asctime)s %(message)s')
fh.setFormatter(formatter)


def pytest_generate_tests(metafunc):

    def createtenant(moDir, tenant=None):
        topMo = cobra.model.pol.Uni('')
        fvTenant = cobra.model.fv.Tenant(topMo, name=tenant, descr=''.join(
            random.choice(string.lowercase) for i in range(16)))
        c = cobra.mit.request.ConfigRequest()
        c.addMo(fvTenant)
        moDir.commit(c)

    def deletetenant(moDir, tenant=None):
        topMo = cobra.model.pol.Uni('')
        fvTenant = cobra.model.fv.Tenant(topMo, name=tenant)
        fvTenant.delete()
        c = cobra.mit.request.ConfigRequest()
        c.addMo(fvTenant)
        moDir.commit(c)

    def createepg(moDir, tenant=None):
        topMo = cobra.model.pol.Uni('')
        fvTenant = cobra.model.fv.Tenant(topMo, name=tenant, descr=''.join(random.choice(string.lowercase) for i in range(16)))
        fvAp = cobra.model.fv.Ap(fvTenant, name='test')
        fvAEPg = cobra.model.fv.AEPg(fvAp, name='test', descr=''.join(random.choice(string.lowercase) for i in range(16)))
        c = cobra.mit.request.ConfigRequest()
        c.addMo(fvTenant)
        moDir.commit(c)

    def deleteepg(moDir, tenant=None):
        topMo = cobra.model.pol.Uni('')
        fvTenant = cobra.model.fv.Tenant(topMo, name=tenant)
        fvTenant.delete()
        c = cobra.mit.request.ConfigRequest()
        c.addMo(fvTenant)
        moDir.commit(c)


    if 'queries' in metafunc.fixturenames:
        metafunc.parametrize(
            'queries',
            [
                (
                    cobra.mit.request.ClassQuery('fvTenant'),   # query to subscribe to
                    createtenant,                               # bring up method
                    deletetenant,                               # tear down method
                    'uni/tn-eventchannel1',                     # dn
                    {'tenant': 'eventchannel1'}                 # kwargs
                ),
                (
                    cobra.mit.request.ClassQuery('fvAEPg'), 
                    createepg, 
                    deleteepg, 
                    'uni/tn-eventchannel1/ap-test/epg-test', 
                    {'tenant': 'eventchannel1'}
                ), 
            ] 
        )


@pytest.fixture(params=['xml', 'json'])
def moDir(apic, request):
    if apic[0] == 'http://mock':
        pytest.skip('No mock support for event channel yet')

    url, user, password, secure = apic
    secure = False if secure == 'False' else True
    session = cobra.mit.session.LoginSession(url, user, password,
                                             secure=secure,
                                             requestFormat=request.param)
    md = cobra.mit.access.MoDirectory(session)
    md.login()
    return md


class Test_eventchannel:

    def test_subscribe(self, moDir, apic, queries):

        if apic[0] == 'http://mock':
            pytest.skip('No mock support for event channel yet')

        query, bringup, teardown, dn, kwargs = queries
        ec = cobra.eventchannel.EventChannel(moDir)
        subscription = ec.subscribe(query)
        assert(subscription.subid != 0)

        logging.info('Subscription ID is {0}'.format(subscription.subid))

    def test_refresh(self, moDir, apic, queries):

        if apic[0] == 'http://mock':
            pytest.skip('No mock support for event channel yet')

        query, bringup, teardown, dn, kwargs = queries
        ec = cobra.eventchannel.EventChannel(moDir)
        subscription = ec.subscribe(query)
        assert(subscription.subid != 0)

        logging.info('Subscription ID is {0}'.format(subscription.subid))
        subscription.refresh()

    def test_receive_event(self, moDir, apic, queries):

        dicttable = lambda d: '\n'.join(['{:{width}}: {}'.format(k, v, width=max(map(len, d.keys()))) for k,v in sorted(d.items(), key=lambda x: x[0])])

        if apic[0] == 'http://mock':
            pytest.skip('No mock support for event channel yet')

        query, bringup, teardown, dn, kwargs = queries

        ec = cobra.eventchannel.EventChannel(moDir)
        subscription = ec.subscribe(query)
        assert(subscription.subid != 0)

        logging.info('Subscription ID is {0}'.format(subscription.subid))
        subscription.refresh()

        logging.info('Pausing for subscription to propogate')
        time.sleep(3)

        bringup(moDir, **kwargs)

        found = False

        events = ec.decipherEvents()

        for moevent in events:
            logging.info('Event:      : {}'.format(moevent.moEventType))
            logging.info('Dn          : {}'.format(moevent.dn))
            logging.info('Class name  : {}'.format(moevent.moClassName))

            if not moevent.__class__.__name__ == 'MoDelete':
                logging.info('-' * 10)
                logging.info(dicttable(moevent.changes))

            if moevent.dn == dn:
                found = True

        assert(found)

    def test_cleanup(self, moDir, apic, queries):

        if apic[0] == 'http://mock':
            pytest.skip('No mock support for event channel yet')

        query, bringup, teardown, dn, kwargs = queries
        teardown(moDir, **kwargs)
