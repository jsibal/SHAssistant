import asyncio
from backend.utils import ask_missing_slot_static
from backend.frame import   QueryFrame
from backend.utils import load_scenes
from backend.sh_assistant.slu import slu


async def handle_query(assistant, result, text_input=False):
    """
    Handles slot-filling and action execution for user queries (e.g., temperature, state).
    
    Args:
        assistant (Dialog): Instance of the SHAssistant.
        result (dict): Parsed SLU result with extracted slots.
        text_input (bool): True if user input was textual (chat), not spoken.
    """
    frame = assistant.pending_frame_update_frame or QueryFrame()

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
            assistant.pending_frame_update_handler = handle_query
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
            assistant.pending_frame_update_handler = handle_query
            return
        else:
            if assistant.stt:
                await assistant.send_message({"type": "mic_on", "data": None}) 
                result = await assistant.recognize_and_wait_for_asr_result(timeout=assistant.TIMEOUT)
                await assistant.send_message({"type": "mic_off", "data": None}) 
                await assistant.send_message({"type": "thinking", "data": "thinking"})
            if result:
                frame.update(slu(assistant,result["word_1best"]))
                assistant.pending_frame_update_frame = frame
                await assistant.display(str(frame))
            else:
                msg = "Zkuste to znovu."
                await assistant.send_message({"type": "chat-dm", "data": msg})
                if assistant.ttsEnabled:
                    await assistant.synthesize_and_wait(msg)

    attrs = assistant.ha.get_attributes(frame.device) or {}
    friendly_name = attrs.get("friendly_name", frame.device)

    if frame.query_type == "temperature":
        value = assistant.ha.get_temperature(frame.device)
        message = f"Aktuální teplota v {friendly_name} je {value}°C." if value is not None else f"Nepodařilo se zjistit teplotu zařízení {friendly_name}."
    elif frame.query_type == "state":
        state = assistant.ha.get_state(frame.device)
        status = state.get("state", "neznámý stav") if state else None
        message = f"Zařízení {friendly_name} je {status}." if status else f"Nepodařilo se zjistit stav zařízení {friendly_name}."
    elif frame.query_type == "brightness":
        brightness = attrs.get("brightness")
        message = f"Jas světla {friendly_name} je {brightness}." if brightness else f"Jas světla {friendly_name} se nepodařilo zjistit."
    elif frame.query_type == "color":
        color = attrs.get("color_name") or attrs.get("rgb_color")
        message = f"Barva světla {friendly_name} je {color}." if color else f"Barvu světla {friendly_name} se nepodařilo zjistit."
    elif frame.query_type == "switch":
        state = assistant.ha.get_state(frame.device)
        status = state.get("state", "neznámý stav") if state else None
        message = f"Zařízení {friendly_name} je {status}." if status else f"Nepodařilo se zjistit stav zařízení {friendly_name}."
    else:
        message = "Tento typ dotazu zatím není podporován."

    await assistant.send_message({"type": "chat-dm", "data": message})
    if assistant.ttsEnabled:
        await assistant.synthesize_and_wait(message)

    assistant.history.append(str(frame))
    assistant.pending_frame_update_frame = None
    assistant.pending_frame_update_handler = None