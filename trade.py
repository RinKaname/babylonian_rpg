"""
trade.py - Long-Distance Mercantile & Caravan Logistics System for Babylonian RPG
================================================================================
Implements:
1. The Tamkarum (Professional Merchant Guild & Caravan Master).
2. The 4 Historical Foreign Trade Corridors:
   - Anatolia & Levant (Overland Donkey Caravan: Silver, Tin, Cedar Timber)
   - Dilmun / Bahrain (Gulf Entrepôt: Pearls, Middleman Exchange)
   - Magan / Oman (Maritime Gulf Route: Raw Copper Ore, Diorite Stone)
   - Meluhha / Indus Valley (Deep-Sea Oceanic Route: Lapis Lazuli, Carnelian, Ivory)
3. Transport Logistics: Pack Donkeys, Bitumen-Sealed Riverboats, Seagoing Barges.
4. Victoria 3 Market Integration:
   - Outbound departure: Buys domestic goods (submits Buy Orders, lifting local prices).
   - Inbound return: Sells foreign goods (submits Sell Orders, supplying local foundries/guilds).
5. Customs Tariffs (Miklū) at the City Gate & Risk Simulation (Bandits, Storms, Smuggling).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import math
import random
import sys

# Ensure clean UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from economics import SocialClass, Good, GoodsRegistry, Market
from character import Character, DualWallet, ClayTablet, DocumentType


# ==============================================================================
# 1. Trade Corridors & Transport Vehicles
# ==============================================================================

class TradeCorridor(Enum):
    ANATOLIA_LEVANT = "Anatolia & Levant (Overland North-West)"
    DILMUN_ENTREPOT = "Dilmun / Bahrain (Persian Gulf Entrepôt)"
    MAGAN_COAST = "Magan / Oman (Copper Coast South)"
    MELUHHA_INDUS = "Meluhha / Indus Valley (Exotic Ocean East)"


class TransportType(Enum):
    PACK_DONKEY = "Pack Donkey Caravan"
    REED_BOAT = "Bitumen-Sealed Reed Coracle"
    EUPHRATES_BARGE = "Heavy Wooden Riverboat"
    SEAGOING_VESSEL = "Deep-Sea Gulf Merchant Ship"


@dataclass
class TransportFleet:
    """Represents the transport capacity and operating costs of a merchant mission."""
    transport_type: TransportType
    units_count: int                   # Number of donkeys or boats
    cargo_capacity_kg: float
    daily_fodder_grain_qa: float       # Grain consumed per day to feed animals/rowers
    guard_cost_silver: float           # Daily silver wage for hired mercenary guards

    @classmethod
    def create_donkey_caravan(cls, num_donkeys: int, guards: int = 2) -> "TransportFleet":
        # Each donkey carries ~80 kg, eats 2 qa grain/day
        return cls(
            transport_type=TransportType.PACK_DONKEY,
            units_count=num_donkeys,
            cargo_capacity_kg=num_donkeys * 80.0,
            daily_fodder_grain_qa=num_donkeys * 2.0,
            guard_cost_silver=guards * 0.03  # ~5 grains of silver per day per guard
        )

    @classmethod
    def create_gulf_barge(cls, num_ships: int, sailors: int = 10) -> "TransportFleet":
        # Each barge carries ~5,000 kg, sailors eat 3 qa grain/day
        return cls(
            transport_type=TransportType.SEAGOING_VESSEL,
            units_count=num_ships,
            cargo_capacity_kg=num_ships * 5000.0,
            daily_fodder_grain_qa=sailors * 3.0,
            guard_cost_silver=sailors * 0.02
        )


# ==============================================================================
# 2. Foreign Market Node Data
# ==============================================================================

@dataclass
class ForeignMarketNode:
    """
    Represents an external trade node outside Mesopotamia.
    Defines travel duration, transit risk, and foreign price multipliers.
    """
    corridor: TradeCorridor
    name: str
    round_trip_days: int
    hazard_risk_percent: float         # Risk of bandit raid or shipwreck per journey
    demand_multipliers: Dict[str, float]  # Foreign willingness to pay for Babylonian exports
    export_supplies: Dict[str, float]     # Foreign base price for raw imports (in silver shekels)


class ForeignTradeDatabase:
    """Stores the pricing profiles of the 4 ancient trade corridors."""
    @staticmethod
    def get_nodes() -> Dict[TradeCorridor, ForeignMarketNode]:
        return {
            TradeCorridor.ANATOLIA_LEVANT: ForeignMarketNode(
                corridor=TradeCorridor.ANATOLIA_LEVANT,
                name="Kanesh & The Levant (Anatolia)",
                round_trip_days=90,  # ~1 season
                hazard_risk_percent=15.0,
                demand_multipliers={"woolen_cloth": 2.2, "dates": 1.6, "sesame_oil": 1.5},
                export_supplies={"tin": 8.0, "timber": 3.5, "bronze_tools": 3.0}
            ),
            TradeCorridor.DILMUN_ENTREPOT: ForeignMarketNode(
                corridor=TradeCorridor.DILMUN_ENTREPOT,
                name="Dilmun / Bahrain Gateway",
                round_trip_days=30,
                hazard_risk_percent=5.0,
                demand_multipliers={"barley": 1.4, "woolen_cloth": 1.3, "sesame_oil": 1.4},
                export_supplies={"dried_fish": 0.20, "dates": 0.40, "bitumen": 0.70}
            ),
            TradeCorridor.MAGAN_COAST: ForeignMarketNode(
                corridor=TradeCorridor.MAGAN_COAST,
                name="Magan / Oman Copper Coast",
                round_trip_days=60,
                hazard_risk_percent=12.0,
                demand_multipliers={"barley": 1.8, "bread": 1.5, "woolen_cloth": 1.5},
                export_supplies={"copper_ore": 2.20, "mudbrick": 0.08}
            ),
            TradeCorridor.MELUHHA_INDUS: ForeignMarketNode(
                corridor=TradeCorridor.MELUHHA_INDUS,
                name="Meluhha / Indus Valley Civilization",
                round_trip_days=120, # ~2 seasons
                hazard_risk_percent=20.0,
                demand_multipliers={"woolen_cloth": 2.8, "sesame_oil": 2.0, "pottery": 1.8},
                export_supplies={"cylinder_seal": 8.0, "perfume": 6.0}
            )
        }


# ==============================================================================
# 3. The Caravan Mission Entity
# ==============================================================================

@dataclass
class CaravanMission:
    """An active long-distance trade expedition under the direction of a Tamkarum."""
    id: str
    sponsor_name: str
    tamkarum_name: str
    corridor: TradeCorridor
    fleet: TransportFleet
    outbound_cargo: Dict[str, float]      # good_id -> quantity loaded in Babylon
    return_cargo: Dict[str, float]        # foreign goods acquired
    silver_capital_carried: float = 0.0   # Silver purse taken to buy foreign goods
    grain_fodder_carried: float = 0.0
    days_elapsed: int = 0
    is_completed: bool = False
    is_plundered_or_lost: bool = False
    net_profit_silver: float = 0.0


# ==============================================================================
# 4. The Mercantile Trade Manager
# ==============================================================================

class TradeManager:
    """
    Orchestrates the preparation, departure, travel, and return of merchant expeditions.
    Connects character finances with the Victoria 3 domestic market.
    """
    def __init__(self, registry: GoodsRegistry, market: Market):
        self.registry = registry
        self.market = market
        self.nodes = ForeignTradeDatabase.get_nodes()
        self.active_missions: List[CaravanMission] = []
        self.mission_counter = 1
        self.city_gate_customs_rate = 0.05  # 5% tariff on luxury/metal imports

    def assemble_caravan(
        self,
        investor: Character,
        corridor: TradeCorridor,
        fleet: TransportFleet,
        cargo_to_export: Dict[str, float],
        silver_purse: float,
        tamkarum_name: str = "Ur-Nungal, the Tamkarum"
    ) -> Tuple[bool, str, Optional[CaravanMission]]:
        """
        Assembles a merchant caravan in Babylon:
        1. Checks cargo weight vs fleet transport capacity.
        2. Buys outbound goods from local domestic market (submitting Buy Orders).
        3. Withdraws silver purse and grain fodder from investor's wallet.
        """
        node = self.nodes[corridor]

        # Step 1: Weight Capacity Verification
        total_weight_kg = 0.0
        for g_id, qty in cargo_to_export.items():
            g = self.registry.get(g_id)
            total_weight_kg += g.weight_kg * qty

        if total_weight_kg > fleet.cargo_capacity_kg:
            return False, f"Cargo overload! Weighs {total_weight_kg:.1f} kg (Fleet capacity: {fleet.cargo_capacity_kg:.1f} kg).", None

        # Step 2: Food & Guard Provisions for Round Trip
        total_fodder_qa = fleet.daily_fodder_grain_qa * node.round_trip_days
        total_guard_silver = fleet.guard_cost_silver * node.round_trip_days
        total_silver_needed = silver_purse + total_guard_silver

        # Step 3: Check Solvency
        if investor.wallet.silver_shekels < total_silver_needed:
            return False, f"Insufficient silver! Needs {total_silver_needed:.1f} shekels (Purse: {silver_purse:.1f} + Guards: {total_guard_silver:.1f}).", None

        if investor.wallet.barley_qa < total_fodder_qa:
            return False, f"Insufficient grain fodder! Needs {total_fodder_qa:.1f} qa for {node.round_trip_days} travel days.", None

        # Step 4: Purchase Domestic Export Cargo from Local Market
        total_cargo_cost = 0.0
        for g_id, qty in cargo_to_export.items():
            _, cost, _, _, _ = self.market.calculate_trade_pricing(g_id, qty, is_buy=True)
            total_cargo_cost += cost

        if investor.wallet.silver_shekels < (total_silver_needed + total_cargo_cost):
            return False, f"Cannot afford domestic export cargo! Costs {total_cargo_cost:.1f} silver shekels on local market.", None

        # Execute Outbound Purchases
        for g_id, qty in cargo_to_export.items():
            investor.buy_good(g_id, qty, self.market, self.registry)

        # Deduct Travel Costs
        investor.wallet.spend_silver(total_silver_needed)
        investor.wallet.spend_barley(total_fodder_qa)

        # Create Mission
        mission_id = f"expedition_{self.mission_counter:04d}"
        self.mission_counter += 1

        mission = CaravanMission(
            id=mission_id,
            sponsor_name=investor.full_name,
            tamkarum_name=tamkarum_name,
            corridor=corridor,
            fleet=fleet,
            outbound_cargo=cargo_to_export.copy(),
            return_cargo={},
            silver_capital_carried=silver_purse,
            grain_fodder_carried=total_fodder_qa
        )

        self.active_missions.append(mission)

        status_msg = (
            f"=== CARAVAN DEPARTURE: {mission.id.upper()} ===\n"
            f" Destination: {node.name} ({corridor.value})\n"
            f" Tamkarum:    {tamkarum_name} | Fleet: {fleet.units_count} {fleet.transport_type.value}\n"
            f" Cargo Mass:  {total_weight_kg:.1f} kg / {fleet.cargo_capacity_kg:.1f} kg capacity\n"
            f" Export Wares: " + ", ".join([f"{k}: {v:.1f}" for k, v in cargo_to_export.items()]) + "\n"
            f" Provisions:  {total_fodder_qa:.0f} qa grain fodder | {total_guard_silver:.1f} silver for guards\n"
            f" Silver Purse:{silver_purse:.1f} shekels carried for foreign purchases\n"
            f" Expected Journey: {node.round_trip_days} days"
        )
        return True, status_msg, mission

    def resolve_mission(self, mission: CaravanMission, investor: Character) -> Tuple[bool, str]:
        """
        Resolves the return of a caravan mission:
        1. Rolls for travel hazards (bandits/storms).
        2. Sells exported goods at foreign markup.
        3. Buys foreign goods with earned revenue + silver purse.
        4. Injects imported goods into Babylon's domestic market (Sell Orders).
        5. Deposits net silver profits into investor's wallet.
        """
        node = self.nodes[mission.corridor]
        lines = [f"=== EXPEDITION RETURN REPORT: {mission.id.upper()} ==="]

        # Step 1: Hazard Roll
        hazard_roll = random.uniform(0.0, 100.0)
        if hazard_roll < node.hazard_risk_percent:
            mission.is_plundered_or_lost = True
            mission.is_completed = True
            lines.append(f" [!] DISASTER EN ROUTE: Attacked by desert nomads / shipwrecked in storm!")
            lines.append(f"     All cargo and silver lost to the sands of the Euphrates. The Tamkarum barely escaped.")
            return False, "\n".join(lines)

        # Step 2: Foreign Sales Execution (Selling Babylonian goods abroad)
        foreign_silver_earned = mission.silver_capital_carried
        lines.append(f" [+] Safe arrival at {node.name}!")
        lines.append(f"     Sold outbound Babylonian wares on foreign markets:")

        for g_id, qty in mission.outbound_cargo.items():
            base_p = self.registry.get(g_id).base_price
            mult = node.demand_multipliers.get(g_id, 1.20)
            foreign_unit_price = base_p * mult
            revenue = foreign_unit_price * qty
            foreign_silver_earned += revenue
            lines.append(f"       * {g_id}: {qty:.1f} units sold at {foreign_unit_price:.2f} silver/ea (+{revenue:.1f} shekels)")

        # Step 3: Purchase Foreign Strategic Imports
        # Allocate foreign purse to buy foreign goods
        lines.append(f"     Acquired foreign strategic imports for return voyage:")
        acquired_cargo = {}
        for imp_id, foreign_price in node.export_supplies.items():
            # Spend up to 40% of purse per available foreign good
            spend_allowance = foreign_silver_earned * 0.40
            units_bought = math.floor(spend_allowance / max(0.1, foreign_price))
            if units_bought > 0:
                cost = units_bought * foreign_price
                foreign_silver_earned -= cost
                acquired_cargo[imp_id] = units_bought
                lines.append(f"       * {imp_id}: {units_bought} units bought at {foreign_price:.2f} silver/ea (-{cost:.1f} shekels)")

        mission.return_cargo = acquired_cargo

        # Step 4: Return to Babylon & City Gate Customs Inspection
        lines.append(f" [+] Returned to Babylon's City Gate (Kārum Quay):")
        customs_paid = 0.0
        for imp_id, qty in acquired_cargo.items():
            local_price = self.market.get_price(imp_id)
            tariff = (local_price * qty) * self.city_gate_customs_rate
            customs_paid += tariff
            # Submits Sell Orders into Babylon's market, expanding domestic supply
            self.market.submit_sell_order(imp_id, qty)
            # Give inventory to investor
            investor.inventory[imp_id] = investor.inventory.get(imp_id, 0.0) + qty

        foreign_silver_earned = max(0.0, foreign_silver_earned - customs_paid)
        lines.append(f"     Paid City Gate customs tariff (Miklū): {customs_paid:.2f} silver shekels")
        lines.append(f"     Deposited remaining silver coin into investor's vault: +{foreign_silver_earned:.1f} shekels")

        investor.wallet.add_silver(foreign_silver_earned)
        investor.reputation = min(100.0, investor.reputation + 4.0)

        mission.net_profit_silver = foreign_silver_earned
        mission.is_completed = True
        return True, "\n".join(lines)


# ==============================================================================
# 5. Verification Demonstration
# ==============================================================================

if __name__ == "__main__":
    print("=" * 75)
    print("      BABYLONIAN RPG - TAMKARUM CARAVAN & TRADE ENGINE")
    print("=" * 75)

    reg = GoodsRegistry()
    mkt = Market(reg)
    trade_mgr = TradeManager(reg, mkt)

    # 1. Setup Merchant Prince Iddin-Marduk
    investor = Character("Iddin-Marduk", "Nabu-ahhe-iddin", SocialClass.AWILUM)
    investor.wallet.silver_shekels = 200.0  # Wealthy merchant capital
    investor.wallet.barley_qa = 2400.0      # 8 gur grain fodder (sufficient for 1,800 qa requirement)

    print("\n--- Investor Starting Profile ---")
    print(investor.get_status_report())

    # 2. Assemble Donkey Caravan to Anatolia (Seeking Tin & Cedar Timber)
    fleet = TransportFleet.create_donkey_caravan(num_donkeys=10, guards=4)
    export_goods = {"woolen_cloth": 20.0, "dates": 15.0}

    print("\n" + "-" * 75)
    print("Preparing Northern Overland Expedition to Anatolia...")
    ok, msg, mission = trade_mgr.assemble_caravan(
        investor=investor,
        corridor=TradeCorridor.ANATOLIA_LEVANT,
        fleet=fleet,
        cargo_to_export=export_goods,
        silver_purse=40.0,
        tamkarum_name="Bel-zer-ibni, Chief Tamkarum"
    )
    print(msg)

    # 3. Simulate Resolution of the Caravan Mission
    if ok and mission:
        print("\n" + "=" * 75)
        print("Simulating 90-day return voyage from Anatolia...\n")
        success, return_report = trade_mgr.resolve_mission(mission, investor)
        print(return_report)

    # 4. Review Investor Ending Assets
    print("\n" + "=" * 75)
    print("--- Investor Ending Profile & Acquired Strategic Goods ---")
    print(investor.get_status_report())
    print("=" * 75)
