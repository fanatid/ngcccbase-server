import sys
import logging

from twisted.python import log


_LEVELS = {
    'info':    logging.INFO,
    'warning': logging.WARNING,
    'error':   logging.ERROR,
}

def startLogging(config):
    if not config.get('logging', 'logging'):
        return

    fmt = logging.Formatter(fmt='%(asctime)-15s %(levelname)s %(message)s')

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)

    fh = logging.FileHandler(config.get('logging', 'filename'))
    fh.setFormatter(fmt)

    tl = logging.getLogger('twisted')
    tl.addHandler(sh)
    tl.addHandler(fh)

    observer = log.PythonLoggingObserver(loggerName='twisted')
    observer.logger.setLevel(_LEVELS.get(config.get('logging', 'level'), logging.ERROR))
    observer.start()
