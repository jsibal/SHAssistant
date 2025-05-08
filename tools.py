import json
import os
from dotenv import load_dotenv
load_dotenv()

def ask_missing_slot_static(missing_slots: list[str]) -> str:
    dotazy = {
        "action": "Jakou akci mám provést - zapnutí, vypnutí, nebo se chcete zeptat?",
        "device": "Jaké zařízení myslíte?",
        "brightness": "Jak silné světlo si přejete?",
        "temperature": "Na kolik stupňů?",
        "query_type": "Na co se chcete zeptat - stav, teplota, jas nebo barva?",
        "scene":"Jakou scénu chcete aktivovat?"
    }
    otazky = [dotazy[s] for s in missing_slots if s in dotazy]
    return " ".join(otazky)

def load_or_create_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def extended_friendly_names(friendly_dict: dict[str, str]) -> dict[str, set[str]]:
    data = load_or_create_json(os.getenv("FRIENDLY_NAMES"))
    result = {}

    for entity_id, new_name in friendly_dict.items():
        if not new_name:
            continue

        # Načíst existující jména jako množinu
        existing = set(data.get(entity_id, {}).get("friendly_names", []))
        existing.add(new_name)  # Přidat nové jméno

        # Uložit zpět do dat
        data[entity_id] = {"friendly_names": list(existing)}
        result[entity_id] =  existing # Do výsledku jako množina

    save_json(os.getenv("FRIENDLY_NAMES"), data)
    return result


def load_grammars():
    with open(os.getenv("GRAMMAR_PATH"), "r", encoding="utf-8") as f:
        data = json.load(f)
        # převod string "true"/"false" zpět na boolean pro BOOL_RESPONSE
        if "BOOL_RESPONSE" in data:
            data["BOOL_RESPONSE"] = {
                True: set(data["BOOL_RESPONSE"].get("true", [])),
                False: set(data["BOOL_RESPONSE"].get("false", []))
            }
        # všechny ostatní slovníky převést na {key: set(values)}
        for key, value in data.items():
            if key != "BOOL_RESPONSE":
                data[key] = {k: set(v) for k, v in value.items()}
        return data
    
   
def grammar_to_json_safe(grammar):
    result = {}
    for key, value in grammar.items():
        if isinstance(value, dict):
            result[key] = {k: list(v) for k, v in value.items()}
        elif isinstance(value, set):
            result[key] = list(value)
        else:
            result[key] = value
    return result

def save_grammars(grammar_dict):
    with open(os.getenv("GRAMMAR_PATH"), "w", encoding="utf-8") as f:
        json.dump(grammar_dict, f, indent=2, ensure_ascii=False)


def load_scenes():
    if os.path.exists(os.getenv("SCENES_PATH")):
        with open(os.getenv("SCENES_PATH"), "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_scene(name: str, actions: list[dict]):
    scenes = load_scenes()
    scenes[name] = { "actions": actions }
    with open(os.getenv("SCENES_PATH"), "w", encoding="utf-8") as f:
        json.dump(scenes, f, indent=4, ensure_ascii=False)