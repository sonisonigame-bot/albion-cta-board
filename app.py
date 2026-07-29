import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="🐻KUMA CTA Board", layout="wide")
st.title("🐻 KUMA 40人構成＆出席ボード")

# --- 1. パスワードの設定 ---
MEMBER_PASSWORD = "sonikuma"
ADMIN_PASSWORD = "sonikuma12341234"

# --- 2. ログイン機能 ---
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

if not (is_admin or is_member):
    st.stop()

# --- 3. 内部ファイル（CSV）からデータ読み込み ---
DATA_FILE = "cta_data.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        # ★読み取ったCSVデータをもとにした初期構成
        new_df = pd.DataFrame({
            "パーティ": [f"Party {(i//5)+1}" for i in range(40)],
            "ロール": ['ヒーラー', 'タンク', 'タンク', 'タンク', 'タンク', 'ヒーラー', 'DPS(Melee)', 'DPS(Melee)', 'サポート', 'DPS(Melee)', 'DPS(Melee)', 'DPS(Melee)', 'DPS(Ranged)', 'DPS(Ranged)', 'DPS(Ranged)', 'DPS(Ranged)', 'ヒーラー', 'ヒーラー', 'ヒーラー', 'サポート', 'ヒーラー', 'タンク', 'サポート', 'サポート', 'ヒーラー', 'サポート', 'ヒーラー', 'DPS(Ranged)', 'DPS(Melee)', 'サポート', 'DPS(Ranged)', 'DPS(Ranged)', 'タンク', 'DPS(Ranged)', 'DPS(Ranged)', 'ヒーラー', 'DPS(Ranged)', '(未定)', '(未定)', '(未定)'],
            "枠(詳細)": [f"Slot {i+1}" for i in range(40)],
            "プレイヤー名": ["" for _ in range(40)],
            "コメント": ["" for _ in range(40)],
            "武器": ['アースルーンの杖', 'ヘビーメイス', 'ヘビーメイス', '基岩のメイス', '基岩のメイス', 'ルートバウンドの杖', 'カービングソード', 'レルムブレイカー', '生呪の杖', 'スパイクガントレット', 'リフトグレーブ', '業火の拳', 'ロングボウ', 'ドーンソング', '凍土のプリズム', '凍土のプリズム', '堕落の杖', '堕落の杖', '堕落の杖', '胴枯れの杖', 'アースルーンの杖', 'ハンマー', '偉大なアーケインの杖', '偉大なアーケインの杖', '堕落の杖', 'アーケインの杖', 'ルートバウンドの杖', 'スピリットハンター', 'リフトグレーブ', '胴枯れの杖', '神秘の杖', '不可思議の杖', 'ヘビーメイス', '破滅の杖', 'オースキーパー', '堕落の杖', '(未定)', '(未定)', '(未定)', '(未定)'],
            "オフハンド": ['なし', 'なし', 'なし', 'シールド', 'シールド', 'なし', 'なし', 'なし', 'シールド', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'シールド', 'なし', 'なし', 'なし', 'シールド', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', 'なし', '(未定)', '(未定)', '(未定)', '(未定)'],
            "頭": ['アサシンフード', '法官のヘルメット', '法官のヘルメット', 'アサシンフード', 'アサシンフード', 'アサシンフード', '法官のヘルメット', '騎士のヘルメット', 'アサシンフード', '騎士のヘルメット', 'アサシンフード', 'ヘリオンフード', 'ミストウォーカーのフード', 'アサシンフード', 'アサシンフード', 'アサシンフード', 'ドルイドの頭巾', 'ドルイドの頭巾', '騎士のヘルメット', 'アサシンフード', 'アサシンフード', 'アサシンフード', 'アサシンフード', 'アサシンフード', 'ドルイドの頭巾', 'ヘリオンフード', 'アサシンフード', 'アサシンフード', 'アサシンフード', 'アサシンフード', 'アサシンフード', 'アサシンフード', '法官のヘルメット', 'アサシンフード', 'アサシンフード', '騎士のヘルメット', '(未定)', '(未定)', '(未定)', '(未定)'],
            "胴": ['法官のアーマー', 'ガーディアンアーマー', 'ガーディアンアーマー', 'デーモンアーマー', 'デーモンアーマー', '法官のアーマー', '法官のアーマー', '王家のジャケット', 'デーモンアーマー', '不屈のジャケット', '聖職者のローブ', '不屈のジャケット', '聖職者のローブ', 'フェイスケールのローブ', '学徒のローブ', '学徒のローブ', '純潔のローブ', '純潔のローブ', '純潔のローブ', '聖職者のローブ', '法官のアーマー', 'デーモンアーマー', 'デーモンアーマー', 'デーモンアーマー', '純潔のローブ', '騎士のアーマー', '法官のアーマー', '王家のジャケット', '聖職者のローブ', '聖職者のローブ', '法官のアーマー', '法官のアーマー', 'ガーディアンアーマー', '学徒のローブ', 'デーモンアーマー', '純潔のローブ', '(未定)', '(未定)', '(未定)', '(未定)'],
            "足": ['狩人の靴', '狩人の靴', '狩人の靴', '墓守のブーツ', '墓守のブーツ', '傭兵の靴', '狂信者のサンダル', '墓守のブーツ', '墓守のブーツ', '墓守のブーツ', 'ストーカー靴', '墓守のブーツ', 'ストーカー靴', 'ストーカー靴', 'ストーカー靴', 'ストーカー靴', '傭兵の靴', '傭兵の靴', '傭兵の靴', '傭兵の靴', '狩人の靴', '狩人の靴', '傭兵の靴', '傭兵の靴', '傭兵の靴', '墓守のブーツ', '傭兵の靴', '墓守のブーツ', 'ストーカー靴', '傭兵の靴', '傭兵の靴', '傭兵の靴', '狩人の靴', '傭兵の靴', '墓守のブーツ', '傭兵の靴', '(未定)', '(未定)', '(未定)', '(未定)'],
            "マント": ['Martlockケープ', 'Martlockケープ', 'Martlockケープ', 'Martlockケープ', 'Martlockケープ', 'Lymhurstケープ', 'Martlockケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Martlockケープ', 'Martlockケープ', 'Martlockケープ', 'Martlockケープ', 'Lymhurstケープ', 'Martlockケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Lymhurstケープ', 'Martlockケープ', 'Lymhurstケープ', 'Martlockケープ', 'Lymhurstケープ', '(未定)', '(未定)', '(未定)', '(未定)'],
            "食べ物": ["(未定)"] * 40,
        })
        return new_df

df = load_data()
df = df.fillna("")

# --- 4. ダッシュボード（集計） ---
attendees = df[df["プレイヤー名"].astype(str).str.strip() != ""]
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

# --- 5. 編集ロック設定 ---
EQUIPMENT_COLUMNS = ["パーティ", "ロール", "枠(詳細)", "武器", "オフハンド", "頭", "胴", "足", "マント", "食べ物"]

if is_admin:
    disabled_cols = []
    config = {
        "ロール": st.column_config.SelectboxColumn("ロール", options=["タンク", "ヒーラー", "DPS(Melee)", "DPS(Ranged)", "サポート", "コーラー"])
    }
    st.write("🔧 **【管理者画面】** 表のセルをクリックして構成を編集してください。（Enterキーで自動保存）")
else:
    disabled_cols = EQUIPMENT_COLUMNS
    config = {}
    st.write("✋ **【出席登録】** 自分の乗る枠の「プレイヤー名」と「コメント」を入力してください。（Enterキーで自動保存）")

# --- 6. 表の表示 ---
edited_df = st.data_editor(
    df,
    disabled=disabled_cols,
    column_config=config,
    use_container_width=True,
    hide_index=True,
    height=1450 # 40人分スクロールなしで見やすいように縦幅を広げました
)

# --- 7. 🔥 内部ファイルへの自動保存システム ---
if not df.equals(edited_df):
    edited_df.to_csv(DATA_FILE, index=False)
    st.success("🔄 変更を自動保存しました！")
    st.rerun()
