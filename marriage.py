"""
marriage.py - Mesopotamian Marriage, Dowry, and Domestic Alliance System
========================================================================
Implements:
1. Legal Marriage Covenant (rikistum) under Code of Hammurabi § 128.
2. The Bride-Price / Betrothal Gift (terhatum) paid to the bride's clan.
3. The Parental Dowry (šeriktum) managed by husband, strictly owned by wife.
4. Inter-Class Marriage Rules (Code §§ 175-176): Children of a free woman and
   slave husband are born legally FREE Mushkenum.
5. Divorce Settlements & Alimony (Code §§ 137-142): Return of dowry, child support,
   and severance fines (1 mina silver for Awilum, 1/3 mina for Mushkenum).
6. Lineage & Inheritance: Division of joint estate and paternal property.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import sys

# Ensure clean UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from economics import SocialClass, GoodsRegistry, Market
from character import Character, DualWallet, ClayTablet, DocumentType, CylinderSeal


# ==============================================================================
# 1. Marriage Status & Legal Enums
# ==============================================================================

class MarriageType(Enum):
    PATRICIAN_COVENANT = "Patrician Alliance (Awilum - Awilum)"
    COMMON_UNION = "Agrarian Commoner Marriage (Mushkenum - Mushkenum)"
    CROSS_CLASS_FREE_SLAVE = "Free Woman & State Servant (Code §§ 175-176)"
    CONCUBINAGE = "Secondary Wife / Concubinage (Šugītum - Code § 144)"


class DivorceReason(Enum):
    MUTUAL_CONSENT = "Mutual Agreement"
    CHILDLESSNESS = "Infertility / Barrenness (Code § 138)"
    CRUELTY_NEGLECT = "Neglect & Desertion by Husband (Code § 142)"
    INFIDELITY_MISCONDUCT = "Misconduct & Squandering of Household (Code § 141)"


# ==============================================================================
# 2. Dowry & Betrothal Structures
# ==============================================================================

@dataclass
class Dowry:
    """
    The parental gift (šeriktum) brought by the bride into the marriage.
    Managed by the husband during the marriage, but legally remains the wife's
    inalienable property and her children's inheritance (Code §§ 162-164).
    """
    silver_shekels: float = 0.0
    land_acres: float = 0.0
    goods: Dict[str, float] = field(default_factory=dict) # e.g. {"fine_linen": 2, "sheep": 5}
    oxen: int = 0
    slaves_wardum: int = 0

    @property
    def total_estimated_value_silver(self) -> float:
        # Land estimated at 25 silver/acre baseline, oxen at 15 silver, sheep at 2 silver
        land_val = self.land_acres * 25.0
        oxen_val = self.oxen * 15.0
        return self.silver_shekels + land_val + oxen_val


# ==============================================================================
# 3. The Marriage Contract Entity
# ==============================================================================

class MarriageContract:
    """
    The legally binding cuneiform marriage covenant (rikistum).
    Without this stamped clay contract, a marriage is null and void under Code § 128.
    """
    def __init__(
        self,
        id: str,
        husband: Character,
        wife: Character,
        bride_price_silver: float,       # terhatum
        dowry: Dowry,                    # šeriktum
        year_contracted: int = 1
    ):
        self.id = id
        self.husband = husband
        self.wife = wife
        self.bride_price_silver = bride_price_silver
        self.dowry = dowry
        self.year_contracted = year_contracted
        self.is_active = True

        # Joint Property accumulated strictly during the marriage
        self.joint_savings_silver: float = 0.0
        self.joint_land_acres: float = 0.0

        # Children born of this union
        self.children: List[Character] = []

        # Determine legal marriage type
        self.marriage_type = self._determine_type()

        # The cuneiform clay contract recording this covenant
        self.cuneiform_tablet = self._create_clay_tablet()

    def _determine_type(self) -> MarriageType:
        if self.husband.social_class == SocialClass.AWILUM and self.wife.social_class == SocialClass.AWILUM:
            return MarriageType.PATRICIAN_COVENANT
        elif self.husband.social_class == SocialClass.WARDUM and self.wife.social_class in (SocialClass.AWILUM, SocialClass.MUSHKENUM):
            return MarriageType.CROSS_CLASS_FREE_SLAVE
        else:
            return MarriageType.COMMON_UNION

    def _create_clay_tablet(self) -> ClayTablet:
        summary = (
            f"Marriage Covenant between {self.husband.full_name} and {self.wife.full_name}. "
            f"Bride-Price (Terhatum): {self.bride_price_silver:.1f} shekels. "
            f"Dowry (Seriktum): {self.dowry.silver_shekels:.1f} silver, {self.dowry.land_acres:.1f} acres. "
            f"Statutory Covenant under the Code of Hammurabi § 128."
        )
        tablet = ClayTablet(
            id=f"tablet_marriage_{self.id}",
            doc_type=DocumentType.MARRIAGE_CONTRACT,
            summary=summary,
            parties_involved=[self.husband.full_name, self.wife.full_name],
            principal_silver=self.bride_price_silver
        )
        # Stamped with husband's seal (and wife's if free)
        if self.husband.cylinder_seal:
            tablet.seal_document(self.husband.cylinder_seal)
        if self.wife.cylinder_seal:
            tablet.seal_document(self.wife.cylinder_seal)
        return tablet

    def add_child(self, name: str, gender: str = "male", age: int = 0) -> Character:
        """
        Registers a child born to this union.
        Code §§ 175-176: If the father is a state slave (Wardum) and the mother is a free woman,
        the children are born as FREE commoners (Mushkenum), not slaves!
        """
        if self.marriage_type == MarriageType.CROSS_CLASS_FREE_SLAVE:
            child_class = SocialClass.MUSHKENUM  # Legally free!
        else:
            child_class = self.husband.social_class

        patronymic = self.husband.name
        child = Character(name=name, patronymic=patronymic, social_class=child_class, age=age)
        self.children.append(child)
        return child


# ==============================================================================
# 4. The Marriage & Family Court Manager
# ==============================================================================

class MarriageManager:
    """
    Enforces marriage proposals, legal contract creation, dowry transfers,
    divorce arbitrations, and inheritance distribution under Babylonian Law.
    """
    def __init__(self):
        self.registry: Dict[str, MarriageContract] = {}
        self.contract_counter = 1

    def propose_and_marry(
        self,
        groom: Character,
        bride: Character,
        bride_price_silver: float,       # terhatum
        dowry: Dowry,                    # šeriktum
        bride_father: Optional[Character] = None,
        year: int = 1
    ) -> Tuple[bool, str, Optional[MarriageContract]]:
        """
        Executes a formal Babylonian marriage:
        1. Checks groom's solvency for bride-price (terhatum).
        2. Transfers terhatum to the bride's father (or bride if independent).
        3. Integrates dowry (šeriktum) assets under domestic administration.
        4. Stamps the cuneiform tablet with cylinder seals (Code § 128).
        """
        # Step 1: Check Bride-Price Solvency
        if groom.wallet.silver_shekels < bride_price_silver:
            return False, f"{groom.name} cannot afford the bride-price ({bride_price_silver} shekels silver needed).", None

        # Step 2: Pay Terhatum to Bride's Clan
        groom.wallet.spend_silver(bride_price_silver)
        if bride_father:
            bride_father.wallet.add_silver(bride_price_silver)

        # Step 3: Integrate Dowry Management
        # The husband administers the dowry land/oxen during the union
        groom.owned_land_acres += dowry.land_acres
        groom.owned_oxen += dowry.oxen
        groom.wallet.add_silver(dowry.silver_shekels)
        for g_id, qty in dowry.goods.items():
            groom.inventory[g_id] = groom.inventory.get(g_id, 0.0) + qty

        # Step 4: Create Binding Clay Covenant
        contract_id = f"covenant_{self.contract_counter:04d}"
        self.contract_counter += 1

        contract = MarriageContract(
            id=contract_id,
            husband=groom,
            wife=bride,
            bride_price_silver=bride_price_silver,
            dowry=dowry,
            year_contracted=year
        )

        groom.tablets.append(contract.cuneiform_tablet)
        bride.tablets.append(contract.cuneiform_tablet)
        self.registry[contract_id] = contract

        status_msg = (
            f"Marriage solemnized between {groom.full_name} and {bride.full_name}!\n"
            f"  * Terhatum Paid: {bride_price_silver:.1f} shekels silver\n"
            f"  * Seriktum Dowry: {dowry.silver_shekels:.1f} silver, {dowry.land_acres:.1f} acres land\n"
            f"  * Legal Status: {contract.marriage_type.value}\n"
            f"  * Sealed on Cuneiform Tablet: '{contract.cuneiform_tablet.id}'"
        )
        return True, status_msg, contract

    def grant_divorce(
        self,
        contract: MarriageContract,
        reason: DivorceReason,
        initiator: str = "husband"
    ) -> Tuple[bool, str]:
        """
        Arbitrates a legal divorce under Hammurabi's Code §§ 137-142:
        - If husband divorces mother of his children (§ 137): He must return her dowry
          and half the estate for child support.
        - If husband divorces childless wife (§§ 138-140): Returns dowry, returns bridal gift
          or pays statutory severance (1 mina / 60 shekels for Awilum; 20 shekels for Mushkenum).
        - If wife sues for neglect (§ 142): If innocent, takes dowry and returns to father's house.
        """
        if not contract.is_active:
            return False, "Marriage covenant is already dissolved."

        h = contract.husband
        w = contract.wife
        dowry = contract.dowry
        has_children = len(contract.children) > 0

        settlement_silver = 0.0
        returned_land = dowry.land_acres
        returned_silver = dowry.silver_shekels

        if initiator == "husband":
            if has_children:
                # Code § 137: Return dowry + give usufruct of half field/goods for children
                child_support_silver = contract.joint_savings_silver * 0.50
                child_support_land = contract.joint_land_acres * 0.50
                returned_silver += child_support_silver
                returned_land += child_support_land
                rule_cited = "Code of Hammurabi § 137 (Maternal Alimony & Child Support)"
            else:
                # Code §§ 138-140: Severance fine for divorcing childless wife
                if h.social_class == SocialClass.AWILUM:
                    settlement_silver = 60.0  # 1 mina (60 shekels) of silver
                else:
                    settlement_silver = 20.0  # 1/3 mina (20 shekels) of silver
                returned_silver += settlement_silver
                rule_cited = "Code of Hammurabi §§ 138-140 (Statutory Dowry & Severance Fine)"
        else:
            # Wife initiated (§ 142)
            rule_cited = "Code of Hammurabi § 142 (Judicial Separation for Neglect)"

        # Deduct assets from husband and return to wife
        h.owned_land_acres = max(0.0, h.owned_land_acres - returned_land)
        w.owned_land_acres += returned_land

        h.wallet.spend_silver(returned_silver)
        w.wallet.add_silver(returned_silver)

        contract.is_active = False

        verdict = (
            f"=== DIVORCE DECREE GRANTED ===\n"
            f" Legal Rule: {rule_cited}\n"
            f" Reason:     {reason.value}\n"
            f" Restitution to {w.full_name}:\n"
            f"   - Dowry Returned:     {dowry.silver_shekels:.1f} silver, {dowry.land_acres:.1f} acres land\n"
            f"   - Statutory Alimony:  {settlement_silver:.1f} shekels silver\n"
            f"   - Total Silver Paid:  {returned_silver:.1f} shekels\n"
            f"   - Total Land Awarded: {returned_land:.1f} acres\n"
            f" The marriage covenant is nullified."
        )
        return True, verdict

    def settle_widowhood(self, contract: MarriageContract, deceased: str = "husband") -> str:
        """
        Settles estate upon death under Code §§ 162-164 & 175-176:
        - Wife retains her full parental dowry (šeriktum); deceased's brothers cannot claim it.
        - If husband was a state servant (Wardum) and wife was free: Master takes 50% of joint
          property, while free widow and her free children keep the other 50% + dowry!
        """
        w = contract.wife
        h = contract.husband
        dowry = contract.dowry

        lines = [f"=== ESTATE INHERITANCE SETTLEMENT ==="]

        if deceased == "husband":
            lines.append(f" Deceased: {h.full_name} | Surviving Widow: {w.full_name}")

            if contract.marriage_type == MarriageType.CROSS_CLASS_FREE_SLAVE:
                lines.append(f" Legal Rule: Code of Hammurabi § 176 (Slave Husband & Free Wife)")
                # Joint property split: 50% to slave master, 50% to free family
                master_share_silver = contract.joint_savings_silver * 0.50
                family_share_silver = contract.joint_savings_silver * 0.50
                w.wallet.add_silver(family_share_silver + dowry.silver_shekels)
                w.owned_land_acres += dowry.land_acres
                lines.append(f"   * Slave Master Reclaims: {master_share_silver:.1f} shekels silver (50% joint wealth)")
                lines.append(f"   * Free Widow Retains:   {family_share_silver + dowry.silver_shekels:.1f} shekels silver + {dowry.land_acres:.1f} acres dowry")
                lines.append(f"   * Status of Children:   ALL {len(contract.children)} CHILDREN ARE FREE CITIZENS!")
            else:
                lines.append(f" Legal Rule: Code of Hammurabi § 162 (Paternal Dowry Protection)")
                w.owned_land_acres += dowry.land_acres
                w.wallet.add_silver(dowry.silver_shekels)
                lines.append(f"   * Widow retains full parental dowry: {dowry.land_acres:.1f} acres land, {dowry.silver_shekels:.1f} silver")
                lines.append(f"   * Dowry reserved exclusively for her children upon her eventual death.")

        contract.is_active = False
        return "\n".join(lines)


# ==============================================================================
# 5. Verification Demonstration
# ==============================================================================

if __name__ == "__main__":
    print("=" * 75)
    print("      BABYLONIAN RPG - MARRIAGE & DOMESTIC LAW ENGINE")
    print("               (Code of Hammurabi §§ 128 - 176)")
    print("=" * 75)

    mgr = MarriageManager()

    # 1. Patrician Match: Iddin-Marduk marries Amat-Ba'u (Awilum - Awilum)
    patrician_groom = Character("Iddin-Marduk", "Nabu-ahhe-iddin", SocialClass.AWILUM)
    patrician_bride = Character("Amat-Ba'u", "Marduk-nasir", SocialClass.AWILUM)
    bride_father = Character("Marduk-nasir", "Ibal-pi-El", SocialClass.AWILUM)

    patrician_dowry = Dowry(
        silver_shekels=40.0,
        land_acres=10.0,
        oxen=1,
        goods={"fine_linen": 3.0, "perfume": 2.0}
    )

    print("\n--- Test 1: Patrician Marriage Alliance (Awilum) ---")
    ok, msg, contract_1 = mgr.propose_and_marry(
        groom=patrician_groom,
        bride=patrician_bride,
        bride_price_silver=15.0,  # 15 shekels Terhatum
        dowry=patrician_dowry,
        bride_father=bride_father,
        year=1
    )
    print(msg)

    # Birth of a son
    son = contract_1.add_child(name="Bel-ibni", gender="male")
    print(f"\n[+] Child Born: {son.full_name} | Legal Class: {son.social_class.value}")

    # 2. Test Cross-Class Marriage (Code § 176): Slave Husband + Free Woman!
    print("\n" + "=" * 75)
    print("--- Test 2: Cross-Class Union (Wardum Husband + Free Commoner Wife) ---")
    slave_husband = Character("Warad-Sin", "Palace Household", SocialClass.WARDUM)
    slave_husband.wallet.silver_shekels = 5.0 # Saved some silver
    free_wife = Character("Ina-Esagila-zerat", "Ea-dayyan", SocialClass.MUSHKENUM)

    commoner_dowry = Dowry(silver_shekels=10.0, land_acres=3.0)
    ok, msg, contract_2 = mgr.propose_and_marry(
        groom=slave_husband,
        bride=free_wife,
        bride_price_silver=2.0,
        dowry=commoner_dowry,
        year=2
    )
    print(msg)

    # Birth of children under Code § 176
    daughter = contract_2.add_child(name="Belti-reminni", gender="female")
    print(f"[+] Child Born: {daughter.name} | Legal Class: {daughter.social_class.value} (Free commoner under Code § 176!)")

    # 3. Test Widowhood Settlement for the Cross-Class Union
    print("\n" + "-" * 75)
    print("Simulating Death of Slave Husband Warad-Sin...")
    contract_2.joint_savings_silver = 20.0 # Accumulated 20 silver during marriage
    settlement_report = mgr.settle_widowhood(contract_2, deceased="husband")
    print(settlement_report)

    # 4. Test Statutory Divorce & Alimony under Code § 138 (Childless Patrician)
    print("\n" + "=" * 75)
    print("--- Test 3: Childless Divorce & Alimony (Code §§ 138-140) ---")
    childless_groom = Character("Nabu-aplu-usur", "Sin-muballit", SocialClass.AWILUM)
    childless_groom.wallet.silver_shekels = 150.0
    childless_bride = Character("Erišti-Aya", "Rim-Sin", SocialClass.AWILUM)
    small_dowry = Dowry(silver_shekels=25.0, land_acres=5.0)

    _, _, contract_3 = mgr.propose_and_marry(
        groom=childless_groom,
        bride=childless_bride,
        bride_price_silver=10.0,
        dowry=small_dowry,
        year=3
    )

    # Husband divorces wife because of childlessness
    ok_div, div_msg = mgr.grant_divorce(
        contract=contract_3,
        reason=DivorceReason.CHILDLESSNESS,
        initiator="husband"
    )
    print(div_msg)
    print(f"Groom Wallet Remaining: {childless_groom.wallet.silver_shekels:.1f} shekels")
    print(f"Divorced Wife Wallet:   {childless_bride.wallet.silver_shekels:.1f} shekels")
    print("=" * 75)
