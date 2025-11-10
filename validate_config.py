#!/usr/bin/env python3
"""
配置验证脚本 - 验证所有适配器的YAML配置是否正确
Configuration Validation Script - Verify all adapter YAML configurations
"""

import yaml
import sys
from pathlib import Path

def validate_adapter_config(agent_name: str, project_root: Path):
    """验证单个适配器的配置"""
    print(f"\n🔍 验证 {agent_name} 配置...")
    
    config_file = project_root / "config" / f"run_{agent_name}.yaml"
    
    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        adapter_params = config.get("adapter_params", {})
        if not adapter_params:
            print(f"❌ adapter_params 为空")
            return False
        
        print(f"✅ 配置文件: {config_file.name}")
        print(f"📋 参数:")
        
        # 验证特定于适配器的必需参数
        if agent_name == "shixuanlin":
            required_keys = ["api_key", "base_url"]
            sensitive_keys = ["api_key"]
        elif agent_name == "hatespeech":
            required_keys = ["base_url", "email", "password"]
            sensitive_keys = ["email", "password"]
        elif agent_name == "verimedia":
            required_keys = ["base_url"]
            sensitive_keys = []
        else:
            required_keys = []
            sensitive_keys = []
        
        # 检查必需参数
        missing_keys = []
        for key in required_keys:
            if key not in adapter_params or not adapter_params[key]:
                missing_keys.append(key)
        
        if missing_keys:
            print(f"❌ 缺少必需参数: {missing_keys}")
            return False
        
        # 显示参数（敏感信息部分隐藏）
        for key, value in adapter_params.items():
            if key in sensitive_keys and value:
                # 隐藏敏感信息
                if len(str(value)) > 8:
                    masked_value = str(value)[:4] + "*" * (len(str(value)) - 8) + str(value)[-4:]
                else:
                    masked_value = "*" * len(str(value))
                print(f"   {key}: {masked_value}")
            else:
                print(f"   {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析配置文件失败: {e}")
        return False

def main():
    """主验证函数"""
    print("🚀 开始验证适配器配置...")
    
    # 获取项目根目录
    project_root = Path(__file__).parent
    
    # 验证所有适配器
    adapters = ["shixuanlin", "hatespeech", "verimedia"]
    results = {}
    
    for adapter in adapters:
        results[adapter] = validate_adapter_config(adapter, project_root)
    
    # 汇总结果
    print(f"\n📊 验证结果汇总:")
    success_count = 0
    for adapter, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {adapter}: {status}")
        if success:
            success_count += 1
    
    print(f"\n🎯 总计: {success_count}/{len(adapters)} 个适配器配置正确")
    
    if success_count == len(adapters):
        print("🎉 所有适配器配置验证通过！")
        return 0
    else:
        print("⚠️  存在配置问题，请检查上述错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())