# Walkthrough: Babylonian RPG - Life in the Cradle of Civilization

We have built, integrated, and verified a feature-complete ancient Mesopotamian life-simulator RPG in [main.py](file:///d:/arc/el/finance/wunder/New%20folder/New%20folder/shipd/Kaggriculture-alt/kaggriculture-data/Babylonian_rpg/main.py). The game is set in Babylon during the reign of King Hammurabi (c. 1750 BC) and is driven by historical Babylonian economic data, the 282 statutory decrees of the Code of Hammurabi, and a *Victoria 3*-style dynamic flow macroeconomy.

---

## 1. System Architecture & Modular Subsystems

The game engine is built on 6 decoupled, cooperating modules located in [Babylonian_rpg](file:///d:/arc/el/finance/wunder/New%20folder/New%20folder/shipd/Kaggriculture-alt/kaggriculture-data/Babylonian_rpg/):

```
Babylonian_rpg/
├── main.py                 # Master Playable Game Loop, UI Dashboard, Turn Cycle & Save/Load
├── economics.py            # Victoria 3 Flow-Market, 29 Goods, PMs, Esagila CPI
├── character.py            # Dual-Currency Wallet, Biological Metabolism, Cylinder Seals, Tablets
├── marriage.py             # Code §§ 128-176 Marriage Covenants, Terhatum, Seriktum, Divorce
├── trade.py                # Tamkarum Guild, 4 Foreign Corridors, Pack Donkey & Gulf Barge Logistics
├── politics.py             # 5 Civic Offices, Puhrum Assembly, Hammurabi Lawsuits, Misharum Jubilees
├── economics_reference.md  # Historical Commodity Manual & Market Formula Reference
└── idea_game_concept.md    # Core Game Design Bible & Four Pillars
```

---

## 2. Core Gameplay Systems in `main.py`

### Archetypes & Character Creation
* **Awilum (Patrician Noble / Merchant)**: Starts with 100 silver shekels, 2 gur barley (600 qa), 20 acres arable land, 2 draft oxen, high literacy, and a Lapis Lazuli cylinder seal inscribed to Marduk.
* **Mushkenum (Free Commoner / Yeoman / Artisan)**: Starts with 10 silver shekels, 1 gur barley (300 qa), 5 acres arable land, practical farming/craft skills, and a Steatite cylinder seal inscribed to Shamash.
* **Wardum (State Servant / Indebted Bondman)**: Starts with 0.5 silver shekels, 60 qa basic food rations, zero land, and no cylinder seal. Must labor and earn silver to purchase a Charter of Manumission.

### 1. The Kārum Public Market
* Browse real-time commodity prices across all 29 Mesopotamian goods or focused sectors.
* Buy and sell goods using weighed silver shekels.
* Direct feedback into the *Victoria 3* market solver: buying increases local demand and raises prices; selling satisfies domestic shortages and lowers prices within the $[-75\%, +75\%]$ corridor.

### 2. Agriculture, Livestock & Workshops
* **Seasonal Fieldwork**:
  * **Autumn**: Sowing seed barley ($10\text{ qa/acre}$) and plowing.
  * **Winter**: Clearing silt from canal ditches and reinforcing dikes.
  * **Spring**: The Great Harvest! Bountiful grain yields boosted by draft oxen ($+25\%$ per ox) and agricultural proficiency, plus wool shearing from sheep.
  * **Summer**: Date palm harvesting along riverbanks and flood mitigation.
* **Arable Land Deeds**: Buy ($20\text{ silver/acre}$) or sell ($15\text{ silver/acre}$) land, accompanied by sealed cuneiform clay title deeds.
* **Livestock Market**: Draft oxen ($15\text{ silver}$) and wool sheep ($2\text{ silver}$).
* **Artisan Workshops**:
  * *Brewery*: Mash barley into cloudy barley beer.
  * *Bakery*: Bake barley into flatbread loaves.
  * *Weaver's Loom*: Weave raw wool into fine woolen cloth.
  * *Smithy*: Smelt copper ore and tin into durable bronze tools.
  * *Brickyard*: Sun-dry reeds and mud into construction mudbricks.
* **Municipal Corvée Wage Labor**: Work royal canals for statutory wages under Code §§ 273–274 ($5\text{ grains of silver/day} \approx 0.83\text{ shekels/month}$).

### 3. The Ale-Wife's Tavern (*Bīth Šikari*)
* Drink cloudy barley beer or fermented date wine through reed straws to quench thirst, restore energy, and heal.
* **The Royal Game of Ur (Dice Minigame)**: Authentic betting minigame casting 4 tetrahedral pyramid dice (rolling $0 \dots 4$ points) against tavern patrons for silver shekels.
* Gather street rumors about foreign caravan arrivals, impending flood levels, and royal edicts.
* Consult the matchmaker for marriage covenants across social classes.

### 4. Long-Distance *Tamkarum* Caravans
* Sponsor expeditions across 4 historical trade corridors:
  1. **Anatolia & Levant** (Overland 90 days: imports Tin and Cedar Timber).
  2. **Dilmun / Bahrain** (Gulf Entrepôt 30 days: imports Pearls, Dates, Bitumen).
  3. **Magan / Oman** (Copper Coast 60 days: imports Raw Copper Ore).
  4. **Meluhha / Indus Valley** (Oceanic East 120 days: imports Lapis Lazuli, Carnelian, Ivory).
* Configurable fleet scale (Small 2-donkey scouting team, Standard 6-donkey merchant train, or Gulf seagoing vessel).
* Automated provision calculation (grain fodder and guard wages) with realistic transit hazard rolls, gate customs tariffs (*Miklū*), and foreign profit returns.

### 5. Civic Politics & The *Puhrum* Assembly
* Seek the 5 historical offices: *Gugallum* (Canal Warden), *Rabi Sikkatim* (Market Overseer), *Dayyānum* (City Magistrate), *Šangû* (Temple High Priest), and *Rabiānum* (City Governor).
* Election campaigning through silver bribes to the Council of Elders, public beer/bread feasts of Ishtar for commoners, and oratory speeches.
* Executive duties: dredge canals, inspect market weights, collect seasonal salaries, or petition the Great King for a *Misharum* debt jubilee.

### 6. The Gate of Shamash (Hall of Justice)
* Prosecute rivals under the Code of Hammurabi:
  * Usury violations ($>20\%$ interest, Code § 88).
  * Canal dike negligence causing neighbor field floods (Code §§ 53–55).
* **The Sacred River Ordeal of Id (Code § 2)**: When evidence is deadlocked, dive into the Euphrates river currents; divine judgment determines guilt, acquittal, or punishment.

### 7. Domestic Household & Cuneiform Clay Archive
* Marriage management under Code § 128 (*rikistum*).
* Dowry custody (*šeriktum*) in trust.
* Statutory divorce settlements and alimony under Code §§ 137–142.
* Inspection of all cylinder-seal imprinted clay tablets.

### 8. Living Seasonal Simulation & Save/Load
* Advance through Autumn $\rightarrow$ Winter $\rightarrow$ Spring $\rightarrow$ Summer.
* Automatic biological metabolism (eating stored food or suffering hunger/thirst).
* Macroeconomic quarterly market updates and price movements.
* Full game state serialization to and from `savegame.json`.

---

## 3. Verification & Automated Smoke Test

The master game engine was tested and verified via `python main.py --test`:

```
==============================================================================
      BABYLONIAN RPG - MASTER SUBSYSTEM INTEGRATION SMOKE TEST
==============================================================================

[1/7] Testing Dashboard Render...
==============================================================================
 YEAR 01 | AUTUMN (Sowing of Seeds & Plowing) | Esagila CPI: 1.000x
==============================================================================
 Citizen:     Iddin-Sin, son of Ea-malik     | Class:  Mushkenum
 Office:      Private Citizen                | Honor:  50.0/100
 Health:      [██████████] 100%        | Energy: [██████████] 100%
 Hunger:        0/100 (Satiated)   | Thirst:   0/100 (Quenched)
------------------------------------------------------------------------------
 Silver (Weighed):    10.00 shekels (1800 grains) | 1 mina = 60 shekels
 Barley (Volume):      1.00 gur (  300 qa / sila)    | 1 gur  = 300 qa
 Real Estate:           5.0 acres arable land | Draft Oxen:  0 | Wool Sheep:  0
 Cylinder Seal:     Steatite (Servant of Shamash)
 Inventory:         barley_beer: 2.0, pottery: 3.0, woolen_cloth: 1.0
 Domestic Estate:   Unmarried | Cuneiform Tablets Sealed: 0
==============================================================================

[2/7] Testing Market Subsystem...
 [+] Market transactions verified.

[3/7] Testing Agriculture & Workshop Labor...
 [+] Workshop brewing verified.

[4/7] Testing Marriage Covenant under Code § 128...
 [+] Marriage contract sealed in clay.

[5/7] Testing Tamkarum Caravan Logistics...
 [+] Caravan voyage successfully resolved.

[6/7] Testing Assembly Politics & Court Litigation...
 [+] Court litigation resolved.

[7/7] Testing Season Advance & Save/Load...
 [+] Season complete! Dawn breaks on WINTER (Year 1).
 [+] Game state successfully imprinted to clay archive 'savegame.json'!
 [+] Save/Load verified.

==============================================================================
   ALL BABYLONIAN RPG SUBSYSTEMS FULLY OPERATIONAL & VERIFIED!
==============================================================================
```

### Launching the Playable Game
To play the interactive terminal game in your shell:
```bash
cd "d:/arc/el/finance/wunder/New folder/New folder/shipd/Kaggriculture-alt/kaggriculture-data/Babylonian_rpg"
python main.py
```
