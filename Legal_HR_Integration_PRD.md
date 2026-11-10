# PRD: Legal-HR Communication Hub & Smart Contract Engine

**Status**: Draft
**Date**: April 2026
**Owner**: Product & Engineering Team

---

## 1. Executive Summary
Eximp & Cloves currently manages personnel data in the HR Portal and legal documentation in the Legal Suite. However, there is no digital bridge between these systems. This project introduces a **Communication Hub** to synchronize HR personnel cases with legal review workflows and upgrades the **Legal Editor** to a state-of-the-art "Smart Template" engine capable of generating high-fidelity, corporate-branded staff contracts.

## 2. Problem Statement
- **Communication Silos**: HR requests for contracts or legal reviews are handled outside the system (email/chat), leading to loss of audit trails.
- **Contract Fragmentation**: Employment contracts and offer letters are generated manually in Word or PDF, making them difficult to track against a staff member's live profile.
- **Branding Inconsistency**: Discrepancies in corporate contact information across old and new document templates.
- **Editor Limitations**: The current legal editor lacks a native "Headed Paper" experience for professional personnel documentation.

## 3. Goals & Success Criteria
| Objective | Success Criterion |
|-----------|-------------------|
| **Centralize Personnel Legal Cases** | 100% of staff legal requests (contracts, reviews) initiated from the HR Portal. |
| **Modernize Contract Generation** | Generation of contracts matching the "Front Desk Offer Letter" design within the system. |
| **Ensure Brand Integrity** | Standardized use of `eximps-cloves.com` and `admin@eximps-cloves.com` across all generated PDFs. |
| **Automate Document Archiving** | 100% of signed personnel contracts automatically linked to the HR Staff Profile. |

## 4. Key Functional Requirements

### 4.1 Internal Case Management (The Bridge)
- **Initiation**: HR Admins can open a "Legal Case" directly from any Staff Profile.
- **Categorization**: Cases categorized as "Contract Request", "Disciplinary Review", or "Legal Clearance".
- **Internal Messaging**: A private, role-restricted "Memo Thread" for HR and Legal to discuss personnel matters securely.
- **Status Tracking**: Visual status indicators in both portals (`Open`, `In-Progress`, `Legal Signing`, `Executed`).

### 4.2 Upgraded "Smart Template" Editor
- **Corporate Framing**: Native rendering of high-fidelity header (Logo + Contact Block) and branded orange footer.
- **Variable Auto-Populate**: Intelligent injection of staff data (Name, Role, Dept, Salary, Commencement Date) into placeholders.
- **Template Library**: Pre-built skeletons for specific personnel documents:
    - *Offer Letter* (Style-matched to provided PDF)
    - *Employment Contract*
    - *Non-Disclosure Agreement (NDA)*
- **Live Preview**: Real-time rendering of content on a digital A4 canvas.

### 4.3 Branding Synchronization
- **Contact Refresh**: Global update of Footer/Header contact details:
    - **Web**: https://eximps-cloves.com
    - **Email**: admin@eximps-cloves.com

## 5. UI/UX Principles
- **Corporate Aesthetics**: Use the established Deep Charcoal, Brand Gold, and White palette found in the Legal Suite.
- **Frictionless Workflow**: One-click transition from HR request to Legal editor.
- **Professionalism**: Generated PDFs must look like high-end professional legal documents, not web print-outs.

## 6. Technical Scope
- **Backend API**: New `hr_legal` router and database tables for cases and history.
- **Rendering Engine**: Update the `pdf_service` to support staff-specific schemas and branded frames.
- **Integration**: React frontend components in the HR Portal linked to the Jinja2/HTML Legal Dashboard.

---
**End of PRD**
