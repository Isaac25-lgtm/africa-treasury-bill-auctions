// Build a review-ready Word manuscript from manuscript_draft.md, embedding figures and the reference list.
// usage: node build_docx.js <repo_root> <refs.json> <in.md> <out.docx> [plain]
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, ImageRun, ExternalHyperlink, Footer, PageNumber,
  LevelFormat, LineNumberRestartFormat, PageBreak,
} = require("docx");

const [root, refsPath, mdPath, outPath, mode] = process.argv.slice(2);
const PLAIN = mode === "plain";
const md = fs.readFileSync(mdPath, "utf8").replace(/\r\n/g, "\n");
// keep only works cited in the text: first author's surname (or organisation) must appear in the body
const bodyText = md.split(/^## References/m)[0].replace(/\s+/g, " ");
const refs = JSON.parse(fs.readFileSync(refsPath, "utf8")).filter(r => {
  const lead = r.pre.split(/,| \(/)[0].trim();
  const ok = bodyText.includes(lead);
  if (!ok) console.log("  (not cited, omitted from reference list):", lead);
  return ok;
});

const FONT = "Calibri";
const CONTENT_W = 11906 - 2 * 1440; // A4 width minus 1" margins (DXA)

// ------------------------------------------------------------------ inline markdown -> runs
function inline(text, base = {}) {
  const out = [];
  const re = /(\*\*([^*]+)\*\*)|(\*([^*\s][^*]*?)\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)\s]+)\))/g;
  let last = 0, m;
  const push = (s, extra = {}) => { if (s) out.push(new TextRun({ text: s, font: FONT, ...base, ...extra })); };
  while ((m = re.exec(text)) !== null) {
    push(text.slice(last, m.index));
    if (m[1]) out.push(...inline(m[2], { ...base, bold: true }));
    else if (m[3]) out.push(...inline(m[4], { ...base, italics: true }));
    else if (m[5]) push(m[6], { font: "Consolas", size: 19 });
    else if (m[7]) out.push(new ExternalHyperlink({ link: m[9], children: [
      new TextRun({ text: m[8], font: FONT, style: "Hyperlink", ...base })] }));
    last = re.lastIndex;
  }
  push(text.slice(last));
  return out;
}

// ------------------------------------------------------------------ block parser
const lines = md.split("\n");
const blocks = [];
for (let i = 0; i < lines.length;) {
  const l = lines[i];
  if (!l.trim()) { i++; continue; }
  if (/^#{1,3} /.test(l)) { blocks.push({ t: "h", level: l.match(/^#+/)[0].length, text: l.replace(/^#+ /, "") }); i++; continue; }
  if (/^---\s*$/.test(l)) { blocks.push({ t: "hr" }); i++; continue; }
  if (l.startsWith("|")) {
    const rows = [];
    while (i < lines.length && lines[i].startsWith("|")) rows.push(lines[i++]);
    blocks.push({ t: "table", rows }); continue;
  }
  if (/^\s*[*-] /.test(l)) {
    const items = [];
    while (i < lines.length && lines[i].trim() && (/^\s*[*-] /.test(lines[i]) || /^\s{2,}\S/.test(lines[i]))) {
      if (/^\s*[*-] /.test(lines[i])) items.push(lines[i].replace(/^\s*[*-] /, ""));
      else items[items.length - 1] += " " + lines[i].trim();
      i++;
    }
    blocks.push({ t: "list", items }); continue;
  }
  const para = [];
  while (i < lines.length && lines[i].trim() && !/^(#{1,3} |---\s*$|\||\s*[*-] )/.test(lines[i])) para.push(lines[i++]);
  blocks.push({ t: "p", lines: para });
}

// ------------------------------------------------------------------ renderers
const children = [];
const LINE = PLAIN ? 276 : 480; // double spacing for the review manuscript
const P = (runs, opts = {}) => new Paragraph({ children: runs, ...opts, spacing: { after: 120, line: LINE, ...(opts.spacing || {}) } });

function table(rows) {
  const split = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
  const head = split(rows[0]);
  const align = split(rows[1]).map(c => (c.endsWith(":") ? AlignmentType.RIGHT : AlignmentType.LEFT));
  const body = rows.slice(2).map(split);
  const n = head.length;
  const lens = head.map((h, j) => Math.max(h.length, ...body.map(r => (r[j] || "").length)));
  const w8 = x => Math.min(Math.max(x, 12), 40); // keep short columns readable, cap long ones
  const total = lens.reduce((a, b) => a + w8(b), 0);
  const widths = lens.map(x => Math.floor((w8(x) / total) * CONTENT_W));
  widths[n - 1] += CONTENT_W - widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
  const cell = (txt, j, isHead) => new TableCell({
    width: { size: widths[j], type: WidthType.DXA },
    borders: { top: border, bottom: border, left: border, right: border },
    shading: isHead ? { type: ShadingType.CLEAR, color: "auto", fill: "E8EEF4" } : undefined,
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: [new Paragraph({ alignment: isHead ? AlignmentType.LEFT : align[j],
      children: inline(txt, { size: 18, bold: isHead || undefined }) })],
  });
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: head.map((h, j) => cell(h, j, true)) }),
      ...body.map(r => new TableRow({ children: r.map((c, j) => cell(c, j, false)) }))],
  });
}

const FIGS = [
  ["fig1_decomposition.png", "Figure 1. Share of shortfall volume from bids short of the offer (D) versus bids not accepted (R), by country and level, common and recent windows."],
  ["fig2_maturity_shift.png", "Figure 2. Distribution of the accepted-minus-offered weighted maturity in auctions that met the overall offer."],
  ["fig3_uganda_timeline.png", "Figure 3. Uganda: overall fill and maturity shift per auction since 2022, with auction #1237 marked."],
];
function pngSize(buf) { return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) }; }

let section = "";
let seenH2 = false; // front matter (title, author block) keeps its line breaks
for (const b of blocks) {
  if (b.t === "h") {
    section = b.text;
    if (b.level >= 2) seenH2 = true;
    if (b.level === 1) {
      children.push(new Paragraph({ heading: HeadingLevel.TITLE, children: inline(b.text) }));
      continue;
    }
    if (b.level === 2 && (b.text === "Figures" || b.text === "References")) children.push(new Paragraph({ children: [new PageBreak()] }));
    children.push(new Paragraph({ heading: b.level === 2 ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2, children: inline(b.text) }));
    if (b.text === "Figures") {
      for (const [file, cap] of FIGS) {
        const buf = fs.readFileSync(path.join(root, "outputs", "figures", file));
        const { w, h } = pngSize(buf);
        const width = 600, height = Math.round((h / w) * width);
        children.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 240 },
          children: [new ImageRun({ type: "png", data: buf, transformation: { width, height },
            altText: { title: cap.split(".")[0], description: cap, name: file } })] }));
        children.push(P(inline(cap, { size: 20 }), { spacing: { after: 360, line: 276 } }));
      }
    }
    if (b.text === "References") {
      for (const r of refs) {
        children.push(new Paragraph({ indent: { left: 360, hanging: 360 }, spacing: { after: 100, line: 276 },
          children: [new TextRun({ text: r.pre, font: FONT, size: 20 }), new TextRun({ text: r.ital, font: FONT, size: 20, italics: true }),
            new TextRun({ text: r.post, font: FONT, size: 20 })] }));
      }
    }
    continue;
  }
  if (section === "Figures") continue; // replaced by embedded figures above
  if (section === "References") {
    if (b.t === "p") children.push(P(inline(b.lines.join(" "), { size: 18, color: "666666" }), { spacing: { before: 200 } }));
    continue;
  }
  if (b.t === "hr") { children.push(new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "999999", space: 4 } }, children: [] })); continue; }
  if (b.t === "table") { children.push(table(b.rows)); children.push(new Paragraph({ children: [], spacing: { after: 120 } })); continue; }
  if (b.t === "list") { for (const it of b.items) children.push(P(inline(it), { numbering: { reference: "bullets", level: 0 }, spacing: { after: 60, line: 360 } })); continue; }
  if (b.t === "p") {
    if (!seenH2 || b.lines[0].startsWith("**Authors:**")) {
      b.lines.forEach((l, k) => children.push(P(inline(l), { spacing: { after: k === b.lines.length - 1 ? 200 : 20 } })));
      continue;
    }
    const text = b.lines.join(" ");
    const isCaption = /^\*\*Table \d/.test(text);
    children.push(P(inline(text), isCaption ? { keepNext: true, spacing: { before: 200, after: 80 } } : {}));
  }
}

const heading = (size) => ({ run: { font: FONT, size, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 280, after: 120 }, keepNext: true } });
const doc = new Document({
  creator: "Omoding Isaac", title: "When Treasury Bill Auctions Miss Their Targets",
  description: "Manuscript draft for author review (generated from manuscript_draft.md)",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { font: FONT, size: 34, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 0, after: 240 }, keepNext: true } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, ...heading(28), paragraph: { ...heading(28).paragraph, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, ...heading(24), paragraph: { ...heading(24).paragraph, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: {
      page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } },
      ...(PLAIN ? {} : { lineNumbers: { countBy: 1, restart: LineNumberRestartFormat.NEW_PAGE, distance: 300 } }),
    },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], font: FONT, size: 18, color: "666666" })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(outPath, buf); console.log("wrote", outPath, buf.length, "bytes;", blocks.length, "blocks"); });
