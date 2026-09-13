# Babylonian RPG: Life in the Cradle of Civilization
### Ancient Mesopotamia (c. 1750 BC / Old Babylonian Period)

An authentic, historically grounded life-simulation terminal RPG set in the city-state of Babylon during the golden reign of King Hammurabi. Built on historical economic records, the 282 statutory decrees of the Code of Hammurabi, astronomical diaries, and a dynamic macroeconomic flow market.

---

## Key Subsystems & Mechanics

### 1. 24-Hour Intraday Clock & Seasonal Rhythms
- **14-Day Seasons**: Each season (Autumn, Winter, Spring, Summer) is divided into 14 distinct days (`DAY 01/14` to `DAY 14/14`).
- **Intraday Progression**: The clock advances with every action through six distinct periods of the Mesopotamian day:
  - `Dawn` (05:00–07:59)
  - `Morning` (08:00–11:59)
  - `Midday Heat` (12:00–13:59)
  - `Afternoon` (14:00–17:59)
  - `Dusk` (18:00–20:59)
  - `Night` (21:00–04:59)
- **Rest & Sleep System**: Rest under the stars to recover 100% energy until 06:00 dawn, consume stored rations to sate hunger/thirst, or advance to the next season.

### 2. Living Macroeconomic Market & Astronomical Diaries CPI
- **29 Mesopotamian Commodities**: Traded across realistic categories—food staples, textiles, metals, luxury goods, building materials, and livestock.
- **Dynamic Flow Pricing**: Prices respond dynamically to supply and demand imbalances within a $[-75\%, +75\%]$ price corridor.
- **Esagila Consumer Price Index (CPI)**: Indexed against the 6 core Mesopotamian benchmark commodities (Barley, Dates, Mustard, Cress, Sesame, Wool).

### 3. Dual-Currency Financial System
- **Silver Shekels (Weighed Currency)**: 1 talent = 60 minas = 3,600 shekels = 648,000 grains (1 shekel = 180 grains).
- **Barley Qa / Sila (Volumetric Currency)**: 1 gur = 300 qa (approx. 300 liters). Used as an official medium of exchange, wage standard, and legal tender under Babylonian law.

### 4. Artisan Workshops & Non-Linear Economies of Scale
- **Facility Tiers**:
  - **Tier 1: Domestic Courtyard**: Family production (Max 3 batches/run, 0 hired workers).
  - **Tier 2: Guild Workshop**: Dedicated brick kilns, vats, and looms (Max 8 batches/run, 1 hired worker, +15% speed).
  - **Tier 3: Patrician Manufactory**: Large-scale manufactory (Max 25 batches/run, 3 hired workers, +30% speed).
- **Sub-Linear Production Scaling**:
  $$\text{Production Time} = \text{base\_hours} \times \left(0.4 + 0.6 \times N^{0.85}\right) \times \text{facility\_multiplier} \times \text{wage\_speed\_mult}$$
  Large batches take significantly less time per unit due to pre-heated ovens and division of labor.

### 5. Labor Management & Statutory Wages (Code §§ 273–274)
- **Hired Artisans (*Agru*)**: Employ craftsmen to operate Tier 2 and Tier 3 facilities.
- **Configurable Wage Policies**:
  - `STINGY`: 3 grains/day (below statutory min; workers grumble, +25% production time).
  - `STATUTORY`: 5 grains/day $\times$ CPI (lawful Code § 274 baseline; reliable 1.0x speed).
  - `EFFICIENCY`: 8 grains/day $\times$ CPI (generous efficiency wage; attracts master artisans, -20% production time).
- **Midnight Payroll**: Daily wages are settled automatically each night. Defaulting causes workers to down tools and depart.

### 6. Agriculture, Irrigation & Seasonal Harvests
- **Autumn**: Plowing and sowing seed across canal fields.
- **Winter**: Canal dredging, clearing silt from irrigation ditches, and dike maintenance.
- **Spring**: The great barley and flax harvest, plus sheep shearing for raw wool.
- **Summer**: Euphrates flood surge and date palm gathering.
- **Draft Oxen & Titles**: Oxen provide a +25% harvest yield bonus per ox. Land deeds are inscribed in sealed cuneiform clay tablets.

### 7. Long-Distance Trade Caravans (Tamkarum Expeditions)
- **Historical Corridors**:
  - *Anatolian Highlands*: Export woolen textiles & tin; import raw copper and silver.
  - *Dilmun Entrepôt (Bahrain)*: Maritime transshipment of copper ingots and pearls.
  - *Magan (Oman)*: Coastal fleet transport for diorite and copper ore.
  - *Meluhha (Indus Valley)*: Exotic voyages importing carnelian beads and lapis lazuli.
- **Fleets & Security**: Organize donkey caravans, river barges, or deep-draft Dilmun ships with hired armed guards (*rēdû*).

### 8. Civic Politics, Puhrum Assembly & Offices
- **Class Structure**: Ascend the social hierarchy from *Wardum* (indentured servant) to *Mushkenum* (free commoner) to *Awilum* (patrician noble).
- **Five Historical Civic Magistracies**:
  1. `Gugallum` (Canal Inspector & Water Bailiff)
  2. `Rabi Sikkatim` (Captain of the City Guard)
  3. `Dayyānum` (High Judge at the Gate of Shamash)
  4. `Šangû` (Temple Chief Administrator)
  5. `Rabiānum` (City Governor & Mayor)
- **Assembly Elections**: Campaign in the Puhrum council of elders through speeches, public feasts, and strategic gifts.

### 9. Hall of Justice at the Gate of Shamash
- **Code of Hammurabi Jurisprudence**: Litigate civil and commercial disputes (debt usury, boundary violations, theft, assault).
- **The Sacred River Ordeal of Id (Code § 2)**: For serious unproven charges, submit to the divine currents of the sacred Euphrates.

### 10. Domestic Life, Marriage Covenants & Cylinder Seals
- **Code § 128 Marriage Contracts**: Sealed contracts (*rikistum*) with bride-price (*terhatum*) and dowry (*seriktum*).
- **Divorce Settlements (Code §§ 137–142)**: Legal dissolution with statutory dowry restitution.
- **Cylinder Seals (*Kunukku*)**: Carved seals in Steatite, Hematite, Carnelian, or Lapis Lazuli mounted with royal gold filigree to seal clay tablets.

---

## Quick Start

### Requirements
- Python 3.8+ (no external third-party dependencies required; uses Python standard library).

### Launching the Game
Clone the repository and run:
```bash
python main.py
```

### Running the Subsystem Smoke Test
Validate all game subsystems, time progression, batch production, and savegame serialization:
```bash
python main.py --test
```

---

## File Architecture

```
babylonian_rpg/
├── main.py                     # Master game engine, 24-hour clock, dashboard HUD, and game loop
├── economics.py                # 29 commodities, flow market, PMs, and Esagila CPI
├── character.py                # Dual wallet (silver/barley), needs, cylinder seals, clay tablets
├── politics.py                 # 5 civic offices, Puhrum elections, lawsuits, and royal decrees
├── marriage.py                 # Code of Hammurabi marriage covenants (§ 128), dowries, and divorce
├── trade.py                    # Tamkarum trade expeditions, donkey caravans, and Gulf fleets
├── economics_reference.md      # Mathematical reference for the flow pricing and CPI system
├── idea_game_concept.md        # Original design document and historical setting notes
├── walkthrough.md              # Feature walkthrough and subsystem verification notes
├── Babylonian Era Economic Goods.pdf # Historical reference source
├── LICENSE                     # Apache 2.0 License
└── README.md                   # Project documentation
```

---

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.