-- Seed: Legal Templates
-- Description: Pre-populate the legal template library with standard personnel templates
-- Run this after the 020_legal_templates_system.sql migration

-- Insert Offer Letter Template
INSERT INTO legal_templates (name, category, description, default_content_html, is_active) 
VALUES (
    'Offer Letter',
    'Offer Letter',
    'Pre-formatted employment offer letter matching company branding',
    '<div class="letterhead" style="padding: 40px 60px; border-bottom: 2px solid #C47D0A; margin-bottom: 20px;">
        <strong style="font-size: 16px;">EXIMP & CLOVES</strong><br>
        <span style="font-size: 11px; color: #666;">Web: https://eximps-cloves.com | Email: admin@eximps-cloves.com</span>
    </div>
    <p style="margin-top: 40px; margin-bottom: 20px; font-weight: bold; font-size: 14px;">Offer of Employment</p>
    <p>Dear {{STAFF_NAME}},</p>
    <p>We are pleased to extend to you an offer of employment for the position of <strong>{{ROLE}}</strong> in our {{DEPARTMENT}} department, effective {{COMMENCEMENT_DATE}}.</p>
    <p><strong>Position Details:</strong></p>
    <ul style="margin-left: 20px; line-height: 1.8;">
        <li>Position Title: {{ROLE}}</li>
        <li>Department: {{DEPARTMENT}}</li>
        <li>Reports to: [Manager Name]</li>
        <li>Commencement Date: {{COMMENCEMENT_DATE}}</li>
        <li>Employment Type: Full-time</li>
    </ul>
    <p><strong style="margin-top: 15px;">Compensation & Benefits:</strong></p>
    <ul style="margin-left: 20px; line-height: 1.8;">
        <li>Base Salary: {{SALARY}} per annum</li>
        <li>Benefits: [Health Insurance, Pension, Leave Allowances]</li>
    </ul>
    <p style="margin-top: 20px;">This offer is contingent upon successful background verification and your acceptance of our standard employment terms and conditions.</p>
    <p style="margin-top: 20px;">By signing below, you acknowledge acceptance of this offer and agree to the terms and conditions outlined herein.</p>
    <p style="margin-top: 60px;"><strong>Sincerely,</strong></p>
    <p style="margin-top: 80px; line-height: 2.5;">_____________________<br><span style="font-size: 9pt;">Authorized Signatory<br>Eximp & Cloves<br>admin@eximps-cloves.com</span></p>',
    TRUE
);

-- Insert Employment Contract Template
INSERT INTO legal_templates (name, category, description, default_content_html, is_active)
VALUES (
    'Employment Contract',
    'Employment Contract',
    'Comprehensive full-time employment agreement with standard clauses',
    '<div class="letterhead" style="padding: 40px 60px; border-bottom: 2px solid #C47D0A; margin-bottom: 20px;">
        <strong style="font-size: 16px;">EXIMP & CLOVES</strong><br>
        <span style="font-size: 11px; color: #666;">Web: https://eximps-cloves.com | Email: admin@eximps-cloves.com</span>
    </div>
    <p style="text-align: center; margin-top: 40px; margin-bottom: 20px; font-weight: bold; font-size: 14px;">EMPLOYMENT AGREEMENT</p>
    <p><strong>This Employment Agreement</strong> ("Agreement") is entered into as of {{COMMENCEMENT_DATE}}, between Eximp & Cloves, a [Jurisdiction] corporation ("Company"), and {{STAFF_NAME}} ("Employee").</p>
    <p style="margin-top: 15px;"><strong>1. POSITION AND DUTIES</strong></p>
    <p>Employee is employed as {{ROLE}} in the {{DEPARTMENT}} department. Employee shall perform such duties and responsibilities as are customary and reasonable for the position, as directed by the Company.</p>
    <p><strong>2. COMPENSATION</strong></p>
    <p>Employee shall receive an annual salary of {{SALARY}}, payable in accordance with the Company payroll practices. The Company may adjust this compensation at its sole discretion.</p>
    <p><strong>3. BENEFITS</strong></p>
    <p>Employee shall be entitled to all benefits provided by the Company to similarly situated employees, including health insurance, pension contributions, and paid leave as per Company policy.</p>
    <p><strong>4. CONFIDENTIALITY AND INTELLECTUAL PROPERTY</strong></p>
    <p>Employee agrees to maintain strict confidentiality regarding all proprietary, sensitive, and non-public Company information, including but not limited to trade secrets, business plans, financial data, and customer information. All work product created by Employee shall be the exclusive property of the Company.</p>
    <p><strong>5. AT-WILL EMPLOYMENT</strong></p>
    <p>Employment under this Agreement is at-will. Either party may terminate employment at any time, with or without cause, upon written notice.</p>
    <p><strong>6. GOVERNING LAW</strong></p>
    <p>This Agreement shall be governed by and construed in accordance with the laws of [Jurisdiction], without regard to conflicts of law principles.</p>
    <p style="margin-top: 40px;"><strong>ACKNOWLEDGED AND AGREED BY:</strong></p>
    <p style="margin-top: 30px; line-height: 2.5;">Employee Signature: _____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Company Signature: _____________________<br>
    <span style="margin-left: 0;">Employee Name (Print): {{STAFF_NAME}}</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span>Name (Print): ________________________</span><br>
    Date: _______________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Date: _______________</p>',
    TRUE
);

-- Insert NDA Template
INSERT INTO legal_templates (name, category, description, default_content_html, is_active)
VALUES (
    'Non-Disclosure Agreement',
    'NDA',
    'Confidentiality and intellectual property protection agreement',
    '<div class="letterhead" style="padding: 40px 60px; border-bottom: 2px solid #C47D0A; margin-bottom: 20px;">
        <strong style="font-size: 16px;">EXIMP & CLOVES</strong><br>
        <span style="font-size: 11px; color: #666;">Web: https://eximps-cloves.com | Email: admin@eximps-cloves.com</span>
    </div>
    <p style="text-align: center; margin-top: 40px; margin-bottom: 20px; font-weight: bold; font-size: 14px;">NON-DISCLOSURE AGREEMENT (NDA)</p>
    <p>This Non-Disclosure Agreement ("NDA") is entered into as of {{COMMENCEMENT_DATE}} by and between Eximp & Cloves ("Disclosing Party") and {{STAFF_NAME}} ("Receiving Party").</p>
    <p><strong>WHEREAS:</strong> Disclosing Party and Receiving Party desire to explore a potential business relationship and may disclose certain confidential information to one another.</p>
    <p><strong>1. DEFINITION OF CONFIDENTIAL INFORMATION</strong></p>
    <p>"Confidential Information" means all non-public information related to the Disclosing Party''s business, including but not limited to: trade secrets, business plans, financial information and projections, customer lists, pricing information, technical data, software code, and strategic initiatives.</p>
    <p><strong>2. OBLIGATIONS OF RECEIVING PARTY</strong></p>
    <p>Receiving Party agrees to:</p>
    <ul style="margin-left: 20px;">
        <li>Maintain Confidential Information in strict confidence</li>
        <li>Limit access to employees or agents with a legitimate need to know</li>
        <li>Not disclose Confidential Information to any third party without prior written consent</li>
        <li>Use Confidential Information only for the purpose of evaluating the potential business relationship</li>
    </ul>
    <p><strong>3. PERMITTED DISCLOSURES</strong></p>
    <p>Receiving Party may disclose Confidential Information to the extent required by law or court order, provided that Receiving Party gives Disclosing Party prompt notice and cooperates with Disclosing Party in seeking protective measures.</p>
    <p><strong>4. TERM</strong></p>
    <p>This Agreement shall commence on the date hereof and remain in effect for a period of three (3) years, unless earlier terminated by either party upon written notice.</p>
    <p><strong>5. REMEDIES</strong></p>
    <p>Receiving Party acknowledges that breach of this Agreement may cause irreparable harm for which monetary damages are inadequate. Disclosing Party shall be entitled to seek injunctive relief and other equitable remedies.</p>
    <p style="margin-top: 40px;"><strong>ACKNOWLEDGED AND AGREED BY:</strong></p>
    <p style="margin-top: 30px; line-height: 2.5;">Receiving Party Signature: _____________________<br>
    Name (Print): {{STAFF_NAME}}<br>
    Date: _______________</p>',
    TRUE
);

-- Insert Disciplinary Review Template
INSERT INTO legal_templates (name, category, description, default_content_html, is_active)
VALUES (
    'Disciplinary Review',
    'Disciplinary Review',
    'Formal documentation of performance issues or conduct violations',
    '<div class="letterhead" style="padding: 40px 60px; border-bottom: 2px solid #C47D0A; margin-bottom: 20px;">
        <strong style="font-size: 16px;">EXIMP & CLOVES</strong><br>
        <span style="font-size: 11px; color: #666;">Web: https://eximps-cloves.com | Email: admin@eximps-cloves.com</span>
    </div>
    <p style="margin-top: 40px; font-weight: bold; font-size: 14px;">FORMAL DISCIPLINARY NOTICE</p>
    <p style="margin-top: 15px;"><strong>Employee Information:</strong></p>
    <ul style="margin-left: 20px; line-height: 1.8;">
        <li>Employee Name: {{STAFF_NAME}}</li>
        <li>Position: {{ROLE}}</li>
        <li>Department: {{DEPARTMENT}}</li>
        <li>Date of Notice: {{COMMENCEMENT_DATE}}</li>
        <li>Notice Level: [Verbal Warning / Written Warning / Final Warning / Suspension / Termination]</li>
    </ul>
    <p style="margin-top: 15px;"><strong>REASON FOR DISCIPLINARY ACTION:</strong></p>
    <p>[Describe the performance issue, misconduct, or policy violation in detail]</p>
    <p><strong>SPECIFIC INCIDENTS:</strong></p>
    <p>[Document dates, times, locations, and specific details of incidents leading to this notice]</p>
    <p><strong>PERFORMANCE EXPECTATIONS & REQUIRED IMPROVEMENTS:</strong></p>
    <p>[Clearly state the expected improvements or compliance requirements, with specific timeline for achievement]</p>
    <p><strong>CONSEQUENCES OF NON-COMPLIANCE:</strong></p>
    <p>Failure to meet the stated expectations or continued violations may result in further disciplinary action, up to and including termination of employment.</p>
    <p><strong>EMPLOYEE ACKNOWLEDGMENT</strong></p>
    <p>I acknowledge receipt of this notice and understand the expectations and potential consequences outlined herein. I have had the opportunity to provide my response to the allegations.</p>
    <p style="margin-top: 40px; line-height: 2.5;">Employee Signature: _____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Manager Signature: _____________________<br>
    Date: _______________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Date: _______________</p>',
    TRUE
);

-- Insert Termination Agreement Template
INSERT INTO legal_templates (name, category, description, default_content_html, is_active)
VALUES (
    'Termination Agreement',
    'Other',
    'Severance and separation agreement documentation',
    '<div class="letterhead" style="padding: 40px 60px; border-bottom: 2px solid #C47D0A; margin-bottom: 20px;">
        <strong style="font-size: 16px;">EXIMP & CLOVES</strong><br>
        <span style="font-size: 11px; color: #666;">Web: https://eximps-cloves.com | Email: admin@eximps-cloves.com</span>
    </div>
    <p style="text-align: center; margin-top: 40px; margin-bottom: 20px; font-weight: bold; font-size: 14px;">SEPARATION AGREEMENT & GENERAL RELEASE</p>
    <p>This Separation Agreement and General Release ("Agreement") is entered into as of {{COMMENCEMENT_DATE}}, between Eximp & Cloves ("Company") and {{STAFF_NAME}} ("Employee").</p>
    <p><strong>1. TERMINATION OF EMPLOYMENT</strong></p>
    <p>The parties agree that Employee''s employment with the Company shall terminate effective [Termination Date], for [reason: resignation / layoff / termination for cause / termination without cause].</p>
    <p><strong>2. FINAL COMPENSATION</strong></p>
    <p>Employee shall receive: (a) all accrued and unpaid salary through the termination date; (b) all accrued and unused paid leave; (c) separation pay of [amount] as consideration for the release and covenants contained herein.</p>
    <p><strong>3. BENEFITS CONTINUATION</strong></p>
    <p>Information regarding COBRA continuation of health insurance coverage will be provided separately. [Specify any other benefits to continue.]</p>
    <p><strong>4. GENERAL RELEASE</strong></p>
    <p>Employee hereby releases and forever discharges the Company, its officers, directors, employees, agents, and successors from any and all claims, demands, and causes of action arising out of Employee''s employment or termination thereof.</p>
    <p><strong>5. CONFIDENTIALITY AND NON-DISPARAGEMENT</strong></p>
    <p>Employee agrees to maintain confidentiality of all proprietary Company information and to refrain from making disparaging comments regarding the Company, its officers, or its business practices.</p>
    <p><strong>6. RETURN OF PROPERTY</strong></p>
    <p>Employee agrees to return all Company property, including but not limited to equipment, access cards, documents, and data, on or before the termination date.</p>
    <p style="margin-top: 40px;"><strong>ACKNOWLEDGED AND AGREED BY:</strong></p>
    <p style="margin-top: 30px; line-height: 2.5;">Employee Signature: _____________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Company Signature: _____________________<br>
    Date: _______________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Date: _______________</p>',
    TRUE
);
