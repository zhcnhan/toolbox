import xml.etree.ElementTree as ET
from typing import Any


def _to_xml_element(tag: str, value: Any) -> ET.Element:
    """递归地将 Python 对象转为 XML Element。"""
    elem = ET.Element(tag)

    if isinstance(value, dict):
        for k, v in value.items():
            # XML 标签名不能以数字开头
            safe_tag = k if k and not k[0].isdigit() else f"item_{k}"
            elem.append(_to_xml_element(safe_tag, v))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            elem.append(_to_xml_element("item", item))
    elif isinstance(value, bool):
        elem.text = "true" if value else "false"
    elif value is None:
        elem.text = ""
    else:
        elem.text = str(value)

    return elem


def _from_xml_element(elem: ET.Element) -> Any:
    """递归地将 XML Element 转为 Python 对象。"""
    children = list(elem)
    if not children:
        text = elem.text or ""
        return text.strip()

    # 检查是否是列表（所有子元素标签名相同且为 "item"）
    tags = [c.tag for c in children]
    if len(set(tags)) == 1 and tags[0] == "item":
        return [_from_xml_element(c) for c in children]

    # 否则是 dict
    result: dict[str, Any] = {}
    for child in children:
        child_value = _from_xml_element(child)
        if child.tag in result:
            # 同名标签转为列表
            if isinstance(result[child.tag], list):
                result[child.tag].append(child_value)
            else:
                result[child.tag] = [result[child.tag], child_value]
        else:
            result[child.tag] = child_value
    return result


def xml_loads(s: str) -> dict[str, Any]:
    """将 XML 文本解析为 Python 字典。"""
    root = ET.fromstring(s)
    return {root.tag: _from_xml_element(root)}


def xml_dumps(obj: Any) -> str:
    """将 Python 对象序列化为 XML 文本。

    自动包装单一根元素，确保 XML 文档只有一个根。
    """
    if isinstance(obj, dict):
        if len(obj) == 1:
            # 已经有单一根
            tag, value = next(iter(obj.items()))
            root = _to_xml_element(tag, value)
        else:
            # 多个顶层 key，包装在 root 下
            root = ET.Element("root")
            for k, v in obj.items():
                safe_tag = k if k and not k[0].isdigit() else f"item_{k}"
                root.append(_to_xml_element(safe_tag, v))
    elif isinstance(obj, list):
        root = ET.Element("root")
        for item in obj:
            root.append(_to_xml_element("item", item))
    else:
        root = ET.Element("root")
        root.text = str(obj)

    ET.indent(root, "  ")
    xml_str = ET.tostring(root, encoding="unicode")
    return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n{xml_str}"
