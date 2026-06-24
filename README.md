---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 05a4cab37a4da1d2d97fa120e9e62602_6a2e76876fab11f1b2f55254006c9bbf
    ReservedCode1: 3c6EXF3xKmZXKGiScyCknIz8+Iar1jwZi3fM1Y4IYiKJDu7riT1nlWqss/6SWzmzr5eyyn9qRyCB5p1z81sEZELzF/8E3BrxukQYnPqe8j6JvsVFAuJstlb50n3qNovzAlW3B0S8EjcJU2s4WOCJDcy8a7vWx+gPSP6P1nS6XCIoHFKJz0VNm7vJKjo=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 05a4cab37a4da1d2d97fa120e9e62602_6a2e76876fab11f1b2f55254006c9bbf
    ReservedCode2: 3c6EXF3xKmZXKGiScyCknIz8+Iar1jwZi3fM1Y4IYiKJDu7riT1nlWqss/6SWzmzr5eyyn9qRyCB5p1z81sEZELzF/8E3BrxukQYnPqe8j6JvsVFAuJstlb50n3qNovzAlW3B0S8EjcJU2s4WOCJDcy8a7vWx+gPSP6P1nS6XCIoHFKJz0VNm7vJKjo=
---

# 小雷没摸鱼agent - 对话式资源AI系统

## 项目简介

一个基于对话交互的资源型AI网页系统。用户在前端对话界面提问，系统从后台资源库中智能匹配并返回相关资源。支持多种文件格式（图片、视频、音频、文档等），支持外部链接。

## 项目结构

```
xiaolei-agent/
├── backend/
│   ├── app.py              # Flask 后端主应用
│   ├── requirements.txt    # Python 依赖
│   ├── data/
│   │   └── resources.json  # 资源元数据存储
│   └── uploads/            # 上传文件存储目录
├── frontend/
│   └── index.html          # 用户对话前端界面
├── admin/
│   └── index.html          # 管理后台界面
├── start.bat               # Windows 一键启动脚本
└── README.md               # 本说明文档
```

## 快速开始

### 环境要求
- Python 3.8+
- 现代浏览器（Chrome / Edge / Firefox）

### 启动步骤

**方式一：一键启动（推荐）**
```
双击运行 start.bat
```

**方式二：手动启动**
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 访问地址

| 界面 | 地址 | 说明 |
|------|------|------|
| 用户前端 | 打开 `frontend/index.html` | 对话搜索界面，无需登录 |
| 管理后台 | 打开 `admin/index.html` | 资源管理，需登录 |
| 后端API | http://localhost:5000 | REST API 服务 |

### 默认管理员账号
- 账号：`admin`
- 密码：`admin123`

## 功能说明

### 用户前端
- 现代化AI聊天界面，蓝紫色渐变科技风
- 输入问题后，系统从资源库中分词匹配并返回相关资源
- 图片资源直接预览，视频支持播放器，音频支持播放，文档支持下载
- 响应式设计，移动端可用

### 管理后台
- 管理员登录认证（JWT Token）
- **文件上传**：支持拖拽上传和点击上传，支持批量
- **链接添加**：添加外部链接资源
- **资源列表**：表格展示所有资源，支持搜索和类型筛选
- **资源删除**：删除资源及其对应文件
- **统计面板**：展示资源总数、文件数、链接数、总大小

### 支持的格式
- **图片**：jpg, jpeg, png, gif, bmp, webp, svg
- **视频**：mp4, avi, mov, mkv, webm
- **音频**：mp3, wav, flac, ogg, wma
- **文档**：pdf, doc, docx, xls, xlsx, ppt, pptx, txt, csv
- **压缩包**：zip, rar, 7z

### API 接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /api/admin/login | 管理员登录 | 否 |
| GET | /api/admin/verify | 验证Token | 否 |
| POST | /api/search | 对话搜索资源 | 否 |
| GET | /api/resources | 资源列表 | 是 |
| POST | /api/resources | 添加链接 | 是 |
| PUT | /api/resources/:id | 编辑资源 | 是 |
| DELETE | /api/resources/:id | 删除资源 | 是 |
| POST | /api/upload | 上传文件 | 是 |
| GET | /api/stats | 统计数据 | 是 |

## 技术栈

- **后端**：Python Flask + JWT
- **前端**：原生 HTML/CSS/JS（无框架依赖）
- **搜索**：自定义中文分词 + 多字段模糊匹配 + 加权评分

## 注意事项

1. 首次启动时，`resources.json` 和 `uploads/` 目录会自动创建
2. 后端默认监听 `0.0.0.0:5000`，如需修改端口请编辑 `app.py`
3. 前端通过 `fetch` 访问 `http://localhost:5000`，部署时需修改 API_BASE
*（内容由AI生成，仅供参考）*
