"""
db.py - SQLite storage helpers for Robot Bi network persistence.
"""

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent.parent
OLD_DB_PATHS = [
    REPO_ROOT / "src_brain" / "network" / "robot_bi.db",
    REPO_ROOT / "src_brain" / "network" / "data" / "robot_bi.db",
    REPO_ROOT / "robot_bi.db",
]
NEW_DB_PATH = REPO_ROOT / "runtime" / "robot_bi.db"
DB_PATH = NEW_DB_PATH

_INIT_LOCK = threading.Lock()
_INITIALIZED = False


def migrate_db_path_if_needed() -> None:
    """
    One-time migration: copy DB tu path cu sang runtime/robot_bi.db.

    Chi copy khi DB moi chua ton tai hoac gan nhu rong, va co DB cu co data.
    DB cu duoc giu nguyen de rollback an toan.
    """
    import shutil

    if NEW_DB_PATH.exists() and NEW_DB_PATH.stat().st_size > 8192:
        return

    old_db = None
    for path in OLD_DB_PATHS:
        if not path.exists():
            continue
        size = path.stat().st_size
        if size <= 8192:
            continue
        if old_db is None or size > old_db.stat().st_size:
            old_db = path

    if old_db is None:
        return

    NEW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old_db, NEW_DB_PATH)
    logger.info(
        "[DB] Migrated DB from %s to %s (%d bytes)",
        old_db,
        NEW_DB_PATH,
        NEW_DB_PATH.stat().st_size,
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_family_id(family_id: str | None) -> str:
    fid = (family_id or "").strip()
    return fid or os.getenv("FAMILY_ID", "default")


def _ensure_family_exists_conn(conn, family_id: str | None, display_name: str | None = None) -> str:
    fid = _normalize_family_id(family_id)
    label = (display_name or fid).strip() or fid
    conn.execute(
        """
        INSERT OR IGNORE INTO families (family_id, display_name, created_at)
        VALUES (?, ?, ?)
        """,
        (fid, label, _utc_now_iso()),
    )
    return fid


def ensure_family_exists(family_id: str | None, display_name: str | None = None) -> str:
    """Create the family row if missing and return the normalized family_id."""
    with get_db_connection() as conn:
        fid = _ensure_family_exists_conn(conn, family_id, display_name)
        conn.commit()
        return fid


@contextmanager
def get_db_connection():
    """Tra ve connection voi WAL mode bat"""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def cleanup_expired_login_attempts(ttl_minutes: int = 60) -> int:
    """Xoa login_attempts cu hon ttl_minutes. Tra ve so rows da xoa."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM login_attempts
            WHERE first_attempt_at IS NOT NULL
              AND first_attempt_at < ?
              AND (locked_until IS NULL OR locked_until <= ?)
            """,
            (cutoff, now),
        )
        conn.commit()
        return cur.rowcount


def cleanup_orphan_sessions(max_age_hours: int = 24) -> int:
    """Dong cac session cu co ended_at IS NULL. Tra ve so session da dong."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            UPDATE conversations
            SET ended_at = ?
            WHERE ended_at IS NULL
              AND started_at < ?
            """,
            (_utc_now_iso(), cutoff),
        )
        conn.commit()
        if cur.rowcount > 0:
            logger.info(
                "[DB] Dong %d orphan session cu hon %dh",
                cur.rowcount,
                max_age_hours,
            )
        return cur.rowcount


def _seed_learning_content(conn) -> None:
    """Seed English 5-7 learning content. Idempotent (INSERT OR IGNORE)."""
    import json as _json

    LESSONS = [
        ("colors", "Basic Colors 1", "Màu cơ bản 1", "🎨", 1, [
            ("Red",    "Màu đỏ",          "🔴", ["Red","Blue","Green","Yellow"]),
            ("Blue",   "Màu xanh dương",   "🔵", ["Red","Blue","Green","Pink"]),
            ("Green",  "Màu xanh lá",      "🟢", ["Green","Orange","Purple","Black"]),
            ("Yellow", "Màu vàng",         "🟡", ["Yellow","Red","Blue","White"]),
            ("Orange", "Màu cam",          "🟠", ["Orange","Yellow","Green","Pink"]),
        ]),
        ("colors", "Basic Colors 2", "Màu cơ bản 2", "🌈", 2, [
            ("Purple", "Màu tím",   "🟣", ["Purple","Blue","Pink","Black"]),
            ("Pink",   "Màu hồng",  "🌸", ["Pink","Red","Purple","Yellow"]),
            ("White",  "Màu trắng", "⬜", ["White","Black","Gray","Blue"]),
            ("Black",  "Màu đen",   "⬛", ["Black","White","Gray","Purple"]),
            ("Brown",  "Màu nâu",   "🟫", ["Brown","Orange","Red","Pink"]),
        ]),
        ("colors", "Color Review", "Ôn tập màu sắc", "✏️", 3, [
            ("Red",    "Màu đỏ",         "🔴", ["Red","Blue","Green","Yellow"]),
            ("Blue",   "Màu xanh dương", "🔵", ["Orange","Blue","Pink","Brown"]),
            ("Yellow", "Màu vàng",       "🟡", ["Purple","Green","Yellow","White"]),
            ("Green",  "Màu xanh lá",    "🟢", ["Green","Black","Red","Pink"]),
            ("Purple", "Màu tím",        "🟣", ["Blue","Purple","Orange","White"]),
        ]),
        ("animals", "Farm Animals", "Động vật nông trại", "🐄", 1, [
            ("Dog",  "Con chó", "🐕", ["Dog","Cat","Bird","Fish"]),
            ("Cat",  "Con mèo", "🐈", ["Dog","Cat","Rabbit","Duck"]),
            ("Cow",  "Con bò",  "🐄", ["Cow","Dog","Cat","Bird"]),
            ("Pig",  "Con lợn", "🐷", ["Pig","Cat","Cow","Duck"]),
            ("Duck", "Con vịt", "🦆", ["Duck","Dog","Pig","Rabbit"]),
        ]),
        ("animals", "Wild Animals", "Động vật hoang dã", "🦁", 2, [
            ("Lion",     "Con sư tử", "🦁", ["Lion","Tiger","Bear","Wolf"]),
            ("Elephant", "Con voi",   "🐘", ["Elephant","Giraffe","Lion","Bear"]),
            ("Tiger",    "Con hổ",    "🐯", ["Tiger","Lion","Leopard","Wolf"]),
            ("Bear",     "Con gấu",   "🐻", ["Bear","Dog","Tiger","Elephant"]),
            ("Rabbit",   "Con thỏ",   "🐰", ["Rabbit","Cat","Duck","Pig"]),
        ]),
        ("animals", "Sea & Birds", "Biển & Chim", "🐟", 3, [
            ("Fish",      "Con cá",   "🐟", ["Fish","Duck","Crab","Turtle"]),
            ("Bird",      "Con chim", "🐦", ["Bird","Fish","Butterfly","Bee"]),
            ("Crab",      "Con cua",  "🦀", ["Crab","Fish","Turtle","Snail"]),
            ("Turtle",    "Con rùa",  "🐢", ["Turtle","Frog","Crab","Fish"]),
            ("Butterfly", "Con bướm", "🦋", ["Butterfly","Bird","Bee","Dragonfly"]),
        ]),
        ("numbers", "Numbers 1-5", "Số 1 đến 5", "🔢", 1, [
            ("One",   "Một", "1️⃣", ["One","Two","Three","Four"]),
            ("Two",   "Hai", "2️⃣", ["One","Two","Five","Three"]),
            ("Three", "Ba",  "3️⃣", ["Three","Four","One","Two"]),
            ("Four",  "Bốn", "4️⃣", ["Four","Five","One","Three"]),
            ("Five",  "Năm", "5️⃣", ["Five","Four","Two","Three"]),
        ]),
        ("numbers", "Numbers 6-10", "Số 6 đến 10", "🔢", 2, [
            ("Six",   "Sáu",  "6️⃣", ["Six","Seven","Eight","Five"]),
            ("Seven", "Bảy",  "7️⃣", ["Six","Seven","Nine","Ten"]),
            ("Eight", "Tám",  "8️⃣", ["Eight","Seven","Six","Nine"]),
            ("Nine",  "Chín", "9️⃣", ["Nine","Eight","Ten","Seven"]),
            ("Ten",   "Mười", "🔟", ["Ten","Nine","Eight","Six"]),
        ]),
        ("numbers", "Number Review", "Ôn tập số đếm", "🧮", 3, [
            ("One",   "Một",  "1️⃣", ["One","Six","Nine","Four"]),
            ("Three", "Ba",   "3️⃣", ["Two","Three","Seven","Ten"]),
            ("Five",  "Năm",  "5️⃣", ["Eight","Five","One","Nine"]),
            ("Seven", "Bảy",  "7️⃣", ["Three","Seven","Two","Six"]),
            ("Ten",   "Mười", "🔟", ["Four","Eight","Ten","Five"]),
        ]),
        ("family", "My Family 1", "Gia đình tôi 1", "👨‍👩‍👧", 1, [
            ("Mom",    "Mẹ",          "👩", ["Mom","Dad","Sister","Brother"]),
            ("Dad",    "Bố",          "👨", ["Mom","Dad","Uncle","Aunt"]),
            ("Sister", "Chị/Em gái", "👧", ["Sister","Brother","Mom","Dad"]),
            ("Brother","Anh/Em trai","👦", ["Brother","Sister","Dad","Mom"]),
            ("Baby",   "Em bé",       "👶", ["Baby","Mom","Dad","Sister"]),
        ]),
        ("family", "My Family 2", "Gia đình tôi 2", "👴", 2, [
            ("Grandma", "Bà",      "👵", ["Grandma","Grandpa","Mom","Aunt"]),
            ("Grandpa", "Ông",     "👴", ["Grandpa","Grandma","Dad","Uncle"]),
            ("Aunt",    "Dì/Cô",   "👩", ["Aunt","Uncle","Mom","Grandma"]),
            ("Uncle",   "Chú/Bác", "👨", ["Uncle","Aunt","Dad","Grandpa"]),
            ("Family",  "Gia đình","👨‍👩‍👧‍👦",["Family","Baby","Home","Friend"]),
        ]),
        ("family", "Family Review", "Ôn tập gia đình", "🏠", 3, [
            ("Mom",     "Mẹ",          "👩", ["Mom","Aunt","Grandma","Sister"]),
            ("Dad",     "Bố",          "👨", ["Uncle","Dad","Grandpa","Brother"]),
            ("Grandma", "Bà",          "👵", ["Grandma","Mom","Aunt","Sister"]),
            ("Brother", "Anh/Em trai", "👦", ["Dad","Uncle","Brother","Grandpa"]),
            ("Baby",    "Em bé",       "👶", ["Family","Baby","Grandma","Sister"]),
        ]),
    ]

    MATH_LESSONS = [
        # ── SHAPES ───────────────────────────────────────────────
        ("math_shapes", "Hình dạng 1", "Basic Shapes", "🔺", 1, [
            ("Hình tròn",      "Circle",    "⭕", ["Hình tròn","Hình vuông","Tam giác","Hình chữ nhật"]),
            ("Hình vuông",     "Square",    "🟦", ["Hình tròn","Hình vuông","Tam giác","Hình thoi"]),
            ("Tam giác",       "Triangle",  "🔺", ["Tam giác","Hình tròn","Hình vuông","Hình chữ nhật"]),
            ("Hình chữ nhật",  "Rectangle", "▭",  ["Hình chữ nhật","Hình vuông","Tam giác","Hình tròn"]),
            ("Hình thoi",      "Diamond",   "💠", ["Hình thoi","Hình tròn","Tam giác","Ngôi sao"]),
        ]),
        ("math_shapes", "Hình dạng 2", "Shapes in life", "🌟", 2, [
            ("Hình tròn",      "Mặt trời có dạng hình gì?",     "☀️", ["Hình tròn","Tam giác","Hình vuông","Hình chữ nhật"]),
            ("Hình chữ nhật",  "Cửa sổ có dạng hình gì?",       "🪟", ["Hình tròn","Hình vuông","Hình chữ nhật","Tam giác"]),
            ("Hình tròn",      "Bánh pizza có dạng hình gì?",    "🍕", ["Hình thoi","Hình tròn","Tam giác","Hình vuông"]),
            ("Tam giác",       "Nón lá có dạng hình gì?",        "👒", ["Tam giác","Hình tròn","Hình vuông","Hình chữ nhật"]),
            ("Hình vuông",     "Khăn tay vuông có dạng gì?",     "🟦", ["Hình tròn","Hình vuông","Tam giác","Hình thoi"]),
        ]),
        ("math_shapes", "Ôn tập hình dạng", "Shape Review", "✏️", 3, [
            ("Tam giác",       "Triangle",  "🔺", ["Hình tròn","Hình vuông","Tam giác","Hình chữ nhật"]),
            ("Hình tròn",      "Circle",    "⭕", ["Hình thoi","Hình tròn","Tam giác","Hình vuông"]),
            ("Hình vuông",     "Square",    "🟦", ["Hình chữ nhật","Hình vuông","Tam giác","Hình tròn"]),
            ("Hình chữ nhật",  "Rectangle", "▭",  ["Hình chữ nhật","Hình vuông","Hình tròn","Tam giác"]),
            ("Hình thoi",      "Diamond",   "💠", ["Tam giác","Hình tròn","Hình thoi","Hình vuông"]),
        ]),
        # ── ADDITION ─────────────────────────────────────────────
        ("math_add", "Cộng trong 5", "Add up to 5", "➕", 1, [
            ("2", "1 + 1 = ?", "🧮", ["1","2","3","4"]),
            ("3", "1 + 2 = ?", "🧮", ["2","3","4","5"]),
            ("4", "2 + 2 = ?", "🧮", ["3","4","5","6"]),
            ("5", "2 + 3 = ?", "🧮", ["3","4","5","6"]),
            ("4", "3 + 1 = ?", "🧮", ["2","3","4","5"]),
        ]),
        ("math_add", "Cộng trong 10", "Add up to 10", "➕", 2, [
            ("7", "3 + 4 = ?", "🧮", ["6","7","8","9"]),
            ("8", "5 + 3 = ?", "🧮", ["6","7","8","9"]),
            ("9", "4 + 5 = ?", "🧮", ["7","8","9","10"]),
            ("10","5 + 5 = ?", "🧮", ["8","9","10","11"]),
            ("6", "4 + 2 = ?", "🧮", ["5","6","7","8"]),
        ]),
        ("math_add", "Ôn tập phép cộng", "Addition Review", "🔢", 3, [
            ("3", "1 + 2 = ?", "🧮", ["2","3","4","5"]),
            ("5", "3 + 2 = ?", "🧮", ["4","5","6","7"]),
            ("7", "4 + 3 = ?", "🧮", ["5","6","7","8"]),
            ("9", "6 + 3 = ?", "🧮", ["7","8","9","10"]),
            ("10","7 + 3 = ?", "🧮", ["8","9","10","11"]),
        ]),
        # ── COUNTING ─────────────────────────────────────────────
        ("math_count", "Đếm 1-5", "Count 1-5", "🔢", 1, [
            ("Một",   "1", "1️⃣", ["Một","Hai","Ba","Bốn"]),
            ("Hai",   "2", "2️⃣", ["Một","Hai","Ba","Năm"]),
            ("Ba",    "3", "3️⃣", ["Hai","Ba","Bốn","Năm"]),
            ("Bốn",   "4", "4️⃣", ["Ba","Bốn","Năm","Sáu"]),
            ("Năm",   "5", "5️⃣", ["Ba","Bốn","Năm","Sáu"]),
        ]),
        ("math_count", "Đếm 6-10", "Count 6-10", "🔢", 2, [
            ("Sáu",   "6", "6️⃣", ["Năm","Sáu","Bảy","Tám"]),
            ("Bảy",   "7", "7️⃣", ["Sáu","Bảy","Tám","Chín"]),
            ("Tám",   "8", "8️⃣", ["Bảy","Tám","Chín","Mười"]),
            ("Chín",  "9", "9️⃣", ["Bảy","Tám","Chín","Mười"]),
            ("Mười", "10", "🔟", ["Tám","Chín","Mười","Mười một"]),
        ]),
        ("math_count", "Ôn tập đếm số", "Count Review", "🧮", 3, [
            ("Hai",   "2", "2️⃣", ["Một","Hai","Ba","Bốn"]),
            ("Năm",   "5", "5️⃣", ["Ba","Bốn","Năm","Sáu"]),
            ("Bảy",   "7", "7️⃣", ["Năm","Sáu","Bảy","Tám"]),
            ("Mười", "10", "🔟", ["Tám","Chín","Mười","Mười một"]),
            ("Ba",    "3", "3️⃣", ["Một","Hai","Ba","Bốn"]),
        ]),
    ]

    SCIENCE_LESSONS = [
        # ── WEATHER ──────────────────────────────────────────────
        ("sci_weather", "Thời tiết 1", "Weather", "☀️", 1, [
            ("Nắng",     "Trời có nắng sáng",        "☀️", ["Nắng","Mưa","Mây","Gió"]),
            ("Mưa",      "Nước rơi từ trên xuống",   "🌧️", ["Nắng","Mưa","Tuyết","Sương"]),
            ("Mây",      "Đám bông trắng trên trời", "☁️", ["Mây","Gió","Mưa","Sao"]),
            ("Cầu vồng", "Xuất hiện sau cơn mưa",    "🌈", ["Cầu vồng","Mây","Nắng","Sao"]),
            ("Gió",      "Không khí chuyển động",    "🌬️", ["Nắng","Mưa","Gió","Mây"]),
        ]),
        ("sci_weather", "Bầu trời", "The Sky", "🌙", 2, [
            ("Mặt trời", "Ngôi sao sáng ban ngày",          "☀️", ["Mặt trời","Mặt trăng","Ngôi sao","Hành tinh"]),
            ("Mặt trăng","Sáng lên ban đêm",                "🌙", ["Mặt trời","Mặt trăng","Ngôi sao","Thiên hà"]),
            ("Ngôi sao", "Lấp lánh trên bầu trời đêm",      "⭐", ["Mặt trời","Mặt trăng","Ngôi sao","Hành tinh"]),
            ("Trái đất", "Hành tinh chúng ta đang sống",    "🌍", ["Trái đất","Mặt trăng","Sao Hỏa","Hành tinh"]),
            ("Bầu trời", "Màu xanh vào ban ngày",           "🌤️", ["Bầu trời","Mặt trăng","Biển","Rừng"]),
        ]),
        ("sci_weather", "Ôn tập thiên nhiên", "Nature Review", "🌿", 3, [
            ("Nắng",     "Trời có nắng sáng",        "☀️", ["Nắng","Mưa","Gió","Mây"]),
            ("Mặt trăng","Sáng lên ban đêm",         "🌙", ["Mặt trời","Mặt trăng","Ngôi sao","Mây"]),
            ("Cầu vồng", "Xuất hiện sau cơn mưa",    "🌈", ["Mây","Nắng","Cầu vồng","Gió"]),
            ("Trái đất", "Hành tinh chúng ta sống",  "🌍", ["Mặt trời","Trái đất","Mặt trăng","Ngôi sao"]),
            ("Mưa",      "Nước rơi từ trên xuống",   "🌧️", ["Nắng","Gió","Mưa","Mây"]),
        ]),
        # ── BODY ─────────────────────────────────────────────────
        ("sci_body", "Bộ phận đầu", "Head Parts", "🧠", 1, [
            ("Mắt",   "Dùng để nhìn",          "👁️", ["Mắt","Tai","Mũi","Miệng"]),
            ("Tai",   "Dùng để nghe",          "👂", ["Mắt","Tai","Mũi","Miệng"]),
            ("Mũi",   "Dùng để ngửi và thở",  "👃", ["Mắt","Tai","Mũi","Miệng"]),
            ("Miệng", "Dùng để ăn và nói",    "👄", ["Mắt","Tai","Mũi","Miệng"]),
            ("Tóc",   "Mọc trên đầu",          "💇", ["Tóc","Da","Tai","Mắt"]),
        ]),
        ("sci_body", "Tay và chân", "Hands & Feet", "✋", 2, [
            ("Tay",      "Dùng để cầm nắm",       "✋", ["Tay","Chân","Đầu","Bụng"]),
            ("Chân",     "Dùng để đi lại",        "🦶", ["Tay","Chân","Đầu","Lưng"]),
            ("Ngón tay", "Mỗi bàn tay có 5...",  "☝️", ["Ngón tay","Ngón chân","Móng tay","Cổ tay"]),
            ("Bụng",     "Nơi chứa dạ dày",       "🍽️", ["Bụng","Ngực","Lưng","Vai"]),
            ("Lưng",     "Phần sau của cơ thể",   "🔙", ["Lưng","Bụng","Ngực","Hông"]),
        ]),
        ("sci_body", "Ôn tập cơ thể", "Body Review", "💪", 3, [
            ("Mắt",   "Dùng để nhìn",          "👁️", ["Tai","Mắt","Miệng","Mũi"]),
            ("Tay",   "Dùng để cầm nắm",       "✋", ["Chân","Đầu","Tay","Bụng"]),
            ("Mũi",   "Dùng để ngửi",          "👃", ["Miệng","Tai","Mũi","Mắt"]),
            ("Chân",  "Dùng để đi lại",        "🦶", ["Tay","Chân","Lưng","Bụng"]),
            ("Miệng", "Dùng để ăn và nói",    "👄", ["Mắt","Mũi","Tai","Miệng"]),
        ]),
        # ── PLANTS ───────────────────────────────────────────────
        ("sci_plant", "Cây cối", "Plants", "🌱", 1, [
            ("Rễ",   "Hút nước từ đất",              "🌱", ["Rễ","Thân","Lá","Hoa"]),
            ("Thân", "Đỡ cành và lá",                "🌳", ["Rễ","Thân","Lá","Hoa"]),
            ("Lá",   "Quang hợp tạo thức ăn",        "🍃", ["Rễ","Thân","Lá","Quả"]),
            ("Hoa",  "Nở đẹp và thơm",               "🌸", ["Lá","Hoa","Quả","Hạt"]),
            ("Quả",  "Mọc ra từ hoa",                "🍎", ["Hoa","Quả","Lá","Hạt"]),
        ]),
        ("sci_plant", "Rau và quả", "Vegetables & Fruits", "🥦", 2, [
            ("Cà rốt",  "Củ màu cam dưới đất",       "🥕", ["Cà rốt","Cà chua","Dưa chuột","Bắp cải"]),
            ("Cà chua", "Quả đỏ tròn",               "🍅", ["Cà rốt","Cà chua","Táo","Dâu"]),
            ("Táo",     "Quả đỏ ngọt",               "🍎", ["Táo","Cam","Chuối","Xoài"]),
            ("Chuối",   "Quả vàng dài cong",          "🍌", ["Táo","Cam","Chuối","Xoài"]),
            ("Bắp ngô", "Hạt vàng trên lõi",         "🌽", ["Bắp ngô","Cà rốt","Cà chua","Dưa"]),
        ]),
        ("sci_plant", "Ôn tập thực vật", "Plant Review", "🌿", 3, [
            ("Lá",      "Quang hợp tạo thức ăn",     "🍃", ["Rễ","Thân","Lá","Hoa"]),
            ("Cà chua", "Quả đỏ tròn",               "🍅", ["Cà rốt","Cà chua","Táo","Dưa"]),
            ("Hoa",     "Nở đẹp và thơm",            "🌸", ["Lá","Hoa","Quả","Rễ"]),
            ("Chuối",   "Quả vàng dài cong",          "🍌", ["Táo","Cam","Chuối","Xoài"]),
            ("Rễ",      "Hút nước từ đất",            "🌱", ["Rễ","Thân","Lá","Quả"]),
        ]),
    ]

    math_module_order = {"math_shapes": 1, "math_add": 2, "math_count": 3}
    sci_module_order  = {"sci_weather": 1, "sci_body": 2, "sci_plant": 3}

    for (module, title, title_vi, emoji, lesson_order, items) in MATH_LESSONS:
        lesson_id = f"vi57_math_{module.split('_')[1]}_{lesson_order}"
        conn.execute(
            """INSERT OR IGNORE INTO learning_lessons
               (lesson_id, language, age_group, module, title, title_vi, emoji, order_index, xp_reward)
               VALUES (?, 'vi', '5-7', ?, ?, ?, ?, ?, 10)""",
            (lesson_id, module, title, title_vi, emoji,
             math_module_order[module] * 100 + lesson_order),
        )
        for idx, (word, word_vi, word_emoji, options) in enumerate(items):
            item_id = f"{lesson_id}_q{idx + 1}"
            conn.execute(
                """INSERT OR IGNORE INTO learning_items
                   (item_id, lesson_id, order_index, question, question_vi, emoji, answer, options_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, lesson_id, idx, word, word_vi, word_emoji,
                 word, _json.dumps(options)),
            )

    for (module, title, title_vi, emoji, lesson_order, items) in SCIENCE_LESSONS:
        lesson_id = f"vi57_sci_{module.split('_')[1]}_{lesson_order}"
        conn.execute(
            """INSERT OR IGNORE INTO learning_lessons
               (lesson_id, language, age_group, module, title, title_vi, emoji, order_index, xp_reward)
               VALUES (?, 'vi', '5-7', ?, ?, ?, ?, ?, 10)""",
            (lesson_id, module, title, title_vi, emoji,
             sci_module_order[module] * 100 + lesson_order),
        )
        for idx, (word, word_vi, word_emoji, options) in enumerate(items):
            item_id = f"{lesson_id}_q{idx + 1}"
            conn.execute(
                """INSERT OR IGNORE INTO learning_items
                   (item_id, lesson_id, order_index, question, question_vi, emoji, answer, options_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, lesson_id, idx, word, word_vi, word_emoji,
                 word, _json.dumps(options)),
            )

    module_order = {"colors": 1, "animals": 2, "numbers": 3, "family": 4}
    for (module, title, title_vi, emoji, lesson_order, items) in LESSONS:
        lesson_id = f"en57_{module}_{lesson_order}"
        conn.execute(
            """INSERT OR IGNORE INTO learning_lessons
               (lesson_id, language, age_group, module, title, title_vi, emoji, order_index, xp_reward)
               VALUES (?, 'en', '5-7', ?, ?, ?, ?, ?, 10)""",
            (lesson_id, module, title, title_vi, emoji,
             module_order[module] * 100 + lesson_order),
        )
        for idx, (word, word_vi, word_emoji, options) in enumerate(items):
            item_id = f"{lesson_id}_q{idx + 1}"
            conn.execute(
                """INSERT OR IGNORE INTO learning_items
                   (item_id, lesson_id, order_index, question, question_vi, emoji, answer, options_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, lesson_id, idx, word, word_vi, word_emoji,
                 word, _json.dumps(options)),
            )


def _seed_exam_content(conn) -> None:
    """Seed starter exam papers + question bank. Idempotent (INSERT OR IGNORE).

    Phase 1 ships a small, deterministic starter set so the exam UI has data
    and tests are stable. The bulk of content is produced later by the AI
    generation pipeline (status='review' -> admin publishes).
    """
    import json as _json

    now = _utc_now_iso()
    year = "2025-2026"

    # Each paper: (paper_id, title, subject, track, comp_level, skill, level,
    #              age_group, duration_minutes, pass_percent, [questions...])
    # Each question: (topic, difficulty, qtype, question, question_vi, emoji,
    #                 options[list], answer, explanation)
    PAPERS = [
        (
            "exam_toeic_lr_starter_1", "TOEIC L&R — Khởi động (Mini)",
            "toeic_lr", "toeic_lr", "", "reading", "toeic_450",
            "15-18", 20, 60,
            [
                ("part5_grammar", 2, "mcq",
                 "The meeting has been ____ until next Monday.",
                 "Chọn từ đúng điền vào chỗ trống.", "📝",
                 ["postponed", "postpone", "postpones", "postponing"],
                 "postponed",
                 "'has been + V3' (thì hiện tại hoàn thành bị động) → 'postponed'."),
                ("part5_grammar", 2, "mcq",
                 "She is responsible ____ training new employees.",
                 "Chọn giới từ đúng.", "📝",
                 ["for", "of", "to", "with"],
                 "for",
                 "'responsible for' là collocation cố định."),
                ("part5_vocab", 3, "mcq",
                 "The new policy will ____ take effect on June 1st.",
                 "Chọn trạng từ phù hợp.", "📝",
                 ["officially", "office", "official", "officer"],
                 "officially",
                 "Cần trạng từ bổ nghĩa cho động từ 'take effect'."),
                ("part6_text", 2, "mcq",
                 "We are pleased to ____ you that your order has shipped.",
                 "Chọn động từ đúng.", "📝",
                 ["inform", "informing", "informed", "information"],
                 "inform",
                 "Sau 'to' dùng động từ nguyên mẫu: 'to inform'."),
                ("part7_reading", 3, "mcq",
                 "What is the main purpose of the notice? (A maintenance schedule)",
                 "Đọc hiểu: mục đích chính của thông báo.", "📖",
                 ["To announce a schedule", "To sell a product",
                  "To request payment", "To apologize"],
                 "To announce a schedule",
                 "Thông báo về lịch bảo trì → thông báo lịch trình."),
            ],
        ),
        (
            "exam_ielts_reading_starter_1", "IELTS Reading — Band 5.5 (Mini)",
            "ielts", "ielts", "", "reading", "band_5.5",
            "15-18", 20, 60,
            [
                ("tfng", 2, "mcq",
                 "Statement: 'The author was born in London.' Passage says he was born in Manchester. The statement is:",
                 "Chọn True / False / Not Given.", "📖",
                 ["False", "True", "Not Given", "Partly true"],
                 "False",
                 "Văn bản nói Manchester → mâu thuẫn → False."),
                ("tfng", 3, "mcq",
                 "Statement: 'The author enjoyed writing as a child.' Passage does not mention this. The statement is:",
                 "Chọn True / False / Not Given.", "📖",
                 ["Not Given", "True", "False", "Unclear"],
                 "Not Given",
                 "Không có thông tin → Not Given."),
                ("vocab", 2, "mcq",
                 "The word 'crucial' in the passage is closest in meaning to:",
                 "Chọn từ đồng nghĩa.", "📖",
                 ["essential", "optional", "unclear", "frequent"],
                 "essential",
                 "'crucial' = thiết yếu = essential."),
                ("heading", 3, "mcq",
                 "Which heading best fits a paragraph about renewable energy benefits?",
                 "Chọn tiêu đề phù hợp.", "📖",
                 ["Advantages of clean power", "A history of coal",
                  "The cost of oil", "Nuclear risks"],
                 "Advantages of clean power",
                 "Đoạn nói về lợi ích năng lượng tái tạo."),
                ("detail", 2, "mcq",
                 "According to the passage, solar panels work best when:",
                 "Chọn chi tiết đúng.", "📖",
                 ["there is direct sunlight", "it is raining",
                  "at midnight", "during storms"],
                 "there is direct sunlight",
                 "Tấm pin mặt trời hoạt động tốt nhất khi có ánh nắng trực tiếp."),
            ],
        ),
        (
            "exam_math_thpt_starter_1", "Toán THPT — Đề luyện (Mini)",
            "math", "exam_thpt", "", "", "grade_12",
            "15-18", 25, 60,
            [
                ("algebra", 2, "mcq",
                 "Đạo hàm của f(x) = x² là:",
                 "Tính đạo hàm.", "🧮",
                 ["2x", "x", "x²", "2"],
                 "2x",
                 "(xⁿ)' = n·xⁿ⁻¹ → (x²)' = 2x."),
                ("algebra", 2, "mcq",
                 "Nghiệm của phương trình 2x + 4 = 0 là:",
                 "Giải phương trình.", "🧮",
                 ["x = -2", "x = 2", "x = 4", "x = -4"],
                 "x = -2",
                 "2x = -4 → x = -2."),
                ("geometry", 3, "mcq",
                 "Diện tích hình tròn bán kính r là:",
                 "Chọn công thức đúng.", "📐",
                 ["πr²", "2πr", "πr", "πd"],
                 "πr²",
                 "Diện tích hình tròn = π·r²."),
                ("probability", 3, "mcq",
                 "Xác suất tung đồng xu ra mặt ngửa là:",
                 "Tính xác suất.", "🎲",
                 ["1/2", "1/3", "1/4", "1"],
                 "1/2",
                 "2 khả năng đồng khả năng → 1/2."),
                ("algebra", 4, "mcq",
                 "Giá trị của 2³ + 3² là:",
                 "Tính giá trị.", "🧮",
                 ["17", "12", "15", "18"],
                 "17",
                 "2³ = 8, 3² = 9, tổng = 17."),
            ],
        ),
    ]

    for (paper_id, title, subject, track, comp_level, skill, level,
         age_group, duration, pass_pct, questions) in PAPERS:
        conn.execute(
            """INSERT OR IGNORE INTO exam_papers
               (paper_id, title, subject, track, comp_level, skill, level,
                age_group, duration_minutes, total_questions, pass_percent,
                school_year, source, status, family_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'starter', 'published', NULL, ?, ?)""",
            (paper_id, title, subject, track, comp_level, skill, level,
             age_group, duration, len(questions), pass_pct, year, now, now),
        )
        for idx, (topic, diff, qtype, q, q_vi, emoji, options, answer, expl) in enumerate(questions):
            question_id = f"{paper_id}_q{idx + 1}"
            conn.execute(
                """INSERT OR IGNORE INTO question_bank
                   (question_id, subject, topic, age_group, track, skill, level,
                    difficulty, question_type, question, question_vi, emoji,
                    options_json, answer, explanation, school_year, source,
                    is_ai_generated, status, family_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'starter', 0, 'published', NULL, ?, ?)""",
                (question_id, subject, topic, age_group, track, skill, level,
                 diff, qtype, q, q_vi, emoji, _json.dumps(options, ensure_ascii=False),
                 answer, expl, year, now, now),
            )
            conn.execute(
                """INSERT OR IGNORE INTO exam_paper_questions
                   (paper_id, question_id, order_index, points)
                   VALUES (?, ?, ?, 1)""",
                (paper_id, question_id, idx),
            )


LEARNING_PACKS_DIR = REPO_ROOT / "resources" / "learning"

# Free-text question types (TOEIC Speaking & Writing). These carry no
# options/answer and are graded by the rubric/LLM grader in exam_router, so the
# pack loader must NOT subject them to the MCQ answer∈options validation.
_FREE_TEXT_QUESTION_TYPES = {"toeic_speaking", "toeic_writing"}
# When a question omits question_type, derive a free-text type from the paper
# skill so S&W packs need not repeat question_type on every task.
_SKILL_TO_FREE_TEXT_TYPE = {"speaking": "toeic_speaking", "writing": "toeic_writing"}


def _seed_learning_packs(conn) -> int:
    """Load JSON content packs from resources/learning/ into the question bank
    and assemble their exam papers. Idempotent (INSERT OR IGNORE).

    Pack schema (one file per subject)::

        {
          "subject": "math",
          "exams": [
            {
              "paper_id": "math_g10_algebra_1",
              "title": "Toán 10 — Đại số (Đề 1)",
              "track": "exam_thpt", "comp_level": "", "skill": "",
              "level": "grade_10", "age_group": "15-18",
              "duration_minutes": 45, "pass_percent": 60,
              "school_year": "2025-2026", "topic": "algebra",
              "questions": [
                {"question": "...", "question_vi": "...", "emoji": "🧮",
                 "options": ["a","b","c","d"], "answer": "a",
                 "explanation": "...", "difficulty": 2}
              ]
            }
          ]
        }

    A question whose ``answer`` is not one of its ``options`` is skipped (logged),
    so malformed/AI content can never produce an ungradeable exam.

    Free-text TOEIC S&W tasks use ``"question_type": "toeic_speaking"`` /
    ``"toeic_writing"`` (or are inferred from ``"skill": "speaking"/"writing"``)
    and carry no ``options``/``answer``; they bypass the MCQ check and are graded
    later by ``exam_router`` (rubric + LLM, with an offline fallback). Set each
    task's ``topic`` to a rubric key (read_aloud, describe_picture,
    respond_to_questions, email, express_opinion, opinion_essay) for max-score.
    Returns the number of papers seeded.
    """
    import json as _json

    if not LEARNING_PACKS_DIR.exists():
        return 0

    now = _utc_now_iso()
    papers_seeded = 0
    for pack_path in sorted(LEARNING_PACKS_DIR.glob("*.json")):
        try:
            pack = _json.loads(pack_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[DB] Bo qua learning pack loi %s: %s", pack_path.name, e)
            continue
        subject = (pack.get("subject") or "").strip()
        exams = pack.get("exams") or []
        if not subject or not isinstance(exams, list):
            logger.warning("[DB] Pack %s thieu subject/exams", pack_path.name)
            continue
        for exam in exams:
            paper_id = (exam.get("paper_id") or "").strip()
            questions = exam.get("questions") or []
            if not paper_id or not questions:
                continue
            # Validate questions first; skip the exam if nothing gradeable remains.
            # MCQ tasks require answer ∈ options; free-text TOEIC S&W tasks carry
            # no options/answer and bypass that check (graded later by exam_router).
            exam_skill = (exam.get("skill") or "").strip().lower()
            valid = []
            for q in questions:
                qtext = (q.get("question") or "").strip()
                if not qtext:
                    continue
                qtype = (q.get("question_type") or "").strip().lower()
                if not qtype:
                    qtype = _SKILL_TO_FREE_TEXT_TYPE.get(exam_skill, "mcq")
                if qtype in _FREE_TEXT_QUESTION_TYPES:
                    valid.append((qtext, q, [], "", qtype))
                    continue
                opts = q.get("options") or []
                ans = (q.get("answer") or "").strip()
                if len(opts) < 2:
                    continue
                if ans not in [str(o).strip() for o in opts]:
                    logger.warning("[DB] Pack %s: dap an khong khop options, bo qua 1 cau",
                                   pack_path.name)
                    continue
                valid.append((qtext, q, opts, ans, "mcq"))
            if not valid:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO exam_papers
                   (paper_id, title, subject, track, comp_level, skill, level,
                    age_group, duration_minutes, total_questions, pass_percent,
                    school_year, source, status, family_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pack', 'published', NULL, ?, ?)""",
                (paper_id, exam.get("title", paper_id), subject,
                 exam.get("track", "practice"), exam.get("comp_level", ""),
                 exam.get("skill", ""), exam.get("level", ""),
                 exam.get("age_group", "all"),
                 int(exam.get("duration_minutes", 30)), len(valid),
                 int(exam.get("pass_percent", 60)),
                 exam.get("school_year", "2025-2026"), now, now),
            )
            topic = exam.get("topic", "")
            for idx, (qtext, q, opts, ans, qtype) in enumerate(valid):
                question_id = f"{paper_id}_q{idx + 1}"
                conn.execute(
                    """INSERT OR IGNORE INTO question_bank
                       (question_id, subject, topic, age_group, track, skill, level,
                        difficulty, question_type, question, question_vi, emoji,
                        options_json, answer, explanation, school_year, source,
                        is_ai_generated, status, family_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pack', ?, 'published', NULL, ?, ?)""",
                    (question_id, subject, q.get("topic", topic),
                     exam.get("age_group", "all"), exam.get("track", "practice"),
                     exam.get("skill", ""), exam.get("level", ""),
                     int(q.get("difficulty", 2)), qtype, qtext, q.get("question_vi", ""),
                     q.get("emoji", ""),
                     _json.dumps([str(o) for o in opts], ensure_ascii=False), ans,
                     q.get("explanation", ""), exam.get("school_year", "2025-2026"),
                     int(bool(q.get("is_ai_generated", 0))), now, now),
                )
                conn.execute(
                    """INSERT OR IGNORE INTO exam_paper_questions
                       (paper_id, question_id, order_index, points) VALUES (?, ?, ?, 1)""",
                    (paper_id, question_id, idx),
                )
            papers_seeded += 1
    if papers_seeded:
        logger.info("[DB] Da nap %d de tu learning packs", papers_seeded)
    return papers_seeded


def init_db() -> None:
    """Khoi tao database va migrate du lieu tu JSON cu neu can."""
    global _INITIALIZED
    migrate_db_path_if_needed()
    if _INITIALIZED:
        return

    with _INIT_LOCK:
        if _INITIALIZED:
            return

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with get_db_connection() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS families (
                    family_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                '''
            )
            _ensure_family_exists_conn(conn, "default", "default")

            # Tao bang events
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS events (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    event_id TEXT,
                    timestamp TEXT,
                    type TEXT NOT NULL,
                    message TEXT,
                    clip_path TEXT,
                    metadata_json TEXT,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    import_key TEXT UNIQUE
                )
                '''
            )
            event_cols = {row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
            if "family_id" not in event_cols:
                conn.execute("ALTER TABLE events ADD COLUMN family_id TEXT DEFAULT 'default'")
            conn.execute(
                """
                UPDATE events
                SET family_id = 'default'
                WHERE family_id IS NULL OR family_id = ''
                """
            )

            # Tao bang tasks - khop voi task_manager.py
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS tasks (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    task_id TEXT,
                    name TEXT NOT NULL,
                    remind_time TEXT,
                    completed_today INTEGER NOT NULL DEFAULT 0,
                    completed_date TEXT,
                    stars INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    last_reminded TEXT,
                    last_reminded_date TEXT,
                    import_key TEXT UNIQUE
                )
                '''
            )
            task_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
            if "family_id" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN family_id TEXT DEFAULT 'default'")
            if "completed_date" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN completed_date TEXT")
            if "last_reminded_date" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN last_reminded_date TEXT")
            conn.execute(
                """
                UPDATE tasks
                SET family_id = 'default'
                WHERE family_id IS NULL OR family_id = ''
                """
            )
            conn.execute(
                """
                UPDATE tasks
                SET completed_date = '2000-01-01'
                WHERE completed_today = 1
                  AND (completed_date IS NULL OR completed_date = '')
                """
            )
            for index_sql in (
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_import_key ON events(import_key)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_import_key ON tasks(import_key)",
                "CREATE INDEX IF NOT EXISTS idx_events_family_db ON events(family_id, db_id)",
                "CREATE INDEX IF NOT EXISTS idx_events_family_timestamp ON events(family_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_events_family_type_timestamp ON events(family_id, type, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_family_db ON tasks(family_id, db_id)",
            ):
                try:
                    conn.execute(index_sql)
                except Exception as e:
                    logger.warning("[DB] Bo qua import_key unique index: %s", e)

            # Parent notes attached to family-scoped events.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS parent_event_notes (
                    note_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    event_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            for index_sql in (
                """
                CREATE INDEX IF NOT EXISTS idx_parent_event_notes_family_event
                ON parent_event_notes(family_id, event_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_parent_event_notes_family_updated
                ON parent_event_notes(family_id, updated_at)
                """,
            ):
                conn.execute(index_sql)

            # Parent App child profiles and settings storage.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS child_profiles (
                    child_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    birth_date TEXT,
                    grade TEXT,
                    avatar TEXT,
                    interests_json TEXT NOT NULL DEFAULT '[]',
                    notes TEXT,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS child_content_settings (
                    setting_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    child_id TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 0,
                    min_age INTEGER,
                    max_age INTEGER,
                    blocked_topics_json TEXT NOT NULL DEFAULT '[]',
                    allowed_topics_json TEXT NOT NULL DEFAULT '[]',
                    strict_mode INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS interaction_limit_settings (
                    setting_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    child_id TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 0,
                    daily_limit_minutes INTEGER NOT NULL DEFAULT 60,
                    warning_minutes INTEGER NOT NULL DEFAULT 10,
                    reset_time TEXT NOT NULL DEFAULT '00:00',
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS daily_interaction_usage (
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    child_id TEXT NOT NULL DEFAULT '',
                    usage_date TEXT NOT NULL,
                    seconds_used INTEGER NOT NULL DEFAULT 0,
                    sessions_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (family_id, child_id, usage_date)
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS sleep_schedule_settings (
                    family_id TEXT PRIMARY KEY
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    start_time TEXT NOT NULL DEFAULT '21:00',
                    end_time TEXT NOT NULL DEFAULT '06:30',
                    days_json TEXT NOT NULL DEFAULT '["mon","tue","wed","thu","fri","sat","sun"]',
                    timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS notification_settings (
                    family_id TEXT PRIMARY KEY
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    event_types_json TEXT NOT NULL DEFAULT '{}',
                    quiet_hours_json TEXT NOT NULL DEFAULT '{}',
                    channels_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS push_subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    endpoint_hash TEXT NOT NULL,
                    subscription_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    revoked_at TEXT
                )
                '''
            )
            for index_sql in (
                "CREATE INDEX IF NOT EXISTS idx_child_profiles_family ON child_profiles(family_id)",
                """
                CREATE INDEX IF NOT EXISTS idx_child_profiles_family_active
                ON child_profiles(family_id, is_active)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_child_content_settings_family_child
                ON child_content_settings(family_id, child_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_interaction_limit_settings_family_child
                ON interaction_limit_settings(family_id, child_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_push_subscriptions_family_user
                ON push_subscriptions(family_id, user_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_push_subscriptions_endpoint_hash
                ON push_subscriptions(endpoint_hash)
                """,
            ):
                conn.execute(index_sql)

            # Parent App Phase 3: report audit metadata, content catalog, and parent chat.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS report_exports (
                    export_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    sections_json TEXT NOT NULL,
                    row_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS content_items (
                    content_id TEXT PRIMARY KEY,
                    family_id TEXT,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    source_url TEXT,
                    thumbnail_url TEXT,
                    age_min INTEGER,
                    age_max INTEGER,
                    language TEXT NOT NULL DEFAULT 'vi',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS parent_chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    message_count INTEGER NOT NULL DEFAULT 0
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS parent_chat_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL
                        REFERENCES parent_chat_sessions(session_id) ON DELETE CASCADE,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                '''
            )
            for index_sql in (
                """
                CREATE INDEX IF NOT EXISTS idx_report_exports_family_created
                ON report_exports(family_id, created_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_content_items_type_enabled
                ON content_items(type, enabled, sort_order)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_content_items_family_type
                ON content_items(family_id, type)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_content_items_age
                ON content_items(age_min, age_max)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_parent_chat_sessions_family_started
                ON parent_chat_sessions(family_id, started_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_parent_chat_messages_session_time
                ON parent_chat_messages(session_id, timestamp)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_parent_chat_messages_family_time
                ON parent_chat_messages(family_id, timestamp)
                """,
            ):
                conn.execute(index_sql)

            content_seeded_at = _utc_now_iso()
            default_content_items = (
                (
                    "radio-bi-story",
                    "radio",
                    "Radio kể chuyện",
                    "Bi kể chuyện cổ tích và truyện thiếu nhi — nghe thư giãn mỗi ngày.",
                    "https://www.voiz.vn/category/thieu-nhi",
                    None,
                    5,
                    12,
                    "vi",
                    ["stories", "listening"],
                    1,
                    10,
                ),
                (
                    "radio-bi-learning",
                    "radio",
                    "Radio học tập",
                    "Các bài radio khoa học, toán và tiếng Anh ngắn dành cho bé.",
                    "https://vov2.vov.gov.vn",
                    None,
                    6,
                    12,
                    "vi",
                    ["education", "science"],
                    1,
                    20,
                ),
                (
                    "video-bi-english-animals",
                    "video",
                    "Học tiếng Anh: Con vật",
                    "Từ vựng tiếng Anh về các con vật qua hình ảnh sinh động.",
                    "https://www.youtube.com/watch?v=wfxA7DXJZWA",
                    "https://i.ytimg.com/vi/wfxA7DXJZWA/hqdefault.jpg",
                    5,
                    9,
                    "vi",
                    ["english", "animals"],
                    1,
                    10,
                ),
                (
                    "video-bi-math-shapes",
                    "video",
                    "Hình học vui",
                    "Nhận biết hình dạng và học toán sơ cấp qua hoạt hình.",
                    "https://www.youtube.com/watch?v=OUMNRfzH_AY",
                    "https://i.ytimg.com/vi/OUMNRfzH_AY/hqdefault.jpg",
                    6,
                    12,
                    "vi",
                    ["math", "geometry"],
                    1,
                    20,
                ),
                (
                    "game-bi-word-quiz",
                    "game",
                    "Đố từ vựng",
                    "Bi đố từ vựng tiếng Việt và tiếng Anh — trả lời đúng nhận sao.",
                    "/api/game/word-quiz/start",
                    None,
                    5,
                    12,
                    "vi",
                    ["vocabulary", "quiz"],
                    1,
                    10,
                ),
                (
                    "game-bi-voice-quiz",
                    "game",
                    "Đố vui bằng giọng nói",
                    "Bi đố câu đố bằng lời nói — bé trả lời bằng giọng nói.",
                    "/api/game/voice-quiz/start",
                    None,
                    7,
                    12,
                    "vi",
                    ["voice", "quiz"],
                    1,
                    20,
                ),
            )
            for item in default_content_items:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO content_items (
                        content_id, family_id, type, title, description, source_url,
                        thumbnail_url, age_min, age_max, language, tags_json, enabled,
                        sort_order, created_at, updated_at
                    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item[0],
                        item[1],
                        item[2],
                        item[3],
                        item[4],
                        item[5],
                        item[6],
                        item[7],
                        item[8],
                        json.dumps(item[9], ensure_ascii=False),
                        item[10],
                        item[11],
                        content_seeded_at,
                        content_seeded_at,
                    ),
                )

            # Parent App Phase 4: QR pairing metadata and robot location metadata.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS device_pairing_codes (
                    pairing_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    purpose TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL,
                    created_by_user_id TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS robot_location_metadata (
                    family_id TEXT PRIMARY KEY
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    room_name TEXT,
                    location_label TEXT,
                    source TEXT NOT NULL DEFAULT 'parent',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    updated_at TEXT NOT NULL,
                    updated_by_user_id TEXT
                )
                '''
            )
            for index_sql in (
                """
                CREATE INDEX IF NOT EXISTS idx_device_pairing_family_expires
                ON device_pairing_codes(family_id, expires_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_robot_location_source
                ON robot_location_metadata(source)
                """,
            ):
                conn.execute(index_sql)

            # Tao bang login_attempts (rate limiting cho /api/auth/login va /auth/login/v2)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    ip_address TEXT PRIMARY KEY,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    first_attempt_at TEXT,
                    locked_until TEXT
                )
                '''
            )

            # Tao bang users (username+password auth)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    family_name TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    token_version INTEGER NOT NULL DEFAULT 0,
                    role TEXT NOT NULL DEFAULT 'parent',
                    child_profile_id TEXT
                )
                '''
            )
            user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "is_admin" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                INSERT OR IGNORE INTO families (family_id, display_name, created_at)
                SELECT DISTINCT family_name, family_name, ?
                FROM users
                WHERE family_name IS NOT NULL AND family_name != ''
                """,
                (_utc_now_iso(),),
            )

            # Migration: them token_version neu chua co (cho DB cu)
            try:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"
                )
                conn.commit()
            except Exception as e:
                msg = str(e).lower()
                if "duplicate column" in msg or "already exists" in msg:
                    pass  # Column da ton tai
                else:
                    logger.error("[DB] Migration token_version failed: %s", e)
                    raise RuntimeError(f"DB migration that bai: {e}") from e

            # Migration US7 (spec 006): vai trò gia đình + liên kết hồ sơ trẻ.
            for _col, _ddl in (
                ("role", "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'parent'"),
                ("child_profile_id", "ALTER TABLE users ADD COLUMN child_profile_id TEXT"),
            ):
                try:
                    conn.execute(_ddl)
                    conn.commit()
                except Exception as e:
                    msg = str(e).lower()
                    if "duplicate column" in msg or "already exists" in msg:
                        pass
                    else:
                        logger.error("[DB] Migration %s failed: %s", _col, e)
                        raise RuntimeError(f"DB migration that bai: {e}") from e

            # Backfill role cho user cũ (idempotent):
            #  - rỗng/NULL → 'parent'
            #  - is_admin=1 → 'owner'
            #  - mỗi gia đình chưa có owner nào → user sớm nhất làm 'owner'
            conn.execute("UPDATE users SET role = 'parent' WHERE role IS NULL OR role = ''")
            conn.execute("UPDATE users SET role = 'owner' WHERE is_admin = 1 AND role != 'child'")
            conn.execute(
                """
                UPDATE users SET role = 'owner'
                WHERE user_id IN (
                    SELECT MIN(u2.user_id) FROM users u2
                    WHERE u2.role = 'parent'
                      AND NOT EXISTS (
                          SELECT 1 FROM users u3
                          WHERE u3.family_name = u2.family_name AND u3.role = 'owner'
                      )
                    GROUP BY u2.family_name
                )
                """
            )

            # family_permissions (US7): quyền con per gia đình — mặc định an toàn (0 = ẩn).
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS family_permissions (
                    family_name TEXT PRIMARY KEY
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    child_can_monitor INTEGER NOT NULL DEFAULT 0,
                    child_can_journal INTEGER NOT NULL DEFAULT 0,
                    child_can_notifications INTEGER NOT NULL DEFAULT 0,
                    child_can_sleep INTEGER NOT NULL DEFAULT 0,
                    child_can_safety INTEGER NOT NULL DEFAULT 0,
                    child_can_device INTEGER NOT NULL DEFAULT 0,
                    child_can_members INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                '''
            )

            # Tao bang auth_tokens (JWT refresh token rotation)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    refresh_token_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_revoked INTEGER NOT NULL DEFAULT 0
                )
                '''
            )

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    title TEXT,
                    turn_count INTEGER DEFAULT 0,
                    is_homework INTEGER NOT NULL DEFAULT 0,
                    homework_marked_at TEXT DEFAULT NULL
                )
                '''
            )
            conversation_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()
            }
            if "family_id" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN family_id TEXT DEFAULT 'default'")
            if "is_homework" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN is_homework INTEGER NOT NULL DEFAULT 0")
            if "homework_marked_at" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN homework_marked_at TEXT DEFAULT NULL")
            conn.execute(
                """
                UPDATE conversations
                SET family_id = 'default',
                    is_homework = COALESCE(is_homework, 0)
                WHERE family_id IS NULL OR family_id = '' OR is_homework IS NULL
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO families (family_id, display_name, created_at)
                SELECT DISTINCT family_id, family_id, ?
                FROM conversations
                WHERE family_id IS NOT NULL AND family_id != ''
                """,
                (_utc_now_iso(),),
            )

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','homework')),
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                '''
            )

            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id)
                '''
            )
            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_conversations_family_started
                ON conversations(family_id, started_at)
                '''
            )
            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_conversations_family_homework_started
                ON conversations(family_id, is_homework, started_at)
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS learning_schedules (
                    family_id TEXT NOT NULL,
                    day_of_week TEXT NOT NULL,
                    subject TEXT,
                    time TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (family_id, day_of_week)
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS game_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                '''
            )
            for trigger_sql in (
                '''
                CREATE TRIGGER IF NOT EXISTS trg_users_family_auto
                BEFORE INSERT ON users
                WHEN NEW.family_name IS NOT NULL AND NEW.family_name != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_name, NEW.family_name, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_conversations_family_auto
                BEFORE INSERT ON conversations
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_events_family_auto
                BEFORE INSERT ON events
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_tasks_family_auto
                BEFORE INSERT ON tasks
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
            ):
                conn.execute(trigger_sql)

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS learning_lessons (
                    lesson_id TEXT PRIMARY KEY,
                    language TEXT NOT NULL DEFAULT 'en',
                    age_group TEXT NOT NULL DEFAULT '5-7',
                    module TEXT NOT NULL,
                    title TEXT NOT NULL,
                    title_vi TEXT NOT NULL,
                    emoji TEXT NOT NULL DEFAULT '📚',
                    order_index INTEGER NOT NULL DEFAULT 0,
                    xp_reward INTEGER NOT NULL DEFAULT 10
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS learning_items (
                    item_id TEXT PRIMARY KEY,
                    lesson_id TEXT NOT NULL
                        REFERENCES learning_lessons(lesson_id) ON DELETE CASCADE,
                    order_index INTEGER NOT NULL DEFAULT 0,
                    question TEXT NOT NULL,
                    question_vi TEXT NOT NULL,
                    emoji TEXT NOT NULL DEFAULT '❓',
                    answer TEXT NOT NULL,
                    options_json TEXT NOT NULL DEFAULT '[]'
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS learning_progress (
                    progress_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL,
                    lesson_id TEXT NOT NULL
                        REFERENCES learning_lessons(lesson_id) ON DELETE CASCADE,
                    completed INTEGER NOT NULL DEFAULT 0,
                    score INTEGER NOT NULL DEFAULT 0,
                    xp_earned INTEGER NOT NULL DEFAULT 0,
                    completed_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(family_id, lesson_id)
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS learning_streaks (
                    streak_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL UNIQUE,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    longest_streak INTEGER NOT NULL DEFAULT 0,
                    last_activity_date TEXT,
                    total_xp INTEGER NOT NULL DEFAULT 0
                )
                '''
            )

            # ── Phase 1 exam system: question bank, exam papers, attempts ──
            # question_bank: large pool of questions tagged for filtering and
            # AI-generation review. status: draft|review|published|archived.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS question_bank (
                    question_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    topic TEXT NOT NULL DEFAULT '',
                    age_group TEXT NOT NULL DEFAULT 'all',
                    track TEXT NOT NULL DEFAULT 'practice',
                    skill TEXT NOT NULL DEFAULT '',
                    level TEXT NOT NULL DEFAULT '',
                    difficulty INTEGER NOT NULL DEFAULT 1,
                    question_type TEXT NOT NULL DEFAULT 'mcq',
                    question TEXT NOT NULL,
                    question_vi TEXT NOT NULL DEFAULT '',
                    emoji TEXT NOT NULL DEFAULT '',
                    options_json TEXT NOT NULL DEFAULT '[]',
                    answer TEXT NOT NULL,
                    explanation TEXT NOT NULL DEFAULT '',
                    school_year TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT '',
                    is_ai_generated INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'published',
                    family_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            # exam_papers: an assembled test (fixed set of questions, timed).
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS exam_papers (
                    paper_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    track TEXT NOT NULL DEFAULT 'practice',
                    comp_level TEXT NOT NULL DEFAULT '',
                    skill TEXT NOT NULL DEFAULT '',
                    level TEXT NOT NULL DEFAULT '',
                    age_group TEXT NOT NULL DEFAULT 'all',
                    duration_minutes INTEGER NOT NULL DEFAULT 30,
                    total_questions INTEGER NOT NULL DEFAULT 0,
                    pass_percent INTEGER NOT NULL DEFAULT 60,
                    school_year TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'published',
                    family_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            # exam_paper_questions: ordered junction paper -> questions.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS exam_paper_questions (
                    paper_id TEXT NOT NULL
                        REFERENCES exam_papers(paper_id) ON DELETE CASCADE,
                    question_id TEXT NOT NULL
                        REFERENCES question_bank(question_id) ON DELETE CASCADE,
                    order_index INTEGER NOT NULL DEFAULT 0,
                    points REAL NOT NULL DEFAULT 1,
                    PRIMARY KEY (paper_id, order_index)
                )
                '''
            )
            # exam_sessions: a family's attempt at an exam paper.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS exam_sessions (
                    session_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL,
                    paper_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    score REAL NOT NULL DEFAULT 0,
                    max_score REAL NOT NULL DEFAULT 0,
                    correct_count INTEGER NOT NULL DEFAULT 0,
                    total_questions INTEGER NOT NULL DEFAULT 0,
                    time_spent_seconds INTEGER NOT NULL DEFAULT 0,
                    answers_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'completed'
                )
                '''
            )
            # youtube_channels: kênh YouTube DUYỆT theo gia đình (allowlist global
            # giữ ở resources/youtube_channels.json; bảng này chỉ cho kênh family thêm).
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS youtube_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    label TEXT NOT NULL DEFAULT '',
                    language TEXT NOT NULL DEFAULT 'vi',
                    age_min INTEGER NOT NULL DEFAULT 5,
                    age_max INTEGER NOT NULL DEFAULT 12,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    UNIQUE(family_id, channel_id)
                )
                '''
            )
            # special_memories: kỷ niệm đặc biệt theo gia đình (Stage 2) — sinh nhật,
            # cột mốc, sở thích… robot ghi nhớ và có thể nhắc lại.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS special_memories (
                    memory_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'other',
                    title TEXT NOT NULL,
                    memory_date TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                '''
            )
            for index_sql in (
                "CREATE INDEX IF NOT EXISTS idx_qbank_subject_track_status ON question_bank(subject, track, status)",
                "CREATE INDEX IF NOT EXISTS idx_qbank_status ON question_bank(status)",
                "CREATE INDEX IF NOT EXISTS idx_qbank_filter ON question_bank(subject, age_group, difficulty, status)",
                "CREATE INDEX IF NOT EXISTS idx_exam_papers_subject_track ON exam_papers(subject, track, status)",
                "CREATE INDEX IF NOT EXISTS idx_exam_papers_track_level ON exam_papers(track, level, status)",
                "CREATE INDEX IF NOT EXISTS idx_exam_pq_paper ON exam_paper_questions(paper_id, order_index)",
                "CREATE INDEX IF NOT EXISTS idx_exam_sessions_family ON exam_sessions(family_id, completed_at)",
                "CREATE INDEX IF NOT EXISTS idx_exam_sessions_family_paper ON exam_sessions(family_id, paper_id)",
                "CREATE INDEX IF NOT EXISTS idx_youtube_channels_family ON youtube_channels(family_id)",
                "CREATE INDEX IF NOT EXISTS idx_special_memories_family ON special_memories(family_id, created_at)",
            ):
                conn.execute(index_sql)

            _seed_learning_content(conn)
            _seed_exam_content(conn)
            _seed_learning_packs(conn)

            _migrate_turns_role_constraint(conn)

            # Normalize legacy capitalized 'Admin' family to lowercase 'admin'
            _migrate_admin_family_case(conn)

            conn.commit()

            # Migrate du lieu cu
            _migrate_legacy_events(conn)
            _migrate_legacy_tasks(conn)

        cleanup_expired_login_attempts(ttl_minutes=1440)

        # Seed admin user neu bang users trong (idempotent)
        try:
            from src.infrastructure.auth.auth import seed_admin_if_empty

            seed_admin_if_empty()
        except Exception as _e:
            logger.warning("[DB] seed_admin_if_empty bo qua: %s", _e)

        _INITIALIZED = True
        logger.info("[DB] Database da duoc khoi tao thanh cong.")


def get_learning_schedule(family_id: str) -> dict:
    """Load schedule tu DB. Tra ve dict {day: {subject, time}}."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT day_of_week, subject, time
            FROM learning_schedules
            WHERE family_id = ?
            """,
            (fid,),
        ).fetchall()
    return {
        row["day_of_week"]: {
            "subject": row["subject"],
            "time": row["time"],
        }
        for row in rows
    }


def save_learning_schedule(family_id: str, schedule: dict) -> bool:
    """Luu schedule vao DB."""
    try:
        fid = ensure_family_exists(family_id)
        with get_db_connection() as conn:
            for day, info in (schedule or {}).items():
                day_key = str(day)
                if info is None:
                    conn.execute(
                        """
                        DELETE FROM learning_schedules
                        WHERE family_id = ? AND day_of_week = ?
                        """,
                        (fid, day_key),
                    )
                else:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO learning_schedules
                            (family_id, day_of_week, subject, time, updated_at)
                        VALUES (?, ?, ?, ?, datetime('now'))
                        """,
                        (fid, day_key, info.get("subject"), info.get("time")),
                    )
            conn.commit()
        return True
    except Exception as e:
        logger.error("[DB] save_learning_schedule error: %s", e)
        return False


def _migrate_legacy_events(conn):
    """Migrate du lieu tu event_queue.json cu sang bang events"""
    json_path = Path(__file__).with_name("event_queue.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            events = json.load(f)

        for event in events:
            conn.execute(
                '''
                INSERT OR IGNORE INTO events
                (event_id, timestamp, type, message, clip_path, metadata_json, is_read)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    event.get("id"),
                    event.get("timestamp"),
                    event.get("type"),
                    event.get("message"),
                    event.get("clip_path"),
                    json.dumps(event.get("metadata", {}), ensure_ascii=False),
                    1 if event.get("read", False) else 0,
                ),
            )
        conn.commit()
        logger.info("[DB] Da migrate %d events tu file JSON cu.", len(events))
    except Exception as e:
        logger.error("[DB] Loi migrate events: %s", e)


def _migrate_legacy_tasks(conn):
    """Migrate du lieu tu tasks.json cu sang bang tasks"""
    json_path = Path(__file__).with_name("tasks.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        for task in tasks:
            task_id = task.get("id")
            if not task_id:
                continue

            # Ho tro ca 'name' va 'title' tu du lieu cu
            name = task.get("name") or task.get("title") or "Khong co tieu de"

            conn.execute(
                '''
                INSERT OR IGNORE INTO tasks
                (task_id, name, remind_time, completed_today, stars,
                 created_at, last_reminded, import_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    task_id,
                    name,
                    task.get("remind_time", ""),
                    1 if task.get("completed_today") else 0,
                    int(task.get("stars", 0)),
                    task.get("created_at"),
                    task.get("last_reminded"),
                    task_id,
                ),
            )
        conn.commit()
        logger.info("[DB] Da migrate %d tasks tu file JSON cu.", len(tasks))
    except Exception as e:
        logger.error("[DB] Loi migrate tasks: %s", e)


def _migrate_turns_role_constraint(conn) -> None:
    row = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = 'turns'
        """
    ).fetchone()
    if not row:
        return

    create_sql = (row["sql"] or "").replace(" ", "").lower()
    if "'homework'" in create_sql and "ondeletecascade" in create_sql:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE turns RENAME TO turns_old")
    conn.execute(
        '''
        CREATE TABLE turns (
            turn_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','homework')),
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        '''
    )
    conn.execute(
        '''
        INSERT INTO turns (turn_id, session_id, role, content, timestamp)
        SELECT turn_id, session_id, role, content, timestamp
        FROM turns_old
        '''
    )
    conn.execute("DROP TABLE turns_old")
    conn.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id)
        '''
    )
    conn.execute("PRAGMA foreign_keys = ON")


def _migrate_admin_family_case(conn) -> None:
    """Rename legacy 'Admin' (capital A) family to lowercase 'admin' if present."""
    row = conn.execute("SELECT family_id FROM families WHERE family_id = 'Admin'").fetchone()
    if not row:
        return
    conn.execute(
        "INSERT OR IGNORE INTO families (family_id, display_name, created_at) VALUES ('admin', 'admin', ?)",
        (_utc_now_iso(),),
    )
    # FK is ON but 'admin' now exists, so these UPDATEs are safe
    conn.execute("UPDATE users SET family_name = 'admin' WHERE family_name = 'Admin'")
    conn.execute("UPDATE conversations SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("UPDATE events SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("UPDATE tasks SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("DELETE FROM families WHERE family_id = 'Admin'")


def create_session(family_id: str) -> str:
    family_id = ensure_family_exists(family_id)
    session_id = uuid4().hex
    with get_db_connection() as conn:
        conn.execute(
            '''
            INSERT INTO conversations (session_id, family_id, started_at)
            VALUES (?, ?, ?)
            ''',
            (session_id, family_id, _utc_now_iso()),
        )
        conn.commit()
    return session_id


def _resolve_session_family_conn(conn, session_id: str) -> str | None:
    row = conn.execute(
        "SELECT family_id FROM conversations WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["family_id"] if row else None


def close_session(session_id: str, family_id: str | None = None) -> None:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return
        conn.execute(
            '''
            UPDATE conversations
            SET ended_at = ?
            WHERE session_id = ? AND family_id = ?
            ''',
            (_utc_now_iso(), session_id, fid),
        )
        conn.commit()


def add_turn(session_id: str, role: str, content: str, family_id: str | None = None) -> str:
    if role not in {"user", "assistant", "homework"}:
        raise ValueError("Invalid turn role")
    turn_id = uuid4().hex
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            raise ValueError("Session not found")
        cur = conn.execute(
            '''
            INSERT INTO turns (turn_id, session_id, role, content, timestamp)
            SELECT ?, c.session_id, ?, ?, ?
            FROM conversations c
            WHERE c.session_id = ? AND c.family_id = ?
            ''',
            (turn_id, role, content, _utc_now_iso(), session_id, fid),
        )
        if cur.rowcount == 0:
            raise ValueError("Session not found")
        conn.execute(
            '''
            UPDATE conversations
            SET turn_count = turn_count + 1
            WHERE session_id = ? AND family_id = ?
            ''',
            (session_id, fid),
        )
        conn.commit()
    return turn_id


def get_session_turns(session_id: str, family_id: str | None = None) -> list[dict]:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return []
        rows = conn.execute(
            '''
            SELECT t.turn_id, t.session_id, t.role, t.content, t.timestamp
            FROM turns t
            JOIN conversations c ON c.session_id = t.session_id
            WHERE t.session_id = ? AND c.family_id = ?
            ORDER BY t.timestamp ASC
            ''',
            (session_id, fid),
        ).fetchall()
    return [dict(row) for row in rows]


def update_session_title(session_id: str, title: str, family_id: str | None = None) -> None:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return
        conn.execute(
            '''
            UPDATE conversations
            SET title = ?
            WHERE session_id = ? AND family_id = ?
            ''',
            (title, session_id, fid),
        )
        conn.commit()


def mark_session_homework(session_id: str, family_id: str | None = None) -> bool:
    if not session_id:
        return False
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return False
        cur = conn.execute(
            """
            UPDATE conversations
            SET is_homework = 1,
                homework_marked_at = datetime('now')
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, fid),
        )
        conn.commit()
        return cur.rowcount > 0


def get_homework_sessions(
    family_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    fid = _normalize_family_id(family_id)
    safe_limit = max(1, min(int(limit), 50))
    safe_offset = max(0, int(offset))
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, family_id, title,
                   started_at, ended_at, turn_count,
                   is_homework, homework_marked_at
            FROM conversations
            WHERE family_id = ? AND is_homework = 1
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (fid, safe_limit, safe_offset),
        ).fetchall()
    return [dict(row) for row in rows]


def list_families() -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.family_id, f.display_name, f.created_at,
                   COUNT(DISTINCT u.user_id) AS user_count
            FROM families f
            LEFT JOIN users u ON u.family_name = f.family_id
            GROUP BY f.family_id, f.display_name, f.created_at
            ORDER BY f.created_at ASC, f.family_id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_family_record(family_id: str, display_name: str | None = None) -> dict | None:
    fid = _normalize_family_id(family_id)
    label = (display_name or fid).strip() or fid
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO families (family_id, display_name, created_at)
            VALUES (?, ?, ?)
            """,
                (fid, label, _utc_now_iso()),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    return {"family_id": fid, "display_name": label}


def _youtube_row_to_dict(row) -> dict:
    try:
        tags = json.loads(row["tags_json"] or "[]")
        if not isinstance(tags, list):
            tags = []
    except Exception:
        tags = []
    return {
        "channel_id": row["channel_id"],
        "label": row["label"] or "",
        "language": (row["language"] or "vi"),
        "age_min": row["age_min"],
        "age_max": row["age_max"],
        "tags": [str(t).lower() for t in tags],
        "created_at": row["created_at"],
        "scope": "family",
    }


def list_family_youtube_channels(family_id: str) -> list[dict]:
    """Kênh YouTube duyệt riêng cho 1 gia đình (không gồm allowlist global)."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT channel_id, label, language, age_min, age_max, tags_json, created_at
            FROM youtube_channels WHERE family_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (fid,),
        ).fetchall()
    return [_youtube_row_to_dict(r) for r in rows]


def add_family_youtube_channel(
    family_id: str,
    channel_id: str,
    label: str = "",
    language: str = "vi",
    age_min: int = 5,
    age_max: int = 12,
    tags: list | None = None,
) -> dict:
    """Thêm/cập nhật 1 kênh cho gia đình (UNIQUE family_id+channel_id → upsert)."""
    fid = _normalize_family_id(family_id)
    cid = str(channel_id or "").strip()
    tags_norm = [str(t).lower() for t in (tags or [])]
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO youtube_channels
                (family_id, channel_id, label, language, age_min, age_max, tags_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(family_id, channel_id) DO UPDATE SET
                label=excluded.label, language=excluded.language,
                age_min=excluded.age_min, age_max=excluded.age_max,
                tags_json=excluded.tags_json
            """,
            (fid, cid, (label or "").strip(), (language or "vi").strip().lower() or "vi",
             int(age_min), int(age_max), json.dumps(tags_norm, ensure_ascii=False), _utc_now_iso()),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT channel_id, label, language, age_min, age_max, tags_json, created_at
            FROM youtube_channels WHERE family_id = ? AND channel_id = ?
            """,
            (fid, cid),
        ).fetchone()
    return _youtube_row_to_dict(row)


def delete_family_youtube_channel(family_id: str, channel_id: str) -> bool:
    fid = _normalize_family_id(family_id)
    cid = str(channel_id or "").strip()
    with get_db_connection() as conn:
        cur = conn.execute(
            "DELETE FROM youtube_channels WHERE family_id = ? AND channel_id = ?",
            (fid, cid),
        )
        conn.commit()
    return cur.rowcount > 0


_SPECIAL_MEMORY_KINDS = {"birthday", "milestone", "favorite", "other"}


def _special_memory_to_dict(row) -> dict:
    return {
        "memory_id": row["memory_id"],
        "kind": row["kind"],
        "title": row["title"],
        "memory_date": row["memory_date"],
        "note": row["note"],
        "created_at": row["created_at"],
    }


def list_special_memories(family_id: str) -> list[dict]:
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT memory_id, kind, title, memory_date, note, created_at
            FROM special_memories WHERE family_id = ?
            ORDER BY created_at DESC
            """,
            (fid,),
        ).fetchall()
    return [_special_memory_to_dict(r) for r in rows]


def add_special_memory(family_id: str, title: str, kind: str = "other",
                       memory_date: str = "", note: str = "") -> dict:
    fid = _normalize_family_id(family_id)
    k = kind if kind in _SPECIAL_MEMORY_KINDS else "other"
    mid = uuid4().hex
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO special_memories
                (memory_id, family_id, kind, title, memory_date, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, fid, k, title.strip(), (memory_date or "").strip(), (note or "").strip(), _utc_now_iso()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT memory_id, kind, title, memory_date, note, created_at FROM special_memories WHERE memory_id = ?",
            (mid,),
        ).fetchone()
    return _special_memory_to_dict(row)


def delete_special_memory(family_id: str, memory_id: str) -> bool:
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        cur = conn.execute(
            "DELETE FROM special_memories WHERE family_id = ? AND memory_id = ?",
            (fid, str(memory_id)),
        )
        conn.commit()
    return cur.rowcount > 0


def event_exists_for_family(family_id: str, event_id: str) -> bool:
    """Return True when an event belongs to the requested family."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM events
            WHERE family_id = ? AND event_id = ?
            LIMIT 1
            """,
            (fid, str(event_id)),
        ).fetchone()
    return row is not None


def _note_row_to_dict(row) -> dict:
    return {
        "note_id": row["note_id"],
        "event_id": row["event_id"],
        "family_id": row["family_id"],
        "user_id": row["user_id"],
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_parent_event_notes(family_id: str, event_id: str) -> list[dict]:
    """List parent notes attached to one event, scoped by family_id."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT note_id, family_id, event_id, user_id, note, created_at, updated_at
            FROM parent_event_notes
            WHERE family_id = ? AND event_id = ?
            ORDER BY created_at ASC, note_id ASC
            """,
            (fid, str(event_id)),
        ).fetchall()
    return [_note_row_to_dict(row) for row in rows]


def create_parent_event_note(
    family_id: str,
    event_id: str,
    user_id: str,
    note: str,
) -> dict:
    """Create a parent note for an existing family-scoped event."""
    fid = _normalize_family_id(family_id)
    now = _utc_now_iso()
    note_id = uuid4().hex
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO parent_event_notes
                (note_id, family_id, event_id, user_id, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (note_id, fid, str(event_id), str(user_id), str(note), now, now),
        )
        conn.commit()
    return {
        "note_id": note_id,
        "event_id": str(event_id),
        "family_id": fid,
        "user_id": str(user_id),
        "note": str(note),
        "created_at": now,
        "updated_at": now,
    }


def update_parent_event_note(
    family_id: str,
    event_id: str,
    note_id: str,
    note: str,
) -> dict | None:
    """Update a parent note only within the event's family scope."""
    fid = _normalize_family_id(family_id)
    now = _utc_now_iso()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            UPDATE parent_event_notes
            SET note = ?, updated_at = ?
            WHERE family_id = ? AND event_id = ? AND note_id = ?
            """,
            (str(note), now, fid, str(event_id), str(note_id)),
        )
        conn.commit()
        if cur.rowcount <= 0:
            return None
        row = conn.execute(
            """
            SELECT note_id, family_id, event_id, user_id, note, created_at, updated_at
            FROM parent_event_notes
            WHERE family_id = ? AND event_id = ? AND note_id = ?
            """,
            (fid, str(event_id), str(note_id)),
        ).fetchone()
    return _note_row_to_dict(row) if row else None


def delete_parent_event_note(family_id: str, event_id: str, note_id: str) -> bool:
    """Delete a parent note only within the event's family scope."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM parent_event_notes
            WHERE family_id = ? AND event_id = ? AND note_id = ?
            """,
            (fid, str(event_id), str(note_id)),
        )
        conn.commit()
    return cur.rowcount > 0


def delete_family_record(family_id: str) -> bool:
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT family_id FROM families WHERE family_id = ?",
            (fid,),
        ).fetchone()
        family_exists = row is not None

        # Delete order matters: child rows before parent rows.
        # auth_tokens has no FK to families — must cascade manually via user_id.
        user_rows = conn.execute(
            "SELECT user_id FROM users WHERE family_name = ?",
            (fid,),
        ).fetchall()
        user_ids = [str(row["user_id"]) for row in user_rows]
        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            # Step 1: auth_tokens (no FK to families; references users)
            conn.execute(
                f"DELETE FROM auth_tokens WHERE user_id IN ({placeholders})",
                tuple(user_ids),
            )

        # Step 2: turns (FK → conversations, not families directly)
        conn.execute(
            """
            DELETE FROM turns
            WHERE session_id IN (
                SELECT session_id FROM conversations WHERE family_id = ?
            )
            """,
            (fid,),
        )
        # Steps 3-5: tables with FK → families (ON DELETE CASCADE would handle
        # these if FK enforcement is active, but explicit deletes are safer)
        conn.execute("DELETE FROM conversations WHERE family_id = ?", (fid,))
        conn.execute("DELETE FROM parent_event_notes WHERE family_id = ?", (fid,))
        conn.execute("DELETE FROM events WHERE family_id = ?", (fid,))
        conn.execute("DELETE FROM tasks WHERE family_id = ?", (fid,))

        # Steps 6-12: newer family-scoped feature tables.
        ALLOWED_CLEANUP_TABLES = frozenset({
            "conversations",
            "events",
            "tasks",
            "users",
            "auth_tokens",
            "learning_schedules",
            "emotion_logs",
            "emotion_journal",
            "emotion_alerts",
            "persona",
            "education_sessions",
            "turns",
            "curriculum_schedules",
            "game_scores",
            "parent_event_notes",
            "child_profiles",
            "child_content_settings",
            "interaction_limit_settings",
            "daily_interaction_usage",
            "sleep_schedule_settings",
            "notification_settings",
            "push_subscriptions",
            "report_exports",
            "content_items",
            "device_pairing_codes",
            "robot_location_metadata",
            "parent_chat_sessions",
            "parent_chat_messages",
            # Bảng family-scoped bị bỏ sót trước đây → orphan khi xóa gia đình
            # (gia đình mới trùng family_id sẽ kế thừa data trẻ cũ). Bổ sung:
            "special_memories",
            "youtube_channels",
            "exam_sessions",
            "exam_papers",
            "question_bank",
            "learning_progress",
            "learning_streaks",
        })
        for table_name in (
            "learning_schedules",
            "special_memories",
            "youtube_channels",
            "exam_sessions",
            "exam_papers",
            "question_bank",
            "learning_progress",
            "learning_streaks",
            "emotion_logs",
            "emotion_journal",
            "emotion_alerts",
            "persona",
            "education_sessions",
            "curriculum_schedules",
            "game_scores",
            "child_content_settings",
            "interaction_limit_settings",
            "daily_interaction_usage",
            "sleep_schedule_settings",
            "notification_settings",
            "push_subscriptions",
            "report_exports",
            "content_items",
            "device_pairing_codes",
            "robot_location_metadata",
            "parent_chat_messages",
            "parent_chat_sessions",
            "child_profiles",
        ):
            if table_name not in ALLOWED_CLEANUP_TABLES:
                logger.error("[DB] Rejected invalid table name: %s", table_name)
                continue
            try:
                conn.execute(f"DELETE FROM {table_name} WHERE family_id = ?", (fid,))
            except Exception:
                pass

        # Step 13: users (FK → families)
        conn.execute("DELETE FROM users WHERE family_name = ?", (fid,))
        # Step 14: families (parent row — delete last)
        cur = conn.execute("DELETE FROM families WHERE family_id = ?", (fid,))
        conn.commit()
        return family_exists and cur.rowcount > 0


def is_user_admin(user_id: str) -> bool:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT is_admin, is_active FROM users WHERE user_id = ?",
            (str(user_id),),
        ).fetchone()
    return bool(row and row["is_active"] and row["is_admin"])


def get_token_version(user_id: str) -> int:
    """Trả về token_version hiện tại của user. Trả 0 nếu user không tồn tại."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_version FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return int(row["token_version"]) if row else 0


def increment_token_version(user_id: str) -> int:
    """Tăng token_version, vô hiệu hóa tất cả access token hiện có. Trả về version mới."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET token_version = token_version + 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT token_version FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row["token_version"]) if row else 0


def get_user_by_id(user_id: str) -> dict | None:
    """Trả về dict {user_id, username, family_name, created_at} hoặc None."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, family_name, created_at, is_admin FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def update_user_password(user_id: str, new_password: str) -> bool:
    """Hash new_password va update DB. Token version do revoke_all_tokens_for_user() tang."""
    from src.infrastructure.auth.auth import hash_password
    new_hash = hash_password(new_password)
    with get_db_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash=? WHERE user_id=?",
            (new_hash, user_id),
        )
        conn.commit()
    return cur.rowcount > 0


def revoke_all_tokens_for_user(user_id: str) -> int:
    """Revoke tất cả refresh token + tăng token_version. Trả về số refresh token bị revoke."""
    with get_db_connection() as conn:
        cur = conn.execute(
            "UPDATE auth_tokens SET is_revoked=1 WHERE user_id=? AND is_revoked=0",
            (user_id,)
        )
        count = cur.rowcount
        conn.execute(
            "UPDATE users SET token_version = token_version + 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        return count


# ── US7 (spec 006): vai trò gia đình + phân quyền con ──────────────────────────

_FAMILY_PERM_COLS = (
    "child_can_monitor", "child_can_journal", "child_can_notifications",
    "child_can_sleep", "child_can_safety", "child_can_device", "child_can_members",
)


def get_user_role(user_id: str) -> str:
    """Trả vai trò gia đình của user ('owner'|'parent'|'child'). Mặc định 'parent'."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE user_id = ?", (str(user_id),)
        ).fetchone()
    return row["role"] if row and row["role"] else "parent"


def get_family_permissions(family_name: str) -> dict:
    """Quyền con của gia đình; mặc định an toàn (tất cả 0) khi chưa cấu hình."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM family_permissions WHERE family_name = ?", (family_name,)
        ).fetchone()
    if not row:
        return {c: 0 for c in _FAMILY_PERM_COLS}
    return {c: int(row[c]) for c in _FAMILY_PERM_COLS}


def set_family_permissions(family_name: str, perms: dict) -> dict:
    """Ghi quyền con (chỉ owner gọi qua endpoint). Merge với giá trị hiện có."""
    cur = get_family_permissions(family_name)
    merged = {c: int(bool(perms.get(c, cur[c]))) for c in _FAMILY_PERM_COLS}
    cols = ", ".join(_FAMILY_PERM_COLS)
    placeholders = ", ".join("?" for _ in _FAMILY_PERM_COLS)
    updates = ", ".join(f"{c}=excluded.{c}" for c in _FAMILY_PERM_COLS)
    with get_db_connection() as conn:
        conn.execute(
            f"""INSERT INTO family_permissions (family_name, {cols}, updated_at)
                VALUES (?, {placeholders}, ?)
                ON CONFLICT(family_name) DO UPDATE SET {updates}, updated_at=excluded.updated_at""",
            (family_name, *[merged[c] for c in _FAMILY_PERM_COLS], _utc_now_iso()),
        )
        conn.commit()
    return merged


def list_family_members(family_name: str) -> list[dict]:
    """Danh sách thành viên trong gia đình (owner trước, rồi parent, rồi child)."""
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT user_id, username, role, child_profile_id, is_active, created_at
               FROM users WHERE family_name = ?
               ORDER BY CASE role WHEN 'owner' THEN 0 WHEN 'parent' THEN 1 ELSE 2 END, user_id""",
            (family_name,),
        ).fetchall()
    return [dict(r) for r in rows]


def count_family_owners(family_name: str) -> int:
    """Số owner đang active của gia đình (để chặn xóa owner cuối)."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE family_name = ? AND role = 'owner' AND is_active = 1",
            (family_name,),
        ).fetchone()
    return int(row["n"]) if row else 0


def set_member_role(family_name: str, user_id: str, role: str) -> bool:
    """Đổi vai trò một thành viên trong gia đình. Chỉ chấp nhận owner/parent/child."""
    if role not in ("owner", "parent", "child"):
        return False
    with get_db_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET role = ? WHERE user_id = ? AND family_name = ?",
            (role, str(user_id), family_name),
        )
        conn.commit()
    return cur.rowcount > 0


def remove_family_member(family_name: str, user_id: str) -> bool:
    """Xóa một thành viên khỏi gia đình (scope theo family_name để cô lập)."""
    with get_db_connection() as conn:
        cur = conn.execute(
            "DELETE FROM users WHERE user_id = ? AND family_name = ?",
            (str(user_id), family_name),
        )
        conn.commit()
    return cur.rowcount > 0
