#!/usr/bin/env python
"""
直接配置LLM - 绕过Web界面
使用方法: python configure_llm.py [model_name]
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_analysis.settings')
django.setup()

from apps.agent.models import LLMConfig


def configure_llm(model_name=None):
    """配置LLM"""
    print("=" * 60)
    print("LLM配置工具")
    print("=" * 60)
    
    # 如果没有指定模型，使用默认模型
    if not model_name:
        model_name = 'Qwen/Qwen2.5-7B-Instruct'
        print(f"\n使用默认模型: {model_name}")
    else:
        print(f"\n使用指定模型: {model_name}")
    
    # 获取或创建配置
    config = LLMConfig.get_config()
    
    print("\n当前配置:")
    print(f"  提供商: {config.provider}")
    print(f"  模型: {config.model}")
    print(f"  启用: {config.enabled}")
    print(f"  Base URL: {config.base_url}")
    if config.api_key:
        print(f"  API Key: {config.api_key[:10]}...{config.api_key[-4:]}")
    
    print("\n" + "=" * 60)
    print("开始配置 SiliconFlow...")
    print("=" * 60)
    
    # 设置配置
    config.provider = 'openai'
    config.api_key = 'sk-xucbhjzjgecfdkampmngifresdyuunrmmwrqeausgmgwgrho'
    config.model = model_name
    config.base_url = 'https://api.siliconflow.cn/v1'
    config.enabled = True
    
    # 保存
    try:
        config.save()
        print("\n✓ 配置保存成功！")
    except Exception as e:
        print(f"\n✗ 配置保存失败: {e}")
        return False
    
    print("\n新配置:")
    print(f"  提供商: {config.provider}")
    print(f"  模型: {config.model}")
    print(f"  启用: {config.enabled}")
    print(f"  Base URL: {config.base_url}")
    print(f"  API Key: {config.api_key[:10]}...{config.api_key[-4:]}")
    
    # 测试连接
    print("\n" + "=" * 60)
    print("测试API连接...")
    print("=" * 60)
    
    try:
        from apps.agent.llm_service import get_llm_service
        
        llm = get_llm_service()
        if not llm or not llm.enabled:
            print("✗ LLM服务初始化失败")
            return False
        
        print(f"\n使用模型: {llm.model}")
        print(f"Base URL: {llm.base_url}")
        print("\n发送测试请求...")
        
        response = llm._call_api("请回复'测试成功'")
        
        if response:
            print(f"\n✓ 测试成功！")
            print(f"响应: {response[:100]}")
            return True
        else:
            print("\n✗ API调用失败")
            print("可能原因:")
            print("  1. API Key错误")
            print("  2. 网络连接问题")
            print("  3. 模型不可用")
            return False
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # 从命令行参数获取模型名称
    model_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = configure_llm(model_name)
    
    print("\n" + "=" * 60)
    if success:
        print("✓ 配置完成！")
        print("\n下一步:")
        print("  1. 访问: http://127.0.0.1:8000/agent/chat/")
        print("  2. 粘贴你的JD测试")
    else:
        print("✗ 配置失败")
        print("\n请检查:")
        print("  1. API Key是否正确")
        print("  2. 网络连接是否正常")
        print("  3. Django服务器是否运行")
    print("=" * 60)
