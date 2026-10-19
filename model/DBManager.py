import sqlite3
import json
import os
import time
import sqlite3
import logging
import requests
from io import BytesIO
from PIL import Image
import imagehash
import gzip
import shutil
from typing import Optional, Dict, Any

logger = logging.getLogger("TcgSorter.Model.DbManager")


class DbManager:
    """
    Data Access Object (DAO) within the Model layer.
    Encapsulates all direct SQLite database interactions.
    """

    def __init__(self, db_path: str = "local_cards.db",
                 pokemon_database_path: str = "crad_dbs/pokemon-tcg-data/cards/en",
                 mtg_database_path: str = "crad_dbs/scryfall_bulk.jsonl",
                 tabel_name: str = "card_hashes",
                 ):
        self.mtg_identifier: str = "mtg"
        self.pokemon_identifier: str = "pokemon"
        self.pokemon_database_path: str = pokemon_database_path
        self.mtg_database_path: str = mtg_database_path
        self.db_path = db_path
        self.tabel_name: str = tabel_name

        self.scryfall_header = {
            "User-Agent": "LegoTcgSorterProject/1.0 (Contact: jan.student@uni.de)",
            "Accept": "application/json"
            }
        logger.info(f"Database Manager initialized for path: '{self.db_path}'")

    def _get_connection(self) -> sqlite3.Connection:
        """Helper to create a fresh connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        # Row factory allows accessing columns by name: row['name'] instead of row[2]
        conn.row_factory = sqlite3.Row
        return conn

    def find_card_by_hash(self, current_hash: str) -> Optional[Dict[str, Any]]:
        """
        Executes the SQL lookup to find the card with the closest or exact pHash.
        """
        # In a real setup, you might fetch all hashes from the DB once
        # into the RAM during startup, or do a specialized SQL query here.
        query = "SELECT * FROM card_hashes WHERE phash = ?"

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (current_hash,))
                row = cursor.fetchone()

                if row:
                    return dict(row)  # Convert sqlite3.Row to standard Python Dict
                return None
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            return None

    def fill_or_update_mtg_cards(self, mtg_data_zip = None):
        """
        Reads the uncompressed plain-text .jsonl file line by line,
        extracts card data, computes pHashes, and populates the SQLite table.
        """
        # 1. Unzip MTG data zip if provided
        if mtg_data_zip is not None:
            self._extract_gzip_archive(mtg_data_zip)


        if not os.path.exists(self.mtg_database_path):
            logger.error(f"❌ Fehler: Die Datei '{self.mtg_database_path}' wurde nicht gefunden!")
            return

        logger.info(f"📖 Öffne lokale JSONL-Datei '{self.mtg_database_path}' und initialisiere SQLite...")

        # 2. Datenbank-Tabelle vorbereiten (falls noch nicht geschehen)
        conn = self._get_connection()
        cursor = conn.cursor()

        # 3. Zeilenweise Verarbeitung (Streaming-Ansatz)
        cards_processed: int = 0
        with open(self.mtg_database_path, "r", encoding="utf-8") as f:
            for line in f:
                if cards_processed < 534820:
                    cards_processed += 1
                    continue
                card = self._get_card_from_line(line)
                if card is not None:
                    try:
                        inserted: bool = self._insert_mtg_card_in_db(cursor, card)
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
                        logger.warning(
                            "🚨 Prozess manuell abgebrochen. Bis hierher gespeicherte Daten sind sicher in der DB.")
                        break
                    except Exception as e:
                        logger.error(f"Fehler bei Karte {card.get("name")}: {e}")

        # Finaler Commit für verbleibende Karten
        conn.commit()
        conn.close()
        logger.info(f"🎉 Fertig! Insgesamt {cards_processed} Karten in '{self.db_path}' eingetragen.")

    def fill_or_update_pokemon_cards(self):
        """
        Reads the uncompressed plain-text .jsonl file line by line,
        extracts card data, computes pHashes, and populates the SQLite table.
        """

        # 1. Durch das Submodule-Verzeichnis wandern und alle JSON-Dateien finden
        if not os.path.exists(self.pokemon_identifier):
            print(f"Fehler: Der Pfad '{self.pokemon_identifier}' wurde nicht gefunden. Bitte überprüfe deinen Submodule-Pfad.")
            return

        # 2. Datenbank-Tabelle vorbereiten (falls noch nicht geschehen)
        conn = self._get_connection()
        cursor = conn.cursor()

        print("Lese JSON-Daten aus dem Submodule... Bitte warten.")
        for root, dirs, files in os.walk(self.pokemon_identifier):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    set_id = file.replace(".json", "")
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            card_data_list = json.load(f)
                            # Add extracted set card list to db
                            for card in card_data_list:
                                inserted: bool = self._insert_pokemon_card_in_db(cursor, card, set_id)
                                if not inserted:
                                    logger.error(
                                        f"Fehler bei einfügen der Karte {card.get("name")} in die DB. Karte übersprungen.")
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
        logger.info(f"🎉 Fertig! Alle Sets in '{self.db_path}' eingetragen.")

    def reset_and_init_database(self):
        """Initializes the database schema with comprehensive gameplay field tracking."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Fixed syntax formatting and added price columns to the schema
        cursor.execute("DROP TABLE IF EXISTS card_hashes")
        cursor.execute(f"""
                       CREATE TABLE {self.table_name} (
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
        logger.info(f"💾 Advanced SQLite Database schema initialized at '{self.db_path}'.")

    def _extract_gzip_archive(self, archive_file_url: str):
        """
        Extracts the manually downloaded 'scryfall_bulk.jsonl.gz' archive
        into a plain text 'scryfall_bulk.jsonl' file on the disk.
        """
        if not os.path.exists(archive_file_url):
            logger.error(f"❌ Source archive '{archive_file_url}' not found in the directory!")
            logger.info("Please make sure the downloaded file is placed directly inside your PyCharm project folder.")
            return False

        logger.info(f"📦 Extracting '{archive_file_url}' into '{self.mtg_database_path}'...")
        try:
            # Open the compressed gzipped file in binary read mode
            with gzip.open(archive_file_url, 'rb') as f_in:
                # Open the target text file in binary write mode
                with open(self.mtg_database_path, 'wb') as f_out:
                    # Shutil optimized block-copy handles the internal buffer streaming efficiently
                    shutil.copyfileobj(f_in, f_out)

            logger.info(f"✅ Extraction successful! Plain text file ready at '{self.mtg_database_path}'.")
            return True

        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
            return False

    def _get_card_from_line(self, line: str) -> bool | None:
        line = line.strip()
        if not line:
            return None
        try:
            card = json.loads(line)
            return card
        except json.JSONDecodeError:
            return None

    def _insert_mtg_card_in_db(self, cursor, card: dict) -> bool:
        # Performance Filter: Digitale Karten (MTG Arena) oder Karten ohne Hauptbild überspringen
        if card.get("digital", False) or "image_uris" not in card:
            logger.info(f"Karte {card.get('name')} nicht hinzugefügt, da sie digital ist oder kein Bild vorhanden ist.")
            return False
        if self._is_id_in_db(card.get("id")):
            logger.info(f"Karte {card.get('name')} nicht hinzugefügt, da sie schon in der DB vorhanden ist.")
            return False

        image_url = card["image_uris"].get("normal")
        try:
            # Bild-Download für das Hashing (CDN-Server blockieren sehr selten)
            img = self._get_image(image_url)
            if img is None:
                logger.error(f"Kein Image für {card.get("name")} gefunden.")
                return False
            p_hash = str(imagehash.phash(img))

            # Preise parsen und sicher zu Floats konvertieren
            prices_dict = card.get("abilities", {})
            usd = float(prices_dict.get("usd")) if prices_dict.get("usd") else None
            eur = float(prices_dict.get("eur")) if prices_dict.get("eur") else None

            # SQL Einfügeoperation (Upsert-Logik)
            self._insert_into_db(cursor, card.get("id"), self.mtg_identifier, card.get("name"), card.get("set", "unk"),
                            card.get("collector_number"),
                            p_hash, card.get("rarity"), card.get("mana_cost", ""), card.get("cmc", 0.0),
                            card.get("type_line", ""), card.get("oracle_text", ""),
                            "".join(card.get("colors", [])), "".join(card.get("color_identity", [])), usd, eur)
            return True
        except Exception as e:
            logger.error(f"Fehler hinzufügen der Magic-Karte {card.get("name")} in die DB: {e}")
            return False

    def _insert_pokemon_card_in_db(self, cursor, card: dict, set_id: str) -> bool:
        card_id: str = card.get("id")
        if self._is_id_in_db(card_id):
            logger.info(f"Karte {card.get('name')} nicht hinzugefügt, da sie schon in der DB vorhanden ist.")
            return False
        card_name = card.get("name")
        coll_num = card.get("number")
        rarity = card.get("rarity", "Unknown")

        # HP as mana_cost
        mana_cost = "NONE"
        try:
            cmc = float(card.get("hp", 0))
        except ValueError:
            cmc = 0.0

        # type_line
        subtypes = card.get("subtypes", [])
        type_line = "/".join(subtypes) if subtypes else card.get("supertype", "")

        # oracle_text
        rules = []
        for ability in card.get("abilities", []):
            rules.append(f"[{ability.get('type')}]: {ability.get('text')}")
        for attack in card.get("attacks", []):
            rules.append(f"{attack.get('name')} ({attack.get('damage', '')}): {attack.get('text', '')}")
        oracle_text = " | ".join(rules) if rules else "No rules text."

        types_list = card.get("types", [])
        # colors and color_identity
        colors = "".join(types_list).upper() if types_list else "COLORLESS"
        color_identity = colors

        # Extract price will be fill when a concrete crad is scanned
        usd = None
        eur = None

        # Get Image
        image_url = card.get("images", {}).get("large")
        if not image_url:
            return False
        try:
            # Calculate pHash
            p_hash = self._get_phash(image_url)
            # Insert Card into DB
            self._insert_into_db(cursor, card_id, self.pokemon_identifier, card_name, set_id, coll_num, p_hash, rarity, mana_cost,
                            cmc, type_line,
                            oracle_text, colors, color_identity, usd, eur)
            return True
        except Exception as e:
            logger.error(f"Fehler beim einfügen der Pokemon Karte {card_name} in die Datenbank: {e}")
            return False

    def _get_image(self, image_url: str) -> Image:
        # Bild-Download für das Hashing (CDN-Server blockieren sehr selten)
        try:
            img_response = requests.get(image_url, headers=self.scryfall_header)
            if img_response.status_code == 200:
                img = Image.open(BytesIO(img_response.content))
                return img
            else:
                logger.error(f"Falscher HTTP status code: {img_response.status_code} beim ZUgriff auf {image_url}")
            return None
        except Exception as e:
            logger.error(f"Fehler bei Image Download {image_url}: {e}")

    def _get_phash(self, image_url: str) -> bool | str:
        try:
            # Bild-Download für das Hashing (CDN-Server blockieren sehr selten)
            image = self._get_image(image_url)
            if image is None:
                logger.error(f"Kein Image für {image_url} gefunden.")
                return False
            else:
                p_hash = str(imagehash.phash(image))
                return p_hash
        except Exception as e:
            logger.error(f"Fehler bei pHash generation for: {image_url}: {e}")
            return False

    def _insert_into_db(self, cursor, card_id: str, tcg: str, name: str, set_code: str, collector_num: int, phash: str,
                        rarity: str, mana_cost: str, cmc: float, type_line: str, oracle_text: str, colors: str,
                        color_identity: str, usd: float, eur: float):
        cursor.execute(f"""
                        INSERT OR REPLACE INTO {self.tabel_name} (
                        id, tcg, name, set_code, collector_num, phash, rarity,
                        mana_cost, cmc, type_line, oracle_text, colors, color_identity, usd, eur
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            card_id, tcg, name, set_code, collector_num, phash, rarity,
            mana_cost, cmc, type_line, oracle_text, colors, color_identity, usd, eur
        ))

    def _is_id_in_db(self, card_id: str) -> bool:
        """
        Prüft, ob ein Primary Key bereits in einer SQLite-Tabelle existiert.

        :param pk_spalte: Name der Primary-Key-Spalte
        :param pk_wert: Der Wert, nach dem gesucht werden soll
        :return: True, wenn der Key existiert, sonst False
        """
        # SQL-Abfrage mit EXISTS (sehr schnell, da die Suche beim ersten Treffer stoppt)
        # Wichtig: Tabellen- und Spaltennamen können nicht über Platzhalter (?) übergeben werden,
        # daher nutzen wir f-Strings. Achtung: Eingaben sollten aus sicheren Quellen stammen.
        query = f"SELECT EXISTS(SELECT 1 FROM {self.tabel_name} WHERE {card_id} = ?)"

        conn = self._get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            # Der card_id wird als Tupel (card_id,) übergeben, um SQL-Injection zu verhindern
            cursor.execute(query, (card_id,))

            # fetchone() gibt z.B. (1,) für True oder (0,) für False zurück
            ergebnis = cursor.fetchone()

            # Umwandlung des numerischen Ergebnisses (1 oder 0) in ein echtes Boolean
            return bool(ergebnis[0]) if ergebnis else False

        finally:
            # Die Verbindung wird in jedem Fall sauber geschlossen
            conn.close()