import os
import json
import hashlib

from twisted.internet import defer, reactor

import bitcoin.core
from coloredcoinlib import CTransaction, ColorDefinition

from bitcoind import BitcoinJSONRPC


def rev_hex(s):
    return s.decode('hex')[::-1].encode('hex')

def int_to_hex(i, length=1):
    s = hex(i)[2:].rstrip('L')
    s = "0"*(2*length - len(s)) + s
    return rev_hex(s)

def hex_to_int(s):
    return int('0x' + s[::-1].encode('hex'), 16)

def hash_decode(x):
    return x.decode('hex')[::-1]

def hash_encode(x):
    return x[::-1].encode('hex')

def hash_digest(x):
    return hashlib.sha256(hashlib.sha256(x).digest()).digest()

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


class AsyncCTransaction(CTransaction):
    @defer.inlineCallbacks
    def ensure_input_values(self):
        if self.have_input_values:
            return
        for inp in self.inputs:
            prev_tx_hash = inp.prevout.hash
            if prev_tx_hash != 'coinbase':
                txhex = yield self.bs.bitcoind.call('getrawtransaction', [prev_tx_hash])
                txbin = bitcoin.core.x(txhex)
                tx = bitcoin.core.CTransaction.deserialize(txbin)
                prevtx = AsyncCTransaction.from_bitcoincore(prev_tx_hash, tx, self.bs)
                inp.prevtx = prevtx
                inp.value = prevtx.outputs[inp.prevout.n].value
            else:
                inp.value = 0  # TODO: value of coinbase tx?
        self.have_input_values = True


class Backend(object):
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

    def get_chunk(self, index):
        lower, upper = index*2016*80, (index+1)*2016*80
        lower = max(0, lower)
        upper = min(len(self._headers), upper)
        return self._headers[lower:upper].encode('hex')

    def get_header(self, height):
        if height > self.current_height or height < 0:
            raise Exception('height number out of range')
        header = self._headers[height*80:(height+1)*80]
        return json.dumps({
            'version':         hex_to_int(header[0:4]),
            'prev_block_hash': hash_encode(header[4:36]),
            'merkle_root':     hash_encode(header[36:68]),
            'timestamp':       hex_to_int(header[68:72]),
            'bits':            hex_to_int(header[72:76]),
            'nonce':           hex_to_int(header[76:80]),
        })

    @defer.inlineCallbacks
    def get_merkle(self, txhash, blockhash):
        block = yield self.bitcoind.call('getblock', [blockhash])
        tx_list = block['tx']
        tx_pos = tx_list.index(txhash)

        merkle = map(hash_decode, tx_list)
        target_hash = hash_decode(txhash)
        s = []
        while len(merkle) != 1:
            if len(merkle) % 2:
                merkle.append(merkle[-1])
            n = []
            while merkle:
                new_hash = hash_digest(merkle[0] + merkle[1])
                if merkle[0] == target_hash:
                    s.append(hash_encode(merkle[1]))
                    target_hash = new_hash
                elif merkle[1] == target_hash:
                    s.append(hash_encode(merkle[0]))
                    target_hash = new_hash
                n.append(new_hash)
                merkle = merkle[2:]
            merkle = n

        defer.returnValue(json.dumps({
            'block_height': block['height'],
            'merkle': s,
            'pos': tx_pos,
        }))

    def get_raw_transaction(self, txhash):
        return self.bitcoind.call('getrawtransaction', [txhash])

    @defer.inlineCallbacks
    def get_tx_blockhash(self, txhash):
        data = yield self.bitcoind.call('getrawtransaction', [txhash, 1])
        defer.returnValue(json.dumps([
            data.get('blockhash'),
            'confirmations' not in data
        ]))

    @defer.inlineCallbacks
    def prefetch(self, txhash, output_set, color_desc, limit):
        # note the id doesn't actually matter we need to add it so
        #  we have a valid color definition
        color_def = ColorDefinition.from_color_desc(9999, color_desc)
        # gather all the transactions and return them
        tx_lookup = {}

        @defer.inlineCallbacks
        def process(current_txhash, current_outindex):
            """For any tx out, process the colorvalues of the affecting
            inputs first and then scan that tx.
            """
            if limit and len(tx_lookup) > limit:
                defer.returnValue(None)
            if tx_lookup.get(current_txhash):
                defer.returnValue(None)

            raw_transaction = yield self.bitcoind.call('getrawtransaction', [current_txhash])
            txbin = bitcoin.core.x(txhex)
            tx = bitcoin.core.CTransaction.deserialize(txbin)
            current_tx = AsyncCTransaction.from_bitcoincore(txhash, tx, self)
            if not current_tx:
                defer.returnValue(None)

            tx_lookup[current_txhash] = raw_transaction

            # note a genesis tx will simply have 0 affecting inputs
            inputs = set()
            inputs = inputs.union(
                color_def.get_affecting_inputs(current_tx,
                                               [current_outindex]))
            for i in inputs:
                yield process(i.prevout.hash, i.prevout.n)

        for oi in output_set:
            yield process(txhash, oi)

        defer.returnValue(tx_lookup)

    def send_raw_transaction(self, txdata):
        return self.bitcoind.call('sendrawtransaction', [txdata])
