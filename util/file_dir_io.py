import os
import stat
import uuid

from fastapi import UploadFile

from config import settings


def chmod_file(path_file):
    """设置文件权限为所有用户可读写执行 (777).

    Args:
        path_file: 文件路径
    """
    os.chmod(path_file, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)


def mk_dir(dir_path):
    """创建目录, 若不存在则递归创建并设置权限.

    Args:
        dir_path: 目录路径
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        chmod_file(dir_path)


async def save_uploaded_file(upload_file: UploadFile):
    """将上传文件保存到临时目录, 文件名附加 UUID 防冲突.

    Args:
        upload_file: FastAPI 上传文件对象

    Returns:
        保存后的文件完整路径
    """
    file_name = settings.temp_path_resolved + "/" + upload_file.filename + str(uuid.uuid4())
    with open(file_name, "wb") as f:
        contents = await upload_file.read()
        f.write(contents)
    return file_name


def is_exist_file(file_path):
    """检查文件是否存在.

    Args:
        file_path: 文件路径

    Returns:
        文件存在返回 True, 否则 False
    """
    return bool(os.path.isfile(file_path))


def get_file_name(id_str: str) -> str:
    """获取缓存文件完整路径.

    Args:
        id_str: 缓存标识符

    Returns:
        完整文件路径
    """
    return settings.img_data_path_resolved + "/" + id_str
