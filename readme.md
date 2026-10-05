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

## 📐 Software Architecture (MVC Pattern)
To ensure scalability and clean separation of concerns, this project is strictly structured around the **Model-View-Controller (MVC)** design pattern.

       ┌───────────────────────────────────────────────────┐
       │                    CONTROLLER                     │
       │                (SorterController)                 │
       └─────────┬───────────────────────────────┬─────────┘
                 │                               │
                 │ Updates Model                 │ Triggers Actions
                 │ & Reads State                 │ & Reads Sensors
                 ▼                               ▼
       ┌───────────────────┐           ┌───────────────────┐
       │       MODEL       │           │       VIEW        │
       │  (Card, State,    │           │ (LegoHardware,    │
       │   CardMatcher)    │           │  CameraWrapper)   │
       └───────────────────┘           └───────────────────┘

### 1. Model (Data & Core Logic)
The Model components handle data storage, configuration, and image processing. They remain entirely independent of the LEGO hardware or the UI layout.
* **`Card`:** Data class representing a physical card (Name, ID, Rarity, Target Bin).
* **`SorterState`:** Manages the runtime status (e.g., total cards sorted, bin capacities).
* **`CardMatcher`:** Implements OpenCV image-processing, thresholding, and Perceptual Hashing (pHash) to identify cards against a database.

### 2. View (Hardware & User Interfaces)
In this robotics context, the "View" represents any component that provides sensory input or mechanical output.
* **`LegoHardware`:** Encapsulates the `nxt-python` API. Translates logical system commands into precise motor degrees.
* **`Camera`:** Wrapper around OpenCV's `VideoCapture` to grab high-resolution frames.

### 3. Controller (Workflow & State Machine)
The Controller connects the Model and View layers. It runs the primary application loop and coordinates the sorting steps.

---

## 📂 Project Structure

```text
LegoTcgSorter/
│
├── .gitignore
├── README.md
├── requirements.txt
├── main.py                 # Application entry point (initializes M, V, C)
│
├── model/
│   ├── __init__.py
│   ├── card.py             # Card Data Class
│   ├── sorter_state.py     # Session stats & tracking
│   └── card_matcher.py     # Image-hashing & API lookup
│
├── view/
│   ├── __init__.py
│   ├── camera.py           # OpenCV capture wrapper
│   └── lego_hardware.py    # NXT motor control wrapper
│
└── controller/
    ├── __init__.py
    └── sorter_controller.py # Main loop / State machine
```

---

## 🔄 Main Sorting Loop Workflow

Each sorting cycle inside the `SorterController` executes the following sequence:
1. **Trigger Intake:** Controller calls `view.LegoHardware.feed_card()`.
2. **Capture Image:** Controller requests a frame via `view.Camera.get_frame()`.
3. **Analyze & Match:** Controller passes the frame to `model.CardMatcher.identify()`.
4. **Determine Action:** The Matcher returns a `Card` object containing the `target_bin`.
5. **Eject & Sort:** Controller executes `view.LegoHardware.sort_to_bin(target_bin)`.
6. **Log Statistics:** Controller increments tracking values in `model.SorterState`.

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
