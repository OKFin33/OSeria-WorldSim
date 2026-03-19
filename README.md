<div align="center">
  <h1>OSeria</h1>
  <p><strong>A Dual-Core Interactive Narrative Engine</strong></p>
  
  [![Architect](https://img.shields.io/badge/Module-Architect-blue.svg)](#the-architect)
  [![Runtime](https://img.shields.io/badge/Module-Runtime-green.svg)](#the-runtime)
  [![Stack](https://img.shields.io/badge/Stack-React%20|%20FastAPI%20|%20Python-black.svg)](#tech-stack)
</div>

---

## ⬡ The Vision
OSeria is not a character-card workbench. It is a **world-card-centered interactive narrative system**. Built upon the cognitive frameworks of *First Principles*, *The Triad Balance*, and *Occam's Razor*, OSeria bridges abstract architectural visions with a flawless, production-ready generative system.

## ⬡ The Dual-Core Architecture

OSeria separates the cognitive load of World Discovery (0 to 1) from World Delivery (1 to 100). The ecosystem is split into two distinct, sibling modules:

```mermaid
flowchart LR
    U["User"] --> FE["Architect Frontend<br/>React + Vite"]
    FE --> API["Architect API / Service<br/>FastAPI + Session"]
    API --> ST["Architect State Layer"]
    ST --> CP["Architect Compile Layer"]
    CP --> DL["Architect Delivery Layer"]
    DL --> OUT["BlueprintSummary + system_prompt + frozen protagonist identity"]
    OUT -. handoff boundary .-> RT["Runtime Backend / Frontend"]
    RT --> MEM["Runtime Memory Layer<br/>recent summaries + lorebook"]
    RT --> UX["Runtime Chat UX<br/>streaming + world list + state drawer"]
```

### 1. [The Architect](./Architect/)
The world compiler module. It handles socratic interviews, semantic state convergence, compile-layer routing, and frozen Runtime handoffs. Architect transforms vague user intent into a mathematically robust, structurally sound narrative environment.

### 2. [The Runtime](./Runtime/)
The immersive narrative engine. It consumes the Architect's pre-compiled `blueprint`, `system_prompt`, and frozen protagonist constraints, allowing the world to recursively grow during gameplay through short-term summaries and asynchronous `Lorebook` injection logic.

## ⬡ Core Philosophies
- **First Principles**: Pruning entropy. Decoupling understanding from generation.
- **The Triad Balance**: Technical Feasibility, UX Desirability, and Viability.
- **Occam's Razor**: The simplest robust architecture wins. Document drift is an anti-pattern; code is the ultimate source of truth.

## ⬡ Technical Documentation
If you are diving deep into the system, start here:
- **[OSeria Technical Overview](./OSeria_technical_overview.md)**: The definitive boundary documentation between Architect and Runtime.
- **[Architect Implementation Plan](./Architect/docs/implementation_plan.md)**
- **[Runtime Implementation Plan](./Runtime/docs/implementation_plan.md)**

## ⬡ Media & Demos
*(Videos hosted externally due to LFS limits)*
- [OSeria End-to-End Demo] <!-- Add Bilibili/YouTube link here -->
- [Architect Interface Walkthrough] <!-- Add Bilibili/YouTube link here -->

---
<div align="center">
  <i>"True architectural elegance requires aggressively pruning the scaffolding once the bridge is built."</i>
  <br/>
  <b>— Strategic Architect</b>
</div>
