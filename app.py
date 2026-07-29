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
    st.stop()

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

def categorize_weapon(w_type):
    if not w_type: return "不明"
    w = str(w_type).upper()
    if any(x in w for x in ['_MACE', '_HAMMER', '_SHIELD']): return "🛡️ タンク"
    if any(x in w for x in ['_HOLYSTAFF', '_NATURESTAFF']): return "💚 ヒーラー"
    if any(x in w for x in ['_ARCANE', '_ENIGMATIC', '_LOCUS', '_CURSED']): return "🌀 サポート/デバフ"
    if any(x in w for x in ['_BOW', '_CROSSBOW', '_FIRESTAFF', '_FROSTSTAFF']): return "🏹 火力(遠距離)"
    if any(x in w for x in ['_SWORD', '_AXE', '_DAGGER', '_SPEAR', '_QUARTERSTAFF', '_KNUCKLES']): return "⚔️ 火力(近接)"
    return "⚪ その他"

@st.cache_data(ttl=300)
def get_guild_info(guild_name):
    try:
        res = requests.get(f"{BASE_URL}/search?q={guild_name}", timeout=10)
        if res.status_code == 200:
            for guild in res.json().get("guilds", []):
                if guild["Name"].upper() == guild_name.upper():
                    detail_res = requests.get(f"{BASE_URL}/guilds/{guild['Id']}", timeout=10)
                    if detail_res.status_code == 200:
                        return detail_res.json()
                    return guild
    except: pass
    return None

@st.cache_data(ttl=300)
def get_guild_members(guild_id):
    try:
        res = requests.get(f"{BASE_URL}/guilds/{guild_id}/members", timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return []

@st.cache_data(ttl=60)
def get_guild_events(guild_id, offset=0):
    try:
        res = requests.get(f"{BASE_URL}/events?limit=20&offset={offset}&guildId={guild_id}", timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return []

@st.cache_data(ttl=300)
def get_analysis_events(guild_id):
    events = []
    for offset in [0, 50, 100]:
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

@st.cache_data(ttl=300)
def get_group_battles(guild_id, guild_name, min_players=3):
    url = f"{BASE_URL}/battles?limit=50&offset=0&guildId={guild_id}"
    valid_battles = []
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            for b in res.json():
                b_id = b.get("id")
                b_detail = get_battle_details(b_id)
                if b_detail:
                    players = b_detail.get("players", {}).values()
                    kuma_count = sum(1 for p in players if p.get("guildName", "").upper() == guild_name.upper())
                    if kuma_count >= min_players:
                        valid_battles.append({"summary": b, "detail": b_detail, "kuma_count": kuma_count})
    except: pass
    return valid_battles

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

    # 【タブ1】総合ステータス ＆ 分析
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
            
        st.subheader("📈 ギルド行動 ＆ メタ分析")
        with st.spinner("行動データを集計中..."):
            analysis_events = get_analysis_events(guild_id)
        
        if analysis_events:
            st.markdown("##### 🕒 最も活発な時間帯 (JST)")
            hour_labels = [f"{h}時" for h in range(1, 24)] + ["24時"]
            hours = {label: 0 for label in hour_labels}
            
            for ev in analysis_events:
                _, jst_time = convert_time(ev.get("TimeStamp", ""))
                if jst_time != "Unknown":
                    hour_str = jst_time.split(" ")[1].split(":")[0]
                    h_int = int(hour_str)
                    label = "24時" if h_int == 0 else f"{h_int}時"
                    hours[label] += 1
            
            st.bar_chart(pd.DataFrame({"キル/デス発生数": list(hours.values())}, index=list(hours.keys())))
            
            st.divider()

            st.markdown("##### ⚔️ ギルド内 ロール別・武器メタTop5")
            role_weapons = {"🛡️ タンク": {}, "⚔️ 火力(近接)": {}, "🏹 火力(遠距離)": {}, "💚 ヒーラー": {}, "🌀 サポート/デバフ": {}}
            
            for ev in analysis_events:
                killer = ev.get("Killer", {})
                if killer.get("GuildName", "").upper() == GUILD_NAME.upper():
                    main_hand = killer.get("Equipment", {}).get("MainHand")
                    if main_hand:
                        w_type = main_hand.get("Type")
                        role = categorize_weapon(w_type)
                        if role in role_weapons:
                            role_weapons[role][w_type] = role_weapons[role].get(w_type, 0) + 1
            
            cols = st.columns(5)
            for idx, (role, weapons) in enumerate(role_weapons.items()):
                with cols[idx]:
                    st.markdown(f"**{role}**")
                    if weapons:
                        sorted_w = sorted(weapons.items(), key=lambda x: x[1], reverse=True)[:5]
                        for w_type, count in sorted_w:
                            img_url = f"{RENDER_URL}/{w_type}.png?size=40"
                            st.markdown(f'<img src="{img_url}" style="background-color: #2c2c2c; border-radius: 6px; vertical-align: middle; margin-right: 5px;"> `{count}回`', unsafe_allow_html=True)
                    else:
                        st.caption("データなし")
        
        st.divider()
        st.subheader("👥 メンバー別 戦績ボード")
        if members_data:
            df = pd.DataFrame(members_data)
            df = df[['Name', 'KillFame', 'DeathFame', 'FameRatio']]
            df.columns = ['プレイヤー名', 'キルフェイム', 'デスフェイム', 'K/D比']
            df = df.sort_values(by='キルフェイム', ascending=False)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, height=600)

    # 【タブ2】最新のキルボード (★絞り込み機能追加★)
    with tab2:
        st.subheader("⚔️ 直近の戦闘ログ")
        
        search_filter = st.text_input("🔍 プレイヤー名でログを絞り込む（空欄で全件表示）", "")
        
        display_events = []
        if search_filter:
            st.caption("※直近150件のログから抽出しています。")
            with st.spinner("検索中..."):
                all_events = get_analysis_events(guild_id)
                for ev in all_events:
                    k_name = ev.get("Killer", {}).get("Name", "")
                    v_name = ev.get("Victim", {}).get("Name", "")
                    if search_filter.upper() in k_name.upper() or search_filter.upper() in v_name.upper():
                        display_events.append(ev)
                display_events = display_events[:50] # 最大50件表示
        else:
            selected_page = st.radio("表示するページを選択してください", [1, 2, 3, 4, 5], horizontal=True)
            display_events = get_guild_events(guild_id, offset=(selected_page - 1) * 20)
        
        if display_events:
            for ev in display_events:
                killer, victim = ev.get("Killer", {}), ev.get("Victim", {})
                _, jst_time = convert_time(ev.get("TimeStamp", ""))
                v_fame = ev.get("TotalVictimKillFame", 0)
                html_images = render_equipment_html(victim.get("Equipment", {}))
                
                k_name, k_guild, k_ip = killer.get("Name", "Unknown"), killer.get("GuildName", ""), int(killer.get("AverageItemPower", 0))
                v_name, v_guild, v_ip = victim.get("Name", "Unknown"), victim.get("GuildName", ""), int(victim.get("AverageItemPower", 0))
                
                if k_guild.upper() == GUILD_NAME.upper():
                    st.success(f"🔥 **キル** : **{k_name}** (IP: {k_ip}) ⚔️ 倒した相手 ➡ **{v_name}** [{v_guild}] (IP: {v_ip})")
                    st.caption(f"🕒 {jst_time} ｜ 🌟 取得名声: {v_fame:,}")
                    if html_images: st.markdown(f"**🎁 相手の装備:**<br>{html_images}", unsafe_allow_html=True)
                else:
                    st.error(f"💀 **デス** : **{v_name}** (IP: {v_ip}) ⚔️ 倒された相手 ➡ **{k_name}** [{k_guild}] (IP: {k_ip})")
                    st.caption(f"🕒 {jst_time} ｜ 🌟 相手の取得名声: {v_fame:,}")
                    if html_images: st.markdown(f"**💥 ロストした装備:**<br>{html_images}", unsafe_allow_html=True)
                st.write("---")
        else:
            if search_filter:
                st.info("条件に一致するログは見つかりませんでした。")
            else:
                st.info("データが見つかりませんでした。")

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

    # 【タブ4】🛡️ 集団戦 バトルレポート (★名声カンマ対応★)
    with tab4:
        st.subheader("🛡️ 集団戦 バトルレポート")
        st.write("※ KUMAが **3名以上** 参加した集団戦を抽出しています。")
        
        with st.spinner("直近のバトルを探索中... (最大50件のバトルを分析します)"):
            group_battles = get_group_battles(guild_id, GUILD_NAME, min_players=3)
            
        if group_battles:
            group_battles = sorted(group_battles, key=lambda x: x["summary"].get("startTime", ""), reverse=True)
            
            battle_options = {}
            for zb in group_battles:
                b = zb["summary"]
                b_id = b.get("id")
                _, jst_time = convert_time(b.get("startTime", ""))
                label = f"🕒 {jst_time} ｜ KUMA参加: {zb['kuma_count']}名 ｜ 総キル: {b.get('totalKills', 0)} (ID: {b_id})"
                battle_options[label] = zb
            
            selected_label = st.selectbox("詳細を見たいバトルを選択してください (最新順)", list(battle_options.keys()))
            b_detail = battle_options[selected_label]["detail"]
            
            if b_detail:
                st.divider()
                _, jst_time = convert_time(b_detail.get("startTime", ""))
                players = list(b_detail.get("players", {}).values())
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("🕒 発生時間", jst_time)
                c2.metric("👥 総参加人数", f"{len(players)} 名")
                c3.metric("💀 総キル数", f"{b_detail.get('totalKills', 0):,}")
                c4.metric("🌟 総獲得名声", f"{b_detail.get('totalFame', 0):,}")
                
                st.divider()
                st.markdown("#### 🚩 ギルド別 戦果比較")
                
                guild_stats = {}
                for p in players:
                    g_name = p.get("guildName", "無所属")
                    if not g_name: g_name = "無所属"
                    
                    if g_name not in guild_stats:
                        guild_stats[g_name] = {"count": 0, "kills": 0, "deaths": 0, "fame": 0}
                    
                    gs = guild_stats[g_name]
                    gs["count"] += 1
                    gs["kills"] += p.get("kills", 0)
                    gs["deaths"] += p.get("deaths", 0)
                    gs["fame"] += p.get("killFame", 0)

                g_rows = []
                for g, gs in guild_stats.items():
                    g_rows.append({
                        "ギルド": g, "人数": gs['count'], "キル": gs['kills'], "デス": gs['deaths'], 
                        "K/D": f"{(gs['kills'] / gs['deaths']):.2f}" if gs['deaths'] > 0 else f"{gs['kills']}.00",
                        # ★ 名声をカンマ区切りにフォーマット
                        "名声": f"{gs['fame']:,}"
                    })
                
                df_guilds = pd.DataFrame(g_rows).sort_values(by="人数", ascending=False)
                df_guilds.index = range(1, len(df_guilds) + 1)
                
                def highlight_kuma(row):
                    return ['background-color: rgba(255, 215, 0, 0.2)'] * len(row) if row['ギルド'].upper() == GUILD_NAME.upper() else [''] * len(row)
                
                st.dataframe(df_guilds.style.apply(highlight_kuma, axis=1), use_container_width=True)
                
                st.divider()
                
                st.markdown("#### 👥 ギルド別 参加メンバー詳細")
                
                guild_list = list(guild_stats.keys())
                default_idx = 0
                for i, g in enumerate(guild_list):
                    if g.upper() == GUILD_NAME.upper():
                        default_idx = i
                        break
                
                selected_guild = st.selectbox("分析したいギルドを選択してください", guild_list, index=default_idx)
                
                target_players = []
                
                for p in players:
                    g_name = p.get("guildName", "無所属")
                    if not g_name: g_name = "無所属"
                    
                    if g_name == selected_guild:
                        target_players.append({
                            "プレイヤー名": p.get("name"),
                            "キル": p.get("kills", 0),
                            "デス": p.get("deaths", 0),
                            # ★ 個人のキル名声もカンマ区切りにフォーマット
                            "キル名声": f"{p.get('killFame', 0):,}"
                        })
                
                if target_players:
                    st.markdown(f"##### 👥 【 {selected_guild} 】 の参加メンバー詳細")
                    df_tp = pd.DataFrame(target_players).sort_values(by="キル", ascending=False)
                    df_tp.index = range(1, len(df_tp) + 1)
                    st.dataframe(df_tp, use_container_width=True)
                else:
                    st.write("詳細データが見つかりませんでした。")
                        
        else:
            st.info("直近50件のバトル内に、KUMAが3人以上参加している集団戦は見つかりませんでした。(反映待ちの可能性があります)")

else:
    st.error("ギルドデータが見つかりませんでした。公式APIが混雑している可能性があります。")
