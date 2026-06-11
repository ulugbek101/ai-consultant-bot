import asyncio
import pymysql

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "tax":         ["налог", "ндс", "ндфл", "декларац", "гни", "солиқ", "налогообложен"],
    "accounting":  ["бухгалтер", "учёт", "учет", "отчётност", "отчетност", "баланс", "проводк"],
    "legal":       ["юридическ", "договор", "суд", "иск", "юрист", "закон", "правов"],
    "procurement": ["закупк", "тендер", "госзакупк", "xarid"],
    "ecology":     ["эколог", "природоохран"],
    "business":    ["бизнес", "предприяти", "регистрац", "ооо", " ип ", "йтт", "тадбиркор"],
}


def classify_topic(text: str) -> str:
    t = text.lower()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return topic
    return "other"


class Database:
    def __init__(self, db_name, db_password, db_user, db_port, db_host):
        self.db_name = db_name
        self.db_password = db_password
        self.db_user = db_user
        self.db_port = db_port
        self.db_host = db_host

    def connect(self):
        return pymysql.Connection(
            database=self.db_name,
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            cursorclass=pymysql.cursors.DictCursor
        )

    def execute(self, sql: str, params: tuple = (), commit=False, fetchone=False, fetchall=False):
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            data = None
            if fetchone:
                data = cursor.fetchone()
            elif fetchall:
                data = cursor.fetchall()
            if commit:
                conn.commit()
            return data
        finally:
            conn.close()

    async def execute_async(self, sql: str, params: tuple = (), commit=False, fetchone=False, fetchall=False):
        return await asyncio.to_thread(self.execute, sql, params, commit, fetchone, fetchall)

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def create_tables(self) -> None:
        self.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INT PRIMARY KEY AUTO_INCREMENT,
                telegram_id     BIGINT NOT NULL UNIQUE,
                first_name      VARCHAR(100),
                last_name       VARCHAR(100),
                fullname        VARCHAR(200),
                username        VARCHAR(100),
                language_code   VARCHAR(10),
                is_premium      TINYINT(1) DEFAULT 0,
                phone           VARCHAR(30),
                email           VARCHAR(150),
                company_name    VARCHAR(200),
                business_type   VARCHAR(100),
                city            VARCHAR(100),
                notes           TEXT,
                message_count   INT DEFAULT 0,
                last_active_at  TIMESTAMP NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """, commit=True)

        self.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INT PRIMARY KEY AUTO_INCREMENT,
                telegram_id BIGINT NOT NULL,
                role        VARCHAR(15) NOT NULL,
                content     TEXT NOT NULL,
                topic       VARCHAR(50) NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_telegram_id (telegram_id)
            )
        """, commit=True)
        # Migrate existing tables that lack the topic column
        try:
            self.execute(
                "ALTER TABLE messages ADD COLUMN topic VARCHAR(50) NULL",
                commit=True
            )
        except Exception:
            pass

        self.execute("""
            CREATE TABLE IF NOT EXISTS subcategories (
                id           INT PRIMARY KEY AUTO_INCREMENT,
                category_key VARCHAR(50)  NOT NULL,
                label        VARCHAR(200) NOT NULL,
                sort_order   INT          DEFAULT 0,
                is_active    TINYINT(1)   DEFAULT 1,
                created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_cat_key (category_key)
            )
        """, commit=True)

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def add_or_update_user(self, telegram_id: int, first_name: str = None,
                                  last_name: str = None, fullname: str = None,
                                  username: str = None, language_code: str = None,
                                  is_premium: bool = False) -> None:
        await self.execute_async("""
            INSERT INTO users (telegram_id, first_name, last_name, fullname, username,
                               language_code, is_premium, last_active_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                first_name     = VALUES(first_name),
                last_name      = VALUES(last_name),
                fullname       = VALUES(fullname),
                username       = VALUES(username),
                language_code  = VALUES(language_code),
                is_premium     = VALUES(is_premium),
                last_active_at = NOW()
        """, (telegram_id, first_name, last_name, fullname, username,
              language_code, int(is_premium)), commit=True)

    async def get_user(self, telegram_id: int) -> dict | None:
        return await self.execute_async(
            "SELECT * FROM users WHERE telegram_id = %s",
            (telegram_id,), fetchone=True
        )

    async def update_contact_info(self, telegram_id: int,
                                   phone: str = None,
                                   email: str = None,
                                   company_name: str = None,
                                   business_type: str = None,
                                   city: str = None,
                                   notes: str = None) -> None:
        fields, values = [], []
        for col, val in [("phone", phone), ("email", email),
                         ("company_name", company_name),
                         ("business_type", business_type),
                         ("city", city), ("notes", notes)]:
            if val is not None:
                fields.append(f"{col} = %s")
                values.append(val)
        if not fields:
            return
        values.append(telegram_id)
        await self.execute_async(
            f"UPDATE users SET {', '.join(fields)} WHERE telegram_id = %s",
            tuple(values), commit=True
        )

    async def increment_message_count(self, telegram_id: int) -> None:
        await self.execute_async(
            "UPDATE users SET message_count = message_count + 1, last_active_at = NOW() WHERE telegram_id = %s",
            (telegram_id,), commit=True
        )

    # ------------------------------------------------------------------
    # Chat history
    # ------------------------------------------------------------------

    async def save_message(self, telegram_id: int, role: str, content: str, topic: str = None) -> None:
        await self.execute_async(
            "INSERT INTO messages (telegram_id, role, content, topic) VALUES (%s, %s, %s, %s)",
            (telegram_id, role, content, topic), commit=True
        )

    async def get_chat_history(self, telegram_id: int, limit: int = 12) -> list:
        rows = await self.execute_async(
            """SELECT role, content FROM messages
               WHERE telegram_id = %s
               ORDER BY created_at DESC
               LIMIT %s""",
            (telegram_id, limit), fetchall=True
        )
        return list(reversed(rows)) if rows else []

    async def clear_chat_history(self, telegram_id: int) -> None:
        await self.execute_async(
            "DELETE FROM messages WHERE telegram_id = %s",
            (telegram_id,), commit=True
        )

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    async def get_users_count(self) -> int:
        row = await self.execute_async(
            "SELECT COUNT(*) as cnt FROM users", fetchone=True
        )
        return (row or {}).get("cnt", 0) or 0

    async def get_users_page(self, page: int = 1, per_page: int = 10) -> list:
        offset = (page - 1) * per_page
        return await self.execute_async(
            """SELECT telegram_id, fullname, username, phone, message_count, last_active_at
               FROM users ORDER BY last_active_at DESC LIMIT %s OFFSET %s""",
            (per_page, offset), fetchall=True
        ) or []

    async def get_full_history(self, telegram_id: int, limit: int = 20) -> list:
        rows = await self.execute_async(
            """SELECT role, content, created_at FROM messages
               WHERE telegram_id = %s ORDER BY created_at DESC LIMIT %s""",
            (telegram_id, limit), fetchall=True
        )
        return list(reversed(rows)) if rows else []

    async def get_stats(self) -> dict:
        def _val(row): return (row or {}).get("c", 0) or 0
        total_users = _val(await self.execute_async(
            "SELECT COUNT(*) as c FROM users", fetchone=True))
        total_msgs = _val(await self.execute_async(
            "SELECT COUNT(*) as c FROM messages WHERE role='user'", fetchone=True))
        today_msgs = _val(await self.execute_async(
            "SELECT COUNT(*) as c FROM messages WHERE role='user' AND DATE(created_at)=CURDATE()",
            fetchone=True))
        week_msgs = _val(await self.execute_async(
            "SELECT COUNT(*) as c FROM messages WHERE role='user' "
            "AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)", fetchone=True))
        new_today = _val(await self.execute_async(
            "SELECT COUNT(*) as c FROM users WHERE DATE(created_at)=CURDATE()", fetchone=True))
        top_users = await self.execute_async(
            "SELECT fullname, username, telegram_id, message_count "
            "FROM users ORDER BY message_count DESC LIMIT 5",
            fetchall=True
        ) or []
        return {
            "total_users": total_users, "total_msgs": total_msgs,
            "today_msgs": today_msgs, "week_msgs": week_msgs,
            "new_today": new_today, "top_users": top_users,
        }

    # ------------------------------------------------------------------
    # Subcategories
    # ------------------------------------------------------------------

    _SUBCATEGORY_SEED = [
        # 1. ПОМОЩЬ С БУХГАЛТЕРИЕЙ
        ("svc_accounting", "Ведение бухгалтерского учета по НСБУ (НСФО)",              1),
        ("svc_accounting", "Ведение бухгалтерского учета по МСФО",                     2),
        ("svc_accounting", "Восстановление бухгалтерского учета",                      3),
        ("svc_accounting", "Консультации по импортным и экспортным операциям",         4),
        # 2. НАЛОГОВОЕ КОНСУЛЬТИРОВАНИЕ
        ("svc_tax",        "Выбор оптимальной системы налогообложения",                1),
        ("svc_tax",        "Подготовка налоговой отчетности",                          2),
        ("svc_tax",        "Ответы на требования налоговых органов",                   3),
        ("svc_tax",        "Сопровождение при налоговом аудите",                       4),
        # 3. ЮРИДИЧЕСКАЯ КОНСУЛЬТАЦИЯ
        ("svc_legal",      "Регистрация ООО, СП, ЯТТ",                                1),
        ("svc_legal",      "Правовая экспертиза договоров",                            2),
        ("svc_legal",      "Претензионная работа с должниками",                        3),
        ("svc_legal",      "Юридические консультации для бизнеса",                     4),
        ("svc_legal",      "Консультации по трудовому законодательству",               5),
        # 4. АУДИТ
        ("svc_audit",      "Проведение обязательного и инициативного аудита",          1),
        ("svc_audit",      "Аудит для резидентов IT Park",                             2),
        ("svc_audit",      "Заключения по крупным сделкам и сделкам с аффилированными лицами", 3),
        ("svc_audit",      "Трансформация отчетности по МСФО",                        4),
        # 5. КОНСУЛЬТАЦИИ ПО КРЕДИТАМ И ИНВЕСТИЦИЯМ
        ("svc_credit",     "Консультации по получению кредитов, включая льготные программы", 1),
        ("svc_credit",     "Разработка бизнес-планов и ТЭО для кредитования и инвестиций",  2),
        # 6. ФИНАНСОВЫЙ КОНСАЛТИНГ ПО ДРУГИМ ВОПРОСАМ
        ("svc_finance",    "Консультации по корпоративному управлению",                1),
        ("svc_finance",    "Сопровождение работы с учредителями и инвесторами",        2),
        ("svc_finance",    "Консультации по государственным закупкам и сопровождение работы с государственными предприятиями", 3),
        ("svc_finance",    "Консалтинг по вопросам финансово-хозяйственной деятельности", 4),
        # 7. КАДРОВЫЙ УЧЕТ
        ("svc_hr",         "Кадровый учет",                                            1),
        ("svc_hr",         "Консультации по трудовому законодательству",               2),
    ]

    def seed_subcategories(self) -> None:
        row = self.execute("SELECT COUNT(*) as cnt FROM subcategories", fetchone=True)
        if (row or {}).get("cnt", 0):
            return  # already seeded
        for category_key, label, sort_order in self._SUBCATEGORY_SEED:
            self.execute(
                "INSERT INTO subcategories (category_key, label, sort_order) VALUES (%s, %s, %s)",
                (category_key, label, sort_order), commit=True,
            )

    async def get_subcategories(self, category_key: str) -> list:
        return await self.execute_async(
            """SELECT id, category_key, label FROM subcategories
               WHERE category_key = %s AND is_active = 1
               ORDER BY sort_order, id""",
            (category_key,), fetchall=True
        ) or []

    async def get_subcategory(self, sub_id: int) -> dict | None:
        return await self.execute_async(
            "SELECT id, category_key, label FROM subcategories WHERE id = %s",
            (sub_id,), fetchone=True
        )

    async def get_topic_stats(self, days: int = 30) -> list:
        return await self.execute_async(
            """SELECT topic, COUNT(*) as cnt FROM messages
               WHERE role='user' AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
               GROUP BY topic ORDER BY cnt DESC""",
            (days,), fetchall=True
        ) or []
