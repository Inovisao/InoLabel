from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class KeybindMap:
    name: str
    bindings: Dict[str, str] = field(default_factory=dict)  # action_id → key string

    def get_key(self, action: str) -> Optional[str]:
        return self.bindings.get(action)

    def set_key(self, action: str, key: str) -> None:
        self.bindings[action] = key

    def conflicts_with(self, key: str, exclude_action: str) -> Optional[str]:
        """Retorna o id da ação que já usa `key`, ou None se livre."""
        if not key:
            return None
        for action, bound_key in self.bindings.items():
            if action != exclude_action and bound_key == key:
                return action
        return None

    def copy(self) -> "KeybindMap":
        return KeybindMap(name=self.name, bindings=copy.deepcopy(self.bindings))

    def to_dict(self) -> Dict[str, str]:
        return dict(self.bindings)
