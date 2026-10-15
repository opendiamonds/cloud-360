"""generator.py — REST→MCP 工具宣告產生器（`BR72.1`–`BR72.11`；PBT 標的）。

`generate_tools(openapi, allowlist)` 是純函式：無 I/O、決定性、輸出依工具名排序，且與 openapi
`paths`／`properties` 的鍵順序無關。任何違反一律拋 `GeneratorError(code, tool_name)`，不部分產出。

**檢查順序固定**（`BR72.1`；使每類違反恰得一個錯誤碼）。對每一項 allowlist entry（依工具名排序）：

1. `path_outside_scope`（`BR72.11`）
2. `missing_operation`（`BR72.2`）
3. `unsupported_parameter_location`（`BR72.3`：header／cookie 參數）
4. `unsupported_body`（`BR72.3`：非 `application/json` 或本體 schema 不是 object）
5. `name_collision`（`BR72.3`）
6. `inject_without_strip`（`BR72.4`）
7. `agent_requirement_mismatch`（`BR72.10`）
   → 套用 strip 與 rename（`BR72.4`、`BR72.5`）
8. `credential_like_property`（`BR72.7`，遞迴任何深度，**在改名之後、白名單比對之前**）
9. `whitelist_mismatch`（`BR72.6`）
10. `unsupported_body`（任一工具屬性型別不是 string）

security 需求一律不產生任何屬性（`BR72.3`）；工具名、描述、屬性描述取自 allowlist（`BR72.8`）。
`validate_tool_specs(specs, allowlist)` 在啟動時對已載入的產物重跑白名單、底線、`requires_agent`
綁定與路徑前綴（`BR71.5`），防止手改產物繞過產生器。

純函式模組：不 import `mcp`、`httpx`、`sqlalchemy`、`fastapi`（`NFR21.40`；CC-2）。
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

#: 路徑前綴白名單（`BR72.11`）。擴充前綴是修改程式常數、必經程式碼審查。
ALLOWED_PATH_PREFIXES: tuple[str, ...] = ("/api/requirements/",)

#: 黑名單底線（`BR72.7`）：不分大小寫的子字串比對。
CREDENTIAL_LIKE = re.compile(r"token|key|secret|authorization", re.IGNORECASE)

#: `inject` 唯一允許的來源種類（`entities.md` `AllowlistEntry.inject`）。
INJECT_SOURCE_AGENT_GROUP = "agent_group_of_declared_agent"

_METHODS = ("GET", "PUT", "DELETE", "POST", "PATCH")
_JSON_MEDIA = "application/json"


class GeneratorError(Exception):
    """產生器唯一的失敗形式。訊息只含 code 與 tool_name，不含 openapi 片段。"""

    CODES = (
        "path_outside_scope", "missing_operation", "unsupported_parameter_location",
        "unsupported_body", "name_collision", "inject_without_strip",
        "agent_requirement_mismatch", "credential_like_property", "whitelist_mismatch",
    )

    def __init__(self, code: str, tool_name: str) -> None:
        if code not in self.CODES:
            raise ValueError(f"unknown generator error code: {code}")
        super().__init__(f"{code}: {tool_name}")
        self.code = code
        self.tool_name = tool_name


class AllowlistFormatError(ValueError):
    """allowlist.json 本身的結構不合（鍵缺漏、型別錯）。訊息只含工具名或固定字樣。"""


# ---- 值物件 ----------------------------------------------------------------------------
@dataclass(frozen=True)
class AllowlistEntry:
    name: str
    method: str
    path: str
    description: str
    properties: tuple[str, ...]
    property_descriptions: Mapping[str, str]
    requires_agent: bool
    strip_body_fields: tuple[str, ...] = ()
    inject: Mapping[str, str] = field(default_factory=dict)
    rename: Mapping[str, str] = field(default_factory=dict)
    property_patterns: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Allowlist:
    entries: tuple[AllowlistEntry, ...]

    def by_name(self) -> dict[str, AllowlistEntry]:
        return {entry.name: entry for entry in self.entries}


@dataclass(frozen=True)
class ToolSpec:
    """`generated_tools.json` 的一項。`binding` 不屬於工具宣告，`tools/list` 不交出它。"""

    name: str
    description: str
    input_schema: Mapping[str, Any]
    requires_agent: bool
    binding: Mapping[str, Any]

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": copy.deepcopy(dict(self.input_schema)),
            "requires_agent": self.requires_agent,
            "binding": copy.deepcopy(dict(self.binding)),
        }

    @classmethod
    def from_json(cls, document: Any) -> "ToolSpec":
        if not isinstance(document, dict):
            raise ValueError("tool spec must be an object")
        expected = {"name", "description", "inputSchema", "requires_agent", "binding"}
        if set(document) != expected:
            raise ValueError("tool spec keys")
        name = document["name"]
        if not isinstance(name, str) or not name:
            raise ValueError("tool spec name")
        if not isinstance(document["description"], str):
            raise ValueError(name)
        if not isinstance(document["inputSchema"], dict):
            raise ValueError(name)
        if not isinstance(document["requires_agent"], bool):
            raise ValueError(name)
        binding = document["binding"]
        if not isinstance(binding, dict):
            raise ValueError(name)
        for key in ("method", "path", "path_params", "query_params", "body_params", "inject"):
            if key not in binding:
                raise ValueError(name)
        if not isinstance(binding["method"], str) or not isinstance(binding["path"], str):
            raise ValueError(name)
        for key in ("path_params", "query_params", "body_params", "inject"):
            value = binding[key]
            if not isinstance(value, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in value.items()
            ):
                raise ValueError(name)
        return cls(name=name, description=document["description"],
                   input_schema=copy.deepcopy(document["inputSchema"]),
                   requires_agent=document["requires_agent"], binding=copy.deepcopy(binding))


# ---- allowlist 解析 --------------------------------------------------------------------
def _str_list(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise AllowlistFormatError(where)
    if len(set(value)) != len(value):
        raise AllowlistFormatError(where)
    return tuple(value)


def _str_map(value: Any, where: str) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise AllowlistFormatError(where)
    return dict(value)


def parse_allowlist(document: Any) -> Allowlist:
    """把 allowlist.json 的內容轉成 `Allowlist`；結構不合拋 `AllowlistFormatError`。"""
    if not isinstance(document, dict) or not isinstance(document.get("tools"), list):
        raise AllowlistFormatError("allowlist.json")
    required = {"name", "method", "path", "description", "properties",
                "property_descriptions", "requires_agent"}
    optional = {"strip_body_fields", "inject", "rename", "property_patterns"}
    entries = []
    seen_names: set[str] = set()
    seen_ops: set[tuple[str, str]] = set()
    for raw in document["tools"]:
        if not isinstance(raw, dict):
            raise AllowlistFormatError("allowlist.json")
        name = raw.get("name")
        where = name if isinstance(name, str) and name else "allowlist.json"
        if not required <= set(raw) or not set(raw) <= required | optional:
            raise AllowlistFormatError(where)
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name):
            raise AllowlistFormatError(where)
        method = raw["method"]
        if method not in _METHODS or not isinstance(raw["path"], str):
            raise AllowlistFormatError(where)
        if not isinstance(raw["description"], str) or not raw["description"]:
            raise AllowlistFormatError(where)
        if not isinstance(raw["requires_agent"], bool):
            raise AllowlistFormatError(where)
        properties = _str_list(raw["properties"], where)
        descriptions = _str_map(raw["property_descriptions"], where)
        if set(descriptions) != set(properties):
            raise AllowlistFormatError(where)
        inject = _str_map(raw.get("inject", {}), where)
        if any(v != INJECT_SOURCE_AGENT_GROUP for v in inject.values()):
            raise AllowlistFormatError(where)
        patterns = _str_map(raw.get("property_patterns", {}), where)
        if not set(patterns) <= set(properties):
            raise AllowlistFormatError(where)
        if name in seen_names or (method, raw["path"]) in seen_ops:
            raise AllowlistFormatError(where)
        seen_names.add(name)
        seen_ops.add((method, raw["path"]))
        entries.append(AllowlistEntry(
            name=name, method=method, path=raw["path"], description=raw["description"],
            properties=properties, property_descriptions=descriptions,
            requires_agent=raw["requires_agent"],
            strip_body_fields=_str_list(raw.get("strip_body_fields", []), where),
            inject=inject, rename=_str_map(raw.get("rename", {}), where),
            property_patterns=patterns,
        ))
    return Allowlist(entries=tuple(sorted(entries, key=lambda e: e.name)))


# ---- openapi 讀取 ----------------------------------------------------------------------
def _resolve(openapi: Mapping[str, Any], schema: Any, depth: int = 0) -> Any:
    """解析單層 `#/components/schemas/<name>` 參照；遞迴解析巢狀結構。"""
    if depth > 32:
        return schema
    if isinstance(schema, dict):
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            target = openapi.get("components", {}).get("schemas", {}).get(
                ref[len("#/components/schemas/"):]
            )
            return _resolve(openapi, target, depth + 1) if isinstance(target, dict) else schema
        return {k: _resolve(openapi, v, depth + 1) for k, v in schema.items()}
    if isinstance(schema, list):
        return [_resolve(openapi, v, depth + 1) for v in schema]
    return schema


def _operation(openapi: Mapping[str, Any], entry: AllowlistEntry) -> Optional[dict]:
    paths = openapi.get("paths")
    if not isinstance(paths, Mapping):
        return None
    item = paths.get(entry.path)
    if not isinstance(item, Mapping):
        return None
    op = item.get(entry.method.lower())
    if not isinstance(op, Mapping):
        return None
    params = []
    for source in (item.get("parameters"), op.get("parameters")):
        if isinstance(source, list):
            params.extend(p for p in source if isinstance(p, Mapping))
    return {"operation": op, "parameters": params}


def _property_names_anywhere(schema: Any) -> list[str]:
    """遞迴列出 schema 內任何深度的屬性名（含 items、anyOf／oneOf／allOf、additionalProperties）。"""
    names: list[str] = []
    if isinstance(schema, Mapping):
        props = schema.get("properties")
        if isinstance(props, Mapping):
            for key, sub in props.items():
                names.append(str(key))
                names.extend(_property_names_anywhere(sub))
        for key in ("items", "additionalProperties", "not"):
            if key in schema:
                names.extend(_property_names_anywhere(schema[key]))
        for key in ("anyOf", "oneOf", "allOf", "prefixItems"):
            if isinstance(schema.get(key), list):
                for sub in schema[key]:
                    names.extend(_property_names_anywhere(sub))
        pattern_props = schema.get("patternProperties")
        if isinstance(pattern_props, Mapping):
            for sub in pattern_props.values():
                names.extend(_property_names_anywhere(sub))
    elif isinstance(schema, list):
        for sub in schema:
            names.extend(_property_names_anywhere(sub))
    return names


def has_credential_like_property(input_schema: Mapping[str, Any]) -> bool:
    """`BR72.7`：任何深度的屬性名命中黑名單底線。"""
    return any(CREDENTIAL_LIKE.search(name) for name in _property_names_anywhere(input_schema))


def _clean_schema(schema: Any) -> dict:
    """複製參數或本體屬性的 schema，去掉 openapi 的 title 與 description。"""
    if not isinstance(schema, Mapping):
        return {}
    cleaned = copy.deepcopy(dict(schema))
    cleaned.pop("title", None)
    cleaned.pop("description", None)
    return cleaned


def _requires_agent_ok(method: str, inject: Mapping[str, str], requires_agent: bool) -> bool:
    """`BR72.10`：method 不是 GET 或有 inject 時，requires_agent 必須為 true。"""
    return requires_agent or (method == "GET" and not inject)


def _build_one(openapi: Mapping[str, Any], entry: AllowlistEntry) -> ToolSpec:
    name = entry.name
    # (1) 路徑前綴白名單
    if not any(entry.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
        raise GeneratorError("path_outside_scope", name)
    # (2) operation 必須存在
    found = _operation(openapi, entry)
    if found is None:
        raise GeneratorError("missing_operation", name)
    op, params = found["operation"], found["parameters"]
    # (3) 參數位置
    path_params: dict[str, dict] = {}
    query_params: dict[str, dict] = {}
    required_api: set[str] = set()
    for raw_param in params:
        param = _resolve(openapi, raw_param)
        location, pname = param.get("in"), param.get("name")
        if location in ("header", "cookie"):
            raise GeneratorError("unsupported_parameter_location", name)
        if not isinstance(pname, str):
            raise GeneratorError("unsupported_parameter_location", name)
        target = path_params if location == "path" else query_params if location == "query" else None
        if target is None:
            raise GeneratorError("unsupported_parameter_location", name)
        target[pname] = _resolve(openapi, param.get("schema", {}))
        if location == "path" or param.get("required") is True:
            required_api.add(pname)
    # (4) 本體：只接受 application/json 且 schema 為 object
    body_props: dict[str, Any] = {}
    body_required: set[str] = set()
    request_body = op.get("requestBody")
    if request_body is not None:
        request_body = _resolve(openapi, request_body)
        content = request_body.get("content") if isinstance(request_body, Mapping) else None
        if not isinstance(content, Mapping) or set(content) != {_JSON_MEDIA}:
            raise GeneratorError("unsupported_body", name)
        schema = _resolve(openapi, content[_JSON_MEDIA].get("schema"))
        if not isinstance(schema, Mapping) or schema.get("type") != "object":
            raise GeneratorError("unsupported_body", name)
        props = schema.get("properties", {})
        if not isinstance(props, Mapping):
            raise GeneratorError("unsupported_body", name)
        body_props = {str(k): v for k, v in props.items()}
        if isinstance(schema.get("required"), list):
            body_required = {str(r) for r in schema["required"]}
    # (5) 名稱衝突
    param_names = set(path_params) | set(query_params)
    if param_names & set(body_props) or set(path_params) & set(query_params):
        raise GeneratorError("name_collision", name)
    # (6) inject 的鍵必須是被剝除的本體屬性
    if not set(entry.inject) <= set(entry.strip_body_fields):
        raise GeneratorError("inject_without_strip", name)
    # (7) requires_agent 與 method／inject 綁定
    if not _requires_agent_ok(entry.method, entry.inject, entry.requires_agent):
        raise GeneratorError("agent_requirement_mismatch", name)

    # 套用 strip 與 rename
    for stripped in entry.strip_body_fields:
        body_props.pop(stripped, None)
        body_required.discard(stripped)
    rename = dict(entry.rename)

    def tool_name(api_name: str) -> str:
        return rename.get(api_name, api_name)

    properties: dict[str, dict] = {}
    required: set[str] = set()
    binding_path: dict[str, str] = {}
    binding_query: dict[str, str] = {}
    binding_body: dict[str, str] = {}
    for api_name, schema in sorted(path_params.items()):
        properties[tool_name(api_name)] = _clean_schema(schema)
        binding_path[tool_name(api_name)] = api_name
    for api_name, schema in sorted(query_params.items()):
        properties[tool_name(api_name)] = _clean_schema(schema)
        binding_query[tool_name(api_name)] = api_name
    for api_name, schema in sorted(body_props.items()):
        properties[tool_name(api_name)] = _clean_schema(_resolve(openapi, schema))
        binding_body[tool_name(api_name)] = api_name
    for api_name in required_api | body_required:
        if api_name in path_params or api_name in query_params or api_name in body_props:
            required.add(tool_name(api_name))
    if len(properties) != len(binding_path) + len(binding_query) + len(binding_body):
        # 改名使兩個屬性同名
        raise GeneratorError("name_collision", name)

    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
        "additionalProperties": False,
    }
    # (8) 黑名單底線：改名之後、白名單之前，遞迴任何深度
    if has_credential_like_property(input_schema):
        raise GeneratorError("credential_like_property", name)
    # (9) 白名單相等
    if set(properties) != set(entry.properties):
        raise GeneratorError("whitelist_mismatch", name)
    # (10) 全部屬性必須是 string
    composite = {"properties", "items", "anyOf", "oneOf", "allOf", "additionalProperties",
                 "patternProperties", "prefixItems", "not", "$ref"}
    for prop_schema in properties.values():
        if prop_schema.get("type") != "string" or composite & set(prop_schema):
            raise GeneratorError("unsupported_body", name)

    for prop_name, prop_schema in properties.items():
        prop_schema["description"] = entry.property_descriptions[prop_name]
        if prop_name in entry.property_patterns:
            prop_schema["pattern"] = entry.property_patterns[prop_name]
        if prop_name in binding_body and prop_name in required:
            prop_schema["minLength"] = 1
    input_schema["properties"] = {k: properties[k] for k in sorted(properties)}

    binding = {
        "method": entry.method,
        "path": entry.path,
        "path_params": binding_path,
        "query_params": binding_query,
        "body_params": binding_body,
        "inject": dict(sorted(entry.inject.items())),
    }
    return ToolSpec(name=name, description=entry.description, input_schema=input_schema,
                    requires_agent=entry.requires_agent, binding=binding)


def generate_tools(openapi: Mapping[str, Any], allowlist: Allowlist) -> tuple[ToolSpec, ...]:
    """`BR72.1`：純函式、決定性、依工具名排序。"""
    specs = [_build_one(openapi, entry) for entry in sorted(allowlist.entries, key=lambda e: e.name)]
    return tuple(sorted(specs, key=lambda spec: spec.name))


# ---- 產物序列化 --------------------------------------------------------------------------
def dump_specs(specs: tuple[ToolSpec, ...]) -> str:
    """`generated_tools.json` 的位元決定性文字：排序鍵、固定縮排、結尾換行。"""
    document = {"version": 1, "tools": [spec.to_json() for spec in specs]}
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_specs(document: Any) -> tuple[ToolSpec, ...]:
    """解析 `generated_tools.json` 的內容；結構不合拋 `ValueError`。"""
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("generated_tools.json")
    tools = document.get("tools")
    if not isinstance(tools, list):
        raise ValueError("generated_tools.json")
    specs = tuple(ToolSpec.from_json(item) for item in tools)
    if len({spec.name for spec in specs}) != len(specs):
        raise ValueError("generated_tools.json")
    return specs


# ---- 啟動時的自我驗證（`BR71.5`） ---------------------------------------------------------
def validate_tool_specs(specs: tuple[ToolSpec, ...], allowlist: Allowlist) -> None:
    """以 `allowlist.json` 為獨立參考重驗已載入的產物（functional-design 審查 R-12 擇 (a)）。

    檢查順序與 `generate_tools` 對應：路徑前綴 → requires_agent 綁定 → 黑名單底線 → 白名單相等
    （含工具集合、method／path 與 inputSchema 形狀）→ binding 映射、inject 與 pattern 與 allowlist 推導值相等
    （程式審查 R-10）。任一不過拋 `GeneratorError`。
    """
    reference = allowlist.by_name()
    for spec in sorted(specs, key=lambda s: s.name):
        method = spec.binding.get("method")
        path = spec.binding.get("path")
        inject = spec.binding.get("inject") or {}
        if not isinstance(path, str) or not any(path.startswith(p) for p in ALLOWED_PATH_PREFIXES):
            raise GeneratorError("path_outside_scope", spec.name)
        if not _requires_agent_ok(method, inject, spec.requires_agent):
            raise GeneratorError("agent_requirement_mismatch", spec.name)
        if has_credential_like_property(spec.input_schema):
            raise GeneratorError("credential_like_property", spec.name)
        entry = reference.get(spec.name)
        props = spec.input_schema.get("properties")
        if (
            entry is None
            or entry.method != method
            or entry.path != path
            or entry.requires_agent != spec.requires_agent
            or not isinstance(props, Mapping)
            or set(props) != set(entry.properties)
            or spec.input_schema.get("type") != "object"
            or spec.input_schema.get("additionalProperties") is not False
        ):
            raise GeneratorError("whitelist_mismatch", spec.name)
        bound = set(spec.binding.get("path_params", {})) | set(spec.binding.get("query_params", {})) \
            | set(spec.binding.get("body_params", {}))
        if bound != set(props):
            raise GeneratorError("whitelist_mismatch", spec.name)
        # 程式審查 R-10：binding 內每個映射的 API 名稱、inject 與屬性 pattern 必須等於由 allowlist 推導的值。
        # 手改產物若移除 inject（寫入少了 on_behalf_of）或把某個工具屬性映射到被剝除的欄位
        # （呼叫端得以指定溯源標示），都在啟動時被擋下。
        inverse = {tool: api for api, tool in entry.rename.items()}
        for key in ("path_params", "query_params", "body_params"):
            for tool_name, api_name in spec.binding.get(key, {}).items():
                if api_name != inverse.get(tool_name, tool_name) or api_name in entry.strip_body_fields:
                    raise GeneratorError("whitelist_mismatch", spec.name)
        if dict(inject) != dict(entry.inject):
            raise GeneratorError("inject_without_strip", spec.name)
        patterns = {name: schema.get("pattern") for name, schema in props.items()
                    if isinstance(schema, Mapping) and "pattern" in schema}
        if patterns != dict(entry.property_patterns):
            raise GeneratorError("whitelist_mismatch", spec.name)
    missing = sorted(set(reference) - {spec.name for spec in specs})
    if missing:
        raise GeneratorError("whitelist_mismatch", missing[0])
