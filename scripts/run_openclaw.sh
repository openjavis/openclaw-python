#!/bin/bash
# OpenClaw 快速运行脚本

# 进入项目目录
cd "$(dirname "$0")"

# 使用虚拟环境的 Python 运行命令
.venv/bin/python -m openclaw.cli.main "$@"
