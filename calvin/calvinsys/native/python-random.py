import random


class Random(object):

    def randint(self, minimum, maximum):
        return random.randint(minimum, maximum)


def register(node=None, actor=None):
    return Random()
