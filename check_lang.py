import os
import sys
import importlib.util
from string import Formatter

def load_module(path):
    """动态加载 Python 文件以检查语法错误"""
    try:
        spec = importlib.util.spec_from_file_location("module.name", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"❌ [语法错误] 无法加载 {os.path.basename(path)}: {e}")
        return None

def extract_placeholders(text):
    """提取字符串中的格式化占位符，例如 '{name}' -> {'name'}"""
    try:
        return {fname for _, fname, _, _ in Formatter().parse(str(text)) if fname is not None}
    except ValueError:
        return set()

def append_missing_keys(file_path, missing_items):
    """将缺失的键追加到文件中的字典末尾"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 寻找最后一个 '}'
        last_brace_index = -1
        for i in range(len(lines) - 1, -1, -1):
            if '}' in lines[i]:
                last_brace_index = i
                break
        
        if last_brace_index == -1:
            print(f"  ❌ 无法自动修复: 在 {os.path.basename(file_path)} 中找不到字典结束符 '}}'")
            return

        # 检查前一行是否有逗号，如果没有则添加 (防止语法错误)
        prev_idx = last_brace_index - 1
        while prev_idx >= 0:
            line = lines[prev_idx].strip()
            if not line or line.startswith('#'):
                prev_idx -= 1
                continue
            
            original_line = lines[prev_idx]
            # 简单启发式：找到最后一个引号，注释肯定在它后面，避免破坏字符串内的 #
            last_quote = max(original_line.rfind('"'), original_line.rfind("'"))
            if last_quote != -1:
                comment_idx = original_line.find('#', last_quote)
            else:
                comment_idx = original_line.find('#')
            
            if comment_idx != -1:
                code_part = original_line[:comment_idx].rstrip()
                comment_part = original_line[comment_idx:]
            else:
                code_part = original_line.rstrip()
                comment_part = ""
            
            if code_part and not code_part.endswith(',') and not code_part.endswith('{'):
                if comment_part:
                     lines[prev_idx] = code_part + ", " + comment_part
                else:
                     lines[prev_idx] = code_part + ",\n"
            break

        new_lines = []
        new_lines.append("    # --- Auto-generated missing keys ---\n")
        for key, val in missing_items.items():
            val_escaped = val.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            new_lines.append(f'    "{key}": "{val_escaped}", # TODO: Translate this\n')
        
        lines[last_brace_index:last_brace_index] = new_lines
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        print(f"  ✨ 已自动追加 {len(missing_items)} 个缺失 Key 到文件末尾 (标记为 TODO)。")
        
    except Exception as e:
        print(f"  ❌ 自动修复失败: {e}")

def check_languages(locales_dir):
    print(f"🔍 正在检查目录: {locales_dir} ...\n")
    
    files = [f for f in os.listdir(locales_dir) if f.endswith('.py') and f != '__init__.py']
    languages = {}
    has_error = False

    # 1. 加载所有语言文件 (检查语法)
    for f in files:
        path = os.path.join(locales_dir, f)
        module = load_module(path)
        if module and hasattr(module, 'translation'):
            languages[f] = module.translation
            print(f"✅ [语法 OK] {f}")
        else:
            print(f"⚠️ [警告] {f} 中未找到 'translation' 字典")
            has_error = True

    if 'zh_CN.py' not in languages:
        print("\n❌ 错误: 找不到基准语言文件 zh_CN.py，无法进行对比检查。")
        return

    base_lang = languages['zh_CN.py']
    print("-" * 60)

    # 2. 对比检查
    for filename, trans in languages.items():
        if filename == 'zh_CN.py':
            continue
            
        print(f"正在对比 {filename} 与 zh_CN.py ...")
        file_has_issue = False
        
        # 检查缺失的 Key
        missing_keys = set(base_lang.keys()) - set(trans.keys())
        if missing_keys:
            print(f"  ❌ 缺失 Key ({len(missing_keys)} 个):")
            for k in missing_keys:
                print(f"    - {k}")
            
            # 自动修复：追加缺失的 Key
            missing_items = {k: base_lang[k] for k in missing_keys}
            append_missing_keys(os.path.join(locales_dir, filename), missing_items)
            
            file_has_issue = True
            has_error = True
            
        # 检查多余的 Key
        extra_keys = set(trans.keys()) - set(base_lang.keys())
        if extra_keys:
            print(f"  ⚠️ 多余 Key ({len(extra_keys)} 个) [可能是旧翻译]:")
            for k in extra_keys:
                print(f"    + {k}")

        # 检查占位符不匹配
        for key, base_val in base_lang.items():
            if key in trans:
                target_val = trans[key]
                base_placeholders = extract_placeholders(base_val)
                target_placeholders = extract_placeholders(target_val)
                
                if base_placeholders != target_placeholders:
                    print(f"  ❌ 占位符不匹配 '{key}':")
                    print(f"    基准: {base_val}  -> {base_placeholders}")
                    print(f"    目标: {target_val}  -> {target_placeholders}")
                    file_has_issue = True
                    has_error = True

        if not file_has_issue:
            print("  ✨ 完美匹配！")
        print("-" * 60)

    if not has_error:
        print("\n🎉 所有语言文件检查通过！")
    else:
        print("\n🚫 发现问题，请修复后再运行程序。")

if __name__ == "__main__":
    # 自动定位到 i18n/locales 目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    locales_path = os.path.join(current_dir, 'i18n', 'locales')
    
    if os.path.exists(locales_path):
        check_languages(locales_path)
    else:
        print(f"错误: 找不到语言目录 {locales_path}")