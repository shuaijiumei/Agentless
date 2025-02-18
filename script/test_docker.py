import docker
from docker.errors import DockerException
import sys
import subprocess
import os
import json

def reset_docker_credentials():
    try:
        # 执行 docker logout
        subprocess.run(['docker', 'logout'], check=True)
        print("已清除 Docker 凭据")
        return True
    except subprocess.CalledProcessError:
        print("清除 Docker 凭据失败")
        return False

def fix_docker_config():
    """修复Docker配置"""
    config_path = os.path.expanduser('~/.docker/config.json')
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # 移除credStore配置
            if 'credsStore' in config:
                del config['credsStore']
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print("Docker配置已更新")
            return True
    except Exception as e:
        print(f"更新Docker配置失败: {e}")
        return False

def test_docker_connection():
    """测试Docker连接"""
    try:
        client = docker.from_env()
        client.ping()
        print("Docker引擎连接成功")
        
        # 不使用认证的基础测试
        container = client.containers.run(
            "hello-world",
            remove=True,
            detach=False
        )
        return True
        
    except DockerException as e:
        print(f"Docker错误: {str(e)}")
        return False

if __name__ == "__main__":
    print("开始Docker修复流程...")
    
    # 1. 修复Docker配置
    if fix_docker_config():
        print("配置已重置，请按照以下步骤操作：")
        print("1. 关闭Docker Desktop")
        print("2. 删除 %APPDATA%\\Docker Desktop 文件夹")
        print("3. 重启计算机")
        print("4. 重新启动Docker Desktop")
        print("5. 执行 docker login")
        input("完成上述步骤后按回车继续...")
    
    # 2. 测试连接
    if test_docker_connection():
        print("Docker测试成功！")
    else:
        print("Docker测试失败，请检查配置")