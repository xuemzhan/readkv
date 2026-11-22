"""V2 训练入口：冻结学生，只更新 Mapper。"""

from readkv.train.cf_rct import train_cf_rct

__all__ = ["train_cf_rct"]
