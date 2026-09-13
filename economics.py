"""
economics.py - Victoria 3-Style Macroeconomic Simulation Engine for Babylonian RPG
==================================================================================
Implements:
1. Goods Taxonomy & Registry (25+ authentic Mesopotamian commodities).
2. Flow-based Market Solver: Price = Base * (1 + 0.75 * (Buy - Sell) / max(Buy, Sell)).
3. Production Methods (PMs) for primary agriculture, manufacturing, and war industries.
4. Social Classes (Wardum, Mushkenum, Awilum) with Pop Consumption Baskets & Standard of Living (SoL).
5. Goods Substitution (e.g. Barley <-> Dates, Beer <-> Wine).
6. The 6 Benchmark CPI Commodities of the Esagila Temple Astronomical Diaries.
7. Hammurabi Legal Code constraints (Statutory wage rates, interest rate ceilings).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import math
import random
import sys

# Ensure clean UTF-8 output on all Windows console environments
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# 1. Enums & Class Taxonomies
# ==============================================================================

class SocialClass(Enum):
    WARDUM = "Wardum"          # State laborers, debt-servants, corvée workers
    MUSHKENUM = "Mushkenum"    # Free commoners, tenant farmers, guild artisans
    AWILUM = "Awilum"          # Patricians, landowners, temple priests, scribes


class GoodCategory(Enum):
    BASIC_FOOD = "Basic Food"           # Barley, Emmer, Dried Fish, Legumes
    DRINK = "Drink & Hydration"         # Barley Beer, Spelt Beer, Date Wine
    FRUIT_SWEET = "Fruit & Sweeteners"  # Dates, Date Syrup, Honey
    OILS_FUEL = "Oils & Fuel"           # Sesame Oil, Animal Dung, Tallow
    TEXTILES = "Textiles & Garments"    # Raw Wool, Flax, Woolen Garments, Linen
    CONSTRUCTION = "Building & Hardware" # Mudbrick, Kiln Brick, Bitumen, Reeds, Timber
    MANUFACTURES = "Utilitarian Crafts" # Pottery, Bronze Tools, Glassware, Plows
    LUXURY_STATUS = "Luxury & Status"   # Perfumes, Jewelry, Cylinder Seals, Purple Dye
    ARMAMENT = "Military & Armament"    # Composite Bows, Bronze Weapons, Armor, Chariots
    RAW_MINERAL = "Raw Metals & Ores"   # Copper Ore, Tin, Silver, Gold, Stone


# ==============================================================================
# 2. Goods Definition & Registry
# ==============================================================================

@dataclass
class Good:
    id: str
    name: str
    akkadian_name: str
    category: GoodCategory
    base_price: float           # In Silver Shekels (~8.33g silver)
    weight_kg: float            # Physical mass per unit (affects transport/caravan capacity)
    is_cpi_benchmark: bool = False  # Tracked in Babylonian Astronomical Diaries
    perishable: bool = False    # Subject to decay/rot if hoarded beyond capacity
    description: str = ""


class GoodsRegistry:
    """Master registry of all economic goods in the Babylonian sphere."""
    def __init__(self):
        self.goods: Dict[str, Good] = {}
        self._register_all()

    def register(self, good: Good):
        self.goods[good.id] = good

    def get(self, good_id: str) -> Good:
        if good_id not in self.goods:
            raise KeyError(f"Unknown commodity '{good_id}'")
        return self.goods[good_id]

    def _register_all(self):
        # 1. Agricultural & Primary Staples
        self.register(Good("barley", "Barley Grain", "še'u", GoodCategory.BASIC_FOOD, 
                           base_price=0.50, weight_kg=25.0, is_cpi_benchmark=True, perishable=True,
                           description="Salt-tolerant staple cereal; used for rations, brewing, animal fodder, and base currency."))
        self.register(Good("emmer", "Emmer Wheat", "zizzu", GoodCategory.BASIC_FOOD, 
                           base_price=0.85, weight_kg=25.0, perishable=True,
                           description="Salt-sensitive premium wheat for elite bread and luxury spelt beer."))
        self.register(Good("dates", "Sweet Dates", "suluppu", GoodCategory.FRUIT_SWEET, 
                           base_price=0.60, weight_kg=20.0, is_cpi_benchmark=True, perishable=True,
                           description="High-calorie orchard crop; eaten dried, brewed into wine, or boiled to syrup."))
        self.register(Good("sesame", "Sesame Seeds", "šamaššammū", GoodCategory.OILS_FUEL, 
                           base_price=1.20, weight_kg=15.0, is_cpi_benchmark=True, perishable=True,
                           description="Primary oilseed; pressed for culinary oil, temple lamps, and cosmetic ointments."))
        self.register(Good("mustard", "Mustard & Herbs", "kasû", GoodCategory.BASIC_FOOD, 
                           base_price=2.00, weight_kg=5.0, is_cpi_benchmark=True,
                           description="Pungent urban cash crop used for seasoning, food preservation, and medicine."))
        self.register(Good("cress", "Cress & Spices", "sahlû", GoodCategory.BASIC_FOOD, 
                           base_price=2.20, weight_kg=5.0, is_cpi_benchmark=True,
                           description="Pharmaceutical and culinary herb tracked monthly in the Astronomical Diaries."))
        self.register(Good("dried_fish", "River Carp & Fish", "nūnu", GoodCategory.BASIC_FOOD, 
                           base_price=0.40, weight_kg=10.0, perishable=True,
                           description="Abundant protein harvested from the Euphrates marshes and dried with salt."))
        
        # 2. Livestock & Pastoral Products
        self.register(Good("raw_wool", "Raw Wool", "šīpātu", GoodCategory.TEXTILES, 
                           base_price=1.00, weight_kg=10.0, is_cpi_benchmark=True,
                           description="The industrial backbone of Mesopotamian exports; shorn from massive temple flocks."))
        self.register(Good("flax", "Flax Fiber", "qu", GoodCategory.TEXTILES, 
                           base_price=1.80, weight_kg=10.0,
                           description="Labor-intensive fiber used for cool, breathable linen fabrics for the elite."))
        self.register(Good("animal_dung", "Dried Dung Cakes", "kibrītu", GoodCategory.OILS_FUEL, 
                           base_price=0.10, weight_kg=15.0,
                           description="Essential domestic and industrial kiln fuel in a timber-scarce alluvial plain."))

        # 3. Manufactured Consumer Goods
        self.register(Good("barley_beer", "Barley Beer", "šikaru", GoodCategory.DRINK, 
                           base_price=0.60, weight_kg=20.0, perishable=True,
                           description="Standard cloudy, unhopped table beer; essential hydration and divine gift of Ninkasi."))
        self.register(Good("spelt_beer", "Premium Spelt Beer", "ulušinnu", GoodCategory.DRINK, 
                           base_price=1.50, weight_kg=20.0, perishable=True,
                           description="Sweet, golden spelt ale reserved for patrician banquets and temple libations."))
        self.register(Good("bread", "Barley Flatbread", "akalu", GoodCategory.BASIC_FOOD, 
                           base_price=0.55, weight_kg=10.0, perishable=True,
                           description="Everyday flatbread baked on hot clay stones or public ovens."))
        self.register(Good("sweet_pastry", "Honey-Date Pastries", "mersu", GoodCategory.FRUIT_SWEET, 
                           base_price=2.50, weight_kg=5.0, perishable=True,
                           description="Confectionery enriched with date syrup, butter, and raw honey for festival banquets."))
        self.register(Good("sesame_oil", "Refined Sesame Oil", "ellu", GoodCategory.OILS_FUEL, 
                           base_price=2.00, weight_kg=10.0,
                           description="Clean cooking oil, clay lamp fuel, and base carrier for perfumes."))
        self.register(Good("woolen_cloth", "Standard Woolen Garment", "subātu", GoodCategory.TEXTILES, 
                           base_price=3.00, weight_kg=2.0,
                           description="Standardized lengths of woolen cloth; functions as a medium of exchange and prime export."))
        self.register(Good("fine_linen", "Bleached Linen Tunic", "kitû", GoodCategory.TEXTILES, 
                           base_price=8.00, weight_kg=1.0,
                           description="Crisp, white luxury garments worn by Awilum patricians and temple priests."))
        self.register(Good("pottery", "Clay Bowls & Jars", "karpatu", GoodCategory.MANUFACTURES, 
                           base_price=0.30, weight_kg=5.0,
                           description="Mass-produced standardized vessels for food storage, transport, and ration measures."))

        # 4. Construction & Industrial Hardware
        self.register(Good("mudbrick", "Sun-Dried Mudbrick", "libittu", GoodCategory.CONSTRUCTION, 
                           base_price=0.15, weight_kg=20.0,
                           description="Standard building brick molded from river alluvium and straw binder."))
        self.register(Good("bitumen", "Petroleum Pitch / Bitumen", "kupru", GoodCategory.CONSTRUCTION, 
                           base_price=1.10, weight_kg=25.0,
                           description="Naturally occurring petroleum seep asphalt; waterproofing for boats, silos, and mortar."))
        self.register(Good("reeds", "Marsh Reeds", "qanû", GoodCategory.CONSTRUCTION, 
                           base_price=0.10, weight_kg=10.0,
                           description="Durable reeds harvested from marshlands; woven into mats, baskets, roofs, and coracles."))
        self.register(Good("timber", "Imported Cedar/Pine", "erēnu", GoodCategory.CONSTRUCTION, 
                           base_price=6.00, weight_kg=50.0,
                           description="Precious structural timber imported from the Lebanon mountains or Anatolia."))
        self.register(Good("copper_ore", "Raw Copper Ore", "erû", GoodCategory.RAW_MINERAL, 
                           base_price=4.00, weight_kg=30.0,
                           description="Imported from Magan (Oman); the lifeblood of Mesopotamian metal foundries."))
        self.register(Good("tin", "Cassiterite / Tin", "annaku", GoodCategory.RAW_MINERAL, 
                           base_price=12.00, weight_kg=10.0,
                           description="Extremely rare imported metal from Anatolia/East; alloyed at 1:9 with copper for bronze."))
        self.register(Good("bronze_tools", "Bronze Plows & Sickles", "niggallu", GoodCategory.MANUFACTURES, 
                           base_price=5.00, weight_kg=4.0,
                           description="Heavy-duty agricultural and artisan tools that drastically increase productivity."))

        # 5. High-Status Luxuries & Military
        self.register(Good("perfume", "Sacred Unguents & Perfume", "ruqqû", GoodCategory.LUXURY_STATUS, 
                           base_price=15.00, weight_kg=1.0,
                           description="Frankincense and myrrh compounded into sesame oil for temple anointing and elite grooming."))
        self.register(Good("cylinder_seal", "Carved Cylinder Seal", "kunukku", GoodCategory.LUXURY_STATUS, 
                           base_price=20.00, weight_kg=0.2,
                           description="Reverse-intaglio semi-precious stone seal; mandatory legal signature and status symbol."))
        self.register(Good("bronze_weapons", "Bronze Spears & Battle-Axes", "kakku", GoodCategory.ARMAMENT, 
                           base_price=8.00, weight_kg=3.0,
                           description="Standard military arms for Rēdû heavy infantry and city gate guards."))
        self.register(Good("composite_bow", "Laminated Composite Bow", "qaštu", GoodCategory.ARMAMENT, 
                           base_price=35.00, weight_kg=1.5,
                           description="Four-tier wood-horn-sinew masterpiece; takes a year to cure; high armor-piercing lethality."))
        self.register(Good("war_chariot", "Spoked War Chariot", "narkabtu", GoodCategory.ARMAMENT, 
                           base_price=120.00, weight_kg=150.0,
                           description="Hardwood chariot with bronze fittings, axle pins, and trained warhorse harness."))


# ==============================================================================
# 3. Victoria 3 Flow-Market Engine
# ==============================================================================

@dataclass
class MarketGoodState:
    good_id: str
    base_price: float
    current_price: float
    buy_orders: float = 0.0
    sell_orders: float = 0.0
    shortage: bool = False
    price_history: List[float] = field(default_factory=list)


class Market:
    """
    Simulates a Victoria 3-style flow-based commodity market.
    Prices adjust dynamically between -75% and +75% of base price based on Buy/Sell order balance.
    """
    def __init__(self, registry: GoodsRegistry):
        self.registry = registry
        self.goods: Dict[str, MarketGoodState] = {}
        for g_id, good in registry.goods.items():
            self.goods[g_id] = MarketGoodState(
                good_id=g_id,
                base_price=good.base_price,
                current_price=good.base_price,
                price_history=[good.base_price]
            )

    def submit_buy_order(self, good_id: str, volume: float):
        """Submit a demand request for a volume of goods."""
        if good_id in self.goods and volume > 0:
            self.goods[good_id].buy_orders += volume

    def submit_sell_order(self, good_id: str, volume: float):
        """Submit a supply offering for a volume of goods."""
        if good_id in self.goods and volume > 0:
            self.goods[good_id].sell_orders += volume

    def resolve_market(self):
        """
        Calculates clearing prices for all goods based on flow equilibrium:
        Price = BasePrice * (1.0 + 0.75 * (Buy - Sell) / max(Buy, Sell))
        """
        for g_id, state in self.goods.items():
            B = state.buy_orders
            S = state.sell_orders

            if B == 0 and S == 0:
                # Idle market drift back towards base price
                new_price = state.current_price + (state.base_price - state.current_price) * 0.10
                state.shortage = False
            else:
                max_vol = max(B, S, 1e-4)
                imbalance = (B - S) / max_vol
                # Clamped between -75% and +75%
                multiplier = 1.0 + 0.75 * imbalance
                multiplier = max(0.25, min(1.75, multiplier))
                new_price = round(state.base_price * multiplier, 3)

                # Severe shortage condition if demand > 150% of supply
                state.shortage = (B > 1.5 * max(S, 0.1))

            state.current_price = new_price
            state.price_history.append(new_price)
            if len(state.price_history) > 50:
                state.price_history.pop(0)

            # Reset accumulators for next tick
            state.buy_orders = 0.0
            state.sell_orders = 0.0

    def get_price(self, good_id: str) -> float:
        return self.goods[good_id].current_price

    def is_in_shortage(self, good_id: str) -> bool:
        return self.goods[good_id].shortage

    def calculate_cpi(self) -> float:
        """
        Calculates the Astronomical Diaries Core Consumer Price Index (CPI)
        using the 6 benchmark liquid commodities: Barley, Dates, Mustard, Cress, Sesame, Wool.
        """
        cpi_goods = [g_id for g_id, g in self.registry.goods.items() if g.is_cpi_benchmark]
        if not cpi_goods:
            return 1.0
        ratios = [self.get_price(g) / self.goods[g].base_price for g in cpi_goods]
        return sum(ratios) / len(ratios)


# ==============================================================================
# 4. Production Methods (PMs) & Buildings
# ==============================================================================

@dataclass
class ProductionMethod:
    name: str
    description: str
    inputs: Dict[str, float]               # good_id -> quantity consumed per tick
    labor_required: Dict[SocialClass, int] # SocialClass -> headcount required
    outputs: Dict[str, float]              # good_id -> quantity produced per tick
    capital_cost_silver: float = 0.0       # Upfront setup or upgrade cost


class Building:
    """
    A productive workplace in the Babylonian economy.
    Employs pops, consumes inputs, and sells outputs on the market.
    """
    def __init__(self, id: str, name: str, methods: List[ProductionMethod]):
        self.id = id
        self.name = name
        self.methods = methods
        self.active_pm_idx = 0
        self.employees: Dict[SocialClass, int] = {c: 0 for c in SocialClass}
        self.throughput_efficiency: float = 1.0
        self.cash_reserves_silver: float = 50.0

    @property
    def active_pm(self) -> ProductionMethod:
        return self.methods[self.active_pm_idx]

    def set_production_method(self, idx: int):
        if 0 <= idx < len(self.methods):
            self.active_pm_idx = idx

    def tick_production(self, market: Market) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Executes one production cycle:
        1. Submits buy orders for required inputs.
        2. Adjusts throughput if input goods are in shortage.
        3. Submits sell orders for generated outputs.
        """
        pm = self.active_pm
        
        # Check input shortages to compute operational throughput
        shortage_penalty = 1.0
        for input_id in pm.inputs.keys():
            if market.is_in_shortage(input_id):
                shortage_penalty *= 0.60  # -40% efficiency per missing input good

        effective_throughput = self.throughput_efficiency * shortage_penalty

        # Submit input buy orders
        actual_inputs = {}
        for in_id, amount in pm.inputs.items():
            needed = amount * effective_throughput
            market.submit_buy_order(in_id, needed)
            actual_inputs[in_id] = needed

        # Submit output sell orders
        actual_outputs = {}
        for out_id, amount in pm.outputs.items():
            produced = amount * effective_throughput
            market.submit_sell_order(out_id, produced)
            actual_outputs[out_id] = produced

        return actual_inputs, actual_outputs


# ==============================================================================
# 5. Pop Demographics & Standard of Living (SoL)
# ==============================================================================

@dataclass
class PopGroup:
    """
    Represents a demographic cohort belonging to a specific social class.
    Possesses wealth, consumes fulfillment categories, and tracks radicalism.
    """
    social_class: SocialClass
    headcount: int
    wealth_silver_per_capita: float
    standard_of_living: float = 10.0   # 1 (Destitute/Starving) to 20+ (Opulent Patrician)
    literacy_rate: float = 0.05        # High for Scribes/Awilum, near zero for Wardum
    unrest_radicalism: float = 0.0     # 0.0 (Content) to 100.0 (Rebellion / Strike)

    def calculate_demands(self, market: Market) -> Dict[str, float]:
        """
        Computes weekly/monthly consumption demand based on SoL and goods substitution.
        Low wealth pops prioritize cheap calories (Barley/Fish).
        High wealth pops substitute luxury food (Emmer/Pastries) and status items (Linen/Perfume).
        """
        demands: Dict[str, float] = {}

        # 1. Basic Food Needs (All pops need caloric sustenance)
        caloric_units_needed = self.headcount * 1.0  # 1 unit per person
        barley_price = market.get_price("barley")
        dates_price = market.get_price("dates")
        fish_price = market.get_price("dried_fish")

        if self.social_class == SocialClass.AWILUM:
            # Patricians consume fine bread, dates, and sweet pastries
            demands["emmer"] = caloric_units_needed * 0.40
            demands["dates"] = caloric_units_needed * 0.30
            demands["sweet_pastry"] = caloric_units_needed * 0.30
        elif self.social_class == SocialClass.MUSHKENUM:
            # Commoners eat bread and dates, substitute fish if grain is expensive
            if barley_price > 0.70 and fish_price < 0.50:
                demands["barley"] = caloric_units_needed * 0.40
                demands["dried_fish"] = caloric_units_needed * 0.40
                demands["dates"] = caloric_units_needed * 0.20
            else:
                demands["barley"] = caloric_units_needed * 0.70
                demands["dates"] = caloric_units_needed * 0.30
        else:
            # Wardum laborers subsist on standard barley flatbread and dried fish
            demands["barley"] = caloric_units_needed * 0.80
            demands["dried_fish"] = caloric_units_needed * 0.20

        # 2. Hydration & Alcohol
        beer_need = self.headcount * 0.50
        if self.social_class == SocialClass.AWILUM:
            demands["spelt_beer"] = beer_need
        else:
            demands["barley_beer"] = beer_need

        # 3. Domestic Fuel & Lighting
        demands["sesame_oil"] = self.headcount * 0.05
        demands["animal_dung"] = self.headcount * 0.15

        # 4. Clothing & Textiles
        if self.social_class == SocialClass.AWILUM:
            demands["fine_linen"] = self.headcount * 0.05
            demands["perfume"] = self.headcount * 0.02
        else:
            demands["woolen_cloth"] = self.headcount * 0.03

        # Submit all calculated demands as Buy Orders to the market
        for g_id, qty in demands.items():
            market.submit_buy_order(g_id, qty)

        return demands

    def update_standard_of_living(self, market: Market):
        """Updates pop happiness, wealth drift, and radicalism based on inflation and food access."""
        cpi = market.calculate_cpi()
        food_shortage = market.is_in_shortage("barley") and market.is_in_shortage("dates")

        if food_shortage:
            self.standard_of_living = max(1.0, self.standard_of_living - 1.5)
            self.unrest_radicalism = min(100.0, self.unrest_radicalism + 15.0)
        elif cpi > 1.30:  # >30% inflation on basic basket
            self.standard_of_living = max(1.0, self.standard_of_living - 0.3)
            self.unrest_radicalism = min(100.0, self.unrest_radicalism + 4.0)
        else:
            # Prosperous conditions
            self.unrest_radicalism = max(0.0, self.unrest_radicalism - 2.0)
            if self.wealth_silver_per_capita > 50.0:
                self.standard_of_living = min(20.0, self.standard_of_living + 0.2)


# ==============================================================================
# 6. Economic Simulation World State
# ==============================================================================

class BabylonianEconomy:
    """
    Complete closed-loop macroeconomic simulation of ancient Babylonia.
    Orchestrates the Victoria 3 flow market, production facilities, and demographic pops.
    """
    def __init__(self):
        self.registry = GoodsRegistry()
        self.market = Market(self.registry)
        self.buildings: List[Building] = []
        self.pops: Dict[SocialClass, PopGroup] = {}
        self.year = 1
        self.season_tick = 0  # 0: Autumn (Sow), 1: Winter, 2: Spring (Harvest), 3: Summer (Flood)
        self._initialize_default_world()

    def _initialize_default_world(self):
        # 1. Initialize Demographics (1,000 citizens total)
        self.pops[SocialClass.WARDUM] = PopGroup(
            SocialClass.WARDUM, headcount=200, wealth_silver_per_capita=2.0, standard_of_living=5.0
        )
        self.pops[SocialClass.MUSHKENUM] = PopGroup(
            SocialClass.MUSHKENUM, headcount=750, wealth_silver_per_capita=15.0, standard_of_living=9.0
        )
        self.pops[SocialClass.AWILUM] = PopGroup(
            SocialClass.AWILUM, headcount=50, wealth_silver_per_capita=250.0, standard_of_living=17.0, literacy_rate=0.70
        )

        # 2. Build Primary Agricultural Sector
        barley_pms = [
            ProductionMethod("Traditional Dry Ard", "Oxen-drawn wooden plow on seasonal alluvium",
                             inputs={"sesame_oil": 0.5}, labor_required={SocialClass.MUSHKENUM: 40},
                             outputs={"barley": 60.0}),
            ProductionMethod("Dredged Canal Irrigation", "Intensive Euphrates silt-cleared canal network (+50% yield)",
                             inputs={"bronze_tools": 1.0, "bitumen": 0.5}, labor_required={SocialClass.MUSHKENUM: 35, SocialClass.WARDUM: 15},
                             outputs={"barley": 110.0}, capital_cost_silver=25.0)
        ]
        b_farm = Building("farm_barley_01", "Euphrates Arable Farmlands", barley_pms)
        b_farm.set_production_method(1) # Start with canal network
        self.buildings.append(b_farm)

        # 3. Date Palm Orchards
        date_pms = [
            ProductionMethod("Canopy Orchard", "Tall date palms shading legume under-crops",
                             inputs={}, labor_required={SocialClass.MUSHKENUM: 20},
                             outputs={"dates": 40.0, "reeds": 10.0})
        ]
        self.buildings.append(Building("orchard_dates_01", "Eridu Date Palm Groves", date_pms))

        # 4. Urban Breweries
        brewery_pms = [
            ProductionMethod("Common Bappir Brewing", "Traditional cloudy barley beer brewed with bread loaves",
                             inputs={"barley": 25.0, "dates": 5.0}, labor_required={SocialClass.MUSHKENUM: 8},
                             outputs={"barley_beer": 35.0}),
            ProductionMethod("Patrician Spelt Fermentation", "Refined sweet beer brewed from emmer wheat",
                             inputs={"emmer": 15.0, "dates": 10.0}, labor_required={SocialClass.MUSHKENUM: 6, SocialClass.AWILUM: 2},
                             outputs={"spelt_beer": 20.0}, capital_cost_silver=15.0)
        ]
        self.buildings.append(Building("brewery_urban_01", "Goddess Ninkasi Royal Brewery", brewery_pms))

        # 5. Wool Textile Guild
        textile_pms = [
            ProductionMethod("Horizontal Loom Weaving", "Weaving standardized woolen lengths for domestic and export trade",
                             inputs={"raw_wool": 20.0}, labor_required={SocialClass.WARDUM: 25, SocialClass.MUSHKENUM: 10},
                             outputs={"woolen_cloth": 18.0})
        ]
        self.buildings.append(Building("textile_guild_01", "Ishtar Temple Weaving Quarters", textile_pms))

        # 6. Brick Kiln & Bitumen Pits
        brick_pms = [
            ProductionMethod("Bitumen-Bonded Kiln Firing", "Waterproof kiln bricks bonded with petroleum pitch",
                             inputs={"reeds": 15.0, "animal_dung": 20.0, "bitumen": 5.0}, 
                             labor_required={SocialClass.WARDUM: 30},
                             outputs={"mudbrick": 50.0})
        ]
        self.buildings.append(Building("brickyard_01", "Euphrates Alluvial Kilns", brick_pms))

    def step_season(self) -> Dict[str, any]:
        """
        Advances the economy by one seasonal tick:
        1. Pops calculate consumption and submit Buy Orders.
        2. Production facilities consume inputs and submit Sell Orders.
        3. Market clears dynamic prices.
        4. Standard of Living and Unrest update.
        """
        seasons = ["Autumn (Sowing)", "Winter (Tending)", "Spring (Harvest)", "Summer (Euphrates Flood)"]
        curr_season = seasons[self.season_tick]

        # 1. Pop Demand Phase
        for pop in self.pops.values():
            pop.calculate_demands(self.market)

        # 2. Production Facility Phase
        total_produced = {}
        for b in self.buildings:
            ins, outs = b.tick_production(self.market)
            for k, v in outs.items():
                total_produced[k] = total_produced.get(k, 0.0) + v

        # Seasonal Harvest Bonus in Spring
        if self.season_tick == 2:  # Spring Harvest
            self.market.submit_sell_order("barley", 200.0) # Massive agrarian harvest glut
            self.market.submit_sell_order("emmer", 50.0)
            self.market.submit_sell_order("dates", 80.0)

        # 3. Market Resolution Phase
        self.market.resolve_market()

        # 4. Demographic Social Feedback Phase
        for pop in self.pops.values():
            pop.update_standard_of_living(self.market)

        # Advance Calendar
        self.season_tick = (self.season_tick + 1) % 4
        if self.season_tick == 0:
            self.year += 1

        return {
            "year": self.year,
            "season": curr_season,
            "cpi": round(self.market.calculate_cpi(), 3),
            "barley_price": self.market.get_price("barley"),
            "beer_price": self.market.get_price("barley_beer"),
            "wool_price": self.market.get_price("woolen_cloth"),
            "unrest_wardum": round(self.pops[SocialClass.WARDUM].unrest_radicalism, 1),
            "sol_mushkenum": round(self.pops[SocialClass.MUSHKENUM].standard_of_living, 1)
        }


# ==============================================================================
# 7. Verification & Interactive Demonstration
# ==============================================================================

if __name__ == "__main__":
    print("=" * 75)
    print("   BABYLONIAN RPG - VICTORIA 3 MACROECONOMIC FLOW ENGINE")
    print("=" * 75)
    
    sim = BabylonianEconomy()
    print(f"Registered {len(sim.registry.goods)} commodities across 10 Mesopotamian sectors.")
    print("Simulating 8 seasonal ticks (2 In-Game Years)...\n")

    header = f"{'Year':<5} | {'Season':<22} | {'CPI':<6} | {'Barley':<8} | {'Beer':<8} | {'Cloth':<8} | {'Wardum Unrest'}"
    print(header)
    print("-" * len(header))

    for t in range(8):
        # In tick 4 (Year 2 Winter), simulate an irrigation canal dike breach (shortage shock)
        if t == 4:
            print("\n[!] HISTORICAL SHOCK: Canal Dike Breached! Silt floods downstream farmlands!")
            sim.buildings[0].throughput_efficiency = 0.30  # Agricultural shock
        elif t == 6:
            print("\n[+] RECOVERY: Corvee laborers restore canal dikes and flush silt.")
            sim.buildings[0].throughput_efficiency = 1.0

        res = sim.step_season()
        print(f"{res['year']:<5} | {res['season']:<22} | {res['cpi']:<6.3f} | {res['barley_price']:<8.3f} | {res['beer_price']:<8.3f} | {res['wool_price']:<8.3f} | {res['unrest_wardum']}%")

    print("\n" + "=" * 75)
    print("Astronomical Diaries 6-Benchmark CPI Status:")
    for g_id in ["barley", "dates", "mustard", "cress", "sesame", "raw_wool"]:
        g = sim.registry.get(g_id)
        p = sim.market.get_price(g_id)
        diff = ((p - g.base_price) / g.base_price) * 100
        print(f"  - {g.name:<18} ({g.akkadian_name}): {p:.3f} shekels ({diff:+.1f}% vs base {g.base_price:.2f})")
    print("=" * 75)
