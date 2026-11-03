# Minecraft 版本分析调度指引

在 mcdelta 项目中，将用户指定版本范围的批量分析作为一个任务。分析要求由 `prompts/snapshot_analysis_worker.md` 提供。

读取项目根目录的 `config.local.json`。执行 `python scripts/prepare_snapshots.py --from <起点> --to <终点> --release <报告所属正式版>`，导出本任务所需的完整源码、创建各版本分析的空工作目录，并生成集中记录分析输入的 `task.json`。范围排除起点、包含终点，对其中每个提交与父提交作比较。

读取 `task.json`，按 `analyses` 中的顺序调用子 agent，同时运行数不超过配置中的 `max_parallel_tasks` 和当前可用数量。

每项版本分析新建一个不继承本会话历史的子 agent；工具支持时使用 `fork_turns="none"`。

初始消息提供 `task.json` 的绝对路径和本次目标版本，并要求子 agent：

- 读取 `task.json`，按 `target.version` 找到 `analyses` 中的对应条目，使用顶层的 `prompt`、`source_github` 及该条目的分析输入。
- 执行命令时使用对应条目的 `work_directory` 作为 `workdir`，临时文件按需存放在该目录中，两端源码作为只读输入。
- 遵循 `prompt` 指向的分析指引，独立完成报告并保存到对应条目的 `report` 路径。
- 禁止创建子 agent。

调度器负责准备源码、分派任务和发起自查，不介入具体分析和改稿。

子 agent 初次交付后，向同一子 agent 追加一轮自查：按对已有玩法的实际影响重新判断各项变化的重要程度，检查是否有应完整展开却写成简述的条目、合并的内容是否真的共享具体机制或使用场景，并按分析指引核对格式排版。修正问题并说明结果；对有疑问的具体判断，再回查相关源码。

全部版本分析自查完成后，清理 `task.json` 中顶层 `work_directory` 指向的任务工作目录，保留 `reports/` 中的报告。
