from .source_code import SourceCode

class Impacker:
    """ Packs a code and its dependencies into a single file. """

    compress_lib: bool
    verbose: bool

    def __init__(self, *, compress_lib=False, verbose=False):
        self.compress_lib = compress_lib
        self.verbose = verbose

    def pack(self, in_code: SourceCode):
        pass

    def log(self, *args):
        if self.verbose: print(*args)