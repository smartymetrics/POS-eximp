# Personnel Studio — Professional Word-Like Editor Rebuild Guide
## For Eximp & Cloves Infrastructure Limited

---

## CONTEXT: WHAT EXISTS AND WHY IT FAILS

The current `templates/personnel_editor.html` uses **GrapesJS** with the newsletter preset. This is fundamentally the wrong tool. GrapesJS is a drag-and-drop **email/newsletter builder** — it renders email-style column layouts and block grids. It has no concept of an A4 page, no real typography control, no justified legal text, no page breaks, no headers/footers, and no document flow. A lawyer sitting at this editor would feel like they are inside a Mailchimp campaign builder, not Microsoft Word.

**The goal**: Replace the entire `personnel_editor.html` file with a self-contained, single-file HTML/CSS/JS document editor that feels like Microsoft Word — white A4 pages in a gray canvas, a formatting ribbon at the top, and real document output that matches the company's established PDF style (as seen in the `FRONTDESK OFFER LETTER.pdf`).

---

## ARCHITECTURE DECISION

Do **not** use GrapesJS, TinyMCE, or Quill for this. Use **ProseMirror** via the **Tiptap** CDN build.

**Why Tiptap?**
- Ships as a single CDN-loadable bundle — no build step needed for a Jinja/Flask template
- Gives true `contenteditable` document semantics (not block soup)
- Supports marks, nodes, custom extensions, and commands identical to Word's model
- Output is clean semantic HTML that WeasyPrint (already used by this project) can render to PDF

**CDN imports needed (put in `<head>`):**
```html
<script src="https://unpkg.com/@tiptap/core@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/pm@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/starter-kit@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/extension-text-align@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/extension-font-family@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/extension-color@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/extension-highlight@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/extension-table@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/extension-table-row@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/extension-table-cell@2.4.0/dist/index.umd.js"></script>
<script src="https://unpkg.com/@tiptap/extension-table-header@2.4.0/dist/index.umd.js"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Times+New+Roman&family=Inter:wght@400;500;600;700&display=swap">
```

> **Note**: If CDN version conflicts arise, pin all Tiptap packages to the same version. Alternatively, use the standalone `@tiptap/core` UMD bundle from jsDelivr.

---

## FULL PAGE LAYOUT STRUCTURE

The HTML body should have three zones:

```
┌────────────────────────────────────────────────────────┐
│  TOP BAR (dark, brand gold accent — fixed, 56px)      │
│  [Logo] [Case Title Input]   [Smart Tags][Save][Back]  │
├────────────────────────────────────────────────────────┤
│  RIBBON (white/light gray — fixed, 44px)              │
│  [Font] [Size] | B I U S | ≡ | Align | Color | Table  │
├────────────────────────────────────────────────────────┤
│                                                        │
│  EDITOR CANVAS (gray, scrollable, overflow-y: auto)   │
│                                                        │
│        ┌──────────────────────────────┐               │
│        │   A4 PAGE (white, shadow)    │               │
│        │  [LETTERHEAD — locked]       │               │
│        │  ─────────────── gold line ─ │               │
│        │                              │               │
│        │  [DOCUMENT BODY — editable] │               │
│        │                              │               │
│        │  [SIGNATURE BLOCK]          │               │
│        │  ─────── footer band ─────  │               │
│        └──────────────────────────────┘               │
│                                                        │
│        [Page 2 if content overflows...]               │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### CSS for the canvas and page simulation:

```css
body, html {
  margin: 0; padding: 0; height: 100%;
  background: #111;
  font-family: 'Inter', sans-serif;
  overflow: hidden;
}

/* Three stacked zones */
#top-bar    { height: 56px; position: fixed; top: 0; width: 100%; z-index: 100; }
#ribbon     { height: 44px; position: fixed; top: 56px; width: 100%; z-index: 99; }
#canvas     { 
  position: fixed; top: 100px; bottom: 0; left: 0; right: 0;
  overflow-y: auto;
  background: #2b2b2b;  /* dark gray like Word's background */
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0 80px;
  gap: 30px;
}

/* The A4 paper simulation */
.a4-page {
  width: 794px;          /* 210mm at 96dpi */
  min-height: 1123px;    /* 297mm at 96dpi */
  background: #fff;
  box-shadow: 0 4px 24px rgba(0,0,0,0.55);
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 0;            /* letterhead/footer handle their own spacing */
  page-break-after: always;
}

/* Responsive: on smaller screens, scale the page */
@media (max-width: 900px) {
  .a4-page { transform: scale(0.75); transform-origin: top center; }
}
```

---

## THE LETTERHEAD (Non-Editable Header)

Study the offer letter PDF carefully. The letterhead structure is:

1. **Top-left**: Company logo (from `/static/img/logo.svg` or the Supabase CDN URL)
2. **Top-right**: Three lines of contact info — Phone, Web, Email — in a small bordered box
3. **Below both**: A thick horizontal gold line (`#C47D0A`) that spans the full width
4. **Background images**: `static/img/headed_paper_top.png` and `static/img/headed_paper_bottom.png` exist in the project — these are the decorative corner images used on the actual PDF. Reference them.

```html
<!-- LETTERHEAD — this div is NOT contenteditable -->
<div class="letterhead" contenteditable="false">
  <!-- Corner decoration top-left (the dark angular bar visible in the PDF) -->
  <img src="/static/img/headed_paper_top.png" class="header-corner-img" alt="">
  
  <div class="letterhead-inner">
    <!-- Logo -->
    <div class="letterhead-logo">
      <img src="/static/img/logo.svg" alt="Eximp & Cloves" style="height:55px;">
    </div>
    
    <!-- Contact box (top-right, matching the PDF exactly) -->
    <div class="letterhead-contact">
      <div class="contact-line">
        <span class="contact-label">Phone:</span> +234 912 6864 383
      </div>
      <div class="contact-line">
        <span class="contact-label">Web:</span> www.eximpandclove.com
      </div>
      <div class="contact-line">
        <span class="contact-label">Email:</span> eximpcloves@gmail.com
      </div>
    </div>
  </div>
  
  <!-- The gold divider line -->
  <div class="letterhead-divider"></div>
</div>
```

```css
.letterhead {
  position: relative;
  padding: 0;
  user-select: none;
  pointer-events: none;   /* Lawyers cannot accidentally click into it */
}

.header-corner-img {
  position: absolute;
  top: 0; left: 0;
  width: 120px;
  z-index: 1;
}

.letterhead-inner {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 36px 16px;
  position: relative;
  z-index: 2;
}

.letterhead-contact {
  border: 1px solid #ddd;
  padding: 8px 12px;
  font-size: 9pt;
  line-height: 1.7;
  color: #333;
}

.contact-label {
  font-weight: 700;
  color: #111;
}

.letterhead-divider {
  height: 4px;
  background: #C47D0A;
  margin: 0 36px;
}
```

---

## THE DOCUMENT BODY (Editable Area)

This is where Tiptap lives. It is a single `div` with `id="editor"` that Tiptap mounts into.

```css
.document-body {
  padding: 28px 72px;   /* ~2.5cm margins left/right, matching A4 standard */
  flex: 1;
  font-family: 'Times New Roman', serif;  /* Legal documents use serif */
  font-size: 11pt;
  line-height: 1.6;
  color: #000;
  min-height: 900px;
}

/* ProseMirror (Tiptap's editor root) */
.ProseMirror {
  outline: none;
  min-height: 800px;
}

.ProseMirror p {
  margin-bottom: 10pt;
  text-align: justify;  /* Default: justified text, matching the offer letter */
}

.ProseMirror h1, .ProseMirror h2, .ProseMirror h3 {
  font-family: 'Inter', sans-serif;
  font-weight: 700;
  color: #111;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 20pt 0 8pt;
}

.ProseMirror h1 { font-size: 13pt; }
.ProseMirror h2 { font-size: 11pt; }
.ProseMirror h3 { font-size: 10.5pt; }

/* Merge fields — highlighted so lawyers can see them */
.merge-field {
  background: #FFF3CD;
  border: 1px dashed #C47D0A;
  border-radius: 3px;
  padding: 0 4px;
  font-family: monospace;
  font-size: 9.5pt;
  color: #7A4E0A;
}

/* Tables */
.ProseMirror table {
  border-collapse: collapse;
  width: 100%;
  margin: 12pt 0;
}
.ProseMirror td, .ProseMirror th {
  border: 1px solid #bbb;
  padding: 6pt 8pt;
  font-size: 10.5pt;
}
.ProseMirror th { background: #f0f0f0; font-weight: bold; }

/* Selection highlight */
.ProseMirror ::selection { background: #c8e6ff; }
```

---

## THE PAGE FOOTER (Non-Editable)

The offer letter PDF shows a dark horizontal band at the bottom of each page with a gold accent. Replicate it:

```html
<!-- FOOTER — not contenteditable -->
<div class="page-footer" contenteditable="false">
  <img src="/static/img/headed_paper_bottom.png" class="footer-corner-img" alt="">
  <div class="footer-bar-gold"></div>
  <div class="footer-bar-dark">
    <span>Eximp & Cloves Infrastructure Limited</span>
    <span class="page-num">Page <span class="page-number">1</span></span>
  </div>
</div>
```

```css
.page-footer {
  margin-top: auto;
  user-select: none;
  pointer-events: none;
  position: relative;
}

.footer-corner-img {
  position: absolute;
  bottom: 0; right: 0;
  width: 120px;
}

.footer-bar-gold {
  height: 6px;
  background: #C47D0A;
}

.footer-bar-dark {
  height: 22px;
  background: #111111;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 36px;
  color: #aaa;
  font-size: 8pt;
  font-family: 'Inter', sans-serif;
}
```

---

## WATERMARK

The offer letter has a faint diagonal watermark. Implement it as a CSS pseudo-element on `.a4-page`:

```css
.a4-page::before {
  content: 'EXIMP & CLOVES';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-35deg);
  font-size: 80px;
  font-weight: 900;
  font-family: 'Inter', sans-serif;
  color: rgba(196, 125, 10, 0.04);  /* Very faint gold */
  letter-spacing: 12px;
  text-transform: uppercase;
  pointer-events: none;
  user-select: none;
  z-index: 0;
  white-space: nowrap;
}

/* If the document is in DRAFT status, show a more visible watermark */
.a4-page.draft-mode::before {
  content: 'DRAFT';
  color: rgba(196, 125, 10, 0.08);
  font-size: 120px;
}
```

---

## THE RIBBON (Formatting Toolbar)

The ribbon goes between the top bar and the canvas. Style it to look like a simplified Word ribbon — light gray background, grouped buttons separated by vertical dividers.

```html
<div id="ribbon">
  <!-- Group 1: Font -->
  <select id="font-family">
    <option value="'Times New Roman', serif">Times New Roman</option>
    <option value="'Inter', sans-serif">Inter</option>
    <option value="Arial, sans-serif">Arial</option>
    <option value="Georgia, serif">Georgia</option>
  </select>
  <select id="font-size">
    <option>8</option><option>9</option><option>10</option>
    <option selected>11</option><option>12</option><option>14</option>
    <option>16</option><option>18</option><option>24</option><option>36</option>
  </select>
  
  <div class="ribbon-divider"></div>
  
  <!-- Group 2: Inline marks -->
  <button data-cmd="bold"          title="Bold (Ctrl+B)"><b>B</b></button>
  <button data-cmd="italic"        title="Italic (Ctrl+I)"><i>I</i></button>
  <button data-cmd="underline"     title="Underline (Ctrl+U)"><u>U</u></button>
  <button data-cmd="strike"        title="Strikethrough"><s>S</s></button>
  
  <div class="ribbon-divider"></div>
  
  <!-- Group 3: Alignment -->
  <button data-align="left"    title="Align Left">⬅</button>
  <button data-align="center"  title="Center">☰</button>
  <button data-align="right"   title="Align Right">➡</button>
  <button data-align="justify" title="Justify" class="active">≡</button>
  
  <div class="ribbon-divider"></div>
  
  <!-- Group 4: Lists -->
  <button data-cmd="bulletList"  title="Bullet List">• List</button>
  <button data-cmd="orderedList" title="Numbered List">1. List</button>
  
  <div class="ribbon-divider"></div>
  
  <!-- Group 5: Heading styles (key for legal docs) -->
  <select id="block-type">
    <option value="paragraph">Normal</option>
    <option value="heading1">Heading 1 (Section Title)</option>
    <option value="heading2">Heading 2</option>
    <option value="heading3">Heading 3</option>
  </select>
  
  <div class="ribbon-divider"></div>
  
  <!-- Group 6: Insert -->
  <button id="insert-table-btn" title="Insert Table">⊞ Table</button>
  <button id="insert-hr-btn"    title="Insert Divider">── Line</button>
  <button id="insert-date-btn"  title="Insert Today's Date">📅 Date</button>
  
  <div class="ribbon-divider"></div>
  
  <!-- Group 7: Print/Export -->
  <button id="print-btn"  title="Print / Save as PDF">🖨 Print</button>
  <button id="export-btn" title="Export to server PDF">⬇ Export PDF</button>
</div>
```

```css
#ribbon {
  background: #f3f3f3;
  border-bottom: 1px solid #ccc;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 0 12px;
  height: 44px;
  overflow-x: auto;
}

#ribbon button {
  background: none;
  border: 1px solid transparent;
  border-radius: 3px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 0.82rem;
  color: #333;
  height: 32px;
  white-space: nowrap;
  transition: background 0.15s;
}

#ribbon button:hover       { background: #e0e0e0; border-color: #bbb; }
#ribbon button.active      { background: #d0d8ff; border-color: #6677cc; }

#ribbon select {
  border: 1px solid #ccc;
  border-radius: 3px;
  padding: 3px 6px;
  font-size: 0.82rem;
  height: 28px;
  background: white;
}

.ribbon-divider {
  width: 1px;
  height: 24px;
  background: #ccc;
  margin: 0 4px;
  flex-shrink: 0;
}
```

---

## TIPTAP INITIALISATION

```javascript
// Import from global UMD bundles loaded via CDN
const { Editor }        = Tiptap;
const { StarterKit }    = TiptapStarterKit;
const { TextAlign }     = TiptapTextAlign;
const { FontFamily }    = TiptapFontFamily;
const { Color }         = TiptapColor;
const { Highlight }     = TiptapHighlight;
const { Table }         = TiptapTable;
const { TableRow }      = TiptapTableRow;
const { TableCell }     = TiptapTableCell;
const { TableHeader }   = TiptapTableHeader;

const editor = new Editor({
  element: document.querySelector('#editor'),
  extensions: [
    StarterKit,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    FontFamily,
    Color,
    Highlight.configure({ multicolor: true }),
    Table.configure({ resizable: true }),
    TableRow,
    TableCell,
    TableHeader,
  ],
  content: `
    <p><strong>15TH APRIL 2026</strong></p>
    <p>Dear <strong>{{full_name}}</strong>,</p>
    <p>We are pleased to offer you the position of <strong>{{job_title}}</strong>...</p>
  `,
  onUpdate({ editor }) {
    // Auto-save to localStorage every 30s as backup
    localStorage.setItem('personnel_draft_' + matterId, editor.getHTML());
  },
  onSelectionUpdate({ editor }) {
    syncRibbonState(editor);
  }
});
```

---

## RIBBON COMMAND WIRING

```javascript
// Wire simple toggle buttons
document.querySelectorAll('[data-cmd]').forEach(btn => {
  btn.addEventListener('click', () => {
    const cmd = btn.dataset.cmd;
    editor.chain().focus()[cmd]().run();
  });
});

// Wire alignment buttons
document.querySelectorAll('[data-align]').forEach(btn => {
  btn.addEventListener('click', () => {
    editor.chain().focus().setTextAlign(btn.dataset.align).run();
  });
});

// Font family select
document.getElementById('font-family').addEventListener('change', e => {
  editor.chain().focus().setFontFamily(e.target.value).run();
});

// Font size — implement as a custom inline style mark
// (Tiptap doesn't have a built-in font size; use the TextStyle extension with CSS)
// Add TiptapTextStyle extension and use:
document.getElementById('font-size').addEventListener('change', e => {
  editor.chain().focus()
    .setMark('textStyle', { fontSize: e.target.value + 'pt' })
    .run();
});

// Block type / heading level
document.getElementById('block-type').addEventListener('change', e => {
  const val = e.target.value;
  if (val === 'paragraph') {
    editor.chain().focus().setParagraph().run();
  } else {
    const level = parseInt(val.replace('heading', ''));
    editor.chain().focus().toggleHeading({ level }).run();
  }
});

// Insert table
document.getElementById('insert-table-btn').addEventListener('click', () => {
  editor.chain().focus()
    .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
    .run();
});

// Insert horizontal rule
document.getElementById('insert-hr-btn').addEventListener('click', () => {
  editor.chain().focus().setHorizontalRule().run();
});

// Insert today's date
document.getElementById('insert-date-btn').addEventListener('click', () => {
  const date = new Date().toLocaleDateString('en-NG', {
    day: 'numeric', month: 'long', year: 'numeric'
  }).toUpperCase();
  editor.chain().focus().insertContent(date).run();
});

// Sync ribbon button active states when cursor moves
function syncRibbonState(editor) {
  const cmds = ['bold','italic','underline','strike','bulletList','orderedList'];
  cmds.forEach(cmd => {
    const btn = document.querySelector(`[data-cmd="${cmd}"]`);
    if (btn) btn.classList.toggle('active', editor.isActive(cmd));
  });
  ['left','center','right','justify'].forEach(align => {
    const btn = document.querySelector(`[data-align="${align}"]`);
    if (btn) btn.classList.toggle('active', editor.isActive({ textAlign: align }));
  });
}
```

---

## KEYBOARD SHORTCUTS

Wire these manually since lawyers expect them:

```javascript
document.addEventListener('keydown', e => {
  if (!e.ctrlKey && !e.metaKey) return;
  switch(e.key) {
    case 'b': e.preventDefault(); editor.chain().focus().toggleBold().run(); break;
    case 'i': e.preventDefault(); editor.chain().focus().toggleItalic().run(); break;
    case 'u': e.preventDefault(); editor.chain().focus().toggleUnderline().run(); break;
    case 's': e.preventDefault(); saveDraft(); break;
    case 'p': e.preventDefault(); printDocument(); break;
    case 'z': e.preventDefault(); editor.chain().focus().undo().run(); break;
    case 'y': e.preventDefault(); editor.chain().focus().redo().run(); break;
  }
});
```

---

## SMART TAGS (MERGE FIELDS)

The existing modal is fine in concept. Improve the **insertion mechanism**: when a user clicks "Insert" (not just "Copy"), the tag should be inserted directly into the editor at the cursor position, styled as a highlighted merge field.

```javascript
// All tags for personnel documents
const SMART_TAGS = [
  // HR / Personnel
  { code: '{{full_name}}',       label: 'Full Name',           group: 'Personnel' },
  { code: '{{job_title}}',       label: 'Job Title',           group: 'Personnel' },
  { code: '{{commencement_date}}', label: 'Start Date',        group: 'Personnel' },
  { code: '{{monthly_salary}}',  label: 'Monthly Salary (₦)',  group: 'Personnel' },
  { code: '{{probation_months}}', label: 'Probation Period',   group: 'Personnel' },
  { code: '{{reporting_to}}',    label: 'Reporting Line',      group: 'Personnel' },
  { code: '{{annual_leave_days}}', label: 'Annual Leave Days', group: 'Personnel' },
  { code: '{{non_compete_months}}', label: 'Non-Compete Period', group: 'Personnel' },
  { code: '{{notice_period}}',   label: 'Notice Period',       group: 'Personnel' },
  // Company
  { code: '{{company_name}}',    label: 'Company Full Name',   group: 'Company' },
  { code: '{{company_address}}', label: 'Company Address',     group: 'Company' },
  { code: '{{today_date}}',      label: "Today's Date",        group: 'Company' },
  // Real Estate context
  { code: '{{property_name}}',   label: 'Property Name',       group: 'Real Estate' },
  { code: '{{plot_size}}',       label: 'Plot Size (sqm)',      group: 'Real Estate' },
  { code: '{{plot_price}}',      label: 'Plot Price (₦)',       group: 'Real Estate' },
];

function insertTag(code) {
  // Insert the merge field as styled inline HTML
  editor.chain().focus().insertContent(
    `<span class="merge-field">${code}</span>&nbsp;`
  ).run();
  closeModal('tags-modal');
}
```

Render the modal body dynamically grouped by the `group` field, with both a **Copy** button and an **Insert at Cursor** button per tag.

---

## CLAUSE LIBRARY

This was stubbed in the existing file but never implemented. Build it as a modal that pre-populates common legal paragraphs a lawyer can insert at cursor with one click.

```javascript
const CLAUSE_LIBRARY = [
  {
    title: 'Confidentiality & Non-Disclosure',
    category: 'Standard Clauses',
    content: `<h2>CONFIDENTIALITY AND NON-DISCLOSURE</h2>
      <p>You are bound by strict confidentiality obligations and must not disclose any Company information during or after your employment without prior written consent. You agree to keep all confidential information, trade secrets, and proprietary data of the Company strictly confidential during and after your employment.</p>`
  },
  {
    title: 'Probationary Period (3 months)',
    category: 'Standard Clauses',
    content: `<h2>PROBATIONARY PERIOD</h2>
      <p>You will be subject to a <strong>three (3) months probationary period</strong>, during which your performance, conduct, communication skills, and overall suitability for the role will be assessed. The Company reserves the right to confirm your employment, extend your probation, or terminate your employment based on performance during this period. During this period, your employment may be terminated with <strong>one week's notice</strong> if performance is deemed unsatisfactory.</p>`
  },
  {
    title: 'Non-Compete & Non-Solicitation (12 months)',
    category: 'Standard Clauses',
    content: `<h2>NON-COMPETE AND NON-SOLICITATION</h2>
      <p>During your employment and for a period of <strong>{{non_compete_months}} months</strong> following termination, you agree not to: (1) solicit, entice away, or attempt to solicit any employee of the Company; or (2) solicit or approach any client or customer of the Company with whom you had dealings during your employment for the purpose of offering competing goods or services.</p>`
  },
  {
    title: 'Intellectual Property Assignment',
    category: 'Standard Clauses',
    content: `<h2>INTELLECTUAL PROPERTY</h2>
      <p>All intellectual property rights in any work, invention, discovery, improvement, or innovation created, developed, or conceived by you during the course of your employment, whether alone or jointly with others, shall belong exclusively to the Company. You agree to promptly disclose all such intellectual property to the Company and to execute all documents necessary to vest such rights in the Company.</p>`
  },
  {
    title: 'AI Use Policy (Eximp Standard)',
    category: 'Company-Specific',
    content: `<h2>ARTIFICIAL INTELLIGENCE USE</h2>
      <p>While we acknowledge and encourage responsible use of artificial intelligence (AI) tools; we require all employees to acknowledge that: (1) any work produced using AI tools shall remain the exclusive property of the Company; (2) you shall not input any confidential information into any external AI platform without prior written authorisation; (3) you are responsible for reviewing, verifying, and taking accountability for any AI-generated outputs; and (4) all work produced with AI assistance must clearly designate that AI was used, specifying how and where.</p>`
  },
  {
    title: 'Acceptance Block',
    category: 'Document Structure',
    content: `<h2 style="text-align:center;">ACCEPTANCE</h2>
      <p>I, <span class="merge-field">{{full_name}}</span>, accept the terms and conditions of this employment offer.</p>
      <br><br>
      <table style="width:100%; border:none;">
        <tr>
          <td style="border:none; width:45%; border-top:1px solid #111; padding-top:8px;">
            <strong>Signature</strong>
          </td>
          <td style="border:none; width:10%;"></td>
          <td style="border:none; width:45%; border-top:1px solid #111; padding-top:8px;">
            <strong>Date</strong>
          </td>
        </tr>
      </table>`
  },
];

function insertClause(content) {
  editor.chain().focus().insertContent(content).run();
  closeModal('clause-modal');
}
```

In the modal, group clauses by `category`, show the title and a short preview, and provide an **"Insert"** button. Do not require the lawyer to copy-paste.

---

## TEMPLATE SELECTOR

Add a "New from Template" option to the top bar. When clicked, it opens a modal with pre-built document templates. The first template should be the full Eximp & Cloves Offer Letter.

```javascript
const TEMPLATES = [
  {
    id: 'offer_letter',
    name: 'Standard Offer Letter',
    description: 'Full employment offer letter matching Eximp & Cloves brand',
    content: `
      <p style="text-align:right;"><strong>{{today_date}}</strong></p>
      <p>Dear <strong><span class="merge-field">{{full_name}}</span></strong>,</p>
      <p>We are pleased to offer you the mid-level professional position of <strong><span class="merge-field">{{job_title}}</span></strong>. This letter outlines the terms and conditions of your employment pending execution of your employment contract.</p>
      <h2>POSITION DETAILS</h2>
      <p><strong>Position:</strong> <span class="merge-field">{{job_title}}</span><br>
      <strong>Reporting To:</strong> <span class="merge-field">{{reporting_to}}</span><br>
      <strong>Commencement Date:</strong> <span class="merge-field">{{commencement_date}}</span></p>
      <h2>COMPENSATION</h2>
      <p><strong>Base Salary: ₦<span class="merge-field">{{monthly_salary}}</span> per month</strong></p>
      <p>You shall be entitled to a gross monthly salary of <span class="merge-field">{{monthly_salary}}</span>. Statutory deductions (PAYE, Pension, etc.) shall apply as required by Nigerian law.</p>
      ... (continue with all standard sections)
    `
  }
];
```

---

## PRINT AND PDF EXPORT

### Browser Print (Recommended for immediate use)

```javascript
function printDocument() {
  // Gather the current editor HTML
  const body = editor.getHTML();
  
  // Build a complete print document with all brand styles
  const printWindow = window.open('', '_blank');
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${document.getElementById('case-title').value || 'Eximp Document'}</title>
      <style>
        @page { size: A4; margin: 1.5cm 1.8cm; }
        body { font-family: 'Times New Roman', serif; font-size: 11pt; 
               line-height: 1.6; color: #000; }
        p { margin-bottom: 10pt; text-align: justify; }
        h1, h2, h3 { font-family: Arial, sans-serif; font-weight: 700; 
                      text-transform: uppercase; letter-spacing: 0.04em; }
        h2 { font-size: 11pt; margin: 18pt 0 6pt; }
        table { border-collapse: collapse; width: 100%; }
        td, th { border: 1px solid #bbb; padding: 5pt 7pt; }
        .merge-field { font-weight: bold; }
        /* Header */
        .print-header { display: flex; justify-content: space-between; 
                         align-items: flex-start; padding-bottom: 12pt; 
                         border-bottom: 3pt solid #C47D0A; margin-bottom: 20pt; }
        .print-contact { border: 1px solid #ddd; padding: 6pt 10pt; 
                          font-size: 9pt; line-height: 1.7; }
        /* Footer via @page is set above */
      </style>
    </head>
    <body>
      <div class="print-header">
        <img src="/static/img/logo.svg" style="height:50px;" alt="Eximp & Cloves">
        <div class="print-contact">
          <strong>Phone:</strong> +234 912 6864 383<br>
          <strong>Web:</strong> www.eximpandclove.com<br>
          <strong>Email:</strong> eximpcloves@gmail.com
        </div>
      </div>
      ${body}
    </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.print();
}
```

### Server-Side PDF Export (WeasyPrint — already in the project)

The existing `pdf_service.py` and WeasyPrint setup is already in this project. Reuse it:

```javascript
async function exportPDF() {
  const btn = document.getElementById('export-btn');
  btn.textContent = 'Generating...';
  btn.disabled = true;
  
  const res = await fetch('/api/hr-legal/matters/render-pdf', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
    },
    body: JSON.stringify({
      title: document.getElementById('case-title').value,
      html: editor.getHTML(),
      matter_id: matterId
    })
  });
  
  if (res.ok) {
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${document.getElementById('case-title').value || 'document'}.pdf`;
    a.click();
  } else {
    alert('PDF export failed. Try browser print instead.');
  }
  
  btn.textContent = '⬇ Export PDF';
  btn.disabled = false;
}
```

---

## SAVE / LOAD LOGIC

Keep the existing API endpoints (`/api/hr-legal/matters/{id}/save`). Just update what is sent:

```javascript
async function saveDraft() {
  const btn = document.getElementById('save-draft');
  btn.textContent = 'Saving...';
  btn.disabled = true;

  const payload = {
    title: document.getElementById('case-title').value,
    html: editor.getHTML(),
    css: ''   // No separate CSS needed — styles are embedded
  };

  try {
    const res = await fetch(`/api/hr-legal/matters/${matterId}/save`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('ec_token')}`
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      btn.textContent = 'Saved ✓';
      setTimeout(() => { btn.textContent = '💾 Save Draft'; btn.disabled = false; }, 2000);
    } else {
      alert('Save failed. Check connection.');
      btn.textContent = '💾 Save Draft';
      btn.disabled = false;
    }
  } catch {
    alert('Network error.');
    btn.textContent = '💾 Save Draft';
    btn.disabled = false;
  }
}

// Auto-save every 60 seconds
setInterval(() => {
  if (matterId) saveDraft();
}, 60000);

// Load on page open
async function loadMatter() {
  if (!matterId) return;
  try {
    const res = await fetch(`/api/hr-legal/matters/${matterId}`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('ec_token')}` }
    });
    const data = await res.json();
    document.getElementById('case-title').value = data.matter.title || '';
    if (data.matter.content_html) {
      editor.commands.setContent(data.matter.content_html);
    }
  } catch (err) { console.error('Load error:', err); }
}
```

---

## TOP BAR

Keep the dark top bar from the existing file. Rearrange slightly:

```html
<div id="top-bar">
  <!-- Left: logo and title -->
  <div class="top-left">
    <img src="/static/img/logo.svg" alt="" style="height:30px;">
    <span class="app-title">Personnel Studio</span>
    <div class="divider-v"></div>
    <input type="text" id="case-title" placeholder="Document title (e.g. Offer Letter – John Doe)">
  </div>
  
  <!-- Right: actions -->
  <div class="top-right">
    <button onclick="openModal('template-modal')">📄 Templates</button>
    <button onclick="openModal('tags-modal')">🏷 Smart Tags</button>
    <button onclick="openModal('clause-modal')">📋 Clauses</button>
    <button onclick="exportPDF()">⬇ Export PDF</button>
    <button id="save-draft" onclick="saveDraft()">💾 Save Draft</button>
    <button onclick="window.history.back()" class="btn-ghost">← Back</button>
  </div>
</div>
```

```css
#top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1a1a1a;
  border-bottom: 3px solid #C47D0A;
  padding: 0 20px;
  height: 56px;
  gap: 12px;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

#case-title {
  background: #2a2a2a;
  border: 1px solid #444;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 0.88rem;
  width: 320px;
  outline: none;
}
#case-title:focus { border-color: #C47D0A; }

.app-title {
  color: #C47D0A;
  font-weight: 700;
  font-size: 1rem;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.divider-v { width: 1px; height: 24px; background: #333; }

.top-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.top-right button {
  background: #C47D0A;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 7px 14px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.top-right button:hover { background: #a96008; }
.top-right button.btn-ghost { background: transparent; border: 1px solid #444; color: #aaa; }
```

---

## MODAL SYSTEM (REUSABLE)

```javascript
function openModal(id)  { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden');    }

// Close on backdrop click
document.querySelectorAll('.modal-overlay').forEach(el => {
  el.addEventListener('click', e => {
    if (e.target === el) closeModal(el.id);
  });
});

// Close on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay:not(.hidden)')
      .forEach(m => closeModal(m.id));
  }
});
```

---

## STATUS BAR (optional but professional)

Add a thin status bar at the very bottom of the screen showing word count, character count, and autosave status:

```html
<div id="status-bar">
  <span id="word-count">0 words</span>
  <span class="sep">|</span>
  <span id="char-count">0 characters</span>
  <span class="sep">|</span>
  <span id="autosave-status">All changes saved</span>
</div>
```

```javascript
editor.on('update', () => {
  const text  = editor.getText();
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  document.getElementById('word-count').textContent = `${words} words`;
  document.getElementById('char-count').textContent = `${text.length} characters`;
  document.getElementById('autosave-status').textContent = 'Unsaved changes';
});
```

---

## THINGS EXPLICITLY NOT TO DO

1. **Do not use GrapesJS** for this file. GrapesJS is still appropriate for `legal_editor.html` if that is for email/marketing templates. But it has no place in a document editor.

2. **Do not use `overflow: hidden` on `body`** in the new version. The page must scroll. Only the top bar and ribbon should be `position: fixed`.

3. **Do not let the letterhead or footer be editable**. Set `contenteditable="false"` on those divs and wrap them outside the Tiptap `#editor` element.

4. **Do not try to implement real multi-page pagination in the browser** with JavaScript. It is unnecessarily complex. Instead: let the content grow naturally below the letterhead (the A4 page `min-height` ensures it looks like paper), and let WeasyPrint handle actual page breaks when rendering to PDF server-side. For the browser print dialog, CSS `@page` and `break-before: page` handles it.

5. **Do not save CSS separately** from HTML. Tiptap produces clean inline-friendly HTML. The `css` field in the API payload can be sent empty.

6. **Do not use `alert()` for copy confirmation**. Use a small toast notification instead.

---

## SUMMARY OF FILES TO CHANGE

| File | Action |
|------|--------|
| `templates/personnel_editor.html` | **Full rewrite** — replace GrapesJS with Tiptap-based editor as described |
| `templates/legal_editor.html` | **Do not touch** |
| `routers/hr_legal.py` | No change required — existing endpoints are correct |
| `pdf_service.py` | Add a `/render-pdf` endpoint that accepts raw HTML body and wraps it in the brand template |
| `static/img/` | Ensure `logo.svg`, `headed_paper_top.png`, `headed_paper_bottom.png` are present — they already are |

---

*Guide prepared April 2026 — for Eximp & Cloves Infrastructure Limited — Personnel Studio rebuild.*