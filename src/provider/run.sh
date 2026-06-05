#!/bin/bash
cd /home/linli/桌面/qt-hr/qtadmin/src/provider
.venv/bin/uvicorn app.__main__:app --host 0.0.0.0 --port 8000
