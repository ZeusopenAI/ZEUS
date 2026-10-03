"""Media resolver — resolves character names to media_ids for imageInputs."""

import logging

logger = logging.getLogger(__name__)


def resolve_references(character_names: list[str], project_chars: list[dict]) -> list[str]:
    """Resolve a list of character names to their UUID media_ids.

    Args:
        character_names: Names of characters/entities to resolve.
        project_chars: List of character dicts from the project (each must have 'name' and 'media_id').

    Returns:
        List of UUID media_ids for characters that have them.

    Raises:
        ValueError: If any named character is missing its media_id (ref image not generated yet).
    """
    if not character_names:
        return []

    name_set = set(character_names)
    valid_ids: list[str] = []
    missing_refs: list[str] = []

    for char in project_chars:
        slug = char.get("slug") or ""
        name = char.get("name", "")
        if not ((slug and slug in name_set) or (name and name in name_set)):
            continue
        mid = char.get("media_id")
        if mid:
            valid_ids.append(mid)
        else:
            missing_refs.append(slug or name)

    if missing_refs:
        raise ValueError(f"Waiting for reference images: {', '.join(missing_refs)}")

    return valid_ids
