from sqlalchemy.dialects import registry
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

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

def sane_traceback(now: bool = True) -> str:
    """
    A simple, sane traceback helper for current execution (or the most recent exception).
     gives you nice multi-line text output and doesn't require a bunch of parameters

    If you specify now=False, you'll get the most recent exception rather than the current stack
    """
    import traceback, sys
    _type, val, tb = sys.exc_info()
    if now or (val is None):
        # no exception has occurred (or we were specifically asked for the current stack)
        tb = traceback.extract_stack()

        tb = tb[0:-1]  # remove the extract_stack call from the trace (i.e 'sane_traceback' will be the end of the tb)
    else:
        tb = traceback.extract_tb(tb)

    ret = "".join(traceback.format_list(tb))

    if val is not None:  # include exception info in the trace
        excret = traceback.format_exception_only(_type, val)
        ret += "\n" + ("".join(excret))

    return ret


def autocreate_hypertable_indexes():
    """
    Here we patch in a new function to replace sqlalchemy.sql.schema.Table.__init__
    This new function:
    1. calls the original __init__ function
    2. checks if the table is a hypertable
    3. if it is, creates an index on the time column to match the index
        which is automatically created by timescaledb when create_hypertable() is called
        This is necessary so that alembic is aware of these indexes and doesn't try to
        drop them on subsequent migrations
    """

    from sqlalchemy import Index
    from sqlalchemy.sql.schema import Table

    _orig_table_init_ = Table.__init__

    def _table_init_override_(self, *args, **kwargs):
        # do regular table init:
        ret = _orig_table_init_(self, *args, **kwargs)

        if hasattr(self,"_hypertable_index"):
            # we've already created a hypertable index for this table, don't do it again
            return ret

        # if it's a hypertable, we declare an index on the relevant field
        if 'timescaledb_hypertable' in kwargs:
            tsdb_opts = kwargs.get('timescaledb_hypertable',{})

            column_name = tsdb_opts.get('time_column_name',None)
            if not column_name:
                raise ValueError("Timescaledb hypertables must have a time_column_name defined!")

            index_name = f"{self.name}_{column_name}_idx"

            # Create the index:
            hypertable_index = Index(index_name, self.columns[column_name].desc())

            # add it to the Table:
            setattr(self, index_name, hypertable_index)

            # add table._hypertable_index so we can prevent creating multiple indexes
            setattr(self,"_hypertable_index",hypertable_index)

        return ret

    type.__setattr__(Table, "__init__", _table_init_override_)


_filter_patched = False

def alembic_ignore_timescaledb_indexes():
    """
    This helper patches alembic to automatically ignore indexes which match the naming convention of
     those created automatically via create_hypertable() (<tablename>_<timecolumn>_idx)

    It does this by replacing api.AutogenContext.run_object_filters to check whether the object looks like
     a timescaledb index

    This is effectively the same as doing:

    context.configure(
        include_object = run_object_filters_and_ignore_hypertable_indexes
    )

    ...but requires no config or coding from the user :D

    We need to do this in addition to autocreate_hypertable_indexes because if we don't,
     alembic would try to create the indexes for us (undesirable).
    """

    # prevent applying patch multiple times
    global _filter_patched
    if _filter_patched:
        return

    _filter_patched = True

    try:
        from alembic.autogenerate import api
    except ImportError as ex:
        raise ImportError(f"Couldn't import alembic! {ex}") from ex

    real_run_object_filters = api.AutogenContext.run_object_filters

    def run_object_filters_and_ignore_hypertable_indexes(
        self,obj,name,type_,reflected,compare_to,
    ) -> bool:
        """
        Replacement for api.AutogenContext.run_object_filters which returns false if the object is an index
         following the naming convention for auto-created timescaledb hypertable indexes

        The signature of this function must match api.AutogenContext.run_object_filters
        """
        log.debug(f"running filters for {type_} {name}")
        if type_ == "index":
            if hasattr(obj.table, "dialect_options"):
                opts = obj.table.dialect_options
                tsdb_opts = opts.get('timescaledb', {})
                ht_opts = tsdb_opts.get('hypertable', {})
                time_col = ht_opts.get('time_column_name', "")

                if name == f"{obj.table.name}_{time_col}_idx":
                    # this index name matches what timescaledb creates automatically
                    #  when create_hypertable is used. thus, alembic should ignore it.
                    log.info(f"(Skipping hypertable index '{name}')")
                    return False

        # not a hypertable index, resume normal operation:
        return real_run_object_filters(self,obj,name,type_,reflected,compare_to)

    api.AutogenContext.run_object_filters = run_object_filters_and_ignore_hypertable_indexes

autocreate_hypertable_indexes()

try:
    import alembic
except ImportError:
    pass
else:
    alembic_ignore_timescaledb_indexes()

