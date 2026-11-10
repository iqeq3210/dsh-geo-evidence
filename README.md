# GEO 组学检索与核验（DeepSeek Harness 插件）

源码仓库：[iqeq3210/dsh-geo-evidence](https://github.com/iqeq3210/dsh-geo-evidence)。使用 `git clone https://github.com/iqeq3210/dsh-geo-evidence.git` 下载后按下文安装。

支持按实验类型指定 `technology`，原有 `rnaseq`、`array` 参数保持兼容。此扩展不包含自动推荐或 WGCNA/biomarker 队列选择。

| 类目 | technology | 说明 |
|---|---|---|
| RNA-seq | rnaseq | 默认，包含 bulk 及部分单细胞研究 |
| 表达芯片 | array | 与 ChIP-seq 不同 |
| ChIP-seq | chipseq / ChIP-seq | 可加 target=CTCF 或 H3K27ac |
| CUT&Tag | cuttag / CUT&Tag | 按方法名称及同义写法检索 |
| CUT&RUN | cutrun / CUT&RUN | 按方法名称及同义写法检索 |
| ATAC-seq | atacseq / ATAC-seq | 染色质开放性 |
| 单细胞 RNA-seq | scrnaseq | 方法关键词 + 转录组类型 |
| 单核 RNA-seq | snrnaseq | 方法关键词 + 转录组类型 |
| Hi-C | hic / Hi-C | 染色质构象候选研究 |
| 甲基化测序 | methylation | GEO 高通量甲基化类目 |
| 甲基化芯片 | methylation_array | GEO 甲基化芯片类目 |
| 不限类型／其他方法 | any | 可加 method=PRO-seq 等自定义关键词 |

可选参数：`target`（靶标或组蛋白修饰）、`tissue`（英文组织/细胞类型）、`method`（其他方法关键词）。这些条件是文本过滤，并不自动验证抗体靶标或组织。`disease` 也可以传入细胞系或研究主题，例如 K562。它们仍受原有物种条件限制，默认 Homo sapiens。

一句话示例：

> 使用 GEO 插件查找人类 K562 细胞的 H3K27ac CUT&Tag 数据，technology 指定 CUT&Tag，target 指定 H3K27ac。

> 使用 GEO 插件查找心力衰竭相关的 ATAC-seq 数据，technology 指定 atacseq。

方法检索不强制绑定 GEO 的宽泛实验大类，避免漏掉标为 Other 或混合组学的记录；因此返回的是候选研究，不保证每个 GSM 都是所选方法。核验时 `geo_inspect(samples=true)` 额外提供 extraction/treatment protocol，可结合 characteristics 检查抗体、靶标和对照。

修改已加载插件的 JS 接口后，需要重新加载插件或重启 DSH，新的参数说明才会生效。

原生 Cordis bundle，提供 `geo_search`、`geo_inspect`。依赖电脑已有 Python 3.10+，无第三方 Python 依赖；通过标准工具定义注册到 DSH 的工具服务，无需导入 DSH 私有安装目录中的模块。

安装：先克隆或下载本仓库，并确认 Python 3.10+ 已安装、`python` 命令可用。在 DSH 的插件页选择「添加插件 → 安装第三方插件」，填写解压后的本地目录绝对路径，安装后启用。也可以使用内置 `plugin_manager`，`action: install_bundle`，`target` 为本目录绝对路径。不要手工修改 `.dsh` 配置。安装是否生效以 `application` 和警告为准。目录链接安装后请保留源码目录。

测试提问：

> 使用 geo_search 查询心力衰竭的人类 RNA-seq，limit=500、details=12。优先列出心脏组织 bulk 研究，随后用 geo_inspect 的 samples=true 核验候选研究。报告 GSE、实验设计、GSM 数、测序类型和文件证据。不要把 GSM 数当供体数，不要把 FPKM 当 counts。不要以预先指定的 GSE 代替搜索。

检索通过 NCBI ESearch + ESummary 获取候选，再通过 GEO SOFT 文本接口读取研究和样本。中文心衰关键词自动扩展；其他疾病可传入英文词。实验类目见上表。高通量转录组过滤同时可能召回单细胞、单核与混合 RNA 类型，必须核验。

`limit` 默认 100，最大 500，超过上限的结果标记 `truncated`；`details` 仅对候选排序后的前 N 个读取完整研究。排序基于关键词与组织/对照描述，是可解释启发式，不代表质量。24 小时 URL 缓存、请求间隔和重试用于降低接口压力；清空工作区 `.geo-cache` 可强制刷新。原始 SOFT 缓存在工作区，不含账号凭据。

本版返回文件链接及文件名线索，**未下载验证表达矩阵内容**；不自动推断独立供体、不做差异分析。GSM 的 characteristics 保留原文供模型核验。未知值不补成确定结论。

本地验证：`python -m unittest discover -s tests -v`；联网基准：`python benchmark.py`。参考集 `reference/heart_failure.json` 在实现前由独立 NCBI 网页搜索建立，只有 3 个正例及 1 个技术负例，不代表 GEO 完整金标准。联网报告在 `reports/`。搜索函数不读取参考集；指定 GSE 的元数据核验与搜索召回分别计分。

安装后的实际 DSH 调用与核心联网测试需要分别验证。只通过命令行核心测试不意味着插件已在 DSH 激活。

联网类目冒烟测试：`python test_assays_live.py`，只检索 K562 的 ChIP-seq、CUT&Tag、ATAC-seq 各少量候选。其余类目的查询构造由单元测试覆盖，尚未逐类完成 DSH 验收。

已知限制：宽泛检索和全量样本核验可能耗时较长；`details=0` 只获取候选摘要，适合先做初筛。此版本没有研究用途自动推荐功能。`disease` 的中文自动扩展目前仅覆盖心力衰竭，其他主题建议使用英文。项目不是 DeepSeek 或 NCBI 的官方产品。

代码与原创图标使用 MIT 许可证。GEO 元数据和下载数据仍适用其原始来源的使用条件。仓库不包含本机缓存、应用会话或本地验收日志。
