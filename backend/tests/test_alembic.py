from pathlib import Path

from alembic.config import Config


def test_alembic_config_points_to_migration_folder() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))

    assert config.get_main_option("script_location") == "alembic"
    assert (backend_dir / "alembic" / "env.py").exists()
    assert (backend_dir / "alembic" / "versions" / "0001_initial_schema.py").exists()
