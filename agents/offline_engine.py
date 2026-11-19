"""
agents/offline_engine.py
========================
High-precision, deterministic Legal Intelligence Engine for ClauseGuard AI.
Enables full contract analysis, clause extraction, risk assessment,
negotiation recommendations, grounding verification, and RAG Q&A
WITHOUT requiring external API keys or network calls.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple

from schemas.clause_schema import ClauseExtractionResult, ExtractedClause
from schemas.risk_schema import (
    GroundingCheck,
    GroundingResult,
    NegotiationPoint,
    NegotiationResult,
    RiskAuditResult,
    RiskItem,
    RiskLevel,
)

# ---------------------------------------------------------------------------
# Document Type Detection
# ---------------------------------------------------------------------------

_DOC_PATTERNS = {
    "Employment Agreement": [
        r"employment", r"offer letter", r"employee", r"employer", r"salary",
        r"ctc", r"probation", r"notice period", r"service bond", r"designation",
        r"annual leave", r"bonus", r"joining date", r"work hours"
    ],
    "Rental Agreement": [
        r"lease", r"tenant", r"landlord", r"lessor", r"lessee", r"rent",
        r"premises", r"security deposit", r"maintenance", r"fixtures",
        r"vacating", r"occupancy", r"subletting"
    ],
    "Freelance Contract": [
        r"freelance", r"contractor", r"client", r"statement of work", r"sow",
        r"deliverable", r"milestone", r"invoice", r"net\s*\d+", r"independent contractor",
        r"hourly rate", r"retainer"
    ],
    "Non-Disclosure Agreement": [
        r"confidential information", r"disclosing party", r"receiving party",
        r"non-disclosure", r"proprietary information", r"trade secret"
    ],
}


def detect_document_type(text: str) -> str:
    """Classify the contract into a specific document type."""
    text_lower = text.lower()
    scores = {}
    for doc_type, patterns in _DOC_PATTERNS.items():
        count = sum(1 for p in patterns if re.search(r"\b" + p + r"\b", text_lower))
        scores[doc_type] = count
    best, score = max(scores.items(), key=lambda kv: kv[1])
    return best if score >= 2 else "Commercial Agreement"


# ---------------------------------------------------------------------------
# Clause Extraction Rules & Heuristics
# ---------------------------------------------------------------------------

CLAUSE_DEFINITIONS = [
    {
        "clause_type": "notice_period",
        "title": "Notice Period & Resignation",
        "keywords": [
            r"notice period", r"notice of termination", r"prior notice",
            r"resignation", r"written notice", r"\b\d+\s*(?:day|days|month|months)\s*notice"
        ],
        "summary_tpl": "Defines the mandatory notice duration required before resigning or terminating the contract.",
    },
    {
        "clause_type": "service_bond",
        "title": "Service Bond / Minimum Commitment",
        "keywords": [
            r"service bond", r"minimum service", r"training bond", r"commitment period",
            r"retention period", r"training cost recovery", r"original certificates",
            r"bank guarantee", r"obligated to serve"
        ],
        "summary_tpl": "Imposes a mandatory minimum tenure commitment, often backed by financial penalties or document retention.",
    },
    {
        "clause_type": "termination",
        "title": "Termination of Agreement",
        "keywords": [
            r"termination", r"terminate this agreement", r"with cause", r"without cause",
            r"immediate termination", r"breach of contract", r"summary dismissal", r"right to terminate"
        ],
        "summary_tpl": "Specifies conditions, grounds, and procedures under which either party may end the agreement.",
    },
    {
        "clause_type": "exit_penalty",
        "title": "Exit Penalty & Liquidated Damages",
        "keywords": [
            r"liquidated damages", r"penalty", r"exit fee", r"forfeit", r"payback",
            r"reimburse the company", r"damages of", r"deducted from final settlement",
            r"financial penalty"
        ],
        "summary_tpl": "Requires payment or salary forfeiture if the signing party terminates the engagement early.",
    },
    {
        "clause_type": "confidentiality",
        "title": "Confidentiality & Non-Disclosure",
        "keywords": [
            r"confidential information", r"non-disclosure", r"proprietary information",
            r"trade secret", r"keep strictly confidential", r"confidentiality obligations"
        ],
        "summary_tpl": "Restricts sharing or unauthorized use of sensitive, business, or proprietary information.",
    },
    {
        "clause_type": "ip_ownership",
        "title": "Intellectual Property Ownership",
        "keywords": [
            r"intellectual property", r"work made for hire", r"assignment of inventions",
            r"inventions", r"moral rights", r"sole and exclusive property", r"copyright",
            r"patents and trademarks"
        ],
        "summary_tpl": "Governs the allocation and assignment of intellectual property created during the engagement.",
    },
    {
        "clause_type": "auto_renewal",
        "title": "Auto-Renewal & Extension",
        "keywords": [
            r"auto-renew", r"automatically renew", r"successive terms", r"escalation",
            r"extension of term", r"automatic extension", r"renewed unless notice"
        ],
        "summary_tpl": "Causes the contract to renew automatically unless timely written notice of cancellation is given.",
    },
    {
        "clause_type": "payment_terms",
        "title": "Payment Terms & Invoicing",
        "keywords": [
            r"payment terms", r"compensation", r"invoice", r"net\s*\d+",
            r"security deposit", r"disbursement", r"late payment", r"monthly rent",
            r"deductions", r"remuneration"
        ],
        "summary_tpl": "Outlines compensation amounts, payment schedules, invoicing deadlines, and deduction rules.",
    },
    {
        "clause_type": "non_compete",
        "title": "Non-Compete & Restrictive Covenants",
        "keywords": [
            r"non-compete", r"restrictive covenant", r"solicit", r"competing business",
            r"non-solicitation", r"poach", r"prohibited from working", r"competitor"
        ],
        "summary_tpl": "Restricts working for competing businesses or soliciting clients and coworkers after departure.",
    },
    {
        "clause_type": "governing_law",
        "title": "Governing Law & Jurisdiction",
        "keywords": [
            r"governing law", r"jurisdiction", r"laws of", r"courts of",
            r"arbitration", r"dispute resolution", r"exclusive jurisdiction"
        ],
        "summary_tpl": "Establishes which legal jurisdiction and court or arbitration forum will resolve disputes.",
    },
]


def extract_clauses_offline(
    full_text: str,
    chunks: List[dict],
) -> ClauseExtractionResult:
    """Deterministic clause extractor using legal regex and context analysis."""
    doc_type = detect_document_type(full_text)
    extracted: List[ExtractedClause] = []
    found_types = set()

    # Pre-clean text blocks
    text_blocks = [c.get("text", "") for c in chunks] if chunks else [full_text]

    for defn in CLAUSE_DEFINITIONS:
        c_type = defn["clause_type"]
        title = defn["title"]
        keywords = defn["keywords"]

        best_match_text = ""
        best_match_page = 1
        best_match_score = 0

        # Scan chunks first for page fidelity
        for chunk in chunks:
            c_text = chunk.get("text", "")
            c_page = chunk.get("page", 1)
            score = 0
            for kw in keywords:
                if re.search(kw, c_text, re.IGNORECASE):
                    score += 1
            if score > best_match_score:
                best_match_score = score
                best_match_text = c_text
                best_match_page = c_page

        # Fallback to full_text scanning if not found in chunks
        if best_match_score == 0:
            for kw in keywords:
                m = re.search(rf"(?:^|\n)([^\n]*?{kw}[^\n]*?(?:\n[^\n]+){{0,3}})", full_text, re.IGNORECASE)
                if m:
                    best_match_text = m.group(1).strip()
                    best_match_score = 1
                    best_match_page = 1
                    break

        if best_match_score > 0 and best_match_text:
            # Extract most relevant passage (2-4 sentences)
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", best_match_text) if s.strip()]
            relevant_sentences = []
            for s in sentences:
                if any(re.search(kw, s, re.IGNORECASE) for kw in keywords):
                    relevant_sentences.append(s)
            if not relevant_sentences:
                relevant_sentences = sentences[:3]
            excerpt = " ".join(relevant_sentences[:4])
            if len(excerpt) > 400:
                excerpt = excerpt[:397] + "..."

            extracted.append(
                ExtractedClause(
                    clause_type=c_type,  # type: ignore
                    title=title,
                    original_text=excerpt,
                    page_number=max(1, best_match_page),
                    summary=defn["summary_tpl"],
                    is_present=True,
                )
            )
            found_types.add(c_type)
        else:
            # Note missing clause
            pass

    all_defined = {d["clause_type"] for d in CLAUSE_DEFINITIONS}
    missing = list(all_defined - found_types)

    return ClauseExtractionResult(
        document_type=doc_type,
        clauses=extracted,
        missing_clause_types=missing,
        raw_llm_response="Generated via ClauseGuard Offline Legal Intelligence Engine",
    )


# ---------------------------------------------------------------------------
# Risk Audit Rules & Checklist Engine
# ---------------------------------------------------------------------------

def audit_risks_offline(
    extraction_result: ClauseExtractionResult,
) -> RiskAuditResult:
    """Evaluate risks with explainable checklists and deterministic scores."""
    items: List[RiskItem] = []

    for clause in extraction_result.clauses:
        text = clause.original_text.lower()
        c_type = clause.clause_type
        risk_level: RiskLevel = "Low"
        risk_score = 2
        concerns: List[str] = []
        checklist: dict[str, bool] = {}
        action = "Accept standard wording."

        if c_type == "notice_period":
            # Check duration
            match_days = re.search(r"(\d+)\s*days?", text)
            match_months = re.search(r"(\d+)\s*months?", text)
            days = 0
            if match_days:
                days = int(match_days.group(1))
            elif match_months:
                days = int(match_months.group(1)) * 30

            checklist = {
                "Is notice duration mutual for both parties?": "mutual" in text or "either party" in text,
                "Is notice period 30 days or less?": days > 0 and days <= 30,
                "Is option to buy out notice available?": "payment in lieu" in text or "buyout" in text,
            }

            if days >= 90 or "3 months" in text or "90 days" in text:
                risk_level = "High"
                risk_score = 8
                concerns.append("Excessive notice duration (90 days / 3 months) severely limits future job transitions.")
                concerns.append("Many potential employers cannot wait 90 days for onboarding.")
                action = "Negotiate to reduce notice period to standard 30 or 45 days."
            elif days >= 60 or "60 days" in text or "2 months" in text:
                risk_level = "Medium"
                risk_score = 5
                concerns.append("60-day notice period is moderately restrictive.")
                action = "Request 30 days notice or mutual notice buyout terms."
            else:
                risk_level = "Low"
                risk_score = 2
                action = "Standard notice period is reasonable."

        elif c_type == "service_bond":
            checklist = {
                "Is there a mandatory service tenure requirement?": True,
                "Are financial penalties attached to early departure?": any(k in text for k in ["reimburse", "penalty", "pay", "$", "usd", "rs", "inr"]),
                "Are original educational certificates being withheld?": any(k in text for k in ["certificate", "original document", "retention"]),
            }
            if any(k in text for k in ["certificate", "original document", "deposit passport"]):
                risk_level = "High"
                risk_score = 10
                concerns.append("ILLEGAL / UNFAIR: Withholding original academic documents or passport is prohibited by law.")
                concerns.append("Substantial financial bond required upon departure.")
                action = "Refuse certificate retention immediately; demand removal of the bond clause."
            elif any(k in text for k in ["$", "usd", "rs", "inr", "penalty", "bond", "2 years", "two years"]):
                risk_level = "High"
                risk_score = 8
                concerns.append("Financial penalty or bond locks you in for a mandatory tenure.")
                concerns.append("Repayment clauses may apply regardless of reasons for resignation.")
                action = "Negotiate removal of service bond or limit liability strictly to prorated, actual training costs with receipts."
            else:
                risk_level = "Medium"
                risk_score = 6
                concerns.append("Minimum commitment clause restricts early career mobility.")
                action = "Request clear exceptions for medical, relocation, or personal emergencies."

        elif c_type == "termination":
            is_unilateral = any(k in text for k in ["sole discretion", "without notice", "immediate termination without cause"])
            checklist = {
                "Can company terminate without cause?": is_unilateral,
                "Does employee receive adequate severance or notice?": "severance" in text or "notice" in text,
                "Is cure period provided for alleged breach?": "cure" in text or "remedy" in text or "14 days" in text or "30 days" in text,
            }
            if is_unilateral or ("without cause" in text and "without notice" in text):
                risk_level = "High"
                risk_score = 8
                concerns.append("One-sided termination allows immediate dismissal without adequate cause or notice.")
                action = "Demand mutual notice requirement and a minimum 14-day cure period for non-gross misconduct."
            elif "sole discretion" in text:
                risk_level = "Medium"
                risk_score = 6
                concerns.append("Employer retains wide discretion to declare material breach.")
                action = "Add objective definition of 'material breach' and written cure window."
            else:
                risk_level = "Low"
                risk_score = 3
                action = "Termination provisions are standard and reciprocal."

        elif c_type == "exit_penalty":
            checklist = {
                "Are liquidated damages demanded?": "liquidated damages" in text or "penalty" in text,
                "Can employer deduct penalty from final salary?": "deduct" in text or "withhold" in text,
                "Is penalty reasonable compared to actual proven loss?": False,
            }
            risk_level = "High"
            risk_score = 9
            concerns.append("Exit penalties and arbitrary liquidated damages are punitive and often legally unenforceable.")
            concerns.append("Risk of having final paycheck or earned bonuses withheld.")
            action = "Strike out liquidated damages clause; limit recovery strictly to unearned signing bonuses on a prorated basis."

        elif c_type == "non_compete":
            has_long_duration = any(k in text for k in ["1 year", "2 years", "12 months", "24 months", "indefinite"])
            has_broad_geo = any(k in text for k in ["worldwide", "global", "any competitor", "any business"])
            checklist = {
                "Is non-compete duration longer than 6 months?": has_long_duration,
                "Is geographic scope unreasonably broad?": has_broad_geo,
                "Does employer pay compensation during non-compete period?": "compensation" in text or "garden leave" in text,
            }
            if has_long_duration or has_broad_geo:
                risk_level = "High"
                risk_score = 8
                concerns.append("Overly broad non-compete may restrict you from working in your domain after leaving.")
                concerns.append("No compensation offered for post-employment restraint of trade.")
                action = "Limit non-compete strictly to direct competitors, reduce duration to 3 months, or require garden leave pay."
            else:
                risk_level = "Medium"
                risk_score = 5
                concerns.append("Non-solicitation and competitive restrictions apply post-contract.")
                action = "Clarify list of named direct competitors."

        elif c_type == "ip_ownership":
            claims_all = any(k in text for k in ["all inventions", "personal time", "outside working hours", "regardless of whether"])
            checklist = {
                "Does assignment apply to off-hours personal projects?": claims_all,
                "Are prior inventions excluded?": "prior inventions" in text or "schedule a" in text,
                "Are moral rights waived irrevocably?": "moral rights" in text and "waive" in text,
            }
            if claims_all or ("outside working hours" in text):
                risk_level = "High"
                risk_score = 8
                concerns.append("Overreaching IP assignment claims personal inventions developed on your own time without company assets.")
                action = "Insert 'carve-out' for personal projects created outside working hours using personal equipment."
            elif "moral rights" in text:
                risk_level = "Medium"
                risk_score = 5
                concerns.append("Full waiver of moral rights and ownership of all deliverables.")
                action = "Ensure prior personal open-source projects are explicitly carved out."
            else:
                risk_level = "Low"
                risk_score = 3
                action = "IP clause reasonably covers work created during the course of employment."

        elif c_type == "auto_renewal":
            short_notice = any(k in text for k in ["10 days", "7 days", "15 days", "automatic"])
            checklist = {
                "Does contract auto-renew without affirmative confirmation?": True,
                "Is rent or rate escalated upon renewal?": "escalation" in text or "%" in text or "increase" in text,
                "Is opt-out notice window at least 30 days?": "30 days" in text or "60 days" in text,
            }
            if "%" in text or "escalation" in text or short_notice:
                risk_level = "Medium"
                risk_score = 6
                concerns.append("Automatic extension with price/rent increase unless strict deadline is met.")
                action = "Require written reminder from counterparty 30 days prior to auto-renewal."
            else:
                risk_level = "Low"
                risk_score = 3
                action = "Auto-renewal includes standard opt-out terms."

        elif c_type == "payment_terms":
            has_long_net = any(k in text for k in ["net 60", "net 90", "net-60", "net-90"])
            has_deductions = any(k in text for k in ["deduct", "discretion", "disputed"])
            checklist = {
                "Is payment timeline Net-30 or better?": not has_long_net,
                "Is there a late payment penalty or interest on overdue amounts?": "interest" in text or "late fee" in text,
                "Are deductions strictly regulated?": not has_deductions,
            }
            if has_long_net or "no interest" in text:
                risk_level = "High"
                risk_score = 7
                concerns.append("Extended payment window (Net 60/90) strains contractor cash flow.")
                action = "Negotiate Net-15 or Net-30 payment terms and 1.5% monthly late fee."
            elif has_deductions:
                risk_level = "Medium"
                risk_score = 5
                concerns.append("Client/Landlord has broad leeway for deductions before payout.")
                action = "Clarify invoice dispute timeline and require detailed itemized receipts for any deduction."
            else:
                risk_level = "Low"
                risk_score = 2
                action = "Payment terms are clear and acceptable."

        elif c_type == "confidentiality":
            is_perpetual = any(k in text for k in ["perpetual", "indefinitely", "in perpetuity", "survive indefinitely"])
            checklist = {
                "Is confidentiality term limited in time (e.g. 2-3 years)?": not is_perpetual,
                "Are standard exclusions included (public knowledge, court orders)?": "public" in text or "required by law" in text,
                "Is definition of confidential information clearly bounded?": "marked" in text or "designated" in text,
            }
            if is_perpetual:
                risk_level = "Medium"
                risk_score = 5
                concerns.append("Perpetual confidentiality obligation with no sunset period.")
                action = "Limit confidentiality duration to 2 or 3 years post-termination, with exceptions for trade secrets."
            else:
                risk_level = "Low"
                risk_score = 2
                action = "Standard non-disclosure terms with customary carve-outs."

        elif c_type == "governing_law":
            checklist = {
                "Is jurisdiction located in local or accessible court?": True,
                "Is arbitration mutually agreed?": "arbitration" in text,
                "Are legal fees allocated fairly?": "prevailing party" in text,
            }
            risk_level = "Low"
            risk_score = 2
            action = "Standard dispute resolution and jurisdiction clause."

        items.append(
            RiskItem(
                clause_type=c_type,
                title=clause.title,
                risk_level=risk_level,
                risk_score=risk_score,
                concerns=concerns if concerns else ["No significant contractual risk identified."],
                checklist=checklist,
                recommended_action=action,
                original_text=clause.original_text,
                page_number=clause.page_number,
            )
        )

    # Calculate overall risk
    high_count = sum(1 for i in items if i.risk_level == "High")
    medium_count = sum(1 for i in items if i.risk_level == "Medium")
    low_count = sum(1 for i in items if i.risk_level == "Low")

    if high_count > 0:
        overall_risk: RiskLevel = "High"
        summary = (
            f"The agreement contains {high_count} HIGH-RISK clause(s) that require active negotiation "
            f"before signing. Key concerns involve restrictive covenants, financial penalties, or one-sided exit terms."
        )
    elif medium_count > 0:
        overall_risk = "Medium"
        summary = (
            f"The agreement contains {medium_count} MEDIUM-RISK terms. While not critical deal-breakers, "
            f"they represent asymmetric burdens that should be clarified or balanced."
        )
    else:
        overall_risk = "Low"
        summary = "The agreement appears balanced with standard commercial and legal protections. No predatory clauses were detected."

    return RiskAuditResult(
        risk_items=items,
        overall_risk_level=overall_risk,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        audit_summary=summary,
    )


# ---------------------------------------------------------------------------
# Negotiation Advisor Rules & Alternative Language
# ---------------------------------------------------------------------------

REWRITE_TEMPLATES = {
    "notice_period": {
        "explanation": "A long notice period (e.g., 60-90 days) locks you into the company and makes competing job offers difficult to accept because new employers usually expect a 30-day start.",
        "alternative": "Either party may terminate this employment agreement by giving thirty (30) days' prior written notice to the other party, or salary in lieu thereof with mutual written consent.",
        "tips": [
            "Propose matching standard industry notice norms of 30 days.",
            "Ask for an explicit buyout option where either party can pay 1 month salary in lieu of notice.",
            "Highlight that a shorter notice period benefits the company as well when rapid restructuring is needed."
        ]
    },
    "service_bond": {
        "explanation": "Mandatory service bonds and financial exit penalties penalize employees who leave early, regardless of whether the workplace environment was satisfactory.",
        "alternative": "In the event the Company provides formal external training with prior mutual written cost approval, Employee agrees that if they resign within twelve (12) months following completion of such training, they shall reimburse strictly the actual, verifiable training fees on a pro-rata basis.",
        "tips": [
            "Never hand over original academic degree certificates or passports under any circumstances.",
            "Insist that any repayment only applies to documented external training costs, never general onboarding or salary.",
            "Ensure reimbursement drops by 1/12th for every month served following the training."
        ]
    },
    "termination": {
        "explanation": "Immediate termination clauses without opportunity to cure give the counterparty unilateral power to dismiss you without notice or financial security.",
        "alternative": "Except in the case of willful misconduct, neither party may terminate this Agreement without providing fourteen (14) days' written notice specifying the alleged breach and granting a reasonable opportunity to cure.",
        "tips": [
            "Add a mandatory 14-day written 'cure period' before any termination for alleged performance breach takes effect.",
            "Ensure the termination notice requirement is strictly bilateral and mutual.",
            "Request pro-rata payment of all accrued benefits and earned compensation up to the final working day."
        ]
    },
    "exit_penalty": {
        "explanation": "Fixed liquidated damages or salary forfeiture clauses are punitive and can result in losing earned wages or being sued for leaving.",
        "alternative": "Upon termination of engagement, neither party shall be liable to the other for punitive damages or liquidated exit fees. Compensation shall be settled strictly based on actual services rendered through the effective date of termination.",
        "tips": [
            "Argue that liquidated damages are unreasonable where no specific unique company assets were destroyed.",
            "Offer that signing bonuses may be returned prorated, but earned compensation remains untouched.",
            "State that labor laws generally disfavor contractual exit penalties."
        ]
    },
    "non_compete": {
        "explanation": "Overly broad non-competes restrict your livelihood and can prevent you from working in your profession or industry after leaving.",
        "alternative": "During the term of this Agreement and for a period of three (3) months thereafter, Contractor shall not solicit or perform identical services for the specific direct competitor accounts explicitly listed in Exhibit A, within the metropolitan area of the engagement.",
        "tips": [
            "Insist on an explicit list of named direct competitors rather than a blanket industry ban.",
            "Reduce the duration from 1-2 years down to 3 to 6 months maximum.",
            "Under many jurisdictions (such as California or Indian Contract Act Sec 27), post-employment non-compete clauses are legally void; keep this in mind during negotiation."
        ]
    },
    "ip_ownership": {
        "explanation": "Broad IP assignment clauses capture intellectual property you build on your own personal time using your own equipment, stripping you of your independent creations.",
        "alternative": "The Company shall own all rights in Inventions created by Employee solely within the scope of regular employment duties and utilizing Company equipment or confidential data. Inventions created by Employee on personal time, without Company equipment, that do not directly compete with Company's core products, remain Employee's exclusive property.",
        "tips": [
            "Attach a 'Schedule of Prior Inventions' listing all personal GitHub repos and side projects before signing.",
            "Include explicit language carving out inventions developed on personal time with personal hardware.",
            "Ensure copyright and patent assignment applies only to deliverables paid for by the client."
        ]
    },
    "payment_terms": {
        "explanation": "Net-60 or Net-90 payment terms force you to act as an interest-free bank for the client, increasing risk of cash flow shortfalls.",
        "alternative": "Client shall pay all undisputed invoice amounts within thirty (30) days of receipt. Invoices overdue past 30 days shall accrue interest at the rate of 1.5% per month or the legal maximum, whichever is lower.",
        "tips": [
            "Request Net-15 or Net-30 as the standard commercial timeline.",
            "Add a clause allowing you to pause services if invoices remain unpaid past 45 days.",
            "For large projects, request a 25-30% upfront deposit before commencing deliverables."
        ]
    },
    "auto_renewal": {
        "explanation": "Auto-renewal with automatic rent or fee escalations can catch you off-guard and renew a contract you intended to vacate or end.",
        "alternative": "This Agreement may be renewed upon mutual written agreement of both parties at least thirty (30) days prior to the expiration of the current Term. Any proposed fee or rent adjustments must be agreed upon in writing at least sixty (60) days in advance.",
        "tips": [
            "Change auto-renewal from opt-out to opt-in (requiring affirmative written agreement).",
            "Cap any annual rent/fee increase at a maximum percentage (e.g. 5% or local CPI).",
            "Set a calendar reminder 45 days before the expiration date to review renewal status."
        ]
    },
    "confidentiality": {
        "explanation": "Perpetual confidentiality agreements create lifelong legal liabilities, especially when confidential information is not clearly defined.",
        "alternative": "The obligations of confidentiality under this Agreement shall survive for a period of two (2) years following the termination of this Agreement, after which the Receiving Party shall have no further obligation with respect thereto.",
        "tips": [
            "Insert a 2 or 3-year sunset period for general business and technical information.",
            "Ensure trade secrets are carved out separately with clear reasonable criteria.",
            "Ensure clear exceptions for information already in the public domain or required by law."
        ]
    },
}


def advise_negotiation_offline(
    risk_result: RiskAuditResult,
) -> NegotiationResult:
    """Generate plain-English negotiation points and suggested redlines."""
    points: List[NegotiationPoint] = []

    for item in risk_result.risk_items:
        if item.risk_level in ("High", "Medium"):
            c_type = item.clause_type
            data = REWRITE_TEMPLATES.get(
                c_type,
                {
                    "explanation": f"This clause sets terms that favor the counterparty. Modifying the wording will establish a fairer balance of obligations.",
                    "alternative": f"The parties agree that all duties under this {item.title} provision shall be exercised reasonably, upon 30 days' written notice, and with mutual consent.",
                    "tips": [
                        "Request clarification and mutual reciprocity for this term.",
                        "Propose standard commercial practices as reasonable benchmarks."
                    ]
                }
            )

            points.append(
                NegotiationPoint(
                    clause_type=c_type,
                    title=item.title,
                    explanation=data["explanation"],
                    alternative_wording=data["alternative"],
                    negotiation_tips=data["tips"],
                    priority=item.risk_level,
                )
            )

    high_count = sum(1 for p in points if p.priority == "High")
    if high_count > 0:
        exec_summary = (
            f"We have identified {len(points)} clauses requiring negotiation, with {high_count} tagged as HIGH PRIORITY. "
            f"Focus your initial discussions on notice periods, service bonds, and IP ownership before discussing commercial terms."
        )
    elif points:
        exec_summary = (
            f"We found {len(points)} clauses where amendments are recommended to better balance rights. "
            f"These represent standard commercial adjustments that can be resolved via email or an addendum."
        )
    else:
        exec_summary = (
            "No high or medium risk clauses were detected. The contract terms appear standard and balanced. "
            "Always review with legal counsel before final signature."
        )

    return NegotiationResult(
        points=points,
        executive_summary=exec_summary,
    )


# ---------------------------------------------------------------------------
# Grounding Critic Rules & Evidence Verification
# ---------------------------------------------------------------------------

def verify_grounding_offline(
    extraction_result: ClauseExtractionResult,
    full_text: str,
    chunks: Optional[List[dict]] = None,
) -> GroundingResult:
    """Verify that every extracted clause exists in the source text."""
    checks: List[GroundingCheck] = []
    full_text_lower = full_text.lower()

    for clause in extraction_result.clauses:
        quote = clause.original_text.strip()
        quote_clean = re.sub(r"\s+", " ", quote).lower()
        words = [w for w in re.findall(r"\w+", quote_clean) if len(w) > 2]

        is_grounded = False
        confidence = 0.0
        evidence_snippet = ""
        found_page = clause.page_number

        # 1. Exact verbatim check
        if quote_clean in full_text_lower:
            is_grounded = True
            confidence = 1.0
            idx = full_text_lower.find(quote_clean)
            evidence_snippet = full_text[idx : idx + min(len(quote), 250)]
        else:
            # 2. Token overlap search in chunks
            best_chunk_score = 0.0
            best_chunk_text = ""
            best_chunk_page = clause.page_number

            search_targets = chunks if chunks else [{"text": full_text, "page": 1}]
            for c in search_targets:
                target_text = c.get("text", "")
                target_lower = target_text.lower()
                matched_words = sum(1 for w in words if w in target_lower)
                score = matched_words / max(1, len(words))
                if score > best_chunk_score:
                    best_chunk_score = score
                    best_chunk_text = target_text
                    best_chunk_page = c.get("page", 1)

            if best_chunk_score >= 0.70:
                is_grounded = True
                confidence = round(best_chunk_score, 2)
                found_page = best_chunk_page
                evidence_snippet = best_chunk_text[:250].strip()
            elif best_chunk_score >= 0.40:
                is_grounded = True
                confidence = round(best_chunk_score, 2)
                found_page = best_chunk_page
                evidence_snippet = best_chunk_text[:200].strip()
            else:
                is_grounded = False
                confidence = round(best_chunk_score, 2)
                evidence_snippet = ""

        note = "Exact verbatim match confirmed." if confidence == 1.0 else (
            f"Fuzzy token overlap verified ({int(confidence * 100)}% match)." if is_grounded
            else "Quotation could not be verified in document context."
        )

        checks.append(
            GroundingCheck(
                clause_type=clause.clause_type,
                original_text=quote,
                is_grounded=is_grounded,
                confidence=confidence,
                evidence_snippet=evidence_snippet,
                page_number=found_page,
                notes=note,
            )
        )

    grounded_count = sum(1 for c in checks if c.is_grounded)
    ungrounded_count = len(checks) - grounded_count
    overall_grounded = ungrounded_count == 0 if checks else False

    summary = (
        f"Verified {grounded_count} of {len(checks)} clauses against the original document "
        f"({int((grounded_count / max(1, len(checks))) * 100)}% grounding rate)."
    )

    return GroundingResult(
        checks=checks,
        overall_grounded=overall_grounded,
        grounded_count=grounded_count,
        ungrounded_count=ungrounded_count,
        grounding_summary=summary,
    )


# ---------------------------------------------------------------------------
# Offline RAG Q&A Engine
# ---------------------------------------------------------------------------

def answer_rag_offline(
    question: str,
    chunks: List[dict],
) -> dict:
    """Answer natural language questions directly from chunks without LLM API."""
    q_lower = question.lower().strip()
    q_words = set(re.findall(r"\w+", q_lower)) - {"what", "is", "the", "are", "of", "and", "in", "a", "an", "does", "can", "how", "for", "to"}

    if not q_words:
        return {
            "answer": "Please ask a specific question regarding clauses, notice period, bond, termination, payment terms, or liability.",
            "sources": [],
            "confidence": "Low",
        }

    scored_chunks: List[Tuple[float, dict]] = []

    for chunk in chunks:
        text = chunk.get("text", "")
        text_lower = text.lower()
        score = 0
        for w in q_words:
            if w in text_lower:
                score += text_lower.count(w)
        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda sc: sc[0], reverse=True)

    if not scored_chunks:
        return {
            "answer": "This information was not found in the uploaded document. Please check the contract text or rephrase your question.",
            "sources": [],
            "confidence": "Low",
        }

    best_score, best_chunk = scored_chunks[0]
    best_text = best_chunk.get("text", "")
    page_num = best_chunk.get("page", 1)

    # Find the most relevant sentence
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", best_text) if s.strip()]
    relevant = []
    for s in sentences:
        s_lower = s.lower()
        if any(w in s_lower for w in q_words):
            relevant.append(s)

    if not relevant:
        relevant = sentences[:3]

    answer_text = " ".join(relevant[:3])
    sources = [
        {
            "page": page_num,
            "text": best_text[:300] + ("..." if len(best_text) > 300 else ""),
            "score": round(min(1.0, best_score / max(1, len(q_words))), 2),
        }
    ]

    confidence = "High" if best_score >= 3 else ("Medium" if best_score >= 1 else "Low")

    formatted_answer = f"{answer_text} (Source: Page {page_num})"

    return {
        "answer": formatted_answer,
        "sources": sources,
        "confidence": confidence,
    }
