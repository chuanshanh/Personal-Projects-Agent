from datetime import date
import streamlit as st
from database import Database
from models import today, PRIORITIES, PROJECT_STATUSES
from config import ModelConfig, load_settings

st.set_page_config(page_title='Project Agent', page_icon='🌱', layout='centered')
st.markdown('''<style>
.block-container {max-width:760px;padding-top:1.5rem;padding-bottom:5rem;}
.stButton button {min-height:44px;} h1 {font-size:2rem!important;}
[data-testid="stCheckbox"] label {min-height:44px;align-items:center;}
@media(max-width:640px){.block-container{padding-left:1rem;padding-right:1rem;}}
</style>''', unsafe_allow_html=True)
try:
    settings = load_settings()
    config_problem = ModelConfig.from_settings(settings).problem()
except (ValueError, OSError):
    st.error('无法读取配置文件，请检查 .streamlit/secrets.toml 的格式与权限。')
    st.stop()
db = Database(settings.get('PROJECT_AGENT_DB'))
st.session_state.setdefault('history', [])
st.session_state.setdefault('messages', [])
st.title('🌱 Project Agent')
st.caption('把想法变成最小下一步，允许计划随时改变。')
page = st.radio('导航', ['Today', 'Projects', 'Explore'], horizontal=True, label_visibility='collapsed')
if st.session_state.get('notice'):
    st.warning(st.session_state.pop('notice'))

def change_task_status(task_id, key):
    try:
        db.update_task(task_id, status='done' if st.session_state[key] else 'todo')
    except ValueError:
        st.session_state.notice = '任务已不存在，请查看刷新后的列表。'


def task_card(task, prefix, editable=False, project_name=None):
    tid = task['id']
    with st.container(border=True):
        key = f'{prefix}_done_{tid}'
        # Render from the database; only an actual checkbox event writes back.
        st.session_state[key] = task['status'] == 'done'
        st.checkbox(task['title'], key=key, on_change=change_task_status, args=(tid, key))
        if project_name:
            st.caption(project_name)
        st.caption(f"#{tid} · {dict(low='低优先级', medium='普通', high='高优先级')[task['priority']]} · {task['due_date'] or '未排期'}")
        if editable:
            with st.expander('修改 / 删除'):
                with st.form(f'edit_{tid}'):
                    title = st.text_input('任务名称', task['title'])
                    priority = st.selectbox('优先级', PRIORITIES, index=PRIORITIES.index(task['priority']))
                    due = st.date_input('截止日期（可清空）', value=date.fromisoformat(task['due_date']) if task['due_date'] else None)
                    if st.form_submit_button('保存修改'):
                        try:
                            db.update_task(tid, title=title, priority=priority, due_date=due.isoformat() if due else '')
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                if st.button('删除任务', key=f'delete_{tid}'):
                    db.delete_task(tid)
                    st.rerun()

projects = db.get_projects()
if page == 'Today':
    st.subheader('My Projects')
    active = [p for p in projects if p['status'] == 'active']
    if not active:
        st.info('从一个项目开始。去 Projects 手动创建，或在下方告诉 Agent 你的想法。')
    for p in active[:3]:
        status = db.get_project_status(p['id'])
        with st.container(border=True):
            st.write(p['name'])
            st.progress(status['progress'] / 100, text=f"{status['progress']}% · {status['completed']}/{status['total']} 已完成")
    if len(active) > 3:
        st.caption(f'还有 {len(active) - 3} 个进行中项目，可在 Projects 查看。')
    st.subheader('Today')
    tasks = db.get_tasks()
    active_ids = {p['id'] for p in active}
    pending = [t for t in tasks if t['status'] == 'todo' and t['project_id'] in active_ids]
    scheduled = [t for t in pending if t['due_date'] and t['due_date'] <= today().isoformat()]
    if not scheduled:
        st.caption('今天没有到期任务，可以轻一点。')
    scheduled.sort(key=lambda t: ({'high': 0, 'medium': 1, 'low': 2}[t['priority']], t['due_date'], t['id']))
    names = {p['id']: p['name'] for p in projects}
    for t in scheduled[:3]:
        task_card(t, 'today', project_name=names[t['project_id']])
    if len(scheduled) > 3:
        with st.expander(f'其他 {len(scheduled) - 3} 个到期任务'):
            for t in scheduled[3:]:
                task_card(t, 'more_today', project_name=names[t['project_id']])
    with st.expander('未排期与接下来的任务'):
        for t in pending:
            if t not in scheduled:
                task_card(t, 'later', project_name=names[t['project_id']])
    st.subheader('Ask Agent')
    if config_problem:
        st.info('手动项目管理已可用。Agent 尚未配置，详见 README。')
        with st.expander('查看配置提示'):
            st.caption(config_problem)
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.write(message['content'])
    prompt = st.chat_input('例如：第二个完成了，把第三个推迟到明天', disabled=bool(config_problem))
    if prompt:
        st.session_state.messages.append({'role': 'user', 'content': prompt})
        try:
            from agent import chat
            with st.spinner('正在查看项目并更新…'):
                answer, history = chat(db, prompt, st.session_state.history)
            st.session_state.history = history
            st.session_state.messages.append({'role': 'assistant', 'content': answer})
        except Exception:
            # Tools commit individually: refresh the UI even after partial failure.
            st.session_state.history = []
            notice = '本轮未能完整执行，部分操作可能已保存。请检查刷新后的项目状态；确认 API Key、模型和网络后再试。'
            st.session_state.messages.append({'role': 'assistant', 'content': notice})
            st.session_state.notice = notice
        st.rerun()
    if st.session_state.messages and st.button('清空对话（保留项目和任务）'):
        st.session_state.history = []
        st.session_state.messages = []
        st.rerun()

elif page == 'Projects':
    with st.expander('＋ 创建项目', expanded=not projects):
        with st.form('new_project', clear_on_submit=True):
            name = st.text_input('项目名称')
            goal = st.text_area('Goal')
            description = st.text_area('描述')
            if st.form_submit_button('创建项目'):
                try:
                    db.create_project(name, description, goal)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    if projects:
        pid = st.selectbox('选择项目', [p['id'] for p in projects], format_func=lambda pid: next(p['name'] for p in projects if p['id'] == pid))
        p = db.get_project_status(pid)
        st.subheader(p['name'])
        st.caption({'active': '进行中', 'paused': '已暂停', 'completed': '已完成'}[p['status']])
        st.write(p['goal'] or '还没有填写 Goal，边做边调整也可以。')
        st.caption(p['description'])
        st.progress(p['progress'] / 100, text=f"{p['progress']}% · {p['completed']}/{p['total']} 已完成")
        with st.expander('编辑项目'):
            with st.form(f'project_{pid}'):
                name = st.text_input('名称', p['name'])
                goal = st.text_area('目标', p['goal'])
                description = st.text_area('项目描述', p['description'])
                status = st.selectbox('状态', PROJECT_STATUSES, index=PROJECT_STATUSES.index(p['status']))
                if st.form_submit_button('保存项目'):
                    try:
                        db.update_project(pid, name, description, goal, status)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            confirm = st.checkbox('同时删除此项目的所有任务', key=f'confirm_{pid}')
            if st.button('删除项目', disabled=not confirm):
                db.delete_project(pid)
                st.rerun()
        with st.expander('＋ 新增任务'):
            with st.form(f'new_task_{pid}', clear_on_submit=True):
                title = st.text_input('任务名称')
                priority = st.selectbox('优先级', PRIORITIES, index=1)
                due = st.date_input('截止日期（可不填）', value=None)
                if st.form_submit_button('新增任务'):
                    try:
                        db.create_task(pid, title, priority, due.isoformat() if due else None)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        for t in p['tasks']:
            task_card(t, 'project', editable=True)
else:
    st.subheader('Explore')
    st.write('我是否真的喜欢 Agent 开发？')
    st.info('先通过项目中的最小行动寻找答案。探索实验、体验记录与总结将在后续加入。')

with st.expander('数据与备份'):
    st.caption('项目和任务保存在服务器上的 SQLite 文件；聊天仅保留在当前会话。')
    st.download_button('下载 SQLite 备份', db.backup(), file_name=f'project-agent-{today()}.sqlite3', mime='application/octet-stream')
