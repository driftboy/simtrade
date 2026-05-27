#!/usr/bin/env python
"""以 HTTPS 启动 Django 开发服务器（Twisted + SSL + Django staticfiles）"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simtrade.settings')

import django
django.setup()

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application
from twisted.internet import ssl, reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

CERT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8443

    # StaticFilesHandler 会自动处理 /static/ 请求，其余交给 Django
    wsgi_app = StaticFilesHandler(get_wsgi_application())
    resource = WSGIResource(reactor, reactor.getThreadPool(), wsgi_app)
    site = Site(resource)

    cert_file = os.path.join(CERT_DIR, 'cert.pem')
    key_file = os.path.join(CERT_DIR, 'key.pem')

    with open(cert_file, 'rb') as f:
        cert_data = f.read()
    with open(key_file, 'rb') as f:
        key_data = f.read()

    from OpenSSL.crypto import load_certificate, load_privatekey, FILETYPE_PEM
    private_key = load_privatekey(FILETYPE_PEM, key_data)
    cert = load_certificate(FILETYPE_PEM, cert_data)
    factory = ssl.CertificateOptions(privateKey=private_key, certificate=cert)

    reactor.listenSSL(port, site, factory, interface='0.0.0.0')
    print(f'HTTPS server running at https://localhost:{port}/')
    print('Press CTRL+C to quit.')
    reactor.run()


if __name__ == '__main__':
    main()
