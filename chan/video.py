import os
import re
import numpy as np
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip
from moviepy.audio.fx.all import audio_loop
import sys
from packaging import version
from PIL import __version__ as PILLOW_VERSION
import psutil


def terminate_all_ffmpeg_processes():
    print("正在终止所有 ffmpeg 进程...")
    terminated = False
    for proc in psutil.process_iter():
        try:
            if proc.name().lower() == "ffmpeg.exe":
                proc.terminate()
                print(f"已终止进程: PID={proc.pid}, 名称={proc.name()}")
                terminated = True
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"无法终止进程: PID={proc.pid} - 错误: {e}")
    if not terminated:
        print("没有找到正在运行的 ffmpeg 进程。")


# 检查 Pillow 版本
print(f"检测 Pillow 版本: {PILLOW_VERSION}")
if version.parse(PILLOW_VERSION) >= version.parse("10.0.0"):
    RESAMPLE_METHOD = Image.Resampling.LANCZOS
    print("使用 Resampling.LANCZOS 作为重采样方法。")
else:
    RESAMPLE_METHOD = Image.ANTIALIAS
    print("使用 Image.ANTIALIAS 作为重采样方法。")


def get_numeric_part(filename):
    """
    从文件名中提取第一个数字部分，用于排序和过滤。
    如果文件名中没有数字，返回 -1。
    """
    match = re.search(r"\d+", filename)
    return int(match.group()) if match else -1


def resize_images(image_folder, image_files, target_size=(1920, 1080)):
    """
    调整图像大小并覆盖原始图像。

    :param image_folder: 图像所在的文件夹路径
    :param image_files: 要处理的图像文件列表
    :param target_size: 目标分辨率 (宽, 高)
    """
    print("\n=== 开始调整图像大小并覆盖原图 ===")
    for idx, img_file in enumerate(image_files, start=1):
        img_path = os.path.join(image_folder, img_file)
        if img_path.lower().endswith(".png"):
            try:
                print(f"调整图像 {idx}/{len(image_files)}: {img_path}")
                with Image.open(img_path) as img:
                    img = img.convert("RGB")
                    img_resized = img.resize(target_size, RESAMPLE_METHOD)
                    img_resized.save(img_path)
            except Exception as e:
                print(f"无法处理图像文件: {img_path}\n错误: {e}")
    print("图像大小调整完成。\n")


def create_video_from_images_with_audio(
    image_folder, image_files, output_video_path, audio_file_path=None, fps=2
):
    print(f"\n=== 开始创建视频 ===")
    print(f"图像文件夹: {image_folder}")
    print(f"输出视频路径: {output_video_path}")
    if audio_file_path:
        print(f"音频文件路径: {audio_file_path}")
    print(f"帧率 (FPS): {fps}")

    # 获取所有图像的完整路径
    image_paths = [os.path.join(image_folder, f) for f in image_files]
    print(f"找到 {len(image_paths)} 张图像文件。")

    # 使用上下文管理器创建 ImageSequenceClip
    print("创建 ImageSequenceClip 对象...")
    try:
        clip = ImageSequenceClip(image_paths, fps=fps)
    except Exception as e:
        print(f"无法创建 ImageSequenceClip: {e}")
        sys.exit(1)

    final_clip = clip  # 默认情况下，无音频
    print("ImageSequenceClip 创建成功。")

    if audio_file_path:  # 仅在提供音频时处理
        try:
            print("加载音频文件...")
            audio_clip = AudioFileClip(audio_file_path)  # 不使用 with
            print(f"音频文件加载成功: {audio_file_path}")

            # 比较视频和音频的时长
            video_duration = clip.duration
            audio_duration = audio_clip.duration
            print(f"视频时长: {video_duration:.2f} 秒")
            print(f"音频时长: {audio_duration:.2f} 秒")

            # 如果视频比音频长，循环音频；如果音频比视频长，截断音频
            if video_duration > audio_duration:
                print("视频时长长于音频，循环音频...")
                audio_clip = audio_clip.fx(audio_loop, duration=video_duration)
            else:
                print("音频时长长于视频，截断音频...")
                audio_clip = audio_clip.subclip(0, video_duration)

            # 将音频添加到视频中
            final_clip = clip.set_audio(audio_clip)
            print("音频已添加到视频。")

        except Exception as e:
            print(f"无法加载音频文件: {audio_file_path}\n错误: {e}")
            sys.exit(1)
        finally:
            audio_clip.close()
            print("音频文件已关闭。")

    # 保存视频
    print("开始保存视频文件...")
    # 仅在有音频时设置 audio_codec，否则禁用音频
    if audio_file_path is None:
        write_kwargs = {
            "codec": "mpeg4",  # 或其他支持的编码器，如 "libxvid"
            "audio": False,  # 禁用音频
            "bitrate": "1000k",
            "ffmpeg_params": ["-movflags", "faststart"],
        }
        print("配置保存参数: 使用 MPEG4 编码器，禁用音频。")
    else:
        write_kwargs = {
            "codec": "libx264",  # 使用更好的编码器
            "audio_codec": "aac",
            "bitrate": "1000k",  # 提高比特率
            "ffmpeg_params": ["-movflags", "faststart"],
        }
        print("配置保存参数: 使用 libx264 编码器，音频编码为 AAC。")

    try:
        final_clip.write_videofile(output_video_path, **write_kwargs)
        print(f"视频已成功保存到: {output_video_path}")
    except Exception as e:
        print(f"保存视频时出错: {e}")
        sys.exit(1)
    finally:
        clip.close()
        if audio_file_path:
            audio_clip.close()


# 获取当前脚本的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"当前脚本目录: {current_dir}")

# 设置 symbol 文件夹名称
symbol = "BTCUSDT"
k_type = "K_5M"
begin_time = "2024-09-30"
end_time = "2024-10-07"
# try:
#     symbol = str(input("交易对："))
#     k_type = str(input("k线周期："))
#     begin_time = str(input("开始时间："))
#     end_time = str(input("结束时间："))
#     image_dir = os.path.join(symbol, k_type, f"{begin_time}-{end_time}")
# except Exception as e:  # 更改为捕获所有异常
#     print("输入错误，请输入有效的字符串。")
#     sys.exit(1)  # 使用非零退出代码表示程序异常终止
image_dir = os.path.join(symbol, k_type, f"{begin_time}-{end_time}")
# 设置 image_folder 为当前目录下的 symbol 文件夹
image_folder = os.path.join(current_dir, image_dir)
print(f"\n图像文件夹设置为: {image_folder}")

# 设置 audio_file_path 为当前目录下的 audio 文件夹中的音频文件
audio_folder = os.path.join(current_dir, "audio")
# audio_file_name = "dylanf - 克罗地亚狂想曲 (钢琴版).flac"
audio_file_name = "m-taku - Komorebi (叶隙间洒落的阳光).ogg"
audio_file_path = os.path.join(audio_folder, audio_file_name)
print(f"音频文件路径设置为: {audio_file_path}")

# 指定要生成视频的图片编号范围
start_num = 1  # 开始编号（包含）
end_num = 3000  # 结束编号（包含）
print(f"\n将生成编号从 {start_num} 到 {end_num} 的图片的视频。")

# 列出文件夹中的所有 .png 文件，并按照文件名中的数字排序
print("\n列出所有 .png 文件并排序...")
image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(".png")]
image_files.sort(key=get_numeric_part)
print(f"排序后找到 {len(image_files)} 张图像文件。")

# 过滤图像文件，选择编号在指定范围内的文件
filtered_image_files = []
for f in image_files:
    num = get_numeric_part(f)
    if start_num <= num <= end_num:
        filtered_image_files.append(f)

print(f"在指定范围内找到 {len(filtered_image_files)} 张图像文件。")

# 检查是否有有效的图像文件
if not filtered_image_files:
    raise ValueError(
        f"指定范围内没有找到编号在 {start_num} 到 {end_num} 的 .png 文件。"
    )

# 调整图像大小并覆盖原图像
resize_images(image_folder, filtered_image_files, target_size=(1920, 1080))

# 设置 video 文件夹路径（symbol 文件夹下的 video 子文件夹）
video_folder = os.path.join(image_folder, "video")
# 如果 video 文件夹不存在，创建它
if not os.path.exists(video_folder):
    os.makedirs(video_folder)
    print(f"已创建视频文件夹: {video_folder}")
else:
    print(f"视频文件夹已存在: {video_folder}")

# 输出视频路径
output_video_path = os.path.join(
    video_folder, f"{symbol}_{k_type}_{start_num}-{end_num}.mp4"
)  # 或 ".avi" 根据需要
print(f"\n输出视频将保存为: {output_video_path}")

# 创建视频
create_video_from_images_with_audio(
    image_folder, filtered_image_files, output_video_path, audio_file_path
)
print("\n视频创建过程完成。")

# 在代码结束前调用这个函数
terminate_all_ffmpeg_processes()
print("所有 ffmpeg 进程已处理完毕。\n")
