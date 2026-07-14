import xmltodict


def xml_loads(s: str):
    return xmltodict.parse(s)


def xml_dumps(obj) -> str:
    return xmltodict.unparse(obj, pretty=True)
