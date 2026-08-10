### **Memory-Augmented LLM Approach for Android Bug Reproduction from Video Reports**
**Feb 2026 - Present**

**Tech Stack:** Python, Google Gemini 2.5 Pro, Vertex AI, ADB, uiautomator2, scikit-image

- Proposed two-stage memory-augmented LLM pipeline for reproducing Android GUI bugs from screen recordings, decoupling video understanding from device automation to avoid repeated per-scene VLM inference
- Evaluated against ViBR, a published VLM-based frame-accurate scene-replay approach (GPT-4o + GroundingDINO + CLIP), across 53 successful runs on 20+ real-world Android apps
- Demonstrated 25.7x latency reduction (39.4s vs 1012.1s avg per run) while preserving task-completion fidelity, suggesting memory reuse is a viable alternative to exhaustive scene-by-scene VLM replay

**AI/ML Engineer:**
- Designed and evaluated a two-stage memory-augmented LLM method: Stage 1 performs single-pass video-to-memory extraction (structured YAML+markdown task summary) via Gemini 2.5 Pro; Stage 2 conditions closed-loop device automation on that memory, eliminating re-analysis of raw video per step
- Ran comparative evaluation against ViBR (published baseline: GPT-4o + GroundingDINO region grounding + CLIP segmentation) across 20+ Android apps using a provider-agnostic LLM abstraction (Gemini, GPT-4o, Llama, Qwen, MiniCPM), isolating method effects from model choice

**Software Developer:**
- Implemented the two-stage pipeline as a staged, config-driven experimental harness (--stage 1/2/all) with dry-run validation for reproducible evaluation runs
- Built device automation harness (uiautomator2/ADB) with stall detection and history-windowed decision loop to execute inferred actions during evaluation
- Designed flat, versioned run-artifact schema to keep every experimental trial reproducible and auditable
