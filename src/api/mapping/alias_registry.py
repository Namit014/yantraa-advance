class AliasRegistry:
    """
    Alias Knowledge Base
    Stores mechanical, electrical, robotics, and manufacturer aliases to remove duplicate nodes.
    """
    def __init__(self):
        self.aliases = {
            "nema23": ["nema 23", "23hs45", "stepper motor nema23"],
            "l298n": ["l298", "l298n motor driver", "dual h-bridge"],
            "esp32": ["esp-32", "esp32 wroom", "esp32-wrover"]
        }

    def get_canonical_name(self, raw_name: str) -> str:
        lower_name = raw_name.lower().strip()
        for canonical, alias_list in self.aliases.items():
            if lower_name == canonical or lower_name in alias_list:
                return canonical
        return lower_name
