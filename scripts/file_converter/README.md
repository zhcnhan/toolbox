# file_converter

多格式文件互转命令行工具。

## 支持的格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| JSON | `.json` | 通用数据交换格式 |
| YAML | `.yaml` / `.yml` | 人类可读的配置格式 |
| CSV | `.csv` | 表格数据 |
| XML | `.xml` | 标记语言 |
| TOML | `.toml` | 配置文件格式 |

> 任意两种格式之间均可互转。注意：CSV 仅支持二维表结构（list[dict]），与其他格式互转时有结构限制。

## 安装

```bash
cd scripts/file_converter
pip install -r requirements.txt
```

## 使用

```bash
# 基本用法
python -m file_converter data.json -t yaml           # JSON → YAML
python -m file_converter config.yaml -t json         # YAML → JSON
python -m file_converter data.json -t csv            # JSON → CSV
python -m file_converter data.csv -t xml             # CSV → XML
python -m file_converter config.toml -t yaml          # TOML → YAML

# 指定输出路径
python -m file_converter data.json -t yaml -o output/config.yaml

# 列出支持的格式
python -m file_converter --list-formats

# 查看版本
python -m file_converter -v
```

## 示例

```bash
# 快速将 package.json 转为更易读的 YAML
python -m file_converter package.json -t yaml -o config.yaml
```

## 项目结构

```
file_converter/
├── __init__.py          # 包初始化 & 版本号
├── __main__.py          # python -m 入口
├── cli.py               # 命令行接口
├── utils.py             # 工具函数（格式检测、文件读写）
├── converters/          # 各格式转换器
│   ├── base.py          # 抽象基类
│   ├── json_converter.py
│   ├── yaml_converter.py
│   ├── csv_converter.py
│   ├── xml_converter.py
│   └── toml_converter.py
├── requirements.txt
└── pyproject.toml
```
