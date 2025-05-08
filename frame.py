class LightControlFrame:
    def __init__(self):
        self.action = None
        self.device = None
        self.color = None
        self.brightness = None
        self._history = []

    def update(self, result: dict):
        if "action" in result and not self.action:
            self.action = result["action"]
            self._history.append('action')
        if "light_entity" in result and not self.device:
            self.device = result["light_entity"]
            self._history.append('device')
        if "color" in result and not self.color:
            self.color = result["color"]
            self._history.append('color')
        if "brightness" in result and not self.brightness:
            try:
                self.brightness = int(result["brightness"])
            except ValueError:
                self.brightness = None
            self._history.append('brightness')

    def missing_slots(self):
        missing = []
        if not self.action:
            missing.append("action")
        if not self.device:
            missing.append("device")
        # color a brightness jsou nepovinné
        return missing

    @property
    def complete(self):
        return self.action is not None and self.device is not None

    def undo_last(self):
        if not self._history:
            return False

        last = self._history.pop()

        if last == "action":
            self.action = None
        elif last == "device":
            self.device = None
        elif last == "color":
            self.color = None
        elif last == "brightness":
            self.brightness = None
        else:
            return False
        return True

    def __str__(self):
        return f"[Light] {self.action or '?'} světlo  barva {self.color or '?'} jas {self.brightness or '?'} v '{self.device or '?'}'"



class TemperatureControlFrame:
    def __init__(self):
        self.temperature = None
        self.device = None  # entity_id zařízení (např. "climate.obyvak")
        self._history = []

    def update(self, result: dict):
        if "temperature" in result and not self.temperature:
            self.temperature = result["temperature"]
            self._history.append("temperature")
        if "climate_entity" in result and not self.device:
            self.device = result["climate_entity"]
            self._history.append("device")

    def undo_last(self):
        if not self._history:
            return False
        last = self._history.pop()
        setattr(self, last, None)
        return True

    @property
    def complete(self):
        return self.temperature is not None and self.device is not None

    def missing_slots(self):
        missing = []
        if not self.temperature:
            missing.append("temperature")
        if not self.device:
            missing.append("device")
        return missing

    def __str__(self):
        return f"[Temp] Nastavit teplotu na {self.temperature}°C v '{self.device or '?'}'"


class QueryFrame:
    def __init__(self):
        self.query_type = None
        self.device = None  # light_entity nebo climate_entity
        self._history = []

    def update(self, result: dict):
        if "query" in result and not self.query_type:
            self.query_type = result["query"]
            self._history.append("query_type")
        if ("light_entity" in result or "climate_entity" in result) and not self.device:
            self.device = result.get("light_entity") or result.get("climate_entity")
            self._history.append("device")

    def undo_last(self):
        if not self._history:
            return False
        last = self._history.pop()
        setattr(self, last, None)
        return True

    @property
    def complete(self):
        return self.query_type is not None and self.device is not None

    def missing_slots(self):
        missing = []
        if not self.query_type:
            missing.append("query_type")
        if not self.device:
            missing.append("device")
        return missing

    def __str__(self):
        return f"[Query] Zjistit '{self.query_type or '?'}' pro '{self.device or '?'}'"

class SceneFrame:
    def __init__(self):
        self.scene = None
        self._history = []

    def update(self, result: dict):
        if "scene" in result and not self.scene:
            self.scene = result["scene"]
            self._history.append("scene")

    def missing_slots(self):
        return ["scene"] if not self.scene else []

    @property
    def complete(self):
        return self.scene is not None

    def undo_last(self):
        if not self._history:
            return False
        last = self._history.pop()
        if last == "scene":
            self.scene = None
            return True
        return False

    def __str__(self):
        return f"[Scene] {self.scene or '?'}"


