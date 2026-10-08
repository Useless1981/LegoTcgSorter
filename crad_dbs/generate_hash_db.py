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
JSONL_FILE = "scryfall_bulk.jsonl"

# Strict API-compliant header matching Scryfall developer rules
HEADERS = {
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

    logger.info(f"📦 Extracting '{archive_file_url}' into '{JSONL_FILE}'...")
    try:
        # Open the compressed gzipped file in binary read mode
        with gzip.open(archive_file_url, 'rb') as f_in:
            # Open the target text file in binary write mode
            with open(JSONL_FILE, 'wb') as f_out:
                # Shutil optimized block-copy handles the internal buffer streaming efficiently
                shutil.copyfileobj(f_in, f_out)

        logger.info(f"✅ Extraction successful! Plain text file ready at '{JSONL_FILE}'.")
        return True

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        return False

def parse_jsonl_and_fill_database():
    """
    Reads the uncompressed plain-text .jsonl file line by line,
    extracts card data, computes pHashes, and populates the SQLite table.
    """
    if not os.path.exists(JSONL_FILE):
        logger.error(f"❌ Fehler: Die Datei '{JSONL_FILE}' wurde nicht gefunden!")
        return

    logger.info(f"📖 Öffne lokale JSONL-Datei '{JSONL_FILE}' und initialisiere SQLite...")

    # 1. Datenbank-Tabelle vorbereiten (falls noch nicht geschehen)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 2. Zeilenweise Verarbeitung (Streaming-Ansatz)
    cards_processed: int = 0
    with open(JSONL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if cards_processed < 152800 :
                cards_processed += 1
                continue
            card = get_card_from_line(line)
            if card is not None:
                try:
                    inserted: bool = insert_mtgcard_in_db(cursor, card)
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

def get_card_from_line(line: str) -> Union[dict, None]:
    line = line.strip()
    if not line:
        return None
    try:
        card = json.loads(line)
        return card
    except json.JSONDecodeError:
        return None

def insert_mtgcard_in_db(cursor, card: dict) -> bool:
    # Performance Filter: Digitale Karten (MTG Arena) oder Karten ohne Hauptbild überspringen
    if card.get("digital", False) or "image_uris" not in card:
        return False

    card_id = card.get("id")
    card_name = card.get("name")
    image_url = card["image_uris"].get("normal")

    try:
        # Bild-Download für das Hashing (CDN-Server blockieren sehr selten)
        img = get_image(image_url)
        if img is None:
            logger.error(f"Kein Image für {card_name} gefunden.")
            return False
        p_hash = str(imagehash.phash(img))

        # Preise parsen und sicher zu Floats konvertieren
        prices_dict = card.get("prices", {})
        usd = float(prices_dict.get("usd")) if prices_dict.get("usd") else None
        eur = float(prices_dict.get("eur")) if prices_dict.get("eur") else None

        # SQL Einfügeoperation (Upsert-Logik)
        insert_into_db(cursor, card_id, "mtg", card_name, card.get("set", "unk"), card.get("collector_number"),
            p_hash, card.get("rarity"), card.get("mana_cost", ""), card.get("cmc", 0.0),
            card.get("type_line", ""), card.get("oracle_text", ""),
            "".join(card.get("colors", [])), "".join(card.get("color_identity", [])), usd, eur)
        return True
    except Exception as e:
        logger.error(f"Fehler hinzufügen der Magic-Karte {card_name} in die DB: {e}")

def get_pokemon_set(set_id: str) -> Union[dict, None]:
    api_url = "https://pokemontcg.io"
    query_params = {"q": f"set.id:{set_id}"}
    try:
        response = requests.get(api_url, headers=HEADERS, params=query_params)
        if response.status_code != 200:
            return None
        logger.info(f"Erfolgreich  das Set {set_id} heruntergeladen.")
        return response.json()
    except Exception as e:
        logger.error(f"Fehler download des Sets {set_id}: {e}")


def download_all_pokemon_sets():
    """Queries the Pokémon set index directory and coordinates mass collection loops."""
    logger.info("🌐 Fetching complete Pokémon Set Directory from pokemontcg.io...")
    response = requests.get("https://pokemontcg.io", headers=HEADERS)
    if response.status_code != 200:
        logger.error("Failed to retrieve Pokémon master set list.")
        return
    sets_list = response.json().get("data", [])
    logger.info(f"📋 Found {len(sets_list)} total Pokémon sets. Commencing loop iterations...")
    for count, set_obj in enumerate(sets_list, start=1):
        set_id = set_obj.get("id")
        set_name = set_obj.get("name")
        logger.info(f"🚀 Processing Pokémon Set [{count}/{len(sets_list)}]: '{set_name.upper()}' ({set_id})")
        try:
            total_hashed = fetch_and_hash_pokemon_set(set_id)
            logger.info(f"✅ Completed Pokémon Set '{set_id}': Indexed {total_hashed} cards.")
            time.sleep(0.5)
        except KeyboardInterrupt:
            logger.warning("🚨 [POKEMON] Master loop paused by user command. Progress saved.")
            break


def fetch_and_hash_pokemon_set(set_id: str) -> int:
    """Idempotently hashes a Pokémon TCG set and maps items symmetrically into the shared table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cards_processed = 0
    # Get set data from pokemontcg.io
    data = get_pokemon_set(set_id)
    if data is None:
        return 0
    for card in data.get("data", []):
        cards_processed: int = 0
        try:
            inserted = insert_pokemoncard_in_db(cursor, card)
            if inserted:
                time.sleep(0.12)
                cards_processed += 1
            if cards_processed % 10 == 0:
                logger.info(
                    f"   ↳ [JSONL Stream] {cards_processed} Karten in DB gesichert. Letzte: {card.get("name")}")
                conn.commit()
        except Exception as e:
            logger.error(f"Error processing Pokémon card '{card.get("name")}': {e}")

    conn.close()

    return cards_processed

def insert_pokemoncard_in_db(cursor, card: dict) -> bool:
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

    # Extract price parameters if available via the TCGPlayer data subnode
    tcgplayer_prices = card.get("tcgplayer", {}).get("prices", {})
    usd_val = None
    if tcgplayer_prices:
        first_market = list(tcgplayer_prices.values())[0]
        usd_val = first_market.get("market") or first_market.get("mid")

    usd = float(usd_val) if usd_val else None
    eur = None  # The Pokemon API does not serve localized EUR data blocks directly

    image_url = card.get("images", {}).get("large")
    if not image_url:
        return False
    try:
        img = get_image(image_url)
        if img is None:
            logger.error(f"Image missing from '{card_name}'")
        p_hash = str(imagehash.phash(img))
        insert_into_db(cursor, card_id, card_name, coll_num, p_hash, rarity, p_hash, mana_cost, cmc, type_line,
                       oracle_text, colors, color_identity, usd, eur)
        return True
    except Exception as e:
        logger.error(f"Fehler beim einfügen der Pokemon Karte {card_name} in die Datenbank: {e}")
        return False

def get_image(image_url:str)-> Image:
    # Bild-Download für das Hashing (CDN-Server blockieren sehr selten)
    try:
        img_response = requests.get(image_url, headers=HEADERS)
        if img_response.status_code == 200:
            img = Image.open(BytesIO(img_response.content))
            return img
        else:
            logger.error(f"Falscher HTTP status code: {img_response.status_code} beim ZUgriff auf {image_url}")
        return None
    except Exception as e:
            logger.error(f"Fehler bei Image Download {image_url}: {e}")



def insert_into_db(cursor, card_id: str, tcg: str, name: str, set_code: str, collector_num: int, phash: str, rarity: str, mana_cost: str, cmc: float, type_line: str, oracle_text: str, colors: str, color_identity: str, usd: float, eur: float):
    cursor.execute("""
                    INSERT OR REPLACE INTO card_hashes (
                    id, tcg, name, set_code, collector_num, phash, rarity,
                    mana_cost, cmc, type_line, oracle_text, colors, color_identity, usd, eur
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        card_id, tcg, name, set_code, collector_num, phash, rarity,
        mana_cost, cmc, type_line, oracle_text, colors, color_identity, usd, eur
    ))

def _debug_print_card_json(print_n: int = 1):
    printed:int = 0
    with open(JSONL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            card = get_card_from_line(line)
            print(card)
            if printed == print_n:
                return



if __name__ == "__main__":
    # init_database() # will rest the db. All data will be lost!

    # Run the full sequence automated. Interrupt via Ctrl+C anytime!

    # Extract MTG data set
    # extract_gzip_archive(COMPRESSED_FILE)

    # Fill database with extracted data set
    parse_jsonl_and_fill_database()

    # Fill database with Pokemon TCG data from pokemontcg.io
    # download_all_pokemon_sets()

    # _debug_print_card_json()
