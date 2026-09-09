from agents import function_tool
from database import Database


def build_tools(db: Database):
    @function_tool
    def update_project(project_id: int, name: str | None = None, description: str | None = None,
                       goal: str | None = None, status: str | None = None) -> dict:
        """编辑项目。null 保持不变；status: active/paused/completed。"""
        return db.update_project(project_id, name, description, goal, status)

    @function_tool
    def delete_project(project_id: int) -> dict:
        """用户明确要求删除整个项目时使用，同时删除项目内全部任务。先读取确认目标。"""
        return db.delete_project(project_id)

    @function_tool
    def create_project(name: str, description: str = '', goal: str = '') -> dict:
        """创建真实项目。先读取已有项目避免重复。"""
        return db.create_project(name, description, goal)

    @function_tool
    def get_projects() -> list[dict]:
        """读取所有项目及任务，任务按 id 升序稳定排列。"""
        return [db.get_project_status(p['id']) for p in db.get_projects()]

    @function_tool
    def create_task(project_id: int, title: str, priority: str = 'medium', due_date: str | None = None) -> dict:
        """创建任务。priority: low/medium/high；日期 YYYY-MM-DD 或 null。"""
        return db.create_task(project_id, title, priority, due_date)

    @function_tool
    def update_task(task_id: int, title: str | None = None, status: str | None = None,
                    priority: str | None = None, due_date: str | None = None) -> dict:
        """修改任务。null 表示不变；due_date 空字符串清除日期。status: todo/done；priority: low/medium/high。"""
        return db.update_task(task_id, title, status, priority, due_date)

    @function_tool
    def complete_task(task_id: int) -> dict:
        """完成任务并记录完成时间。"""
        return db.complete_task(task_id)

    @function_tool
    def postpone_task(task_id: int, days: int = 1) -> dict:
        """将任务顺延若干天。读取数据库当前日期计算：未来任务从原日期顺延，否则从今天顺延。"""
        return db.postpone_task(task_id, days)

    @function_tool
    def delete_task(task_id: int) -> dict:
        """根据用户的删除意图删除指定任务。"""
        return db.delete_task(task_id)

    @function_tool
    def get_project_status(project_id: int) -> dict:
        """读取项目详情、进度、所有任务及其真实 ID。"""
        return db.get_project_status(project_id)

    return [create_project, get_projects, update_project, delete_project, create_task, update_task,
            complete_task, postpone_task, delete_task, get_project_status]
