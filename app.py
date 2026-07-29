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
    try:
        dt_utc = datetime.strptime(time_str[:19], "%Y-%m-%dT%H:%M:%S")
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        dt_jst = dt_utc.astimezone(timezone(timedelta(hours=9)))
        return dt_utc.strftime("%m/%d %H:%M"), dt_jst.strftime("%m/%d %H:%M")
    except Exception:
        return "Unknown", "Unknown"

def render_equipment_html(equipment_dict):
    html_images = ""
    for slot, item in equipment_dict.items():
        if item:
            item_name = item.get('Type')
            img_url = f"{RENDER_URL}/{item_name}.png?size=60"
            html_images += f'<img src="{img_url}" width="50" title="{item_name}" style="background-color: #2c2c2c; border-radius: 8px; margin-right: 5px; border: 1px solid #555;">'
    return html_images

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
def get_player_recent_history(player_id, event_type="kills", limit=3):
    url = f"{BASE_URL}/players/{player_id}/{event_type}?limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()[:limit]
    except Exception:
        pass
    return []

# ★ 新規追加：分析用の大量データ一括取得（100件）
@st.cache_data(ttl=300)
def get_analysis_events(guild_id):
    events = []
    for offset in [0, 50]:
        url = f"{BASE_URL}/events?limit=50&offset={offset}&guildId={guild_id}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                events.extend(res.json())
        except Exception:
            pass
    return events

# ★ 新規追加：集団戦(ZvZ)バトルデータの取得
@st.cache_data(ttl=300)
def get_guild_battles(guild_id):
    url = f"{BASE_URL}/battles?limit=5&offset=0&guildId={guild_id}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

# --- 3. データの取得 ---
with st.spinner("Albion公式サーバーからデータを取得中..."):
    guild_info = get_guild_info(GUILD_NAME)

if guild_info:
    guild_id = guild_info["Id"]
    
    # --- 4. 画面表示 ---
    # ★ タブを4つに拡張しました！
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 ギルド総合ステータス", 
        "⚔️ 最近のキルボード", 
        "🔍 プレイヤー詳細分析", 
        "📈 分析＆バトルレポート"
    ])

    # 【タブ1】ギルド情報とメンバーランキング
    with tab1:
        st.subheader("📊 ギルド総合ステータス")
        members_data = get_guild_members(guild_id)
        total_members = len(members_data) if members_data else 0
        
        col1, col2, col3, col4 = st.columns(4)
        kill_fame = int(guild_info.get('killFame') or guild_info.get('KillFame') or 0)
        death_fame = int(guild_info.get('deathFame') or guild_info.get('DeathFame') or 0)
        kd_ratio = kill_fame / death_fame if death_fame > 0 else 0
        
        col1.metric("👥 現在のメンバー数", f"{total_members} 名")
        col2.metric("🔥 総キルフェイム", f"{kill_fame:,}")
        col3.metric("💀 総デスフェイム", f"{death_fame:,}")
        col4.metric("⚖️ ギルド総合 K/D", f"{kd_ratio:.2f}")

        st.divider()

        if members_data:
            df = pd.DataFrame(members_data)
            df = df[['Name', 'KillFame', 'DeathFame', 'FameRatio']]
            df.columns = ['プレイヤー名', 'キルフェイム', 'デスフェイム', 'K/D比']
            
            st.subheader("🏆 ギルド内MVP (現在のトップランカー)")
            mvp_col1, mvp_col2, mvp_col3 = st.columns(3)
            
            top_killers = df.sort_values(by='キルフェイム', ascending=False).head(3)
            with mvp_col1:
                st.markdown("##### ⚔️ 最多キルフェイム")
                for i, row in top_killers.iterrows():
                    st.info(f"**{row['プレイヤー名']}**\n\n{int(row['キルフェイム']):,} Fame")
            
            valid_kd = df[df['キルフェイム'] >= 1000000].sort_values(by='K/D比', ascending=False).head(3)
            with mvp_col2:
                st.markdown("##### 👑 ベスト K/D 比 (1M Fame以上)")
                if not valid_kd.empty:
                    for i, row in valid_kd.iterrows():
                        st.success(f"**{row['プレイヤー名']}**\n\nK/D: {row['K/D比']:.2f}")
                else:
                    st.write("該当者なし")
            
            top_deaths = df.sort_values(by='デスフェイム', ascending=False).head(3)
            with mvp_col3:
                st.markdown("##### 🛡️ 最多デス (前線MVP)")
                for i, row in top_deaths.iterrows():
                    st.error(f"**{row['プレイヤー名']}**\n\n{int(row['デスフェイム']):,} Fame")
            
            st.divider()
            
            st.subheader("📈 ギルド戦闘力分布（メンバーのキルフェイム層）")
            bins = [0, 1000000, 5000000, 10000000, 50000000, float('inf')]
            labels = ['100万未満 (初心者)', '100万〜500万', '500万〜1000万', '1000万〜5000万', '5000万以上 (ベテラン)']
            df['フェイム層'] = pd.cut(df['キルフェイム'], bins=bins, labels=labels, right=False)
            dist = df['フェイム層'].value_counts().reindex(labels)
            dist_df = pd.DataFrame({"人数": dist})
            st.bar_chart(dist_df)
            
            st.divider()

            st.subheader("👥 メンバー別 戦績ボード")
            df_display = df[['プレイヤー名', 'キルフェイム', 'デスフェイム', 'K/D比']].sort_values(by='キルフェイム', ascending=False)
            df_display.index = range(1, len(df_display) + 1)
            st.dataframe(df_display, use_container_width=True, height=600)

    # 【タブ2】最新のキル＆デス履歴
    with tab2:
        st.subheader("⚔️ 直近の戦闘ログ")
        selected_page = st.radio("表示するページを選択してください", [1, 2, 3, 4, 5], horizontal=True)
        current_offset = (selected_page - 1) * 20
        events_data = get_guild_events(guild_id, offset=current_offset)
        
        if events_data:
            for ev in events_data:
                killer = ev.get("Killer", {})
                victim = ev.get("Victim", {})
                time_str = ev.get("TimeStamp", "")
                utc_time, jst_time = convert_time(time_str)
                victim_fame = ev.get("TotalVictimKillFame", 0)
                
                k_name = killer.get("Name", "Unknown")
                k_guild = killer.get("GuildName", "")
                k_ip = int(killer.get("AverageItemPower", 0))
                
                v_name = victim.get("Name", "Unknown")
                v_guild = victim.get("GuildName", "")
                v_ip = int(victim.get("AverageItemPower", 0))
                
                html_images = render_equipment_html(victim.get("Equipment", {}))
                
                if k_guild.upper() == GUILD_NAME.upper():
                    st.success(f"🔥 **キル** : **{k_name}** (IP: {k_ip}) ⚔️ 倒した相手 ➡ **{v_name}** [{v_guild}] (IP: {v_ip})")
                    st.caption(f"🕒 **日本時間:** {jst_time} (UTC: {utc_time}) ｜ 🌟 **取得名声(Fame):** {victim_fame:,}")
                    if html_images:
                        st.markdown(f"**🎁 相手の装備（ドロップ候補）:**<br>{html_images}", unsafe_allow_html=True)
                else:
                    st.error(f"💀 **デス** : **{v_name}** (IP: {v_ip}) ⚔️ 倒された相手 ➡ **{k_name}** [{k_guild}] (IP: {k_ip})")
                    st.caption(f"🕒 **日本時間:** {jst_time} (UTC: {utc_time}) ｜ 🌟 **相手の取得名声:** {victim_fame:,}")
                    if html_images:
                        st.markdown(f"**💥 ロストした装備:**<br>{html_images}", unsafe_allow_html=True)
                st.write("---")
        else:
            st.info("このページの戦闘データは見つかりませんでした。")

    # 【タブ3】個人メンバー詳細分析
    with tab3:
        st.subheader("🔍 プレイヤー詳細分析")
        search_name = st.text_input("プレイヤー名を入力（例: sonikuma）")
        if st.button("検索する", type="primary"):
            if search_name:
                with st.spinner(f"「{search_name}」のデータを解析中..."):
                    player_result = search_player(search_name)
                    
                    if player_result:
                        player_data = player_result["info"]
                        player_id = player_result["id"]
                        
                        st.success(f"✅ {player_data['Name']} のデータが見つかりました！")
                        st.write(f"🛡️ **現在の所属ギルド:** {player_data.get('GuildName', '無所属')}")
                        
                        p_col1, p_col2, p_col3 = st.columns(3)
                        p_k_fame = int(player_data.get('KillFame') or player_data.get('killFame') or 0)
                        p_d_fame = int(player_data.get('DeathFame') or player_data.get('deathFame') or 0)
                        p_kd_ratio = p_k_fame / p_d_fame if p_d_fame > 0 else 0
                        
                        p_col1.metric("🔥 キルフェイム", f"{p_k_fame:,}")
                        p_col2.metric("💀 デスフェイム", f"{p_d_fame:,}")
                        p_col3.metric("⚖️ K/D 比", f"{p_kd_ratio:.2f}")
                        
                        stats = player_data.get('LifetimeStatistics', {})
                        pve_fame = int(stats.get('PvE', {}).get('Total', 0))
                        crafting_fame = int(stats.get('Crafting', {}).get('Total', 0))
                        gathering_fame = int(stats.get('Gathering', {}).get('All', {}).get('Total', 0))
                        
                        st.markdown(f"**[ 📊 生涯フェイム ]**\n* ⚔️ PvE (Mob討伐): **{pve_fame:,}** ｜ 🔨 製作: **{crafting_fame:,}** ｜ 🪓 採集: **{gathering_fame:,}**")
                        
                        st.divider()
                        st.subheader("🔥 直近のキル (最新3件)")
                        recent_kills = get_player_recent_history(player_id, event_type="kills", limit=3)
                        if recent_kills:
                            for kill in recent_kills:
                                k_equip_html = render_equipment_html(kill.get("Killer", {}).get("Equipment", {}))
                                v_equip_html = render_equipment_html(kill.get("Victim", {}).get("Equipment", {}))
                                utc_time, jst_time = convert_time(kill.get("TimeStamp", ""))
                                v_name = kill.get("Victim", {}).get("Name", "Unknown")
                                v_guild = kill.get("Victim", {}).get("GuildName", "無所属")
                                v_fame = kill.get("TotalVictimKillFame", 0)
                                
                                st.info(f"⚔️ 倒した相手: **{v_name}** [{v_guild}] ｜ 🕒 **{jst_time}**")
                                st.markdown(f"**自分の装備:**<br>{k_equip_html}", unsafe_allow_html=True)
                                st.markdown(f"**相手の装備 (取得名声: {v_fame:,}):**<br>{v_equip_html}", unsafe_allow_html=True)
                                st.write("")
                        else:
                            st.write("キル履歴がありません。")

                        st.divider()
                        st.subheader("💀 直近のデス (最新3件)")
                        recent_deaths = get_player_recent_history(player_id, event_type="deaths", limit=3)
                        if recent_deaths:
                            for death in recent_deaths:
                                k_equip_html = render_equipment_html(death.get("Killer", {}).get("Equipment", {}))
                                v_equip_html = render_equipment_html(death.get("Victim", {}).get("Equipment", {}))
                                utc_time, jst_time = convert_time(death.get("TimeStamp", ""))
                                k_name = death.get("Killer", {}).get("Name", "Unknown")
                                k_guild = death.get("Killer", {}).get("GuildName", "無所属")
                                v_fame = death.get("TotalVictimKillFame", 0)
                                
                                st.error(f"⚔️ 倒された相手: **{k_name}** [{k_guild}] ｜ 🕒 **{jst_time}**")
                                st.markdown(f"**相手の装備:**<br>{k_equip_html}", unsafe_allow_html=True)
                                st.markdown(f"**自分がロストした装備 (相手の取得名声: {v_fame:,}):**<br>{v_equip_html}", unsafe_allow_html=True)
                                st.write("")
                        else:
                            st.write("デス履歴がありません。")
                    else:
                        st.error("プレイヤーが見つかりませんでした。")

    # 【タブ4】📈 ギルド分析 ＆ バトルレポート (★超絶アップデート★)
    with tab4:
        st.subheader("📈 ギルド行動分析 ＆ バトルレポート")
        st.write("直近100件の戦闘データを元に、ギルドの戦術傾向を分析します。")
        
        with st.spinner("データを集計中... (これには数秒かかります)"):
            analysis_events = get_analysis_events(guild_id)
        
        if analysis_events:
            # --- 1. 活動時間帯ヒートマップ ---
            st.markdown("### 🕒 最も活発な時間帯 (JST)")
            st.write("ギルド内で直近キル・デスが発生している時間帯のピークです。")
            
            hours = {f"{h}時": 0 for h in range(24)}
            for ev in analysis_events:
                _, jst_time = convert_time(ev.get("TimeStamp", ""))
                if jst_time != "Unknown":
                    # "10/27 21:30" -> "21"
                    hour_str = jst_time.split(" ")[1].split(":")[0]
                    hour_key = f"{int(hour_str)}時"
                    hours[hour_key] += 1
                    
            df_hours = pd.DataFrame({"イベント発生数": list(hours.values())}, index=list(hours.keys()))
            st.bar_chart(df_hours)
            
            st.divider()

            # --- 2. 武器メタ分析 ---
            st.markdown("### ⚔️ ギルド内 武器メタ分析 (Top 5)")
            st.write("直近の戦闘において、ギルドメンバーがキルを獲得した際に使用していた武器のランキングです。")
            
            weapon_counts = {}
            for ev in analysis_events:
                killer = ev.get("Killer", {})
                # KUMAメンバーのキルの場合のみ集計
                if killer.get("GuildName", "").upper() == GUILD_NAME.upper():
                    main_hand = killer.get("Equipment", {}).get("MainHand")
                    if main_hand:
                        w_type = main_hand.get("Type")
                        weapon_counts[w_type] = weapon_counts.get(w_type, 0) + 1
            
            if weapon_counts:
                # 使用回数順に並び替え
                sorted_weapons = sorted(weapon_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                
                cols = st.columns(len(sorted_weapons))
                for i, (w_type, count) in enumerate(sorted_weapons):
                    with cols[i]:
                        img_url = f"{RENDER_URL}/{w_type}.png?size=100"
                        st.markdown(f'<img src="{img_url}" style="background-color: #2c2c2c; border-radius: 12px; border: 2px solid #aaa;">', unsafe_allow_html=True)
                        st.metric(label=f"Rank {i+1}", value=f"{count} キル")
                        st.caption(f"`{w_type}`")
            else:
                st.write("分析に十分なキルデータがありません。")

        st.divider()

        # --- 3. 集団戦(ZvZ) バトルレポート ---
        st.markdown("### 🛡️ 集団戦(ZvZ) バトルレポート (直近5件)")
        st.write("システムが検知したギルドが関与した大規模戦闘（バトルボード）の結果です。")
        
        with st.spinner("バトルデータを取得中..."):
            battles = get_guild_battles(guild_id)
            
        if battles:
            for b in battles:
                b_id = b.get("id")
                total_kills = b.get("totalKills", 0)
                total_fame = b.get("totalFame", 0)
                _, jst_time = convert_time(b.get("startTime", ""))
                
                # 参加ギルドの抽出
                guilds_dict = b.get("guilds", {})
                guild_names = [g.get("name") for g in guilds_dict.values() if g.get("name")]
                g_str = " / ".join(guild_names[:6]) + ("..." if len(guild_names) > 6 else "")
                
                st.info(f"⚔️ **バトルID:** `{b_id}` ｜ 🕒 発生時間: **{jst_time}** ｜ 💀 **総キル数:** {total_kills} ｜ 🌟 **総フェイム:** {total_fame:,}")
                st.write(f"🚩 **激突したギルド:** {g_str}")
                st.write("") # スペース
        else:
            st.info("直近の集団戦データがありません。（小規模な戦いはZvZバトルとして記録されません）")

else:
    st.error(f"ギルド『{GUILD_NAME}』のデータが見つかりませんでした。公式APIが混雑している可能性があります。")
