from bitcoind import BitcoinJSONRPC


class Blockchain(object):
    def __init__(self, config):
        self.bitcoind = BitcoinJSONRPC(config)

    def _get_block_count_callback(self, result, d):
        d.callback(result['result'])

    def _get_block_count_errback(self, fail=None, d=None):
        if d is None:
            fail, d = None, fail
        d.errback(fail)

    def get_block_count(self, d):
        request = self.bitcoind.call('getblockcount')
        request.addCallback(self._get_block_count_callback, d)
        request.addErrback(self._get_block_count_errback, d)
