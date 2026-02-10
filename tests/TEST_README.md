# OpenClaw Python 测试指南

## 📁 测试结构

```
tests/
├── unit/                    # 单元测试（快速，隔离）
│   ├── test_config_loader.py
│   ├── test_rpc_client.py
│   ├── test_session_manager.py
│   ├── test_health_system.py
│   └── test_diagnostic_events.py
├── integration/             # 集成测试（需要服务）
│   ├── test_gateway_e2e.py
│   └── test_gateway_health.py
├── conftest.py             # 共享 fixtures
└── TEST_README.md          # 本文档
```

## 🚀 运行测试

### 运行所有测试
```bash
cd /Users/openbot/Desktop/xopen/openclaw-python
/Users/openbot/.local/bin/uv run pytest
```

### 运行单元测试（快速）
```bash
/Users/openbot/.local/bin/uv run pytest tests/unit/ -v
```

### 运行集成测试
```bash
/Users/openbot/.local/bin/uv run pytest tests/integration/ -v
```

### 运行特定测试文件
```bash
/Users/openbot/.local/bin/uv run pytest tests/unit/test_config_loader.py -v
```

### 运行特定测试函数
```bash
/Users/openbot/.local/bin/uv run pytest tests/unit/test_config_loader.py::test_load_config_default -v
```

### 跳过慢速测试
```bash
/Users/openbot/.local/bin/uv run pytest -m "not slow"
```

### 只运行集成测试
```bash
/Users/openbot/.local/bin/uv run pytest -m integration
```

### 生成覆盖率报告
```bash
/Users/openbot/.local/bin/uv run pytest --cov=openclaw --cov-report=html
open htmlcov/index.html
```

## 📊 测试类型

### 单元测试 (`tests/unit/`)
- **特点**: 快速、隔离、不依赖外部服务
- **测试内容**: 单个函数、类、模块
- **示例**:
  - `test_config_loader.py` - 配置加载逻辑
  - `test_rpc_client.py` - RPC 客户端（使用 mock）
  - `test_session_manager.py` - 会话管理

### 集成测试 (`tests/integration/`)
- **特点**: 较慢、测试多个组件交互
- **测试内容**: 完整功能流程
- **示例**:
  - `test_gateway_e2e.py` - Gateway 端到端测试
  - `test_gateway_health.py` - 健康检查集成

## 🎯 测试标记 (Markers)

使用标记来分类和筛选测试：

```python
@pytest.mark.unit
def test_something_fast():
    pass

@pytest.mark.integration
async def test_something_with_services():
    pass

@pytest.mark.slow
async def test_long_running():
    pass
```

运行特定标记的测试：
```bash
# 只运行单元测试
pytest -m unit

# 跳过慢速测试
pytest -m "not slow"

# 运行集成测试
pytest -m integration
```

## 🔧 常用 Fixtures

在 `conftest.py` 中定义了共享 fixtures：

- `event_loop` - 异步测试的事件循环
- `temp_config` - 临时配置文件
- `mock_env` - 模拟环境变量

使用示例：
```python
def test_with_config(temp_config):
    config = load_config(temp_config)
    assert config is not None

def test_with_env(mock_env):
    assert os.environ["GOOGLE_API_KEY"] == "test-key"
```

## 📝 编写测试

### 单元测试示例
```python
"""tests/unit/test_my_module.py"""
import pytest
from openclaw.my_module import my_function

def test_my_function():
    """Test basic functionality"""
    result = my_function("input")
    assert result == "expected_output"

def test_my_function_error():
    """Test error handling"""
    with pytest.raises(ValueError):
        my_function(invalid_input)
```

### 异步测试示例
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality"""
    result = await async_function()
    assert result == "expected"
```

### Mock 示例
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    """Test with mocked dependency"""
    with patch("module.external_call") as mock_call:
        mock_call.return_value = "mocked_result"
        result = await function_under_test()
        assert result == "expected"
        mock_call.assert_called_once()
```

## 🐛 调试测试

### 详细输出
```bash
pytest -vv
```

### 显示打印语句
```bash
pytest -s
```

### 停在第一个失败
```bash
pytest -x
```

### 重新运行失败的测试
```bash
pytest --lf
```

### 显示最慢的10个测试
```bash
pytest --durations=10
```

## 📈 持续集成

测试应该在 CI/CD 管道中自动运行：

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run tests
        run: uv run pytest
```

## 🎯 测试覆盖率目标

- **单元测试**: >= 80%
- **集成测试**: 关键功能路径
- **整体**: >= 70%

查看当前覆盖率：
```bash
pytest --cov=openclaw --cov-report=term-missing
```

## 📚 最佳实践

1. **遵循 AAA 模式**:
   - Arrange (准备)
   - Act (执行)
   - Assert (断言)

2. **测试命名**: `test_<function>_<scenario>`
   - `test_load_config_default`
   - `test_load_config_with_env_vars`

3. **使用 fixtures**: 重用测试设置

4. **Mock 外部依赖**: 保持单元测试快速和隔离

5. **清理资源**: 使用 fixtures 的 `yield` 或 `finally`

6. **测试边界情况**: 空值、错误、边界值

## 🆘 故障排除

### 问题: Import errors
```bash
# 确保在虚拟环境中
uv sync
uv run pytest
```

### 问题: Async tests not working
```bash
# 安装 pytest-asyncio
uv add pytest-asyncio
```

### 问题: Tests hang
```bash
# 使用超时
pytest --timeout=30
```

## 📖 更多资源

- [Pytest 文档](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
