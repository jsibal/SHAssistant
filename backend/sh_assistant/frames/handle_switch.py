import asyncio

from backend.utils import ask_missing_slot_static
from backend.frame import SwitchControlFrame
from backend.utils import load_scenes
from backend.sh_assistant.slu import slu



async def handle_switch(assistant, result, text_input=False):
    """
    Handles slot-filling and action execution for smart switch control.
    
    Args:
        assistant (Dialog): The main assistant object.
        result (dict): Should include action and switch_entity.
        text_input (bool): Indicates whether input came from chat.
    """

    frame = assistant.pending_frame_update_frame or SwitchControlFrame()

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
            assistant.pending_frame_update_handler = handle_switch
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
            assistant.pending_frame_update_handler = handle_switch
            return

        result = await assistant.recognize_and_wait_for_asr_result(timeout=5.0)
        if result:
            frame.update(slu(result["word_1best"]))
            assistant.pending_frame_update_frame = frame
            await assistant.display(str(frame))
        else:
            msg = "Zkuste to znovu."
            await assistant.send_message({"type": "chat-dm", "data": msg})
            if assistant.ttsEnabled:
                await assistant.synthesize_and_wait(msg)

    # vykonání
    assistant.ha.control_switch(frame.action, frame.device)
    message = f"Zásuvka {frame.device} byla {frame.action}."
    await assistant.send_message({"type": "chat-dm", "data": message})
    if assistant.ttsEnabled:
        await assistant.synthesize_and_wait(message)
    await asyncio.sleep(1)
    await assistant.send_message({"type": "state_update", "data": assistant.ha.get_all_entities()})

    assistant.history.append(str(frame))
    assistant.pending_frame_update_frame = None
    assistant.pending_frame_update_handler = None
