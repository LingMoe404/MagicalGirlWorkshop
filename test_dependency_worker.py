import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 将项目根目录加入路径，以便导入 main.py
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from PySide6.QtWidgets import QApplication

# QThread 需要 QApplication 实例存在才能初始化
if not QApplication.instance():
    app = QApplication(sys.argv)

from workers.dependency import DependencyWorker

class TestDependencyWorker(unittest.TestCase):
    def setUp(self):
        """每个测试用例运行前执行"""
        self.worker = DependencyWorker()
        # Mock 信号，以便验证是否发射了正确的信号
        self.worker.log_signal = MagicMock()
        self.worker.result_signal = MagicMock()
        self.worker.missing_signal = MagicMock()

    @patch('workers.dependency.os.path.exists')
    @patch('workers.dependency.tool_path')
    def test_missing_dependencies(self, mock_tool_path, mock_exists):
        """测试当工具缺失时，是否正确发射 missing_signal"""
        # 模拟 tool_path 返回虚拟路径
        mock_tool_path.side_effect = lambda x: f"tools/{x}"
        
        # 模拟 'ffmpeg.exe' 不存在，其他都存在
        def exists_side_effect(path):
            return "ffmpeg.exe" not in path
        mock_exists.side_effect = exists_side_effect

        # 运行自检
        self.worker.run()

        # 验证：应该发射 missing_signal
        self.worker.missing_signal.emit.assert_called_once()
        # 验证：缺失列表中应包含 FFmpeg
        missing_list = self.worker.missing_signal.emit.call_args[0][0]
        self.assertTrue(any("FFmpeg" in item for item in missing_list))
        
        # 验证：不应发射结果信号
        self.worker.result_signal.emit.assert_not_called()

    @patch('workers.dependency.subprocess.Popen')
    @patch('workers.dependency.subprocess.check_output')
    @patch('workers.dependency.os.path.exists')
    @patch('workers.dependency.tool_path')
    def test_no_hardware_encoders(self, mock_tool_path, mock_exists, mock_check_output, mock_popen):
        """测试当工具存在但无硬件编码器时的情况"""
        mock_tool_path.return_value = "dummy_path"
        mock_exists.return_value = True
        
        # 模拟 ffmpeg -encoders 输出，不包含任何 av1 硬件编码器
        mock_check_output.return_value = b"libaom-av1 libsvtav1"

        self.worker.run()

        # 验证：result_signal 应发射 (False, False, False)
        self.worker.result_signal.emit.assert_called_once_with(False, False, False)
        self.worker.missing_signal.emit.assert_not_called()

    @patch('workers.dependency.subprocess.Popen')
    @patch('workers.dependency.subprocess.check_output')
    @patch('workers.dependency.os.path.exists')
    @patch('workers.dependency.tool_path')
    def test_qsv_detected_success(self, mock_tool_path, mock_exists, mock_check_output, mock_popen):
        """测试成功检测到 QSV 编码器"""
        mock_tool_path.return_value = "dummy_path"
        mock_exists.return_value = True
        
        # 模拟 ffmpeg -encoders 输出包含 av1_qsv
        mock_check_output.return_value = b"av1_qsv"

        # 模拟 Popen 上下文管理器 (with subprocess.Popen(...) as proc)
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"") # stdout, stderr
        mock_process.returncode = 0 # 模拟执行成功
        
        mock_popen.return_value.__enter__.return_value = mock_process

        self.worker.run()

        # 验证：result_signal 应发射 (True, False, False)
        self.worker.result_signal.emit.assert_called_once_with(True, False, False)

    @patch('workers.dependency.subprocess.Popen')
    @patch('workers.dependency.subprocess.check_output')
    @patch('workers.dependency.os.path.exists')
    @patch('workers.dependency.tool_path')
    def test_nvenc_detected_but_failed(self, mock_tool_path, mock_exists, mock_check_output, mock_popen):
        """测试检测到 NVENC 编码器但硬件自检失败（例如驱动不支持）"""
        mock_tool_path.return_value = "dummy_path"
        mock_exists.return_value = True
        
        # 模拟 ffmpeg -encoders 输出包含 av1_nvenc
        mock_check_output.return_value = b"av1_nvenc"

        # 模拟 Popen 执行失败 (returncode != 0)
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"Error: No device found")
        mock_process.returncode = 1
        
        mock_popen.return_value.__enter__.return_value = mock_process

        self.worker.run()

        # 验证：result_signal 应发射 (False, False, False)，因为自检失败了
        self.worker.result_signal.emit.assert_called_once_with(False, False, False)
        # 验证：应该记录了错误日志
        self.worker.log_signal.emit.assert_called()

if __name__ == '__main__':
    unittest.main()