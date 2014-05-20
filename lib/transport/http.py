import json

from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet.defer import Deferred


class RootResource(Resource):
    isLeaf = True

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def render_POST(self, request):
        try:
            query = json.loads(request.content.read())
        except (ValueError, TypeError):
            request.setResponseCode(400)
            return 'JSON loads error'

        if 'method' not in query:
            request.setResponseCode(400)
            return 'method not in request'
        if 'params' not in query:
            request.setResponseCode(400)
            return 'params not in request'
        if not isinstance(query['params'], list):
            request.setResponseCode(400)
            return 'params not list'

        method, params = query['method'], query['params']
        if method == 'getblockcount':
            return self.getblockcount(request, params)

        request.setResponseCode(400)
        return 'method not found'

    def _common_errback(self, fail=None, request=None):
        if request is None:
            fail, request = None, fail
        request.write(json.dumps({
            'result': None,
            'error': str(fail),
        }))
        request.finish()

    def getblockcount(self, request, params):
        d = Deferred()
        d.addCallback(self._getblockcount_callback, request)
        d.addErrback(self._common_errback, request)
        self.blockchain.get_block_count(d)
        return NOT_DONE_YET

    def _getblockcount_callback(self, result, request):
        request.write(json.dumps({
            'result': result,
            'error': None,
        }))
        request.finish()


def get_HTTPFactory(config, blockchain):
    return Site(RootResource(blockchain))
