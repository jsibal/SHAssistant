import requests

class HA:
    def __init__(self, url: str,token: str):
        """
        Initializes the Home Assistant API client.

        Args:
            url (str): Base URL of the Home Assistant instance (e.g., "http://localhost:8123/api").
            token (str): Long-lived access token for authenticating with Home Assistant.
        """

        # self.base_url = "http://homeassistant.local:8123/api"
        self.base_url = url

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def is_alive(self):
        """
        Checks whether the Home Assistant API is operational using the /api/config endpoint.

        :return: True if the API responds with status 200, otherwise False.
        """

        url = f"{self.base_url}/config"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Chyba při kontrole API: {e}")
            return False

    def _call_service(self, domain: str, service: str, data: dict):
        """
        Sends a POST request to a Home Assistant service endpoint.

        Args:
            domain (str): Domain of the device (e.g., "light").
            service (str): Name of the service (e.g., "turn_on").
            data (dict): Payload to send with the request.

        Returns:
            Any: JSON response or error string.
        """

        url = f"{self.base_url}/services/{domain}/{service}"
        response = requests.post(url, json=data, headers=self.headers)
        if response.status_code not in (200, 201):
            return (f"Chyba při volání služby: {response.status_code} - {response.text}")
        return response.json()

    def control_light(self, action: str, entity_id: str, brightness: int = None, color_name: str = None):
        """
        Controls a light entity (on/off, brightness, color).

        Args:
            action (str): "on" or "off".
            entity_id (str): The entity ID of the light.
            brightness (int, optional): Brightness level (0–255).
            color_name (str, optional): Name of the color (e.g., "red").

        Returns:
            Any: API call result.
        """

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
            return f"Neznámá akce: {action}"
        
    def set_temperature(self, entity_id: str, temperature: float):
        """
        Sets the target temperature of a climate device.

        Args:
            entity_id (str): The climate entity ID.
            temperature (float): Target temperature in Celsius.

        Returns:
            Any: API call result.
        """

        data = {
            "entity_id": entity_id,
            "temperature": temperature
        }
        return self._call_service("climate", "set_temperature", data)

    def get_state(self, entity_id: str):
        """
        Retrieves the current state of a specific entity.

        Args:
            entity_id (str): Entity ID to query.

        Returns:
            dict: State data of the entity.
        """

        url = f"{self.base_url}/states/{entity_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return f"Chyba při získávání stavu: {response.status_code} - {response.text}"
        return response.json()
    
    def get_all_entities(self):
        """
        Retrieves all entities available in Home Assistant.

        Returns:
            list[dict]: List of all entity states.
        """

        url = f"{self.base_url}/states"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return f"Chyba při získávání entit: {response.status_code} - {response.text}"
        return response.json()
    
    def get_friendly_names_by_domain(self, domain: str) -> dict[str, str]:
        """
        Returns a mapping from entity ID to friendly name for a specific domain.

        Args:
            domain (str): Domain to filter (e.g., "light").

        Returns:
            dict[str, str]: Mapping of entity IDs to friendly names.
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
        Toggles a light entity on or off based on its current state.

        Args:
            entity_id (str): The light entity ID.

        Returns:
            Any: API call result.
        """

        state = self.get_state(entity_id)
        if state.get("state") == "on":
            return self.control_light("off", entity_id)
        else:
            return self.control_light("on", entity_id)

    def set_light_color(self, entity_id: str, color_name: str):
        """
        Sets the color of a light.

        Args:
            entity_id (str): The light entity ID.
            color_name (str): Name of the color to apply.

        Returns:
            Any: API call result.
        """

        data = {
            "entity_id": entity_id,
            "color_name": color_name
        }
        return self._call_service("light", "turn_on", data)

    def set_light_temperature(self, entity_id: str, mireds: int):
        """
        Sets the white color temperature of a light in mireds.

        Args:
            entity_id (str): Light entity ID.
            mireds (int): Color temperature value in mireds.

        Returns:
            Any: API call result.
        """

        data = {
            "entity_id": entity_id,
            "color_temp": mireds
        }
        return self._call_service("light", "turn_on", data)

    def get_temperature(self, entity_id: str):
        """
        Retrieves the current temperature from a climate entity.

        Args:
            entity_id (str): Climate entity ID.

        Returns:
            float: Current temperature, if available.
        """

        state = self.get_state(entity_id)
        attrs = state.get("attributes", {})
        return attrs.get("current_temperature")

    def get_entities_by_domain(self, domain: str):
        """
        Gets all entities belonging to a specific domain.

        Args:
            domain (str): Domain name (e.g., "switch").

        Returns:
            list[str]: List of entity IDs.
        """

        entities = self.get_all_entities()
        return [e["entity_id"] for e in entities if e["entity_id"].startswith(domain + ".")]

    def get_attributes(self, entity_id: str):
        """
        Returns the attributes of a specific entity.

        Args:
            entity_id (str): The entity ID.

        Returns:
            dict: Attributes dictionary.
        """

        state = self.get_state(entity_id)
        return state.get("attributes", {})
    
    def control_switch(self, action: str, entity_id: str):
        """
        Controls a smart switch (on or off).

        Args:
            action (str): "on" or "off".
            entity_id (str): The switch entity ID.

        Returns:
            Any: API call result.
        """

        if action == "on":
            return self._call_service("switch", "turn_on", {"entity_id": entity_id})
        elif action == "off":
            return self._call_service("switch", "turn_off", {"entity_id": entity_id})
        else:
            return f"Neznámá akce: {action}"
    def toggle_switch(self, entity_id: str):
        """
        Toggles a smart switch on or off based on its current state.

        Args:
            entity_id (str): The switch entity ID.

        Returns:
            Any: API call result.
        """

        state = self.get_state(entity_id)
        if state.get("state") == "on":
            return self.control_switch("off", entity_id)
        else:
            return self.control_switch("on", entity_id)

