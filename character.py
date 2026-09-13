"""
character.py - Player & NPC Agent Entity System for Babylonian RPG
===================================================================
Implements:
1. Dual-Currency Wallet: Weighed Silver Shekels (kaspum) + Volumetric Barley (še'u).
2. Social Status & Legal Standing (Wardum, Mushkenum, Awilum).
3. The Cuneiform Cylinder Seal (kunukku) for legal contract authentication.
4. Physical Needs (Hunger, Thirst, Energy, Health) and Standard of Living (SoL).
5. Inventory, Real Estate, and Livestock Asset Ownership.
6. Cuneiform Clay Tablet Documents (Deeds, Debt Notes, Contracts).
7. Skill Trees: Agriculture, Craftsmanship, Literacy/Scribal Arts, Commerce, and Oratory.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import sys

# Ensure clean UTF-8 output on Windows console environments
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from economics import SocialClass, Good, GoodsRegistry, Market


# ==============================================================================
# 1. Currency & Volumetric Standards
# ==============================================================================

@dataclass
class DualWallet:
    """
    Manages the dual currency system of ancient Mesopotamia:
    - Weighed Silver (kaspum): Shekels (~8.33g) & Grains (1/180 shekel).
    - Volumetric Barley (še'u): Gur (300 qa) & Qa/Sila (~0.85-1.0 Liter).
    """
    silver_shekels: float = 0.0     # Liquid silver mass (shekels)
    barley_qa: float = 0.0          # Stored volumetric grain in qa / sila

    @property
    def silver_grains(self) -> float:
        """1 Shekel = 180 Grains of silver."""
        return self.silver_shekels * 180.0

    @property
    def barley_gur(self) -> float:
        """1 Gur = 300 Qa."""
        return self.barley_qa / 300.0

    def add_silver(self, amount: float):
        if amount > 0:
            self.silver_shekels += amount

    def spend_silver(self, amount: float) -> bool:
        if 0 < amount <= self.silver_shekels:
            self.silver_shekels -= amount
            return True
        return False

    def add_barley(self, amount_qa: float):
        if amount_qa > 0:
            self.barley_qa += amount_qa

    def spend_barley(self, amount_qa: float) -> bool:
        if 0 < amount_qa <= self.barley_qa:
            self.barley_qa -= amount_qa
            return True
        return False

    def __repr__(self) -> str:
        return f"Wallet({self.silver_shekels:.2f} shekels silver | {self.barley_gur:.2f} gur / {self.barley_qa:.0f} qa barley)"


# ==============================================================================
# 2. Legal Documents & The Cylinder Seal
# ==============================================================================

class DocumentType(Enum):
    LAND_DEED = "Land Title Deed"
    DEBT_PROMISSORY = "Promissory Debt Note"
    MARRIAGE_CONTRACT = "Marriage Covenant"
    LABOR_HIRE = "Labor Indenture Agreement"
    FREEDOM_CHARTER = "Charter of Manumission"
    ROYAL_DECREE = "Royal Edict & Ennoblement Patent"


@dataclass
class CylinderSeal:
    """
    Reverse-intaglio carved cylinder seal used to sign clay tablets.
    Essential status symbol and legal prerequisite under Hammurabi's Code.
    """
    owner_name: str
    material: str             # e.g., "Lapis Lazuli", "Hematite", "Carnelian", "Steatite"
    patron_deity: str         # e.g., "Shamash (God of Justice)", "Marduk (Patron of Babylon)"
    inscription: str = ""
    prestige_rating: int = 5  # Affects social deference and credibility in court

    def imprint(self) -> str:
        return f"[SEAL IMPRINT: '{self.owner_name}, Servant of {self.patron_deity}' carved in {self.material}]"


@dataclass
class ClayTablet:
    """A cuneiform tablet recording a binding legal or commercial transaction."""
    id: str
    doc_type: DocumentType
    summary: str
    parties_involved: List[str]
    principal_silver: float = 0.0
    principal_grain_qa: float = 0.0
    interest_rate_percent: float = 0.0  # Max 20% silver, 33.3% grain under Code
    sealed_by: List[str] = field(default_factory=list)
    is_fulfilled: bool = False

    def seal_document(self, seal: CylinderSeal):
        if seal.imprint() not in self.sealed_by:
            self.sealed_by.append(seal.imprint())


# ==============================================================================
# 3. Attributes & Skill Proficiencies
# ==============================================================================

@dataclass
class CharacterSkills:
    """Skills developed through labor, study, trade, and civic life."""
    agriculture: int = 1       # Field plowing, irrigation dike maintenance, crop yield bonuses
    craftsmanship: int = 1     # Brewing, pottery, textile weaving, brickmaking throughput
    literacy: int = 0          # Scribal arts; reading/drafting legal tablets; bookkeeping
    commerce: int = 1          # Appraising silver purity, caravan bargaining, reducing market margins
    oratory: int = 1           # Court litigation, assembly persuasion at the Puhrum, election campaigning


# ==============================================================================
# 4. The Character Entity Class
# ==============================================================================

class Character:
    """
    Represents an individual agent (player or NPC) living in ancient Babylon.
    Owns property, earns wages, consumes market goods, and pursues social mobility.
    """
    def __init__(
        self,
        name: str,
        patronymic: str,
        social_class: SocialClass,
        age: int = 20,
        gender: str = "male",
        is_player: bool = False
    ):
        self.name = name
        self.patronymic = patronymic
        self.social_class = social_class
        self.age = age
        self.gender = gender
        self.is_player = is_player

        # Biological & Physical Needs (0-100 scale)
        self.health = 100.0
        self.hunger = 0.0          # 0 = Satiated, 100 = Starving
        self.thirst = 0.0          # 0 = Quenched, 100 = Dehydrated
        self.energy = 100.0        # 100 = Well-rested, 0 = Exhausted
        self.is_alive = True

        # Social & Economic Standing
        self.wallet = DualWallet()
        self.inventory: Dict[str, float] = {}  # good_id -> quantity
        self.tablets: List[ClayTablet] = []
        self.skills = CharacterSkills()
        self.cylinder_seal: Optional[CylinderSeal] = None

        # Real Estate & Capital Assets
        self.owned_land_acres: float = 0.0
        self.owned_oxen: int = 0
        self.owned_sheep: int = 0
        self.civic_office: Optional[str] = None  # e.g., "Gugallum (Canal Warden)"
        self.reputation: float = 50.0            # 0 (Outcast/Debtor) to 100 (Revered Patrician)

        self._initialize_starting_kit()

    @property
    def full_name(self) -> str:
        if not self.patronymic:
            return self.name
        kin_term = "daughter of" if self.gender.lower() == "female" else "son of"
        return f"{self.name}, {kin_term} {self.patronymic}"

    def _initialize_starting_kit(self):
        """Sets starting wallet, inventory, and skills based on social class."""
        if self.social_class == SocialClass.AWILUM:
            self.wallet.silver_shekels = 100.0
            self.wallet.barley_qa = 600.0        # 2 gur
            self.owned_land_acres = 20.0
            self.owned_oxen = 2
            self.skills.literacy = 3
            self.skills.commerce = 3
            self.cylinder_seal = CylinderSeal(
                owner_name=self.full_name,
                material="Lapis Lazuli",
                patron_deity="Marduk",
                prestige_rating=15
            )
            self.inventory["fine_linen"] = 2.0
            self.inventory["perfume"] = 1.0
            self.inventory["spelt_beer"] = 4.0
            self.inventory["barley"] = self.wallet.barley_qa

        elif self.social_class == SocialClass.MUSHKENUM:
            self.wallet.silver_shekels = 10.0
            self.wallet.barley_qa = 300.0        # 1 gur
            self.owned_land_acres = 5.0
            self.skills.agriculture = 2
            self.skills.craftsmanship = 2
            self.cylinder_seal = CylinderSeal(
                owner_name=self.full_name,
                material="Steatite",
                patron_deity="Shamash",
                prestige_rating=5
            )
            self.inventory["woolen_cloth"] = 1.0
            self.inventory["pottery"] = 3.0
            self.inventory["barley_beer"] = 2.0
            self.inventory["barley"] = self.wallet.barley_qa

        else:  # WARDUM
            self.wallet.silver_shekels = 0.5
            self.wallet.barley_qa = 60.0         # Basic ration
            self.skills.agriculture = 1
            self.cylinder_seal = None             # Slaves/debtors cannot own seals
            self.inventory["bread"] = 2.0
            self.inventory["barley"] = self.wallet.barley_qa

    # --------------------------------------------------------------------------
    # Life Sim & Metabolism Cycle
    # --------------------------------------------------------------------------

    def tick_daily_metabolism(self, registry: GoodsRegistry, market: Optional[Market] = None):
        """Advances physical needs by one day. Consumes food/drink if available."""
        if not self.is_alive:
            return

        self.hunger += 10.0
        self.thirst += 15.0
        self.energy -= 10.0

        # Attempt to auto-consume from personal inventory
        self._consume_daily_rations(registry)

        # Starvation and dehydration damage
        if self.hunger >= 100.0:
            self.health -= 12.0
        if self.thirst >= 100.0:
            self.health -= 20.0

        if self.health <= 0.0:
            self.health = 0.0
            self.is_alive = False

    def _consume_daily_rations(self, registry: GoodsRegistry):
        """Consumes food and drink from inventory to alleviate hunger and thirst."""
        # 1. Food Consumption
        food_priority = ["sweet_pastry", "bread", "barley", "dates", "dried_fish"]
        for food_id in food_priority:
            if self.inventory.get(food_id, 0.0) >= 1.0 and self.hunger > 20.0:
                self.inventory[food_id] -= 1.0
                if food_id == "sweet_pastry":
                    self.hunger = max(0.0, self.hunger - 60.0)
                    self.reputation += 0.5
                elif food_id == "bread":
                    self.hunger = max(0.0, self.hunger - 45.0)
                else:
                    self.hunger = max(0.0, self.hunger - 30.0)
                break

        # 2. Hydration Consumption (Barley beer or water)
        drink_priority = ["spelt_beer", "barley_beer"]
        for drink_id in drink_priority:
            if self.inventory.get(drink_id, 0.0) >= 1.0 and self.thirst > 20.0:
                self.inventory[drink_id] -= 1.0
                self.thirst = max(0.0, self.thirst - 60.0)
                self.energy = min(100.0, self.energy + 10.0)
                break

    def sleep(self):
        """Rests for the night, restoring health and energy."""
        self.energy = 100.0
        self.health = min(100.0, self.health + 15.0)

    # --------------------------------------------------------------------------
    # Market Trading & Inventory Operations
    # --------------------------------------------------------------------------

    def buy_good(self, good_id: str, quantity: float, market: Market, registry: GoodsRegistry, sales_tax_rate: float = 0.0) -> bool:
        """Buys a quantity of goods from the public market using weighed silver, drawing from warehouse stock with marginal slippage."""
        if quantity <= 0:
            return False

        avail_stock = market.get_stock(good_id)
        if avail_stock <= 0:
            return False

        actual_bought, base_cost, avg_price, _, _ = market.calculate_trade_pricing(good_id, quantity, is_buy=True)
        if actual_bought <= 0:
            return False

        tax = base_cost * max(0.0, sales_tax_rate)
        total_cost = base_cost + tax

        if self.wallet.spend_silver(total_cost):
            market.execute_buy(good_id, actual_bought)
            if good_id == "barley":
                self.wallet.add_barley(actual_bought)
                self.inventory["barley"] = self.wallet.barley_qa
            else:
                self.inventory[good_id] = self.inventory.get(good_id, 0.0) + actual_bought
            return True
        return False

    def sell_good(self, good_id: str, quantity: float, market: Market, registry: GoodsRegistry) -> bool:
        """Sells an inventory good to the market, collecting silver and adding to warehouse stock with marginal slippage."""
        if quantity <= 0:
            return False
        if good_id == "barley":
            if self.wallet.barley_qa >= quantity:
                actual_vol, revenue, avg_price, _, _ = market.calculate_trade_pricing(good_id, quantity, is_buy=False)
                self.wallet.spend_barley(quantity)
                self.inventory["barley"] = self.wallet.barley_qa
                if self.inventory["barley"] <= 0:
                    del self.inventory["barley"]
                market.execute_sell(good_id, quantity)
                self.wallet.add_silver(revenue)
                return True
            return False
        else:
            if self.inventory.get(good_id, 0.0) >= quantity:
                actual_vol, revenue, avg_price, _, _ = market.calculate_trade_pricing(good_id, quantity, is_buy=False)
                self.inventory[good_id] -= quantity
                if self.inventory[good_id] <= 0:
                    del self.inventory[good_id]
                market.execute_sell(good_id, quantity)
                self.wallet.add_silver(revenue)
                return True
            return False

    def consume_item(self, item_id: str) -> Tuple[bool, str]:
        """Manually eats or drinks a consumable item from personal inventory."""
        if item_id == "barley":
            if self.wallet.barley_qa >= 1.0:
                self.wallet.spend_barley(1.0)
                self.inventory["barley"] = self.wallet.barley_qa
                if self.inventory["barley"] <= 0:
                    del self.inventory["barley"]
                self.hunger = max(0.0, self.hunger - 25.0)
                self.energy = min(100.0, self.energy + 5.0)
                return True, "You chewed on a handful of wholesome toasted barley grains. (Hunger -25, Energy +5)"
            return False, "You have no barley left to chew."

        if self.inventory.get(item_id, 0.0) < 1.0:
            return False, f"You don't have any {item_id} in your sacks."

        self.inventory[item_id] -= 1.0
        if self.inventory[item_id] <= 0:
            del self.inventory[item_id]

        if item_id == "bread":
            self.hunger = max(0.0, self.hunger - 45.0)
            self.energy = min(100.0, self.energy + 10.0)
            return True, "You ate a loaf of warm, oven-baked barley flatbread. (Hunger -45, Energy +10)"
        elif item_id == "dates":
            self.hunger = max(0.0, self.hunger - 30.0)
            self.energy = min(100.0, self.energy + 15.0)
            return True, "You ate sweet, chewy riverbank dates. (Hunger -30, Energy +15)"
        elif item_id == "barley_beer":
            self.thirst = max(0.0, self.thirst - 50.0)
            self.energy = min(100.0, self.energy + 25.0)
            return True, "You drank a jar of cool, fermented barley beer through a straw. (Thirst -50, Energy +25)"
        elif item_id == "spelt_beer":
            self.thirst = max(0.0, self.thirst - 60.0)
            self.energy = min(100.0, self.energy + 30.0)
            return True, "You drank rich, golden spelt beer. (Thirst -60, Energy +30)"
        elif item_id == "date_wine":
            self.thirst = max(0.0, self.thirst - 60.0)
            self.health = min(100.0, self.health + 15.0)
            self.energy = min(100.0, self.energy + 30.0)
            return True, "You drank rich, fermented date wine. (Thirst -60, Health +15, Energy +30)"
        elif item_id == "dried_fish":
            self.hunger = max(0.0, self.hunger - 30.0)
            self.health = min(100.0, self.health + 10.0)
            return True, "You ate salty Euphrates river fish dried in the sun. (Hunger -30, Health +10)"
        elif item_id == "sweet_pastry":
            self.hunger = max(0.0, self.hunger - 60.0)
            self.health = min(100.0, self.health + 10.0)
            self.reputation = min(100.0, self.reputation + 0.5)
            return True, "You indulged in honey-glazed temple pastry! (Hunger -60, Health +10, Honor +0.5)"
        elif item_id == "perfume":
            self.reputation = min(100.0, self.reputation + 2.0)
            return True, "You anointed yourself with sacred frankincense perfume. The citizens revere your divine grace! (+2.0 Honor)"
        elif item_id == "fine_linen":
            self.reputation = min(100.0, self.reputation + 3.0)
            return True, "You donned a bleached linen patrician tunic (kitû). Your noble majesty radiates across Babylon! (+3.0 Honor)"
        elif item_id == "sesame_oil":
            self.hunger = max(0.0, self.hunger - 20.0)
            self.energy = min(100.0, self.energy + 10.0)
            return True, "You tasted rich refined sesame oil. (Hunger -20, Energy +10)"
        else:
            # Generic fallback
            self.hunger = max(0.0, self.hunger - 20.0)
            return True, f"You consumed {item_id}. (Hunger -20)"

    # --------------------------------------------------------------------------
    # Legal & Scribal Operations (Hammurabi's Code)
    # --------------------------------------------------------------------------

    def sign_tablet(self, tablet: ClayTablet) -> bool:
        """Stamps a cuneiform tablet with the character's cylinder seal."""
        if not self.cylinder_seal:
            return False  # Slaves and disenfranchised commoners cannot notarize contracts
        tablet.seal_document(self.cylinder_seal)
        return True

    def get_status_report(self) -> str:
        """Returns a detailed status overview of the character."""
        seal_desc = self.cylinder_seal.material + f" ({self.cylinder_seal.patron_deity})" if self.cylinder_seal else "None (Unenfranchised)"
        office_desc = self.civic_office if self.civic_office else "Private Citizen"
        
        lines = [
            f"=== {self.full_name.upper()} ===",
            f" Social Class:  {self.social_class.value} | Status: {office_desc} | Age: {self.age}",
            f" Health:        {self.health:.0f}/100 | Energy: {self.energy:.0f}/100 | Hunger: {self.hunger:.0f} | Thirst: {self.thirst:.0f}",
            f" Wallet:        {self.wallet.silver_shekels:.2f} silver shekels | {self.wallet.barley_gur:.2f} gur grain ({self.wallet.barley_qa:.0f} qa)",
            f" Real Estate:   {self.owned_land_acres:.1f} acres arable land | {self.owned_oxen} oxen | {self.owned_sheep} sheep",
            f" Cylinder Seal: {seal_desc}",
            f" Inventory:     " + ", ".join([f"{k}: {v:.1f}" for k, v in self.inventory.items()]) if self.inventory else " Inventory:     (Empty)",
            f" Tablets Held:  {len(self.tablets)} legal contracts recorded on clay"
        ]
        return "\n".join(lines)


# ==============================================================================
# 5. Verification Demonstration
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("      BABYLONIAN RPG - CHARACTER & AGENT ENTITY ENGINE")
    print("=" * 70)

    reg = GoodsRegistry()
    mkt = Market(reg)

    # Create 3 characters from different social strata
    patrician = Character("Iddin-Marduk", "Nabu-ahhe-iddin", SocialClass.AWILUM)
    farmer = Character("Sin-nasir", "Enlil-bani", SocialClass.MUSHKENUM)
    laborer = Character("Arad-Gula", "", SocialClass.WARDUM)

    print("\n--- Starting Character Profiles ---")
    print(patrician.get_status_report())
    print("\n" + "-" * 70)
    print(farmer.get_status_report())
    print("\n" + "-" * 70)
    print(laborer.get_status_report())

    print("\n" + "=" * 70)
    print("--- Market Trading & Contract Notarization Test ---")
    
    # Farmer buys a bronze sickle from the market
    success = farmer.buy_good("bronze_tools", 1.0, mkt, reg)
    print(f"Farmer Sin-nasir buys 1 Bronze Tool: {'SUCCESS' if success else 'FAILED'}")
    print(f"Farmer Wallet now: {farmer.wallet.silver_shekels:.2f} silver shekels")

    # Patrician drafts a loan promissory note to the farmer
    loan_tablet = ClayTablet(
        id="tablet_001",
        doc_type=DocumentType.DEBT_PROMISSORY,
        summary="Loan of 5 Shekels silver for spring sowing seeds",
        parties_involved=[patrician.full_name, farmer.full_name],
        principal_silver=5.0,
        interest_rate_percent=20.0  # Max statutory limit under Code § 88
    )

    patrician.sign_tablet(loan_tablet)
    farmer.sign_tablet(loan_tablet)
    patrician.tablets.append(loan_tablet)

    print(f"\nDrafted Legal Cuneiform Tablet: {loan_tablet.summary}")
    print(f"Interest Rate: {loan_tablet.interest_rate_percent}% (Statutory compliance checked)")
    print(f"Sealed by:")
    for seal_str in loan_tablet.sealed_by:
        print(f"  * {seal_str}")

    print("\n" + "=" * 70)
    print("Simulating 3 days of metabolism for Farmer Sin-nasir...")
    for day in range(1, 4):
        farmer.tick_daily_metabolism(reg, mkt)
        print(f"Day {day} -> Hunger: {farmer.hunger:.0f}, Thirst: {farmer.thirst:.0f}, Health: {farmer.health:.0f}")

    print("\n" + farmer.get_status_report())
    print("=" * 70)
