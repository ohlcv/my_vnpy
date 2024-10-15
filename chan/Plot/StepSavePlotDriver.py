import os
import matplotlib.pyplot as plt
from IPython.display import clear_output, display

from Chan import CChan
from .PlotDriver import CPlotDriver

class CStepSaveDriver:
    def __init__(self, chan: CChan, plot_config=None, plot_para=None, save_dir='output_frames'):
        self.chan = chan
        self.plot_config = plot_config or {}
        self.plot_para = plot_para or {}
        self.save_dir = save_dir
        self.frame_count = 0

        # 确保保存目录存在
        os.makedirs(self.save_dir, exist_ok=True)

    def run(self):
        for _ in self.chan.step_load():
            try:
                g = CPlotDriver(self.chan, self.plot_config, self.plot_para)
                
                # 保存图片
                filename = f"frame_{self.frame_count:04d}.png"
                filepath = os.path.join(self.save_dir, filename)
                g.figure.savefig(filepath)
                print(f"Saved frame to {filepath}")
                
                self.frame_count += 1
                
                # 显示图片（如果在 Jupyter Notebook 环境中）
                clear_output(wait=True)
                display(g.figure)
                
                plt.close(g.figure)
            except Exception as e:
                print(f"Error occurred while saving frame {self.frame_count}: {e}")

# 使用示例
if __name__ == "__main__":
    # 这里只是一个示例，实际使用时需要正确初始化 CChan 对象
    chan = CChan(...)  # 初始化 CChan 对象
    plot_config = {...}  # 设置绘图配置
    plot_para = {...}  # 设置绘图参数
    save_dir = "output_frames"  # 指定保存图片的目录
    
    driver = CStepSaveDriver(chan, plot_config, plot_para, save_dir)
    driver.run()