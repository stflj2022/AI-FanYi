"""为 jobs 表补充 description / workflow_id 字段

与 Job 模型对齐：Web UI 任务创建（JobCreate 携带 description/workflow_id）
与响应（JobResponse 含 description）需要这两个字段，此前模型缺列导致
create_job 报 TypeError。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'web_ui_005'
down_revision: Union[str, Sequence[str], None] = 'web_ui_004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 jobs 表添加 description / workflow_id 列。"""
    op.add_column('jobs', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    """删除 jobs 表的 description / workflow_id 列。"""
    op.drop_column('jobs', 'workflow_id')
    op.drop_column('jobs', 'description')
