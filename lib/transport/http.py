import json

from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet import defer


class RootResource(Resource):
    isLeaf = True

    AVAILABLE_METHODS = {
        'getblockcount':     'get_block_count',
        'getrawtransaction': 'get_raw_transaction',
    }

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def render_POST(self, request):
        try:
            query = json.loads(request.content.read())
        except (ValueError, TypeError):
            return self._render_error400(request, 'JSON loads error')

        if 'method' not in query:
            return self._render_error400(request, 'method not in request')
        if 'params' not in query:
            return self._render_error400(request, 'params not in request')
        if not isinstance(query['params'], list):
            return self._render_error400(request, 'params not list')

        method, params = query['method'], query['params']
        if method in self.AVAILABLE_METHODS:
            getattr(self, self.AVAILABLE_METHODS[method])(request, params)
            return NOT_DONE_YET

        return self._render_error400(request, 'method not found')

    def _render_result(self, request, result):
        request.write(json.dumps({'result': result, 'error': None}))
        request.finish()
        return NOT_DONE_YET

    def _render_error(self, request, error):
        request.write(json.dumps({'result': None, 'error': error}))
        request.finish()
        return NOT_DONE_YET

    def _render_error400(self, request, error):
        request.setResponseCode(400)
        return self._render_error(request, error)

    def _render_error500(self, request, error):
        request.setResponseCode(500)
        return self._render_error(request, error)


    @defer.inlineCallbacks
    def get_block_count(self, request, params):
        try:
            result = yield defer.maybeDeferred(self.blockchain.get_block_count)
            self._render_result(request, result)
        except Exception, e:
            self._render_error500(request, str(e))

    @defer.inlineCallbacks
    def get_raw_transaction(self, request, params):
        if len(params) != 1 or not isinstance(params[0], basestring):
            self._render_error400('txhash not found')
        else:
            try:
                result = yield defer.maybeDeferred(self.blockchain.get_raw_transaction, params[0])
                self._render_result(request, result)
            except Exception, e:
                self._render_error500(request, str(e))


def get_HTTPFactory(config, blockchain):
    return Site(RootResource(blockchain))
