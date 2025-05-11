import asyncio
import os
import logging
from dotenv import load_dotenv

from backend.dialog import Dialog
from backend.ha import HA
from backend.utils import load_or_create_json, save_json, load_scenes, save_scene, grammar_to_json_safe, save_grammars, load_grammars
from .frames.handle_switch import handle_switch
from .frames.handle_light import handle_light
from .frames.handle_temperature import handle_temperature
from .frames.handle_query import handle_query
from .frames.handle_scene import handle_scene
from .slu import initialize_slu, slu


class SHAssistant(Dialog):

    async def main(self):
        """
        Main entry point of the assistant after session start.
        Initializes environment, SLU, and enters dialog loop.
        """

        load_dotenv()
        self.running = True
        self.ttsEnabled = False
        self.stt = False
        self.TIMEOUT = os.getenv("TIMEOUT")
        self.pending_frame_update_frame = None
        self.pending_frame_update_handler = None
        self.history = []
        self.ha = HA(url=os.getenv("HA_URL"),token=os.getenv("HA_TOKEN"))

        initialize_slu(self)
        await self.dialog_loop()
        await self.synthesize_and_wait("Děkuji, končím.")
        await self.display_history()

    async def dialog_loop(self):
        """
        Main loop waiting for speech input and handling continuous recognition if enabled.
        """

        await self.send_message({"type": "init", "data": self.ha.get_all_entities()})
        await self.send_message({"type": "chat-dm", "data": "Pro ovládání pomocí řeči zmáčkni tlačítko mikrofonu"})

        self.running = True
        while self.running:
            result = await self.recognize_and_wait_for_asr_result(timeout=5.)
            while self.stt and self.running:
                await self.send_message({"type": "chat-dm", "data": "Řekněte příkaz."})
                if self.ttsEnabled:
                    await self.synthesize_and_wait("Řekněte příkaz.")
                result = await self.recognize_and_wait_for_asr_result(timeout=5.)
                if result:
                    await self.handle_slu_result(result["word_1best"])
                else:
                    message = "Nerozuměl jsem. Zkuste to znovu."
                    await self.send_message({"type": "chat-dm", "data": message})
                    if self.ttsEnabled:
                        await self.synthesize_and_wait(message)

    async def handle_slu_result(self, result, text=False):
        """
        Processes SLU result and dispatches to the appropriate handler based on intent.

        Args:
            result (str): Text input from user or ASR result.
            text (bool): True if the input came from text input, not speech.
        """

        result = slu(self, result)
        self.logger.debug(result)

        if result.get("action") == "end":
            msg = "Ukončuji dialog."
            await self.send_message({"type": "chat-dm", "data": msg})
            if self.ttsEnabled:
                await self.synthesize_and_wait("Děkuji, končím.")
            self.running = False
            return

        if result.get("query"):
            return await handle_query(self, result, text)

        if result.get("light_entity") or result.get("target") == "light" or result.get("color") or result.get("brightness"):
            return await handle_light(self, result, text)

        if result.get("climate_entity") or result.get("target") == "climate" or result.get("temperature"):
            return await handle_temperature(self, result, text)
        if result.get("switch_entity") or result.get("target") == "switch":
            return await handle_switch(self, result, text)
        if result.get("scene") or result.get("target") == "scene":
            return await handle_scene(self, result, text)

        msg = "Nerozuměl jsem, co chcete ovládat. Můžete to zkusit znovu?"
        await self.send_message({"type": "chat-dm", "data": msg})
        if self.ttsEnabled:
            await self.synthesize_and_wait(msg)

    def on_receive_message(self, data):
        """
        Handles incoming WebSocket messages and maps them to backend actions.

        Args:
            data (dict): A dictionary containing the message data (must include 'type').
        """


        self.logger.debug("Received message:\n%s", str(data))

        if not isinstance(data, dict) or "type" not in data:
            return

        msg_type = data["type"]

        handlers = {
            "toggle_light": lambda: (self.ha.toggle_light(data["entity_id"])),
            "set_light_color": lambda: (self.ha.set_light_color(data["entity_id"],data["color"])),
            "set_brightness": lambda:(self.ha.control_light("on", data["entity_id"])),
            "set_temperature": lambda: self.ha.set_temperature(data["entity_id"], data["temperature"]),
            "control_light": (lambda: self.ha.control_light(data.get("action", "on"), data["entity_id"], data.get("brightness"), data.get("color"))),
            "get_temperature": lambda: asyncio.create_task(
                self.send_message({"type": "temperature_update",
                    "data": {"elementId": data["elementId"],"current_temperature": self.ha.get_temperature(data["entity_id"])}})),
            "chat_input": lambda: asyncio.create_task(  self.handle_slu_result(data["data"],True)),
            "toggleTTS": lambda: (setattr(self, "ttsEnabled", not self.ttsEnabled)),
            "toggleRec": lambda: (setattr(self, "stt", not self.stt)),
            "settings": lambda: asyncio.create_task(
                self.send_message({"type": "settings", "data": load_or_create_json(os.getenv("FRIENDLY_NAMES"))})),
            "set_friendly_names": lambda: (
                save_json(os.getenv("FRIENDLY_NAMES"), data["data"]), initialize_slu(self), 
                asyncio.create_task(self.send_message({"type": "chat-dm",  "data": f"Friendly names byla uložena."}))),
            "get_scenes": lambda: asyncio.create_task(
                self.send_message({"type": "scene_list", "data": list(load_scenes().keys())})),
            "save_scene": lambda: (
                save_scene(data["name"], data["actions"]),
                asyncio.create_task(self.send_message({"type": "chat-dm","data": f"Scéna '{data['name']}' byla uložena."})),
                asyncio.create_task(self.send_message({"type": "scene_list", "data": list(load_scenes().keys())}))),
            "activate_scene": lambda: asyncio.create_task(self.activate_scene(data["scene"])),
            "get_grammar": lambda: asyncio.create_task(self.send_message({"type": "grammar","data": grammar_to_json_safe(load_grammars())})),
            "set_grammar": lambda: (save_grammars(data["data"]),initialize_slu(self),asyncio.create_task(self.send_message({"type": "chat-dm",
                    "data": f"Gramatika byla uložena."}))),
            "get_device_states": lambda: asyncio.create_task( self.send_message({"type": "state_update","data": self.ha.get_all_entities()})),
            "toggle_switch": lambda: self.ha.toggle_switch(data["entity_id"]),
            "control_switch": lambda: self.ha.control_switch(data.get("action", "on"), data["entity_id"]),

            }
        handler = handlers.get(msg_type)
        if handler:
            handler()
        else:
            self.logger.warning("Unknown message type received: %s", msg_type)

    async def display_history(self):
        """
        Sends a list of past commands and actions to the frontend for logging/debug purposes.
        """
        await self.display("Historie požadavků:")
        for h in self.history:
            await self.display(h)
