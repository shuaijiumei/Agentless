import json
import os
import fcntl
from threading import Lock
from contextlib import contextmanager
from typing import Dict, Any

class CacheManager:
    """缓存管理器，确保线程安全的缓存操作"""
    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self.memory_cache: Dict[str, Any] = {}
        self.memory_lock = Lock()
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
    @contextmanager
    def file_lock(self):
        """文件锁上下文管理器"""
        lock_path = f"{self.cache_path}.lock"
        with open(lock_path, 'w') as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                
    def read(self) -> Dict[str, Any]:
        """线程安全地读取缓存"""
        with self.memory_lock:
            if self.memory_cache:
                return self.memory_cache.copy()
            
        with self.file_lock():
            if os.path.exists(self.cache_path):
                try:
                    with open(self.cache_path, 'r') as f:
                        data = json.load(f)
                        with self.memory_lock:
                            self.memory_cache = data
                        return data.copy()
                except (json.JSONDecodeError, IOError):
                    return {}
            return {}
            
    def write(self, key: str, value: Any):
        """线程安全地写入缓存"""
        with self.file_lock():
            # 读取当前缓存
            try:
                with open(self.cache_path, 'r') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError, FileNotFoundError):
                data = {}
            
            # 更新缓存
            data[key] = value
            
            # 写入文件
            with open(self.cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # 更新内存缓存
            with self.memory_lock:
                self.memory_cache = data.copy() 