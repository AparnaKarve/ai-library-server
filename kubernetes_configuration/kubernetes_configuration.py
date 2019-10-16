import os
import logging
import kubernetes.client as kc


LOGGER = logging.getLogger()


def file_contents(filename) -> str:
    try:
        f = open(filename, "r")
        return f.read()
    except FileNotFoundError as e:
        LOGGER.error(
            'Unable to read file: "%s". Error: "%s"',
            filename, e
        )
        return ''


NAMESPACE = file_contents(os.environ.get('NAMESPACE'))

API_EXCEPTION = kc.rest.ApiException


def kubernetes_api_instance():
    """Return Kubernetes API Instance."""

    configuration = kc.Configuration()

    configuration.api_key['authorization'] = file_contents(os.environ.get('API_KEY'))
    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.host = os.environ.get('K8S_HOST', '')
    configuration.ssl_ca_cert = os.environ.get('CA_CERT', '')

    api_instance = kc.CustomObjectsApi(kc.ApiClient(configuration))
    return api_instance
