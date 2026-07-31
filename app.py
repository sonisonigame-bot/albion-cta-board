import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
import plotly.express as px

# 画面設定
st.set_page_config(page_title="🐻KUMA Albion Dashboard", layout="wide")

# --- 🔒 パスワード認証システム ＆ サイドバー ---
st.sidebar.title("🐻 KUMA ダッシュボード")
password = st.sidebar.text_input("🔑 パスワード", type="password")

if password != "sonikuma":
    st.warning("👈 このダッシュボードを閲覧するには、左側のサイドバーからパスワードを入力してロックを解除してください。")
    st.stop()

# --- ⏱️ Albion ライブ時計ウィジェット (HTML/JS) ---
with st.sidebar:
    st.divider()
    components.html("""
    <div style="font-family: sans-serif; padding: 15px; background: #262730; color: white; border-radius: 10px; text-align: center; border: 1px solid #444;">
        <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 8px;">⏱️ サーバー時間</div>
        <div style="font-size: 1.6em; color: #ffbd45; font-weight: bold; letter-spacing: 2px;" id="utc-time">--:--:--</div>
        <div style="font-size: 0.9em; color: #ccc; margin-top: 5px;" id="jst-time">日本時間: --:--:--</div>
    </div>
    <script>
        function updateTime() {
            const now = new Date();
            const utc = now.toISOString().substring(11, 19);
            document.getElementById("utc-time").innerText = "UTC " + utc;
            const jstTime = new Date(now.getTime() + 9 * 60 * 60 * 1000);
            const jst = jstTime.toISOString().substring(11, 19);
            document.getElementById("jst-time").innerText = "JST " + jst;
        }
        setInterval(updateTime, 1000);
        updateTime();
    </script>
    """, height=120)

# メイン画面ヘッダー
st.title("🐻 KUMA ギルドダッシュボード (Asiaサーバー)")
st.write("Albion Onlineの公式データから自動取得しています。")

# --- 1. API設定 ---
BASE_URL = "https://gameinfo-sgp.albiononline.com/api/gameinfo"
RENDER_URL = "https://render.albiononline.com/v1/item"
MARKET_API_URL = "https://east.albion-online-data.com/api/v2/stats/prices"
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
    slots = ['Bag', 'Head', 'Cape', 'MainHand', 'Armor', 'OffHand', 'Potion', 'Shoes', 'Food', 'Mount']
    html_images = "<div style='display: flex; flex-wrap: wrap; gap: 4px; max-width: 200px;'>"
    for slot in slots:
        item = equipment_dict.get(slot)
        if item:
            item_name = item.get('Type')
            count = item.get('Count', 1)
            img_url = f"{RENDER_URL}/{item_name}.png?size=60"
            count_html = f"<div style='position:absolute; bottom:0; right:4px; font-size:12px; font-weight:bold; color:white; text-shadow: 1px 1px 2px black;'>{count}</div>" if count > 1 else ""
            html_images += f"<div style='position:relative;'><img src='{img_url}' width='45' title='{item_name}' style='background-color: #2c2c2c; border-radius: 5px; border: 1px solid #555;'>{count_html}</div>"
        else:
            html_images += f"<div style='width: 45px; height: 45px; background-color: #1a1a1a; border-radius: 5px; border: 1px solid #333;'></div>"
    html_images += "</div>"
    return html_images

def render_inventory_html(inventory_list):
    if not inventory_list: return ""
    html_images = "<div style='display: flex; flex-wrap: wrap; gap: 4px;'>"
    has_items = False
    for item in inventory_list:
        if item:
            has_items = True
            item_name = item.get('Type')
            count = item.get('Count', 1)
            img_url = f"{RENDER_URL}/{item_name}.png?size=50"
            count_html = f"<div style='position:absolute; bottom:0; right:4px; font-size:11px; font-weight:bold; color:white; text-shadow: 1px 1px 2px black;'>{count}</div>" if count > 1 else ""
            html_images += f"<div style='position:relative;'><img src='{img_url}' width='40' title='{item_name}' style='background-color: #2c2c2c; border-radius: 4px; border: 1px solid #555;'>{count_html}</div>"
    html_images += "</div>"
    return html_images if has_items else ""

def render_participants(participants_list):
    if not participants_list or len(participants_list) <= 1:
        return "⚔️ **Solo Kill** (1対1の戦い)"
    parts = []
    for p in participants_list:
        name = p.get("Name")
        dmg = int(p.get("DamageDone", 0))
        heal = int(p.get("SupportHealingDone", 0))
        info = f"**{name}**"
        if dmg > 0: info += f" (⚔️{dmg})"
        if heal > 0: info += f" (💚{heal})"
        parts.append({"name": name, "dmg": dmg, "heal": heal, "info": info})
    parts = sorted(parts, key=lambda x: x["dmg"], reverse=True)
    parts_str = ", ".join([p["info"] for p in parts])
    return f"👥 **アシスト ({len(participants_list)}名):** {parts_str}"

def categorize_weapon(w_type):
    if not w_type: return "⚪ その他"
    w = str(w_type).upper()
    if any(x in w for x in ['_MACE', '_HAMMER', '_SHIELD']): return "🛡️ タンク"
    if any(x in w for x in ['_HOLYSTAFF', '_NATURESTAFF']): return "💚 ヒーラー"
    if any(x in w for x in ['_ARCANE', '_ENIGMATIC', '_LOCUS', '_CURSED']): return "🌀 サポート/デバフ"
    if any(x in w for x in ['_BOW', '_CROSSBOW', '_FIRESTAFF', '_FROSTSTAFF']): return "🏹 火力(遠距離)"
    if any(x in w for x in ['_SWORD', '_AXE', '_DAGGER', '_SPEAR', '_QUARTERSTAFF', '_KNUCKLES']): return "⚔️ 火力(近接)"
    return "⚪ その他"

@st.cache_data(ttl=3600)
def get_market_prices(item_ids):
    if not item_ids: return {}
    prices = {}
    item_ids = list(set(item_ids))
    chunk_size = 100 
    for i in range(0, len(item_ids), chunk_size):
        chunk = item_ids[i:i+chunk_size]
        ids_str = ",".join(chunk)
        url = f"{MARKET_API_URL}/{ids_str}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                for d in res.json():
                    iid = d.get("item_id")
                    p = d.get("sell_price_min", 0)
                    if p > 0: 
                        if iid not in prices or prices[iid] == 0:
                            prices[iid] = p
                        else:
                            if p < prices[iid]: prices[iid] = p
        except: pass
    return prices

def calculate_loot_value(victim, price_dict):
    total = 0
    for slot, item in victim.get("Equipment", {}).items():
        if item:
            iid = item.get("Type")
            count = item.get("Count", 1)
            total += price_dict.get(iid, 0) * count
    for item in victim.get("Inventory", []):
        if item:
            iid = item.get("Type")
            count = item.get("Count", 1)
            total += price_dict.get(iid, 0) * count
    return total

# ★ 修正: key_prefix を追加して、円グラフ描画時の重複エラーを回避
def render_battle_summary(events, market_prices, key_prefix="default"):
    kuma_kills, kuma_deaths = 0, 0
    gained_fame, lost_fame, gained_silver, lost_silver = 0, 0, 0, 0
    
    enemy_stats, enemy_alliance_stats, kuma_stats = {}, {}, {}
    weapon_stats, enemy_victim_stats = {}, {}
    kuma_player_roles = {}
    
    for ev in events:
        killer, victim = ev.get("Killer", {}), ev.get("Victim", {})
        fame = ev.get("TotalVictimKillFame", 0)
        loot_value = calculate_loot_value(victim, market_prices)
        
        k_guild_raw = killer.get("GuildName", "")
        v_guild_raw = victim.get("GuildName", "")
        
        if k_guild_raw.upper() == GUILD_NAME.upper():
            k_name = killer.get("Name", "Unknown")
            w_type = killer.get("Equipment", {}).get("MainHand", {}).get("Type")
            if w_type: kuma_player_roles[k_name] = categorize_weapon(w_type)
        if v_guild_raw.upper() == GUILD_NAME.upper():
            v_name = victim.get("Name", "Unknown")
            w_type = victim.get("Equipment", {}).get("MainHand", {}).get("Type")
            if w_type: kuma_player_roles[v_name] = categorize_weapon(w_type)
        
        if k_guild_raw.upper() == GUILD_NAME.upper():
            kuma_kills += 1; gained_fame += fame; gained_silver += loot_value
            
            k_name = killer.get("Name", "Unknown")
            if k_name not in kuma_stats: kuma_stats[k_name] = {"プレイヤー名": k_name, "キル": 0, "デス": 0, "獲得名声": 0}
            kuma_stats[k_name]["キル"] += 1; kuma_stats[k_name]["獲得名声"] += fame
            
            e_guild_raw, e_alliance_raw = victim.get("GuildName", ""), victim.get("AllianceName", "")
            e_guild_disp = f"[{e_alliance_raw}] {e_guild_raw}" if e_alliance_raw else (e_guild_raw if e_guild_raw else "無所属")
                
            if e_guild_disp not in enemy_stats: enemy_stats[e_guild_disp] = {"敵対ギルド名": e_guild_disp, "倒した数": 0, "やられた数": 0, "奪った名声": 0}
            enemy_stats[e_guild_disp]["倒した数"] += 1; enemy_stats[e_guild_disp]["奪った名声"] += fame
            
            e_alliance_disp = f"[{e_alliance_raw}]" if e_alliance_raw else "無所属"
            if e_alliance_disp not in enemy_alliance_stats: enemy_alliance_stats[e_alliance_disp] = {"敵対同盟名": e_alliance_disp, "倒した数": 0, "やられた数": 0, "奪った名声": 0}
            enemy_alliance_stats[e_alliance_disp]["倒した数"] += 1; enemy_alliance_stats[e_alliance_disp]["奪った名声"] += fame

            w_type = killer.get("Equipment", {}).get("MainHand", {}).get("Type")
            if w_type: weapon_stats[w_type] = weapon_stats.get(w_type, 0) + 1
                
            v_name = victim.get("Name", "Unknown")
            v_disp = f"{v_name} {e_guild_disp}" if e_guild_disp != "無所属" else v_name
            if v_disp not in enemy_victim_stats: enemy_victim_stats[v_disp] = {"敵プレイヤー名": v_disp, "倒した回数": 0, "奪った名声": 0}
            enemy_victim_stats[v_disp]["倒した回数"] += 1; enemy_victim_stats[v_disp]["奪った名声"] += fame
                
        else:
            kuma_deaths += 1; lost_fame += fame; lost_silver += loot_value
            
            v_name = victim.get("Name", "Unknown")
            if v_name not in kuma_stats: kuma_stats[v_name] = {"プレイヤー名": v_name, "キル": 0, "デス": 0, "獲得名声": 0}
            kuma_stats[v_name]["デス"] += 1
            
            e_guild_raw, e_alliance_raw = killer.get("GuildName", ""), killer.get("AllianceName", "")
            e_guild_disp = f"[{e_alliance_raw}] {e_guild_raw}" if e_alliance_raw else (e_guild_raw if e_guild_raw else "無所属")
                
            if e_guild_disp not in enemy_stats: enemy_stats[e_guild_disp] = {"敵対ギルド名": e_guild_disp, "倒した数": 0, "やられた数": 0, "奪った名声": 0}
            enemy_stats[e_guild_disp]["やられた数"] += 1

            e_alliance_disp = f"[{e_alliance_raw}]" if e_alliance_raw else "無所属"
            if e_alliance_disp not in enemy_alliance_stats: enemy_alliance_stats[e_alliance_disp] = {"敵対同盟名": e_alliance_disp, "倒した数": 0, "やられた数": 0, "奪った名声": 0}
            enemy_alliance_stats[e_alliance_disp]["やられた数"] += 1
    
    st.markdown("#### ⚔️ 全体戦果")
    m1, m2, m3 = st.columns(3)
    m1.metric("🔥 キル / 💀 デス", f"{kuma_kills} / {kuma_deaths}")
    m2.metric("🌟 奪った名声 / 📉 ロスト", f"{gained_fame:,} / {lost_fame:,}")
    m3.metric("💰 奪った推定シルバー / 💸 ロスト", f"{gained_silver:,} / {lost_silver:,}")
    st.divider()
    
    col_al, col_gu = st.columns(2)
    with col_al:
        st.markdown("#### 🎌 交戦した敵対同盟")
        if enemy_alliance_stats:
            df_alliance = pd.DataFrame(list(enemy_alliance_stats.values())).sort_values(by="倒した数", ascending=False)
            df_alliance["奪った名声"] = df_alliance["奪った名声"].apply(lambda x: f"{x:,}")
            df_alliance.index = range(1, len(df_alliance) + 1)
            st.dataframe(df_alliance, use_container_width=True)
        else: st.write("交戦データなし")

    with col_gu:
        st.markdown("#### 🎯 交戦した敵対ギルド")
        if enemy_stats:
            df_enemy = pd.DataFrame(list(enemy_stats.values())).sort_values(by="倒した数", ascending=False)
            df_enemy["奪った名声"] = df_enemy["奪った名声"].apply(lambda x: f"{x:,}")
            df_enemy.index = range(1, len(df_enemy) + 1)
            st.dataframe(df_enemy, use_container_width=True)
        else: st.write("交戦データなし")
    
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("#### 🏆 活躍したKUMAメンバー")
        if kuma_stats:
            df_kuma = pd.DataFrame(list(kuma_stats.values())).sort_values(by="獲得名声", ascending=False)
            df_kuma["獲得名声"] = df_kuma["獲得名声"].apply(lambda x: f"{x:,}")
            df_kuma.index = range(1, len(df_kuma) + 1)
            st.dataframe(df_kuma, use_container_width=True)
        else: st.write("活躍データなし")

    with col_r:
        st.markdown("#### 💀 カモにされた敵プレイヤー")
        if enemy_victim_stats:
            df_enemy_v = pd.DataFrame(list(enemy_victim_stats.values())).sort_values(by="倒した回数", ascending=False)
            df_enemy_v["奪った名声"] = df_enemy_v["奪った名声"].apply(lambda x: f"{x:,}")
            df_enemy_v.index = range(1, len(df_enemy_v) + 1)
            st.dataframe(df_enemy_v, use_container_width=True)
        else: st.write("データなし")
            
    st.divider()
    col_w, col_p = st.columns([6, 4])
    with col_w:
        st.markdown("#### ⚔️ 最もキルを生んだ武器")
        if weapon_stats:
            sorted_w = sorted(weapon_stats.items(), key=lambda x: x[1], reverse=True)[:6]
            w_cols = st.columns(3)
            for i, (w_type, count) in enumerate(sorted_w):
                with w_cols[i % 3]:
                    img_url = f"{RENDER_URL}/{w_type}.png?size=80"
                    st.markdown(f"<div style='text-align:center;'><img src='{img_url}' style='background-color: #2c2c2c; border-radius: 8px; border: 1px solid #555;'><br><b>{count} キル</b></div>", unsafe_allow_html=True)
        else: st.caption("武器データなし")
            
    with col_p:
        st.markdown("#### 📊 KUMAメンバー構成 (ロール)")
        if kuma_player_roles:
            role_counts = {}
            for r in kuma_player_roles.values(): role_counts[r] = role_counts.get(r, 0) + 1
            df_roles = pd.DataFrame(list(role_counts.items()), columns=["ロール", "人数"])
            fig = px.pie(
                df_roles, values="人数", names="ロール", hole=0.4, color="ロール",
                color_discrete_map={"🛡️ タンク": "#3498db","⚔️ 火力(近接)": "#e74c3c","🏹 火力(遠距離)": "#e67e22","💚 ヒーラー": "#2ecc71","🌀 サポート/デバフ": "#9b59b6","⚪ その他": "#95a5a6"}
            )
            fig.update_layout(margin=dict(t=20, b=20, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", font_color="white", showlegend=True)
            # ★ 修正: key 引数を追加して、Streamlitエラーを回避
            st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_pie")
        else: st.write("データなし")

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
def get_guild_events(guild_id, offset=0, limit=10):
    try:
        res = requests.get(f"{BASE_URL}/events?limit={limit}&offset={offset}&guildId={guild_id}", timeout=10)
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

@st.cache_data(ttl=60)
def get_last_hour_events(guild_id):
    events = []
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    
    for offset in range(0, 500, 50):
        try:
            res = requests.get(f"{BASE_URL}/events?limit=50&offset={offset}&guildId={guild_id}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                if not data: break
                keep_going = True
                for ev in data:
                    ts_str = ev.get("TimeStamp", "")
                    try:
                        ev_time = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                        if ev_time >= one_hour_ago: events.append(ev)
                        else: keep_going = False 
                    except: pass
                if not keep_going: break
            else: break
        except: break
    return events

@st.cache_data(ttl=180)
def generate_custom_battles(guild_id, time_limit_hours=24):
    events = []
    now = datetime.now(timezone.utc)
    limit_time = now - timedelta(hours=time_limit_hours)
    
    for offset in range(0, 1000, 50):
        try:
            res = requests.get(f"{BASE_URL}/events?limit=50&offset={offset}&guildId={guild_id}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                if not data: break
                keep_going = True
                for ev in data:
                    ts_str = ev.get("TimeStamp", "")
                    try:
                        ev_time = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                        if ev_time >= limit_time: events.append(ev)
                        else: keep_going = False
                    except: pass
                if not keep_going: break
            else: break
        except: break

    if not events: return []

    events_sorted = sorted(events, key=lambda x: datetime.strptime(x["TimeStamp"][:19], "%Y-%m-%dT%H:%M:%S"))
    battles = []
    current_battle = []
    last_event_time = None
    
    for ev in events_sorted:
        ev_time = datetime.strptime(ev["TimeStamp"][:19], "%Y-%m-%dT%H:%M:%S")
        if last_event_time is None:
            current_battle.append(ev)
            last_event_time = ev_time
        else:
            diff = ev_time - last_event_time
            if diff.total_seconds() <= 300: # 5分以内
                current_battle.append(ev)
                last_event_time = ev_time
            else:
                battles.append(current_battle)
                current_battle = [ev]
                last_event_time = ev_time
                
    if current_battle: battles.append(current_battle)
        
    valid_battles = []
    for b in battles:
        players = set()
        for ev in b:
            if ev.get("Killer", {}).get("Name"): players.add(ev["Killer"]["Name"])
            if ev.get("Victim", {}).get("Name"): players.add(ev["Victim"]["Name"])
            for p in ev.get("Participants", []):
                if p.get("Name"): players.add(p["Name"])
                
        if len(players) > 2: # 1v1を除外
            valid_battles.append({"events": b, "players_count": len(players)})
            
    return list(reversed(valid_battles))

@st.cache_data(ttl=300)
def search_player(player_name):
    search_url = f"{BASE_URL}/search?q={player_name}"
    try:
        res = requests.get(search_url, timeout=10)
        if res.status_code == 200:
            for p in res.json().get("players", []):
                if p["Name"].upper() == player_name.upper():
                    detail_res = requests.get(f"{BASE_URL}/players/{p['Id']}", timeout=10)
                    if detail_res.status_code == 200: return {"info": detail_res.json(), "id": p['Id']}
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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 総合ステータス＆分析", 
        "⚔️ 最近のキルボード (超詳細)",
        "🔍 プレイヤー詳細分析",
        "🛡️ バトルレポート(公式API)",
        "⏳ 1時間の戦況レポート",
        "🛠️ 新バトルシステム(テスト)"
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
            hour_labels = [f"{h:02d}時" for h in range(1, 25)]
            hours = {label: 0 for label in hour_labels}
            for ev in analysis_events:
                _, jst_time = convert_time(ev.get("TimeStamp", ""))
                if jst_time != "Unknown":
                    hour_str = jst_time.split(" ")[1].split(":")[0]
                    h_int = int(hour_str)
                    h_int = 24 if h_int == 0 else h_int
                    label = f"{h_int:02d}時"
                    hours[label] += 1
            df_hours = pd.DataFrame({"時間": list(hours.keys()), "キル/デス発生数": list(hours.values())})
            st.bar_chart(df_hours, x="時間", y="キル/デス発生数")
        st.divider()
        st.subheader("👥 メンバー別 戦績ボード")
        if members_data:
            df = pd.DataFrame(members_data)
            df = df[['Name', 'KillFame', 'DeathFame', 'FameRatio']]
            df.columns = ['プレイヤー名', 'キルフェイム', 'デスフェイム', 'K/D比']
            df = df.sort_values(by='キルフェイム', ascending=False)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True, height=600)

    # 【タブ2】最新のキルボード
    with tab2:
        st.subheader("⚔️ 最近の戦闘ログ (超詳細)")
        search_filter = st.text_input("🔍 プレイヤー名でログを絞り込む（空欄で全件表示）", "")
        display_events = []
        if search_filter:
            with st.spinner("検索中..."):
                all_events = get_analysis_events(guild_id)
                for ev in all_events:
                    k_name = ev.get("Killer", {}).get("Name", "")
                    v_name = ev.get("Victim", {}).get("Name", "")
                    if search_filter.upper() in k_name.upper() or search_filter.upper() in v_name.upper():
                        display_events.append(ev)
                display_events = display_events[:10]
        else:
            selected_page = st.radio("表示するページを選択してください", [1, 2, 3, 4, 5], horizontal=True)
            display_events = get_guild_events(guild_id, offset=(selected_page - 1) * 10, limit=10)
        
        if display_events:
            with st.spinner("💰 ロスト品の市場価格を相場APIから取得中..."):
                all_item_ids = []
                for ev in display_events:
                    for item in ev.get("Victim", {}).get("Equipment", {}).values():
                        if item: all_item_ids.append(item.get("Type"))
                    for item in ev.get("Victim", {}).get("Inventory", []):
                        if item: all_item_ids.append(item.get("Type"))
                market_prices = get_market_prices(all_item_ids)

            for ev in display_events:
                killer, victim = ev.get("Killer", {}), ev.get("Victim", {})
                _, jst_time = convert_time(ev.get("TimeStamp", ""))
                v_fame = ev.get("TotalVictimKillFame", 0)
                total_silver = calculate_loot_value(victim, market_prices)
                
                k_alliance = f"[{killer.get('AllianceName')}] " if killer.get('AllianceName') else ""
                v_alliance = f"[{victim.get('AllianceName')}] " if victim.get('AllianceName') else ""
                k_name, k_guild, k_ip = killer.get("Name", "Unknown"), killer.get("GuildName", ""), int(killer.get("AverageItemPower", 0))
                v_name, v_guild, v_ip = victim.get("Name", "Unknown"), victim.get("GuildName", ""), int(victim.get("AverageItemPower", 0))
                k_disp = f"{k_alliance}{k_name} [{k_guild}]" if k_guild else f"{k_alliance}{k_name}"
                v_disp = f"{v_alliance}{v_name} [{v_guild}]" if v_guild else f"{v_alliance}{v_name}"
                
                if k_guild.upper() == GUILD_NAME.upper():
                    st.success(f"🔥 **キル** : **{k_disp}** (IP: {k_ip}) ⚔️ 倒した相手 ➡ **{v_disp}** (IP: {v_ip})")
                else:
                    st.error(f"💀 **デス** : **{v_disp}** (IP: {v_ip}) ⚔️ 倒された相手 ➡ **{k_disp}** (IP: {k_ip})")
                    
                st.caption(f"🕒 {jst_time} ｜ 🌟 取得名声: {v_fame:,} ｜ **💰 推定ロスト総額: {total_silver:,} シルバー**")
                st.markdown(render_participants(ev.get("Participants", [])))
                
                k_eq_html = render_equipment_html(killer.get("Equipment", {}))
                v_eq_html = render_equipment_html(victim.get("Equipment", {}))
                inv_html = render_inventory_html(victim.get("Inventory", []))
                
                col_k, col_v, col_i = st.columns([1.2, 1.2, 1.5])
                with col_k: st.markdown(f"**🔥 {k_name} の装備:**<br>{k_eq_html}", unsafe_allow_html=True)
                with col_v: st.markdown(f"**💀 {v_name} の装備:**<br>{v_eq_html}", unsafe_allow_html=True)
                with col_i: st.markdown(f"**🎒 ロストしたアイテム:**<br>{inv_html}" if inv_html else "**🎒 ロストしたアイテム:** 空っぽ", unsafe_allow_html=True)
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
                    else:
                        st.error("プレイヤーが見つかりませんでした。")

    # 【タブ4】🛡️ バトルレポート (公式API版)
    with tab4:
        st.subheader("🛡️ バトルレポート (公式API版)")
        st.write("※ 公式システムが「バトル」と認定し、APIを発行した戦闘のみ表示されます。(遅延する場合があります)")
        st.info("現在はテストとして、右側の「🛠️ 新バトルシステム(テスト)」タブをお試しください！")

    # 【タブ5】⏳ 1時間の戦況レポート
    with tab5:
        st.subheader("⏳ 直近1時間のリアルタイム・レポート")
        with st.spinner("直近1時間分のデータを探索・集計中..."):
            recent_events = get_last_hour_events(guild_id)
            
        if not recent_events:
            st.info("直近1時間以内に発生したKUMAの戦闘ログはありません。みんな平和に採集しているか、休憩中です！☕")
        else:
            with st.spinner("💰 1時間分のロスト品の市場価格を解析中..."):
                all_item_ids_hour = []
                for ev in recent_events:
                    for item in ev.get("Victim", {}).get("Equipment", {}).values():
                        if item: all_item_ids_hour.append(item.get("Type"))
                    for item in ev.get("Victim", {}).get("Inventory", []):
                        if item: all_item_ids_hour.append(item.get("Type"))
                market_prices_hour = get_market_prices(all_item_ids_hour)

            # ★ タブ5用のユニークな key_prefix を渡す
            render_battle_summary(recent_events, market_prices_hour, key_prefix="tab5_hour")

    # 【タブ6】🛠️ 新バトルシステム(テスト)
    with tab6:
        st.subheader("🛠️ 自作アルゴリズム バトルレポート (テスト版)")
        st.write("公式APIの更新遅延を回避するため、キルログから「戦闘が5分空いたら別バトル」という独自ロジックで集団戦を自動生成しています。（過去24時間・1v1は除外）")
        
        with st.spinner("過去24時間分の全キルログを解析し、バトルを再構築しています... (最大1000件)"):
            custom_battles = generate_custom_battles(guild_id, time_limit_hours=24)
            
        if not custom_battles:
            st.info("過去24時間に、条件に一致するKUMAの集団戦（3人以上）は見つかりませんでした。")
        else:
            with st.spinner("💰 全バトルのロスト品の市場価格を一括解析中..."):
                all_battle_item_ids = []
                for b in custom_battles:
                    for ev in b["events"]:
                        for item in ev.get("Victim", {}).get("Equipment", {}).values():
                            if item: all_battle_item_ids.append(item.get("Type"))
                        for item in ev.get("Victim", {}).get("Inventory", []):
                            if item: all_battle_item_ids.append(item.get("Type"))
                battle_market_prices = get_market_prices(all_battle_item_ids)

            for idx, battle_data in enumerate(custom_battles):
                events = battle_data["events"]
                players_count = battle_data["players_count"]
                
                start_ev = events[0]
                end_ev = events[-1]
                _, jst_start = convert_time(start_ev.get("TimeStamp", ""))
                _, jst_end = convert_time(end_ev.get("TimeStamp", ""))
                
                kuma_k, kuma_d = 0, 0
                for ev in events:
                    if ev.get("Killer", {}).get("GuildName", "").upper() == GUILD_NAME.upper():
                        kuma_k += 1
                    else:
                        kuma_d += 1
                
                header_title = f"⚔️ {jst_start} 〜 {jst_end.split(' ')[1]} ｜ KUMA戦績: {kuma_k}キル / {kuma_d}デス ｜ 参加人数: {players_count}名"
                
                with st.expander(header_title, expanded=(idx == 0)):
                    # ★ タブ6用のユニークな key_prefix を渡す (idxを利用)
                    render_battle_summary(events, battle_market_prices, key_prefix=f"tab6_battle_{idx}")

else:
    st.error("ギルドデータが見つかりませんでした。公式APIが混雑している可能性があります。")
