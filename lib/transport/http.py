import json
import collections

from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.internet import defer


class RootResource(Resource):
    isLeaf = True

    AVAILABLE_METHODS = {
        'getblockcount':      'get_block_count',
        'getchunk':           'get_chunk',
        'getheader':          'get_header',
        'getmerkle':          'get_merkle',
        'getrawtransaction':  'get_raw_transaction',
        'gettxblockhash':     'get_tx_blockhash',
        'prefetch':           'prefetch',
        'sendrawtransaction': 'send_raw_transaction',
    }

    def __init__(self, backend):
        self.backend = backend

    def render_POST(self, request):
        try:
            query = json.loads(request.content.read())
        except (ValueError, TypeError):
            return self._render_error400(request, 'JSON loads error')

        if 'method' not in query:
            return self._render_error400(request, 'method not in request')
        if 'params' not in query:
            return self._render_error400(request, 'params not in request')
        if not isinstance(query['params'], dict):
            return self._render_error400(request, 'params not dict')

        method, params = query['method'], query['params']
        if method in self.AVAILABLE_METHODS:
            getattr(self, self.AVAILABLE_METHODS[method])(request, params)
            return NOT_DONE_YET

        return self._render_error400(request, 'method not found')


    @defer.inlineCallbacks
    def _render_func(self, request, func, *args, **kwargs):
        try:
            result = yield defer.maybeDeferred(func, *args, **kwargs)
            request.write(json.dumps({'result': result, 'error': None}))
            request.finish()
        except Exception, e:
            self._render_error500(request, str(e))

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

    def _require(self, params, key, msg):
        if key not in params:
            raise Exception(msg)
        return params[key]

    def _validate(self, key, test, msg):
        if not test(key):
            raise Exception(msg)


    def get_block_count(self, request, params):
        self._render_func(request, self.backend.get_block_count)

    def get_chunk(self, request, params):
        try:
            index = self._require(params, 'index', 'index not found')
            self._validate(index, lambda x: isinstance(x, int), 'index not int')
        except Exception, e:
            self._render_error400(request, str(e))
        else:
            self._render_func(request, self.backend.get_chunk, index)

    def get_header(self, request, params):
        try:
            height = self._require(params, 'height', 'height not found')
            self._validate(height, lambda x: isinstance(x, int), 'height not int')
        except Exception, e:
            self._render_error400(request, str(e))
        else:
            self._render_func(request, self.backend.get_header, height)

    def get_merkle(self, request, params):
        try:
            txhash = self._require(params, 'txhash', 'txhash not found')
            self._validate(txhash, lambda x: isinstance(x, basestring), 'txhash not string')
            blockhash = self._require(params, 'blockhash', 'blockhash not found')
            self._validate(blockhash, lambda x: isinstance(x, basestring), 'blockhash not string')
        except Exception, e:
            self._render_error400(request, str(e))
        else:
            self._render_func(request, self.backend.get_merkle, txhash, blockhash)

    def get_raw_transaction(self, request, params):
        try:
            txhash = self._require(params, 'txhash', 'txhash not found')
            self._validate(txhash, lambda x: isinstance(x, basestring), 'txhash not string')
        except Exception, e:
            self._render_error400(request, str(e))
        else:
            self._render_func(request, self.backend.get_raw_transaction, txhash)

    def get_tx_blockhash(self, request, params):
        try:
            txhash = self._require(params, 'txhash', 'txhash not found')
            self._validate(txhash, lambda x: isinstance(x, basestring), 'txhash not string')
        except Exception, e:
            self._render_error400(request, str(e))
        else:
            self._render_func(request, self.backend.get_tx_blockhash, txhash)

    def prefetch(self, request, params):
        try:
            txhash = self._require(params, 'txhash', 'txhash not found')
            self._validate(txhash, lambda x: isinstance(x, basestring), 'txhash not string')
            output_set = self._require(params, 'output_set', 'output_set not found')
            self._validate(output_set, lambda x: isinstance(x, collections.Iterable, 'output_set not iterable'))
            color_desc = self._require(params, 'color_desc', 'color_desc not found')
            #self._validate(color_desc, lambda x: isinstance(x, ???), 'color_desc not ???')
            limit = params.get('limit')
        except Exception, e:
            self._render_error400(request, str(e))
        else:
            self._render_func(request, self.backend.prefetch, txhash, output_set, color_desc, limit)

    def send_raw_transaction(self, request, params):
        try:
            txdata = self._require(params, 'txdata', 'txdata not found')
            self._validate(txdata, lambda x: isinstance(x, basestring), 'txdata not string')
        except Exception, e:
            self._render_error400(request, str(e))
        else:
            self._render_func(request, self.backend.send_raw_transaction, txdata)


def get_HTTPFactory(config, backend):
    return Site(RootResource(backend))
