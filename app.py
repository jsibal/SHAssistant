import asyncio
import logging
from dotenv import load_dotenv

from dialog import SpeechCloudWS, Dialog

from collections import defaultdict
from frame import *
from ha import HA
from tools import *

class SHAssistant(Dialog):

    
    async def main(self):
        load_dotenv()
        self.running = True
        self.ttsEnabled= False
        self.stt=False
        self.command_count=0
        self.TIMEOUT=5
        self.pending_frame_update_frame = None
        self.pending_frame_update_handler = None
        self.history = []
        self.ha = HA(token=os.getenv("HA_TOKEN"))

        self.initialize_slu()
        await self.dialog_loop()
        await self.synthesize_and_wait("Děkuji, končím.")
        await self.display_history()

    def on_receive_message(self, data):
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
            "chat_input": lambda: asyncio.create_task( self.pending_frame_update_handler(self.slu(data["data"]), text_input=True)
                                                        if hasattr(self, "pending_frame_update_handler") and self.pending_frame_update_handler
                                                        else self.handle_slu_result(data["data"],True)),
            "toggleTTS": lambda: (setattr(self, "ttsEnabled", not self.ttsEnabled),
                                self.logger.debug("TTS toggled. Now:", "Enabled" if self.ttsEnabled else "Disabled")),
            "toggleRec": lambda: (setattr(self, "stt", not self.stt),
                                self.logger.debug("STT toggled. Now:", "Enabled" if self.stt else "Disabled")),
            "settings": lambda: asyncio.create_task(
                self.send_message({"type": "settings", "data": load_or_create_json(os.getenv("FRIENDLY_NAMES"))})),
            "set_friendly_names": lambda: (
                save_json(os.getenv("FRIENDLY_NAMES"), data["data"]), self.initialize_slu(), 
                asyncio.create_task(self.send_message({"type": "chat-dm",  "data": f"Friendly names byla uložena."}))),
            "get_scenes": lambda: asyncio.create_task(
                self.send_message({"type": "scene_list", "data": list(load_scenes().keys())})),
            "save_scene": lambda: (
                save_scene(data["name"], data["actions"]),
                asyncio.create_task(self.send_message({"type": "chat-dm","data": f"Scéna '{data['name']}' byla uložena."})),
                asyncio.create_task(self.send_message({"type": "scene_list", "data": list(load_scenes().keys())}))),
            "activate_scene": lambda: asyncio.create_task(self.activate_scene(data["scene"])),
            "get_grammar": lambda: asyncio.create_task(self.send_message({"type": "grammar","data": grammar_to_json_safe(load_grammars())})),
            "set_grammar": lambda: (save_grammars(data["data"]),self.initialize_slu(),asyncio.create_task(self.send_message({"type": "chat-dm",
                    "data": f"Gramatika byla uložena."}))),
            "get_light_states": lambda: asyncio.create_task( self.send_message({"type": "state_update","data": self.ha.get_all_entities()})),
            }
        handler = handlers.get(msg_type)
        if handler:
            handler()
        else:
            self.logger.warning("Unknown message type received: %s", msg_type)


    def build_reverse_index(self,categories):
        reverse = defaultdict(list)
        for slot_name, slot_dict in categories.items():
            for value, phrases in slot_dict.items():
                for phrase in phrases:
                    reverse[phrase].append((slot_name, value))
        return reverse

    def initialize_slu(self):
        GRAMMARS = load_grammars()
        extended_light = extended_friendly_names(self.ha.get_friendly_names_by_domain("light"))   # dict[str, set[str]]
        extended_climate = extended_friendly_names(self.ha.get_friendly_names_by_domain("climate"))
        scene_phrases = {}
        for scene_name in load_scenes().keys():
            normalized = scene_name.lower().strip()
            scene_phrases[normalized] = {scene_name, normalized, normalized.replace(" ", "")}

        scene_grammar = {k: set(v) for k, v in scene_phrases.items()}

        self.REVERSE_INDEX = self.build_reverse_index({
            "action": GRAMMARS["ACTION"],
            "temperature":  GRAMMARS["TEMPERATURE"],
            "brightness": GRAMMARS["BRIGHTNESS"],
            "color": GRAMMARS["COLOR"],
            "query": GRAMMARS["QUERY_TYPE"],
            "bool_response":GRAMMARS["BOOL_RESPONSE"],
            "target": GRAMMARS["TARGET"],
            "light_entity": extended_light,
            "climate_entity": extended_climate,
            "scene": scene_grammar
        })

    def slu(self, text: str) -> dict:
        text = text.lower()
        found = {}

        for phrase, slots in self.REVERSE_INDEX.items():
            if phrase in text:
                for slot_name, value in slots:
                    if slot_name not in found:
                        found[slot_name] = value

        return found



    async def dialog_loop(self):
        await self.send_message({"type": "init", "data": self.ha.get_all_entities()})
        await self.send_message({"type": "chat-dm", "data": "Pro ovládání pomocí řeči zmáčkni tlačítko mikrofonu"}) 

        self.running = True

        while self.running:
            result = await self.recognize_and_wait_for_asr_result(timeout=5.)
            while self.stt and self.running:
                message = "Řekněte příkaz."
                await self.send_message({"type": "chat-dm", "data": message}) 
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)

                result = await self.recognize_and_wait_for_asr_result(timeout=5.)
                if result:
                    await self.handle_slu_result(result["word_1best"])
                else:
                    message = "Nerozuměl jsem. Zkuste to znovu."
                    await self.send_message({"type": "chat-dm", "data": message}) 
                    if self.ttsEnabled:
                        await self.synthesize_and_wait(message)

                    
    async def handle_slu_result(self, result, text=False):
        result = self.slu(result)
        self.logger.debug(result)
        if result.get("action") == "end":
            await self.send_message({"type": "chat-dm", "data": "Ukončuji dialog."})
            if self.ttsEnabled:
                await self.synthesize_and_wait("Děkuji, končím.")
            self.running = False
            return

        if result.get("query"):
            return await self.handle_query(result,text)

        if result.get("light_entity") or result.get("target") == "light" or result.get("color") or result.get("brightness"):
            return await self.handle_light(result,text)

        if result.get("climate_entity") or result.get("target") == "climate" or result.get("temperature"):
            return await self.handle_temperature(result,text)

        if result.get("scene") or result.get("target") == "scene":
            return await self.handle_scene(result,text)

        message = "Nerozuměl jsem, co chcete ovládat. Můžete to zkusit znovu?"
        await self.send_message({"type": "chat-dm", "data": message})
        if self.ttsEnabled:
            await self.synthesize_and_wait(message)


    async def handle_light(self, result, text_input=False):
        frame = self.pending_frame_update_frame or LightControlFrame()

        if result.get("action") == "cancel":
            message = "Akce byla zrušena."
            await self.send_message({"type": "chat-dm", "data": message})
            if self.ttsEnabled:
                await self.synthesize_and_wait(message)
            self.pending_frame_update_frame = None
            self.pending_frame_update_handler = None
            return

        if result.get("action") == "back":
            if frame.undo_last():
                message = "Poslední údaj byl vrácen zpět."
                await self.send_message({"type": "chat-dm", "data": message})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)
                await self.display(str(frame))
                self.pending_frame_update_frame = frame
                self.pending_frame_update_handler = self.handle_light
                return
            else:
                message = "Žádný údaj už nelze vrátit zpět. Akce byla zrušena."
                await self.send_message({"type": "chat-dm", "data": message})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)
                self.pending_frame_update_frame = None
                self.pending_frame_update_handler = None
                return

        frame.update(result)
        self.pending_frame_update_frame = frame  # uchování stavu

        await self.display(str(frame))

        # Doptávání chybějících údajů
        while not frame.complete:
            slot_to_ask = frame.missing_slots()[0]
            question = ask_missing_slot_static([slot_to_ask])
            await self.send_message({"type": "chat-dm", "data": question})
            if self.ttsEnabled:
                await self.synthesize_and_wait(question)

            if text_input:
                self.pending_frame_update_handler = self.handle_light
                print("Čekám na další textový vstup")
                return  # nevracíme handle_light, jen čekáme na text
            else:
                result = await self.recognize_and_wait_for_asr_result(timeout=5.)
                if result:
                    result = self.slu(result["word_1best"])
                    frame.update(result)
                    self.pending_frame_update_frame = frame
                    await self.display(str(frame))
                else:
                    message = "Zkuste to znovu."
                    await self.send_message({"type": "chat-dm", "data": message})
                    if self.ttsEnabled:
                        await self.synthesize_and_wait(message)

        # provést akci
        message = "Provádím akci."
        await self.send_message({"type": "chat-dm", "data": message})
        if self.ttsEnabled:
            await self.synthesize_and_wait(message)

        if frame.action in {"set", "on"}:
            self.ha.control_light(
                action="on",
                entity_id=frame.device,
                brightness=frame.brightness,
                color_name=frame.color,
            )
        elif frame.action == "off":
            self.ha.control_light(action="off", entity_id=frame.device)

        message = f"Světlo {frame.device} nastaveno."
        await self.send_message({"type": "chat-dm", "data": message})
        if self.ttsEnabled:
            await self.synthesize_and_wait(message) 
        await asyncio.sleep(1) 
        await self.send_message({"type": "state_update","data": self.ha.get_all_entities()})
                    
        self.history.append(str(frame))
        self.pending_frame_update_frame = None
        self.pending_frame_update_handler = None


    async def handle_temperature(self, result, text_input=False):
        frame = self.pending_frame_update_frame or TemperatureControlFrame()

        if result.get("action") == "cancel":
            message = "Akce byla zrušena."
            await self.send_message({"type": "chat-dm", "data": message})
            if self.ttsEnabled:
                await self.synthesize_and_wait(message)
            self.pending_frame_update_frame = None
            self.pending_frame_update_handler = None
            return

        if result.get("action") == "back":
            if frame.undo_last():
                message = "Poslední údaj byl vrácen zpět."
                await self.send_message({"type": "chat-dm", "data": message})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)
                await self.display(str(frame))
                self.pending_frame_update_frame = frame
                self.pending_frame_update_handler = self.handle_temperature
                return
            else:
                message = "Žádný údaj už nelze vrátit zpět. Akce byla zrušena."
                await self.send_message({"type": "chat-dm", "data": message})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)
                self.pending_frame_update_frame = None
                self.pending_frame_update_handler = None
                return

        frame.update(result)
        self.pending_frame_update_frame = frame
        await self.display(str(frame))

        while not frame.complete:
            question = ask_missing_slot_static(frame.missing_slots())
            await self.send_message({"type": "chat-dm", "data": question})
            if self.ttsEnabled:
                await self.synthesize_and_wait(question)

            if text_input:
                self.pending_frame_update_handler = self.handle_temperature
                return

            result = await self.recognize_and_wait_for_asr_result(timeout=self.TIMEOUT)
            if result:
                frame.update(self.slu(result["word_1best"]))
                self.pending_frame_update_frame = frame
                await self.display(str(frame))
            else:
                msg = "Zkuste to znovu."
                await self.send_message({"type": "chat-dm", "data": msg})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(msg)

        self.ha.set_temperature(frame.device, float(frame.temperature))
        message = f"Teplota v {frame.device} nastavena."
        await self.send_message({"type": "chat-dm", "data": message})
        if self.ttsEnabled:
            await self.synthesize_and_wait(message)

        self.history.append(str(frame))
        self.pending_frame_update_frame = None
        self.pending_frame_update_handler = None

    async def handle_query(self, result, text_input=False):
        frame = self.pending_frame_update_frame or QueryFrame()

        if result.get("action") == "cancel":
            message = "Akce byla zrušena."
            await self.send_message({"type": "chat-dm", "data": message})
            if self.ttsEnabled:
                await self.synthesize_and_wait(message)
            self.pending_frame_update_frame = None
            self.pending_frame_update_handler = None
            return

        if result.get("action") == "back":
            if frame.undo_last():
                message = "Poslední údaj byl vrácen zpět."
                await self.send_message({"type": "chat-dm", "data": message})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)
                await self.display(str(frame))
                self.pending_frame_update_frame = frame
                self.pending_frame_update_handler = self.handle_query
                return
            else:
                message = "Žádný údaj už nelze vrátit zpět. Akce byla zrušena."
                await self.send_message({"type": "chat-dm", "data": message})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)
                self.pending_frame_update_frame = None
                self.pending_frame_update_handler = None
                return

        frame.update(result)
        self.pending_frame_update_frame = frame
        await self.display(str(frame))

        while not frame.complete:
            question = ask_missing_slot_static(frame.missing_slots())
            await self.send_message({"type": "chat-dm", "data": question})
            if self.ttsEnabled:
                await self.synthesize_and_wait(question)

            if text_input:
                self.pending_frame_update_handler = self.handle_query
                return

            result = await self.recognize_and_wait_for_asr_result(timeout=5.)
            if result:
                frame.update(self.slu(result["word_1best"]))
                self.pending_frame_update_frame = frame
                await self.display(str(frame))
            else:
                msg = "Zkuste to znovu."
                await self.send_message({"type": "chat-dm", "data": msg})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(msg)

        attrs = self.ha.get_attributes(frame.device) or {}
        friendly_name = attrs.get("friendly_name", frame.device)

        if frame.query_type == "temperature":
            value = self.ha.get_temperature(frame.device)
            message = f"Aktuální teplota v {friendly_name} je {value}°C." if value is not None else f"Nepodařilo se zjistit teplotu zařízení {friendly_name}."
        elif frame.query_type == "state":
            state = self.ha.get_state(frame.device)
            status = state.get("state", "neznámý stav") if state else None
            message = f"Zařízení {friendly_name} je {status}." if status else f"Nepodařilo se zjistit stav zařízení {friendly_name}."
        elif frame.query_type == "brightness":
            brightness = attrs.get("brightness")
            message = f"Jas světla {friendly_name} je {brightness}." if brightness else f"Jas světla {friendly_name} se nepodařilo zjistit."
        elif frame.query_type == "color":
            color = attrs.get("color_name") or attrs.get("rgb_color")
            message = f"Barva světla {friendly_name} je {color}." if color else f"Barvu světla {friendly_name} se nepodařilo zjistit."
        else:
            message = "Tento typ dotazu zatím není podporován."

        await self.send_message({"type": "chat-dm", "data": message})
        if self.ttsEnabled:
            await self.synthesize_and_wait(message)

        self.history.append(str(frame))
        self.pending_frame_update_frame = None
        self.pending_frame_update_handler = None

    async def handle_scene(self, result, text_input=False):
        frame = self.pending_frame_update_frame or SceneFrame()

        if result.get("action") == "cancel":
            message = "Akce byla zrušena."
            await self.send_message({"type": "chat-dm", "data": message})
            if self.ttsEnabled:
                await self.synthesize_and_wait(message)
            self.pending_frame_update_frame = None
            self.pending_frame_update_handler = None
            return

        if result.get("action") == "back":
            if frame.undo_last():
                message = "Poslední údaj byl vrácen zpět."
                await self.send_message({"type": "chat-dm", "data": message})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)
                await self.display(str(frame))
                self.pending_frame_update_frame = frame
                self.pending_frame_update_handler = self.handle_scene
                return
            else:
                message = "Žádný údaj už nelze vrátit zpět. Akce byla zrušena."
                await self.send_message({"type": "chat-dm", "data": message})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(message)
                self.pending_frame_update_frame = None
                self.pending_frame_update_handler = None
                return

        # Aktualizuj frame
        frame.update(result)
        self.pending_frame_update_frame = frame
        await self.display(str(frame))

        # Slot-filling cyklus
        while not frame.complete:
            question = ask_missing_slot_static(frame.missing_slots())
            await self.send_message({"type": "chat-dm", "data": question})
            if self.ttsEnabled:
                await self.synthesize_and_wait(question)

            if text_input:
                self.pending_frame_update_handler = self.handle_scene
                return

            result = await self.recognize_and_wait_for_asr_result(timeout=5.)
            if result:
                frame.update(self.slu(result["word_1best"]))
                self.pending_frame_update_frame = frame
                await self.display(str(frame))
            else:
                msg = "Zkuste to znovu."
                await self.send_message({"type": "chat-dm", "data": msg})
                if self.ttsEnabled:
                    await self.synthesize_and_wait(msg)

        # Spuštění scény
        scenes = load_scenes()
        scene = scenes.get(frame.scene)

        if not scene:
            msg = f"Scéna '{frame.scene}' neexistuje."
            await self.send_message({"type": "chat-dm", "data": msg})
            if self.ttsEnabled:
                await self.synthesize_and_wait(msg)
            return

        actions = scene.get("actions", [])
        for action in actions:
            self.on_receive_message(action)  # může být async-safe podle implementace

        msg = f"Scéna '{frame.scene}' byla aktivována."
        await self.send_message({"type": "chat-dm", "data": msg})
        if self.ttsEnabled:
            await self.synthesize_and_wait(msg)
        await asyncio.sleep(1) 
        await self.send_message({"type": "state_update","data": self.ha.get_all_entities()})
        
        self.history.append(str(frame))
        self.pending_frame_update_frame = None
        self.pending_frame_update_handler = None


    async def activate_scene(self, scene_name: str):
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


    async def display_history(self):
        await self.display("Historie požadavků:")
        for h in self.history:
            await self.display(h)


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)-10s %(message)s', level=logging.DEBUG)

    print("http://127.0.0.1:8888/static/index.html")
    SpeechCloudWS.run(SHAssistant, address="0.0.0.0", port=8888, static_path="./static")
    

