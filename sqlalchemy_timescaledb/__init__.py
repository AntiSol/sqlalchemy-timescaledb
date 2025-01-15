from sqlalchemy.dialects import registry

registry.register(
    'timescaledb',
    'sqlalchemy_timescaledb.dialect',
    'TimescaledbPsycopg2Dialect'
)
registry.register(
    'timescaledb.psycopg2',
    'sqlalchemy_timescaledb.dialect',
    'TimescaledbPsycopg2Dialect'
)
registry.register(
    'timescaledb.asyncpg',
    'sqlalchemy_timescaledb.dialect',
    'TimescaledbAsyncpgDialect'
)



def autocreate_hypertable_indices():
    """
    Here we patch in a new function to replace sqlalchemy.sql.schema.Table.__init__
    This new function:
    1. calls the original __init__ function
    2. checks if the table is a hypertable
    3. if it is, creates an index on the time column to match the index
        which is automatically created by timescaledb when create_hypertable() is called
        This is necessary so that alembic is aware of these indices and doesn't try to
        drop them on subsequent migrations
    """

    from sqlalchemy import Index
    from sqlalchemy.sql.schema import Table

    _orig_table_init_ = Table.__init__

    def _table_init_override_(self, *args, **kwargs):
        
        # do regular table init:
        ret = _orig_table_init_(self, *args, **kwargs)

        # if it's a hypertable, we declare an index on the relevant field
        if 'timescaledb_hypertable' in kwargs:

            column_name = kwargs['timescaledb_hypertable']['time_column_name']
            index_name = f"{self.name}_{column_name}_idx"

            # Create the index:
            hypertable_index = Index(index_name, self.columns[column_name].desc())  # TODO: error handling here? check for column's existence?

            # add it to the Table object:
            setattr(self, index_name, hypertable_index)

        return ret

    type.__setattr__(Table, "__init__", _table_init_override_)

autocreate_hypertable_indices()
