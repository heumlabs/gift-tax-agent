from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import create_engine, pool, text
from sqlalchemy.dialects import postgresql
from alembic import context

# backend 디렉토리를 Python path에 추가
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

# 프로젝트 설정 및 모델 import
from config import settings
from chalicelib.models.database import SQLModel

# pgvector import (타입 인식용)
from pgvector.sqlalchemy import Vector

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Note: DATABASE_URL은 settings에서 직접 사용하므로 config에 설정하지 않음
# (ConfigParser의 % interpolation 문제 회피)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLModel 메타데이터 설정 (autogenerate 지원)
target_metadata = SQLModel.metadata


# SQLModel AutoString을 표준 SQLAlchemy 타입으로 렌더링
def render_item(type_, obj, autogen_context):
    """SQLModel의 AutoString을 표준 타입으로 렌더링"""
    from sqlmodel.sql.sqltypes import AutoString
    
    if type_ == "type" and isinstance(obj, AutoString):
        # AutoString을 VARCHAR 또는 TEXT로 변환
        if obj.length:
            return f"sa.String(length={obj.length})"
        else:
            return "sa.Text()"
    
    # pgvector의 Vector 타입 처리
    if type_ == "type" and isinstance(obj, Vector):
        return f"Vector({obj.dim})"
    
    return False


# pgvector HNSW 인덱스에 operator class 자동 추가
def render_index(index, autogen_context):
    """pgvector HNSW 인덱스에 operator class 추가"""
    from sqlalchemy import Index
    
    # HNSW 인덱스이고 vector 컬럼인 경우
    if hasattr(index, 'dialect_options') and index.dialect_options.get('postgresql_using') == 'hnsw':
        # embedding 컬럼에 대한 인덱스인 경우 vector_cosine_ops 추가
        for col in index.expressions:
            col_name = str(col)
            if 'embedding' in col_name:
                # 렌더링 텍스트 수정
                import re
                rendered = autogen_context.opts['render_item'](index, autogen_context)
                if rendered and 'embedding' in rendered:
                    rendered = re.sub(
                        r"\['embedding'\]",
                        "[sa.text('embedding vector_cosine_ops')]",
                        rendered
                    )
                    return rendered
    
    return None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # settings에서 직접 DATABASE_URL 가져오기 (% escape 불필요)
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 타입 변경 감지
        compare_server_default=True,  # 서버 기본값 변경 감지
        render_item=render_item,  # SQLModel 타입 렌더링
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # settings에서 직접 DATABASE_URL 가져와서 엔진 생성
    # ConfigParser의 % interpolation 문제 회피
    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # pgvector 확장 확인 및 설치
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 타입 변경 감지
            compare_server_default=True,  # 서버 기본값 변경 감지
            render_item=render_item,  # SQLModel 타입 렌더링
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
