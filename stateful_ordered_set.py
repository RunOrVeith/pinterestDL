from collections import OrderedDict

class StatefulOrderedSet(object):

    def __init__(self, autoreset=False, *args):
        self.index = 0
        self.autoreset = autoreset
        self._iterable = OrderedDict()
        for arg in args:
            if hasattr(arg, "__iter__"):
                for item in arg:
                    self.__setitem__(item)
            else:
                self.__setitem__(arg, None)

    def __iter__(self):
        yield from list(self._iterable.keys())[self.index:]
        self.index = 0 if self.autoreset else len(self._iterable)

    def __setitem__(self, key, value=None):
        self._iterable[key] = value

    def __getitem__(self, key):
        return list(self._iterable.keys())[key]

    def __str__(self):
        return f"StatefulOrderedSet: {list(self._iterable.keys()).__str__()}, Idx {self.index}"

    def extend(self, iterable):
        for item in iterable:
            self.__setitem__(item)

    def append(self, item):
        self.__setitem__(item)

    def reset(self, reset_to_index=0):
        self.index = reset_to_index


if __name__ == "__main__":
    x = StatefulOrderedSet(True, [4,5,6, 6])
