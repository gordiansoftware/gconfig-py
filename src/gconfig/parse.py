from typing import Any, Optional


def parse_entry(typ: type, val: Any) -> Optional[Any]:
    if typ == str:
        return str(val) if val is not None else None
    elif typ == int:
        return int(val) if val is not None else None
    elif typ == float:
        return float(val) if val is not None else None
    elif typ == bool:
        return (
            (val if type(val) == bool else val.lower() == "true")
            if val is not None
            else None
        )
    return None
