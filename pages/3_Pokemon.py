import os, sys

_task_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'task3_pokemon'))
os.chdir(_task_dir)
if _task_dir not in sys.path:
    sys.path.insert(0, _task_dir)

exec(open(os.path.join(_task_dir, 'app.py'), encoding='utf-8').read())
