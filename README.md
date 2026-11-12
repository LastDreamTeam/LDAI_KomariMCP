# Komari 监控 MCP

> **自用项目** · 本仓库主要供维护者自用。

通过 Komari 原生 API 查询主机指标并维护到期日、配额等资产字段。 本仓库是独立维护的第三方 stdio MCP 连接器。

## 安装运行环境

使用 Python 3.11 或更高版本。在仓库根目录执行 `python -m venv .venv`。Windows 用 `.venv\Scripts\python.exe -m pip install -r requirements.txt` 安装依赖，macOS/Linux 用 `.venv/bin/python -m pip install -r requirements.txt`。

## 连接自己的账户

1. 准备自己的 Komari 面板地址。公网用 HTTPS，本机部署可用 HTTP 回环地址。需要访问隐藏节点或维护资产时，在面板生成管理员 API Key，单独保存在本机私有文件。
2. 运行下方配置生成器时追加 `--env KOMARI_BASE_URL=https://monitor.example.org --env KOMARI_API_KEY_FILE=/path/to/key-file`，替换示例地址和路径。游客模式可以省略密钥文件。也可通过进程环境传入 `KOMARI_API_KEY`。
3. `komari_list_servers` 列出可见节点，`komari_latest_status` 和 `komari_monitor_records` 分别查实时和历史数据。管理员可以查看探测任务、主题、插件，并更新资产字段。修改后按同一 UUID 回读，提供字段旧值、新值和核验结果。到期时间包含时区，流量配额单位是字节。

## 接入 Cursor、DSH 或 Codex

在仓库目录执行对应命令。生成器使用 Python 3，按当前机器的路径输出可合并的客户端配置。

```sh
python client_config.py cursor
python client_config.py dsh
python client_config.py codex
```

| 客户端 | 配置位置 |
| --- | --- |
| Cursor | 项目 `.cursor/mcp.json` 或用户级 `~/.cursor/mcp.json` 的 `mcpServers` |
| DSH | 当前 profile 的插件列表，启用一条 `@deepseek-ai/dsh-mcp-client` 记录 |
| Codex | `~/.codex/config.toml` 的 `mcp_servers` 条目 |

可重复使用 `--env NAME=VALUE` 传递这些设置：`KOMARI_BASE_URL`、`KOMARI_API_KEY_FILE`。涉及密钥的设置只填写私有文件的路径。在客户端刷新工具后先调用 `komari_status`。各端使用同一个服务入口，克隆到另一台机器时重新生成路径。仓库另附 Codex 插件清单、图标和技能，可用于打包本地插件。若插件被复制到客户端缓存，可通过进程环境 `LDAI_MCP_PYTHON` 指定已安装依赖的 Python 绝对路径。 [Cursor MCP 文档](https://cursor.com/docs/mcp) · [DSH MCP 客户端](https://github.com/deepseek-ai/deepseek-harness/blob/main/packages/mcp/mcp-client/README.zh.md)

## 实现参考

GitHub 数据核对日期为 2026-11-11。

参考社区 Komari MCP 的面板选择与 Bearer 认证方式，并为资产字段更新加入回读。

- [komari-monitor/komari](https://github.com/komari-monitor/komari) · 6,978 stars，默认分支 900 次提交
- [mogumc/Komari-MCP-Server](https://github.com/mogumc/Komari-MCP-Server) · 5 stars，默认分支 19 次提交

## 许可

本项目以 **GNU Affero General Public License v3.0 only（AGPL-3.0-only）** 发布。分发受许可覆盖的修改版或通过网络向用户提供修改版时，应按许可条款向相应用户提供对应源码。仅在本机自行使用无需公开发布。第三方服务及依赖遵循各自条款。[许可全文](LICENSE)

## 账号管理窗口

账号版从本插件详情页点「管理」→「已连接的账户」→「连接另一个账户」。已连接账号右侧菜单提供重命名、重新连接和断开连接。

使用独立 stdio 客户端时可运行 `python account_manager.py` 设置本机账号。站点与凭据保存在部署端；图形窗口需要 Python 的 Tk 组件。

按名称、标签、地区、分组或 UUID 搜索；按 UUID 读取配置、累计上下行字节、实时速率和配额。komari_add_host 创建面板登记并按 UUID 回读，探针注册命令由面板提供。

## 多账号和终端更新

MCP 入口为 `router.py`，需要 Python 3.11+。主机在本地保存账号配置，默认位置为 `~/.config/ldai-mcp/komari/accounts.json`，也可用 `LDAI_ACCOUNTS_FILE` 指定。复制 [两账号示例](examples/accounts.example.json)，将地址与路径换成自己的值。每个账号分别设置面板地址和管理员 Key 文件。

`ldai_accounts` 仅列出别名和连接状态。配置两个账号后，工具以 `work__` 和 `personal__` 前缀区分，所选工具始终进入该账号的独立子进程。已有单账号配置继续使用原工具名。运行 `python profile_exec.py work -- <程序> <参数…>` 可在同一账号环境完成登录或初始化。完成配置后重新连接 MCP。需要自有适配器时，管理员可为某个账号填写可信 stdio 程序的 `command`、`args` 和 `env`；连接器仅发布当前产品前缀下的业务工具。

安装本仓库后，其他终端可运行 `git pull --ff-only`；Python 服务在其虚拟环境执行 `python -m pip install -r requirements.txt`，随后重新加载客户端。需要固定版本时可检出发布标签。

维护者在 main 提交改进、运行测试，并同步更新 connector.json、两个插件清单的版本，再执行 `python build_plugin.py --push`。此命令将 main 与版本标签一起推送到本仓库，再从已提交文件生成 ZIP。更新既有账号插件时传 `--account-name <既有包名>`，把生成的 ZIP 发布到同一插件。包内 release-source.json 记录精确提交，可与各终端核对。Git 推送与账号插件发布是两个独立步骤。

许可为 **AGPL-3.0-only**。[许可全文](LICENSE)

[原生插件页多账号接入候选版：部署、覆盖范围与验收](native_account/README.md)

使用 Codex 插件页连接、重连和管理多个工作站账号，见[工作站接入](native_account/WORKSTATION.md)。
