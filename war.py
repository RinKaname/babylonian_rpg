"""
war.py - Babylonian Warfare, Military Command & City Garrison Engine
=====================================================================
Governed by the Code of Hammurabi (c. 1750 BC / Old Babylonian Period §§ 26-41).

Subsystems:
1. Unit Types & Equipment:
   - Bā'iru (Light Skirmishers / Archers) - requires Composite Bows (qaštu)
   - Rēdû (Heavy Phalanx Spearmen) - requires Bronze Weapons (kakku)
   - Narkabtu (War Charioteers) - requires Spoked War Chariots (narkabtu)
   - Peasant Levies / Militia - basic defense, improvised weapons
2. Babylon City Garrison (Bābili Rēdû):
   - Manning the 4 Great Gates: Ishtar, Shamash, Marduk, and Urash.
   - City Security Rating (0% to 100%): Suppresses theft, halts farmland raids, and secures trade routes.
3. 3-Phase Tactical Combat Solver:
   - Phase 1: Ranged Volley (Archery superiority)
   - Phase 2: Chariot Shock Charge (Breaking open enemy battle lines)
   - Phase 3: Melee Phalanx Clash (Spearmen resolve the field)
4. Military Campaigns & Spoils of War (Šallatu):
   - Repelling Sutean Desert Nomad Incursions
   - Purging Bandit Strongholds from Trade Corridors
   - Joining King Hammurabi's Imperial Campaigns (Larsa / Elam)
   - Seizing spoils: Silver, captured weapons, sheep, and captive laborers (wardum).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import random
import math
import sys

# Ensure clean UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from character import Character, DualWallet
from economics import GoodsRegistry, Market


# ==============================================================================
# 1. Military Unit Types & Specifications
# ==============================================================================

class UnitType(Enum):
    BAIRU = "Bā'iru (Composite Bow Skirmishers)"
    REDU = "Rēdû (Heavy Bronze Spearmen)"
    NARKABTU = "Narkabtu (Two-Wheeled War Chariot)"
    MILITIA = "Peasant Militia / Commoner Levies"


@dataclass
class UnitDefinition:
    unit_type: UnitType
    name: str
    akkadian_name: str
    required_equipment: Optional[str]  # Item ID from GoodsRegistry
    base_range_attack: float
    base_melee_attack: float
    base_defense: float
    base_morale: float                 # 0 to 100
    recruitment_cost_silver: float     # Per soldier
    daily_fodder_grain_qa: float       # Daily grain upkeep per soldier
    daily_wage_silver: float           # Daily silver pay per soldier
    description: str


UNIT_CATALOG: Dict[UnitType, UnitDefinition] = {
    UnitType.BAIRU: UnitDefinition(
        unit_type=UnitType.BAIRU,
        name="Bā'iru Archers",
        akkadian_name="bā'iru",
        required_equipment="composite_bow",
        base_range_attack=28.0,
        base_melee_attack=10.0,
        base_defense=12.0,
        base_morale=65.0,
        recruitment_cost_silver=2.0,
        daily_fodder_grain_qa=3.0,
        daily_wage_silver=0.03,  # ~5 grains silver/day (Code § 274 standard)
        description="Agile river patrolmen and archers armed with laminated horn bows. Decimates enemy ranks from afar."
    ),
    UnitType.REDU: UnitDefinition(
        unit_type=UnitType.REDU,
        name="Rēdû Heavy Spearmen",
        akkadian_name="rēdû",
        required_equipment="bronze_weapons",
        base_range_attack=0.0,
        base_melee_attack=25.0,
        base_defense=30.0,
        base_morale=80.0,
        recruitment_cost_silver=3.0,
        daily_fodder_grain_qa=4.0,
        daily_wage_silver=0.04,
        description="Disciplined royal phalanx holding bronze-tipped spears and large oxhide shields. The unbreakable wall of Babylon."
    ),
    UnitType.NARKABTU: UnitDefinition(
        unit_type=UnitType.NARKABTU,
        name="Narkabtu War Chariots",
        akkadian_name="narkabtu",
        required_equipment="war_chariot",
        base_range_attack=18.0,
        base_melee_attack=42.0,
        base_defense=22.0,
        base_morale=85.0,
        recruitment_cost_silver=10.0,
        daily_fodder_grain_qa=12.0,  # Fodder for chariot team of 2 horses/onagers
        daily_wage_silver=0.10,
        description="Elite shock vehicles crewed by a driver and noble archer. Shatters open battle lines across the flat plains."
    ),
    UnitType.MILITIA: UnitDefinition(
        unit_type=UnitType.MILITIA,
        name="Peasant Levies",
        akkadian_name="ṣābu",
        required_equipment=None,
        base_range_attack=5.0,
        base_melee_attack=10.0,
        base_defense=10.0,
        base_morale=45.0,
        recruitment_cost_silver=0.5,
        daily_fodder_grain_qa=2.0,
        daily_wage_silver=0.015,
        description="Tenant farmers and bondmen mobilized in emergency defense. Inexpensive and numerous, but prone to panic."
    )
}


@dataclass
class SoldierRegiment:
    id: str
    unit_type: UnitType
    soldiers_count: int
    is_equipped: bool = False
    experience_level: int = 1         # 1 (Green) to 5 (Veteran Royal Guard)
    stationed_gate: Optional[str] = None

    @property
    def definition(self) -> UnitDefinition:
        return UNIT_CATALOG[self.unit_type]

    @property
    def range_power(self) -> float:
        mult = 1.0 + (self.experience_level - 1) * 0.15
        equip_mult = 1.0 if self.is_equipped or self.definition.required_equipment is None else 0.35
        return self.definition.base_range_attack * self.soldiers_count * mult * equip_mult

    @property
    def melee_power(self) -> float:
        mult = 1.0 + (self.experience_level - 1) * 0.15
        equip_mult = 1.0 if self.is_equipped or self.definition.required_equipment is None else 0.40
        return self.definition.base_melee_attack * self.soldiers_count * mult * equip_mult

    @property
    def defense_power(self) -> float:
        mult = 1.0 + (self.experience_level - 1) * 0.15
        equip_mult = 1.0 if self.is_equipped or self.definition.required_equipment is None else 0.50
        return self.definition.base_defense * self.soldiers_count * mult * equip_mult

    @property
    def total_morale(self) -> float:
        exp_bonus = (self.experience_level - 1) * 8.0
        equip_bonus = 10.0 if self.is_equipped else -15.0
        return max(15.0, min(100.0, self.definition.base_morale + exp_bonus + equip_bonus))


# ==============================================================================
# 2. Babylon Gates & City Garrison
# ==============================================================================

class CityGate(Enum):
    ISHTAR_GATE = "Ishtar Gate (North / Processional Way)"
    SHAMASH_GATE = "Gate of Shamash (South / Canals & Fields)"
    MARDUK_GATE = "Marduk Gate (East / Temple Quarter)"
    URASH_GATE = "Urash Gate (West / Euphrates Quays)"


@dataclass
class BattleResult:
    victory: bool
    title: str
    chronicle: List[str]
    friendly_casualties: int
    enemy_casualties: int
    spoils_silver: float = 0.0
    spoils_barley_qa: float = 0.0
    spoils_goods: Dict[str, float] = field(default_factory=dict)
    honor_gain: float = 0.0


# ==============================================================================
# 3. Tactical Battle Solver (3-Phase Resolution)
# ==============================================================================

class TacticalBattleEngine:
    """
    Simulates authentic ancient Near Eastern warfare in three decisive tactical phases:
    1. Archery / Skirmish Volley
    2. Chariot Shock Charge
    3. Melee Phalanx Clash
    """

    @staticmethod
    def resolve_battle(
        friendly_regiments: List[SoldierRegiment],
        enemy_name: str,
        enemy_range: float,
        enemy_chariot: float,
        enemy_melee: float,
        enemy_defense: float,
        enemy_morale: float,
        terrain: str = "Alluvial Plain"
    ) -> BattleResult:
        chronicle: List[str] = [
            f"=== BATTLE REPORT: ENGAGEMENT AT THE {terrain.upper()} ===",
            f" Opposing Host: {enemy_name}",
            f" Babylon Forces: {sum(r.soldiers_count for r in friendly_regiments)} warriors under the banner of the Golden Bull."
        ]

        # Calculate combined friendly battle stats
        total_friendly_soldiers = sum(r.soldiers_count for r in friendly_regiments)
        if total_friendly_soldiers == 0:
            return BattleResult(
                victory=False,
                title="Rout & Debacle",
                chronicle=[" [!] No soldiers took the field! Babylon's lines were overrun without resistance."],
                friendly_casualties=0,
                enemy_casualties=0
            )

        friendly_range = sum(r.range_power for r in friendly_regiments)
        friendly_chariot = sum(r.melee_power for r in friendly_regiments if r.unit_type == UnitType.NARKABTU)
        friendly_melee = sum(r.melee_power for r in friendly_regiments if r.unit_type != UnitType.NARKABTU)
        friendly_defense = sum(r.defense_power for r in friendly_regiments)
        avg_friendly_morale = sum(r.total_morale * r.soldiers_count for r in friendly_regiments) / total_friendly_soldiers

        f_losses = 0
        e_losses = 0

        # ----------------------------------------------------------------------
        # PHASE 1: Archery Volley & Skirmish Duel
        # ----------------------------------------------------------------------
        chronicle.append("\n--- [PHASE 1: THE ARCHERY VOLLEY] ---")
        if friendly_range > 0 or enemy_range > 0:
            # Friendly archers fire
            if friendly_range > 0:
                e_arrow_casualties = int(friendly_range * random.uniform(0.18, 0.28) / max(1.0, enemy_defense * 0.05))
                e_losses += e_arrow_casualties
                chronicle.append(f" [+] Babylonian Bā'iru archers loosed dark clouds of arrows! Slew ~{e_arrow_casualties} enemy skirmishers.")
            else:
                chronicle.append(" [!] Babylon fielded no archers; enemy arrows rained unopposed.")

            # Enemy archers fire
            if enemy_range > 0:
                f_arrow_casualties = int(enemy_range * random.uniform(0.15, 0.25) / max(1.0, friendly_defense * 0.05))
                f_losses += min(total_friendly_soldiers // 4, f_arrow_casualties)
                chronicle.append(f" [!] Hostile bowmen returned fire, inflicting {f_arrow_casualties} casualties upon our front ranks.")
        else:
            chronicle.append(" Neither side possessed bowmen; the hosts closed in silence.")

        # ----------------------------------------------------------------------
        # PHASE 2: Chariot Shock Charge
        # ----------------------------------------------------------------------
        chronicle.append("\n--- [PHASE 2: CHARIOT SHOCK CHARGE] ---")
        if friendly_chariot > 0 or enemy_chariot > 0:
            if friendly_chariot > 0:
                e_shock = int(friendly_chariot * random.uniform(0.25, 0.38))
                e_losses += e_shock
                enemy_morale -= min(25.0, friendly_chariot * 0.15)
                chronicle.append(f" [+] Bronze-spoked Narkabtu chariots thundered across the plain! Trampled {e_shock} enemy infantry and shattered enemy cohesion!")
            if enemy_chariot > 0:
                f_shock = int(enemy_chariot * random.uniform(0.20, 0.32) / max(1.0, friendly_defense * 0.03))
                f_losses += min(total_friendly_soldiers // 3, f_shock)
                avg_friendly_morale -= 15.0
                chronicle.append(f" [!] Enemy war wagons smashed into our perimeter, causing {f_shock} casualties!")
        else:
            chronicle.append(" No chariots operated on this ground; infantry closed the distance.")

        # ----------------------------------------------------------------------
        # PHASE 3: Melee Phalanx Clash
        # ----------------------------------------------------------------------
        chronicle.append("\n--- [PHASE 3: MELEE CLASH OF BRONZE SPEARS] ---")
        clash_f = (friendly_melee * 0.6) + (friendly_defense * 0.4) + (avg_friendly_morale * 2.0)
        clash_e = (enemy_melee * 0.6) + (enemy_defense * 0.4) + (enemy_morale * 2.0)

        # Apply random tactical variance
        roll_f = clash_f * random.uniform(0.85, 1.25)
        roll_e = clash_e * random.uniform(0.85, 1.25)

        melee_f_losses = int(max(0, (roll_e / max(1.0, roll_f)) * random.uniform(5, 15)))
        melee_e_losses = int(max(0, (roll_f / max(1.0, roll_e)) * random.uniform(8, 20)))
        f_losses += min(total_friendly_soldiers - f_losses, melee_f_losses)
        e_losses += melee_e_losses

        is_victory = (roll_f >= roll_e)

        if is_victory:
            chronicle.append(f" [+] The bronze spears of Babylon held firm! The enemy ranks broke and fled in disarray.")
            chronicle.append(f"     Enemy losses in the rout: ~{e_losses} dead or captive.")
        else:
            chronicle.append(f" [!] Our lines were forced back under fierce pressure! Orderly withdrawal sounded.")

        # Distribute casualties among regiments proportionally
        remaining_f_losses = f_losses
        for reg in friendly_regiments:
            if remaining_f_losses <= 0:
                break
            drop = min(reg.soldiers_count, math.ceil(f_losses * (reg.soldiers_count / total_friendly_soldiers)))
            reg.soldiers_count = max(0, reg.soldiers_count - drop)
            remaining_f_losses -= drop

        # Remove destroyed regiments
        friendly_regiments[:] = [r for r in friendly_regiments if r.soldiers_count > 0]

        # Award experience to surviving regiments
        if is_victory:
            for reg in friendly_regiments:
                if reg.experience_level < 5:
                    reg.experience_level += 1

        return BattleResult(
            victory=is_victory,
            title="Glorious Triumph" if is_victory else "Tactical Defeat",
            chronicle=chronicle,
            friendly_casualties=f_losses,
            enemy_casualties=e_losses,
            honor_gain=12.0 if is_victory else -4.0
        )


# ==============================================================================
# 4. The Master Babylonian Warfare Engine
# ==============================================================================

class BabylonianWarEngine:
    """
    Coordinates recruitment, weapons arming, garrison assignments at Babylon's gates,
    and military campaign expeditions under the Code of Hammurabi.
    """

    def __init__(self, registry: GoodsRegistry, market: Market):
        self.registry = registry
        self.market = market
        self.standing_army: List[SoldierRegiment] = []
        self.regiment_counter = 1
        
        # Babylon Municipal Coffers & Public Granary (Bīt Ālī)
        self.city_treasury_silver: float = 250.0   # Civic silver reserves
        self.city_granary_barley: float = 3000.0   # Public grain silos (10 gur = 3,000 qa)
        self.gate_toll_revenue_daily: float = 1.80 # Daily caravan customs from 4 Great Gates

        # Initial starter garrison stationed at the gates
        self._initialize_starter_garrison()

    def _initialize_starter_garrison(self):
        """Populates Babylon with a baseline municipal guard."""
        # 1 regiment of Redu spearmen at Ishtar Gate
        r1 = SoldierRegiment(
            id=f"reg_{self.regiment_counter:03d}",
            unit_type=UnitType.REDU,
            soldiers_count=12,
            is_equipped=True,
            experience_level=2,
            stationed_gate=CityGate.ISHTAR_GATE.value
        )
        self.regiment_counter += 1
        
        # 1 regiment of Bairu archers at Shamash Gate
        r2 = SoldierRegiment(
            id=f"reg_{self.regiment_counter:03d}",
            unit_type=UnitType.BAIRU,
            soldiers_count=10,
            is_equipped=True,
            experience_level=2,
            stationed_gate=CityGate.SHAMASH_GATE.value
        )
        self.regiment_counter += 1

        self.standing_army.extend([r1, r2])

    # --------------------------------------------------------------------------
    # Recruitment & Armament
    # --------------------------------------------------------------------------

    def recruit_regiment(
        self,
        player: Character,
        unit_type: UnitType,
        count: int
    ) -> Tuple[bool, str]:
        """Recruits a new military detachment, paying silver and initial grain costs."""
        u_def = UNIT_CATALOG[unit_type]
        if count <= 0:
            return False, "Regiment must have at least 1 soldier."

        total_silver = u_def.recruitment_cost_silver * count
        total_grain = u_def.daily_fodder_grain_qa * count * 3.0  # 3 days starting rations

        if player.wallet.silver_shekels < total_silver:
            return False, f"Cannot afford recruitment: needs {total_silver:.2f} silver (Have: {player.wallet.silver_shekels:.2f})."
        if player.wallet.barley_qa < total_grain:
            return False, f"Insufficient starting grain rations: needs {total_grain:.0f} qa (Have: {player.wallet.barley_qa:.0f} qa)."

        player.wallet.spend_silver(total_silver)
        player.wallet.spend_barley(total_grain)

        reg_id = f"reg_{self.regiment_counter:03d}"
        self.regiment_counter += 1

        # Check if player has weapons in inventory to auto-arm
        is_equipped = False
        if u_def.required_equipment:
            needed = count
            avail = player.inventory.get(u_def.required_equipment, 0.0)
            if avail >= needed:
                player.inventory[u_def.required_equipment] -= needed
                if player.inventory[u_def.required_equipment] <= 1e-4:
                    del player.inventory[u_def.required_equipment]
                is_equipped = True

        new_reg = SoldierRegiment(
            id=reg_id,
            unit_type=unit_type,
            soldiers_count=count,
            is_equipped=is_equipped,
            experience_level=1,
            stationed_gate=CityGate.ISHTAR_GATE.value
        )
        self.standing_army.append(new_reg)

        equip_status = "Fully Equipped with arms!" if is_equipped else (
            "Unequipped (Fighting with improvised weapons. Forge or buy equipment to maximize combat efficiency!)"
            if u_def.required_equipment else "Fully Equipped (Militia standard)"
        )

        msg = (
            f"=== MILITARY LEVY CONCLUDED (CODE §§ 26-41) ===\n"
            f" Recruited {count} warriors for {new_reg.definition.name} ({reg_id}).\n"
            f" Cost: {total_silver:.2f} silver shekels and {total_grain:.0f} qa initial grain rations.\n"
            f" Armament Status: {equip_status}"
        )
        return True, msg

    def arm_regiment(self, player: Character, regiment_id: str) -> Tuple[bool, str]:
        """Equips an unequipped regiment using manufactured weapons from player inventory."""
        target_reg = next((r for r in self.standing_army if r.id == regiment_id), None)
        if not target_reg:
            return False, "Regiment not found."

        if target_reg.is_equipped:
            return False, f"{target_reg.id} is already fully armed and equipped!"

        req_item = target_reg.definition.required_equipment
        if not req_item:
            target_reg.is_equipped = True
            return True, "Militia does not require specialized manufactured weapons."

        needed = target_reg.soldiers_count
        avail = player.inventory.get(req_item, 0.0)
        if avail < needed:
            return False, f"Missing equipment! Requires {needed} units of '{req_item}' (You have: {avail:.1f} in inventory sacks)."

        player.inventory[req_item] -= needed
        if player.inventory[req_item] <= 1e-4:
            del player.inventory[req_item]
        target_reg.is_equipped = True

        return True, f"[+] Equipped {target_reg.soldiers_count} warriors of {target_reg.id} with {req_item}! Combat prowess elevated."

    # --------------------------------------------------------------------------
    # Garrison Readiness & Security
    # --------------------------------------------------------------------------

    def calculate_city_security(self) -> float:
        """Calculates Babylon's overall defense and security index (0% to 100%)."""
        if not self.standing_army:
            return 10.0

        total_defense = sum(r.defense_power for r in self.standing_army)
        # 120 defense rating gives ~100% security
        security = min(100.0, (total_defense / 120.0) * 100.0)
        return round(security, 1)

    def get_security_label(self) -> str:
        sec = self.calculate_city_security()
        if sec >= 85.0:
            return "Impregnable Citadel (Crime suppressed, trade corridors secure)"
        elif sec >= 60.0:
            return "Strong Garrison (Well-defended, minor border incursions)"
        elif sec >= 40.0:
            return "Adequate Watch (Vulnerable to sudden nomad raids)"
        else:
            return "Vulnerable / Under-defended (High risk of banditry and plundering)"

    def calculate_daily_upkeep(self) -> Tuple[float, float]:
        """Calculates daily grain (qa) and silver (shekels) required to maintain the garrison."""
        total_grain = 0.0
        total_silver = 0.0
        for reg in self.standing_army:
            total_grain += reg.definition.daily_fodder_grain_qa * reg.soldiers_count
            total_silver += reg.definition.daily_wage_silver * reg.soldiers_count
        return total_grain, total_silver

    def pay_daily_upkeep(self, player: Optional[Character] = None) -> Tuple[bool, str]:
        """
        Deducts daily garrison wages and food rations from the Babylon Municipal Coffers (Bīt Ālī).
        Incoming trade through the 4 Great Gates deposits customs tariffs daily into the civic treasury.
        If municipal silos are empty, Mayor can subsidize or troops desert under Code §§ 26-41.
        """
        # 1. Inflow: Caravans & merchants pay customs tariffs into municipal treasury
        self.city_treasury_silver += self.gate_toll_revenue_daily

        grain_needed, silver_needed = self.calculate_daily_upkeep()
        if not self.standing_army:
            return True, "No standing troops."

        # 2. Paid directly from Babylon Municipal Coffers & Public Granary
        if self.city_treasury_silver >= silver_needed and self.city_granary_barley >= grain_needed:
            self.city_treasury_silver -= silver_needed
            self.city_granary_barley -= grain_needed
            return True, f"[City Coffers (Bīt Ālī)] Paid garrison upkeep ({silver_needed:.2f} silv, {grain_needed:.0f} qa grain) from Municipal Treasury (Treasury: {self.city_treasury_silver:.1f} silv | Granary: {self.city_granary_barley:.0f} qa)."

        # 3. Deficit handling: Check if Mayor can/wants to subsidize from personal funds
        deficit_silver = max(0.0, silver_needed - self.city_treasury_silver)
        deficit_grain = max(0.0, grain_needed - self.city_granary_barley)

        if player and player.wallet.silver_shekels >= deficit_silver and player.wallet.barley_qa >= deficit_grain:
            self.city_treasury_silver = max(0.0, self.city_treasury_silver - silver_needed)
            self.city_granary_barley = max(0.0, self.city_granary_barley - grain_needed)
            if deficit_silver > 0:
                player.wallet.spend_silver(deficit_silver)
            if deficit_grain > 0:
                player.wallet.spend_barley(deficit_grain)
            player.reputation = min(100.0, player.reputation + 2.0)
            return True, f"[Mayoral Emergency Subsidy] City silos were short! Governor {player.full_name} subsidized {deficit_silver:.2f} silver and {deficit_grain:.0f} qa grain (+2.0 Honor)."

        # 4. Desertion crisis if both city coffers and player cannot provide
        deserted_reg = self.standing_army.pop()
        if player:
            player.reputation = max(10.0, player.reputation - 6.0)
        return False, f" [!] Municipal Granary Empty! City granary holds {self.city_granary_barley:.0f} qa (needed {grain_needed:.0f} qa). Regiment {deserted_reg.id} deserted the walls!"

    # --------------------------------------------------------------------------
    # Military Campaigns & Expeditions
    # --------------------------------------------------------------------------

    def launch_campaign(
        self,
        player: Character,
        campaign_idx: int,
        participating_regiments: List[SoldierRegiment]
    ) -> BattleResult:
        """Executes a military campaign against external threats or joins imperial wars."""
        if not participating_regiments:
            return BattleResult(
                victory=False,
                title="Aborted",
                chronicle=["No regiments selected for campaign."],
                friendly_casualties=0,
                enemy_casualties=0
            )

        if campaign_idx == 1:
            # Repel Desert Nomad Raiders (Suteans)
            result = TacticalBattleEngine.resolve_battle(
                friendly_regiments=participating_regiments,
                enemy_name="Sutean Desert Nomad Raiders",
                enemy_range=40.0,
                enemy_chariot=15.0,
                enemy_melee=35.0,
                enemy_defense=25.0,
                enemy_morale=55.0,
                terrain="Euphrates Irrigation Perimeters"
            )
            if result.victory:
                silver_loot = round(random.uniform(25.0, 55.0), 2)
                grain_loot = round(random.uniform(150.0, 400.0), 1)
                result.spoils_silver = silver_loot
                result.spoils_barley_qa = grain_loot
                result.spoils_goods["wool"] = 4.0
                player.wallet.add_silver(silver_loot)
                player.wallet.add_barley(grain_loot)
                player.inventory["wool"] = player.inventory.get("wool", 0.0) + 4.0
                player.reputation = min(100.0, player.reputation + result.honor_gain)
                result.chronicle.append(f"\n [★] SPOILS SECURED: Recovered {silver_loot:.2f} silver shekels, {grain_loot:.0f} qa barley, and 4 raw wool bales from raider camps!")
            return result

        elif campaign_idx == 2:
            # Purge Caravan Bandits along Zagros Mountain Pass
            result = TacticalBattleEngine.resolve_battle(
                friendly_regiments=participating_regiments,
                enemy_name="Zagros Mountain Brigands & Deserters",
                enemy_range=30.0,
                enemy_chariot=0.0,
                enemy_melee=60.0,
                enemy_defense=45.0,
                enemy_morale=70.0,
                terrain="Rocky Foothills & Mountain Pass"
            )
            if result.victory:
                silver_loot = round(random.uniform(40.0, 85.0), 2)
                result.spoils_silver = silver_loot
                result.spoils_goods["copper_ore"] = 5.0
                result.spoils_goods["tin"] = 0.5
                player.wallet.add_silver(silver_loot)
                player.inventory["copper_ore"] = player.inventory.get("copper_ore", 0.0) + 5.0
                player.inventory["tin"] = player.inventory.get("tin", 0.0) + 0.5
                player.reputation = min(100.0, player.reputation + result.honor_gain + 5.0)
                result.chronicle.append(f"\n [★] TRADE ROUTE LIBERATED: Seized {silver_loot:.2f} silver, 5 copper ore, and 0.5 tin ingots from bandit cache!")
                result.chronicle.append("     Foreign caravan transit hazard drastically reduced for Babylon's merchants!")
            return result

        elif campaign_idx == 3:
            # Royal Imperial Campaign of King Hammurabi (Battle of Larsa / Elam)
            result = TacticalBattleEngine.resolve_battle(
                friendly_regiments=participating_regiments,
                enemy_name="Elamite Highland Vanguard & Larsa Garrison",
                enemy_range=75.0,
                enemy_chariot=60.0,
                enemy_melee=110.0,
                enemy_defense=85.0,
                enemy_morale=85.0,
                terrain="Open River Plain of Southern Sumer"
            )
            if result.victory:
                silver_loot = round(random.uniform(90.0, 160.0), 2)
                result.spoils_silver = silver_loot
                result.spoils_goods["bronze_weapons"] = 4.0
                result.spoils_goods["fine_linen"] = 3.0
                player.wallet.add_silver(silver_loot)
                player.inventory["bronze_weapons"] = player.inventory.get("bronze_weapons", 0.0) + 4.0
                player.inventory["fine_linen"] = player.inventory.get("fine_linen", 0.0) + 3.0
                player.reputation = min(100.0, player.reputation + 20.0)
                result.chronicle.append(f"\n [★] IMPERIAL TRIUMPH: Great King Hammurabi granted Governor {player.full_name} royal commendation!")
                result.chronicle.append(f"     Awarded {silver_loot:.2f} silver shekels, 4 captured bronze weapons, and 3 fine linen garments!")
                result.chronicle.append("     The bells of Esagila peal across Babylon in celebration of your victory!")
            return result

        else:
            # Military Drill
            for reg in participating_regiments:
                if reg.experience_level < 5:
                    reg.experience_level += 1
            return BattleResult(
                victory=True,
                title="Garrison Review & Military Drill",
                chronicle=[
                    "=== GRAND GARRISON INSPECTION AT THE PROCESSIONAL WAY ===",
                    f" Reviewed {sum(r.soldiers_count for r in participating_regiments)} soldiers.",
                    " [+] Combat drills, shield formation, and archery practice concluded.",
                    " [+] Participating regiments advanced in combat experience!"
                ],
                friendly_casualties=0,
                enemy_casualties=0,
                honor_gain=3.0
            )
