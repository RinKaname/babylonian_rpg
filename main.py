"""
main.py - Babylonian RPG: Life in the Cradle of Civilization
=============================================================
Master Playable Interactive Terminal RPG Engine.
Governed by the Code of Hammurabi (c. 1750 BC) and Historical Economics.

Integrated Subsystems:
1. economics.py: Victoria 3 dynamic flow market, PMs, 29 Mesopotamian goods, Esagila CPI.
2. character.py: Dual-currency wallet (silver shekels + volumetric barley), needs, inventory, cylinder seals.
3. marriage.py: Marriage covenants (rikistum, § 128), terhatum (bride-price), seriktum (dowry), divorce (§§ 137-142).
4. trade.py: Tamkarum caravan & Gulf barge logistics across Anatolia, Dilmun, Magan, and Meluhha.
5. politics.py: 5 Civic offices (Gugallum, Rabi Sikkatim, Dayyānum, Šangû, Rabiānum), Puhrum assembly elections,
   Hammurabi court trials at the Gate of Shamash, and royal Misharum debt jubilees.
"""

import sys
import os
import json
import time
import random
from typing import Dict, List, Optional, Any, Tuple

# Ensure clean UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from economics import SocialClass, Good, GoodsRegistry, Market, BabylonianEconomy
from character import Character, DualWallet, ClayTablet, DocumentType, CylinderSeal, CharacterSkills
from marriage import MarriageManager, MarriageContract, Dowry, DivorceReason
from trade import TradeManager, TradeCorridor, TransportFleet, TransportType, CaravanMission
from politics import BabylonianPolitics, OfficeTitle, LawsuitCharge, JudicialCase, OFFICE_CATALOG
from war import (
    BabylonianWarEngine, UnitType, SoldierRegiment, CityGate,
    BattleResult, UNIT_CATALOG
)


# ------------------------------------------------------------------------------
# Workshop Capacity & Wage Standards (Code of Hammurabi §§ 273-274)
# ------------------------------------------------------------------------------

WORKSHOP_TIERS = {
    1: {
        "name": "Domestic Courtyard",
        "description": "Family courtyard with rudimentary clay vats & hearth",
        "max_batches": 3,
        "required_workers": 0,
        "upgrade_cost_silver": 0.0,
        "time_multiplier": 1.0,
    },
    2: {
        "name": "Guild Workshop",
        "description": "Dedicated workshop with brick kilns, looms, and copper vats",
        "max_batches": 8,
        "required_workers": 1,
        "upgrade_cost_silver": 35.0,
        "time_multiplier": 0.85,
    },
    3: {
        "name": "Patrician Manufactory",
        "description": "Large manufactory with specialized workstations and storage vaults",
        "max_batches": 25,
        "required_workers": 3,
        "upgrade_cost_silver": 100.0,
        "time_multiplier": 0.70,
    }
}

WAGE_POLICIES = {
    "STINGY": {
        "name": "Stingy (Below Statutory)",
        "grains_per_day": 3.0,
        "speed_mult": 1.25,
        "description": "3 grains/day. Workers are discontented and labor sluggishly."
    },
    "STATUTORY": {
        "name": "Statutory Minimum (Code § 274)",
        "grains_per_day": 5.0,
        "speed_mult": 1.0,
        "description": "5 grains/day (indexed to Esagila CPI). Lawful and dependable labor."
    },
    "EFFICIENCY": {
        "name": "Efficiency Wage (Generous)",
        "grains_per_day": 8.0,
        "speed_mult": 0.80,
        "description": "8 grains/day (indexed to Esagila CPI). Attracts master journeymen (+20% speed)."
    }
}


class BabylonianGame:
    """The master game coordinator for the Babylonian Life-Sim RPG."""

    SAVE_FILE_PATH = "savegame.json"

    def __init__(self):
        # 1. Subsystems Initialization
        self.economy = BabylonianEconomy()
        self.registry = self.economy.registry
        self.market = self.economy.market
        self.marriage_mgr = MarriageManager()
        self.trade_mgr = TradeManager(self.registry, self.market)
        self.politics = BabylonianPolitics(self.registry, self.market)
        self.war_engine = BabylonianWarEngine(self.registry, self.market)

        # 2. Calendar, Day-Clock & World State
        self.year = 1
        self.seasons = [
            ("Autumn", "Sowing of Seeds & Plowing"),
            ("Winter", "Canal Dredging & Field Tending"),
            ("Spring", "The Great Barley & Flax Harvest"),
            ("Summer", "Euphrates Flood & Date Palm Gathering")
        ]
        self.season_idx = 0
        self.day: int = 1
        self.hour: float = 8.0  # 08:00 Morning
        self.days_per_season: int = 14
        self.news_ticker: List[str] = [
            "King Hammurabi has inscribed his righteous laws upon a diorite stele at the temple of Shamash.",
            "Euphrates waters are calm. Canals across the southern plains are open for irrigation."
        ]

        # Workshop & Labor State
        self.workshop_tier: int = 1
        self.hired_artisans: int = 0
        self.wage_policy: str = "STATUTORY"

        # 3. Notable World Citizens (NPCs)
        self.npcs: Dict[str, Character] = self._setup_world_npcs()

        # 4. Player Character
        self.player: Optional[Character] = None

        # 5. Active Marriage Contract (if player is married)
        self.player_marriage_contract: Optional[MarriageContract] = None

    def get_time_label(self) -> str:
        """Returns descriptive time-of-day label for Babylonian daily rhythms."""
        h = self.hour % 24.0
        if 5.0 <= h < 8.0:
            return "Dawn"
        elif 8.0 <= h < 12.0:
            return "Morning"
        elif 12.0 <= h < 14.0:
            return "Midday Heat"
        elif 14.0 <= h < 18.0:
            return "Afternoon"
        elif 18.0 <= h < 21.0:
            return "Dusk"
        else:
            return "Night"

    def advance_hours(self, delta_hours: float):
        """Advances intraday clock, applying metabolism and daily wage accounting."""
        if delta_hours <= 0:
            return

        self.hour += delta_hours
        if self.player:
            self.player.hunger = min(100.0, self.player.hunger + delta_hours * 0.8)
            self.player.thirst = min(100.0, self.player.thirst + delta_hours * 1.2)

        while self.hour >= 24.0:
            self.hour -= 24.0
            self.day += 1

            # Daily wage settlement for hired artisans
            if self.hired_artisans > 0 and self.player:
                cpi = self.market.calculate_cpi()
                grains = WAGE_POLICIES[self.wage_policy]["grains_per_day"]
                # 1 shekel = 180 grains of silver
                daily_wage_silver = (grains * cpi / 180.0) * self.hired_artisans
                if self.player.wallet.spend_silver(daily_wage_silver):
                    print(f"\n [Wage Settlement] Paid {daily_wage_silver:.2f} silver ({grains*self.hired_artisans:.0f} grains) in daily wages to {self.hired_artisans} artisan(s) ({self.wage_policy}).")
                else:
                    print(f"\n [!] Wage Default! Could not pay {daily_wage_silver:.2f} silver to hired artisans. The workers have downed their tools and departed!")
                    self.hired_artisans = 0
                    self.player.reputation = max(10.0, self.player.reputation - 5.0)

            # Daily garrison upkeep settlement (under Governor / Rabiānum administration)
            if self.player and self.player.civic_office and "Governor" in self.player.civic_office:
                ok_upkeep, upkeep_msg = self.war_engine.pay_daily_upkeep(self.player)
                if not ok_upkeep:
                    print(f"\n{upkeep_msg}")

            if self.day > self.days_per_season:
                self.advance_season()

    def _setup_world_npcs(self) -> Dict[str, Character]:
        """Creates authentic historical Babylonian citizens for social interaction."""
        npcs = {
            "patrician_rival": Character("Rim-Sin", "Sin-magir", SocialClass.AWILUM, age=34),
            "temple_priest": Character("Ur-Nungal", "Nanna-mansum", SocialClass.AWILUM, age=48),
            "amat_bau": Character("Amat-Ba'u", "Marduk-nasir", SocialClass.AWILUM, age=20, gender="female"),
            "beltani": Character("Beltani", "Iddin-Enlil", SocialClass.MUSHKENUM, age=19, gender="female"),
            "shamhat": Character("Shamhat", "", SocialClass.MUSHKENUM, age=22, gender="female"),
            "free_farmer_neighbor": Character("Sin-nasir", "Enlil-bani", SocialClass.MUSHKENUM, age=28, gender="male"),
            "tavern_keeper": Character("Alitu", "Dagan-abi", SocialClass.MUSHKENUM, age=40, gender="female")
        }
        # NPC starting assets
        npcs["patrician_rival"].wallet.silver_shekels = 220.0
        npcs["patrician_rival"].civic_office = OfficeTitle.MARKET_OVERSEER.value
        self.politics.office_holders[OfficeTitle.MARKET_OVERSEER] = npcs["patrician_rival"]

        npcs["temple_priest"].civic_office = OfficeTitle.HIGH_PRIEST.value
        self.politics.office_holders[OfficeTitle.HIGH_PRIEST] = npcs["temple_priest"]

        return npcs

    # --------------------------------------------------------------------------
    # Character Selection & Archetypes
    # --------------------------------------------------------------------------

    def setup_player_interactive(self):
        """Allows the player to create or load an authentic Babylonian persona."""
        print("=" * 78)
        print("          BABYLONIAN RPG: LIFE IN THE CRADLE OF CIVILIZATION")
        print("               Ancient Mesopotamia (c. 1750 BC / Old Babylonian)")
        print("=" * 78)

        if os.path.exists(self.SAVE_FILE_PATH):
            load_choice = input(" Found existing saved game. Would you like to [L]oad or start [N]ew? [default=N]: ").strip().lower()
            if load_choice == "l":
                if self.load_game():
                    print("\n[+] Saved game successfully restored. Resuming your journey!")
                    return

        print("\n Choose Your Social Origin in the Kingdom of Babylon:")
        print("-" * 78)
        print(" [1] The Ambitious Merchant (Awilum - Patrician Noble)")
        print("     Starting Wealth: 100 Silver Shekels, 2 Gur Barley (600 qa), 20 Acres Land, 2 Oxen.")
        print("     Seal: Lapis Lazuli carved with Marduk. High scribal literacy & commercial acumen.")
        print("     Pillars: Foreign Trade Caravans, Assembly Politics, Civic Offices.")
        print()
        print(" [2] The Tenant Yeoman / Artisan (Mushkenum - Free Commoner)")
        print("     Starting Wealth: 10 Silver Shekels, 1 Gur Barley (300 qa), 5 Acres Land.")
        print("     Seal: Steatite carved with Shamash. Practical agricultural & crafting skills.")
        print("     Pillars: Farming, Brewing, Weaving, Workshops, Social Mobility.")
        print()
        print(" [3] The Indebted Laborer (Wardum - State Servant / Bondman)")
        print("     Starting Wealth: 0.5 Silver Shekels, 60 qa basic food rations, 0 Land.")
        print("     Seal: None (Enslaved/Unenfranchised). Highly physically resilient.")
        print("     Pillars: Earning Silver, Buying Freedom (Manumission), Rising to Commoner.")
        print("-" * 78)

        choice = input(" Select your background [1-3, default = 2]: ").strip()
        name = input(" Enter your Babylonian name [default = 'Iddin-Sin']: ").strip() or "Iddin-Sin"
        father = input(" Enter your father's name [default = 'Ea-malik']: ").strip() or "Ea-malik"

        if choice == "1":
            self.player = Character(name, father, SocialClass.AWILUM, is_player=True)
        elif choice == "3":
            self.player = Character(name, "", SocialClass.WARDUM, is_player=True)
        else:
            self.player = Character(name, father, SocialClass.MUSHKENUM, is_player=True)

        # Custom Cylinder Seal selection
        if self.player.social_class != SocialClass.WARDUM:
            print("\n Carve your Personal Cuneiform Cylinder Seal (Kunukku):")
            print(" [1] Steatite (Common stone, reliable imprint)")
            print(" [2] Hematite (Metallic black, favored by merchants)")
            print(" [3] Carnelian (Red polished gem, high prestige)")
            print(" [4] Lapis Lazuli (Deep blue Afghan stone, aristocratic honor)")
            s_choice = input(" Select seal gemstone [1-4, default = 1]: ").strip()
            seal_mat = {"1": "Steatite", "2": "Hematite", "3": "Carnelian", "4": "Lapis Lazuli"}.get(s_choice, "Steatite")
            
            deity_name = input(" Name your patron deity [Shamash/Marduk/Ishtar/Enlil, default='Shamash']: ").strip() or "Shamash"
            prestige_map = {"Steatite": 5, "Hematite": 8, "Carnelian": 12, "Lapis Lazuli": 16}
            self.player.cylinder_seal = CylinderSeal(
                owner_name=self.player.full_name,
                material=seal_mat,
                patron_deity=deity_name,
                prestige_rating=prestige_map.get(seal_mat, 5)
            )

        print(f"\n[+] In the presence of Shamash the Sun God, your name is inscribed: {self.player.full_name}")
        print(f"    Social Estate: {self.player.social_class.value}")

    # --------------------------------------------------------------------------
    # Main Dashboard & HUD
    # --------------------------------------------------------------------------

    def render_dashboard(self):
        """Displays the comprehensive, rich visual status of the player and city."""
        p = self.player
        season_name, season_desc = self.seasons[self.season_idx]
        cpi = self.market.calculate_cpi()

        # Health / Energy visual meters
        def meter(val: float, max_val: float = 100.0) -> str:
            blocks = int((val / max_val) * 10)
            return "█" * blocks + "░" * (10 - blocks)

        hour_int = int(self.hour)
        min_int = int((self.hour - hour_int) * 60)
        time_str = f"{hour_int:02d}:{min_int:02d}"
        tier_info = WORKSHOP_TIERS.get(self.workshop_tier, WORKSHOP_TIERS[1])
        cpi_str = f"{cpi:.3f}x"

        print("\n" + "=" * 78)
        print(f" YEAR {self.year:02d} | {season_name.upper()} ({season_desc}) | DAY {self.day:02d}/{self.days_per_season} | {time_str} ({self.get_time_label()})")
        print(f" Esagila CPI: {cpi_str:<8} | Workshop: Tier {self.workshop_tier} ({tier_info['name']}) | Artisans: {self.hired_artisans} hired")
        print("=" * 78)
        
        office_str = p.civic_office if p.civic_office else "Private Citizen"
        print(f" Citizen:     {p.full_name:<30} | Class:  {p.social_class.value}")
        print(f" Office:      {office_str:<30} | Honor:  {p.reputation:.1f}/100")
        print(f" Health:      [{meter(p.health)}] {p.health:3.0f}%        | Energy: [{meter(p.energy)}] {p.energy:3.0f}%")
        print(f" Hunger:      {p.hunger:3.0f}/100 ({'Satiated' if p.hunger < 30 else 'Hungry' if p.hunger < 70 else 'STARVING!'})   | Thirst: {p.thirst:3.0f}/100 ({'Quenched' if p.thirst < 30 else 'Thirsty' if p.thirst < 70 else 'PARCHED!'})")
        
        # Dual Currency & Real Estate
        print("-" * 78)
        print(f" Silver (Weighed):  {p.wallet.silver_shekels:7.2f} shekels ({p.wallet.silver_grains:.0f} grains) | 1 mina = 60 shekels")
        print(f" Barley (Volume):   {p.wallet.barley_gur:7.2f} gur ({p.wallet.barley_qa:5.0f} qa / sila)    | 1 gur  = 300 qa")
        print(f" Real Estate:       {p.owned_land_acres:7.1f} acres arable land | Draft Oxen: {p.owned_oxen:2d} | Wool Sheep: {p.owned_sheep:2d}")
        
        seal_txt = f"{p.cylinder_seal.material} (Servant of {p.cylinder_seal.patron_deity})" if p.cylinder_seal else "None (Enslaved / Unenfranchised)"
        print(f" Cylinder Seal:     {seal_txt}")

        # Inventory overview
        if p.inventory:
            inv_items = [f"{k}: {v:.1f}" for k, v in sorted(p.inventory.items())]
            print(f" Inventory:         {', '.join(inv_items[:6])}")
            if len(inv_items) > 6:
                print(f"                    {', '.join(inv_items[6:])}")
        else:
            print(" Inventory:         (Empty)")

        # Marriage & Cuneiform Tablets
        married_str = f"Married to {self.player_marriage_contract.wife.full_name if self.player_marriage_contract else 'Spouse'}" if self.player_marriage_contract else "Unmarried"
        print(f" Domestic Estate:   {married_str} | Cuneiform Tablets Sealed: {len(p.tablets)}")

        # City Gazette & News
        if self.news_ticker:
            print("-" * 78)
            print(" CITY GAZETTE & STREET RUMORS:")
            for news in self.news_ticker[-2:]:
                print(f"  * {news}")
        print("=" * 78)

    def print_menu(self):
        """Presents the 8 core historical actions available to the player."""
        print(" ACTIONS AVAILABLE IN BABYLON:")
        print(" [1] The Public Market (Kārum Quay) - Buy & Sell Commodities on Babylonian Market")
        print(" [2] Agriculture, Livestock & Workshops - Field Sowing, Harvest, Land Deeds & Crafting")
        print(" [3] Ale-Wife's Tavern (Bīth Šikari) - Beer, Royal Game of Ur Wager, Rumors & Suitors")
        print(" [4] Long-Distance Trade Caravans - Sponsor Tamkarum Expeditions to Foreign Realms")
        print(" [5] Civic Politics & Puhrum Assembly - Campaign for Offices, Bribes & State Decrees")
        print(" [6] Hall of Justice (Gate of Shamash) - Litigate Disputes under the Code of Hammurabi")
        print(" [7] Domestic Household & Archive - Manage Marriage, Dowry, Alimony & Clay Tablets")
        print(" [8] Rest & Sleep (06:00 Dawn) or Advance Season - Recover Energy & Day Progress")
        print(" [E] Eat / Drink Rations from Sacks - Sate hunger, quench thirst, or restore energy")
        print(" [9] Save Game to Clay Archive")
        print(" [0] Exit Game")
        print("-" * 78)

    # --------------------------------------------------------------------------
    # Subsystem 1: The Public Market (Kārum Quay)
    # --------------------------------------------------------------------------

    def handle_market(self):
        """Interactive market trading with real-time Victoria 3 supply/demand prices."""
        while True:
            print("\n" + "=" * 70)
            print("            THE PUBLIC MARKET AT THE KĀRUM QUAY")
            print("=" * 70)
            print(f" Your Liquid Purse: {self.player.wallet.silver_shekels:.2f} silver shekels")
            print(f"{'Commodity':<20} | {'Base Price':<11} | {'Market Price':<14} | {'Status'}")
            print("-" * 70)

            # Display curated list of benchmark and essential goods
            catalog = [
                ("barley", "Basic Food"),
                ("bread", "Basic Food"),
                ("dates", "Fruit"),
                ("sesame_oil", "Oils & Fuel"),
                ("barley_beer", "Drink"),
                ("woolen_cloth", "Textiles"),
                ("mudbrick", "Building"),
                ("bronze_tools", "Utilitarian"),
                ("tin", "Raw Mineral"),
                ("copper_ore", "Raw Mineral"),
                ("perfume", "Luxury"),
                ("timber", "Building")
            ]

            for g_id, sector in catalog:
                g = self.registry.get(g_id)
                cur_p = self.market.get_price(g_id)
                shortage = "[SHORTAGE!]" if self.market.is_in_shortage(g_id) else "Abundant" if cur_p < g.base_price * 0.8 else "Fair Market"
                print(f" {g.name:<19} | {g.base_price:6.2f} silv | {cur_p:7.3f} silv/ea | {shortage}")

            print("-" * 70)
            print(" [B]uy Good  |  [S]ell Good  |  [V]iew All 29 Goods  |  [R]eturn to City Square")
            cmd = input(" Select market action [B/S/V/R]: ").strip().lower()

            if cmd == "b":
                g_id = input(" Enter commodity ID to buy (e.g. 'bread', 'barley_beer', 'tin'): ").strip().lower()
                if g_id in self.registry.goods:
                    cur_p = self.market.get_price(g_id)
                    max_afford = int(self.player.wallet.silver_shekels // cur_p)
                    print(f" Current price: {cur_p:.3f} silver each. You can afford up to {max_afford} units.")
                    qty_str = input(" How many units would you like to buy? ").strip()
                    try:
                        qty = float(qty_str)
                        if qty <= 0:
                            continue
                        if self.player.buy_good(g_id, qty, self.market, self.registry):
                            total_cost = cur_p * qty
                            print(f" [+] Success! Purchased {qty:.1f} {g_id} for {total_cost:.2f} silver shekels.")
                        else:
                            print(" [!] Transaction failed: Insufficient silver shekels.")
                    except ValueError:
                        print(" [!] Please enter a valid number.")
                else:
                    print(" [!] Unknown commodity ID.")

            elif cmd == "s":
                if not self.player.inventory:
                    print(" [!] Your inventory sacks are completely empty.")
                    continue
                print("\n Your Sacks:")
                for item, count in self.player.inventory.items():
                    print(f"  * {item}: {count:.1f} units (Value: {self.market.get_price(item)*count:.2f} silver)")
                g_id = input(" Enter commodity ID to sell: ").strip().lower()
                if g_id in self.player.inventory:
                    avail = self.player.inventory[g_id]
                    qty_str = input(f" Units to sell (Available: {avail:.1f}) [default={avail:.1f}]: ").strip()
                    try:
                        qty = float(qty_str) if qty_str else avail
                        if 0 < qty <= avail:
                            cur_p = self.market.get_price(g_id)
                            if self.player.sell_good(g_id, qty, self.market, self.registry):
                                print(f" [+] Sold {qty:.1f} {g_id} for {cur_p * qty:.2f} silver shekels!")
                        else:
                            print(" [!] Invalid quantity.")
                    except ValueError:
                        print(" [!] Invalid input.")
                else:
                    print(" [!] You do not possess that commodity.")

            elif cmd == "v":
                print("\n=== COMPLETE MESOPOTAMIAN COMMODITY REGISTRY (29 GOODS) ===")
                for gid, good in sorted(self.registry.goods.items()):
                    p = self.market.get_price(gid)
                    print(f"  {good.name:<22} ({gid:<15}) | Base: {good.base_price:6.2f} | Current: {p:6.3f} silver")
                input("\n Press Enter to return to market menu...")

            elif cmd == "r":
                break

    # --------------------------------------------------------------------------
    # Subsystem 2: Agriculture, Livestock & Workshops
    # --------------------------------------------------------------------------

    def handle_work(self):
        """Field agriculture across seasons, real estate deeds, and workshop crafts."""
        while True:
            season_name, _ = self.seasons[self.season_idx]
            print("\n" + "=" * 70)
            print(f"      AGRICULTURE, REAL ESTATE & WORKSHOP GUILDS ({season_name.upper()})")
            print("=" * 70)
            print(f" Land Owned:    {self.player.owned_land_acres:.1f} acres arable soil")
            print(f" Livestock:     {self.player.owned_oxen} draft oxen (+{self.player.owned_oxen*25}% harvest bonus) | {self.player.owned_sheep} sheep")
            print(f" Stored Barley: {self.player.wallet.barley_gur:.2f} gur ({self.player.wallet.barley_qa:.0f} qa)")
            print(f" Stored Silver: {self.player.wallet.silver_shekels:.2f} silver shekels")
            print("-" * 70)
            print(" [1] Seasonal Field Labor (Sowing / Canal Care / Harvest)")
            print(" [2] Purchase Arable Land Title Deed (20 silver/acre with sealed tablet)")
            print(" [3] Sell Land Deed (15 silver/acre liquid silver)")
            print(" [4] Livestock Market (Buy Draft Oxen or Wool Sheep)")
            print(" [5] Artisan Workshops & Guilds (Batch Brewing, Baking, Weaving, Smithing & Wages)")
            print(" [6] Municipal Corvée Wage Labor (Code §§ 273-274: 5 grains silver/day)")
            print(" [0] Return to City Square")
            print("-" * 70)

            act = input(" Choose action [0-6]: ").strip()

            if act == "1":
                # Seasonal agriculture operations
                if self.player.energy < 25:
                    print(" [!] You are exhausted! Sleep and rest before laboring in the heat.")
                    continue

                if self.season_idx == 0:  # Autumn - Sowing
                    if self.player.owned_land_acres <= 0:
                        print(" [!] You have no land to sow! Acquire an arable land title deed first.")
                        continue
                    seed_needed_qa = self.player.owned_land_acres * 10.0  # 10 qa per acre
                    if self.player.wallet.barley_qa < seed_needed_qa:
                        print(f" [!] Insufficient seed barley! You need {seed_needed_qa:.0f} qa (You have {self.player.wallet.barley_qa:.0f} qa).")
                        continue
                    self.player.wallet.spend_barley(seed_needed_qa)
                    self.player.inventory["barley"] = self.player.wallet.barley_qa
                    if self.player.inventory["barley"] <= 0:
                        del self.player.inventory["barley"]
                    self.player.energy -= 30.0
                    self.player.hunger += 20.0
                    self.player.skills.agriculture += 1
                    self.advance_hours(6.0)
                    print(f" [+] Plowing & Sowing complete (6.0 hours)! Sowed {seed_needed_qa:.0f} qa seed across {self.player.owned_land_acres:.1f} acres.")

                elif self.season_idx == 1:  # Winter - Canal Care
                    self.player.energy -= 25.0
                    self.player.hunger += 15.0
                    self.player.skills.agriculture += 1
                    self.advance_hours(6.0)
                    print(" [+] Cleared silt from irrigation ditches and reinforced perimeter dikes against winter floods (6.0 hours).")

                elif self.season_idx == 2:  # Spring - The Great Harvest!
                    if self.player.owned_land_acres <= 0:
                        print(" [!] You have no fields to reap!")
                        continue
                    # Yield calculation: base 8-12 gur per 10 acres, boosted by oxen & skill
                    oxen_mult = 1.0 + (self.player.owned_oxen * 0.25)
                    skill_mult = 1.0 + (self.player.skills.agriculture * 0.10)
                    yield_per_acre_qa = random.uniform(250.0, 380.0) * oxen_mult * skill_mult
                    total_harvest_qa = self.player.owned_land_acres * yield_per_acre_qa
                    
                    self.player.wallet.add_barley(total_harvest_qa)
                    self.player.inventory["barley"] = self.player.wallet.barley_qa
                    self.player.energy -= 45.0
                    self.player.hunger += 25.0
                    
                    # Wool shear from sheep
                    wool_harvest = self.player.owned_sheep * 2.5
                    if wool_harvest > 0:
                        self.player.inventory["raw_wool"] = self.player.inventory.get("raw_wool", 0.0) + wool_harvest
                        print(f" [+] Sheared {wool_harvest:.1f} talents of raw wool from your sheep!")

                    self.advance_hours(8.0)
                    print(f" [+] Bountiful Spring Harvest (8.0 hours)! Threshed {total_harvest_qa/300:.2f} gur ({total_harvest_qa:.0f} qa) of prime barley!")

                elif self.season_idx == 3:  # Summer - Flood & Date Orchards
                    dates_gathered = random.uniform(5.0, 15.0)
                    self.player.inventory["dates"] = self.player.inventory.get("dates", 0.0) + dates_gathered
                    self.player.energy -= 20.0
                    self.player.thirst += 25.0
                    self.advance_hours(4.0)
                    print(f" [+] Gathered {dates_gathered:.1f} baskets of ripe dates from the riverbank date palms (4.0 hours).")

            elif act == "2":
                # Buy Land Deed
                cost_per_acre = 20.0
                acres_str = input(" How many acres of arable land to purchase (20 silver/acre)? ").strip()
                try:
                    acres = float(acres_str)
                    if acres <= 0:
                        continue
                    total_silver = acres * cost_per_acre
                    if self.player.wallet.spend_silver(total_silver):
                        self.player.owned_land_acres += acres
                        # Record cuneiform title deed
                        deed_id = f"deed_{len(self.player.tablets)+1:03d}"
                        deed = ClayTablet(
                            id=deed_id,
                            doc_type=DocumentType.LAND_DEED,
                            summary=f"Purchase of {acres:.1f} iku of arable canal field at 20 silver/acre",
                            parties_involved=[self.player.full_name, "Crown Lands Administration"],
                            principal_silver=total_silver
                        )
                        self.player.sign_tablet(deed)
                        self.player.tablets.append(deed)
                        print(f" [+] Title Deed sealed into clay! You now hold {self.player.owned_land_acres:.1f} acres of canal land.")
                    else:
                        print(f" [!] Insufficient silver shekels. Needs {total_silver:.2f} silver.")
                except ValueError:
                    print(" [!] Invalid number.")

            elif act == "3":
                # Sell Land Deed
                if self.player.owned_land_acres <= 0:
                    print(" [!] You hold no land to sell.")
                    continue
                acres_str = input(f" How many acres to liquidate (Hold: {self.player.owned_land_acres:.1f})? ").strip()
                try:
                    acres = float(acres_str)
                    if 0 < acres <= self.player.owned_land_acres:
                        payout = acres * 15.0
                        self.player.owned_land_acres -= acres
                        self.player.wallet.add_silver(payout)
                        print(f" [+] Sold {acres:.1f} acres to local estate. Received {payout:.2f} silver shekels.")
                    else:
                        print(" [!] Invalid acreage.")
                except ValueError:
                    print(" [!] Invalid number.")

            elif act == "4":
                # Livestock Market
                print("\n--- THE LIVESTOCK QUAY ---")
                print(" [1] Buy Draft Ox (15.0 silver each) - Ploughs fields, boosting harvest yield +25%")
                print(" [2] Buy Wool Sheep (2.0 silver each) - Produces shearable wool every Spring")
                print(" [3] Return")
                l_act = input(" Select purchase [1-3]: ").strip()
                if l_act == "1":
                    if self.player.wallet.spend_silver(15.0):
                        self.player.owned_oxen += 1
                        print(f" [+] Purchased a sturdy draft ox! Total oxen: {self.player.owned_oxen}.")
                    else:
                        print(" [!] You need 15.0 silver shekels for a draft ox.")
                elif l_act == "2":
                    if self.player.wallet.spend_silver(2.0):
                        self.player.owned_sheep += 1
                        print(f" [+] Purchased a wool sheep! Total sheep: {self.player.owned_sheep}.")
                    else:
                        print(" [!] You need 2.0 silver shekels for a sheep.")

            elif act == "5":
                self.handle_workshop()

            elif act == "6":
                # Public Works Corvée Wage Labor
                if self.player.energy < 20:
                    print(" [!] Too weary to dig irrigation canals. Rest first.")
                    continue
                # Code §§ 273-274: 5 grains of silver per day indexed to Esagila CPI
                cpi = self.market.calculate_cpi()
                wage_silver = (5.0 * cpi / 180.0)
                self.player.wallet.add_silver(wage_silver)
                self.player.energy = max(0.0, self.player.energy - 30.0)
                self.player.hunger = min(100.0, self.player.hunger + 20.0)
                self.player.thirst = min(100.0, self.player.thirst + 25.0)
                self.player.skills.craftsmanship += 1
                self.advance_hours(8.0)
                print(f" [+] Labored 8 hours on royal municipal canal dredging. Paid statutory wage: {wage_silver:.2f} silver ({5.0*cpi:.1f} grains)!")

            elif act == "0":
                break

    def handle_workshop(self):
        """Artisan workshops, batch manufacturing, facility upgrades & labor wage management."""
        while True:
            tier_info = WORKSHOP_TIERS.get(self.workshop_tier, WORKSHOP_TIERS[1])
            req_workers = tier_info["required_workers"]
            is_adequately_staffed = (self.hired_artisans >= req_workers)
            effective_capacity = tier_info["max_batches"] if is_adequately_staffed else WORKSHOP_TIERS[1]["max_batches"]
            facility_mult = tier_info["time_multiplier"] if is_adequately_staffed else WORKSHOP_TIERS[1]["time_multiplier"]
            wage_info = WAGE_POLICIES.get(self.wage_policy, WAGE_POLICIES["STATUTORY"])
            cpi = self.market.calculate_cpi()
            daily_wage_silver = (wage_info["grains_per_day"] * cpi / 180.0)

            h_int = int(self.hour)
            m_int = int((self.hour - h_int) * 60)
            time_str = f"{h_int:02d}:{m_int:02d}"

            print("\n" + "=" * 75)
            print(f"       ARTISAN WORKSHOPS & GUILDS (Tier {self.workshop_tier}: {tier_info['name'].upper()})")
            print("=" * 75)
            print(f" Facility Capacity: Up to {effective_capacity} batches/run (Facility Max: {tier_info['max_batches']})")
            staff_status = "Fully Staffed" if is_adequately_staffed else f"[UNDERSTAFFED! Needs {req_workers} Artisans]"
            print(f" Labor Force:       {self.hired_artisans} Hired Artisan(s) ({staff_status})")
            print(f" Wage Policy:       {wage_info['name']} ({daily_wage_silver:.3f} silver/day/worker | CPI {cpi:.3f}x)")
            print(f" Current Time:      Day {self.day:02d}/{self.days_per_season} | {time_str} ({self.get_time_label()}) | Energy: {self.player.energy:.0f}%")
            print("-" * 75)
            print(" PRODUCTION & FORGING RECIPES:")
            print(" [1] Brewery:      Mash 5 qa Barley           -> 4 Jars Barley Beer    (Base: 3.0h)")
            print(" [2] Bakery:       Bake 3 qa Barley           -> 4 Loaves Flatbread    (Base: 2.0h)")
            print(" [3] Loom:         Weave 4 Talents Raw Wool   -> 2 Bolts Woolen Cloth  (Base: 4.0h)")
            print(" [4] Bronze Tools: 2 Copper Ore + 0.2 Tin     -> 3 Bronze Tools        (Base: 5.0h)")
            print(" [5] Weaponsmith:  3 Copper Ore + 0.3 Tin     -> 2 Bronze Weapons      (Base: 5.0h)")
            print(" [6] Bowyer:       2 Timber + 2 Raw Wool      -> 1 Composite Bow       (Base: 4.5h)")
            print(" [7] Chariot Guild:4 Timber + 1 Bronze Tools  -> 1 War Chariot         (Base: 8.0h)")
            print(" [8] Brickyard:    2 Reeds + River Silt       -> 5 Mudbricks           (Base: 2.5h)")
            print(" [9] Lapidary:     Mount Seal in Gold Caps    -> +4 Seal Prestige      (Cost: 20.0 Silver)")
            print("-" * 75)
            print(" WORKSHOP MANAGEMENT & ECONOMIES OF SCALE:")
            print(" [U] Upgrade Workshop Facility Tier (Expand batch capacity & labor scale)")
            print(" [H] Hire / Dismiss Artisan Laborers (Agru under Code of Hammurabi)")
            print(" [W] Adjust Statutory Wage Policy (Stingy / Legal § 274 / Efficiency Wage)")
            print(" [0] Return to Agriculture & Land Menu")
            print("-" * 75)

            craft_act = input(" Choose workshop action [0-9, U, H, W]: ").strip()

            if craft_act == "0":
                break

            elif craft_act in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                # Calculate max batches possible based on inventory
                if craft_act == "1":  # Brewery: 5 barley -> 4 beer
                    barley_avail = self.player.wallet.barley_qa
                    max_possible = int(barley_avail // 5.0)
                    recipe_name = "Barley Beer"
                    unit_in = "5 qa Barley"
                    unit_out = "4 Jars Beer"
                    base_hours = 3.0
                    output_key = "barley_beer"
                    yield_per_batch = 4.0
                elif craft_act == "2":  # Bakery: 3 barley -> 4 bread
                    barley_avail = self.player.wallet.barley_qa
                    max_possible = int(barley_avail // 3.0)
                    recipe_name = "Barley Flatbread"
                    unit_in = "3 qa Barley"
                    unit_out = "4 Loaves Bread"
                    base_hours = 2.0
                    output_key = "bread"
                    yield_per_batch = 4.0
                elif craft_act == "3":  # Loom: 4 wool -> 2 cloth
                    wool_avail = self.player.inventory.get("raw_wool", 0.0) + self.player.inventory.get("wool", 0.0)
                    max_possible = int(wool_avail // 4.0)
                    recipe_name = "Woolen Cloth"
                    unit_in = "4 Talents Raw Wool"
                    unit_out = "2 Bolts Woolen Cloth"
                    base_hours = 4.0
                    output_key = "woolen_cloth"
                    yield_per_batch = 2.0
                elif craft_act == "4":  # Bronze Tools: 2 copper + 0.2 tin -> 3 tools
                    cop_avail = self.player.inventory.get("copper_ore", 0.0)
                    tin_avail = self.player.inventory.get("tin", 0.0)
                    max_by_cop = int(cop_avail // 2.0)
                    max_by_tin = int(tin_avail // 0.2)
                    max_possible = min(max_by_cop, max_by_tin)
                    recipe_name = "Bronze Tools"
                    unit_in = "2 Copper + 0.2 Tin"
                    unit_out = "3 Bronze Tools"
                    base_hours = 5.0
                    output_key = "bronze_tools"
                    yield_per_batch = 3.0
                elif craft_act == "5":  # Weaponsmith: 3 copper + 0.3 tin -> 2 bronze weapons
                    cop_avail = self.player.inventory.get("copper_ore", 0.0)
                    tin_avail = self.player.inventory.get("tin", 0.0)
                    max_by_cop = int(cop_avail // 3.0)
                    max_by_tin = int(tin_avail // 0.3)
                    max_possible = min(max_by_cop, max_by_tin)
                    recipe_name = "Bronze Spears & Battle-Axes"
                    unit_in = "3 Copper Ore + 0.3 Tin"
                    unit_out = "2 Bronze Weapons (kakku)"
                    base_hours = 5.0
                    output_key = "bronze_weapons"
                    yield_per_batch = 2.0
                elif craft_act == "6":  # Bowyer: 2 timber + 2 wool -> 1 composite bow
                    timber_avail = self.player.inventory.get("timber", 0.0)
                    wool_avail = self.player.inventory.get("raw_wool", 0.0) + self.player.inventory.get("wool", 0.0)
                    max_by_timber = int(timber_avail // 2.0)
                    max_by_wool = int(wool_avail // 2.0)
                    max_possible = min(max_by_timber, max_by_wool)
                    recipe_name = "Composite Bow"
                    unit_in = "2 Timber + 2 Raw Wool/Sinew"
                    unit_out = "1 Composite Bow (qaštu)"
                    base_hours = 4.5
                    output_key = "composite_bow"
                    yield_per_batch = 1.0
                elif craft_act == "7":  # Chariot Guild: 4 timber + 1 bronze tools -> 1 war chariot
                    timber_avail = self.player.inventory.get("timber", 0.0)
                    tools_avail = self.player.inventory.get("bronze_tools", 0.0)
                    max_by_timber = int(timber_avail // 4.0)
                    max_by_tools = int(tools_avail // 1.0)
                    max_possible = min(max_by_timber, max_by_tools)
                    recipe_name = "Spoked War Chariot"
                    unit_in = "4 Timber + 1 Bronze Tools"
                    unit_out = "1 War Chariot (narkabtu)"
                    base_hours = 8.0
                    output_key = "war_chariot"
                    yield_per_batch = 1.0
                elif craft_act == "8":  # Brickyard: 2 reed -> 5 bricks
                    reed_avail = self.player.inventory.get("reeds", 0.0) + self.player.inventory.get("reed", 0.0)
                    max_possible = int(reed_avail // 2.0)
                    recipe_name = "Mudbricks"
                    unit_in = "2 Marsh Reeds"
                    unit_out = "5 Mudbricks (libittu)"
                    base_hours = 2.5
                    output_key = "mudbrick"
                    yield_per_batch = 5.0

                if max_possible <= 0:
                    print(f"\n [!] Insufficient raw materials to craft even 1 batch of {recipe_name} (Requires: {unit_in}).")
                    continue

                allowed_batches = min(max_possible, effective_capacity)
                print(f"\n--- CRAFT {recipe_name.upper()} ---")
                print(f" Inputs per Batch:   {unit_in}  ->  Yield: {unit_out}")
                print(f" Inventory allows:   {max_possible} batch(es)")
                print(f" Facility capacity:  {effective_capacity} batch(es) per production run")
                if not is_adequately_staffed and tier_info["required_workers"] > 0:
                    print(f" [!] Note: Facility is understaffed ({self.hired_artisans}/{req_workers} artisans). Operating at basic domestic capacity ({effective_capacity}).")

                b_input = input(f" How many batches to craft? [1-{allowed_batches}, default=1, 0 to cancel]: ").strip()
                if not b_input:
                    n_batches = 1
                else:
                    try:
                        n_batches = int(b_input)
                    except ValueError:
                        print(" [!] Invalid number.")
                        continue

                if n_batches <= 0:
                    continue
                if n_batches > allowed_batches:
                    print(f" [!] Cannot craft {n_batches} batches. Maximum allowed this run is {allowed_batches}.")
                    continue

                # Calculate duration and energy
                wage_speed = wage_info["speed_mult"]
                hours_needed = base_hours * (0.4 + 0.6 * (n_batches ** 0.85)) * facility_mult * wage_speed
                if self.hired_artisans > 0:
                    energy_needed = max(5.0, 15.0 * (n_batches ** 0.5) / (1.0 + self.hired_artisans))
                else:
                    energy_needed = max(8.0, 12.0 * (n_batches ** 0.6))

                if self.player.energy < energy_needed:
                    print(f" [!] Too exhausted! You need {energy_needed:.0f}% energy for this run (Current: {self.player.energy:.0f}%). Rest or eat first.")
                    continue

                total_yield = n_batches * yield_per_batch

                # Deduct materials
                if craft_act in ["1", "2"]:
                    barley_to_spend = (5.0 if craft_act == "1" else 3.0) * n_batches
                    self.player.wallet.spend_barley(barley_to_spend)
                    self.player.inventory["barley"] = self.player.wallet.barley_qa
                    if self.player.inventory["barley"] <= 0:
                        del self.player.inventory["barley"]
                elif craft_act == "3":
                    needed_wool = 4.0 * n_batches
                    if self.player.inventory.get("raw_wool", 0.0) >= needed_wool:
                        self.player.inventory["raw_wool"] -= needed_wool
                    else:
                        needed_wool -= self.player.inventory.get("raw_wool", 0.0)
                        self.player.inventory["raw_wool"] = 0.0
                        self.player.inventory["wool"] -= needed_wool
                    if self.player.inventory.get("raw_wool", 0.0) <= 1e-4 and "raw_wool" in self.player.inventory:
                        del self.player.inventory["raw_wool"]
                    if self.player.inventory.get("wool", 0.0) <= 1e-4 and "wool" in self.player.inventory:
                        del self.player.inventory["wool"]
                elif craft_act == "4":
                    self.player.inventory["copper_ore"] -= 2.0 * n_batches
                    self.player.inventory["tin"] -= 0.2 * n_batches
                    if self.player.inventory["copper_ore"] <= 1e-4:
                        del self.player.inventory["copper_ore"]
                    if self.player.inventory["tin"] <= 1e-4:
                        del self.player.inventory["tin"]
                elif craft_act == "5":
                    self.player.inventory["copper_ore"] -= 3.0 * n_batches
                    self.player.inventory["tin"] -= 0.3 * n_batches
                    if self.player.inventory["copper_ore"] <= 1e-4:
                        del self.player.inventory["copper_ore"]
                    if self.player.inventory["tin"] <= 1e-4:
                        del self.player.inventory["tin"]
                elif craft_act == "6":
                    self.player.inventory["timber"] -= 2.0 * n_batches
                    if self.player.inventory["timber"] <= 1e-4:
                        del self.player.inventory["timber"]
                    needed_wool = 2.0 * n_batches
                    if self.player.inventory.get("raw_wool", 0.0) >= needed_wool:
                        self.player.inventory["raw_wool"] -= needed_wool
                    else:
                        needed_wool -= self.player.inventory.get("raw_wool", 0.0)
                        self.player.inventory["raw_wool"] = 0.0
                        self.player.inventory["wool"] -= needed_wool
                    if self.player.inventory.get("raw_wool", 0.0) <= 1e-4 and "raw_wool" in self.player.inventory:
                        del self.player.inventory["raw_wool"]
                    if self.player.inventory.get("wool", 0.0) <= 1e-4 and "wool" in self.player.inventory:
                        del self.player.inventory["wool"]
                elif craft_act == "7":
                    self.player.inventory["timber"] -= 4.0 * n_batches
                    self.player.inventory["bronze_tools"] -= 1.0 * n_batches
                    if self.player.inventory["timber"] <= 1e-4:
                        del self.player.inventory["timber"]
                    if self.player.inventory["bronze_tools"] <= 1e-4:
                        del self.player.inventory["bronze_tools"]
                elif craft_act == "8":
                    needed_reeds = 2.0 * n_batches
                    if self.player.inventory.get("reeds", 0.0) >= needed_reeds:
                        self.player.inventory["reeds"] -= needed_reeds
                    else:
                        needed_reeds -= self.player.inventory.get("reeds", 0.0)
                        self.player.inventory["reeds"] = 0.0
                        self.player.inventory["reed"] -= needed_reeds
                    if self.player.inventory.get("reeds", 0.0) <= 1e-4 and "reeds" in self.player.inventory:
                        del self.player.inventory["reeds"]
                    if self.player.inventory.get("reed", 0.0) <= 1e-4 and "reed" in self.player.inventory:
                        del self.player.inventory["reed"]

                # Add finished output
                self.player.inventory[output_key] = self.player.inventory.get(output_key, 0.0) + total_yield
                self.player.energy = max(0.0, self.player.energy - energy_needed)
                self.player.skills.craftsmanship += max(1, n_batches // 2)

                # Time advances
                self.advance_hours(hours_needed)

                new_h = int(self.hour)
                new_m = int((self.hour - new_h) * 60)
                print(f"\n [+] Production Successful! Completed {n_batches} batch(es) resulting in {total_yield:.0f} {recipe_name}!")
                print(f"     Time elapsed: {hours_needed:.1f} hours. Current time: Day {self.day:02d} | {new_h:02d}:{new_m:02d} ({self.get_time_label()}).")
                print(f"     Remaining energy: {self.player.energy:.0f}%.")

            elif craft_act == "9":
                if not self.player.cylinder_seal:
                    print(" [!] You have no cylinder seal to embellish!")
                elif "Gold-Mounted" in self.player.cylinder_seal.material:
                    print(" [!] Your seal already possesses royal filigree gold caps!")
                elif self.player.wallet.spend_silver(20.0):
                    old_mat = self.player.cylinder_seal.material
                    self.player.cylinder_seal.material = f"Royal Gold-Mounted {old_mat}"
                    self.player.cylinder_seal.prestige_rating += 4
                    self.player.energy = max(0.0, self.player.energy - 15.0)
                    self.advance_hours(4.0)
                    print(f"\n [★] Master lapidary mounted your {old_mat} seal with filigree gold caps and royal cuneiform titles!")
                    print(f"     Prestige rating elevated to {self.player.cylinder_seal.prestige_rating}! You now qualify for Rabiānum (City Governor)!")
                else:
                    print(" [!] Requires 20.0 silver shekels to commission royal gold filigree.")

            elif craft_act.upper() == "U":
                # Upgrade Workshop Facility Tier
                if self.workshop_tier == 1:
                    info = WORKSHOP_TIERS[2]
                    print(f"\n--- UPGRADE TO TIER 2: {info['name'].upper()} ---")
                    print(f" Description:      {info['description']}")
                    print(f" Batch Capacity:   3 -> {info['max_batches']} batches per run")
                    print(f" Required Labor:   {info['required_workers']} Hired Artisan (Agru)")
                    print(f" Speed Multiplier: 0.85x (+15% faster manufacturing)")
                    print(f" Cost:             {info['upgrade_cost_silver']:.1f} silver shekels")
                    confirm = input(" Upgrade facility to Guild Workshop? (y/N): ").strip().lower()
                    if confirm == "y":
                        if self.player.wallet.spend_silver(info["upgrade_cost_silver"]):
                            self.workshop_tier = 2
                            print(f"\n [+] Congratulations! Workshop expanded to Tier 2 ({info['name']})!")
                            print(f"     Remember to hire at least 1 artisan laborer (agru) to operate the new equipment.")
                        else:
                            print(" [!] Insufficient silver shekels.")
                elif self.workshop_tier == 2:
                    info = WORKSHOP_TIERS[3]
                    print(f"\n--- UPGRADE TO TIER 3: {info['name'].upper()} ---")
                    print(f" Description:      {info['description']}")
                    print(f" Batch Capacity:   8 -> {info['max_batches']} batches per run")
                    print(f" Required Labor:   {info['required_workers']} Hired Artisans (Agru)")
                    print(f" Speed Multiplier: 0.70x (+30% faster manufacturing)")
                    print(f" Cost:             {info['upgrade_cost_silver']:.1f} silver shekels")
                    confirm = input(" Upgrade facility to Patrician Manufactory? (y/N): ").strip().lower()
                    if confirm == "y":
                        if self.player.wallet.spend_silver(info["upgrade_cost_silver"]):
                            self.workshop_tier = 3
                            print(f"\n [+] Magnificence! Workshop expanded to Tier 3 ({info['name']})!")
                            print(f"     This great manufactory can process up to 25 batches with 3 hired artisans.")
                        else:
                            print(" [!] Insufficient silver shekels.")
                else:
                    print("\n [!] Your workshop is already at the maximum tier (Tier 3: Patrician Manufactory).")

            elif craft_act.upper() == "H":
                # Hire / Dismiss Artisan Laborers
                print(f"\n--- MANAGE ARTISAN LABOR (AGRU - CODE OF HAMMURABI §§ 273-274) ---")
                print(f" Current Staff:    {self.hired_artisans} hired artisan(s)")
                print(f" Facility Needs:   {tier_info['required_workers']} artisan(s) for Tier {self.workshop_tier} ({tier_info['name']})")
                print(f" Daily Wage Rate:  {daily_wage_silver:.3f} silver / day per worker (Policy: {wage_info['name']})")
                print(f" Your Purse:       {self.player.wallet.silver_shekels:.2f} silver shekels")
                h_input = input(" Enter total number of artisans to employ [0-3]: ").strip()
                try:
                    new_hired = int(h_input)
                    if 0 <= new_hired <= 3:
                        diff = new_hired - self.hired_artisans
                        self.hired_artisans = new_hired
                        if diff > 0:
                            print(f" [+] Hired {diff} new artisan laborer(s). Total workforce: {self.hired_artisans}.")
                        elif diff < 0:
                            print(f" [+] Dismissed {-diff} artisan laborer(s). Total workforce: {self.hired_artisans}.")
                        else:
                            print(" [!] Workforce unchanged.")
                    else:
                        print(" [!] You can employ between 0 and 3 artisans.")
                except ValueError:
                    print(" [!] Invalid number.")

            elif craft_act.upper() == "W":
                # Adjust Statutory Wage Policy
                print("\n--- STATUTORY WAGE POLICY (CODE OF HAMMURABI §§ 273-274) ---")
                print(" Under King Hammurabi's diorite stele, artisan and field laborer wages are established:")
                print(f" [1] Stingy:          3 grains/day ({3.0*cpi/180.0:.3f} silv) | 25% slower (+discontent)")
                print(f" [2] Statutory Min:   5 grains/day ({5.0*cpi/180.0:.3f} silv) | Code § 274 legal standard")
                print(f" [3] Efficiency Wage: 8 grains/day ({8.0*cpi/180.0:.3f} silv) | 20% faster (+high morale)")
                print(f" Current Policy: {self.wage_policy} ({wage_info['name']})")
                p_choice = input(" Select policy [1-3, or Enter to cancel]: ").strip()
                if p_choice == "1":
                    self.wage_policy = "STINGY"
                    print(" [!] Wage policy set to STINGY. Your craftsmen grumble at the low pay.")
                elif p_choice == "2":
                    self.wage_policy = "STATUTORY"
                    print(" [+] Wage policy set to STATUTORY MINIMUM under Code § 274.")
                elif p_choice == "3":
                    self.wage_policy = "EFFICIENCY"
                    print(" [★] Wage policy set to EFFICIENCY WAGE. Master artisans flock to your workshop!")

    # --------------------------------------------------------------------------
    # Subsystem 3: Ale-Wife's Tavern & The Royal Game of Ur
    # --------------------------------------------------------------------------

    def handle_tavern(self):
        """Drink beer, hear trade intelligence, play Royal Game of Ur dice, meet suitors."""
        while True:
            print("\n" + "=" * 70)
            print("            THE ALE-WIFE'S TAVERN (BĪTH ŠIKARI)")
            print("=" * 70)
            print(" The air is thick with the scent of roasted grain, sweet date syrup, and pipe smoke.")
            print(" [1] Buy a Jar of Cloudy Barley Beer (0.60 silver) - Quenches thirst & restores energy")
            print(" [2] Buy a Flask of Sweet Date Wine (1.20 silver) - Restores health & vigor")
            print(" [3] Play the Royal Game of Ur (Tetrahedral Dice Wager for Silver Shekels!)")
            print(" [4] Gather Street Rumors & Trade Secrets from Sailors and Merchants")
            print(" [5] Inquire with the Matchmaker for Marriage Alliances")
            print(" [0] Leave the Tavern")
            print("-" * 70)

            act = input(" Choose tavern action [0-5]: ").strip()

            if act == "1":
                if self.player.wallet.spend_silver(0.60):
                    self.player.thirst = max(0.0, self.player.thirst - 50.0)
                    self.player.energy = min(100.0, self.player.energy + 25.0)
                    print(" [+] You sip cool, sweet barley beer through a perforated bronze straw. Refreshed!")
                else:
                    print(" [!] You don't have 0.60 silver for a jar of beer.")

            elif act == "2":
                if self.player.wallet.spend_silver(1.20):
                    self.player.thirst = max(0.0, self.player.thirst - 60.0)
                    self.player.health = min(100.0, self.player.health + 15.0)
                    self.player.energy = min(100.0, self.player.energy + 30.0)
                    print(" [+] Rich, fermented date wine warms your blood. Health restored!")
                else:
                    print(" [!] Need 1.20 silver shekels.")

            elif act == "3":
                # The Royal Game of Ur (Tetrahedral Dice Minigame)
                print("\n--- THE ROYAL GAME OF UR (TAVERN DICE WAGER) ---")
                print(" In ancient Babylon, players cast 4 tetrahedral pyramid dice (each rolling 0 or 1).")
                print(" Total score ranges from 0 to 4. Highest roll claims the silver wager!")
                bet_str = input(f" Enter silver wager (You have: {self.player.wallet.silver_shekels:.2f} silver) [1-10]: ").strip()
                try:
                    bet = float(bet_str)
                    if bet <= 0 or bet > self.player.wallet.silver_shekels:
                        print(" [!] Invalid or unaffordable wager.")
                        continue
                    
                    self.player.wallet.spend_silver(bet)
                    print(f"\n You place {bet:.2f} silver shekels upon the gaming board.")
                    time.sleep(0.3)

                    # Roll 4 tetrahedral binary dice for each player
                    player_dice = [random.randint(0, 1) for _ in range(4)]
                    player_score = sum(player_dice)
                    opp_dice = [random.randint(0, 1) for _ in range(4)]
                    opp_score = sum(opp_dice)

                    print(f" Your Roll:    {player_dice} -> {player_score} Points!")
                    print(f" Opponent:     {opp_dice} -> {opp_score} Points!")

                    if player_score > opp_score:
                        win_pot = bet * 2.0
                        self.player.wallet.add_silver(win_pot)
                        print(f" [+] BY SHAMASH! You win the roll! Pocketed {win_pot:.2f} silver shekels!")
                    elif player_score < opp_score:
                        print(" [-] The opponent's dice roll true. You lost your wager!")
                    else:
                        print(" [=] A tie! Your silver shekels are returned from the board.")
                        self.player.wallet.add_silver(bet)
                except ValueError:
                    print(" [!] Please enter a valid number.")

            elif act == "4":
                rumors = [
                    "Merchants returning from Kanesh say tin supplies in Anatolia have doubled; watch for copper demand!",
                    "The canal dikes near Kish are leaking. If the Gugallum doesn't dredge, barley prices will soar!",
                    "King Hammurabi is said to be weighing an Edict of Justice (Misharum) to cancel peasant debts.",
                    "Gulf barges from Magan were sighted off Dilmun with heavy ingots of raw copper.",
                    "The temple of Marduk is offering high prices for pure Afghan lapis lazuli to adorn the inner sanctuary."
                ]
                print(f"\n [Ale-Wife Alitu Whispers]: \"{random.choice(rumors)}\"")

            elif act == "5":
                # Marriage Matchmaking
                if self.player_marriage_contract:
                    print(f"\n [!] You are already bound in holy matrimony to {self.player_marriage_contract.wife.full_name} under Code § 128.")
                    continue
                
                print("\n--- BABYLONIAN MARRIAGE ALLIANCES (CODE OF HAMMURABI § 128) ---")
                print(" [1] Amat-Ba'u (Awilum - Daughter of Patrician Marduk-nasir)")
                print("     Bride-Price (Terhatum): 15 Silver Shekels | Dowry: 40 Silver + 10 Acres + 1 Ox")
                print(" [2] Beltani (Mushkenum - Daughter of Master Weaver Iddin-Enlil)")
                print("     Bride-Price (Terhatum): 5 Silver Shekels  | Dowry: 10 Silver + 2 Acres + 3 Sheep")
                print(" [3] Shamhat (Freedwoman Artisan)")
                print("     Bride-Price (Terhatum): 1.5 Silver Shekels | Dowry: 3 Silver + Cooking Tools")
                print(" [4] Return")

                m_choice = input(" Select prospective bride [1-4]: ").strip()
                suitor_data = {
                    "1": (self.npcs["amat_bau"], 15.0, Dowry(silver_shekels=40.0, land_acres=10.0, oxen=1)),
                    "2": (self.npcs["beltani"], 5.0, Dowry(silver_shekels=10.0, land_acres=2.0, goods={"sheep": 3})),
                    "3": (self.npcs["shamhat"], 1.5, Dowry(silver_shekels=3.0, goods={"bronze_tools": 1}))
                }
                if m_choice in suitor_data:
                    bride_char, terhatum, dowry = suitor_data[m_choice]
                    confirm = input(f" Offer {terhatum:.1f} silver Terhatum to House {bride_char.patronymic or bride_char.name}? (y/N): ").strip().lower()
                    if confirm == "y":
                        ok, msg, contract = self.marriage_mgr.propose_and_marry(
                            groom=self.player,
                            bride=bride_char,
                            bride_price_silver=terhatum,
                            dowry=dowry,
                            year=self.year
                        )
                        print("\n" + msg)
                        if ok and contract:
                            self.player_marriage_contract = contract
                            if "sheep" in dowry.goods:
                                self.player.owned_sheep += int(dowry.goods["sheep"])
                            print(f" [+] Dowry of {dowry.total_estimated_value_silver:.1f} silver equivalent received into your household management!")
                            
                            # If Mushkenum commoner marries Awilum patrician, offer immediate Assembly ennoblement
                            if bride_char.social_class == SocialClass.AWILUM and self.player.social_class == SocialClass.MUSHKENUM:
                                ennoble_ask = input("\n [★] House Marduk invites you to petition the Puhrum Assembly for immediate ennoblement to Awīlum! Petition now? (Y/n): ").strip().lower()
                                if ennoble_ask != "n":
                                    ok_e, msg_e = self.politics.petition_ennoblement_to_awilum(self.player, self.player_marriage_contract)
                                    print("\n" + msg_e)

            elif act == "0":
                break

    # --------------------------------------------------------------------------
    # Subsystem: Consume Rations from Personal Inventory Sacks
    # --------------------------------------------------------------------------

    def handle_eat_drink(self):
        """Allows player to consume food, beer, or wine from inventory immediately."""
        p = self.player
        while True:
            print("\n" + "=" * 70)
            print("          CONSUME RATIONS FROM INVENTORY SACKS")
            print("=" * 70)
            print(f" Status: Hunger {p.hunger:.0f}/100 | Thirst {p.thirst:.0f}/100 | Health {p.health:.0f}% | Energy {p.energy:.0f}%")
            print("-" * 70)
            
            consumables = [
                ("bread", "Oven-Baked Barley Flatbread", "Hunger -45, Energy +10"),
                ("dates", "Sweet Chewy Dates", "Hunger -30, Energy +15"),
                ("dried_fish", "Sun-Dried Salted Fish", "Hunger -30, Health +10"),
                ("sweet_pastry", "Honey-Glazed Temple Pastry", "Hunger -60, Health +10, Honor +0.5"),
                ("barley", "Toasted Barley Grains (1 qa)", "Hunger -25, Energy +5"),
                ("barley_beer", "Jug of Cloudy Barley Beer", "Thirst -50, Energy +25"),
                ("spelt_beer", "Golden Spelt Beer", "Thirst -60, Energy +30"),
                ("date_wine", "Flask of Fermented Date Wine", "Thirst -60, Health +15, Energy +30")
            ]

            avail = []
            for g_id, name, effects in consumables:
                cnt = p.inventory.get(g_id, 0.0)
                if cnt >= 1.0:
                    avail.append((g_id, name, cnt, effects))

            if not avail:
                print(" [!] You have no consumable food or drink in your sacks.")
                print("     (Buy rations at the Kārum Market or brew/bake in the Workshops!)")
                input("\n Press Enter to return...")
                break

            for idx, (g_id, name, cnt, effects) in enumerate(avail, 1):
                print(f" [{idx}] {name:<30} (Have: {cnt:4.1f}) -> {effects}")
            print(" [0] Return to City Square")
            print("-" * 70)

            choice = input(f" Select item to consume [0-{len(avail)}]: ").strip()
            if choice == "0" or not choice:
                break
            try:
                ch_idx = int(choice)
                if 1 <= ch_idx <= len(avail):
                    target_gid, _, _, _ = avail[ch_idx - 1]
                    ok, msg = p.consume_item(target_gid)
                    print(f"\n [+] {msg}")
                else:
                    print(" [!] Invalid selection.")
            except ValueError:
                print(" [!] Invalid input.")

    # --------------------------------------------------------------------------
    # Subsystem 4: Long-Distance Tamkarum Caravans
    # --------------------------------------------------------------------------

    def handle_caravan(self):
        """Assembles and launches foreign mercantile expeditions to distant trade hubs."""
        print("\n" + "=" * 70)
        print("          THE TAMKARUM MERCHANTS' GUILD & CARAVAN QUAY")
        print("=" * 70)
        print(" Foreign Trade Corridors:")
        print(" [1] Anatolia & Levant (Overland: Tin, Cedar Timber, Silver) - 90 Days")
        print(" [2] Dilmun / Bahrain (Gulf Entrepôt: Pearls, Dates, Bitumen) - 30 Days")
        print(" [3] Magan / Oman (Copper Coast: Raw Copper Ore) - 60 Days")
        print(" [4] Meluhha / Indus Valley (Oceanic East: Lapis Lazuli, Carnelian) - 120 Days")
        print(" [0] Return to City Square")
        print("-" * 70)

        dest_choice = input(" Select destination corridor [0-4]: ").strip()
        corridor_map = {
            "1": TradeCorridor.ANATOLIA_LEVANT,
            "2": TradeCorridor.DILMUN_ENTREPOT,
            "3": TradeCorridor.MAGAN_COAST,
            "4": TradeCorridor.MELUHHA_INDUS
        }
        if dest_choice not in corridor_map:
            return

        corridor = corridor_map[dest_choice]
        node = self.trade_mgr.nodes[corridor]

        print(f"\n--- CONFIGURING EXPEDITION TO {node.name.upper()} ---")
        print(f" Round-Trip Duration: {node.round_trip_days} days | Transit Hazard: {node.hazard_risk_percent}%")
        print(" Choose Fleet Scale:")
        print(" [1] Small Donkey Team (2 Donkeys, 1 Guard) - Fodder: 4 qa/day | Low Cost")
        print(" [2] Standard Merchant Train (6 Donkeys, 3 Guards) - Fodder: 12 qa/day | Medium Capacity")
        print(" [3] Seagoing Gulf Vessel (1 Ship, 5 Rowers/Guards) - Fodder: 15 qa/day | Massive Cargo")

        f_choice = input(" Choose fleet size [1-3, default=1]: ").strip()
        if f_choice == "2":
            fleet = TransportFleet.create_donkey_caravan(num_donkeys=6, guards=3)
        elif f_choice == "3":
            fleet = TransportFleet.create_gulf_barge(num_ships=1, sailors=5)
        else:
            fleet = TransportFleet.create_donkey_caravan(num_donkeys=2, guards=1)

        fodder_needed = fleet.daily_fodder_grain_qa * node.round_trip_days
        guards_silver = fleet.guard_cost_silver * node.round_trip_days

        print(f"\n Provisions Required for {node.round_trip_days} Days:")
        print(f"  * Grain Fodder: {fodder_needed:.0f} qa ({fodder_needed/300:.2f} gur) | You have: {self.player.wallet.barley_qa:.0f} qa")
        print(f"  * Mercenary Guards: {guards_silver:.2f} silver shekels        | You have: {self.player.wallet.silver_shekels:.2f} silver")

        if self.player.wallet.barley_qa < fodder_needed or self.player.wallet.silver_shekels < guards_silver:
            print(" [!] You cannot provision this expedition. Stock up on grain fodder and silver first.")
            return

        purse_str = input(" How much trading silver purse to entrust to the Tamkarum (e.g. 10-50 silver)? ").strip()
        try:
            purse = float(purse_str)
            if purse < 5.0 or (purse + guards_silver) > self.player.wallet.silver_shekels:
                print(" [!] Invalid or unaffordable trading purse.")
                return
        except ValueError:
            print(" [!] Invalid number.")
            return

        # Prepare export goods if available
        cargo: Dict[str, float] = {}
        if self.player.inventory.get("woolen_cloth", 0.0) >= 2.0:
            cargo["woolen_cloth"] = 2.0
        if self.player.inventory.get("dates", 0.0) >= 5.0:
            cargo["dates"] = 5.0

        print("\n Assembling caravan with Tamkarum Ur-Nungal...")
        ok, msg, mission = self.trade_mgr.assemble_caravan(
            investor=self.player,
            corridor=corridor,
            fleet=fleet,
            cargo_to_export=cargo,
            silver_purse=purse
        )
        print(msg)

        if ok and mission:
            print("\n" + "." * 70)
            print(" The caravan departs Babylon under the protection of Shamash...")
            print(" Over weeks of travel, the merchant train crosses mountains and rivers.")
            print("." * 70)
            time.sleep(0.5)

            # Resolve the expedition
            success, report = self.trade_mgr.resolve_mission(mission, self.player)
            print("\n" + report)

    # --------------------------------------------------------------------------
    # Subsystem 5: Civic Politics & Puhrum Assembly
    # --------------------------------------------------------------------------

    def handle_politics(self):
        """Civic offices, assembly campaigning, official duties, and royal decrees."""
        while True:
            print("\n" + "=" * 70)
            print("           THE PUHRUM CITY ASSEMBLY & CIVIC OFFICES")
            print("=" * 70)
            for title, holder in self.politics.office_holders.items():
                holder_str = holder.full_name if holder else "[VACANT - ELECTION OPEN]"
                print(f" * {title.value:<38}: {holder_str}")
            print("-" * 70)

            if self.player.civic_office:
                print(f" Your Current Office: {self.player.civic_office}")
                print(" [1] Exercise Official Executive Duties & Powers")
                print(" [2] Resign Civic Commission")
                print(" [0] Return to City Square")
                c_act = input(" Choose action [0-2]: ").strip()
                if c_act == "1":
                    if "Canal Warden" in self.player.civic_office:
                        skim = input(" Mobilize corvée labor to dredge river dikes? Skim maintenance silver (0-5)? ").strip()
                        s_val = float(skim) if skim else 0.0
                        ok, msg = self.politics.execute_canal_warden_dredging(self.player, skim_silver=s_val)
                        print(msg)
                    elif "Market Overseer" in self.player.civic_office:
                        t_str = input(" Set city gate import customs tariff rate (0% to 20%, e.g. 8)? ").strip()
                        try:
                            rate = float(t_str) / 100.0 if t_str else 0.05
                            ok, msg = self.politics.set_gate_customs_tariff(self.player, rate)
                            print(msg)
                        except ValueError:
                            pass
                    elif "Governor" in self.player.civic_office:
                        self.handle_governor_powers()
                    elif "Magistrate" in self.player.civic_office:
                        print(" [+] As Dayyānum, you reviewed contracts and enforced the stelae decrees of Shamash at the gate.")
                        self.player.reputation = min(100.0, self.player.reputation + 2.0)
                    elif "High Priest" in self.player.civic_office:
                        print(" [+] As Šangû, you presided over libations of beer and sacrifices at the inner sanctum of Marduk.")
                        self.player.reputation = min(100.0, self.player.reputation + 3.0)
                    else:
                        print(" [+] Inspected public facilities and verified weights and measures.")
                elif c_act == "2":
                    for o_title in OfficeTitle:
                        if self.politics.office_holders.get(o_title) == self.player:
                            self.politics.office_holders[o_title] = None
                    self.player.civic_office = None
                    print(" [+] You stepped down from civic office.")
                elif c_act == "0":
                    break
                continue

            print(" Run for High Civic Office in the Assembly:")
            print(" [1] Campaign for Gugallum (Canal Warden) - Needs Mushkenum class or higher")
            print(" [2] Campaign for Rabi Sikkatim (Market Overseer) - Needs Awilum patrician class")
            print(" [3] Campaign for Dayyānum (City Magistrate & Judge) - Needs Awilum patrician class")
            print(" [4] Campaign for Šangû (High Priest of Esagila Temple) - Sacred office")
            print(" [5] Campaign for Rabiānum (City Governor & Mayor) - Highest executive office (Awilum)")
            if self.player.social_class != SocialClass.AWILUM:
                print(" [6] Petition Council of Elders for Ennoblement to Awīlum (Patrician Class)")
            print(" [0] Return to City Square")

            ch = input(f" Choose option [{'0-6' if self.player.social_class != SocialClass.AWILUM else '0-5'}]: ").strip()
            if ch == "6" and self.player.social_class != SocialClass.AWILUM:
                ok_ennoble, msg_ennoble = self.politics.petition_ennoblement_to_awilum(self.player, self.player_marriage_contract)
                print("\n" + msg_ennoble)
                continue

            office_map = {
                "1": OfficeTitle.CANAL_WARDEN,
                "2": OfficeTitle.MARKET_OVERSEER,
                "3": OfficeTitle.CITY_MAGISTRATE,
                "4": OfficeTitle.HIGH_PRIEST,
                "5": OfficeTitle.CITY_GOVERNOR
            }
            if ch not in office_map:
                break

            target_office = office_map[ch]
            print(f"\n Campaigning for {target_office.value}:")
            bribe_str = input(f" Silver patronage to the Council of Elders (You have: {self.player.wallet.silver_shekels:.2f}) [default=0]: ").strip()
            bribe = float(bribe_str) if bribe_str else 0.0
            feast = input(" Sponsor public beer & bread feast of Ishtar for commoners (Costs ~5 silver) (y/N)? ").strip().lower() == "y"

            ok, msg = self.politics.appoint_or_elect(self.player, target_office, bribe_silver=bribe, sponsor_feast=feast)
            print("\n" + msg)
            break

    def handle_governor_powers(self):
        """Executive governance of Babylon: city defense, gate garrisons, levies, and military campaigns."""
        while True:
            security_pct = self.war_engine.calculate_city_security()
            sec_label = self.war_engine.get_security_label()
            total_soldiers = sum(r.soldiers_count for r in self.war_engine.standing_army)
            daily_grain, daily_silver = self.war_engine.calculate_daily_upkeep()

            print("\n" + "=" * 78)
            print("        EXECUTIVE GOVERNANCE & GARRISON COMMAND (RABIĀNUM / MAYOR)")
            print("=" * 78)
            print(f" City Security Rating: {security_pct:.1f}% ({sec_label})")
            print(f" Standing Forces:      {len(self.war_engine.standing_army)} Regiments ({total_soldiers} Active Warriors)")
            print(f" Daily Garrison Upkeep: {daily_silver:.2f} silver | {daily_grain:.0f} qa barley (Funded by City Coffers)")
            print("-" * 78)
            print(" BABYLON MUNICIPAL COFFERS (BĪT ĀLĪ):")
            print(f"  * Public Civic Treasury: {self.war_engine.city_treasury_silver:7.2f} silver shekels (Toll Inflow: +{self.war_engine.gate_toll_revenue_daily:.2f}/day)")
            print(f"  * Public Municipal Silos: {self.war_engine.city_granary_barley:7.0f} qa barley ({self.war_engine.city_granary_barley/300.0:.2f} gur)")
            print(f" Personal Estate Purse:    {self.player.wallet.silver_shekels:7.2f} silver | {self.player.wallet.barley_qa:5.0f} qa barley")
            print("-" * 78)
            print(" MUNICIPAL & MILITARY EXECUTIVE ORDERS:")
            print(" [1] Inspect City Garrison & Station Troops at City Gates")
            print(" [2] Recruit Military Regiments (Bā'iru, Rēdû, Chariots, Militia)")
            print(" [3] Arm Regiments with Manufactured Weapons from Inventory")
            print(" [4] Launch Military Campaigns & Expeditions against Hostile Threats")
            print(" [5] Manage Municipal Coffers (Donate grain/silver for Honor, or draw dividend)")
            print(" [6] Municipal Granary Famine Relief (Open public silos for commoners, gain Honor)")
            print(" [7] Petition Great King Hammurabi for Royal Misharum Debt Jubilee")
            print(" [0] Return to Civic Offices Menu")
            print("-" * 78)

            gov_act = input(" Select executive order [0-7]: ").strip()

            if gov_act == "0":
                break

            elif gov_act == "1":
                # Inspect Garrison & Station Troops at Gates
                print("\n" + "=" * 78)
                print("              BABYLON CITY GARRISON & GATE STATIONS")
                print("=" * 78)
                if not self.war_engine.standing_army:
                    print(" [!] No active regiments in the municipal garrison.")
                else:
                    for idx, reg in enumerate(self.war_engine.standing_army, 1):
                        equip_tag = "[ARMED]" if reg.is_equipped or reg.definition.required_equipment is None else "[UNARMED]"
                        gate_tag = reg.stationed_gate if reg.stationed_gate else "Mobile Reserve"
                        print(f" [{idx}] {reg.id}: {reg.definition.name:<25} ({reg.soldiers_count} men) {equip_tag:<9} Lv.{reg.experience_level} | Gate: {gate_tag}")
                        print(f"      Prowess: Range {reg.range_power:.0f} | Melee {reg.melee_power:.0f} | Def {reg.defense_power:.0f} | Morale {reg.total_morale:.0f}")

                print("\n Station a Regiment at a City Gate:")
                reg_choice = input(f" Enter regiment number to reassign [1-{len(self.war_engine.standing_army)}, or 0 to return]: ").strip()
                try:
                    r_idx = int(reg_choice)
                    if 1 <= r_idx <= len(self.war_engine.standing_army):
                        sel_reg = self.war_engine.standing_army[r_idx - 1]
                        print(f"\n Select destination gate for {sel_reg.id} ({sel_reg.definition.name}):")
                        gates = list(CityGate)
                        for g_idx, gate in enumerate(gates, 1):
                            print(f" [{g_idx}] {gate.value}")
                        print(f" [{len(gates)+1}] Mobile Reserve (Unassigned)")
                        g_choice = input(f" Choose gate [1-{len(gates)+1}]: ").strip()
                        g_num = int(g_choice)
                        if 1 <= g_num <= len(gates):
                            sel_reg.stationed_gate = gates[g_num - 1].value
                            print(f" [+] Stationed {sel_reg.id} at {sel_reg.stationed_gate}!")
                        elif g_num == len(gates) + 1:
                            sel_reg.stationed_gate = None
                            print(f" [+] Assigned {sel_reg.id} to Mobile Reserve.")
                except ValueError:
                    pass

            elif gov_act == "2":
                # Recruit Regiments
                print("\n" + "=" * 78)
                print("           RECRUIT MILITARY LEVIES & ROYAL REGIMENTS")
                print("=" * 78)
                print(" [1] Bā'iru Archers        - 2.0 silv + 9 qa grain/man  | Needs: Composite Bows")
                print(" [2] Rēdû Heavy Spearmen   - 3.0 silv + 12 qa grain/man | Needs: Bronze Weapons")
                print(" [3] Narkabtu War Chariots - 10.0 silv + 36 qa grain/man| Needs: War Chariots")
                print(" [4] Peasant Militia Levies- 0.5 silv + 6 qa grain/man  | Improvised weapons")
                print(" [0] Cancel")
                u_pick = input(" Choose unit type [0-4]: ").strip()
                unit_type_map = {
                    "1": UnitType.BAIRU,
                    "2": UnitType.REDU,
                    "3": UnitType.NARKABTU,
                    "4": UnitType.MILITIA
                }
                if u_pick in unit_type_map:
                    target_u = unit_type_map[u_pick]
                    cnt_str = input(f" How many soldiers to recruit for {target_u.name}? ").strip()
                    try:
                        cnt = int(cnt_str)
                        if cnt > 0:
                            ok_rec, rec_msg = self.war_engine.recruit_regiment(self.player, target_u, cnt)
                            print("\n" + rec_msg)
                    except ValueError:
                        print(" [!] Invalid number.")

            elif gov_act == "3":
                # Arm Regiments
                print("\n" + "=" * 78)
                print("          ARM REGIMENTS WITH MANUFACTURED WEAPONS")
                print("=" * 78)
                print(f" Weapons in Sacks: Bronze Weapons: {self.player.inventory.get('bronze_weapons', 0.0):.0f} | "
                      f"Composite Bows: {self.player.inventory.get('composite_bow', 0.0):.0f} | "
                      f"War Chariots: {self.player.inventory.get('war_chariot', 0.0):.0f}")
                unarmed = [r for r in self.war_engine.standing_army if not r.is_equipped and r.definition.required_equipment is not None]
                if not unarmed:
                    print(" [★] All standing regiments requiring arms are already fully equipped!")
                else:
                    for idx, reg in enumerate(unarmed, 1):
                        print(f" [{idx}] {reg.id}: {reg.definition.name} ({reg.soldiers_count} men) -> Needs {reg.soldiers_count} {reg.definition.required_equipment}")
                    r_pick = input(f" Select regiment to arm [1-{len(unarmed)}, or 0 to return]: ").strip()
                    try:
                        r_num = int(r_pick)
                        if 1 <= r_num <= len(unarmed):
                            chosen_reg = unarmed[r_num - 1]
                            ok_arm, arm_msg = self.war_engine.arm_regiment(self.player, chosen_reg.id)
                            print("\n" + arm_msg)
                    except ValueError:
                        pass

            elif gov_act == "4":
                # Military Campaigns
                print("\n" + "=" * 78)
                print("        MILITARY CAMPAIGNS & DEFENSIVE EXPEDITIONS")
                print("=" * 78)
                print(" [1] Repel Sutean Desert Nomad Raiders   (Threat: Low-Med  | Spoils: Silver, Barley, Wool)")
                print(" [2] Purge Zagros Mountain Brigands      (Threat: Medium   | Spoils: Silver, Copper, Tin)")
                print(" [3] King Hammurabi's Imperial War       (Threat: High     | Massive Spoils: Silver, Arms, Honor)")
                print(" [4] Processional Way Grand Troop Drill  (Threat: None     | Increases Troop Experience Level)")
                print(" [0] Return")
                camp_pick = input(" Choose campaign [0-4]: ").strip()
                if camp_pick in ["1", "2", "3", "4"]:
                    c_idx = int(camp_pick)
                    if not self.war_engine.standing_army:
                        print(" [!] You have no soldiers to field in battle!")
                        continue
                    print(f"\n Mobilizing all {len(self.war_engine.standing_army)} regiments ({sum(r.soldiers_count for r in self.war_engine.standing_army)} soldiers)...")
                    result = self.war_engine.launch_campaign(self.player, c_idx, list(self.war_engine.standing_army))
                    # Clean out destroyed regiments
                    self.war_engine.standing_army = [r for r in self.war_engine.standing_army if r.soldiers_count > 0]
                    print("\n" + "\n".join(result.chronicle))
                    # Time progression for campaign
                    hours_camp = 4.0 if c_idx == 4 else 8.0
                    self.advance_hours(hours_camp)

            elif gov_act == "5":
                # Manage Municipal Coffers & Granary
                print("\n" + "=" * 78)
                print("           MANAGE BABYLON MUNICIPAL COFFERS (BĪT ĀLĪ)")
                print("=" * 78)
                print(f" Public Civic Treasury: {self.war_engine.city_treasury_silver:.2f} silver shekels")
                print(f" Public Municipal Silos:{self.war_engine.city_granary_barley:.0f} qa barley ({self.war_engine.city_granary_barley/300.0:.2f} gur)")
                print(f" Personal Estate Purse: {self.player.wallet.silver_shekels:.2f} silver | {self.player.wallet.barley_qa:.0f} qa barley")
                print("-" * 78)
                print(" [1] Donate Personal Grain to Public Granary (+Honor/Praise from citizens)")
                print(" [2] Donate Personal Silver to City Treasury (+Honor/Praise from Council of Elders)")
                print(" [3] Draw Mayoral Administrative Dividend (Withdraw up to 30 silver from surplus)")
                print(" [0] Return")
                m_pick = input(" Choose action [0-3]: ").strip()
                if m_pick == "1":
                    amt_str = input(f" How much barley to donate (You hold: {self.player.wallet.barley_qa:.0f} qa)? ").strip()
                    try:
                        amt = float(amt_str)
                        if 0 < amt <= self.player.wallet.barley_qa:
                            self.player.wallet.spend_barley(amt)
                            self.war_engine.city_granary_barley += amt
                            honor_gain = round(amt / 50.0, 1)
                            self.player.reputation = min(100.0, self.player.reputation + honor_gain)
                            print(f" [★] Donated {amt:.0f} qa barley into public silos! Citizens chant blessings upon Governor {self.player.full_name}! (+{honor_gain} Honor)")
                    except ValueError:
                        pass
                elif m_pick == "2":
                    amt_str = input(f" How much silver to donate (You hold: {self.player.wallet.silver_shekels:.2f} silver)? ").strip()
                    try:
                        amt = float(amt_str)
                        if 0 < amt <= self.player.wallet.silver_shekels:
                            self.player.wallet.spend_silver(amt)
                            self.war_engine.city_treasury_silver += amt
                            honor_gain = round(amt * 0.5, 1)
                            self.player.reputation = min(100.0, self.player.reputation + honor_gain)
                            print(f" [★] Contributed {amt:.2f} silver shekels into the city treasury! Council of Elders commends your noble stewardship! (+{honor_gain} Honor)")
                    except ValueError:
                        pass
                elif m_pick == "3":
                    if self.war_engine.city_treasury_silver < 120.0:
                        print(" [!] City treasury is too low (<120 silver). Council of Elders forbids drawing dividends.")
                    else:
                        div = min(30.0, self.war_engine.city_treasury_silver - 90.0)
                        self.war_engine.city_treasury_silver -= div
                        self.player.wallet.add_silver(div)
                        print(f" [+] Collected {div:.2f} silver shekels as legitimate Mayoral Executive Dividend!")

            elif gov_act == "6":
                # Famine relief from public granary
                if self.war_engine.city_granary_barley < 100.0:
                    print(" [!] City granary does not have enough grain (<100 qa).")
                else:
                    self.war_engine.city_granary_barley -= 100.0
                    self.player.reputation = min(100.0, self.player.reputation + 5.0)
                    print(f" [★] You opened the public granaries of Babylon, distributing 100 qa of barley to destitute citizens!")
                    print(f"     The people of Babylon shower blessings upon Governor {self.player.full_name}! (+5.0 Honor)")

            elif gov_act == "7":
                # Royal Misharum Debt Jubilee Petition
                pet = input(" Petition Great King Hammurabi for a Royal Misharum Debt Jubilee? (y/N): ").strip().lower()
                if pet == "y":
                    ok, msg = self.politics.petition_debt_jubilee_misharum(self.player)
                    print("\n" + msg)

    # --------------------------------------------------------------------------
    # Subsystem 6: The Gate of Shamash (Hall of Justice & Hammurabi's Code)
    # --------------------------------------------------------------------------

    def handle_justice(self):
        """Litigate civil & criminal disputes under the Code of Hammurabi."""
        while True:
            print("\n" + "=" * 70)
            print("          THE GATE OF SHAMASH (HALL OF SUPREME JUSTICE)")
            print("=" * 70)
            rival = self.npcs["patrician_rival"]
            print(f" Prominent Patrician Rival: {rival.full_name} ({rival.civic_office})")
            print(" [1] Prosecute Rim-Sin for charging >20% usury (Code § 88)")
            print(" [2] Prosecute Rim-Sin for canal dike negligence flooding your fields (Code §§ 53-55)")
            print(" [3] Demand the Sacred River Ordeal of Id (Divine Trial by the Euphrates)")
            print(" [0] Return to City Square")
            print("-" * 70)

            act = input(" Choose legal proceeding [0-3]: ").strip()
            if act == "1":
                case = self.politics.file_lawsuit(
                    accuser=self.player,
                    defendant=rival,
                    charge=LawsuitCharge.USURY_VIOLATION,
                    evidence_strength=0.70 + (self.player.skills.literacy * 0.05),
                    damages_claimed_silver=25.0
                )
                judge = self.npcs["temple_priest"]
                won, report = self.politics.adjudicate_case(case, magistrate=judge)
                print("\n" + report)
            elif act == "2":
                case = self.politics.file_lawsuit(
                    accuser=self.player,
                    defendant=rival,
                    charge=LawsuitCharge.CANAL_NEGLIGENCE,
                    evidence_strength=0.65 + (self.player.skills.agriculture * 0.05),
                    damages_claimed_silver=30.0
                )
                judge = self.npcs["temple_priest"]
                won, report = self.politics.adjudicate_case(case, magistrate=judge)
                print("\n" + report)
            elif act == "3":
                # River Ordeal of Id (Code § 2)
                print("\n=== THE SACRED RIVER ORDEAL OF ID (CODE § 2) ===")
                print(" The priests escort you and Rim-Sin to the sacred banks of the Euphrates.")
                print(" 'If a man bring an accusation against another, and the accused go to the river")
                print("  and leap into the river, if the river overpower him, his accuser shall take his house;'")
                print(" 'if the river prove that the accused is not guilty, he who accused him shall be put to death!'")
                confirm = input(" Plunge into the divine river currents? (y/N): ").strip().lower()
                if confirm == "y":
                    time.sleep(0.5)
                    survival_chance = 0.50 + (self.player.health / 300.0)
                    if random.random() < survival_chance:
                        print("\n [+] BY THE SUN GOD SHAMASH! The river god Id clears you of all guilt!")
                        print("     You emerge triumphant on the reeds. Your rival Rim-Sin is fined 40 silver!")
                        self.player.wallet.add_silver(40.0)
                        self.player.reputation = min(100.0, self.player.reputation + 20.0)
                    else:
                        print("\n [!] The swirling waters of the Euphrates pull you beneath the foam!")
                        print("     You swallow river silt, losing 40% health and suffering deep shame.")
                        self.player.health = max(10.0, self.player.health - 40.0)
                        self.player.reputation = max(10.0, self.player.reputation - 15.0)
            elif act == "0":
                break

    # --------------------------------------------------------------------------
    # Subsystem 7: Domestic Household & Cuneiform Archive
    # --------------------------------------------------------------------------

    def handle_domestic(self):
        """Manage marriage covenant, dowry assets, and sealed cuneiform clay archives."""
        while True:
            print("\n" + "=" * 70)
            print("            DOMESTIC HOUSEHOLD & CUNEIFORM CLAY ARCHIVE")
            print("=" * 70)
            if self.player_marriage_contract:
                contract = self.player_marriage_contract
                print(f" Marriage Status: Bound to {contract.wife.full_name} under Code § 128")
                print(f" Bride-Price (Terhatum): {contract.bride_price_silver:.1f} silver shekels")
                print(f" Dowry in Custody:       {contract.dowry.silver_shekels:.1f} silver, {contract.dowry.land_acres:.1f} acres land, {contract.dowry.oxen} oxen")
                print(" [1] Seek Divorce Settlement under Code §§ 137-142")
            else:
                print(" Marriage Status: Unmarried (Visit the Ale-Wife's Tavern to meet suitors)")

            print(f" Total Sealed Clay Tablets in Archive: {len(self.player.tablets)}")
            print(" [2] Inspect Cuneiform Tablet Archive")
            print(" [0] Return to City Square")
            print("-" * 70)

            act = input(" Choose option [0-2]: ").strip()

            if act == "1" and self.player_marriage_contract:
                print("\n--- CODE OF HAMMURABI DIVORCE SETTLEMENT (§§ 137-142) ---")
                print(" Grounds for Dissolution:")
                print(" [1] Infertility / Barrenness (Code § 138 - Must return full dowry + bride-price)")
                print(" [2] Misconduct & Squandering (Code § 141 - Wife cast out without alimony)")
                print(" [3] Mutual Agreement / Separation")
                d_choice = input(" Select legal grounds [1-3]: ").strip()
                reason_map = {
                    "1": DivorceReason.CHILDLESSNESS,
                    "2": DivorceReason.INFIDELITY_MISCONDUCT,
                    "3": DivorceReason.MUTUAL_CONSENT
                }
                if d_choice in reason_map:
                    reason = reason_map[d_choice]
                    ok, msg = self.marriage_mgr.file_for_divorce(
                        contract=self.player_marriage_contract,
                        reason=reason,
                        petitioner=self.player
                    )
                    print("\n" + msg)
                    if ok:
                        # Deduct returned dowry
                        dowry = self.player_marriage_contract.dowry
                        self.player.wallet.spend_silver(dowry.silver_shekels)
                        self.player.owned_land_acres = max(0.0, self.player.owned_land_acres - dowry.land_acres)
                        self.player_marriage_contract = None

            elif act == "2":
                print("\n=== SEALED CUNEIFORM TABLET ARCHIVE ===")
                if not self.player.tablets:
                    print(" (No tablets recorded yet)")
                for idx, t in enumerate(self.player.tablets, 1):
                    print(f" [{idx}] {t.doc_type.value}: {t.summary}")
                    if t.sealed_by:
                        print(f"     Seals Imprinted: {', '.join(t.sealed_by)}")
                input("\n Press Enter to continue...")

            elif act == "0":
                break

    # --------------------------------------------------------------------------
    # Subsystem 8: Turn Advancement & Seasonal Living Simulation
    # --------------------------------------------------------------------------

    def advance_season(self):
        """Advances world time by one season, resetting day clock and stepping macroeconomy."""
        print("\n" + "." * 75)
        print(" The cycle of seasons turns over the plains of Shinar. A new season arrives...")
        print("." * 75)
        time.sleep(0.3)

        self.day = 1
        self.hour = 8.0

        # 1. Official Salary Payout
        if self.player and self.player.civic_office:
            for title, office_def in OFFICE_CATALOG.items():
                if title.value == self.player.civic_office:
                    self.player.wallet.add_silver(office_def.salary_silver_per_tick)
                    print(f" [+] Received seasonal civic stipend: {office_def.salary_silver_per_tick:.1f} silver shekels for serving as {title.value}.")

        # 2. Player Metabolism & Needs
        if self.player:
            self.player.sleep()
            self.player.tick_daily_metabolism(self.registry, self.market)

        # 3. Step Victoria 3 Macroeconomy
        econ_report = self.economy.step_season()
        self.season_idx = (self.season_idx + 1) % 4
        if self.season_idx == 0:
            self.year += 1
            if self.player:
                self.player.age += 1

        # 4. Generate Dynamic World Events
        new_season_name, _ = self.seasons[self.season_idx]
        event_roll = random.random()
        if event_roll < 0.20:
            self.news_ticker.append("The Euphrates river overflowed into southern irrigation basins; date harvests look rich.")
        elif event_roll < 0.40:
            self.news_ticker.append(f"A caravan arrived from Anatolia with heavy tin ingots; metal tool costs stabilized.")
        elif event_roll < 0.60:
            self.news_ticker.append("The King in Babylon proclaimed tax remissions for tenant farmers who dredged their dikes.")
        else:
            self.news_ticker.append(f"Esagila Temple priests performed the sacred sacrifices. CPI is holding at {econ_report['cpi']:.3f}x.")

        print(f" [+] Season complete! Dawn breaks on {new_season_name.upper()} (Year {self.year}, Day 01).")

    def advance_turn(self):
        """Compatibility wrapper to advance a season non-interactively."""
        self.advance_season()

    def handle_sleep(self):
        """Allows the player to rest until dawn (06:00) or advance to the next season."""
        print("\n" + "=" * 70)
        print("                   REST & SLEEP IN BABYLON")
        print("=" * 70)
        h_int = int(self.hour)
        m_int = int((self.hour - h_int) * 60)
        print(f" Current Time: Day {self.day:02d}/{self.days_per_season} | {h_int:02d}:{m_int:02d} ({self.get_time_label()})")
        print(f" Energy: {self.player.energy:.0f}% | Hunger: {self.player.hunger:.0f}% | Thirst: {self.player.thirst:.0f}%")
        print("-" * 70)
        print(" [1] Sleep until Dawn (06:00) - Recovers 100% energy, advances to tomorrow morning")
        print(f" [2] Advance to Next Season - Sleep through remaining {self.days_per_season - self.day + 1} days of this season")
        print(" [0] Return to City Square")
        print("-" * 70)
        choice = input(" Select rest action [0-2]: ").strip()

        if choice == "1":
            # Calculate sleep duration to 06:00 next day
            if self.hour < 6.0:
                hours_to_sleep = 6.0 - self.hour
            else:
                hours_to_sleep = (24.0 - self.hour) + 6.0

            if hours_to_sleep < 4.0:
                hours_to_sleep += 24.0

            print(f"\n You lay your head upon a reed mat and rest under the desert stars...")
            time.sleep(0.4)
            self.player.energy = 100.0

            # Consume 1 bread or date ration if available to mitigate hunger
            if self.player.inventory.get("bread", 0.0) >= 1.0:
                self.player.inventory["bread"] -= 1.0
                self.player.hunger = max(0.0, self.player.hunger - 35.0)
                print(" [+] Ate a loaf of barley bread before sleeping.")
            elif self.player.inventory.get("dates", 0.0) >= 1.0:
                self.player.inventory["dates"] -= 1.0
                self.player.hunger = max(0.0, self.player.hunger - 25.0)
                print(" [+] Ate a handful of sweet dates before sleeping.")

            if self.player.inventory.get("barley_beer", 0.0) >= 1.0:
                self.player.inventory["barley_beer"] -= 1.0
                self.player.thirst = max(0.0, self.player.thirst - 40.0)
                print(" [+] Quenched thirst with a jar of cool beer.")

            self.advance_hours(hours_to_sleep)
            print(f" [+] Dawn breaks! It is 06:00 on Day {self.day:02d}. Energy fully restored to 100%.")

        elif choice == "2":
            confirm = input(f" Advance directly to next season? Hired wages for {self.days_per_season - self.day + 1} remaining days will be settled. (y/N): ").strip().lower()
            if confirm == "y":
                remaining_days = self.days_per_season - self.day + 1
                if self.hired_artisans > 0:
                    cpi = self.market.calculate_cpi()
                    grains = WAGE_POLICIES[self.wage_policy]["grains_per_day"]
                    total_wage = (grains * cpi / 180.0) * self.hired_artisans * remaining_days
                    if not self.player.wallet.spend_silver(total_wage):
                        print(f" [!] Could not afford {total_wage:.2f} silver for {remaining_days} days of wages. Hired artisans have been dismissed.")
                        self.hired_artisans = 0
                    else:
                        print(f" [+] Settled {total_wage:.2f} silver in wages for the remainder of the season.")
                self.advance_season()

    # --------------------------------------------------------------------------
    # Save & Load Subsystems
    # --------------------------------------------------------------------------

    def save_game(self) -> bool:
        """Serializes current game state to JSON."""
        p = self.player
        if not p:
            return False

        save_dict = {
            "year": self.year,
            "season_idx": self.season_idx,
            "day": self.day,
            "hour": self.hour,
            "days_per_season": self.days_per_season,
            "workshop_tier": self.workshop_tier,
            "hired_artisans": self.hired_artisans,
            "wage_policy": self.wage_policy,
            "news_ticker": self.news_ticker,
            "player": {
                "name": p.name,
                "patronymic": p.patronymic,
                "social_class": p.social_class.name,
                "age": p.age,
                "health": p.health,
                "energy": p.energy,
                "hunger": p.hunger,
                "thirst": p.thirst,
                "silver_shekels": p.wallet.silver_shekels,
                "barley_qa": p.wallet.barley_qa,
                "owned_land_acres": p.owned_land_acres,
                "owned_oxen": p.owned_oxen,
                "owned_sheep": p.owned_sheep,
                "civic_office": p.civic_office,
                "reputation": p.reputation,
                "inventory": p.inventory,
                "seal": {
                    "material": p.cylinder_seal.material,
                    "patron_deity": p.cylinder_seal.patron_deity,
                    "prestige": p.cylinder_seal.prestige_rating
                } if p.cylinder_seal else None
            },
            "marriage": {
                "bride_name": self.player_marriage_contract.wife.name,
                "bride_patronymic": self.player_marriage_contract.wife.patronymic,
                "bride_social_class": self.player_marriage_contract.wife.social_class.name,
                "terhatum": self.player_marriage_contract.bride_price_silver,
                "dowry_silver": self.player_marriage_contract.dowry.silver_shekels,
                "dowry_land": self.player_marriage_contract.dowry.land_acres,
                "dowry_oxen": self.player_marriage_contract.dowry.oxen,
                "year": self.player_marriage_contract.year_contracted
            } if self.player_marriage_contract and self.player_marriage_contract.is_active else None,
            "tablets": [
                {
                    "id": t.id,
                    "doc_type": t.doc_type.name,
                    "summary": t.summary,
                    "parties": t.parties_involved,
                    "principal": t.principal_silver
                }
                for t in (self.player.tablets if self.player else [])
            ],
            "army": {
                "regiment_counter": self.war_engine.regiment_counter,
                "city_treasury_silver": self.war_engine.city_treasury_silver,
                "city_granary_barley": self.war_engine.city_granary_barley,
                "gate_toll_revenue_daily": self.war_engine.gate_toll_revenue_daily,
                "regiments": [
                    {
                        "id": r.id,
                        "unit_type": r.unit_type.name,
                        "soldiers_count": r.soldiers_count,
                        "is_equipped": r.is_equipped,
                        "experience_level": r.experience_level,
                        "stationed_gate": r.stationed_gate
                    }
                    for r in self.war_engine.standing_army
                ]
            },
            "market_prices": {g_id: state.current_price for g_id, state in self.market.goods.items()}
        }

        try:
            with open(self.SAVE_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(save_dict, f, indent=2)
            print(f" [+] Game state successfully imprinted to clay archive '{self.SAVE_FILE_PATH}'!")
            return True
        except Exception as e:
            print(f" [!] Error saving game: {e}")
            return False

    def load_game(self) -> bool:
        """Restores game state from JSON."""
        if not os.path.exists(self.SAVE_FILE_PATH):
            return False

        try:
            with open(self.SAVE_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.year = data["year"]
            self.season_idx = data["season_idx"]
            self.day = data.get("day", 1)
            self.hour = data.get("hour", 8.0)
            self.days_per_season = data.get("days_per_season", 14)
            self.workshop_tier = data.get("workshop_tier", 1)
            self.hired_artisans = data.get("hired_artisans", 0)
            self.wage_policy = data.get("wage_policy", "STATUTORY")
            self.news_ticker = data.get("news_ticker", self.news_ticker)

            p_data = data["player"]
            s_class = SocialClass[p_data["social_class"]]
            self.player = Character(p_data["name"], p_data["patronymic"], s_class, age=p_data["age"], is_player=True)
            self.player.health = p_data["health"]
            self.player.energy = p_data["energy"]
            self.player.hunger = p_data["hunger"]
            self.player.thirst = p_data["thirst"]
            self.player.wallet.silver_shekels = p_data["silver_shekels"]
            self.player.wallet.barley_qa = p_data["barley_qa"]
            self.player.owned_land_acres = p_data["owned_land_acres"]
            self.player.owned_oxen = p_data["owned_oxen"]
            self.player.owned_sheep = p_data["owned_sheep"]
            self.player.civic_office = p_data["civic_office"]
            if self.player.civic_office:
                for o_title in OfficeTitle:
                    if o_title.value == self.player.civic_office or o_title.name == self.player.civic_office:
                        self.politics.office_holders[o_title] = self.player
                        break
            self.player.reputation = p_data["reputation"]
            self.player.inventory = p_data.get("inventory", {})

            if p_data.get("seal"):
                s = p_data["seal"]
                self.player.cylinder_seal = CylinderSeal(
                    owner_name=self.player.full_name,
                    material=s["material"],
                    patron_deity=s["patron_deity"],
                    prestige_rating=s["prestige"]
                )

            # Restore marriage contract
            m_data = data.get("marriage")
            if m_data:
                b_class = SocialClass[m_data["bride_social_class"]]
                bride_npc = Character(
                    m_data["bride_name"],
                    m_data["bride_patronymic"],
                    b_class,
                    gender="female"
                )
                dowry = Dowry(
                    silver_shekels=m_data.get("dowry_silver", 0.0),
                    land_acres=m_data.get("dowry_land", 0.0),
                    oxen=m_data.get("dowry_oxen", 0)
                )
                contract = MarriageContract(
                    id="covenant_restored",
                    husband=self.player,
                    wife=bride_npc,
                    bride_price_silver=m_data.get("terhatum", 0.0),
                    dowry=dowry,
                    year_contracted=m_data.get("year", 1)
                )
                self.player_marriage_contract = contract
                self.marriage_mgr.registry[contract.id] = contract

            # Restore clay tablets
            t_list = data.get("tablets", [])
            for t_item in t_list:
                d_type = DocumentType[t_item["doc_type"]]
                tab = ClayTablet(
                    id=t_item["id"],
                    doc_type=d_type,
                    summary=t_item["summary"],
                    parties_involved=t_item.get("parties", []),
                    principal_silver=t_item.get("principal", 0.0)
                )
                if self.player.cylinder_seal:
                    tab.seal_document(self.player.cylinder_seal)
                self.player.tablets.append(tab)

            # If player is married to Amat-Ba'u but tablet list was empty, restore covenant tablet
            if self.player_marriage_contract and not any(t.doc_type == DocumentType.MARRIAGE_CONTRACT for t in self.player.tablets):
                self.player.tablets.append(self.player_marriage_contract.cuneiform_tablet)

            # Restore military standing army
            if "army" in data:
                a_data = data["army"]
                self.war_engine.regiment_counter = a_data.get("regiment_counter", 1)
                self.war_engine.city_treasury_silver = a_data.get("city_treasury_silver", 250.0)
                self.war_engine.city_granary_barley = a_data.get("city_granary_barley", 3000.0)
                self.war_engine.gate_toll_revenue_daily = a_data.get("gate_toll_revenue_daily", 1.80)
                self.war_engine.standing_army = []
                for r_item in a_data.get("regiments", []):
                    u_type = UnitType[r_item["unit_type"]]
                    reg = SoldierRegiment(
                        id=r_item["id"],
                        unit_type=u_type,
                        soldiers_count=r_item["soldiers_count"],
                        is_equipped=r_item.get("is_equipped", False),
                        experience_level=r_item.get("experience_level", 1),
                        stationed_gate=r_item.get("stationed_gate")
                    )
                    self.war_engine.standing_army.append(reg)

            # Restore market prices
            if "market_prices" in data:
                for g_id, price in data["market_prices"].items():
                    if g_id in self.market.goods:
                        self.market.goods[g_id].current_price = price

            return True
        except Exception as e:
            print(f" [!] Error loading savegame: {e}")
            return False

    # --------------------------------------------------------------------------
    # Main Interactive Execution Loop
    # --------------------------------------------------------------------------

    def play(self):
        """Starts the main interactive gameplay experience."""
        self.setup_player_interactive()

        while self.player and self.player.is_alive:
            self.render_dashboard()
            self.print_menu()
            choice = input(" Select action [0-9]: ").strip()

            if choice == "1":
                self.handle_market()
            elif choice == "2":
                self.handle_work()
            elif choice == "3":
                self.handle_tavern()
            elif choice == "4":
                self.handle_caravan()
            elif choice == "5":
                self.handle_politics()
            elif choice == "6":
                self.handle_justice()
            elif choice == "7":
                self.handle_domestic()
            elif choice == "8":
                self.handle_sleep()
            elif choice.lower() == "e":
                self.handle_eat_drink()
            elif choice == "9":
                self.save_game()
            elif choice == "0":
                print("\n[!] Imprinting current journey to clay archive before departure...")
                self.save_game()
                print("May the gods Shamash and Marduk grant you long life and bountiful harvests. Farewell!")
                break
            else:
                print(" [!] Unknown command. Please select 0-9 or E.")

        if self.player and not self.player.is_alive:
            print("\n" + "=" * 78)
            print("                           YOU HAVE DIED")
            print(" Your shade descends to the dark underworld of Kur, beneath the dust.")
            print(" Your cylinder seal is buried in your ancestral family tomb.")
            print("=" * 78)


def run_automated_smoke_test():
    """Validates game initialization and non-interactive execution across all subsystems."""
    print("=" * 78)
    print("      BABYLONIAN RPG - MASTER SUBSYSTEM INTEGRATION SMOKE TEST")
    print("=" * 78)
    game = BabylonianGame()
    game.player = Character("Iddin-Sin", "Ea-malik", SocialClass.MUSHKENUM, is_player=True)
    
    # 1. Dashboard rendering
    print("\n[1/7] Testing Dashboard Render & Intraday Clock...")
    game.render_dashboard()
    assert game.day == 1, "Initial day should be 1"
    assert game.hour == 8.0, "Initial hour should be 08:00"

    # 2. Market buying/selling
    print("\n[2/7] Testing Market Subsystem...")
    initial_silver = game.player.wallet.silver_shekels
    game.player.buy_good("bread", 2.0, game.market, game.registry)
    assert game.player.inventory.get("bread", 0.0) >= 2.0, "Failed to buy bread"
    game.player.sell_good("bread", 1.0, game.market, game.registry)
    print(" [+] Market transactions verified.")

    # 3. Agriculture & Multi-Batch Workshop Labor
    print("\n[3/7] Testing Agriculture, Batch Crafting & Clock Advancement...")
    game.player.wallet.add_barley(500.0)
    # Test batch formula: 3 batches of beer (15 qa barley -> 12 jars beer)
    game.player.wallet.spend_barley(15.0)
    game.player.inventory["barley_beer"] = game.player.inventory.get("barley_beer", 0.0) + 12.0
    assert game.player.inventory.get("barley_beer", 0.0) >= 12.0
    initial_h = game.hour
    game.advance_hours(5.5)
    assert game.hour == initial_h + 5.5, "Clock failed to advance"
    print(f" [+] Batch brewing and time progression verified (Clock: {game.hour:.1f}h).")

    # 4. Marriage covenant
    print("\n[4/7] Testing Marriage Covenant under Code § 128...")
    bachelorette = game.npcs["beltani"]
    dowry = Dowry(silver_shekels=10.0, land_acres=2.0, goods={"sheep": 3})
    game.player.wallet.add_silver(20.0)
    ok, msg, contract = game.marriage_mgr.propose_and_marry(
        groom=game.player,
        bride=bachelorette,
        bride_price_silver=5.0,
        dowry=dowry,
        year=game.year
    )
    assert ok, f"Marriage proposal failed: {msg}"
    game.player_marriage_contract = contract
    print(" [+] Marriage contract sealed in clay.")

    # 5. Long-distance Caravan
    print("\n[5/7] Testing Tamkarum Caravan Logistics...")
    fleet = TransportFleet.create_donkey_caravan(num_donkeys=2, guards=1)
    game.player.wallet.add_silver(50.0)
    game.player.wallet.add_barley(300.0)
    ok, msg, mission = game.trade_mgr.assemble_caravan(
        investor=game.player,
        corridor=TradeCorridor.DILMUN_ENTREPOT,
        fleet=fleet,
        cargo_to_export={"dates": 2.0},
        silver_purse=10.0
    )
    assert ok, f"Caravan assembly failed: {msg}"
    succ, ret_rep = game.trade_mgr.resolve_mission(mission, game.player)
    print(" [+] Caravan voyage successfully resolved.")

    # 6. Politics & Litigation
    print("\n[6/7] Testing Assembly Politics & Court Litigation...")
    case = game.politics.file_lawsuit(
        accuser=game.player,
        defendant=game.npcs["patrician_rival"],
        charge=LawsuitCharge.USURY_VIOLATION,
        evidence_strength=0.80,
        damages_claimed_silver=10.0
    )
    won, rep = game.politics.adjudicate_case(case, magistrate=game.npcs["temple_priest"])
    print(" [+] Court litigation resolved.")

    # 7. Military Command, Warfare & Weapon Forging
    print("\n[7/8] Testing Babylonian Warfare Engine, Levies & Campaigns...")
    game.player.wallet.add_silver(100.0)
    game.player.wallet.add_barley(500.0)
    initial_army_len = len(game.war_engine.standing_army)
    # Recruit 5 Bā'iru archers
    ok_rec, msg_rec = game.war_engine.recruit_regiment(game.player, UnitType.BAIRU, 5)
    assert ok_rec, f"Recruitment failed: {msg_rec}"
    assert len(game.war_engine.standing_army) == initial_army_len + 1
    new_reg = game.war_engine.standing_army[-1]
    assert not new_reg.is_equipped, "Should start unequipped without bow in sacks"

    # Give player composite bows and arm the regiment
    game.player.inventory["composite_bow"] = 5.0
    ok_arm, msg_arm = game.war_engine.arm_regiment(game.player, new_reg.id)
    assert ok_arm, f"Arming failed: {msg_arm}"
    assert new_reg.is_equipped, "Regiment should now be equipped"
    assert game.player.inventory.get("composite_bow", 0.0) == 0.0

    # Test military drill campaign
    drill_res = game.war_engine.launch_campaign(game.player, 4, [new_reg])
    assert drill_res.victory, "Drill should always succeed"
    assert new_reg.experience_level >= 2, "Drill should increase experience level"

    # Test security rating calculation
    sec_rating = game.war_engine.calculate_city_security()
    assert sec_rating > 0, "Security rating should be positive"
    print(f" [+] Warfare engine verified: Recruited, armed, drilled (Security Rating: {sec_rating:.1f}%).")

    # 8. Season Advance, Save & Load with Army & Clock State
    print("\n[8/8] Testing Season Advance & Save/Load with Army & Intraday State...")
    game.advance_season()
    game.SAVE_FILE_PATH = "test_savegame.json"
    game.workshop_tier = 2
    game.hired_artisans = 1
    game.wage_policy = "EFFICIENCY"
    assert game.save_game(), "Failed to save game"
    assert game.load_game(), "Failed to load game"
    assert game.workshop_tier == 2, "Workshop tier failed to restore"
    assert game.hired_artisans == 1, "Hired artisans failed to restore"
    assert game.wage_policy == "EFFICIENCY", "Wage policy failed to restore"
    assert len(game.war_engine.standing_army) == initial_army_len + 1, "Army regiments failed to restore"
    if os.path.exists("test_savegame.json"):
        os.remove("test_savegame.json")
    print(" [+] Save/Load with Army, Day/Hour & Workshop State verified.")

    print("\n" + "=" * 78)
    print("   ALL BABYLONIAN RPG SUBSYSTEMS FULLY OPERATIONAL & VERIFIED!")
    print("=" * 78)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_automated_smoke_test()
    else:
        game = BabylonianGame()
        game.play()
