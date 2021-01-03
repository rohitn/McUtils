import os, enum, weakref

from ..Parsers import FileStreamReader, StringStreamReader

__all__ = [
    "Logger",
    "NullLogger",
    "LogLevel",
    "LogParser"
]

class LogLevel(enum.Enum):
    """
    A simple log level object to standardize more pieces of the logger interface
    """
    Quiet = 0
    Warnings = 1
    Debug = 10
    All = 100

    def __eq__(self, other):
        if isinstance(other, LogLevel):
            other = other.value
        return self.value == other
    def __le__(self, other):
        if isinstance(other, LogLevel):
            other = other.value
        return self.value <= other
    def __ge__(self, other):
        if isinstance(other, LogLevel):
            other = other.value
        return self.value >= other
    def __lt__(self, other):
        if isinstance(other, LogLevel):
            other = other.value
        return self.value < other
    def __gt__(self, other):
        if isinstance(other, LogLevel):
            other = other.value
        return self.value > other

class LoggingBlock:
    """
    A class that extends the utility of a logger by automatically setting up a
    named block of logs that add context and can be
    that
    """
    block_settings = [
        {
            'opener': ">>" + "-" * 25 + '{tag}' + "-" * 25,
            'prompt': "::{meta} ",
            'closer': '<<'
        },
        {
            'opener': "::>{tag}",
            'prompt': "  >{meta} ",
            'closer': '<::'
        }
    ]
    block_level_padding= " " * 2
    def __init__(self,
                 logger,
                 log_level=None,
                 block_level=0,
                 block_level_padding=None,
                 tag=None,
                 opener=None,
                 prompt=None,
                 closer=None
                 ):
        self.logger = logger
        if block_level_padding is None:
            block_level_padding = self.block_level_padding
        if block_level >= len(self.block_settings):
            padding = block_level_padding * (block_level - len(self.block_settings) + 1)
            settings = {k: padding + v for k,v in self.block_settings[-1].items()}
        else:
            settings = self.block_settings[block_level]
        self.tag = "" if tag is None else " {} ".format(tag)
        self._old_loglev = None
        self.log_level = log_level if log_level is not None else logger.default_verbosity
        self.opener = settings['opener'] if opener is None else opener
        self._old_prompt = None
        self.prompt = settings['prompt'] if prompt is None else prompt
        self.closer = settings['closer'] if closer is None else closer
        self._in_block = False

    def __enter__(self):
        if self.log_level <= self.logger.verbosity:
            self._in_block = True
            self.logger.log_print(self.opener, tag=self.tag, padding="")
            self._old_prompt = self.logger.padding
            self.logger.padding = self.prompt
            self._old_loglev = self.logger.default_verbosity
            self.logger.default_verbosity = self.log_level
            self.logger.block_level += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._in_block:
            self._in_block = False
            self.logger.log_print(self.closer, tag=self.tag, padding="")
            self.logger.padding = self._old_prompt
            self._old_prompt = None
            self.logger.default_verbosity = self._old_loglev
            self._old_loglev = None
            self.logger.block_level -= 1

class Logger:
    """
    Defines a simple logger object to write log data to a file based on log levels.
    """

    _loggers = weakref.WeakValueDictionary()
    default_verbosity = 0
    def __init__(self,
                 log_file = None,
                 verbosity = LogLevel.All,
                 padding="",
                 newline="\n"
                 ):
        self.log_file = log_file
        self.verbosity = verbosity
        self.padding = padding
        self.newline = newline
        self.block_level = 0 # just an int to pass to `block(...)` so that it can

    def block(self, **kwargs):
        return LoggingBlock(self, block_level=self.block_level, **kwargs)

    def register(self, key):
        """
        Registers the logger under the given key
        :param key:
        :type key:
        :return:
        :rtype:
        """
        self._loggers[key] = self
    @classmethod
    def lookup(cls, key):
        """
        Looks up a logger. Has the convenient, but potentially surprising
        behavior that if no logger is found a `NullLogger` is returned.
        :param key:
        :type key:
        :return:
        :rtype:
        """
        if key in cls._loggers:
            logger = cls._loggers[key]
        else:
            logger = None
        if logger is None:
            logger = NullLogger()
        return logger

    def format_message(self, message, *params, **kwargs):
        if len(kwargs) > 0:
            message = message.format(**kwargs)
        elif len(params) > 0:
            message = message.format(*params)
        return message

    def format_metainfo(self, metainfo):
        if metainfo is None:
            return ""
        else:
            import json
            return json.dumps(metainfo)
    def log_print(self, message, *params, print_options=None, padding=None, newline=None, metainfo=None, **kwargs):
        """
        :param message: message to print
        :type message: str | Iterable[str]
        :param params:
        :type params:
        :param print_options: options to be passed through to print
        :type print_options:
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        if padding is None:
            padding = self.padding
        if newline is None:
            newline = self.newline

        if not isinstance(message, str):
            joiner = (newline + padding)
            message = joiner.join(
                [padding + message[0]]
                + list(message[1:])
            )
        else:
            message = padding + message

        # print(">>>>", repr(message), params)

        if print_options is None:
            print_options={}
        if 'verbosity' in kwargs:
            verbosity = kwargs['verbosity']
            del kwargs['verbosity']
        else:
            verbosity = self.default_verbosity

        if verbosity <= self.verbosity:
            log = self.log_file
            if isinstance(log, str):
                if not os.path.isdir(os.path.dirname(log)):
                    try:
                        os.makedirs(os.path.dirname(log))
                    except OSError:
                        pass
                #O_NONBLOCK is *nix only
                with open(log, "a", os.O_NONBLOCK) as lf: # this is potentially quite slow but I am also quite lazy
                    print(self.format_message(message, *params, meta=self.format_metainfo(metainfo), **kwargs), file=lf, **print_options)
            elif log is None:
                print(self.format_message(message, *params, meta=self.format_metainfo(metainfo), **kwargs), **print_options)
            else:
                print(self.format_message(message, *params, meta=self.format_metainfo(metainfo), **kwargs), file=log, **print_options)

class NullLogger(Logger):
    """
    A logger that implements the interface, but doesn't ever print.
    Allows code to avoid a bunch of "if logger is not None" blocks
    """
    def log_print(self, message, *params, print_options=None, padding=None, newline=None, **kwargs):
        pass

class LogParser(FileStreamReader):
    """
    A parser that will take a log file and stream it as a series of blocks
    """
    def __init__(self, file, block_settings=None, block_level_padding=None, **kwargs):
        if block_settings is None:
            block_settings = LoggingBlock.block_settings
        self.block_settings = block_settings
        if block_level_padding is None:
            block_level_padding = LoggingBlock.block_level_padding
        self.block_level_padding = block_level_padding
        super().__init__(file, **kwargs)

    def get_block_settings(self, block_level):
        block_level_padding = self.block_level_padding
        if block_level >= len(self.block_settings):
            padding = block_level_padding * (block_level - len(self.block_settings) + 1)
            return {k: padding + v for k, v in self.block_settings[-1].items()}
        else:
            return self.block_settings[block_level]

    class LogBlockParser:
        """
        A little holder class that allows block data to be parsed on demand
        """
        def __init__(self, block_data, parent, block_depth):
            """
            :param block_data:
            :type block_data: str
            :param parent:
            :type parent: LogParser
            :param block_depth:
            :type block_depth: int
            """
            self.data = block_data
            self._lines = None
            self._tag = None
            self.parent = parent
            self.depth = block_depth

        @property
        def lines(self):
            if self._lines is None:
                self._tag, self._lines = self.parse_block_data()
            return self._lines
        @property
        def tag(self):
            if self._tag is None:
                self._tag, self._lines = self.parse_block_data()
            return self._tag

        def block_iterator(self, opener, closer,
                           preblock_handler=lambda c,w: w,
                           postblock_handler=lambda e:e,
                           start=0):

            where = self.data.find(opener, start)
            while where > -1:
                chunk = self.data[start:where]
                where = preblock_handler(chunk, where)
                end = self.data.find(closer, where)
                end = postblock_handler(end)
                subblock = self.data[where:end]
                start = end
                yield subblock, start
                where = self.data.find(opener, start)

        def line_iterator(self, pattern=""):
            og_settings = self.parent.get_block_settings(self.depth)
            prompt = og_settings['prompt'].format(meta="") + pattern

        def parse_prompt_blocks(self, chunk, prompt):
            splitsies = chunk.split("\n" + prompt)
            if splitsies[0] == "":
                splitsies = splitsies[1:]
            return splitsies

        def make_subblock(self, block):
            return type(self)(block, self.parent, self.depth+1)

        def parse_block_data(self):
            # find where subblocks are
            # parse around them
            og_settings = self.parent.get_block_settings(self.depth)
            prompt = og_settings['prompt'].split("{meta}", 1)[0]

            new_settings = self.parent.get_block_settings(self.depth+1)
            opener = "\n" + new_settings['opener'].split("{tag}", 1)[0]
            closer = "\n" + new_settings['closer'].split("{tag}", 1)[0]

            start = 0
            lines = []

            with StringStreamReader(self.data) as parser:
                header = parser.parse_key_block("", {"tag":opener, "skip_tag":False})
                if header is not None:
                    lines.extend(self.parse_prompt_blocks(header, prompt))
                    block = parser.parse_key_block("", closer)
                    lines.append(self.make_subblock(block))
                    while header is not None:
                        header = parser.parse_key_block("", {"tag":opener, "skip_tag":False})
                        if header is None:
                            break #
                        lines.extend(self.parse_prompt_blocks(header, prompt))
                        block = parser.parse_key_block("", closer)
                        lines.append(self.make_subblock(block))

                rest = parser.stream.read()
                lines.extend(self.parse_prompt_blocks(rest, prompt))

            tag_start = og_settings['opener'].split("{tag}", 1)[0]
            tag_end = og_settings['opener'].split("{tag}", 2)[-1]
            if tag_start == "":
                if tag_end == "":
                    tag = lines[0].strip()
                else:
                    tag = lines[0].split(tag_end)[0].strip()
            elif tag_end == "":
                tag = lines[0].split(tag_start, 1)[-1].strip()
            else:
                tag = lines[0].split(tag_start, 1)[-1].split(tag_end)[0].strip()

            block_end = "\n" + og_settings['closer'].split("{tag}", 1)[0]
            lines[-1] = lines[-1].split(block_end, 1)[0]

            return tag, lines[1:]

        def __repr__(self):
            return "{}('{}', #records={})".format(
                type(self).__name__,
                self.tag,
                len(self.lines)
            )

    def get_block(self, level=0, tag=None):
        """
        :param level:
        :type level:
        :param tag:
        :type tag:
        :return:
        :rtype:
        """

        block_settings = self.get_block_settings(level)
        if tag is None:
            opener = block_settings['opener'].split("{tag}", 1)[0]
        else:
            opener_split = block_settings['opener'].split("{tag}", 1)
            opener = opener_split[0]
            if len(opener_split) > 1:
                opener += " {} ".format(tag)

        if tag is None:
            closer = block_settings['closer'].split("{tag}", 1)[0]
        else:
            close_split = block_settings['closer'].split("{tag}", 1)
            closer = close_split[0]
            if len(close_split) > 1:
                closer += " {} ".format(tag)

        block_data = self.parse_key_block(opener, "\n"+closer, mode="Single", parser=lambda x:x) #type: str
        if block_data is None:
            raise ValueError("no more blocks")
        # I now need to process get_block further...
        block_data = opener + block_data.split("\n"+closer, 1)[0]

        return self.LogBlockParser(block_data, self, level)

    def get_line(self, level=0, tag=None):
        """
        :param level:
        :type level:
        :param tag:
        :type tag:
        :return:
        :rtype:
        """

        block_settings = self.get_block_settings(level)
        prompt = block_settings['prompt'].split("{meta}", 1)[0]
        if tag is not None:
            prompt += " {}".format(tag)

        # at some point I can try to refactor to keep the header info or whatever
        block_data = self.parse_key_block({'tag':"\n" + prompt, 'skip_tag':True}, {"tag":"\n", 'skip_tag': False}, mode="Single", parser=lambda x:x) #type: str
        if block_data is None:
            raise ValueError("no more lines")

        return block_data

    def get_blocks(self, tag=None, level=0):
        while True: # would be nice to have a smarter iteration protocol but ah well...
            try:
                next_block = self.get_block(level=level, tag=tag)
            except ValueError as e:
                args = e.args
                if len(args) == 1 and isinstance(args[0], str) and args[0] == "no more blocks":
                    return None
                raise
            else:
                if next_block is None:
                    return None
                yield next_block

    def get_lines(self, tag=None, level=0):
        while True: # would be nice to have a smarter iteration protocol but ah well...
            try:
                next_block = self.get_line(level=level, tag=tag)
            except ValueError as e:
                args = e.args
                if len(args) == 1 and isinstance(args[0], str) and args[0] == "no more lines":
                    return None
                raise
            else:
                if next_block is None:
                    return None
                yield next_block