# pylama:ignore=C0103
bind = '127.0.0.1:8000'

workers = 3
threads = 3

forwarded_allow_ips = '*'
secure_scheme_headers = {'X-Forwarded-Proto': 'https'}
