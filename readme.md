# LEGO Mindstorms NXT 2.0 - TCG Sorter

Ein automatisiertes Sortiersystem für Trading Card Games (z.B. Magic: The Gathering, Pokémon), gesteuert über ein Python-Backend und einen LEGO Mindstorms NXT 2.0 Brick (8547).

## 🚀 Projekt-Architektur
Das Projekt nutzt einen **Master-Slave-Ansatz**, um die hardwareseitigen Limitierungen des NXT-Bricks zu umgehen:
* **Master (PC):** Übernimmt die rechenintensive Bildverarbeitung (Computer Vision) via OpenCV, den Abgleich mit TCG-Datenbanken und die Logik-Entscheidungen.
* **Slave (NXT):** Agiert als reines ausführendes Organ und steuert die Servomotoren für den Karteneinzug und die Sortierweichen basierend auf PC-Befehlen.

## 🛠️ Tech Stack & Voraussetzungen
* **Programmiersprache:** Python 3.12
* **IDE:** PyCharm (mit lokaler `venv`)
* **Firmware/Kommunikation:** NXT Standard-Firmware gesteuert via `nxt-python` & `pyusb`
* **Bildverarbeitung (Geplant):** OpenCV (`opencv-python`)

---

## 💻 Setup & Installation

### 1. Repository klonen & venv einrichten
```bash
git clone https://github.com
cd LegoTcgSorter
```
*Erstelle eine virtuelle Umgebung in PyCharm und aktiviere sie.*

### 2. Abhängigkeiten installieren
Die benötigten Python-Bibliotheken werden innerhalb der `venv` installiert:
```bash
pip install nxt-python pyusb opencv-python
```

### 3. USB-Treiber konfigurieren (Wichtig für Windows)
Da der standardmäßige LEGO-Fantom-Treiber nicht direkt mit Python kompatibel ist, muss der USB-Treiber umgeschrieben werden:
1. Das Tool **[Zadig](https://akeo.ie)** herunterladen und als Administrator starten.
2. Unter `Options` -> `List All Devices` aktivieren.
3. Den NXT-Brick (eingeschaltet und per USB verbunden) im Dropdown auswählen (Vendor ID: `0694`).
4. Als Ziel-Treiber **`libusb-win32`** auswählen und auf `Replace Driver` klicken.

---

## 🚦 Aktueller Meilenstein: Verbindungstest
Zum Überprüfen der Verbindung zwischen PC und NXT befindet sich das Skript `connect.py` im Root-Verzeichnis. Es initialisiert den Brick über USB und testet die Funktionalität eines Motors an Port A.

```bash
python connect.py
```

## 🗺️ Roadmap / Nächste Schritte
- [ ] Stabilen mechanischen Karteneinzug (Singulator/Reibrad) mit LEGO-Teilen konstruieren.
- [ ] Kamera-Setup und Bild-Pre-Processing (Freistellen der Karte, Ausrichtung) mit OpenCV implementieren.
- [ ] pHash (Perceptual Hashing) für den Abgleich der gescannten Karten mit TCG-Datenbank-Bildern integrieren.
- [ ] Mehrstufige Sortierlogik für die 3 NXT-Servomotoren programmieren.
