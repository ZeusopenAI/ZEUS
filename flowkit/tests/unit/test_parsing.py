"""Unit tests for agent/worker/_parsing.py — pure functions, no mocking needed."""

import pytest

from agent.worker._parsing import (
    _is_error,
    _is_uuid,
    _extract_uuid_from_url,
    _extract_media_id,
    _extract_output_url,
)


# ---------------------------------------------------------------------------
# _is_error
# ---------------------------------------------------------------------------

class TestIsError:
    def test_top_level_error_key(self, sample_error_response):
        assert _is_error(sample_error_response) is True

    def test_nested_data_error(self, sample_nested_error):
        assert _is_error(sample_nested_error) is True

    def test_status_400(self):
        assert _is_error({"status": 400}) is True

    def test_status_500(self):
        assert _is_error({"status": 500}) is True

    def test_status_200_is_not_error(self):
        assert _is_error({"status": 200, "data": {}}) is False

    def test_success_response_is_not_error(self, sample_image_success):
        assert _is_error(sample_image_success) is False

    def test_empty_dict_is_not_error(self):
        assert _is_error({}) is False


# ---------------------------------------------------------------------------
# _is_uuid
# ---------------------------------------------------------------------------

class TestIsUuid:
    def test_valid_uuid(self, sample_uuid):
        assert _is_uuid(sample_uuid) is True

    def test_valid_uuid_uppercase(self):
        assert _is_uuid("550E8400-E29B-41D4-A716-446655440000") is True

    def test_cams_string_is_not_uuid(self, sample_cams_id):
        assert _is_uuid(sample_cams_id) is False

    def test_empty_string(self):
        assert _is_uuid("") is False

    def test_plain_string(self):
        assert _is_uuid("not-a-uuid") is False

    def test_uuid_without_dashes(self):
        assert _is_uuid("550e8400e29b41d4a716446655440000") is False


# ---------------------------------------------------------------------------
# _extract_uuid_from_url
# ---------------------------------------------------------------------------

class TestExtractUuidFromUrl:
    def test_extract_from_fife_url(self, sample_uuid):
        url = f"https://lh3.googleusercontent.com/image/{sample_uuid}?sqp=params"
        assert _extract_uuid_from_url(url) == sample_uuid

    def test_extract_from_storage_url(self, sample_uuid):
        url = f"https://storage.googleapis.com/video/{sample_uuid}"
        assert _extract_uuid_from_url(url) == sample_uuid

    def test_no_uuid_in_url(self):
        assert _extract_uuid_from_url("https://example.com/no/uuid/here") == ""

    def test_empty_string(self):
        assert _extract_uuid_from_url("") == ""

    def test_cams_url_no_uuid(self, sample_cams_id):
        url = f"https://example.com/media/{sample_cams_id}"
        assert _extract_uuid_from_url(url) == ""


# ---------------------------------------------------------------------------
# _extract_media_id
# ---------------------------------------------------------------------------

class TestExtractMediaId:
    def test_generate_image_with_uuid_name(self, sample_image_success, sample_uuid):
        result = _extract_media_id(sample_image_success, "GENERATE_IMAGE")
        assert result == sample_uuid

    def test_generate_image_cams_name_falls_back_to_url(self, sample_image_success_no_uuid):
        result = _extract_media_id(sample_image_success_no_uuid, "GENERATE_IMAGE")
        assert result == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    def test_edit_image_same_as_generate_image(self, sample_image_success, sample_uuid):
        result = _extract_media_id(sample_image_success, "EDIT_IMAGE")
        assert result == sample_uuid

    def test_generate_video_extracts_from_operations(self, sample_video_success, sample_uuid):
        result = _extract_media_id(sample_video_success, "GENERATE_VIDEO")
        assert result == sample_uuid

    def test_generate_video_refs(self, sample_video_success, sample_uuid):
        result = _extract_media_id(sample_video_success, "GENERATE_VIDEO_REFS")
        assert result == sample_uuid

    def test_upscale_video(self, sample_video_success, sample_uuid):
        result = _extract_media_id(sample_video_success, "UPSCALE_VIDEO")
        assert result == sample_uuid

    def test_empty_response_returns_none(self):
        assert _extract_media_id({}, "GENERATE_IMAGE") is None

    def test_unknown_req_type_returns_none(self, sample_image_success):
        assert _extract_media_id(sample_image_success, "UNKNOWN_TYPE") is None


# ---------------------------------------------------------------------------
# _extract_output_url
# ---------------------------------------------------------------------------

class TestExtractOutputUrl:
    def test_image_fife_url(self, sample_image_success, sample_uuid):
        url = _extract_output_url(sample_image_success, "GENERATE_IMAGE")
        assert url == f"https://lh3.googleusercontent.com/image/{sample_uuid}?sqp=params"

    def test_video_fife_url(self, sample_video_success, sample_uuid):
        url = _extract_output_url(sample_video_success, "GENERATE_VIDEO")
        assert url == f"https://storage.googleapis.com/video/{sample_uuid}"

    def test_fallback_to_video_uri(self):
        result = {"videoUri": "https://example.com/video.mp4"}
        assert _extract_output_url(result, "UNKNOWN") == "https://example.com/video.mp4"

    def test_fallback_to_image_uri(self):
        result = {"imageUri": "https://example.com/image.jpg"}
        assert _extract_output_url(result, "UNKNOWN") == "https://example.com/image.jpg"

    def test_empty_response_returns_empty_string(self):
        assert _extract_output_url({}, "GENERATE_IMAGE") == ""
