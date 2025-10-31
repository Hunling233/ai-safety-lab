import os

# 项目结构定义
structure = {
    "adapters": ["base.py"],
    "common": ["models.py"],
    "orchestrator": ["run.py"],
    "sandbox": ["api.py"],
    "compliance": {
        "mapper.py": None,
        "rules": ["eu_ai_act.yaml", "un_ethics.yaml", "us_ai_act.yaml"]
    },
    "reporting": {
        "json_reporter.py": None,
        "html_reporter.py": None,
        "templates": ["report.html.j2"]
    },
    "testsuites": {
        "adversarial": ["prompt_injection.py"],
        "consistency": ["multi_seed.py"],
        "explainability": ["trace_capture.py"],
        "ethics": ["policy_checks.py"]
    },
    "docker": ["Dockerfile"],
    "": ["pyproject.toml", "README.md", "quickstart.py"]
}


def create_structure(base_path, structure_dict):
    for key, value in structure_dict.items():
        folder = os.path.join(base_path, key)
        if key != "":
            os.makedirs(folder, exist_ok=True)
            print(f"📁 Created folder: {folder}")
        if isinstance(value, list):
            for file in value:
                file_path = os.path.join(folder, file)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("")  # 空文件
                print(f"  📝 Created file: {file_path}")
        elif isinstance(value, dict):
            create_structure(folder, value)


if __name__ == "__main__":
    base_dir = os.getcwd()
    print(f"🚀 Creating AI Safety Lab structure in: {base_dir}\n")
    create_structure(base_dir, structure)
    print("\n✅ All folders and files created successfully!")

