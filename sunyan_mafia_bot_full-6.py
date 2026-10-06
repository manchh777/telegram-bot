import logging
import time
import threading
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    PreCheckoutQueryHandler,
)
from enum import Enum
from datetime import datetime, timedelta
import telegram.error
import random
from collections import Counter
from telegram import Animation

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Game states
class GameState(Enum):
    IDLE = 0
    REGISTRATION = 1
    RUNNING = 2
    NIGHT = 3
    DAY = 4
    VOTING = 5
    LAST_WORD = 6
    CONFIRM_KILL = 7

# Roles
class Role(Enum):
    CITIZEN = "👨🏼 Խաղաղ բնակիչ"
    MAFIA = "🤵🏻 Դոն"
    MAFIA_SUB = "🤵🏻 Մաֆիա"
    DOCTOR = "👨🏼‍⚕️ Բժիշկ"
    COMMISSAR = "👮‍♂️ Կոմիսար"
    MANIAC = "🪓 Մոլագար"
    MISTRESS = "💃 Սիրուհի"
    SERGEANT = "👮‍♀️ Սերժանտ"
    LAWYER = "🧑🏼‍💼 Իրավաբան"
    WANDERER = "//‍♀️ Թափառական"
    KAMIKAZE = "💣 Կամիկաձե"
    THIEF = "🦹 Գող"
    JOURNALIST = "📰 Լրագրող"
    GUARD = "🛡️ Պահակ"
    ACCOUNTANT = "📊 Հաշվապահ"
    SPY = "🕴️ Լրտես"
    TRAITOR = "🗡️ Դավաճան"
    DISABLED = "♿ Հաշմանդամ"
    JUDGE = "⚖️ Դատավոր"
    LUCKY = "🍀 Հաջողակ"


# Դերերի գեղեցիկ գիֆեր (Telegram-ում աշխատող հանրային հղումներ)
ROLE_GIFS = {
    # Բոլորը i.giphy.com — ստուգված աշխատող հղումներ (յուրաքանչյուր դեր առանձին)
    Role.CITIZEN: "https://i.giphy.com/media/hWk2jVZYz8x9A5rOnY/giphy.gif",        # բնակիչ / Mr Bean
    Role.MAFIA: "https://i.giphy.com/media/ze5DIMqmLOKpg2yVlK/giphy.gif",          # դոն / Boss Mafia
    Role.MAFIA_SUB: "https://i.giphy.com/media/ze5DIMqmLOKpg2yVlK/giphy.gif",      # մաֆիա / Boss Mafia
    Role.DOCTOR: "https://i.giphy.com/media/6xjato9VF2mWSzStXN/giphy.gif",        # բժիշկ / Doctor Pigeon
    Role.COMMISSAR: "https://i.giphy.com/media/26gsgWH4lnurglMWY/giphy.gif",      # կոմիսար / Reno 911
    Role.MANIAC: "https://i.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif",        # մոլագար / սարսափ
    Role.MISTRESS: "https://i.giphy.com/media/l0HlvtIPzPdt2usKs/giphy.gif",       # սիրուհի / պար
    Role.SERGEANT: "https://i.giphy.com/media/26gsgWH4lnurglMWY/giphy.gif",       # սերժանտ / Reno 911
    Role.LAWYER: "https://i.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif",        # իրավաբան / փաստաթուղթ
    Role.WANDERER: "https://i.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",       # թափառական / քայլ
    Role.KAMIKAZE: "https://i.giphy.com/media/26tPplGWjN0xLybiU/giphy.gif",       # կամիկաձե / պայթյուն
    Role.THIEF: "https://i.giphy.com/media/l3q2K5jinAlChoCLS/giphy.gif",          # գող / stealth
    Role.JOURNALIST: "https://i.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif",    # լրագրող
    Role.GUARD: "https://i.giphy.com/media/3oriO0OEd9QIDdllqo/giphy.gif",         # պահակ
    Role.ACCOUNTANT: "https://i.giphy.com/media/xT0xeJpnrWC4XWblEk/giphy.gif",    # հաշվապահ
    Role.SPY: "https://i.giphy.com/media/l0HlNQ03J5JxX6lva/giphy.gif",            # լրտես
    Role.TRAITOR: "https://i.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif",       # դավաճան
    Role.DISABLED: "https://i.giphy.com/media/l4FGuhL4U2WyjdkaY/giphy.gif",       # հաշմանդամ
    Role.JUDGE: "https://i.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",          # դատավոր
    Role.LUCKY: "https://i.giphy.com/media/hWk2jVZYz8x9A5rOnY/giphy.gif",        # հաջողակ / Mr Bean
}


# Դերերի գներ Telegram Stars-ով (XTR)
ROLE_PRICES = {
    Role.CITIZEN: 5,
    Role.MAFIA: 25,
    Role.MAFIA_SUB: 20,
    Role.DOCTOR: 22,
    Role.COMMISSAR: 25,
    Role.MANIAC: 30,
    Role.MISTRESS: 20,
    Role.SERGEANT: 15,
    Role.LAWYER: 18,
    Role.WANDERER: 15,
    Role.KAMIKAZE: 18,
    Role.THIEF: 20,
    Role.JOURNALIST: 15,
    Role.GUARD: 18,
    Role.ACCOUNTANT: 12,
    Role.SPY: 20,
    Role.TRAITOR: 22,
    Role.DISABLED: 12,
    Role.JUDGE: 18,
    Role.LUCKY: 22,
}

# Գնված դերեր՝ {user_id: [role_name, ...]} — կարող է ունենալ մի քանի
user_owned_roles = {}
# Խաղում օգտագործման սպասում՝ {user_id: role_name} (երբ խաղը սկսվում է)
pending_role_choice = {}
# Stars վիճակագրություն
stars_total_earned = 0  # ընդհանուր ստացված Stars
stars_purchases = []    # վերջին գնումներ՝ [{"user_id", "name", "username", "role", "stars", "time"}, ...]


#Class Game
class Game:
    def __init__(self):
        self.state = GameState.IDLE
        self.players = {}  # {user_id: {"name": str, "role": Role, "alive": bool, "private_chat": bool}}
        self.start_time = None
        self.night_count = 0
        self.mafia_votes = {}  # {user_id: voted_user_id}
        self.doctor_saves = {}  # {user_id: saved_user_id}
        self.commissar_checks = {}  # {user_id: checked_user_id}
        self.commissar_kills = {}  # {user_id: killed_user_id}
        self.maniac_kills = {}  # {user_id: killed_user_id}
        self.mistress_choices = {}  # {user_id: chosen_user_id}
        self.last_word_sent = set()  # Հետևել, թե ով է արդեն ուղարկել վերջին խոսքը
        self.votes = {}  # {user_id: voted_user_id or "none"}
        self.confirm_votes = {}  # {user_id: "like" or "dislike"} for kill confirmation
        self.language = "hy"  # Հայերեն
        self.registration_duration = 777
        self.registration_end_time = None  # Գրանցման ավարտի ժամանակ (datetime)
        self.night_duration = 30
        self.day_duration = 30
        self.voting_duration = 45
        self.confirm_duration = 30  # Duration for kill confirmation
        self.group_chat_id = None
        self.registration_message_id = None
        self.confirm_message_id = None  # Message ID for kill confirmation
        self.last_killed_id = None
        self.welcome_message_sent = {}  # {chat_id: bool}
        self.bot_creator_id = None
        self.bot_admins = []  # List of bot admin user IDs
        self.max_players = 20  # TrueMafiaBlack style - max 20 players
        self.mafia_chat = []  # List to store mafia chat messages
        self.lawyer_protections = {}  # {user_id: protected_user_id}
        self.wanderer_witness = {}  # {user_id: witnessed_user_id}
        self.kamikaze_targets = {}  # {user_id: target_user_id}
        self.thief_checks = {}  # {user_id: target_user_id} — այս գիշերվա գողության թիրախ
        self.thief_used = set()  # user_ids որոնք արդեն օգտագործել են Գողի ունակությունը (ամբողջ խաղում 1 անգամ)
        self.journalist_reveals = {}  # {user_id: revealed_user_id}
        self.guard_protections = {}  # {user_id: protected_user_id}
        self.accountant_checks = {}  # {user_id: bool}
        self.spy_observations = {}  # {user_id: observed_mafia_target_id}
        self.traitor_choices = {}  # {user_id: bool}
        self.disabled_blocks = {}  # {user_id: blocked_user_id}
        self.lucky_saved = set()  # user_ids որոնք արդեն օգտագործել են Հաջողակի փրկությունը
        self.active_roles = {role: True for role in Role}  # Դերերի ակտիվ/անջատված վիճակ
        self.mute_settings = {
            "killed": False,       # մահացածները
            "mistress": True,      # Սիրուհու զոհերը
            "sleeping": True,      # գիշերը (քնածները)
            "non_players": True,   # չխաղացողները
        }
        self.leave_duration = 30   # ելքի սահմանափակում
        self.muted_all = False     # /muteall — հաղորդագրությունները ջնջվում են
        self.hard_muted = False    # /dmute — set_chat_permissions

        # ================== ՍԻՐՈՒՀՈՒ ՆՈՐ ԴԱՇՏԵՐ (TrueMafia style) ==================
        self.mistress_blocked = None       # ով է արգելափակված (գիշեր + հաջորդ ցերեկ)
        self.last_mistress_target = None   # նախորդ գիշերվա թիրախը (կրկնությունը արգելելու համար)
        self.mistress_notified = set()     # ում արդեն ուղարկվել է արգելափակման հաղորդագրությունը (միայն 1 անգամ)

        # ================== ԲԺՇԿԻ ՆՈՐ ԴԱՇՏԵՐ ==================
        self.doctor_self_healed = False    # Բժիշկը արդեն օգտագործե՞լ է ինքն իրեն փրկելու իրավունքը (միայն 1 անգամ)

        # Մահացած / չխաղացողների ծանուցում (միայն 1 անգամ)
        self.non_player_notified = set()


# Multi-game support: each group has its own Game instance
games = {}  # {chat_id: Game}

# Բոտի հիմնադիր ID (փոխիր քո Telegram ID-ով)
bot_creator_id = 7639289885
# Բոտի ադմիններ — ավելացվում են միայն /setadmin հրամանով
bot_admins = []
# Արգելված օգտատերեր (չեն կարող խաղալ)
banned_users = set()
# Զգուշացումներ՝ {user_id: count}
user_warnings = {}
# Telegram-ում լռեցվածներ՝ {chat_id: set(user_ids)}
telegram_muted = {}
# Օգնություն սպասող օգտատերեր (անձնական չաթ)
help_awaiting = set()
# Բոտի գտնվող բոլոր խմբերը՝ {chat_id: {"title": str, "link": str, "creator_username": str, "creator_id": int, "creator_name": str}}
known_groups = {}
# Anti-spam՝ հրամանների սպամ — {user_id: [datetime, ...]}
command_spam_tracker = {}
# Anti-spam կարգավորումներ
SPAM_WINDOW_SECONDS = 10   # ժամանակային պատուհան
SPAM_MAX_COMMANDS = 5      # այսքան հրաման պատուհանում → mute
SPAM_MUTE_SECONDS = 300    # 5 րոպե mute
# Խմբերի սև ցուցակ — բոտը չի մտնի / դուրս կգա
blacklisted_groups = set()
# Դերերի կարգավորելի բաշխում՝ {player_count: [Role, ...]}
custom_role_setups = {}

# ================== ՏՎՅԱԼՆԵՐԻ ՊԱՀՊԱՆՈՒՄ ==================
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATA_FILE = os.path.join(DATA_DIR, "bot_data.json")
GAMES_FILE = os.path.join(DATA_DIR, "active_games.json")

# Օգտատիրոջ վիճակագրություն՝ {user_id: {"games": int, "wins": int, "name": str, "last_seen": str, "roles_played": {role_name: count}}}
user_stats = {}

# /rek — սպասում է բովանդակություն ուղարկելու (հիմնադիր/ադմին)
rek_awaiting = set()
# Բոտի բոլոր օգտատերեր (ովքեր /start են արել) — /rek-ի համար
known_users = set()
# Գնման էկրանի message_id — վճարումից հետո նույն հաղորդագրությունը խմբագրելու համար
pending_shop_msg = {}  # {user_id: message_id}
# Կրկնակի invoice-ից խուսափել
invoice_lock = set()  # user_ids որոնք հիմա invoice են ստանում

def _ensure_data_dir():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create data dir: {e}")

def save_data():
    """Պահպանել բոլոր կարևոր տվյալները JSON ֆայլում"""
    global bot_admins, banned_users, user_warnings, known_groups, blacklisted_groups, custom_role_setups, user_stats, user_owned_roles, stars_total_earned, stars_purchases, known_users
    try:
        _ensure_data_dir()
        # custom_role_setups-ում Role enum-ները պետք է string դարձնել
        serializable_roles = {}
        for n, roles in custom_role_setups.items():
            serializable_roles[str(n)] = [r.name if isinstance(r, Role) else str(r) for r in roles]

        data = {
            "bot_admins": list(bot_admins),
            "banned_users": list(banned_users),
            "user_warnings": {str(k): v for k, v in user_warnings.items()},
            "known_groups": {str(k): v for k, v in known_groups.items()},
            "blacklisted_groups": list(blacklisted_groups),
            "custom_role_setups": serializable_roles,
            "user_stats": {str(k): v for k, v in user_stats.items()},
            "user_owned_roles": {str(k): v for k, v in user_owned_roles.items()},
            "stars_total_earned": stars_total_earned,
            "stars_purchases": stars_purchases[-100:],  # վերջին 100-ը
            "known_users": list(known_users),
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Data saved successfully")
    except Exception as e:
        logger.error(f"Failed to save data: {e}")

def load_data():
    """Բեռնել տվյալները ֆայլից"""
    global bot_admins, banned_users, user_warnings, known_groups, blacklisted_groups, custom_role_setups, user_stats, user_owned_roles
    try:
        if not os.path.exists(DATA_FILE):
            logger.info("No saved data found, starting fresh")
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        bot_admins = list(data.get("bot_admins", []))
        banned_users = set(data.get("banned_users", []))
        user_warnings = {int(k): v for k, v in data.get("user_warnings", {}).items()}
        known_groups = {int(k): v for k, v in data.get("known_groups", {}).items()}
        blacklisted_groups = set(data.get("blacklisted_groups", []))

        # Վերականգնել custom_role_setups
        custom_role_setups.clear()
        for n_str, role_names in data.get("custom_role_setups", {}).items():
            try:
                n = int(n_str)
                roles = []
                for rn in role_names:
                    try:
                        roles.append(Role[rn])
                    except KeyError:
                        roles.append(Role.CITIZEN)
                custom_role_setups[n] = roles
            except Exception:
                pass

        user_stats = {int(k): v for k, v in data.get("user_stats", {}).items()}
        user_owned_roles = {int(k): list(v) for k, v in data.get("user_owned_roles", {}).items()}
        global stars_total_earned, stars_purchases, known_users
        stars_total_earned = int(data.get("stars_total_earned", 0))
        stars_purchases = list(data.get("stars_purchases", []))
        known_users = set(int(x) for x in data.get("known_users", []))
        # Համալրել known_users-ը գոյություն ունեցող աղբյուրներից
        known_users.update(user_stats.keys())
        known_users.update(user_owned_roles.keys())
        logger.info(f"Data loaded: {len(bot_admins)} admins, {len(banned_users)} banned, {len(user_stats)} user stats, {len(known_groups)} groups, {len(user_owned_roles)} owners, users={len(known_users)}, stars={stars_total_earned}")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")

def update_user_stat(user_id, name=None, won=False, role=None):
    """Թարմացնել օգտատիրոջ վիճակագրությունը"""
    global user_stats
    uid = int(user_id)
    if uid not in user_stats:
        user_stats[uid] = {
            "games": 0,
            "wins": 0,
            "name": name or str(uid),
            "last_seen": datetime.now().isoformat(),
            "roles_played": {},
        }
    st = user_stats[uid]
    st["games"] = st.get("games", 0) + 1
    if won:
        st["wins"] = st.get("wins", 0) + 1
    if name:
        st["name"] = name
    st["last_seen"] = datetime.now().isoformat()
    if role:
        role_name = role.name if isinstance(role, Role) else str(role)
        roles_played = st.get("roles_played", {})
        roles_played[role_name] = roles_played.get(role_name, 0) + 1
        st["roles_played"] = roles_played


def _serialize_role(role):
    if role is None:
        return None
    if isinstance(role, Role):
        return role.name
    return str(role)


def _deserialize_role(name):
    if name is None:
        return None
    try:
        return Role[name]
    except Exception:
        return Role.CITIZEN


def serialize_game(game):
    """Game օբյեկտը JSON-ի վերածել"""
    players = {}
    for uid, p in game.players.items():
        players[str(uid)] = {
            "name": p.get("name"),
            "role": _serialize_role(p.get("role")),
            "alive": p.get("alive", True),
            "private_chat": p.get("private_chat", False),
        }
    return {
        "state": game.state.name if game.state else "IDLE",
        "players": players,
        "start_time": game.start_time.isoformat() if game.start_time else None,
        "night_count": game.night_count,
        "language": game.language,
        "registration_duration": game.registration_duration,
        "night_duration": game.night_duration,
        "day_duration": game.day_duration,
        "voting_duration": game.voting_duration,
        "confirm_duration": game.confirm_duration,
        "group_chat_id": game.group_chat_id,
        "registration_message_id": game.registration_message_id,
        "max_players": game.max_players,
        "mistress_blocked": game.mistress_blocked,
        "last_mistress_target": game.last_mistress_target,
        "doctor_self_healed": game.doctor_self_healed,
        "muted_all": game.muted_all,
        "hard_muted": game.hard_muted,
        "mute_settings": game.mute_settings,
        "leave_duration": getattr(game, "leave_duration", 30),
        "saved_at": datetime.now().isoformat(),
    }


def deserialize_game(data):
    """JSON-ից Game օբյեկտ վերականգնել"""
    g = Game()
    try:
        g.state = GameState[data.get("state", "IDLE")]
    except Exception:
        g.state = GameState.IDLE
    players = {}
    for uid_str, p in data.get("players", {}).items():
        try:
            uid = int(uid_str)
            players[uid] = {
                "name": p.get("name", str(uid)),
                "role": _deserialize_role(p.get("role")),
                "alive": p.get("alive", True),
                "private_chat": p.get("private_chat", False),
            }
        except Exception:
            pass
    g.players = players
    if data.get("start_time"):
        try:
            g.start_time = datetime.fromisoformat(data["start_time"])
        except Exception:
            g.start_time = None
    g.night_count = data.get("night_count", 0)
    g.language = data.get("language", "hy")
    g.registration_duration = data.get("registration_duration", 777)
    g.night_duration = data.get("night_duration", 30)
    g.day_duration = data.get("day_duration", 30)
    g.voting_duration = data.get("voting_duration", 45)
    g.confirm_duration = data.get("confirm_duration", 30)
    g.group_chat_id = data.get("group_chat_id")
    g.registration_message_id = data.get("registration_message_id")
    g.max_players = data.get("max_players", 20)
    g.mistress_blocked = data.get("mistress_blocked")
    g.last_mistress_target = data.get("last_mistress_target")
    g.doctor_self_healed = data.get("doctor_self_healed", False)
    g.muted_all = data.get("muted_all", False)
    g.hard_muted = data.get("hard_muted", False)
    if data.get("mute_settings"):
        g.mute_settings = data["mute_settings"]
    g.leave_duration = data.get("leave_duration", 30)
    return g


def save_games():
    """Պահպանել բոլոր ակտիվ խաղերը"""
    try:
        _ensure_data_dir()
        active = {}
        for cid, g in games.items():
            if g.state != GameState.IDLE and g.players:
                active[str(cid)] = serialize_game(g)
        with open(GAMES_FILE, "w", encoding="utf-8") as f:
            json.dump(active, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(active)} active game(s)")
    except Exception as e:
        logger.error(f"Failed to save games: {e}")


def load_games():
    """Բեռնել ակտիվ խաղերը"""
    global games
    try:
        if not os.path.exists(GAMES_FILE):
            return 0
        with open(GAMES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for cid_str, gdata in data.items():
            try:
                cid = int(cid_str)
                g = deserialize_game(gdata)
                if g.state != GameState.IDLE and g.players:
                    games[cid] = g
                    count += 1
            except Exception as e:
                logger.error(f"Failed to load game {cid_str}: {e}")
        logger.info(f"Loaded {count} active game(s)")
        return count
    except Exception as e:
        logger.error(f"Failed to load games: {e}")
        return 0


DEFAULT_ROLE_SETUPS = {
    4: [Role.MAFIA, Role.DOCTOR, Role.COMMISSAR, Role.CITIZEN],
    5: [Role.MAFIA, Role.DOCTOR, Role.COMMISSAR, Role.CITIZEN, Role.CITIZEN],
    6: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.CITIZEN, Role.CITIZEN],
    7: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.CITIZEN, Role.CITIZEN],
    8: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.CITIZEN, Role.CITIZEN],
    9: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.CITIZEN, Role.CITIZEN],
    10: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.CITIZEN, Role.CITIZEN],
    11: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.CITIZEN, Role.CITIZEN],
    12: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN],
    13: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN],
    14: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN],
    15: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN],
    16: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN],
    17: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN],
    18: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN],
    19: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN],
    20: [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR, Role.MANIAC, Role.MISTRESS, Role.SERGEANT, Role.LAWYER, Role.WANDERER, Role.KAMIKAZE, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN, Role.CITIZEN],
}


def get_default_roles(n):
    if n in DEFAULT_ROLE_SETUPS:
        return list(DEFAULT_ROLE_SETUPS[n])
    return [Role.MAFIA, Role.MAFIA_SUB, Role.DOCTOR, Role.COMMISSAR] + [Role.CITIZEN] * max(0, n - 4)


def get_roles_for_count(n):
    """Վերադարձնում է դերերի ցանկ n խաղացողի համար (custom կամ default)"""
    if n in custom_role_setups:
        roles = list(custom_role_setups[n])
        while len(roles) < n:
            roles.append(Role.CITIZEN)
        return roles[:n]
    return get_default_roles(n)


def register_group_info(context, chat_id, chat=None):
    """Պահպանել/թարմացնել խմբի տվյալները known_groups-ում"""
    try:
        if chat is None:
            chat = context.bot.get_chat(chat_id)
        title = getattr(chat, "title", None) or "Անանուն խումբ"
        link = None
        try:
            link = context.bot.export_chat_invite_link(chat_id)
        except Exception:
            link = getattr(chat, "invite_link", None) or getattr(chat, "username", None)
            if link and not str(link).startswith("http"):
                link = f"https://t.me/{link}"
        if not link:
            link = f"(մասնավոր խումբ, chat_id: {chat_id})"

        creator_username = "—"
        creator_name = "—"
        creator_id = None
        try:
            admins = context.bot.get_chat_administrators(chat_id)
            for adm in admins:
                if adm.status == "creator":
                    creator_id = adm.user.id
                    creator_name = adm.user.full_name or "—"
                    creator_username = f"@{adm.user.username}" if adm.user.username else "—"
                    break
        except Exception:
            pass

        known_groups[chat_id] = {
            "title": title,
            "link": link,
            "creator_username": creator_username,
            "creator_id": creator_id,
            "creator_name": creator_name,
        }
        return known_groups[chat_id]
    except Exception as e:
        logger.error(f"register_group_info failed for {chat_id}: {e}")
        return None


def get_game(chat_id):
    """Ստանալ կամ ստեղծել խաղ տվյալ խմբի համար"""
    if chat_id not in games:
        games[chat_id] = Game()
        games[chat_id].group_chat_id = chat_id
    return games[chat_id]

def find_game_by_user(user_id):
    """Գտնել այն խաղը, որտեղ օգտատերը խաղում է (անձնական հաղորդագրությունների համար)"""
    for chat_id, g in games.items():
        if user_id in g.players and g.state != GameState.IDLE:
            return g
    return None

def get_all_active_games():
    return {cid: g for cid, g in games.items() if g.state != GameState.IDLE}

# Language texts
def get_text(key, lang="hy"):
    texts = {
        "start_message": {
            "hy": "Ողջո՛ւյն։Ես @ArmeniaMafia_Bot բոտ-խաղավարն եմ 🤵🏻 Մաֆիա խաղի համար։ Խաղը խմբում սկսելու համար ավելացրեք ինձ խումբ և տվեք ադմինի թույլտվություններ , կապ հիմնադիրի հետ /creator:)"
        },
        "welcome_message": {
            "hy": "Ողջո՛ւյն։\nԵս @ArmeniaMafia_Bot բոտ-խաղավարն եմ 🤵🏻 Մաֆիա խաղի համար։\nԽաղը սկսելու համար ինձ տվեք հետևյալ ադմինիստրատիվ թույլտվությունները՝\n☑️ ջնջել հաղորդագրություններ\n☑️ արգելափակել օգտատերեր\n☑️ ամրացնել հաղորդագրություններ"
        },
        "game_created": {
            "hy": "Խաղի գրանցումը սկսված է"
        },
        "registered_players": {
            "hy": "Գրանցված են:\n@{}"
        },
        "registration_confirmation": {
            "hy": "Դուք միացել եք խաղին"
        },
        "game_started": {
            "hy": "Խաղը սկսվում է! Մի քանի վայրկյանում բոտը ձեզ անձնական հաղորդագրություն կուղարկի դերի և դրա նկարագրության մասին:"
        },
        "role_assigned": {
            "hy": "Դու {} ես"
        },
        "view_role_button": {
            "hy": "Դիտել դերը"
        },
        "night_message": {
            "hy": "🌃 Մութն ընկնում է\nՔաղաք դուրս են գալիս միայն անվախները։ Առավոտյան կփորձենք հաշվել նրանց գլուխները..."
        },
        "go_to_bot_button": {
            "hy": "Անցնել բոտի մոտ"
        },
        "night_ended": {
            "hy": "🏙 Ցերեկ {}\nԴուրս եկավ արևը՝ չորացնելով փողոցներում թափված արյունը..."
        },
        "day_message": {
            "hy": "Ողջ խաղացողներ.\n{}"
        },
        "voting_message": {
            "hy": "Ժամանակն է գտնել և պատժել մեղավորներին: Քվեարկությունը կտևի 45 վայրկյան"
        },
        "vote_button": {
            "hy": "Քվեարկել"
        },
        "vote_result": {
            "hy": "👹 {} քվեարկել է {} դեմ:"
        },
        "vote_result_none": {
            "hy": "Բնակիչների կարծիքները հավասարեցին ({} 👍 | {} 👎)...\nԲնակիչները որոշեցին այսպես էլ ոչ ոքի կախաղան չհանելով..."
        },
        "confirm_kill_message": {
            "hy": "Վստա՞հ եք, որ ուզում եք սպանել {}-ին"
        },
        "player_killed": {
            "hy": "{} սպանվել է (դեր՝ {})\nՍպանող՝ {}"
        },
        "no_kill": {
            "hy": "🤷 Զարմանալի է, բայց այս գիշեր զոհեր չկան"
        },
        "no_voted_out": {
            "hy": "Բնակիչների կարծիքները հավասարեցին (0 👍 | 0 👎)...\nԲնակիչները որոշեցին այսպես էլ ոչ ոքի կախաղան չհանելով..."
        },
        "day_timer": {
            "hy": "Քննարկմանը մնացել է {} ր. {} վրկ."
        },
        "mistress_action_group": {
            "hy": "💃 Սիրուհին արդեն սպասում է ինչ-որ մեկի այցին..."
        },
        "commissar_action_group": {
            "hy": "🕵️‍♂️ Կոմիսար Կատտանին գնաց չարագործներին փնտրելու..."
        },
        "wanderer_action_group": {
            "hy": "🧙‍♀️ Թափառականը գնաց ինչ-որ մեկի մոտ 2ժի ետևից..."
        },
        "doctor_action_group": {
            "hy": "👨‍⚕️ Բժիշկը դուրս եկավ գիշերային հերթապահության..."
        },
        "mafia_action_group": {
            "hy": "🤵🏻 Մաֆիան ընտրեց զոհին..."
        },
        "maniac_action_group": {
            "hy": "🪓 Մոլագարը ընտրեց զոհին..."
        },
        "game_over": {
            "hy": "Խաղն ավարտված է!\nՀաղթեց {}\n\nՀաղթողներ:\n{}\n\nՄնացած մասնակիցներ:\n{}\n\nԽաղը տևեց {} ր. {} վրկ."
        },
        "game_over_one_mafia_one_citizen": {
            "hy": "Խաղն ավարտված է!\nՀաղթեց Մաֆիան\n\nՀաղթողներ:\n{}\n\nՄնացած մասնակիցներ:\n{}\n\nԽաղը տևեց {} ր. {} վրկ."
        },
        "game_over_citizens_win": {
            "hy": "Խաղն ավարտված է!\nՀաղթեցին Խաղաղ բնակիչները\n\nՀաղթողներ:\n{}\n\nՄնացած մասնակիցներ:\n{}\n\nԽաղը տևեց {} ր. {} վրկ."
        },
        "game_over_maniac_wins": {
            "hy": "Խաղն ավարտված է!\nՀաղթեց Մոլագարը\n\nՀաղթողներ:\n{}\n\nՄնացած մասնակիցներ:\n{}\n\nԽաղը տևեց {} ր. {} վրկ."
        },
        "game_stopped_insufficient_players": {
            "hy": "Խաղը կանգնեցված է, քանի որ խաղացողների թիվը 2-ից պակաս է:"
        },
        "mafia_action": {
            "hy": "🤵🏻 Դոն, ընտրեք Ձեր զոհին:\nՄաֆիայի անդամներ՝ {}"
        },
        "mafia_sub_action": {
            "hy": "🤵🏻 Մաֆիա, ընտրեք Ձեր զոհին:\nՄաֆիայի անդամներ՝ {}"
        },
        "doctor_action": {
            "hy": "👨🏼‍⚕️ Բժիշկ, ընտրեք, ում փրկել:"
        },
        "commissar_action": {
            "hy": "👮‍♂️ Կոմիսար, ընտրեք՝ ստուգել կամ սպանել:"
        },
        "commissar_check": {
            "hy": "👮‍♂️ Կոմիսար, ընտրեք, ում դերը ստուգել:"
        },
        "commissar_kill": {
            "hy": "👮‍♂️ Կոմիսար, ընտրեք, ում սպանել:"
        },
        "maniac_action": {
            "hy": "🪓 Մոլագար, ընտրեք Ձեր զոհին:"
        },
        "mistress_action": {
            "hy": "💃 Սիրուհի, ընտրեք, ում վնասազերծել մեկ օրով (գիշեր + հաջորդ ցերեկ):"
        },
        "sergeant_action": {
            "hy": "👮‍♀️ Սերժանտ, դուք Կոմիսար Կատտանիի օգնականն եք: Կոմիսարը կտեղեկացնի Ձեզ իր գործողությունների մասին:"
        },
        "lawyer_action": {
            "hy": "🧑🏼‍💼 Իրավաբան, ընտրեք, ում պաշտպանել: Եթե ընտրեք մաֆիային, Կոմիսարը կտեսնի նրան որպես խաղաղ բնակիչ:"
        },
        "wanderer_action": {
            "hy": "//‍♀️ Թափառական, ընտրեք, ում մոտ գնալ՝ սպանություն ականատես լինելու համար:"
        },
        "kamikaze_action": {
            "hy": "💣 Կամիկաձե, եթե Ձեզ փորձեն կախաղան հանել, ընտրեք, ում տանել Ձեզ հետ:"
        },
        "commissar_result": {
            "hy": "{} - {}:"
        },
        "mafia_sub_message": {
            "hy": "🤵🏻 Դուք կարող եք խոսել Դոնի հետ։ Դոն՝ {}"
        },
        "mafia_chat_message": {
            "hy": "{}: {}"
        },
        "sergeant_notification": {
            "hy": "👮‍♀️ Կոմիսարը {} գործողություն է կատարել՝ {}:"
        },
        "lawyer_action_group": {
            "hy": "🧑🏼‍💼 Իրավաբանը պաշտպանեց ինչ-որ մեկին..."
        },
        "wanderer_witnessed": {
            "hy": "//‍♀️ Դուք ականատես եղաք, որ {} սպանվել է {} կողմից:"
        },
        "kamikaze_triggered": {
            "hy": "💣 Կամիկաձե {} վերցրեց {} իր հետ:"
        },
        "no_players_start_night": {
            "hy": "Ոչ ոք չի գրանցվել: Խաղը կանգնեցված է:"
        },
        "chat_not_allowed": {
            "hy": "Դուք չեք կարող գրել խմբում, քանի որ խաղի մասնակից չեք կամ մահացել եք:"
        },
        "chat_not_allowed_night": {
            "hy": "🛑 Ձեր հաղորդագրությունը ջնջվել է:\nԳիշեր է, խմբում գրելն արգելված է:"
        },
        "chat_question_allowed": {
            "hy": "Մահացած կամ խաղում չգտնվող օգտատերերը կարող են գրել միայն '?' նշանով սկսվող հաղորդագրություններ:"
        },
        "player_removed_no_private": {
            "hy": "{} հեռացվել է խաղից, քանի որ չի սկսել անձնական զրույց @ArmeniaMafia_Bot-ի հետ:"
        },
        "registration_extended": {
            "hy": "Գրանցման ժամանակը երկարացվել է {} վայրկյանով:"
        },
        "voting_extended": {
            "hy": "Քվեարկության ժամանակը երկարացվել է 30 վայրկյանով:"
        },
        "extend_not_allowed": {
            "hy": "Երկարացումը հնարավոր է միայն գրանցման կամ քվեարկության ժամանակ:"
        },
        "extend_usage": {
            "hy": "Օգտագործեք /extend <վայրկյաններ>, օրինակ՝ /extend 300"
        },
        "extend_invalid_duration": {
            "hy": "Ժամանակը պետք է լինի դրական թիվ, առնվազն 10 վայրկյան:"
        },
        "set_durations": {
            "hy": "Ժամանակի կարգավորում՝ /setdurations <գրանցում> <գիշեր> <ցերեկ> <քվեարկություն> (վայրկյաններով, օր.՝ /setdurations 60 30 30 45)"
        },
        "durations_updated": {
            "hy": "Ժամանակները թարմացվել են՝ գրանցում: {} վրկ, գիշեր: {} վրկ, ցերեկ: {} վրկ, քվեարկություն: {} վրկ"
        },
        "duration_error": {
            "hy": "Ժամանակները պետք է լինեն առնվազն 10 վայրկյան:"
        },
        "duration_value_error": {
            "hy": "Խնդրում ենք մուտքագրել ճիշտ թվեր (օր.՝ /setdurations 60 30 30 45):"
        },
        "private_chat_warning": {
            "hy": "⚠️ {} խնդրում ենք սկսել անձնական զրույց @ArmeniaMafia_Bot-ի հետ:"
        },
        "action_accepted": {
            "hy": "Գործողությունն ընդունված է:"
        },
        "action_failed": {
            "hy": "Գործողությունը ձախողվել է, փորձեք կրկին:"
        },
        "game_already_started": {
            "hy": "Խաղն արդեն սկսված է կամ ընթանում է:"
        },
        "not_enough_players": {
            "hy": "Խաղի կանոնների համաձայն՝ անհրաժեշտ է առնվազն 4 խաղացող:"
        },
        "max_players_reached": {
            "hy": "Հասել եք առավելագույն խաղացողների թվին (20): Խաղը ավտոմատ կսկսվի:"
        },
        "game_not_started": {
            "hy": "Խաղը դեռ սկսված չէ:"
        },
        "player_left": {
            "hy": "Դու լքել ես խաղը:"
        },
        "game_stopped": {
            "hy": "Խաղը չեղարկված է:"
        },
        "vote_none": {
            "hy": "Դուք քվեարկել եք Ոչ ոքի դեմ:"
        },
        "last_word_prompt": {
            "hy": "Քեզ սպանեցին ։(\nԴուք կարող եք ուղարկել Ձեր վերջին խոսքը այստեղ։"
        },
        "last_word_message": {
            "hy": "Բնակիչներից ինչ-որ մեկը լսել է , թե ինչպես է {} բղավել մահից առաջ:\n{}"
        },
        "status_message": {
            "hy": "🎮 Խաղի վիճակ՝ {}\nԿենդանի խաղացողներ՝ {}\nԸնթացիկ փուլ՝ {}"
        },
        "last_word_sent": {
            "hy": "Ձեր վերջին խոսքն ուղարկվել է խմբում:"
        },
        "last_word_already_sent": {
            "hy": "Դուք արդեն ուղարկել եք Ձեր վերջին խոսքը։ Այլևս չեք կարող գրել։"
        },
        "roles_message": {
            "hy": "Դերերի բաշխում՝\n{}"
        },
        "all_roles_message": {
            "hy": "Բոլոր խաղացողների դերերը՝\n{}"
        },
        "rules_message": {
            "hy": "📜 **Խաղի կանոններ**:\n\n"
                  "1. **Խաղի նպատակ**:\n"
                  "   - Խաղաղ բնակիչները փորձում են բացահայտել և վերացնել մաֆիային:\n"
                  "   - Մաֆիան փորձում է սպանել խաղաղ բնակիչներին՝ թաքնվելով նրանց մեջ:\n"
                  "   - Մոլագարը (Սերիական մարդասպան) գործում է միայնակ և կարող է սպանել ցանկացած խաղացողի:\n"
                  "   - Սիրուհին խանգարում է խաղացողի գործողությունները գիշերային փուլում + հաջորդ ցերեկ:\n\n"
                  "2. **Դերեր**:\n"
                  "   - **Խաղաղ բնակիչ**: Քվեարկում է ցերեկային փուլում մաֆիային բացահայտելու համար:\n"
                  "   - **Դոն/Մաֆիա**: Գիշերային փուլում ընտրում է զոհին: Չեն կարող սպանել միմյանց:\n"
                  "   - **Բժիշկ**: Գիշերային փուլում ընտրում է մեկ խաղացողի՝ փրկելու համար:\n"
                  "   - **Կոմիսար**: Երկրորդ գիշերից սկսած կարող է ընտրել՝ ստուգել խաղացողի դերը կամ սպանել նրան:\n"
                  "   - **Մոլագար**: Ամեն գիշեր սպանում է մեկ խաղացողի, չի պատկանում որևէ թիմի:\n"
                  "   - **Սիրուհի**: Գիշերային փուլում ընտրում է խաղացողի, ում գործողությունները խանգարում է (գիշեր + հաջորդ ցերեկ):\n"
                  "   - **Սերժանտ**: Կոմիսարի օգնականն է: Կոմիսարի մահից հետո դառնում է Կոմիսար:\n"
                  "   - **Իրավաբան**: Պաշտպանում է խաղացողին գիշերային փուլում: Եթե ընտրեք մաֆիային, Կոմիսարը տեսնում է նրան որպես խաղաղ բնակիչ:\n"
                  "   - **Թափառական**: Գիշերային փուլում կարող է ականատես լինել սպանությանը:\n"
                  "   - **Կամիկաձե**: Եթե քվեարկությամբ փորձեն վերացնել, կարող է մեկ խաղացողի տանել իր հետ:\n\n"
                  "3. **Խաղի փուլեր**:\n"
                  "   - **Գրանցում**: Խաղացողները գրանցվում են խաղին միանալու համար (առավելագույնը 30 խաղացող):\n"
                  "   - **Գիշեր**: Մաֆիան, Բժիշկը, Կոմիսարը, Մոլագարը, Սիրուհին և այլն կատարում են իրենց գործողությունները:\n"
                  "   - **Ցերեկ**: Խաղացողները քննարկում են և քվեարկում՝ վերացնելու կասկածյալին:\n"
                  "   - **Քվեարկություն**: Խաղացողները քվեարկում են՝ ընտրելու, թե ում վերացնել:\n"
                  "   - **Հաստատում**: Քվեարկության արդյունքում ընտրված խաղացողի հեռացումը հաստատվում է Like/Dislike քվեարկությամբ:\n"
                  "   - **Վերջին խոսք**: Սպանված խաղացողը կարող է ուղարկել վերջին հաղորդագրություն:\n\n"
                  "4. **Հաղթանակի պայմաններ**:\n"
                  "   - Խաղը ավարտվում է, եթե մնում է 1 մաֆիա և 1 խաղաղ բնակիչ (հաղթում է մաֆիան):\n"
                  "   - Եթե մաֆիան հավասարվում կամ գերազանցում է խաղաղ բնակիչներին, հաղթում է մաֆիան:\n"
                  "   - Եթե բոլոր մաֆիաները վերացվում են, հաղթում են խաղաղ բնակիչները:\n"
                  "   - Մոլագարը հաղթում է, եթե մնում է միայնակ:\n\n"
                  "5. **Լրացուցիչ**:\n"
                  "   - Խաղը սկսվում է /go հրամանով կամ ավտոմատ, եթե գրանցվում է 30 խաղացող:\n"
                  "   - Գիշերային փուլում խմբում գրելն արգելվում է:\n"
                  "   - Սպանված խաղացողի վերջին խոսքը խմբում հայտնվում է անմիջապես:"
        },
        "help_message": {
            "hy": "Հասանելի հրամաններ՝\n/create — սկսել գրանցումը\n/go — սկսել խաղը\n/stop — կանգնեցնել խաղը\n/leave — լքել խաղը\n/extend <վայրկյաններ> — երկարացնել գրանցումը\n/rules — ցուցադրել խաղի կանոնները\n/settings — կարգավորումներ (դերեր, ժամանակներ, խոսք)\n/time — գրանցման մնացած ժամանակը"
        },
        "only_bot_admin": {
            "hy": "❌ Այս հրամանը կարող է օգտագործել միայն բոտի ադմինը կամ հիմնադիրը։"
        },
        "kick_success": {
            "hy": "{} հեռացվել է խաղից:"
        },
        "kick_not_found": {
            "hy": "Օգտատերը չի գտնվել խաղացողների ցուցակում:"
        },
        "kick_not_admin": {
            "hy": "Այս հրամանը կարող են օգտագործել միայն ադմինները կամ բոտի հիմնադիրը:"
        },
        "not_admin": {
            "hy": "Այս հրամանը կարող են օգտագործել միայն խմբի ադմինները, բոտի ադմինները կամ բոտի հիմնադիրը:"
        },
        "doctor_visited": {
            "hy": "👨🏼‍⚕️ Բժիշկը հյուր էր եկել"
        },
        "doctor_saved": {
            "hy": "👨🏼‍⚕️ Բժիշկը բուժեց քեզ"
        },
        "commissar_checked": {
            "hy": "Ինչ-որ մեկը շատ հետաքրքրված է քո դերով..."
        },
        "mistress_blocked": {
            "hy": "💃 Սիրուհին խանգարել է Ձեր գիշերային գործողությունները:"
        },
        "mistress_blocked_chat": {
            "hy": "💃 Սիրուհին խանգարել է Ձեզ։ Այս ցերեկը չեք կարող գրել խմբում։"
        },
        "mistress_blocked_vote": {
            "hy": "💃 Սիրուհին խանգարել է Ձեր քվեարկությունը։"
        },
        "mistress_same_target": {
            "hy": "Նույն խաղացողին հաջորդ գիշեր չես կարող ընտրել։"
        },
        "setcreator_success": {
            "hy": "Դուք այժմ @ArmeniaMafia_Bot-ի հիմնադիրն եք:"
        },
        "setcreator_already_set": {
            "hy": "Հիմնադիրը արդեն սահմանված է:"
        },
        "setadmin_success": {
            "hy": "{} նշանակվել է բոտի ադմին:"
        },
        "setadmin_not_found": {
            "hy": "Օգտատերը չի գտնվել խաղացողների ցուցակում:"
        },
        "setadmin_usage": {
            "hy": "Օգտագործեք /setadmin <օգտանուն>, օրինակ՝ /setadmin @Username"
        },
        "broadcast_usage": {
            "hy": "Օգտագործեք /broadcast <հաղորդագրություն>, օրինակ՝ /broadcast Բարև, բոլորին!"
        },
        "broadcast_sent": {
            "hy": "Հաղորդագրությունն ուղարկվել է բոլոր խաղացողներին:"
        },
        "not_creator": {
            "hy": "Այս հրամանը կարող է օգտագործել միայն բոտի հիմնադիրը:"
        },
        "thief_action": {
            "hy": "🦹 Գող, ընտրեք, ում դերը գողանալ (ամբողջ խաղում միայն 1 անգամ):\nԹիրախը կդառնա Խաղաղ բնակիչ, դու կդառնաս նրա դերը։"
        },
        "journalist_action": {
            "hy": "📰 Լրագրող, ընտրեք, ում դերը բացահայտել խմբում:"
        },
        "guard_action": {
            "hy": "🛡️ Պահակ, ընտրեք, ում պաշտպանել մաֆիայի սպանությունից:"
        },
        "accountant_action": {
            "hy": "📊 Հաշվապահ, ցանկանու՞մ եք իմանալ, թե քանի մաֆիա է մնացել:"
        },
        "spy_action": {
            "hy": "🕴️ Լրտես, ընտրեք, ում մաֆիայի ընտրությունը տեսնել:"
        },
        "traitor_action": {
            "hy": "🗡️ Դավաճան, ցանկանու՞մ եք միանալ մաֆիային:"
        },
        "disabled_action": {
            "hy": "♿ Հաշմանդամ, ընտրեք, ում քվեարկությունը արգելափակել:"
        },
        "thief_result": {
            "hy": "🦹 Դու գողացիր {1}-ի դերը ({0})։\nՆա այժմ Խաղաղ բնակիչ է, դու այժմ՝ {0}։"
        },
        "thief_stolen_from": {
            "hy": "🦹 Քո դերը գողացել են։ Այժմ դու Խաղաղ բնակիչ ես։"
        },
        "thief_already_used": {
            "hy": "🦹 Դու արդեն օգտագործել ես գողությունը այս խաղում։"
        },
        "lucky_saved": {
            "hy": "🍀 Հաջողակը փրկվեց գիշերային սպանությունից։"
        },
        "lucky_saved_private": {
            "hy": "🍀 Քո հաջողությունը փրկեց քեզ։ Այլևս չես կարող փրկվել։"
        },
        "journalist_reveal": {
            "hy": "📰 Լրագրողը բացահայտեց, որ {} ունի {} դեր:"
        },
        "guard_protected": {
            "hy": "🛡️ Պահակը պաշտպանեց Ձեզ:"
        },
        "accountant_result": {
            "hy": "📊 Խաղում մնացել է {} մաֆիա:"
        },
        "spy_result": {
            "hy": "🕴️ Լրտեսը տեսավ, որ մաֆիան ընտրել է {}:"
        },
        "traitor_joined": {
            "hy": "🗡️ Դավաճանը միացավ մաֆիային:"
        },
        "disabled_blocked": {
            "hy": "♿ Ձեր քվեարկությունը արգելափակվել է Հաշմանդամի կողմից:"
        },
        "thief_action_group": {
            "hy": "🦹 Գողը ինչ-որ մեկի դերն է գողանում..."
        },
        "journalist_action_group": {
            "hy": "📰 Լրագրողը պատրաստվում է բացահայտման..."
        },
        "guard_action_group": {
            "hy": "🛡️ Պահակը սկսեց պաշտպանություն..."
        },
        "accountant_action_group": {
            "hy": "📊 Հաշվապահը սկսեց հաշվարկ..."
        },
        "spy_action_group": {
            "hy": "🕴️ Լրտեսը սկսեց հետևել..."
        },
        "traitor_action_group": {
            "hy": "🗡️ Դավաճանը կայացրեց որոշում..."
        },
        "disabled_action_group": {
            "hy": "♿ Հաշմանդամը արգելափակեց ինչ-որ մեկին..."
        },
        "mistress_notification": {
            "hy": "Ինձ հետ մոռացիր ամեն ինչ... - երգում էր 💃🏼 Սիրուհի"
        },
        "player_left_group": {
            "hy": " {} չդիմացավ քաղաքի ճնշող մթնոլորտին և հեռացավ: Նա {} էր:"
        }
    }
    return texts.get(key, {}).get(lang, key)


def delete_message(context, chat_id, message_id):
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Հաղորդագրություն {message_id} ջնջվել է չատ {chat_id}-ում")
    except Exception as e:
        logger.error(f"Հաղորդագրություն {message_id} ջնջելը ձախողվել է չատ {chat_id}-ում: {e}")


def is_bot_admin(user_id):
    """Ստուգում է՝ միայն բոտի հիմնադիր կամ բոտի ադմին (խմբի ադմին չի հաշվվում)"""
    global bot_creator_id, bot_admins
    if bot_creator_id is not None and user_id == bot_creator_id:
        return True
    if user_id in bot_admins:
        return True
    return False


def is_admin_or_creator(context, chat_id, user_id):
    """Ստուգում է՝ խմբի ադմին, բոտի ադմին, թե բոտի հիմնադիր"""
    global bot_creator_id, bot_admins
    try:
        if is_bot_admin(user_id):
            return True
        # Խմբի ադմին / հիմնադիր
        chat_member = context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['administrator', 'creator']
    except Exception as e:
        logger.error(f"Failed to check admin status for user %s in chat %s: %s", user_id, chat_id, e)
        return False


def is_mistress_blocked(user_id, game=None):
    """Ստուգում է՝ արդյոք խաղացողը արգելափակված է Սիրուհու կողմից"""
    if game is None:
        game = find_game_by_user(user_id)
    if not game:
        return False
    return game.mistress_blocked is not None and user_id == game.mistress_blocked


def start(update, context):
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type

    # Գրանցել օգտատիրոջը known_users-ում (/rek-ի համար)
    if user_id not in known_users:
        known_users.add(user_id)
        try:
            save_data()
        except Exception:
            pass

    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # /start աշխատում է միայն անձնական չաթում
    if chat_type != "private":
        try:
            context.bot.send_message(chat_id=chat_id, text="❌ /start հրամանը աշխատում է միայն անձնական չաթում։")
        except Exception:
            pass
        return

    # ===== JOIN LOGIC: /start join_CHATID =====
    if context.args and str(context.args[0]).startswith("join"):
        try:
            parts = str(context.args[0]).split("_", 1)
            group_chat_id = None
            if len(parts) == 2 and parts[1].lstrip("-").isdigit():
                group_chat_id = int(parts[1])
            else:
                # fallback — գտնել ցանկացած active registration
                for cid, g in games.items():
                    if g.state == GameState.REGISTRATION:
                        group_chat_id = cid
                        break

            if group_chat_id is None:
                context.bot.send_message(chat_id=user_id, text="❌ Գրանցում չի ընթանում։")
                return

            game = get_game(group_chat_id)

            if game.state != GameState.REGISTRATION:
                context.bot.send_message(chat_id=user_id, text="❌ Գրանցում չի ընթանում այս խմբում։")
                return
            if user_id in banned_users:
                context.bot.send_message(chat_id=user_id, text="🚫 Դու արգելափակված ես և չես կարող խաղալ։")
                return
            if user_id in game.players:
                context.bot.send_message(chat_id=user_id, text="✅ Դու արդեն գրանցված ես խաղին։")
                return
            if len(game.players) >= game.max_players:
                context.bot.send_message(chat_id=user_id, text="❌ Խաղը լրիվ է։")
                return

            player_name = update.effective_user.full_name
            game.players[user_id] = {"name": player_name, "role": None, "alive": True, "private_chat": True}
            context.bot.send_message(chat_id=user_id, text=f"✅ Դու միացել ես խաղին — {player_name}")

            # Եթե ունի գնված/տրված սուպեր դերեր — առաջարկել օգտագործել
            owned = user_owned_roles.get(user_id, [])
            if owned:
                try:
                    lines = ["⭐ <b>Սուպեր դեր</b>\n", "Ունես սուպեր դեր(եր). Ընտրիր՝ օգտագործե՞լ այս խաղում.\n"]
                    keyboard = []
                    for rn in owned:
                        try:
                            r = Role[rn]
                            keyboard.append([InlineKeyboardButton(
                                f"✅ Օգտագործել {r.value}",
                                callback_data=f"use_role_yes_{group_chat_id}_{rn}"
                            )])
                        except Exception:
                            pass
                    keyboard.append([InlineKeyboardButton(
                        "🎲 Չօգտագործել (պատահական դեր)",
                        callback_data=f"use_role_no_{group_chat_id}_none"
                    )])
                    context.bot.send_message(
                        chat_id=user_id,
                        text="\n".join(lines),
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to offer super roles: {e}")

            # Update group registration message
            if game.group_chat_id and game.registration_message_id:
                players_list = "\n".join([
                    f'{i+1}. <a href="tg://user?id={uid}">{p["name"]}</a>'
                    for i, (uid, p) in enumerate(game.players.items())
                ])
                try:
                    context.bot.edit_message_text(
                        chat_id=game.group_chat_id,
                        message_id=game.registration_message_id,
                        text=f"{get_text('registered_players', game.language)}{players_list}\n\nՍեղմեք գրանցվելու համար:",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Միանալ", url=f"http://t.me/ArmeniaMafia_Bot?start=join_{game.group_chat_id}")]]),
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Failed to update registration message: %s", e)

            if len(game.players) >= game.max_players:
                try:
                    context.bot.send_message(chat_id=game.group_chat_id, text=get_text("max_players_reached", game.language))
                    end_registration(context, game.group_chat_id)
                except Exception as e:
                    logger.error(f"Failed max players: {e}")
            return
        except Exception as e:
            logger.error(f"Failed join for user %s: %s", user_id, e)
            return

    # Սովորական /start — գլխավոր մենյու
    try:
        keyboard = [
            [
                InlineKeyboardButton("🎮 Ավելացնել խմբում", url="http://t.me/ArmeniaMafia_Bot?startgroup=true"),
                InlineKeyboardButton("💬 Մուտք չատ", url="https://t.me/+37fKHd7KvgEyMjI6"),
            ],
            [
                InlineKeyboardButton("🎭 Դերեր", callback_data="show_roles"),
                InlineKeyboardButton("⭐ Գնել դեր", callback_data="buy_roles_menu"),
            ],
            [
                InlineKeyboardButton("🆘 Օգնություն", callback_data="help_contact"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=chat_id,
            text=get_text("start_message", "hy"),
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to send start message: {e}")


# Դերերի ցուցադրում և նկարագրություն
def show_roles(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton(role.value, callback_data=f"role_info_{role.name}")]
        for role in Role
    ]
    keyboard.append([InlineKeyboardButton("Հետ գնալ", callback_data="back_to_start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        query.message.edit_text(
            text="Ընտրեք դերը՝ տեսնելու նրա նկարագրությունը:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to show roles: %s", e)


def role_info(update, context):
    query = update.callback_query
    role_name = query.data.split("_")[2]
    role = Role[role_name]
    role_descriptions = {
        Role.CITIZEN: "Միրնի բնակիչ։ Գիշերը քնում է, ցերեկը փորձում է գտնել և կախաղան հանել մաֆիային։",
        Role.MAFIA: "Դոն — մաֆիայի ղեկավար։ Գիշերը ընտանիքի հետ ընտրում է զոհին և կատարում դատավճիռը։",
        Role.MAFIA_SUB: "Մաֆիա։ Գիշերը ընտանիքի հետ ընտրում է զոհին։ Եթե Դոնը մեռնում է — կարող է դառնալ նոր Դոն։",
        Role.DOCTOR: "Բժիշկ։ Գիշերը կարող է գնալ մեկ խաղացողի մոտ և փրկել նրա կյանքը։ Ինքն իրեն կարող է փրկել միայն 1 անգամ։",
        Role.COMMISSAR: "Կոմիսար Կատտանի։ Գիշերը կարող է կամ իմանալ մեկ խաղացողի դերը, կամ սպանել նրան։",
        Role.MANIAC: "Մոլագար։ Ամեն գիշեր սպանում է մեկ խաղացողի։ Նպատակը — սպանել բոլորին և մնալ միայնակ։",
        Role.MISTRESS: "Սիրուհի։ Գիշերը կարող է շեղել ցանկացած խաղացողի (եթե ինքը զոհ չէ)։ Նրա զոհը չի գործում ամբողջ գիշեր և հաջորդ ցերեկ։",
        Role.SERGEANT: "Սերժանտ։ Կոմիսարի օգնական։ Իմանում է Կոմիսարի բոլոր ստուգումների մասին, իսկ Կոմիսարի մահից հետո դառնում է նոր Կոմիսար։",
        Role.LAWYER: "Ադվոկատ։ Գիշերը ընտրում է պաշտպանյալ։ Եթե Կոմիսարը ստուգում է նրան — տեսնում է որպես միրնի բնակիչ։",
        Role.WANDERER: "Թափառական (Բոմժ)։ Գիշերը կարող է գնալ մեկի մոտ և տեսնել, թե ով է սպանել նրան։",
        Role.KAMIKAZE: "Կամիկաձե։ Եթե նրան կախաղան են հանում — կարող է մեկ խաղացողի տանել իր հետ։",
        Role.THIEF: "Գող։ Ամբողջ խաղում 1 անգամ գիշերը գողանում է մեկի դերը — թիրախը դառնում է Բնակիչ, Գողը՝ այդ դերը։",
        Role.JOURNALIST: "Լրագրող։ Գիշերը կարող է բացահայտել մեկ խաղացողի դերը խմբում։",
        Role.GUARD: "Պահակ։ Գիշերը պաշտպանում է մեկ խաղացողին մաֆիայի սպանությունից։",
        Role.ACCOUNTANT: "Հաշվապահ։ Գիշերը կարող է իմանալ, թե քանի մաֆիա է մնացել։",
        Role.SPY: "Լրտես։ Գիշերը կարող է տեսնել, թե ում է ընտրել մաֆիան։",
        Role.TRAITOR: "Դավաճան։ Կարող է միանալ մաֆիային։",
        Role.DISABLED: "Հաշմանդամ։ Գիշերը կարող է արգելափակել մեկ խաղացողի քվեարկությունը։",
        Role.JUDGE: "Դատավոր։ Քվեարկության և Like/Dislike ժամանակ նրա ձայնը հաշվվում է որպես 2 ձայն։",
        Role.LUCKY: "Հաջողակ։ Առաջին գիշերային սպանության փորձից ավտոմատ փրկվում է (միայն 1 անգամ)։",
        
    }
    try:
        query.message.edit_text(
            text=f"{role.value}\n\n{role_descriptions.get(role, 'Նկարագրություն չկա')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Հետ գնալ", callback_data="show_roles")]])
        )
    except Exception as e:
        logger.error(f"Failed to show role info for %s: %s", role_name, e)


# ================== ԴԵՐԵՐԻ ԳՆՈՒՄ (Telegram Stars) ==================

ROLE_DESCRIPTIONS_SHOP = {
    Role.CITIZEN: "Միրնի բնակիչ։ Գիշերը քնում է, ցերեկը փորձում է գտնել և կախաղան հանել մաֆիային։",
    Role.MAFIA: "Դոն — մաֆիայի ղեկավար։ Գիշերը ընտանիքի հետ ընտրում է զոհին և կատարում դատավճիռը։",
    Role.MAFIA_SUB: "Մաֆիա։ Գիշերը ընտանիքի հետ ընտրում է զոհին։ Եթե Դոնը մեռնում է — կարող է դառնալ նոր Դոն։",
    Role.DOCTOR: "Բժիշկ։ Գիշերը կարող է գնալ մեկ խաղացողի մոտ և փրկել նրա կյանքը։ Ինքն իրեն կարող է փրկել միայն 1 անգամ։",
    Role.COMMISSAR: "Կոմիսար Կատտանի։ Գիշերը կարող է կամ իմանալ մեկ խաղացողի դերը, կամ սպանել նրան։",
    Role.MANIAC: "Մոլագար։ Ամեն գիշեր սպանում է մեկ խաղացողի։ Նպատակը — սպանել բոլորին և մնալ միայնակ։",
    Role.MISTRESS: "Սիրուհի։ Գիշերը կարող է շեղել ցանկացած խաղացողի։ Նրա զոհը չի գործում ամբողջ գիշեր և հաջորդ ցերեկ։",
    Role.SERGEANT: "Սերժանտ։ Կոմիսարի օգնական։ Կոմիսարի մահից հետո դառնում է նոր Կոմիսար։",
    Role.LAWYER: "Ադվոկատ։ Գիշերը պաշտպանում է մեկին։ Եթե Կոմիսարը ստուգի — տեսնում է որպես միրնի։",
    Role.WANDERER: "Թափառական։ Գիշերը կարող է գնալ մեկի մոտ և տեսնել, թե ով է սպանել նրան։",
    Role.KAMIKAZE: "Կամիկաձե։ Եթե կախաղան հանեն — կարող է մեկին տանել իր հետ։",
    Role.THIEF: "Գող։ Ամբողջ խաղում 1 անգամ գիշերը գողանում է մեկի դերը — թիրախը դառնում է Բնակիչ, Գողը՝ այդ դերը։",
    Role.JOURNALIST: "Լրագրող։ Գիշերը կարող է բացահայտել մեկ խաղացողի դերը։",
    Role.GUARD: "Պահակ։ Գիշերը պաշտպանում է մեկ խաղացողին մաֆիայի սպանությունից։",
    Role.ACCOUNTANT: "Հաշվապահ։ Գիշերը կարող է իմանալ, թե քանի մաֆիա է մնացել։",
    Role.SPY: "Լրտես։ Գիշերը կարող է տեսնել, թե ում է ընտրել մաֆիան։",
    Role.TRAITOR: "Դավաճան։ Կարող է միանալ մաֆիային։",
    Role.DISABLED: "Հաշմանդամ։ Կարող է արգելափակել մեկի քվեարկությունը։",
    Role.JUDGE: "Դատավոր։ Քվեարկության և Like/Dislike ժամանակ նրա ձայնը հաշվվում է որպես 2 ձայն։",
    Role.LUCKY: "Հաջողակ։ Առաջին գիշերային սպանության փորձից ավտոմատ փրկվում է (միայն 1 անգամ)։",
    
}


def buy_roles_menu(update, context):
    """Դերերի խանութ — ցուցակ"""
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    owned = user_owned_roles.get(user_id, [])

    lines = ["⭐ <b>Դերերի խանութ</b>\n", "Ընտրիր դեր՝ տեսնելու նկարագրությունը և գինը։\n"]
    keyboard = []
    row = []
    for role in Role:
        price = ROLE_PRICES.get(role, 10)
        owned_mark = " ✅" if role.name in owned else ""
        btn_text = f"{role.value.split()[-1] if role.value else role.name} — {price}⭐{owned_mark}"
        # Կարճ անուն կոճակի համար
        short = role.value[:20] if len(role.value) > 20 else role.value
        row.append(InlineKeyboardButton(f"{short} · {price}⭐", callback_data=f"buy_role_view_{role.name}"))
        if len(row) == 1:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("📦 Իմ գնած դերերը", callback_data="my_owned_roles")])
    keyboard.append([InlineKeyboardButton("« Հետ", callback_data="back_to_start")])

    try:
        query.message.edit_text(
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"buy_roles_menu: {e}")


def buy_role_view(update, context):
    """Մեկ դերի նկարագրություն + Վճարել / Հետ — նույն հաղորդագրության վրա"""
    query = update.callback_query
    query.answer()
    role_name = query.data.replace("buy_role_view_", "")
    try:
        role = Role[role_name]
    except KeyError:
        query.answer("Դեր չի գտնվել", show_alert=True)
        return

    price = ROLE_PRICES.get(role, 10)
    desc = ROLE_DESCRIPTIONS_SHOP.get(role, "Նկարագրություն չկա")
    user_id = query.from_user.id
    owned = role.name in user_owned_roles.get(user_id, [])

    text = (
        f"🎭 <b>{role.value}</b>\n\n"
        f"{desc}\n\n"
        f"💰 Գին՝ <b>{price} Telegram Stars</b>"
    )
    if owned:
        text += "\n\n✅ Դու արդեն ունես այս դերը։ Կարող ես օգտագործել հաջորդ խաղում։"

    keyboard = []
    if not owned:
        keyboard.append([
            InlineKeyboardButton(f"💳 Վճարել · {price}⭐", callback_data=f"buy_role_pay_{role.name}"),
        ])
    keyboard.append([InlineKeyboardButton("« Հետ", callback_data="buy_roles_menu")])

    try:
        query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        pending_shop_msg[user_id] = query.message.message_id
    except Exception as e:
        logger.error(f"buy_role_view: {e}")


def buy_role_pay(update, context):
    """Վճարել — հիմնական տեքստը մնում է, ուղարկվում է 1 invoice (առանց կրկնության)"""
    query = update.callback_query
    role_name = query.data.replace("buy_role_pay_", "")
    try:
        role = Role[role_name]
    except KeyError:
        query.answer("Դեր չի գտնվել", show_alert=True)
        return

    price = ROLE_PRICES.get(role, 10)
    user_id = query.from_user.id

    if role.name in user_owned_roles.get(user_id, []):
        query.answer("Դու արդեն ունես այս դերը։", show_alert=True)
        return

    # Կրկնակի սեղմումից խուսափել
    if user_id in invoice_lock:
        query.answer("Սպասիր…", show_alert=False)
        return
    invoice_lock.add(user_id)

    desc = ROLE_DESCRIPTIONS_SHOP.get(role, role.value)[:255]

    # Պահել message_id — վճարումից հետո նույն տեքստի վրա շնորհակալություն
    try:
        pending_shop_msg[user_id] = query.message.message_id
    except Exception:
        pass

    try:
        # Հիմնական տեքստը Չի ջնջվում
        context.bot.send_invoice(
            chat_id=user_id,
            title=role.value[:32],
            description=desc,
            payload=f"buy_role_{role.name}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=role.value[:32], amount=price)],
            start_parameter=f"buy_{role.name}",
        )
        query.answer("⭐ Վճարման պատուհանը բացված է", show_alert=False)
    except Exception as e:
        logger.error(f"buy_role_pay invoice error: {e}")
        try:
            query.answer(f"Սխալ՝ {e}", show_alert=True)
        except Exception:
            pass
    finally:
        def _unlock():
            invoice_lock.discard(user_id)
        threading.Timer(3.0, _unlock).start()


def my_owned_roles(update, context):
    """Ցույց տալ օգտատիրոջ գնած դերերը"""
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    owned = user_owned_roles.get(user_id, [])
    if not owned:
        text = "📦 Դու դեռ դեր չես գնել։\n\nԳնիր դեր խանութից և խաղի սկզբում կկարողանաս օգտագործել։"
    else:
        lines = ["📦 <b>Քո գնած դերերը</b>\n"]
        for rn in owned:
            try:
                r = Role[rn]
                lines.append(f"• {r.value}")
            except Exception:
                lines.append(f"• {rn}")
        lines.append("\nԽաղը սկսվելիս կստանաս առաջարկ՝ օգտագործել գնված դերը։")
        text = "\n".join(lines)
    try:
        query.message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Հետ խանութ", callback_data="buy_roles_menu")]]),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"my_owned_roles: {e}")


def precheckout_callback(update, context):
    """Telegram Stars pre-checkout — միշտ հաստատել եթե payload-ը մերն է"""
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("buy_role_"):
        query.answer(ok=True)
    else:
        query.answer(ok=False, error_message="Անհայտ վճարում")


def successful_payment_callback(update, context):
    """Հաջող վճարում — ավելացնել դերը օգտատիրոջը"""
    global user_owned_roles, stars_total_earned, stars_purchases
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    payload = payment.invoice_payload
    if not payload.startswith("buy_role_"):
        return
    role_name = payload.replace("buy_role_", "")
    try:
        role = Role[role_name]
    except KeyError:
        context.bot.send_message(chat_id=user_id, text="❌ Դերը չի գտնվել։ Կապվեք ադմինի հետ։")
        return

    if user_id not in user_owned_roles:
        user_owned_roles[user_id] = []
    if role_name not in user_owned_roles[user_id]:
        user_owned_roles[user_id].append(role_name)

    stars = payment.total_amount
    user = update.effective_user
    name = user.full_name or str(user_id)
    username = f"@{user.username}" if user.username else "—"
    desc = ROLE_DESCRIPTIONS_SHOP.get(role, role.value)

    stars_total_earned += stars
    stars_purchases.append({
        "user_id": user_id,
        "name": name,
        "username": username,
        "role": role.name,
        "role_value": role.value,
        "stars": stars,
        "time": datetime.now().isoformat(),
    })
    save_data()

    # Գեղեցիկ շնորհակալություն — նախ նույն հաղորդագրության վրա
    buyer_text = (
        f"╔══════════════════╗\n"
        f"   ⭐ ԳՆՈՒՄԸ ՀԱՋՈՂՎԵՑ ⭐\n"
        f"╚══════════════════╝\n\n"
        f"🎭 <b>{role.value}</b>\n\n"
        f"{desc}\n\n"
        f"💰 Վճարված՝ <b>{stars} Telegram Stars</b>\n\n"
        f"🙏 <b>Շնորհակալություն գնումի համար!</b>\n\n"
        f"Հաջորդ խաղին միանալիս կստանաս առաջարկ՝\n"
        f"✅ օգտագործել այս դերը\n"
        f"կամ 🎲 խաղալ պատահական դերով։\n\n"
        f"Հաջողություն խաղում 🍀"
    )
    keyboard_thanks = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Խանութ", callback_data="buy_roles_menu")],
        [InlineKeyboardButton("« Գլխավոր", callback_data="back_to_start")],
    ])
    edited = False
    msg_id = pending_shop_msg.pop(user_id, None)
    if msg_id:
        try:
            context.bot.edit_message_text(
                chat_id=user_id,
                message_id=msg_id,
                text=buyer_text,
                reply_markup=keyboard_thanks,
                parse_mode="HTML"
            )
            edited = True
        except Exception as e:
            logger.error(f"edit thank you on shop msg: {e}")
    if not edited:
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=buyer_text,
                reply_markup=keyboard_thanks,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"buyer thank you message: {e}")

    # Ավտոմատ ծանուցում հիմնադրին
    try:
        if bot_creator_id:
            founder_text = (
                f"⭐ <b>ՆՈՐ ԳՆՈՒՄ</b>\n\n"
                f"👤 Անուն՝ {name}\n"
                f"🔗 Username՝ {username}\n"
                f"🆔 ID՝ <code>{user_id}</code>\n\n"
                f"🎭 Գնված դեր՝ {role.value}\n"
                f"💰 Գումար՝ <b>{stars} Stars</b>\n\n"
                f"📊 Ընդհանուր եկամուտ՝ <b>{stars_total_earned} Stars</b>"
            )
            context.bot.send_message(
                chat_id=bot_creator_id,
                text=founder_text,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"founder notify purchase: {e}")


def use_purchased_role_callback(update, context):
    """Խաղի սկզբում՝ օգտագործել / չօգտագործել գնված դերը"""
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("use_role_yes_"):
        # use_role_yes_CHATID_ROLENAME
        parts = data.replace("use_role_yes_", "").split("_", 1)
        if len(parts) != 2:
            return
        chat_id_str, role_name = parts
        try:
            chat_id = int(chat_id_str)
        except Exception:
            return
        game = get_game(chat_id)
        if user_id not in game.players:
            query.edit_message_text("❌ Դու այլևս այս խաղում չես։")
            return
        if role_name not in user_owned_roles.get(user_id, []):
            query.edit_message_text("❌ Այս դերն այլևս հասանելի չէ։")
            return
        # Նշել որ այս խաղում պետք է այս դերը
        pending_role_choice[user_id] = role_name
        try:
            role = Role[role_name]
            query.edit_message_text(
                f"✅ Ընտրված է՝ {role.value}\n\nԽաղը սկսվելիս կստանաս այս դերը։"
            )
        except Exception:
            query.edit_message_text("✅ Դերը ընտրված է։")
    elif data.startswith("use_role_no_"):
        parts = data.replace("use_role_no_", "").split("_", 1)
        if len(parts) != 2:
            return
        pending_role_choice.pop(user_id, None)
        query.edit_message_text(
            "👍 Լավ։ Կստանաս պատահական դեր՝ ինչպես մյուսները։"
        )


def back_to_start(update, context):
    query = update.callback_query
    query.answer()
    try:
        keyboard = [
            [
                InlineKeyboardButton("🎮 Ավելացնել խմբում", url="http://t.me/ArmeniaMafia_Bot?startgroup=true"),
                InlineKeyboardButton("💬 Մուտք չատ", url="https://t.me/+37fKHd7KvgEyMjI6"),
            ],
            [
                InlineKeyboardButton("🎭 Դերեր", callback_data="show_roles"),
                InlineKeyboardButton("⭐ Գնել դեր", callback_data="buy_roles_menu"),
            ],
            [
                InlineKeyboardButton("🆘 Օգնություն", callback_data="help_contact"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text(
            text=get_text("start_message", "hy"),
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to return to start menu: %s", e)


def notify_founder_new_group(context, chat_id, chat=None):
    """Ուղարկել հիմնադրին ծանուցում նոր խմբի մասին"""
    if not bot_creator_id:
        logger.error("bot_creator_id not set, cannot notify")
        return

    info = register_group_info(context, chat_id, chat)
    title = (info or {}).get("title") or (getattr(chat, "title", None) if chat else None) or "Անանուն խումբ"
    link = (info or {}).get("link") or f"chat_id: {chat_id}"
    creator_name = (info or {}).get("creator_name") or "—"
    creator_username = (info or {}).get("creator_username") or "—"

    # HTML — Chat ID սեղմելի է (copy)
    safe_title = str(title).replace("<", "").replace(">", "")
    safe_creator = str(creator_name).replace("<", "").replace(">", "")
    notify_text = (
        f"🆕 Բոտը ավելացվեց նոր խմբում\n\n"
        f"📛 Անուն՝ {safe_title}\n"
        f"🔗 Հղում՝ {link}\n"
        f"👤 Խմբի հիմնադիր՝ {safe_creator} ({creator_username})\n"
        f"🆔 Chat ID՝ <code>{chat_id}</code>"
    )
    try:
        context.bot.send_message(
            chat_id=bot_creator_id,
            text=notify_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logger.info(f"Notified founder about new group {chat_id} ({title})")
    except Exception as e:
        logger.error(f"Failed to notify founder about new group {chat_id}: {e}")
        try:
            context.bot.send_message(
                chat_id=bot_creator_id,
                text=f"🆕 Բոտը ավելացվեց խմբում\nԱնուն՝ {safe_title}\nChat ID՝ {chat_id}\nՀղում՝ {link}"
            )
        except Exception as e2:
            logger.error(f"Second notify attempt also failed: {e2}")


def new_chat_member(update, context):
    """Խմբում նոր անդամ / բոտի ավելացում"""
    try:
        if not update.message:
            return
        chat = update.effective_chat
        if not chat or chat.type not in ["group", "supergroup"]:
            return

        chat_id = chat.id
        new_members = update.message.new_chat_members or []
        game = get_game(chat_id)

        # Բոտի ID
        try:
            bot_id = context.bot.id
        except Exception:
            try:
                bot_id = context.bot.get_me().id
            except Exception:
                bot_id = None

        # Ստուգել՝ արդյոք բոտն է ավելացվել
        bot_was_added = False
        if bot_id is not None:
            for m in new_members:
                mid = getattr(m, "id", None)
                if mid is not None and int(mid) == int(bot_id):
                    bot_was_added = True
                    break
                # Երբեմն is_bot flag
                if getattr(m, "is_bot", False) and getattr(m, "username", None) == getattr(context.bot, "username", None):
                    bot_was_added = True
                    break

        if bot_was_added:
            logger.info(f"Bot was added to group {chat_id} ({getattr(chat, 'title', '')})")
            # Սև ցուցակ — ավտոմատ դուրս գալ
            is_blacklisted = (
                chat_id in blacklisted_groups
                or abs(chat_id) in blacklisted_groups
                or int(str(chat_id).replace("-100", "")) in blacklisted_groups
            )
            if is_blacklisted:
                try:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text="🚫 Այս խումբը արգելափակված է։ Բոտը չի կարող այստեղ աշխատել։"
                    )
                except Exception:
                    pass
                try:
                    context.bot.leave_chat(chat_id)
                except Exception as e:
                    logger.error(f"Failed to leave blacklisted group {chat_id}: {e}")
                if bot_creator_id:
                    try:
                        title = (getattr(chat, "title", "") or "").replace("<", "").replace(">", "")
                        context.bot.send_message(
                            chat_id=bot_creator_id,
                            text=(
                                f"🚫 Սև ցուցակի խումբ\n\n"
                                f"📛 {title}\n"
                                f"🆔 <code>{chat_id}</code>\n"
                                f"✅ Բոտը ավտոմատ դուրս եկավ"
                            ),
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
                return
            notify_founder_new_group(context, chat_id, chat)

        # Ողջույնի հաղորդագրություն խմբում (միայն մեկ անգամ)
        if chat_id not in game.welcome_message_sent or not game.welcome_message_sent.get(chat_id):
            try:
                context.bot.send_message(
                    chat_id=chat_id,
                    text=get_text("welcome_message", game.language)
                )
                game.welcome_message_sent[chat_id] = True
            except Exception as e:
                logger.error(f"Failed to send welcome message in chat %s: {e}", chat_id)
    except Exception as e:
        logger.error(f"new_chat_member error: {e}")


def create(update, context):
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    chat_type = update.effective_chat.type
    game = get_game(chat_id)  # յուրաքանչյուր խումբ՝ առանձին խաղ

    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # Գրանցել խումբը known_groups-ում (եթե դեռ չկա)
    if chat_type in ["group", "supergroup"] and chat_id not in known_groups:
        try:
            register_group_info(context, chat_id, update.effective_chat)
        except Exception:
            pass

    # /create աշխատում է միայն խմբում
    if chat_type not in ["group", "supergroup"]:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ /create հրամանը աշխատում է միայն խմբում։"
            )
        except Exception:
            pass
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return

    if not is_admin_or_creator(context, chat_id, user_id):
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("not_admin", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send not admin message in chat %s: {e}", chat_id)
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return
    if game.state != GameState.IDLE:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("game_already_started", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send create error message in chat %s: {e}", chat_id)
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return
    game.state = GameState.REGISTRATION
    game.group_chat_id = chat_id
    game.players.clear()
    game.mistress_blocked = None
    game.last_mistress_target = None
    game.mistress_notified.clear()
    game.doctor_self_healed = False
    game.lucky_saved = set()
    game.thief_used = set()
    game.non_player_notified.clear()
    game.registration_end_time = datetime.now() + timedelta(seconds=game.registration_duration)
    keyboard = [[InlineKeyboardButton("Միանալ", url=f"http://t.me/ArmeniaMafia_Bot?start=join_{chat_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        message = context.bot.send_message(
            chat_id=chat_id,
            text=get_text("game_created", game.language).format(game.registration_duration),
            reply_markup=reply_markup
        )
        game.registration_message_id = message.message_id
        context.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message.message_id,
            disable_notification=True
        )
    except telegram.error.BadRequest as e:
        logger.error(f"Failed to send or pin game created message in chat %s: {e}", chat_id)
    except Exception as e:
        logger.error(f"Unexpected error in create for chat %s: {e}", chat_id)
    threading.Timer(game.registration_duration, lambda: end_registration(context, chat_id)).start()
    logger.info("Registration started in chat %s", chat_id)
    threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()


def end_registration(context, chat_id):
    game = get_game(chat_id)
    logger.info("End of registration for chat %s", chat_id)
    if game.state != GameState.REGISTRATION:
        logger.warning("Registration ended but state is %s", game.state)
        return
    game.registration_end_time = None
    try:
        if game.registration_message_id:
            delete_message(context, chat_id, game.registration_message_id)
            context.bot.unpin_chat_message(chat_id=chat_id, message_id=game.registration_message_id)
            game.registration_message_id = None
    except telegram.error.BadRequest as e:
        logger.error(f"Failed to delete or unpin registration message in chat %s: {e}", chat_id)
    except Exception as e:
        logger.error(f"Unexpected error in end_registration for chat %s: {e}", chat_id)
    if len(game.players) < 4:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("not_enough_players", game.language)
            )
            game.state = GameState.IDLE
            game.players.clear()
            game.group_chat_id = None
        except Exception as e:
            logger.error(f"Failed to send no players message in chat %s: {e}", chat_id)
        return
    try:
        context.bot.send_message(
            chat_id=chat_id,
            text="Գրանցումն ավարտվել է։ Օգտագործեք /go՝ խաղը սկսելու համար:"
        )
    except Exception as e:
        logger.error(f"Failed to send registration ended message in chat %s: {e}", chat_id)


def start_game(context, chat_id):
    game = get_game(chat_id)
    if game.state != GameState.REGISTRATION:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("game_already_started", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send game already started message in chat %s: {e}", chat_id)
        return
    try:
        if game.registration_message_id:
            delete_message(context, chat_id, game.registration_message_id)
            context.bot.unpin_chat_message(chat_id=chat_id, message_id=game.registration_message_id)
            game.registration_message_id = None
    except telegram.error.BadRequest as e:
        logger.error(f"Failed to delete or unpin registration message in chat %s: {e}", chat_id)
    except Exception as e:
        logger.error(f"Unexpected error in start_game for chat %s: {e}", chat_id)
    game.state = GameState.RUNNING
    game.start_time = datetime.now()
    players = list(game.players.keys())
    random.shuffle(players)
    num_players = len(players)
    if num_players < 4:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("not_enough_players", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send not enough players message in chat %s: {e}", chat_id)
        game.state = GameState.IDLE
        game.players.clear()
        game.group_chat_id = None
        return

    # Դերերի բաշխում (custom կամ default) + գնված դերեր
    roles = get_roles_for_count(num_players)
    random.shuffle(roles)

    # Նախ նշանակել գնված դերերը
    assigned_purchased = {}  # player_id -> Role
    for player_id in list(players):
        chosen = pending_role_choice.get(player_id)
        if chosen and chosen in user_owned_roles.get(player_id, []):
            try:
                role_obj = Role[chosen]
                assigned_purchased[player_id] = role_obj
                # Հանել այդ դերը pool-ից եթե կա
                if role_obj in roles:
                    roles.remove(role_obj)
                else:
                    # Եթե չկա pool-ում — փոխարինել մեկ CITIZEN
                    if Role.CITIZEN in roles:
                        roles.remove(Role.CITIZEN)
                # Սպառել գնումը (մեկ անգամ օգտագործում)
                user_owned_roles[player_id].remove(chosen)
                if not user_owned_roles[player_id]:
                    user_owned_roles.pop(player_id, None)
                pending_role_choice.pop(player_id, None)
            except Exception as e:
                logger.error(f"Purchased role assign error: {e}")
                pending_role_choice.pop(player_id, None)

    save_data()

    # Մնացած խաղացողներին պատահական դերեր
    remaining_players = [p for p in players if p not in assigned_purchased]
    random.shuffle(roles)
    for i, player_id in enumerate(remaining_players):
        if i < len(roles):
            game.players[player_id]["role"] = roles[i]
        else:
            game.players[player_id]["role"] = Role.CITIZEN

    for player_id, role_obj in assigned_purchased.items():
        game.players[player_id]["role"] = role_obj

    for i, player_id in enumerate(players):
        if player_id in game.players and game.players[player_id]["private_chat"]:
            try:
                role = game.players[player_id]["role"]
                # TrueMafia-style beautiful role messages
                role_full_messages = {
                    Role.CITIZEN: "Դու blond Խաղաղ բնակիչ ես։\nՔո խնդիրն է գտնել մաֆիայի ներկայացուցիչներին և հաջորդ ժամանակ կախաղան բարձրացնել նրանց",
                    Role.MAFIA: "Դու 🤵‍♂️ Դոն ես (մաֆիայի առաջնորդ)!\nԴու ես որոշում, թե ով չպետք է արթնանա այս գիշեր...",
                    Role.MAFIA_SUB: "Դու 🤵‍♂️ Մաֆիա ես։\nԳիշերը օգնում ես Դոնին ընտրել զոհին։",
                    Role.DOCTOR: "Դու 👨‍⚕️ Բժիշկ ես։\nԳիշերը կարող ես փրկել մեկ խաղացողի կյանքը։ Ինքդ քեզ կարող ես փրկել միայն 1 անգամ։",
                    Role.COMMISSAR: "Դու 🕵️‍♂️ Կոմիսար Կատտանի ես։\nԳիշերը կարող ես կամ ստուգել մեկ խաղացողի դերը, կամ սպանել նրան։",
                    Role.MANIAC: "Դու 🪓 Մոլագար ես։\nԱմեն գիշեր սպանում ես մեկին։ Նպատակդ՝ մնալ միայնակ։",
                    Role.MISTRESS: "Դու 💃 Սիրուհի ես։\nԳիշերը կարող ես շեղել մեկ խաղացողի (նա չի գործի գիշերը և հաջորդ ցերեկ)։",
                    Role.SERGEANT: "Դու 👮‍♀️ Սերժանտ ես։\nԿոմիսարի օգնականն ես։ Կոմիսարի մահից հետո դառնում ես Կոմիսար։",
                    Role.LAWYER: "Դու 🧑‍💼 Ադվոկատ ես։\nԳիշերը պաշտպանում ես մեկին։ Եթե Կոմիսարը ստուգի նրան՝ կտեսնի որպես միրնի։",
                    Role.WANDERER: "Դու 🧙‍♀️ Թափառական ես։\nԳիշերը կարող ես գնալ մեկի մոտ և տեսնել, թե ով է սպանել նրան։",
                    Role.KAMIKAZE: "Դու 💣 Կամիկաձե ես։\nԵթե քեզ կախաղան հանեն՝ կարող ես մեկին տանել քեզ հետ։",
                    Role.THIEF: "Դու 🦹 Գող ես։\nԱմբողջ խաղում 1 անգամ կարող ես գողանալ մեկի դերը։ Թիրախը կդառնա Խաղաղ բնակիչ, դու կդառնաս նրա դերը։",
                    Role.JOURNALIST: "Դու 📰 Լրագրող ես։\nԳիշերը կարող ես բացահայտել մեկ խաղացողի դերը։",
                    Role.GUARD: "Դու 🛡️ Պահակ ես։\nԳիշերը պաշտպանում ես մեկ խաղացողին։",
                    Role.ACCOUNTANT: "Դու 📊 Հաշվապահ ես։\nԳիշերը կարող ես իմանալ մաֆիաների քանակը։",
                    Role.SPY: "Դու 🕴️ Լրտես ես։\nԳիշերը կարող ես տեսնել մաֆիայի ընտրությունը։",
                    Role.TRAITOR: "Դու 🗡️ Դավաճան ես։\nԿարող ես միանալ մաֆիային։",
                    Role.DISABLED: "Դու ♿ Հաշմանդամ ես։\nԿարող ես արգելափակել մեկի քվեարկությունը։",
                    Role.JUDGE: "Դու ⚖️ Դատավոր ես։\nՔվեարկության և Like/Dislike ժամանակ քո ձայնը հաշվվում է որպես 2 ձայն։",
                    Role.LUCKY: "Դու 🍀 Հաջողակ ես։\nԱռաջին անգամ երբ քեզ գիշերը սպանել փորձեն — ավտոմատ կփրկվես (միայն 1 անգամ)։",
                }
                role_message = role_full_messages.get(role, f"Դու {role.value} ես")
                # Ուղարկել դերի գիֆ + տեքստ
                gif_url = ROLE_GIFS.get(role)
                if gif_url:
                    try:
                        context.bot.send_animation(
                            chat_id=player_id,
                            animation=gif_url,
                            caption=role_message
                        )
                    except Exception:
                        # Եթե գիֆը չաշխատեց — միայն տեքստ
                        context.bot.send_message(chat_id=player_id, text=role_message)
                else:
                    context.bot.send_message(chat_id=player_id, text=role_message)
                # Մաֆիայի թիմակիցների ցանկ (TrueMafia style) — բոլորին
                if game.players[player_id]["role"] in [Role.MAFIA, Role.MAFIA_SUB]:
                    teammates = []
                    for u_id, p in game.players.items():
                        if p["role"] in [Role.MAFIA, Role.MAFIA_SUB]:
                            role_label = "Դոն" if p["role"] == Role.MAFIA else "Մաֆիա"
                            # Սեղմելի անուն
                            name_link = f"<a href=\"tg://user?id={u_id}\">{p['name']}</a>"
                            teammates.append(f"{name_link} - 🤵 {role_label}")
                    if teammates:
                        team_text = "Հիշիր քո թիմակիցներին:\n" + "\n".join(teammates)
                        context.bot.send_message(
                            chat_id=player_id, 
                            text=team_text,
                            parse_mode="HTML"
                        )

                elif game.players[player_id]["role"] == Role.TRAITOR:
                    context.bot.send_message(
                        chat_id=player_id,
                        text="Դուք կարող եք խոսել մաֆիայի հետ, եթե միանաք նրանց:"
                    )
            except telegram.error.BadRequest as e:
                logger.error(f"Failed to send role to %s: %s", player_id, e)
                try:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=get_text("private_chat_warning", game.language).format(game.players[player_id]["name"])
                    )
                except Exception as e:
                    logger.error(f"Failed to send private chat warning in chat %s: {e}", chat_id)
            except Exception as e:
                logger.error(f"Unexpected error sending role to %s: %s", player_id, e)
    try:
        keyboard = [[InlineKeyboardButton(get_text("view_role_button", game.language), url="http://t.me/ArmeniaMafia_Bot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=chat_id,
            text=get_text("game_started", game.language),
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to send game started message in chat %s: {e}", chat_id)
    logger.info("Game started in chat %s with %d players", chat_id, num_players)
    save_games()
    start_night(context, chat_id)


def start_night(context, chat_id):
    game = get_game(chat_id)
    game.state = GameState.NIGHT
    game.night_count += 1
    save_games()
    game.mafia_votes.clear()
    game.doctor_saves.clear()
    game.commissar_checks.clear()
    game.commissar_kills.clear()
    game.maniac_kills.clear()
    game.mistress_choices.clear()
    game.lawyer_protections.clear()
    game.wanderer_witness.clear()
    game.thief_checks.clear()
    game.journalist_reveals.clear()
    game.guard_protections.clear()
    game.accountant_checks.clear()
    game.spy_observations.clear()
    game.traitor_choices.clear()
    game.disabled_blocks.clear()
    game.mafia_chat.clear()

    # ===== Սիրուհու արգելափակումը մաքրել նոր գիշերից առաջ =====
    game.mistress_blocked = None

    logger.info("Night %s started in chat %s", game.night_count, chat_id)
    players_to_remove = [
        user_id for user_id, player in list(game.players.items())
        if not player["private_chat"] and player["alive"]
    ]
    for user_id in players_to_remove:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("player_removed_no_private", game.language).format(game.players[user_id]["name"])
            )
            del game.players[user_id]
        except Exception as e:
            logger.error(f"Failed to send player removed message in chat %s: {e}", chat_id)
    if len([p for p in game.players.values() if p["alive"]]) < 2 and game.night_count > 1:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("game_stopped_insufficient_players", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send game stopped message in chat %s: {e}", chat_id)
        game.state = GameState.IDLE
        game.players.clear()
        game.night_count = 0
        game.group_chat_id = None
        logger.info("Game stopped due to insufficient players in chat %s", chat_id)
        return
    try:
        keyboard = [[InlineKeyboardButton(get_text("go_to_bot_button", game.language), url="http://t.me/ArmeniaMafia_Bot")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_animation(
            chat_id=chat_id,
            animation="https://64.media.tumblr.com/cfdb1958123cb581959a3643ee79ff2b/c31b9e8f68c91e07-d6/s500x750/82d040326d5d84d513ebd54a168abdc105629be5.gif",
            caption=get_text("night_message", game.language),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        # Խաղացողների ցուցակ գիշերային հաղորդագրության տակ — սեղմելի անուններով
        alive_players = [(uid, p) for uid, p in game.players.items() if p["alive"]]
        players_list = "\n".join([
            f'{i+1}. <a href="tg://user?id={uid}">{p["name"]}</a>'
            for i, (uid, p) in enumerate(alive_players)
        ])
        minutes = game.night_duration // 60
        seconds = game.night_duration % 60
        keyboard2 = [[InlineKeyboardButton(get_text("go_to_bot_button", game.language), url="http://t.me/ArmeniaMafia_Bot")]]
        context.bot.send_message(
            chat_id=chat_id,
            text=f"Ողջ խաղացողներ.\n{players_list}\n\nՔննարկմանը մնացել է {minutes} ր. {seconds} վրկ.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard2),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to send night animation to chat %s: %s", chat_id, e)
    mafia_members = ", ".join(p["name"] for u_id, p in game.players.items() if p["role"] in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR] and p["alive"])
    commissar_id = next((u_id for u_id, p in game.players.items() if p["role"] == Role.COMMISSAR and p["alive"]), None)
    sergeant_id = next((u_id for u_id, p in game.players.items() if p["role"] == Role.SERGEANT and p["alive"]), None)
    for user_id, player in game.players.items():
        if not player["alive"]:
            continue
        try:
            if player["role"] in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR]:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_mafia_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"] and p["role"] not in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR] and u_id != user_id
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                action_text = "mafia_action" if player["role"] == Role.MAFIA else "mafia_sub_action" if player["role"] == Role.MAFIA_SUB else "mafia_action"
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text(action_text, game.language).format(mafia_members),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.DOCTOR:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_doctor_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("doctor_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.COMMISSAR:
                if game.night_count >= 2:
                    # TrueMafia style: first choose action type
                    keyboard = [
                        [InlineKeyboardButton("🔍 Ստուգել", callback_data="commissar_choose_check")],
                        [InlineKeyboardButton("🔫 Սպանել", callback_data="commissar_choose_kill")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    context.bot.send_message(
                        chat_id=user_id,
                        text="Դու 🕵️‍♂️ Կոմիսար Կատտանի ես։\nԸնտրիր գործողությունը՝",
                        reply_markup=reply_markup
                    )
                else:
                    # First night - only check
                    keyboard = [
                        [InlineKeyboardButton(p["name"], callback_data=f"night_action_commissar_check_{u_id}")]
                        for u_id, p in game.players.items() if p["alive"] and u_id != user_id
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    context.bot.send_message(
                        chat_id=user_id,
                        text="Դու 🕵️‍♂️ Կոմիսար Կատտանի ես։\nԱռաջին գիշեր կարող ես միայն ստուգել։ Ընտրիր խաղացողին՝",
                        reply_markup=reply_markup
                    )
            elif player["role"] == Role.MANIAC:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_maniac_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"] and u_id != user_id
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("maniac_action", game.language),
                    reply_markup=reply_markup
                )

            # ================== ՍԻՐՈՒՀԻ ==================
            elif player["role"] == Role.MISTRESS:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_mistress_{u_id}")]
                    for u_id, p in game.players.items()
                    if p["alive"] and u_id != user_id and u_id != game.last_mistress_target
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("mistress_action", game.language),
                    reply_markup=reply_markup
                )

            elif player["role"] == Role.LAWYER:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_lawyer_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("lawyer_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.WANDERER:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_wanderer_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"] and u_id != user_id
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("wanderer_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.KAMIKAZE:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_kamikaze_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"] and u_id != user_id
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("kamikaze_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.THIEF:
                if user_id in game.thief_used:
                    try:
                        context.bot.send_message(
                            chat_id=user_id,
                            text=get_text("thief_already_used", game.language)
                        )
                    except Exception:
                        pass
                else:
                    keyboard = [
                        [InlineKeyboardButton(p["name"], callback_data=f"night_action_thief_{u_id}")]
                        for u_id, p in game.players.items() if p["alive"] and u_id != user_id
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    context.bot.send_message(
                        chat_id=user_id,
                        text=get_text("thief_action", game.language),
                        reply_markup=reply_markup
                    )
            elif player["role"] == Role.JOURNALIST:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_journalist_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"] and u_id != user_id
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("journalist_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.GUARD:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_guard_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("guard_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.ACCOUNTANT:
                keyboard = [
                    [InlineKeyboardButton("Հաշվել", callback_data="night_action_accountant_check")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("accountant_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.SPY:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_spy_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"] and p["role"] in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("spy_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.TRAITOR:
                keyboard = [
                    [InlineKeyboardButton("Միանալ մաֆիային", callback_data="night_action_traitor_join")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("traitor_action", game.language),
                    reply_markup=reply_markup
                )
            elif player["role"] == Role.DISABLED:
                keyboard = [
                    [InlineKeyboardButton(p["name"], callback_data=f"night_action_disabled_{u_id}")]
                    for u_id, p in game.players.items() if p["alive"] and u_id != user_id
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("disabled_action", game.language),
                    reply_markup=reply_markup
                )



        except telegram.error.BadRequest as e:
            logger.error(f"Failed to send action to %s: %s", user_id, e)
            try:
                context.bot.send_message(
                    chat_id=chat_id,
                    text=get_text("private_chat_warning", game.language).format(player["name"])
                )
            except Exception as e:
                logger.error(f"Failed to send private chat warning in chat %s: {e}", chat_id)
        except Exception as e:
            logger.error(f"Unexpected error sending action to %s: %s", user_id, e)
    threading.Timer(game.night_duration, lambda: end_night(context, chat_id)).start()



def commissar_choose_action(update, context):
    """Կոմիսարը ընտրում է՝ Ստուգել թե Սպանել"""
    query = update.callback_query
    user_id = query.from_user.id
    game = find_game_by_user(user_id)
    if not game or game.state != GameState.NIGHT or user_id not in game.players or not game.players[user_id]["alive"]:
        query.answer("Գործողությունը հնարավոր չէ")
        return
    if game.players[user_id]["role"] != Role.COMMISSAR:
        query.answer("Դու Կոմիսար չես")
        return

    choice = query.data  # commissar_choose_check or commissar_choose_kill

    if choice == "commissar_choose_check":
        keyboard = [
            [InlineKeyboardButton(p["name"], callback_data=f"night_action_commissar_check_{u_id}")]
            for u_id, p in game.players.items() if p["alive"] and u_id != user_id
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text(
            text="🔍 Ո՞ւմ ես ուզում ստուգել։",
            reply_markup=reply_markup
        )
    elif choice == "commissar_choose_kill":
        keyboard = [
            [InlineKeyboardButton(p["name"], callback_data=f"night_action_commissar_kill_{u_id}")]
            for u_id, p in game.players.items() if p["alive"] and u_id != user_id
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text(
            text="🔫 Ո՞ւմ ես ուզում սպանել։",
            reply_markup=reply_markup
        )


def night_action(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    game = find_game_by_user(user_id)
    if not game or game.state != GameState.NIGHT or user_id not in game.players or not game.players[user_id]["alive"]:
        query.answer("Գործողությունը հնարավոր չէ")
        return

    # Եթե խաղացողը արգելափակված է Սիրուհու կողմից — չի կարող գործել
    if is_mistress_blocked(user_id):
        query.answer(get_text("mistress_blocked", game.language))
        return

    action_data = query.data.split("_")[2:]
    action = action_data[0]
    target_id = int(action_data[-1]) if len(action_data) > 1 and action_data[-1].isdigit() else None

    try:
        if action == "mafia" and game.players[user_id]["role"] in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR]:
            game.mafia_votes[user_id] = target_id
            query.message.edit_text(f"Դու ընտրել ես {game.players[target_id]['name']}")

            # Գեղեցիկ հայտարարություն մաֆիայի չաթում
            role_label = "Դոն" if game.players[user_id]["role"] == Role.MAFIA else "Մաֆիա"
            voter_link = f"<a href=\"tg://user?id={user_id}\">{game.players[user_id]['name']}</a>"
            target_link = f"<a href=\"tg://user?id={target_id}\">{game.players[target_id]['name']}</a>"

            mafia_members = [u_id for u_id, p in game.players.items() 
                             if p["role"] in [Role.MAFIA, Role.MAFIA_SUB] and p["alive"]]
            for member_id in mafia_members:
                if member_id == user_id:
                    continue
                try:
                    context.bot.send_message(
                        chat_id=member_id,
                        text=f"🤵 {role_label} {voter_link} քվեարկեց {target_link} դեմ",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

            # Խմբում հաղորդագրություն միայն երբ ԴՈՆ-ն է ընտրում
            if game.players[user_id]["role"] == Role.MAFIA:
                context.bot.send_message(
                    chat_id=game.group_chat_id,
                    text=get_text("mafia_action_group", game.language)
                )
        elif action == "doctor" and game.players[user_id]["role"] == Role.DOCTOR:
            # Բժիշկը ինքն իրեն կարող է փրկել միայն 1 անգամ
            if target_id == user_id:
                if game.doctor_self_healed:
                    query.answer("Դուք արդեն օգտագործել եք ինքներդ ձեզ փրկելու իրավունքը։")
                    return
                game.doctor_self_healed = True

            game.doctor_saves[user_id] = target_id
            query.message.edit_text(f"Դու ընտրել ես {game.players[target_id]['name']}")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("doctor_action_group", game.language)
            )
        elif action == "commissar" and game.players[user_id]["role"] == Role.COMMISSAR:
            if action_data[1] == "check":
                game.commissar_checks[user_id] = target_id
                query.message.edit_text(f"Դու ընտրել ես {game.players[target_id]['name']}")
                context.bot.send_message(
                    chat_id=game.group_chat_id,
                    text="🕵️‍♂️ Կոմիսար Կատտանին գնաց չարագործներին փնտրելու..."
                )
                sergeant_id = next((u_id for u_id, p in game.players.items() if p["role"] == Role.SERGEANT and p["alive"]), None)
                if sergeant_id:
                    context.bot.send_message(
                        chat_id=sergeant_id,
                        text=get_text("sergeant_notification", game.language).format("ստուգել", game.players[target_id]["name"])
                    )
            elif action_data[1] == "kill" and game.night_count >= 2:
                game.commissar_kills[user_id] = target_id
                query.message.edit_text(f"Դու ընտրել ես {game.players[target_id]['name']}")
                # Գեղեցիկ տեքստ խմբում — Կոմիսարը կրակում է
                context.bot.send_message(
                    chat_id=game.group_chat_id,
                    text="🔫 Կոմիսար Կատտանին լիցքավորեց ատրճանակը..."
                )
                sergeant_id = next((u_id for u_id, p in game.players.items() if p["role"] == Role.SERGEANT and p["alive"]), None)
                if sergeant_id:
                    context.bot.send_message(
                        chat_id=sergeant_id,
                        text=get_text("sergeant_notification", game.language).format("սպանել", game.players[target_id]["name"])
                    )
        elif action == "maniac" and game.players[user_id]["role"] == Role.MANIAC:
            game.maniac_kills[user_id] = target_id
            query.message.edit_text(f"Դու ընտրել ես {game.players[target_id]['name']}")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("maniac_action_group", game.language)
            )

        # ================== ՍԻՐՈՒՀԻ ԳՈՐԾՈՂՈՒԹՅՈՒՆ (TrueMafia style) ==================
        elif action == "mistress" and game.players[user_id]["role"] == Role.MISTRESS:
            if target_id == game.last_mistress_target:
                query.answer(get_text("mistress_same_target", game.language))
                return

            # Միայն պահպանում ենք ընտրությունը։ Արգելափակումը կկիրառվի գիշերվա վերջում
            game.mistress_choices[user_id] = target_id
            game.last_mistress_target = target_id

            query.message.edit_text(f"Դու ընտրել ես {game.players[target_id]['name']}")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("mistress_action_group", game.language)
            )

        elif action == "lawyer" and game.players[user_id]["role"] == Role.LAWYER:
            game.lawyer_protections[user_id] = target_id
            query.message.edit_text(f"Դու ընտրել ես {game.players[target_id]['name']}")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("lawyer_action_group", game.language)
            )
        elif action == "wanderer" and game.players[user_id]["role"] == Role.WANDERER:
            game.wanderer_witness[user_id] = target_id
            query.message.edit_text(f"//‍♀️ Դուք գնացել եք {game.players[target_id]['name']} մոտ:")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("wanderer_action_group", game.language)
            )
        elif action == "kamikaze" and game.players[user_id]["role"] == Role.KAMIKAZE:
            game.kamikaze_targets[user_id] = target_id
            query.message.edit_text(f"Դու ընտրել ես {game.players[target_id]['name']}")
        elif action == "thief" and game.players[user_id]["role"] == Role.THIEF:
            if user_id in game.thief_used:
                query.message.edit_text(get_text("thief_already_used", game.language))
            else:
                game.thief_checks[user_id] = target_id
                query.message.edit_text(
                    f"🦹 Դու ընտրեցիր {game.players[target_id]['name']}-ին։ "
                    f"Գիշերվա վերջում կգողանաս նրա դերը։"
                )
                context.bot.send_message(
                    chat_id=game.group_chat_id,
                    text=get_text("thief_action_group", game.language)
                )
        elif action == "journalist" and game.players[user_id]["role"] == Role.JOURNALIST:
            game.journalist_reveals[user_id] = target_id
            query.message.edit_text(f"📰 Դուք բացահայտել եք {game.players[target_id]['name']}:")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("journalist_action_group", game.language)
            )
        elif action == "guard" and game.players[user_id]["role"] == Role.GUARD:
            game.guard_protections[user_id] = target_id
            query.message.edit_text(f"🛡️ Դուք պաշտպանել եք {game.players[target_id]['name']}:")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("guard_action_group", game.language)
            )
        elif action == "accountant" and game.players[user_id]["role"] == Role.ACCOUNTANT:
            game.accountant_checks[user_id] = True
            query.message.edit_text(f"📊 Դուք սկսել եք հաշվարկը:")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("accountant_action_group", game.language)
            )
        elif action == "spy" and game.players[user_id]["role"] == Role.SPY:
            game.spy_observations[user_id] = target_id
            query.message.edit_text(f"🕴️ Դուք հետևում եք {game.players[target_id]['name']}-ին:")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("spy_action_group", game.language)
            )
        elif action == "traitor" and game.players[user_id]["role"] == Role.TRAITOR:
            game.traitor_choices[user_id] = True
            query.message.edit_text(f"🗡️ Դուք միացել եք մաֆիային:")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("traitor_action_group", game.language)
            )
            for mafia_id in [u_id for u_id, p in game.players.items() if p["role"] in [Role.MAFIA, Role.MAFIA_SUB] and p["alive"]]:
                context.bot.send_message(
                    chat_id=mafia_id,
                    text=get_text("traitor_joined", game.language)
                )
        elif action == "disabled" and game.players[user_id]["role"] == Role.DISABLED:
            game.disabled_blocks[user_id] = target_id
            query.message.edit_text(f"♿ Դուք արգելափակել եք {game.players[target_id]['name']}-ի քվեարկությունը:")
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("disabled_action_group", game.language)
            )



        query.answer(get_text("action_accepted", game.language))
    except Exception as e:
        logger.error(f"Failed to process night action for user %s: %s", user_id, e)
        query.answer(get_text("action_failed", game.language))


def handle_mafia_chat(update, context):
    """Մաֆիայի ներքին չաթ — Դոնը և Մաֆիաները կարող են խոսել միմյանց հետ բոտում"""
    user_id = update.message.from_user.id
    game = find_game_by_user(user_id)
    if not game or user_id not in game.players or not game.players[user_id]["alive"]:
        return
    if game.players[user_id]["role"] not in [Role.MAFIA, Role.MAFIA_SUB]:
        return
    if game.state not in [GameState.NIGHT, GameState.DAY, GameState.VOTING, GameState.CONFIRM_KILL]:
        return

    message = update.message.text
    if not message:
        return

    mafia_members = [u_id for u_id, p in game.players.items() 
                     if p["role"] in [Role.MAFIA, Role.MAFIA_SUB] and p["alive"]]

    game.mafia_chat.append((user_id, message))

    role_name = "Դոն" if game.players[user_id]["role"] == Role.MAFIA else "Մաֆիա"
    sender_name = game.players[user_id]["name"]
    # Սեղմելի անուն
    mention = f"<a href=\"tg://user?id={user_id}\">{sender_name}</a>"

    for member_id in mafia_members:
        if member_id == user_id:
            continue
        try:
            context.bot.send_message(
                chat_id=member_id,
                text=f"{mention}:\n{message}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send mafia chat message to %s: %s", member_id, e)




def try_kill_player(context, game, target_id, killer_name, killed_players):
    """Փորձել սպանել խաղացողին։ Հաջողակը 1 անգամ փրկվում է։"""
    if target_id not in game.players or not game.players[target_id]["alive"]:
        return False
    # 🍀 Հաջողակ — առաջին գիշերային սպանությունից փրկվում է
    if (game.players[target_id]["role"] == Role.LUCKY
            and target_id not in game.lucky_saved):
        game.lucky_saved.add(target_id)
        try:
            context.bot.send_message(
                chat_id=target_id,
                text=get_text("lucky_saved_private", game.language)
            )
        except Exception:
            pass
        try:
            if game.group_chat_id:
                context.bot.send_message(
                    chat_id=game.group_chat_id,
                    text=get_text("lucky_saved", game.language)
                )
        except Exception:
            pass
        return False
    game.players[target_id]["alive"] = False
    if game.players[target_id]["role"] == Role.MAFIA:
        promote_new_don(context, game, target_id)
    killed_players.append((target_id, killer_name))
    return True


def get_mafia_target(game):
    """Վերջնական զոհը միայն Դոնի քվեն է։ Եթե Դոնը չի քվեարկել — զոհ չկա։"""
    if not game.mafia_votes:
        return None
    don_id = next((uid for uid, p in game.players.items() if p["role"] == Role.MAFIA and p["alive"]), None)
    if don_id and don_id in game.mafia_votes:
        return game.mafia_votes[don_id]
    return None  # Դոնը չի ընտրել → զոհ չկա


def promote_new_don(context, game, dead_don_id):
    """Երբ Դոնը մեռնում է — պատահական կենդանի մաֆիա դառնում է նոր Դոն"""
    living_mafia = [uid for uid, p in game.players.items() 
                    if p["role"] == Role.MAFIA_SUB and p["alive"] and uid != dead_don_id]
    if not living_mafia:
        return None
    new_don_id = random.choice(living_mafia)
    game.players[new_don_id]["role"] = Role.MAFIA  # դարձնել Դոն

    # Ծանուցել նոր Դոնին
    try:
        context.bot.send_message(
            chat_id=new_don_id,
            text="🎩 Դու հիմա Դոն ես!\nՆախորդ Դոնը մահացավ, և դու դարձար մաֆիայի նոր առաջնորդ։"
        )
    except Exception:
        pass

    # Ծանուցել մյուս մաֆիաներին
    for uid, p in game.players.items():
        if p["role"] in [Role.MAFIA, Role.MAFIA_SUB] and p["alive"] and uid != new_don_id:
            try:
                context.bot.send_message(
                    chat_id=uid,
                    text=f"🎩 Նոր Դոն է նշանակվել՝ {game.players[new_don_id]['name']}"
                )
            except Exception:
                pass

    return new_don_id

def end_night(context, chat_id):
    game = get_game(chat_id)
    logger.info("Night %s ended in chat %s", game.night_count, chat_id)
    if game.state != GameState.NIGHT:
        logger.warning("Night ended but state is %s", game.state)
        return
    try:
        context.bot.send_animation(
            chat_id=chat_id,
            animation="https://i.pinimg.com/originals/56/ca/26/56ca26ecdbf79f6739c8e60ce987fc4a.gif",
            caption=get_text("night_ended", game.language).format(game.night_count),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Failed to send night ended animation to chat %s: %s", chat_id, e)

    killed_players = []

    # ===== ՍԻՐՈՒՀՈՒ ԱՐԳԵԼԱՓԱԿՈՒՄԸ ԿԻՐԱՌԵԼ ԳԻՇԵՐՎԱ ՎԵՐՋՈՒՄ =====
    mistress_id = next((uid for uid, p in game.players.items() if p["role"] == Role.MISTRESS and p["alive"]), None)
    mistress_target = next(iter(game.mistress_choices.values()), None) if game.mistress_choices else None

    # Նախ հաշվարկել հնարավոր սպանությունները
    don_id = next((uid for uid, p in game.players.items() if p["role"] == Role.MAFIA and p["alive"]), None)
    mafia_target = get_mafia_target(game)
    saved_id = next(iter(game.doctor_saves.values()), None)
    protected_id = next(iter(game.guard_protections.values()), None)

    # Եթե Սիրուհին գնացել է Դոնի մոտ, և Դոնը սպանում է Սիրուհուն → Սիրուհին մեռնում է, Դոնը ՉԻ արգելափակվում
    if (mistress_id and mistress_target == don_id and mafia_target == mistress_id):
        # Սիրուհին մեռնում է, արգելափակում չկա
        game.mistress_blocked = None
    elif mistress_id and mistress_target:
        # Սովորական դեպք՝ արգելափակել թիրախին
        game.mistress_blocked = mistress_target
        game.mistress_notified.clear()
        try:
            context.bot.send_message(
                chat_id=mistress_target,
                text="💃 Սիրուհին քեզ վնասազերծել է այս գիշեր և հաջորդ ցերեկ։ Դու չես կարող գործել, խոսել և քվեարկել։"
            )
            game.mistress_notified.add(mistress_target)
        except Exception:
            pass
    else:
        game.mistress_blocked = None

    # Եթե Սիրուհին ինքը սպանվել է (այլ պատճառով) → արգելափակումը չեղյալ
    if mistress_id and not game.players[mistress_id]["alive"]:
        game.mistress_blocked = None

    # Բժիշկը փրկում է արգելափակումից
    if saved_id is not None and saved_id == game.mistress_blocked:
        game.mistress_blocked = None
        game.mistress_notified.discard(saved_id)
        try:
            context.bot.send_message(
                chat_id=saved_id,
                text="👨🏼‍⚕️ Բժիշկը քեզ փրկեց Սիրուհու արգելափակումից։ Այժմ կարող ես խոսել և քվեարկել։"
            )
        except Exception:
            pass

    # ----- Մաֆիայի սպանություն -----
    if mafia_target:
        # Եթե Սիրուհին արգելափակել է Դոնին → սպանությունը չի կատարվում
        blocked_by_mistress = (don_id is not None and don_id == game.mistress_blocked)

        if not blocked_by_mistress and mafia_target != saved_id and mafia_target != protected_id:
            if mafia_target in game.players and game.players[mafia_target]["alive"]:
                was_killed = try_kill_player(context, game, mafia_target, "Մաֆիա", killed_players)

                # Եթե Դոնը սպանեց Կամիկաձեին → Դոնն էլ մեռնում է
                if was_killed and game.players[mafia_target]["role"] == Role.KAMIKAZE and don_id and game.players[don_id]["alive"]:
                    try_kill_player(context, game, don_id, "Կամիկաձե (հետը տարավ)", killed_players)
                    try:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text=f"💣 Կամիկաձեն իր հետ տարավ Դոնին։"
                        )
                    except Exception:
                        pass

    # ----- Կոմիսարի սպանություն -----
    if game.commissar_kills:
        target_id = next(iter(game.commissar_kills.values()))
        if target_id != game.mistress_blocked and target_id in game.players and game.players[target_id]["alive"]:
            try_kill_player(context, game, target_id, "Կոմիսար", killed_players)

    # ----- Մոլագարի սպանություն -----
    if game.maniac_kills:
        target_id = next(iter(game.maniac_kills.values()))
        if target_id != game.mistress_blocked and target_id in game.players and game.players[target_id]["alive"]:
            try_kill_player(context, game, target_id, "Մոլագար", killed_players)

    
    
    for target_id, killer in killed_players:
        try:
            name_link = f'<a href="tg://user?id={target_id}">{game.players[target_id]["name"]}</a>'
            context.bot.send_message(
                chat_id=chat_id,
                text=f"Այսօր դաժանաբար սպանվել է {name_link}, նա {game.players[target_id]['role'].value} էր...\nՆրան այցելել է {killer}",
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send kill message to chat %s: {e}", chat_id)

    if not killed_players:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("no_kill", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send no kill message to chat %s: {e}", chat_id)

    # ===== ԹԱՓԱՌԱԿԱՆԻ ՀԱՇՎԵՏՎՈՒԹՅՈՒՆ =====
    # Թափառականը տեսնում է բոլոր այցելուներին՝ անուն + դեր
    for wanderer_id, target_id in game.wanderer_witness.items():
        if not game.players.get(wanderer_id, {}).get("alive"):
            continue
        if target_id not in game.players:
            continue
        visitors = []  # list of (uid, role_label)

        def _add_visitor(uid, label):
            if uid and uid in game.players and uid != wanderer_id:
                name = game.players[uid]["name"]
                visitors.append(f"• {name} — {label}")

        # Մաֆիա (Դոն + բոլոր ովքեր քվեարկել են այդ թիրախի դեմ)
        for uid, tid in game.mafia_votes.items():
            if tid == target_id and uid in game.players:
                role = game.players[uid]["role"]
                label = role.value if role else "Մաֆիա"
                _add_visitor(uid, label)

        # Բժիշկ
        for uid, tid in game.doctor_saves.items():
            if tid == target_id:
                _add_visitor(uid, Role.DOCTOR.value)

        # Սիրուհի
        for uid, tid in game.mistress_choices.items():
            if tid == target_id:
                _add_visitor(uid, Role.MISTRESS.value)

        # Կոմիսար (ստուգում կամ սպանություն)
        for uid, tid in game.commissar_checks.items():
            if tid == target_id:
                _add_visitor(uid, Role.COMMISSAR.value)
        for uid, tid in game.commissar_kills.items():
            if tid == target_id:
                _add_visitor(uid, Role.COMMISSAR.value)

        # Մոլագար
        for uid, tid in game.maniac_kills.items():
            if tid == target_id:
                _add_visitor(uid, Role.MANIAC.value)

        # Իրավաբան
        for uid, tid in game.lawyer_protections.items():
            if tid == target_id:
                _add_visitor(uid, Role.LAWYER.value)

        # Պահակ
        for uid, tid in game.guard_protections.items():
            if tid == target_id:
                _add_visitor(uid, Role.GUARD.value)

        # Գող
        for uid, tid in game.thief_checks.items():
            if tid == target_id:
                _add_visitor(uid, Role.THIEF.value)

        # Լրագրող
        for uid, tid in game.journalist_reveals.items():
            if tid == target_id:
                _add_visitor(uid, Role.JOURNALIST.value)

        # Լրտես
        for uid, tid in game.spy_observations.items():
            if tid == target_id:
                _add_visitor(uid, Role.SPY.value)

        # Հաշմանդամ
        for uid, tid in getattr(game, "disabled_blocks", {}).items():
            if tid == target_id:
                _add_visitor(uid, Role.DISABLED.value)

        # Unique visitors (same person only once)
        seen = set()
        unique_visitors = []
        for v in visitors:
            if v not in seen:
                seen.add(v)
                unique_visitors.append(v)

        try:
            target_name = game.players[target_id]["name"]
            if unique_visitors:
                text = (
                    f"🧙‍♀️ Դու գնացիր {target_name}-ի մոտ և տեսար {len(unique_visitors)} այցելու.\n\n"
                    + "\n".join(unique_visitors)
                )
            else:
                text = f"🧙‍♀️ Դու գնացիր {target_name}-ի մոտ։ Ոչ ոք չէր եկել։"
            context.bot.send_message(chat_id=wanderer_id, text=text)
        except Exception as e:
            logger.error(f"Failed to send wanderer report: {e}")

    commissar_id = next((u_id for u_id, p in game.players.items() if p["role"] == Role.COMMISSAR and not p["alive"]), None)
    sergeant_id = next((u_id for u_id, p in game.players.items() if p["role"] == Role.SERGEANT and p["alive"]), None)
    if commissar_id and sergeant_id:
        game.players[sergeant_id]["role"] = Role.COMMISSAR
        try:
            context.bot.send_message(
                chat_id=sergeant_id,
                text="👮‍♂️ Կոմիսարը մահացել է: Դուք այժմ Կոմիսար եք:"
            )
        except Exception as e:
            logger.error(f"Failed to send sergeant promotion message to %s: %s", sergeant_id, e)
    
    for user_id, check_id in game.commissar_checks.items():
        try:
            role = game.players[check_id]["role"]
            if check_id in game.lawyer_protections.values() and role in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR]:
                role = Role.CITIZEN
            context.bot.send_message(
                chat_id=user_id,
                text=get_text("commissar_result", game.language).format(
                    game.players[check_id]["name"], role.value
                )
            )
            if check_id in game.players and game.players[check_id]["alive"]:
                context.bot.send_message(
                    chat_id=check_id,
                    text=get_text("commissar_checked", game.language)
                )
        except Exception as e:
            logger.error(f"Failed to send commissar check result to %s: %s", user_id, e)
    
    # ----- Գող — դերի գողություն (ամբողջ խաղում 1 անգամ) -----
    for thief_id, target_id in list(game.thief_checks.items()):
        try:
            if thief_id in game.thief_used:
                continue
            if thief_id not in game.players or target_id not in game.players:
                continue
            if not game.players[thief_id]["alive"] or not game.players[target_id]["alive"]:
                continue
            if game.players[thief_id]["role"] != Role.THIEF:
                continue
            stolen_role = game.players[target_id]["role"]
            target_name = game.players[target_id]["name"]
            # Թիրախը դառնում է Բնակիչ, Գողը՝ գողացված դերը
            game.players[target_id]["role"] = Role.CITIZEN
            game.players[thief_id]["role"] = stolen_role
            game.thief_used.add(thief_id)

            # Եթե գողացել է Դոնի դերը — թիրախը Բնակիչ է, Գողը նոր Դոն
            # Եթե գողացել է Մաֆիա_SUB և Դոնը մեռած է — կարող է դառնալ Դոն later via promote

            try:
                context.bot.send_message(
                    chat_id=thief_id,
                    text=get_text("thief_result", game.language).format(
                        stolen_role.value,
                        target_name
                    )
                )
            except Exception as e:
                logger.error(f"thief notify thief {thief_id}: {e}")

            try:
                context.bot.send_message(
                    chat_id=target_id,
                    text=get_text("thief_stolen_from", game.language)
                )
            except Exception as e:
                logger.error(f"thief notify target {target_id}: {e}")

            # Եթե Գողը դարձավ մաֆիա — ցույց տալ թիմակիցներին
            if stolen_role in [Role.MAFIA, Role.MAFIA_SUB]:
                try:
                    teammates = []
                    for u_id, p in game.players.items():
                        if p["role"] in [Role.MAFIA, Role.MAFIA_SUB] and p["alive"]:
                            role_label = "Դոն" if p["role"] == Role.MAFIA else "Մաֆիա"
                            name_link = f"<a href=\"tg://user?id={u_id}\">{p['name']}</a>"
                            teammates.append(f"{name_link} - 🤵 {role_label}")
                    if teammates:
                        context.bot.send_message(
                            chat_id=thief_id,
                            text="Հիշիր քո թիմակիցներին:\n" + "\n".join(teammates),
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logger.error(f"thief mafia team notify: {e}")

            # Թիրախին ասել որ այլևս մաֆիա չէ եթե էր
            logger.info(f"Thief {thief_id} stole {stolen_role.name} from {target_id}")
        except Exception as e:
            logger.error(f"Failed thief steal for {thief_id}: {e}")
    
    for user_id, reveal_id in game.journalist_reveals.items():
        try:
            role = game.players[reveal_id]["role"]
            if reveal_id in game.lawyer_protections.values() and role in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR]:
                role = Role.CITIZEN
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("journalist_reveal", game.language).format(
                    game.players[reveal_id]["name"], role.value
                )
            )
        except Exception as e:
            logger.error(f"Failed to send journalist reveal to chat %s: %s", chat_id, e)
    
    # Բժշկի ծանուցումներ — եթե փրկել է սպանությունից → «բուժեց», հակառակ դեպքում → «հյուր էր եկել»
    attacked_ids = set()
    if game.mafia_votes:
        mafia_final = get_mafia_target(game)
        if mafia_final:
            attacked_ids.add(mafia_final)
    if game.maniac_kills:
        attacked_ids.add(next(iter(game.maniac_kills.values())))
    if game.commissar_kills:
        attacked_ids.add(next(iter(game.commissar_kills.values())))
    
    
    for user_id, save_id in game.doctor_saves.items():
        try:
            if save_id in game.players and game.players[save_id]["alive"]:
                if save_id in attacked_ids:
                    context.bot.send_message(
                        chat_id=save_id,
                        text=get_text("doctor_saved", game.language)
                    )
                else:
                    context.bot.send_message(
                        chat_id=save_id,
                        text=get_text("doctor_visited", game.language)
                    )
        except Exception as e:
            logger.error(f"Failed to send doctor visit message to %s: %s", save_id, e)
    
    for user_id, protect_id in game.guard_protections.items():
        try:
            if protect_id in game.players and game.players[protect_id]["alive"]:
                context.bot.send_message(
                    chat_id=protect_id,
                    text=get_text("guard_protected", game.language)
                )
        except Exception as e:
            logger.error(f"Failed to send guard protection message to %s: %s", protect_id, e)
    
    for user_id in game.accountant_checks:
        try:
            mafia_count = len([p for p in game.players.values() if p["role"] in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR] and p["alive"]])
            context.bot.send_message(
                chat_id=user_id,
                text=get_text("accountant_result", game.language).format(mafia_count)
            )
        except Exception as e:
            logger.error(f"Failed to send accountant result to %s: %s", user_id, e)
    
    for user_id, observe_id in game.spy_observations.items():
        try:
            mafia_target = get_mafia_target(game)
            if mafia_target:
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("spy_result", game.language).format(game.players[mafia_target]["name"])
                )
        except Exception as e:
            logger.error(f"Failed to send spy result to %s: %s", user_id, e)
    
    mafia_count = len([p for p in game.players.values() if p["role"] in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR] and p["alive"]])
    citizen_count = len([p for p in game.players.values() if p["role"] not in [Role.MAFIA, Role.MAFIA_SUB, Role.MANIAC, Role.TRAITOR] and p["alive"]])
    maniac_count = len([p for p in game.players.values() if p["role"] == Role.MANIAC and p["alive"]])

    if mafia_count >= citizen_count:
        end_game(context, chat_id, "Մաֆիա")
        return
    if mafia_count == 1 and citizen_count == 1:
        end_game(context, chat_id, "Մաֆիա")
        return
    if mafia_count == 0 and maniac_count == 0:
        end_game(context, chat_id, "Խաղաղ բնակիչներ")
        return
    if maniac_count == 1 and mafia_count == 0 and citizen_count == 0:
        end_game(context, chat_id, "Մոլագար")
        return
    if killed_players:
        for target_id, _ in killed_players:
            # Վերջին խոսքի հրավեր — միայն 1 անգամ, առանց սպասելու
            if (game.players[target_id]["private_chat"]
                    and target_id not in game.last_word_sent):
                try:
                    context.bot.send_message(
                        chat_id=target_id,
                        text=get_text("last_word_prompt", game.language)
                    )
                except Exception as e:
                    logger.error(f"Failed to send last word prompt to {target_id}: {e}")
    # Անմիջապես անցնել ցերեկ (20 վրկ դադար չկա)
    start_day(context, chat_id)


def handle_last_word(update, context):
    game = find_game_by_user(update.message.from_user.id)
    if not game:
        return
    user_id = update.message.from_user.id

    # Միայն մահացած խաղացողները կարող են գրել, և միայն մեկ անգամ ամբողջ խաղի ընթացքում
    if user_id not in game.players or game.players[user_id]["alive"]:
        return

    if user_id in game.last_word_sent:
        try:
            context.bot.send_message(chat_id=user_id, text=get_text("last_word_already_sent", game.language))
        except Exception:
            pass
        return

    # Թույլատրել միայն LAST_WORD փուլում կամ ընդհանրապես մահացած լինելու դեպքում (եթե ուզում ես ավելի խիստ — թող միայն LAST_WORD)
    if game.state not in [GameState.LAST_WORD, GameState.DAY, GameState.VOTING, GameState.NIGHT, GameState.CONFIRM_KILL]:
        return

    message = update.message.text
    if not message or not message.strip():
        return

    game.last_word_sent.add(user_id)  # Նշում ենք, որ արդեն ուղարկել է (միայն մեկ անգամ)

    if not game.group_chat_id:
        logger.error("No group_chat_id set for last word")
        try:
            context.bot.send_message(chat_id=user_id, text="Սխալ: Խմբի ID-ն չի սահմանված:")
        except Exception:
            pass
        return

    try:
        name_link = f'<a href="tg://user?id={user_id}">{game.players[user_id]["name"]}</a>'
        context.bot.send_message(
            chat_id=game.group_chat_id,
            text=f"Բնակիչներից ինչ-որ մեկը լսել է , թե ինչպես է {name_link} բղավել մահից առաջ:\n{message}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        context.bot.send_message(
            chat_id=user_id,
            text=get_text("last_word_sent", game.language)
        )
        logger.info(f"Last word sent to group {game.group_chat_id} from user {user_id}: {message}")
    except Exception as e:
        logger.error(f"Failed to send last word to group {game.group_chat_id} from {user_id}: {e}")
        try:
            context.bot.send_message(chat_id=user_id, text="Սխալ ուղարկելիս: Փորձեք կրկին:")
        except Exception:
            pass


def start_day(context, chat_id):
    game = get_game(chat_id)
    game.state = GameState.DAY
    alive_players = [(uid, p) for uid, p in game.players.items() if p["alive"]]
    # Սեղմելի անուններ
    players_list = "\n".join([
        f'{i+1}. <a href="tg://user?id={uid}">{p["name"]}</a>'
        for i, (uid, p) in enumerate(alive_players)
    ])
    role_counts = Counter(p["role"] for _, p in alive_players)
    roles_text = ", ".join(
        f"{role.value} - {count}" if count > 1 else f"{role.value}"
        for role, count in role_counts.items()
    ) if role_counts else "Ոչ ոք"
    total_players = len(alive_players)
    minutes = game.day_duration // 60
    seconds = game.day_duration % 60
    try:
        context.bot.send_message(
            chat_id=chat_id,
            text=f"Ողջ խաղացողներ.\n{players_list}\n\n"
                 f"Նրանք են:\n{roles_text}\n"
                 f"Ընդհանուր: {total_players} մարդ\n\n"
                 f"Քննարկմանը մնացել է {minutes} ր. {seconds} վրկ.",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to send day message to chat %s: %s", chat_id, e)
    
    mafia_count = len([p for p in game.players.values() if p["role"] in [Role.MAFIA, Role.MAFIA_SUB] and p["alive"]])
    citizen_count = len([p for p in game.players.values() if p["role"] not in [Role.MAFIA, Role.MAFIA_SUB, Role.MANIAC] and p["alive"]])
    maniac_count = len([p for p in game.players.values() if p["role"] == Role.MANIAC and p["alive"]])

    if mafia_count >= citizen_count:
        end_game(context, chat_id, "Մաֆիա")
        return
    if mafia_count == 1 and citizen_count == 1:
        end_game(context, chat_id, "Մաֆիա")
        return
    if mafia_count == 0 and maniac_count == 0:
        end_game(context, chat_id, "Խաղաղ բնակիչներ")
        return
    if maniac_count == 1 and mafia_count == 0 and citizen_count == 0:
        end_game(context, chat_id, "Մոլագար")
        return

    logger.info("Day %s started in chat %s", game.night_count, chat_id)
    threading.Timer(game.day_duration, lambda: start_voting(context, chat_id)).start()


def start_voting(context, chat_id):
    game = get_game(chat_id)
    game.state = GameState.VOTING
    game.votes.clear()
    logger.info("Voting started in chat %s", chat_id)
    try:
        keyboard = [
            [InlineKeyboardButton(get_text("vote_button", game.language), url="http://t.me/ArmeniaMafia_Bot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=chat_id,
            text=get_text("voting_message", game.language).format(game.voting_duration),
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to send voting message to chat %s: %s", chat_id, e)
    
    for user_id, player in game.players.items():
        if not player["alive"] or not player["private_chat"]:
            continue

        # Եթե Սիրուհին արգելափակել է — չի կարող քվեարկել
        if is_mistress_blocked(user_id):
            try:
                context.bot.send_message(chat_id=user_id, text=get_text("mistress_blocked_vote", game.language))
            except Exception:
                pass
            continue

        try:
            keyboard = [
                [InlineKeyboardButton(p["name"], callback_data=f"vote_{u_id}")]
                for u_id, p in game.players.items() if p["alive"] and u_id != user_id
            ]
            keyboard.append([InlineKeyboardButton("Ոչ ոք", callback_data="vote_none")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(
                chat_id=user_id,
                text=get_text("voting_message", game.language).format(game.voting_duration),
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Failed to send voting options to %s: %s", user_id, e)
    
    threading.Timer(game.voting_duration, lambda: end_voting(context, chat_id)).start()


def vote(update, context):
    game = find_game_by_user(update.callback_query.from_user.id)
    if not game:
        return
    query = update.callback_query
    user_id = query.from_user.id
    if game.state != GameState.VOTING or user_id not in game.players or not game.players[user_id]["alive"]:
        query.answer(get_text("action_failed", game.language))
        return

    # Սիրուհու արգելափակում
    if is_mistress_blocked(user_id):
        query.answer(get_text("mistress_blocked_vote", game.language))
        return

    if user_id in game.disabled_blocks.values():
        query.answer(get_text("disabled_blocked", game.language))
        return
    vote_data = query.data.split("_")[1]
    if vote_data == "none":
        game.votes[user_id] = "none"
        query.message.edit_text(get_text("vote_none", game.language))
        try:
            voter_name = game.players[user_id]["name"]
            voter_link = f'<a href="tg://user?id={user_id}">{voter_name}</a>'
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("vote_result", game.language).format(voter_link, "Ոչ ոք"),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send vote result to chat %s: %s", game.group_chat_id, e)
    else:
        target_id = int(vote_data)
        if target_id in game.players and game.players[target_id]["alive"]:
            game.votes[user_id] = target_id
            query.message.edit_text(f"🗳 Դուք քվեարկել եք {game.players[target_id]['name']}-ի դեմ:")
            try:
                voter_name = game.players[user_id]["name"]
                target_name = game.players[target_id]["name"]
                voter_link = f'<a href="tg://user?id={user_id}">{voter_name}</a>'
                target_link = f'<a href="tg://user?id={target_id}">{target_name}</a>'
                context.bot.send_message(
                    chat_id=game.group_chat_id,
                    text=get_text("vote_result", game.language).format(voter_link, target_link),
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Failed to send vote result to chat %s: %s", game.group_chat_id, e)
        else:
            query.answer(get_text("action_failed", game.language))
            return
    query.answer(get_text("action_accepted", game.language))


def end_voting(context, chat_id):
    game = get_game(chat_id)
    logger.info("Voting ended in chat %s", chat_id)
    if game.state != GameState.VOTING:
        logger.warning("Voting ended but state is %s", game.state)
        return
    # Դատավորի ձայնը ×2
    weighted_votes = []
    for uid, target in game.votes.items():
        weighted_votes.append(target)
        if uid in game.players and game.players[uid].get("role") == Role.JUDGE and game.players[uid].get("alive"):
            weighted_votes.append(target)  # երկրորդ ձայն
    vote_counts = Counter(weighted_votes)
    if not vote_counts or vote_counts.most_common(1)[0][0] == "none":
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("vote_result_none", game.language).format(0, 0)
            )
        except Exception as e:
            logger.error(f"Failed to send no voted out message to chat %s: %s", chat_id, e)
        start_night(context, chat_id)
        return
    target_id, vote_count = vote_counts.most_common(1)[0]
    if target_id != "none":
        game.last_killed_id = target_id
        try:
            keyboard = [
                [InlineKeyboardButton("👍", callback_data="confirm_like"),
                 InlineKeyboardButton("👎", callback_data="confirm_dislike")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = context.bot.send_message(
                chat_id=chat_id,
                text=get_text("confirm_kill_message", game.language).format(game.players[target_id]["name"]),
                reply_markup=reply_markup
            )
            game.confirm_message_id = message.message_id
            game.state = GameState.CONFIRM_KILL
            threading.Timer(game.confirm_duration, lambda: end_confirm_kill(context, chat_id, target_id)).start()
        except Exception as e:
            logger.error(f"Failed to send confirm kill message to chat %s: %s", chat_id, e)
            start_night(context, chat_id)



def count_confirm_votes(game):
    """Դատավորի like/dislike = 2 ձայն"""
    likes = 0
    dislikes = 0
    for uid, v in game.confirm_votes.items():
        weight = 2 if (
            uid in game.players
            and game.players[uid].get("alive")
            and game.players[uid].get("role") == Role.JUDGE
        ) else 1
        if v == "like":
            likes += weight
        elif v == "dislike":
            dislikes += weight
    return likes, dislikes


def confirm_kill(update, context):
    game = find_game_by_user(update.callback_query.from_user.id)
    if not game:
        return
    query = update.callback_query
    user_id = query.from_user.id
    action = query.data.split("_")[1]
    
    if user_id not in game.players or not game.players[user_id]["alive"] or game.state != GameState.CONFIRM_KILL:
        query.answer(get_text("action_failed", game.language))
        return
    
    game.confirm_votes[user_id] = action
    query.answer(f"Դուք ընտրել եք {action}")
    
    likes, dislikes = count_confirm_votes(game)
    
    try:
        keyboard = [
            [InlineKeyboardButton(f"👍 {likes}", callback_data="confirm_like"),
             InlineKeyboardButton(f"👎 {dislikes}", callback_data="confirm_dislike")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text(
            text=get_text("confirm_kill_message", game.language).format(
                game.players[game.last_killed_id]["name"]
            ),
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to update confirm kill message: {e}")
    
    alive_players = [pid for pid, p in game.players.items() if p["alive"]]
    if len(game.confirm_votes) >= len(alive_players):
        end_confirm_kill(context, game.group_chat_id, game.last_killed_id)


def end_confirm_kill(context, chat_id, target_id):
    game = get_game(chat_id)
    logger.info("Confirm kill ended in chat %s", chat_id)
    if game.state != GameState.CONFIRM_KILL:
        logger.warning("Confirm kill ended but state is %s", game.state)
        return
    like_count, dislike_count = count_confirm_votes(game)
    try:
        context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=game.confirm_message_id,
            text=get_text("vote_result_none", game.language).format(like_count, dislike_count)
        )
    except Exception as e:
        logger.error(f"Failed to update confirm kill message in chat %s: %s", chat_id, e)
    if like_count > dislike_count:
        game.players[target_id]["alive"] = False
        # Եթե մահացածը Դոն էր — նոր Դոն նշանակել
        if game.players[target_id]["role"] == Role.MAFIA:
            promote_new_don(context, game, target_id)
        try:
            name_link = f'<a href="tg://user?id={target_id}">{game.players[target_id]["name"]}</a>'
            context.bot.send_message(
                chat_id=chat_id,
                text=f"{name_link} սպանվել է (դեր՝ {game.players[target_id]['role'].value})\nՍպանող՝ Բնակիչներ",
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            if game.players[target_id]["role"] == Role.KAMIKAZE and target_id in game.kamikaze_targets:
                kamikaze_target = game.kamikaze_targets[target_id]
                if kamikaze_target in game.players and game.players[kamikaze_target]["alive"]:
                    game.players[kamikaze_target]["alive"] = False
                    if game.players[kamikaze_target]["role"] == Role.MAFIA:
                        promote_new_don(context, game, kamikaze_target)
                    k_link = f'<a href="tg://user?id={kamikaze_target}">{game.players[kamikaze_target]["name"]}</a>'
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=f"💣 Կամիկաձե {name_link} վերցրեց {k_link} իր հետ:",
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
            # Քվեարկությամբ հանված խաղացողը ՎԵՐՋԻՆ ԽՈՍՔ ՉԻ ՍՏԱՆՈՒՄ
        except Exception as e:
            logger.error(f"Failed to send vote result to chat %s: %s", chat_id, e)
    
    game.confirm_votes.clear()
    game.confirm_message_id = None

    mafia_count = len([p for p in game.players.values() if p["role"] in [Role.MAFIA, Role.MAFIA_SUB] and p["alive"]])
    citizen_count = len([p for p in game.players.values() if p["role"] not in [Role.MAFIA, Role.MAFIA_SUB, Role.MANIAC] and p["alive"]])
    maniac_count = len([p for p in game.players.values() if p["role"] == Role.MANIAC and p["alive"]])

    if mafia_count >= citizen_count:
        end_game(context, chat_id, "Մաֆիա")
        return
    if mafia_count == 1 and citizen_count == 1:
        end_game(context, chat_id, "Մաֆիա")
        return
    if mafia_count == 0 and maniac_count == 0:
        end_game(context, chat_id, "Խաղաղ բնակիչներ")
        return
    if maniac_count == 1 and mafia_count == 0 and citizen_count == 0:
        end_game(context, chat_id, "Մոլագար")
        return

    # Անմիջապես անցնել գիշեր (վերջին խոսք միայն գիշերային սպանության համար է)
    start_night(context, chat_id)


def end_game(context, chat_id, winner):
    game = get_game(chat_id)
    if game.start_time:
        game_duration = datetime.now() - game.start_time
        total_sec = int(game_duration.total_seconds())
        minutes = total_sec // 60
        seconds = total_sec % 60
    else:
        minutes, seconds = 0, 0

    # Հաղթող թիմի emoji և վերնագիր
    winner_styles = {
        "Մաֆիա": ("🤵", "🖤 Հաղթեց Մաֆիան 🖤"),
        "Խաղաղ բնակիչներ": ("☀️", "🏙 Հաղթեցին Խաղաղ բնակիչները 🏙"),
        "Մոլագար": ("🪓", "🩸 Հաղթեց Մոլագարը 🩸"),
    }
    emoji, title = winner_styles.get(winner, ("🏆", f"Հաղթեց {winner}"))

    def is_winner_role(role):
        if winner == "Մաֆիա":
            return role in [Role.MAFIA, Role.MAFIA_SUB, Role.TRAITOR]
        if winner == "Խաղաղ բնակիչներ":
            return role not in [Role.MAFIA, Role.MAFIA_SUB, Role.MANIAC, Role.TRAITOR]
        if winner == "Մոլագար":
            return role == Role.MANIAC
        return False

    def name_link(uid, name):
        return f'<a href="tg://user?id={uid}">{name}</a>'

    # Հաղթողներ — անուն + դեր
    winners_lines = []
    for uid, p in game.players.items():
        if p.get("alive") and p.get("role") and is_winner_role(p["role"]):
            winners_lines.append(
                f'  ✅ {name_link(uid, p["name"])} — {p["role"].value}'
            )
    # Եթե հաղթող թիմի անդամները մահացած են, բայց թիմը հաղթել է — ցույց տալ նաև նրանց
    if not winners_lines:
        for uid, p in game.players.items():
            if p.get("role") and is_winner_role(p["role"]):
                winners_lines.append(
                    f'  ✅ {name_link(uid, p["name"])} — {p["role"].value}'
                )
    winners_block = "\n".join(winners_lines) if winners_lines else "  —"

    # Մահացածներ — անուն + դեր
    dead_lines = []
    for uid, p in game.players.items():
        if not p.get("alive"):
            role_val = p["role"].value if p.get("role") else "—"
            dead_lines.append(
                f'  💀 {name_link(uid, p["name"])} — {role_val}'
            )
    dead_block = "\n".join(dead_lines) if dead_lines else "  —"

    night_info = f"Գիշերներ՝ {game.night_count}" if game.night_count else ""
    duration_str = f"{minutes} ր. {seconds} վրկ."

    text = (
        f"╔══════════════════╗\n"
        f"   {emoji} ԽԱՂՆ ԱՎԱՐՏՎԱԾ Է {emoji}\n"
        f"╚══════════════════╝\n\n"
        f"{title}\n\n"
        f"🏆 Հաղթողներ\n"
        f"{winners_block}\n\n"
        f"💀 Մահացածներ\n"
        f"{dead_block}\n\n"
        f"⏱ Տևողություն՝ {duration_str}\n"
        f"🌃 {night_info}\n\n"
        f"─────────────────\n"
        f"Նոր խաղ՝ /create"
    )

    try:
        context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to send game over message to chat %s: %s", chat_id, e)
        try:
            plain = (
                f"Խաղն ավարտված է!\nՀաղթեց՝ {winner}\n"
                f"Տևողություն՝ {duration_str}\n"
                f"Գիշերներ՝ {game.night_count}"
            )
            context.bot.send_message(chat_id=chat_id, text=plain)
        except Exception:
            pass

    # ===== Օգտատերերի վիճակագրություն =====
    try:
        for uid, p in list(game.players.items()):
            role = p.get("role")
            won = bool(role and is_winner_role(role))
            update_user_stat(uid, name=p.get("name"), won=won, role=role)
        save_data()
    except Exception as e:
        logger.error(f"Failed to update user stats: {e}")

    game.state = GameState.IDLE
    game.players.clear()
    game.night_count = 0
    game.group_chat_id = None
    game.confirm_votes.clear()
    game.confirm_message_id = None
    game.last_word_sent.clear()
    game.mistress_blocked = None
    game.last_mistress_target = None
    game.mistress_notified.clear()
    game.doctor_self_healed = False
    game.lucky_saved = set()
    game.thief_used = set()
    game.non_player_notified.clear()
    save_games()
    logger.info("Game ended in chat %s, winner: %s", chat_id, winner)


def go(update, context):
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    chat_type = update.effective_chat.type
    game = get_game(chat_id)

    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # /go աշխատում է միայն խմբում
    if chat_type not in ["group", "supergroup"]:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ /go հրամանը աշխատում է միայն խմբում։"
            )
        except Exception:
            pass
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return

    if not is_admin_or_creator(context, chat_id, user_id):
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("not_admin", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send not admin message in chat %s: %s", chat_id, e)
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return
    if game.state != GameState.REGISTRATION:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("game_not_started", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send game not started message in chat %s: %s", chat_id, e)
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return
    if len(game.players) < 4:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("not_enough_players", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send not enough players message in chat %s: %s", chat_id, e)
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return
    try:
        if game.registration_message_id:
            delete_message(context, chat_id, game.registration_message_id)
            context.bot.unpin_chat_message(chat_id=chat_id, message_id=game.registration_message_id)
            game.registration_message_id = None
    except telegram.error.BadRequest as e:
        logger.error(f"Failed to delete or unpin registration message in chat %s: %s", chat_id, e)
    start_game(context, chat_id)
    threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()


def stop(update, context):
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    chat_type = update.effective_chat.type
    game = get_game(chat_id)

    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # /stop աշխատում է միայն խմբում
    if chat_type not in ["group", "supergroup"]:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ /stop հրամանը աշխատում է միայն խմբում։"
            )
        except Exception:
            pass
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return

    if not is_admin_or_creator(context, chat_id, user_id):
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("not_admin", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send not admin message in chat %s: %s", chat_id, e)
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return
    if game.state == GameState.IDLE:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text=get_text("game_not_started", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to send game not started message in chat %s: %s", chat_id, e)
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return
    try:
        context.bot.send_message(
            chat_id=chat_id,
            text=get_text("game_stopped", game.language)
        )
        if game.registration_message_id:
            delete_message(context, chat_id, game.registration_message_id)
            context.bot.unpin_chat_message(chat_id=chat_id, message_id=game.registration_message_id)
            game.registration_message_id = None
    except telegram.error.BadRequest as e:
        logger.error(f"Failed to delete or unpin registration message in chat %s: %s", chat_id, e)
    except Exception as e:
        logger.error(f"Failed to send game stopped message to chat %s: %s", chat_id, e)
    game.state = GameState.IDLE
    game.players.clear()
    game.night_count = 0
    game.group_chat_id = None
    game.confirm_votes.clear()
    game.confirm_message_id = None
    game.last_word_sent.clear()
    game.mistress_blocked = None
    game.last_mistress_target = None
    game.mistress_notified.clear()
    game.doctor_self_healed = False
    game.lucky_saved = set()
    game.thief_used = set()
    game.non_player_notified.clear()
    threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()


def leave(update, context):
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    chat_type = update.effective_chat.type
    game = get_game(chat_id)

    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # /leave աշխատում է միայն խմբում
    if chat_type not in ["group", "supergroup"]:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ /leave հրամանը աշխատում է միայն խմբում։"
            )
        except Exception:
            pass
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return

    if user_id not in game.players:
        try:
            context.bot.send_message(
                chat_id=user_id,
                text="Դուք խաղի մասնակից չեք:"
            )
        except Exception as e:
            logger.error(f"Failed to send leave error message to %s: %s", user_id, e)
        threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()
        return
    player_name = game.players[user_id]["name"]
    player_role = game.players[user_id]["role"].value if game.players[user_id]["role"] else "Անհայտ"
    del game.players[user_id]
    try:
        context.bot.send_message(
            chat_id=user_id,
            text=get_text("player_left", game.language)
        )
        if game.state != GameState.REGISTRATION and game.group_chat_id:
            name_link = f'<a href="tg://user?id={user_id}">{player_name}</a>'
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=f" {name_link} չդիմացավ քաղաքի ճնշող մթնոլորտին և հեռացավ: Նա {player_role} էր:",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"Failed to send leave message for %s: %s", user_id, e)
    if game.state == GameState.REGISTRATION and game.players and game.group_chat_id:
        players_list = "\n".join([
            f'{i+1}. <a href="tg://user?id={uid}">{p["name"]}</a>'
            for i, (uid, p) in enumerate(game.players.items())
        ])
        try:
            context.bot.edit_message_text(
                chat_id=game.group_chat_id,
                message_id=game.registration_message_id,
                text=f"{get_text('registered_players', game.language)}{players_list}\n\nՍեղմեք գրանցվելու համար:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Գրանցվել", url=f"http://t.me/ArmeniaMafia_Bot?start=join_{chat_id}")]]),
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        except telegram.error.BadRequest as e:
            logger.error(f"Failed to update registration message: %s", e)
    if game.state != GameState.IDLE and len([p for p in game.players.values() if p["alive"]]) < 2:
        try:
            context.bot.send_message(
                chat_id=game.group_chat_id,
                text=get_text("game_stopped_insufficient_players", game.language)
            )
            game.state = GameState.IDLE
            game.players.clear()
            game.night_count = 0
            game.group_chat_id = None
            game.confirm_votes.clear()
            game.confirm_message_id = None
            game.last_word_sent.clear()
            game.mistress_blocked = None
            game.last_mistress_target = None
        except Exception as e:
            logger.error(f"Failed to send game stopped message to chat %s: %s", game.group_chat_id, e)
    threading.Timer(5, lambda: delete_message(context, chat_id, message_id)).start()


def handle_non_player_message(update, context):
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    message_text = update.message.text or ""

    # /muteall — ջնջել բՈԼՈՐԻ հաղորդագրությունները (ադմիններ + խմբի հիմնադիր), միայն բոտի հիմնադիրը կարող է գրել
    if getattr(game, "muted_all", False):
        if user_id == bot_creator_id:
            return  # միայն բոտի հիմնադիրը — չջնջել
        try:
            delete_message(context, chat_id, message_id)
        except Exception:
            pass
        return
    
    # Գիշերը ոչ ոք չի կարող գրել
    if game.state == GameState.NIGHT and user_id in game.players and game.players[user_id]["alive"]:
        try:
            delete_message(context, chat_id, message_id)
            context.bot.send_message(
                chat_id=user_id,
                text=get_text("chat_not_allowed_night", game.language)
            )
        except Exception as e:
            logger.error(f"Failed to handle night message for %s: %s", user_id, e)
        return

    # Սիրուհու արգելափակում ցերեկը (հաղորդագրությունը միայն 1 անգամ)
    if game.state in [GameState.DAY, GameState.VOTING, GameState.CONFIRM_KILL] and is_mistress_blocked(user_id):
        try:
            delete_message(context, chat_id, message_id)
            if user_id not in game.mistress_notified:
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("mistress_blocked_chat", game.language)
                )
                game.mistress_notified.add(user_id)
        except Exception as e:
            logger.error(f"Failed to handle mistress block for %s: %s", user_id, e)
        return

    # Մահացածներ / չխաղացողներ — հաղորդագրությունը միայն 1 անգամ
    if game.state in [GameState.NIGHT, GameState.DAY, GameState.VOTING, GameState.CONFIRM_KILL] and (user_id not in game.players or not game.players.get(user_id, {}).get("alive", False)):
        if message_text.startswith("?"):
            return
        try:
            delete_message(context, chat_id, message_id)
            if user_id not in game.non_player_notified:
                context.bot.send_message(
                    chat_id=user_id,
                    text=get_text("chat_not_allowed", game.language)
                )
                game.non_player_notified.add(user_id)
        except Exception as e:
            logger.error(f"Failed to handle non-player message for %s: %s", user_id, e)


def help_command(update, context):
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    try:
        context.bot.send_message(
            chat_id=chat_id,
            text=get_text("help_message", game.language)
        )
    except Exception as e:
        logger.error(f"Failed to send help message in chat %s: {e}", chat_id)


def rules_command(update, context):
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    try:
        context.bot.send_message(
            chat_id=chat_id,
            text=get_text("rules_message", game.language),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send rules: {e}")


def roles_command(update, context):
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    message_id = update.message.message_id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", game.language))
        except Exception:
            pass
        return
    if not game.players:
        context.bot.send_message(chat_id=chat_id, text="Խաղը դեռ չի սկսվել։")
        return
    roles_text = ""
    for i, (uid, p) in enumerate(game.players.items(), 1):
        role_name = p["role"].value if p["role"] else "Դեռ չի բաժանվել"
        status = "✅" if p["alive"] else "💀"
        roles_text += f"{i}. {status} {p['name']} — {role_name}\n"
    try:
        context.bot.send_message(chat_id=chat_id, text=f"🎭 Դերերի բաշխում՝\n\n{roles_text}")
    except Exception as e:
        logger.error(f"Failed to send roles: {e}")


def status_command(update, context):
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    game = get_game(chat_id)
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", game.language))
        except Exception:
            pass
        return
    state_names = {
        GameState.IDLE: "Պարապ",
        GameState.REGISTRATION: "Գրանցում",
        GameState.RUNNING: "Ընթացքում",
        GameState.NIGHT: "Գիշեր",
        GameState.DAY: "Ցերեկ",
        GameState.VOTING: "Քվեարկություն",
        GameState.LAST_WORD: "Վերջին խոսք",
        GameState.CONFIRM_KILL: "Հաստատում",
    }
    alive = len([p for p in game.players.values() if p["alive"]])
    total = len(game.players)
    state = state_names.get(game.state, str(game.state))
    try:
        context.bot.send_message(
            chat_id=chat_id,
            text=f"🎮 Խաղի վիճակ՝ {state}\nԿենդանի խաղացողներ՝ {alive}/{total}\nԳիշեր №{game.night_count}"
        )
    except Exception as e:
        logger.error(f"Failed to send status: {e}")


def extend_command(update, context):
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    game = get_game(chat_id)

    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # /extend աշխատում է միայն խմբում
    if chat_type not in ["group", "supergroup"]:
        try:
            msg = context.bot.send_message(chat_id=chat_id, text="❌ /extend հրամանը աշխատում է միայն խմբում։")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
        except Exception:
            pass
        return

    if not is_admin_or_creator(context, chat_id, user_id):
        try:
            msg = context.bot.send_message(chat_id=chat_id, text=get_text("not_admin", game.language))
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
        except Exception:
            pass
        return

    if game.state != GameState.REGISTRATION:
        try:
            msg = context.bot.send_message(chat_id=chat_id, text="❌ Գրանցում չի ընթանում։ /extend-ը աշխատում է միայն գրանցման ժամանակ։")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
        except Exception:
            pass
        return

    try:
        if not context.args:
            msg = context.bot.send_message(chat_id=chat_id, text="⏱ Օգտագործում՝ `/extend <վայրկյան>`\nՕրինակ՝ `/extend 60` կամ `/extend 120`\nԱռավելագույնը՝ 300 վայրկյան (5 րոպե)")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
            return

        seconds = int(context.args[0])
        if seconds < 10:
            msg = context.bot.send_message(chat_id=chat_id, text="❌ Նվազագույնը 10 վայրկյան է։")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
            return
        if seconds > 300:
            msg = context.bot.send_message(chat_id=chat_id, text="❌ Առավելագույնը 300 վայրկյան է (5 րոպե)։")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
            return

        # Ավելացնել իրական ժամանակը
        if game.registration_end_time is None:
            game.registration_end_time = datetime.now() + timedelta(seconds=seconds)
        else:
            game.registration_end_time += timedelta(seconds=seconds)

        remaining = max(0, int((game.registration_end_time - datetime.now()).total_seconds()))
        minutes = remaining // 60
        secs = remaining % 60

        # TrueMafia-ի նման տեքստ
        msg = context.bot.send_message(
            chat_id=chat_id,
            text=f"+{seconds} վայրկյան գրանցման ժամանակին\n"
                 f"Գրանցման ավարտին մնացել է {minutes} ր. {secs} վրկ."
        )
        # Այս հաղորդագրությունը 5 վայրկյան հետո ջնջել
        threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()

        # Նոր տայմեր՝ մնացած իրական ժամանակով
        threading.Timer(remaining, lambda: end_registration(context, chat_id)).start()

    except (ValueError, IndexError):
        try:
            msg = context.bot.send_message(chat_id=chat_id, text="❌ Սխալ ֆորմատ։ Օրինակ՝ `/extend 60`")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
        except Exception:
            pass


def time_command(update, context):
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    game = get_game(chat_id)

    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # /time աշխատում է միայն խմբում
    if chat_type not in ["group", "supergroup"]:
        try:
            msg = context.bot.send_message(chat_id=chat_id, text="❌ /time հրամանը աշխատում է միայն խմբում։")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
        except Exception:
            pass
        return

    if game.state != GameState.REGISTRATION:
        try:
            msg = context.bot.send_message(chat_id=chat_id, text="❌ Գրանցում չի ընթանում։ /time-ը աշխատում է միայն գրանցման ժամանակ։")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
        except Exception:
            pass
        return

    if game.registration_end_time is None:
        try:
            msg = context.bot.send_message(chat_id=chat_id, text="⏳ Գրանցման ժամանակը դեռ սահմանված չէ։")
            threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
        except Exception:
            pass
        return

    remaining = max(0, int((game.registration_end_time - datetime.now()).total_seconds()))
    minutes = remaining // 60
    secs = remaining % 60

    try:
        # TrueMafia-ի նման տեքստ + Միանալ կոճակ
        keyboard = [[InlineKeyboardButton("Միանալ", url=f"http://t.me/ArmeniaMafia_Bot?start=join_{chat_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=chat_id,
            text=f"Խաղի գրանցումը սկսված է\n"
                 f"Գրանցման ավարտին մնացել է {minutes} ր. {secs} վրկ.",
            reply_markup=reply_markup
        )
        # /time-ի հաղորդագրությունը ՉԻ ՋՆՋՎՈՒՄ
    except Exception as e:
        logger.error(f"Failed to send time message: {e}")


def setcreator_command(update, context):
    """Հիմնադիրը արդեն սահմանված է կոդում։"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    try:
        context.bot.send_message(
            chat_id=user_id if chat_id != user_id else chat_id,
            text=f"✅ Բոտի հիմնադիր ID-ն արդեն սահմանված է կոդում՝ {bot_creator_id}"
        )
    except Exception:
        pass


def setadmin_command(update, context):
    global bot_admins
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    game = get_game(chat_id)
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    # Միայն հիմնադիրը կարող է ադմին նշանակել
    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", game.language))
        except Exception:
            pass
        return
    if not context.args:
        context.bot.send_message(chat_id=chat_id, text=get_text("setadmin_usage", game.language))
        return
    target_arg = " ".join(context.args).replace("@", "").strip()
    target_id = None
    # Եթե թիվ է — ուղիղ ID
    if target_arg.lstrip("-").isdigit():
        target_id = int(target_arg)
    else:
        for uid, p in game.players.items():
            if target_arg.lower() in p["name"].lower():
                target_id = uid
                break
    if target_id:
        if target_id not in bot_admins:
            bot_admins.append(target_id)
            save_data()
        name = game.players.get(target_id, {}).get("name", str(target_id))
        context.bot.send_message(chat_id=chat_id, text=get_text("setadmin_success", game.language).format(name))
    else:
        context.bot.send_message(chat_id=chat_id, text=get_text("setadmin_not_found", game.language))


def kick_command(update, context):
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    message_id = update.message.message_id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", game.language))
        except Exception:
            pass
        return
    if not context.args:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /kick <անուն>")
        return
    target_name = " ".join(context.args).replace("@", "")
    target_id = None
    for uid, p in game.players.items():
        if target_name.lower() in p["name"].lower():
            target_id = uid
            break
    if target_id:
        name = game.players[target_id]["name"]
        del game.players[target_id]
        context.bot.send_message(chat_id=chat_id, text=get_text("kick_success", game.language).format(name))
    else:
        context.bot.send_message(chat_id=chat_id, text=get_text("kick_not_found", game.language))


def broadcast_command(update, context):
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    message_id = update.message.message_id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", game.language))
        except Exception:
            pass
        return
    if not context.args:
        context.bot.send_message(chat_id=chat_id, text=get_text("broadcast_usage", game.language))
        return
    message = " ".join(context.args)
    for uid in game.players:
        try:
            context.bot.send_message(chat_id=uid, text=message)
        except Exception:
            pass
    context.bot.send_message(chat_id=chat_id, text=get_text("broadcast_sent", game.language))


def allroles_command(update, context):
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    message_id = update.message.message_id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", game.language))
        except Exception:
            pass
        return
    if not game.players:
        context.bot.send_message(chat_id=chat_id, text="Խաղացողներ չկան։")
        return
    text = "🎭 Բոլոր դերերը՝\n\n"
    for i, (uid, p) in enumerate(game.players.items(), 1):
        role = p["role"].value if p["role"] else "—"
        status = "✅" if p["alive"] else "💀"
        text += f"{i}. {status} {p['name']} — {role}\n"
    context.bot.send_message(chat_id=chat_id, text=text)


def setdurations_command(update, context):
    chat_id = update.effective_chat.id
    game = get_game(chat_id)
    message_id = update.message.message_id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", game.language))
        except Exception:
            pass
        return
    if len(context.args) != 4:
        context.bot.send_message(chat_id=chat_id, text=get_text("set_durations", game.language))
        return
    try:
        reg, night, day, vote = map(int, context.args)
        if min(reg, night, day, vote) < 10:
            context.bot.send_message(chat_id=chat_id, text=get_text("duration_error", game.language))
            return
        game.registration_duration = reg
        game.night_duration = night
        game.day_duration = day
        game.voting_duration = vote
        context.bot.send_message(chat_id=chat_id, text=get_text("durations_updated", game.language).format(reg, night, day, vote))
    except ValueError:
        context.bot.send_message(chat_id=chat_id, text=get_text("duration_value_error", game.language))


# ================== /settings ՀԱՄԱԿԱՐԳ ==================

# ================== /settings — TrueMafia style ==================

DURATION_OPTIONS = [30, 45, 60, 75, 90, 120, 180, 240, 300, 360]

def _settings_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎭 Դերեր", callback_data="settings_roles")],
        [InlineKeyboardButton("⏱ Ժամանակներ", callback_data="settings_timings")],
        [InlineKeyboardButton("🙊 Լռություն", callback_data="settings_mute")],
        [InlineKeyboardButton("🔧 Այլ", callback_data="settings_other")],
        [InlineKeyboardButton("🇦🇲 Լեզու / Language", callback_data="settings_lang")],
        [InlineKeyboardButton("⬅️ Ետ", callback_data="settings_close")],
    ])


def settings_command(update, context):
    """/settings — միայն ադմին/հիմնադիր, մենյուն բացվում է բոտի անձնական չաթում"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    game = get_game(chat_id)

    # Անմիջապես ջնջել հրամանի հաղորդագրությունը
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # /settings աշխատում է միայն խմբում
    if chat_type not in ["group", "supergroup"]:
        try:
            context.bot.send_message(
                chat_id=chat_id,
                text="❌ /settings հրամանը աշխատում է միայն խմբում։"
            )
        except Exception:
            pass
        return

    if not is_admin_or_creator(context, chat_id, user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("not_admin", game.language))
        except Exception:
            pass
        return

    # Եթե խմբից է գրվել — ուղարկել անձնական չաթ
    try:
        context.bot.send_message(
            chat_id=user_id,
            text="Ի՞նչ պարամետրեր եք ուզում փոխել:",
            reply_markup=_settings_main_keyboard()
        )
        if chat_id != user_id:
            # Խմբում կարճ հաստատում
            try:
                msg = context.bot.send_message(chat_id=chat_id, text="⚙️ Կարգավորումները բացվել են բոտի անձնական չաթում։")
                threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
            except Exception:
                pass
    except telegram.error.Unauthorized:
        context.bot.send_message(
            chat_id=chat_id,
            text="Խնդրում ենք սկզբում սկսել զրույց բոտի հետ՝ http://t.me/ArmeniaMafia_Bot"
        )
    except Exception as e:
        logger.error(f"Failed to open settings: {e}")


def settings_main(update, context):
    query = update.callback_query
    query.answer()
    try:
        query.message.edit_text(
            text="Ի՞նչ պարամետրեր եք ուզում փոխել:",
            reply_markup=_settings_main_keyboard()
        )
    except Exception as e:
        logger.error(f"settings_main error: {e}")


def settings_close(update, context):
    query = update.callback_query
    query.answer()
    try:
        query.message.delete()
    except Exception:
        try:
            query.message.edit_text("Կարգավորումները փակված են։")
        except Exception:
            pass


# ----- Դերեր -----
def settings_roles(update, context):
    user_id = update.callback_query.from_user.id
    game = find_game_by_user(user_id)
    if not game:
        game = next(iter(games.values()), Game()) if games else Game()
    query = update.callback_query
    query.answer()
    keyboard = []
    for role in Role:
        status = "✅" if game.active_roles.get(role, True) else "❌"
        keyboard.append([InlineKeyboardButton(
            f"{status} {role.value}",
            callback_data=f"toggle_role_{role.name}"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Ետ", callback_data="settings_main")])
    try:
        query.message.edit_text(
            text="🎭 Դերերի կառավարում\nՍեղմեք՝ միացնելու/անջատելու համար:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"settings_roles error: {e}")


def toggle_role(update, context):
    user_id = update.callback_query.from_user.id
    game = find_game_by_user(user_id)
    if not game:
        game = next(iter(games.values()), Game()) if games else Game()
    query = update.callback_query
    role_name = query.data.replace("toggle_role_", "")
    try:
        role = Role[role_name]
        game.active_roles[role] = not game.active_roles.get(role, True)
        status = "միացված ✅" if game.active_roles[role] else "անջատված ❌"
        query.answer(f"{role.value} — {status}")
        settings_roles(update, context)
    except Exception as e:
        query.answer("Սխալ")
        logger.error(f"toggle_role error: {e}")


# ----- Ժամանակներ -----
def settings_timings(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("⏱ Գրանցում", callback_data="set_timing_reg")],
        [InlineKeyboardButton("⏱ Գիշեր", callback_data="set_timing_night")],
        [InlineKeyboardButton("⏱ Ցերեկ", callback_data="set_timing_day")],
        [InlineKeyboardButton("⏱ Քվեարկություն", callback_data="set_timing_vote")],
        [InlineKeyboardButton("⏱ Հաստատում", callback_data="set_timing_confirm")],
        [InlineKeyboardButton("⏱ Ելքի սահմանափակում", callback_data="set_timing_leave")],
        [InlineKeyboardButton("⬅️ Ետ", callback_data="settings_main")],
    ]
    try:
        query.message.edit_text(
            text="Ընտրեք ժամանակի ո՞ր պարամետրերն ենք պետք է փոխվել:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"settings_timings error: {e}")


def set_timing_menu(update, context):
    user_id = update.callback_query.from_user.id
    game = find_game_by_user(user_id)
    if not game:
        game = next(iter(games.values()), Game()) if games else Game()
    """Ցույց տալ տևողության ընտրանքները (30, 45, 60...360)"""
    query = update.callback_query
    query.answer()
    kind = query.data.replace("set_timing_", "")  # reg / night / day / vote / confirm / leave

    current = {
        "reg": game.registration_duration,
        "night": game.night_duration,
        "day": game.day_duration,
        "vote": game.voting_duration,
        "confirm": game.confirm_duration,
        "leave": getattr(game, "leave_duration", 30),
    }.get(kind, 60)

    titles = {
        "reg": "Ընտրեք գրանցման տևողությունը (վ.)",
        "night": "Ընտրեք գիշերվա տևողությունը (վ.)",
        "day": "Ընտրեք ցերեկվա տևողությունը (վ.)",
        "vote": "Ընտրեք քվեարկության տևողությունը (վ.)",
        "confirm": "Ընտրեք հաստատման տևողությունը (վ.)",
        "leave": "Ընտրեք ելքի սահմանափակման տևողությունը (վ.)",
    }

    # 2 սյունակով կոճակներ
    keyboard = []
    row = []
    for i, sec in enumerate(DURATION_OPTIONS):
        mark = "▪️" if sec == current else "▫️"
        row.append(InlineKeyboardButton(f"{sec} {mark}", callback_data=f"apply_timing_{kind}_{sec}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Ետ", callback_data="settings_timings")])

    try:
        query.message.edit_text(
            text=titles.get(kind, "Ընտրեք տևողությունը (վ.)"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"set_timing_menu error: {e}")


def apply_timing(update, context):
    user_id = update.callback_query.from_user.id
    game = find_game_by_user(user_id)
    if not game:
        game = next(iter(games.values()), Game()) if games else Game()
    query = update.callback_query
    parts = query.data.split("_")  # apply_timing_reg_120
    kind = parts[2]
    seconds = int(parts[3])

    if kind == "reg":
        game.registration_duration = seconds
    elif kind == "night":
        game.night_duration = seconds
    elif kind == "day":
        game.day_duration = seconds
    elif kind == "vote":
        game.voting_duration = seconds
    elif kind == "confirm":
        game.confirm_duration = seconds
    elif kind == "leave":
        game.leave_duration = seconds

    query.answer(f"Սահմանված է {seconds} վրկ")
    # Վերադառնալ նույն մենյուին՝ նշված արժեքով
    query.data = f"set_timing_{kind}"
    set_timing_menu(update, context)


# ----- Լռություն -----
def settings_mute(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("🙊 Մահացածների համար", callback_data="mute_opt_killed")],
        [InlineKeyboardButton("🙊 Սիրունու զոհերի համար", callback_data="mute_opt_mistress")],
        [InlineKeyboardButton("🙊 Քնածների համար", callback_data="mute_opt_sleeping")],
        [InlineKeyboardButton("🙊 Չխաղացողների համար", callback_data="mute_opt_non_players")],
        [InlineKeyboardButton("⬅️ Ետ", callback_data="settings_main")],
    ]
    try:
        query.message.edit_text(
            text="Անջատել խաղասենյակում գրելու հնարավորությունը",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"settings_mute error: {e}")


def mute_option(update, context):
    user_id = update.callback_query.from_user.id
    game = find_game_by_user(user_id)
    if not game:
        game = next(iter(games.values()), Game()) if games else Game()
    """Այո / Ոչ ընտրություն"""
    query = update.callback_query
    query.answer()
    key = query.data.replace("mute_opt_", "")  # killed / mistress / sleeping / non_players

    titles = {
        "killed": "Հարկավո՞ր է արգելել մահացածներին գրել խաղասենյակում",
        "mistress": "Հարկավո՞ր է արգելել Սիրուհու զոհերին գրել",
        "sleeping": "Հարկավո՞ր է արգելել քնածներին գրել (գիշերը)",
        "non_players": "Հարկավո՞ր է արգելել չխաղացողներին գրել",
    }
    current = game.mute_settings.get(key, False)

    keyboard = [
        [InlineKeyboardButton(f"Այո {'▪️' if current else '▫️'}", callback_data=f"mute_set_{key}_1")],
        [InlineKeyboardButton(f"Ոչ {'▪️' if not current else '▫️'}", callback_data=f"mute_set_{key}_0")],
        [InlineKeyboardButton("⬅️ Ետ", callback_data="settings_mute")],
    ]
    try:
        query.message.edit_text(
            text=titles.get(key, "Ընտրեք:"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"mute_option error: {e}")


def mute_set(update, context):
    user_id = update.callback_query.from_user.id
    game = find_game_by_user(user_id)
    if not game:
        game = next(iter(games.values()), Game()) if games else Game()
    query = update.callback_query
    parts = query.data.split("_")  # mute_set_killed_1
    key = parts[2]
    value = parts[3] == "1"
    game.mute_settings[key] = value
    query.answer("Այո" if value else "Ոչ")
    query.data = f"mute_opt_{key}"
    mute_option(update, context)


# ----- Այլ -----
def settings_other(update, context):
    user_id = update.callback_query.from_user.id
    game = find_game_by_user(user_id)
    if not game:
        game = next(iter(games.values()), Game()) if games else Game()
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton(f"Մաքս. խաղացողներ: {game.max_players}", callback_data="settings_max_players")],
        [InlineKeyboardButton("⬅️ Ետ", callback_data="settings_main")],
    ]
    try:
        query.message.edit_text(
            text="🔧 Այլ կարգավորումներ",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"settings_other error: {e}")


# ----- Լեզու -----
def settings_lang(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("🇦🇲 Հայերեն", callback_data="set_lang_hy")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton("⬅️ Ետ", callback_data="settings_main")],
    ]
    try:
        query.message.edit_text(
            text="Ընտրեք լեզուն / Выберите язык:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"settings_lang error: {e}")


def set_lang(update, context):
    user_id = update.callback_query.from_user.id
    game = find_game_by_user(user_id)
    if not game:
        game = next(iter(games.values()), Game()) if games else Game()
    query = update.callback_query
    lang = query.data.replace("set_lang_", "")
    game.language = lang
    query.answer("Հայերեն" if lang == "hy" else "Русский")
    settings_main(update, context)


def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")



# ================== ՀԻՄՆԱԴՐԻ ՀՐԱՄԱՆՆԵՐ ==================

def admins_command(update, context):
    """Ցույց տալ բոտի ադմիններին"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    lines = [f"👑 Հիմնադիր: {bot_creator_id}"]
    if bot_admins:
        for i, aid in enumerate(bot_admins, 1):
            lines.append(f"{i}. {aid}")
    else:
        lines.append("Ադմիններ չկան։")
    try:
        context.bot.send_message(chat_id=chat_id, text="📋 Բոտի ադմիններ՝\n" + "\n".join(lines))
    except Exception as e:
        logger.error(f"admins_command error: {e}")


def removeadmin_command(update, context):
    """Հեռացնել բոտի ադմինին"""
    global bot_admins
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    # Միայն հիմնադիրը
    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    if not context.args:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /removeadmin <ID կամ անուն>")
        return
    target_arg = " ".join(context.args).replace("@", "").strip()
    target_id = None
    if target_arg.lstrip("-").isdigit():
        target_id = int(target_arg)
    else:
        game = get_game(chat_id)
        for uid, p in game.players.items():
            if target_arg.lower() in p["name"].lower():
                target_id = uid
                break
    if target_id is None:
        context.bot.send_message(chat_id=chat_id, text="❌ Օգտատերը չի գտնվել։")
        return
    if target_id not in bot_admins:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս օգտատերը բոտի ադմին չէ։")
        return
    bot_admins.remove(target_id)
    save_data()
    context.bot.send_message(chat_id=chat_id, text=f"✅ {target_id} հեռացվել է բոտի ադմիններից։")


def announce_command(update, context):
    """Ուղարկել հաղորդագրություն բոլոր ակտիվ խմբերին"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    if not context.args:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /announce <տեքստ>")
        return
    text = " ".join(context.args)
    sent = 0
    for cid, g in games.items():
        if g.group_chat_id:
            try:
                context.bot.send_message(chat_id=g.group_chat_id, text=f"📢 {text}")
                sent += 1
            except Exception:
                pass
    context.bot.send_message(chat_id=chat_id, text=f"✅ Հաղորդագրությունն ուղարկվել է {sent} խմբի։")


def reload_command(update, context):
    """Վերագործարկել կարգավորումները"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    # Պարզ վերագործարկում — մաքրել ժամանակավոր տվյալներ
    for g in games.values():
        g.mafia_chat.clear()
        g.non_player_notified.clear()
        g.mistress_notified.clear()
    context.bot.send_message(chat_id=chat_id, text="✅ Բոտի կարգավորումները վերագործարկվել են։")


def muteall_command(update, context):
    """Լռեցնել խումբը — ջնջում է ԲՈԼՈՐԻ հաղորդագրությունները
    (խմբի ադմիններ + խմբի հիմնադիր նույնպես),
    միայն բոտի հիմնադիրը կարող է գրել։
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    game = get_game(chat_id)
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return
    game.muted_all = True
    try:
        context.bot.send_message(chat_id=chat_id, text="🔇 Խումբը փակված է։")
    except Exception:
        pass



def unmuteall_command(update, context):
    """Բացել խումբը (/muteall-ից հետո)"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    game = get_game(chat_id)
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return
    game.muted_all = False
    try:
        context.bot.send_message(chat_id=chat_id, text="🔊 Խումբը բացված է։")
    except Exception:
        pass


def can_use_dmute(context, chat_id, user_id):
    """Բոտի հիմնադիր, խմբի ադմին կամ խմբի հիմնադիր"""
    if user_id == bot_creator_id:
        return True
    if is_bot_admin(user_id):
        return True
    try:
        member = context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def dmute_command(update, context):
    """Իրական խմբի փակում set_chat_permissions-ով
    Կարող են՝ բոտի հիմնադիր, խմբի ադմիններ, խմբի հիմնադիր
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    game = get_game(chat_id)
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    if not can_use_dmute(context, chat_id, user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը միայն բոտի հիմնադրի, խմբի ադմինների և խմբի հիմնադրի համար է։")
        except Exception:
            pass
        return

    try:
        from telegram import ChatPermissions
        context.bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            )
        )
        game.hard_muted = True
        context.bot.send_message(chat_id=chat_id, text="🔇 Խումբը կոշտ փակված է (dmute)։")
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ բոտը պետք է ունենա Restrict members իրավունք։\n{e}")


def dunmute_command(update, context):
    """Բացել dmute փակումը"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    game = get_game(chat_id)
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    if not can_use_dmute(context, chat_id, user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը միայն բոտի հիմնադրի, խմբի ադմինների և խմբի հիմնադրի համար է։")
        except Exception:
            pass
        return

    try:
        from telegram import ChatPermissions
        context.bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
            )
        )
        game.hard_muted = False
        context.bot.send_message(chat_id=chat_id, text="🔊 Խումբը բացված է (dunmute)։")
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ {e}")



def ban_command(update, context):
    """Արգելել օգտատիրոջը խաղալ"""
    global banned_users
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    if not context.args:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /ban <ID>")
        return
    target_arg = context.args[0].strip()
    if not target_arg.lstrip("-").isdigit():
        context.bot.send_message(chat_id=chat_id, text="❌ Պետք է լինի թվային ID։")
        return
    target_id = int(target_arg)
    banned_users.add(target_id)
    # Հեռացնել ընթացիկ խաղից եթե կա
    game = get_game(chat_id)
    if target_id in game.players:
        del game.players[target_id]
    save_data()
    context.bot.send_message(chat_id=chat_id, text=f"🚫 {target_id} արգելափակված է և չի կարող խաղալ։")


def unban_command(update, context):
    """Հանել արգելքը"""
    global banned_users
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    if not context.args:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /unban <ID>")
        return
    target_arg = context.args[0].strip()
    if not target_arg.lstrip("-").isdigit():
        context.bot.send_message(chat_id=chat_id, text="❌ Պետք է լինի թվային ID։")
        return
    target_id = int(target_arg)
    if target_id in banned_users:
        banned_users.discard(target_id)
        save_data()
        context.bot.send_message(chat_id=chat_id, text=f"✅ {target_id} արգելքը հանվել է։")
    else:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս ID-ն արգելափակված չէ։")



def is_group_creator(context, chat_id, user_id):
    """Ստուգում է՝ արդյոք օգտատերը խմբի հիմնադիրն է"""
    try:
        member = context.bot.get_chat_member(chat_id, user_id)
        return member.status == "creator"
    except Exception:
        return False


def is_group_admin(context, chat_id, user_id):
    """Ստուգում է՝ արդյոք օգտատերը խմբի ադմին է (ոչ creator)"""
    try:
        member = context.bot.get_chat_member(chat_id, user_id)
        return member.status == "administrator"
    except Exception:
        return False


def demote_admin(context, chat_id, user_id):
    """Հանում է ադմին իրավունքները (որպեսզի հետո կարելի լինի ban/mute անել)"""
    try:
        context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False,
            can_manage_video_chats=False,
            is_anonymous=False,
        )
        return True
    except Exception as e:
        logger.error(f"demote_admin failed for {user_id}: {e}")
        try:
            context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_change_info=False,
                can_delete_messages=False,
                can_invite_users=False,
                can_restrict_members=False,
                can_pin_messages=False,
                can_promote_members=False,
            )
            return True
        except Exception as e2:
            logger.error(f"demote_admin second try failed for {user_id}: {e2}")
            return False


def parse_duration(text):
    """Պարզել ժամանակը՝ 1r=1րոպե, 1h=1ժամ, 1d=1օր, 1sh=1շաբաթ
    Վերադարձնում է վայրկյաններ կամ None"""
    if not text:
        return None
    text = text.strip().lower().replace(" ", "")
    import re
    m = re.match(r'^(\d+)(r|ր|h|ժ|d|օ|o|sh|շ)?$', text)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2) or "r"
    if unit in ("r", "ր"):
        return num * 60
    if unit in ("h", "ժ"):
        return num * 3600
    if unit in ("d", "օ", "o"):
        return num * 86400
    if unit in ("sh", "շ"):
        return num * 604800
    return num * 60


def format_duration(seconds):
    """Մարդկային ձևով ցույց տալ ժամանակը"""
    if seconds < 60:
        return f"{seconds} վրկ"
    if seconds < 3600:
        return f"{seconds // 60} րոպե"
    if seconds < 86400:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        if m:
            return f"{h} ժամ {m} րոպե"
        return f"{h} ժամ"
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    if h:
        return f"{d} օր {h} ժամ"
    return f"{d} օր"


def resolve_target_and_duration(update, context):
    """Վերադարձնում է (target_id, duration_seconds կամ None)
    Օրինակներ՝
      /gmute 123456 1h
      /gmute 1r   (reply-ի հետ)
      /gmute @user 30r
    """
    args = list(context.args) if context.args else []
    target_id = None
    duration = None

    # Reply → target from reply
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        # Բոլոր args-ը կարող են լինել duration
        if args:
            duration = parse_duration(args[0])
            if duration is None and len(args) > 1:
                duration = parse_duration(args[-1])
        return target_id, duration

    if not args:
        return None, None

    # Առաջին arg — ID կամ անուն
    first = args[0].replace("@", "").strip()
    if first.lstrip("-").isdigit():
        target_id = int(first)
    else:
        # duration է առաջինը? (reply չկա)
        dur = parse_duration(first)
        if dur is not None and len(args) == 1:
            # Միայն duration, բայց target չկա
            return None, dur
        chat_id = update.effective_chat.id
        game = get_game(chat_id)
        for uid, p in game.players.items():
            if first.lower() in p["name"].lower():
                target_id = uid
                break

    # Երկրորդ (կամ վերջին) arg — duration
    if len(args) >= 2:
        duration = parse_duration(args[1])
        if duration is None:
            duration = parse_duration(args[-1])

    return target_id, duration


def resolve_target_id(update, context, args_text):
    """Հին ֆունկցիա — համատեղելիության համար"""
    tid, _ = resolve_target_and_duration(update, context)
    return tid


def group_ban_command(update, context):
    """Telegram խմբից արգելել օգտատիրոջը (միայն բոտի հիմնադիր)"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    args_text = " ".join(context.args) if context.args else ""
    target_id = resolve_target_id(update, context, args_text)
    if target_id is None:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /gban <ID> կամ reply արա օգտատիրոջը")
        return

    if is_group_creator(context, chat_id, target_id):
        context.bot.send_message(chat_id=chat_id, text="❌ Չես կարող արգելել խմբի հիմնադրին։")
        return

    if target_id == bot_creator_id:
        context.bot.send_message(chat_id=chat_id, text="❌ Չես կարող արգելել բոտի հիմնադրին։")
        return

    try:
        if is_group_admin(context, chat_id, target_id):
            demote_admin(context, chat_id, target_id)
        context.bot.ban_chat_member(chat_id=chat_id, user_id=target_id)
        context.bot.send_message(chat_id=chat_id, text=f"🚫 Օգտատերը ({target_id}) արգելվել է խմբից։")
    except Exception as e:
        err = str(e)
        if "administrator" in err.lower() or "admin" in err.lower():
            context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ Այս օգտատերը ադմին է և բոտը չի կարող արգելել։\n"
                    "Լուծում՝ խմբի հիմնադիրը պետք է հանի նրա ադմինությունը, "
                    "կամ բոտին նշանակի ադմին **հիմնադիրը**՝ «Add new admins» իրավունքով։"
                )
            )
        else:
            context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ {e}")


def group_unban_command(update, context):
    """Telegram խմբից հանել արգելքը"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    args_text = " ".join(context.args) if context.args else ""
    target_id = resolve_target_id(update, context, args_text)
    if target_id is None:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /gunban <ID>")
        return

    try:
        context.bot.unban_chat_member(chat_id=chat_id, user_id=target_id, only_if_banned=True)
        context.bot.send_message(chat_id=chat_id, text=f"✅ Օգտատերը ({target_id}) արգելքը հանվել է։")
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ {e}")


def group_mute_command(update, context):
    """Telegram-ում լռեցնել օգտատիրոջը
    Օրինակներ՝
      /gmute          (reply)
      /gmute 1r       (reply + 1 րոպե)
      /gmute 123456 1h
      /gmute 1h       (reply + 1 ժամ)
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    target_id, duration = resolve_target_and_duration(update, context)
    if target_id is None:
        context.bot.send_message(
            chat_id=chat_id,
            text="Օգտագործեք՝\n/gmute <ID> <ժամանակ>\nկամ reply + /gmute 1r\n\nԺամանակ՝ 1r=րոպե, 1h=ժամ, 1d=օր, 1sh=շաբաթ"
        )
        return

    if is_group_creator(context, chat_id, target_id):
        context.bot.send_message(chat_id=chat_id, text="❌ Չես կարող լռեցնել խմբի հիմնադրին։")
        return

    if target_id == bot_creator_id:
        context.bot.send_message(chat_id=chat_id, text="❌ Չես կարող լռեցնել բոտի հիմնադրին։")
        return

    # Եթե ադմին է — փորձել հանել ադմինությունը (պարտադիր չէ հաջող լինի)
    was_admin = is_group_admin(context, chat_id, target_id)
    if was_admin:
        demoted = demote_admin(context, chat_id, target_id)
        if not demoted:
            # Փորձել միևնույն է restrict անել — որոշ դեպքերում աշխատում է
            logger.warning(f"Could not demote {target_id}, trying restrict anyway")

    try:
        from telegram import ChatPermissions
        from datetime import datetime, timedelta

        until_date = None
        if duration and duration > 0:
            until_date = datetime.utcnow() + timedelta(seconds=duration)

        kwargs = {
            "chat_id": chat_id,
            "user_id": target_id,
            "permissions": ChatPermissions(can_send_messages=False),
        }
        if until_date:
            kwargs["until_date"] = until_date

        context.bot.restrict_chat_member(**kwargs)

        if chat_id not in telegram_muted:
            telegram_muted[chat_id] = set()
        telegram_muted[chat_id].add(target_id)

        if duration:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"🔇 Օգտատերը ({target_id}) լռեցված է {format_duration(duration)}։"
            )
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=f"🔇 Օգտատերը ({target_id}) լռեցված է (անժամկետ)։"
            )
    except Exception as e:
        err = str(e)
        if "administrator" in err.lower() or "admin" in err.lower():
            context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ Այս օգտատերը ադմին է և բոտը չի կարող լռեցնել։\n"
                    "Պատճառը՝ ադմինը նշանակվել է խմբի հիմնադրի կողմից։\n"
                    "Լուծում՝ խմբի հիմնադիրը պետք է հանի նրա ադմինությունը, "
                    "կամ բոտին տա ադմինություն **հիմնադրի** կողմից «Add new admins» իրավունքով։"
                )
            )
        else:
            context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ {e}")



def group_unmute_command(update, context):
    """Telegram-ում բացել լռեցված օգտատիրոջը"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    args_text = " ".join(context.args) if context.args else ""
    target_id = resolve_target_id(update, context, args_text)
    if target_id is None:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /gunmute <ID> կամ reply արա")
        return

    try:
        from telegram import ChatPermissions
        context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        if chat_id in telegram_muted:
            telegram_muted[chat_id].discard(target_id)
        context.bot.send_message(chat_id=chat_id, text=f"🔊 Օգտատերը ({target_id}) բացված է։")
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ {e}")


def warn_command(update, context):
    """Զգուշացում տալ օգտատիրոջը (3-ից հետո ավտո-ban)
    /warn կամ /gwarn — նույնն են
    """
    global user_warnings
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    target_id, _ = resolve_target_and_duration(update, context)
    if target_id is None:
        context.bot.send_message(
            chat_id=chat_id,
            text="Օգտագործեք /gwarn <ID> կամ reply արա օգտատիրոջը"
        )
        return

    if is_group_creator(context, chat_id, target_id):
        context.bot.send_message(chat_id=chat_id, text="❌ Չես կարող զգուշացնել խմբի հիմնադրին։")
        return

    if target_id == bot_creator_id:
        context.bot.send_message(chat_id=chat_id, text="❌ Չես կարող զգուշացնել բոտի հիմնադրին։")
        return

    # Անուն ստանալ
    try:
        member = context.bot.get_chat_member(chat_id, target_id)
        name = member.user.full_name or str(target_id)
    except Exception:
        name = str(target_id)

    user_warnings[target_id] = user_warnings.get(target_id, 0) + 1
    count = user_warnings[target_id]

    if count >= 3:
        try:
            if is_group_admin(context, chat_id, target_id):
                demote_admin(context, chat_id, target_id)
            context.bot.ban_chat_member(chat_id=chat_id, user_id=target_id)
            user_warnings[target_id] = 0
            context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 {name} ({target_id}) ստացել է 3 զգուշացում և ավտոմատ արգելվել է խմբից։"
            )
        except Exception as e:
            err = str(e)
            if "administrator" in err.lower() or "admin" in err.lower():
                context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ {name} ունի {count}/3 զգուշացում, բայց ադմին է — ban չհաջողվեց։ Հանեք ադմինությունը ձեռքով։"
                )
            else:
                context.bot.send_message(chat_id=chat_id, text=f"❌ Ban սխալ՝ {e}")
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ {name} ({target_id}) ստացել է զգուշացում ({count}/3)։"
        )


def unwarn_command(update, context):
    """Հանել զգուշացումը — /unwarn կամ /gunwarn"""
    global user_warnings
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    target_id, _ = resolve_target_and_duration(update, context)
    if target_id is None:
        context.bot.send_message(chat_id=chat_id, text="Օգտագործեք /gunwarn <ID> կամ reply արա")
        return

    try:
        member = context.bot.get_chat_member(chat_id, target_id)
        name = member.user.full_name or str(target_id)
    except Exception:
        name = str(target_id)

    if target_id in user_warnings and user_warnings[target_id] > 0:
        user_warnings[target_id] -= 1
        left = user_warnings[target_id]
        context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ {name}-ի զգուշացումը հանվել է։ Մնացել է՝ {left}/3"
        )
    else:
        context.bot.send_message(chat_id=chat_id, text=f"❌ {name}-ը զգուշացում չունի։")



def grouphelp_command(update, context):
    """Խմբային մոդերացիայի հրամաններ (միայն բոտի հիմնադիր)"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    text = (
        "🛡 **Խմբային մոդերացիա** (միայն բոտի հիմնադիր)\n\n"
        "/gban <ID> — արգելել խմբից (աշխատում է ադմինների վրա, բայց ոչ խմբի հիմնադրի)\n"
        "/gunban <ID> — հանել արգելքը\n"
        "/gmute <ID> [ժամանակ] — լռեցնել (1r=րոպե, 1h=ժամ, 1d=օր)\n"
        "/gunmute <ID> — բացել լռեցումը\n"
        "/warn <ID> — զգուշացում (3-ից հետո ավտո-ban)\n"
        "/gunwarn <ID> — հանել զգուշացումը\n\n"
        "💡 Կարող ես նաև reply անել օգտատիրոջ հաղորդագրությանը և գրել հրամանը։\n"
        "⚠️ Բոտը պետք է լինի խմբի ադմին (ban/restrict իրավունքներով)։"
    )
    try:
        context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"grouphelp error: {e}")





def say_command(update, context):
    """Բոտը գրում է հիմնադրի փոխարեն — միայն բոտի հիմնադիր
    - Խմբում /say տեքստ → գրում է այդ խմբում
    - Անձնականում /say տեքստ → ուղարկում է բոլոր խմբերին, որտեղ գտնվում է բոտը
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if not context.args:
        context.bot.send_message(
            chat_id=chat_id,
            text="Օգտագործեք /say <տեքստ>\n\n• Խմբում — գրում է այդ խմբում\n• Անձնականում — ուղարկում է բոլոր խմբերին, որտեղ գտնվում է բոտը"
        )
        return

    text = " ".join(context.args)

    # Անձնական չաթ — ուղարկել բոլոր խմբերին, որտեղ բոտը գտնվում է
    if chat_type == "private":
        targets = set(known_groups.keys())
        # Ավելացնել նաև games-ից (եթե որևէ խումբ դեռ known_groups-ում չէ)
        for cid, g in games.items():
            if g.group_chat_id:
                targets.add(g.group_chat_id)
            else:
                targets.add(cid)
        if not targets:
            context.bot.send_message(chat_id=chat_id, text="❌ Բոտը դեռ ոչ մի խմբում չկա։ Ավելացրեք բոտը խմբերում։")
            return
        sent = 0
        failed = 0
        for gid in targets:
            try:
                context.bot.send_message(chat_id=gid, text=text)
                sent += 1
            except Exception as e:
                failed += 1
                logger.error(f"say to {gid}: {e}")
        result = f"✅ Ուղարկվել է {sent} խմբի։"
        if failed:
            result += f"\n⚠️ Չհաջողվեց {failed} խմբում։"
        context.bot.send_message(chat_id=chat_id, text=result)
        return

    # Խմբում — գրել նույն խմբում
    try:
        context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ {e}")


def can_use_mod_tools(context, chat_id, user_id):
    """Բոտի հիմնադիր, խմբի ադմին կամ խմբի հիմնադիր"""
    if user_id == bot_creator_id or is_bot_admin(user_id):
        return True
    try:
        member = context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def pin_command(update, context):
    """Ամրացնել reply արված հաղորդագրությունը
    Կարող են՝ բոտի հիմնադիր, խմբի ադմին, խմբի հիմնադիր
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    if not can_use_mod_tools(context, chat_id, user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը միայն ադմինների և հիմնադրի համար է։")
        except Exception:
            pass
        return

    if not update.message.reply_to_message:
        context.bot.send_message(chat_id=chat_id, text="Պատասխանիր (reply) այն հաղորդագրությանը, որը ուզում ես ամրացնել, հետո գրիր /pin")
        return

    try:
        context.bot.pin_chat_message(
            chat_id=chat_id,
            message_id=update.message.reply_to_message.message_id,
            disable_notification=False
        )
        context.bot.send_message(chat_id=chat_id, text="📌 Հաղորդագրությունը ամրացված է։")
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ բոտը պետք է ունենա Pin messages իրավունք։\n{e}")


def unpin_command(update, context):
    """Ապամրացնել reply արված (կամ բոլոր) ամրացված հաղորդագրությունը
    Կարող են՝ բոտի հիմնադիր, խմբի ադմին, խմբի հիմնադիր
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if update.effective_chat.type not in ["group", "supergroup"]:
        context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը աշխատում է միայն խմբում։")
        return

    if not can_use_mod_tools(context, chat_id, user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը միայն ադմինների և հիմնադրի համար է։")
        except Exception:
            pass
        return

    if not update.message.reply_to_message:
        context.bot.send_message(chat_id=chat_id, text="Պատասխանիր (reply) ամրացված հաղորդագրությանը, հետո գրիր /unpin")
        return

    try:
        context.bot.unpin_chat_message(
            chat_id=chat_id,
            message_id=update.message.reply_to_message.message_id
        )
        context.bot.send_message(chat_id=chat_id, text="📌 Հաղորդագրությունն ապամրացված է։")
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ բոտը պետք է ունենա Pin messages իրավունք։\n{e}")


def id_command(update, context):
    """Ցույց տալ ID — reply կամ սեփական
    Կարող են՝ բոտի հիմնադիր, խմբի ադմին, խմբի հիմնադիր
    ID-ները սեղմելի են (copy), անունը՝ պրոֆիլի հղում
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if not can_use_mod_tools(context, chat_id, user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը միայն ադմինների և հիմնադրի համար է։")
        except Exception:
            pass
        return

    # Reply → այդ օգտատիրոջ ID
    if update.message.reply_to_message:
        t = update.message.reply_to_message.from_user
        name = t.full_name or "—"
        name_link = f'<a href="tg://user?id={t.id}">{name}</a>'
        uname = f"@{t.username}" if t.username else "—"
        text = (
            f"👤 Անուն՝ {name_link}\n"
            f"🆔 User ID՝ <code>{t.id}</code>\n"
            f"🔗 Username՝ {uname}\n"
            f"💬 Chat ID՝ <code>{chat_id}</code>"
        )
    else:
        u = update.effective_user
        name = u.full_name or "—"
        name_link = f'<a href="tg://user?id={u.id}">{name}</a>'
        uname = f"@{u.username}" if u.username else "—"
        text = (
            f"👤 Անուն՝ {name_link}\n"
            f"🆔 User ID՝ <code>{u.id}</code>\n"
            f"🔗 Username՝ {uname}\n"
            f"💬 Chat ID՝ <code>{chat_id}</code>"
        )

    try:
        context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=text.replace("<code>", "").replace("</code>", "").replace("<a href=\"tg://user?id=", "").replace("\">", " ").replace("</a>", ""))




def group_command(update, context):
    """Ցույց տալ բոլոր խմբերը, որտեղ գտնվում է բոտը — միայն բոտի հիմնադիր"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if not known_groups:
        if not games:
            context.bot.send_message(chat_id=chat_id, text="❌ Բոտը դեռ ոչ մի խմբում չկա։")
            return
        lines = ["📋 Բոտի խմբեր (games-ից)՝\n"]
        for i, (cid, g) in enumerate(games.items(), 1):
            lines.append(f"{i}. Chat ID: {cid}")
        context.bot.send_message(chat_id=chat_id, text="\n".join(lines))
        return

    lines = [f"📋 Բոտի խմբեր ({len(known_groups)} հատ)՝\n"]
    for i, (cid, info) in enumerate(known_groups.items(), 1):
        title = str(info.get("title", "—")).replace("<", "").replace(">", "")
        link = str(info.get("link", "—"))
        creator_username = str(info.get("creator_username", "—"))
        creator_name = str(info.get("creator_name", "—")).replace("<", "").replace(">", "")
        lines.append(
            f"{i}. 📛 {title}\n"
            f"   🔗 {link}\n"
            f"   👤 Հիմնադիր՝ {creator_name} ({creator_username})\n"
            f"   🆔 {cid}\n"
        )
    text = "\n".join(lines)
    try:
        if len(text) > 4000:
            chunk = ""
            for line in lines:
                if len(chunk) + len(line) > 3900:
                    context.bot.send_message(chat_id=chat_id, text=chunk, disable_web_page_preview=True)
                    chunk = line + "\n"
                else:
                    chunk += line + "\n"
            if chunk:
                context.bot.send_message(chat_id=chat_id, text=chunk, disable_web_page_preview=True)
        else:
            context.bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"group_command error: {e}")
        try:
            context.bot.send_message(chat_id=chat_id, text=text[:4000])
        except Exception:
            pass


def grban_command(update, context):
    """Խումբը սև ցուցակում — բոտը դուրս է գալիս և այլևս չի մտնի"""
    global blacklisted_groups
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    target_id = None
    if context.args:
        raw = context.args[0].strip().replace(" ", "")
        # Աջակցել -100... և սովորական թվերին
        if raw.lstrip("-").isdigit():
            target_id = int(raw)
    elif update.effective_chat.type in ["group", "supergroup"]:
        target_id = chat_id

    if target_id is None:
        context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🚫 Օգտագործում՝\n"
                "/grban <chat_id>\n\n"
                "Օրինակ՝ /grban -1001234567890\n"
                "Կամ խմբում գրիր պարզապես /grban"
            )
        )
        return

    # Ավելացնել սև ցուցակ
    blacklisted_groups.add(target_id)
    # Հնարավոր տարբերակներ (եթե -100 prefix չկա)
    if target_id > 0:
        blacklisted_groups.add(-target_id)
        blacklisted_groups.add(int(f"-100{target_id}"))
    known_groups.pop(target_id, None)
    save_data()

    # Դուրս գալ խմբից
    left = False
    leave_error = None
    ids_to_try = [target_id]
    if target_id > 0:
        ids_to_try.extend([-target_id, int(f"-100{target_id}")])
    elif str(target_id).startswith("-") and not str(target_id).startswith("-100"):
        # հին group id → փորձել -100 տարբերակ
        ids_to_try.append(int(f"-100{abs(target_id)}"))

    for tid in ids_to_try:
        try:
            context.bot.leave_chat(tid)
            left = True
            target_id = tid
            blacklisted_groups.add(tid)
            break
        except Exception as e:
            leave_error = str(e)
            logger.error(f"grban leave_chat {tid}: {e}")

    # Գեղեցիկ պատասխան
    if left:
        msg = (
            f"🚫 Խումբը արգելափակված է\n\n"
            f"🆔 Chat ID՝ {target_id}\n"
            f"✅ Բոտը դուրս եկավ խմբից\n"
            f"🔒 Այլևս չեն կարող ավելացնել բոտը այս խմբում"
        )
    else:
        msg = (
            f"🚫 Խումբը ավելացվեց սև ցուցակում\n\n"
            f"🆔 Chat ID՝ {target_id}\n"
            f"⚠️ Դուրս գալ չհաջողվեց (գուցե բոտն արդեն չկա այդ խմբում)\n"
            f"🔒 Եթե նորից ավելացնեն — բոտը ավտոմատ կդուրս գա\n"
        )
        if leave_error:
            msg += f"\nՍխալ՝ {leave_error}"

    # Միշտ ուղարկել հիմնադրի անձնական չաթ
    try:
        context.bot.send_message(chat_id=user_id, text=msg)
    except Exception:
        try:
            context.bot.send_message(chat_id=chat_id, text=msg)
        except Exception:
            pass


def urban_command(update, context):
    """Հանել խումբը սև ցուցակից"""
    global blacklisted_groups
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if not context.args or not context.args[0].lstrip("-").isdigit():
        # Ցույց տալ ցուցակը
        if not blacklisted_groups:
            context.bot.send_message(chat_id=chat_id, text="Սև ցուցակը դատարկ է։\nՕգտագործեք՝ /urban <chat_id>")
            return
        lines = ["🚫 Սև ցուցակի խմբեր՝\n"] + [f"• `{cid}`" for cid in blacklisted_groups]
        lines.append("\nՀանելու համար՝ /urban <chat_id>")
        context.bot.send_message(chat_id=chat_id, text="\n".join(lines), parse_mode="Markdown")
        return

    target_id = int(context.args[0])
    if target_id in blacklisted_groups:
        blacklisted_groups.discard(target_id)
        save_data()
        context.bot.send_message(chat_id=chat_id, text=f"✅ Խումբը ({target_id}) հանվեց սև ցուցակից։ Այժմ կարող են կրկին ավելացնել բոտը։")
    else:
        context.bot.send_message(chat_id=chat_id, text=f"❌ {target_id}-ը սև ցուցակում չէ։")


# ================== /show — ԴԵՐԵՐԻ ԿԱՐԳԱՎՈՐՈՒՄ ==================

def _show_roles_text(n):
    roles = get_roles_for_count(n)
    from collections import Counter
    counts = Counter(roles)
    lines = [f"🎭 <b>{n} խաղացող</b>\n"]
    for role, cnt in counts.items():
        lines.append(f"  • {role.value} × {cnt}")
    custom = " (փոփոխված)" if n in custom_role_setups else " (default)"
    lines[0] = f"🎭 <b>{n} խաղացող</b>{custom}\n"
    return "\n".join(lines)


def _show_detail_keyboard(n):
    roles = get_roles_for_count(n)
    from collections import Counter
    counts = Counter(roles)
    keyboard = []
    # + / - for each role type present or all roles
    row = []
    for role in Role:
        cnt = counts.get(role, 0)
        row.append(InlineKeyboardButton(f"+{role.value.split()[-1] if ' ' in role.value else role.value}", callback_data=f"show_add_{n}_{role.name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    # remove buttons for roles that exist
    row = []
    for role, cnt in counts.items():
        if cnt > 0:
            row.append(InlineKeyboardButton(f"− {role.value} ({cnt})", callback_data=f"show_rem_{n}_{role.name}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔄 Վերականգնել default", callback_data=f"show_reset_{n}")])
    keyboard.append([InlineKeyboardButton("⬅️ Հետ", callback_data="show_main")])
    return InlineKeyboardMarkup(keyboard)


def show_command(update, context):
    """Դերերի կարգավորում մենյու — միայն հիմնադիր"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    keyboard = []
    row = []
    for n in range(4, 21):
        mark = "✏️" if n in custom_role_setups else ""
        row.append(InlineKeyboardButton(f"{n}{mark}", callback_data=f"show_n_{n}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔄 Վերականգնել բոլորը", callback_data="show_reset_all")])
    keyboard.append([InlineKeyboardButton("❌ Փակել", callback_data="show_close")])

    try:
        context.bot.send_message(
            chat_id=user_id,
            text="🎭 <b>Դերերի բաշխում ըստ խաղացողների քանակի</b>\n\nԸնտրեք խաղացողների քանակը՝ փոփոխելու համար։\n✏️ = արդեն փոփոխված",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        if chat_id != user_id:
            try:
                msg = context.bot.send_message(chat_id=chat_id, text="🎭 Դերերի մենյուն բացվել է բոտի անձնական չաթում։")
                threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
            except Exception:
                pass
    except telegram.error.Unauthorized:
        context.bot.send_message(chat_id=chat_id, text="Խնդրում ենք սկզբում /start անել բոտի անձնական չաթում։")
    except Exception as e:
        logger.error(f"show_command error: {e}")


def show_callback(update, context):
    """/show մենյուի callback-ներ"""
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != bot_creator_id:
        query.answer("Միայն հիմնադիրը")
        return

    data = query.data
    query.answer()

    try:
        if data == "show_main":
            keyboard = []
            row = []
            for n in range(4, 21):
                mark = "✏️" if n in custom_role_setups else ""
                row.append(InlineKeyboardButton(f"{n}{mark}", callback_data=f"show_n_{n}"))
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🔄 Վերականգնել բոլորը", callback_data="show_reset_all")])
            keyboard.append([InlineKeyboardButton("❌ Փակել", callback_data="show_close")])
            query.message.edit_text(
                text="🎭 <b>Դերերի բաշխում ըստ խաղացողների քանակի</b>\n\nԸնտրեք խաղացողների քանակը։\n✏️ = փոփոխված",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return

        if data == "show_close":
            try:
                query.message.delete()
            except Exception:
                query.message.edit_text("Փակված է։")
            return

        if data == "show_reset_all":
            custom_role_setups.clear()
            save_data()
            query.answer("Բոլորը վերականգնված են")
            # back to main
            query.data = "show_main"
            show_callback(update, context)
            return

        if data.startswith("show_n_"):
            n = int(data.replace("show_n_", ""))
            text = _show_roles_text(n) + "\n\n➕ Ավելացնել դեր (փոխարինում է Բնակչին)\n➖ Հեռացնել դեր (դառնում է Բնակիչ)"
            query.message.edit_text(
                text=text,
                reply_markup=_show_detail_keyboard(n),
                parse_mode="HTML"
            )
            return

        if data.startswith("show_add_"):
            # show_add_8_MANIAC
            parts = data.split("_")
            n = int(parts[2])
            role_name = parts[3]
            role = Role[role_name]
            roles = get_roles_for_count(n)

            # Դոն կարող է լինել միայն 1-ը — եթե արդեն կա Դոն, ավելացնել Մաֆիա
            if role == Role.MAFIA and Role.MAFIA in roles:
                role = Role.MAFIA_SUB
            # Եթե սեղմել են Մաֆիա, բայց Դոն չկա — ավելացնել որպես Մաֆիա (ոչ Դոն)
            # (MAFIA_SUB մնում է MAFIA_SUB)

            if Role.CITIZEN in roles:
                idx = roles.index(Role.CITIZEN)
                roles[idx] = role
                custom_role_setups[n] = roles
                save_data()
                query.answer(f"Ավելացվեց {role.value}")
            else:
                query.answer("Տեղ չկա — նախ հեռացրեք այլ դեր")
            text = _show_roles_text(n) + "\n\n➕ Ավելացնել դեր (փոխարինում է Բնակչին)\n➖ Հեռացնել դեր (դառնում է Բնակիչ)\n⚠️ Դոն՝ միայն 1"
            query.message.edit_text(text=text, reply_markup=_show_detail_keyboard(n), parse_mode="HTML")
            return

        if data.startswith("show_rem_"):
            parts = data.split("_")
            n = int(parts[2])
            role_name = parts[3]
            role = Role[role_name]
            roles = get_roles_for_count(n)
            if role in roles and role != Role.CITIZEN:
                idx = roles.index(role)
                roles[idx] = Role.CITIZEN
                custom_role_setups[n] = roles
                save_data()
                query.answer(f"Հեռացվեց {role.value}")
            else:
                query.answer("Չի հնարավոր")
            text = _show_roles_text(n) + "\n\n➕ Ավելացնել դեր (փոխարինում է Բնակչին)\n➖ Հեռացնել դեր (դառնում է Բնակիչ)"
            query.message.edit_text(text=text, reply_markup=_show_detail_keyboard(n), parse_mode="HTML")
            return

        if data.startswith("show_reset_"):
            n = int(data.replace("show_reset_", ""))
            custom_role_setups.pop(n, None)
            save_data()
            query.answer(f"{n} խաղացող — default")
            text = _show_roles_text(n) + "\n\n➕ Ավելացնել դեր (փոխարինում է Բնակչին)\n➖ Հեռացնել դեր (դառնում է Բնակիչ)"
            query.message.edit_text(text=text, reply_markup=_show_detail_keyboard(n), parse_mode="HTML")
            return
    except Exception as e:
        logger.error(f"show_callback error: {e}")
        query.answer("Սխալ")


def balance_command(update, context):
    """⭐ Բոտի Stars բալանս և վաճառքների պատմություն — միայն հիմնադիր և բոտի ադմիններ"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    total = stars_total_earned
    purchases = stars_purchases
    count = len(purchases)

    # Փորձել Telegram API բալանս (եթե գրադարանը աջակցում է)
    api_balance = None
    try:
        if hasattr(context.bot, "get_my_star_balance"):
            bal = context.bot.get_my_star_balance()
            api_balance = getattr(bal, "amount", None) or getattr(bal, "star_count", None)
        elif hasattr(context.bot, "getMyStarBalance"):
            bal = context.bot.getMyStarBalance()
            api_balance = getattr(bal, "amount", None)
    except Exception as e:
        logger.info(f"getMyStarBalance not available: {e}")

    lines = [
        "⭐ <b>ԲՈՏԻ STARS ԲԱԼԱՆՍ</b>\n",
        f"💰 Ընդհանուր ստացված (բոտի հաշվառում)՝ <b>{total} Stars</b>",
        f"🛒 Գնումների քանակ՝ <b>{count}</b>",
    ]
    if api_balance is not None:
        lines.append(f"🏦 Telegram API բալանս՝ <b>{api_balance} Stars</b>")
    else:
        lines.append("🏦 Telegram API բալանս՝ հասանելի չէ այս տարբերակում (տես բոտի պրոֆիլ / Fragment)")

    lines.append("")
    if purchases:
        lines.append("📋 <b>Վերջին գնումներ</b> (մինչև 10)\n")
        for p in reversed(purchases[-10:]):
            t = p.get("time", "")[:16].replace("T", " ")
            lines.append(
                f"• {p.get('name', '?')} ({p.get('username', '—')})\n"
                f"  🆔 <code>{p.get('user_id')}</code>\n"
                f"  🎭 {p.get('role_value', p.get('role', '?'))} — <b>{p.get('stars', 0)}⭐</b>\n"
                f"  🕐 {t}\n"
            )
    else:
        lines.append("Դեռ գնումներ չկան։")

    lines.append(
        "\n💡 Stars-ները հավաքվում են բոտի հաշվին։\n"
        "Հանելու համար՝ <a href=\"https://fragment.com\">Fragment.com</a>"
    )

    try:
        context.bot.send_message(
            chat_id=chat_id if update.effective_chat.type != "private" else user_id,
            text="\n".join(lines),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"balance_command: {e}")
        try:
            context.bot.send_message(chat_id=user_id, text="\n".join(lines), parse_mode="HTML")
        except Exception:
            pass


def loading_command(update, context):
    """Խաղի վիճակի վերականգնում — միայն բոտի հիմնադիր և բոտի ադմիններ
    /loading — բեռնել պահված ակտիվ խաղերը և ցույց տալ վիճակը
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    try:
        count = load_games()
        active = [(cid, g) for cid, g in games.items() if g.state != GameState.IDLE and g.players]
        lines = [
            "♻️ <b>Խաղի վիճակի վերականգնում</b>\n",
            f"📂 Բեռնված ակտիվ խաղեր՝ <b>{count}</b>\n",
        ]
        if active:
            lines.append("🎮 Ակտիվ խաղեր՝\n")
            for cid, g in active:
                alive = sum(1 for p in g.players.values() if p.get("alive"))
                total = len(g.players)
                state_name = g.state.name if g.state else "?"
                title = known_groups.get(cid, {}).get("title", str(cid))
                lines.append(
                    f"• <b>{title}</b>\n"
                    f"  🆔 <code>{cid}</code>\n"
                    f"  📊 {alive}/{total} կենդանի | Փուլ՝ {state_name} | Գիշեր՝ {g.night_count}\n"
                )
                # Ծանուցել խմբին
                try:
                    context.bot.send_message(
                        chat_id=cid,
                        text=(
                            "♻️ Բոտը վերագործարկվել է։\n"
                            f"Խաղը վերականգնված է։\n"
                            f"Փուլ՝ {state_name} | Կենդանի՝ {alive}/{total}\n"
                            "Շարունակեք խաղը։"
                        )
                    )
                except Exception as e:
                    logger.error(f"Notify restore to {cid}: {e}")
        else:
            lines.append("Ակտիվ խաղեր չկան։")

        context.bot.send_message(
            chat_id=chat_id if update.effective_chat.type != "private" else user_id,
            text="\n".join(lines),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"loading_command error: {e}")
        try:
            context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ {e}")
        except Exception:
            pass


def rek_command(update, context):
    """/rek — բովանդակություն ուղարկել բոլոր օգտատերերին
    Միայն բոտի հիմնադիր և բոտի ադմիններ։
    Գրում ես /rek → բոտը սպասում է քո հաղորդագրությանը (տեքստ, նկար, գիֆ, ստիկեր...)
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if not is_bot_admin(user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    rek_awaiting.add(user_id)
    text = (
        "📢 <b>Ռեկլամ / Հաղորդագրություն բոլորին</b>\n\n"
        "Հիմա ուղարկիր այն, ինչ ուզում ես տարածել բոլոր օգտատերերին։\n\n"
        "✅ Կարող ես ուղարկել՝\n"
        "• Տեքստ\n"
        "• Նկար (photo)\n"
        "• Գիֆ / անիմացիա\n"
        "• Ստիկեր\n"
        "• Վիդեո\n"
        "• Փաստաթուղթ\n\n"
        "❌ Չեղարկելու համար գրիր /cancel\n\n"
        "⬇️ Ուղարկիր բովանդակությունը հիմա..."
    )
    try:
        # Միշտ անձնական չաթում
        context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
        if chat_id != user_id:
            try:
                msg = context.bot.send_message(chat_id=chat_id, text="📢 /rek մենյուն բացվել է բոտի անձնական չաթում։")
                threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
            except Exception:
                pass
    except telegram.error.Unauthorized:
        context.bot.send_message(chat_id=chat_id, text="Խնդրում ենք սկզբում /start անել բոտի անձնական չաթում։")
    except Exception as e:
        logger.error(f"rek_command error: {e}")


def handle_rek_message(update, context):
    """/rek-ից հետո ստացված բովանդակությունը ուղարկել բոլորին"""
    if not update.message or not update.effective_user:
        return
    user_id = update.effective_user.id
    if user_id not in rek_awaiting:
        return
    if update.effective_chat.type != "private":
        return

    # Cancel
    if update.message.text and update.message.text.strip().startswith("/cancel"):
        rek_awaiting.discard(user_id)
        try:
            context.bot.send_message(chat_id=user_id, text="❌ Ռեկլամը չեղարկված է։")
        except Exception:
            pass
        return

    # Եթե հրաման է — չենք վերցնում
    if update.message.text and update.message.text.strip().startswith("/"):
        return

    rek_awaiting.discard(user_id)

    # Հավաքել բՈԼՈՐ գրանցված օգտատերերին
    targets = set(known_users)
    targets.update(user_stats.keys())
    targets.update(user_owned_roles.keys())
    for g in games.values():
        targets.update(g.players.keys())
    if bot_creator_id:
        targets.add(bot_creator_id)
    targets.update(bot_admins)
    targets.discard(None)
    targets.discard(0)

    if not targets:
        try:
            context.bot.send_message(
                chat_id=user_id,
                text="❌ Ոչ մի գրանցված օգտատեր չկա։ Մարդիկ պետք է գոնե մեկ անգամ /start անեն բոտում։"
            )
        except Exception:
            pass
        return

    sent = 0
    failed = 0
    msg = update.message

    for tid in list(targets):
        try:
            if msg.photo:
                context.bot.send_photo(
                    chat_id=tid,
                    photo=msg.photo[-1].file_id,
                    caption=msg.caption or None
                )
            elif msg.animation:
                context.bot.send_animation(
                    chat_id=tid,
                    animation=msg.animation.file_id,
                    caption=msg.caption or None
                )
            elif msg.sticker:
                context.bot.send_sticker(chat_id=tid, sticker=msg.sticker.file_id)
            elif msg.video:
                context.bot.send_video(
                    chat_id=tid,
                    video=msg.video.file_id,
                    caption=msg.caption or None
                )
            elif msg.document:
                context.bot.send_document(
                    chat_id=tid,
                    document=msg.document.file_id,
                    caption=msg.caption or None
                )
            elif msg.voice:
                context.bot.send_voice(chat_id=tid, voice=msg.voice.file_id, caption=msg.caption or None)
            elif msg.video_note:
                context.bot.send_video_note(chat_id=tid, video_note=msg.video_note.file_id)
            elif msg.text:
                context.bot.send_message(chat_id=tid, text=msg.text)
            else:
                # fallback — copy message
                context.bot.copy_message(chat_id=tid, from_chat_id=msg.chat_id, message_id=msg.message_id)
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"rek to {tid}: {e}")

    try:
        context.bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ Ռեկլամն ուղարկված է։\n\n"
                f"📤 Հաջող՝ <b>{sent}</b>\n"
                f"⚠️ Չհաջողվեց՝ <b>{failed}</b>\n"
                f"👥 Ընդհանուր թիրախ՝ <b>{len(targets)}</b>"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass


def userinfo_command(update, context):
    """Օգտատիրոջ պատմություն — միայն բոտի հիմնադիր և խմբի ադմիններ
    Օգտագործում՝ /userinfo <ID> կամ reply + /userinfo
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    # Միայն հիմնադիր, բոտի ադմին կամ խմբի ադմին
    if not can_use_mod_tools(context, chat_id, user_id):
        try:
            context.bot.send_message(chat_id=chat_id, text="❌ Այս հրամանը միայն բոտի հիմնադրի և խմբի ադմինների համար է։")
        except Exception:
            pass
        return

    target_id = None
    # Reply-ից
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        arg = context.args[0].strip().replace("@", "")
        if arg.lstrip("-").isdigit():
            target_id = int(arg)
        else:
            # Փորձել գտնել անունով խաղացողներից
            game = get_game(chat_id)
            for uid, p in game.players.items():
                if arg.lower() in p.get("name", "").lower():
                    target_id = uid
                    break
            if target_id is None:
                # Փնտրել user_stats-ում
                for uid, st in user_stats.items():
                    if arg.lower() in st.get("name", "").lower():
                        target_id = uid
                        break

    if target_id is None:
        context.bot.send_message(
            chat_id=chat_id,
            text="📋 Օգտագործեք՝\n/userinfo <ID>\nկամ reply արա օգտատիրոջը + /userinfo"
        )
        return

    # Հավաքել տվյալներ
    st = user_stats.get(target_id, {})
    games_played = st.get("games", 0)
    wins = st.get("wins", 0)
    losses = max(0, games_played - wins)
    winrate = f"{(wins / games_played * 100):.1f}%" if games_played > 0 else "—"
    name = st.get("name") or str(target_id)
    last_seen = st.get("last_seen", "—")
    if last_seen != "—":
        try:
            last_seen = datetime.fromisoformat(last_seen).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

    # Telegram-ից անուն/username
    tg_name = name
    tg_username = "—"
    try:
        member = context.bot.get_chat_member(chat_id, target_id) if update.effective_chat.type in ["group", "supergroup"] else None
        if member:
            tg_name = member.user.full_name or name
            tg_username = f"@{member.user.username}" if member.user.username else "—"
        else:
            chat = context.bot.get_chat(target_id)
            tg_name = chat.full_name or chat.first_name or name
            tg_username = f"@{chat.username}" if getattr(chat, "username", None) else "—"
    except Exception:
        pass

    # Զգուշացումներ և ban
    warns = user_warnings.get(target_id, 0)
    is_banned = target_id in banned_users
    ban_status = "🚫 Արգելված է խաղալ" if is_banned else "✅ Կարող է խաղալ"

    # Ամենաշատ խաղացած դերեր
    roles_played = st.get("roles_played", {})
    roles_text = "—"
    if roles_played:
        sorted_roles = sorted(roles_played.items(), key=lambda x: -x[1])[:5]
        role_lines = []
        for rn, cnt in sorted_roles:
            try:
                role_val = Role[rn].value
            except Exception:
                role_val = rn
            role_lines.append(f"  • {role_val} — {cnt}x")
        roles_text = "\n".join(role_lines)

    name_link = f'<a href="tg://user?id={target_id}">{tg_name}</a>'

    text = (
        f"👤 <b>Օգտատիրոջ պատմություն</b>\n\n"
        f"📛 Անուն՝ {name_link}\n"
        f"🔗 Username՝ {tg_username}\n"
        f"🆔 ID՝ <code>{target_id}</code>\n\n"
        f"🎮 Խաղեր՝ {games_played}\n"
        f"🏆 Հաղթանակներ՝ {wins}\n"
        f"💀 Պարտություններ՝ {losses}\n"
        f"📊 Winrate՝ {winrate}\n\n"
        f"⚠️ Զգուշացումներ՝ {warns}/3\n"
        f"{ban_status}\n\n"
        f"🎭 Ամենաշատ խաղացած դերեր՝\n{roles_text}\n\n"
        f"🕐 Վերջին խաղ՝ {last_seen}"
    )

    try:
        context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"userinfo_command error: {e}")
        try:
            context.bot.send_message(chat_id=chat_id, text=text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").replace(f'<a href="tg://user?id={target_id}">', "").replace("</a>", ""))
        except Exception:
            pass


def give_command(update, context):
    """Հիմնադիրը տալիս է սուպեր դեր օգտատիրոջը
    Օգտագործում՝ /give <ID>
    Բացվում է դերերի ցանկ → ընտրում ես դերը → տրվում է օգտատիրոջը։
    Խաղին միանալիս օգտատիրոջը կստանա կոճակներ՝ օգտագործել / չօգտագործել։
    """
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    target_id = None
    # Reply-ից
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        arg = context.args[0].strip().replace("@", "")
        if arg.lstrip("-").isdigit():
            target_id = int(arg)

    if target_id is None:
        try:
            context.bot.send_message(
                chat_id=chat_id if update.effective_chat.type == "private" else user_id,
                text=(
                    "🎁 <b>/give — Սուպեր դեր տալ</b>\n\n"
                    "Օգտագործում՝\n"
                    "/give &lt;ID&gt;\n"
                    "կամ reply արա օգտատիրոջը + /give\n\n"
                    "Օրինակ՝ <code>/give 123456789</code>"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    # Դերերի ցանկ
    keyboard = []
    row = []
    for role in Role:
        short = role.value if len(role.value) <= 22 else role.value[:20] + "…"
        row.append(InlineKeyboardButton(short, callback_data=f"give_role_{target_id}_{role.name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Չեղարկել", callback_data="give_cancel")])

    # Փորձել անուն ստանալ
    target_name = str(target_id)
    try:
        if update.effective_chat.type in ["group", "supergroup"]:
            member = context.bot.get_chat_member(chat_id, target_id)
            target_name = member.user.full_name or str(target_id)
        else:
            chat = context.bot.get_chat(target_id)
            target_name = chat.full_name or chat.first_name or str(target_id)
    except Exception:
        pass

    text = (
        f"🎁 <b>Սուպեր դեր տալ</b>\n\n"
        f"👤 Ստացող՝ <a href=\"tg://user?id={target_id}\">{target_name}</a>\n"
        f"🆔 ID՝ <code>{target_id}</code>\n\n"
        f"Ընտրիր դերը, որը ուզում ես տալ․"
    )
    try:
        # Միշտ ուղարկել հիմնադրի անձնական չաթ
        context.bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        if chat_id != user_id:
            try:
                msg = context.bot.send_message(chat_id=chat_id, text="🎁 Դերի ընտրության մենյուն բացվել է անձնական չաթում։")
                threading.Timer(5, lambda: delete_message(context, chat_id, msg.message_id)).start()
            except Exception:
                pass
    except telegram.error.Unauthorized:
        context.bot.send_message(chat_id=chat_id, text="Խնդրում ենք սկզբում /start անել բոտի անձնական չաթում։")
    except Exception as e:
        logger.error(f"give_command error: {e}")
        try:
            context.bot.send_message(chat_id=chat_id, text=f"❌ Սխալ՝ {e}")
        except Exception:
            pass


def give_role_callback(update, context):
    """/give-ից դերի ընտրություն → ավելացնել user_owned_roles-ում"""
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != bot_creator_id:
        query.answer("Միայն հիմնադիրը", show_alert=True)
        return

    data = query.data

    if data == "give_cancel":
        query.answer("Չեղարկված է")
        try:
            query.message.edit_text("❌ Դեր տալը չեղարկված է։")
        except Exception:
            pass
        return

    if not data.startswith("give_role_"):
        return

    # give_role_TARGETID_ROLENAME
    rest = data.replace("give_role_", "", 1)
    parts = rest.split("_", 1)
    if len(parts) != 2:
        query.answer("Սխալ տվյալ", show_alert=True)
        return

    try:
        target_id = int(parts[0])
        role_name = parts[1]
        role = Role[role_name]
    except Exception as e:
        query.answer(f"Սխալ՝ {e}", show_alert=True)
        return

    # Ավելացնել user_owned_roles-ում (նույն համակարգը ինչ գնված դերերին)
    global user_owned_roles
    if target_id not in user_owned_roles:
        user_owned_roles[target_id] = []
    if role_name not in user_owned_roles[target_id]:
        user_owned_roles[target_id].append(role_name)
    else:
        # Արդեն ունի — միևնույն է թողնենք (կարող է ունենալ մի քանի)
        pass

    # known_users-ում ավելացնել
    if target_id not in known_users:
        known_users.add(target_id)

    save_data()
    query.answer("✅ Դերը տրվեց")

    target_name = str(target_id)
    try:
        chat = context.bot.get_chat(target_id)
        target_name = chat.full_name or chat.first_name or str(target_id)
    except Exception:
        pass

    # Հիմնադրին հաստատում
    try:
        query.message.edit_text(
            f"✅ <b>Սուպեր դերը տրվեց</b>\n\n"
            f"👤 Ստացող՝ <a href=\"tg://user?id={target_id}\">{target_name}</a>\n"
            f"🆔 ID՝ <code>{target_id}</code>\n"
            f"🎭 Դեր՝ {role.value}\n\n"
            f"Խաղին միանալիս նրան կհարցվի՝ օգտագործե՞լ այս դերը։",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"give_role_callback edit: {e}")

    # Օգտատիրոջը ծանուցում
    try:
        context.bot.send_message(
            chat_id=target_id,
            text=(
                f"🎁 <b>Ստացար սուպեր դեր!</b>\n\n"
                f"🎭 Դեր՝ <b>{role.value}</b>\n\n"
                f"Հաջորդ խաղին միանալիս բոտը կհարցնի քեզ կոճակներով՝\n"
                f"✅ Օգտագործել այս դերը\n"
                f"🎲 Չօգտագործել (պատահական դեր)\n\n"
                f"Եթե սեղմես «Օգտագործել» — խաղում կստանաս հենց այս դերը։"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"give_role notify user {target_id}: {e}")
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=f"⚠️ Դերը տրվեց, բայց օգտատիրոջը հաղորդագրություն չհաջողվեց ուղարկել (գուցե /start չի արել)։\nID՝ {target_id}"
            )
        except Exception:
            pass


def manch_command(update, context):
    """Հիմնադրի բոլոր հրամանների ցուցակ"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return
    text = (
        "👑 **Հիմնադրի հրամաններ**\n\n"
        "📋 **Բոտի կառավարում**\n"
        "/admins — բոտի ադմիններ\n"
        "/setadmin <ID> — նշանակել ադմին\n"
        "/removeadmin <ID> — հեռացնել ադմին\n"
        "/announce <տեքստ> — բոլոր խմբերին\n"
        "/reload — վերագործարկել\n"
        "/broadcast <տեքստ> — բոլոր խաղացողներին\n"
        "/kick <անուն> — հեռացնել խաղից\n"
        "/ban <ID> — արգելել խաղալ\n"
        "/unban <ID> — հանել խաղի արգելքը\n"
        "/give <ID> — տալ սուպեր դեր (ընտրում ես ցանկից)\n"
        "/allroles /roles /status /setdurations\n"
        "/setcreator — ցույց տալ հիմնադրի ID\n"
        "/group — բոտի բոլոր խմբերը (հղում + հիմնադիր)\n"
        "/show — դերերի կարգավորում (ըստ խաղացողների)\n"
        "/grban <id> — խումբը սև ցուցակ (բոտը դուրս է գալիս)\n"
        "/urban <id> — հանել սև ցուցակից\n\n"
        "🔇 **Լռեցում**\n"
        "/muteall — ջնջել բոլորի գրածը (միայն դու կարող ես գրել)\n"
        "/unmuteall — բացել muteall\n"
        "/dmute — կոշտ փակել խումբը\n"
        "/dunmute — բացել dmute\n\n"
        "🛡 **Խմբային մոդերացիա**\n"
        "/grouphelp — մոդերացիայի ցուցակ\n"
        "/gban /gunban — արգելել/հանել խմբից\n"
        "/gmute [ժամանակ] /gunmute — լռեցնել\n"
        "/gwarn /gunwarn — զգուշացում (3→ban)\n\n"
        "✨ **Այլ**\n"
        "/say <տեքստ> — բոտը գրում է բոլոր խմբերում (անձնականից)\n"
        "/reply <ID> <տեքստ> — պատասխանել օգնության հարցին\n"
        "/pin — ամրացնել (reply)\n"
        "/unpin — ապամրացնել (reply)\n"
        "/id — ցույց տալ ID (reply կամ սեփական)\n"
        "/userinfo <ID> — օգտատիրոջ պատմություն (խաղեր, winrate, դերեր)\n"
        "/loading — խաղի վիճակի վերականգնում\n"
        "/balance — Stars բալանս և գնումների պատմություն\n"
        "/rek — ռեկլամ/հաղորդագրություն բոլոր օգտատերերին\n"
        "/manch — այս ցուցակը"
    )
    try:
        context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"manch_command error: {e}")



def help_contact(update, context):
    """Օգնություն կոճակ — օգտատերը կարող է հարց գրել հիմնադրին"""
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    help_awaiting.add(user_id)
    try:
        query.message.reply_text(
            "🆘 Գրեք ձեր հարցը այս չաթում։\n"
            "Այն կուղարկվի բոտի հիմնադրին՝ ձեր անունով և ID-ով։\n\n"
            "Չեղարկելու համար գրեք /cancel"
        )
    except Exception as e:
        logger.error(f"help_contact error: {e}")


def handle_help_message(update, context):
    """Օգտատերի հարցը ուղարկել հիմնադրին"""
    user = update.effective_user
    user_id = user.id
    if user_id not in help_awaiting:
        return
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if text.startswith("/"):
        return

    help_awaiting.discard(user_id)

    name = user.full_name or "—"
    username = f"@{user.username}" if user.username else "—"
    msg = (
        f"🆘 **Նոր հարց**\n\n"
        f"👤 Անուն՝ {name}\n"
        f"🔗 Username՝ {username}\n"
        f"🆔 ID՝ `{user_id}`\n\n"
        f"💬 Հարց՝\n{text}\n\n"
        f"Պատասխանել՝ `/reply {user_id} ձեր պատասխանը`"
    )
    try:
        if bot_creator_id:
            context.bot.send_message(
                chat_id=bot_creator_id,
                text=msg,
                parse_mode="Markdown"
            )
        context.bot.send_message(
            chat_id=user_id,
            text="✅ Ձեր հարցն ուղարկվել է բոտի հիմնադրին։ Շուտով կպատասխանեն։"
        )
    except Exception as e:
        logger.error(f"handle_help_message error: {e}")
        try:
            context.bot.send_message(chat_id=user_id, text="❌ Չհաջողվեց ուղարկել։ Փորձեք կրկին։")
        except Exception:
            pass


def cancel_help(update, context):
    """Չեղարկել օգնության հարցը կամ /rek-ը"""
    user_id = update.effective_user.id
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()
    cancelled = False
    if user_id in help_awaiting:
        help_awaiting.discard(user_id)
        context.bot.send_message(chat_id=user_id, text="❌ Օգնության հարցը չեղարկված է։")
        cancelled = True
    if user_id in rek_awaiting:
        rek_awaiting.discard(user_id)
        context.bot.send_message(chat_id=user_id, text="❌ Ռեկլամը չեղարկված է։")
        cancelled = True
    if not cancelled:
        context.bot.send_message(chat_id=user_id, text="Ակտիվ գործողություն չկա։")


def reply_command(update, context):
    """Հիմնադիրը պատասխանում է օգտատիրոջը՝ /reply <ID> <տեքստ>"""
    message_id = update.message.message_id
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    threading.Timer(0.3, lambda: delete_message(context, chat_id, message_id)).start()

    if user_id != bot_creator_id:
        try:
            context.bot.send_message(chat_id=chat_id, text=get_text("only_bot_admin", "hy"))
        except Exception:
            pass
        return

    if not context.args or len(context.args) < 2:
        context.bot.send_message(
            chat_id=chat_id,
            text="Օգտագործեք՝ /reply <ID> <պատասխան>\nՕրինակ՝ /reply 123456789 Բարև, պատասխանս է..."
        )
        return

    target_arg = context.args[0].strip()
    if not target_arg.lstrip("-").isdigit():
        context.bot.send_message(chat_id=chat_id, text="❌ Առաջին արգումենտը պետք է լինի թվային ID։")
        return

    target_id = int(target_arg)
    reply_text = " ".join(context.args[1:])

    try:
        context.bot.send_message(
            chat_id=target_id,
            text=f"📩 **Պատասխան բոտի հիմնադրից**\n\n{reply_text}",
            parse_mode="Markdown"
        )
        context.bot.send_message(chat_id=chat_id, text=f"✅ Պատասխանն ուղարկվել է {target_id}-ին։")
    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"❌ Չհաջողվեց ուղարկել։ Օգտատերը գուցե չի սկսել բոտը։\n{e}")



def anti_command_spam(update, context):
    """Anti-spam՝ եթե օգտատերը շատ հաճախ է ուղարկում բոտի հրամաններ՝ 5 րոպե mute
    Աշխատում է միայն խմբերում։ Հիմնադիրը և բոտի ադմինները չեն ազդվում։
    """
    try:
        if not update.message or not update.effective_user:
            return
        chat = update.effective_chat
        if not chat or chat.type not in ["group", "supergroup"]:
            return

        user_id = update.effective_user.id
        chat_id = chat.id
        message_id = update.message.message_id

        # Հիմնադիր և բոտի ադմիններ — չենք mute անում
        if user_id == bot_creator_id or is_bot_admin(user_id):
            return

        now = datetime.now()
        times = command_spam_tracker.get(user_id, [])
        # Մաքրել հին գրառումները
        times = [t for t in times if (now - t).total_seconds() < SPAM_WINDOW_SECONDS]
        times.append(now)
        command_spam_tracker[user_id] = times

        if len(times) < SPAM_MAX_COMMANDS:
            return

        # Սպամ հայտնաբերված — mute 5 րոպե
        command_spam_tracker[user_id] = []
        try:
            from telegram import ChatPermissions
            until = datetime.utcnow() + timedelta(seconds=SPAM_MUTE_SECONDS)
            context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            if chat_id not in telegram_muted:
                telegram_muted[chat_id] = set()
            telegram_muted[chat_id].add(user_id)

            name = update.effective_user.full_name or str(user_id)
            # Ջնջել սպամ հրամանը
            try:
                delete_message(context, chat_id, message_id)
            except Exception:
                pass
            context.bot.send_message(
                chat_id=chat_id,
                text=f"🔇 {name}-ը սպամել է հրամաններ և լռեցվել է 5 րոպեով։"
            )
            try:
                context.bot.send_message(
                    chat_id=user_id,
                    text="🔇 Դուք շատ հաճախ եք ուղարկել բոտի հրամաններ։ Լռեցված եք 5 րոպեով։"
                )
            except Exception:
                pass
            logger.info(f"Anti-spam mute: user {user_id} in chat {chat_id} for {SPAM_MUTE_SECONDS}s")
        except Exception as e:
            logger.error(f"Anti-spam mute failed for {user_id}: {e}")
    except Exception as e:
        logger.error(f"anti_command_spam error: {e}")


def main():
    # ⚠️ Փոխիր այս թոքենը նորով (BotFather-ից)
    TOKEN = "8853414110:AAFgk5m5qR0wBnbOIqDIO3yI1153GdjzKTI"

    # Բեռնել պահպանված տվյալները և ակտիվ խաղերը
    load_data()
    load_games()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Anti-spam՝ հրամանների սպամ (աշխատում է բոլոր հրամաններից առաջ)
    dp.add_handler(MessageHandler(Filters.command & Filters.chat_type.groups, anti_command_spam), group=-3)

    # Հրամաններ
    dp.add_handler(CommandHandler("start", start))
    # Բոտի ավելացում խմբում — բարձր առաջնահերթություն
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_chat_member), group=-2)
    dp.add_handler(MessageHandler(Filters.status_update, new_chat_member), group=-2)
    dp.add_handler(CommandHandler("create", create))
    dp.add_handler(CommandHandler("go", go))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("leave", leave))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("rules", rules_command))
    dp.add_handler(CommandHandler("roles", roles_command))
    dp.add_handler(CommandHandler("status", status_command))
    dp.add_handler(CommandHandler("extend", extend_command))
    dp.add_handler(CommandHandler("time", time_command))
    dp.add_handler(CommandHandler("setcreator", setcreator_command))
    dp.add_handler(CommandHandler("setadmin", setadmin_command))
    dp.add_handler(CommandHandler("kick", kick_command))
    dp.add_handler(CommandHandler("broadcast", broadcast_command))
    dp.add_handler(CommandHandler("allroles", allroles_command))
    dp.add_handler(CommandHandler("setdurations", setdurations_command))
    dp.add_handler(CommandHandler("settings", settings_command))
    # Հիմնադրի հրամաններ
    dp.add_handler(CommandHandler("admins", admins_command))
    dp.add_handler(CommandHandler("removeadmin", removeadmin_command))
    dp.add_handler(CommandHandler("announce", announce_command))
    dp.add_handler(CommandHandler("reload", reload_command))
    dp.add_handler(CommandHandler("muteall", muteall_command))
    dp.add_handler(CommandHandler("unmuteall", unmuteall_command))
    dp.add_handler(CommandHandler("dmute", dmute_command))
    dp.add_handler(CommandHandler("dunmute", dunmute_command))
    dp.add_handler(CommandHandler("ban", ban_command))
    dp.add_handler(CommandHandler("unban", unban_command))
    dp.add_handler(CommandHandler("give", give_command))
    dp.add_handler(CommandHandler("manch", manch_command))
    dp.add_handler(CommandHandler("userinfo", userinfo_command))
    dp.add_handler(CommandHandler("loading", loading_command))
    dp.add_handler(CommandHandler("balance", balance_command))
    dp.add_handler(CommandHandler("rek", rek_command))
    dp.add_handler(CommandHandler("say", say_command))
    dp.add_handler(CommandHandler("group", group_command))
    dp.add_handler(CommandHandler("grban", grban_command))
    dp.add_handler(CommandHandler("urban", urban_command))
    dp.add_handler(CommandHandler("show", show_command))
    dp.add_handler(CommandHandler("pin", pin_command))
    dp.add_handler(CommandHandler("unpin", unpin_command))
    dp.add_handler(CommandHandler("id", id_command))
    dp.add_handler(CommandHandler("reply", reply_command))
    dp.add_handler(CommandHandler("cancel", cancel_help))
    dp.add_handler(CallbackQueryHandler(help_contact, pattern="^help_contact$"))
    # Խմբային մոդերացիա (միայն բոտի հիմնադիր)
    dp.add_handler(CommandHandler("grouphelp", grouphelp_command))
    dp.add_handler(CommandHandler("gban", group_ban_command))
    dp.add_handler(CommandHandler("gunban", group_unban_command))
    dp.add_handler(CommandHandler("gmute", group_mute_command))
    dp.add_handler(CommandHandler("gunmute", group_unmute_command))
    dp.add_handler(CommandHandler("warn", warn_command))
    dp.add_handler(CommandHandler("unwarn", unwarn_command))
    dp.add_handler(CommandHandler("gwarn", warn_command))
    dp.add_handler(CommandHandler("gunwarn", unwarn_command))

    # Callback-ներ
    dp.add_handler(CallbackQueryHandler(show_roles, pattern="^show_roles$"))
    dp.add_handler(CallbackQueryHandler(show_callback, pattern="^show_(main|close|reset_all|n_|add_|rem_|reset_)"))
    dp.add_handler(CallbackQueryHandler(role_info, pattern="^role_info_"))
    dp.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))
    # Դերերի գնում (Stars)
    dp.add_handler(CallbackQueryHandler(buy_roles_menu, pattern="^buy_roles_menu$"))
    dp.add_handler(CallbackQueryHandler(buy_role_view, pattern="^buy_role_view_"))
    dp.add_handler(CallbackQueryHandler(buy_role_pay, pattern="^buy_role_pay_"))
    dp.add_handler(CallbackQueryHandler(my_owned_roles, pattern="^my_owned_roles$"))
    dp.add_handler(CallbackQueryHandler(use_purchased_role_callback, pattern="^use_role_"))
    dp.add_handler(CallbackQueryHandler(give_role_callback, pattern="^give_(role_|cancel)"))
    dp.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dp.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))
    dp.add_handler(CallbackQueryHandler(commissar_choose_action, pattern="^commissar_choose_"))
    dp.add_handler(CallbackQueryHandler(night_action, pattern="^night_action_"))
    dp.add_handler(CallbackQueryHandler(vote, pattern="^vote_"))
    dp.add_handler(CallbackQueryHandler(confirm_kill, pattern="^confirm_"))
    # Settings callbacks
    dp.add_handler(CallbackQueryHandler(settings_main, pattern="^settings_main$"))
    dp.add_handler(CallbackQueryHandler(settings_close, pattern="^settings_close$"))
    dp.add_handler(CallbackQueryHandler(settings_roles, pattern="^settings_roles$"))
    dp.add_handler(CallbackQueryHandler(toggle_role, pattern="^toggle_role_"))
    dp.add_handler(CallbackQueryHandler(settings_timings, pattern="^settings_timings$"))
    dp.add_handler(CallbackQueryHandler(set_timing_menu, pattern="^set_timing_"))
    dp.add_handler(CallbackQueryHandler(apply_timing, pattern="^apply_timing_"))
    dp.add_handler(CallbackQueryHandler(settings_mute, pattern="^settings_mute$"))
    dp.add_handler(CallbackQueryHandler(mute_option, pattern="^mute_opt_"))
    dp.add_handler(CallbackQueryHandler(mute_set, pattern="^mute_set_"))
    dp.add_handler(CallbackQueryHandler(settings_other, pattern="^settings_other$"))
    dp.add_handler(CallbackQueryHandler(settings_lang, pattern="^settings_lang$"))
    dp.add_handler(CallbackQueryHandler(set_lang, pattern="^set_lang_"))

    # Հաղորդագրություններ
    # /rek — ցանկացած տիպի բովանդակություն (տեքստ, նկար, գիֆ, ստիկեր...)
    dp.add_handler(MessageHandler(Filters.chat_type.private & ~Filters.command, handle_rek_message), group=-2)
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private & ~Filters.command, handle_help_message), group=-1)
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private & ~Filters.command, handle_mafia_chat), group=0)
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private & ~Filters.command, handle_last_word), group=1)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_non_player_message))
    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

