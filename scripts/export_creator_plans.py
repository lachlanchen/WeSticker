"""Export the existing caption sets for offline native and web planning."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.store import THEMES

value = {
    "version": 1,
    "mode": "on-device-template-planner",
    "themes": THEMES,
    "keywords": {
        "daily": ["daily", "everyday", "日常", "毎日"],
        "office": ["work", "office", "boss", "工作", "上班", "仕事", "職場"],
        "couple": ["couple", "love", "hug", "情侣", "恋爱", "恋人", "カップル"],
        "sports": ["sport", "exercise", "gym", "workout", "运动", "健身", "運動", "スポーツ"],
    },
}
if __name__ == "__main__":
    (ROOT / "public/creator-plans.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print("Shared offline caption sets exported.")
