import streamlit as st
import requests
import pandas as pd

# 画面設定
st.set_page_config(page_title="🐻KUMA Albion Dashboard", layout="wide")
st.title("🐻 KUMA ギルドダッシュボード (Asiaサーバー)")
st.write("Albion Onlineの公式データから自動取得しています。")

# --- 1. Albion Asia(East)サーバーのAPI設定 ---
BASE_URL = "https://gameinfo-sgp.albiononline.com/api/gameinfo"
GUILD_NAME = "KUMA"

# --- 2. データを取得する関数（@st.cache_dataで通信を節約） ---
@st.cache_data(ttl=300) # 5分間は結果を保存し、APIへの負荷を減らす
def get_guild_info(guild_name):
    """ギルドの名前からIDを検索し、基本情報を取得する"""
    search_url = f"{BASE_URL}/search?q={guild_name}"
    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # 検索結果から名前が完全一致するギルドを探す
            for guild in data.get("guilds", []):
                if guild["Name"].upper() == guild_name.upper():
                    return guild
    except Exception as e:
        st.error(f"通信エラーが発生しました: {e}")
    return None

@st.cache_data(ttl=300)
def get_guild_members(guild_id):
    """ギルドIDから所属メンバーの一覧と戦績を取得する"""
    members_url = f"{BASE_URL}/guilds/{guild_id}/members"
    try:
        response = requests.get(members_url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return []

# --- 3. データの取得と表示 ---
with st.spinner("Albion公式サーバーからデータを取得中..."):
    guild_info = get_guild_info(GUILD_NAME)

if guild_info:
    guild_id = guild_info["Id"]
    st.success("✅ データ取得成功！")

    # --- ギルドの基本ステータス ---
    st.subheader("📊 ギルド総合ステータス")
    col1, col2, col3 = st.columns(3)
    
    # 3桁区切りのカンマを入れて見やすく表示
    kill_fame = guild_info.get('KillFame', 0)
    death_fame = guild_info.get('DeathFame', 0)
    
    col1.metric("🔥 総キルフェイム", f"{kill_fame:,}")
    col2.metric("💀 総デスフェイム", f"{death_fame:,}")
    
    # キルデス比（K/D）を計算
    kd_ratio = kill_fame / death_fame if death_fame > 0 else 0
    col3.metric("⚖️ K/D 比", f"{kd_ratio:.2f}")

    st.divider()

    # --- メンバーの戦績ランキング ---
    st.subheader("👥 メンバー別 戦績ボード")
    members_data = get_guild_members(guild_id)
    
    if members_data:
        # 取得したデータをPandas（表計算ツール）に変換
        df = pd.DataFrame(members_data)
        
        # 必要な列だけを抽出して日本語名に変更
        df = df[['Name', 'KillFame', 'DeathFame', 'FameRatio']]
        df.columns = ['プレイヤー名', 'キルフェイム', 'デスフェイム', 'K/D比']
        
        # キルフェイムが高い順に並び替え
        df = df.sort_values(by='キルフェイム', ascending=False)
        
        # インデックスを1からのランキング順位にする
        df.index = range(1, len(df) + 1)
        
        # 表の表示
        st.dataframe(
            df, 
            use_container_width=True, 
            height=600
        )
else:
    st.error(f"ギルド『{GUILD_NAME}』のデータが見つかりませんでした。公式APIが混雑している可能性があります。")
