""" See COPYING for license information. """

import re
import os
from urllib    import quote
from urlparse  import urlparse
from errors    import InvalidUrl
from httplib   import HTTPConnection, HTTPSConnection, HTTP
from sys       import version_info

def parse_url(url):
    """
    Given a URL, returns a 4-tuple containing the hostname, port,
    a path relative to root (if any), and a boolean representing
    whether the connection should use SSL or not.
    """
    (scheme, netloc, path, params, query, frag) = urlparse(url)

    # We only support web services
    if not scheme in ('http', 'https'):
        raise InvalidUrl('Scheme must be one of http or https')

    is_ssl = scheme == 'https' and True or False

    # Verify hostnames are valid and parse a port spec (if any)
    match = re.match('([a-zA-Z0-9\-\.]+):?([0-9]{2,5})?', netloc)

    if match:
        (host, port) = match.groups()
        if not port:
            port = is_ssl and '443' or '80'
    else:
        raise InvalidUrl('Invalid host and/or port: %s' % netloc)

    return (host, int(port), path.strip('/'), is_ssl)


def requires_name(exc_class):
    """Decorator to guard against invalid or unset names."""
    def wrapper(f):
        def decorator(*args, **kwargs):
            if not hasattr(args[0], 'name'):
                raise exc_class('')
            if not args[0].name:
                raise exc_class(args[0].name)
            return f(*args, **kwargs)
        decorator.__name__ = f.__name__
        decorator.__doc__ = f.__doc__
        decorator.parent_func = f
        return decorator
    return wrapper


def unicode_quote(s):
    """
    Utility function to address handling of unicode characters when using the quote
    method of the stdlib module urlparse. Converts unicode, if supplied, to utf-8
    and returns quoted utf-8 string.

    For more info see http://bugs.python.org/issue1712522 or
    http://mail.python.org/pipermail/python-dev/2006-July/067248.html
    """
    if isinstance(s, unicode):
        return quote(s.encode("utf-8"))
    else:
        return quote(str(s))


class THTTPConnection(HTTPConnection):
    def __init__(self, host, port, timeout):
        HTTPConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        HTTPConnection.connect(self)
        self.sock.settimeout(self.timeout)


class THTTP(HTTP):
    _connection_class = THTTPConnection

    def set_timeout(self, timeout):
        self._conn.timeout = timeout


class THTTPSConnection(HTTPSConnection):
    def __init__(self, host, port, timeout):
        HTTPSConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        HTTPSConnection.connect(self)
        self.sock.settimeout(self.timeout)


class THTTPS(HTTP):
    _connection_class = THTTPSConnection

    def set_timeout(self, timeout):
        self._conn.timeout = timeout


class ProxyConnection(HTTPSConnection):
    def __init__(self, host, port, timeout):
        proxy = os.environ.get("https_proxy")
        (self.proxy_host,self.proxy_port, path, ssl) = parse_url(proxy)
        self.target_host = host
        self.target_port = port
        HTTPSConnection.__init__(self, self.proxy_host, self.proxy_port)
        self.timeout = timeout

    def connect(self):
        self.set_tunnel(self.target_host, self.target_port)
        HTTPSConnection.connect(self)
        self.sock.settimeout(self.timeout)


def get_conn_class(ssl):
    proxy = os.environ.get("https_proxy", None)
    if ssl:
        if proxy is None:
            if version_info[0] <= 2 and version_info[1] < 6:
                return THTTPSConnection
            else:
                return HTTPSConnection
        else:
            if version_info[0] <= 2 and version_info[1] < 7:
                raise RuntimeError("https_proxy env variable is set, but this python version " \
                                   "doesn't support set_tunnel")
            else: 
                return ProxyConnection
    else:
        if version_info[0] <= 2 and version_info[1] < 6:
            return THTTPConnection
        else:
            return HTTPConnection
