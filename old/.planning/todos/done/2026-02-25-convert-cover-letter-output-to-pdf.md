---
created: 2026-02-25T23:36:26.587Z
title: Convert cover letter output to PDF
area: general
files:
  - src/jd/service.py
  - scripts/run.py
---

## Problem

The cover letter is currently generated as text/markdown output only. It needs to be converted to a PDF file, similar to how the resume is compiled to PDF via LaTeX/tectonic. Users need a ready-to-send PDF cover letter alongside the resume PDF.

## Solution

Add a PDF conversion step for the cover letter after generation:
1. Determine output format — options include LaTeX (using existing tectonic pipeline), a simple HTML-to-PDF approach (e.g., WeasyPrint or pdfkit), or a plain-text-to-PDF approach
2. Create a cover letter LaTeX/HTML template that matches the structure in `templates/cover_letter_prompt.md`
3. Pipe the generated cover letter text into the template and compile to PDF
4. Save the PDF output alongside the resume PDF in the output directory
