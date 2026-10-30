from functools import lru_cache

import oracledb

from app.core.config import settings


@lru_cache(maxsize=1)
def get_pool():
    return oracledb.create_pool(
        user=settings.oracle_user,
        password=settings.oracle_password,
        dsn=settings.oracle_dsn,
        config_dir=settings.wallet_location,
        wallet_location=settings.wallet_location,
        wallet_password=settings.wallet_password,
        min=2,
        max=10,
        increment=1,
    )