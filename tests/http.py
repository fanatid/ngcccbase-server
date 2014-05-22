import unittest
import urllib2
import json


class TestTransportHTTP(unittest.TestCase):
    def setUp(self):
        self.server_url = "http://localhost:28832/"

    def call(self, method, params=None):
        data = json.dumps({
            'method': method,
            'params': [] if params is None else params,
        })
        req = urllib2.Request(
            self.server_url,
            data,
            {'Content-Type': 'application/json'}
        )
        return json.loads(urllib2.urlopen(req).read())

    def test_getblockcount(self):
        response = self.call('getblockcount')
        self.assertTrue(isinstance(response['result'], int))
        self.assertTrue(response['result'] > 0)

    def test_getrawtransaction(self):
        txhash = 'f0315ffc38709d70ad5647e22048358dd3745f3ce3874223c80a7c92fab0c8ba'
        raw_transaction = '01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff0e0420e7494d017f062f503253482fffffffff0100f2052a010000002321021aeaf2f8638a129a3156fbe7e5ef635226b0bafd495ff03afe2c843d7e3a4b51ac00000000'

        response = self.call('getrawtransaction', [txhash])
        self.assertEqual(response['result'], raw_transaction)


if __name__ == "__main__":
    unittest.main()
