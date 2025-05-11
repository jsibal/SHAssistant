import asyncio
import json
import os
from dotenv import load_dotenv
load_dotenv()

def ask_missing_slot_static(missing_slots: list[str]) -> str:
    """
    Returns a prompt question for each missing slot to guide the user.

    Args:
        missing_slots (list[str]): List of missing slot names.

    Returns:
        str: Concatenated prompt string.
    """

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
    """
    Loads a JSON file if it exists, otherwise returns an empty dictionary.

    Args:
        path (str): Path to the JSON file.

    Returns:
        dict: Loaded JSON data or an empty dictionary.
    """

    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(path, data):
    """
    Saves a dictionary as a JSON file.

    Args:
        path (str): Path to the output file.
        data (dict): Data to save.
    """

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def extended_friendly_names(friendly_dict: dict[str, str]) -> dict[str, set[str]]:
    """
    Extends and saves friendly names for given entities.

    Args:
        friendly_dict (dict[str, str]): Mapping of entity_id to new friendly name.

    Returns:
        dict[str, set[str]]: Updated mapping of entity_id to all known friendly names.
    """

    data = load_or_create_json(os.getenv("FRIENDLY_NAMES"))
    result = {}

    for entity_id, new_name in friendly_dict.items():
        if not new_name:
            continue

        # Načíst existující jména jako množinu
        existing = set(data.get(entity_id, {}).get("friendly_names", []))
        existing.add(new_name)  # Přidat nové jméno


        data[entity_id] = {"friendly_names": list(existing)}
        result[entity_id] =  existing 

    save_json(os.getenv("FRIENDLY_NAMES"), data)
    return result


def load_grammars():
    """
    Loads grammar definitions from a JSON file and converts them to usable format.

    Returns:
        dict: Grammar data with slot names and synonyms.
    """

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
    """
    Converts in-memory grammar data with sets to a JSON-serializable structure.

    Args:
        grammar (dict): Grammar with sets and dicts.

    Returns:
        dict: JSON-serializable version of the grammar.
    """

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
    """
    Saves grammar definitions to a JSON file.

    Args:
        grammar_dict (dict): Grammar data to save.
    """

    with open(os.getenv("GRAMMAR_PATH"), "w", encoding="utf-8") as f:
        json.dump(grammar_dict, f, indent=2, ensure_ascii=False)


def load_scenes():
    """
    Loads scene definitions from a JSON file.

    Returns:
        dict: Mapping of scene names to action lists.
    """

    if os.path.exists(os.getenv("SCENES_PATH")):
        with open(os.getenv("SCENES_PATH"), "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_scene(name: str, actions: list[dict]):
    """
    Saves a scene with a given name and list of actions.

    Args:
        name (str): Scene name.
        actions (list[dict]): List of actions in the scene.
    """

    scenes = load_scenes()
    scenes[name] = { "actions": actions }
    with open(os.getenv("SCENES_PATH"), "w", encoding="utf-8") as f:
        json.dump(scenes, f, indent=4, ensure_ascii=False)


async def activate_scene(self, scene_name: str):
        """
        Activates a predefined scene by executing its actions and sending messages.

        Args:
            self (Dialog): Assistant instance with access to Home Assistant and messaging.
            scene_name (str): Name of the scene to activate.
        """

        scenes = load_scenes()
        scene = scenes.get(scene_name)

        if not scene:
            await self.send_message({
                "type": "chat-dm",
                "data": f"Scéna '{scene_name}' neexistuje."
            })
            return

        actions = scene.get("actions", [])

        for action in actions:
            self.on_receive_message(action)

        await self.send_message({
            "type": "chat-dm",
            "data": f"Scéna '{scene_name}' byla aktivována."
        })
        await asyncio.sleep(1) 
        await self.send_message({"type": "state_update","data": self.ha.get_all_entities()})
        
        if self.ttsEnabled:
            await self.synthesize_and_wait(f"Scéna {scene_name} byla aktivována.")