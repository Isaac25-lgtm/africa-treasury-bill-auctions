# Exploratory pilot replay

Treat this directory as research reference material. It contains 671 exact original-document URL/hash pairs and a local snapshot of the pilot's normalized extracts. The documents themselves remain on official sites. Some URLs can change. The fixtures and snapshot are not a completed public data release. Before publishing anything from this folder, review project scope and source permissions. Build a separate production-quality pipeline following the main handoff.

## Quick offline replay from the frozen exploratory extracts

Use Python 3.11 or later with pandas 2.2.3, NumPy, scikit-learn 1.8.0 and python-dateutil, subject to compatible installation. scikit-learn 1.8.0 requires Python 3.11 or later. Then run from this directory:

```sh
python -m pip install "pandas==2.2.3" "scikit-learn==1.8.0" numpy python-dateutil openpyxl
python -c "from pathlib import Path; import shutil; [shutil.copyfile(Path('cached_exploratory')/p, p) for p in ('panel.csv', 'ghana.csv')]"
python eval.py
python checks.py
python three.py
python economic.py
python aggregate_forecast.py
python maturity_forecast.py
```

For faster runs set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1 in your shell. Expected logs are included for the main exploratory run. Read labels carefully. Some outputs are grouped by tenor rows, other outputs are grouped by date. The Uganda and Kenya results cover different original date ranges. Three-country common-period results are computed by three.py after loading both snapshots. Expected logs are historical. The economic log was generated before the final Ghana parse, so a fresh run adds the Ghana lines.

## Verify or reconstruct from the exact source documents

Install Poppler (pdftotext and pdftoppm) and Tesseract. Regenerate OCR from the verified PDFs and check it against the source table pages. Cached OCR page text is not bundled. Use the fetch wrapper to verify originals. A source failure is visible and does not invalidate the offline snapshot of the exploratory outputs.

```sh
python fetch_frozen.py --group UG --limit 1
python fetch_frozen.py
python parse.py
python parse_ghana_frozen.py
python offer_audit.py
python eval.py
python checks.py
python three.py
python economic.py
python aggregate_forecast.py
python maturity_forecast.py
```

The raw replay may print parsing failures for three unrelated Uganda workbooks and skip several Ghana documents with ambiguous formats. A strict fetch accepts only exact original hashes and skips changed versions with a diagnostic. A raw replay after a partial fetch is only a partial reconstruction. Review the fetch report first. Move a freshly rebuilt panel to a separate file if you want a clean comparison to cached_exploratory. If OCR results differ, report why and regenerate audit evidence instead of forcing agreement. The formal analysis must enforce dated source availability, robust coverage, invitation timing and locked evaluation beyond the exploratory scripts.
