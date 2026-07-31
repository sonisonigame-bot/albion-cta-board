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
                            if p < prices[iid]:
                                prices[iid] = p
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
                        if ev_time >= one_hour_ago:
                            events.append(ev)
                        else:
                            keep_going = False 
                    except: pass
                if not keep_going: break
            else:
                break
        except: break
    return events

# ★ 追加: 自作アルゴリズムによる「バトル生成関数」 (過去24時間、間隔5分でクラスタリング)
@st.cache_data(ttl=180)
def generate_custom_battles(guild_id, time_limit_hours=24):
    events = []
    now = datetime.now(timezone.utc)
    limit_time = now - timedelta(hours=time_limit_hours)
    
    # APIの負荷を考え、最大1000件（または24時間）まで遡る
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
                        if ev_time >= limit_time:
                            events.append(ev)
                        else:
                            keep_going = False
                    except: pass
                if not keep_going: break
            else: break
        except: break

    if not events:
        return []

    # イベントを古い順（時間軸通り）にソート
    events_sorted = sorted(events, key=lambda x: datetime.strptime(x["TimeStamp"][:19], "%Y-%m-%dT%H:%M:%S"))
    
    battles = []
    current_battle = []
    last_event_time = None
    
    # 5分（300秒）間隔で戦闘を区切るクラスタリング処理
    for ev in events_sorted:
        ev_time = datetime.strptime(ev["TimeStamp"][:19], "%Y-%m-%dT%H:%M:%S")
        if last_event_time is None:
            current_battle.append(ev)
            last_event_time = ev_time
        else:
            diff = ev_time - last_event_time
            if diff.total_seconds() <= 300: # 5分以内なら同じバトル
                current_battle.append(ev)
                last_event_time = ev_time
            else: # 5分以上空いたら別バトルとして保存し、新しくリストを作る
                battles.append(current_battle)
                current_battle = [ev]
                last_event_time = ev_time
                
    if current_battle:
        battles.append(current_battle)
        
    valid_battles = []
    for b in battles:
        # 1v1を除外するため、関与したユニークなプレイヤー数を数える
        players = set()
        for ev in b:
            if ev.get("Killer", {}).get("Name"): players.add(ev["Killer"]["Name"])
            if ev.get("Victim", {}).get("Name"): players.add(ev["Victim"]["Name"])
            for p in ev.get("Participants", []):
                if p.get("Name"): players.add(p["Name"])
                
        if len(players) > 2: # 合計人数が3人以上なら「集団での戦闘」とみなす
            valid_battles.append({"events": b, "players_count": len(players)})
            
    # 最新のバトルが一番上に来るように反転して返す
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
    # ★ タブ6を追加
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

    # 【タブ4】🛡️ バトルレポート (既存の公式API)
    with tab4:
        st.subheader("🛡️ バトルレポート (公式API版)")
        st.write("※ 公式システムが「バトル」と認定し、APIを発行した戦闘のみ表示されます。(遅延する場合があります)")
        
        with st.spinner("公式のバトル履歴を検索中..."):
            # ★ 既存のバトルAPI（公式版）を使用（関数の定義は省略せずそのまま使用）
            # ここでは便宜上、get_group_battles を呼び出さないか、軽く呼ぶ程度に留めます
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

            kuma_kills, kuma_deaths = 0, 0
            gained_fame, lost_fame, gained_silver, lost_silver = 0, 0, 0, 0
            
            for ev in recent_events:
                killer, victim = ev.get("Killer", {}), ev.get("Victim", {})
                fame = ev.get("TotalVictimKillFame", 0)
                loot_value = calculate_loot_value(victim, market_prices_hour)
                if killer.get("GuildName", "").upper() == GUILD_NAME.upper():
                    kuma_kills += 1; gained_fame += fame; gained_silver += loot_value
                else:
                    kuma_deaths += 1; lost_fame += fame; lost_silver += loot_value
            
            st.divider()
            st.markdown("#### ⚔️ 1時間の全体戦果")
            m1, m2, m3 = st.columns(3)
            m1.metric("🔥 キル / 💀 デス", f"{kuma_kills} / {kuma_deaths}")
            m2.metric("🌟 奪った名声 / 📉 ロスト", f"{gained_fame:,} / {lost_fame:,}")
            m3.metric("💰 奪った推定シルバー / 💸 ロスト", f"{gained_silver:,} / {lost_silver:,}")
            st.divider()
            st.info("詳細は省略表示しています。")

    # 【タブ6】🛠️ 新バトルシステム(テスト) (★追加★)
    with tab6:
        st.subheader("🛠️ 自作アルゴリズム バトルレポート (テスト版)")
        st.write("公式APIの更新遅延を回避するため、キルログから「戦闘が5分空いたら別バトル」という独自ロジックで集団戦を自動生成しています。（過去24時間・1v1は除外）")
        
        with st.spinner("過去24時間分の全キルログを解析し、バトルを再構築しています... (最大1000件)"):
            custom_battles = generate_custom_battles(guild_id, time_limit_hours=24)
            
        if not custom_battles:
            st.info("過去24時間に、条件に一致するKUMAの集団戦（3人以上）は見つかりませんでした。")
        else:
            for idx, battle_data in enumerate(custom_battles):
                events = battle_data["events"]
                players_count = battle_data["players_count"]
                
                # バトルの開始時間と終了時間を取得（eventsは古い順で入っているので最初と最後）
                start_ev = events[0]
                end_ev = events[-1]
                _, jst_start = convert_time(start_ev.get("TimeStamp", ""))
                _, jst_end = convert_time(end_ev.get("TimeStamp", ""))
                
                # 簡易集計
                kuma_k, kuma_d, total_fame = 0, 0, 0
                for ev in events:
                    if ev.get("Killer", {}).get("GuildName", "").upper() == GUILD_NAME.upper():
                        kuma_k += 1
                        total_fame += ev.get("TotalVictimKillFame", 0)
                    else:
                        kuma_d += 1
                
                # アコーディオン（展開）でリストを表示
                header_title = f"⚔️ {jst_start} 〜 {jst_end.split(' ')[1]} ｜ KUMA戦績: {kuma_k}キル / {kuma_d}デス ｜ 参加人数: {players_count}名"
                
                with st.expander(header_title, expanded=(idx == 0)): # 最新の1件目だけ最初から開いておく
                    st.markdown("#### 🚩 バトル詳細レポート")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("🐻 KUMAのキル", kuma_k)
                    c2.metric("💀 KUMAのデス", kuma_d)
                    c3.metric("🌟 奪った総名声", f"{total_fame:,}")
                    
                    st.divider()
                    
                    # このバトル内の個人成績を集計
                    kuma_stats = {}
                    enemy_stats = {}
                    
                    for ev in events:
                        killer, victim = ev.get("Killer", {}), ev.get("Victim", {})
                        k_guild = killer.get("GuildName", "").upper()
                        v_guild = victim.get("GuildName", "").upper()
                        fame = ev.get("TotalVictimKillFame", 0)
                        
                        if k_guild == GUILD_NAME.upper():
                            # KUMAキル
                            k_name = killer.get("Name", "Unknown")
                            if k_name not in kuma_stats: kuma_stats[k_name] = {"プレイヤー名": k_name, "キル": 0, "デス": 0}
                            kuma_stats[k_name]["キル"] += 1
                            
                            # 敵集計
                            e_guild = victim.get("GuildName", "")
                            e_alliance = victim.get("AllianceName", "")
                            e_disp = f"[{e_alliance}] {e_guild}" if e_alliance else (e_guild if e_guild else "無所属")
                            if e_disp not in enemy_stats: enemy_stats[e_disp] = {"敵対ギルド": e_disp, "倒した数": 0, "やられた数": 0}
                            enemy_stats[e_disp]["倒した数"] += 1
                            
                        elif v_guild == GUILD_NAME.upper():
                            # KUMAデス
                            v_name = victim.get("Name", "Unknown")
                            if v_name not in kuma_stats: kuma_stats[v_name] = {"プレイヤー名": v_name, "キル": 0, "デス": 0}
                            kuma_stats[v_name]["デス"] += 1
                            
                            e_guild = killer.get("GuildName", "")
                            e_alliance = killer.get("AllianceName", "")
                            e_disp = f"[{e_alliance}] {e_guild}" if e_alliance else (e_guild if e_guild else "無所属")
                            if e_disp not in enemy_stats: enemy_stats[e_disp] = {"敵対ギルド": e_disp, "倒した数": 0, "やられた数": 0}
                            enemy_stats[e_disp]["やられた数"] += 1

                    col_k, col_e = st.columns(2)
                    with col_k:
                        st.markdown("**🐻 参加KUMAメンバー戦績**")
                        if kuma_stats:
                            df_kuma = pd.DataFrame(list(kuma_stats.values())).sort_values(by="キル", ascending=False)
                            df_kuma.index = range(1, len(df_kuma) + 1)
                            st.dataframe(df_kuma, use_container_width=True)
                    with col_e:
                        st.markdown("**🎯 交戦した敵対ギルド**")
                        if enemy_stats:
                            df_enemy = pd.DataFrame(list(enemy_stats.values())).sort_values(by="倒した数", ascending=False)
                            df_enemy.index = range(1, len(df_enemy) + 1)
                            st.dataframe(df_enemy, use_container_width=True)

else:
    st.error("ギルドデータが見つかりませんでした。公式APIが混雑している可能性があります。")
