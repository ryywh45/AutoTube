from pathlib import Path

from autotube.config import load_settings


class TestConfig:
    def test_load_default_settings(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        settings = load_settings(config_path=tmp_path / "nonexistent.yaml")
        assert settings.llm.model == "tbd"
        assert settings.tts.language == "zh-TW"
        assert settings.video.fps == 30

    def test_load_from_yaml(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("llm:\n  model: gpt-4o\n  temperature: 0.5\n")
        settings = load_settings(config_path=config_file)
        assert settings.llm.model == "gpt-4o"
        assert settings.llm.temperature == 0.5
