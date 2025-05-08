import requests

class HA:
    def __init__(self, token: str):
        """
        Inicializuje objekt pro komunikaci s Home Assistant API.
        
        :param base_url: Základní URL adresa instance Home Assistanta,  "http://localhost:8123"
        :param token: Dlouhodobý přístupový token (Long-Lived Access Token)
        """
        # self.base_url = "http://homeassistant.local:8123/api"
        self.base_url = "https://mubxwqflswxbowpezhgi0tvzx5f3vrk0.ui.nabu.casa/api"

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _call_service(self, domain: str, service: str, data: dict):
        """
        Interní metoda pro volání služby přes REST API Home Assistanta.
        
        :param domain: Doména zařízení (např. "light", "climate")
        :param service: Název služby (např. "turn_on", "set_temperature")
        :param data: Tělo požadavku jako slovník
        :return: JSON odpověď z Home Assistanta
        """
        url = f"{self.base_url}/services/{domain}/{service}"
        response = requests.post(url, json=data, headers=self.headers)
        if response.status_code not in (200, 201):
            raise Exception(f"Chyba při volání služby: {response.status_code} - {response.text}")
        return response.json()

    def control_light(self, action: str, entity_id: str, brightness: int = None, color_name: str = None):
        data = {"entity_id": entity_id}
        if action == "on":
            if brightness is not None:
               if 0 <= brightness <= 255:
                    data["brightness"] = brightness
            if color_name:
                data["color_name"] = color_name
        if action == "on":
            return self._call_service("light", "turn_on", data)
        elif action == "off":
             return self._call_service("light", "turn_off", data)
        else:
            raise ValueError(f"Neznámá akce: {action}")

    def set_temperature(self, entity_id: str, temperature: float):
        """
        Nastaví cílovou teplotu pro klimatizaci nebo termostat.

        :param entity_id: ID zařízení, např. "climate.living_room"
        :param temperature: Cílová teplota ve stupních Celsia
        :return: Výsledek požadavku
        """
        data = {
            "entity_id": entity_id,
            "temperature": temperature
        }
        return self._call_service("climate", "set_temperature", data)

    def get_state(self, entity_id: str):
        """
        Získá aktuální stav zařízení (např. jestli je světlo zapnuté, aktuální teplota apod.)

        :param entity_id: ID zařízení
        :return: Stav zařízení jako slovník (JSON)
        """
        url = f"{self.base_url}/states/{entity_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Chyba při získávání stavu: {response.status_code} - {response.text}")
        return response.json()
    
    def get_all_entities(self):
        """
        Načte seznam všech entit v Home Assistantu (např. světla, klimatizace, senzory).
        
        :return: Seznam entit jako slovníky (JSON array)
        """
        url = f"{self.base_url}/states"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Chyba při získávání entit: {response.status_code} - {response.text}")
        return response.json()
    
    def get_friendly_names_by_domain(self, domain: str) -> dict[str, str]:
        """
        Vrátí slovník {friendly_name: entity_id} pro danou doménu (např. 'light', 'climate').

        :param domain: Doména Home Assistant zařízení (např. 'light', 'climate', 'switch')
        :return: Slovník {friendly_name: entity_id}
        """
        entities = self.get_all_entities()
        mapping = {}

        for entity in entities:
            entity_id = entity.get("entity_id", "")
            attrs = entity.get("attributes", {})
            friendly_name = attrs.get("friendly_name")

            if entity_id.startswith(domain + ".") and friendly_name:
                mapping[entity_id] = friendly_name

        return mapping

    
    def toggle_light(self, entity_id: str):
        """
        Přepne světlo podle aktuálního stavu – zapne nebo vypne.
        """
        state = self.get_state(entity_id)
        if state.get("state") == "on":
            return self.control_light("off", entity_id)
        else:
            return self.control_light("on", entity_id)

    def set_light_color(self, entity_id: str, color_name: str):
        """
        Nastaví barvu RGB světla podle názvu barvy (např. 'red', 'blue').
        """
        data = {
            "entity_id": entity_id,
            "color_name": color_name
        }
        return self._call_service("light", "turn_on", data)

    def set_light_temperature(self, entity_id: str, mireds: int):
        """
        Nastaví teplotu bílé barvy světla v jednotkách mired (např. 250 = teplá bílá).
        """
        data = {
            "entity_id": entity_id,
            "color_temp": mireds
        }
        return self._call_service("light", "turn_on", data)

    def get_temperature(self, entity_id: str):
        """
        Získá aktuální teplotu z teplotního senzoru nebo klimatizace.
        """
        state = self.get_state(entity_id)
        attrs = state.get("attributes", {})
        return attrs.get("current_temperature")

    def get_entities_by_domain(self, domain: str):
        """
        Vrátí seznam všech entity_id patřících do dané domény (např. 'light', 'climate').
        """
        entities = self.get_all_entities()
        return [e["entity_id"] for e in entities if e["entity_id"].startswith(domain + ".")]

    def get_attributes(self, entity_id: str):
        """
        Vrátí celý slovník atributů dané entity.
        """
        state = self.get_state(entity_id)
        return state.get("attributes", {})