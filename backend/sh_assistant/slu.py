from collections import defaultdict
from backend.utils import load_grammars, extended_friendly_names, load_scenes


def build_reverse_index(categories):
    """
    Builds a reverse index mapping phrases to their corresponding slot and value.

    Args:
        categories (dict): Dictionary of slot categories (e.g., "color", "brightness") 
                        where keys are slot names and values are dicts {value: set of phrases}.

    Returns:
        dict: Mapping from phrase (str) to list of (slot_name, value) tuples.
    """

    reverse = defaultdict(list)
    for slot_name, slot_dict in categories.items():
        for value, phrases in slot_dict.items():
            for phrase in phrases:
                reverse[phrase].append((slot_name, value))
    return reverse

def initialize_slu(assistant):
    """
    Initializes the SLU component of the assistant.

    Loads extended friendly names, scene grammar and grammars.json,
    and builds the reverse index for phrase-based slot detection.

    Args:
        assistant (Dialog): Instance of the assistant (SHAssistant).
    """

    grammars = load_grammars()
    extended_light = extended_friendly_names(assistant.ha.get_friendly_names_by_domain("light"))
    extended_climate = extended_friendly_names(assistant.ha.get_friendly_names_by_domain("climate"))
    raw_switches = assistant.ha.get_friendly_names_by_domain("switch")
    filtered_switches = {
        entity_id: names
        for entity_id, names in raw_switches.items()
        if "detsky_zamek" not in entity_id and "security_camera" not in entity_id
    }
    extended_switch = extended_friendly_names(filtered_switches)


    scene_phrases = {}
    for scene_name in load_scenes().keys():
        normalized = scene_name.lower().strip()
        scene_phrases[normalized] = {scene_name, normalized, normalized.replace(" ", "")}
    scene_grammar = {k: set(v) for k, v in scene_phrases.items()}

    assistant.REVERSE_INDEX = build_reverse_index({
        "action": grammars["ACTION"],
        "temperature": grammars["TEMPERATURE"],
        "brightness": grammars["BRIGHTNESS"],
        "color": grammars["COLOR"],
        "query": grammars["QUERY_TYPE"],
        "bool_response": grammars["BOOL_RESPONSE"],
        "target": grammars["TARGET"],
        "light_entity": extended_light,
        "climate_entity": extended_climate,
        "switch_entity": extended_switch,
        "scene": scene_grammar,
    })

def slu(assistant, text: str) -> dict:
    """
    Extracts slots from input text using a reverse phrase index.

    Args:
        assistant (Dialog): The assistant object containing the REVERSE_INDEX.
        text (str): Input user command or sentence.

    Returns:
        dict: Detected slots and their values (e.g., {"action": "on", "color": "red"}).
    """

    text = text.lower()
    found = {}

    for phrase, slots in assistant.REVERSE_INDEX.items():
        if phrase in text:
            for slot_name, value in slots:
                if slot_name not in found:
                    found[slot_name] = value
    return found
