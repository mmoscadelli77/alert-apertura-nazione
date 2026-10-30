import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, time
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse

URL = "https://www.lanazione.it/"
FILE = "ultimo_titolo.json"

def trova_apertura():
    risposta = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    risposta.raise_for_status()
    soup = BeautifulSoup(risposta.text, "html.parser")

    main = soup.find("main")
    if main is None:
        raise RuntimeError("Area principale non trovata")

    # Cerca il primo titolo di articolo nell'area principale.
    for titolo in main.select("h2, h3, h1"):
        link = titolo.find("a", href=True)
        if link is None:
            link = titolo.find_parent("a", href=True)
        if link is None:
            continue

        testo = titolo.get_text(" ", strip=True)
        indirizzo = urljoin(URL, link["href"])
        dominio = urlparse(indirizzo).hostname or ""

        if (len(testo) >= 20
                and dominio in ("lanazione.it", "www.lanazione.it")
                and urlparse(indirizzo).path not in ("", "/")):
            return {"titolo": testo, "url": indirizzo}

    raise RuntimeError("Nessun titolo valido trovato")

def invia_telegram(messaggio):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    risposta = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": messaggio},
        timeout=30
    )
    risposta.raise_for_status()
    if not risposta.json().get("ok"):
        raise RuntimeError("Invio Telegram non riuscito")

def main():
    adesso = datetime.now(ZoneInfo("Europe/Rome"))

    if not time(7, 0) <= adesso.time() < time(23, 59, 59):
        print("Fuori orario: nessun controllo")
        return

    nuova = trova_apertura()
    print("Apertura rilevata:", nuova["titolo"])

    precedente = None
    if os.path.exists(FILE):
        with open(FILE, encoding="utf-8") as f:
            precedente = json.load(f)

    if precedente is None:
        print("Prima esecuzione: salvo l'apertura")
    elif (precedente["url"] != nuova["url"]
          or precedente["titolo"] != nuova["titolo"]):
        messaggio = (
            "🔴 LA NAZIONE - NUOVA APERTURA\n\n"
            f"📰 {nuova['titolo']}\n\n"
            f"🔗 {nuova['url']}\n\n"
            f"Precedente: {precedente['titolo']}\n"
            f"Rilevata alle {adesso:%H:%M}"
        )
        invia_telegram(messaggio)
        print("Notifica inviata")
    else:
        print("Apertura invariata")

    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(nuova, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
