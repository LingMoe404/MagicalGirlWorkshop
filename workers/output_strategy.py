"""输出落盘策略：将转码临时文件安全移动到最终输出路径。

本模块从 EncoderWorker 中拆出，只负责纯文件移动/备份/恢复逻辑，
不导入 Qt、不发送信号、不打印日志。所有路径统一经 to_long_path()
转换为 Windows 长路径后再执行实际文件操作。
"""

import errno
import os
import shutil
import time

from utils import to_long_path


def move_with_retries(source, destination, replace_existing=False, retries=3):
    """将 source 移动到 destination，失败时按 retries 次重试。

    同盘（默认）优先 os.replace()，跨盘抛 OSError(errno.EXDEV) 时回退
    shutil.move()。全部尝试失败后返回 False，由调用方决定如何处理。
    """
    for attempt in range(retries):
        try:
            if replace_existing:
                try:
                    os.replace(source, destination)
                except OSError as error:
                    if error.errno != errno.EXDEV:
                        raise
                    shutil.move(source, destination)
            else:
                shutil.move(source, destination)
            return True
        except OSError:
            if attempt + 1 < retries:
                time.sleep(1)
    return False


def save_non_overwrite_output(temp_output, final_output):
    """非覆盖模式：仅移动临时文件到最终路径，不预先删除目标。

    移动失败（含重试后仍失败）时抛出无用户文案的 OSError，且保证既有
    目标文件不被删除。调用方负责捕获异常并按本地化键发送失败信号。
    """
    lp_temp = to_long_path(temp_output)
    lp_dest = to_long_path(final_output)
    if not move_with_retries(lp_temp, lp_dest):
        raise OSError()


def save_overwrite_output(source_path, temp_output, final_output):
    """覆盖模式：用临时文件替换最终输出，失败时恢复源文件。

    源路径与最终路径相同（原地覆盖）时，先把源文件改名成 .bak 备份，
    移动成功则删除备份，移动失败则把 .bak 改回源文件。
    源路径与最终路径不同（跨目录输出）时，替换最终目标并在成功后删除
    源文件，失败则保留源文件不变。仍失败时抛出无用户文案的 OSError，
    由调用方负责本地化提示。
    """
    abs_src = os.path.normcase(os.path.abspath(os.fspath(source_path)))
    abs_dest = os.path.normcase(os.path.abspath(os.fspath(final_output)))
    same_path = abs_src == abs_dest

    lp_temp = to_long_path(temp_output)
    lp_dest = to_long_path(final_output)

    if same_path:
        lp_src = to_long_path(source_path)
        bak_path = lp_src + ".bak"
        # [Fix] 仅当源文件存在时才执行备份重命名（防止重试时因源文件已更名而报错）
        if os.path.exists(lp_src):
            if os.path.exists(bak_path):
                os.remove(bak_path)
            os.replace(lp_src, bak_path)

        try:
            # 原地覆盖可能瞬时失败（文件被占用等），重试 3 次再放弃
            if not move_with_retries(
                lp_temp, lp_dest, replace_existing=True, retries=3
            ):
                raise OSError()
            if os.path.exists(bak_path):
                os.remove(bak_path)
        except OSError:
            if os.path.exists(bak_path) and not os.path.exists(lp_src):
                os.replace(bak_path, lp_src)
            raise
    else:
        if not move_with_retries(lp_temp, lp_dest, replace_existing=True):
            raise OSError()
        if os.path.exists(to_long_path(source_path)):
            os.remove(to_long_path(source_path))
