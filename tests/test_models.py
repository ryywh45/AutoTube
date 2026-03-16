from autotube.models import (
    Script,
    ScriptSection,
    StoryboardScene,
    VideoProject,
    VideoFormat,
    VideoMetadata,
)


class TestScript:
    def test_create_script(self):
        script = Script(
            title="Test Video",
            concept="Testing concept",
            sections=[
                ScriptSection(heading="Intro", narration="這是一段測試文字"),
                ScriptSection(heading="Main", narration="主要內容在這裡"),
            ],
        )
        assert len(script.sections) == 2
        assert "測試" in script.full_narration

    def test_estimated_duration(self):
        script = Script(
            title="Test",
            concept="Test",
            sections=[ScriptSection(heading="A", narration="一二三四五六七八")],
        )
        # 8 chars / 4 chars per sec = 2 seconds
        assert script.estimated_duration_seconds == 2.0


class TestStoryboardScene:
    def test_create_scene(self):
        scene = StoryboardScene(
            scene_index=0,
            narration="旁白文字",
            visual_description="A person standing",
        )
        assert scene.image_path is None


class TestVideoProject:
    def test_create_project(self):
        project = VideoProject(concept="Test concept", format=VideoFormat.MEDIUM)
        assert project.format == "medium"
        assert project.scenes == []


class TestVideoMetadata:
    def test_create_metadata(self):
        meta = VideoMetadata(
            title="Test Title",
            description="A description",
            tags=["test", "video"],
        )
        assert len(meta.tags) == 2
