# -*- coding: utf-8 -*-
"""
企业微信消息加解密模块 (AES-256-CBC)

实现企业微信群机器人回调接口的消息加解密和签名验证。
参考: https://developer.work.weixin.qq.com/document/path/90968
"""
import base64
import hashlib
import json
import os
import random
import string
import struct
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'wework_config.json')


def load_config():
    """加载企业微信配置文件"""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"企业微信配置文件不存在: {CONFIG_FILE}")
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_token(length=32):
    """生成随机 Token（32位，a-zA-Z0-9）"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def generate_encoding_aes_key(length=43):
    """生成随机 EncodingAESKey（43位，a-zA-Z0-9）"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def _get_aes_key(encoding_aes_key):
    """将 43 位 EncodingAESKey 解码为 32 字节 AES 密钥"""
    key = encoding_aes_key + '='
    return base64.b64decode(key)


def _compute_signature(token, timestamp, nonce, encrypt_msg):
    """
    计算消息签名（SHA1）
    
    参数:
        token: 企业微信 Token
        timestamp: 时间戳
        nonce: 随机字符串
        encrypt_msg: 加密的消息内容
    
    返回:
        SHA1 签名字符串（小写十六进制）
    """
    params = sorted([token, timestamp, nonce, encrypt_msg])
    joined = ''.join(params)
    return hashlib.sha1(joined.encode('utf-8')).hexdigest()


def verify_signature(token, timestamp, nonce, msg_encrypt, msg_signature):
    """
    验证消息签名
    
    参数:
        token: 企业微信 Token
        timestamp: 时间戳
        nonce: 随机字符串
        msg_encrypt: 加密的消息密文
        msg_signature: 企业微信传来的签名
    
    返回:
        bool: 签名是否匹配
    """
    computed = _compute_signature(token, timestamp, nonce, msg_encrypt)
    return computed == msg_signature


def decrypt_message(encoding_aes_key, msg_encrypt, corp_id):
    """
    解密企业微信回调消息
    
    密文格式: Base64(AES-256-CBC-Encrypt(random_16_bytes + msg_len_4_bytes_network_order + msg + corp_id))
    
    参数:
        encoding_aes_key: 43位 EncodingAESKey
        msg_encrypt: Base64 编码的密文
        corp_id: 企业 CorpID（用于校验接收方）
    
    返回:
        str: 解密后的明文 XML 字符串
    """
    aes_key = _get_aes_key(encoding_aes_key)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv=aes_key[:16])

    ciphertext = base64.b64decode(msg_encrypt)
    plaintext = cipher.decrypt(ciphertext)

    # 去除 PKCS7 填充
    plaintext = unpad(plaintext, AES.block_size, style='pkcs7')

    # 解析: random(16) + msg_len(4) + msg + receiveid
    random_bytes = plaintext[:16]
    msg_len_bytes = plaintext[16:20]
    msg_len = struct.unpack('!I', msg_len_bytes)[0]  # network byte order (big-endian)
    msg = plaintext[20:20 + msg_len].decode('utf-8')
    receive_id = plaintext[20 + msg_len:].decode('utf-8')

    # 校验 receive_id 是否匹配
    if receive_id != corp_id:
        raise ValueError(f"CorpID 不匹配: 期望 {corp_id}, 实际 {receive_id}")

    return msg


def encrypt_message(encoding_aes_key, msg, corp_id):
    """
    加密企业微信回复消息
    
    参数:
        encoding_aes_key: 43位 EncodingAESKey
        msg: 明文 XML 字符串
        corp_id: 企业 CorpID
    
    返回:
        str: Base64 编码的密文
    """
    aes_key = _get_aes_key(encoding_aes_key)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv=aes_key[:16])

    # 构造明文: random(16) + msg_len(4) + msg + corp_id
    random_bytes = os.urandom(16)
    msg_bytes = msg.encode('utf-8')
    msg_len_bytes = struct.pack('!I', len(msg_bytes))
    plaintext = random_bytes + msg_len_bytes + msg_bytes + corp_id.encode('utf-8')

    # PKCS7 填充 + AES 加密
    padded = pad(plaintext, AES.block_size, style='pkcs7')
    ciphertext = cipher.encrypt(padded)

    return base64.b64encode(ciphertext).decode('utf-8')


def verify_url(token, encoding_aes_key, msg_signature, timestamp, nonce, echostr, corp_id):
    """
    验证 URL（企业微信回调配置时的 GET 请求）
    
    参数:
        token: 企业微信 Token
        encoding_aes_key: 43位 EncodingAESKey
        msg_signature: 签名
        timestamp: 时间戳
        nonce: 随机字符串
        echostr: 加密的随机字符串
        corp_id: 企业 CorpID
    
    返回:
        str: 解密后的 echostr 明文（需原样返回）
    """
    if not verify_signature(token, timestamp, nonce, echostr, msg_signature):
        raise ValueError("签名验证失败")
    return decrypt_message(encoding_aes_key, echostr, corp_id)
