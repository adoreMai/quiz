# 题库练习系统 (Quiz Practice)

> 一站式开源刷题平台，纯静态、零依赖、GitHub Pages 一键部署。支持多学科切换，换题库只需替换 JSON 文件。

在线地址：[adoremai.github.io/quiz](https://adoremai.github.io/quiz/) | 开源仓库：[github.com/adoreMai/quiz](https://github.com/adoreMai/quiz)

## 功能

| 模式 | 说明 |
|------|------|
| **考试** | 按章节占比随机抽题，题型数量与分值可自定义，限时可调。 |
| **背题** | 全部题目直接显示答案，可按章节、题型筛选。 |
| **逐章测试** | 按章节逐题练习，进度自动保存至浏览器（localStorage）。 |
| **错题本** | 做错的题自动收录，支持筛选、复习、逐题移除。 |

## 文件结构

```
quiz/
├── index.html              # 主页面（纯静态、零依赖）
├── subjects.json           # 学科注册表（含考试配置）
├── subjects/
│   ├── 共同体概论.json      # 中华民族共同体概论（1754题/17章）
│   ├── 大学语文.json         # 大学语文各课测试题（124题/9章）
│   └── 明德英语B2.json       # 明德英语B2（165题/5章）
├── clean.py                # 超星学习通题库清洗脚本
├── extract_dxyw.py         # Word 文档题库提取脚本
├── CHANGELOG.md            # 更新日志与公告
├── README.md
├── LICENSE
├── robots.txt
└── .gitignore
```

## 当前题库

| 学科 | 题数 | 章数 | 题型 |
|------|------|------|------|
| 中华民族共同体概论 | 1754 | 17 | 单选、多选、判断、填空 |
| 大学语文各课测试题 | 124 | 9 | 单选、多选、判断、填空、简答、古文今译 |
| 明德英语B2 | 165 | 5 | 选词填空、汉译英、英译汉、写作 |

## 添加新学科

### 1. 准备题库 JSON

在 `subjects/` 目录下创建题库文件，格式如下：

```json
[
  {
    "chapter": "第一章",
    "sections": [
      {
        "type": "章节测验",
        "questions": [
          {
            "index": 1,
            "type": "单选题",
            "content": "题目正文",
            "options": [
              { "label": "A", "text": "选项A" },
              { "label": "B", "text": "选项B" }
            ],
            "answer": "B"
          }
        ]
      }
    ]
  }
]
```

**支持的客观题型**（渲染为选项按钮、自动计分）：`单选题`、`多选题`、`判断题`、`选词填空`

**支持的主观题型**（渲染为文本输入框、不计分、含 AI 警告标识）：`简答题`、`论述题`、`填空题`、`古文今译题`、`汉译英`、`英译汉`、`写作`

### 2. 注册学科

在 `subjects.json` 中添加一条配置：

```json
{
  "id": "英语四级",
  "name": "大学英语四级题库",
  "shortName": "英语四级",
  "file": "subjects/英语四级.json",
  "author": "",
  "university": "",
  "profession": "",
  "questionCount": 1200,
  "chapters": 12
}
```

### 3. （可选）考试模式自定义配置

如果学科需要按特定规则抽题（例如英语题库按 Section A/B/C 分别抽题），可在 `subjects.json` 中添加 `examConfig` 字段：

```json
"examConfig": {
  "scored": [
    { "type": "选词填空", "section": "Section A", "count": 1, "score": 10 },
    { "type": "选词填空", "section": "Section B", "count": 1, "score": 10 },
    { "type": "选词填空", "section": "Section C", "count": 1, "score": 10 }
  ],
  "unscored": [
    { "type": "汉译英", "count": 1 },
    { "type": "英译汉", "count": 1 }
  ],
  "timeMinutes": 60
}
```

- `scored`：从指定 type + section 的题目池中随机抽取 count 道，每题分值 score
- `unscored`：从指定 type 的题目池中随机抽取，不计分
- 不配置 `examConfig` 的学科沿用默认逻辑（按章节占比抽题，题型和数量由用户自定义）

### 4. 刷新页面

页面顶部下拉框自动出现新学科，切换即可使用。

## 部署到 GitHub Pages

1. Fork 此仓库
2. 修改 `index.html` 中的 `REPO_ISSUES_URL` 为你的仓库 Issues 地址
3. 仓库 Settings → Pages → Source 选 main 分支，目录选 `/ (root)`
4. 访问 `https://你的用户名.github.io/quiz/`

## 工具脚本

### clean.py — 超星学习通题库清洗

将超星学习通导出的 txt 题库清洗为标准 JSON 格式。内置字符映射修复乱码、章节命名统一、冗余字段去除。

```bash
python clean.py
```

### extract_dxyw.py — Word 文档题库提取

从 .docx/.doc 格式的试题文档中提取结构化题库数据。

```bash
python extract_dxyw.py
```

## 贡献题库

如果你有整理好的题库，欢迎贡献！点击页面底部的「贡献题库」按钮，或通过 GitHub Issues 联系。

提交内容：题库 JSON 文件、学科名称、所属大学/专业（选填）。审核通过后加入系统。

也欢迎 Fork 本项目自行搭建。

## 反馈

- **GitHub Issues**：点击页面底部的「提交反馈」链接，自动填入题目信息
- **微信**：m228120520
