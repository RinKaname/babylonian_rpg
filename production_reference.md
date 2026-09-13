# Babylonian RPG: Master Production & Time Reference Guide
## Complete Codex of Workshop Recipes, Agricultural Cycles, Military Levies & Time Mechanics

> *Inscribed for the Master Craftsmen, Canal Wardens, and Governors of the City of Babylon. Under the statutory ordinances of King Hammurabi (c. 1750 BC).*

---

## 1. Quick Production Cheat-Sheet

| Production Line | Action / Good Produced | Inputs per Batch | Output Yield per Batch | Base Time | Energy Cost | Primary Skill / Benefit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Brewery** | Barley Beer (*šikaru*) | 5.0 qa Barley | 4 Jars Beer | 3.0h | 8–12% | Craftsmanship / Hydration |
| **Bakery** | Barley Flatbread (*akalu*) | 3.0 qa Barley | 4 Loaves Bread | 2.0h | 8–12% | Craftsmanship / Satiety |
| **Weaver's Loom** | Woolen Cloth (*subātu*) | 4.0 Talents Raw Wool | 2 Bolts Woolen Cloth | 4.0h | 8–12% | Prime Export / Currency |
| **Foundry** | Bronze Tools (*niggallu*) | 2 Copper Ore + 0.2 Tin | 3 Bronze Tools | 5.0h | 8–12% | Chariot input / Trade |
| **Weaponsmith** | Bronze Weapons (*kakku*) | 3 Copper Ore + 0.3 Tin | 2 Bronze Weapons | 5.0h | 8–12% | Arms Rēdû Heavy Spearmen |
| **Bowyer** | Composite Bow (*qaštu*) | 2 Timber + 2 Raw Wool | 1 Composite Bow | 4.5h | 8–12% | Arms Bā'iru Skirmishers |
| **Chariot Guild** | War Chariot (*narkabtu*) | 4 Timber + 1 Bronze Tools | 1 Spoked War Chariot | 8.0h | 8–12% | Arms Narkabtu Charioteers |
| **Brickyard** | Mudbricks (*libittu*) | 2 Marsh Reeds | 5 Sun-Dried Mudbricks | 2.5h | 8–12% | Construction / Export |
| **Lapidary** | Royal Gold Mount Seal | 20.0 Silver Shekels | +4 Seal Prestige | 4.0h | 15% | Unlocks Governor Magistracy |
| **Autumn Farm** | Sowing & Plowing | 10.0 qa Barley / Acre | Fields Sowed | 6.0h | 30% | Agriculture Skill (+1) |
| **Winter Farm** | Canal Silt Dredging | *None* | Canals Cleared | 6.0h | 25% | Agriculture Skill (+1) |
| **Spring Farm** | The Great Harvest | *None* (Harvests fields) | 250–380 qa/Acre (+Oxen) | 8.0h | 45% | Massive Barley Yield |
| **Spring Sheep** | Wool Shearing | *None* (Automatic) | 2.5 Talents Wool / Sheep | Instant | 0% | Raw Wool Inventory |
| **Summer Farm** | Date Palm Foraging | *None* | 5–15 Baskets Dates | 4.0h | 20% | Food & Sugar Supply |
| **Corvée Labor** | Royal Canal Digging | *None* | 5 grains silver $\times$ CPI | 8.0h | 30% | Statutory Wage Earnings |

---

## 2. Artisan Workshop Economics & Time Formulas

Batch manufacturing in Babylon features **economies of scale**: crafting multiple batches at once is significantly faster per unit than crafting single batches one at a time.

### 2.1 The Master Production Time Formula

$$\text{Production Hours} = \text{Base Hours} \times \left( 0.4 + 0.6 \times N^{0.85} \right) \times \text{Facility Multiplier} \times \text{Wage Speed Multiplier}$$

*Where $N$ is the number of batches crafted in a single production run.*

### 2.2 Energy & Fatigue Formula
- **Solo Crafting (0 Hired Artisans):**
  $$\text{Energy Cost} = \max\left(8.0,\; 12.0 \times N^{0.6}\right)$$
- **With Hired Artisans:**
  $$\text{Energy Cost} = \max\left(5.0,\; \frac{15.0 \times N^{0.5}}{1 + \text{Hired Artisans}}\right)$$
  *(Hiring artisans significantly protects your personal stamina!)*

---

### 2.3 Workshop Facility Tiers

To expand batch capacity and unlock speed bonuses, upgrade your workshop in the `[U]` menu:

| Tier | Name | Max Batches / Run | Required Artisans | Upgrade Cost | Speed Multiplier | Description |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **Tier 1** | **Domestic Courtyard** | **3** batches | 0 workers | *Starting Tier* | **1.00x** (Base) | Simple family hearth and clay vats. |
| **Tier 2** | **Guild Workshop** | **8** batches | 1 worker | 35.0 Silver Shekels | **0.85x** (+15% faster) | Dedicated brick kilns, looms, and copper cauldrons. |
| **Tier 3** | **Patrician Manufactory** | **25** batches | 3 workers | 100.0 Silver Shekels | **0.70x** (+30% faster) | Industrial complex with master workstations and vaults. |

> [!WARNING]
> **Understaffing Penalty:** If your workshop is upgraded to Tier 2 or 3 but lacks the required hired artisans, it will drop back to Tier 1 capacity (max 3 batches) and 1.00x speed until adequately staffed.

---

### 2.4 Statutory Wage Policies (Code of Hammurabi §§ 273–274)

Adjustable under workshop option `[W]`:

| Wage Policy | Daily Pay per Worker | Speed Multiplier | Morale & Effect |
| :--- | :--- | :---: | :--- |
| **Stingy** | 3.0 grains silver / day | **1.25x** (-25% slower) | Discontented laborers work sluggishly. Cheap but inefficient. |
| **Statutory (§ 274)** | 5.0 grains silver / day $\times$ CPI | **1.00x** (Standard) | Lawful minimum wage standard under Babylonian law. Dependable. |
| **Efficiency Wage** | 8.0 grains silver / day $\times$ CPI | **0.80x** (+20% faster) | Attracts premier guild journeymen. Production speeds surge! |

*Note: Daily wages are settled at midnight and scale dynamically with the Esagila Consumer Price Index (CPI).*

---

### 2.5 Quick Time Reference Matrix (Hours Required)

#### At Tier 1 (Domestic Courtyard, 1.00x Speed):
| Recipe | Base Time | 1 Batch | 2 Batches | 3 Batches |
| :--- | :---: | :---: | :---: | :---: |
| **Bakery** (Bread) | 2.0h | **2.0h** | **2.9h** | **3.7h** |
| **Brickyard** (Bricks) | 2.5h | **2.5h** | **3.7h** | **4.6h** |
| **Brewery** (Beer) | 3.0h | **3.0h** | **4.4h** | **5.5h** |
| **Loom** (Woolen Cloth) | 4.0h | **4.0h** | **5.9h** | **7.4h** |
| **Bowyer** (Composite Bow) | 4.5h | **4.5h** | **6.6h** | **8.3h** |
| **Foundry** (Tools) | 5.0h | **5.0h** | **7.4h** | **9.2h** |
| **Weaponsmith** (Arms) | 5.0h | **5.0h** | **7.4h** | **9.2h** |
| **Chariot Guild** (War Chariot)| 8.0h | **8.0h** | **11.8h** | **14.8h** |

#### At Tier 2 (Guild Workshop + Efficiency Wage, ~0.68x Combined Speed):
| Recipe | 1 Batch | 3 Batches | 5 Batches | 8 Batches (Max) |
| :--- | :---: | :---: | :---: | :---: |
| **Bakery** (Bread) | **1.4h** | **2.5h** | **3.4h** | **4.7h** |
| **Brewery** (Beer) | **2.0h** | **3.8h** | **5.2h** | **7.1h** |
| **Loom** (Woolen Cloth) | **2.7h** | **5.0h** | **6.9h** | **9.4h** |
| **Weaponsmith** (Arms) | **3.4h** | **6.3h** | **8.6h** | **11.8h** |
| **Chariot Guild** (War Chariot)| **5.4h** | **10.1h** | **13.8h** | **18.9h** |

---

## 3. Agricultural Seasons & Land Yields

The Babylonian agricultural calendar runs on **4 Seasons of 14 Days each** (56 days per year).

```
   AUTUMN (14 Days)      ->       WINTER (14 Days)      ->       SPRING (14 Days)      ->       SUMMER (14 Days)
 Sowing of Seeds & Plowing        Canal Silt Dredging         Great Barley Harvest & Shearing     Date Palm Gathering
```

### 3.1 Seasonal Actions Breakdown

#### Autumn (Months of *Tašrītu* & *Arahsamna*): Plowing & Sowing
- **Requirement:** Arable land title deeds + seed barley.
- **Cost:** **10.0 qa of barley per acre** owned.
- **Time & Vigor:** **6.0 hours**, 30% Energy, 20% Hunger.
- **Reward:** Seeds planted into the fertile canal alluvium; +1 Agriculture skill.

#### Winter (Months of *Kislimu* & *Tebētu*): Irrigation Canal Maintenance
- **Requirement:** None.
- **Time & Vigor:** **6.0 hours**, 25% Energy, 15% Hunger.
- **Reward:** Dredges silt from intake channels and reinforces dikes against winter floods; +1 Agriculture skill.

#### Spring (Months of *Nisannu* & *Ayyāru*): The Great Harvest
- **Time & Vigor:** **8.0 hours**, 45% Energy, 25% Hunger.
- **Barley Harvest Formula:**
  $$\text{Yield per Acre} = \text{Uniform}(250.0, 380.0\text{ qa}) \times \left(1 + \text{Oxen} \times 0.25\right) \times \left(1 + \text{AgriSkill} \times 0.10\right)$$
  $$\text{Total Harvest} = \text{Acres Owned} \times \text{Yield per Acre}$$
- **Draft Ox Multiplier:** Each draft ox owned adds a massive **+25% harvest yield bonus**!
- **Sheep Wool Shearing:** Spring automatically shears **2.5 talents of raw wool** per owned sheep.

#### Summer (Months of *Simānu* & *Dumuzi*): Date Palm Orchards
- **Time & Vigor:** **4.0 hours**, 20% Energy, 25% Thirst.
- **Reward:** Gathers **5.0 to 15.0 baskets of sweet dates** (*suluppu*) from Euphrates orchards.

---

### 3.2 Real Estate & Livestock Economics

| Asset | Purchase Cost | Liquidate / Resell | Direct Economic Benefit |
| :--- | :--- | :--- | :--- |
| **Arable Canal Land** | **20.0 Silver Shekels** / Acre | 15.0 Silver Shekels / Acre | Produces 250–380+ qa grain every Spring; creates sealed legal deed tablet. |
| **Draft Ox (*alpu*)** | **15.0 Silver Shekels** | *Cannot resell* | Boosts entire estate harvest yield by **+25% per ox**. Essential capital investment! |
| **Wool Sheep (*immeru*)** | **2.0 Silver Shekels** | *Cannot resell* | Yields **2.5 talents of raw wool** every Spring (worth ~2.5 silver in market or 1.25 bolts cloth). |

---

## 4. Military Levies, Recruitment & Gate Garrisons

Managed via the Puhrum Civic Assembly under the Mayoral Executive Office (*Rabiānum*).

### 4.1 Unit Specifications & Upkeep

| Unit Type | Akkadian Name | Required Equipment | Recruitment Cost / Soldier | Daily Fodder Grain | Daily Silver Wage | Range Atk | Melee Atk | Defense | Morale |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bā'iru Archers** | *bā'iru* | 1 Composite Bow (*qaštu*) | **2.0 Silver** | 3.0 qa / day | 0.03 Silver | **28.0** | 10.0 | 12.0 | 65 |
| **Rēdû Spearmen** | *rēdû* | 1 Bronze Weapons (*kakku*) | **3.0 Silver** | 4.0 qa / day | 0.04 Silver | 0.0 | **25.0** | **30.0** | 80 |
| **Narkabtu Chariots**| *narkabtu* | 1 War Chariot (*narkabtu*) | **10.0 Silver** | 12.0 qa / day | 0.10 Silver | 18.0 | **42.0** | 22.0 | **85** |
| **Peasant Levies** | *ṣābu* | *None* (Improvised arms) | **0.5 Silver** | 2.0 qa / day | 0.015 Silver | 5.0 | 10.0 | 10.0 | 45 |

### 4.2 Upkeep Source & City Coffers (*Bīt Ālī*)
- **Automated Settlement:** Every day at 00:00 (midnight), total garrison rations and wages are settled.
- **Municipal Funding:** Deducted automatically from the **Babylon Municipal Coffers (*Bīt Ālī*)** and **Public Granary (*É-NÍG-GA*)**.
- **Gate Toll Inflow:** Daily trade caravans entering Babylon generate **+1.80 silver shekels/day** into city coffers.
- **Your Personal Funds:** **Completely safe.** Personal barley/silver are only requested if city granaries are empty, in which case funding grants **+2.0 Honor**.

### 4.3 Gate Stations & Security Rating
Station regiments at Babylon's 4 Great Gates to maintain order and safeguard canals:
1. **Ishtar Gate** (North / Processional Way): Shields against Northern nomads.
2. **Gate of Shamash** (South / Canals & Fields): Protects rural farmers and irrigation canals.
3. **Marduk Gate** (East / Temple Quarter): Guarantees civic temple tranquility.
4. **Urash Gate** (West / Euphrates Quays): Secures river docks, warehouses, and shipping.

---

## 5. Foreign Trade Caravans (*Tamkārum* Expeditions)

Chartered via the Merchant Quarter (*Kārum*) to export Babylonian manufactured goods and import scarce foreign raw materials.

| Trade Corridor | Destination | Round-Trip Duration | Transit Risk | High-Demand Babylonian Exports (High Selling Price) | Foreign Raw Materials Imported (Low Buying Price) |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Anatolia & Levant** | Kanesh & Syrian Coast | **90 Days** (Overland) | 15.0% | Woolen Cloth (2.2x), Dates (1.6x), Sesame Oil (1.5x) | **Tin** (8.0 silv), **Timber** (3.5 silv), Bronze Tools |
| **Dilmun Gateway** | Bahrain (Persian Gulf) | **30 Days** (Maritime) | 5.0% | Barley (1.4x), Woolen Cloth (1.3x), Sesame Oil (1.4x) | Dried Fish (0.20 silv), Dates, Bitumen |
| **Magan Coast** | Oman Copper Coast | **60 Days** (Coastal) | 12.0% | Barley (1.8x), Bread (1.5x), Woolen Cloth (1.5x) | **Raw Copper Ore** (2.20 silv), Mudbricks |
| **Meluhha Indus** | Indus Valley Civilization | **120 Days** (Deep Ocean)| 20.0% | Woolen Cloth (2.8x), Sesame Oil (2.0x), Pottery (1.8x) | **Cylinder Seals** (8.0 silv), Luxury Perfume |

---

## 6. Daily Schedule & Clock Advancements

Babylon operates on an authentic **intraday clock** with dynamic energy depletion:

| Time Interval | Period | Typical Recommended Activities |
| :---: | :---: | :--- |
| **06:00 – 08:00** | Dawn (*Šērtu*) | Eat breakfast flatbread, drink beer, plan daily workshop runs. |
| **08:00 – 12:00** | Morning (*Muslālu*) | High-efficiency workshop production runs (3–4 hours). |
| **12:00 – 14:00** | Midday Heat | Kārum market trading, banking tablet inspection, civic litigation. |
| **14:00 – 18:00** | Afternoon (*Kinūnu*) | Seasonal agricultural field labor or second crafting shift. |
| **18:00 – 21:00** | Evening (*Līlātu*) | City tavern dining, temple offerings, Puhrum assembly meetings. |
| **21:00 – 06:00** | Night (*Mūšu*) | **Sleep in Courtyard / Townhouse:** Restores 100% Energy, advances to 06:00. |

> [!TIP]
> **Stamina Management:** If your energy drops below 20%, crafts and agricultural tasks become blocked. Keep flatbread (`bread`) and beer (`barley_beer`) in your inventory at all times to quench hunger and thirst without having to interrupt your labor!
