import os
import hashlib

from twisted.internet import defer, reactor

from bitcoind import BitcoinJSONRPC


def rev_hex(s):
    return s.decode('hex')[::-1].encode('hex')

def int_to_hex(i, length=1):
    s = hex(i)[2:].rstrip('L')
    s = "0"*(2*length - len(s)) + s
    return rev_hex(s)

def header_to_raw(h):
    s = int_to_hex(h.get('version'),4) \
        + rev_hex(h.get('previousblockhash', "0"*64)) \
        + rev_hex(h.get('merkleroot')) \
        + int_to_hex(h.get('time'),4) \
        + rev_hex(h.get('bits')) \
        + int_to_hex(h.get('nonce'),4)
    return s.decode('hex')

def hash_header(raw_header):
    return hashlib.sha256(hashlib.sha256(raw_header).digest()).digest()[::-1].encode('hex_codec')


class Blockchain(object):
    def __init__(self, config):
        self._store_path = config.get('store', 'path')
        self._headers = ''
        self._next_update_headers = None

        self.bitcoind = BitcoinJSONRPC(config)

        reactor.callWhenRunning(self._init_headers)

    @property
    def current_height(self):
        return len(self._headers)/80 - 1

    def _init_headers(self):
        with open(os.path.join(self._store_path, 'blockchain_headers'), 'ab+') as headers:
            self._headers = headers.read()
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown_headers)
        self._next_update_headers = reactor.callLater(0, self._update_headers)

    @defer.inlineCallbacks
    def _update_headers(self):
        try:
            height = yield self.bitcoind.call('getblockcount')
            if height < self.current_height:
                self._headers = self._headers[:height*80]
            while height > self.current_height:
                block_height = self.current_height + 1
                blockhash = yield self.bitcoind.call('getblockhash', [block_height])
                block = yield self.bitcoind.call('getblock', [blockhash])

                if block_height == 0:
                    self._headers = header_to_raw(block)
                else:
                    prev_hash = hash_header(self._headers[-80:])
                    if prev_hash == block.get('previousblockhash'):
                        self._headers += header_to_raw(block)
                    else:
                        self._headers = self._headers[:-80]
        except Exception, e:
            print e

        self._next_update_headers = reactor.callLater(1, self._update_headers)

    def _shutdown_headers(self):
        if self._next_update_headers is not None and self._next_update_headers.active():
            self._next_update_headers.cancel()
        with open(os.path.join(self._store_path, 'blockchain_headers'), 'wb') as headers:
            headers.write(self._headers)


    def get_block_count(self):
        return self.current_height

    def get_raw_transaction(self, txhash):
        return self.bitcoind.call('getrawtransaction', [txhash])
