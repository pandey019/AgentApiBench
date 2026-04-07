import json
import random
from pathlib import Path
from typing import Dict, Any


class ScenarioLoader:
    def __init__(self, scenarios_dir: Path):
        self.scenarios_dir = scenarios_dir
        self.scenarios = list(self.scenarios_dir.glob("*.json"))

    def load_random(self) -> Dict[str, Any]:
        if not self.scenarios:
            raise RuntimeError(f"No scenarios found in {self.scenarios_dir}")
        scenario_file = random.choice(self.scenarios)
        with open(scenario_file, "r") as f:
            return json.load(f)
