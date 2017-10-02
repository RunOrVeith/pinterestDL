class MemorySet(list):

    def __init__(self, *args, **kwargs):
        self.last_len = 0
        super(MemorySet, self).__init__(*args, **kwargs)

    def __iter__(self):
        return iter(self[self.last_len:])

    def update(self, more_entries):
        temp_entries = set(more_entries)
        additions = [x for x in temp_entries if x not in self]

        if len(additions) == 0:
            return False
        else:
            self.last_len = len(self)
            self.extend(additions)
            return True
