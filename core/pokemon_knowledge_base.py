import os
import pandas as pd
from typing import Optional, Dict, List

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
POKEMON_CSV_PATH = os.path.join(DATA_DIR, 'pokemon_data.csv')

try:
    _df = pd.read_csv(POKEMON_CSV_PATH, encoding='utf-8')
except Exception as e:
    print(f"[寶可夢知識庫] 載入失敗: {e}")
    _df = pd.DataFrame(columns=["id", "zh_name", "en_name", "ja_name"])

_pokemon_dict = {row['zh_name']: row.to_dict() for _, row in _df.iterrows()}


def get_pokemon_details_by_zh_name(zh_name: str) -> Optional[Dict[str, str]]:
    return _pokemon_dict.get(zh_name)


def format_pokemon_names_for_prompt(user_input: str) -> str:
    names = [name.strip() for name in user_input.split(',') if name.strip()]
    formatted = []
    for name in names:
        details = get_pokemon_details_by_zh_name(name)
        if details:
            formatted.append(f"{details['zh_name']} ({details['en_name']})")
        else:
            formatted.append(name)
    return ', '.join(formatted)

if __name__ == "__main__":
    print("[測試] 查詢皮卡丘:", get_pokemon_details_by_zh_name("皮卡丘"))
    print("[測試] 格式化: 皮卡丘, 伊布, 超夢 =>", format_pokemon_names_for_prompt("皮卡丘, 伊布, 超夢"))
    print("[測試] 格式化: 小火龍, 妙蛙種子, 不存在寶可夢 =>", format_pokemon_names_for_prompt("小火龍, 妙蛙種子, 不存在寶可夢"))