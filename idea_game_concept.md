# Babylonian RPG: Life in the Cradle of Civilization
## Preliminary Game Concept & High-Level Design Document

> *"When Anu the Sublime and Enlil, lord of heaven and earth, committed the rule of all mankind to Marduk... then they named Babylon by its illustrious name, and made it great upon the earth."*  
> — **Preamble to the Code of Hammurabi (c. 1750 BC)**

---

## 1. High Concept & Elevator Pitch

* **Genre:** Historical Life-Sim RPG with a Dynamic Macroeconomic Engine.
* **Inspiration:** *Medieval Dynasty* & *Kenshi* meets *Victoria 3* & *The Guild*.
* **Setting:** Southern Mesopotamia along the Euphrates River (Babylon, Nippur, Sippar, and Ur) during the Bronze/Early Iron Age transition.
* **Core Fantasy:** You are not an omniscient deity pushing abstract sliders—you are an individual human being born into the world's first true urban civilization. Start as an indebted tenant farmer, a ditch-digger on royal canals, or an apprentice potter, and navigate a **living, simulated economy** where every grain of barley, jar of sesame oil, and weighed silver shekel physically flows through supply chains. Rise to become a master artisan, a wealthy estate landlord, or an international merchant prince (*tamkarum*) whose trade caravans shape the geopolitical balance of the ancient Near East.

---

## 2. Core Pillars

```
                               +---------------------------------------------+
                               |         BABYLONIAN LIFE SIM RPG             |
                               +---------------------------------------------+
                                                      |
         +------------------------+-------------------+------------------------+
         |                        |                   |                        |
         v                        v                   v                        v
+------------------+     +------------------+  +-------------------+  +-------------------+
|  LIVING VIC-3    |     | CLASS & SOCIAL   |  | CIVIC POLITICS    |  | EVERYDAY BRONZE   |
|  MACRO ECONOMY   |     | MOBILITY (3 TIER)|  | & OFFICES (GUILD) |  | AGE ANTIQUITY     |
+------------------+     +------------------+  +-------------------+  +-------------------+
| • Flow Buy/Sell  |     | • Wardum (Labor) |  | • Canal Warden    |  | • Cuneiform Clay  |
| • No magic items |     | • Mushkenum(Free)|  | • Market Overseer |  |   Debt Contracts  |
| • Production PMs |     | • Awilum (Elites)|  | • City Magistrate |  | • Hydraulic canals|
| • 6-Good CPI     |     | • Upward mobility|  | • Temple HighPriest| | • Taverns & Beer  |
+------------------+     +------------------+  +-------------------+  +-------------------+
```

### Pillar I: A Living, Flow-Based Economy (Victoria 3 Mechanics)
* **No "Magic Merchant" Inventories:** NPCs and market stalls don't spawn infinite gold or items. Goods exist because someone harvested, transported, and processed them.
* **Buy/Sell Flow Pricing:** Prices rise and fall based on the exact ratio of local supply (Sell Orders) to demand (Buy Orders). 
* **Input-Output Production Methods:** Bakeries consume raw grain and date syrup to make bread; oil presses consume sesame to produce lamp fuel and cooking fats; brickyards consume river silt, straw, and bitumen to make kiln-fired bricks.
* **Systemic Shocks:** Silt clogs the canals $\to$ harvest drops $\to$ bread price spikes $\to$ urban workers strike or riot $\to$ royal palace intervenes with price controls or bread subsidies.

### Pillar II: The Three Estates & Dynamic Social Mobility
Mesopotamian society was divided into three legal classes with stark rights, obligations, and lifestyle standards under Hammurabi's Code:
1. **Wardum (State Laborers, Debt-Servants, Slaves):**
   * Subsist on royal rations (standardized measures of barley, wool, and oil).
   * Do the grueling physical work: canal dredging, brick-molding, city wall construction.
   * Can earn private silver on the side to purchase their own freedom.
2. **Mushkenum (Free Commoners, Tenant Farmers, Guild Artisans):**
   * The vast middle class. Rent fields, run private craft shops, pool grain into village granaries.
   * Legally free, but subject to military drafts and royal corvée labor.
   * High risk: A single bad harvest or unpayable loan can cause foreclosure into debt bondage.
3. **Awilum (Patricians, Landowners, Temple Priests, Royal Scribes):**
   * The aristocracy. Own large private estates, control temple trade, hold administrative seats.
   * Fund international merchant caravans (*tamkarum*) and collect commercial rents.
   * Enjoy full legal privileges, but pay heavy penalties for malpractice under the Code.
* **The Player's Ascent:** The game features total vertical mobility. Save silver, buy land deeds, hire tenant laborers, obtain a personalized cylinder seal, and enter high political society—or mismanage debts and face the debtor's court.

### Pillar III: Authentic Bronze Age Daily Life
* **Cuneiform Tablet System:** All major financial interactions (loans, land purchases, employment contracts) are recorded on clay tablets. Players carry, bake, and sign tablets with their custom **Cylinder Seal**.
* **The River as Lifeblood:** The Euphrates is your road and your greatest hazard. Navigate reed coracles and wooden riverboats; watch seasonal floods that deposit fertile silt or wipe out earthen dikes.
* **Beer & Tavern Culture:** Ancient Babylon ran on cloudy barley beer (*Sikaru*), consumed through drinking straws to filter chaff. Taverns (often run by female brew-mistresses) are the social hubs for rumors, trade intelligence, hiring labor, and black-market credit.
* **Royal Edicts (*Misharum*):** When agrarian debt reaches boiling points, the King can declare a clean-slate debt jubilee, invalidating private consumer debts, freeing debt slaves, and shocking merchant balance sheets!

---

## 3. Core Gameplay Loop

```
  [DAILY SURVIVAL & CONSUMPTION]
  • Eat daily bread/dates, drink beer/water, maintain shelter, pay rent/taxes.
                   │
                   ▼
  [ECONOMIC ACTIVITY & LABOR]
  • Work as laborer/artisan OR manage your own fields, kilns, or textile looms.
  • Buy inputs from city market stalls at prevailing supply/demand prices.
                   │
                   ▼
  [VALUE-ADD PROCESSING & TRADE]
  • Transform raw goods (Barley -> Beer; Sesame -> Perfumed Oil; Wool -> Dyed Garments).
  • Sell finished wares on the domestic market OR pack onto donkey caravans.
                   │
                   ▼
  [CAPITAL ACCUMULATION & INVESTMENT]
  • Convert earnings into Weighed Silver Shekels (hoard in vault or lend at interest).
  • Buy Arable Land Deeds, upgrade workshop Production Methods, hire workers.
                   │
                   ▼
  [SOCIAL MOBILITY & INFLUENCE]
  • Commission a reverse-intaglio Cylinder Seal.
  • Sponsor foreign trade routes to Dilmun, Magan, or Anatolia.
  • Gain standing in the City Assembly (Puhrum) or Temple Priesthood.
```

---

## 4. Playable Character Archetypes / Backgrounds

Players can choose their starting background or forge their own path:

| Archetype | Starting Social Class | Core Skills & Focus | Primary Gameplay Loop |
| :--- | :--- | :--- | :--- |
| **The Tenant Farmer** | *Mushkenum* (Commoner) | Agriculture, Irrigation, Ox-handling | Managing seasonal crops, dredging feeder canals, storing grain against rats, avoiding debt foreclosures. |
| **The Urban Artisan** | *Mushkenum* (Commoner) | Crafting (Pottery, Brewing, Weaving) | Sourcing cheap raw inputs (clay, wool, barley), producing goods, selling in market stalls, expanding workshop. |
| **The Junior Scribe** | *Mushkenum* $\to$ *Awilum* | Literacy, Accounting, Administration | Drafting cuneiform contracts, measuring granaries, calculating taxes for the palace, finding legal loopholes. |
| **The Caravan Merchant** | *Awilum* (Patrician) | Commerce, Appraisal, Navigation | Borrowing palace silver, assembling donkey caravans, arbitrage between Babylon and foreign nodes (Anatolia, Dilmun). |
| **The Ambitious Magistrate** | *Awilum* (Patrician) | Rhetoric, Law (Code of Hammurabi), Intrigue | Climbing from Canal Warden to City Governor, trading political favors, manipulating market regulations and legal verdicts. |
| **The Indebted Laborer** | *Wardum* (Servant) | Manual Labor, Street Smarts, Resilience | Working off family debt on state projects, saving secret silver, plotting escape or legal redemption. |

---

## 5. Key Simulation Systems

### 5.1 The Dual-Currency Wallet
1. **The Barley Standard (`še'u`):**
   * Volumetric measure: *qa* (~0.85 L) and *gur* (300 qa).
   * Used for daily food purchases, tavern tabs, field hand wages, and agricultural debts.
   * **Mechanic:** Bulky, perishable (rots/eaten by rats if improperly stored), but accepted everywhere.
2. **The Silver Standard (`kaspum`):**
   * Mass measure: *shekel* (~8.3g), *mina* (60 shekels), *talent* (60 minas).
   * Circulates as cast coils, rings, and cut pieces ("hacksilver").
   * Used for wholesale commerce, real estate, luxury imports, and institutional investments.
   * **Mechanic:** Weight-based, non-perishable, immune to vermin, but requires trust or testing for purity.

### 5.2 Pop Needs & Standard of Living (SoL)
Every NPC and player character has an ongoing consumption basket:
* **Hunger & Hydration:** Raw barley flatbread, bappir, beer, dried fish, onions, dates.
* **Household Comfort:** Sesame lamp oil for nighttime light, reed mats, wool blankets, pottery storage jars.
* **Status & Luxury (Elites):** Fine linen tunics, Tyrian purple dyes, myrrh/frankincense perfumes, date wine, lapis lazuli cylinder seals.
* **Goods Substitution:** If barley is too expensive due to drought, pops buy dates or legumes instead. If both are gone, starvation strikes, leading to unrest, crime, or flight into nomadic desert tribes.

### 5.3 Legal & Contract System (Code of Hammurabi)
* **Written Contracts:** When hiring workers, leasing land, or taking loans, you stamp an inscribed clay tablet.
* **Statutory Caps:** Interest is capped at 20% for silver and 33.3% for grain. Going above this forfeits principal.
* **Strict Liabilities:** 
  * If a builder builds a house that collapses, he pays compensation or faces execution.
  * If a tenant farmer neglects the irrigation dike and floods his neighbor's field, he must compensate the damaged crop.

### 5.4 The Political Ladder & Civic Offices (*The Guild* Style)
Politics in the Mesopotamian city-state is not a distant abstraction—it is run by municipal councils, temple colleges, and royal magistrates who hold immense discretionary power over commerce, public works, and the law:

```
                       [THE CIVIC POWER HIERARCHY]
                                    ▲
                                    │
               ┌────────────────────┴────────────────────┐
               │    CITY GOVERNOR / MAYOR (Rabiānum)     │
               │  Executive command, garrison, decrees   │
               └────────────────────┬────────────────────┘
                                    │
          ┌─────────────────────────┴─────────────────────────┐
          │                                                   │
┌─────────────────────────┐                               ┌─────────────────────────┐
│ TEMPLE HIGH PRIEST      │                               │ CITY MAGISTRATE / JUDGE │
│ (Šangû)                 │                               │ (Dayyānum)              │
│ Sacred estates, tithes, │                               │ Courts, deed disputes,  │
│ festivals, offerings    │                               │ Code enforcement        │
└─────────┬───────────────┘                               └─────────┬───────────────┘
          │                                                         │
          └─────────────────────────┬───────────────────────────────┘
                                    │
          ┌─────────────────────────┴─────────────────────────┐
          │                                                   │
┌─────────────────────────┐                               ┌─────────────────────────┐
│ MARKET OVERSEER         │                               │ CANAL WARDEN            │
│ (Rabi Sikkatim)         │                               │ (Gugallum)              │
│ Tariffs, silver purity, │                               │ Water sluices, corvée,  │
│ price caps, stall fees  │                               │ dike maintenance        │
└─────────────────────────┘                               └─────────────────────────┘
```

1. **The Civic Offices:**
   * **Canal Warden (*Gugallum*):**
     * *Department:* Irrigation & Public Works.
     * *Powers:* Directs royal corvée labor to dredge canals; opens/closes river sluice gates; investigates dike breaches; levies canal repair assessments on local farmers.
     * *Abuse of Power:* Skim repair silver; prioritize your own fields' irrigation while starving a rival's crops of water.
   * **Market Overseer (*Rabi Sikkatim*):**
     * *Department:* Commerce & Tax.
     * *Powers:* Inspects merchant stalls and incoming donkey caravans at the city gates; tests silver coil purity; enforces Hammurabi's statutory wage/price ceilings; collects market stall fees.
     * *Abuse of Power:* Extort foreign *tamkarum* merchants; accept bribes to overlook light-weight silver or watered-down beer; confiscate "contraband" goods.
   * **City Magistrate / Judge (*Dayyānum*):**
     * *Department:* Justice & Civil Disputes.
     * *Powers:* Sits at the Gate of Shamash with the Council of Elders (*Šībūtum*); adjudicates property boundaries, broken contracts, debt foreclosures, and malpractice claims under the Code of Hammurabi.
     * *Abuse of Power:* Accept gifts from wealthy litigants to rule against vulnerable debtors; foreclose on rival estates and reassign land deeds to allies.
   * **Temple Administrator / High Priest (*Šangû*):**
     * *Department:* The Sacred Economy (Esagila / Temple of Marduk).
     * *Powers:* Manages vast temple estates, sacred sheep flocks, and grain storehouses; orders luxury offerings (incense, date wine, bleached linen); collects religious tithes; organizes the New Year (*Akitu*) festival.
     * *Abuse of Power:* Divert temple loans to personal trade syndicates; declare political rivals ritualistically impure.
   * **City Governor / Royal Mayor (*Rabiānum* / *Šakkanakku*):**
     * *Department:* Executive Governance & Military Defense.
     * *Powers:* Commands city watchmen and chariot garrisons; sets municipal grain reserve targets during droughts; negotiates trade treaties; petitions the King in Babylon for a royal debt jubilee (*Misharum*).

2. **Political Campaigning & Intrigue:**
   * **The City Assembly (*Puhrum*):** Free citizens gather at the city gate to vote on vacant offices and municipal policy.
   * **Electoral Tactics:**
     * *Populist Benefaction:* Sponsoring free beer (*Sikaru*) and bread banquets during the Feast of Ishtar to win commoner votes.
     * *Patrician Alliances:* Arranging dowry marriages, signing joint trade contracts, and trading votes with prominent merchant houses.
     * *Blackmail & Litigation:* Uncovering clay tablets showing a rival charged $>20\%$ interest (usury) or failed to maintain their dike, prosecuting them publicly under the Code of Hammurabi to disqualify them from office!

---

## 6. Development Roadmap (Next Steps)

1. **Phase 1: Economic Data & Schema (`economics_reference.md`)**
   * Finalize the comprehensive taxonomy of all raw, processed, and luxury goods.
   * Define input-output tables, base prices, labor ratios, and consumption baskets.
2. **Phase 2: Headless Python Simulation Engine**
   * Build the standalone market solver (Buy/Sell orders, dynamic pricing, production method tick).
   * Integrate demographic pop simulation (reproduction, consumption, class mobility).
3. **Phase 3: Player Interaction Layer**
   * Character state, inventory (weighed silver + volumetric grain), crafting recipes.
   * Clay tablet contract generation and market stall interactions.
4. **Phase 4: World & Narrative Expansion**
   * Dynamic town simulation (Babylon riverbanks, temple district, artisan quarters, caravan gates).
   * Event system (river floods, locust swarms, debt jubilees, foreign caravan arrivals).
