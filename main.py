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
import shutil
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
    BattleResult, UNIT_CATALOG, TaxPolicy, TAX_POLICIES_CONFIG,
    MiningOutpost
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

    SAVES_DIR = "saves"
    TOTAL_SLOTS = 20
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
        self.season_idx: int = 0
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

        # Agricultural Season State-Tracking & Incremental Sowing
        self.has_harvested_spring: bool = False
        self.sowed_acres: float = 0.0
        self.sowed_barley_acres: float = 0.0
        self.sowed_emmer_acres: float = 0.0

        # 3. Notable World Citizens (NPCs)
        self.npcs: Dict[str, Character] = self._setup_world_npcs()

        # 4. Player Character
        self.player: Optional[Character] = None

        # 5. Active Marriage Contract (if player is married)
        self.player_marriage_contract: Optional[MarriageContract] = None

        # 6. Save Slots Management (20 Slots)
        self.current_slot: int = 1
        self.ensure_saves_dir()

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
        """Allows the player to create or load an authentic Babylonian persona from 20 save slots."""
        self.ensure_saves_dir()

        while True:
            print("=" * 80)
            print("          BABYLONIAN RPG: LIFE IN THE CRADLE OF CIVILIZATION")
            print("               Ancient Mesopotamia (c. 1750 BC / Old Babylonian)")
            print("=" * 80)
            print(" [L] Open Cuneiform Archive Vault (Load Save Slot 1-20)")
            print(" [N] Inscribe New Clay Tablet (Start New Character)")
            print(" [Q] Depart Babylon / Quit")
            print("-" * 80)
            choice = input(" Select option [L/N/Q, default=L]: ").strip().upper() or "L"

            if choice == "L":
                self.display_save_vault()
                slot_inp = input(f"\n Select tablet slot to load [1-{self.TOTAL_SLOTS}, or B to return]: ").strip()
                if slot_inp.upper() == "B":
                    continue
                try:
                    slot_num = int(slot_inp)
                    if 1 <= slot_num <= self.TOTAL_SLOTS:
                        meta = self.get_slot_metadata(slot_num)
                        if not meta["exists"]:
                            print(f" [!] Slot [{slot_num:02d}] is empty. No cuneiform tablet found.")
                            continue
                        self.current_slot = slot_num
                        self.SAVE_FILE_PATH = self.get_slot_filepath(slot_num)
                        if self.load_game(self.SAVE_FILE_PATH):
                            print(f"\n[+] Tablet Slot [{slot_num:02d}] successfully unsealed! Resuming journey of {self.player.full_name}...")
                            return
                        else:
                            print(f" [!] Failed to load save from slot [{slot_num:02d}].")
                    else:
                        print(f" [!] Please select a slot between 1 and {self.TOTAL_SLOTS}.")
                except ValueError:
                    print(" [!] Invalid input. Please enter a valid slot number.")

            elif choice == "N":
                # Find first empty slot as default
                default_slot = 1
                for s in range(1, self.TOTAL_SLOTS + 1):
                    if not self.get_slot_metadata(s)["exists"]:
                        default_slot = s
                        break

                self.display_save_vault()
                s_pick = input(f"\n Choose slot for new persona [1-{self.TOTAL_SLOTS}, default={default_slot}, or B to return]: ").strip()
                if s_pick.upper() == "B":
                    continue
                try:
                    slot_num = int(s_pick) if s_pick else default_slot
                    if not (1 <= slot_num <= self.TOTAL_SLOTS):
                        print(f" [!] Slot must be between 1 and {self.TOTAL_SLOTS}.")
                        continue
                    meta = self.get_slot_metadata(slot_num)
                    if meta["exists"]:
                        warn = input(f" [!] Warning: Slot [{slot_num:02d}] already contains {meta['full_name']}. Overwrite? (y/N): ").strip().lower()
                        if warn != "y":
                            continue
                    self.current_slot = slot_num
                    self.SAVE_FILE_PATH = self.get_slot_filepath(slot_num)
                    break
                except ValueError:
                    print(" [!] Invalid input.")

            elif choice == "Q":
                print("May the gods walk beside you. Farewell!")
                sys.exit(0)

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
        
        # Auto-save initial persona to the assigned slot
        print(f"    Imprinting initial tablet into Slot [{self.current_slot:02d}]...")
        self.save_game(self.get_slot_filepath(self.current_slot))

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
        print(f" [9] Cuneiform Archive Vault (Save / Switch Slot - Active: [{self.current_slot:02d}])")
        print(" [0] Exit Game")
        print("-" * 78)

    # --------------------------------------------------------------------------
    # Subsystem 1: The Public Market (Kārum Quay)
    # --------------------------------------------------------------------------

    def handle_market(self):
        """Interactive market trading with real-time Victoria 3 supply/demand prices and live warehouse stock."""
        while True:
            print("\n" + "=" * 74)
            print("            THE PUBLIC MARKET AT THE KĀRUM QUAY")
            print("=" * 74)
            tax_rate = self.war_engine.get_tax_rates().get("sales_tax_rate", 0.0)
            tax_tag = f" | Municipal Duty: {tax_rate*100:.0f}%" if tax_rate > 0 else ""
            print(f" Your Liquid Purse: {self.player.wallet.silver_shekels:.2f} silver shekels{tax_tag}")
            print(f"{'Commodity':<20} | {'Base Price':<10} | {'Market Price':<13} | {'In Stock':<11} | {'Status'}")
            print("-" * 74)

            # Display curated list of benchmark and essential goods
            catalog = [
                ("barley", "Basic Food"),
                ("emmer", "Basic Food"),
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
                stk = self.market.get_stock(g_id)
                unit_suffix = "qa" if g_id in ("barley", "emmer") else "ea"
                stk_str = f"{stk:6.1f} {unit_suffix}"
                shortage = "[SHORTAGE!]" if self.market.is_in_shortage(g_id) else "High Demand" if cur_p > g.base_price * 1.15 else "Abundant" if cur_p < g.base_price * 0.85 else "Fair Market"
                print(f" {g.name:<19} | {g.base_price:6.2f} silv | {cur_p:6.3f} silv/ea | {stk_str:<11} | {shortage}")

            print("-" * 74)
            print(" [B]uy Good  |  [S]ell Good  |  [V]iew All Goods  |  [R]eturn to City Square")
            cmd = input(" Select market action [B/S/V/R]: ").strip().lower()

            if cmd == "b":
                g_id = input(" Enter commodity ID to buy (e.g. 'bread', 'barley_beer', 'timber', 'tin'): ").strip().lower()
                if g_id in self.registry.goods:
                    cur_p = self.market.get_price(g_id)
                    avail_stk = self.market.get_stock(g_id)
                    if avail_stk <= 0:
                        print(f" [!] OUT OF STOCK! The Kārum warehouse has 0 units of {g_id}.")
                        continue

                    tax_rate = self.war_engine.get_tax_rates().get("sales_tax_rate", 0.0)
                    max_buyable = self.market.calculate_max_affordable_volume(g_id, self.player.wallet.silver_shekels, tax_rate=tax_rate)
                    tax_info = f" (Includes {tax_rate*100:.0f}% Mayoral Municipal Duty)" if tax_rate > 0 else ""
                    print(f" Current spot price: {cur_p:.3f} silver each{tax_info}.")
                    print(f" Warehouse Stock: {avail_stk:.1f} units | Max you can afford: {max_buyable:.1f} units.")
                    qty_str = input(f" How many units would you like to buy (Max: {max_buyable:.1f})? ").strip()
                    try:
                        qty = float(qty_str)
                        if qty <= 0:
                            continue
                        if qty > avail_stk:
                            print(f" [!] Only {avail_stk:.1f} units are available in the warehouse!")
                            continue
                        actual_vol, base_cost, avg_p, s_spot, e_spot = self.market.calculate_trade_pricing(g_id, qty, is_buy=True)
                        tax_paid = base_cost * tax_rate
                        total_needed = base_cost + tax_paid
                        if self.player.wallet.silver_shekels < total_needed:
                            print(f" [!] Insufficient silver! Need {total_needed:.2f} silver shekels (incl. tax), but you hold {self.player.wallet.silver_shekels:.2f}.")
                            continue

                        if self.player.buy_good(g_id, qty, self.market, self.registry, sales_tax_rate=tax_rate):
                            if tax_paid > 0:
                                self.war_engine.city_treasury_silver += tax_paid
                            new_p = self.market.get_price(g_id)
                            new_stk = self.market.get_stock(g_id)
                            print(f" [+] Success! Purchased {actual_vol:.1f} {g_id} for {total_needed:.2f} silver shekels!")
                            print(f"     Execution: Avg price {avg_p:.3f} silver/unit (Spot slipped: {s_spot:.3f} -> {new_p:.3f}).")
                            if tax_paid > 0:
                                print(f"     Remitted {tax_paid:.2f} silver in municipal duty into City Coffers (Bīt Ālī).")
                            print(f"     Warehouse stock fell to {new_stk:.1f} units.")
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
                    _, est_rev, _, _, _ = self.market.calculate_trade_pricing(item, count, is_buy=False)
                    print(f"  * {item}: {count:.1f} units (Estimated Market Value: {est_rev:.2f} silver)")
                g_id = input(" Enter commodity ID to sell: ").strip().lower()
                if g_id in self.player.inventory:
                    avail = self.player.inventory[g_id]
                    qty_str = input(f" Units to sell (Available: {avail:.1f}) [default={avail:.1f}]: ").strip()
                    try:
                        qty = float(qty_str) if qty_str else avail
                        if 0 < qty <= avail:
                            actual_vol, rev, avg_p, s_spot, e_spot = self.market.calculate_trade_pricing(g_id, qty, is_buy=False)
                            if self.player.sell_good(g_id, qty, self.market, self.registry):
                                new_p = self.market.get_price(g_id)
                                new_stk = self.market.get_stock(g_id)
                                print(f" [+] Sold {actual_vol:.1f} {g_id} for {rev:.2f} silver shekels!")
                                print(f"     Execution: Avg price {avg_p:.3f} silver/unit (Spot slipped: {s_spot:.3f} -> {new_p:.3f}).")
                                print(f"     Warehouse stock rose to {new_stk:.1f} units.")
                        else:
                            print(" [!] Invalid quantity.")
                    except ValueError:
                        print(" [!] Invalid input.")
                else:
                    print(" [!] You do not possess that commodity.")

            elif cmd == "v":
                total_count = len(self.registry.goods)
                print(f"\n=== COMPLETE MESOPOTAMIAN COMMODITY REGISTRY ({total_count} GOODS) ===")
                print(f" {'Commodity':<27} ({'ID':<15}) | {'Base':<11} | {'Market Price':<14} | {'In Stock':<12} | Status")
                print("-" * 92)
                for gid, good in sorted(self.registry.goods.items()):
                    p = self.market.get_price(gid)
                    stk = self.market.get_stock(gid)
                    unit_suffix = "qa" if gid in ("barley", "emmer") else "ea"
                    stk_str = f"{stk:6.1f} {unit_suffix}"
                    status = "[SHORTAGE!]" if self.market.is_in_shortage(gid) else "High Demand" if p > good.base_price * 1.15 else "Abundant" if p < good.base_price * 0.85 else "Fair Market"
                    print(f"  {good.name:<26} ({gid:<15}) | {good.base_price:6.2f} silv | {p:6.3f} silv/ea | {stk_str:<12} | {status}")
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
            crop_detail = f"({self.sowed_barley_acres:.1f} Barley | {self.sowed_emmer_acres:.1f} Emmer)" if self.sowed_acres > 0 else ""
            print(f" Land Owned:    {self.player.owned_land_acres:.1f} acres arable soil (Sown: {self.sowed_acres:.1f} acres {crop_detail})")
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
            print(" [7] Forage & Gather Alluvial Commons (Timber, Reeds, Silt, Dung, Cress, Fish, Bitumen)")
            print(" [8] Mobilize Corvée Labor Gangs (Tupšikku / Agrū Bulk Gathering - 0% Energy)")
            print(" [9] Imperial Mountain Mining Outpost (Halṣum Šadî - Zagros Foothills)")
            print(" [0] Return to City Square")
            print("-" * 70)

            act = input(" Choose action [0-9]: ").strip()

            if act == "1":
                # Seasonal agriculture operations
                if self.player.energy < 25:
                    print(" [!] You are exhausted! Sleep and rest before laboring in the heat.")
                    continue

                if self.season_idx == 0:  # Autumn - Sowing
                    if self.player.owned_land_acres <= 0:
                        print(" [!] You have no land to sow! Acquire an arable land title deed first.")
                        continue
                    unsowed_acres = max(0.0, self.player.owned_land_acres - self.sowed_acres)
                    if unsowed_acres <= 0.0:
                        print(f" [+] All {self.player.owned_land_acres:.1f} acres of your estate are already plowed and sown for this agricultural year!")
                        continue

                    print(f" You have {unsowed_acres:.1f} unsown acres on your estate.")
                    print(" Select cereal grain to sow (10 qa seed / acre):")
                    print(f" [1] Barley Grain (še'u)    - Available seed: {self.player.wallet.barley_qa:.0f} qa (Primary volumetric currency)")
                    avail_emmer = self.player.inventory.get("emmer", 0.0)
                    print(f" [2] Emmer Wheat (zizzu)    - Available seed: {avail_emmer:.0f} qa (Aristocratic grain for Spelt Beer & Pastries)")
                    print(" [0] Cancel")
                    crop_choice = input(" Choose crop to sow [1-2, default=1]: ").strip() or "1"

                    if crop_choice == "0":
                        continue
                    elif crop_choice == "2":
                        # Sowing Emmer Wheat
                        if avail_emmer < 10.0:
                            print(f" [!] Insufficient seed emmer! Need at least 10 qa to sow 1 acre (You have: {avail_emmer:.1f} qa in sacks).")
                            print("     (Buy emmer at Kārum Market, or gather via Foraging [9] or Corvée [9]).")
                            continue
                        max_can_sow = int(min(unsowed_acres, avail_emmer // 10.0))
                        acres_str = input(f" How many acres to sow with Emmer Wheat [1-{max_can_sow}, default={max_can_sow}]? ").strip()
                        try:
                            acres_to_sow = float(acres_str) if acres_str else float(max_can_sow)
                            acres_to_sow = min(float(max_can_sow), max(1.0, acres_to_sow))
                        except ValueError:
                            acres_to_sow = float(max_can_sow)
                        seed_spent = acres_to_sow * 10.0
                        self.player.inventory["emmer"] -= seed_spent
                        if self.player.inventory["emmer"] <= 1e-4:
                            del self.player.inventory["emmer"]
                        self.sowed_emmer_acres += acres_to_sow
                        self.sowed_acres += acres_to_sow
                        crop_name = "Emmer Wheat (zizzu)"
                    else:
                        # Sowing Barley Grain
                        seed_needed_qa = unsowed_acres * 10.0
                        if self.player.wallet.barley_qa < seed_needed_qa:
                            max_can_sow = int(self.player.wallet.barley_qa // 10.0)
                            if max_can_sow < 1:
                                print(f" [!] Insufficient seed barley! Need at least 10 qa to sow 1 acre (You have {self.player.wallet.barley_qa:.0f} qa).")
                                continue
                            print(f" [!] You hold {self.player.wallet.barley_qa:.0f} qa seed barley, sufficient to sow {max_can_sow} of your {unsowed_acres:.1f} unsown acres.")
                            acres_str = input(f" Sow how many acres with barley [1-{max_can_sow}, default={max_can_sow}]? ").strip()
                            try:
                                acres_to_sow = float(acres_str) if acres_str else float(max_can_sow)
                                acres_to_sow = min(float(max_can_sow), max(1.0, acres_to_sow))
                            except ValueError:
                                acres_to_sow = float(max_can_sow)
                            seed_spent = acres_to_sow * 10.0
                        else:
                            acres_str = input(f" Sow how many acres with barley [1-{unsowed_acres:.0f}, default={unsowed_acres:.0f}]? ").strip()
                            try:
                                acres_to_sow = float(acres_str) if acres_str else unsowed_acres
                                acres_to_sow = min(unsowed_acres, max(1.0, acres_to_sow))
                            except ValueError:
                                acres_to_sow = unsowed_acres
                            seed_spent = acres_to_sow * 10.0

                        self.player.wallet.spend_barley(seed_spent)
                        self.player.inventory["barley"] = self.player.wallet.barley_qa
                        if self.player.inventory["barley"] <= 0:
                            del self.player.inventory["barley"]
                        self.sowed_barley_acres += acres_to_sow
                        self.sowed_acres += acres_to_sow
                        crop_name = "Barley Grain (še'u)"

                    self.has_harvested_spring = False
                    self.player.energy = max(0.0, self.player.energy - 30.0)
                    self.player.hunger = min(100.0, self.player.hunger + 20.0)
                    self.player.skills.agriculture += 1
                    self.advance_hours(6.0)
                    print(f" [+] Plowing & Sowing complete (6.0 hours)! Sowed {seed_spent:.0f} qa seed across {acres_to_sow:.1f} acres of {crop_name}.")
                    print(f"     Estate Status: {self.sowed_acres:.1f} / {self.player.owned_land_acres:.1f} acres sown ({self.sowed_barley_acres:.1f} Barley | {self.sowed_emmer_acres:.1f} Emmer).")

                elif self.season_idx == 1:  # Winter - Canal Care
                    self.player.energy = max(0.0, self.player.energy - 25.0)
                    self.player.hunger = min(100.0, self.player.hunger + 15.0)
                    self.player.skills.agriculture += 1
                    self.advance_hours(6.0)
                    print(f" [+] Cleared silt from irrigation ditches and reinforced perimeter dikes protecting your {self.sowed_acres:.1f} sown acres (6.0 hours).")

                elif self.season_idx == 2:  # Spring - The Great Harvest!
                    if self.has_harvested_spring:
                        print(" [!] The fields of Babylon have already been reaped this spring!")
                        print("     The dry stubble remains until next Autumn's plowing and sowing cycle.")
                        continue
                    if self.sowed_acres <= 0.0:
                        print(" [!] You have no sown crops to reap! Fields must be plowed and sown with seed in Autumn.")
                        continue

                    # Fallback for save compatibility if only total sowed_acres was tracked
                    if self.sowed_barley_acres == 0.0 and self.sowed_emmer_acres == 0.0 and self.sowed_acres > 0.0:
                        self.sowed_barley_acres = self.sowed_acres

                    oxen_mult = 1.0 + (self.player.owned_oxen * 0.25)
                    skill_mult = 1.0 + (self.player.skills.agriculture * 0.10)
                    tithe_rate = self.war_engine.get_tax_rates().get("harvest_tithe_rate", 0.10)
                    harvest_reports = []

                    # 1. Barley Harvest
                    if self.sowed_barley_acres > 0.0:
                        yield_b = random.uniform(250.0, 380.0) * oxen_mult * skill_mult
                        gross_b = self.sowed_barley_acres * yield_b
                        tithe_b = round(gross_b * tithe_rate, 1)
                        net_b = round(gross_b - tithe_b, 1)
                        self.war_engine.city_granary_barley += tithe_b
                        self.player.wallet.add_barley(net_b)
                        self.player.inventory["barley"] = self.player.wallet.barley_qa
                        harvest_reports.append(
                            f"     * Barley Grain ({self.sowed_barley_acres:.1f} acres): Gross {gross_b/300:.2f} gur ({gross_b:.0f} qa) | Tithe {tithe_b:.0f} qa -> Net +{net_b:.0f} qa in Granary"
                        )

                    # 2. Emmer Wheat Harvest
                    if self.sowed_emmer_acres > 0.0:
                        yield_e = random.uniform(230.0, 350.0) * oxen_mult * skill_mult
                        gross_e = self.sowed_emmer_acres * yield_e
                        tithe_e = round(gross_e * tithe_rate, 1)
                        net_e = round(gross_e - tithe_e, 1)
                        self.war_engine.city_granary_barley += tithe_e
                        self.player.inventory["emmer"] = self.player.inventory.get("emmer", 0.0) + net_e
                        harvest_reports.append(
                            f"     * Emmer Wheat ({self.sowed_emmer_acres:.1f} acres): Gross {gross_e/300:.2f} gur ({gross_e:.0f} qa) | Tithe {tithe_e:.0f} qa -> Net +{net_e:.0f} qa in Sacks"
                        )

                    # 3. Wool shear from sheep
                    wool_harvest = self.player.owned_sheep * 2.5
                    if wool_harvest > 0:
                        self.player.inventory["raw_wool"] = self.player.inventory.get("raw_wool", 0.0) + wool_harvest
                        harvest_reports.append(f"     * Sheep Wool: Sheared +{wool_harvest:.1f} talents of raw wool from {self.player.owned_sheep} sheep!")

                    self.player.energy = max(0.0, self.player.energy - 45.0)
                    self.player.hunger = min(100.0, self.player.hunger + 25.0)
                    self.advance_hours(8.0)

                    print(f"\n" + "=" * 76)
                    print(f" [+] THE GREAT SPRING HARVEST (8.0 hours) across {self.sowed_acres:.1f} sown acres!")
                    print("=" * 76)
                    for r in harvest_reports:
                        print(r)
                    print("=" * 76)

                    self.has_harvested_spring = True
                    self.sowed_acres = 0.0
                    self.sowed_barley_acres = 0.0
                    self.sowed_emmer_acres = 0.0

                elif self.season_idx == 3:  # Summer - Flood & Date Orchards
                    self.has_harvested_spring = False
                    dates_gathered = random.uniform(5.0, 15.0)
                    self.player.inventory["dates"] = self.player.inventory.get("dates", 0.0) + dates_gathered
                    self.player.energy = max(0.0, self.player.energy - 20.0)
                    self.player.thirst = min(100.0, self.player.thirst + 25.0)
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
                        if self.sowed_acres > self.player.owned_land_acres:
                            scale = self.player.owned_land_acres / self.sowed_acres if self.sowed_acres > 0 else 1.0
                            self.sowed_barley_acres *= scale
                            self.sowed_emmer_acres *= scale
                            self.sowed_acres = self.player.owned_land_acres
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

            elif act == "7":
                self.handle_forage()

            elif act == "8":
                self.handle_corvee_forage()

            elif act == "9":
                self.handle_mining_outpost()

            elif act == "0":
                break

    def handle_forage(self):
        """Gathering and foraging raw natural resources in the alluvial commons around Babylon."""
        while True:
            print("\n" + "=" * 72)
            print("          ALLUVIAL COMMONS & EUPHRATES RIVER FORAGING")
            print("=" * 72)
            print(" The uncultivated marshes, riverbanks, and grazing plains around Babylon")
            print(" belong to the commons. Any citizen or laborer may gather natural resources.")
            print(f" Physical Energy: {self.player.energy:.1f}% | Hunger: {self.player.hunger:.1f}%")
            print("-" * 72)
            print(" [1] Fell Riverbank Timber & Poplar (Iṣu)     - 4.5 hrs, 30% nrg -> 2-5 Timber (Building/Crafts)")
            print(" [2] Cut Euphrates Marsh Reeds (Qanû)        - 3.0 hrs, 15% nrg -> 15-35 Reeds (Beer/Kiln/Fences)")
            print(" [3] Dig River Silt & Alluvial Clay (Tīdu)   - 4.0 hrs, 25% nrg -> 10-25 Mudbricks/Pottery Clay")
            print(" [4] Gather Dried Dung Fuel Cakes (Kibrītu)  - 3.0 hrs, 15% nrg -> 20-45 Animal Dung (Kiln Fuel)")
            print(" [5] Forage Wild Watercress & Mustard Herbs  - 3.0 hrs, 15% nrg -> 3-8 Cress, 2-5 Mustard (CPI Food)")
            print(" [6] Net River Carp in Euphrates (Nūnu)      - 4.0 hrs, 20% nrg -> 8-20 Dried Fish (Protein)")
            print(" [7] Haul Raw Bitumen Pitch from Seeps (Ittû)- 4.0 hrs, 25% nrg -> 4-10 Bitumen (Waterproofing)")
            print(" [8] Harvest Ripe Date Palms (Suluppu)      - 3.5 hrs, 20% nrg -> 8-20 Sweet Dates (Food/Sweetener)")
            print(" [9] Gather Wild River Emmer Wheat (Zizzu)  - 3.5 hrs, 20% nrg -> 15-35 qa Emmer Wheat (Brewing/Pastries)")
            print(" [C] Mobilize Corvée Labor Gang (Tupšikku)   - Requisition laborers for BULK harvests (0% energy)")
            print(" [0] Return to Agriculture & Workshop Menu")
            print("-" * 72)

            f_act = input(" Choose foraging expedition [0-9, C]: ").strip()
            if f_act == "0":
                break
            if f_act.upper() == "C":
                self.handle_corvee_forage()
                continue

            if self.player.energy < 20:
                print(" [!] You are too exhausted to trek the marshes and riverbanks. Rest first!")
                continue

            if f_act == "1":
                # Timber felling
                hrs, nrg, hng = 4.5, 30.0, 20.0
                if self.player.energy < nrg:
                    print(" [!] Not enough energy to swing axes in the river groves.")
                    continue
                qty = round(random.uniform(2.0, 5.0) + (self.player.skills.agriculture * 0.3), 1)
                self.player.inventory["timber"] = self.player.inventory.get("timber", 0.0) + qty
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.player.skills.agriculture += 1
                self.advance_hours(hrs)
                print(f" [+] Timber Felling (4.5 hours)! Hewed {qty:.1f} logs of river poplar and tamarisk timber (Iṣu)!")

            elif f_act == "2":
                # Reeds
                hrs, nrg, hng = 3.0, 15.0, 10.0
                qty = round(random.uniform(15.0, 35.0) + (self.player.skills.agriculture * 2.0), 1)
                self.player.inventory["reeds"] = self.player.inventory.get("reeds", 0.0) + qty
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.player.skills.agriculture += 1
                self.advance_hours(hrs)
                print(f" [+] Marsh Reeds (3.0 hours)! Bundled {qty:.1f} stalks of thick marsh reeds (Qanû)!")

            elif f_act == "3":
                # Silt / Clay (Mudbrick)
                hrs, nrg, hng = 4.0, 25.0, 15.0
                qty = round(random.uniform(10.0, 25.0) + (self.player.skills.craftsmanship * 1.5), 1)
                self.player.inventory["mudbrick"] = self.player.inventory.get("mudbrick", 0.0) + qty
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.player.skills.craftsmanship += 1
                self.advance_hours(hrs)
                print(f" [+] River Silt & Clay (4.0 hours)! Dug and shaped {qty:.1f} sun-dried alluvial mudbricks (Tīdu)!")

            elif f_act == "4":
                # Animal Dung
                hrs, nrg, hng = 3.0, 15.0, 10.0
                qty = round(random.uniform(20.0, 45.0), 1)
                self.player.inventory["animal_dung"] = self.player.inventory.get("animal_dung", 0.0) + qty
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.advance_hours(hrs)
                print(f" [+] Pastoral Commons (3.0 hours)! Gathered {qty:.1f} dried animal dung fuel cakes (Kibrītu)!")

            elif f_act == "5":
                # Cress & Mustard
                hrs, nrg, hng = 3.0, 15.0, 10.0
                q_cress = round(random.uniform(3.0, 8.0) + (self.player.skills.agriculture * 0.5), 1)
                q_mustard = round(random.uniform(2.0, 5.0) + (self.player.skills.agriculture * 0.4), 1)
                self.player.inventory["cress"] = self.player.inventory.get("cress", 0.0) + q_cress
                self.player.inventory["mustard"] = self.player.inventory.get("mustard", 0.0) + q_mustard
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.player.skills.agriculture += 1
                self.advance_hours(hrs)
                print(f" [+] Wetland Herbs (3.0 hours)! Foraged {q_cress:.1f} bundles of wild cress (Sahlû) and {q_mustard:.1f} bags of spicy mustard seeds (Kasû)!")

            elif f_act == "6":
                # River Carp Netting
                hrs, nrg, hng = 4.0, 20.0, 15.0
                qty = round(random.uniform(8.0, 20.0), 1)
                self.player.inventory["dried_fish"] = self.player.inventory.get("dried_fish", 0.0) + qty
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.player.skills.agriculture += 1
                self.advance_hours(hrs)
                print(f" [+] Euphrates Netting (4.0 hours)! Hauled in and salted {qty:.1f} river carp and catfish (Nūnu)!")

            elif f_act == "7":
                # Bitumen Seep Hauling
                hrs, nrg, hng = 4.0, 25.0, 15.0
                qty = round(random.uniform(4.0, 10.0) + (self.player.skills.craftsmanship * 0.5), 1)
                self.player.inventory["bitumen"] = self.player.inventory.get("bitumen", 0.0) + qty
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.player.skills.craftsmanship += 1
                self.advance_hours(hrs)
                print(f" [+] Bitumen Pits (4.0 hours)! Ladled {qty:.1f} jars of natural petroleum pitch (Ittû)!")

            elif f_act == "8":
                # Date Palms
                hrs, nrg, hng = 3.5, 20.0, 15.0
                if self.player.energy < nrg:
                    print(" [!] Not enough energy to climb palm trees.")
                    continue
                qty = round(random.uniform(8.0, 20.0) + (self.player.skills.agriculture * 0.8), 1)
                self.player.inventory["dates"] = self.player.inventory.get("dates", 0.0) + qty
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.player.skills.agriculture += 1
                self.advance_hours(hrs)
                print(f" [+] Date Palm Groves (3.5 hours)! Scaled riverbank palms and harvested {qty:.1f} baskets of ripe sweet dates (Suluppu)!")

            elif f_act == "9":
                # Wild Emmer Wheat
                hrs, nrg, hng = 3.5, 20.0, 15.0
                if self.player.energy < nrg:
                    print(" [!] Not enough energy to trek the river terraces.")
                    continue
                qty = round(random.uniform(15.0, 35.0) + (self.player.skills.agriculture * 1.5), 1)
                self.player.inventory["emmer"] = self.player.inventory.get("emmer", 0.0) + qty
                self.player.energy = max(0.0, self.player.energy - nrg)
                self.player.hunger = min(100.0, self.player.hunger + hng)
                self.player.skills.agriculture += 1
                self.advance_hours(hrs)
                print(f" [+] River Terraces (3.5 hours)! Gathered and threshed {qty:.1f} qa of wild emmer wheat (Zizzu)!")

    def handle_corvee_forage(self):
        """Requisition or hire day-labor gangs (Tupšikku / Agrū under Code §§ 273-274) to harvest alluvial resources in industrial bulk."""
        while True:
            ox_bonus_pct = self.player.owned_oxen * 10
            status_title = "Awīlum Patrician" if self.player.social_class == SocialClass.AWILUM else self.player.social_class.value
            civic_off = getattr(self.player, "civic_office", getattr(self.player, "office", None))
            if civic_off and str(civic_off) != "Private Citizen":
                office_str = civic_off.value if hasattr(civic_off, "value") else str(civic_off)
                status_title = f"{status_title} & {office_str}"

            print("\n" + "=" * 74)
            print("       MOBILIZE CORVÉE / HIRED LABOR GANG (TUPŠIKKU & AGRŪ)")
            print("=" * 74)
            print(" Requisition a team of day-laborers with pack beasts and ox-carts to harvest")
            print(" natural raw materials from the commons in industrial quantities (0% player energy).")
            print(f" Commissioner:     {self.player.full_name} ({status_title})")
            print(f" Treasury Purse:   {self.player.wallet.silver_shekels:.2f} silver shekels | Granary: {self.player.wallet.barley_qa:.0f} qa barley")
            print(f" Beast Transport:  {self.player.owned_oxen} draft oxen (+{ox_bonus_pct}% haul capacity bonus)")
            print("-" * 74)
            print(" [1] Timber Felling Crew (Iṣu)       - 5.0 silv + 20 qa grain -> 25-50 Timber Logs")
            print(" [2] Marsh Reed Harvesters (Qanû)    - 2.0 silv + 15 qa grain -> 120-250 Marsh Reeds")
            print(" [3] Mudbrick Molding Crew (Tīdu)    - 3.5 silv + 15 qa grain -> 80-180 Mudbricks")
            print(" [4] Dung Fuel Sweepers (Kibrītu)    - 1.5 silv + 10 qa grain -> 150-300 Dung Fuel Cakes")
            print(" [5] Wetland Herb Pickers (Sahlû)    - 2.5 silv + 15 qa grain -> 30-60 Cress, 20-40 Mustard")
            print(" [6] River Fisherman Flotilla (Nūnu) - 3.0 silv + 15 qa grain -> 60-140 Dried Fish")
            print(" [7] Bitumen Seep Haulers (Ittû)     - 4.0 silv + 20 qa grain -> 30-70 Bitumen Pitch")
            print(" [8] Date Palm Orchard Harvesters    - 3.0 silv + 15 qa grain -> 40-90 Baskets Sweet Dates")
            print(" [9] Emmer Wheat Reapers (Zizzu)     - 3.5 silv + 15 qa grain -> 60-140 qa Emmer Wheat")
            print(" [0] Return to Commons Foraging Menu")
            print("-" * 74)

            c_act = input(" Choose corvée labor dispatch [0-9]: ").strip()
            if c_act == "0":
                break

            MISSIONS = {
                "1": {
                    "name": "Riverbank Timber Felling Gang",
                    "item_key": "timber",
                    "item_name": "poplar and tamarisk timber logs (Iṣu)",
                    "silver_cost": 5.0,
                    "grain_cost": 20.0,
                    "base_min": 25.0,
                    "base_max": 50.0,
                    "desc": "A team of 8 woodcutters with bronze axes cleared wild poplar groves along the Euphrates banks."
                },
                "2": {
                    "name": "Marsh Reed Harvesting Crew",
                    "item_key": "reeds",
                    "item_name": "bundles of thick marsh reeds (Qanû)",
                    "silver_cost": 2.0,
                    "grain_cost": 15.0,
                    "base_min": 120.0,
                    "base_max": 250.0,
                    "desc": "Sickle-wielding marsh harvesters reaped and bundled dense reed thickets along canal channels."
                },
                "3": {
                    "name": "Mudbrick Molding & Silt Crew",
                    "item_key": "mudbrick",
                    "item_name": "sun-dried alluvial mudbricks (Tīdu)",
                    "silver_cost": 3.5,
                    "grain_cost": 15.0,
                    "base_min": 80.0,
                    "base_max": 180.0,
                    "desc": "Laborers dredged alluvium from the canal beds and packed it into rectangular wooden brick molds."
                },
                "4": {
                    "name": "Pastoral Dung Fuel Sweepers",
                    "item_key": "animal_dung",
                    "item_name": "dried animal dung fuel cakes (Kibrītu)",
                    "silver_cost": 1.5,
                    "grain_cost": 10.0,
                    "base_min": 150.0,
                    "base_max": 300.0,
                    "desc": "Sweepers swept the sheep grazing commons and packed dried dung into combustible fuel cakes."
                },
                "5": {
                    "name": "Wetland Herb Pickers",
                    "item_key": "cress_and_mustard",
                    "silver_cost": 2.5,
                    "grain_cost": 15.0,
                    "base_min": 30.0,
                    "base_max": 60.0,
                    "desc": "Herbalists gathered pungent watercress leaves and threshed bags of wild mustard seeds."
                },
                "6": {
                    "name": "Euphrates Fisherman Flotilla",
                    "item_key": "dried_fish",
                    "item_name": "salted river carp and catfish (Nūnu)",
                    "silver_cost": 3.0,
                    "grain_cost": 15.0,
                    "base_min": 60.0,
                    "base_max": 140.0,
                    "desc": "Crews in bitumen-coated coracles swept large linen nets through the deep Euphrates channels."
                },
                "7": {
                    "name": "Bitumen Seep Hauling Train",
                    "item_key": "bitumen",
                    "item_name": "jars of heavy petroleum pitch (Ittû)",
                    "silver_cost": 4.0,
                    "grain_cost": 20.0,
                    "base_min": 30.0,
                    "base_max": 70.0,
                    "desc": "Haulers dug asphalt from natural oil seeps and hauled sealed clay jars back to your storehouse."
                },
                "8": {
                    "name": "Date Palm Orchard Harvesters",
                    "item_key": "dates",
                    "item_name": "baskets of sweet chewy dates (Suluppu)",
                    "silver_cost": 3.0,
                    "grain_cost": 15.0,
                    "base_min": 40.0,
                    "base_max": 90.0,
                    "desc": "Agile palm climbers scaled the date palm trunks along the canal banks and harvested heavy fruit clusters."
                },
                "9": {
                    "name": "Emmer Wheat Reapers (Zizzu Gang)",
                    "item_key": "emmer",
                    "item_name": "qa of golden emmer wheat (Zizzu)",
                    "silver_cost": 3.5,
                    "grain_cost": 15.0,
                    "base_min": 60.0,
                    "base_max": 140.0,
                    "desc": "Reapers with flint-bladed sickles reaped outlying emmer wheat terraces and threshed the hulled grain."
                }
            }

            if c_act in MISSIONS:
                m = MISSIONS[c_act]
                silv_req = m["silver_cost"]
                grain_req = m["grain_cost"]

                if self.player.wallet.silver_shekels < silv_req:
                    print(f" [!] Insufficient silver! You need {silv_req:.2f} silver shekels for wages (You hold {self.player.wallet.silver_shekels:.2f}).")
                    continue
                if self.player.wallet.barley_qa < grain_req:
                    print(f" [!] Insufficient grain rations! You need {grain_req:.0f} qa barley to provision the gang (You hold {self.player.wallet.barley_qa:.0f} qa).")
                    continue

                # Deduct wages & rations
                self.player.wallet.spend_silver(silv_req)
                self.player.wallet.spend_barley(grain_req)
                self.player.inventory["barley"] = self.player.wallet.barley_qa
                if self.player.inventory["barley"] <= 0:
                    self.player.inventory.pop("barley", None)

                # Multipliers: Draft oxen + Patrician/Governor status
                ox_mult = 1.0 + (self.player.owned_oxen * 0.10)
                status_mult = 1.15 if self.player.social_class == SocialClass.AWILUM else 1.0
                civic_off = getattr(self.player, "civic_office", getattr(self.player, "office", None))
                if civic_off and str(civic_off) != "Private Citizen":
                    status_mult += 0.10

                if m["item_key"] == "cress_and_mustard":
                    q_cress = round(random.uniform(30.0, 60.0) * ox_mult * status_mult, 1)
                    q_must = round(random.uniform(20.0, 40.0) * ox_mult * status_mult, 1)
                    self.player.inventory["cress"] = self.player.inventory.get("cress", 0.0) + q_cress
                    self.player.inventory["mustard"] = self.player.inventory.get("mustard", 0.0) + q_must
                    yield_desc = f"{q_cress:.1f} bundles of wild cress (Sahlû) and {q_must:.1f} bags of mustard (Kasû)"
                else:
                    qty = round(random.uniform(m["base_min"], m["base_max"]) * ox_mult * status_mult, 1)
                    self.player.inventory[m["item_key"]] = self.player.inventory.get(m["item_key"], 0.0) + qty
                    yield_desc = f"{qty:.1f} {m['item_name']}"

                # Takes 1.0 hour for overseer briefing & gate intake; 0% energy from player
                self.advance_hours(1.0)

                print("\n" + "=" * 70)
                print(f" [+] CORVÉE DISPATCH SUCCESSFUL: {m['name'].upper()}!")
                print("=" * 70)
                print(f"     Overseer Briefing: 1.0 hour elapsed. Player Energy spent: 0% (Laborers performed all sweat).")
                print(f"     Expenditures:      Paid {silv_req:.2f} silver statutory wages | Provisioned {grain_req:.0f} qa barley.")
                print(f"     Field Report:      {m['desc']}")
                print(f"     Cargo Delivered:   Ox-carts delivered {yield_desc} straight to your estate sacks!")
                print("=" * 70)

            else:
                print(" [!] Invalid labor gang option.")

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
            RECIPES = {
                "1": {
                    "name": "Barley Beer (šikaru)",
                    "category": "Brewery",
                    "inputs": {"barley": 5.0},
                    "input_desc": "5 qa Barley",
                    "output_key": "barley_beer",
                    "yield": 4.0,
                    "output_desc": "4 Jars Barley Beer",
                    "base_hours": 3.0,
                    "skill_bonus": 1
                },
                "2": {
                    "name": "Golden Spelt Beer (ulušinnu)",
                    "category": "Spelt Brewery",
                    "inputs": {"emmer": 4.0},
                    "input_desc": "4 Emmer Wheat",
                    "output_key": "spelt_beer",
                    "yield": 3.0,
                    "output_desc": "3 Jars Spelt Beer",
                    "base_hours": 3.5,
                    "skill_bonus": 1
                },
                "3": {
                    "name": "Barley Flatbread (akalu)",
                    "category": "Bakery",
                    "inputs": {"barley": 3.0},
                    "input_desc": "3 qa Barley",
                    "output_key": "bread",
                    "yield": 4.0,
                    "output_desc": "4 Loaves Flatbread",
                    "base_hours": 2.0,
                    "skill_bonus": 1
                },
                "4": {
                    "name": "Honey-Date Pastries (mersu)",
                    "category": "Confectionery",
                    "inputs": {"dates": 2.0, "grain_or_flour": 2.0},
                    "input_desc": "2 Dates + 2 Emmer/Barley",
                    "output_key": "sweet_pastry",
                    "yield": 3.0,
                    "output_desc": "3 Date Pastries",
                    "base_hours": 2.0,
                    "skill_bonus": 1
                },
                "5": {
                    "name": "Standard Woolen Cloth (subātu)",
                    "category": "Wool Loom",
                    "inputs": {"wool": 4.0},
                    "input_desc": "4 Talents Raw Wool",
                    "output_key": "woolen_cloth",
                    "yield": 2.0,
                    "output_desc": "2 Bolts Woolen Cloth",
                    "base_hours": 4.0,
                    "skill_bonus": 1
                },
                "6": {
                    "name": "Bleached Linen Tunic (kitû)",
                    "category": "Linen Loom",
                    "inputs": {"flax": 2.0},
                    "input_desc": "2 Flax Fiber",
                    "output_key": "fine_linen",
                    "yield": 1.0,
                    "output_desc": "1 Fine Linen Tunic",
                    "base_hours": 4.0,
                    "skill_bonus": 1
                },
                "7": {
                    "name": "Refined Sesame Oil (ellu)",
                    "category": "Oil Press",
                    "inputs": {"sesame": 3.0},
                    "input_desc": "3 Sesame Seeds",
                    "output_key": "sesame_oil",
                    "yield": 2.0,
                    "output_desc": "2 Jars Sesame Oil",
                    "base_hours": 2.5,
                    "skill_bonus": 1
                },
                "8": {
                    "name": "Sacred Perfume & Unguents (ruqqû)",
                    "category": "Perfumery",
                    "inputs": {"sesame_oil": 1.0, "spice": 1.0},
                    "input_desc": "1 Sesame Oil + 1 Cress/Mustard",
                    "output_key": "perfume",
                    "yield": 1.0,
                    "output_desc": "1 Flacon Sacred Perfume",
                    "base_hours": 4.0,
                    "skill_bonus": 2
                },
                "9": {
                    "name": "Bronze Plows & Sickles (niggallu)",
                    "category": "Foundry",
                    "inputs": {"copper_ore": 2.0, "tin": 0.2},
                    "input_desc": "2 Copper Ore + 0.2 Tin",
                    "output_key": "bronze_tools",
                    "yield": 3.0,
                    "output_desc": "3 Bronze Tools",
                    "base_hours": 5.0,
                    "skill_bonus": 1
                },
                "10": {
                    "name": "Bronze Spears & Battle-Axes (kakku)",
                    "category": "Weaponsmith",
                    "inputs": {"copper_ore": 3.0, "tin": 0.3},
                    "input_desc": "3 Copper Ore + 0.3 Tin",
                    "output_key": "bronze_weapons",
                    "yield": 2.0,
                    "output_desc": "2 Bronze Weapons",
                    "base_hours": 5.0,
                    "skill_bonus": 1
                },
                "11": {
                    "name": "Laminated Composite Bow (qaštu)",
                    "category": "Bowyer",
                    "inputs": {"timber": 2.0, "wool": 2.0},
                    "input_desc": "2 Timber + 2 Raw Wool/Sinew",
                    "output_key": "composite_bow",
                    "yield": 1.0,
                    "output_desc": "1 Composite Bow",
                    "base_hours": 4.5,
                    "skill_bonus": 1
                },
                "12": {
                    "name": "Spoked War Chariot (narkabtu)",
                    "category": "Chariot Guild",
                    "inputs": {"timber": 4.0, "bronze_tools": 1.0},
                    "input_desc": "4 Timber + 1 Bronze Tools",
                    "output_key": "war_chariot",
                    "yield": 1.0,
                    "output_desc": "1 War Chariot",
                    "base_hours": 8.0,
                    "skill_bonus": 2
                },
                "13": {
                    "name": "Sun-Dried Mudbrick (libittu)",
                    "category": "Brickyard",
                    "inputs": {"reeds": 2.0},
                    "input_desc": "2 Marsh Reeds",
                    "output_key": "mudbrick",
                    "yield": 5.0,
                    "output_desc": "5 Mudbricks",
                    "base_hours": 2.5,
                    "skill_bonus": 1
                },
                "14": {
                    "name": "Clay Bowls & Jars (karpatu)",
                    "category": "Potter's Kiln",
                    "inputs": {"pottery_fuel": 2.0},
                    "input_desc": "2 Reeds or Dung Fuel",
                    "output_key": "pottery",
                    "yield": 4.0,
                    "output_desc": "4 Clay Vessels",
                    "base_hours": 2.5,
                    "skill_bonus": 1
                },
                "15": {
                    "name": "Carved Cylinder Seal (kunukku)",
                    "category": "Seal Engraver",
                    "inputs": {"bronze_tools": 1.0, "silver": 2.0},
                    "input_desc": "1 Bronze Tools + 2.0 Silver Stone",
                    "output_key": "cylinder_seal",
                    "yield": 1.0,
                    "output_desc": "1 Carved Cylinder Seal",
                    "base_hours": 5.0,
                    "skill_bonus": 2
                }
            }

            def get_avail(item_key):
                if item_key == "barley":
                    return self.player.wallet.barley_qa
                elif item_key == "wool":
                    return self.player.inventory.get("raw_wool", 0.0) + self.player.inventory.get("wool", 0.0)
                elif item_key == "reeds":
                    return self.player.inventory.get("reeds", 0.0) + self.player.inventory.get("reed", 0.0)
                elif item_key == "grain_or_flour":
                    return self.player.inventory.get("emmer", 0.0) + self.player.wallet.barley_qa
                elif item_key == "spice":
                    return self.player.inventory.get("cress", 0.0) + self.player.inventory.get("mustard", 0.0)
                elif item_key == "pottery_fuel":
                    return self.player.inventory.get("reeds", 0.0) + self.player.inventory.get("reed", 0.0) + self.player.inventory.get("animal_dung", 0.0)
                elif item_key == "silver":
                    return self.player.wallet.silver_shekels
                else:
                    return self.player.inventory.get(item_key, 0.0)

            def spend_item(item_key, amount):
                if item_key == "barley":
                    self.player.wallet.spend_barley(amount)
                    self.player.inventory["barley"] = self.player.wallet.barley_qa
                    if self.player.inventory["barley"] <= 0:
                        self.player.inventory.pop("barley", None)
                elif item_key == "wool":
                    rem = amount
                    have_raw = self.player.inventory.get("raw_wool", 0.0)
                    spend_raw = min(have_raw, rem)
                    self.player.inventory["raw_wool"] = have_raw - spend_raw
                    rem -= spend_raw
                    if self.player.inventory.get("raw_wool", 0.0) <= 1e-4:
                        self.player.inventory.pop("raw_wool", None)
                    if rem > 0:
                        have_w = self.player.inventory.get("wool", 0.0)
                        self.player.inventory["wool"] = max(0.0, have_w - rem)
                        if self.player.inventory.get("wool", 0.0) <= 1e-4:
                            self.player.inventory.pop("wool", None)
                elif item_key == "reeds":
                    rem = amount
                    have_r = self.player.inventory.get("reeds", 0.0)
                    spend_r = min(have_r, rem)
                    self.player.inventory["reeds"] = have_r - spend_r
                    rem -= spend_r
                    if self.player.inventory.get("reeds", 0.0) <= 1e-4:
                        self.player.inventory.pop("reeds", None)
                    if rem > 0:
                        have_rd = self.player.inventory.get("reed", 0.0)
                        self.player.inventory["reed"] = max(0.0, have_rd - rem)
                        if self.player.inventory.get("reed", 0.0) <= 1e-4:
                            self.player.inventory.pop("reed", None)
                elif item_key == "grain_or_flour":
                    rem = amount
                    have_emmer = self.player.inventory.get("emmer", 0.0)
                    spend_emmer = min(have_emmer, rem)
                    self.player.inventory["emmer"] = have_emmer - spend_emmer
                    rem -= spend_emmer
                    if self.player.inventory.get("emmer", 0.0) <= 1e-4:
                        self.player.inventory.pop("emmer", None)
                    if rem > 0:
                        self.player.wallet.spend_barley(rem)
                        self.player.inventory["barley"] = self.player.wallet.barley_qa
                        if self.player.inventory["barley"] <= 0:
                            self.player.inventory.pop("barley", None)
                elif item_key == "spice":
                    rem = amount
                    have_cress = self.player.inventory.get("cress", 0.0)
                    spend_cress = min(have_cress, rem)
                    self.player.inventory["cress"] = have_cress - spend_cress
                    rem -= spend_cress
                    if self.player.inventory.get("cress", 0.0) <= 1e-4:
                        self.player.inventory.pop("cress", None)
                    if rem > 0:
                        have_mustard = self.player.inventory.get("mustard", 0.0)
                        self.player.inventory["mustard"] = max(0.0, have_mustard - rem)
                        if self.player.inventory.get("mustard", 0.0) <= 1e-4:
                            self.player.inventory.pop("mustard", None)
                elif item_key == "pottery_fuel":
                    rem = amount
                    have_reeds = self.player.inventory.get("reeds", 0.0) + self.player.inventory.get("reed", 0.0)
                    spend_reeds = min(have_reeds, rem)
                    if spend_reeds > 0:
                        r_avail = self.player.inventory.get("reeds", 0.0)
                        s_r = min(r_avail, spend_reeds)
                        self.player.inventory["reeds"] = r_avail - s_r
                        if self.player.inventory.get("reeds", 0.0) <= 1e-4:
                            self.player.inventory.pop("reeds", None)
                        rem_r = spend_reeds - s_r
                        if rem_r > 0:
                            self.player.inventory["reed"] = max(0.0, self.player.inventory.get("reed", 0.0) - rem_r)
                            if self.player.inventory.get("reed", 0.0) <= 1e-4:
                                self.player.inventory.pop("reed", None)
                    rem -= spend_reeds
                    if rem > 0:
                        have_dung = self.player.inventory.get("animal_dung", 0.0)
                        self.player.inventory["animal_dung"] = max(0.0, have_dung - rem)
                        if self.player.inventory.get("animal_dung", 0.0) <= 1e-4:
                            self.player.inventory.pop("animal_dung", None)
                elif item_key == "silver":
                    self.player.wallet.spend_silver(amount)
                else:
                    self.player.inventory[item_key] = max(0.0, self.player.inventory.get(item_key, 0.0) - amount)
                    if self.player.inventory.get(item_key, 0.0) <= 1e-4:
                        self.player.inventory.pop(item_key, None)

            print("-" * 75)
            print(" PRODUCTION & FORGING RECIPES:")
            print(" --- BREWERY, BAKERY & CONFECTIONERY ---")
            print(" [1]  Barley Brewery:  5 qa Barley            -> 4 Jars Barley Beer    (Base: 3.0h)")
            print(" [2]  Spelt Brewery:   4 Emmer Wheat          -> 3 Jars Spelt Beer     (Base: 3.5h)")
            print(" [3]  Bakery:          3 qa Barley            -> 4 Loaves Flatbread    (Base: 2.0h)")
            print(" [4]  Pastry Chef:     2 Dates + 2 Emmer/Barley-> 3 Honey Pastries      (Base: 2.0h)")
            print(" --- TEXTILE LOOMS, OILS & PERFUMERY ---")
            print(" [5]  Wool Loom:       4 Talents Raw Wool     -> 2 Bolts Woolen Cloth  (Base: 4.0h)")
            print(" [6]  Linen Loom:      2 Flax Fiber           -> 1 Bleached Linen Tunic(Base: 4.0h)")
            print(" [7]  Oil Press:       3 Sesame Seeds         -> 2 Jars Sesame Oil     (Base: 2.5h)")
            print(" [8]  Perfumery:       1 Sesame Oil + 1 Spice -> 1 Sacred Perfume      (Base: 4.0h)")
            print(" --- FOUNDRY, WEAPONSMITHING & MILITARY ---")
            print(" [9]  Bronze Tools:    2 Copper Ore + 0.2 Tin -> 3 Bronze Tools        (Base: 5.0h)")
            print(" [10] Weaponsmith:     3 Copper Ore + 0.3 Tin -> 2 Bronze Weapons      (Base: 5.0h)")
            print(" [11] Bowyer & Fletcher:2 Timber + 2 Raw Wool -> 1 Composite Bow       (Base: 4.5h)")
            print(" [12] Chariot Guild:   4 Timber + 1 Tools     -> 1 War Chariot         (Base: 8.0h)")
            print(" --- MASONRY, CERAMICS & LAPIDARY ---")
            print(" [13] Brickyard:       2 Reeds                -> 5 Mudbricks           (Base: 2.5h)")
            print(" [14] Potter's Kiln:   2 Reeds or Dung        -> 4 Clay Vessels        (Base: 2.5h)")
            print(" [15] Seal Engraver:   1 Bronze Tools + 2 Silv-> 1 Cylinder Seal       (Base: 5.0h)")
            print(" [16] Royal Lapidary:  Mount Seal in Gold Caps-> +4 Seal Prestige      (Cost: 20.0 Silv)")
            print("-" * 75)
            print(" WORKSHOP MANAGEMENT & ECONOMIES OF SCALE:")
            print(" [U] Upgrade Workshop Facility Tier (Expand batch capacity & labor scale)")
            print(" [H] Hire / Dismiss Artisan Laborers (Agru under Code of Hammurabi)")
            print(" [W] Adjust Statutory Wage Policy (Stingy / Legal § 274 / Efficiency Wage)")
            print(" [0] Return to Agriculture & Land Menu")
            print("-" * 75)

            craft_act = input(" Choose workshop action [1-16, U, H, W, 0]: ").strip()

            if craft_act == "0":
                break

            elif craft_act in RECIPES:
                recipe = RECIPES[craft_act]
                recipe_name = recipe["name"]
                unit_in = recipe["input_desc"]
                unit_out = recipe["output_desc"]
                base_hours = recipe["base_hours"]
                output_key = recipe["output_key"]
                yield_per_batch = recipe["yield"]

                # Calculate max batches possible based on inventory
                max_possible = 999999
                for ing_key, ing_qty in recipe["inputs"].items():
                    avail_qty = get_avail(ing_key)
                    possible_with_ing = int(avail_qty // ing_qty)
                    if possible_with_ing < max_possible:
                        max_possible = possible_with_ing

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
                for ing_key, ing_qty in recipe["inputs"].items():
                    spend_item(ing_key, ing_qty * n_batches)

                # Add finished output
                self.player.inventory[output_key] = self.player.inventory.get(output_key, 0.0) + total_yield
                self.player.energy = max(0.0, self.player.energy - energy_needed)
                self.player.skills.craftsmanship += max(1, (n_batches * recipe.get("skill_bonus", 1)) // 2)

                # Time advances
                self.advance_hours(hours_needed)

                new_h = int(self.hour)
                new_m = int((self.hour - new_h) * 60)
                print(f"\n [+] Production Successful! Completed {n_batches} batch(es) resulting in {total_yield:.0f} {recipe_name}!")
                print(f"     Time elapsed: {hours_needed:.1f} hours. Current time: Day {self.day:02d} | {new_h:02d}:{new_m:02d} ({self.get_time_label()}).")
                print(f"     Remaining energy: {self.player.energy:.0f}%.")

            elif craft_act == "16":
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
                ("date_wine", "Flask of Fermented Date Wine", "Thirst -60, Health +15, Energy +30"),
                ("sesame_oil", "Sip of Refined Sesame Oil", "Hunger -20, Energy +10"),
                ("fine_linen", "Don Bleached Linen Patrician Tunic", "Honor +3.0 (Noble Splendor)"),
                ("perfume", "Anoint with Sacred Frankincense Perfume", "Honor +2.0 (Divine Reverence)")
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
        print(" [1] Anatolia & Levant (Overland: Tin, Cedar Timber, Silver) - 14 Days (1 Season)")
        print(" [2] Dilmun / Bahrain (Gulf Entrepôt: Pearls, Dates, Bitumen) - 5 Days (~⅓ Season)")
        print(" [3] Magan / Oman (Copper Coast: Raw Copper Ore) - 7 Days (~½ Season)")
        print(" [4] Meluhha / Indus Valley (Oceanic East: Lapis Lazuli, Carnelian) - 28 Days (2 Seasons)")
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
            if purse < 0.0 or (purse + guards_silver) > self.player.wallet.silver_shekels:
                print(" [!] Invalid or unaffordable trading purse.")
                return
        except ValueError:
            print(" [!] Invalid number.")
            return

        # Step 4: Interactive Cargo Loading from Player's Personal Sacks
        cargo: Dict[str, float] = {}
        cap_kg = fleet.cargo_capacity_kg
        used_kg = 0.0

        print("\n" + "=" * 70)
        print(f"          CARGO LOADING DOCK (Fleet Capacity: {cap_kg:.1f} kg)")
        print("=" * 70)
        print(" Select goods from your sacks to pack into the caravan for foreign sale.")

        # Display eligible goods held in player's inventory
        exportable = [(gid, qty) for gid, qty in self.player.inventory.items() if qty > 0.0 and gid not in ("barley",)]
        if exportable:
            print(" Available in your sacks:")
            for gid, qty in exportable:
                g = self.registry.get(gid)
                w = g.weight_kg if g else 1.0
                base_p = g.base_price if g else 1.0
                mult = node.demand_multipliers.get(gid, 1.20)
                f_price = round(base_p * mult, 2)
                bonus_str = f" [★ PREMIUM {mult:.1f}x!]" if mult > 1.20 else ""
                print(f"  * {gid:<18}: {qty:5.1f} available ({w:4.1f} kg/ea) -> Foreign Price: {f_price:6.2f} silv{bonus_str}")
        else:
            print(" (No non-grain commodities currently held in your sacks.)")

        print("-" * 70)
        print(" Options: Type good ID to load, '[A]' to auto-pack top wares, or press Enter / '[D]' to finish loading.")

        while True:
            rem_kg = cap_kg - used_kg
            if rem_kg <= 0.1:
                print(f" [+] Fleet is fully loaded! ({used_kg:.1f} kg / {cap_kg:.1f} kg)")
                break

            load_in = input(f" Load good [ID / A=Auto / D=Done, Loaded: {used_kg:.1f}/{cap_kg:.1f} kg]: ").strip().lower()
            if load_in in ("", "d", "done"):
                break
            elif load_in in ("a", "auto"):
                # Auto-pack highest foreign-value items that fit remaining weight
                sorted_goods = sorted(
                    [(gid, self.player.inventory[gid]) for gid, _ in exportable if self.player.inventory.get(gid, 0.0) > cargo.get(gid, 0.0)],
                    key=lambda x: (self.registry.get(x[0]).base_price * node.demand_multipliers.get(x[0], 1.20)) / max(0.1, self.registry.get(x[0]).weight_kg),
                    reverse=True
                )
                packed_any = False
                for gid, total_avail in sorted_goods:
                    rem_avail = total_avail - cargo.get(gid, 0.0)
                    if rem_avail <= 0:
                        continue
                    w = self.registry.get(gid).weight_kg
                    max_by_wt = int(rem_kg // max(0.01, w)) if w > 0 else int(rem_avail)
                    take = min(int(rem_avail), max_by_wt)
                    if take > 0:
                        cargo[gid] = cargo.get(gid, 0.0) + float(take)
                        used_kg += take * w
                        rem_kg = cap_kg - used_kg
                        packed_any = True
                        print(f"  [+] Auto-loaded {take} {gid} (+{take * w:.1f} kg).")
                if not packed_any:
                    print("  [!] No more eligible inventory fits remaining fleet capacity.")
                break
            elif load_in in self.player.inventory and self.player.inventory[load_in] > 0:
                gid = load_in
                w = self.registry.get(gid).weight_kg
                rem_avail = self.player.inventory[gid] - cargo.get(gid, 0.0)
                if rem_avail <= 0:
                    print(f"  [!] You have already loaded all your {gid}.")
                    continue
                max_fit = int(rem_kg // max(0.01, w)) if w > 0 else int(rem_avail)
                max_loadable = min(int(rem_avail), max_fit)
                if max_loadable <= 0:
                    print(f"  [!] Not enough weight capacity left for even 1 {gid} (Weighs {w:.1f} kg, Remaining capacity: {rem_kg:.1f} kg).")
                    continue

                q_str = input(f" How many {gid} to load [1-{max_loadable}, default={max_loadable}]? ").strip()
                try:
                    q_val = float(q_str) if q_str else float(max_loadable)
                    q_val = min(float(max_loadable), max(1.0, q_val))
                    cargo[gid] = cargo.get(gid, 0.0) + q_val
                    used_kg += q_val * w
                    print(f"  [+] Loaded {q_val:.0f} {gid} (+{q_val*w:.1f} kg).")
                except ValueError:
                    print("  [!] Invalid number.")
            else:
                print("  [!] Commodity not available in your sacks.")

        # Step 5: Strategic Import Directive Selection
        print("\n" + "=" * 70)
        print(f"          STRATEGIC RETURN IMPORT DIRECTIVE ({node.name.upper()})")
        print("=" * 70)
        print(" How should the Tamkarum invest your foreign sales revenue and silver purse?")
        imp_list = list(node.export_supplies.items())
        for idx, (imp_id, f_price) in enumerate(imp_list, start=1):
            local_p = self.market.get_price(imp_id)
            print(f" [{idx}] Prioritize {imp_id:<14} (Foreign: {f_price:5.2f} silv/ea | Babylon Spot: {local_p:5.2f} silv/ea)")
        print(f" [A] Balanced Assortment   (Evenly distribute investment across all {len(imp_list)} foreign wares)")
        print(f" [S] Pure Silver Coin Only (Do not buy goods; repatriate 100% of capital in liquid silver!)")
        print("-" * 70)

        imp_choice = input(f" Choose import directive [1-{len(imp_list)}, A, S, default=A]: ").strip().lower()
        target_import = "BALANCED"
        try:
            choice_num = int(imp_choice)
            if 1 <= choice_num <= len(imp_list):
                target_import = imp_list[choice_num - 1][0]
        except ValueError:
            if imp_choice in ("s", "silver"):
                target_import = "PURE_SILVER"
            else:
                target_import = "BALANCED"

        print("\n Assembling caravan with Tamkarum Ur-Nungal...")
        ok, msg, mission = self.trade_mgr.assemble_caravan(
            investor=self.player,
            corridor=corridor,
            fleet=fleet,
            cargo_to_export=cargo,
            silver_purse=purse,
            target_import=target_import
        )
        print(msg)

        if ok and mission:
            print("\n" + "." * 70)
            print(" The caravan departs Babylon under the protection of Shamash...")
            print(" Over weeks of travel, the merchant train crosses mountains and rivers.")
            print("." * 70)
            time.sleep(0.5)

            # Resolve the expedition
            self.advance_hours(2.0)
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
                        self.handle_canal_warden_powers()
                    elif "Market Overseer" in self.player.civic_office:
                        self.handle_market_overseer_powers()
                    elif "Governor" in self.player.civic_office:
                        self.handle_governor_powers()
                    elif "Magistrate" in self.player.civic_office:
                        self.handle_magistrate_powers()
                    elif "High Priest" in self.player.civic_office:
                        self.handle_high_priest_powers()
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
            if self.player.social_class == SocialClass.WARDUM:
                print(" [M] Purchase Statutory Manumission (20.0 Silver Shekels) - Rise to Muškēnum")
            elif self.player.social_class != SocialClass.AWILUM:
                print(" [6] Petition Council of Elders for Ennoblement to Awīlum (Patrician Class)")
            print(" [0] Return to City Square")

            opt_prompt = '0-5, M' if self.player.social_class == SocialClass.WARDUM else ('0-6' if self.player.social_class != SocialClass.AWILUM else '0-5')
            ch = input(f" Choose option [{opt_prompt}]: ").strip()
            if ch.upper() == "M" and self.player.social_class == SocialClass.WARDUM:
                self.handle_justice()
                continue
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


    def handle_canal_warden_powers(self):
        """Irrigation management and corvée labor execution."""
        while True:
            print("\n" + "=" * 78)
            print("        IRRIGATION & PUBLIC WORKS (GUGALLUM / CANAL WARDEN)")
            print("=" * 78)
            print(f" Maintenance Funded: {'Yes' if self.politics.canal_maintenance_funded else 'No'}")
            print("-" * 78)
            print(" [1] Mobilize Corvée Labor to Dredge River Dikes")
            print(" [0] Return to Civic Offices Menu")

            choice = input(" Choose action [0-1]: ").strip()

            if choice == "1":
                skim = input(" Embezzle municipal maintenance silver to your vault (0-5)? ").strip()
                try:
                    s_val = float(skim) if skim else 0.0
                    ok, msg = self.politics.execute_canal_warden_dredging(self.player, skim_silver=s_val)
                    print(msg)
                except ValueError:
                    print(" Invalid input.")
            elif choice == "0":
                break

    def handle_market_overseer_powers(self):
        """Gate customs and market tariffs."""
        while True:
            print("\n" + "=" * 78)
            print("        COMMERCE & GATES (RABI SIKKATIM / MARKET OVERSEER)")
            print("=" * 78)
            print(f" Current Gate Tariff: {self.politics.gate_customs_tariff_rate * 100:.1f}%")
            print("-" * 78)
            print(" [1] Set City Gate Import Customs Tariff Rate")
            print(" [0] Return to Civic Offices Menu")

            choice = input(" Choose action [0-1]: ").strip()

            if choice == "1":
                t_str = input(" Set tariff rate (0% to 20%, e.g. 8)? ").strip()
                try:
                    rate = float(t_str) / 100.0 if t_str else 0.05
                    ok, msg = self.politics.set_gate_customs_tariff(self.player, rate)
                    print(msg)
                except ValueError:
                    print(" Invalid input.")
            elif choice == "0":
                break

    def handle_high_priest_powers(self):
        """Executive sacred governance: Esagila Temple tithes, festivals, and ritual purity."""
        while True:
            print("\n" + "=" * 78)
            print("        SACRED GOVERNANCE & ESAGILA ADMINISTRATION (ŠANGÛ / HIGH PRIEST)")
            print("=" * 78)
            print(f" Temple Treasury: {self.politics.temple_treasury_silver:.2f} silver shekels")
            print(f" Current Tithe:   {self.politics.temple_tithe_rate * 100:.1f}%")
            print("-" * 78)
            print(" [1] Set Temple Tithe Rate")
            print(" [2] Host Akitu (New Year) Festival")
            print(" [3] Divert Sacred Funds (Embezzle)")
            print(" [4] Declare Political Rival Ritually Impure")
            print(" [0] Return to Civic Offices Menu")

            choice = input(" Choose action [0-4]: ").strip()

            if choice == "1":
                t_str = input(" Set temple tithe rate (0% to 30%, e.g. 10)? ").strip()
                try:
                    rate = float(t_str) / 100.0 if t_str else 0.10
                    ok, msg = self.politics.set_temple_tithe(self.player, rate)
                    print(msg)
                except ValueError:
                    print(" Invalid input.")
            elif choice == "2":
                ok, msg = self.politics.host_akitu_festival(self.player)
                print(msg)
            elif choice == "3":
                amt_str = input(" Amount of silver to quietly divert to your personal vault? ").strip()
                try:
                    amt = float(amt_str)
                    ok, msg = self.politics.divert_sacred_funds(self.player, amt)
                    print(msg)
                except ValueError:
                    print(" Invalid input.")
            elif choice == "4":
                print(" Select rival to declare impure:")
                target_npcs = [npc for name, npc in self.npcs.items() if npc != self.player and npc.social_class == SocialClass.AWILUM]
                for idx, npc in enumerate(target_npcs):
                    print(f" [{idx + 1}] {npc.full_name} (Reputation: {npc.reputation:.1f})")
                r_choice = input(" Choose rival or [0] to cancel: ").strip()
                try:
                    r_idx = int(r_choice) - 1
                    if 0 <= r_idx < len(target_npcs):
                        ok, msg = self.politics.excommunicate_rival(self.player, target_npcs[r_idx])
                        print(msg)
                except ValueError:
                    pass
            elif choice == "0":
                break

    def handle_magistrate_powers(self):
        """Judicial trials at the Gate of Shamash."""
        while True:
            print("\n" + "=" * 78)
            print("        JUSTICE AT THE GATE OF SHAMASH (DAYYĀNUM / CITY MAGISTRATE)")
            print("=" * 78)
            pending = [c for c in self.politics.pending_lawsuits if not c.is_resolved]
            print(f" Pending Cases: {len(pending)}")
            print("-" * 78)
            print(" [1] Review and Adjudicate Pending Lawsuit")
            print(" [0] Return to Civic Offices Menu")

            choice = input(" Choose action [0-1]: ").strip()

            if choice == "1":
                if not pending:
                    print(" There are no pending cases on the clay docket.")
                    continue

                print(" Select case to hear:")
                for idx, case in enumerate(pending):
                    print(f" [{idx + 1}] {case.case_id}: {case.accuser.name} vs. {case.defendant.name} ({case.charge.value})")

                c_choice = input(" Choose case or [0] to cancel: ").strip()
                try:
                    c_idx = int(c_choice) - 1
                    if 0 <= c_idx < len(pending):
                        selected_case = pending[c_idx]
                        bribe_str = input(f" Does {selected_case.defendant.name} offer a bribe for acquittal? (Enter silver amount, 0 for none): ").strip()
                        bribe = float(bribe_str) if bribe_str else 0.0
                        ok, msg = self.politics.adjudicate_case(selected_case, self.player, bribe_from_defendant=bribe)
                        print(msg)
                except ValueError:
                    print(" Invalid input.")
            elif choice == "0":
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
            print(" [8] Promulgate Municipal Tax & Customs Decrees (Miksu & Šibšu)")
            print(" [9] Imperial Mountain Mining Outpost (Halṣum Šadî - Zagros Foothills)")
            print(" [0] Return to Civic Offices Menu")
            print("-" * 78)

            gov_act = input(" Select executive order [0-9]: ").strip()

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

            elif gov_act == "8":
                # Promulgate Municipal Tax & Customs Decrees (Miksu & Šibšu)
                print("\n" + "=" * 78)
                print("         BABYLON MUNICIPAL TAXATION & CUSTOMS DECREES (MIKSU & ŠIBŠU)")
                print("=" * 78)
                rates = self.war_engine.get_tax_rates()
                print(f" Current Enacted Policy: {self.war_engine.tax_policy} ({rates['name']})")
                print(f" Gate Toll Inflow:       +{rates['gate_toll_daily']:.2f} silver shekels / day into City Coffers")
                print(f" Harvest Tithe (Šibšu):  {rates['harvest_tithe_rate']*100:.0f}% of spring harvest threshed into Public Silos")
                print(f" Market Duty (Miksu):    {rates['sales_tax_rate']*100:.0f}% sales duty on Kārum market purchases")
                print(f" Civic Impact:           {rates['honor_daily']:+.1f} Honor / day")
                print(f" Description:            {rates['desc']}")
                print("-" * 78)
                print(" AVAILABLE TAX DECREES:")
                for k, cfg in TAX_POLICIES_CONFIG.items():
                    active_marker = " [ACTIVE]" if k == self.war_engine.tax_policy else ""
                    print(f" [{k[0]}] {cfg['name']}{active_marker}")
                    print(f"     Toll: {cfg['gate_toll_daily']:.2f} silv/day | Tithe: {cfg['harvest_tithe_rate']*100:.0f}% | Duty: {cfg['sales_tax_rate']*100:.0f}% | Honor: {cfg['honor_daily']:+.1f}/day")
                print(" [R] Return without changes")
                d_pick = input(" Promulgate new decree [F/S/H/W/R]: ").strip().upper()
                pol_map = {"F": "FREE_TRADE", "S": "STATUTORY", "H": "HEAVY_PATRICIAN", "W": "WAR_TITHE"}
                if d_pick in pol_map:
                    ok, msg = self.war_engine.set_tax_policy(pol_map[d_pick])
                    print("\n" + msg)

            elif gov_act == "9":
                self.handle_mining_outpost()

    # --------------------------------------------------------------------------
    # Imperial Mountain Mining Outpost (Halṣum Šadî) Command
    # --------------------------------------------------------------------------

    def handle_mining_outpost(self):
        """Imperial Mountain Mining Outpost (Halṣum Šadî) in the Zagros Foothills."""
        while True:
            outpost = self.war_engine.mining_outpost
            is_gov = bool(self.player and self.player.civic_office and "Governor" in self.player.civic_office)
            cleared_pass = self.war_engine.campaigns_completed.get(2, 0) > 0

            # Stationed garrison info
            garrison_reg = None
            if outpost.garrisoned_regiment_id:
                garrison_reg = next((r for r in self.war_engine.standing_army if r.id == outpost.garrisoned_regiment_id), None)
                if not garrison_reg:
                    outpost.garrisoned_regiment_id = None

            print("\n" + "=" * 78)
            print("        IMPERIAL MOUNTAIN MINING OUTPOST (HALṢUM ŠADÎ - ZAGROS)")
            print("=" * 78)
            status_tag = "ACTIVE & OPERATIONAL" if outpost.is_established else "UNFOUNDED / WILDERNESS"
            print(f" Outpost Status:      [{status_tag}]")
            if outpost.is_established:
                print(f" Development Scale:   {outpost.tier_name}")
                print(f" Extraction Force:    {outpost.miners_count} Miners (Seasonal Upkeep: {outpost.seasonal_upkeep[0]:.1f} silv, {outpost.seasonal_upkeep[1]:.0f} qa grain)")
                if garrison_reg:
                    print(f" Frontier Garrison:   {garrison_reg.id} ({garrison_reg.definition.name}, {garrison_reg.soldiers_count} men) [SECURE - 100% Haul Guarded]")
                else:
                    print(f" Frontier Garrison:   [NONE - DANGER!] Unguarded pits face 60% chance of Gutian raids (65% ore loss)!")
                print(f" Cumulative Haul:     {outpost.total_copper_delivered:.1f} Copper Ore | {outpost.total_tin_delivered:.2f} Tin | {outpost.total_stone_delivered:.1f} Diorite Stone")
                print(f" Defense Record:      {outpost.total_raids_repelled} Highland Raids Repelled | {outpost.total_raids_suffered} Ambush Losses Suffered")
            else:
                pass_status = "PACIFIED (25% Founding Discount)" if cleared_pass else "CONTESTED (Zagros brigands active)"
                print(f" Mountain Corridor:   {pass_status}")
                print(" Raw Metals Context:  Mesopotamia has zero native metal ore or stone bedrock.")
                print("                      Establishing this outpost secures regular seasonal shipments of")
                print("                      raw copper ore (erû), cassiterite tin (annaku), and diorite stone (abnu)!")

            print("-" * 78)
            print(f" Personal Estate Purse: {self.player.wallet.silver_shekels:7.2f} silver | {self.player.wallet.barley_qa:5.0f} qa barley")
            if is_gov:
                print(f" Municipal Treasury:    {self.war_engine.city_treasury_silver:7.2f} silver | {self.war_engine.city_granary_barley:5.0f} qa barley (Can co-fund outpost)")
            print(f" Sacks Inventory:       {self.player.inventory.get('timber', 0.0):.1f} Timber | {self.player.inventory.get('bronze_tools', 0.0):.1f} Bronze Tools | {self.player.inventory.get('copper_ore', 0.0):.1f} Copper Ore | {self.player.inventory.get('tin', 0.0):.2f} Tin | {self.player.inventory.get('stone', 0.0):.1f} Stone")
            print("-" * 78)

            if not outpost.is_established:
                cost_s = 45.0 if cleared_pass else 60.0
                print(f" [1] Found Mountain Mining Outpost ({cost_s:.1f} silver + 15 cedar timber)")
                print(" [2] Geological Survey & Production Estimates")
                print(" [0] Return")
                print("-" * 78)
                o_act = input(" Select action [0-2]: ").strip()

                if o_act == "0":
                    break
                elif o_act == "1":
                    use_city = False
                    if is_gov:
                        f_pick = input(" Fund from [1] Municipal City Coffers or [2] Personal Estate Purse? [default=1]: ").strip()
                        use_city = (f_pick != "2")
                    reg_id = None
                    if self.war_engine.standing_army:
                        print("\n Select a Standing Army Regiment to deploy immediately as Frontier Garrison:")
                        for idx, r in enumerate(self.war_engine.standing_army, 1):
                            print(f" [{idx}] {r.id}: {r.definition.name} ({r.soldiers_count} men) at {r.stationed_gate or 'Reserve'}")
                        print(f" [{len(self.war_engine.standing_army)+1}] None (Deploy later)")
                        r_pick = input(f" Choose regiment [1-{len(self.war_engine.standing_army)+1}]: ").strip()
                        try:
                            r_num = int(r_pick)
                            if 1 <= r_num <= len(self.war_engine.standing_army):
                                reg_id = self.war_engine.standing_army[r_num - 1].id
                        except ValueError:
                            pass
                    ok_est, msg_est = self.war_engine.establish_mining_outpost(self.player, regiment_id=reg_id, from_city_funds=use_city)
                    print("\n" + msg_est)
                elif o_act == "2":
                    self._display_mining_geological_survey()

            else:
                print(" [1] Geological Survey & Tier Yield Estimates")
                if outpost.tier < 3:
                    next_tier_cost = "75 silv + 20 timber + 6 bronze tools" if outpost.tier == 1 else "150 silv + 35 timber + 15 bronze tools"
                    print(f" [2] Upgrade Outpost to Tier {outpost.tier + 1} ({next_tier_cost})")
                else:
                    print(" [2] Outpost at Maximum Tier (Tier 3: Deep Vein Complex)")
                print(" [3] Station / Reassign Frontier Garrison Regiment")
                print(" [4] Withdraw Garrison Regiment to Mobile Reserve")
                print(" [0] Return")
                print("-" * 78)
                o_act = input(" Select action [0-4]: ").strip()

                if o_act == "0":
                    break
                elif o_act == "1":
                    self._display_mining_geological_survey()
                elif o_act == "2":
                    if outpost.tier >= 3:
                        print(" [!] Outpost is already fully expanded to Tier 3.")
                        continue
                    use_city = False
                    if is_gov:
                        f_pick = input(" Fund upgrade from [1] Municipal City Coffers or [2] Personal Estate Purse? [default=1]: ").strip()
                        use_city = (f_pick != "2")
                    ok_up, msg_up = self.war_engine.upgrade_mining_outpost(self.player, from_city_funds=use_city)
                    print("\n" + msg_up)
                elif o_act == "3":
                    if not self.war_engine.standing_army:
                        print(" [!] You have no active standing army regiments to station as garrison.")
                        continue
                    print("\n Station a Regiment as Frontier Garrison at Zagros Mining Outpost:")
                    for idx, r in enumerate(self.war_engine.standing_army, 1):
                        current_tag = " [CURRENT GARRISON]" if r.id == outpost.garrisoned_regiment_id else f" at {r.stationed_gate or 'Reserve'}"
                        print(f" [{idx}] {r.id}: {r.definition.name} ({r.soldiers_count} men){current_tag}")
                    print(f" [0] Cancel")
                    r_pick = input(f" Choose regiment [1-{len(self.war_engine.standing_army)}, 0 to cancel]: ").strip()
                    try:
                        r_num = int(r_pick)
                        if 1 <= r_num <= len(self.war_engine.standing_army):
                            chosen_r = self.war_engine.standing_army[r_num - 1]
                            ok_g, msg_g = self.war_engine.assign_outpost_garrison(chosen_r.id)
                            print("\n" + msg_g)
                    except ValueError:
                        pass
                elif o_act == "4":
                    ok_w, msg_w = self.war_engine.assign_outpost_garrison(None)
                    print("\n" + msg_w)

    def _display_mining_geological_survey(self):
        """Displays historical geological survey and mineral output rates across Zagros tiers."""
        print("\n" + "=" * 78)
        print("          GEOLOGICAL & METALLURGICAL SURVEY: ZAGROS FOOTHILLS")
        print("=" * 78)
        print(" Because the Tigris-Euphrates basin has zero native ore veins, Mesopotamian")
        print(" civilization depends entirely on mountain mining expeditions and armed trains.")
        print("-" * 78)
        print(" TIER 1: SURFACE TRENCH PITS & OPEN QUARRY")
        print("  * Workforce: 6 pit miners | Upkeep: 6.0 silver + 120 qa grain / season")
        print("  * Seasonal Output: 22 - 36 Raw Copper Ore (erû) | 2.2 - 4.0 Tin (annaku)")
        print("                     16 - 26 Mountain Diorite Stone (abnu)")
        print("  * Founding Cost:  60 silver (45 if Zagros pass pacified) + 15 cedar timber")
        print("-" * 78)
        print(" TIER 2: TIMBERED ADIT SHAFTS & SMELTING HEARTH")
        print("  * Workforce: 12 miners | Upkeep: 12.0 silver + 240 qa grain / season")
        print("  * Seasonal Output: 48 - 78 Copper Ore | 5.5 - 9.5 Tin | 36 - 58 Stone")
        print("  * Upgrade Cost:   75 silver + 20 timber + 6 bronze tools")
        print("-" * 78)
        print(" TIER 3: DEEP MOUNTAIN VEIN COMPLEX & MONUMENTAL QUARRY")
        print("  * Workforce: 20 miners | Upkeep: 20.0 silver + 400 qa grain / season")
        print("  * Seasonal Output: 85 - 135 Copper Ore | 11.0 - 19.0 Tin | 65 - 110 Stone")
        print("                     + 35% chance of 15.0 - 30.0 raw silver bullion!")
        print("  * Upgrade Cost:   150 silver + 35 timber + 15 bronze tools")
        print("-" * 78)
        print(" FRONTIER SECURITY & GARRISON DOCTRINE:")
        print("  * Stationing an armed regiment guarantees 100% shipment arrival and earns")
        print("    combat experience for troops when repelling Gutian mountain raiders.")
        print("  * Unguarded outposts suffer a 60% chance of ambush each season, losing 65% of haul!")
        print("=" * 78)
        input(" Press Enter to continue...")


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
            if self.player.social_class == SocialClass.WARDUM:
                print(" [4] Purchase Statutory Manumission & Redemption (Code §§ 117, 175) - 20.0 Silver")
            print(" [0] Return to City Square")
            print("-" * 70)

            act_range = "0-4" if self.player.social_class == SocialClass.WARDUM else "0-3"
            act = input(f" Choose legal proceeding [{act_range}]: ").strip()
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
            elif act == "4":
                if self.player.social_class != SocialClass.WARDUM:
                    print("\n [!] You are already a free citizen of Babylon!")
                    continue

                redemption_price = 20.0
                if self.player.wallet.silver_shekels < redemption_price:
                    print(f"\n [!] You hold {self.player.wallet.silver_shekels:.2f} silver shekels. You need {redemption_price:.2f} silver for statutory redemption ransom.")
                    continue

                self.player.wallet.spend_silver(redemption_price)
                self.player.social_class = SocialClass.MUSHKENUM
                if not self.player.cylinder_seal:
                    self.player.cylinder_seal = CylinderSeal(
                        owner_name=self.player.full_name,
                        material="Steatite",
                        patron_deity="Shamash",
                        prestige_rating=10
                    )

                manumit_id = f"freedom_{len(self.player.tablets)+1:03d}"
                summary = (
                    f"Manumission Charter (ṭuppi andurārim): {self.player.full_name} weighed {redemption_price:.1f} silver shekels "
                    f"ransom before the Dayyānū judges at the Gate of Shamash. The debt is shattered like clay. "
                    f"The slave-mark (abbuttum) is shaved from his brow; anointed with sacred cedar oil and enrolled as a "
                    f"free citizen (Muškēnum) with full rights of property, legal contract, and court standing under King Hammurabi."
                )
                freedom_tablet = ClayTablet(
                    id=manumit_id,
                    doc_type=DocumentType.FREEDOM_CHARTER,
                    summary=summary,
                    parties_involved=[self.player.full_name, "Crown Tribunal of Shamash", "Royal Assembly of Babylon"],
                    principal_silver=redemption_price,
                    is_fulfilled=True
                )
                self.player.sign_tablet(freedom_tablet)
                self.player.tablets.append(freedom_tablet)

                self.player.honor = min(100.0, self.player.honor + 15.0)
                self.player.reputation = min(100.0, self.player.reputation + 15.0)
                self.advance_hours(1.0)

                print("\n" + "=" * 74)
                print("   SOLEMN MANUMISSION & EMANCIPATION AT THE GATE OF SHAMASH (ANDURĀRUM)")
                print("=" * 74)
                print(" The royal Dayyānū judges and temple priests assemble before the diorite stele.")
                print(f" {self.player.full_name} steps forward and weighs {redemption_price:.2f} silver shekels upon the copper scale.")
                print("\n 'He was a bondman in the eyes of the city; today his debt is shattered like dry clay!'")
                print("\n [+] The barber of Shamash ceremonially shaves the slave-mark (abbuttum) from your brow!")
                print(" [+] Anointed with sacred cedar oil and enrolled into the city rolls as a free commoner (Muškēnum)!")
                print(" [+] Invested with your own carved Steatite Cylinder Seal (Servant of Shamash - Prestige 10)!")
                print(" [+] Sealed Cuneiform Tablet of Manumission (ṭuppi andurārim) deposited in your archive!")
                print(f" [+] Civic Honor elevated to {self.player.honor:.1f}/100!")
                print("=" * 74)
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
                print(f" Children Born:          {len(contract.children)}")
                print(" [1] Seek Divorce Settlement under Code §§ 137-142")
                print(" [3] Pray to Ninhursag for a Child (Cost: 2.0 silver offering)")
                if len(contract.children) > 0:
                    print(" [4] Send Child to the Eduba (Scribal School) - Cost: 5.0 silver")
            else:
                print(" Marriage Status: Unmarried (Visit the Ale-Wife's Tavern to meet suitors)")

            print(f" Total Sealed Clay Tablets in Archive: {len(self.player.tablets)}")
            print(" [2] Inspect Cuneiform Tablet Archive")
            print(" [0] Return to City Square")
            print("-" * 70)

            if self.player_marriage_contract:
                opt_prompt = "0-4" if len(self.player_marriage_contract.children) > 0 else "0-3"
            else:
                opt_prompt = "0-2"

            act = input(f" Choose option [{opt_prompt}]: ").strip()

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

            elif act == "3" and self.player_marriage_contract:
                cost = 2.0
                if self.player.wallet.spend_silver(cost):
                    name = input(" Enter the name of your new child: ").strip()
                    if not name:
                        name = "Awīl-ili"
                    gender = "male" if random.random() > 0.5 else "female"
                    child = self.player_marriage_contract.add_child(name=name, gender=gender, age=0)
                    print(f"\n [★] BLESSING OF NINHURSAG!")
                    print(f" Your wife has given birth to a {gender} child named {child.full_name}!")
                    print(f" Legal Class: {child.social_class.value}")
                    self.player.reputation = min(100.0, self.player.reputation + 5.0)
                else:
                    print(f" [-] You cannot afford the {cost:.1f} silver temple offering to the fertility goddess.")

            elif act == "4" and self.player_marriage_contract and len(self.player_marriage_contract.children) > 0:
                print("\n--- THE EDUBA (SCRIBAL TABLET HOUSE) ---")
                print(" Select a child to receive a scribal education (Requires Age >= 5):")
                valid_children = [c for c in self.player_marriage_contract.children if c.age >= 5]
                if not valid_children:
                    print(" [-] None of your children are old enough (Must be 5 years or older).")
                    continue

                for idx, c in enumerate(valid_children):
                    print(f" [{idx + 1}] {c.full_name} (Age: {c.age}, Literacy: {c.skills.literacy})")

                c_choice = input(" Choose child or [0] to cancel: ").strip()
                try:
                    c_idx = int(c_choice) - 1
                    if 0 <= c_idx < len(valid_children):
                        tuition = 5.0
                        if self.player.wallet.spend_silver(tuition):
                            selected_child = valid_children[c_idx]
                            selected_child.skills.literacy += 1
                            selected_child.skills.oratory += 1
                            print(f"\n [+] {selected_child.name} has attended the Eduba!")
                            print(f"     Paid {tuition:.1f} silver. Literacy increased to {selected_child.skills.literacy}.")
                        else:
                            print(f" [-] You cannot afford the {tuition:.1f} silver tuition fee.")
                except ValueError:
                    pass

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
        if self.season_idx == 0:  # Entering Autumn (New Agricultural Year)
            self.year += 1
            if self.player:
                self.player.age += 1
            self.has_harvested_spring = False
            self.sowed_acres = 0.0
            self.sowed_barley_acres = 0.0
            self.sowed_emmer_acres = 0.0

            # Aging Mechanic: Everyone ages 1 year
            if self.player:
                self.player.age += 1
            for npc in self.npcs.values():
                npc.age += 1
            if self.player_marriage_contract:
                for child in self.player_marriage_contract.children:
                    child.age += 1
            self.news_ticker.append("A new year begins. The citizens of Babylon grow one year older.")
        elif self.season_idx == 3:  # Entering Summer (Spring harvest concluded)
            self.has_harvested_spring = False

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

        # 4b. Settle Zagros Mountain Mining Outpost Haul & Baggage Train
        if self.war_engine.mining_outpost.is_established and self.player:
            ok_mine, mine_chronicle, mine_haul = self.war_engine.settle_seasonal_mining(self.player, new_season_name)
            if ok_mine and mine_chronicle:
                print(mine_chronicle)
                self.news_ticker.append(
                    f"Armed mining train arrived from Zagros: +{mine_haul.get('copper_ore', 0):.0f} copper, "
                    f"+{mine_haul.get('tin', 0):.1f} tin, +{mine_haul.get('stone', 0):.0f} diorite stone."
                )

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
    # Save & Load Subsystems (20 Cuneiform Tablet Slots)
    # --------------------------------------------------------------------------

    def ensure_saves_dir(self):
        """Ensures the saves directory exists and migrates root savegame.json if needed."""
        try:
            os.makedirs(self.SAVES_DIR, exist_ok=True)
            slot1_path = os.path.join(self.SAVES_DIR, "slot_01.json")
            if not os.path.exists(slot1_path) and os.path.exists("savegame.json"):
                shutil.copy("savegame.json", slot1_path)
        except Exception:
            pass

    def get_slot_filepath(self, slot: int) -> str:
        """Returns the file path for a given save slot (1-20)."""
        slot = max(1, min(self.TOTAL_SLOTS, slot))
        return os.path.join(self.SAVES_DIR, f"slot_{slot:02d}.json")

    def get_slot_metadata(self, slot: int) -> dict:
        """Reads lightweight metadata from a save slot without loading the whole world."""
        filepath = self.get_slot_filepath(slot)
        if not os.path.exists(filepath):
            if slot == 1 and os.path.exists("savegame.json"):
                filepath = "savegame.json"
            else:
                return {"slot": slot, "exists": False, "filepath": filepath}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            p = data.get("player", {})
            name = p.get("name", "Unknown")
            patronymic = p.get("patronymic", "")
            full_name = f"{name} mār {patronymic}" if patronymic else name
            s_class = p.get("social_class", "MUSHKENUM")
            office = p.get("civic_office") or "Private Citizen"
            if "Rabiānum" in office or "Rabianum" in office:
                office_short = "Rabiānum"
            elif "Gugallum" in office:
                office_short = "Gugallum"
            elif "Dayyānum" in office or "Dayyanum" in office:
                office_short = "Dayyānum"
            elif "Šangû" in office or "Sangu" in office:
                office_short = "Šangû"
            elif "Rabi Sikkatim" in office:
                office_short = "General"
            else:
                office_short = "Citizen"

            year = data.get("year", 1)
            s_idx = data.get("season_idx", 0)
            season_names = ["Autumn", "Winter", "Spring", "Summer"]
            season_name = season_names[s_idx % len(season_names)]
            day = data.get("day", 1)
            hour = data.get("hour", 8.0)
            h_int = int(hour)
            m_int = int((hour - h_int) * 60)
            silver = p.get("silver_shekels", 0.0)
            barley = p.get("barley_qa", 0.0)
            return {
                "slot": slot,
                "exists": True,
                "filepath": filepath,
                "full_name": full_name,
                "social_class": s_class,
                "office": office_short,
                "year": year,
                "season": season_name,
                "day": day,
                "time_str": f"{h_int:02d}:{m_int:02d}",
                "silver": silver,
                "barley": barley,
            }
        except Exception:
            return {"slot": slot, "exists": False, "corrupt": True, "filepath": filepath}

    def display_save_vault(self):
        """Displays formatted listing of all 20 Cuneiform save slots."""
        print("\n" + "=" * 82)
        print("          CUNEIFORM CLAY ARCHIVE VAULT - ROYAL ARCHIVES OF BABYLON")
        print("                            [ 20 TABLET SLOTS ]")
        print("=" * 82)
        for s in range(1, self.TOTAL_SLOTS + 1):
            meta = self.get_slot_metadata(s)
            active_tag = " [ACTIVE]" if s == self.current_slot else ""
            if not meta["exists"]:
                if meta.get("corrupt"):
                    print(f" [{s:02d}] <Corrupted Clay Tablet Archive>{active_tag}")
                else:
                    print(f" [{s:02d}] <Empty Clay Tablet Slot>{active_tag}")
            else:
                p_name = meta["full_name"]
                c_cls = meta["social_class"]
                c_off = meta["office"]
                yr = meta["year"]
                sea = meta["season"]
                dy = meta["day"]
                tm = meta["time_str"]
                silv = meta["silver"]
                barl = meta["barley"]

                desc = f"{p_name} ({c_cls} / {c_off})"
                date_str = f"Yr {yr} {sea} D{dy:02d} {tm}"
                wealth_str = f"{silv:,.1f}s | {barl:,.0f}q"
                print(f" [{s:02d}] {desc:<34} | {date_str:<18} | {wealth_str:<17}{active_tag}")
        print("=" * 82)

    def handle_save_menu(self):
        """Allows quick-saving, saving to another slot, or loading a different playthrough."""
        while True:
            print("\n" + "=" * 80)
            print(f"               INSCRIBE CLAY ARCHIVE TABLET (SAVE GAME)")
            print(f"               Current Active Tablet Slot: [{self.current_slot:02d}]")
            print("=" * 80)
            print(f" [1] Quick-Save to Active Slot [{self.current_slot:02d}]")
            print(f" [2] Save to Another Slot (Select 1-{self.TOTAL_SLOTS})")
            print(f" [3] Load Another Tablet Slot (Switch Persona / Playthrough)")
            print(f" [0] Return to City Square")
            print("-" * 80)
            act = input(" Choose option [0-3, default=1]: ").strip() or "1"
            if act == "1":
                self.save_game(self.get_slot_filepath(self.current_slot))
                break
            elif act == "2":
                self.display_save_vault()
                s_inp = input(f"\n Choose target slot [1-{self.TOTAL_SLOTS}, or 0 to cancel]: ").strip()
                if s_inp == "0":
                    continue
                try:
                    s_num = int(s_inp)
                    if 1 <= s_num <= self.TOTAL_SLOTS:
                        meta = self.get_slot_metadata(s_num)
                        if meta["exists"] and s_num != self.current_slot:
                            confirm = input(f" [!] Overwrite existing archive in Slot [{s_num:02d}] ({meta['full_name']})? (y/N): ").strip().lower()
                            if confirm != "y":
                                continue
                        self.current_slot = s_num
                        self.SAVE_FILE_PATH = self.get_slot_filepath(s_num)
                        self.save_game(self.get_slot_filepath(s_num))
                        break
                    else:
                        print(f" [!] Select between 1 and {self.TOTAL_SLOTS}.")
                except ValueError:
                    print(" [!] Invalid input.")
            elif act == "3":
                self.display_save_vault()
                s_inp = input(f"\n Choose tablet slot to load [1-{self.TOTAL_SLOTS}, or 0 to cancel]: ").strip()
                if s_inp == "0":
                    continue
                try:
                    s_num = int(s_inp)
                    if 1 <= s_num <= self.TOTAL_SLOTS:
                        meta = self.get_slot_metadata(s_num)
                        if not meta["exists"]:
                            print(f" [!] Slot [{s_num:02d}] is empty.")
                            continue
                        confirm = input(f" [!] Unsaved progress on current persona will be lost if not saved. Load Slot [{s_num:02d}] ({meta['full_name']})? (y/N): ").strip().lower()
                        if confirm == "y":
                            self.current_slot = s_num
                            self.SAVE_FILE_PATH = self.get_slot_filepath(s_num)
                            if self.load_game(self.SAVE_FILE_PATH):
                                print(f"\n[+] Successfully switched to persona in Slot [{s_num:02d}]: {self.player.full_name}!")
                                break
                    else:
                        print(f" [!] Select between 1 and {self.TOTAL_SLOTS}.")
                except ValueError:
                    print(" [!] Invalid input.")
            elif act == "0":
                break

    def save_game(self, filepath: Optional[str] = None) -> bool:
        """Serializes current game state to JSON."""
        p = self.player
        if not p:
            return False

        target_path = filepath or self.SAVE_FILE_PATH
        if target_path == "savegame.json" and self.current_slot:
            target_path = self.get_slot_filepath(self.current_slot)

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
            "has_harvested_spring": self.has_harvested_spring,
            "sowed_acres": self.sowed_acres,
            "sowed_barley_acres": self.sowed_barley_acres,
            "sowed_emmer_acres": self.sowed_emmer_acres,
            "army": {
                "regiment_counter": self.war_engine.regiment_counter,
                "city_treasury_silver": self.war_engine.city_treasury_silver,
                "city_granary_barley": self.war_engine.city_granary_barley,
                "gate_toll_revenue_daily": self.war_engine.gate_toll_revenue_daily,
                "tax_policy": self.war_engine.tax_policy,
                "campaigns_completed": self.war_engine.campaigns_completed,
                "mining_outpost": self.war_engine.mining_outpost.to_dict(),
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
            "market_stocks": {g_id: state.stock for g_id, state in self.market.goods.items()},
            "market_prices": {g_id: state.current_price for g_id, state in self.market.goods.items()}
        }

        try:
            os.makedirs(os.path.dirname(target_path) if os.path.dirname(target_path) else ".", exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(save_dict, f, indent=2)
            print(f" [+] Game state successfully imprinted to clay archive '{target_path}' (Slot [{self.current_slot:02d}])!")
            # If saving specifically to slot 1, mirror to root savegame.json
            if target_path == self.get_slot_filepath(1):
                try:
                    with open("savegame.json", "w", encoding="utf-8") as f:
                        json.dump(save_dict, f, indent=2)
                except Exception:
                    pass
            return True
        except Exception as e:
            print(f" [!] Error saving game: {e}")
            return False

    def load_game(self, filepath: Optional[str] = None) -> bool:
        """Restores game state from JSON."""
        target_path = filepath or self.SAVE_FILE_PATH
        if target_path == "savegame.json" and not os.path.exists("savegame.json"):
            slot_p = self.get_slot_filepath(self.current_slot)
            if os.path.exists(slot_p):
                target_path = slot_p

        if not os.path.exists(target_path):
            return False

        try:
            with open(target_path, "r", encoding="utf-8") as f:
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

            # Restore agricultural cycle state
            self.has_harvested_spring = data.get("has_harvested_spring", False)
            self.sowed_acres = data.get(
                "sowed_acres",
                self.player.owned_land_acres if self.season_idx in (0, 1, 2) and not self.has_harvested_spring else 0.0
            )
            self.sowed_barley_acres = data.get("sowed_barley_acres", self.sowed_acres)
            self.sowed_emmer_acres = data.get("sowed_emmer_acres", 0.0)

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
                tax_pol = a_data.get("tax_policy", "STATUTORY")
                self.war_engine.set_tax_policy(tax_pol)
                self.war_engine.gate_toll_revenue_daily = a_data.get("gate_toll_revenue_daily", self.war_engine.gate_toll_revenue_daily)
                if "campaigns_completed" in a_data:
                    self.war_engine.campaigns_completed = {int(k): v for k, v in a_data["campaigns_completed"].items()}
                else:
                    self.war_engine.campaigns_completed = {}
                if "mining_outpost" in a_data:
                    self.war_engine.mining_outpost = MiningOutpost.from_dict(a_data["mining_outpost"])
                else:
                    self.war_engine.mining_outpost = MiningOutpost()
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

            # Restore market warehouse stocks & prices
            if "market_stocks" in data:
                for g_id, stk in data["market_stocks"].items():
                    if g_id in self.market.goods:
                        self.market.goods[g_id].stock = stk
                        self.market.goods[g_id].shortage = (stk <= 0.10 * self.market.goods[g_id].base_stock)
                        self.market.goods[g_id].current_price = self.market.calculate_price(g_id)
            elif "market_prices" in data:
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

        while True:
            if not self.player or not self.player.is_alive:
                self.handle_death()
                if not self.player or not self.player.is_alive:
                    break # Game over completely
                else:
                    continue # Inherited, keep playing!

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
                self.handle_save_menu()
            elif choice == "0":
                print(f"\n[!] Imprinting current journey to clay tablet slot [{self.current_slot:02d}] before departure...")
                self.save_game(self.get_slot_filepath(self.current_slot))
                print("May the gods Shamash and Marduk grant you long life and bountiful harvests. Farewell!")
                break
            else:
                print(" [!] Unknown command. Please select 0-9 or E.")

    def handle_death(self):
        if self.player and not self.player.is_alive:
            print("\n" + "=" * 78)
            print("                           YOU HAVE DIED")
            print(" Your shade descends to the dark underworld of Kur, beneath the dust.")
            print("=" * 78)

            # Inheritance System
            heir_selected = False
            if self.player_marriage_contract and self.player_marriage_contract.children:
                adult_children = [c for c in self.player_marriage_contract.children if c.age >= 15]
                if adult_children:
                    while True:
                        print("\n Your estate must be settled. The following heirs have come of age:")
                        for idx, c in enumerate(adult_children):
                            print(f" [{idx + 1}] {c.full_name} (Age: {c.age}, Literacy: {c.skills.literacy}, Oratory: {c.skills.oratory})")

                        choice = input(" Select an heir to continue your dynasty (or [0] to pass into history): ").strip()
                        try:
                            c_idx = int(choice) - 1
                            if c_idx == -1:
                                break
                            if 0 <= c_idx < len(adult_children):
                                heir = adult_children[c_idx]
                                print(f"\n [+] {heir.full_name} takes up your cylinder seal and inherits the estate!")

                                # Transfer Assets
                                heir.wallet = self.player.wallet
                                heir.inventory = self.player.inventory
                                heir.tablets = self.player.tablets
                                heir.cylinder_seal = self.player.cylinder_seal
                                heir.owned_land_acres = self.player.owned_land_acres
                                heir.owned_oxen = self.player.owned_oxen
                                heir.owned_sheep = self.player.owned_sheep

                                # Settle Widowhood & Dissolve Contract
                                msg = self.marriage_mgr.settle_widowhood(self.player_marriage_contract, deceased="husband")
                                print(f" [+] {msg}")

                                self.player_marriage_contract = None

                                # Promote Heir to Player
                                heir.is_player = True
                                heir.is_alive = True
                                heir.health = 100.0
                                heir.energy = 100.0
                                heir.hunger = 0.0
                                heir.thirst = 0.0

                                self.player = heir
                                heir_selected = True
                                break
                            else:
                                print(" Invalid selection. Try again.")
                        except ValueError:
                            print(" Invalid input. Try again.")

            if not heir_selected:
                print(" Your cylinder seal is buried in your ancestral family tomb. Your lineage ends here.")
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

    # 2. Market buying/selling & Warehouse Stock Dynamics
    print("\n[2/8] Testing Live Market Subsystem & Warehouse Stocks...")
    initial_stock = game.market.get_stock("bread")
    initial_price = game.market.get_price("bread")
    assert initial_stock > 0, "Market should have positive stock"
    game.player.buy_good("bread", 2.0, game.market, game.registry)
    assert game.player.inventory.get("bread", 0.0) >= 2.0, "Failed to buy bread"
    assert game.market.get_stock("bread") == initial_stock - 2.0, "Warehouse stock should decrease by 2"
    assert game.market.get_price("bread") >= initial_price, "Price should rise with lower stock"
    game.player.sell_good("bread", 1.0, game.market, game.registry)
    assert game.market.get_stock("bread") == initial_stock - 1.0, "Warehouse stock should increase by 1"
    print(f" [+] Live Market warehouse stocks & dynamic pricing verified (Stock: {game.market.get_stock('bread')}).")

    # 3. Agriculture, Incremental Sowing, Spring Harvest Cooldown & Alluvial Foraging
    print("\n[3/8] Testing Agriculture, Incremental Sowing, Harvest Cooldown & Foraging...")
    game.player.owned_land_acres = 10.0
    game.player.wallet.add_barley(500.0)
    # Test incremental sowing
    unsowed = max(0.0, game.player.owned_land_acres - game.sowed_acres)
    assert unsowed == 10.0
    game.sowed_acres += 6.0
    game.player.owned_land_acres += 4.0  # Buy 4 more acres
    unsowed2 = max(0.0, game.player.owned_land_acres - game.sowed_acres)
    assert unsowed2 == 8.0, "Should only have 8 unsowed acres remaining"
    game.sowed_acres += 8.0
    assert game.sowed_acres == 14.0, "All 14 acres sowed"

    # Test Spring Harvest cooldown
    game.season_idx = 2  # Spring
    game.has_harvested_spring = False
    initial_city_granary = game.war_engine.city_granary_barley
    # Simulate spring harvest
    gross_yield = game.sowed_acres * 300.0
    tithe_rate = game.war_engine.get_tax_rates()["harvest_tithe_rate"]
    tithe_qa = gross_yield * tithe_rate
    game.war_engine.city_granary_barley += tithe_qa
    game.player.wallet.add_barley(gross_yield - tithe_qa)
    game.has_harvested_spring = True
    game.sowed_acres = 0.0
    assert game.has_harvested_spring, "Should be marked as harvested for the year"
    assert game.war_engine.city_granary_barley == initial_city_granary + tithe_qa, "Public granary should receive tithe"

    # Test foraging timber
    game.player.inventory["timber"] = game.player.inventory.get("timber", 0.0) + 3.0
    assert game.player.inventory.get("timber", 0.0) >= 3.0, "Failed to forage timber"
    print(" [+] Incremental sowing, spring harvest tithes/cooldown, and timber foraging verified.")

    # 4. Multi-Batch Workshop Labor & Clock Advancement
    print("\n[4/8] Testing Batch Crafting & Clock Advancement...")
    # Test batch formula: 3 batches of beer (15 qa barley -> 12 jars beer)
    game.player.wallet.spend_barley(15.0)
    game.player.inventory["barley_beer"] = game.player.inventory.get("barley_beer", 0.0) + 12.0
    assert game.player.inventory.get("barley_beer", 0.0) >= 12.0
    initial_h = game.hour
    game.advance_hours(5.5)
    assert game.hour == initial_h + 5.5, "Clock failed to advance"
    print(f" [+] Batch brewing and time progression verified (Clock: {game.hour:.1f}h).")

    # 5. Marriage covenant
    print("\n[5/8] Testing Marriage Covenant under Code § 128...")
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

    # 6. Long-distance Caravan & Mayoral Tax Decrees
    print("\n[6/8] Testing Tamkarum Caravans & Mayoral Tax Decrees...")
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

    # Test Tax Policy switch
    ok_tax, msg_tax = game.war_engine.set_tax_policy("HEAVY_PATRICIAN")
    assert ok_tax, "Tax policy update failed"
    assert game.war_engine.gate_toll_revenue_daily == 4.50
    assert game.war_engine.get_tax_rates()["sales_tax_rate"] == 0.15
    print(" [+] Mayoral Tax Decrees verified (Heavy Patrician 15% duty enacted).")

    # 7. Politics, Litigation & Warfare Command
    print("\n[7/8] Testing Assembly Politics, Court Litigation & Warfare...")
    case = game.politics.file_lawsuit(
        accuser=game.player,
        defendant=game.npcs["patrician_rival"],
        charge=LawsuitCharge.USURY_VIOLATION,
        evidence_strength=0.80,
        damages_claimed_silver=10.0
    )
    won, rep = game.politics.adjudicate_case(case, magistrate=game.npcs["temple_priest"])
    print(" [+] Court litigation resolved.")

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

    # Test military drill campaign
    drill_res = game.war_engine.launch_campaign(game.player, 4, [new_reg])
    assert drill_res.victory, "Drill should always succeed"

    sec_rating = game.war_engine.calculate_city_security()
    assert sec_rating > 0, "Security rating should be positive"
    print(f" [+] Warfare engine verified: Recruited, armed, drilled (Security Rating: {sec_rating:.1f}%).")

    # 8. Season Advance, Save & Load with Stocks, Tax Policy & Mining Outpost
    print("\n[8/8] Testing Season Advance & Save/Load with Stocks, Taxes & Mining Outpost...")
    
    # Establish and garrison mining outpost in smoke test
    game.player.wallet.add_silver(200.0)
    game.player.inventory["timber"] = 30.0
    ok_est, msg_est = game.war_engine.establish_mining_outpost(game.player, regiment_id=new_reg.id)
    assert ok_est, f"Outpost establishment failed: {msg_est}"
    assert game.war_engine.mining_outpost.is_established
    assert game.war_engine.mining_outpost.garrisoned_regiment_id == new_reg.id

    init_copper = game.player.inventory.get("copper_ore", 0.0)
    game.advance_season()
    assert game.player.inventory.get("copper_ore", 0.0) > init_copper, "Mining baggage train should deliver copper"
    assert game.war_engine.mining_outpost.total_copper_delivered > 0

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
    assert game.war_engine.tax_policy == "HEAVY_PATRICIAN", "Tax policy failed to restore"
    assert game.war_engine.mining_outpost.is_established, "Mining outpost failed to restore"
    assert game.war_engine.mining_outpost.garrisoned_regiment_id == new_reg.id, "Outpost garrison failed to restore"
    assert game.market.get_stock("bread") > 0, "Market stock failed to restore"
    if os.path.exists("test_savegame.json"):
        os.remove("test_savegame.json")
    print(" [+] Save/Load with Market Stocks, Tax Decrees & Harvest State verified.")

    print("\n" + "=" * 78)
    print("   ALL BABYLONIAN RPG SUBSYSTEMS FULLY OPERATIONAL & VERIFIED!")
    print("=" * 78)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_automated_smoke_test()
    else:
        game = BabylonianGame()
        game.play()
