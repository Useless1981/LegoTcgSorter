import json
import os
import time
import sqlite3
import logging
from typing import Union
import requests
from io import BytesIO
from PIL import Image
import imagehash
import gzip
import shutil

from model.card import Card

# Central console logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("BulkHashDbGenerator")

DB_NAME = "local_cards.db"
COMPRESSED_FILE = "all-cards-20261006211848.jsonl.gz"
MTG_DATA = "scryfall_bulk.jsonl"
MTG_IDENTIFIER = "mtg"
POKEMON_IDENTIFIER = "pokemon"
POKEMON_DATA = "pokemon-tcg-data\\cards\\en"

# Strict API-compliant header matching Scryfall developer rules
SCRYFALL_HEADERS = {
    "User-Agent": "LegoTcgSorterProject/1.0 (Contact: jan.student@uni.de)",
    "Accept": "application/json"
}

def init_database():
    """Initializes the database schema with comprehensive gameplay field tracking."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Fixed syntax formatting and added price columns to the schema
    cursor.execute("DROP TABLE IF EXISTS card_hashes")
    cursor.execute("""
                   CREATE TABLE card_hashes
                   (
                       id             TEXT PRIMARY KEY,
                       tcg            TEXT NOT NULL,
                       name           TEXT NOT NULL,
                       set_code       TEXT NOT NULL,
                       collector_num  TEXT NOT NULL,
                       phash          TEXT NOT NULL,
                       rarity         TEXT,
                       mana_cost      TEXT,
                       cmc            REAL,
                       type_line      TEXT,
                       oracle_text    TEXT,
                       colors         TEXT,
                       color_identity TEXT,
                       usd            REAL,
                       eur            REAL
                   )
                   """)

    conn.commit()
    conn.close()
    logger.info(f"💾 Advanced SQLite Database schema initialized at '{DB_NAME}'.")

def extract_gzip_archive(archive_file_url: str):
    """
    Extracts the manually downloaded 'scryfall_bulk.jsonl.gz' archive
    into a plain text 'scryfall_bulk.jsonl' file on the disk.
    """
    if not os.path.exists(archive_file_url):
        logger.error(f"❌ Source archive '{archive_file_url}' not found in the directory!")
        logger.info("Please make sure the downloaded file is placed directly inside your PyCharm project folder.")
        return False

    logger.info(f"📦 Extracting '{archive_file_url}' into '{MTG_DATA}'...")
    try:
        # Open the compressed gzipped file in binary read mode
        with gzip.open(archive_file_url, 'rb') as f_in:
            # Open the target text file in binary write mode
            with open(MTG_DATA, 'wb') as f_out:
                # Shutil optimized block-copy handles the internal buffer streaming efficiently
                shutil.copyfileobj(f_in, f_out)

        logger.info(f"✅ Extraction successful! Plain text file ready at '{MTG_DATA}'.")
        return True

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        return False

def parse_mtg_jsonl_and_fill_database():
    """
    Reads the uncompressed plain-text .jsonl file line by line,
    extracts card data, computes pHashes, and populates the SQLite table.
    """
    if not os.path.exists(MTG_DATA):
        logger.error(f"❌ Fehler: Die Datei '{MTG_DATA}' wurde nicht gefunden!")
        return

    logger.info(f"📖 Öffne lokale JSONL-Datei '{MTG_DATA}' und initialisiere SQLite...")

    # 1. Datenbank-Tabelle vorbereiten (falls noch nicht geschehen)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 2. Zeilenweise Verarbeitung (Streaming-Ansatz)
    cards_processed: int = 0
    with open(MTG_DATA, "r", encoding="utf-8") as f:
        for line in f:
            if cards_processed < 534820 :
                cards_processed += 1
                continue
            card = _get_card_from_line(line)
            if card is not None:
                try:
                    inserted: bool = _insert_mtg_card_in_db(cursor, card)
                    if inserted:
                        cards_processed += 1
                        # Alle 10 Karten wegschreiben (Crash-Safety)
                        if cards_processed % 10 == 0:
                            logger.info(
                                f"   ↳ [JSONL Stream] {cards_processed} Karten in DB gesichert. Letzte: {card.get("name")}")
                            conn.commit()
                    # Kurze Pause (50ms) um den Bildserver nicht zu überlasten
                    time.sleep(0.05)
                except KeyboardInterrupt:
                    logger.warning("🚨 Prozess manuell abgebrochen. Bis hierher gespeicherte Daten sind sicher in der DB.")
                    break
                except Exception as e:
                    logger.error(f"Fehler bei Karte {card.get("name")}: {e}")

    # Finaler Commit für verbleibende Karten
    conn.commit()
    conn.close()
    logger.info(f"🎉 Fertig! Insgesamt {cards_processed} Karten in '{DB_NAME}' eingetragen.")

def _get_card_from_line(line: str) -> Union[dict, None]:
    line = line.strip()
    if not line:
        return None
    try:
        card = json.loads(line)
        return card
    except json.JSONDecodeError:
        return None

def _insert_mtg_card_in_db(cursor, card: dict) -> bool:
    # Performance Filter: Digitale Karten (MTG Arena) oder Karten ohne Hauptbild überspringen
    if card.get("digital", False) or "image_uris" not in card:
        return False

    image_url = card["image_uris"].get("normal")
    try:
        # Bild-Download für das Hashing (CDN-Server blockieren sehr selten)
        img = _get_image(image_url)
        if img is None:
            logger.error(f"Kein Image für {card.get("name")} gefunden.")
            return False
        p_hash = str(imagehash.phash(img))

        # Preise parsen und sicher zu Floats konvertieren
        prices_dict = card.get("abilities", {})
        usd = float(prices_dict.get("usd")) if prices_dict.get("usd") else None
        eur = float(prices_dict.get("eur")) if prices_dict.get("eur") else None

        # SQL Einfügeoperation (Upsert-Logik)
        _insert_into_db(cursor, card.get("id"), MTG_IDENTIFIER, card.get("name"), card.get("set", "unk"), card.get("collector_number"),
                        p_hash, card.get("rarity"), card.get("mana_cost", ""), card.get("cmc", 0.0),
                        card.get("type_line", ""), card.get("oracle_text", ""),
            "".join(card.get("colors", [])), "".join(card.get("color_identity", [])), usd, eur)
        return True
    except Exception as e:
        logger.error(f"Fehler hinzufügen der Magic-Karte {card.get("name")} in die DB: {e}")

def parse_pokemon_jsonl_and_fill_database():
    """
    Reads the uncompressed plain-text .jsonl file line by line,
    extracts card data, computes pHashes, and populates the SQLite table.
    """

    # 1. Durch das Submodule-Verzeichnis wandern und alle JSON-Dateien finden
    if not os.path.exists(POKEMON_DATA):
        print(f"Fehler: Der Pfad '{POKEMON_DATA}' wurde nicht gefunden. Bitte überprüfe deinen Submodule-Pfad.")
        return

    # 2. Datenbank-Tabelle vorbereiten (falls noch nicht geschehen)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("Lese JSON-Daten aus dem Submodule... Bitte warten.")
    for root, dirs, files in os.walk(POKEMON_DATA):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                set_id = file.replace(".json", "")
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        card_data_list = json.load(f)
                        # Add extracted set card list to db
                        for card in card_data_list:
                            inserted: bool = _insert_pokemon_card_in_db(cursor, card, set_id)
                            if not inserted:
                                logger.error(f"Fehler bei einfügen der Karte {card.get("name")} in die DB. Karte übersprungen.")
                    except KeyboardInterrupt:
                        logger.warning(
                            "🚨 Prozess manuell abgebrochen. Bis hierher gespeicherte Daten sind sicher in der DB.")
                        break
                    except Exception as e:
                        logger.error(f"Fehler bei Set-JSON {file_path}: {e}")
                    logger.info(
                        f"   ↳ [JSONL Stream] {set_id} Set in DB gesichert.")
                    conn.commit()
    conn.commit()
    conn.close()
    logger.info(f"🎉 Fertig! Alle Sets in '{DB_NAME}' eingetragen.")

def _insert_pokemon_card_in_db(cursor, card: dict, set_id: str) -> bool:
    card_id = card.get("id")
    card_name = card.get("name")
    coll_num = card.get("number")
    rarity = card.get("rarity", "Unknown")

    mana_cost = "NONE"
    try:
        cmc = float(card.get("hp", 0))
    except ValueError:
        cmc = 0.0

    subtypes = card.get("subtypes", [])
    type_line = "/".join(subtypes) if subtypes else card.get("supertype", "")

    rules = []
    for ability in card.get("abilities", []):
        rules.append(f"[{ability.get('type')}]: {ability.get('text')}")
    for attack in card.get("attacks", []):
        rules.append(f"{attack.get('name')} ({attack.get('damage', '')}): {attack.get('text', '')}")
    oracle_text = " | ".join(rules) if rules else "No rules text."

    types_list = card.get("types", [])
    colors = "".join(types_list).upper() if types_list else "COLORLESS"
    color_identity = colors

    # Extract price will be fill when a concrete crad is scanned

    usd = None
    eur = None

    image_url = card.get("images", {}).get("large")
    if not image_url:
        return False
    try:
        p_hash = _get_phash(image_url)
        _insert_into_db(cursor, card_id, POKEMON_IDENTIFIER, card_name, set_id, coll_num, p_hash, rarity, mana_cost, cmc, type_line,
                        oracle_text, colors, color_identity, usd, eur)
        return True
    except Exception as e:
        logger.error(f"Fehler beim einfügen der Pokemon Karte {card_name} in die Datenbank: {e}")
        return False

def _get_image(image_url:str) -> Image:
    # Bild-Download für das Hashing (CDN-Server blockieren sehr selten)
    try:
        img_response = requests.get(image_url, headers=SCRYFALL_HEADERS)
        if img_response.status_code == 200:
            img = Image.open(BytesIO(img_response.content))
            return img
        else:
            logger.error(f"Falscher HTTP status code: {img_response.status_code} beim ZUgriff auf {image_url}")
        return None
    except Exception as e:
            logger.error(f"Fehler bei Image Download {image_url}: {e}")

def _get_phash(image_url:str)-> bool | str:
    try:
        # Bild-Download für das Hashing (CDN-Server blockieren sehr selten)
        image = _get_image(image_url)
        if image is None:
            logger.error(f"Kein Image für {image_url} gefunden.")
            return False
        else:
            p_hash = str(imagehash.phash(image))
            return p_hash
    except Exception as e:
        logger.error(f"Fehler bei pHash generation for: {image_url}: {e}")
        return False

def _insert_into_db(cursor, card_id: str, tcg: str, name: str, set_code: str, collector_num: int, phash: str, rarity: str, mana_cost: str, cmc: float, type_line: str, oracle_text: str, colors: str, color_identity: str, usd: float, eur: float):
    cursor.execute("""
                    INSERT OR REPLACE INTO card_hashes (
                    id, tcg, name, set_code, collector_num, phash, rarity,
                    mana_cost, cmc, type_line, oracle_text, colors, color_identity, usd, eur
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        card_id, tcg, name, set_code, collector_num, phash, rarity,
        mana_cost, cmc, type_line, oracle_text, colors, color_identity, usd, eur
    ))

if __name__ == "__main__":
    # Resets and Inits the db. All data will be lost!
    # init_database()

    # Run the full sequence automated. Interrupt via Ctrl+C anytime!

    # Extract MTG data set
    # extract_gzip_archive(COMPRESSED_FILE)

    # Fill database with extracted data set
    # parse_jsonl_and_fill_database()

    # Fill database with Pokemon TCG data from pokemontcg.io
     parse_pokemon_jsonl_and_fill_database()

    # _debug_print_card_json()
