"""Entity resolution module for research worker."""

import difflib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EntityResolver:
    """Resolve and merge duplicate entities."""

    # Relationship ontology mapping
    RELATIONSHIP_ALIASES = {
        "spouse": ["wife", "husband", "partner", "married_to", "wife_of", "husband_of", "spouse_of"],
        "parent": ["mother", "father", "parent_of"],
        "child": ["son", "daughter", "child_of"],
        "sibling": ["brother", "sister", "brother_of", "sister_of", "sibling_of"],
        "friend": ["friend_of", "friends_with"],
        "partner": ["business_partner", "crime_partner", "partner_in_crime"],
        "employer": ["boss", "employer_of"],
        "employee": ["worker", "staff", "employee_of", "works_for"],
        "enemy": ["rival", "opponent", "enemy_of", "rival_of"],
        "relative": ["family", "relative_of", "family_member"],
        "colleague": ["coworker", "coworker_of", "colleague_of"],
        "associate": ["acquaintance", "associate_of", "acquaintance_of"],
    }

    def __init__(self, similarity_threshold: float = 0.85):
        """Initialize entity resolver.

        Args:
            similarity_threshold: Threshold for considering entities as the same.
        """
        self.similarity_threshold = similarity_threshold

    def normalize_name(self, name: str) -> str:
        """Normalize a name for comparison.

        Args:
            name: Name to normalize.

        Returns:
            str: Normalized name.
        """
        if not name:
            return ""

        # Lowercase and strip
        normalized = name.lower().strip()

        # Remove common titles
        for title in ["mr.", "mrs.", "ms.", "dr.", "prof.", "capt.", "det.", "agent"]:
            normalized = normalized.replace(title, "")

        # Remove extra whitespace
        normalized = " ".join(normalized.split())

        return normalized

    def compute_name_similarity(self, name1: str, name2: str) -> float:
        """Compute similarity between two names.

        Args:
            name1: First name.
            name2: Second name.

        Returns:
            float: Similarity score (0.0 to 1.0).
        """
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)

        if norm1 == norm2:
            return 1.0

        # Use sequence matcher
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()

        # Check if one is a substring of the other
        if norm1 in norm2 or norm2 in norm1:
            similarity = max(similarity, 0.8)

        return similarity

    def compute_character_similarity(
        self,
        char1: dict,
        char2: dict,
    ) -> float:
        """Compute similarity between two characters.

        Args:
            char1: First character data.
            char2: Second character data.

        Returns:
            float: Similarity score (0.0 to 1.0).
        """
        scores = []

        # Name similarity
        name1 = char1.get("canonical_name", "")
        name2 = char2.get("canonical_name", "")
        if name1 and name2:
            name_sim = self.compute_name_similarity(name1, name2)
            scores.append(("name", name_sim))

        # Actor match
        actor1 = char1.get("actor_id")
        actor2 = char2.get("actor_id")
        if actor1 and actor2:
            actor_sim = 1.0 if actor1 == actor2 else 0.0
            scores.append(("actor", actor_sim))

        # TMDB ID match
        tmdb1 = char1.get("tmdb_id")
        tmdb2 = char2.get("tmdb_id")
        if tmdb1 and tmdb2:
            tmdb_sim = 1.0 if tmdb1 == tmdb2 else 0.0
            scores.append(("tmdb_id", tmdb_sim))

        # Wikidata ID match
        wikidata1 = char1.get("wikidata_id")
        wikidata2 = char2.get("wikidata_id")
        if wikidata1 and wikidata2:
            wikidata_sim = 1.0 if wikidata1 == wikidata2 else 0.0
            scores.append(("wikidata_id", wikidata_sim))

        # Check aliases
        aliases1 = set(char1.get("aliases", []))
        aliases2 = set(char2.get("aliases", []))
        if aliases1 and aliases2:
            alias_sim = len(aliases1 & aliases2) / max(len(aliases1), len(aliases2))
            scores.append(("aliases", alias_sim))

        # Weighted average
        weights = {
            "tmdb_id": 1.0,
            "wikidata_id": 1.0,
            "actor": 0.95,
            "name": 0.9,
            "aliases": 0.8,
        }

        if not scores:
            return 0.0

        weighted_sum = sum(score * weights.get(label, 0.5) for label, score in scores)
        total_weight = sum(weights.get(label, 0.5) for label, _ in scores)

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def resolve_characters(
        self,
        characters: list[dict],
    ) -> tuple[list[dict], list[tuple[str, str, float]]]:
        """Resolve duplicate characters.

        Args:
            characters: List of characters to resolve.

        Returns:
            tuple: (resolved_characters, merge_pairs)
        """
        if not characters:
            return [], []

        # Sort by ID to ensure deterministic results
        sorted_chars = sorted(characters, key=lambda c: c.get("id", ""))

        resolved: list[dict] = []
        merged_pairs: list[tuple[str, str, float]] = []

        for char in sorted_chars:
            char_id = char.get("id")

            # Check for matches in resolved
            merged = False
            for i, resolved_char in enumerate(resolved):
                similarity = self.compute_character_similarity(char, resolved_char)

                if similarity >= self.similarity_threshold:
                    # Merge into existing character
                    self._merge_characters(resolved_char, char, similarity)
                    merged_pairs.append((char_id, resolved_char.get("id"), similarity))
                    merged = True
                    break

            if not merged:
                resolved.append(char.copy())

        return resolved, merged_pairs

    def _merge_characters(
        self,
        target: dict,
        source: dict,
        similarity: float,
    ) -> None:
        """Merge source character into target.

        Args:
            target: Target character (modified in-place).
            source: Source character.
            similarity: Similarity score.
        """
        # Merge aliases
        target_aliases = set(target.get("aliases", []))
        source_aliases = set(source.get("aliases", []))
        target["aliases"] = list(target_aliases | source_aliases)

        # Use highest confidence
        target["confidence"] = max(target.get("confidence", 0.0), source.get("confidence", 0.0))

        # Prefer non-null values
        for key in ["actor_id", "tmdb_id", "wikidata_id", "description"]:
            target_val = target.get(key)
            source_val = source.get(key)
            if source_val and not target_val:
                target[key] = source_val

        # Store merge info
        if "merged_from" not in target:
            target["merged_from"] = []
        target["merged_from"].append({
            "id": source.get("id"),
            "similarity": similarity,
        })

    def normalize_relationship(self, relation: str) -> str:
        """Normalize relationship to canonical form.

        Args:
            relation: Relationship string.

        Returns:
            str: Canonical relationship type.
        """
        relation_lower = relation.lower().strip()

        # Check each canonical relationship
        for canonical, aliases in self.RELATIONSHIP_ALIASES.items():
            if relation_lower == canonical:
                return canonical
            if relation_lower in aliases:
                return canonical

        # Return original if not found
        return relation

    def resolve_relationships(
        self,
        relationships: list[dict],
        character_map: dict[str, str],
    ) -> list[dict]:
        """Resolve and normalize relationships.

        Args:
            relationships: List of relationships.
            character_map: Mapping from old character IDs to new IDs.

        Returns:
            list: Resolved relationships.
        """
        resolved: list[dict] = []

        for rel in relationships:
            subject = rel.get("subject")
            object = rel.get("object")
            relation = self.normalize_relationship(rel.get("relation", ""))

            # Map character IDs
            new_subject = character_map.get(subject, subject)
            new_object = character_map.get(object, object)

            if not new_subject or not new_object or not relation:
                continue

            resolved.append({
                "subject": new_subject,
                "relation": relation,
                "object": new_object,
                "confidence": rel.get("confidence", 0.8),
                "evidence": rel.get("evidence", []),
            })

        # Remove duplicates
        seen = set()
        unique: list[dict] = []

        for rel in resolved:
            key = (rel["subject"], rel["relation"], rel["object"])
            if key not in seen:
                seen.add(key)
                unique.append(rel)

        return unique

    def detect_conflicts(
        self,
        characters: list[dict],
        relationships: list[dict],
    ) -> list[dict]:
        """Detect conflicts in entity data.

        Args:
            characters: List of characters.
            relationships: List of relationships.

        Returns:
            list: Detected conflicts.
        """
        conflicts: list[dict] = []

        # Check for character-actor conflicts
        char_actor_map: dict[str, dict] = {}
        for char in characters:
            char_name = char.get("canonical_name")
            actor_id = char.get("actor_id")

            if char_name and actor_id:
                if char_name in char_actor_map:
                    if char_actor_map[char_name]["actor_id"] != actor_id:
                        conflicts.append({
                            "type": "character_actor_mismatch",
                            "character": char_name,
                            "actor_1": char_actor_map[char_name]["actor_id"],
                            "actor_2": actor_id,
                            "severity": "high",
                        })
                else:
                    char_actor_map[char_name] = {"actor_id": actor_id}

        # Check for contradictory relationships
        rel_pairs: dict[tuple[str, str], list[str]] = {}
        for rel in relationships:
            subject = rel.get("subject")
            obj = rel.get("object")
            relation = rel.get("relation")

            if subject and obj:
                key = (subject, obj)
                if key not in rel_pairs:
                    rel_pairs[key] = []
                rel_pairs[key].append(relation)

        # Check for contradictions
        contradictions = {
            ("spouse", "parent"),
            ("spouse", "child"),
            ("parent", "child"),
            ("friend", "enemy"),
        }

        for (subj, obj), relations in rel_pairs.items():
            for rel1, rel2 in contradictions:
                if rel1 in relations and rel2 in relations:
                    conflicts.append({
                        "type": "contradictory_relationship",
                        "subject": subj,
                        "object": obj,
                        "relations": relations,
                        "severity": "high",
                    })

        return conflicts


# Factory function
def get_entity_resolver(similarity_threshold: float = 0.85) -> EntityResolver:
    """Get an entity resolver instance.

    Args:
        similarity_threshold: Threshold for considering entities as the same.

    Returns:
        EntityResolver: Resolver instance.
    """
    return EntityResolver(similarity_threshold)
