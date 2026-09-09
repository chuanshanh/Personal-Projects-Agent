from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

PROJECT_STATUSES = ('active', 'paused', 'completed')
TASK_STATUSES = ('todo', 'done')
PRIORITIES = ('low', 'medium', 'high')

def now():
    return datetime.now(timezone.utc).isoformat()

def today():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date()

def nonempty(value):
    value = value.strip()
    if not value:
        raise ValueError('名称不能为空')
    return value

def choice(value, choices):
    if value not in choices:
        raise ValueError(f'无效值 {value}，允许值：{choices}')
    return value

def valid_date(value):
    if value is None or value == '':
        return None
    return date.fromisoformat(value).isoformat()
