import os
import sys
import time
import re
from pathlib import Path
from typing import List, Tuple, Dict



# 定义不同系统的非法字符（文件夹+文件通用）
ILLEGAL_CHARS = {
    'windows': r'[<>:"/\\|?*]',
    'macos': r'[:/]',
    'linux': r'[/]'
}

# 获取当前操作系统类型
def get_os_type() -> str:
    """
    获取当前操作系统类型
    返回值：windows/macos/linux
    """
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('darwin'):
        return 'macos'
    else:
        return 'linux'

# 校验根路径合法性（用于"所有内容"模式）
def validate_root_path(path: str) -> Tuple[bool, str]:
    """
    校验根路径合法性（必须是文件夹）
    参数：path - 用户输入的根路径
    返回值：(校验结果, 提示信息/绝对路径)
    """
    if not path:
        return False, "错误：路径不能为空！"
    
    try:
        abs_path = Path(path).resolve()
    except Exception as e:
        return False, f"错误：路径格式非法 - {str(e)}"
    
    if not abs_path.exists():
        return False, f"错误：根路径 '{abs_path}' 不存在！"
    
    if not abs_path.is_dir():
        return False, f"错误：'{abs_path}' 不是文件夹（根路径必须是文件夹）！"
    
    # 检查访问权限
    try:
        test_file = abs_path / f".tmp_{int(time.time())}"
        test_file.touch(exist_ok=True)
        test_file.unlink()
    except PermissionError:
        return False, f"错误：没有访问 '{abs_path}' 的权限！"
    
    return True, str(abs_path)

# 过滤名称中的非法字符
def filter_illegal_chars(content: str) -> Tuple[str, List[str]]:
    """
    过滤名称中的非法字符
    参数：content - 用户输入的自定义内容
    返回值：(过滤后的内容, 被过滤的字符列表)
    """
    os_type = get_os_type()
    pattern = ILLEGAL_CHARS[os_type]
    illegal_chars = re.findall(pattern, content)
    
    # 去重
    illegal_chars = list(set(illegal_chars))
    
    # 替换非法字符
    filtered_content = re.sub(pattern, '', content)
    
    return filtered_content, illegal_chars

# 获取待重命名的目标列表（支持根路径下所有内容）
def get_target_list(input_path: str, target_mode: str) -> List[Dict]:
    """
    根据用户选择的模式获取待重命名的目标列表
    参数：
        input_path - 用户输入的路径
        target_mode - 目标模式（folder/ file/ all）
                      folder=仅文件夹, file=仅文件, all=根路径下所有文件+文件夹
    返回值：待处理的目标列表（字典格式：{'path': Path, 'type': 'folder/file'}）
    """
    target_list = []
    
    # 模式1：根路径下所有内容（文件+文件夹）
    if target_mode == 'all':
        # 先校验根路径合法性
        valid, abs_root_path = validate_root_path(input_path)
        if not valid:
            print(abs_root_path)
            return []
        
        root_path = Path(abs_root_path)
        # 遍历根路径下所有内容（不递归子目录）
        for item in root_path.iterdir():
            if item.is_dir():
                target_list.append({'path': item.resolve(), 'type': 'folder'})
            elif item.is_file():
                target_list.append({'path': item.resolve(), 'type': 'file'})
        
        if not target_list:
            print(f"错误：根路径 '{root_path}' 下未找到任何文件/文件夹！")
            return []
    
    # 模式2：仅文件夹/仅文件（原单/多/通配符逻辑）
    else:
        target_type = 'folder' if target_mode == 'folder' else 'file'
        # 处理多路径（逗号分隔）
        if ',' in input_path:
            path_list = [p.strip() for p in input_path.split(',')]
            for p in path_list:
                valid, abs_path = validate_single_path(p, target_type)
                if valid:
                    target_list.append({'path': Path(abs_path), 'type': target_type})
                else:
                    print(f"跳过无效路径 '{p}'：{abs_path}")
        else:
            # 处理通配符
            if '*' in input_path:
                try:
                    parent_dir = Path(input_path).parent
                    pattern = Path(input_path).name
                    for item in parent_dir.glob(pattern):
                        if (target_type == 'folder' and item.is_dir()) or (target_type == 'file' and item.is_file()):
                            target_list.append({'path': item.resolve(), 'type': target_type})
                except Exception as e:
                    print(f"通配符路径解析失败：{str(e)}")
                    return []
            else:
                # 单路径
                valid, abs_path = validate_single_path(input_path, target_type)
                if valid:
                    target_list.append({'path': Path(abs_path), 'type': target_type})
                else:
                    print(abs_path)
                    return []
    
    # 去重并过滤空列表
    target_list = [dict(t) for t in {tuple(d.items()) for d in target_list}]
    if not target_list:
        mode_name = {
            'folder': '文件夹',
            'file': '文件',
            'all': '文件/文件夹'
        }[target_mode]
        print(f"错误：未找到有效待重命名的{mode_name}！")
        return []
    
    return target_list

# 校验单路径合法性（区分文件/文件夹）
def validate_single_path(path: str, target_type: str) -> Tuple[bool, str]:
    """
    校验单个文件/文件夹路径的合法性
    参数：
        path - 待校验的路径
        target_type - 目标类型（folder/file）
    返回值：(校验结果, 提示信息/绝对路径)
    """
    if not path:
        return False, "错误：路径不能为空！"
    
    try:
        abs_path = Path(path).resolve()
    except Exception as e:
        return False, f"错误：路径格式非法 - {str(e)}"
    
    if not abs_path.exists():
        return False, f"错误：路径 '{abs_path}' 不存在！"
    
    if target_type == 'folder' and not abs_path.is_dir():
        return False, f"错误：'{abs_path}' 不是文件夹！"
    elif target_type == 'file' and not abs_path.is_file():
        return False, f"错误：'{abs_path}' 不是文件！"
    
    # 检查访问权限
    try:
        if target_type == 'folder':
            test_file = abs_path / f".tmp_{int(time.time())}"
            test_file.touch(exist_ok=True)
            test_file.unlink()
        else:
            with open(abs_path, 'rb'):
                pass
    except PermissionError:
        return False, f"错误：没有访问 '{abs_path}' 的权限！"
    
    return True, str(abs_path)

# 生成新名称（支持开头/末尾/中间插入）
def generate_new_name(target: Dict, position: str, custom_content: str, insert_index: int = 0) -> str:
    """
    生成新名称（支持开头/末尾/中间插入）
    参数：
        target - 目标字典（{'path': Path, 'type': 'folder/file'}）
        position - 位置（开头/末尾/中间）
        custom_content - 过滤后的自定义内容
        insert_index - 中间插入的位置索引（从0开始）
    返回值：新名称
    """
    target_path = target['path']
    target_type = target['type']
    
    if target_type == 'folder':
        # 文件夹：处理完整名称
        original_name = target_path.name
        if position == '开头':
            new_name = f"{custom_content}{original_name}"
        elif position == '末尾':
            new_name = f"{original_name}{custom_content}"
        else:  # 中间
            # 处理索引超出长度的情况（默认插入到名称中间）
            if insert_index >= len(original_name):
                insert_index = len(original_name) // 2
            new_name = f"{original_name[:insert_index]}{custom_content}{original_name[insert_index:]}"
    else:
        # 文件：仅处理主名称，保留扩展名
        original_stem = target_path.stem  # 主名称（无扩展名）
        original_suffix = target_path.suffix  # 扩展名（含.）
        if position == '开头':
            new_stem = f"{custom_content}{original_stem}"
        elif position == '末尾':
            new_stem = f"{original_stem}{custom_content}"
        else:  # 中间
            if insert_index >= len(original_stem):
                insert_index = len(original_stem) // 2
            new_stem = f"{original_stem[:insert_index]}{custom_content}{original_stem[insert_index:]}"
        new_name = f"{new_stem}{original_suffix}"
    
    return new_name

# 检查新名称是否重复
def check_duplicate_name(target_path: Path, new_name: str) -> bool:
    """
    检查新名称是否与同目录下的文件/文件夹重复
    参数：
        target_path - 原目标路径
        new_name - 新名称
    返回值：True（重复）/False（不重复）
    """
    parent_dir = target_path.parent
    new_path = parent_dir / new_name
    return new_path.exists()

# 保存操作日志
def save_operation_log(log_content: str, log_file: str = "rename_log.txt"):
    """
    保存重命名操作日志到本地txt文件
    参数：
        log_content - 日志内容
        log_file - 日志文件路径
    """
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{log_content}\n")
        print(f"操作日志已保存到 {os.path.abspath(log_file)}")
    except Exception as e:
        print(f"日志保存失败：{str(e)}")

# 核心重命名逻辑
def rename_core():
    """
    核心重命名流程（支持开头/末尾/中间插入内容）
    """
    print("="*60)
    print("          跨平台文件/文件夹批量重命名工具          ")
    print("="*60)
    
    while True:
        # 选择重命名模式
        print("\n【请选择操作模式】")
        print("1 - 仅重命名文件夹（单/多/通配符）")
        print("2 - 仅重命名文件（单/多/通配符）")
        print("3 - 重命名指定路径下的所有文件+所有文件夹（不递归）")
        mode_choice = input("请输入数字（1/2/3）：").strip()
        
        if mode_choice not in ['1', '2', '3']:
            print("错误：仅支持输入1/2/3，请重新选择！")
            continue
        
        # 映射模式名称
        target_mode = {
            '1': 'folder',
            '2': 'file',
            '3': 'all'
        }[mode_choice]
        
        # 提示文案适配
        mode_prompt = {
            'folder': '文件夹',
            'file': '文件',
            'all': '根路径（该路径下所有文件+文件夹）'
        }[target_mode]
        
        # 第一步：输入路径
        print(f"\n【第一步】请输入待重命名的{mode_prompt}路径（支持：")
        if target_mode == 'all':
            print("  仅支持单个根文件夹路径（如 C:\\Users\\user\\Desktop）")
        else:
            print("  1. 单路径（绝对/相对）")
            print("  2. 多路径（逗号分隔）")
            print("  3. 通配符路径（如 ./test/*）")
        
        input_path = input(f"请输入{mode_prompt}路径：").strip()
        
        # 获取目标列表
        target_list = get_target_list(input_path, target_mode)
        if not target_list:
            continue
        
        # 第二步：选择添加内容的位置（新增中间选项）
        while True:
            position = input(f"\n【第二步】请选择添加内容的位置（开头/末尾/中间）：").strip()
            if position in ['开头', '末尾', '中间']:
                break
            print("错误：仅支持输入'开头'或'末尾'或'中间'，请重新输入！")
        
        # 第三步：处理中间插入的位置索引（仅中间模式需要）
        insert_index = 0
        if position == '中间':
            # 展示第一个目标的名称示例，引导用户输入索引
            sample_target = target_list[0]
            sample_name = sample_target['path'].stem if sample_target['type'] == 'file' else sample_target['path'].name
            print(f"\n【第三步-1】中间插入位置设置（索引从0开始）")
            print(f"示例：名称「{sample_name}」的索引分布：")
            for i, char in enumerate(sample_name):
                print(f"  索引{i} → 字符「{char}」")
            
            # 输入并校验索引
            while True:
                index_input = input(f"请输入插入位置索引（默认{len(sample_name)//2}）：").strip()
                if not index_input:
                    insert_index = len(sample_name) // 2
                    break
                try:
                    insert_index = int(index_input)
                    if insert_index < 0:
                        print("错误：索引不能为负数，请重新输入！")
                        continue
                    break
                except ValueError:
                    print("错误：请输入有效的数字索引！")
        
        # 第四步：输入自定义内容并过滤非法字符
        while True:
            custom_content = input(f"\n【第三步{'（中间模式）' if position == '中间' else ''}】请输入需要添加的自定义内容：").strip()
            if not custom_content:
                print("错误：自定义内容不能为空，请重新输入！")
                continue
            
            # 过滤非法字符
            filtered_content, illegal_chars = filter_illegal_chars(custom_content)
            if illegal_chars:
                print(f"提示：检测到非法字符 {','.join(illegal_chars)}，已自动过滤！")
                if not filtered_content:
                    print("错误：过滤后内容为空，请重新输入！")
                    continue
            
            break
        
        # 第五步：预览并重命名确认
        print(f"\n【第四步】重命名预览（共{len(target_list)}个目标）：")
        print("-"*60)
        rename_plan: List[Dict] = []
        duplicate_flag = False
        
        for target in target_list:
            target_path = target['path']
            target_type = target['type']
            original_name = target_path.name
            new_name = generate_new_name(target, position, filtered_content, insert_index)
            
            # 检查名称重复
            if check_duplicate_name(target_path, new_name):
                print(f"⚠️  [{target_type}] {target_path.parent}/{original_name} → {new_name}（新名称已存在）")
                duplicate_flag = True
            else:
                print(f"✅  [{target_type}] {target_path.parent}/{original_name} → {new_name}")
            
            rename_plan.append({
                'original_path': target_path,
                'original_name': original_name,
                'new_name': new_name,
                'new_path': target_path.parent / new_name,
                'type': target_type,
                'duplicate': check_duplicate_name(target_path, new_name)
            })
        
        print("-"*60)
        
        # 重复名称处理
        if duplicate_flag:
            confirm = input("检测到重复名称，是否继续？（Y/N，继续将跳过重复项）：").strip().upper()
        else:
            confirm = input("是否确认执行重命名操作？（Y/N）：").strip().upper()
        
        if confirm != 'Y':
            print("操作已取消，返回初始步骤！")
            continue
        
        # 执行重命名
        success_count = 0
        fail_count = 0
        log_records = []
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        operator = os.getlogin() if hasattr(os, 'getlogin') else "未知用户"
        
        print(f"\n开始执行重命名操作...")
        for plan in rename_plan:
            if plan['duplicate']:
                print(f"跳过 [{plan['type']}] {plan['original_name']}：新名称已存在")
                fail_count += 1
                continue
            
            try:
                # 执行重命名
                os.rename(plan['original_path'], plan['new_path'])
                success_count += 1
                print(f"成功 [{plan['type']}]：{plan['original_name']} → {plan['new_name']}")
                
                # 记录日志
                log_records.append(
                    f"[{current_time}] 操作人：{operator} | 类型：{plan['type']} | 位置：{position} | 插入索引：{insert_index if position == '中间' else '无'} | 原路径：{plan['original_path']} | 新路径：{plan['new_path']}"
                )
            except PermissionError:
                print(f"失败 [{plan['type']}]：{plan['original_name']} → 权限不足")
                fail_count += 1
            except Exception as e:
                print(f"失败 [{plan['type']}]：{plan['original_name']} → {str(e)}")
                fail_count += 1
        
        # 输出执行结果
        print("\n" + "="*60)
        print(f"执行完成！总计：{len(rename_plan)} | 成功：{success_count} | 失败：{fail_count}")
        print("="*60)
        
        # 保存日志（可选）
        save_log = input("是否保存操作日志到本地？（Y/N）：").strip().upper()
        if save_log == 'Y' and log_records:
            save_operation_log("\n".join(log_records))
        
        # 询问是否继续操作
        continue_oper = input("\n是否继续进行其他重命名操作？（Y/N）：").strip().upper()
        if continue_oper != 'Y':
            print("\n感谢使用，程序已退出！")
            break

# 程序入口
if __name__ == "__main__":
    try:
        rename_core()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断，已退出！")
    except Exception as e:
        print(f"\n程序运行出错：{str(e)}")
        sys.exit(1)