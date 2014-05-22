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

    def test_blockcount(self):
        response = self.call('getblockcount')
        self.assertTrue(isinstance(response['result'], int))
        self.assertTrue(response['result'] > 0)


if __name__ == "__main__":
    unittest.main()
