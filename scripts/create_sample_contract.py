"""
Generates a realistic sample contract PDF for testing.
Run this once to create a test file.

Usage: python scripts/create_sample_contract.py
"""

from fpdf import FPDF
from pathlib import Path


def create_sample_contract():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Title ──
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 15, "MASTER SERVICES AGREEMENT", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Contract No: MSA-2025-00142", ln=True, align="C")
    pdf.cell(0, 8, "Effective Date: January 15, 2025", ln=True, align="C")
    pdf.ln(10)

    # ── Parties ──
    pdf.set_font("Helvetica", "", 10)
    parties = (
        'This Master Services Agreement ("Agreement") is entered into as of '
        "January 15, 2025 (the \"Effective Date\") by and between Nexus "
        "Dynamics Inc., a Delaware corporation with offices at 400 Innovation "
        "Drive, Suite 300, Wilmington, DE 19801 (\"Company\"), and Brightpath "
        "Solutions LLC, a California limited liability company with offices at "
        "1200 Market Street, San Francisco, CA 94103 (\"Service Provider\")."
    )
    pdf.multi_cell(0, 6, parties)
    pdf.ln(8)

    # ── Sections (each one has specific risk characteristics) ──
    sections = [
        ("1. DEFINITIONS", """
For purposes of this Agreement, the following terms shall have the meanings set forth below:

"Confidential Information" means any and all non-public information, including but not limited to trade secrets, business plans, customer lists, financial data, technical specifications, and any other proprietary information disclosed by either party.

"Deliverables" means all work product, reports, software, documentation, and materials created by Service Provider in the performance of Services under this Agreement.

"Services" means the consulting, development, and advisory services described in each Statement of Work executed under this Agreement.

"Statement of Work" or "SOW" means a document executed by both parties that describes the specific Services to be performed, timelines, and fees.
"""),
        ("2. TERM AND RENEWAL", """
2.1 Initial Term. This Agreement shall commence on the Effective Date and shall continue for an initial term of twenty-four (24) months (the "Initial Term").

2.2 Automatic Renewal. Upon expiration of the Initial Term, this Agreement shall AUTOMATICALLY RENEW for successive twelve (12) month periods (each a "Renewal Term") unless either party provides written notice of non-renewal at least ninety (90) days prior to the end of the then-current term. During any Renewal Term, Company reserves the right to adjust pricing and terms upon thirty (30) days written notice.

2.3 Effect of Renewal. All terms and conditions of this Agreement, including all active Statements of Work, shall remain in full force and effect during any Renewal Term unless otherwise modified in writing by the parties.
"""),
        ("3. SERVICES AND DELIVERABLES", """
3.1 Scope of Services. Service Provider shall perform the Services as described in each Statement of Work. Each SOW shall be signed by authorized representatives of both parties and shall be incorporated into this Agreement by reference.

3.2 Standard of Performance. Service Provider shall perform all Services in a professional and workmanlike manner, consistent with generally accepted industry standards and practices.

3.3 Personnel. Service Provider shall assign qualified personnel to perform the Services. Company shall have the right to request replacement of any Service Provider personnel, and Service Provider shall comply with such request within fifteen (15) business days.
"""),
        ("4. COMPENSATION AND PAYMENT", """
4.1 Fees. Company shall pay Service Provider the fees set forth in each Statement of Work. Unless otherwise specified in a SOW, Service Provider shall invoice Company monthly in arrears.

4.2 Payment Terms. All invoices are due and payable within Net 60 days of receipt. Late payments shall accrue interest at the rate of 1.5% per month or the maximum rate permitted by law, whichever is less.

4.3 Expenses. Company shall reimburse Service Provider for reasonable, pre-approved travel and out-of-pocket expenses incurred in connection with the Services, provided that Service Provider submits itemized receipts within thirty (30) days.

4.4 Taxes. Service Provider shall be solely responsible for all taxes, contributions, and assessments arising from compensation received under this Agreement.
"""),
        ("5. INTELLECTUAL PROPERTY", """
5.1 Work Product Assignment. All Deliverables, work product, inventions, discoveries, improvements, and materials of any kind created, developed, or conceived by Service Provider, solely or jointly with others, in the course of performing Services under this Agreement shall be considered "work made for hire" as defined under the U.S. Copyright Act. To the extent any Deliverable does not qualify as work made for hire, Service Provider hereby irrevocably assigns to Company all right, title, and interest worldwide in and to such Deliverable, including all intellectual property rights therein.

5.2 Pre-Existing IP. Notwithstanding Section 5.1, Service Provider retains ownership of its pre-existing intellectual property that existed prior to the Effective Date. However, Service Provider grants Company a perpetual, irrevocable, worldwide, royalty-free license to use any pre-existing IP incorporated into the Deliverables.

5.3 Moral Rights. To the fullest extent permitted by applicable law, Service Provider waives all moral rights in the Deliverables, including rights of attribution and integrity.

5.4 Further Assurances. Service Provider agrees to execute any documents and take any actions reasonably requested by Company to perfect, protect, or enforce Company's intellectual property rights in the Deliverables.
"""),
        ("6. CONFIDENTIALITY", """
6.1 Obligations. Each party agrees to hold the other party's Confidential Information in strict confidence and not to disclose such information to any third party without the prior written consent of the disclosing party.

6.2 Duration. The obligations of confidentiality shall survive termination of this Agreement and continue in perpetuity with respect to trade secrets and for a period of seven (7) years for all other Confidential Information.

6.3 Exceptions. Confidential Information shall not include information that: (a) is or becomes publicly available through no fault of the receiving party; (b) was known to the receiving party prior to disclosure; (c) is independently developed by the receiving party; or (d) is required to be disclosed by law or court order.
"""),
        ("7. LIABILITY", """
7.1 Unlimited Liability. SERVICE PROVIDER SHALL BE LIABLE FOR ALL DAMAGES OF ANY KIND ARISING FROM OR RELATED TO THIS AGREEMENT, INCLUDING BUT NOT LIMITED TO DIRECT, INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL, PUNITIVE, AND EXEMPLARY DAMAGES, REGARDLESS OF WHETHER SUCH DAMAGES WERE FORESEEABLE OR WHETHER SERVICE PROVIDER WAS ADVISED OF THE POSSIBILITY OF SUCH DAMAGES. THERE SHALL BE NO CAP OR LIMITATION ON SERVICE PROVIDER'S LIABILITY UNDER THIS AGREEMENT.

7.2 Company Limitation. COMPANY'S TOTAL AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED THE FEES PAID BY COMPANY TO SERVICE PROVIDER IN THE THREE (3) MONTHS IMMEDIATELY PRECEDING THE CLAIM.

7.3 Exclusion. IN NO EVENT SHALL COMPANY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL, OR EXEMPLARY DAMAGES ARISING FROM THIS AGREEMENT.
"""),
        ("8. INDEMNIFICATION", """
8.1 Service Provider Indemnification. Service Provider shall defend, indemnify, and hold harmless Company, its officers, directors, employees, agents, and affiliates from and against any and all claims, damages, losses, liabilities, costs, and expenses (including reasonable attorneys' fees) arising from or related to: (a) Service Provider's breach of this Agreement; (b) Service Provider's negligence or willful misconduct; (c) any claim that the Deliverables infringe any third-party intellectual property rights; or (d) any act or omission of Service Provider's personnel.

8.2 No Reciprocal Indemnification. For the avoidance of doubt, Company shall have no obligation to indemnify Service Provider under any circumstances arising from this Agreement.
"""),
        ("9. NON-COMPETITION AND NON-SOLICITATION", """
9.1 Non-Compete. During the term of this Agreement and for a period of thirty-six (36) months following its termination or expiration, Service Provider shall not, directly or indirectly, engage in, own, manage, operate, control, be employed by, consult for, or participate in the ownership, management, operation, or control of any business that competes with Company's business anywhere within North America.

9.2 Non-Solicitation. During the term and for twenty-four (24) months after termination, Service Provider shall not directly or indirectly solicit, recruit, or hire any employee, contractor, or consultant of Company, or encourage any such person to leave Company's service.

9.3 Reasonableness. Service Provider acknowledges that the restrictions in this Section 9 are reasonable and necessary to protect Company's legitimate business interests and that any breach will cause irreparable harm to Company.
"""),
        ("10. TERMINATION", """
10.1 Termination for Cause. Either party may terminate this Agreement upon thirty (30) days written notice if the other party materially breaches this Agreement and fails to cure such breach within the notice period.

10.2 Termination for Convenience by Company. Company may terminate this Agreement or any SOW at any time for any reason upon fifteen (15) days written notice to Service Provider.

10.3 No Termination for Convenience by Service Provider. Service Provider may not terminate this Agreement for convenience and shall be obligated to complete all Services under active Statements of Work regardless of circumstances.

10.4 Effect of Termination. Upon termination, Service Provider shall immediately deliver all completed and in-progress Deliverables to Company, return all Confidential Information, and provide reasonable transition assistance for a period of up to sixty (60) days at Service Provider's expense.
"""),
        ("11. GOVERNING LAW AND DISPUTE RESOLUTION", """
11.1 Governing Law. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of laws principles.

11.2 Mandatory Arbitration. Any dispute, controversy, or claim arising out of or relating to this Agreement shall be resolved exclusively through binding arbitration administered by the American Arbitration Association in Wilmington, Delaware. The arbitration shall be conducted by a single arbitrator selected by Company. The arbitrator's decision shall be final and binding, and judgment may be entered in any court of competent jurisdiction.

11.3 Waiver of Jury Trial. EACH PARTY HEREBY IRREVOCABLY WAIVES ALL RIGHT TO A TRIAL BY JURY IN ANY ACTION, PROCEEDING, OR COUNTERCLAIM ARISING OUT OF OR RELATING TO THIS AGREEMENT.

11.4 Attorneys' Fees. In any dispute arising under this Agreement, the prevailing party shall be entitled to recover its reasonable attorneys' fees and costs from the non-prevailing party.
"""),
        ("12. GENERAL PROVISIONS", """
12.1 Entire Agreement. This Agreement, together with all SOWs and exhibits, constitutes the entire agreement between the parties with respect to its subject matter and supersedes all prior and contemporaneous agreements, proposals, and representations.

12.2 Amendment. This Agreement may only be amended or modified by a written instrument signed by authorized representatives of both parties.

12.3 Waiver. The failure of either party to enforce any provision of this Agreement shall not constitute a waiver of such provision or the right to enforce it at a later time.

12.4 Severability. If any provision of this Agreement is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.

12.5 Assignment. Service Provider may not assign or transfer this Agreement or any rights hereunder without Company's prior written consent. Company may freely assign this Agreement to any affiliate or successor entity.

12.6 Notices. All notices under this Agreement shall be in writing and delivered by certified mail, overnight courier, or email to the addresses set forth above.

12.7 Survival. Sections 5, 6, 7, 8, 9, and 11 shall survive termination or expiration of this Agreement.
"""),
    ]

    for title, body in sections:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", "", 10)
        # Clean up the text
        body = body.strip()
        pdf.multi_cell(0, 5, body)

    # ── Signature Block ──
    pdf.ln(15)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "IN WITNESS WHEREOF, the parties have executed this Agreement.", ln=True)
    pdf.ln(10)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, "NEXUS DYNAMICS INC.", ln=0)
    pdf.cell(95, 6, "BRIGHTPATH SOLUTIONS LLC", ln=True)
    pdf.ln(8)
    pdf.cell(95, 6, "By: ___________________________", ln=0)
    pdf.cell(95, 6, "By: ___________________________", ln=True)
    pdf.cell(95, 6, "Name: Jonathan R. Hartwell", ln=0)
    pdf.cell(95, 6, "Name: Sarah K. Mitchell", ln=True)
    pdf.cell(95, 6, "Title: Chief Executive Officer", ln=0)
    pdf.cell(95, 6, "Title: Managing Partner", ln=True)
    pdf.cell(95, 6, "Date: January 15, 2025", ln=0)
    pdf.cell(95, 6, "Date: January 15, 2025", ln=True)

    # Save
    output_dir = Path("data/sample_contracts")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sample_msa_risky.pdf"
    pdf.output(str(output_path))
    print(f"✓ Sample contract created: {output_path}")
    print(f"  Pages: {pdf.page_no()}")
    print(f"  Contains: auto-renewal, uncapped liability, IP assignment,")
    print(f"  non-compete, one-sided indemnification, mandatory arbitration")


if __name__ == "__main__":
    create_sample_contract()