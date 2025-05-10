import numpy as np
from collections import defaultdict
import os
import tempfile
import pickle
import json

KEY_SEPARATOR = "@"

def write_dic(file_name, obj):
    # ファイルに書き込む
    with open(file_name, "ab") as f:
        pickle.dump(obj, f)
        f.close

def get_memory_index(x, y, grid_size):
    """ハンターh, 座標(x, y) から QUBO変数インデックスを取得"""
    if 0 <= x < grid_size and 0 <= y < grid_size:
        # 変数インデックスの計算式は GRID_SIZE に依存
        return y * grid_size + x
    else:
        raise ValueError(f"Invalid input for variable index: h={h}, x={x}, y={y}")

# --- 距離 (変更なし) ---
def uqlid_distance(pos1, pos2):
    return np.linalg.norm(np.array(pos1)-np.array(pos2))

# --- 様々な位置にするqubo ---
def setVariousPositionQubo(grid_size,num_hunters) :

    for tx in range(grid_size):
        for ty in range(grid_size):
            default_qubo=defaultdict(float)
            target_pos_init=[tx,ty]
            qubo_dictionary={}
            for y1 in range(grid_size): # ループ範囲が grid_size に依存
                for x1 in range(grid_size): # ループ範囲が grid_size に依存
                    for y2 in range(grid_size): # ループ範囲が grid_size に依存
                        for x2 in range(grid_size): # ループ範囲が grid_size に依存
                            memory_idx1 = get_memory_index(x1, y1, grid_size)
                            memory_idx2 = get_memory_index(x2, y2, grid_size)
                            pos1=[x1,y1]
                            pos2=[x2,y2]
                            ip=np.dot(np.array(pos1) - np.array(target_pos_init),np.array(pos2) - np.array(target_pos_init))
                            dist_cross=uqlid_distance(pos1, target_pos_init)*uqlid_distance(pos2, target_pos_init)
                            if dist_cross!= 0 :
                                default_qubo[(memory_idx1, memory_idx2)] += ip / dist_cross

            key=str(tx) + KEY_SEPARATOR + str(ty)
            qubo_dictionary[key]=default_qubo

            # 辞書をファイルに出力
            file_name = "qubo_dic" + key + ".pkl"
            write_dic(file_name, qubo_dictionary)

if __name__ == "__main__":
    GRID_SIZE = 20  # グリッドのサイズを 20x20 に変更 ★★★
    NUM_HUNTERS = 6
    # --- qubo 作成 ---
    setVariousPositionQubo(GRID_SIZE, NUM_HUNTERS)