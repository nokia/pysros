# Copyright 2021 Nokia

import collections
import re

from .errors import *


NL_RE = "[\n]+"
WSP_RE = "[ \t\r]+"
SINGLELINE_COMMENT_RE = "[/][/][^\n]*"
MULTILINE_COMMENT_RE = "[/][*].*?[*][/]"
UNQUOTED_STR_RE = """[^ \t\r\n"';{}](?:[^ \t\r\n;{}/]|[/*](?=[^/])|[/](?=[^/*]))*"""
QUOTED_STR_RE = """\
(?:["](?:[^\\\\"]|[\\\\][\\\\nt"])*["])\
|(?:['](?:[^'])*['])\
"""
STMT_END_RE = ";"
BLOCK_BEGIN_RE = "[{]"
BLOCK_END_RE = "[}]"

TOKEN_REGEX = re.compile(f"""(?:\
(?P<WSP>{WSP_RE})\
|(?P<NEW_LINES>{NL_RE})\
|(?P<SINGLELINE_COMMENT>{SINGLELINE_COMMENT_RE})\
|(?P<MULTILINE_COMMENT>{MULTILINE_COMMENT_RE})\
|(?P<UNQUOTED_STR>{UNQUOTED_STR_RE})\
|(?P<QUOTED_STR>{QUOTED_STR_RE})\
|(?P<STMT_END>{STMT_END_RE})\
|(?P<BLOCK_BEGIN>{BLOCK_BEGIN_RE})\
|(?P<BLOCK_END>{BLOCK_END_RE})\
|(?P<REST>.)\
)""", re.DOTALL)



TOKEN_KIND_STR = 0
TOKEN_STMT_END = 1
TOKEN_BLOCK_BEGIN = 2
TOKEN_BLOCK_END = 3
TOKEN_COMMENT = 4

TOKEN_NAME_TO_ID = {
    "UNQUOTED_STR": TOKEN_KIND_STR,
    "QUOTED_STR": TOKEN_KIND_STR,
    "STMT_END": TOKEN_STMT_END,
    "BLOCK_BEGIN": TOKEN_BLOCK_BEGIN,
    "BLOCK_END": TOKEN_BLOCK_END,
    "SINGLELINE_COMMENT_RE": TOKEN_COMMENT,
    "MULTILINE_COMMENT_RE": TOKEN_COMMENT,
}

def tokenize(s:str):
    for i in re.finditer(TOKEN_REGEX, s):
        if i.lastgroup in ("WSP", "SINGLELINE_COMMENT"):
            continue
        if i.lastgroup in ("NEW_LINES", "MULTILINE_COMMENT"):
            continue
        assert i.lastgroup != "REST"
        val = i.group()
        if i.lastgroup == "QUOTED_STR":
            val = val[1:-1]
        yield (TOKEN_NAME_TO_ID[i.lastgroup], val)

def yang_parser(yang, handler):
    it = iter(tokenize(yang))
    stack = collections.deque()
    ahead_token = None

    def get_token(expected):
        nonlocal ahead_token
        if ahead_token:
            res, ahead_token = ahead_token, None
        else:
            res = next(it, None)
        if res is None:
            if None in expected:
                return None
            raise make_exception(pysros_err_unexpected_end_of_yang)
        if res[0] not in expected:
            raise make_exception(pysros_err_unexpected_token, token=res[1])
        if res[0] == TOKEN_KIND_STR:
            ahead_token = next(it, None)
            while ahead_token and ahead_token[1] == "+":
                ahead_token = next(it, None)
                if ahead_token is None:
                    raise make_exception(pysros_err_unexpected_end_of_yang)
                if ahead_token[0] != TOKEN_KIND_STR:
                    raise make_exception(pysros_err_wrong_rhs)
                res = (res[0], res[1] + ahead_token[1])
                ahead_token = next(it, None)

        return res

    while True:
        token = get_token((TOKEN_KIND_STR, TOKEN_BLOCK_END, None, ))
        if not token:
            assert not stack
            break
        if token[0] == TOKEN_BLOCK_END:
            kw = stack.pop()
            handler.leave(kw)
            continue
        kw = token[1]
        token = get_token((TOKEN_KIND_STR, TOKEN_BLOCK_BEGIN, TOKEN_STMT_END, ))
        if token[0] == TOKEN_KIND_STR:
            arg = token[1]
            token = get_token((TOKEN_BLOCK_BEGIN, TOKEN_STMT_END, ))
        else:
            arg = None

        handler.enter(kw, arg)
        kind = token[0]
        if kind == TOKEN_STMT_END:
            handler.leave(kw)
        else:
            stack.append(kw)
