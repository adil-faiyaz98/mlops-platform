# /project_root/tests/utils/test_config.py

import pytest
import os
from src.utils.config import Config

def test_config_defaults(monkeypatch): #Use monkey patch since you can't reset the config.
    # Clear environment variables to test default values
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.delenv("FEATURE_NAMES", raising=False)
    monkeypatch.delenv("TARGET_VARIABLE", raising=False)
    config = Config()

    assert config.aws_region == "us-east-1"
    assert config.s3_bucket == "your-s3-bucket-name"
    assert config.feature_names == ["feature1", "feature2", "feature3"]
    assert config.target_variable == "target"

def test_config_environment_variables(monkeypatch): # Reset Env Var
    # Set environment variables for testing
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("FEATURE_NAMES", "a,b,c")
    monkeypatch.setenv("TARGET_VARIABLE", "new_target")

    config = Config()

    assert config.aws_region == "us-west-2"
    assert config.s3_bucket == "test-bucket"
    assert config.feature_names == ["a", "b", "c"]
    assert config.target_variable == "new_target"

def test_config_file_override(monkeypatch, tmp_path): # Create local directory for you.
    # Create a temporary config file
    config_data = {
        "aws_region": "us-central1",
        "s3_bucket": "file-override-bucket",
        "feature_names": ["x", "y"],
        "target_variable": "file_target"
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    # Set CONFIG_FILE_PATH environment variable
    monkeypatch.setenv("CONFIG_FILE_PATH", str(config_file))

    config = Config()

    assert config.aws_region == "us-central1"
    assert config.s3_bucket == "file-override-bucket"
    assert config.feature_names == ["x", "y"]
    assert config.target_variable == "file_target"