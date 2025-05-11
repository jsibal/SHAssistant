Multimodální osobní asistent pro automatizaci domácnosti

# Multimodální hlasový asistent pro domácí automatizaci

Tento projekt implementuje webovou aplikaci propojenou s dialogovým manažerem využívajícím službu [SpeechCloud](https://speechcloud.kky.zcu.cz/) a API [Home Assistant](https://www.home-assistant.io/) pro ovládání chytré domácnosti.

## Funkce

- Podpora hlasu, textu i tlačítek
- Ovládání světel (zapnutí, vypnutí, barva, jas)
- Nastavení teploty
- Dotazy na stav zařízení (jas, teplota, barva, zapnuto/vypnuto)
- Ovládání zásuvek
- Slot-filling s doptáváním, možností „zpět“ a „zruš“
- Aktivace a tvorba scén
- Úprava aliasů a gramatik přes webové rozhraní

## Struktura projektu

- `index.html`, `styles.css`, `script.js` – frontendová aplikace
- `SC_script.js` – připojení ke službě SpeechCloud
- `core.py`, `frame.py`, `slu.py`, `handle_*.py` – backend logika asistenta
- `ha.py` – rozhraní pro komunikaci s Home Assistant API
- `utils.py` – pomocné funkce pro načítání aliasů, gramatik, scén
- `app.py` – spouštěcí bod aplikace (Tornado server)
- `requirements.txt` – seznam potřebných knihoven

## Spuštění

```bash
pip install -r requirements.txt
python app.py
```
