"""Verification module for research worker."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResearchVerifier:
    """Verify research results."""

    def __init__(self):
        """Initialize research verifier."""
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def verify_manifest(self, manifest: dict) -> dict:
        """Verify research manifest.

        Args:
            manifest: Research manifest to verify.

        Returns:
            dict: Verification result.
        """
        self.warnings = []
        self.errors = []

        # Check required fields
        self._check_required_fields(manifest)

        # Check confidence levels
        self._check_confidence(manifest)

        # Check data consistency
        self._check_consistency(manifest)

        # Check evidence coverage
        self._check_evidence(manifest)

        # Determine overall status
        if self.errors:
            status = "FAILED"
        elif self.warnings:
            status = "SUCCESS_WITH_WARNINGS"
        else:
            status = "SUCCESS"

        return {
            "status": status,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }

    def _check_required_fields(self, manifest: dict) -> None:
        """Check for required fields in manifest.

        Args:
            manifest: Manifest to check.
        """
        required_fields = [
            "schema_version",
            "project",
            "confidence",
        ]

        for field in required_fields:
            if field not in manifest:
                self.errors.append(f"Missing required field: {field}")

        # Check project fields
        if "project" in manifest:
            project = manifest["project"]
            project_required = ["id", "title"]
            for field in project_required:
                if field not in project:
                    self.errors.append(f"Missing required project field: {field}")

    def _check_confidence(self, manifest: dict) -> None:
        """Check confidence levels.

        Args:
            manifest: Manifest to check.
        """
        confidence = manifest.get("confidence", {})

        # Check project confidence
        project_conf = confidence.get("project", 0.0)
        if project_conf < 0.7:
            self.warnings.append(f"Low project confidence: {project_conf:.2f}")
        elif project_conf < 0.5:
            self.errors.append(f"Very low project confidence: {project_conf:.2f}")

        # Check episode confidence
        if "episode" in manifest:
            episode_conf = confidence.get("episode", 0.0)
            if episode_conf < 0.7:
                self.warnings.append(f"Low episode confidence: {episode_conf:.2f}")

    def _check_consistency(self, manifest: dict) -> None:
        """Check data consistency.

        Args:
            manifest: Manifest to check.
        """
        characters = manifest.get("characters", [])
        actors = manifest.get("actors", [])

        # Check for characters without actors
        chars_no_actor = [c for c in characters if not c.get("actor_id")]
        if chars_no_actor:
            self.warnings.append(f"{len(chars_no_actor)} characters without actors")

        # Check for orphaned actors (actors not linked to characters)
        actor_ids = {c.get("actor_id") for c in characters if c.get("actor_id")}
        manifest_actor_ids = {a.get("id") for a in actors}
        orphaned_actors = manifest_actor_ids - actor_ids

        if orphaned_actors:
            self.warnings.append(f"{len(orphaned_actors)} actors not linked to characters")

        # Check relationships
        relationships = manifest.get("relationships", [])
        char_ids = {c.get("id") for c in characters}

        for rel in relationships:
            subject = rel.get("subject")
            obj = rel.get("object")

            if subject and subject not in char_ids:
                self.warnings.append(f"Relationship subject not found: {subject}")

            if obj and obj not in char_ids:
                self.warnings.append(f"Relationship object not found: {obj}")

    def _check_evidence(self, manifest: dict) -> None:
        """Check evidence coverage.

        Args:
            manifest: Manifest to check.
        """
        characters = manifest.get("characters", [])

        # Check characters without evidence
        chars_no_evidence = [
            c for c in characters
            if not c.get("evidence") or len(c.get("evidence", [])) == 0
        ]

        if chars_no_evidence:
            self.warnings.append(f"{len(chars_no_evidence)} characters without evidence")

        # Check sources
        sources = manifest.get("sources", [])
        if len(sources) == 0:
            self.errors.append("No sources found in manifest")
        elif len(sources) < 2:
            self.warnings.append("Only one source found, consider adding more sources")

    def verify_entity(
        self,
        entity_type: str,
        entity: dict,
        min_confidence: float = 0.7,
    ) -> dict:
        """Verify a single entity.

        Args:
            entity_type: Type of entity (character, actor, etc.).
            entity: Entity data.
            min_confidence: Minimum confidence threshold.

        Returns:
            dict: Verification result.
        """
        errors = []
        warnings = []

        # Check required fields
        if "id" not in entity:
            errors.append(f"{entity_type}: Missing ID")

        if entity_type == "character":
            if "canonical_name" not in entity:
                errors.append(f"{entity_type}: Missing canonical_name")

            # Check confidence
            confidence = entity.get("confidence", 0.0)
            if confidence < min_confidence:
                warnings.append(f"{entity_type} {entity.get('canonical_name')}: Low confidence {confidence:.2f}")

            # Check evidence
            if not entity.get("evidence") or len(entity.get("evidence", [])) == 0:
                warnings.append(f"{entity_type} {entity.get('canonical_name')}: No evidence")

        elif entity_type == "actor":
            if "canonical_name" not in entity:
                errors.append(f"{entity_type}: Missing canonical_name")

            confidence = entity.get("confidence", 0.0)
            if confidence < min_confidence:
                warnings.append(f"{entity_type} {entity.get('canonical_name')}: Low confidence {confidence:.2f}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def verify_relationship(self, relationship: dict, characters: list[dict]) -> dict:
        """Verify a relationship.

        Args:
            relationship: Relationship data.
            characters: List of valid characters.

        Returns:
            dict: Verification result.
        """
        errors = []
        warnings = []

        char_ids = {c.get("id") for c in characters}

        subject = relationship.get("subject")
        obj = relationship.get("object")
        relation = relationship.get("relation")

        if not subject:
            errors.append("Relationship: Missing subject")
        elif subject not in char_ids:
            warnings.append(f"Relationship: Subject {subject} not found")

        if not obj:
            errors.append("Relationship: Missing object")
        elif obj not in char_ids:
            warnings.append(f"Relationship: Object {obj} not found")

        if not relation:
            errors.append("Relationship: Missing relation type")

        # Check for self-relationship
        if subject == obj:
            warnings.append(f"Relationship: Self-relation ({subject} {relation} {subject})")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# Factory function
def get_research_verifier() -> ResearchVerifier:
    """Get a research verifier instance.

    Returns:
        ResearchVerifier: Verifier instance.
    """
    return ResearchVerifier()
