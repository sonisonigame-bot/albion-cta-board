import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

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

# ★ 究極のKUMA所属判定関数 ★
# ギルドID、ギルド名に加え、「ギルドメンバー名簿(kuma_member_names)」とも照合する
def is_kuma(p_obj, guild_id, guild_name, kuma_member_names):
    if not p_obj: return False
    # ① ギルドIDが一致すればOK
    if p_obj.get("GuildId") == guild_id: return True
    # ② ギルド名が一致すればOK
    gn = p_obj.get("GuildName")
    if gn and str(gn).upper() == guild_name.upper(): return True
    # ③ APIバグでギルドが空っぽでも、名前がKUMA名簿にあれば確実にKUMAとして扱う！
    name = p_obj.get("Name")
    if name and str(name).upper() in kuma_member_names: return True
    return False

# タイムライン生成専用関数
def generate_timeline_html(events, guild_id, guild_name, kuma_member_names):
    kuma_kill_logs = []
    kuma_death_logs = []
    
    def format_player(p):
        name = p.get("Name", "Unknown")
        g = p.get("GuildName") or ""
        a = p.get("AllianceName") or ""
        if g:
            g_str = f"[{a}] {g}" if a else f"{g}"
            return f"{name} <span style='font-size:0.85em;color:#aaa;'>{g_str}</span>"
        return name

    for ev in events:
        killer, victim = ev.get("Killer", {}), ev.get("Victim", {})
        
        # 修正された確実な判定
        is_k_kuma = is_kuma(killer, guild_id, guild_name, kuma_member_names)
        is_v_kuma = is_kuma(victim, guild_id, guild_name, kuma_member_names)
        if not is_k_kuma and not is_v_kuma:
            is_k_kuma = any(is_kuma(p, guild_id, guild_name, kuma_member_names) for p in ev.get("Participants", []))
            
        k_wep = killer.get("Equipment", {}).get("MainHand", {}).get("Type")
        v_wep = victim.get("Equipment", {}).get("MainHand", {}).get("Type")
        k_wep_url = f"{RENDER_URL}/{k_wep}.png?size=40" if k_wep else None
        v_wep_url = f"{RENDER_URL}/{v_wep}.png?size=40" if v_wep else None
        
        k_img_html = f"<img src='{k_wep_url}' width='26' style='vertical-align:middle; background-color:#2c2c2c; border-radius:4px;'>" if k_wep else "👊"
        v_img_html = f"<img src='{v_wep_url}' width='26' style='vertical-align:middle; background-color:#2c2c2c; border-radius:4px;'>" if v_wep else "👊"
        
        _, jst_time = convert_time(ev.get("TimeStamp", ""))
        time_str = jst_time.split(" ")[1] if jst_time != "Unknown" else "??:??"
        
        k_ip_val = int(killer.get("AverageItemPower", 0))
        v_ip_val = int(victim.get("AverageItemPower", 0))
        
        k_disp = format_player(killer)
        v_disp = format_player(victim)

        if is_k_kuma and not is_v_kuma:
            log_str = f"<div style='margin-bottom:6px; color:#ffffff; font-size:15px;'><span style='color:#a0a0a0;font-size:13px;'>[{time_str}]</span> {k_img_html} <b>{k_disp}</b> <span style='font-size:12px;color:#f39c12;'>[IP:{k_ip_val}]</span> <span style='color:#3498db; margin: 0 4px;'>▶キル▶</span> {v_img_html} <b>{v_disp}</b> <span style='font-size:12px;color:#f39c12;'>[IP:{v_ip_val}]</span></div>"
            kuma_kill_logs.append(log_str)
        elif is_v_kuma:
            log_str = f"<div style='margin-bottom:6px; color:#ffffff; font-size:15px;'><span style='color:#a0a0a0;font-size:13px;'>[{time_str}]</span> {v_img_html} <b>{v_disp}</b> <span style='font-size:12px;color:#f39c12;'>[IP:{v_ip_val}]</span> <span style='color:#e74c3c; margin: 0 4px;'>◀デス◀</span> {k_img_html} <b>{k_disp}</b> <span style='font-size:12px;color:#f39c12;'>[IP:{k_ip_val}]</span></div>"
            kuma_death_logs.append(log_str)
            
    return kuma_kill_logs, kuma_death_logs

# 詳細レポート共通関数
def render_battle_summary(events, market_prices, guild_id, guild_name, kuma_member_names):
    kuma_kills, kuma_deaths = 0, 0
    gained_fame, lost_fame, gained_silver, lost_silver = 0, 0, 0, 0
    
    kuma_players = {}
    enemy_players = {}
    
    def track_player(p_obj):
        if not p_obj or not p_obj.get("Name"): return
        name = p_obj["Name"]
        guild = p_obj.get("GuildName") or ""
        alliance = p_obj.get("AllianceName") or ""
        ip = int(p_obj.get("AverageItemPower", 0))
        w_type = p_obj.get("Equipment", {}).get("MainHand", {}).get("Type")
        w_url = f"{RENDER_URL}/{w_type}.png?size=40" if w_type else None
        
        if is_kuma(p_obj, guild_id, guild_name, kuma_member_names):
            if name not in kuma_players:
                kuma_players[name] = {"武器": w_url, "プレイヤー名": name, "IP": ip}
            else:
                kuma_players[name]["IP"] = max(kuma_players[name]["IP"], ip)
                if w_url: kuma_players[name]["武器"] = w_url
        else:
            a_disp = f"[{alliance}]" if alliance else "無所属"
            g_disp = f"[{alliance}] {guild}" if alliance else (guild if guild else "無所属")
            if name not in enemy_players:
                enemy_players[name] = {"武器": w_url, "プレイヤー名": name, "所属": g_disp, "IP": ip, "alliance_disp": a_disp}
            else:
                enemy_players[name]["IP"] = max(enemy_players[name]["IP"], ip)
                if w_url: enemy_players[name]["武器"] = w_url

    for ev in events:
        track_player(ev.get("Killer"))
        track_player(ev.get("Victim"))
        for p in ev.get("Participants", []):
            track_player(p)
            
    enemy_stats = {}
    enemy_alliance_stats = {}
    for name, info in enemy_players.items():
        g_disp = info["所属"]
        a_disp = info["alliance_disp"]
        ip = info["IP"]
        
        if g_disp not in enemy_stats:
            enemy_stats[g_disp] = {"敵対ギルド名": g_disp, "参加人数": 0, "平均IP": 0, "倒した数": 0, "やられた数": 0, "奪った名声": 0, "_ip_sum": 0}
        enemy_stats[g_disp]["参加人数"] += 1
        enemy_stats[g_disp]["_ip_sum"] += ip
        
        if a_disp not in enemy_alliance_stats:
            enemy_alliance_stats[a_disp] = {"敵対同盟名": a_disp, "参加人数": 0, "平均IP": 0, "倒した数": 0, "やられた数": 0, "奪った名声": 0, "_ip_sum": 0}
        enemy_alliance_stats[a_disp]["参加人数"] += 1
        enemy_alliance_stats[a_disp]["_ip_sum"] += ip

    for stats in enemy_stats.values():
        stats["平均IP"] = int(stats["_ip_sum"] / stats["参加人数"])
        del stats["_ip_sum"]
    for stats in enemy_alliance_stats.values():
        stats["平均IP"] = int(stats["_ip_sum"] / stats["参加人数"])
        del stats["_ip_sum"]
        
    kuma_stats = {}
    enemy_victim_stats = {}

    for ev in events:
        killer, victim = ev.get("Killer", {}), ev.get("Victim", {})
        fame = ev.get("TotalVictimKillFame", 0)
        loot_value = calculate_loot_value(victim, market_prices)
        
        is_k_kuma = is_kuma(killer, guild_id, guild_name, kuma_member_names)
        is_v_kuma = is_kuma(victim, guild_id, guild_name, kuma_member_names)
        if not is_k_kuma and not is_v_kuma:
            is_k_kuma = any(is_kuma(p, guild_id, guild_name, kuma_member_names) for p in ev.get("Participants", []))
        
        if is_k_kuma and not is_v_kuma:
            kuma_kills += 1; gained_fame += fame; gained_silver += loot_value
            
            k_name = killer.get("Name", "Unknown") if is_kuma(killer, guild_id, guild_name, kuma_member_names) else None
            if not k_name:
                for p in ev.get("Participants", []):
                    if is_kuma(p, guild_id, guild_name, kuma_member_names):
                        k_name = p.get("Name", "Unknown")
                        break
            
            if k_name:
                k_wep_url = kuma_players.get(k_name, {}).get("武器")
                if k_name not in kuma_stats:
                    kuma_stats[k_name] = {"武器": k_wep_url, "プレイヤー名": k_name, "IP": kuma_players.get(k_name, {}).get("IP", 0), "キル": 0, "デス": 0, "獲得名声": 0}
                kuma_stats[k_name]["キル"] += 1; kuma_stats[k_name]["獲得名声"] += fame
            
            e_guild_raw, e_alliance_raw = victim.get("GuildName") or "", victim.get("AllianceName") or ""
            e_guild_disp = f"[{e_alliance_raw}] {e_guild_raw}" if e_alliance_raw else (e_guild_raw if e_guild_raw else "無所属")
            e_alliance_disp = f"[{e_alliance_raw}]" if e_alliance_raw else "無所属"
            
            if e_guild_disp in enemy_stats:
                enemy_stats[e_guild_disp]["倒した数"] += 1; enemy_stats[e_guild_disp]["奪った名声"] += fame
            if e_alliance_disp in enemy_alliance_stats:
                enemy_alliance_stats[e_alliance_disp]["倒した数"] += 1; enemy_alliance_stats[e_alliance_disp]["奪った名声"] += fame

            v_name = victim.get("Name", "Unknown")
            v_disp = f"{v_name} {e_guild_disp}" if e_guild_disp != "無所属" else v_name
            v_wep_url = enemy_players.get(v_name, {}).get("武器")
            
            if v_disp not in enemy_victim_stats:
                enemy_victim_stats[v_disp] = {"武器": v_wep_url, "敵プレイヤー名": v_disp, "IP": enemy_players.get(v_name, {}).get("IP", 0), "倒した回数": 0, "奪った名声": 0}
            enemy_victim_stats[v_disp]["倒した回数"] += 1; enemy_victim_stats[v_disp]["奪った名声"] += fame
                
        elif is_v_kuma:
            kuma_deaths += 1; lost_fame += fame; lost_silver += loot_value
            v_name = victim.get("Name", "Unknown")
            v_wep_url = kuma_players.get(v_name, {}).get("武器")
            
            if v_name not in kuma_stats:
                kuma_stats[v_name] = {"武器": v_wep_url, "プレイヤー名": v_name, "IP": kuma_players.get(v_name, {}).get("IP", 0), "キル": 0, "デス": 0, "獲得名声": 0}
            kuma_stats[v_name]["デス"] += 1
            
            e_guild_raw, e_alliance_raw = killer.get("GuildName") or "", killer.get("AllianceName") or ""
            e_guild_disp = f"[{e_alliance_raw}] {e_guild_raw}" if e_alliance_raw else (e_guild_raw if e_guild_raw else "無所属")
            e_alliance_disp = f"[{e_alliance_raw}]" if e_alliance_raw else "無所属"
            
            if e_guild_disp in enemy_stats: enemy_stats[e_guild_disp]["やられた数"] += 1
            if e_alliance_disp in enemy_alliance_stats: enemy_alliance_stats[e_alliance_disp]["やられた数"] += 1

    kuma_p_count = len(kuma_players)
    enemy_p_count = len(enemy_players)
    kuma_avg_ip = int(sum(info["IP"] for info in kuma_players.values()) / kuma_p_count) if kuma_p_count > 0 else 0
    enemy_avg_ip = int(sum(info["IP"] for info in enemy_players.values()) / enemy_p_count) if enemy_p_count > 0 else 0

    st.markdown(f"#### ⚔️ 全体戦果 (KUMA **{kuma_p_count}名** 🆚 敵軍 **{enemy_p_count}名**)")
    st.caption(f"🛡️ **平均IP:** KUMA `{kuma_avg_ip}` ｜ 敵軍 `{enemy_avg_ip}`")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔥 キル / 💀 デス", f"{kuma_kills} / {kuma_deaths}")
    m2.metric("👥 参加人数 (KUMA / 敵)", f"{kuma_p_count} / {enemy_p_count}")
    m3.metric("🌟 名声 (奪 / 失)", f"{gained_fame:,} / {lost_fame:,}")
    m4.metric("💰 シルバー (奪 / 失)", f"{gained_silver:,} / {lost_silver:,}")
    st.divider()
    
    col_al, col_gu = st.columns(2)
    with col_al:
        st.markdown("#### 🎌 交戦した敵対同盟")
        if enemy_alliance_stats:
            df_alliance = pd.DataFrame(list(enemy_alliance_stats.values()))
            df_alliance = df_alliance[['敵対同盟名', '参加人数', '平均IP', '倒した数', 'やられた数', '奪った名声']]
            df_alliance = df_alliance.sort_values(by="参加人数", ascending=False)
            df_alliance["奪った名声"] = df_alliance["奪った名声"].apply(lambda x: f"{x:,}")
            df_alliance.index = range(1, len(df_alliance) + 1)
            st.dataframe(df_alliance, use_container_width=True)
        else: st.write("交戦データなし")

    with col_gu:
        st.markdown("#### 🎯 交戦した敵対ギルド")
        if enemy_stats:
            df_enemy = pd.DataFrame(list(enemy_stats.values()))
            df_enemy = df_enemy[['敵対ギルド名', '参加人数', '平均IP', '倒した数', 'やられた数', '奪った名声']]
            df_enemy = df_enemy.sort_values(by="参加人数", ascending=False)
            df_enemy["奪った名声"] = df_enemy["奪った名声"].apply(lambda x: f"{x:,}")
            df_enemy.index = range(1, len(df_enemy) + 1)
            st.dataframe(df_enemy, use_container_width=True)
        else: st.write("交戦データなし")
    
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("#### 🏆 活躍したKUMAメンバー")
        if kuma_stats:
            df_kuma = pd.DataFrame(list(kuma_stats.values()))
            df_kuma = df_kuma[['武器', 'プレイヤー名', 'IP', 'キル', 'デス', '獲得名声']]
            df_kuma = df_kuma.sort_values(by="獲得名声", ascending=False)
            df_kuma["獲得名声"] = df_kuma["獲得名声"].apply(lambda x: f"{x:,}")
            df_kuma.index = range(1, len(df_kuma) + 1)
            st.dataframe(df_kuma, column_config={"武器": st.column_config.ImageColumn("武器", width="small")}, use_container_width=True)
        else: st.write("活躍データなし")

    with col_r:
        st.markdown("#### 💀 カモにされた敵プレイヤー")
        if enemy_victim_stats:
            df_enemy_v = pd.DataFrame(list(enemy_victim_stats.values()))
            df_enemy_v = df_enemy_v[['武器', '敵プレイヤー名', 'IP', '倒した回数', '奪った名声']]
            df_enemy_v = df_enemy_v.sort_values(by="倒した回数", ascending=False)
            df_enemy_v["奪った名声"] = df_enemy_v["奪った名声"].apply(lambda x: f"{x:,}")
            df_enemy_v.index = range(1, len(df_enemy_v) + 1)
            st.dataframe(df_enemy_v, column_config={"武器": st.column_config.ImageColumn("武器", width="small")}, use_container_width=True)
        else: st.write("データなし")
            
    st.divider()
    col_k_part, col_e_part = st.columns(2)
    with col_k_part:
        st.markdown("#### 🐻 参加したKUMAメンバー一覧")
        if kuma_players:
            df_kp = pd.DataFrame(list(kuma_players.values()))
            df_kp = df_kp[['武器', 'プレイヤー名', 'IP']]
            df_kp = df_kp.sort_values(by="IP", ascending=False)
            df_kp.index = range(1, len(df_kp) + 1)
            st.dataframe(df_kp, column_config={"武器": st.column_config.ImageColumn("武器", width="small")}, use_container_width=True)
        else: st.write("データなし")
            
    with col_e_part:
        st.markdown("#### 👿 参加した敵プレイヤー一覧")
        if enemy_players:
            df_ep = pd.DataFrame(list(enemy_players.values()))
            df_ep = df_ep[['武器', 'プレイヤー名', '所属', 'IP']]
            df_ep = df_ep.sort_values(by="IP", ascending=False)
            df_ep.index = range(1, len(df_ep) + 1)
            st.dataframe(df_ep, column_config={"武器": st.column_config.ImageColumn("武器", width="small")}, use_container_width=True)
        else: st.write("データなし")
        
    st.divider()
    kill_logs, death_logs = generate_timeline_html(events, guild_id, guild_name, kuma_member_names)
    with st.expander("📜 バトル タイムライン (詳細キル/デスログ)", expanded=False):
        col_kl, col_dl = st.columns(2)
        with col_kl:
            st.markdown("**🔥 KUMAのキルログ**")
            if kill_logs:
                st.markdown("<div style='max-height: 400px; overflow-y: auto; padding: 12px; background-color: #1e1e1e; border-radius: 8px;'>" + "".join(kill_logs) + "</div>", unsafe_allow_html=True)
            else:
                st.write("キルログなし")
                
        with col_dl:
            st.markdown("**💀 KUMAのデスログ**")
            if death_logs:
                st.markdown("<div style='max-height: 400px; overflow-y: auto; padding: 12px; background-color: #1e1e1e; border-radius: 8px;'>" + "".join(death_logs) + "</div>", unsafe_allow_html=True)
            else:
                st.write("デスログなし")

@st.cache_data(ttl=300)
def get_guild_info(guild_name):
    try:
        res = requests.get(f"{BASE_URL}/search?q={guild_name}", timeout=10)
        if res.status_code == 200:
            for guild in res.json().get("guilds", []):
                if guild["Name"].upper() == guild_name.upper():
                    detail_res = requests.get(f"{BASE_URL}/guilds/{guild['Id']}", timeout=10)
                    if detail_res.status_code == 200: return detail_res.json()
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
def get_recent_events(guild_id, hours=1):
    events = []
    now = datetime.now(timezone.utc)
    limit_time = now - timedelta(hours=hours)
    
    for offset in range(0, 2000, 50):
        try:
            res = requests.get(f"{BASE_URL}/events?limit=50&offset={offset}&guildId={guild_id}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                if not data: break
                old_count = 0
                for ev in data:
                    ts_str = ev.get("TimeStamp", "")
                    try:
                        ev_time = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                        if ev_time >= limit_time: events.append(ev)
                        else: old_count += 1 
                    except: pass
                if old_count == len(data): break
            else: break
        except: break
    return events

@st.cache_data(ttl=180)
def generate_custom_battles(guild_id, time_limit_hours=24):
    events = []
    now = datetime.now(timezone.utc)
    limit_time = now - timedelta(hours=time_limit_hours)
    
    for offset in range(0, 2000, 50):
        try:
            res = requests.get(f"{BASE_URL}/events?limit=50&offset={offset}&guildId={guild_id}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                if not data: break
                old_count = 0
                for ev in data:
                    ts_str = ev.get("TimeStamp", "")
                    try:
                        ev_time = datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                        if ev_time >= limit_time: events.append(ev)
                        else: old_count += 1
                    except: pass
                if old_count == len(data): break
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
    
    # ★ APIのバグ（ギルド名消失）を無効化するため、ギルドメンバー名簿を裏で取得しておく
    with st.spinner("ギルド名簿を同期中..."):
        members_data = get_guild_members(guild_id)
        # 大文字に統一して検索しやすいセットにする
        kuma_member_names = {str(m["Name"]).upper() for m in members_data} if members_data else set()
    
    # --- 4. 画面表示 ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 総合ステータス＆分析", 
        "🛡️ バトルレポート (新システム)",
        "⏳ 1時間の戦況レポート",
        "⚔️ 最近のキルボード",
        "🔍 プレイヤー詳細分析"
    ])

    # 【タブ1】総合ステータス ＆ 分析
    with tab1:
        st.subheader("📊 ギルド総合ステータス")
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

        st.subheader("📜 過去6時間のバトル タイムライン (詳細キル/デスログ)")
        with st.spinner("直近6時間のタイムラインを生成中..."):
            recent_events_tab1 = get_recent_events(guild_id, hours=6)
            
        if recent_events_tab1:
            kill_logs_t1, death_logs_t1 = generate_timeline_html(recent_events_tab1, guild_id, GUILD_NAME, kuma_member_names)
            col_kl1, col_dl1 = st.columns(2)
            with col_kl1:
                st.markdown("**🔥 KUMAのキルログ**")
                if kill_logs_t1:
                    st.markdown("<div style='max-height: 400px; overflow-y: auto; padding: 12px; background-color: #1e1e1e; border-radius: 8px;'>" + "".join(kill_logs_t1) + "</div>", unsafe_allow_html=True)
                else:
                    st.write("直近6時間のキルログはありません")
            with col_dl1:
                st.markdown("**💀 KUMAのデスログ**")
                if death_logs_t1:
                    st.markdown("<div style='max-height: 400px; overflow-y: auto; padding: 12px; background-color: #1e1e1e; border-radius: 8px;'>" + "".join(death_logs_t1) + "</div>", unsafe_allow_html=True)
                else:
                    st.write("直近6時間のデスログはありません")
        else:
            st.info("過去6時間以内に発生した戦闘ログはありません。")
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

    # 【タブ2】🛡️ バトルレポート (新システム)
    with tab2:
        st.subheader("🛡️ 新バトルレポート")
        st.write("公式APIの更新遅延を回避するため、キルログから「戦闘が5分空いたら別バトル」という独自ロジックで集団戦を自動生成しています。（過去24時間・1v1は除外）")
        
        with st.spinner("過去24時間分の全キルログを解析し、バトルを再構築しています... (最大2000件)"):
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
                    is_k_kuma = is_kuma(ev.get("Killer", {}), guild_id, GUILD_NAME, kuma_member_names)
                    is_v_kuma = is_kuma(ev.get("Victim", {}), guild_id, GUILD_NAME, kuma_member_names)
                    if not is_k_kuma and not is_v_kuma:
                        is_k_kuma = any(is_kuma(p, guild_id, GUILD_NAME, kuma_member_names) for p in ev.get("Participants", []))
                    
                    if is_k_kuma and not is_v_kuma: kuma_k += 1
                    if is_v_kuma: kuma_d += 1
                        
                header_title = f"⚔️ {jst_start} 〜 {jst_end.split(' ')[1]} ｜ KUMA戦績: {kuma_k}キル / {kuma_d}デス ｜ 参加総数: {players_count}名"
                
                with st.expander(header_title, expanded=(idx == 0)):
                    render_battle_summary(events, battle_market_prices, guild_id, GUILD_NAME, kuma_member_names)

    # 【タブ3】⏳ 1時間の戦況レポート
    with tab3:
        st.subheader("⏳ 直近1時間のリアルタイム・レポート")
        with st.spinner("直近1時間分のデータを探索・集計中..."):
            recent_events = get_recent_events(guild_id, hours=1)
            
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

            render_battle_summary(recent_events, market_prices_hour, guild_id, GUILD_NAME, kuma_member_names)

    # 【タブ4】⚔️ 最近のキルボード
    with tab4:
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
                
                is_kuma_k = is_kuma(killer, guild_id, GUILD_NAME, kuma_member_names)
                is_kuma_v = is_kuma(victim, guild_id, GUILD_NAME, kuma_member_names)
                if not is_kuma_k and not is_kuma_v:
                    is_kuma_k = any(is_kuma(p, guild_id, GUILD_NAME, kuma_member_names) for p in ev.get("Participants", []))
                
                if is_kuma_k and not is_kuma_v:
                    st.success(f"🔥 **キル** : **{k_disp}** (IP: {k_ip}) ⚔️ 倒した相手 ➡ **{v_disp}** (IP: {v_ip})")
                elif is_kuma_v:
                    st.error(f"💀 **デス** : **{v_disp}** (IP: {v_ip}) ⚔️ 倒された相手 ➡ **{k_disp}** (IP: {k_ip})")
                else:
                    st.info(f"⚪ **戦闘** : **{k_disp}** (IP: {k_ip}) ⚔️ 倒した相手 ➡ **{v_disp}** (IP: {v_ip})")
                    
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

    # 【タブ5】🔍 プレイヤー詳細分析
    with tab5:
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
                            col_k, col_v = st.columns(2)
                            with col_k:
                                st.markdown(f"**自分の装備:**<br>{k_eq}", unsafe_allow_html=True)
                            with col_v:
                                st.markdown(f"**相手の装備 (名声: {kill.get('TotalVictimKillFame', 0):,}):**<br>{v_eq}", unsafe_allow_html=True)
                            st.write("")
                            
                        st.subheader("💀 直近のデス (最新3件)")
                        for death in get_player_recent_history(p_id, "deaths", 3):
                            k_eq = render_equipment_html(death.get("Killer", {}).get("Equipment", {}))
                            v_eq = render_equipment_html(death.get("Victim", {}).get("Equipment", {}))
                            _, jst_time = convert_time(death.get("TimeStamp", ""))
                            st.error(f"⚔️ 倒された相手: **{death.get('Killer', {}).get('Name', 'Unknown')}** ｜ 🕒 **{jst_time}**")
                            col_k, col_v = st.columns(2)
                            with col_k:
                                st.markdown(f"**相手の装備:**<br>{k_eq}", unsafe_allow_html=True)
                            with col_v:
                                st.markdown(f"**ロストした装備 (相手の名声: {death.get('TotalVictimKillFame', 0):,}):**<br>{v_eq}", unsafe_allow_html=True)
                            st.write("")
                    else:
                        st.error("プレイヤーが見つかりませんでした。")

else:
    st.error("ギルドデータが見つかりませんでした。公式APIが混雑している可能性があります。")
