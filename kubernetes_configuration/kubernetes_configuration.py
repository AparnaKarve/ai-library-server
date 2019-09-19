import os
import kubernetes.client as kc


def file_contents(filename) -> str:
    f = open(filename, "r")
    return f.read()


NAMESPACE = file_contents(os.environ.get('NAMESPACE'))


def kubernetes_api_instance():
    """Kubernetes Configuration."""

    configuration = kc.Configuration()

    configuration.api_key['authorization'] = file_contents(os.environ.get('API_KEY'))
    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.host = os.environ.get('K8S_HOST', '')
    configuration.ssl_ca_cert = os.environ.get('CA_CERT', '')


    # TOKEN = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJhay1wcm9qZWN0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tcHd6YjQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImE5ZjNiNDE1LWM1MGMtMTFlOS1hNWExLTY0MDA2YTYyNWUxOSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDphay1wcm9qZWN0OmRlZmF1bHQifQ.fBYH8VL1GEzK9672aWuHJkAeJJs8cLOxw-LoxdrRRLXPkgfyj07mimJnjGk7DcRi5jOaes9bMKMZsofg_HaFETZiALc_9XOU-Ka8Ww2fhyDUJgTZa70sxMx-ec9VmkdKyukn_e5fdsxsQ0kpjqeSkqgbMPEna93t4_rv0kCHBY9dlcCNW1ZuQwlcV51Gb0EitmIBDAlYYbDvG16cwRd_ifeT9OeZ55ZNX17av7zXO8b9AJejfzdDEkfzD0lzv1TrTicc7x50nCC15fI40K-4u9oDnXW-H-QvzLtPtvheHdV73HdwARhd3MFXeuqsNBEyMpPLEKOiFHSYnz-fV7ECHA'
    # CONFIGURATION.api_key['authorization'] = os.environ.get('API_KEY', TOKEN)
    # CONFIGURATION.api_key_prefix['authorization'] = 'Bearer'
    # CONFIGURATION.host = os.environ.get('KUBERNETES_SERVICE_HOST', 'https://sde-ci-works05.3a2m.lab.eng.bos.redhat.com:8443')
    # CONFIGURATION.verify_ssl = False

    api_instance = kc.CustomObjectsApi(kc.ApiClient(configuration))
    return api_instance

