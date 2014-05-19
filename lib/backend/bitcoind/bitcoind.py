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


class BitcoinJSONRPC(object):
    def __init__(self, config):
        self.agent = Agent(reactor)

        self.bitcoind_url = 'http://%s:%s/' % (config.get('bitcoind', 'host'), config.get('bitcoind', 'port'))
        authpair = config.get('bitcoind', 'user') + ':' + config.get('bitcoind', 'password')
        self.headers = Headers({
            'Authorization': [b"Basic " + base64.b64encode(authpair.encode('utf8'))],
            'Content-Type': ['application/x-www-form-urlencoded'],
        })

    def _json_loads(self, result, d):
        try:
            d.callback(json.loads(result))
        except:
            d.errback()

    def _request_callback(self, response):
        d1, d2 = defer.Deferred(), defer.Deferred()
        response.deliverBody(BodyReceiver(d1))
        d1.addCallback(self._json_loads, d2)
        return d2

    def call(self, method, params=None):
        if params is None:
            params = []
        data = {"method": method, 'params': params, 'id': 'jsonrpc'}

        request = self.agent.request(
            'POST',
            self.bitcoind_url,
            self.headers,
            StringProducer(json.dumps(data))
        )
        return request.addCallback(self._request_callback)
