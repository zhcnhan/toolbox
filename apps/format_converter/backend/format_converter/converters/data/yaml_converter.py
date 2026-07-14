import yaml


def yaml_loads(s: str):
    return yaml.safe_load(s)


def yaml_dumps(obj) -> str:
    return yaml.dump(obj, allow_unicode=True, sort_keys=False)
