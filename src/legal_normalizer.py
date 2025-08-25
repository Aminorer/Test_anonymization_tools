"""
Utilities for normalizing French legal entities such as personal names.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from .utils import PARTICLES, get_similarity_threshold, get_similarity_weights


@dataclass
class NormalizedPersonName:
    """Structured representation of a normalized personal name."""

    canonical: str
    first_names: List[str]
    last_name: str
    particles: List[str]


class LegalEntityNormalizer:
    """Normalize and match personal names for legal entities.

    The normalizer strips civil titles, preserves particles as part of the
    last name, and caches results for performance. It also provides simple
    similarity and matching helpers operating on canonicalized forms.
    """

    DEFAULT_TITLES: Set[str] = {
        "m",
        "mr",
        "mme",
        "mlle",
        "dr",
        "me",
        "maitre",
        "maître",
    }

    def __init__(
        self,
        titles: Optional[Iterable[str]] = None,
        particles: Optional[Iterable[str]] = None,
        score_cutoff: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self.titles: Set[str] = (
            {t.strip().lower() for t in titles}
            if titles is not None
            else set(self.DEFAULT_TITLES)
        )
        self.particles: Set[str] = (
            {p.strip().lower() for p in particles}
            if particles is not None
            else set(PARTICLES)
        )
        self.score_cutoff = (
            score_cutoff if score_cutoff is not None else get_similarity_threshold()
        )
        self.weights = weights if weights is not None else get_similarity_weights()

        pattern = r"^(?:%s)\.?\s+" % "|".join(sorted(self.titles))
        self._title_regex = re.compile(pattern, re.IGNORECASE)

        self._cache: Dict[str, NormalizedPersonName] = {}
        self.registry: Dict[str, Set[str]] = {}

    def normalize_person_name(self, name: str) -> NormalizedPersonName:
        """Return the normalized representation of ``name``.

        Parameters
        ----------
        name: str
            Original person name.

        Returns
        -------
        NormalizedPersonName
            Structured data containing the canonical form, first names,
            particles and last name.
        """
        if name in self._cache:
            return self._cache[name]

        working = self._title_regex.sub("", name).strip()
        if not working:
            result = NormalizedPersonName("", [], "", [])
            self._cache[name] = result
            return result

        working = unicodedata.normalize("NFKD", working)
        working = "".join(c for c in working if not unicodedata.combining(c))
        working = working.lower()

        tokens = working.split()
        if not tokens:
            result = NormalizedPersonName("", [], "", [])
            self._cache[name] = result
            return result

        remaining = tokens[:]
        last_parts: List[str] = []
        while remaining:
            token = remaining.pop()
            last_parts.insert(0, token)
            if token in self.particles:
                continue
            while remaining and remaining[-1] in self.particles:
                last_parts.insert(0, remaining.pop())
            break

        first_names = remaining
        last_name = last_parts[-1] if last_parts else ""
        particles = [t for t in last_parts[:-1] if t in self.particles]
        canonical = " ".join(first_names + last_parts)

        result = NormalizedPersonName(
            canonical=canonical,
            first_names=first_names,
            last_name=last_name,
            particles=particles,
        )
        self._cache[name] = result
        return result

    def compute_similarity_score(self, a: str, b: str) -> float:
        """Compute a composite similarity score between two names.

        The score combines three components:
        - Levenshtein ratio on canonical forms
        - Jaccard token overlap
        - Phonetic similarity using a French ``metaphone``-like algorithm

        Individual weights for each component are configurable via
        ``self.weights``. The resulting score is expressed between 0 and 1.
        """

        norm_a = self.normalize_person_name(a).canonical
        norm_b = self.normalize_person_name(b).canonical
        if not norm_a or not norm_b:
            return 0.0

        # Levenshtein ratio
        try:
            from rapidfuzz import fuzz

            lev = fuzz.ratio(norm_a, norm_b) / 100.0
        except ImportError:
            from difflib import SequenceMatcher

            lev = SequenceMatcher(None, norm_a, norm_b).ratio()

        # Jaccard token overlap
        tokens_a = set(norm_a.split())
        tokens_b = set(norm_b.split())
        if tokens_a or tokens_b:
            jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
        else:
            jaccard = 0.0

        # Phonetic similarity
        ph_a = self._metaphone_fr(norm_a)
        ph_b = self._metaphone_fr(norm_b)
        if ph_a and ph_b:
            from difflib import SequenceMatcher

            phonetic = SequenceMatcher(None, ph_a, ph_b).ratio()
        else:
            phonetic = 0.0

        weights = self.weights
        score = (
            weights.get("levenshtein", 0.0) * lev
            + weights.get("jaccard", 0.0) * jaccard
            + weights.get("phonetic", 0.0) * phonetic
        )
        return score

    @staticmethod
    def _metaphone_fr(value: str) -> str:
        """Return a crude French metaphone representation of ``value``."""

        value = unicodedata.normalize("NFKD", value)
        value = "".join(c for c in value if not unicodedata.combining(c))
        value = value.lower()
        value = re.sub(r"[^a-z]", "", value)

        replacements = [
            ("ph", "f"),
            ("th", "t"),
            ("ch", "x"),
            ("sch", "x"),
            ("gn", "n"),
            ("qu", "k"),
            ("ck", "k"),
            ("cq", "k"),
        ]
        for old, new in replacements:
            value = value.replace(old, new)

        if not value:
            return ""
        first = value[0]
        rest = re.sub(r"[aeiouy]", "", value[1:])
        return (first + rest).upper()

    def find_canonical_match(
        self,
        name: str,
        candidates: Optional[Iterable[str]] = None,
    ) -> Optional[NormalizedPersonName]:
        """Find the best canonical match for ``name`` among ``candidates``.

        If ``candidates`` is omitted, registered canonical names are used.
        Returns ``None`` when no candidate exceeds the ``score_cutoff``.
        """
        candidates_iter: Iterable[str] = (
            candidates if candidates is not None else self.registry.keys()
        )
        best_score = 0.0
        best_candidate: Optional[str] = None
        for candidate in candidates_iter:
            score = self.compute_similarity_score(name, candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate and best_score >= self.score_cutoff:
            return self.normalize_person_name(best_candidate)
        return None

    def register_entity_variant(self, canonical: str, variant: str) -> None:
        """Register ``variant`` as a form of ``canonical`` name.

        The method stores the original ``variant`` under the canonical key and
        caches its normalized representation for faster future lookups.
        """
        key = self.normalize_person_name(canonical).canonical
        self.registry.setdefault(key, set()).add(variant)
        self.normalize_person_name(variant)
