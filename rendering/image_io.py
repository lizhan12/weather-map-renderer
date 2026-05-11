import gc
import os
from io import BytesIO

import matplotlib


matplotlib.use("agg")
from matplotlib.figure import Figure


def create_figure(width: int, height: int, show_border: bool) -> tuple:
    """创建 matplotlib Figure 和 Mercator 投影 Axes.

    Args:
        width: 图片宽度 (像素)
        height: 图片高度 (像素)
        show_border: 是否显示图框

    Returns:
        (fig, ax) 元组
    """
    import cartopy.crs as ccrs

    fig = Figure(
        figsize=[width / 80, height / 80],
        dpi=80,
        frameon=show_border,
        linewidth=1.0,
        edgecolor="#fff",
        facecolor="#fff",
    )
    ax = fig.add_subplot(projection=ccrs.Mercator())
    return fig, ax


def save_figure_to_stream(fig) -> BytesIO:
    """将 Figure 保存为 PNG 字节流.

    Args:
        fig: matplotlib Figure 对象

    Returns:
        PNG 字节流 (已 seek(0))
    """
    stream = BytesIO()
    fig.savefig(stream, format="png", dpi=fig.dpi)
    stream.seek(0)
    return stream


def save_figure_to_file(fig, file_path: str) -> None:
    """将 Figure 保存为 PNG 文件, 自动创建父目录.

    Args:
        fig: matplotlib Figure 对象
        file_path: 输出文件路径
    """
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fig.savefig(file_path, format="png", dpi=fig.dpi, bbox_inches="tight")


def close_figure(fig) -> None:
    """释放 Figure 资源并触发垃圾回收.

    Args:
        fig: matplotlib Figure 对象
    """
    fig.clear()
    gc.collect()
