import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


def toml_loads(s: str):
    return tomllib.loads(s)


def toml_dumps(obj) -> str:
    return tomli_w.dumps(obj)
