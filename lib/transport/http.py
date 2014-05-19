from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet.defer import Deferred


class BaseResource(Resource):
    def __init__(self, blockchain):
        self.blockchain = blockchain


class LeafResource(BaseResource):
    isLeaf = True


class BlockCount(LeafResource):
    def _callback(self, result, request):
        request.write(str(result))
        request.finish()

    def render_GET(self, request):
        d = Deferred()
        d.addCallback(self._callback, request)
        self.blockchain.get_block_count(d)
        return NOT_DONE_YET


def get_HTTPFactory(config, blockchain):
    root = Resource()
    root.putChild('blockcount', BlockCount(blockchain))
    return Site(root)
