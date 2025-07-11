

import pytest
from models.veo import text_to_video

@pytest.mark.integration
def test_veo_t2v_api_call(gcs_bucket_for_tests):
    """An integration test that calls the real VEO API for text-to-video.
    
    This test is marked as 'integration' and will be skipped unless explicitly
    run with 'pytest -m integration'. It verifies that the application can
    successfully communicate with the live VEO API and receive a valid response.
    """
    # --- Arrange ---
    # Use a simple, reliable prompt that is unlikely to trigger content filters.
    prompt = "a happy dog running on a sunny beach"
    model = "2.0"  # Use the stable Veo 2.0 model for this test
    output_gcs = f"{gcs_bucket_for_tests}/integration_tests"

    # --- Act ---
    # Call the actual text_to_video function, which will make a real API call.
    # This will take some time.
    operation_result = text_to_video(
        model=model,
        prompt=prompt,
        seed=42,
        aspect_ratio="16:9",
        sample_count=1,
        output_gcs=output_gcs,
        enable_pr=False,
        duration_seconds=5,
    )

    # --- Assert ---
    # Verify that the operation completed successfully and returned a valid response.
    assert operation_result is not None, "The API operation result should not be None."
    assert operation_result.get("done"), "The 'done' flag in the operation should be True."
    
    response_data = operation_result.get("response", {})
    assert "videos" in response_data, "The response should contain a 'videos' key."
    
    videos = response_data["videos"]
    assert len(videos) > 0, "The 'videos' list should not be empty."
    
    video_uri = videos[0].get("gcsUri")
    assert video_uri is not None, "The video should have a 'gcsUri'."
    assert video_uri.startswith(output_gcs), f"The video URI should be in the specified output bucket. Got {video_uri}"

    print(f"\nIntegration test PASSED. Video generated successfully at: {video_uri}")

