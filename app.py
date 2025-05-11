import logging
from backend.sh_assistant import SHAssistant
from backend.dialog import SpeechCloudWS


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(levelname)-10s %(message)s', level=logging.DEBUG)

    print("http://127.0.0.1:8888/static/index.html")
    SpeechCloudWS.run(SHAssistant, address="0.0.0.0", port=8888, static_path="./static")