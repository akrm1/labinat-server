from typing import Any, Mapping
from datetime import datetime, timezone
import json
import yaml
from jsonpath_ng import parse
import uuid

def generate_unique_id() -> str:
    return str(uuid.uuid4())

def utcnow() -> datetime:
    """Naive UTC now, matching how SQLite round-trips `DateTime` columns.

    SQLite has no timezone-aware type, so stored values come back naive.
    Using this for every persisted timestamp keeps comparisons against
    columns like `expires_at` from raising on naive-vs-aware mismatches.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

def asjson(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)

def asyaml(obj: Any) -> str:
    return yaml.dump(obj, indent=2, allow_unicode=True, sort_keys=False, default_flow_style=False)

def load_yaml(filepath: str) -> Any:
    with open(filepath, "r") as file:
        return yaml.safe_load(file)

def load_json(filepath: str) -> Any:
    with open(filepath, "r") as file:
        return json.load(file)

def save_yaml(filepath: str, obj: Any) -> None:
    with open(filepath, "w") as file:
        yaml.dump(obj, file, indent=2, allow_unicode=True, sort_keys=False, default_flow_style=False)

def save_json(filepath: str, obj: Any) -> None:
    with open(filepath, "w") as file:
        json.dump(obj, file, indent=2, ensure_ascii=False, default=str)

def jsonpath(jsondata, attribute_path: str):
    path = (attribute_path or "").strip()
    if not path:
        raise ValueError("attribute path must be non-empty")
    
    if path.startswith("$"):
        expr = path
    else:
        path = path.lstrip(".")
        expr = "$" if not path else f"$.{path}"
    
    match = parse(expr).find(jsondata)
    if len(match) == 0:
        raise KeyError(f"Key \'{attribute_path}\' not found")
        
    return match[0].value

def flatten_dict(dictionary: Any, parent: str = "", sep: str = ".") -> dict[str, Any]:
    out: dict[str, Any] = {}

    def add_leaf(path: str, value: Any) -> None:
        out[path or "$"] = value

    def walk(node: Any, prefix: str) -> None:
        if isinstance(node, Mapping):
            for k, v in node.items():
                # safe key segment for simple identifiers
                seg = k if isinstance(k, str) and k.isidentifier() else str(k)
                p = f"{prefix}{sep}{seg}" if prefix else seg
                walk(v, p)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                p = f"{prefix}[{i}]" if prefix else f"[{i}]"
                walk(v, p)
        else:
            add_leaf(prefix, node)

    walk(dictionary, parent)
    return out