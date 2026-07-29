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

# --- 2. データを取得する関数 ---
@st.cache_data(ttl=300)
def get_guild_info(guild_name):
    search_url = f"{BASE_URL}/search?q={guild_name}"
    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for guild in data.get("guilds", []):
                if guild["Name"].upper() == guild_name.upper():
                    return guild
    except Exception as e:
        pass
    return None

@st.cache_data(ttl=300)
def get_guild_members(guild_id):
    members_url = f"{BASE_URL}/guilds/{guild_id}/members"
    try:
        response = requests.get(members_url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return []

@st.cache_data(ttl=60) # キル履歴は頻繁に変わるため、1分で最新化
def get_guild_events(guild_id):
    """ギルドの最新の戦闘イベント（キル/デス）を取得する"""
    events_url = f"{BASE_URL}/events?limit=20&offset=0&guildId={guild_id}"
    try:
        response = requests.get(events_url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return []

# --- 3. データの取得 ---
with st.spinner("Albion公式サーバーからデータを取得中..."):
    guild_info = get_guild_info(GUILD_NAME)

if guild_info:
    guild_id = guild_info["Id"]
    st.success("✅ データ取得成功！")

    # --- 4. 画面表示（タブで分割） ---
    tab1, tab2 = st.tabs(["📊 ギルド情報＆メンバー", "⚔️ 最近のキルボード (最新20件)"])

    # 【タブ1】ギルド情報とメンバーランキング
    with tab1:
        st.subheader("📊 ギルド総合ステータス")
        col1, col2, col3 = st.columns(3)
        
        # エラー対策：データが空でも0として扱う
        raw_kill = guild_info.get('killFame') or guild_info.get('KillFame') or 0
        raw_death = guild_info.get('deathFame') or guild_info.get('DeathFame') or 0
        
        kill_fame = int(raw_kill)
        death_fame = int(raw_death)
        
        col1.metric("🔥 総キルフェイム", f"{kill_fame:,}")
        col2.metric("💀 総デスフェイム", f"{death_fame:,}")
        
        kd_ratio = kill_fame / death_fame if death_fame > 0 else 0
        col3.metric("⚖️ K/D 比", f"{kd_ratio:.2f}")

        st.divider()

        st.subheader("👥 メンバー別 戦績ボード")
        members_data = get_guild_members(guild_id)
        
        if members_data:
            df = pd.DataFrame(members_data)
            df = df[['Name', 'KillFame', 'DeathFame', 'FameRatio']]
            df.columns = ['プレイヤー名', 'キルフェイム', 'デスフェイム', 'K/D比']
            df = df.sort_values(by='キルフェイム', ascending=False)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, height=600)

    # 【タブ2】最新のキル＆デス履歴
    with tab2:
        st.subheader("⚔️ 直近の戦闘ログ (キル / デス)")
        events_data = get_guild_events(guild_id)
        
        if events_data:
            for ev in events_data:
                killer = ev.get("Killer", {})
                victim = ev.get("Victim", {})
                
                # キラー（倒した側）の情報
                k_name = killer.get("Name", "Unknown")
                k_guild = killer.get("GuildName", "")
                k_ip = int(killer.get("AverageItemPower", 0))
                
                # ビクティム（倒された側）の情報
                v_name = victim.get("Name", "Unknown")
                v_guild = victim.get("GuildName", "")
                v_ip = int(victim.get("AverageItemPower", 0))
                
                # KUMAのメンバーがキルしたか、デスしたかで表示を変える
                if k_guild.upper() == GUILD_NAME.upper():
                    st.info(f"🔥 **キル** : **{k_name}** (IP: {k_ip}) ⚔️ 倒した相手 ➡ **{v_name}** [{v_guild}] (IP: {v_ip})")
                else:
                    st.error(f"💀 **デス** : **{v_name}** (IP: {v_ip}) ⚔️ 倒された相手 ➡ **{k_name}** [{k_guild}] (IP: {k_ip})")
        else:
            st.write("最近の戦闘データが見つかりませんでした。")

else:
    st.error(f"ギルド『{GUILD_NAME}』のデータが見つかりませんでした。公式APIが混雑している可能性があります。")
