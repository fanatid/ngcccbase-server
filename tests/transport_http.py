import unittest
import urllib2
import json


class TestTransportHTTP(unittest.TestCase):
    def setUp(self):
        self.server_url = "http://localhost:28832/"

    def _call(self, method, params=None):
        data = json.dumps({
            'method': method,
            'params': [] if params is None else params,
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
        request = urllib2.Request(self.server_url, json.dumps({'params': []}))
        self._assertError400(request, 'method not in request')

    def test_params_not_in_request(self):
        request = urllib2.Request(self.server_url, json.dumps({'method': ''}))
        self._assertError400(request, 'params not in request')

    def test_params_not_list(self):
        request = urllib2.Request(self.server_url, json.dumps({'method': '', 'params': ''}))
        self._assertError400(request, 'params not list')

    def test_method_not_found(self):
        request = urllib2.Request(self.server_url, json.dumps({'method': 'strange method', 'params': []}))
        self._assertError400(request, 'method not found')


    def test_getblockcount(self):
        response = self._call('getblockcount')
        self.assertTrue(isinstance(response['result'], int))
        self.assertTrue(response['result'] > 0)

    def test_getrawtransaction(self):
        txhash = 'f0315ffc38709d70ad5647e22048358dd3745f3ce3874223c80a7c92fab0c8ba'
        raw_transaction = '01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0e0420e7494d017f062f503253482fffffffff0100f2052a010000002321021aeaf2f8638a129a3156fbe7e5ef635226b0bafd495ff03afe2c843d7e3a4b51ac00000000'

        response = self._call('getrawtransaction', [txhash])
        self.assertEqual(response['result'], raw_transaction)


if __name__ == "__main__":
    unittest.main()
