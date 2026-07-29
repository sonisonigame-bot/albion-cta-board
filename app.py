import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Albion CTA Board", layout="wide")
st.title("⚔️ Albion Online 40人構成＆出席ボード")

# --- 1. パスワードの設定 ---
MEMBER_PASSWORD = "sonikuma"
ADMIN_PASSWORD = "sonikuma12341234"

# --- 2. ログイン機能（サイドバー） ---
with st.sidebar:
    st.header("🔑 ログイン")
    entered_password = st.text_input("パスワードを入力してください", type="password")
    
    is_admin = (entered_password == ADMIN_PASSWORD)
    is_member = (entered_password == MEMBER_PASSWORD)
    
    if is_admin:
        st.success("👑 管理者モード\n\n構成と全メンバーの編集が可能です。")
    elif is_member:
        st.info("👤 メンバーモード\n\n「名前」と「コメント」のみ入力可能です。")
    else:
        if entered_password:
            st.error("パスワードが違います")
        st.warning("パスワードを入力すると参加表が表示されます。")

# パスワードが合っていない場合は、ここで画面の描画をストップする
if not (is_admin or is_member):
    st.stop()

# --- 3. スプレッドシート読み込み ---
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="2m")

# 初期データの作成（データが空、または「コメント」列がない場合）
if df.empty or "コメント" not in df.columns:
    df = pd.DataFrame({
        "パーティ": [f"Party {(i//5)+1}" for i in range(40)],
        "ロール": ["タンク", "ヒーラー", "DPS(Melee)", "DPS(Ranged)", "サポート"] * 8,
        "枠(詳細)": [f"Slot {i+1}" for i in range(40)],
        "プレイヤー名": ["" for _ in range(40)],
        "コメント": ["" for _ in range(40)], # ★新規追加
        "武器": ["(未定)"] * 40,
        "オフハンド": ["-"] * 40,
        "頭": ["(未定)"] * 40,
        "胴": ["(未定)"] * 40,
        "足": ["(未定)"] * 40,
        "マント": ["(未定)"] * 40,
        "食べ物": ["(未定)"] * 40,
    })

# データ内の「NaN（欠損値）」を空文字に変換（エラー防止）
df = df.fillna("")

# --- 4. ダッシュボード（集計） ---
attendees = df[df["プレイヤー名"].str.strip() != ""]
filled_count = len(attendees)

st.subheader("📊 現在の編成ステータス")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="🔥 参加人数", value=f"{filled_count} / 40 名")
    st.progress(filled_count / 40.0 if filled_count <= 40 else 1.0)
with col2:
    healer_count = len(attendees[attendees["ロール"].str.contains("ヒーラー", na=False)])
    tank_count = len(attendees[attendees["ロール"].str.contains("タンク", na=False)])
    st.write(f"🛡️ **タンク:** {tank_count} 名 ｜ 💚 **ヒーラー:** {healer_count} 名")
with col3:
    if healer_count < 6 and filled_count > 10:
        st.error("⚠️ ヒーラーが不足しています！")
    elif tank_count < 4 and filled_count > 10:
        st.warning("⚠️ タンクが少なめです。")
    else:
        st.success("✅ バランス良好！")

st.divider()

# --- 5. 編集ロック設定（権限コントロール） ---
# 装備・構成に関する列のリスト（メンバーには触らせない）
EQUIPMENT_COLUMNS = ["パーティ", "ロール", "枠(詳細)", "武器", "オフハンド", "頭", "胴", "足", "マント", "食べ物"]

if is_admin:
    # 管理者はすべて編集可能（ロックなし）
    disabled_cols = []
    config = {
        "ロール": st.column_config.SelectboxColumn("ロール", options=["タンク", "ヒーラー", "DPS(Melee)", "DPS(Ranged)", "サポート", "コーラー"])
    }
    st.write("🔧 **【管理者画面】** 表のセルをクリックして構成を編集してください。（Enterキーを押すと自動保存されます）")
else:
    # メンバーは「プレイヤー名」「コメント」以外をロック
    disabled_cols = EQUIPMENT_COLUMNS
    config = {}
    st.write("✋ **【出席登録】** 自分の乗る枠の「プレイヤー名」と「コメント」を入力してください。（Enterキーを押すと自動保存されます）")

# --- 6. 表の表示 ---
edited_df = st.data_editor(
    df,
    disabled=disabled_cols,
    column_config=config,
    use_container_width=True,
    hide_index=True,
    height=800 
)

# --- 7. 🔥 完全自動保存システム 🔥 ---
# 読み込んだ時のデータ(df)と、画面上で編集されたデータ(edited_df)に違いがあるかチェック
if not df.equals(edited_df):
    # 違いがあれば、自動的にスプレッドシートを更新！
    conn.update(data=edited_df)
    st.success("🔄 変更を自動保存しました！")
    st.rerun() # 画面をリロードして最新状態をキープ
