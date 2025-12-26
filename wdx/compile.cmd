del __pycache__\*.*
python -m compileall constants.py
python -m compileall dialogs.py
python -m compileall main.py
python -m compileall main_window.py
python -m compileall project_manager.py
python -m compileall project_window.py
python -m compileall server.py
ren .\__pycache__\dialogs.cpython-313.pyc dialogs.pyc
ren .\__pycache__\constants.cpython-313.pyc constants.pyc
ren .\__pycache__\main.cpython-313.pyc main.pyc
ren .\__pycache__\main_window.cpython-313.pyc main_window.pyc
ren .\__pycache__\project_manager.cpython-313.pyc project_manager.pyc
ren .\__pycache__\project_window.cpython-313.pyc project_window.pyc
ren .\__pycache__\server.cpython-313.pyc server.pyc
mkdir .\__pycache__\com.crackyOS.wdx
move .\__pycache__\*.pyc .\__pycache__\com.crackyOS.wdx\
copy ..\wdx_extension\wdx_extension.crx .\__pycache__\com.crackyOS.wdx\
copy .\icon128.ico .\__pycache__\com.crackyOS.wdx\