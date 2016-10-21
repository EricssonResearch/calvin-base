import time
import datetime


class Time(object):

    def timestamp(self):
        return time.time()

    def datetime(self):
        dt = datetime.datetime.now()
        retval = {
            'century': dt.year // 100,
            'year': dt.year % 100,
            'month': dt.month,
            'day': dt.day,
            'hour': dt.hour,
            'minute': dt.minute,
            'second': dt.second,
            'timezone': None
        }
        return retval

    def strftime(self, formating):
        return time.strftime(formating, time.gmtime())


def register(node = None, actor = None):
    return Time()
