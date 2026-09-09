"""Real model acceptance test. Uses an isolated temporary SQLite database."""
import asyncio
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from agent import run_turn
from database import Database
from config import ModelConfig, load_settings
from models import today


def assert_date_language_matches(answer: str, actual_due_date: date) -> None:
    """Reject relative date words that do not match the persisted date."""
    day_offset = (actual_due_date - today()).days
    if '明天' in answer:
        assert day_offset == 1, f'回复称为“明天”，但实际日期是 {actual_due_date}'
    if '后天' in answer:
        assert day_offset == 2, f'回复称为“后天”，但实际日期是 {actual_due_date}'

async def main():
    config = ModelConfig.from_settings(load_settings())
    if config.problem():
        raise SystemExit(config.problem())
    with tempfile.TemporaryDirectory() as directory:
        db = Database(Path(directory) / 'live.sqlite3')
        answer, history = await run_turn(db, '最近我想准备 Agent 实习。我先做这个项目管理 Agent，不想一开始系统学很多东西，帮我建立一个项目。')
        print(answer)
        assert len(db.get_projects()) == 1
        tasks = db.get_tasks()
        assert len(tasks) == 3, '核心故事应创建三个最小下一步'
        original_due_date_text = tasks[2]['due_date']
        # The initial request is intentionally vague, so the model may leave tasks unscheduled.
        # Establish a future baseline dynamically; the behavior under test is relative postponement.
        original_due_date = date.fromisoformat(original_due_date_text) if original_due_date_text else today() + timedelta(days=7)
        if original_due_date <= today():
            original_due_date = today() + timedelta(days=7)
        if original_due_date_text != original_due_date.isoformat():
            db.update_task(tasks[2]['id'], due_date=original_due_date.isoformat())
        print(f'第三个任务原截止日期：{original_due_date.isoformat()}')
        answer, history = await run_turn(db, '第二个已经完成了，但是今天比较累，把第三个推迟一下。', history)
        print(answer)
        assert db.get('tasks', tasks[1]['id'])['status'] == 'done'
        assert db.get('tasks', tasks[1]['id'])['completed_at']
        updated_due_date = date.fromisoformat(db.get('tasks', tasks[2]['id'])['due_date'])
        assert updated_due_date == original_due_date + timedelta(days=1), (
            f'第三个任务应从 {original_due_date} 顺延一天，实际为 {updated_due_date}'
        )
        assert_date_language_matches(answer, updated_due_date)
        assert updated_due_date.isoformat() in answer, 'Agent 回复应包含与数据库一致的完整日期'
        answer, _ = await run_turn(db, f"删除任务 #{tasks[2]['id']}，保留其他任务。", history)
        print(answer)
        assert len(Database(db.path).get_tasks()) == 2
        print('PASS: real model -> SDK tools -> SQLite -> persisted state')

if __name__ == '__main__':
    asyncio.run(main())
