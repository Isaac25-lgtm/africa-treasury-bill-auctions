# Journal submission build (Emerging Markets Review)

Regenerates the submission manuscripts in `manuscript/emr_submission/` from `manuscript/manuscript_draft.md`.

```bash
python scripts/journal/bib2json.py manuscript/references.bib refs.json
python scripts/journal/make_journal_md.py . manuscript/emr_submission
npm install docx@9.5.1            # once, in this folder or any parent
node scripts/journal/build_docx.js . refs.json manuscript/emr_submission/manuscript_EMR_anonymised.md manuscript_EMR_anonymised.docx
node scripts/journal/build_docx.js . refs.json manuscript/emr_submission/manuscript_EMR_full.md manuscript_EMR_full.docx
node scripts/journal/build_docx.js . refs.json manuscript/emr_submission/title_page_EMR.md title_page_EMR.docx plain
node scripts/journal/build_docx.js . refs.json manuscript/emr_submission/highlights_EMR.md highlights_EMR.docx plain
node scripts/journal/build_docx.js . refs.json manuscript/emr_submission/cover_letter_EMR.md cover_letter_EMR.docx plain
```

`manuscript_draft.md` stays the master copy; edit it, then rebuild. The reference list keeps only works cited in the text.
