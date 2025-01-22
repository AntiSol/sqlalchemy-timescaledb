import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from tests.models import Base


class TestAlembic:
    def setup_class(self):
        # TODO: Disable output for alembic
        self.config = Config(
            os.path.join(os.path.dirname(__file__), 'alembic.ini')
        )
        self.migration_versions_path = os.path.join(
            os.path.dirname(__file__), 'migrations', 'versions'
        )
        self.config.set_main_option("version_locations",self.migration_versions_path)

    def test_create_revision(self, engine):
        Base.metadata.drop_all(bind=engine)
        script = command.revision(
            self.config, message='initial', autogenerate=True
        )
        migration_file = os.path.join(
            self.migration_versions_path, f'{script.revision}_initial.py'
        )

        assert script.down_revision is None
        assert Path(migration_file).is_file()

        Path(migration_file).unlink()
        Base.metadata.create_all(bind=engine)

    def test_alembic_migration_doesnt_drop_indexes_created_by_timescaledb(self,engine):
        #TODO: write a test for this
        # see: https://github.com/dorosch/sqlalchemy-timescaledb/issues/21 for details of the bug
        # bug fixed by autocreate_hypertable_indexes()
        assert True

