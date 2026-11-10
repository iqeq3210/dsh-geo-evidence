<p align="center">
  <img src="./icon.svg" width="80" height="80" alt="GEO Evidence logo" />
</p>

<h1 align="center">GEO Evidence</h1>

<p align="center">
  <strong>在 DeepSeek Harness 里，用一句话查找 GEO 组学数据</strong>
</p>

<p align="center">
  RNA-seq · ChIP-seq · CUT&Tag · CUT&RUN · ATAC-seq · Hi-C
</p>

<p align="center">
  <a href="https://github.com/deepseek-ai/deepseek-harness"><img src="https://img.shields.io/badge/DeepSeek_Harness-Plugin-125c65?style=flat-square" alt="DeepSeek Harness plugin" /></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10 or newer" />
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-16876b?style=flat-square" alt="MIT license" /></a>
</p>

<p align="center">
  <a href="#一句话开始">使用示例</a> ·
  <a href="#快速安装">快速安装</a> ·
  <a href="#支持哪些数据">数据类型</a> ·
  <a href="#工具与参数">工具参数</a> ·
  <a href="#常见问题">常见问题</a>
</p>

---

**GEO Evidence**（`dsh-geo-evidence`）是 DeepSeek Harness 的原生组学数据检索插件。告诉 Agent 研究主题、物种和实验类型，它可以搜索 NCBI GEO，返回研究编号、实验设计、样本信息和数据文件入口。

从寻找心衰 RNA-seq 队列，到查找 K562 的 H3K27ac CUT&Tag 数据，都可以在同一个对话里完成。

> 无需额外配置 GEO API Key，无第三方 Python 依赖。使用 DSH 已配置的模型理解需求，通过 NCBI 公共接口检索数据。

## 一句话开始

安装后，直接在 DSH 对话中说：

| 你想做什么 | 可以这样说 |
| :--- | :--- |
| 🧬 查找转录组 | 使用 GEO 插件查找人类心力衰竭相关的心脏组织 RNA-seq 数据。 |
| 🎯 指定靶标 | 查找人类 K562 细胞的 H3K27ac CUT&Tag 数据，列出研究编号和文件入口。 |
| 🔓 查找开放染色质 | 使用 GEO 插件检索心力衰竭相关的 ATAC-seq 数据。 |
| 🧪 查找蛋白结合 | 查找人类 K562 细胞的 CTCF ChIP-seq 数据。 |
| 🔬 查找单细胞数据 | 使用 GEO 插件查找心力衰竭相关的单核 RNA-seq 研究。 |
| 📋 核验一个研究 | 用 GEO 插件查看 GSE116250 的样本分组、实验设计和补充文件。 |

**想先看少量候选？** 可以明确限制初筛范围：

> 用 `geo_search` 搜索人类心力衰竭 RNA-seq，`limit=20`、`details=0`。先从结果中列出最多 5 个相关候选，不下载文件，不逐样本核验。

先初筛，再选择具体 GSE 深入查看。候选数量与相关性取决于检索结果。

## 快速安装

### 1. 准备环境

已安装 **DeepSeek Harness**，并配置好普通对话使用的模型；已安装 **Python 3.10+**，DSH 的运行环境可以执行 `python`，并能访问 NCBI 公共接口。

```bash
python --version
```

### 2. 下载源码

```bash
git clone https://github.com/iqeq3210/dsh-geo-evidence.git
```

也可以在本仓库点击 **Code → Download ZIP**，解压后使用。

### 3. 安装并启用

打开 DSH 的 **插件 → 添加插件 → 安装第三方插件**，填写源码目录的绝对路径，安装后启用 **GEO 组学检索与核验**。

选择的目录应直接包含 `package.json`、`index.js` 和 `cordis.patch.yml`。本地目录链接安装后，请保留源码目录。

重新加载插件或重启 DSH，然后发送上面的任意一句检索示例即可。

<details>
<summary><strong>DSH Web / CLI 安装方式</strong></summary>

如果环境中已有 `dsh` 命令，可以从 GitHub 安装到 Web profile：

```bash
dsh plugin --profile web add github:iqeq3210/dsh-geo-evidence
```

该方式要求仓库根目录存在插件文件。当前版本已在 Windows 版 DSH 中通过本地目录安装测试；其他环境及 GitHub 直装仍需在你的环境中验证。

</details>

## 支持哪些数据

在对话中说出方法名称，或通过 `technology` 参数指定：

| 研究方向 | 实验类型 | 参数值 |
| :--- | :--- | :--- |
| **基因表达** | RNA-seq、表达芯片 | `rnaseq`、`array` |
| **单细胞表达** | 单细胞 / 单核 RNA-seq | `scrnaseq`、`snrnaseq` |
| **蛋白结合与修饰** | ChIP-seq、CUT&Tag、CUT&RUN | `chipseq`、`cuttag`、`cutrun` |
| **染色质开放性** | ATAC-seq | `atacseq` |
| **染色质构象** | Hi-C | `hic` |
| **DNA 甲基化** | 甲基化测序、甲基化芯片 | `methylation`、`methylation_array` |
| **其他方法** | 不限实验大类，附加自定义方法词 | `any` + `method` |

`ChIP-seq`、`CUT&Tag`、`CUT&RUN`、`ATAC-seq` 等常见写法也可直接作为参数。

> **表达芯片 ≠ ChIP-seq。** 混合组学研究可能包含多种实验，命中一个 GSE 不代表其全部 GSM 都属于指定方法。

## 返回哪些信息

| 信息 | 你能看到什么 |
| :--- | :--- |
| **研究来源** | GSE 编号、标题、GEO 页面和可复现的检索式 |
| **实验设计** | 研究摘要、分组描述、实验类型和平台 |
| **样本证据** | GSM 数量；深入核验时可查看样本特征、建库策略和实验处理流程 |
| **数据入口** | 补充文件链接，以及 GEO 记录中的 SRA / BioProject 关联 |
| **使用提示** | 归一化表达文件线索、混合实验提醒，以及尚未验证的事项 |

文件类型提示来自元数据和文件名，**不表示已下载并检查文件内容**。例如，名为 `count_data` 的文件只会标记为 counts 候选。

## 工具与参数

**`geo_search` 发现研究，`geo_inspect` 核验选中的研究。**

<details>
<summary><strong>geo_search · 检索参数与示例</strong></summary>

| 参数 | 用途 | 默认值 |
| :--- | :--- | :--- |
| `disease` | 必填；疾病、细胞系或研究主题 | — |
| `organism` | 物种名称 | `Homo sapiens` |
| `technology` | 实验类型，见上表 | `rnaseq` |
| `target` | 靶标或修饰，例如 `CTCF`、`H3K27ac` | 不限制 |
| `tissue` | 英文组织或细胞类型 | 不限制 |
| `method` | 自定义方法词，例如 `PRO-seq` | 不限制 |
| `limit` | 候选数量上限，范围 1–500 | `100` |
| `details` | 读取前多少项候选的研究详情，范围 0–limit | `20` |

```json
{
  "disease": "K562",
  "organism": "Homo sapiens",
  "technology": "cuttag",
  "target": "H3K27ac",
  "limit": 20,
  "details": 3
}
```

附加条件是文本筛选，不是已核实的样本标签。中文主题目前只对“心力衰竭”内置英文同义词扩展，其他主题建议使用英文。

</details>

<details>
<summary><strong>geo_inspect · 研究与样本核验</strong></summary>

| 参数 | 用途 | 默认值 |
| :--- | :--- | :--- |
| `accession` | 必填；GSE 编号 | — |
| `samples` | 是否读取全部 GSM 元数据 | `false` |

```json
{
  "accession": "GSE116250",
  "samples": true
}
```

`samples=true` 会读取整组样本，较大的研究可能耗时较长、输出较多。建议选中研究后再使用。

</details>

## 常见问题

**为什么有时检索很慢？**  
宽泛检索、详情读取和全量样本核验都会增加等待。先用较小的 `limit` 和 `details=0` 初筛，再核验选中的 GSE。URL 缓存有效期为 24 小时，重复查询可能直接使用缓存。

**能直接推荐 WGCNA 或 biomarker 队列吗？**  
当前提供检索与证据核验，没有专门的用途推荐工具。Agent 可以提出候选，但仍需核实独立供体数、表型、批次和队列重叠情况。

**GSM 数量等于患者数量吗？**  
不一定。同一供体可能有多种实验、重复取样或技术重复。FPKM / RPKM / TPM 也不等于原始 counts。

**查询和数据会去哪里？**  
查询条件发送给 NCBI，返回的元数据缓存在本地 `.geo-cache/`。模型对话和工具结果由 DSH 及你配置的模型服务处理。插件不要求独立 API Key，不设置第三方中转服务。

**可以直接作为 MCP 安装吗？**  
这是 DSH 原生 Cordis 插件，当前没有单独的 MCP 服务。Python 检索核心位于 `geo_plugin/`。

## 开发与验证

```bash
python -m unittest discover -s tests -v
node --check index.js
```

<details>
<summary><strong>联网测试与项目结构</strong></summary>

以下命令会访问 NCBI；心衰基准还会读取参考研究的完整样本元数据：

```bash
python test_assays_live.py
python benchmark.py
```

- 类目冒烟测试：K562 的 ChIP-seq、CUT&Tag、ATAC-seq。
- 心衰参考集：3 个 RNA-seq 正例、1 个芯片技术负例，见 `reference/heart_failure.json`。
- 排序在已知参考集上开发，不代表盲测或全库召回率。其余类目未逐项完成联网和 DSH 验收。
- 测试报告生成到本地 `reports/`，不随源码分发。

```text
dsh-geo-evidence/
├── index.js               # DSH 工具注册与 Python 调用
├── cordis.patch.yml       # 插件组合配置
├── geo_plugin/            # GEO 检索与 SOFT 解析
├── locale/                # 中英文插件说明
├── tests/                 # 单元测试
└── reference/             # 小型参考测试集
```

</details>

欢迎通过 [Issues](https://github.com/iqeq3210/dsh-geo-evidence/issues) 反馈问题或建议。请提供复现步骤，并移除密钥、私人样本信息及敏感路径。

## License

[MIT](./LICENSE)。代码与原创图标按 MIT 许可证提供，GEO 数据遵循原始来源的使用条件。本项目是社区插件，与 DeepSeek、NCBI 无官方隶属关系。
