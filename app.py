import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

# 画面設定
st.set_page_config(page_title="🐻KUMA Albion Dashboard", layout="wide")
st.title("🐻 KUMA ギルドダッシュボード (Asiaサーバー)")
st.write("Albion Onlineの公式データから自動取得しています。")

# --- 1. API設定 ---
BASE_URL = "https://gameinfo-sgp.albiononline.com/api/gameinfo"
RENDER_URL = "https://render.albiononline.com/v1/item"
GUILD_NAME = "KUMA"

# --- 2. ユーティリティ・データ取得関数 ---
def convert_time(time_str):
    """AlbionのUTC時間を日本時間(JST)とUTCに変換する"""
    try:
        # "2023-10-26T12:34:56.789Z" のような文字列の先頭19文字分を取得して変換
        dt_utc = datetime.strptime(time_str[:19], "%Y-%m-%dT%H:%M:%S")
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        dt_jst = dt_utc.astimezone(timezone(timedelta(hours=9)))
        return dt_utc.strftime("%m/%d %H:%M"), dt_jst.strftime("%m/%d %H:%M")
    except Exception:
        return "Unknown", "Unknown"

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
    except Exception:
        pass
    return None

@st.cache_data(ttl=300)
def get_guild_members(guild_id):
    members_url = f"{BASE_URL}/guilds/{guild_id}/members"
    try:
        response = requests.get(members_url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

# ★ offsetを追加してページ切り替えに対応
@st.cache_data(ttl=60)
def get_guild_events(guild_id, offset=0):
    events_url = f"{BASE_URL}/events?limit=20&offset={offset}&guildId={guild_id}"
    try:
        response = requests.get(events_url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

@st.cache_data(ttl=300)
def search_player(player_name):
    search_url = f"{BASE_URL}/search?q={player_name}"
    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for p in data.get("players", []):
                if p["Name"].upper() == player_name.upper():
                    player_id = p["Id"]
                    detail_url = f"{BASE_URL}/players/{player_id}"
                    detail_res = requests.get(detail_url, timeout=10)
                    if detail_res.status_code == 200:
                        return {"info": detail_res.json(), "id": player_id}
    except Exception:
        pass
    return None

@st.cache_data(ttl=300)
def get_player_recent_kill(player_id):
    kills_url = f"{BASE_URL}/players/{player_id}/kills?limit=1"
    try:
        response = requests.get(kills_url, timeout=10)
        if response.status_code == 200:
            kills = response.json()
            if kills:
                return kills[0]
    except Exception:
        pass
    return None

# --- 3. データの取得 ---
with st.spinner("Albion公式サーバーからデータを取得中..."):
    guild_info = get_guild_info(GUILD_NAME)

if guild_info:
    guild_id = guild_info["Id"]
    
    # --- 4. 画面表示 ---
    tab1, tab2, tab3 = st.tabs(["📊 ギルド情報＆メンバー", "⚔️ 最近のキルボード (最大100件)", "🔍 メンバー検索"])

    # 【タブ1】ギルド情報とメンバーランキング
    with tab1:
        st.subheader("📊 ギルド総合ステータス")
        col1, col2, col3 = st.columns(3)
        kill_fame = int(guild_info.get('killFame') or guild_info.get('KillFame') or 0)
        death_fame = int(guild_info.get('deathFame') or guild_info.get('DeathFame') or 0)
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

    # 【タブ2】最新のキル＆デス履歴 (ページネーション対応)
    with tab2:
        st.subheader("⚔️ 直近の戦闘ログ")
        
        # ★ ページ切り替え用UI（1〜5ページで最大100件）
        selected_page = st.radio("表示するページを選択してください", [1, 2, 3, 4, 5], horizontal=True)
        current_offset = (selected_page - 1) * 20
        
        events_data = get_guild_events(guild_id, offset=current_offset)
        
        if events_data:
            for ev in events_data:
                killer = ev.get("Killer", {})
                victim = ev.get("Victim", {})
                
                # ★ 時間の取得と変換
                time_str = ev.get("TimeStamp", "")
                utc_time, jst_time = convert_time(time_str)
                
                # ★ 装備の推定価値（獲得フェイム基準）
                victim_fame = ev.get("TotalVictimKillFame", 0)
                
                k_name = killer.get("Name", "Unknown")
                k_guild = killer.get("GuildName", "")
                k_ip = int(killer.get("AverageItemPower", 0))
                
                v_name = victim.get("Name", "Unknown")
                v_guild = victim.get("GuildName", "")
                v_ip = int(victim.get("AverageItemPower", 0))
                
                victim_equipment = victim.get("Equipment", {})
                html_images = ""
                for slot, item in victim_equipment.items():
                    if item:
                        item_name = item.get('Type')
                        img_url = f"{RENDER_URL}/{item_name}.png?size=60"
                        html_images += f'<img src="{img_url}" width="50" title="{item_name}" style="background-color: #2c2c2c; border-radius: 8px; margin-right: 5px; border: 1px solid #555;">'
                
                # 表示の組み立て
                if k_guild.upper() == GUILD_NAME.upper():
                    st.success(f"🔥 **キル** : **{k_name}** (IP: {k_ip}) ⚔️ 倒した相手 ➡ **{v_name}** [{v_guild}] (IP: {v_ip})")
                    st.caption(f"🕒 **日本時間:** {jst_time} (UTC: {utc_time}) ｜ 💰 **装備推定価値(Fame):** {victim_fame:,}")
                    if html_images:
                        st.markdown(f"**🎁 相手の装備（ドロップ候補）:**<br>{html_images}", unsafe_allow_html=True)
                else:
                    st.error(f"💀 **デス** : **{v_name}** (IP: {v_ip}) ⚔️ 倒された相手 ➡ **{k_name}** [{k_guild}] (IP: {k_ip})")
                    st.caption(f"🕒 **日本時間:** {jst_time} (UTC: {utc_time}) ｜ 💰 **ロスト推定価値(Fame):** {victim_fame:,}")
                    if html_images:
                        st.markdown(f"**💥 ロストした装備:**<br>{html_images}", unsafe_allow_html=True)
                
                st.write("---")
        else:
            st.info("このページの戦闘データは見つかりませんでした。")

    # 【タブ3】個人メンバー検索
    with tab3:
        st.subheader("🔍 プレイヤー詳細検索")
        st.write("気になるプレイヤーの名前を入力して、現在のステータスと直近の戦闘装備を確認できます。")
        
        search_name = st.text_input("プレイヤー名を入力（例: sonikuma）")
        if st.button("検索する", type="primary"):
            if search_name:
                with st.spinner(f"「{search_name}」のデータを検索中..."):
                    player_result = search_player(search_name)
                    
                    if player_result:
                        player_data = player_result["info"]
                        player_id = player_result["id"]
                        
                        st.success(f"✅ {player_data['Name']} のデータが見つかりました！")
                        
                        p_col1, p_col2 = st.columns(2)
                        p_k_fame = int(player_data.get('KillFame') or player_data.get('killFame') or 0)
                        p_d_fame = int(player_data.get('DeathFame') or player_data.get('deathFame') or 0)
                        
                        p_col1.metric("🔥 キルフェイム", f"{p_k_fame:,}")
                        p_col2.metric("💀 デスフェイム", f"{p_d_fame:,}")
                        
                        st.write(f"🛡️ **所属ギルド:** {player_data.get('GuildName', '無所属')}")
                        
                        recent_kill = get_player_recent_kill(player_id)
                        if recent_kill:
                            killer_equip = recent_kill.get("Killer", {}).get("Equipment", {})
                            equip_html = ""
                            for slot, item in killer_equip.items():
                                if item:
                                    item_name = item.get('Type')
                                    img_url = f"{RENDER_URL}/{item_name}.png?size=80"
                                    equip_html += f'<img src="{img_url}" width="60" title="{item_name}" style="background-color: #2c2c2c; border-radius: 8px; margin-right: 5px; border: 1px solid #777;">'
                            
                            st.markdown(f"**⚔️ 直近の戦闘装備 (Latest Combat Loadout):**<br>{equip_html}", unsafe_allow_html=True)
                            
                            time_str = recent_kill.get("TimeStamp", "")
                            utc_time, jst_time = convert_time(time_str)
                            st.caption(f"※🕒 {jst_time} に {recent_kill.get('Victim', {}).get('Name', 'Unknown')} をキルした際の装備です。")
                        else:
                            st.info("直近の戦闘データ（装備情報）が見つかりませんでした。")
                        
                        st.divider()
                        
                        stats = player_data.get('LifetimeStatistics', {})
                        pve_fame = int(stats.get('PvE', {}).get('Total', 0))
                        crafting_fame = int(stats.get('Crafting', {}).get('Total', 0))
                        gathering_fame = int(stats.get('Gathering', {}).get('All', {}).get('Total', 0))
                        
                        st.markdown(f"""
                        **[ 📊 生涯フェイム ]**
                        * ⚔️ PvE (Mob討伐): **{pve_fame:,}**
                        * 🔨 製作 (Crafting): **{crafting_fame:,}**
                        * 🪓 採集 (Gathering): **{gathering_fame:,}**
                        """)
                    else:
                        st.error("プレイヤーが見つかりませんでした。名前が間違っているか、APIサーバーが混雑しています。")

else:
    st.error(f"ギルド『{GUILD_NAME}』のデータが見つかりませんでした。公式APIが混雑している可能性があります。")
