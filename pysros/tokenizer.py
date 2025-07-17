# Copyright 2021-2024 Nokia

import collections
import re

from .errors import *
from .errors import make_exception

NL_RE = "[\n]+"
WSP_RE = "[ \t\r]+"
SINGLELINE_COMMENT_RE = "[/][/][^\n]*"
MULTILINE_COMMENT_RE = "[/][*].*?[*][/]"
UNQUOTED_STR_RE = """[^ \t\r\n"';{}](?:[^ \t\r\n;{}/]|[/*](?=[^/])|[/](?=[^/*]))*"""
QUOTED_STR_RE = """\
(?:["](?:[^\\\\"]|(?:[\\\\].))*["])\
|(?:['](?:[^'])*['])\
"""
STMT_END_RE = ";"
BLOCK_BEGIN_RE = "[{]"
BLOCK_END_RE = "[}]"
CONCATINATION_RE = "[+]"

COMMON_SUBREGEX = f"""\
(?P<WSP>{WSP_RE})\
|(?P<NEW_LINES>{NL_RE})\
|(?P<SINGLELINE_COMMENT>{SINGLELINE_COMMENT_RE})\
|(?P<MULTILINE_COMMENT>{MULTILINE_COMMENT_RE})\
"""

INIT_REGEX = re.compile(f"""(?:\
{COMMON_SUBREGEX}\
|(?P<UNQUOTED_STR>{UNQUOTED_STR_RE})\
|(?P<QUOTED_STR>{QUOTED_STR_RE})\
|(?P<REST>.)\
)""", re.DOTALL)

AFTER_FIRST_QUOTED_TOKEN_REGEX = re.compile(f"""(?:\
{COMMON_SUBREGEX}\
|(?P<CONCATINATION>{CONCATINATION_RE})\
|(?P<UNQUOTED_STR>{UNQUOTED_STR_RE})\
|(?P<QUOTED_STR>{QUOTED_STR_RE})\
|(?P<STMT_END>{STMT_END_RE})\
|(?P<BLOCK_BEGIN>{BLOCK_BEGIN_RE})\
|(?P<REST>.)\
)""", re.DOTALL)

AFTER_FIRST_TOKEN_REGEX = re.compile(f"""(?:\
{COMMON_SUBREGEX}\
|(?P<UNQUOTED_STR>{UNQUOTED_STR_RE})\
|(?P<QUOTED_STR>{QUOTED_STR_RE})\
|(?P<STMT_END>{STMT_END_RE})\
|(?P<BLOCK_BEGIN>{BLOCK_BEGIN_RE})\
|(?P<REST>.)\
)""", re.DOTALL)

AFTER_FIRST_TOKEN_CONCATINATION_REGEX = re.compile(f"""(?:\
{COMMON_SUBREGEX}\
|(?P<QUOTED_STR>{QUOTED_STR_RE})\
|(?P<STMT_END>{STMT_END_RE})\
|(?P<BLOCK_BEGIN>{BLOCK_BEGIN_RE})\
|(?P<REST>.)\
)""", re.DOTALL)

AFTER_SECOND_TOKEN_REGEX = re.compile(f"""(?:\
{COMMON_SUBREGEX}\
|(?P<STMT_END>{STMT_END_RE})\
|(?P<BLOCK_BEGIN>{BLOCK_BEGIN_RE})\
|(?P<REST>.)\
)""", re.DOTALL)

AFTER_SECOND_QUOTED_TOKEN_REGEX = re.compile(f"""(?:\
{COMMON_SUBREGEX}\
|(?P<CONCATINATION>{CONCATINATION_RE})\
|(?P<STMT_END>{STMT_END_RE})\
|(?P<BLOCK_BEGIN>{BLOCK_BEGIN_RE})\
|(?P<REST>.)\
)""", re.DOTALL)

AFTER_SECOND_TOKEN_CONCATINATION_REGEX = re.compile(f"""(?:\
{COMMON_SUBREGEX}\
|(?P<QUOTED_STR>{QUOTED_STR_RE})\
|(?P<REST>.)\
)""", re.DOTALL)

AFTER_STATEMENT_REGEX = re.compile(f"""(?:\
{COMMON_SUBREGEX}\
|(?P<UNQUOTED_STR>{UNQUOTED_STR_RE})\
|(?P<QUOTED_STR>{QUOTED_STR_RE})\
|(?P<BLOCK_END>{BLOCK_END_RE})\
|(?P<REST>.)\
)""", re.DOTALL)


#     container a { "descr" + "iption" "a" + "b" ; }
#     |        | | |       | |        |   | |   | |  |
#     |        | | |       | |        |   | |   | |  AFTER_STATEMENT_STATE
#     |        | | |       | |        |   | |   | |
#     |        | | |       | |        |   | |   | AFTER_STATEMENT_STATE
#     |        | | |       | |        |   | |   |
#     |        | | |       | |        |   | |   AFTER_SECOND_TOKEN_STATE
#     |        | | |       | |        |   | |
#     |        | | |       | |        |   | AFTER_SECOND_TOKEN_CONCATINATION_STATE
#     |        | | |       | |        |   |
#     |        | | |       | |        |   AFTER_SECOND_QUOTED_TOKEN_STATE
#     |        | | |       | |        AFTER_FIRST_TOKEN_STATE
#     |        | | |       | AFTER_FIRST_TOKEN_CONCATINATION_STATE
#     |        | | |       AFTER_FIRST_QUOTED_TOKEN_STATE
#     |        | | AFTER_STATEMENT_STATE
#     |        | AFTER_SECOND_TOKEN_STATE
#     |        AFTER_FIRST_TOKEN_STATE
#     INIT_STATE

INIT_STATE                              = 0
AFTER_FIRST_QUOTED_TOKEN_STATE          = 1
AFTER_FIRST_TOKEN_STATE                 = 2
AFTER_FIRST_TOKEN_CONCATINATION_STATE   = 3
AFTER_SECOND_TOKEN_STATE                = 4
AFTER_SECOND_QUOTED_TOKEN_STATE         = 5
AFTER_SECOND_TOKEN_CONCATINATION_STATE  = 6
AFTER_STATEMENT_STATE                   = 7

STATE_TO_REGEX = (
    INIT_REGEX,
    AFTER_FIRST_QUOTED_TOKEN_REGEX,
    AFTER_FIRST_TOKEN_REGEX,
    AFTER_FIRST_TOKEN_CONCATINATION_REGEX,
    AFTER_SECOND_TOKEN_REGEX,
    AFTER_SECOND_QUOTED_TOKEN_REGEX,
    AFTER_SECOND_TOKEN_CONCATINATION_REGEX,
    AFTER_STATEMENT_REGEX,
)


TOKEN_KIND_QUOTED_STR    = 0
TOKEN_KIND_UNQUOTED_STR  = 1
TOKEN_KIND_STMT_END      = 2
TOKEN_KIND_BLOCK_BEGIN   = 3
TOKEN_KIND_BLOCK_END     = 4
TOKEN_KIND_CONCATINATION = 5

TOKEN_NAME_TO_ID = {
    "UNQUOTED_STR": TOKEN_KIND_UNQUOTED_STR,
    "QUOTED_STR": TOKEN_KIND_QUOTED_STR,
    "STMT_END": TOKEN_KIND_STMT_END,
    "BLOCK_BEGIN": TOKEN_KIND_BLOCK_BEGIN,
    "BLOCK_END": TOKEN_KIND_BLOCK_END,
    "CONCATINATION": TOKEN_KIND_CONCATINATION,
}


def finditer(regex: re.Pattern, s: str):
    pos = 0
    while True:
        m = regex.match(s, pos)
        if m is None:
            return
        pos = m.end()
        if m.lastgroup in ("WSP", "SINGLELINE_COMMENT", "NEW_LINES", "MULTILINE_COMMENT", ):
            continue
        assert m.lastgroup != "REST"
        regex = yield m


def send_with_default(it, data, default):
    try:
        return it.send(data)
    except StopIteration:
        return default


def tokenize(s: str, init_regex: re.Pattern):
    it = iter(finditer(init_regex, s))
    try:
        i = next(it)
    except StopIteration:
        return
    while i is not None:
        val = i.group()
        if i.lastgroup == "QUOTED_STR":
            val = val[1:-1]
        regex = yield (TOKEN_NAME_TO_ID[i.lastgroup], val)
        i = send_with_default(it, regex, None)


class Tokenizer:
    def __init__(self, yang):
        self._state = INIT_STATE
        self._it = iter(tokenize(yang, STATE_TO_REGEX[self._state]))
        self._ahead_token = [next(self._it)]
        self._state_handlers = (
            self._first_token,
            None,
            self._second_token,
            None,
            self._after_second_token,
            None,
            None,
            self._first_token
        )

    def __call__(self):
        return self._state_handlers[self._state]()

    def __iter__(self):
        return self

    def __next__(self):
        return self._state_handlers[self._state]()

    def _first_token(self):
        res = self._try_consume()
        if res is None:
            return None
        if res[0] == TOKEN_KIND_UNQUOTED_STR:
            self._state = AFTER_FIRST_TOKEN_STATE
            return res
        elif res[0] == TOKEN_KIND_BLOCK_END:
            self._state = AFTER_STATEMENT_STATE
            return res
        assert res[0] == TOKEN_KIND_QUOTED_STR
        self._state = AFTER_FIRST_QUOTED_TOKEN_STATE
        ahead = self._peek()
        while ahead[0] == TOKEN_KIND_CONCATINATION:
            self._state = AFTER_FIRST_TOKEN_CONCATINATION_STATE
            ahead = self._peek(1)
            if ahead[0] == TOKEN_KIND_QUOTED_STR:
                self._consume()
                res = (TOKEN_KIND_QUOTED_STR, res[1]+self._consume()[1])
                self._state = AFTER_FIRST_QUOTED_TOKEN_STATE
                ahead = self._peek()
            else:
                break
        self._state = AFTER_FIRST_TOKEN_STATE
        return res

    def _second_token(self):
        res = self._consume()
        if res[0] in (TOKEN_KIND_UNQUOTED_STR, TOKEN_KIND_CONCATINATION, ): #concatination is `keywork + {` case
            self._state = AFTER_SECOND_TOKEN_STATE
            return (TOKEN_KIND_UNQUOTED_STR, res[1])
        elif res[0] in (TOKEN_KIND_STMT_END, TOKEN_KIND_BLOCK_BEGIN, ):
            self._state = AFTER_STATEMENT_STATE
            return res
        assert res[0] == TOKEN_KIND_QUOTED_STR
        self._state = AFTER_SECOND_QUOTED_TOKEN_STATE
        ahead = self._peek()
        while ahead[0] == TOKEN_KIND_CONCATINATION:
            self._consume()
            self._state = AFTER_SECOND_TOKEN_CONCATINATION_STATE
            res = (TOKEN_KIND_QUOTED_STR, res[1]+self._consume()[1])
            self._state = AFTER_SECOND_QUOTED_TOKEN_STATE
            ahead = self._peek()
        self._state = AFTER_SECOND_TOKEN_STATE
        return res

    def _after_second_token(self):
        self._peek()
        self._state = AFTER_STATEMENT_STATE
        return self._consume()

    def _try_peek(self, offset=0):
        self._populate_read_ahead(offset)
        return self._ahead_token[offset]

    def _peek(self, offset=0):
        res = self._try_peek(offset)
        if res is None:
            raise make_exception(pysros_err_unexpected_end_of_yang)
        return res

    def _try_consume(self):
        if self._ahead_token:
            res = self._ahead_token.pop(0)
        else:
            res = self._get_token()
        return res

    def _consume(self):
        res = self._try_consume()
        if res is None:
            raise make_exception(pysros_err_unexpected_end_of_yang)
        return res

    def _get_token(self):
        return send_with_default(self._it, STATE_TO_REGEX[self._state], None)

    def _populate_read_ahead(self, offset=0):
        while len(self._ahead_token) < offset+1:
            self._ahead_token.append(self._get_token())

def yang_parser(yang, handler):
    it = iter(Tokenizer(yang))
    stack = collections.deque()

    while True:
        token = next(it)
        if not token:
            assert not stack
            break
        assert token[0] in (TOKEN_KIND_QUOTED_STR, TOKEN_KIND_UNQUOTED_STR, TOKEN_KIND_BLOCK_END, )
        if token[0] == TOKEN_KIND_BLOCK_END:
            kw = stack.pop()
            handler.leave(kw)
            continue
        kw = token[1]
        token = next(it)
        assert token[0] in (TOKEN_KIND_QUOTED_STR, TOKEN_KIND_UNQUOTED_STR, TOKEN_KIND_BLOCK_BEGIN, TOKEN_KIND_STMT_END, )
        if token[0] in (TOKEN_KIND_QUOTED_STR, TOKEN_KIND_UNQUOTED_STR, ):
            arg = token[1]
            token = next(it)
            assert token[0] in (TOKEN_KIND_BLOCK_BEGIN, TOKEN_KIND_STMT_END, )
        else:
            arg = None

        handler.enter(kw, arg)
        kind = token[0]
        if kind == TOKEN_KIND_STMT_END:
            handler.leave(kw)
        else:
            stack.append(kw)
