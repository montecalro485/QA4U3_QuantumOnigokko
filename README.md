# QuantumOnigokko
QuantumOnigokko created by QA4U3 Group4430_QuantumUnicorns at Tohoku University 


# 本プロジェクトの参照方法

- 以下のファイルが各フォルダに存在する


-- 動画ファイル

  実行結果の動画ファイルを下記の表に格納する

|項目|詳細|フォルダ|
|----|----|----|
|改善前デモ_ターゲット位置が中心|改善前のソースにおいて、ターゲット位置が10,10から実行した結果(ログと動画)|demo\before_taget_center|
|改善前デモ_ターゲット位置が中心|改善前のソースにおいて、ターゲット位置が1,1から実行した結果(ログと動画)|demo\before_taget_corner|
|改善後デモ_ターゲット位置が中心|改善後のソースにおいて、ターゲット位置が10,10から実行した結果(ログと動画)|demo\after_taget_center|
|改善後デモ_ターゲット位置が中心|改善後のソースにおいて、ターゲット位置が1,1から実行した結果(ログと動画)|demo\after_taget_corner|



-- ソース

  各ソースの説明
|ソース名|詳細|ファイル|
|----|----|----|
|改善前ソース|改善前のソース|source\quantum_sim_onigokko_before.py|
|改善後ソース_実行前|改善後のソースで、コサイン類似度を前もって計算する。<br>その結果をgoogleドライブの/content配下に格納。<br>実行時間は1時間ほどかかる。<br>代わりの手段として下記に示す前提ファイルをgoogleドライブのcontentフォルダに格納する。|source\quantum_sim_onigokko_initial.py|
|改善後ソース_シミュレーション|改善後のソースにおいて、シミュレーションするソース。<br>「改善後ソース_実行前」を動作するか、もしくは、googleドライブのcontentフォルダ直下に前提ファイル（次の項で示す）を置くかしないと実行できない。|source\quantum_sim_onigokko_after.py|



-- 前提ファイル

  改善後のソースを実行前に格納するファイル。source\quantum_sim_onigokko_initial.pyを実行すると本ファイルの格納は不要である。
|ファイル種類|フォルダ|
|----|----|
|前提ファイル|prepared_file|

# 改善前の動作方法(google Colab)

1.!pip install openjij dimod numpy matplotlib numpy を実行する

2.quantum_sim_onigokko_before.pyを実行

# 改善後の動作方法(google Colab)

1.!pip install openjij dimod numpy matplotlib numpy を実行する

2.contentフォルダに以下の方法でファイルを置く

方法1 source配下にあるquantum_sim_onigokko_initial.pyを実行

方法2 prepared_fileフォルダにあるファイルを置く

3.quantum_sim_onigokko_after.pyを実行
