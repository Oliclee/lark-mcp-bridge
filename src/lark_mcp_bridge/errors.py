"""错误层级定义。"""


class BridgeError(Exception):
    """所有 bridge 错误的基类。"""

    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class ConfigError(BridgeError):
    """配置相关错误。"""


class DiscoveryError(BridgeError):
    """Discovery 阶段错误。"""


class ExecutionError(BridgeError):
    """命令执行错误（不可恢复的启动级别）。"""


class FilterError(BridgeError):
    """过滤策略错误。"""
