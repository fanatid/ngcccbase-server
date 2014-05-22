import unittest
import urllib2
import json


class TestTransportHTTP(unittest.TestCase):
    def setUp(self):
        self.server_url = "http://localhost:28832/"

    def _call(self, method, params=None):
        data = json.dumps({
            'method': method,
            'params': {} if params is None else params,
        })
        request = urllib2.Request(self.server_url, data)
        try:
            return json.loads(urllib2.urlopen(request).read())
        except urllib2.HTTPError, e:
            print e.code, e.read()
            raise

    def _assertError400(self, request, msg):
        self.assertRaises(urllib2.HTTPError, urllib2.urlopen, request)
        try:
            urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            self.assertEqual(e.code, 400)
            data = json.loads(e.read())
            self.assertEqual(data['result'], None)
            self.assertEqual(data['error'], msg)

    def test_not_json_body(self):
        request = urllib2.Request(self.server_url, 'just string')
        self.assertRaises(urllib2.HTTPError, urllib2.urlopen, request)
        self._assertError400(request, 'JSON loads error')

    def test_method_not_in_request(self):
        request = urllib2.Request(self.server_url, json.dumps({}))
        self._assertError400(request, 'method not in request')

    def test_params_not_in_request(self):
        request = urllib2.Request(self.server_url, json.dumps({'method': ''}))
        self._assertError400(request, 'params not in request')

    def test_params_not_list(self):
        request = urllib2.Request(self.server_url, json.dumps({'method': '', 'params': ''}))
        self._assertError400(request, 'params not dict')

    def test_method_not_found(self):
        request = urllib2.Request(self.server_url, json.dumps({'method': 'strange method', 'params': {}}))
        self._assertError400(request, 'method not found')


    def test_getblockcount(self):
        response = self._call('getblockcount')
        self.assertTrue(isinstance(response['result'], int))
        self.assertTrue(response['result'] > 0)

    def test_getchunk(self):
        response = self._call('getchunk', {'index': 0})
        self.assertEqual(len(response['result']), 322560)

    def test_getheader(self):
        response = self._call('getheader', {'height': 0})
        header = json.loads(response['result'])
        self.assertEqual(header['prev_block_hash'], '0'*64)

    def test_germerkle(self):
        txhash = '748a2229c02e2a857a369249bdbd9c91e0338495ac004f1d3e27f9c978050fbd'
        blockhash = json.loads(self._call('gettxblockhash', {'txhash': txhash})['result'])[0]

        data = json.loads(self._call('getmerkle', {'txhash': txhash, 'blockhash': blockhash})['result'])
        self.assertEqual(data['block_height'], 244668)
        self.assertEqual(data['pos'], 1)

    def test_getrawtransaction(self):
        txhash = 'f0315ffc38709d70ad5647e22048358dd3745f3ce3874223c80a7c92fab0c8ba'
        raw_transaction = '01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0e0420e7494d017f062f503253482fffffffff0100f2052a010000002321021aeaf2f8638a129a3156fbe7e5ef635226b0bafd495ff03afe2c843d7e3a4b51ac00000000'

        response = self._call('getrawtransaction', {'txhash': txhash})
        self.assertEqual(response['result'], raw_transaction)

    def test_gettxblockhash(self):
        txhash = '748a2229c02e2a857a369249bdbd9c91e0338495ac004f1d3e27f9c978050fbd'

        response = self._call('gettxblockhash', {'txhash': txhash})
        data = json.loads(response['result'])
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1], False)

    def test_prefetch(self):
        pass

    def test_sendrawtransaction(self):
        pass


if __name__ == "__main__":
    unittest.main()
