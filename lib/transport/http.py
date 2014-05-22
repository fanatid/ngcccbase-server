import json

from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet import defer


class RootResource(Resource):
    isLeaf = True

    AVAILABLE_METHODS = {
        'getblockcount': 'get_block_count',
    }

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
        if method in self.AVAILABLE_METHODS:
            getattr(self, self.AVAILABLE_METHODS[method])(request, params)
            return NOT_DONE_YET

        request.setResponseCode(400)
        return 'method not found'


    def _finish_request(self, request, result, error):
        request.write(json.dumps({'result': result, 'error': error}))
        request.finish()

    @defer.inlineCallbacks
    def get_block_count(self, request, params):
        result = yield defer.maybeDeferred(self.blockchain.get_block_count)
        self._finish_request(request, result, None)


def get_HTTPFactory(config, blockchain):
    return Site(RootResource(blockchain))
