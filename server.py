import argparse
import ConfigParser
import socket

from twisted.internet import reactor

import imp
imp.load_module("ngcccbase_server", *imp.find_module("lib"))
from ngcccbase_server.log import startLogging
from ngcccbase_server.backend.bitcoind import Backend as BitcoindBackend
from ngcccbase_server.transport.http import get_HTTPFactory


def arg_parser():
    parser = argparse.ArgumentParser(usage='%(prog)s [command-line options]')
    parser.add_argument('-c', '--conf',
        action='store',
        default='ngcccbase-server.conf',
        type=str,
        help='Specify configuration file',
        metavar='<file>'
    )
    return parser

def load_config(filename):
    config = ConfigParser.ConfigParser()
    if config.read(filename) == [filename]:
        return config
    raise IOError('load config failed')

def main():
    parser = arg_parser()
    args = vars(parser.parse_args())

    config = load_config(args.get('conf'))

    startLogging(config)

    backend = BitcoindBackend(config)

    reactor.listenTCP(
        int(config.get('server', 'port')),
        get_HTTPFactory(config, backend),
        interface=socket.gethostbyname(config.get('server', 'host'))
    )
    reactor.run()

if __name__ == "__main__":
    main()
