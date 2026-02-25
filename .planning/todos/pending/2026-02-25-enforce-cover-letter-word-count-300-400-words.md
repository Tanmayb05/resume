---
created: 2026-02-25T23:35:14.955Z
title: Enforce cover letter word count 300-400 words
area: general
files:
  - templates/cover_letter_prompt.md
---

## Problem

The cover letter generation does not consistently produce output in the 300-400 word range. The prompt in `templates/cover_letter_prompt.md` currently says "≤450 words" but the desired range is 300-400 words. The generated cover letter should strictly follow the structure defined in `cover_letter_prompt.md` (salutation, introduction with exact first sentence, main body with 3-5 reasons, availability paragraph, closing, signature block) AND land within the 300-400 word count.

## Solution

Update the cover letter prompt in `templates/cover_letter_prompt.md` to:
1. Change the word limit from "≤450 words" to a strict "300-400 words" range
2. Add explicit word count guidance (e.g., "Target exactly 300-400 words. Count words before finalizing.")
3. Ensure any cover letter generation logic/pipeline step enforces this range when producing output
