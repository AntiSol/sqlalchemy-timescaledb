# SQLAlchemy TimescaleDB

This is the TimescaleDB dialect driver for SQLAlchemy. Drivers `psycopg2` and `asyncpg` are supported.

Alembic is supported, it should correctly ignore objects (indexes, table partitions, etc) created by timescaledb.

## Install

```bash
$ pip install git+https://github.com/AntiSol/sqlalchemy-timescaledb.git
```

## Usage

Adding to table `timescaledb_hypertable` option allows you to configure the [hypertable parameters][5]:

```Python
import datetime
from sqlalchemy import create_engine, MetaData
from sqlalchemy import Table, Column, Integer, String, DateTime

engine = create_engine('timescaledb://user:password@host:port/database')
metadata = MetaData()
metadata.bind = engine

Metric = Table(
    'metric', metadata,
    Column('name', String),
    Column('value', Integer),
    Column('timestamp', DateTime(), default=datetime.datetime.now),
    timescaledb_hypertable={
        'time_column_name': 'timestamp'
    }
)

metadata.create_all(engine)
```

Or using `declarative_base` style:

```Python
import datetime

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Float, String, DateTime

Base = declarative_base()

class Metric(Base):
    __table_args__ = ({
        'timescaledb_hypertable': {
            'time_column_name': 'timestamp'
        }
    })

    name = Column(String)
    value = Column(Float)
    timestamp = Column(
        DateTime(), default=datetime.datetime.now, primary_key=True
    )
```

## Parameters

* [chunk_time_interval][6]

## Functions

Timescaledb functions implemented:

### [first(value, time)][7]

```Python
func.first(Metric.value, Metric.timestamp)
```

### [last(value, time)][8]

```Python
func.last(Metric.value, Metric.timestamp)
```


[5]: https://docs.timescale.com/api/latest/hypertable/create_hypertable/#optional-arguments
[6]: https://docs.timescale.com/api/latest/hypertable/set_chunk_time_interval/
[7]: https://docs.timescale.com/api/latest/hyperfunctions/first/
[8]: https://docs.timescale.com/api/latest/hyperfunctions/last/
