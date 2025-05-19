import asyncio
from backend.utils import ask_missing_slot_static
from backend.frame import  TemperatureControlFrame
from backend.utils import load_scenes
from backend.sh_assistant.slu import slu


async def handle_temperature(assistant, result, text_input=False):
    """
    Handles slot-filling and action execution for temperature setting.
    
    Args:
        assistant (Dialog): The main assistant object.
        result (dict): Should include action and switch_entity.
        text_input (bool): Indicates whether input came from chat.
    """

    frame = assistant.pending_frame_update_frame or TemperatureControlFrame()

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
            assistant.pending_frame_update_handler = handle_temperature
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
    assistant.pending_frame_update_frame = frame
    await assistant.display(str(frame))

    while not frame.complete:
        question = ask_missing_slot_static(frame.missing_slots())
        await assistant.send_message({"type": "chat-dm", "data": question})
        if assistant.ttsEnabled:
            await assistant.synthesize_and_wait(question)

        if text_input:
            assistant.pending_frame_update_handler = handle_temperature
            return
        else:
            if assistant.stt:
                await self.send_message({"type": "mic_on", "data": None}) 
                result = await self.recognize_and_wait_for_asr_result(timeout=assistant.TIMEOUT)
                await self.send_message({"type": "mic_off", "data": None}) 
                await self.send_message({"type": "thinking", "data": "thinking"})
            if result:
                frame.update(slu(assistant,result["word_1best"]))
                assistant.pending_frame_update_frame = frame
                await assistant.display(str(frame))
            else:
                msg = "Zkuste to znovu."
                await assistant.send_message({"type": "chat-dm", "data": msg})
                if assistant.ttsEnabled:
                    await assistant.synthesize_and_wait(msg)

    assistant.ha.set_temperature(frame.device, float(frame.temperature))
    message = f"Teplota v {frame.device} nastavena."
    await assistant.send_message({"type": "chat-dm", "data": message})
    if assistant.ttsEnabled:
        await assistant.synthesize_and_wait(message)

    assistant.history.append(str(frame))
    assistant.pending_frame_update_frame = None
    assistant.pending_frame_update_handler = None