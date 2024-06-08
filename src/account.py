from dataclasses import dataclass
from typing import Optional


@dataclass
class Account:
    username: str
    password: str
    proxy: Optional[str] = None
