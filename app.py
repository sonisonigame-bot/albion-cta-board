import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

# 画面設定
st.set_page_config(page_title="🐻KUMA Albion Dashboard", layout="wide")

# --- 🔒 パスワード認証システム ---
st.title("🐻 KUMA ギルドダッシュボード (Asiaサーバー)")
password = st.sidebar.text_input("🔑 パスワード", type="password")

if password != "sonikuma":
    st.warning("👈 このダッシュボードを閲覧するには、左側のサイドバーからパスワードを入力してロックを解除してください。")
    st.stop() # パスワードが一致するまでここで処理を停止します

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
        res = requests.get(search_url, timeout=10)
        if res.status_code == 200:
            for guild in res.json().get("guilds", []):
                if guild["Name"].upper() == guild_name.upper():
                    return guild
    except: pass
    return None

@st.cache_data(ttl=300)
def get_guild_members(guild_id):
    members_url = f"{BASE_URL}/guilds/{guild_id}/members"
    try:
        res = requests.get(members_url, timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return []

@st.cache_data(ttl=60)
def get_guild_events(guild_id, offset=0):
    events_url = f"{BASE_URL}/events?limit=20&offset={offset}&guildId={guild_id}"
    try:
        res = requests.get(events_url, timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return []

@st.cache_data(ttl=300)
def search_player(player_name):
    search_url = f"{BASE_URL}/search?q={player_name}"
    try:
        res = requests.get(search_url, timeout=10)
        if res.status_code == 200:
            for p in res.json().get("players", []):
                if p["Name"].upper() == player_name.upper():
                    detail_res = requests.get(f"{BASE_URL}/players/{p['Id']}", timeout=10)
                    if detail_res.status_code == 200:
                        return {"info": detail_res.json(), "id": p['Id']}
    except: pass
    return None

@st.cache_data(ttl=300)
def get_player_recent_history(player_id, event_type="kills", limit=3):
    url = f"{BASE_URL}/players/{player_id}/{event_type}?limit={limit}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200: return res.json()[:limit]
    except: pass
    return []

@st.cache_data(ttl=300)
def get_analysis_events(guild_id):
    events = []
    for offset in [0, 50]:
        try:
            res = requests.get(f"{BASE_URL}/events?limit=50&offset={offset}&guildId={guild_id}", timeout=10)
            if res.status_code == 200: events.extend(res.json())
        except: pass
    return events

@st.cache_data(ttl=300)
def get_battle_details(battle_id):
    try:
        res = requests.get(f"{BASE_URL}/battles/{battle_id}", timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return None

# ★ 修正ポイント：KUMAが「3人以上」いる集団戦バトルを抽出するように変更
@st.cache_data(ttl=300)
def get_group_battles(guild_id, guild_name, min_players=3):
    url = f"{BASE_URL}/battles?limit=20&offset=0&guildId={guild_id}"
    valid_battles = []
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            battles_list = res.json()
            for b in battles_list:
                b_id = b.get("id")
                b_detail = get_battle_details(b_id)
                if b_detail:
                    players = b_detail.get("players", {}).values()
                    kuma_count = sum(1 for p in players if p.get("guildName", "").upper() == guild_name.upper())
                    if kuma_count >= min_players:
                        valid_battles.append({"summary": b, "detail": b_detail, "kuma_count": kuma_count})
    except: pass
    return valid_battles

# --- 3. データの取得 ---
with st.spinner("Albion公式サーバーからデータを取得中..."):
    guild_info = get_guild_info(GUILD_NAME)

if guild_info:
    guild_id = guild_info["Id"]
    
    # --- 4. 画面表示 ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 総合ステータス＆分析", 
        "⚔️ 最近のキルボード", 
        "🔍 プレイヤー詳細分析", 
        "🛡️ 集団戦 バトルレポート"
    ])

    # 【タブ1】総合ステータス
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
            
            top_deaths = df.sort_values(by='デスフェイム', ascending=False).head(3)
            with mvp_col3:
                st.markdown("##### 🛡️ 最多デス (前線MVP)")
                for i, row in top_deaths.iterrows():
                    st.error(f"**{row['プレイヤー名']}**\n\n{int(row['デスフェイム']):,} Fame")
            
            st.divider()
            
            st.subheader("📈 ギルド行動分析 ＆ メタ分析")
            with st.spinner("行動データを集計中..."):
                analysis_events = get_analysis_events(guild_id)
            
            if analysis_events:
                ana_col1, ana_col2 = st.columns(2)
                with ana_col1:
                    st.markdown("##### 🕒 最も活発な時間帯 (JST)")
                    hours = {f"{h}時": 0 for h in range(24)}
                    for ev in analysis_events:
                        _, jst_time = convert_time(ev.get("TimeStamp", ""))
                        if jst_time != "Unknown":
                            hour_str = jst_time.split(" ")[1].split(":")[0]
                            hours[f"{int(hour_str)}時"] += 1
                    st.bar_chart(pd.DataFrame({"イベント数": list(hours.values())}, index=list(hours.keys())))
                
                with ana_col2:
                    st.markdown("##### ⚔️ ギルド内 武器メタ (Top 5)")
                    weapon_counts = {}
                    for ev in analysis_events:
                        killer = ev.get("Killer", {})
                        if killer.get("GuildName", "").upper() == GUILD_NAME.upper():
                            main_hand = killer.get("Equipment", {}).get("MainHand")
                            if main_hand:
                                w_type = main_hand.get("Type")
                                weapon_counts[w_type] = weapon_counts.get(w_type, 0) + 1
                    
                    if weapon_counts:
                        sorted_weapons = sorted(weapon_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                        for w_type, count in sorted_weapons:
                            img_url = f"{RENDER_URL}/{w_type}.png?size=50"
                            st.markdown(f'<img src="{img_url}" width="40" style="background-color: #2c2c2c; border-radius: 8px; vertical-align: middle; margin-right: 10px;"> **{w_type}** : {count} キル', unsafe_allow_html=True)
            
            st.divider()
            st.subheader("👥 メンバー別 戦績ボード")
            df_display = df[['プレイヤー名', 'キルフェイム', 'デスフェイム', 'K/D比']].sort_values(by='キルフェイム', ascending=False)
            df_display.index = range(1, len(df_display) + 1)
            st.dataframe(df_display, use_container_width=True, height=600)

    # 【タブ2】最新のキルボード
    with tab2:
        st.subheader("⚔️ 直近の戦闘ログ")
        selected_page = st.radio("表示するページを選択してください", [1, 2, 3, 4, 5], horizontal=True)
        events_data = get_guild_events(guild_id, offset=(selected_page - 1) * 20)
        
        if events_data:
            for ev in events_data:
                killer, victim = ev.get("Killer", {}), ev.get("Victim", {})
                _, jst_time = convert_time(ev.get("TimeStamp", ""))
                v_fame = ev.get("TotalVictimKillFame", 0)
                html_images = render_equipment_html(victim.get("Equipment", {}))
                
                k_name, k_guild, k_ip = killer.get("Name", "Unknown"), killer.get("GuildName", ""), int(killer.get("AverageItemPower", 0))
                v_name, v_guild, v_ip = victim.get("Name", "Unknown"), victim.get("GuildName", ""), int(victim.get("AverageItemPower", 0))
                
                if k_guild.upper() == GUILD_NAME.upper():
                    st.success(f"🔥 **キル** : **{k_name}** (IP: {k_ip}) ⚔️ 倒した相手 ➡ **{v_name}** [{v_guild}] (IP: {v_ip})")
                    st.caption(f"🕒 **日本時間:** {jst_time} ｜ 🌟 **取得名声:** {v_fame:,}")
                    if html_images: st.markdown(f"**🎁 相手の装備:**<br>{html_images}", unsafe_allow_html=True)
                else:
                    st.error(f"💀 **デス** : **{v_name}** (IP: {v_ip}) ⚔️ 倒された相手 ➡ **{k_name}** [{k_guild}] (IP: {k_ip})")
                    st.caption(f"🕒 **日本時間:** {jst_time} ｜ 🌟 **相手の取得名声:** {v_fame:,}")
                    if html_images: st.markdown(f"**💥 ロストした装備:**<br>{html_images}", unsafe_allow_html=True)
                st.write("---")

    # 【タブ3】プレイヤー詳細分析
    with tab3:
        st.subheader("🔍 プレイヤー詳細分析")
        search_name = st.text_input("プレイヤー名を入力（例: sonikuma）")
        if st.button("検索する", type="primary"):
            if search_name:
                with st.spinner("解析中..."):
                    player_result = search_player(search_name)
                    if player_result:
                        p_data, p_id = player_result["info"], player_result["id"]
                        st.success(f"✅ {p_data['Name']} (所属: {p_data.get('GuildName', '無所属')})")
                        
                        k_fame = int(p_data.get('KillFame') or p_data.get('killFame') or 0)
                        d_fame = int(p_data.get('DeathFame') or p_data.get('deathFame') or 0)
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("🔥 キルフェイム", f"{k_fame:,}")
                        c2.metric("💀 デスフェイム", f"{d_fame:,}")
                        c3.metric("⚖️ K/D 比", f"{k_fame / d_fame if d_fame > 0 else 0:.2f}")
                        
                        st.divider()
                        
                        st.subheader("🔥 直近のキル (最新3件)")
                        for kill in get_player_recent_history(p_id, "kills", 3):
                            k_eq = render_equipment_html(kill.get("Killer", {}).get("Equipment", {}))
                            v_eq = render_equipment_html(kill.get("Victim", {}).get("Equipment", {}))
                            _, jst_time = convert_time(kill.get("TimeStamp", ""))
                            st.info(f"⚔️ 倒した相手: **{kill.get('Victim', {}).get('Name', 'Unknown')}** ｜ 🕒 **{jst_time}**")
                            st.markdown(f"**自分の装備:**<br>{k_eq}", unsafe_allow_html=True)
                            st.markdown(f"**相手の装備 (名声: {kill.get('TotalVictimKillFame', 0):,}):**<br>{v_eq}", unsafe_allow_html=True)
                            st.write("")
                            
                        st.subheader("💀 直近のデス (最新3件)")
                        for death in get_player_recent_history(p_id, "deaths", 3):
                            k_eq = render_equipment_html(death.get("Killer", {}).get("Equipment", {}))
                            v_eq = render_equipment_html(death.get("Victim", {}).get("Equipment", {}))
                            _, jst_time = convert_time(death.get("TimeStamp", ""))
                            st.error(f"⚔️ 倒された相手: **{death.get('Killer', {}).get('Name', 'Unknown')}** ｜ 🕒 **{jst_time}**")
                            st.markdown(f"**相手の装備:**<br>{k_eq}", unsafe_allow_html=True)
                            st.markdown(f"**ロストした装備 (相手の名声: {death.get('TotalVictimKillFame', 0):,}):**<br>{v_eq}", unsafe_allow_html=True)
                            st.write("")
                    else:
                        st.error("プレイヤーが見つかりませんでした。")

    # 【タブ4】🛡️ 集団戦 バトルレポート
    with tab4:
        st.subheader("🛡️ 最強 集団戦 バトルレポート")
        st.write("※ KUMAのメンバーが **3名以上** 参加した集団戦のみを自動抽出し、完全解析します。")
        
        with st.spinner("直近のバトルを探索・集計中... (最大20件のバトルを分析するため、数秒かかります)"):
            # ★ 参加条件を 3人 に変更
            group_battles = get_group_battles(guild_id, GUILD_NAME, min_players=3)
            
        if group_battles:
            battle_options = {}
            for zb in group_battles:
                b = zb["summary"]
                k_count = zb["kuma_count"]
                b_id = b.get("id")
                _, jst_time = convert_time(b.get("startTime", ""))
                total_kills = b.get("totalKills", 0)
                label = f"🕒 {jst_time} ｜ KUMA参加: {k_count}名 ｜ 総キル: {total_kills} (ID: {b_id})"
                battle_options[label] = zb
            
            selected_label = st.selectbox("詳細を見たい集団戦バトルを選択してください", list(battle_options.keys()))
            b_detail = battle_options[selected_label]["detail"]
            
            if b_detail:
                st.divider()
                _, jst_time = convert_time(b_detail.get("startTime", ""))
                players = list(b_detail.get("players", {}).values())
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("🕒 発生時間", jst_time)
                col2.metric("👥 総参加人数", f"{len(players)} 名")
                col3.metric("💀 総キル数", f"{b_detail.get('totalKills', 0):,}")
                col4.metric("🌟 総獲得名声", f"{b_detail.get('totalFame', 0):,}")
                
                st.markdown("#### 👑 バトルMVP (彼我全体トップ)")
                if players:
                    top_killer = max(players, key=lambda x: x.get('kills', 0))
                    top_fame = max(players, key=lambda x: x.get('killFame', 0))
                    top_healer = max(players, key=lambda x: x.get('healing', 0) if x.get('healing') else 0)
                    
                    mvp_c1, mvp_c2, mvp_c3 = st.columns(3)
                    mvp_c1.info(f"**⚔️ 最多キル:** {top_killer.get('name')} [{top_killer.get('guildName', '無所属')}]\n\n{top_killer.get('kills')} キル")
                    mvp_c2.success(f"**🌟 最高名声:** {top_fame.get('name')} [{top_fame.get('guildName', '無所属')}]\n\n{int(top_fame.get('killFame', 0)):,} Fame")
                    
                    if top_healer.get('healing', 0) > 0:
                        mvp_c3.error(f"**💚 最多ヒール:** {top_healer.get('name')} [{top_healer.get('guildName', '無所属')}]\n\n{int(top_healer.get('healing', 0)):,} Heal")
                    else:
                        mvp_c3.error("**💚 最多ヒール:** データなし (または0)")
                        
                st.divider()

                st.markdown("#### 🚩 ギルド別 戦果比較レポート")
                
                guild_stats = {}
                for p in players:
                    g_name = p.get("guildName", "無所属")
                    if not g_name: g_name = "無所属"
                    
                    if g_name not in guild_stats:
                        guild_stats[g_name] = {
                            "alliance": p.get("allianceName", ""),
                            "player_count": 0,
                            "total_ip": 0.0,
                            "kills": 0,
                            "deaths": 0,
                            "kill_fame": 0,
                            "players_list": [],
                            "top_killer": {"name": "", "kills": -1},
                            "top_healer": {"name": "", "healing": -1},
                            "top_fame": {"name": "", "fame": -1}
                        }
                    
                    gs = guild_stats[g_name]
                    gs["player_count"] += 1
                    gs["total_ip"] += p.get("averageItemPower", 0)
                    gs["kills"] += p.get("kills", 0)
                    gs["deaths"] += p.get("deaths", 0)
                    gs["kill_fame"] += p.get("killFame", 0)
                    gs["players_list"].append(p.get("name"))
                    
                    if p.get("kills", 0) > gs["top_killer"]["kills"]:
                        gs["top_killer"] = {"name": p.get("name"), "kills": p.get("kills", 0)}
                    if p.get("healing", 0) > gs["top_healer"]["healing"]:
                        gs["top_healer"] = {"name": p.get("name"), "healing": p.get("healing", 0)}
                    if p.get("killFame", 0) > gs["top_fame"]["fame"]:
                        gs["top_fame"] = {"name": p.get("name"), "fame": p.get("killFame", 0)}

                data_rows = []
                for g_name, gs in guild_stats.items():
                    avg_ip = gs["total_ip"] / gs["player_count"] if gs["player_count"] > 0 else 0
                    t_kill = f"{gs['top_killer']['name']} ({gs['top_killer']['kills']})" if gs['top_killer']['kills'] > 0 else "-"
                    t_heal = f"{gs['top_healer']['name']} ({int(gs['top_healer']['healing']):,})" if gs['top_healer']['healing'] > 0 else "-"
                    t_fame = f"{gs['top_fame']['name']} ({int(gs['top_fame']['fame']):,})" if gs['top_fame']['fame'] > 0 else "-"
                    
                    data_rows.append({
                        "ギルド": g_name,
                        "同盟": gs['alliance'],
                        "参加人数": gs['player_count'],
                        "平均IP": int(avg_ip),
                        "キル": gs['kills'],
                        "デス": gs['deaths'],
                        "K/D": f"{(gs['kills'] / gs['deaths']):.2f}" if gs['deaths'] > 0 else f"{gs['kills']}.00",
                        "獲得名声": gs['kill_fame'],
                        "Top Kill": t_kill,
                        "Top Heal": t_heal,
                        "Top Fame": t_fame
                    })
                
                df_guilds = pd.DataFrame(data_rows)
                df_guilds = df_guilds.sort_values(by="参加人数", ascending=False)
                df_guilds.index = range(1, len(df_guilds) + 1)
                
                def highlight_kuma(row):
                    if row['ギルド'].upper() == GUILD_NAME.upper():
                        return ['background-color: rgba(255, 215, 0, 0.2)'] * len(row)
                    return [''] * len(row)
                
                st.dataframe(df_guilds.style.apply(highlight_kuma, axis=1), use_container_width=True)
                
                with st.expander("👥 参加プレイヤー完全名簿 (ギルド別)"):
                    st.write("各ギルドの参加者一覧です。")
                    for g_name, gs in sorted(guild_stats.items(), key=lambda x: x[1]['player_count'], reverse=True):
                        st.markdown(f"**【 {g_name} 】** ({gs['player_count']}名)\n> {', '.join(sorted(gs['players_list']))}")
                        
        else:
            st.info("直近20件のバトル内に、KUMAメンバーが3人以上参加している集団戦は見つかりませんでした。")

else:
    st.error(f"ギルド『{GUILD_NAME}』のデータが見つかりませんでした。公式APIが混雑している可能性があります。")
