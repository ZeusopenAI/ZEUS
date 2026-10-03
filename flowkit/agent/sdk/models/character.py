"""SDK Character domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from agent.sdk.models.base import DomainModel

if TYPE_CHECKING:
    from agent.sdk.models.project import Project
    from agent.sdk.models.media import GenerationResult


@dataclass
class Character(DomainModel):
    """A reference entity (character, location, creature, visual_asset, etc.)."""

    _table: str = field(default="character", init=False, repr=False, compare=False)

    name: str = ""
    slug: Optional[str] = None
    entity_type: str = "character"
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    voice_description: Optional[str] = None
    reference_image_url: Optional[str] = None
    media_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Back-reference set after construction
    _project: Optional[Project] = field(default=None, repr=False, compare=False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_operation_dict(self, project_id: str) -> dict:
        """Convert to the dict that OperationService direct methods expect."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "entity_type": self.entity_type,
            "description": self.description,
            "image_prompt": self.image_prompt,
            "voice_description": self.voice_description,
            "reference_image_url": self.reference_image_url,
            "media_id": self.media_id,
        }

    # ------------------------------------------------------------------
    # Queue-based generation (returns request_id)
    # ------------------------------------------------------------------

    async def generate_image(self, *, project_id: Optional[str] = None) -> str:
        """Submit a GENERATE_CHARACTER_IMAGE request. Returns the request id."""
        from agent.sdk.services.operations import get_operations

        pid = project_id or (self._project.id if self._project else None)
        if not pid:
            raise ValueError("project_id required (not attached to a project)")
        ops = get_operations()
        return await ops.generate_character_image(
            character_id=self.id,
            project_id=pid,
        )

    async def edit_image(
        self,
        edit_prompt: str,
        *,
        project_id: Optional[str] = None,
        source_media_id: Optional[str] = None,
    ) -> str:
        """Submit an EDIT_IMAGE request for this entity. Returns the request id."""
        from agent.sdk.services.operations import get_operations

        pid = project_id or (self._project.id if self._project else None)
        if not pid:
            raise ValueError("project_id required (not attached to a project)")
        ops = get_operations()
        return await ops.edit_character_image(
            character_id=self.id,
            project_id=pid,
            edit_prompt=edit_prompt,
            source_media_id=source_media_id or self.media_id,
        )

    # ------------------------------------------------------------------
    # Direct execution (calls FlowClient directly, returns result)
    # ------------------------------------------------------------------

    async def execute_generate_image(
        self, *, project_id: Optional[str] = None
    ) -> "GenerationResult":
        """Generate reference image directly (blocking). Returns GenerationResult."""
        from agent.sdk.models.media import GenerationResult
        from agent.sdk.services.operations import get_operations
        from agent.sdk.services.result_handler import parse_result, apply_character_result

        pid = project_id or (self._project.id if self._project else None)
        if not pid:
            raise ValueError("project_id required (not attached to a project)")
        ops = get_operations()
        raw = await ops.generate_reference_image(self.to_operation_dict(pid), pid)
        result = parse_result(raw, "GENERATE_CHARACTER_IMAGE")
        if result.success:
            await apply_character_result(self.id, result)
            self.media_id = result.media_id
            if result.url:
                self.reference_image_url = result.url
        return result

    async def execute_edit_image(
        self,
        edit_prompt: str,
        *,
        project_id: Optional[str] = None,
        source_media_id: Optional[str] = None,
    ) -> "GenerationResult":
        """Edit character reference image directly (blocking). Returns GenerationResult."""
        from agent.sdk.models.media import GenerationResult
        from agent.sdk.services.operations import get_operations
        from agent.sdk.services.result_handler import parse_result, apply_character_result

        pid = project_id or (self._project.id if self._project else None)
        if not pid:
            raise ValueError("project_id required (not attached to a project)")
        src = source_media_id or self.media_id
        if not src:
            raise ValueError("No source image to edit — generate a reference image first")
        ops = get_operations()
        char_dict = self.to_operation_dict(pid)
        char_dict["_project_id"] = pid
        char_dict["image_prompt"] = edit_prompt
        raw = await ops.edit_scene_image(char_dict, "VERTICAL", source_media_id=src)
        result = parse_result(raw, "EDIT_IMAGE")
        if result.success:
            await apply_character_result(self.id, result)
            self.media_id = result.media_id
            if result.url:
                self.reference_image_url = result.url
        return result
