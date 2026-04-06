# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于Python的电商AI客服桌面应用程序，使用PyQt6构建用户界面，集成了AI驱动的客户服务自动化功能。应用支持多平台渠道集成，主要面向电商场景提供智能客服解决方案。

## 常用开发命令

### 启动应用
```bash
# 激活虚拟环境并启动
source .venv/bin/activate && python app.py

# Windows环境
.venv\Scripts\activate && python app.py
```

### 依赖管理
```bash
# 安装/同步依赖
uv sync

# 添加新依赖
uv add package_name

# 更新依赖
uv sync --upgrade
```

### 构建打包
```bash
# 构建Windows可执行文件（必须在Windows系统上运行）
python scripts/build_win_exe.py --clean

# 跨平台构建
python scripts/build_exe.py

# 安装Playwright浏览器（如需要）
python scripts/install_playwright.py
```

### 测试与开发工具
项目目前未配置正式的测试、格式化工具，建议使用：
- 代码格式化：`black .`
- 类型检查：`mypy .`
- Lint检查：`flake8 .`
- 运行测试：`python -m pytest test/`（需先配置pytest）

## 高层架构

### 核心模块结构
- **ui/**: PyQt6用户界面模块，包含主窗口和各种功能界面
  - `main_ui.py`: 主窗口入口，集成所有功能模块
  - `Knowledge_ui.py`: 知识库管理界面
  - `auto_reply_ui.py`: 自动回复设置界面
  - `keyword_ui.py`: 关键词规则配置界面
  - `log_ui.py`: 日志查看界面
  - `setting_ui.py`: 系统设置界面
  - `user_ui.py`: 用户管理界面

- **core/**: 核心服务模块，包含依赖注入容器、缓存和基础服务
  - `di_container.py`: 依赖注入容器实现，支持SINGLETON、TRANSIENT、SCOPED生命周期
  - `connection_status.py`: 连接状态管理（ConnectionStatusManager），线程安全，跨PDDChannel实例共享
  - `service_providers.py`: 服务提供者代理（_DIProxy），提供向后兼容的懒代理
  - `base_service.py`: 基础服务抽象类
  - `cache.py`: 缓存服务实现

- **Agent/**: AI代理模块，包含客服代理和知识库管理
  - `CustomerAgent/`: 客服代理实现
    - `agent.py`: 主要代理逻辑
    - `agent_description.py`: 代理描述和配置
    - `agent_knowledge.py`: 知识库集成
    - `tools/`: 代理工具集
      - `get_product_list.py`: 商品列表工具
      - `move_conversation.py`: 会话转移工具
    - `readers/`: 文档读取器
      - `doc_reader.py`: 文档读取器
      - `excel_reader.py`: Excel读取器
  - `bot.py`: 机器人基础类

- **Message/**: 消息处理模块，实现异步消息处理和路由
  - `core/`: 核心消息处理组件
    - `consumer.py`: 消息消费者
    - `handlers.py`: 处理器管理
    - `queue.py`: 消息队列实现
  - `handlers/`: 具体处理器实现
    - `ai_handler.py`: AI处理器
    - `base.py`: 基础处理器
    - `keyword_handler.py`: 关键词处理器
    - `preprocessor.py`: 预处理器
  - `models/`: 消息模型定义
    - `queue_models.py`: 队列相关模型
  - `message.py`: 消息基础类

- **Channel/**: 渠道集成模块，目前支持拼多多平台
  - `channel.py`: 渠道基础抽象类
  - `pinduoduo/`: 拼多多渠道实现
    - `pdd_channel.py`: 拼多多渠道主类
    - `pdd_login.py`: 登录处理
    - `pdd_message.py`: 消息处理
    - `utils/API/`: 拼多多API工具
      - `get_shop_info.py`: 获取店铺信息
      - `Set_up_online.py`: 设置在线状态
      - `get_token.py`: 获取令牌
      - `get_user_info.py`: 获取用户信息
      - `product_manager.py`: 商品管理
      - `send_message.py`: 发送消息
    - `utils/base_request.py`: 基础请求工具

- **database/**: 数据库模块，使用SQLAlchemy ORM
  - `db_manager.py`: 数据库管理器
  - `connection_pool.py`: 连接池管理
  - `models.py`: 数据模型定义

- **utils/**: 工具模块，包含日志、路径管理等实用工具
  - `logger_loguru.py`: 统一日志系统，支持UI集成和结构化日志
  - `logger_config.py`: 日志配置
  - `path_utils.py`: 路径工具
  - `runtime_path.py`: 运行时路径管理
  - `resource_manager.py`: 资源管理
  - `logging_context.py`: 日志上下文

- **bridge/**: 桥接模块，处理不同组件间的通信
  - `context.py`: 上下文管理
  - `reply.py`: 回复处理

### 设计模式
- **依赖注入**: 使用自定义DI容器管理服务生命周期，支持单例、瞬时和作用域模式
- **消息处理器模式**: 基于类型和渠道的消息处理链，支持预处理器、AI处理器、关键词处理器
- **策略模式**: 不同渠道和消息类型的处理策略
- **工厂模式**: 服务实例创建和管理

### 数据流
用户消息 → 渠道接收 → 消息队列 → 预处理器 → AI处理器/关键词处理器 → 响应生成 → 渠道发送

## 技术栈关键点

- **界面框架**: PyQt6 + PyQt6-Fluent-Widgets（现代化UI组件）
- **AI框架**: Agno + OpenAI兼容API（支持多种LLM）
- **数据存储**: SQLAlchemy + SQLite + LanceDB（向量数据库）
- **日志系统**: Loguru（结构化日志，支持自动轮转和UI集成）
- **配置管理**: Pydantic（类型安全的配置验证）
- **异步处理**: asyncio + WebSocket（高并发消息处理）
- **Web自动化**: Playwright（浏览器自动化）
- **包管理**: UV（现代Python包管理器）

## 开发约定

### 命名规范
- 类名使用PascalCase
- 函数和变量使用snake_case
- 常量使用UPPER_CASE
- 文件名使用snake_case

### 代码组织
- 使用类型注解提高代码可读性
- 遵循标准Python docstring格式
- 错误处理使用自定义异常类
- 配置操作需要线程安全
- 服务通过DI容器管理，避免直接实例化

### 重要文件说明
- `config.py`: 线程安全的配置管理系统，支持嵌套配置访问，使用Pydantic模型验证
- `app.py`: 应用程序入口点，初始化PyQt6应用和主窗口
- `core/di_container.py`: 依赖注入容器实现，支持多种服务生命周期
- `utils/logger_loguru.py`: 统一日志系统，支持UI集成和结构化日志

## 配置管理

应用使用JSON配置文件（config.json），首次运行会自动创建默认配置。支持：
- 嵌套配置访问（如 `config.get('llm.api_key')`）
- Pydantic模型验证
- 线程安全的配置操作
- 自动创建默认配置
- 支持多种LLM提供商配置（OpenAI、DeepSeek、Gemini、Kimi、Claude）

## 部署和构建

- 使用UV作为Python包管理器
- 支持打包为Windows可执行文件（通过PyInstaller）
- 日志文件自动轮转和压缩（logs/目录）
- 临时文件存储在temp/目录
- Playwright浏览器自动安装和管理

## 注意事项

- 配置文件（config.json）包含敏感信息，已被.gitignore忽略
- 应用依赖虚拟环境，使用Python 3.11+
- UI组件使用延迟加载优化启动性能
- 消息处理采用异步架构，支持高并发场景
- 依赖注入容器确保服务实例的正确生命周期管理
- 向量数据库（LanceDB）用于知识库的语义搜索

## 测试

测试文件位于 `test/` 目录，包含：
- `test_agent_tool.py`: 代理工具测试

