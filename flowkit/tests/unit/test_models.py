"""Unit tests for SDK domain models: media, scene, character."""

import json
import pytest

from agent.sdk.models.media import GenerationResult, MediaAsset, OrientationSlot, MediaStatus
from agent.sdk.models.scene import Scene
from agent.sdk.models.character import Character


# ---------------------------------------------------------------------------
# GenerationResult
# ---------------------------------------------------------------------------

class TestGenerationResult:
    def test_success_construction(self, sample_uuid):
        result = GenerationResult(
            success=True,
            media_id=sample_uuid,
            url="https://example.com/image.jpg",
        )
        assert result.success is True
        assert result.media_id == sample_uuid
        assert result.url == "https://example.com/image.jpg"
        assert result.error is None

    def test_error_construction(self):
        result = GenerationResult(
            success=False,
            error="caller does not have permission",
        )
        assert result.success is False
        assert result.media_id is None
        assert result.url is None
        assert result.error == "caller does not have permission"

    def test_raw_field_excluded_from_repr(self, sample_uuid):
        result = GenerationResult(success=True, media_id=sample_uuid, raw={"huge": "payload"})
        assert "raw" not in repr(result)


# ---------------------------------------------------------------------------
# MediaAsset.ready
# ---------------------------------------------------------------------------

class TestMediaAssetReady:
    def test_ready_when_completed_with_media_id(self, sample_uuid):
        asset = MediaAsset(media_id=sample_uuid, status="COMPLETED")
        assert asset.ready is True

    def test_not_ready_when_pending(self, sample_uuid):
        asset = MediaAsset(media_id=sample_uuid, status="PENDING")
        assert asset.ready is False

    def test_not_ready_when_processing(self, sample_uuid):
        asset = MediaAsset(media_id=sample_uuid, status="PROCESSING")
        assert asset.ready is False

    def test_not_ready_when_completed_but_no_media_id(self):
        asset = MediaAsset(media_id=None, status="COMPLETED")
        assert asset.ready is False

    def test_not_ready_when_failed(self, sample_uuid):
        asset = MediaAsset(media_id=sample_uuid, status="FAILED")
        assert asset.ready is False


# ---------------------------------------------------------------------------
# OrientationSlot default construction
# ---------------------------------------------------------------------------

class TestOrientationSlotDefaults:
    def test_default_construction_all_pending(self):
        slot = OrientationSlot()
        assert slot.image.status == "PENDING"
        assert slot.video.status == "PENDING"
        assert slot.upscale.status == "PENDING"

    def test_default_construction_no_media_ids(self):
        slot = OrientationSlot()
        assert slot.image.media_id is None
        assert slot.video.media_id is None
        assert slot.upscale.media_id is None
        assert slot.end_scene_media_id is None

    def test_slots_are_independent_instances(self):
        slot1 = OrientationSlot()
        slot2 = OrientationSlot()
        slot1.image.media_id = "some-id"
        assert slot2.image.media_id is None


# ---------------------------------------------------------------------------
# Scene.from_row
# ---------------------------------------------------------------------------

class TestSceneFromRow:
    def test_inflates_flat_row_into_scene(self, sample_scene_row, sample_uuid):
        scene = Scene.from_row(sample_scene_row)
        assert scene.id == "scene-001"
        assert scene.video_id == "video-001"
        assert scene.display_order == 0
        assert scene.prompt == "Hero walks into the castle courtyard at dawn"
        assert scene.chain_type == "ROOT"

    def test_inflates_vertical_orientation_slot(self, sample_scene_row, sample_uuid):
        scene = Scene.from_row(sample_scene_row)
        assert scene.vertical.image.media_id == sample_uuid
        assert scene.vertical.image.status == "COMPLETED"
        assert scene.vertical.video.status == "PENDING"
        assert scene.vertical.video.media_id is None

    def test_inflates_horizontal_orientation_slot(self, sample_scene_row):
        scene = Scene.from_row(sample_scene_row)
        assert scene.horizontal.image.status == "PENDING"
        assert scene.horizontal.image.media_id is None

    def test_parses_json_character_names_string(self, sample_scene_row):
        scene = Scene.from_row(sample_scene_row)
        assert scene.character_names == ["Hero", "Castle"]

    def test_handles_null_character_names(self, sample_scene_row):
        row = dict(sample_scene_row, character_names=None)
        scene = Scene.from_row(row)
        assert scene.character_names is None

    def test_handles_invalid_json_character_names(self, sample_scene_row):
        row = dict(sample_scene_row, character_names="not-valid-json")
        scene = Scene.from_row(row)
        assert scene.character_names is None


# ---------------------------------------------------------------------------
# Scene.to_operation_dict
# ---------------------------------------------------------------------------

class TestSceneToOperationDict:
    def test_produces_flat_dict_with_project_id(self, sample_scene_row):
        scene = Scene.from_row(sample_scene_row)
        d = scene.to_operation_dict("proj-123")
        assert d["_project_id"] == "proj-123"
        assert d["id"] == "scene-001"
        assert d["video_id"] == "video-001"

    def test_includes_all_orientation_fields(self, sample_scene_row, sample_uuid):
        scene = Scene.from_row(sample_scene_row)
        d = scene.to_operation_dict("proj-123")
        assert d["vertical_image_media_id"] == sample_uuid
        assert d["vertical_image_status"] == "COMPLETED"
        assert d["vertical_video_media_id"] is None
        assert d["horizontal_image_status"] == "PENDING"
        assert "vertical_end_scene_media_id" in d
        assert "horizontal_end_scene_media_id" in d

    def test_character_names_list_serialized_to_json_string(self, sample_scene_row):
        scene = Scene.from_row(sample_scene_row)
        d = scene.to_operation_dict("proj-123")
        assert isinstance(d["character_names"], str)
        assert json.loads(d["character_names"]) == ["Hero", "Castle"]

    def test_none_character_names_stays_none(self, sample_scene_row):
        row = dict(sample_scene_row, character_names=None)
        scene = Scene.from_row(row)
        d = scene.to_operation_dict("proj-123")
        assert d["character_names"] is None

    def test_roundtrip_from_row_to_operation_dict(self, sample_scene_row, sample_uuid):
        scene = Scene.from_row(sample_scene_row)
        d = scene.to_operation_dict("proj-999")
        assert d["id"] == sample_scene_row["id"]
        assert d["video_id"] == sample_scene_row["video_id"]
        assert d["prompt"] == sample_scene_row["prompt"]
        assert d["chain_type"] == sample_scene_row["chain_type"]
        assert d["vertical_image_media_id"] == sample_uuid
        assert d["_project_id"] == "proj-999"


# ---------------------------------------------------------------------------
# Character.to_operation_dict
# ---------------------------------------------------------------------------

class TestCharacterToOperationDict:
    def test_includes_all_character_fields(self, sample_character_row, sample_uuid):
        char = Character(
            id=sample_character_row["id"],
            name=sample_character_row["name"],
            entity_type=sample_character_row["entity_type"],
            description=sample_character_row["description"],
            image_prompt=sample_character_row["image_prompt"],
            voice_description=sample_character_row["voice_description"],
            reference_image_url=sample_character_row["reference_image_url"],
            media_id=sample_character_row["media_id"],
        )
        d = char.to_operation_dict("proj-123")
        assert d["id"] == "char-001"
        assert d["name"] == "Hero"
        assert d["entity_type"] == "character"
        assert d["description"] == sample_character_row["description"]
        assert d["image_prompt"] == sample_character_row["image_prompt"]
        assert d["voice_description"] == "Deep calm heroic voice"
        assert d["media_id"] == sample_uuid

    def test_handles_none_optional_fields(self):
        char = Character(id="char-002", name="Unnamed")
        d = char.to_operation_dict("proj-123")
        assert d["description"] is None
        assert d["image_prompt"] is None
        assert d["voice_description"] is None
        assert d["reference_image_url"] is None
        assert d["media_id"] is None

    def test_project_id_not_in_dict(self):
        # to_operation_dict takes project_id as arg but doesn't include it in the dict
        char = Character(id="char-003", name="Test")
        d = char.to_operation_dict("proj-123")
        assert "_project_id" not in d
