from bitcoind import BitcoinJSONRPC


class Blockchain(object):
    def __init__(self, config):
        self.bitcoind = BitcoinJSONRPC(config)

    def _get_block_count_callback(self, result, d):
        d.callback(result['result'])

    def get_block_count(self, d):
        request = self.bitcoind.call('getblockcount')
        request.addCallback(self._get_block_count_callback, d)
