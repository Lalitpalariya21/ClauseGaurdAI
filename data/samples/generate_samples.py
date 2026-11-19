"""
data/samples/generate_samples.py
================================
Generates 3 realistic fictional sample contract PDFs for demonstration:
1. it_offer_letter.pdf
2. rental_agreement.pdf
3. freelance_contract.pdf
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF

SAMPLES_DIR = Path(__file__).resolve().parent
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


def create_pdf(filename: str, pages_text: list[str]) -> None:
    doc = fitz.open()
    for page_num, text in enumerate(pages_text, 1):
        page = doc.new_page(width=612, height=792)  # Standard Letter size
        # Header
        page.insert_text(
            (50, 45),
            f"CONFIDENTIAL & BINDING LEGAL AGREEMENT  |  PAGE {page_num}",
            fontsize=8,
            color=(0.5, 0.5, 0.5),
        )
        # Body text (wrapped into rectangle)
        rect = fitz.Rect(50, 70, 562, 730)
        page.insert_textbox(rect, text, fontsize=10.5, lineheight=1.35)
        # Footer
        page.insert_text(
            (50, 755),
            "Generated for ClauseGuard AI Evaluation & Testing. Fictional Parties.",
            fontsize=8,
            color=(0.6, 0.6, 0.6),
        )

    out_path = SAMPLES_DIR / filename
    doc.save(str(out_path))
    doc.close()
    print(f"Generated: {out_path} ({len(pages_text)} pages)")


# ── Sample 1: IT Offer Letter ──────────────────────────────────────────────────
IT_OFFER_LETTER_P1 = """NEXUS SOFTWARE TECHNOLOGIES PRIVATE LIMITED
OFFER OF EMPLOYMENT & SERVICE AGREEMENT

Date: October 15, 2026
Candidate Name: Alex Mercer
Designation: Senior Full Stack Software Engineer
Department: Engineering & Product Development
Compensation: $115,000 per annum (All-Inclusive Annual CTC)

Dear Alex,

We are pleased to offer you the position of Senior Full Stack Software Engineer at Nexus Software Technologies. This letter, together with the following Terms and Conditions, constitutes your employment contract upon acceptance.

1. PROBATION & NOTICE PERIOD
You shall be on probation for an initial period of six (6) months from your date of joining. During probation, either party may terminate the employment with fourteen (14) days' written notice. Upon successful completion and written confirmation of probation, the employee is required to serve a mandatory ninety (90) days' notice period prior to resignation. The Company reserves the exclusive right to waive the notice period without payment in lieu, or to demand full salary buyout at its sole discretion.

2. SERVICE BOND & TRAINING RECOVERY
The Company invests substantial resources in proprietary software training. As a condition of employment, you agree to execute a mandatory minimum service bond of twenty-four (24) months from your joining date. If you resign or your employment is terminated for cause prior to completing twenty-four months, you shall pay the Company a fixed liquidated sum of $5,000 (Five Thousand US Dollars) as training cost recovery. Furthermore, original educational degree certificates must be deposited with HR during the tenure of the service bond."""

IT_OFFER_LETTER_P2 = """NEXUS SOFTWARE TECHNOLOGIES PRIVATE LIMITED — TERMS & CONDITIONS (CONTINUED)

3. TERMINATION OF EMPLOYMENT
The Company reserves the right to terminate your employment immediately without cause or prior notice during any financial quarter based on operational redundancy or performance restructuring. In the event of alleged misconduct or policy breach, termination shall be immediate with forfeiture of unpaid bonuses.

4. INTELLECTUAL PROPERTY & INVENTIONS
You acknowledge and agree that all inventions, designs, source code, algorithms, software architectures, and creative works conceived, authored, or reduced to practice by you—whether during regular office hours or outside working hours, whether using Company computers or personal equipment—shall be the sole and exclusive property of Nexus Software Technologies. You hereby irrevocably assign all worldwide copyright, patent rights, and moral rights to the Company in perpetuity.

5. NON-COMPETE & RESTRICTIVE COVENANTS
For a duration of twelve (12) months following the termination or resignation of your employment, you agree not to directly or indirectly work for, consult, or assist any competing business, enterprise, or startup operating in cloud computing or developer tooling globally. You further agree not to solicit or hire any employee or contractor of the Company for twenty-four (24) months post-departure.

6. GOVERNING LAW & JURISDICTION
This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, USA, and the courts of Wilmington, Delaware shall have exclusive jurisdiction over all disputes arising hereunder.

Accepted and Agreed:

_______________________                          _______________________
Alex Mercer (Employee)                           Nexus HR Operations"""


# ── Sample 2: Rental Agreement ─────────────────────────────────────────────────
RENTAL_AGREEMENT_P1 = """RESIDENTIAL LEASE & TENANCY AGREEMENT

This Agreement is made on this 1st day of November 2026, by and between:
LANDLORD: Sterling Properties Management LLC ("Lessor")
TENANT: Jordan Taylor ("Lessee")
PREMISES: Apartment 4B, 142 Elmwood Boulevard, Metro City

1. TERM & AUTO-RENEWAL
The initial lease term shall be for eleven (11) months, commencing on November 1, 2026. This Agreement shall automatically renew for successive eleven-month terms unless the Lessee delivers written notice of intention to vacate at least sixty (60) days prior to the expiration date. Upon each auto-renewal, the monthly rent shall automatically escalate by fifteen percent (15%) over the prevailing rate.

2. RENT & PAYMENT TERMS
The monthly rent shall be $2,400 per month, payable in advance on or before the first (1st) business day of each calendar month. A late payment fee of $150 shall be assessed if rent is received after the 3rd of the month, and additional interest of 1.5% per week shall accrue until full settlement.

3. SECURITY DEPOSIT & FORFEITURE
The Tenant has deposited a refundable Security Deposit of $4,800. The Landlord reserves the right to deduct from the security deposit any costs associated with painting, routine cleaning, general wear and tear, and administrative processing fees upon vacating."""

RENTAL_AGREEMENT_P2 = """RESIDENTIAL LEASE AGREEMENT — TERMS & OBLIGATIONS (CONTINUED)

4. EARLY TERMINATION & EXIT PENALTY
If the Lessee vacates the premises prior to the completion of the agreed term, the entire security deposit of $4,800 shall be forfeited as liquidated damages. In addition, the Lessee shall remain liable to pay the full monthly rent until a suitable new replacement tenant approved by the Landlord is onboarded.

5. INSPECTION & ACCESS
The Landlord or authorized agents may enter the premises at any time without prior written notice to inspect condition, show premises to prospective buyers, or verify adherence to lease covenants.

6. REPAIRS & MAINTENANCE
The Tenant shall be solely responsible for all maintenance and repair charges within the premises up to $300 per incident, including plumbing, HVAC filters, electrical switches, and appliance servicing.

7. GOVERNING JURISDICTION
This lease is governed by the Residential Tenancies Act and the local district civil court of Metro City.

IN WITNESS WHEREOF, the parties hereto have signed this Lease:

___________________________                      ___________________________
Sterling Properties LLC (Lessor)                 Jordan Taylor (Lessee)"""


# ── Sample 3: Freelance Contract ───────────────────────────────────────────────
FREELANCE_CONTRACT_P1 = """INDEPENDENT CONTRACTOR & FREELANCE SERVICES AGREEMENT

Effective Date: October 1, 2026
Client: Apex Digital Media Inc. ("Client")
Contractor: Morgan Vance, Freelance UI/UX & Backend Developer ("Contractor")
Scope of Work: Mobile Application UI/UX Redesign and REST API Microservice Development

1. SCOPE & UNLIMITED REVISIONS
The Contractor agrees to deliver high-fidelity UI mockups, frontend components, and backend endpoints as described in Statement of Work (SOW-1). The Contractor shall provide unlimited revisions until the Client's executive team provides unconditional written sign-off, without any additional compensation.

2. PAYMENT TERMS & INVOICING
Compensation for completed milestones is set at $8,000 payable upon full project completion. Invoices submitted by the Contractor shall be settled on Net-60 payment terms (60 calendar days from receipt of invoice approval). The Client shall not be liable for any late payment penalties or interest on delayed disbursements. In the event of client budget freeze, payments may be deferred up to an additional 45 days.

3. WORK PRODUCT & MORAL RIGHTS
All deliverables, prototypes, codebases, and media created under this agreement shall be considered works made for hire and become the sole property of Apex Digital Media Inc. Contractor waives all moral rights and agrees not to showcase any part of the project in public portfolios or case studies without written client consent."""

FREELANCE_CONTRACT_P2 = """INDEPENDENT CONTRACTOR AGREEMENT — GENERAL COVENANTS (CONTINUED)

4. TERMINATION & CANCELLATION
The Client may terminate this agreement at any time, with or without cause, upon written email notice. In such event, the Contractor shall receive payment strictly for approved milestones completed prior to the notice. If the Client terminates due to dissatisfaction with deliverables, all milestone payments made to date shall be refunded by the Contractor within 14 days.

5. INDEMNIFICATION & LIABILITY
The Contractor agrees to indemnify, defend, and hold harmless Apex Digital Media Inc., its officers, and affiliates from all claims, damages, liabilities, and legal fees arising from the deliverables, including any third-party intellectual property infringement or server downtime, with liability capped at no less than $50,000.

6. CONFIDENTIALITY
Contractor agrees to hold all client technical data, business plans, and user metrics in strict confidence indefinitely in perpetuity.

7. GOVERNING LAW
This contract is governed by the laws of the State of New York, USA.

Signatures:

___________________________                      ___________________________
Apex Digital Media Inc.                          Morgan Vance (Contractor)"""


def main():
    print("Generating sample contract PDFs...")
    create_pdf("it_offer_letter.pdf", [IT_OFFER_LETTER_P1, IT_OFFER_LETTER_P2])
    create_pdf("rental_agreement.pdf", [RENTAL_AGREEMENT_P1, RENTAL_AGREEMENT_P2])
    create_pdf("freelance_contract.pdf", [FREELANCE_CONTRACT_P1, FREELANCE_CONTRACT_P2])
    print("All sample PDFs generated successfully in data/samples/!")


if __name__ == "__main__":
    main()
