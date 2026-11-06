from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.models.drug import Drug


def test_local_migration_history_contains_the_recorded_composition_revision():
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    scripts = ScriptDirectory.from_config(config)

    revision = scripts.get_revision("20261001_drug_composition")

    assert revision is not None
    assert revision.down_revision == "20261001_qr_payload"
    assert len(scripts.get_heads()) == 1
    assert scripts.get_current_head() == "20261105_ai_telemetry_analysis"
    assert "composition" in Drug.__table__.columns
    assert Drug.__table__.columns["composition"].nullable is True
