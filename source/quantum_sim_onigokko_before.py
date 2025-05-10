# Google Colab で実行する場合、最初に必要なライブラリをインストールします
# !pip install openjij dimod numpy matplotlib

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation # アニメーション用
import random
import time
from collections import defaultdict
import openjij # OpenJij をインポート
import dimod # SampleSetなどを使用するためにdimodもインポート
import math # 距離計算用

# --- 定数定義 ---
GRID_SIZE = 20  # グリッドのサイズを 20x20 に変更 ★★★
NUM_HUNTERS = 6
TARGET_MARKER = 'ro'
HUNTER_MARKER = 'bx'
SIMULATION_TIME_LIMIT = 600 # 制限時間 (必要に応じて調整)

# --- QUBO パラメータ (v4 - 包囲目的) ---
# 注意: グリッドサイズ変更に伴い、これらのパラメータの再調整が必要になる可能性が高い
PARAM_A = 35.0  # 距離1ボーナス係数
PARAM_A_FAR = 1.5 # 距離2以上ペナルティ係数
PARAM_P1 = 25.0 # 制約項1(位置一意性)のペナルティ
PARAM_P2 = 15.0 # 制約項2(衝突回避)のペナルティ
PARAM_P3 = 20.0 # 制約項3(ターゲットとの衝突回避)のペナルティ
PARAM_P4 = 0.5 # 制約項4(現ターゲット位置と理想位置の距離の差)のペナルティ
NUM_READS = 3 # サンプリング回数 (20x20ではさらに増やす必要があるかも)

# --- 変数インデックス変換 (GRID_SIZE を使うように修正) ---
# 関数自体は grid_size を引数に取るので変更不要だが、呼び出し元で定数 GRID_SIZE を使う
def get_variable_index(h, x, y, grid_size):
    """ハンターh, 座標(x, y) から QUBO変数インデックスを取得"""
    if 0 <= h < NUM_HUNTERS and 0 <= x < grid_size and 0 <= y < grid_size:
        # 変数インデックスの計算式は GRID_SIZE に依存
        return h * (grid_size * grid_size) + y * grid_size + x
    else:
        raise ValueError(f"Invalid input for variable index: h={h}, x={x}, y={y}")

def get_hxy_from_index(index, grid_size, num_hunters):
    """QUBO変数インデックスから ハンターh, 座標(x, y) を取得"""
    num_cells = grid_size * grid_size # GRID_SIZE に依存
    if 0 <= index < num_hunters * num_cells:
        h = index // num_cells
        remainder = index % num_cells
        y = remainder // grid_size
        x = remainder % grid_size
        return h, x, y
    else:
        raise ValueError(f"Invalid index: {index}")

# --- 距離計算関数 (変更なし) ---
def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

# --- QUBO構築関数 (v4 - 包囲目的) (内部ロジックは grid_size を使うので変更不要) ---
def build_qubo(target_pos, grid_size, num_hunters, A, A_far, P1, P2, P3,P4,hunter_positions_list):
    """ターゲット位置と係数に基づきQUBO辞書を構築する (包囲目的)"""
    Q = defaultdict(float)
    num_cells = grid_size * grid_size
    tx, ty = target_pos

    # --- 1. 目的項: H_target_new (距離1ボーナス) ---
    for h in range(num_hunters):
        for y in range(grid_size): # ループ範囲が grid_size に依存
            for x in range(grid_size): # ループ範囲が grid_size に依存
                idx = get_variable_index(h, x, y, grid_size)
                distance = manhattan_distance([x, y], target_pos)
                target_score = 0.0
                if distance == 0: 
                    target_score = P3
                elif distance == 1:
                    target_score = -A
                else: 
                    target_score = A_far * (distance - 1)
                Q[(idx, idx)] += target_score  

    # --- 2. 制約項1: H_pos_unique ---
    for h in range(num_hunters):
        indices_h = []
        for y in range(grid_size): # ループ範囲が grid_size に依存
            for x in range(grid_size): # ループ範囲が grid_size に依存
                idx = get_variable_index(h, x, y, grid_size)
                indices_h.append(idx)
                Q[(idx, idx)] -= P1
        for i in range(len(indices_h)):
            for j in range(i + 1, len(indices_h)):
                idx1 = indices_h[i]
                idx2 = indices_h[j]
                Q[(min(idx1, idx2), max(idx1, idx2))] += 2.0 * P1

    # --- 3. 制約項2: H_collision ---
    for y in range(grid_size): # ループ範囲が grid_size に依存
        for x in range(grid_size): # ループ範囲が grid_size に依存
            indices_xy = []
            for h in range(num_hunters):
                idx = get_variable_index(h, x, y, grid_size)
                indices_xy.append(idx)
            for i in range(len(indices_xy)):
                for j in range(i + 1, len(indices_xy)):
                    idx1 = indices_xy[i]
                    idx2 = indices_xy[j]
                    Q[(min(idx1, idx2), max(idx1, idx2))] += 2.0 * P2

    # --- 4. 制約項3: H_target_collision ---
    for h in range(num_hunters):
        try:
           # ターゲット座標がグリッド範囲内かチェックしてからインデックス取得
           if 0 <= tx < grid_size and 0 <= ty < grid_size:
               idx = get_variable_index(h, tx, ty, grid_size)
               Q[(idx, idx)] += P3
        except ValueError:
            pass # ターゲットが範囲外の場合は何もしない

    return Q

# --- QUBOソルバー関数 (変更なし) ---
def solve_qubo_openjij(Q, num_reads=10):
    sampler = openjij.SASampler()
    print(f"使用するサンプラー: {type(sampler).__name__}")
    print(f"QUBOをサンプリング中 (num_reads={num_reads}, 変数={len(Q)})...") # 変数の数を表示
    start_solve_time = time.time()
    response = sampler.sample_qubo(Q, num_reads=num_reads)
    end_solve_time = time.time()
    print(f"サンプリング完了. (所要時間: {end_solve_time - start_solve_time:.2f}秒)")
    if not response:
        print("警告: サンプラーから有効な応答が得られませんでした。")
        return None, None
    best_sample_view = response.first
    best_sample = best_sample_view.sample
    best_energy = best_sample_view.energy
    print(f"最良解のエネルギー: {best_energy:.4f}")
    return best_sample, best_energy

# --- 初期位置の設定 (個別入力・個別ランダム対応、GRID_SIZE を使うように修正) ---
def initialize_positions(grid_size, num_hunters, initial_target_str=None, initial_hunters_list=None):
    """ターゲットとハンターの初期位置を設定する。入力があればそれを使い、空欄や無効ならそのハンターのみランダム。"""
    target_pos = None
    hunter_positions = [None] * num_hunters
    occupied_positions = set()

    # 1. ターゲット位置の決定
    valid_target = False
    if initial_target_str:
        try:
            coords = [int(c.strip()) for c in initial_target_str.split(',')]
            # grid_size で範囲チェック
            if len(coords) == 2 and 0 <= coords[0] < grid_size and 0 <= coords[1] < grid_size:
                target_pos = coords
                occupied_positions.add(tuple(target_pos))
                valid_target = True
                print(f"入力されたターゲット初期位置を使用: {target_pos}")
            else:
                print(f"警告: ターゲットの入力座標が範囲外(0-{grid_size-1})です。ランダムに配置します。")
        except ValueError:
            print("警告: ターゲットの入力形式が無効です (例: 'x,y')。ランダムに配置します。")

    if not valid_target:
        while True:
            # grid_size を使用
            pos = [random.randint(0, grid_size - 1), random.randint(0, grid_size - 1)]
            if tuple(pos) not in occupied_positions:
                 target_pos = pos
                 occupied_positions.add(tuple(target_pos))
                 break
        print(f"ターゲット初期位置をランダムに設定: {target_pos}")

    # 2. ハンター位置の決定
    print("--- ハンター初期位置設定 ---")
    if initial_hunters_list is None:
        initial_hunters_list = ["" for _ in range(num_hunters)]

    for h in range(num_hunters):
        hunter_input_str = initial_hunters_list[h] if h < len(initial_hunters_list) else ""
        place_randomly = False
        reason = ""

        if hunter_input_str:
            try:
                coords = [int(c.strip()) for c in hunter_input_str.split(',')]
                 # grid_size で範囲チェック
                if len(coords) == 2 and 0 <= coords[0] < grid_size and 0 <= coords[1] < grid_size:
                    pos_tuple = tuple(coords)
                    if pos_tuple in occupied_positions:
                        place_randomly = True
                        reason = f"入力位置 {coords} が重複"
                    else:
                        hunter_positions[h] = coords
                        occupied_positions.add(pos_tuple)
                        print(f"  ハンター{h}: 入力位置 {coords} を使用")
                else:
                    place_randomly = True
                    reason = f"入力座標が範囲外(0-{grid_size-1})か形式無効 ({hunter_input_str})"
            except ValueError:
                place_randomly = True
                reason = f"入力形式が無効 ({hunter_input_str})"
        else:
            place_randomly = True
            reason = "入力が空欄"

        if place_randomly:
            print(f"情報: ハンター{h} をランダムに配置します。({reason})")
            while True:
                 # grid_size を使用
                pos = [random.randint(0, grid_size - 1), random.randint(0, grid_size - 1)]
                if tuple(pos) not in occupied_positions:
                    hunter_positions[h] = pos
                    occupied_positions.add(tuple(pos))
                    print(f"  ハンター{h}: ランダム配置 -> {pos}")
                    break
                if len(occupied_positions) >= grid_size * grid_size:
                    raise RuntimeError("配置可能な空きマスがありません！")

    if any(p is None for p in hunter_positions):
         print(f"警告: 一部のハンターの位置が未設定です。処理に問題がある可能性があります。")

    return target_pos, hunter_positions


# --- ターゲット移動 (GRID_SIZE を使うように修正) ---
def move_target(target_pos, hunter_positions, grid_size):
    """ターゲットをランダムに縦横1マス移動させる (ハンターとの衝突回避)"""
    possible_moves = [(0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)]
    random.shuffle(possible_moves)
    current_hunter_tuples = {tuple(p) for p in hunter_positions if p}
    for dx, dy in possible_moves:
        new_x = target_pos[0] + dx
        new_y = target_pos[1] + dy
        # grid_size で範囲チェック
        if 0 <= new_x < grid_size and 0 <= new_y < grid_size:
            if tuple([new_x, new_y]) not in current_hunter_tuples:
                return [new_x, new_y]
    return list(target_pos)

# --- 捕獲判定関数 (GRID_SIZE を使うように修正) ---
def check_capture(target_pos, hunter_positions, grid_size):
    """ターゲットがハンターに上下左右を囲まれたか判定"""
    tx, ty = target_pos
    adjacent_cells = [(tx, ty + 1), (tx, ty - 1), (tx + 1, ty), (tx - 1, ty)]
    required_cells = set()
    for x, y in adjacent_cells:
         # grid_size で範囲チェック
        if 0 <= x < grid_size and 0 <= y < grid_size:
            required_cells.add(tuple([x, y]))
    if not required_cells: return False
    current_hunter_tuples = {tuple(p) for p in hunter_positions if p}
    return required_cells.issubset(current_hunter_tuples)


# --- ハンター移動フィルター関数 (GRID_SIZE を使うように修正) ---
def filter_hunter_moves(current_positions, suggested_positions, target_pos, grid_size):
    """QA推奨位置に基づき、移動制約を考慮して次の位置を決める"""
    next_positions = [list(p) if p else None for p in current_positions]
    num_hunters = len(current_positions)
    target_tuple = tuple(target_pos)
    occupied_next = {tuple(p) for p in current_positions if p}
    # print("  [移動フィルター開始]") # ログ簡略化
    sorted_hunters = sorted(suggested_positions.keys())
    for h in sorted_hunters:
        if h >= num_hunters or current_positions[h] is None: continue
        current_pos = current_positions[h]
        suggested_pos = suggested_positions[h]
        current_pos_tuple = tuple(current_pos)
        # print(f"  H{h}: 現在{current_pos}, 推奨{suggested_pos}") # ログ簡略化
        if current_pos == suggested_pos:
            # print(f"    -> 推奨位置が現在位置と同じ。移動なし。") # ログ簡略化
            continue
        move_options = []
        dx = suggested_pos[0] - current_pos[0]
        dy = suggested_pos[1] - current_pos[1]
        possible_steps = []
        if dx > 0: possible_steps.append((1, 0))
        elif dx < 0: possible_steps.append((-1, 0))
        if dy > 0: possible_steps.append((0, 1))
        elif dy < 0: possible_steps.append((0, -1))
        if not possible_steps:
             # print(f"    -> 推奨位置への有効な1ステップ方向なし。移動なし。") # ログ簡略化
             continue
        moved = False
        random.shuffle(possible_steps)
        for move_dx, move_dy in possible_steps:
            next_step_x = current_pos[0] + move_dx
            next_step_y = current_pos[1] + move_dy
            next_step_pos = [next_step_x, next_step_y]
            next_step_tuple = tuple(next_step_pos)
             # grid_size で範囲チェック
            if not (0 <= next_step_x < grid_size and 0 <= next_step_y < grid_size):
                # print(f"    -> 試行: {next_step_pos} はグリッド範囲外") # ログ簡略化
                continue
            is_collision_target = (next_step_tuple == target_tuple)
            is_collision_hunter = (next_step_tuple in occupied_next and next_step_tuple != current_pos_tuple)
            if is_collision_target:
                 # print(f"    -> 試行: {next_step_pos} はターゲット位置と衝突") # ログ簡略化
                 continue
            if is_collision_hunter:
                 # print(f"    -> 試行: {next_step_pos} は他のハンターと衝突") # ログ簡略化
                 continue
            # print(f"    -> 決定: {current_pos} -> {next_step_pos} へ移動") # ログ簡略化
            next_positions[h] = next_step_pos
            occupied_next.remove(current_pos_tuple)
            occupied_next.add(next_step_tuple)
            moved = True
            break
        # if not moved: print(f"    -> 有効な1ステップ移動先なし。移動なし。") # ログ簡略化
    # print("  [移動フィルター終了]") # ログ簡略化
    return [p for p in next_positions if p is not None]


# --- シミュレーション本体 & アニメーション ---
if __name__ == "__main__":
    # --- 初期位置の入力 (個別入力) ---
    print("--- 初期位置設定 ---")
    print(f"グリッドサイズ: {GRID_SIZE}x{GRID_SIZE}") # グリッドサイズ表示追加
    print(f"ターゲットの初期位置を 'x,y' (0-{GRID_SIZE-1}) 形式で入力してください。空欄でEnterを押すとランダム配置になります。")
    init_target_input = input("ターゲット初期位置: ")

    init_hunters_inputs = []
    print(f"\nハンター{NUM_HUNTERS}人の初期位置を1人ずつ 'x,y' (0-{GRID_SIZE-1}) 形式で入力してください。空欄でEnterを押すと、そのハンターはランダム配置になります。")
    for h in range(NUM_HUNTERS):
        hunter_input = input(f"  ハンター {h} 初期位置 (x,y): ")
        init_hunters_inputs.append(hunter_input)

    # --- 初期化 (入力値を使用) ---
    target_position, hunter_positions_list = initialize_positions(
        GRID_SIZE, NUM_HUNTERS, init_target_input, init_hunters_inputs
    )
    step_count = 0
    start_time = time.time()
    elapsed_time = 0
    caught = False
    simulation_history = []

    print(f"\n--- OpenJij版 ターゲット捕獲シミュレーション (v4, {GRID_SIZE}x{GRID_SIZE} Grid + 初期位置入力) ---") # タイトル更新
    print(f"QUBOパラメータ: A={PARAM_A}, A_far={PARAM_A_FAR}, P1={PARAM_P1}, P2={PARAM_P2}, P3={PARAM_P3}, num_reads={NUM_READS}")
    print(f"初期ターゲット位置: {target_position}")
    print(f"初期ハンター位置: {hunter_positions_list}")
    print("シミュレーション実行中... (計算に時間がかかる場合があります)") # 注意喚起追加

    # シミュレーションループ
    while elapsed_time < SIMULATION_TIME_LIMIT and not caught:
        step_count += 1
        current_time = time.time()
        elapsed_time = current_time - start_time

        current_hunter_snapshot = [list(p) for p in hunter_positions_list]
        simulation_history.append({
            'step': step_count, 'time': elapsed_time,
            'target_pos': list(target_position),
            'hunter_pos': current_hunter_snapshot
        })

        # --- ターゲット移動 ---
        target_position = move_target(target_position, hunter_positions_list, GRID_SIZE) # grid_size 渡す

        # --- ハンター移動 ---
        print(f"\n--- ステップ {step_count} (経過時間: {elapsed_time:.1f}s) ---")
        print(f"ターゲット位置: {target_position}")

        # build_qubo に grid_size を渡す
        qubo = build_qubo(target_position, GRID_SIZE, NUM_HUNTERS, PARAM_A, PARAM_A_FAR, PARAM_P1, PARAM_P2, PARAM_P3, PARAM_P4,hunter_positions_list)
        best_sample, best_energy = solve_qubo_openjij(qubo, num_reads=NUM_READS)

        if best_sample:
            suggested_positions = {}
            assigned_hunters_in_step = set()
            valid_solution_in_step = True
            for var_index, value in best_sample.items():
                if value == 1:
                    # get_hxy_from_index に grid_size を渡す
                    h, x, y = get_hxy_from_index(var_index, GRID_SIZE, NUM_HUNTERS)
                    if h in assigned_hunters_in_step:
                        valid_solution_in_step = False
                        break
                    suggested_positions[h] = [x, y]
                    assigned_hunters_in_step.add(h)
            if len(assigned_hunters_in_step) != NUM_HUNTERS: 
                valid_solution_in_step = False

            if valid_solution_in_step:
                 # filter_hunter_moves に grid_size を渡す
                hunter_positions_list = filter_hunter_moves(
                    current_hunter_snapshot, suggested_positions, target_position, GRID_SIZE
                )
            else: print("QAの解が無効なため、ハンターは移動しません。")
        else: print("QAソルバーから解が得られませんでした。ハンターは移動しません。")

        # print(f"ハンター現在位置: {hunter_positions_list}") # ログ簡略化

        # --- 捕獲判定 ---
        # check_capture に grid_size を渡す
        caught = check_capture(target_position, hunter_positions_list, GRID_SIZE)
        if caught:
             print(f"\nステップ {step_count}: ターゲット捕獲！ (上下左右を包囲)")
             simulation_history.append({ # 最終状態を記録
                'step': step_count, 
                'time': elapsed_time,
                'target_pos': list(target_position),
                'hunter_pos': [list(p) for p in hunter_positions_list],
                'caught': True })
             break

    print(f"\nシミュレーション終了 (全 {step_count} ステップ)")
    if caught: 
        print(f"結果: ターゲット捕獲成功！ (所要時間: {simulation_history[-1]['time']:.2f}秒)")
    elif elapsed_time >= SIMULATION_TIME_LIMIT: 
        print(f"結果: 時間切れ ({SIMULATION_TIME_LIMIT}秒経過)")

    # --- アニメーション描画 (GRID_SIZE 変更に対応) ---
    print("アニメーション生成中...")
    fig, ax = plt.subplots(figsize=(8, 8)) # プロットサイズを少し大きく

    def update_frame(frame_index):
        ax.clear()
        data = simulation_history[frame_index]
        step, elapsed_time = data['step'], data['time']
        target_pos, hunter_pos = data['target_pos'], data['hunter_pos']
        is_caught = data.get('caught', False)
        ax.plot(target_pos[0], target_pos[1], TARGET_MARKER, markersize=8, label='Target') # マーカーサイズ調整
        if hunter_pos:
            valid_hunter_pos = [p for p in hunter_pos if p]
            if valid_hunter_pos:
                hunters_x = [p[0] for p in valid_hunter_pos]
                hunters_y = [p[1] for p in valid_hunter_pos]
                ax.plot(hunters_x, hunters_y, HUNTER_MARKER, markersize=6, linestyle='None', label='Hunters') # マーカーサイズ調整
        # 目盛りとグリッド線の設定を GRID_SIZE に合わせる
        ax.set_xticks(np.arange(-0.5, GRID_SIZE, 1), [])
        ax.set_yticks(np.arange(-0.5, GRID_SIZE, 1), [])
        # グリッド線が多くなりすぎる場合は間隔を調整 (例: 5ごと)
        ax.set_xticks(np.arange(-0.5, GRID_SIZE, 5), minor=True)
        ax.set_yticks(np.arange(-0.5, GRID_SIZE, 5), minor=True)
        ax.grid(True, which='major', color='gray', linestyle='-', linewidth=0.5)
        ax.grid(True, which='minor', color='gray', linestyle=':', linewidth=0.25) # マイナーグリッド追加
        # 軸範囲を GRID_SIZE に合わせる
        ax.set_xlim(-0.5, GRID_SIZE - 0.5); ax.set_ylim(-0.5, GRID_SIZE - 0.5)
        ax.set_aspect('equal', adjustable='box')
        title = f'Step: {step}, Time: {elapsed_time:.1f}s';
        if is_caught: title += ' - Caught!'
        ax.set_title(title)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0)); fig.tight_layout(rect=[0, 0, 0.85, 1])

    # アニメーション生成 (フレーム数を制限してテストしやすくすることも可能 frames=min(len(simulation_history), 100) など)
    ani = animation.FuncAnimation(fig, update_frame, frames=len(simulation_history), interval=300, repeat=False)
    from IPython.display import HTML, display
    print("HTMLアニメーションを生成・表示します...")
    html_output = HTML(ani.to_jshtml())
    display(html_output)
    plt.close(fig)
    print("アニメーション表示完了。")