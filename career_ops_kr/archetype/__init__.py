"""Archetype classifier — classifies Korean finance/tech jobs into buckets.

Exports:
    ArchetypeClassifier: main classifier
    Archetype: enum (BLOCKCHAIN / DIGITAL_ASSET / FINANCIAL_IT / RESEARCH /
                     FINTECH_PRODUCT / PUBLIC_FINANCE / CERTIFICATION / UNKNOWN)
"""

from __future__ import annotations

from career_ops_kr.archetype.classifier import Archetype, ArchetypeClassifier

__all__ = ["Archetype", "ArchetypeClassifier"]
