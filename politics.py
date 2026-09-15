"""
politics.py - Civic Offices, The Puhrum Assembly, and Legal Power Engine
========================================================================
Implements:
1. The 5 Civic Offices of Ancient Babylon:
   - Gugallum (Canal Warden): Controls water gates, corvée labor, canal dredging.
   - Rabi Sikkatim (Market Overseer): Controls city gate tariffs, silver purity, stall fees.
   - Dayyānum (City Magistrate / Judge): Presides over court at the Gate of Shamash.
   - Šangû (Temple Administrator / High Priest): Manages temple estates, tithes, sacred festivals.
   - Rabiānum (City Governor / Mayor): Executive command, city watch, petitions for royal debt jubilees.
2. The City Assembly (Puhrum) & Council of Elders (Šībūtum):
   - Election campaigning, populist beer feasts, patrician patronage, and oratory debates.
3. Official Powers & Abuse of Authority:
   - Skimming maintenance funds, extorting caravans, taking judicial bribes, water diversion.
4. Legal Warfare & Court Trials under the Code of Hammurabi:
   - Prosecuting political rivals for usury (>20% interest), canal dike negligence, or fraud.
5. The Royal Debt Jubilee (Misharum):
   - Wiping out agrarian debts to quell civic unrest.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import random
import sys

# Ensure clean UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from economics import SocialClass, Good, GoodsRegistry, Market
from character import Character, DualWallet, ClayTablet, DocumentType, CylinderSeal


# ==============================================================================
# 1. Civic Office Enums & Office Data
# ==============================================================================

class OfficeTitle(Enum):
    CANAL_WARDEN = "Gugallum (Canal Warden)"
    MARKET_OVERSEER = "Rabi Sikkatim (Market Overseer)"
    CITY_MAGISTRATE = "Dayyānum (City Magistrate & Judge)"
    HIGH_PRIEST = "Šangû (Temple Administrator & High Priest)"
    CITY_GOVERNOR = "Rabiānum (City Governor & Mayor)"


@dataclass
class OfficeDefinition:
    title: OfficeTitle
    department: str
    salary_silver_per_tick: float
    min_social_class: SocialClass
    min_prestige_seal: int
    description: str


OFFICE_CATALOG: Dict[OfficeTitle, OfficeDefinition] = {
    OfficeTitle.CANAL_WARDEN: OfficeDefinition(
        title=OfficeTitle.CANAL_WARDEN,
        department="Irrigation & Public Works",
        salary_silver_per_tick=5.0,
        min_social_class=SocialClass.MUSHKENUM,
        min_prestige_seal=3,
        description="Oversees river sluices, dikes, and corvée canal dredging across all agricultural sectors."
    ),
    OfficeTitle.MARKET_OVERSEER: OfficeDefinition(
        title=OfficeTitle.MARKET_OVERSEER,
        department="Commerce, Gates & Standards",
        salary_silver_per_tick=8.0,
        min_social_class=SocialClass.AWILUM,
        min_prestige_seal=8,
        description="Inspects caravan cargo at the city gates, verifies silver purity, and sets market tolls."
    ),
    OfficeTitle.CITY_MAGISTRATE: OfficeDefinition(
        title=OfficeTitle.CITY_MAGISTRATE,
        department="Justice & The Gate of Shamash",
        salary_silver_per_tick=12.0,
        min_social_class=SocialClass.AWILUM,
        min_prestige_seal=10,
        description="Adjudicates contract disputes, debts, and criminal liability under the Code of Hammurabi."
    ),
    OfficeTitle.HIGH_PRIEST: OfficeDefinition(
        title=OfficeTitle.HIGH_PRIEST,
        department="The Sacred Esagila Temple",
        salary_silver_per_tick=18.0,
        min_social_class=SocialClass.AWILUM,
        min_prestige_seal=15,
        description="Manages temple grain storehouses, sacred herds, religious tithes, and festival banquets."
    ),
    OfficeTitle.CITY_GOVERNOR: OfficeDefinition(
        title=OfficeTitle.CITY_GOVERNOR,
        department="Executive Command & Garrison",
        salary_silver_per_tick=25.0,
        min_social_class=SocialClass.AWILUM,
        min_prestige_seal=18,
        description="Commands the city watch, sets emergency grain quotas, and petitions the King for debt jubilees."
    )
}


# ==============================================================================
# 2. Judicial Court System (Code of Hammurabi)
# ==============================================================================

class LawsuitCharge(Enum):
    USURY_VIOLATION = "Charging interest above statutory 20% (Code § 88)"
    CANAL_NEGLIGENCE = "Neglecting dike and flooding neighbor's field (Code §§ 53-55)"
    TAVERN_FRAUD = "Accepting silver instead of grain at unfair rates (Code § 108)"
    BREACH_OF_CONTRACT = "Defaulting on sealed promissory note without just cause"
    FALSE_ACCUSATION = "Bringing a capital charge without proof (Code § 1)"


@dataclass
class JudicialCase:
    case_id: str
    accuser: Character
    defendant: Character
    charge: LawsuitCharge
    evidence_strength: float       # 0.0 (Fabricated) to 1.0 (Signed Cuneiform Tablet proof)
    damages_claimed_silver: float
    is_resolved: bool = False
    verdict: str = ""


# ==============================================================================
# 3. The City Politics Engine
# ==============================================================================

class BabylonianPolitics:
    """
    Simulates municipal power, electoral campaigns, judicial trials, and corrupt authority.
    """
    def __init__(self, registry: GoodsRegistry, market: Market):
        self.registry = registry
        self.market = market
        self.office_holders: Dict[OfficeTitle, Optional[Character]] = {t: None for t in OfficeTitle}
        
        # Policy Settings controlled by Office Holders
        self.canal_maintenance_funded: bool = True
        self.gate_customs_tariff_rate: float = 0.05  # 5% baseline
        self.temple_tithe_rate: float = 0.10         # 10% harvest tithe
        self.city_grain_reserve_target_gur: float = 100.0
        self.temple_treasury_silver: float = 200.0   # Treasury for the Esagila Temple
        
        # Court & Judicial Records
        self.pending_lawsuits: List[JudicialCase] = []
        self.case_counter = 1

    # --------------------------------------------------------------------------
    # Office Appointments & Elections
    # --------------------------------------------------------------------------

    def appoint_or_elect(
        self,
        candidate: Character,
        office_title: OfficeTitle,
        bribe_silver: float = 0.0,
        sponsor_feast: bool = False
    ) -> Tuple[bool, str]:
        """
        Runs an election or council appointment at the Puhrum City Assembly.
        Calculates votes from Commoners (Mushkenum) and Patricians (Awilum).
        """
        office_def = OFFICE_CATALOG[office_title]

        # Step 1: Check Legal Qualification
        if office_def.min_social_class == SocialClass.AWILUM and candidate.social_class != SocialClass.AWILUM:
            return False, f"Disqualified! {office_title.value} is restricted to patrician Awilum nobility."

        seal_prestige = candidate.cylinder_seal.prestige_rating if candidate.cylinder_seal else 0
        if seal_prestige < office_def.min_prestige_seal:
            return False, f"Inadequate status! Requires a cylinder seal with prestige >= {office_def.min_prestige_seal} (Candidate has {seal_prestige})."

        # Step 2: Compute Voting Points
        # Base support from reputation and oratory skill
        commoner_votes = candidate.reputation * 0.40 + candidate.skills.oratory * 8.0
        patrician_votes = candidate.reputation * 0.50 + candidate.skills.commerce * 5.0 + (candidate.wallet.silver_shekels / 10.0)

        # Populist Benefaction: Throwing a Feast of Ishtar
        if sponsor_feast:
            feast_cost_beer = 15.0
            feast_cost_bread = 20.0
            if candidate.inventory.get("barley_beer", 0.0) >= feast_cost_beer and candidate.inventory.get("bread", 0.0) >= feast_cost_bread:
                candidate.inventory["barley_beer"] -= feast_cost_beer
                candidate.inventory["bread"] -= feast_cost_bread
                commoner_votes += 35.0  # Massive populist surge from commoners!
            else:
                return False, "Cannot sponsor feast: missing 15 barley beer or 20 bread in inventory!"

        # Patrician Collusion / Bribery
        if bribe_silver > 0.0:
            if candidate.wallet.spend_silver(bribe_silver):
                patrician_votes += bribe_silver * 1.5
            else:
                return False, f"Cannot afford silver bribe ({bribe_silver} shekels needed)."

        total_vote_score = commoner_votes + patrician_votes
        threshold = 65.0  # Threshold to win the Assembly

        if total_vote_score >= threshold:
            # Check if replacing an existing holder
            old_holder = self.office_holders[office_title]
            if old_holder:
                old_holder.civic_office = None

            self.office_holders[office_title] = candidate
            candidate.civic_office = office_title.value
            candidate.reputation = min(100.0, candidate.reputation + 8.0)

            msg = (
                f"=== VICTORY IN THE PUHRUM ASSEMBLY ===\n"
                f" {candidate.full_name} has been confirmed as {office_title.value}!\n"
                f" Department: {office_def.department}\n"
                f" Assembly Vote Score: {total_vote_score:.1f} (Commoner: {commoner_votes:.1f} | Patrician: {patrician_votes:.1f})\n"
                f" Statutory Salary: {office_def.salary_silver_per_tick:.1f} silver shekels per season"
            )
            return True, msg
        else:
            candidate.reputation = max(0.0, candidate.reputation - 4.0)
            msg = (
                f"=== DEFEAT IN THE PUHRUM ASSEMBLY ===\n"
                f" {candidate.full_name} fell short of confirmation (Score: {total_vote_score:.1f} / {threshold:.1f} needed).\n"
                f" The Council of Elders rejected the candidacy."
            )
            return False, msg

    # --------------------------------------------------------------------------
    # Executive Powers & Actions of Office
    # --------------------------------------------------------------------------

    def execute_canal_warden_dredging(self, actor: Character, skim_silver: float = 0.0) -> Tuple[bool, str]:
        """Canal Warden (Gugallum) mobilizes corvée labor to clear irrigation canals."""
        if actor.civic_office != OfficeTitle.CANAL_WARDEN.value:
            return False, "Only the Canal Warden (Gugallum) can direct municipal irrigation works."

        budget_silver = 20.0
        if skim_silver > 0.0:
            if skim_silver > 10.0:
                return False, "Embezzlement too blatant! Scribes will detect missing silver."
            actor.wallet.add_silver(skim_silver)
            budget_silver -= skim_silver

        self.canal_maintenance_funded = True
        actor.reputation += 2.0 if skim_silver == 0.0 else -3.0

        msg = (
            f"=== MUNICIPAL CANAL DREDGING EXECUTED ===\n"
            f" Gugallum {actor.name} mobilized 40 corvée laborers.\n"
            f" Euphrates silt cleared; downstream farmlands receive +25% harvest throughput bonus!\n"
        )
        if skim_silver > 0.0:
            msg += f" [!] Corruption: Gugallum quietly diverted +{skim_silver:.1f} silver shekels to personal vault!"
        return True, msg

    def set_gate_customs_tariff(self, actor: Character, new_tariff_rate: float) -> Tuple[bool, str]:
        """Market Overseer (Rabi Sikkatim) adjusts city gate import tariffs."""
        if actor.civic_office != OfficeTitle.MARKET_OVERSEER.value:
            return False, "Only the Market Overseer (Rabi Sikkatim) can set city gate tariffs."

        if not (0.0 <= new_tariff_rate <= 0.20):
            return False, "Tariff rate must be between 0% and 20% under royal statute."

        self.gate_customs_tariff_rate = new_tariff_rate
        actor.reputation += 1.0 if new_tariff_rate <= 0.08 else -3.0

        return True, f"Rabi Sikkatim {actor.name} declared city gate tariff rate at {new_tariff_rate*100:.1f}% on foreign cargo."

    def petition_debt_jubilee_misharum(self, governor: Character) -> Tuple[bool, str]:
        """City Governor (Rabiānum) petitions the King in Babylon for a clean-slate debt jubilee."""
        if governor.civic_office != OfficeTitle.CITY_GOVERNOR.value:
            return False, "Only the City Governor (Rabiānum) can petition the King for a Misharum."

        # The King accepts if municipal unrest is high
        lines = [
            f"=== ROYAL DECREE: MISHARUM (EDICT OF JUSTICE) ===",
            f" By order of the Great King in Babylon, on petition of Governor {governor.full_name}:",
            f" 1. All consumer grain debts of peasants and commoners are NULLIFIED.",
            f" 2. Pledged ancestral fields are restored to original farming households.",
            f" 3. Debt-slaves (Wardum) held for agrarian insolvency are SET FREE.",
            f" 4. Commercial contracts between Tamkarum merchants remain strictly protected.",
            f" [+] Commoner unrest collapses by -40%! Governor popularity surges by +15%!"
        ]
        governor.reputation = min(100.0, governor.reputation + 15.0)
        return True, "\n".join(lines)

    def set_temple_tithe(self, actor: Character, new_rate: float) -> Tuple[bool, str]:
        """High Priest (Šangû) sets the religious tithe rate."""
        if actor.civic_office != OfficeTitle.HIGH_PRIEST.value:
            return False, "Only the High Priest (Šangû) can set the temple tithe rate."

        if not (0.0 <= new_rate <= 0.30):
            return False, "Tithe rate must be between 0% and 30%."

        self.temple_tithe_rate = new_rate
        if new_rate <= 0.05:
            actor.reputation = min(100.0, actor.reputation + 5.0)
            reaction = "Commoners praise your leniency!"
        elif new_rate >= 0.20:
            actor.reputation = max(0.0, actor.reputation - 10.0)
            reaction = "The commoners grumble at the heavy burden."
        else:
            reaction = "The tithe is considered standard."

        return True, f"High Priest {actor.name} decreed the temple tithe rate at {new_rate*100:.1f}%. {reaction}"

    def host_akitu_festival(self, actor: Character) -> Tuple[bool, str]:
        """High Priest (Šangû) hosts the Akitu New Year festival to gain reputation."""
        if actor.civic_office != OfficeTitle.HIGH_PRIEST.value:
            return False, "Only the High Priest (Šangû) can host the Akitu festival."

        festival_cost = 50.0
        if self.temple_treasury_silver < festival_cost:
            return False, f"The Esagila temple treasury cannot afford the Akitu festival (needs {festival_cost} silver)."

        self.temple_treasury_silver -= festival_cost
        actor.reputation = min(100.0, actor.reputation + 20.0)

        return True, (
            f"=== AKITU FESTIVAL SPONSORED ===\n"
            f" High Priest {actor.name} opened the temple storehouses for the New Year.\n"
            f" Cost: {festival_cost} silver drawn from the Temple Treasury.\n"
            f" [+] Massive public celebration! High Priest reputation surges by +20%!"
        )

    def divert_sacred_funds(self, actor: Character, amount: float) -> Tuple[bool, str]:
        """High Priest (Šangû) embezzles from the temple treasury."""
        if actor.civic_office != OfficeTitle.HIGH_PRIEST.value:
            return False, "Only the High Priest (Šangû) has access to the temple treasury."

        if self.temple_treasury_silver < amount:
            return False, f"The temple treasury only has {self.temple_treasury_silver:.1f} silver shekels left."

        if amount > 50.0:
            # Get caught!
            actor.reputation = max(0.0, actor.reputation - 25.0)
            return False, f"[!] BLASPHEMY! The scribes caught High Priest {actor.name} attempting to steal {amount} silver! Reputation plummets!"

        self.temple_treasury_silver -= amount
        actor.wallet.add_silver(amount)
        actor.reputation = max(0.0, actor.reputation - 2.0)

        return True, (
            f"[!] Corruption: High Priest {actor.name} quietly diverted {amount:.1f} silver shekels "
            f"from the sacred loans into their personal vault."
        )

    def excommunicate_rival(self, actor: Character, rival: Character) -> Tuple[bool, str]:
        """High Priest (Šangû) declares a rival ritually impure, destroying their reputation."""
        if actor.civic_office != OfficeTitle.HIGH_PRIEST.value:
            return False, "Only the High Priest (Šangû) can declare ritual impurity."

        if rival == actor:
            return False, "You cannot excommunicate yourself!"

        rival.reputation = max(0.0, rival.reputation - 30.0)

        return True, (
            f"=== DECLARATION OF RITUAL IMPURITY ===\n"
            f" High Priest {actor.name} has declared {rival.name} ritually impure and forbidden from entering the Esagila!\n"
            f" [-] {rival.name}'s reputation collapses by -30%!"
        )

    # --------------------------------------------------------------------------
    # Judicial Lawsuits & Litigation (Code of Hammurabi)
    # --------------------------------------------------------------------------

    def file_lawsuit(
        self,
        accuser: Character,
        defendant: Character,
        charge: LawsuitCharge,
        evidence_strength: float,
        damages_claimed_silver: float
    ) -> JudicialCase:
        """Files a legal claim to be tried before the City Magistrate at the Gate of Shamash."""
        case_id = f"case_{self.case_counter:04d}"
        self.case_counter += 1

        case = JudicialCase(
            case_id=case_id,
            accuser=accuser,
            defendant=defendant,
            charge=charge,
            evidence_strength=evidence_strength,
            damages_claimed_silver=damages_claimed_silver
        )
        self.pending_lawsuits.append(case)
        return case

    def adjudicate_case(
        self,
        case: JudicialCase,
        magistrate: Character,
        bribe_from_defendant: float = 0.0
    ) -> Tuple[bool, str]:
        """
        City Magistrate (Dayyānum) conducts a trial and delivers a binding cuneiform verdict.
        """
        lines = [
            f"=== TRIAL AT THE GATE OF SHAMASH ===",
            f" Presiding Magistrate: {magistrate.full_name}",
            f" Accuser:   {case.accuser.full_name}",
            f" Defendant: {case.defendant.full_name}",
            f" Charge:    {case.charge.value}"
        ]

        # Magistrate Corruption Check
        corrupted = False
        if bribe_from_defendant > 0.0:
            if case.defendant.wallet.spend_silver(bribe_from_defendant):
                magistrate.wallet.add_silver(bribe_from_defendant)
                corrupted = True
                lines.append(f" [!] Bribe accepted: Magistrate pocketed {bribe_from_defendant:.1f} shekels silver under the bench!")

        # Trial Logic
        if corrupted or case.evidence_strength < 0.40:
            # Defendant Acquitted
            case.is_resolved = True
            case.verdict = "ACQUITTED"
            lines.append(f" Verdict: DEFENDANT ACQUITTED due to insufficient clay tablet evidence.")
            # If false accusation was brought maliciously: Code § 1 penalty
            if case.evidence_strength < 0.20:
                penalty = 5.0
                case.accuser.wallet.spend_silver(penalty)
                case.accuser.reputation = max(0.0, case.accuser.reputation - 10.0)
                lines.append(f" Code § 1 Enforcement: Accuser fined {penalty:.1f} silver shekels for false witness!")
            return False, "\n".join(lines)
        else:
            # Defendant Convicted
            case.is_resolved = True
            case.verdict = "CONVICTED"
            fine = case.damages_claimed_silver
            case.defendant.wallet.spend_silver(fine)
            case.accuser.wallet.add_silver(fine)
            case.defendant.reputation = max(0.0, case.defendant.reputation - 15.0)

            # If defendant held a civic office, they are stripped of it
            if case.defendant.civic_office:
                for title, holder in self.office_holders.items():
                    if holder == case.defendant:
                        self.office_holders[title] = None
                lines.append(f" [!] DISQUALIFIED: Conviction strips {case.defendant.name} of public office ({case.defendant.civic_office})!")
                case.defendant.civic_office = None

            lines.append(f" Verdict: DEFENDANT CONVICTED under the statutes of Hammurabi!")
            lines.append(f" Damages Awarded: {fine:.1f} silver shekels transferred to accuser.")
            return True, "\n".join(lines)

    # --------------------------------------------------------------------------
    # Social Class Mobility: Ennoblement to Awīlum (Patrician Class)
    # --------------------------------------------------------------------------

    def petition_ennoblement_to_awilum(
        self,
        candidate: Character,
        marriage_contract: Optional[Any] = None
    ) -> Tuple[bool, str]:
        """
        Petitions the Council of Elders (Puhrum) to elevate a citizen to the patrician Awīlum class.
        Qualifications under Old Babylonian institutional custom:
        1. Aristocratic Marriage Alliance: Bound in a legal marriage covenant (Code § 128)
           with an Awīlum noblewoman (e.g., Amat-Ba'u of House Marduk).
        2. Landed Freehold Independence: Owning >= 15.0 acres of arable land, >= 1 draft ox,
           >= 50.0 silver shekels, and a cylinder seal with prestige >= 12.
        """
        if candidate.social_class == SocialClass.AWILUM:
            return False, "You are already recorded on the clay rolls as an Awīlum patrician."

        reasons = []
        approved = False

        # Path 1: Patrician Alliance through Marriage
        if marriage_contract and getattr(marriage_contract, "is_active", False):
            wife = getattr(marriage_contract, "wife", None)
            if wife and getattr(wife, "social_class", None) == SocialClass.AWILUM:
                approved = True
                dowry = getattr(marriage_contract, "dowry", None)
                d_land = getattr(dowry, "land_acres", 0.0) if dowry else 0.0
                d_silver = getattr(dowry, "silver_shekels", 0.0) if dowry else 0.0
                reasons.append(
                    f"Solemn marriage alliance with noble House {wife.patronymic or wife.name} "
                    f"(Dowry Estate in Custody: {d_land:.1f} acres, {d_silver:.1f} silver)"
                )

        # Path 2: Freehold Estate & Economic Independence
        has_land = candidate.owned_land_acres >= 15.0
        has_ox = candidate.owned_oxen >= 1
        has_silver = candidate.wallet.silver_shekels >= 50.0
        has_seal = candidate.cylinder_seal is not None and candidate.cylinder_seal.prestige_rating >= 12

        if has_land and has_ox and has_silver and has_seal:
            approved = True
            seal_mat = candidate.cylinder_seal.material if candidate.cylinder_seal else "carved"
            reasons.append(
                f"Landed Freehold Estate of {candidate.owned_land_acres:.1f} acres, {candidate.owned_oxen} draft oxen, "
                f"{candidate.wallet.silver_shekels:.1f} silver treasury, and {seal_mat} cylinder seal"
            )

        if not approved:
            return False, (
                "[-] The Council of Elders rejects your petition!\n"
                "    To be enrolled as Awīlum, you must fulfill either:\n"
                "    1. Solemn marriage alliance with an Awīlum patrician woman (Code § 128), OR\n"
                "    2. Hold at least 15 acres of arable land, 1 draft ox, 50 silver shekels, and a prestigious cylinder seal."
            )

        # Apply Ennoblement
        candidate.social_class = SocialClass.AWILUM
        candidate.reputation = min(100.0, candidate.reputation + 15.0)

        # Mint Royal Cuneiform Charter of Ennoblement
        charter_summary = (
            f"Imperial Charter of Patrician Ennoblement: {candidate.full_name} is hereby enrolled into "
            f"the rank of Awīlum by the Puhrum Council of Elders and King Hammurabi. Granted full patrician franchise, "
            f"standing in the courts of Shamash, and eligibility for all high civic magistracies."
        )
        charter_tablet = ClayTablet(
            id=f"tablet_ennoblement_{candidate.name.lower()}",
            doc_type=DocumentType.ROYAL_DECREE,
            summary=charter_summary,
            parties_involved=[candidate.full_name, "Puhrum Council of Elders", "King Hammurabi"]
        )
        if candidate.cylinder_seal:
            charter_tablet.seal_document(candidate.cylinder_seal)
        candidate.tablets.append(charter_tablet)

        verdict = [
            "======================================================================",
            "        ROYAL EDICT OF THE PUHRUM ASSEMBLY: PATRICIAN ENNOBLEMENT",
            "======================================================================",
            f" Citizen: {candidate.full_name}",
            f" Legal Grounds Approved by the Council:",
        ]
        for r in reasons:
            verdict.append(f"  * {r}")
        verdict.extend([
            "----------------------------------------------------------------------",
            " [★] VERDICT: The Council of Elders and King Hammurabi's royal scribes",
            "     have officially inscribed your name upon the golden tablet of the AWĪLUM!",
            " [★] Social Standing: +15 Reputation | Full Patrician Rights Acquired",
            " [★] All High Civic Offices are now unlocked for campaign:",
            "     - Rabi Sikkatim (Market Overseer)",
            "     - Dayyānum (City Magistrate & Judge)",
            "     - Šangû (High Priest of Esagila)",
            "     - Rabiānum (City Governor & Mayor)",
            "======================================================================"
        ])
        return True, "\n".join(verdict)



# ==============================================================================
# 4. Verification Demonstration
# ==============================================================================

if __name__ == "__main__":
    print("=" * 75)
    print("      BABYLONIAN RPG - CIVIC POLITICS & JUDICIAL ENGINE")
    print("                 (The Puhrum Assembly & The Law)")
    print("=" * 75)

    reg = GoodsRegistry()
    mkt = Market(reg)
    gov_sys = BabylonianPolitics(reg, mkt)

    # 1. Setup Candidates
    patrician = Character("Iddin-Marduk", "Nabu-ahhe-iddin", SocialClass.AWILUM)
    farmer = Character("Sin-nasir", "Enlil-bani", SocialClass.MUSHKENUM)

    print("\n--- Candidate Profiles ---")
    print(patrician.get_status_report())
    print("\n" + "-" * 75)
    print(farmer.get_status_report())

    # 2. Farmer campaigns for Canal Warden (Gugallum) by sponsoring a beer feast
    print("\n" + "=" * 75)
    print("--- Test 1: Puhrum Election for Canal Warden (Gugallum) ---")
    farmer.inventory["barley_beer"] = 20.0
    farmer.inventory["bread"] = 25.0
    
    ok, election_msg = gov_sys.appoint_or_elect(
        candidate=farmer,
        office_title=OfficeTitle.CANAL_WARDEN,
        sponsor_feast=True
    )
    print(election_msg)

    # 3. Farmer exercises Canal Warden power & skims a little maintenance silver
    if ok:
        print("\n" + "-" * 75)
        print("Canal Warden Sin-nasir mobilizes corvée labor...")
        ok_dredge, dredge_msg = gov_sys.execute_canal_warden_dredging(farmer, skim_silver=3.0)
        print(dredge_msg)
        print(f"Farmer Wallet now: {farmer.wallet.silver_shekels:.2f} silver shekels")

    # 4. Patrician runs for City Magistrate (Dayyānum) using silver influence
    print("\n" + "=" * 75)
    print("--- Test 2: Patrician Bribes Council for City Magistrate (Dayyānum) ---")
    ok_judge, judge_msg = gov_sys.appoint_or_elect(
        candidate=patrician,
        office_title=OfficeTitle.CITY_MAGISTRATE,
        bribe_silver=30.0
    )
    print(judge_msg)

    # 5. Court Trial under Code § 88 (Usury Charge)
    print("\n" + "=" * 75)
    print("--- Test 3: Judicial Trial at the Gate of Shamash (Code § 88) ---")
    rival_merchant = Character("Rim-Sin", "Sin-magir", SocialClass.AWILUM)
    rival_merchant.civic_office = OfficeTitle.MARKET_OVERSEER.value

    # Sin-nasir prosecutes Rim-Sin for charging 40% interest (exceeding statutory 20% cap)
    lawsuit = gov_sys.file_lawsuit(
        accuser=farmer,
        defendant=rival_merchant,
        charge=LawsuitCharge.USURY_VIOLATION,
        evidence_strength=0.85, # Strong evidence: signed cuneiform tablet
        damages_claimed_silver=25.0
    )

    # Magistrate Iddin-Marduk presides over the trial
    won, trial_report = gov_sys.adjudicate_case(
        case=lawsuit,
        magistrate=patrician,
        bribe_from_defendant=0.0 # No bribe, rule justly
    )
    print(trial_report)

    # 6. Petition for Royal Debt Jubilee (Misharum)
    print("\n" + "=" * 75)
    print("--- Test 4: Royal Debt Jubilee (Misharum) Decreed by Governor ---")
    patrician.civic_office = OfficeTitle.CITY_GOVERNOR.value # Promoted to Governor
    ok_misharum, misharum_report = gov_sys.petition_debt_jubilee_misharum(patrician)
    print(misharum_report)

    # 7. High Priest Mechanics
    print("\n" + "=" * 75)
    print("--- Test 5: High Priest (Šangû) Mechanics ---")
    patrician.civic_office = OfficeTitle.HIGH_PRIEST.value # Promoted to High Priest

    # 7a. Set Tithe Rate
    ok_tithe, tithe_msg = gov_sys.set_temple_tithe(patrician, 0.25)
    print(tithe_msg)

    # 7b. Host Akitu Festival
    ok_akitu, akitu_msg = gov_sys.host_akitu_festival(patrician)
    print(akitu_msg)

    # 7c. Embezzle Funds
    ok_embezzle, embezzle_msg = gov_sys.divert_sacred_funds(patrician, 20.0)
    print(embezzle_msg)
    print(f"Patrician Wallet after embezzlement: {patrician.wallet.silver_shekels:.2f} silver shekels")

    # 7d. Excommunicate Rival
    ok_excom, excom_msg = gov_sys.excommunicate_rival(patrician, rival_merchant)
    print(excom_msg)
    print(f"Rival Merchant Reputation: {rival_merchant.reputation:.1f}")

    print("=" * 75)
