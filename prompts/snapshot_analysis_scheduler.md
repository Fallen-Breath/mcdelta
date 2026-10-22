# Minecraft 版本分析调度指引

在 mcdelta 项目中，将用户指定版本范围的批量分析作为一个任务。分析要求由 `prompts/snapshot_behavior_analysis.md` 提供。

读取项目根目录的 `config.local.json`。执行 `python scripts/prepare_snapshots.py --from <起点> --to <终点> --release <报告所属正式版>`，导出本任务所需的完整源码、创建各版本分析的空工作目录，并生成集中记录分析输入的 `task.json`。范围排除起点、包含终点，对其中每个提交与父提交作比较。

读取 `task.json`，按 `analyses` 中的顺序调用子 agent，同时运行数不超过配置中的 `max_parallel_tasks` 和当前可用数量。

每项版本分析新建一个不继承本会话历史的子 agent；工具支持时使用 `fork_turns="none"`。初始消息提供对应的目标与基准版本、提交哈希、两端源码目录、分析工作目录、当前分析指引路径、GitHub 仓库地址及报告路径，要求独立完成报告，并禁止创建子 agent。

明确指定每个分析 agent 的工作目录，执行命令时使用该目录作为 `workdir`。临时文件由 agent 按需存放在自己的目录中；源码作为只读输入。调度器只准备源码和分析输入。

启动后等待子 agent 独立交付，调度过程不介入分析和改稿。各项报告保存到指定路径。

任务完成后，清理 `task.json` 中顶层 `work_directory` 指向的任务工作目录，保留 `reports/` 中的报告。
