"""授权占位。

本库为独立干净室实现，不含任何授权/许可校验机制。
authenticate 保留同名接口以兼容调用方式，但始终直接成功。
"""
from ..param import WxResponse


def authenticate(*args, **kwargs) -> WxResponse:
    """无操作授权，恒返回成功（本库免授权）。"""
    return WxResponse.success(message='wxconnector4 无需授权')
