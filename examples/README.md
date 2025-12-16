# Examples and Tests

这个目录包含测试脚本和示例代码。

## 测试脚本

### test_ppt_support.py
测试 PPT 文件支持功能。

```bash
python examples/test_ppt_support.py
```

**测试内容：**
- PPT 文本提取
- PPT 文件分类
- PPT 文件重命名

---

### test_pending_mechanism.py
测试 pending 审批机制。

```bash
python examples/test_pending_mechanism.py
```

**测试内容：**
- pending JSON 生成
- pending 文件读取
- 审批流程模拟

---

### test_watcher.py
测试文件监听器功能。

```bash
python examples/test_watcher.py
```

**测试内容：**
- 文件检测
- 防抖机制
- 队列处理

---

## Demo 脚本

### demo_workflow_import.py
演示如何导入和使用 `JanitorWorkflow` 类。

```bash
python examples/demo_workflow_import.py
```

**演示内容：**
- 工作流类的导入
- 单文件处理
- 结果获取

---

### demo_hitl.bat (Windows)
演示人工在环（HITL）审批流程。

```bash
examples\demo_hitl.bat
```

**演示内容：**
- 交互式文件审批
- 命令行确认流程

---

## 运行所有测试

```bash
# 依次运行所有测试
python examples/test_ppt_support.py
python examples/test_pending_mechanism.py
python examples/test_watcher.py
```

---

## 注意事项

1. **运行前确保：**
   - 已激活虚拟环境 (`conda activate janitor`)
   - 已安装所有依赖 (`pip install -r requirements.txt`)
   - 已配置 API Key (`.env` 文件)

2. **测试文件准备：**
   - 某些测试需要在 `inbox/` 目录中放置测试文件
   - 测试会自动清理生成的文件

3. **测试数据：**
   - 测试脚本不会修改真实数据
   - 所有测试都是独立的，可以单独运行

---

返回 [主 README](../README.md)

