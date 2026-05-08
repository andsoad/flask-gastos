"""
Router minimalista para Cloudflare Workers Python.
Sin dependencias externas — solo stdlib.
"""
import re


class Router:
    def __init__(self):
        self._routes = []

    def add(self, method: str, pattern: str, handler):
        regex = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern) + '$'
        self._routes.append((method.upper(), re.compile(regex), handler))

    def get(self, pattern: str):
        def decorator(fn):
            self.add('GET', pattern, fn)
            return fn
        return decorator

    def post(self, pattern: str):
        def decorator(fn):
            self.add('POST', pattern, fn)
            return fn
        return decorator

    async def dispatch(self, request, env):
        from urllib.parse import urlparse
        url    = urlparse(request.url)
        path   = url.path.rstrip('/') or '/'
        method = request.method.upper()

        for route_method, pattern, handler in self._routes:
            if route_method != method:
                continue
            m = pattern.match(path)
            if m:
                return await handler(request, env, **m.groupdict())

        return Response('Not Found', status=404)


class Response:
    """Wrapper simple de respuesta HTTP."""
    def __init__(self, body: str = '', status: int = 200,
                 content_type: str = 'text/html; charset=utf-8',
                 headers: dict = None):
        self.body         = body
        self.status       = status
        self.content_type = content_type
        self.extra_headers = headers or {}

    def to_js_response(self):
        from js import Response as JSResponse, Headers
        h = Headers.new()
        h.set('Content-Type', self.content_type)
        for k, v in self.extra_headers.items():
            h.set(k, v)
        return JSResponse.new(self.body, status=self.status, headers=h)


def redirect(location: str, status: int = 302) -> Response:
    return Response('', status=status, headers={'Location': location})
