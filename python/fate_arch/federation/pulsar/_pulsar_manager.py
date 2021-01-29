########################################################
# Copyright 2019-2021 program was created VMware, Inc. #
# SPDX-License-Identifier: Apache-2.0                  #
########################################################

import logging
import json
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

MAX_RETRIES = 10
MAX_REDIRECT = 5
BACKOFF_FACTOR = 1

# sleep time equips to {BACKOFF_FACTOR} * (2 ** ({NUMBER_OF_TOTALRETRIES} - 1))

CLUSTER = 'clusters/{}'
TENANT = 'tenants/{}'

# APIs are refer to https://pulsar.apache.org/admin-rest-api/?version=2.7.0&apiversion=v2

class PulsarManager():
    def __init__(self, address: str, port: str, runtime_config: dict ={}):
        self.service_url = "http://{}:{}/admin/v2/".format(address, port)
        self.runtime_config = runtime_config

    # create session is used to construct url and request parameters
    def _create_session(self):
        # retry mechanism refers to https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#urllib3.util.Retry
        retry = Retry(total=MAX_RETRIES, redirect=MAX_REDIRECT,
                      backoff_factor=BACKOFF_FACTOR)
        s = requests.Session()
        # initialize headers
        s.headers.update({'Content-Type': 'application/json'})

        http_adapter = HTTPAdapter(max_retries=retry)
        s.mount('http://', http_adapter)
        s.mount('https://', http_adapter)
        return s

    # allocator
    def get_allocator(self, allocator: str = 'default'):
        session = self._create_session()
        response = session.get(
            self.service_url + 'broker-stats/allocator-stats/{}'.format(allocator))
        return response

    # cluster
    def get_cluster(self, cluster_name: str = ''):
        session = self._create_session()
        response = session.get(
            self.service_url + CLUSTER.format(cluster_name))
        return response

    def delete_cluster(self, cluster_name: str = ''):
        session = self._create_session()

        response = session.delete(
            self.service_url + CLUSTER.format(cluster_name))
        return response

    def _construct_cluster_data(self, service_url: str, broker_url: str,
                                proxy_url: str = '', proxy_protocol: str = "SNI", peer_cluster_names: list = [],
                                enable_tls: bool = False):
        protol = 'http://'

        cluster_urls = {
            'service_url': 'serviceUrl',
            'broker_url': 'brokerServiceUrl',
        }

        if enable_tls:
            for k, v in cluster_urls.items():
                service_urls[k] = cluster_urls[k]+'Tls'
            protol = 'https://'

        # initialize data
        data = {
            cluster_urls['service_url']: service_url,
            cluster_urls['broker_url']: broker_url,
            'peerClusterNames': peer_cluster_names
        }

        if proxy_url != '':
            data.update({
                'proxyServiceUrl': proxy_url,
                'proxyProtocol': proxy_protocol
            })
        return data

    # service_url not need to provide "http://" prefix
    def create_cluster(self, cluster_name: str, service_url: str, broker_url: str,
                       proxy_url: str = '', proxy_protocol: str = "SNI", peer_cluster_names: list = [],
                       enable_tls: bool = False):

        data = _construct_cluster_data(self, service_url, broker_url,
                                       proxy_url, proxy_protocol, peer_cluster_names,
                                       enable_tls)

        session = self._create_session()

        response = session.put(
            self.service_url + CLUSTER.format(cluster_name), data=json.dumps(data))
        return response

    def update_cluster(self, cluster_name: str, service_url: str, broker_url: str,
                       proxy_url: str = '', proxy_protocol: str = "SNI", peer_cluster_names: list = [],
                       enable_tls: bool = False):

        data = _construct_cluster_data(self, service_url, broker_url,
                                       proxy_url, proxy_protocol, peer_cluster_names,
                                       enable_tls)

        session = self._create_session()

        response = session.post(
            self.service_url + CLUSTER.format(cluster_name), data=json.dumps(data))
        return response

    # tenants
    def get_tenant(self, tenant: str = ''):
        session = self._create_session()
        response = session.get(self.service_url + TENANT.format(tenant))
        return response

    def create_tenant(self, tenant: str, admins: list, clusters: list):
        session = self._create_session()

        data = {'adminRoles': admins,
                'allowedClusters': clusters}

        response = session.put(
            self.service_url + TENANT.format(tenant), data=json.dumps(data))

        return response

    def delete_tenant(self, tenant: str):
        session = self._create_session()
        response = session.delete(
            self.service_url + TENANT.format(tenant))
        return response

    def update_tenant(self, tenant: str, admins: list, clusters: list):
        session = self._create_session()

        data = {'adminRoles': admins,
                'allowedClusters': clusters}

        response = session.post(
            self.service_url + TENANT.format(tenant), data=json.dumps(data))
        return response

    # namespace

    def get_namespace(self, tenant: str):
        session = self._create_session()
        response = session.get(
            self.service_url + 'namespaces/{}'.format(tenant))
        return response

     # 'replication_clusters' is always required
    def create_namespace(self, tenant: str, namespace: str, policies: dict = {}):
        session = self._create_session()
        response = session.put(
            self.service_url + 'namespaces/{}/{}'.format(tenant, namespace),
            data=json.dumps(policies)
        )
        return response

    def delete_namespace(self, tenant: str, namespace: str):
        session = self._create_session()
        response = session.delete(
            self.service_url + 'namespace/{}/{}'.format(tenant, namespace)
        )
        return response


if __name__ == '__main__':
    pulsar_manager_a = PulsarManager('localhost', '8080')
    pulsar_manager_b = PulsarManager('localhost', '8081')

    pulsar_manager_a.create_cluster(
        'cluster2', 'http://10.78.172.42:8081', 'pulsar://10.78.172.42:6651')
    print(pulsar_manager_a.get_cluster().text)

    pulsar_manager_b.create_cluster(
        'cluster1', 'http://10.78.172.42:8080', 'pulsar://10.78.172.42:6650')
    print(pulsar_manager_a.get_cluster().text)
    # pulsar_manager_a.delete_cluster('cluster1')

    # tenant could be guest_id-host_id
    response = pulsar_manager_a.create_tenant(
        tenant='geo-tenant', admins=[], clusters=['standalone', 'cluster2'])
    print(response.text)
    response = pulsar_manager_a.create_namespace(
        'geo-tenant', 'geo-namespace', {'replication_clusters': ['standalone', 'cluster2']})
    print(response.text)

    response = pulsar_manager_b.create_tenant(
        tenant='geo-tenant', admins=[], clusters=['cluster1', 'standalone'])
    print(response.text)
    response = pulsar_manager_b.create_namespace(
        'geo-tenant', 'geo-namespace', {'replication_clusters': ['cluster1', 'standalone']})
    print(response.text)