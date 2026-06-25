# -*- coding: utf-8 -*-
"""
小雷没摸鱼agent - 后端服务
Flask REST API + JWT认证 + 资源管理 + 智能搜索
"""
import os
import re
import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, supports_credentials=True)

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
RESOURCES_FILE = os.path.join(DATA_FOLDER, 'resources.json')
JWT_SECRET = 'xiaolei-agent-secret-key-2024'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# 管理员账号
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    # 图片
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico',
    'tiff', 'tif', 'raw', 'cr2', 'nef', 'dng', 'arw', 'heic', 'heif',
    'psd', 'ai', 'eps', 'cdr', 'indd', 'xcf', 'psb', 'orf', 'rw2',
    'pef', 'raf', 'srw', 'x3f', 'jp2', 'j2k', 'jxr', 'hdp', 'wdp',
    # 视频
    'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv', 'mts', 'm2ts',
    'ts', 'vob', '3gp', 'ogv', 'rmvb', 'rm', 'asf', 'mpeg', 'mpg',
    'mod', 'tod', 'f4v', 'm4v', 'divx', 'xvid',
    # 音频
    'mp3', 'wav', 'flac', 'ogg', 'wma', 'aac', 'm4a', 'aiff', 'alac',
    'ape', 'mid', 'midi', 'amr', 'opus', 'mka', 'ac3', 'dts', 'wv',
    'ra', 'm3u', 'caf', 'pcm', 'au',
    # 文档
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv',
    'md', 'rtf', 'odt', 'ods', 'odp', 'epub', 'mobi', 'azw3', 'djvu',
    'tex', 'pages', 'numbers', 'key', 'log', 'xml', 'html', 'htm',
    # 压缩归档
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'iso', 'cab', 'arj',
    'lz', 'lz4', 'zst', 'tgz', 'tbz2', 'txz', 'lzh', 'ace', 'uue',
    # 3D / 设计
    'c4d', 'blend', 'fbx', 'obj', 'stl', '3ds', 'max', 'mb', 'ma',
    'glb', 'gltf', 'dae', 'usd', 'usdz', 'pz3', 'step', 'stp', 'iges',
    'igs', 'ply', 'abc', 'skp', '3mf', 'amf', 'wrl', 'vrml',
    # 代码 / 脚本
    'js', 'ts', 'jsx', 'tsx', 'py', 'java', 'c', 'cpp', 'h', 'hpp',
    'go', 'rs', 'swift', 'kt', 'php', 'rb', 'r', 'sql', 'sh', 'bat',
    'ps1', 'yml', 'yaml', 'toml', 'ini', 'cfg', 'conf', 'env', 'css',
    'scss', 'less', 'sass', 'vue', 'svelte',
    # 字体
    'ttf', 'otf', 'woff', 'woff2', 'eot',
    # 可执行 / 应用包
    'exe', 'msi', 'apk', 'dmg', 'pkg', 'ipa', 'deb', 'rpm',
    # 数据库
    'db', 'sqlite', 'sqlite3', 'mdb', 'accdb',
}

# 文件类型分类
FILE_TYPE_MAP = {
    'image': {'jpg','jpeg','png','gif','bmp','webp','svg','ico',
              'tiff','tif','raw','cr2','nef','dng','arw','heic','heif',
              'psd','ai','eps','cdr','indd','xcf','psb','orf','rw2',
              'pef','raf','srw','x3f','jp2','j2k','jxr','hdp','wdp'},
    'video': {'mp4','avi','mov','mkv','webm','flv','wmv','mts','m2ts',
              'ts','vob','3gp','ogv','rmvb','rm','asf','mpeg','mpg',
              'mod','tod','f4v','m4v','divx','xvid'},
    'audio': {'mp3','wav','flac','ogg','wma','aac','m4a','aiff','alac',
              'ape','mid','midi','amr','opus','mka','ac3','dts','wv',
              'ra','m3u','caf','pcm','au'},
    '3d': {'c4d','blend','fbx','obj','stl','3ds','max','mb','ma',
           'glb','gltf','dae','usd','usdz','pz3','step','stp','iges',
           'igs','ply','abc','skp','3mf','amf','wrl','vrml'},
    'document': {'pdf','doc','docx','xls','xlsx','ppt','pptx','txt','csv',
                 'md','rtf','odt','ods','odp','epub','mobi','azw3','djvu',
                 'tex','pages','numbers','key','log','xml','html','htm'},
    'archive': {'zip','rar','7z','tar','gz','bz2','xz','iso','cab','arj',
                'lz','lz4','zst','tgz','tbz2','txz','lzh','ace','uue'},
    'code': {'js','ts','jsx','tsx','py','java','c','cpp','h','hpp',
             'go','rs','swift','kt','php','rb','r','sql','sh','bat',
             'ps1','yml','yaml','toml','ini','cfg','conf','env','css',
             'scss','less','sass','vue','svelte'},
}

def get_file_category(ext):
    ext = ext.lower().lstrip('.')
    for cat, exts in FILE_TYPE_MAP.items():
        if ext in exts:
            return cat
    return 'other'

def load_resources():
    if not os.path.exists(RESOURCES_FILE):
        return []
    with open(RESOURCES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_resources(data):
    with open(RESOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# ========== JWT 简易实现 ==========
def create_jwt_token(username):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "username": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400 * 7  # 7天过期
    }
    header_b64 = _b64_encode(json.dumps(header))
    payload_b64 = _b64_encode(json.dumps(payload))
    signature = hashlib.sha256(f"{header_b64}.{payload_b64}.{JWT_SECRET}".encode()).hexdigest()
    return f"{header_b64}.{payload_b64}.{signature}"

def verify_jwt_token(token):
    parts = token.split('.')
    if len(parts) != 3:
        return None
    header_b64, payload_b64, signature = parts
    expected_sig = hashlib.sha256(f"{header_b64}.{payload_b64}.{JWT_SECRET}".encode()).hexdigest()
    if signature != expected_sig:
        return None
    payload = json.loads(_b64_decode(payload_b64))
    if payload.get('exp', 0) < time.time():
        return None
    return payload

def _b64_encode(s):
    import base64
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')

def _b64_decode(s):
    import base64
    s += '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s).decode()

def require_admin(f):
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({"error": "未授权访问，请先登录"}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


# ========== 管理层 API ==========
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    if username == ADMIN_USERNAME and hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
        token = create_jwt_token(username)
        return jsonify({"success": True, "token": token, "username": username})
    return jsonify({"success": False, "error": "账号或密码错误"}), 401


@app.route('/api/admin/verify', methods=['GET'])
def admin_verify():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
    payload = verify_jwt_token(token)
    if payload:
        return jsonify({"success": True, "username": payload['username']})
    return jsonify({"success": False}), 401


# ========== 资源 CRUD ==========
@app.route('/api/resources', methods=['GET'])
@require_admin
def list_resources():
    resources = load_resources()
    # 支持搜索
    q = request.args.get('q', '').strip()
    file_type = request.args.get('type', '').strip()
    if q:
        q_lower = q.lower()
        resources = [r for r in resources if
                     q_lower in r.get('title','').lower() or
                     q_lower in r.get('description','').lower() or
                     q_lower in r.get('tags','').lower() or
                     q_lower in r.get('filename','').lower()]
    if file_type:
        resources = [r for r in resources if r.get('file_type','') == file_type]
    return jsonify({"success": True, "data": resources, "total": len(resources)})


@app.route('/api/resources', methods=['POST'])
@require_admin
def add_link():
    """添加链接资源"""
    data = request.json
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    description = data.get('description', '').strip()
    tags = data.get('tags', '').strip()
    if not title or not url:
        return jsonify({"success": False, "error": "标题和链接不能为空"}), 400
    resources = load_resources()
    resource = {
        "id": str(uuid.uuid4()),
        "title": title,
        "url": url,
        "description": description,
        "tags": tags,
        "resource_type": "link",
        "file_type": "link",
        "filename": "",
        "file_size": 0,
        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    resources.append(resource)
    save_resources(resources)
    return jsonify({"success": True, "data": resource})


@app.route('/api/resources/<resource_id>', methods=['DELETE'])
@require_admin
def delete_resource(resource_id):
    resources = load_resources()
    target = None
    for r in resources:
        if r['id'] == resource_id:
            target = r
            break
    if not target:
        return jsonify({"success": False, "error": "资源不存在"}), 404
    # 删除物理文件
    if target.get('resource_type') == 'file' and target.get('filename'):
        fpath = os.path.join(UPLOAD_FOLDER, target['filename'])
        if os.path.exists(fpath):
            os.remove(fpath)
    resources = [r for r in resources if r['id'] != resource_id]
    save_resources(resources)
    return jsonify({"success": True, "message": "删除成功"})


@app.route('/api/upload', methods=['POST'])
@require_admin
def upload_file():
    if 'files' not in request.files:
        return jsonify({"success": False, "error": "未选择文件"}), 400
    files = request.files.getlist('files')
    # 从表单读取自定义名称和标签
    custom_title = request.form.get('title', '').strip()
    custom_tags = request.form.get('tags', '').strip()
    custom_desc = request.form.get('description', '').strip()
    resources = load_resources()
    uploaded = []
    single_file = len(files) == 1
    for file in files:
        if file.filename == '':
            continue
        if not allowed_file(file.filename):
            uploaded.append({"filename": file.filename, "error": "不支持的文件格式"})
            continue
        original_name = file.filename
        ext = original_name.rsplit('.', 1)[1].lower()
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, safe_name))
        file_size = os.path.getsize(os.path.join(UPLOAD_FOLDER, safe_name))
        category = get_file_category(ext)
        # 单个文件时使用自定义名称，多文件时用文件名
        title = custom_title if single_file and custom_title else original_name.rsplit('.', 1)[0]
        resource = {
            "id": str(uuid.uuid4()),
            "title": title,
            "filename": safe_name,
            "original_name": original_name,
            "url": f"/api/file/{safe_name}",
            "file_size": file_size,
            "file_type": category,
            "file_ext": ext,
            "description": custom_desc if single_file else "",
            "tags": custom_tags,
            "resource_type": "file",
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        resources.append(resource)
        uploaded.append({"filename": original_name, "success": True, "resource": resource})
    save_resources(resources)
    return jsonify({"success": True, "data": uploaded})


@app.route('/api/file/<filename>')
def serve_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ========== 前端对话搜索 API ==========
COMMON_STOPWORDS = {'的','了','在','是','我','有','和','就','不','人','都','一','一个','上','也','很','到','说',
                    '要','去','你','会','着','没有','看','好','自己','这','他','她','它','们','那','些','什么',
                    '怎么','如何','哪些','哪个','哪里','怎样','为什么','因为','所以','如果','虽然','但是',
                    '可以','能','会','要','想','需要','应该','必须','可能','已经','还','又','再','才','就',
                    '把','被','让','给','对','从','在','向','关于','为','为了','除了','跟','与','或','和',
                    '吗','呢','吧','啊','哦','嗯','么','呀','请','帮我','找','一下','看看','有没有','有没有什么',
                    '有没有人','告诉我','知道','知道吗','吗','呢','吧','啊','嗯'}

def tokenize(text):
    """中文分词（简易jieba风格）"""
    text = text.lower().strip()
    # 去除标点
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9 ]', ' ', text)
    tokens = []
    # 中文按字符切分后做bigram
    chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)
    for i in range(len(chinese_chars)):
        if len(chinese_chars[i]) > 0:
            tokens.append(chinese_chars[i])
    # bigram
    for i in range(len(chinese_chars) - 1):
        tokens.append(chinese_chars[i] + chinese_chars[i+1])
    # 英文单词
    english_words = re.findall(r'[a-zA-Z0-9]+', text)
    for w in english_words:
        if len(w) >= 2:
            tokens.append(w)
    # 过滤停用词和短词
    tokens = [t for t in tokens if t not in COMMON_STOPWORDS and len(t) >= 1]
    return tokens

def match_score(query, resource):
    """计算资源与查询的匹配分数"""
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0
    # 构建搜索文本
    search_text = f"{resource.get('title','')} {resource.get('description','')} {resource.get('tags','')} {resource.get('original_name','')} {resource.get('filename','')}"
    search_text_lower = search_text.lower()
    search_tokens = tokenize(search_text)
    score = 0
    for qt in query_tokens:
        if qt in search_text_lower:
            score += 2
        if qt in search_tokens:
            score += 1
    # title匹配加权
    title_lower = resource.get('title','').lower()
    for qt in query_tokens:
        if qt in title_lower:
            score += 3
    return score


@app.route('/api/search', methods=['POST'])
def search_resources():
    data = request.json
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"success": True, "data": [], "message": "请输入问题"})
    resources = load_resources()
    if not resources:
        return jsonify({"success": True, "data": [], "message": "资源库暂时为空，请联系管理员添加资源"})
    # 计算匹配分数
    scored = []
    for r in resources:
        s = match_score(query, r)
        scored.append((s, r))
    # 按分数降序排列
    scored.sort(key=lambda x: x[0], reverse=True)
    # 返回分数>0的前10条
    results = [r for s, r in scored if s > 0][:10]
    if not results:
        return jsonify({"success": True, "data": [], "message": "未找到匹配的资源，请尝试换个方式提问"})
    return jsonify({"success": True, "data": results, "total": len(results)})


# ========== 资源编辑 API ==========
@app.route('/api/resources/<resource_id>', methods=['PUT'])
@require_admin
def update_resource(resource_id):
    data = request.json
    resources = load_resources()
    for r in resources:
        if r['id'] == resource_id:
            if 'title' in data: r['title'] = data['title']
            if 'description' in data: r['description'] = data['description']
            if 'tags' in data: r['tags'] = data['tags']
            if 'url' in data: r['url'] = data['url']
            save_resources(resources)
            return jsonify({"success": True, "data": r})
    return jsonify({"success": False, "error": "资源不存在"}), 404


@app.route('/api/stats', methods=['GET'])
@require_admin
def get_stats():
    resources = load_resources()
    total = len(resources)
    files = sum(1 for r in resources if r.get('resource_type') == 'file')
    links = sum(1 for r in resources if r.get('resource_type') == 'link')
    total_size = sum(r.get('file_size', 0) for r in resources)
    return jsonify({
        "success": True,
        "data": {
            "total": total,
            "files": files,
            "links": links,
            "total_size": total_size
        }
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
