import json
import pickle


def load_config(file_path):
    """加载配置文件"""
    with open(file_path, "r") as f:
        config_data = json.load(f)
    return config_data


def save_chan_instance(chan, file_path):
    """保存 CChan 实例到指定路径"""
    with open(file_path, "wb") as f:
        pickle.dump(chan, f)
        # pickle.dump(list(chan), f)


def load_chan_instance(file_path):
    """
    从指定的pickle文件中加载CChan实例。

    Args:
        file_path (str): pickle文件的路径。

    Returns:
        CChan: 加载的CChan实例。

    Raises:
        FileNotFoundError: 如果指定的文件不存在。
        pickle.UnpicklingError: 如果文件内容无法被pickle加载。
        Exception: 其他可能的异常。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"指定的pickle文件不存在: {file_path}")

    try:
        with open(file_path, "rb") as f:
            chan = pickle.load(f)
        return chan
    except pickle.UnpicklingError as e:
        raise pickle.UnpicklingError(f"无法解序列化文件: {file_path}") from e
    except Exception as e:
        raise Exception(f"加载CChan实例时发生错误: {str(e)}") from e
