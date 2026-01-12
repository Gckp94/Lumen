# 1. Introduction

## Purpose & Scope

This document defines the technical architecture for **Lumen**, a desktop application for trading data analysis. It provides implementation-level guidance for developers and AI agents, covering system design, component specifications, data models, workflows, and coding standards.

## Document Conventions

- **Code blocks** contain implementation-ready examples
- **Tables** summarize specifications and mappings
- **Diagrams** use ASCII art for portability
- **Cross-references** link to PRD (docs/prd.md) and Front-End Spec (docs/front-end-spec.md)

## Relationship to Other Documents

| Document | Purpose | Authority |
|----------|---------|-----------|
| PRD (docs/prd.md) | Requirements, user stories, acceptance criteria | What to build |
| Front-End Spec (docs/front-end-spec.md) | UX design, visual specifications, animations | How it looks |
| Architecture (this document) | Technical design, implementation patterns | How to build it |

**Note:** Where PRD and Front-End Spec differ (e.g., directory structure, fonts), this architecture document is authoritative for implementation.

## Revision History

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-09 | 1.0 | Initial architecture | Winston (Architect) |

---
