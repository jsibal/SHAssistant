import asyncio
from backend.utils import ask_missing_slot_static
from backend.frame import  SceneFrame
from backend.utils import load_scenes
from backend.sh_assistant.slu import slu


async def handle_scene(assistant, result, text_input=False):
    """
    Handles slot-filling and activation of user-defined scenes.
    
    Args:
        assistant (Dialog): Instance of the SHAssistant.
        result (dict): Parsed SLU result with extracted slots.
        text_input (bool): True if user input was textual (chat), not spoken.
    """

    frame = assistant.pending_frame_update_frame or SceneFrame()

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
            assistant.pending_frame_update_handler = handle_scene
            return
        else:
            message = "Žádný údaj už nelze vrátit zpět. Akce byla zrušena."
            await assistant.send_message({"type": "chat-dm", "data": message})
            if assistant.ttsEnabled:
                await assistant.synthesize_and_wait(message)
            assistant.pending_frame_update_frame = None
            assistant.pending_frame_update_handler = None
            return

    # Aktualizuj frame
    frame.update(result)
    assistant.pending_frame_update_frame = frame
    await assistant.display(str(frame))

    # Slot-filling cyklus
    while not frame.complete:
        question = ask_missing_slot_static(frame.missing_slots())
        await assistant.send_message({"type": "chat-dm", "data": question})
        if assistant.ttsEnabled:
            await assistant.synthesize_and_wait(question)

        if text_input:
            assistant.pending_frame_update_handler = handle_scene
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

    # Spuštění scény
    scenes = load_scenes()
    scene = scenes.get(frame.scene)

    if not scene:
        msg = f"Scéna '{frame.scene}' neexistuje."
        await assistant.send_message({"type": "chat-dm", "data": msg})
        if assistant.ttsEnabled:
            await assistant.synthesize_and_wait(msg)
        return

    actions = scene.get("actions", [])
    for action in actions:
        assistant.on_receive_message(action)  # může být async-safe podle implementace

    msg = f"Scéna '{frame.scene}' byla aktivována."
    await assistant.send_message({"type": "chat-dm", "data": msg})
    if assistant.ttsEnabled:
        await assistant.synthesize_and_wait(msg)
    await asyncio.sleep(1) 
    await assistant.send_message({"type": "state_update","data": assistant.ha.get_all_entities()})
    
    assistant.history.append(str(frame))
    assistant.pending_frame_update_frame = None
    assistant.pending_frame_update_handler = None