import streamlit as st
import pandas as pd

# ページの基本設定（画面を広く使う設定）
st.set_page_config(layout="wide")

st.title("⚔️ Albion Online ギルドCTAダッシュボード")

# ギルドメンバーの初期データ（実際はスプレッドシートから読み込みます）
if 'albion_data' not in st.session_state:
    st.session_state.albion_data = pd.DataFrame({
        "プレイヤー名": ["Taro", "Jiro", "Saburo", "Shiro"],
        "ロール": ["タンク (Engage)", "ヒーラー (Holy)", "DPS (Ranged)", "サポート (Arcane)"],
        "予定装備 (武器)": ["Camlann Mace", "Fallen Staff", "Permafrost", "Locus"],
        "装備IP (目安)": [1400, 1350, 1500, 1300],
        "本日のCTA参加": [True, False, True, False],
        "備考": ["少し遅れます", "リアル仕事", "", ""]
    })

st.subheader("🛡️ 今夜のCTA出欠表 (12:00 UTC / 日本時間 21:00)")
st.write("自分の名前の行を見つけて、参加チェックとIP、武器を更新してください。")

# ロールの選択肢（ドロップダウンで選べるようにする設定）
column_config = {
    "ロール": st.column_config.SelectboxColumn(
        "ロール",
        options=["タンク (Engage)", "タンク (Defensive)", "ヒーラー (Holy)", "ヒーラー (Nature)", "DPS (Melee)", "DPS (Ranged)", "サポート", "コーラー"]
    ),
    "装備IP (目安)": st.column_config.NumberColumn(
        "装備IP",
        min_value=1000,
        max_value=2000,
        step=10
    )
}

# データエディターの表示（ブラウザ上で直接編集できます）
edited_df = st.data_editor(
    st.session_state.albion_data, 
    column_config=column_config,
    num_rows="dynamic",
    use_container_width=True
)

# ======== 自動集計機能 ========
# 参加者だけを抽出
attendees = edited_df[edited_df["本日のCTA参加"] == True]

# 画面を2分割して、集計データを表示
col1, col2 = st.columns(2)

with col1:
    st.success(f"🔥 現在の参加予定人数: {len(attendees)} 名")
    # ロールごとの人数をグラフ化
    role_counts = attendees["ロール"].value_counts()
    st.bar_chart(role_counts)

with col2:
    st.warning("⚠️ パーティ編成アラート")
    if len(attendees[attendees["ロール"].str.contains("ヒーラー", na=False)]) < 2:
        st.error("ヒーラーが不足しています！（最低2名推奨）")
    if len(attendees[attendees["ロール"].str.contains("タンク", na=False)]) < 1:
        st.error("タンクがいません！")