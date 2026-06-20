# 题库练习系统 (Quiz Practice)

> 一站式开源刷题平台，任何学校/专业都能自建题库：`https://github.com/adoreMai/quiz` — 支持清洗超星数据、一键部署、多学科切换，有题库可以发我后台更新，方便的话可以给我点一个 Star ⭐

纯静态、零依赖的刷题网站。支持多学科切换，**考试、背题、逐章测试、错题本**四种模式。数据由 JSON 驱动，换题库只需替换 JSON 文件。

## 功能

| 模式 | 说明 |
|------|------|
| **考试** | 按章节占比抽题，题型数量和每题分值可自定义。限时可调。 |
| **背题** | 全部题目直接显示答案，可按章节/题型筛选。 |
| **测试** | 按章节逐题练习，进度自动保存（localStorage）。 |
| **错题本** | 做错的题自动收录，可筛选、复习、清空。 |

## 文件结构

```
quiz/
├── index.html              # 主页面（纯静态、零依赖）
├── subjects.json           # 学科列表配置
├── subjects/
│   ├── 共同体概论.json      # 共同体概论题库（1550题/16章）
│   └── 大学语文.json         # 大学语文题库（124题/9章）
├── clean.py                # 超星学习通题库清洗脚本
├── extract_dxyw.py         # Word文档题库提取脚本
├── CHANGELOG.md            # 更新日志
├── README.md
└── .gitignore
```

## 添加新学科

1. 准备题库 JSON 文件（格式见下方），放入 `subjects/` 目录
2. 在 `subjects.json` 中添加一行配置：

```json
{
  "id": "英语四级",
  "name": "大学英语四级题库",
  "shortName": "英语四级",
  "file": "subjects/英语四级.json",
  "author": "张三",
  "university": "某某大学",
  "profession": "英语",
  "questionCount": 1200,
  "chapters": 12
}
```

3. 刷新页面即可在顶部下拉框切换到新学科

题库名称会同时出现在页面标题和浏览器标签页。

## 题库 JSON 格式

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

支持的题型：`单选题`、`多选题`、`判断题`、`简答题`、`论述题`、`填空题`

## 部署到 GitHub Pages

1. Fork 此仓库（或直接使用）
2. 修改 `index.html` 中的 `REPO_ISSUES_URL` 为你的仓库 Issues 地址
3. 在仓库 Settings → Pages 中启用，Source 选 main 分支，目录选 `/ (root)`
4. 访问 `https://你的用户名.github.io/quiz/`

## 数据清洗工具

### clean.py — 超星学习通题库清洗

将超星学习通导出的 txt 题库清洗为标准 JSON 格式。内置字符映射修复乱码、章节命名统一、冗余字段去除等功能。

```bash
python clean.py
```

### extract_dxyw.py — Word 文档题库提取

从 .docx / .doc 格式的试题文档中提取结构化题库数据。

```bash
python extract_dxyw.py
```

## 贡献题库

如果你有整理好的题库希望加入系统，欢迎贡献！点击页面底部的"贡献题库"按钮，或直接通过以下方式联系：

- **邮箱**：zs125656423@qq.com
- **微信**：m228120520

提交时请附上：题库 JSON 文件、学科名称、所属大学（可选）、专业名称（可选）。审核通过后会被加入到系统中。

也欢迎自行 Fork 本项目进行二次开发，搭建属于自己学校/专业的刷题平台。

## 反馈

- **GitHub Issues**：点击页面底部的"提交反馈"链接，自动填入题目信息
- **邮箱**：zs125656423@qq.com
- **微信**：m228120520

不会使用 GitHub 或没有账号的同学，可以通过邮箱或微信直接联系我反馈问题。
