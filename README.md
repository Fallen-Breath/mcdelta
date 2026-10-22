# mcdelta

从源码与数据分析 Minecraft 版本之间的游戏表现变化，记录它们对已有玩法和装置的影响。

## 使用

需要 Python 3.11 或更新版本，以及 Git。

将 `config.example.json` 复制为 `config.local.json`，填写本地源码仓库路径。配置项：

- `source_repo`：本地源码仓库路径。
- `source_github`：可选的 GitHub 仓库地址，例如 `https://github.com/TISUnion/guardian`。填写时，代码出处链接到对应提交的文件和行号；留空时，使用相对于源码仓库根目录的路径，以 `/` 分隔。
- `max_parallel_tasks`：同时运行的分析任务数，默认串行。

在本项目中新开会话，提供 [调度指引](prompts/snapshot_analysis_scheduler.md) 和版本范围，例如：

> 按调度指引分析 26.2 到 26.3 的全部变更，报告放到 reports/26.3/。

范围排除起点、包含终点，对其中每个提交与父提交作比较。分析采用 [报告指引](prompts/snapshot_behavior_analysis.md)。

手动准备材料的命令：

```shell
python scripts/prepare_snapshots.py --from 26.2 --to 26.3 --release 26.3
```

加上 `--plan-only` 可查看提交列表而不导出。端点支持版本名称、Git 引用和提交哈希。

## 文件组织

```text
prompts/                              分析与调度指引
scripts/                              源码准备脚本
reports/<release>/<version>.md         报告
work/<起点版本>_<终点版本>/
  task.json                          任务范围及各版本分析的信息
  sources/<commit>/                  本任务所需的完整源码
  analyses/<version>/                各版本分析的工作目录，初始为空
```

一个指定版本范围的批量分析称为一个任务，其中每项称为版本分析。整个 `work/` 忽略版本管理；任务完成后清理对应的范围目录。提交哈希用于准确定位源码，报告按游戏版本命名。

`task.json` 集中记录范围、源码位置、各分析的工作目录及报告路径。调度器在初始消息中提供 `task.json` 的绝对路径和目标版本，由子 agent 读取公共配置及对应的分析输入。分析 agent 在自己的工作目录中按需生成 diff、临时脚本和搜索输出；调度器只准备源码与分析输入。

每个 release 目录收录上一个正式版之后、直到该正式版的全部提交报告。例如 `reports/26.3/` 对应 `26.2 < X ≤ 26.3`。
