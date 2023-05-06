from typing import List, Tuple

def list_to_string(inp: List[Tuple[str,str]]) -> str:
    return "\n".join([f"{pred}{elm}" for pred,elm in inp])
    