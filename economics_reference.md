# Babylonian Era Economics: Comprehensive Simulation Reference
## Architectural Reference for Victoria 3-Style Flow Mechanics in Ancient Mesopotamia

> *Based on cuneiform records, the Code of Hammurabi (c. 1750 BC), the Late Babylonian Astronomical Diaries (c. 464–61 BC), and Polanyi's dual-market historical framework.*

---

## 1. Mathematical Framework: Victoria 3 Dynamic Flow Pricing

The economy does not rely on static inventories to determine prices. Every tick/turn, the market calculates **Buy Orders ($B$)** and **Sell Orders ($S$)** for every good.

### 1.1 Price Determination Formula
The market price deviates from the **Base Price ($P_0$)** proportionally to the supply/demand imbalance, clamped within a $\pm 75\%$ corridor:

$$\text{Price} = P_0 \times \left( 1 + 0.75 \times \frac{B - S}{\max(B, S)} \right)$$

* **Equilibrium ($B = S$):** $\text{Price} = P_0$
* **Maximum Glut ($S \gg B$):** $\text{Price} = 0.25 \times P_0$ ($-75\%$ floor)
* **Maximum Shortage ($B \gg S$):** $\text{Price} = 1.75 \times P_0$ ($+75\%$ ceiling)

### 1.2 The Goods Shortage State
If demand severely outstrips supply ($B > 1.5 \times S$):
* A **Goods Shortage Condition** triggers for that commodity.
* Buildings/workshops consuming that input suffer a **Throughput Debuff** scaling from $-10\%$ up to $-75\%$.
* Pops consuming that good experience an immediate **Standard of Living (SoL) collapse**, accelerating political radicalism, unrest, and potential famine.

---

## 2. Currency & Financial Standards

Babylonia operated on a formal **dual-commodity currency standard**, integrating everyday volumetric rations with precious metal bullion.

### 2.1 The Two Currency Streams
1. **The Silver Standard (`kaspum`):**
   * High-value commercial transactions, international caravan trade, real estate, and fines.
   * Weighed by mass, not minted:
     * **1 Talent (`biltu`)** = 60 Minas (~30.0 kg)
     * **1 Mina (`manû`)** = 60 Shekels (~500 g)
     * **1 Shekel (`šiqlu`)** = 180 Grains of Barley (~8.33 g)
     * **1 Grain (`uţţetu`)** = ~0.046 g of silver
2. **The Barley Standard (`še'u`):**
   * Everyday commoner currency, market street food, tavern tabs, and field wages.
   * Measured by volume:
     * **1 Gur (`kurru`)** = 300 *qa* / *sila* (~250 to 300 Liters)
     * **1 Qa / Sila** = ~0.85 to 1.0 Liter (roughly one adult daily cereal ration)
   * **Legal Baseline Exchange Rate:** Under standard harvests, **1 Shekel of Silver $\approx$ 1 to 2 Gur of Barley** (180 to 300 qa/shekel).

### 2.2 Credit, Debt, and Hammurabi's Statutory Regulations
* **Maximum Interest Rates (Code § 88):**
  * Silver Loans: Capped at **$20.0\%$ per annum** (1/6th shekel per shekel).
  * Grain Loans: Capped at **$33.3\%$ per annum** (100 qa per gur).
  * Penalty for usury: Forfeiture of all principal.
* **Statutory Daily Wages (Code §§ 273–274):**
  * Skilled Artisans (Potters, Carpenters, Tailors, Rope Makers): **5 grains of silver per diem** (~0.028 shekels/day).
  * Agricultural Laborers (Field hands, Herdsmen): **6 to 8 gur of grain per annum** (~6 to 8 silver shekels/year equivalent).
* **The Royal Debt Jubilee (*Misharum*):**
  * Decreed periodically by the King to prevent widespread agrarian debt-slavery.
  * Wipes out all consumer/peasant grain debts and returns ancestral mortgaged land. Commercial loans between *tamkarum* merchants remain exempt.

---

## 3. The 6 Benchmark CPI Commodities
*(As tracked monthly by Babylonian astronomers in the Esagila Temple Astronomical Diaries)*

These six goods form the **core price index** measuring the purchasing power of 1 Shekel of Silver:

| Good | Akkadian Name | Base Value (per 1 Shekel) | Primary Economic Role |
| :--- | :--- | :--- | :--- |
| **Barley** | *še'u* | 1 to 2 *gur* (300–600 *qa*) | Primary caloric intake, animal feed, brewing, base wages. |
| **Dates** | *suluppu* | 1 to 2 *gur* (300–600 *qa*) | High-calorie long-term storage food, sweetener, exports. |
| **Mustard** | *kasû* | 20 to 40 *qa* | High-value urban spice, preservative, medicinal trade. |
| **Cress / Cardamom** | *sahlû* | 20 to 35 *qa* | High-value culinary seasoning, pharmaceutical staple. |
| **Sesame Seeds** | *šamaššammū* | 25 to 50 *qa* | Cooking oil, cosmetic ointment base, lamp fuel. |
| **Wool** | *šīpātu* | 3 to 6 *minas* (~1.5–3.0 kg) | Textile manufacturing, garment exports, standard cloth currency. |

---

## 4. Production Chains & Building Methods (PMs)

### 4.1 Primary Extraction & Agriculture

| Building / Sector | Inputs Required | Labor Profile | Outputs Generated | Historical Context |
| :--- | :--- | :--- | :--- | :--- |
| **Barley Field** | River Water, Seed Grain | 50 Peasants, 2 Foremen | Barley (*še'u*), Straw | Salt-tolerant staple; backbone of the caloric economy. |
| **Emmer & Spelt Field** | Fresh Water (Low Salinity), Seed | 40 Peasants, 5 Landowners | Emmer Wheat, Spelt | Sensitive to soil salt; premium grain for elite bread and beer. |
| **Date Palm Orchard** | Water, Fertile River Alluvium | 20 Farmers, 5 Climbers | Dates, Palm Fronds, Palm Wood | Canopy protects delicate vegetable microclimates below. |
| **Sesame Plot** | Summer Irrigation, Seeds | 25 Farmers | Sesame Seeds | Primary oilseed crop; thrives in Mesopotamian summer heat. |
| **Vegetable & Herb Garden** | Date Canopy Shade, Water | 15 Horticulturalists | Onions, Garlic, Leeks, Cress | Grown in shade under date palms to prevent sun scorch. |
| **Sheep & Goat Pasture** | Steppe Grazing Land, Water | 10 Herdsmen, 2 Shearers | Raw Wool, Goat Hair, Dairy Milk | Maintained at ~14:1 female-to-male breeding ratio. |
| **Cattle & Ox Corrals** | Fodder Grain, Straw, Water | 12 Herdsmen, 1 Vet | Oxen (Draft), Dairy, Hides, Dung | Oxen are critical capital assets; rented under strict legal rates. |
| **Reed Marsh Harvesting** | River Marshes | 15 Gatherers | Marsh Reeds | Inexhaustible river resource; used for mats, baskets, and boats. |
| **Bitumen Seep Pit** | Tools, Transport Wagons | 20 Laborers | Raw Bitumen (Petroleum Pitch) | Extracted from natural oil seeps (e.g. Hit); vital for waterproofing. |

---

### 4.2 Civilian Manufacturing & Processing

| Production Facility | Input Goods | Labor Profile | Refined Outputs | PM Tech Upgrades |
| :--- | :--- | :--- | :--- | :--- |
| **Community Brewery** | Barley, Water, Dates | 8 Brewers (often Women) | Standard Barley Beer (*Sikaru*) | **Spelt Brewing:** Uses Emmer $\to$ Luxury Spelt Beer. |
| **Urban Bakery** | Barley Flour, Water, Sesame Oil | 10 Bakers | Barley Flatbread | **Royal Confectionery:** Adds honey/dates $\to$ Sweet Pastries. |
| **Sesame Oil Press** | Sesame Seeds | 12 Pressers | Sesame Oil, Seed Cake (Fodder) | **Lever Pressing:** Increases oil yield per bushel by $+30\%$. |
| **Wool Textile Guild** | Raw Wool, Dyes (Madder/Kermes) | 50 Weavers, 10 Carders | Finished Woolen Cloth, Dyed Garments | **Varicolored Dyeing:** Uses imported murex purple for elites. |
| **Flax Weaving Workshop** | Flax Fibers | 25 Weavers | Fine Linen Tunics, Temple Vestments | Luxury alternative to wool; prized for breathability. |
| **Pottery Kiln** | Clay, Water, Dried Dung (Fuel) | 15 Potters (5 gr. silver/day) | Storage Jars, Bowls, Clay Tablets | **Fast Wheel:** Mass-produces standardized ration bowls. |
| **Glass & Faience Workshop** | Quartz Sand, Plant Ash, Metallic Oxides | 8 Master Alchemists | Cobalt Faience, Core-formed Glass | Secret chemical recipes; simulates precious gemstones. |
| **Brickyard** | River Mud, Straw, Bitumen | 35 Laborers | Sun-dried Bricks, Kiln-baked Bricks | Kiln-baked with bitumen mortar withstands annual floods. |
| **Carpentry Guild** | Imported Timber (Cedar/Pine), Bronze Tools | 12 Master Carpenters | Ard Plows, Wagons, Riverboats | Essential capital equipment for agriculture and transport. |
| **Perfume & Unguents Lab** | Sesame Oil, Myrrh, Frankincense | 5 Perfumers | Perfumes, Sacred Temple Anointing Oils | Consumed in gallons for elite grooming and temple statues. |
| **Glyptic Art Studio** | Semi-Precious Stone, Copper Drills | 4 Master Gem-cutters | Carved Cylinder Seals, Amulets | Mandatory for legal contract authentication and status. |

---

### 4.3 Military & Armament Sector

| Armament Good | Component Inputs Required | Manufacturing Time | Strategic Function |
| :--- | :--- | :--- | :--- |
| **Composite Bow** | Flexible Wood Core, Animal Horn, Sinew, Animal Glue | 6 to 12 Months (Curing) | Elite high-velocity armor-piercing ranged weapon. |
| **Bronze Melee Weapons** | Copper Ore (Magan), Tin (Anatolia), Wood | Fast (Foundry Cast) | Standard infantry weapons (spears, piercing battle-axes). |
| **Scale Body Armor** | Leather / Linen Tunic, Bronze or Iron Scales | High Labor | Heavy protection for elite chariot archers and shock infantry. |
| **Infantry Tower Shield** | Densely Woven Reeds, Thick Leather, Bronze Boss | Moderate | Mobile siege protection for archer-shieldbearer pairs. |
| **War Chariot** | Hardwood (Ash/Elm), Leather Harness, Bronze Axles | Very High (Multi-Guild) | Fast mobile missile platform; ancient main battle weapon. |
| **Equine War Mount** | Fodder Grain, Pasture, Leather Saddles | 3 Years (Breeding/Training) | Chariot draft teams and shock cavalry. |

---

## 5. Pop Consumption Baskets & Standard of Living (SoL)

Pops allocate their personal income to fulfill **Category Needs**. If a specific good is expensive, they substitute with another good in the same category.

```
                      POP STANDARD OF LIVING (SoL)
  ┌─────────────────────────┬─────────────────────────┬─────────────────────────┐
  │   SUBSISTENCE (1–5)     │     MIDDLE (6–12)       │     PATRICIAN (13+)     │
  │    (Wardum / Debtors)   │   (Mushkenum / Artisans)│   (Awilum / Merchants)  │
  ├─────────────────────────┼─────────────────────────┼─────────────────────────┤
  │ • Basic Barley Bread    │ • Leavened Bread        │ • Sweet Date Pastries   │
  │ • Dried River Fish      │ • Barley Beer (Sikaru)  │ • Spelt Beer & Wine     │
  │ • Raw Onions & Garlic   │ • Dates & Vegetables    │ • Choice Mutton & Beef  │
  │ • Rough Wool Tunic      │ • Sesame Lamp Oil       │ • Fine Bleached Linen   │
  │ • Reed Sleeping Mat     │ • Dyed Woolen Cloak     │ • Perfumes & Anointing  │
  │ • Simple Clay Bowl      │ • Quality Pottery       │ • Glassware & Faience   │
  │                         │ • Bronze Utensils       │ • Lapis Cylinder Seal   │
  └─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

### 5.1 Goods Substitution Categories
* **Basic Nutrition:** Barley Bread $\leftrightarrow$ Dried Fish $\leftrightarrow$ Lentils/Beans.
* **Hydration & Intoxication:** Standard Barley Beer $\leftrightarrow$ Date Wine $\leftrightarrow$ Well Water (Risk of Disease!).
* **Sweeteners:** Dried Dates $\leftrightarrow$ Date Syrup (*Dibs*) $\leftrightarrow$ Raw Honey.
* **Lighting & Unguents:** Plain Sesame Oil $\leftrightarrow$ Rendered Animal Tallow.
* **Luxury Apparel:** Woolen Fabric $\leftrightarrow$ Egyptian Linen $\leftrightarrow$ Tyrian Purple Garments.

---

## 6. International Trade Corridors (*The Tamkarum Routes*)

Babylonia has zero domestic timber, workable stone, or copper/tin ores. Long-distance trade is an absolute physiological necessity for Bronze Age civilization.

```
                                      [ANATOLIA & LEVANT]
                                     Silver, Tin, Cedar, Dyes
                                                ▲
                                                │ (Donkey Caravans)
                                                ▼
     [MESOPOTAMIAN CORE: BABYLON, SIPPAR, NIPPUR, UR]
     Exports: Woolen Garments, Barley, Sesame Oil, Dates
                        │
                        ▼ (Euphrates & Persian Gulf Barges)
                  [DILMUN / BAHRAIN]  <── Middleman Entrepôt
                   /              \
                  ▼                ▼
          [MAGAN / OMAN]     [MELUHHA / INDUS VALLEY]
       Raw Copper Ore, Diorite  Carnelian, Lapis Lazuli, Ivory
```

### 6.1 Trade Corridor Breakdown

| Corridor | Primary Transport | Babylonian Exports | Foreign Strategic Imports | Economic Implication |
| :--- | :--- | :--- | :--- | :--- |
| **Northern Overland (Anatolia & Levant)** | Donkey Caravans (up to 300 donkeys) | High-value Woolen Garments, Finished Textiles, Dates | **Silver**, **Gold**, **Tin** (for bronze), **Cedar Timber**, Murex Purple | Essential for metallurgy and high construction. Funded by palace/merchant credit. |
| **Dilmun Entrepôt (Bahrain)** | Coastal River Barges & Coracles | Grain, Sesame Oil, Coarse Textiles | Safe harbor exchange node; pearls, intermediate goods | The trading hub where eastern and western goods swap hands. |
| **Magan Coast (Oman / UAE)** | Persian Gulf Seagoing Vessels | Barley, Woolen Cloth | **Raw Copper Ore**, **Diorite Stone** | The sole supplier of copper for Babylonian bronze foundries and hard stone for statues. |
| **Meluhha Node (Indus Valley)** | Deep-sea Maritime Barges | Textiles, Refined Oils, Silver | **Carnelian**, **Lapis Lazuli**, **Ivory**, Exotic Hardwoods | High-end luxury trade; sustained a permanent Meluhhan expatriate quarter in southern Sumer. |
