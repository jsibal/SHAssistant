import asyncio
from backend.utils import ask_missing_slot_static
from backend.frame import LightControlFrame
from backend.utils import load_scenes
from backend.sh_assistant.slu import slu


async def handle_light(assistant, result, text_input=False):
        """
        Handles slot-filling and action execution for light control.

        Args:
            assistant (Dialog): Instance of the SHAssistant.
            result (dict): Parsed SLU result with extracted slots.
            text_input (bool): True if user input was textual (chat), not spoken.
        """

        frame = assistant.pending_frame_update_frame or LightControlFrame()

        if result.get("action") == "cancel":
            message = "Akce byla zrušena."
            await assistant.send_message({"type": "chat-dm", "data": message})
            if assistant.ttsEnabled:
                await assistant.synthesize_and_wait(message)
            assistant.pending_frame_update_frame = None
            assistant.pending_frame_update_handler = None
            return

        if result.get("action") == "back":
            if frame.undo_last():
                message = "Poslední údaj byl vrácen zpět."
                await assistant.send_message({"type": "chat-dm", "data": message})
                if assistant.ttsEnabled:
                    await assistant.synthesize_and_wait(message)
                await assistant.display(str(frame))
                assistant.pending_frame_update_frame = frame
                assistant.pending_frame_update_handler = handle_light
                return
            else:
                message = "Žádný údaj už nelze vrátit zpět. Akce byla zrušena."
                await assistant.send_message({"type": "chat-dm", "data": message})
                if assistant.ttsEnabled:
                    await assistant.synthesize_and_wait(message)
                assistant.pending_frame_update_frame = None
                assistant.pending_frame_update_handler = None
                return

        frame.update(result)
        assistant.pending_frame_update_frame = frame  # uchování stavu

        await assistant.display(str(frame))

        # Doptávání chybějících údajů
        while not frame.complete:
            slot_to_ask = frame.missing_slots()[0]
            question = ask_missing_slot_static([slot_to_ask])
            await assistant.send_message({"type": "chat-dm", "data": question})
            if assistant.ttsEnabled:
                await assistant.synthesize_and_wait(question)

            if text_input:
                assistant.pending_frame_update_handler = handle_light
                print("Čekám na další textový vstup")
                return  # nevracíme handle_light, jen čekáme na text
            else:
                if assistant.stt:
                    await assistant.send_message({"type": "mic_on", "data": None}) 
                    result = await assistant.recognize_and_wait_for_asr_result(timeout=assistant.TIMEOUT)
                    await assistant.send_message({"type": "mic_off", "data": None}) 
                    await assistant.send_message({"type": "thinking", "data": "thinking"})

                if result:
                    result = slu(assistant,result["word_1best"])
                    frame.update(result)
                    assistant.pending_frame_update_frame = frame
                    await assistant.display(str(frame))
                else:
                    message = "Zkuste to znovu."
                    await assistant.send_message({"type": "chat-dm", "data": message})
                    if assistant.ttsEnabled:
                        await assistant.synthesize_and_wait(message)

        # provést akci
        message = "Provádím akci."
        await assistant.send_message({"type": "chat-dm", "data": message})
        if assistant.ttsEnabled:
            await assistant.synthesize_and_wait(message)

        if frame.action in {"set", "on"}:
            assistant.ha.control_light(
                action="on",
                entity_id=frame.device,
                brightness=frame.brightness,
                color_name=frame.color,
            )
        elif frame.action == "off":
            assistant.ha.control_light(action="off", entity_id=frame.device)

        message = f"Světlo {frame.device} nastaveno."
        await assistant.send_message({"type": "chat-dm", "data": message})
        if assistant.ttsEnabled:
            await assistant.synthesize_and_wait(message) 
        await asyncio.sleep(1) 
        await assistant.send_message({"type": "state_update","data": assistant.ha.get_all_entities()})
                    
        assistant.history.append(str(frame))
        assistant.pending_frame_update_frame = None
        assistant.pending_frame_update_handler = None