# Future Game Feature Suggestions & Design Roadmap

This document outlines proposed gameplay mechanics and systemic upgrades discussed for future updates of **Babylonian RPG**.

---

## 1. Asynchronous Multi-Day Caravan Expeditions

### The Current Behavior (Instant Resolution)
* In the current build, sponsoring an expedition through the **Tamkarum Guild (`[4]`)** advances the game clock by **2.0 hours** (representing contract signing, pack inspection, and customs intake at the quay).
* The entire round-trip (e.g. 5 days for Dilmun, 14 days for Anatolia, 28 days for Meluhha) is simulated and resolved immediately.
* While great for rapid prototyping and quick market testing, it allows a player to theoretically dispatch and return 10 multi-season international caravans in a single afternoon!

---

### The Proposed Asynchronous System

Instead of instant teleportation, caravans should operate as **living expeditions traveling over real in-game days** while the player lives their life in Babylon:

```
[ Day 01: Morning ]
  Chakra finances Tamkarum Ur-Nungal at the Kārum Quay.
  * Cargo: 3 Spoked War Chariots loaded onto 6 pack donkeys.
  * Silver Purse: 50 shekels | Provisions: 168 qa grain fodder.
  * Destination: Kanesh (Anatolia) - Round-trip: 14 Days.
  * Status: Expedition Dispatched -> Departs through the Ishtar Gate.

[ Days 02 – 13: Life in Babylon ]
  Chakra stays in the capital, tending fields, managing artisan manufactories,
  litigating lawsuits at the Gate of Shamash, and advancing seasons.
  * Active Caravan Board: "Expedition #001: En Route across the Syrian Steppe (Day 6/14)".

[ Day 14: Dawn ]
  A gate messenger arrives at Chakra's domestic villa:
  "Lookouts atop the Marduk Gate have sighted the donkey train!
   Tamkarum Ur-Nungal has safely returned from Anatolia!"
  * Returns with 120 units Cassiterite Tin, 450 silver shekels, and fresh foreign news.
```

---

### Key Technical Implementation Details

#### 1. Mission State Tracking (`CaravanMission`)
Add calendar timing fields to `CaravanMission` in `trade.py`:
```python
@dataclass
class CaravanMission:
    id: str
    sponsor_name: str
    tamkarum_name: str
    corridor: TradeCorridor
    fleet: TransportFleet
    outbound_cargo: Dict[str, float]
    return_cargo: Dict[str, float]
    silver_capital_carried: float
    grain_fodder_carried: float
    departure_day: int
    departure_season: int
    departure_year: int
    total_days_required: int
    days_elapsed: int = 0
    is_completed: bool = False
    is_plundered_or_lost: bool = False
    target_import: Optional[str] = None
```

#### 2. Daily Tick & Clock Hook (`advance_hours` & `handle_sleep`)
* Whenever a day completes (either through hourly progression past 24:00 or sleeping until 06:00 dawn), check `trade_mgr.active_missions`:
  * Increment `mission.days_elapsed += 1`.
  * If `mission.days_elapsed >= mission.total_days_required`:
    * Trigger arrival ceremony and resolve trade payouts (`trade_mgr.resolve_mission`).
    * Display a banner in the morning Gazette:
      `[★] CARAVAN RETURN: Expedition to Kanesh has docked at the quay with imported cargo!`

#### 3. Dynamic Mid-Journey Events (Hazard Rolls)
Rather than a single dice roll upon departure, roll dynamic narrative events during travel:
* **Nomad Tolls**: Sutean desert raiders demand a 5-silver passage tax; mercenary guards negotiate or fight.
* **Desert Oasis Trade**: An unexpected encounter with an Elamite caravan allows buying rare raw materials en route.
* **River Floods / Muddy Mountain Passes**: Adds a 1–2 day delay if pack animals get bogged down.

#### 4. Active Fleet & Port Board in Menu `[4]`
Display a live dashboard at the Tamkarum Guild:
```
======================================================================
         THE TAMKARUM MERCHANTS' GUILD - EXPEDITION BOARD
======================================================================
 [Active Expeditions in Transit]:
  * EXP_0001 (Kanesh / Anatolia): Day 09/14 | En Route | 6 Donkeys
    Outbound: 2 War Chariots | Target Import: Cassiterite Tin
  * EXP_0002 (Dilmun / Bahrain): Day 04/05 | Returning | 2 Donkeys
    Outbound: Cash Purse | Target Import: Bitumen (Arrives Tomorrow!)

 [1] Launch New Caravan Expedition (Select Destination & Fleet)
 [2] Inspect Active Expeditions & Tamkarum Contracts
 [0] Return to City Square
======================================================================
```

#### 5. Save/Load Persistence
* Serialize `active_missions` inside `save_game()` so en-route expeditions are preserved when saving to clay archive slots.

---

## 2. Dynamic Foreign City Stock Depletion (Market Memory)

* **Concept**: If the player dumps 20 War Chariots in Anatolia, the foreign markup should temporarily soften (e.g. from $1.5\times$ down to $1.2\times$), gradually recovering over several in-game seasons as foreign kings consume the goods in their wars.
* **Benefit**: Encourages rotating trade corridors between Anatolia, Dilmun, Magan, and Meluhha rather than spamming a single route indefinitely.
