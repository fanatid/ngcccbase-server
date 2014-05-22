import base64, json

from zope.interface import implements
from twisted.internet import defer, protocol, reactor
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer


class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class BodyReceiver(protocol.Protocol):
    def __init__(self, d):
        self.buf = ''
        self.d = d

    def dataReceived(self, data):
        self.buf += data

    def connectionLost(self, reason):
        self.d.callback(self.buf)


class JSONRPCException(Exception):
    def __init__(self, rpc_error):
        super(JSONRPCException, self).__init__('msg: %r  code: %r' %
                (rpc_error['message'], rpc_error['code']))
        self.error = rpc_error


class BitcoinJSONRPC(object):
    def __init__(self, config):
        self._agent = Agent(reactor)

        self._bitcoind_url = 'http://%s:%s/' % (config.get('bitcoind', 'host'), config.get('bitcoind', 'port'))
        authpair = config.get('bitcoind', 'user') + ':' + config.get('bitcoind', 'password')
        self._headers = Headers({
            'Authorization': [b"Basic " + base64.b64encode(authpair.encode('utf8'))],
            'Content-Type': ['application/x-www-form-urlencoded'],
        })

    def _get_body(self, response):
        d = defer.Deferred()
        response.deliverBody(BodyReceiver(d))
        return d

    @defer.inlineCallbacks
    def call(self, method, params=None):
        if params is None:
            params = []
        data = {"method": method, 'params': params, 'id': 'jsonrpc'}

        request = yield self._agent.request(
            'POST',
            self._bitcoind_url,
            self._headers,
            StringProducer(json.dumps(data))
        )
        response = json.loads((yield self._get_body(request)))

        if response['error'] is not None:
            raise JSONRPCException(response['error'])
        if 'result' not in response:
            raise JSONRPCException({
                'code': -343,
                'message': 'missing JSON-RPC result',
            })
        defer.returnValue(response['result'])
