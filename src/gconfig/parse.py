from typing import Any, Optional, TypeVar

T = TypeVar("T")

def parse_entry(typ: type[T], val: Any) -> Optional[T]:
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
