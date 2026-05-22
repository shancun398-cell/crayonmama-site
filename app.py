from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response
import sqlite3
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import date, datetime
import shutil
from flask import session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import smtplib
from email.message import EmailMessage
import secrets
import csv
import io
import qrcode
from io import BytesIO
from flask import send_file


UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4"}
MAX_VIDEO_MB = 50
MAIL_USERNAME = "crayonmama90488@gmail.com"
MAIL_PASSWORD = "jdeilodgayjxxaik"
MAIL_FROM = MAIL_USERNAME
MAIL_TO = MAIL_USERNAME


def add_application_cancel_columns():
    conn = get_db()

    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(applications)").fetchall()
    ]

    if "cancel_token" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN cancel_token TEXT")

    if "cancelled_at" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN cancelled_at TEXT")

    conn.commit()
    conn.close()


def add_application_child_columns():
    conn = get_db()

    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(applications)").fetchall()
    ]

    if "child4_name" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN child4_name TEXT")

    if "child4_age" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN child4_age TEXT")

    if "child5_name" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN child5_name TEXT")

    if "child5_age" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN child5_age TEXT")

    conn.commit()
    conn.close()


def send_application_mail(to_email, subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MAIL_USERNAME
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        smtp.send_message(msg)


def send_admin_mail(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        smtp.send_message(msg)


def init_member_gallery_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS member_gallery_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            display_order INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def init_public_members_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS public_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT,
            comment TEXT,
            icon TEXT DEFAULT '👤',
            image_path TEXT,
            display_order INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def add_members_page_image_columns():
    conn = get_db()

    page_columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(site_pages)").fetchall()
    ]
    if "main_image" not in page_columns:
        conn.execute("ALTER TABLE site_pages ADD COLUMN main_image TEXT")

    member_columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(public_members)").fetchall()
    ]
    if "image_path" not in member_columns:
        conn.execute("ALTER TABLE public_members ADD COLUMN image_path TEXT")

    conn.commit()
    conn.close()


def add_status_column():
    conn = get_db()
    try:
        conn.execute(
            "ALTER TABLE contacts ADD COLUMN status TEXT DEFAULT '0'")
        conn.commit()
        print("statusカラム追加完了")
    except Exception as e:
        print("すでに追加済み or エラー:", e)
    finally:
        conn.close()


def alter_events_table():
    conn = get_db()
    columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(events)").fetchall()
    ]

    if "video_path" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN video_path TEXT")

    if "image_url" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN image_url TEXT")

    conn.commit()
    conn.close()


def allowed_video_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS
    )


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def init_site_pages_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS site_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            body TEXT
        )
    """)

    page = conn.execute("""
        SELECT * FROM site_pages WHERE page_key = 'members'
    """).fetchone()

    if not page:
        conn.execute(
            """
            INSERT INTO site_pages (page_key, title, body)
            VALUES (?, ?, ?)
        """,
            (
                "members",
                "活動・メンバー紹介",
                "くれよんママは、音楽・絵本・手遊びを通して、親子の笑顔とつながりを育む活動を行っています。",
            ),
        )

    conn.commit()
    conn.close()


def add_time_columns():
    conn = get_db()

    columns = [
        ("events", "time1_start", "TEXT"),
        ("events", "time1_end", "TEXT"),
        ("events", "time2_start", "TEXT"),
        ("events", "time2_end", "TEXT"),
        ("events", "capacity_time1", "INTEGER"),
        ("events", "capacity_time2", "INTEGER"),
        ("applications", "time_slot", "TEXT DEFAULT '1'")
    ]

    for table, column, col_type in columns:
        try:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            )
            print(f"追加: {table}.{column}")

        except Exception as e:
            if "duplicate column name" in str(e):
                pass
            else:
                print(e)

    conn.commit()
    conn.close()


app = Flask(__name__)
app.secret_key = "crayonmama-secret-key"
app.secret_key = "change-this-secret-key"

DB_NAME = "database.db"
app.config["UPLOAD_FOLDER"] = "static/uploads"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_users_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin'
        )
    """)

    admin = conn.execute(
        """
        SELECT * FROM users WHERE email = ?
    """,
        ("admin@example.com",),
    ).fetchone()

    if not admin:
        conn.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """,
            (
                "管理者",
                "admin@example.com",
                generate_password_hash("admin1234"),
                "admin",
            ),
        )

    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("admin_login"))

        if session.get("user_role") != "admin":
            return redirect(url_for("admin_dashboard"))

        return view(*args, **kwargs)

    return wrapped_view


def add_event_extra_columns():
    conn = get_db()

    columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(events)").fetchall()
    ]

    if "start_time" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN start_time TEXT")

    if "flyer_image" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN flyer_image TEXT")

    if "additional_notes" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN additional_notes TEXT")

    if "belongings" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN belongings TEXT")

    if "location" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN location TEXT")

    conn.commit()
    conn.close()


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            event_date TEXT NOT NULL,
            status TEXT NOT NULL,
            description TEXT,
            capacity INTEGER,
            image_url TEXT,
            location TEXT,
            youtube_url TEXT,
            video_path TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            parent_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            adult_count INTEGER NOT NULL,
            child_count INTEGER NOT NULL,
            child1_name TEXT,
            child1_age TEXT,
            child2_name TEXT,
            child2_age TEXT,
            child3_name TEXT,
            child3_age TEXT,
            child4_name TEXT,
            child4_age TEXT,
            child5_name TEXT,
            child5_age TEXT,
            status TEXT NOT NULL DEFAULT 'confirmed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mail_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            subject TEXT,
            message TEXT,
            target TEXT,
            sent_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_type TEXT NOT NULL,
            name TEXT,
            email TEXT,
            message TEXT NOT NULL,
            reply_needed INTEGER DEFAULT 0,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            satisfaction TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

    conn.commit()
    conn.close()

# QRコード生成


@app.route("/admin/events/<int:event_id>/survey_qr")
@login_required
def survey_qr(event_id):

    survey_url = url_for(
        "event_survey",
        event_id=event_id,
        _external=True
    )

    qr = qrcode.make(survey_url)

    img_io = BytesIO()
    qr.save(img_io, "PNG")
    img_io.seek(0)

    return send_file(
        img_io,
        mimetype="image/png"
    )

# アンケートページ


@app.route("/admin/surveys")
@login_required
def admin_surveys():
    selected_year = request.args.get("year", "")
    selected_event_id = request.args.get("event_id", "")

    conn = get_db()

    year_list = conn.execute("""
        SELECT DISTINCT strftime('%Y', event_date) AS year
        FROM events
        WHERE date(event_date) < date('now')
        ORDER BY year DESC
    """).fetchall()

    event_list = conn.execute("""
        SELECT id, title, event_date
        FROM events
        WHERE date(event_date) < date('now')
        ORDER BY event_date DESC
    """).fetchall()

    params = []

    where_sql = "WHERE date(events.event_date) < date('now')"

    if selected_year:
        where_sql += " AND strftime('%Y', events.event_date) = ?"
        params.append(selected_year)

    if selected_event_id:
        where_sql += " AND events.id = ?"
        params.append(selected_event_id)

    surveys = conn.execute(f"""
        SELECT
            surveys.*,
            events.id AS event_id,
            events.title AS event_title,
            events.event_date
        FROM surveys
        JOIN events
        ON surveys.event_id = events.id
        {where_sql}
        ORDER BY events.event_date DESC, surveys.created_at DESC
    """, params).fetchall()

    grouped_surveys = []

    for survey in surveys:
        group = None

        for g in grouped_surveys:
            if g["event_id"] == survey["event_id"]:
                group = g
                break

        if group is None:
            group = {
                "event_id": survey["event_id"],
                "event_title": survey["event_title"],
                "event_date": survey["event_date"],
                "count": 0,
                "items": []
            }
            grouped_surveys.append(group)

        group["items"].append(survey)
        group["count"] += 1

    conn.close()

    return render_template(
        "admin_surveys.html",
        grouped_surveys=grouped_surveys,
        year_list=year_list,
        selected_year=selected_year,
        event_list=event_list,
        selected_event_id=selected_event_id,
    )


@app.route("/events/<int:event_id>/survey", methods=["GET", "POST"])
def event_survey(event_id):

    conn = get_db()

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ?
        """,
        (event_id,)
    ).fetchone()

    if event is None:
        conn.close()
        return "イベントが見つかりません", 404

    if request.method == "POST":

        satisfaction = request.form.get("satisfaction")
        comment = request.form.get("comment")

        conn.execute(
            """
            INSERT INTO surveys (
                event_id,
                satisfaction,
                comment
            )
            VALUES (?, ?, ?)
            """,
            (
                event_id,
                satisfaction,
                comment
            )
        )

        conn.commit()
        conn.close()

        return render_template(
            "survey_complete.html",
            event=event
        )

    conn.close()

    return render_template(
        "event_survey.html",
        event=event
    )

# 管理者向けお問い合わせ既読API


@app.route("/admin/contacts/<int:contact_id>/read", methods=["POST"])
def admin_contact_read(contact_id):

    conn = get_db()

    conn.execute("""
        UPDATE contacts
        SET is_read = 1
        WHERE id = ?
    """, (contact_id,))

    conn.commit()
    conn.close()

    return "", 204

# 管理者ユーザーテーブルの初期化


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            return redirect(url_for("admin_dashboard"))

        return render_template(
            "admin_login.html", error="メールアドレスまたはパスワードが違います"
        )

    return render_template("admin_login.html")


# ブレッドクラム用のコンテキストプロセッサ


@app.context_processor
def inject_breadcrumbs():
    endpoint = request.endpoint

    breadcrumb_map = {
        "events": [
            {"label": "ホーム", "url": url_for("index")},
            {"label": "イベント一覧", "url": url_for("events")},
        ],
        "event_detail": [
            {"label": "ホーム", "url": url_for("index")},
            {"label": "イベント一覧", "url": url_for("events")},
            {"label": "詳細", "url": "#"},
        ],
        "archive": [
            {"label": "ホーム", "url": url_for("index")},
            {"label": "ギャラリー", "url": url_for("archive")},
        ],
        "archive_detail": [
            {"label": "ホーム", "url": url_for("index")},
            {"label": "ギャラリー", "url": url_for("archive")},
            {"label": "詳細", "url": "#"},
        ],
    }

    return {"breadcrumbs": breadcrumb_map.get(endpoint, [])}


# 管理者ユーザー一覧ルート


@app.route("/admin/users")
@admin_required
def admin_users():
    conn = get_db()

    users = conn.execute("""
        SELECT id, name, email, role
        FROM users
        ORDER BY id ASC
    """).fetchall()

    conn.close()

    return render_template("admin_users.html", users=users)


# 管理者ユーザー新規作成ルート


@app.route("/admin/users/new", methods=["GET", "POST"])
@admin_required
def admin_user_new():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        conn = get_db()

        conn.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """,
            (name, email, generate_password_hash(password), role),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_users"))

    return render_template("admin_user_form.html")


# 管理者ユーザー編集ルート


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_user_edit(user_id):
    conn = get_db()

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        role = request.form.get("role")

        conn.execute(
            """
            UPDATE users
            SET name = ?, email = ?, role = ?
            WHERE id = ?
        """,
            (name, email, role, user_id),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_users"))

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
    """,
        (user_id,),
    ).fetchone()

    conn.close()

    return render_template("admin_user_form.html", user=user)


# 管理者ユーザー削除ルート


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_user_delete(user_id):
    login_user_id = session.get("user_id")

    # 自分自身は削除不可
    if login_user_id == user_id:
        return redirect(url_for("admin_users"))

    conn = get_db()

    target_user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
    """,
        (user_id,),
    ).fetchone()

    if not target_user:
        conn.close()
        return redirect(url_for("admin_users"))

    # 管理者が1人だけなら削除不可
    if target_user["role"] == "admin":
        admin_count = conn.execute("""
            SELECT COUNT(*) AS count
            FROM users
            WHERE role = 'admin'
        """).fetchone()["count"]

        if admin_count <= 1:
            conn.close()
            return redirect(url_for("admin_users"))

    conn.execute(
        """
        DELETE FROM users
        WHERE id = ?
    """,
        (user_id,),
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_users"))


# 管理者ユーザーパスワード変更ルート


@app.route("/admin/users/<int:user_id>/password", methods=["GET", "POST"])
@admin_required
def admin_user_password(user_id):
    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
    """,
        (user_id,),
    ).fetchone()

    if not user:
        conn.close()
        return redirect(url_for("admin_users"))

    if request.method == "POST":
        password = request.form.get("password")

        conn.execute(
            """
            UPDATE users
            SET password = ?
            WHERE id = ?
        """,
            (generate_password_hash(password), user_id),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_users"))

    conn.close()

    return render_template("admin_user_password.html", user=user)


# トップページルート


@app.route("/")
def index():
    conn = get_db()

    # 画像付与関数
    def attach_image(event):
        if not event:
            return None

        event = dict(event)

        # 活動画像を優先
        img = conn.execute(
            """
            SELECT image_path
            FROM event_images
            WHERE event_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (event["id"],),
        ).fetchone()

        if img:
            event["image_url"] = img["image_path"]
            return event

        # 活動画像がなければチラシ
        if "flyer_image" in event and event["flyer_image"]:
            event["image_url"] = event["flyer_image"]
            return event

        event["image_url"] = None
        return event

    # 次回イベント
    next_event = conn.execute("""
        SELECT * FROM events
        WHERE status = '公開'
        AND event_date >= date('now')
        ORDER BY event_date ASC
        LIMIT 1
    """).fetchone()

    if next_event:
        next_event = dict(next_event)

        capacity1 = next_event["capacity_time1"] or 0
        capacity2 = next_event["capacity_time2"] or 0

        capacity = capacity1 + capacity2

        if capacity <= 0:
            capacity = next_event["capacity"] or 10

        confirmed_count = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM applications
            WHERE event_id = ?
            AND status = 'confirmed'
        """, (next_event["id"],)).fetchone()["cnt"]

        waiting_count = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM applications
            WHERE event_id = ?
            AND status = 'waiting'
        """, (next_event["id"],)).fetchone()["cnt"]

        next_event["confirmed_count"] = confirmed_count
        next_event["waiting_count"] = waiting_count
        next_event["remaining_count"] = max(0, capacity - confirmed_count)
        next_event["display_capacity"] = capacity
        next_event["progress_percent"] = min(
            100, int((confirmed_count / capacity) * 100))

    # 今後イベント
    upcoming_events = conn.execute("""
        SELECT * FROM events
        WHERE status = '公開'
        AND event_date >= date('now')
        ORDER BY event_date ASC
    """).fetchall()

    # 過去イベント
    recent_events = conn.execute("""
        SELECT * FROM events
        WHERE status = '公開'
        AND event_date < date('now')
        ORDER BY event_date DESC
        LIMIT 4
    """).fetchall()

    # 活動・メンバー紹介ページ情報
    page = conn.execute("""
        SELECT *
        FROM site_pages
        WHERE page_key = 'members'
    """).fetchone()

    # ★ここで画像を付与
    next_event = attach_image(next_event)
    upcoming_events = [attach_image(e) for e in upcoming_events]
    recent_events = [attach_image(e) for e in recent_events]

    conn.close()

    return render_template(
        "index.html",
        next_event=next_event,
        upcoming_events=upcoming_events,
        recent_events=recent_events,
        page=page,
    )


# 公開イベント一覧ルート


@app.route("/events")
def events():
    conn = get_db()

    selected_category = request.args.get("category", "").strip()

    upcoming_events = conn.execute("""
        SELECT *
        FROM events
        WHERE status = '公開'
          AND event_date >= date('now')
        ORDER BY event_date ASC, id ASC
    """).fetchall()

    past_events = conn.execute("""
        SELECT *
        FROM events
        WHERE status = '公開'
        AND event_date < date('now')
        ORDER BY event_date DESC, id DESC
        LIMIT 4
    """).fetchall()

    event_list = []
    category_set = set()

    for event in upcoming_events:
        category = (
            event["category"]
            if "category" in event.keys() and event["category"]
            else ""
        )
        if category:
            category_set.add(category)

        if selected_category and category != selected_category:
            continue

        first_image = None
        try:
            first_image = conn.execute(
                """
                SELECT image_path
                FROM event_images
                WHERE event_id = ?
                ORDER BY id ASC
                LIMIT 1
            """,
                (event["id"],),
            ).fetchone()
        except:
            first_image = None

        # ★ここを丸ごと置き換え
        image_url = None

        # ① チラシ優先
        if "flyer_image" in event.keys() and event["flyer_image"]:
            image_url = event["flyer_image"]

        # ② なければ既存画像
        else:
            first_image = None
            try:
                first_image = conn.execute(
                    """
                    SELECT image_path
                    FROM event_images
                    WHERE event_id = ?
                    ORDER BY id ASC
                    LIMIT 1
                """,
                    (event["id"],),
                ).fetchone()
            except:
                first_image = None

            if first_image:
                image_url = first_image["image_path"]
            elif "image_url" in event.keys() and event["image_url"]:
                image_url = event["image_url"]

        capacity1 = event["capacity_time1"] or 0
        capacity2 = event["capacity_time2"] or 0

        capacity = capacity1 + capacity2

        if capacity <= 0:
            capacity = 10

        confirmed_row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM applications
            WHERE event_id = ?
            AND status = 'confirmed'
        """,
            (event["id"],),
        ).fetchone()

        confirmed_count = confirmed_row["cnt"] if confirmed_row else 0
        remaining_count = capacity - confirmed_count
        if remaining_count < 0:
            remaining_count = 0

        progress_percent = min(100, int((confirmed_count / capacity) * 100))

        event_list.append(
            {"progress_percent": progress_percent,
                "id": event["id"],
                "title": event["title"],
                "category": category,
                "event_date": event["event_date"],
                "time1_start": event["time1_start"] if "time1_start" in event.keys() else "",
                "time1_end": event["time1_end"] if "time1_end" in event.keys() else "",
                "time2_start": event["time2_start"] if "time2_start" in event.keys() else "",
                "time2_end": event["time2_end"] if "time2_end" in event.keys() else "",
                "location": event["location"] if "location" in event.keys() else "",
                "capacity": capacity,
                "confirmed_count": confirmed_count,
                "remaining_count": remaining_count,
                "image_url": image_url,
                "status_text": "キャンセル待ち受付" if remaining_count == 0 else "受付中",
                "status_class": "full" if remaining_count == 0 else "open",
             }
        )

    past_event_cards = []

    for event in past_events:
        past_image = conn.execute(
            """
            SELECT image_path
            FROM event_images
            WHERE event_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (event["id"],),
        ).fetchone()

        past_image_url = None

        if past_image:
            past_image_url = past_image["image_path"]
        elif "flyer_image" in event.keys() and event["flyer_image"]:
            past_image_url = event["flyer_image"]
        elif "image_url" in event.keys() and event["image_url"]:
            past_image_url = event["image_url"]

        past_event_cards.append({
            "id": event["id"],
            "title": event["title"],
            "category": event["category"] if "category" in event.keys() else "",
            "event_date": event["event_date"],
            "image_url": past_image_url,
        })

    conn.close()

    category_list = sorted(list(category_set))

    return render_template(
        "events.html",
        upcoming_events=event_list,
        past_events=past_event_cards,
        category_list=category_list,
        selected_category=selected_category,
    )


# イベント詳細ルート


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    conn = get_db()
    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ? AND status = ?
    """,
        (event_id, "公開"),
    ).fetchone()

    capacity1 = event["capacity_time1"] or 0
    capacity2 = event["capacity_time2"] or 0

    capacity = capacity1 + capacity2

    if capacity <= 0:
        capacity = event["capacity"] or 10

    confirmed_count = conn.execute(
        """
            SELECT COUNT(*) AS cnt
            FROM applications
            WHERE event_id = ?
            AND status = 'confirmed'
        """,
        (event_id,),
    ).fetchone()["cnt"]
    confirmed_count_time1 = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM applications
        WHERE event_id = ?
        AND time_slot = '1'
        AND status = 'confirmed'
        """,
        (event_id,),
    ).fetchone()["cnt"]

    confirmed_count_time2 = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM applications
        WHERE event_id = ?
        AND time_slot = '2'
        AND status = 'confirmed'
        """,
        (event_id,),
    ).fetchone()["cnt"]

    remaining_time1 = max(0, capacity1 - confirmed_count_time1)
    remaining_time2 = max(0, capacity2 - confirmed_count_time2)

    waiting_count = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM applications
        WHERE event_id = ?
        AND status = 'waiting'
    """,
        (event_id,),
    ).fetchone()["cnt"]

    remaining = capacity - confirmed_count
    if remaining < 0:
        remaining = 0

    conn.close()

    if event is None:
        return "イベントが見つかりません", 404

    return render_template(
        "event_detail.html",
        event=event,
        remaining=remaining,
        confirmed_count=confirmed_count,
        waiting_count=waiting_count,
        remaining_time1=remaining_time1,
        remaining_time2=remaining_time2,
        capacity1=capacity1,
        capacity2=capacity2,
    )


# イベント申込ルート


@app.route("/events/<int:event_id>/apply", methods=["GET", "POST"])
def apply_form(event_id):
    conn = get_db()
    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ? AND status = ?
    """,
        (event_id, "公開"),
    ).fetchone()
    conn.close()

    if event is None:
        return "イベントが見つかりません", 404

    if request.method == "POST":
        time_slot = request.form.get("time_slot")
        adult_count = int(request.form.get("adult_count"))
        child_count = int(request.form.get("child_count"))

        total_count = adult_count + child_count

        if adult_count < 1 or adult_count > 3:
            return "大人人数は1〜3人です"
        if child_count < 1 or child_count > 5:
            return "子ども人数は1〜5人です"
        if total_count > 8:
            return "合計8人までです"

        data = request.form.to_dict()
        if time_slot == "2":
            capacity = event["capacity_time2"] or 10
        else:
            capacity = event["capacity_time1"] or 10

        conn = get_db()
        confirmed_count = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM applications
            WHERE event_id = ?
            AND time_slot = ?
            AND status = 'confirmed'
        """, (event_id, time_slot)).fetchone()["cnt"]
        conn.close()

        application_status = "confirmed"
        if confirmed_count >= capacity:
            application_status = "waiting"

        return render_template(
            "apply_confirm.html",
            event=event,
            data=data,
            status=application_status
        )

    return render_template("apply_form.html", event=event)


# イベント申込完了ルート


@app.route("/events/<int:event_id>/apply/complete", methods=["POST"])
def apply_complete(event_id):
    conn = get_db()

    data = request.form
    time_slot = data.get("time_slot", "1")

    cancel_token = secrets.token_urlsafe(32)

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ?
    """,
        (event_id,),
    ).fetchone()

    if time_slot == "2":
        capacity = event["capacity_time2"] or 10
    else:
        capacity = event["capacity_time1"] or 10

    confirmed_count = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM applications
        WHERE event_id = ?
        AND time_slot = ?
        AND status = 'confirmed'
    """,
        (event_id, time_slot),
    ).fetchone()["cnt"]

    application_status = "confirmed"

    if confirmed_count >= capacity:
        application_status = "waiting"

    conn.execute(
        """
        INSERT INTO applications (
            event_id, parent_name, email, phone,
            adult_count, child_count,
            child1_name, child1_age,
            child2_name, child2_age,
            child3_name, child3_age,
            child4_name, child4_age,
            child5_name, child5_age,
            status, cancel_token, time_slot
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            event_id,
            data.get("parent_name"),
            data.get("email"),
            data.get("phone"),
            data.get("adult_count"),
            data.get("child_count"),
            data.get("child1_name"),
            data.get("child1_age"),
            data.get("child2_name"),
            data.get("child2_age"),
            data.get("child3_name"),
            data.get("child3_age"),
            data.get("child4_name"),
            data.get("child4_age"),
            data.get("child5_name"),
            data.get("child5_age"),
            application_status,
            cancel_token,
            time_slot
        ),
    )

    conn.commit()

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ?
    """,
        (event_id,),
    ).fetchone()
    if application_status == "confirmed":
        status_message = "お申込みを受付しました。"
        status_label = "受付完了"
    else:
        status_message = "現在満員のため、待機として受付しました。空きが出た場合はメールでご連絡します。"
        status_label = "待機受付"

    try:
        cancel_url = url_for("cancel_application",
                             token=cancel_token, _external=True)

        event_time = event["start_time"] if "start_time" in event.keys(
        ) and event["start_time"] else "10:00"
        event_location = event["location"] if "location" in event.keys(
        ) and event["location"] else "未定"
        event_belongings = event["belongings"] if "belongings" in event.keys(
        ) and event["belongings"] else "特にありません"
        event_notes = event["additional_notes"] if "additional_notes" in event.keys(
        ) and event["additional_notes"] else "特にありません"

        send_application_mail(
            data.get("email"),
            "【くれよんママ】お申込みありがとうございます",
            f"""
        {data.get("parent_name")} 様

        このたびはお申込みいただきありがとうございます。
        {status_message}

        【イベント名】
        {event['title']}

        【開催日時】
        {event['event_date']} {event_time}〜

        【開催場所】
        {event_location}

        【参加人数】
        大人 {data.get("adult_count")} 名
        子ども {data.get("child_count")} 名

        【持ち物】
        {event_belongings}

        【その他のご案内】
        {event_notes}

        【キャンセルはこちら】
        {cancel_url}

        くれよんママ
        """,
        )
        send_admin_mail(
            "【くれよんママ】新しいお申込みがありました",
            f"""
    新しいお申込みがありました。

    【イベント名】
    {event['title']}
    【申込状態】
    {status_label}
    【保護者名】
    {data.get("parent_name")}
    【メール】
    {data.get("email")}
    """,
        )

    except Exception as e:
        print("メール送信エラー:", e)

    conn.close()

    return render_template("apply_complete.html", event=event, status=application_status)


# 申し込みキャンセル


@app.route("/cancel/<token>", methods=["GET", "POST"])
def cancel_application(token):
    conn = get_db()

    application = conn.execute(
        """
        SELECT applications.*, events.title AS event_title, events.event_date
        FROM applications
        LEFT JOIN events ON applications.event_id = events.id
        WHERE applications.cancel_token = ?
    """,
        (token,),
    ).fetchone()

    if not application:
        conn.close()
        return "キャンセルURLが無効です。"

    if application["status"] == "cancelled":
        conn.close()
        return "この申込はすでにキャンセル済みです。"

    if request.method == "POST":
        old_status = application["status"]

        conn.execute(
            """
            UPDATE applications
            SET status = 'cancelled',
                cancelled_at = datetime('now', 'localtime')
            WHERE cancel_token = ?
        """,
            (token,),
        )

        promoted_user = None

        # 確定申込がキャンセルされた時だけ、待機者を繰り上げ
        if old_status == "confirmed":
            promoted_user = conn.execute(
                """
                SELECT *
                FROM applications
                WHERE event_id = ?
                  AND status = 'waiting'
                ORDER BY created_at ASC
                LIMIT 1
            """,
                (application["event_id"],),
            ).fetchone()

            if promoted_user:
                conn.execute(
                    """
                    UPDATE applications
                    SET status = 'confirmed'
                    WHERE id = ?
                """,
                    (promoted_user["id"],),
                )

        conn.commit()
        conn.close()

        # メール送信はDB更新後に行う
        try:
            send_admin_mail(
                "【くれよんママ】申込キャンセルがありました",
                f"""
申込キャンセルがありました。

【イベント名】
{application['event_title']}

【開催日】
{application['event_date']}

【キャンセルした方】
{application['parent_name']}

【元の申込状態】
{'通常申込' if old_status == 'confirmed' else '待機申込'}
""",
            )

            if promoted_user:
                send_application_mail(
                    promoted_user["email"],
                    "【くれよんママ】キャンセル待ち繰り上げのご案内",
                    f"""
{promoted_user['parent_name']} 様

キャンセルが出たため、待機申込から通常申込へ繰り上がりました。

【イベント名】
{application['event_title']}

【開催日】
{application['event_date']}

当日お会いできることを楽しみにしています。

くれよんママ
""",
                )

                send_admin_mail(
                    "【くれよんママ】待機申込を自動繰り上げしました",
                    f"""
待機申込を自動で通常申込に変更しました。

【イベント名】
{application['event_title']}

【繰り上げ対象】
{promoted_user['parent_name']}

【メール】
{promoted_user['email']}
""",
                )

        except Exception as e:
            print("キャンセル・繰り上げメール送信エラー:", e)

        return render_template("cancel_complete.html")

    conn.close()

    return render_template("cancel_confirm.html", application=application)


# 活動記録一覧ルート


@app.route("/archive")
def archive():
    conn = get_db()

    selected_year = request.args.get("year", "").strip()

    archive_events = conn.execute("""
        SELECT *
        FROM events
        WHERE status = '公開'
          AND event_date < date('now')
        ORDER BY event_date DESC, id DESC
    """).fetchall()

    archive_list = []
    year_set = set()

    for event in archive_events:
        event_date = event["event_date"]
        event_year = event_date[:4] if event_date else ""

        if event_year:
            year_set.add(event_year)

        if selected_year and event_year != selected_year:
            continue

        first_image = conn.execute(
            """
            SELECT image_path
            FROM event_images
            WHERE event_id = ?
            ORDER BY id ASC
            LIMIT 1
        """,
            (event["id"],),
        ).fetchone()

        thumbnail = None
        if first_image:
            thumbnail = first_image["image_path"]
        elif "image_url" in event.keys() and event["image_url"]:
            thumbnail = event["image_url"]

        archive_list.append(
            {
                "id": event["id"],
                "title": event["title"],
                "category": event["category"] if "category" in event.keys() else None,
                "event_date": event["event_date"],
                "thumbnail": thumbnail,
            }
        )

    conn.close()

    year_list = sorted(list(year_set), reverse=True)

    return render_template(
        "archive.html",
        archive_events=archive_list,
        year_list=year_list,
        selected_year=selected_year,
    )


# 活動記録詳細ルート


@app.route("/archive/<int:event_id>")
def archive_detail(event_id):
    conn = get_db()

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ?
          AND status = '公開'
    """,
        (event_id,),
    ).fetchone()

    if not event:
        conn.close()
        return "活動記録が見つかりません", 404

    event_images = conn.execute(
        """
        SELECT *
        FROM event_images
        WHERE event_id = ?
        ORDER BY id ASC
    """,
        (event_id,),
    ).fetchall()

    # 安全に値を読む
    event_keys = event.keys()

    image_url = event["image_url"] if "image_url" in event_keys else None
    video_path = event["video_path"] if "video_path" in event_keys else None

    main_image = None
    if event_images:
        main_image = event_images[0]["image_path"]
    elif image_url:
        main_image = image_url

    participant_count = 8

    conn.close()

    return render_template(
        "archive_detail.html",
        event=event,
        event_images=event_images,
        main_image=main_image,
        video_path=video_path,
        participant_count=participant_count,
    )


# お問い合わせルート


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        contact_type = request.form.get("contact_type", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        reply_needed = 1 if request.form.get("reply_needed") else 0

        if not contact_type:
            flash("問い合わせ種別を選択してください", "error")
            return render_template("contact.html")

        if not message:
            flash("内容を入力してください", "error")
            return render_template("contact.html")

        conn = get_db()

        data = request.form

        conn.execute(
            """
            INSERT INTO contacts (
                contact_type,
                name,
                email,
                message,
                reply_needed
            )
            VALUES (?, ?, ?, ?, ?)
        """,
            (contact_type, name, email, message, reply_needed),
        )
        conn.commit()

        send_admin_mail(
            "【くれよんママ】新しいお問い合わせがありました",
            f"""
        新しいお問い合わせが届きました。

        【お名前】
        {data.get("name")}

        【メール】
        {data.get("email")}

        【種別】
        {data.get("contact_type")}

        【内容】
        {data.get("message")}

        管理画面よりご確認ください。
        """,
        )
        conn.close()

        return redirect(url_for("contact_complete"))

    return render_template("contact.html")


@app.route("/contact/complete")
def contact_complete():
    return render_template("contact_complete.html")


# 管理者ダッシュボードルート


@app.route("/admin")
@login_required
def admin_dashboard():
    conn = get_db()

    # 今後イベント数
    upcoming_events = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM events
        WHERE date(event_date) >= date('now')
    """).fetchone()["cnt"]

    # 今後イベントの確定申込数
    confirmed_applications = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM applications
        JOIN events ON applications.event_id = events.id
        WHERE date(events.event_date) >= date('now')
          AND applications.status = 'confirmed'
    """).fetchone()["cnt"]

    # 今後イベントの待機申込数
    waiting_applications = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM applications
        JOIN events ON applications.event_id = events.id
        WHERE date(events.event_date) >= date('now')
          AND applications.status = 'waiting'
    """).fetchone()["cnt"]

    # 未読お問い合わせ
    unread_contacts = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM contacts
        WHERE is_read = 0
    """).fetchone()["cnt"]

    # 管理者人数
    admin_users = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM users
        WHERE role = 'admin'
    """).fetchone()["cnt"]

    # 最近の申込（今後イベントのみ・5件）
    recent_applications = conn.execute("""
        SELECT 
            parent_name AS name,
            applications.created_at AS applied_at,
            applications.status,
            events.title AS event_name
        FROM applications
        LEFT JOIN events ON applications.event_id = events.id
        WHERE date(events.event_date) >= date('now')
          AND applications.status IN ('confirmed', 'waiting')
        ORDER BY applications.created_at DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    stats = {
        "upcoming_events": upcoming_events,
        "confirmed_applications": confirmed_applications,
        "waiting_applications": waiting_applications,
        "unread_contacts": unread_contacts,
        "admin_users": admin_users,
    }

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        recent_applications=recent_applications
    )

# 管理者用バックアップダウンロードルート


@app.route("/admin/backup")
@login_required
def admin_backup():
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"crayonmama_backup_{now}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    shutil.copy(DB_NAME, backup_path)

    return send_file(
        backup_path,
        as_attachment=True,
        download_name=backup_filename
    )


@app.route("/admin/members-page/main-image/delete", methods=["POST"])
@login_required
def admin_members_main_image_delete():
    conn = get_db()

    conn.execute("""
        UPDATE site_pages
        SET main_image = NULL
        WHERE page_key = 'members'
    """)

    conn.commit()
    conn.close()

    return redirect(url_for("admin_members_page"))


@app.route("/admin/logout")
def admin_logout():

    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_role", None)

    return redirect(url_for("admin_login"))


@app.route("/members")
def members():
    conn = get_db()

    page = conn.execute("""
        SELECT *
        FROM site_pages
        WHERE page_key = 'members'
    """).fetchone()

    public_members = conn.execute("""
        SELECT *
        FROM public_members
        ORDER BY display_order ASC, id ASC
    """).fetchall()

    gallery_images = conn.execute("""
        SELECT *
        FROM member_gallery_images
        ORDER BY display_order ASC, id ASC
    """).fetchall()

    conn.close()

    return render_template(
        "members.html",
        page=page,
        public_members=public_members,
        gallery_images=gallery_images,
    )


# 管理者用活動・メンバー紹介ページ編集ルート


@app.route("/admin/members-page", methods=["GET", "POST"])
@login_required
def admin_members_page():
    conn = get_db()

    if request.method == "POST":
        title = request.form.get("title")
        body = request.form.get("body")

        page = conn.execute("""
            SELECT * FROM site_pages
            WHERE page_key = 'members'
        """).fetchone()

        main_image = page["main_image"] if "main_image" in page.keys(
        ) else None

        file = request.files.get("main_image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            main_image = url_for("static", filename=f"uploads/{filename}")

        gallery_order = request.form.get("gallery_order", "")

        if gallery_order:
            image_ids = gallery_order.split(",")

            for index, image_id in enumerate(image_ids):
                conn.execute("""
                    UPDATE member_gallery_images
                    SET display_order = ?
                    WHERE id = ?
                """, (index, image_id))
        conn.execute(
            """
            UPDATE site_pages
            SET title = ?, body = ?, main_image = ?
            WHERE page_key = 'members'
        """,
            (title, body, main_image),
        )

        conn.commit()

        return redirect(url_for("admin_members_page"))

    page = conn.execute("""
        SELECT *
        FROM site_pages
        WHERE page_key = 'members'
    """).fetchone()

    members = conn.execute("""
        SELECT *
        FROM public_members
        ORDER BY display_order ASC, id ASC
    """).fetchall()

    gallery_images = conn.execute("""
        SELECT *
        FROM member_gallery_images
        ORDER BY display_order ASC, id ASC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_members_page.html",
        page=page,
        members=members,
        gallery_images=gallery_images,
    )


# 管理者用活動・メンバー紹介ページ ギャラリー画像追加ルート


@app.route("/admin/members-page/gallery/add", methods=["POST"])
@login_required
def admin_member_gallery_add():
    file = request.files.get("gallery_image")
    display_order = request.form.get("display_order") or 0

    if file and file.filename:
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        image_path = url_for("static", filename=f"uploads/{filename}")

        conn = get_db()
        conn.execute(
            """
            INSERT INTO member_gallery_images (image_path, display_order)
            VALUES (?, ?)
        """,
            (image_path, display_order),
        )
        conn.commit()
        conn.close()

    return redirect(url_for("admin_members_page"))


# 管理者用活動・メンバー紹介ページ ギャラリー画像削除ルート


@app.route("/admin/members-page/gallery/<int:image_id>/delete", methods=["POST"])
@login_required
def admin_member_gallery_delete(image_id):
    conn = get_db()

    conn.execute(
        """
        DELETE FROM member_gallery_images
        WHERE id = ?
    """,
        (image_id,),
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_members_page"))


# 管理者用活動・メンバー紹介ページ メンバー管理ルート


@app.route("/admin/public-members")
@login_required
def admin_public_members():
    conn = get_db()

    members = conn.execute("""
        SELECT *
        FROM public_members
        ORDER BY display_order ASC, id ASC
    """).fetchall()

    conn.close()

    return render_template("admin_public_members.html", members=members)


@app.route("/admin/public-members/new", methods=["GET", "POST"])
@login_required
def admin_public_member_new():
    if request.method == "POST":
        image_path = None

        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            image_path = url_for("static", filename=f"uploads/{filename}")

        conn = get_db()

        conn.execute(
            """
            INSERT INTO public_members (name, role, comment, icon, image_path, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                request.form.get("name"),
                request.form.get("role"),
                request.form.get("comment"),
                request.form.get("icon"),
                image_path,
                request.form.get("display_order") or 0,
            ),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_members_page"))

    return render_template("admin_public_member_form.html", member=None)


# 管理者用活動・メンバー紹介ページ メンバー編集ルート


@app.route("/admin/public-members/<int:member_id>/edit", methods=["GET", "POST"])
@login_required
def admin_public_member_edit(member_id):
    conn = get_db()

    member = conn.execute(
        """
        SELECT *
        FROM public_members
        WHERE id = ?
    """,
        (member_id,),
    ).fetchone()

    if request.method == "POST":
        image_path = member["image_path"] if "image_path" in member.keys(
        ) else None

        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            image_path = url_for("static", filename=f"uploads/{filename}")

        conn.execute(
            """
            UPDATE public_members
            SET name = ?,
                role = ?,
                comment = ?,
                icon = ?,
                image_path = ?,
                display_order = ?
            WHERE id = ?
        """,
            (
                request.form.get("name"),
                request.form.get("role"),
                request.form.get("comment"),
                request.form.get("icon"),
                image_path,
                request.form.get("display_order") or 0,
                member_id,
            ),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_members_page"))

    conn.close()

    return render_template("admin_public_member_form.html", member=member)


# 管理者用活動・メンバー紹介ページ メンバー削除ルート


@app.route("/admin/public-members/<int:member_id>/delete", methods=["POST"])
@login_required
def admin_public_member_delete(member_id):
    conn = get_db()

    conn.execute(
        """
        DELETE FROM public_members
        WHERE id = ?
    """,
        (member_id,),
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_public_members"))


@app.route("/admin/public-members/<int:member_id>/image/delete", methods=["POST"])
@login_required
def admin_public_member_image_delete(member_id):
    conn = get_db()

    conn.execute("""
        UPDATE public_members
        SET image_path = NULL
        WHERE id = ?
    """, (member_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_public_member_edit", member_id=member_id))


# 申込管理ルート


@app.route("/admin/applications")
def admin_applications():
    selected_event_id = request.args.get("event_id", "")
    selected_status = request.args.get("status", "all")
    view_mode = request.args.get("view", "upcoming")

    conn = get_db()

    if view_mode == "past":
        events = conn.execute("""
            SELECT id, title
            FROM events
            WHERE date(event_date) < date('now')
            ORDER BY event_date DESC
        """).fetchall()
        date_condition = "date(events.event_date) < date('now')"
    else:
        events = conn.execute("""
            SELECT id, title
            FROM events
            WHERE date(event_date) >= date('now')
            ORDER BY event_date ASC
        """).fetchall()
        date_condition = "date(events.event_date) >= date('now')"

    where_clauses = [date_condition]
    params = []

    if selected_event_id:
        where_clauses.append("applications.event_id = ?")
        params.append(selected_event_id)

    if selected_status != "all":
        where_clauses.append("applications.status = ?")
        params.append(selected_status)

    where_sql = "WHERE " + " AND ".join(where_clauses)

    applications = conn.execute(
        f"""
        SELECT
            applications.*,
            events.title,
            events.event_date
        FROM applications
        JOIN events ON applications.event_id = events.id
        {where_sql}
        ORDER BY
            events.event_date ASC,
            events.id ASC,
            applications.time_slot ASC,
            CASE applications.status
                WHEN 'confirmed' THEN 1
                WHEN 'waiting' THEN 2
                WHEN 'cancelled' THEN 3
                ELSE 4
            END,
            applications.created_at DESC
        """,
        params,
    ).fetchall()

    grouped_applications = []

    for app in applications:
        group = None

        for g in grouped_applications:
            if g["event_id"] == app["event_id"]:
                group = g
                break

        if group is None:
            group = {
                "event_id": app["event_id"],
                "event_title": app["title"],
                "event_date": app["event_date"],
                "count": 0,
                "confirmed_count": 0,
                "waiting_count": 0,
                "cancelled_count": 0,
                "time1_count": 0,
                "time2_count": 0,
                "items": [],
                "items_time1": [],
                "items_time2": [],
            }
            grouped_applications.append(group)

        group["items"].append(app)

        if app["time_slot"] == "2":
            group["items_time2"].append(app)
        else:
            group["items_time1"].append(app)

        group["count"] += 1

        if app["status"] == "confirmed":
            group["confirmed_count"] += 1
        elif app["status"] == "waiting":
            group["waiting_count"] += 1
        elif app["status"] == "cancelled":
            group["cancelled_count"] += 1
        if app["time_slot"] == "2":
            group["time2_count"] += 1
        else:
            group["time1_count"] += 1

    summary_query = f"""
        SELECT
            SUM(CASE WHEN applications.status = 'confirmed' THEN 1 ELSE 0 END) AS confirmed,
            SUM(CASE WHEN applications.status = 'waiting' THEN 1 ELSE 0 END) AS waiting,
            SUM(CASE WHEN applications.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled
        FROM applications
        JOIN events ON applications.event_id = events.id
        WHERE {date_condition}
    """

    summary_params = []

    if selected_event_id:
        summary_query += " AND applications.event_id = ?"
        summary_params.append(selected_event_id)

    if selected_status != "all":
        summary_query += " AND applications.status = ?"
        summary_params.append(selected_status)

    summary_row = conn.execute(summary_query, summary_params).fetchone()

    conn.close()

    summary = {
        "confirmed": summary_row["confirmed"] or 0,
        "waiting": summary_row["waiting"] or 0,
        "cancelled": summary_row["cancelled"] or 0,
    }

    return render_template(
        "admin_applications.html",
        applications=applications,
        grouped_applications=grouped_applications,
        events=events,
        summary=summary,
        selected_event_id=selected_event_id,
        selected_status=selected_status,
        view_mode=view_mode,
    )


# 管理者用申込CSVダウンロードルート

@app.route("/admin/applications/<int:event_id>/csv")
@login_required
def admin_applications_csv(event_id):
    conn = get_db()

    event = conn.execute("""
        SELECT *
        FROM events
        WHERE id = ?
    """, (event_id,)).fetchone()

    if not event:
        conn.close()
        flash("イベントが見つかりませんでした", "error")
        return redirect(url_for("admin_applications"))

    applications = conn.execute("""
        SELECT *
        FROM applications
        WHERE event_id = ?
          AND status IN ('confirmed')
        ORDER BY
          CASE status
            WHEN 'confirmed' THEN 1
            WHEN 'waiting' THEN 2
            ELSE 3
          END,
          created_at ASC
    """, (event_id,)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "受付",
        "保護者名",
        "大人",
        "子ども",
        "子ども情報"
    ])

    for app_data in applications:
        children = []

        for i in range(1, 6):
            name = app_data[f"child{i}_name"]
            age = app_data[f"child{i}_age"]

            if name:
                children.append(f"子{i}: {name}（{age or '年齢未設定'}）")

        status_label = "確定" if app_data["status"] == "confirmed" else "待機"

        writer.writerow([
            "□",
            app_data["parent_name"],
            f"{app_data['adult_count']}名",
            f"{app_data['child_count']}名",
            " / ".join(children)
        ])

    conn.close()

    csv_text = output.getvalue()
    output.close()

    filename = f"applications_{event_id}.csv"

    return Response(
        "\ufeff" + csv_text,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

# 申込キャンセルルート


@app.route("/admin/applications/<int:application_id>/cancel", methods=["POST"])
def admin_application_cancel(application_id):
    conn = get_db()
    conn.execute(
        """
        UPDATE applications
        SET status = 'cancelled'
        WHERE id = ?
    """,
        (application_id,),
    )
    conn.commit()
    conn.close()

    flash("申込をキャンセルに更新しました", "success")
    return redirect(request.referrer or url_for("admin_applications"))


@app.route("/admin/event-images")
def admin_event_images():
    conn = get_db()

    selected_year = request.args.get("year", "").strip()
    selected_event_id = request.args.get("event_id", "").strip()

    year_rows = conn.execute("""
        SELECT DISTINCT strftime('%Y', event_date) AS year
        FROM events
        WHERE event_date IS NOT NULL
          AND date(event_date) < date('now')
        ORDER BY year DESC
    """).fetchall()

    year_list = [row["year"] for row in year_rows if row["year"]]

    query = """
        SELECT id, title, event_date, category
        FROM events
        WHERE date(event_date) < date('now')
    """
    params = []

    if selected_year:
        query += " AND strftime('%Y', event_date) = ?"
        params.append(selected_year)

    query += " ORDER BY event_date DESC, id DESC"

    events = conn.execute(query, params).fetchall()

    selected_event = None
    images = []

    if selected_event_id:
        selected_event = conn.execute(
            """
            SELECT *
            FROM events
            WHERE id = ?
              AND date(event_date) < date('now')
            """,
            (selected_event_id,),
        ).fetchone()

    elif events:
        selected_event_id = str(events[0]["id"])

        selected_event = conn.execute(
            """
            SELECT *
            FROM events
            WHERE id = ?
            """,
            (selected_event_id,),
        ).fetchone()

    if selected_event:
        images = conn.execute(
            """
            SELECT *
            FROM event_images
            WHERE event_id = ?
            ORDER BY id DESC
            """,
            (selected_event["id"],),
        ).fetchall()

    conn.close()

    return render_template(
        "admin_event_images.html",
        events=events,
        year_list=year_list,
        selected_year=selected_year,
        selected_event_id=selected_event_id,
        selected_event=selected_event,
        images=images,
    )

# お問い合わせ管理ルート


@app.route("/admin/contact")
def admin_contacts():
    conn = get_db()

    contacts = conn.execute("""
        SELECT *
        FROM contacts
        ORDER BY created_at DESC
    """).fetchall()

    grouped_contacts = []

    for contact in contacts:
        month_key = contact["created_at"][:7] if contact["created_at"] else "日付未設定"

        group = None

        for g in grouped_contacts:
            if g["month_key"] == month_key:
                group = g
                break

        if group is None:
            group = {
                "month_key": month_key,
                "count": 0,
                "unread_count": 0,
                "reply_needed_count": 0,
                "contacts": []
            }
            grouped_contacts.append(group)

        group["contacts"].append(contact)
        group["count"] += 1

        if contact["is_read"] == 0:
            group["unread_count"] += 1

        if contact["reply_needed"] == 1:
            group["reply_needed_count"] += 1

    summary_row = conn.execute("""
        SELECT
            COUNT(*) AS total_count,
            SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) AS unread_count,
            SUM(CASE WHEN reply_needed = 1 THEN 1 ELSE 0 END) AS reply_needed_count
        FROM contacts
    """).fetchone()

    conn.close()

    summary = {
        "total_count": summary_row["total_count"] or 0,
        "unread_count": summary_row["unread_count"] or 0,
        "reply_needed_count": summary_row["reply_needed_count"] or 0,
    }

    return render_template(
        "admin_contacts.html",
        contacts=contacts,
        grouped_contacts=grouped_contacts,
        summary=summary
    )


# イベント管理ルート


@app.route("/admin/events")
def admin_events():
    selected_year = request.args.get("year", "")
    selected_month = request.args.get("month", "")

    conn = get_db()
    today = date.today().isoformat()

    query = """
        SELECT *
        FROM events
        WHERE 1 = 1
    """
    params = []

    if selected_year:
        query += " AND strftime('%Y', event_date) = ?"
        params.append(selected_year)

    if selected_month:
        query += " AND strftime('%m', event_date) = ?"
        params.append(selected_month.zfill(2))

    query += " ORDER BY event_date DESC, id DESC"

    events = conn.execute(query, params).fetchall()

    year_rows = conn.execute("""
        SELECT DISTINCT strftime('%Y', event_date) AS year
        FROM events
        WHERE event_date IS NOT NULL
        ORDER BY year DESC
    """).fetchall()

    year_list = [row["year"] for row in year_rows if row["year"]]

    event_list = []

    for event in events:
        application_count = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM applications
            WHERE event_id = ?
            AND status = 'confirmed'
        """,
            (event["id"],),
        ).fetchone()["cnt"]

        capacity1 = event["capacity_time1"] or 0
        capacity2 = event["capacity_time2"] or 0

        capacity = capacity1 + capacity2

        if capacity <= 0:
            capacity = 10

        confirmed_count = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM applications
            WHERE event_id = ?
            AND status = 'confirmed'
        """, (event["id"],)).fetchone()["cnt"]

        waiting_count = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM applications
            WHERE event_id = ?
            AND status = 'waiting'
        """, (event["id"],)).fetchone()["cnt"]

        remaining_count = max(0, capacity - confirmed_count)

        event_list.append(
            {
                "id": event["id"],
                "title": event["title"],
                "category": event["category"],
                "event_date": event["event_date"],
                "status": event["status"],
                "capacity": event["capacity"],
                "application_count": application_count,
                "flyer_image": (
                    event["flyer_image"] if "flyer_image" in event.keys() else None),
                "remaining_count": remaining_count,
                "waiting_count": waiting_count,
                "is_finished": event["event_date"] < today,
            }
        )

    conn.close()

    return render_template(
        "admin_events.html",
        events=event_list,
        year_list=year_list,
        selected_year=selected_year,
        selected_month=selected_month,
    )


# イベント複製ルート


@app.route("/admin/events/<int:event_id>/duplicate", methods=["POST"])
def admin_event_duplicate(event_id):
    conn = get_db()

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ?
    """,
        (event_id,),
    ).fetchone()

    if not event:
        conn.close()
        return redirect(url_for("admin_events"))

    cursor = conn.execute(
        """
        INSERT INTO events (
            category,
            title,
            flyer_image,
            event_date,
            status,
            capacity,
            description,
            belongings,
            additional_notes,
            time1_start,
            time1_end,
            time2_start,
            time2_end,
            capacity_time1,
            capacity_time2
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            event["category"],
            event["title"] + "（コピー）",
            event["flyer_image"] if "flyer_image" in event.keys() else None,
            date.today().isoformat(),
            "下書き",
            event["capacity"],
            event["description"],
            event["belongings"] if "belongings" in event.keys() else None,
            event["additional_notes"] if "additional_notes" in event.keys() else None,
        ),
    )

    new_event_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return redirect(url_for("admin_event_edit", event_id=new_event_id))


# イベント新規作成ルート


@app.route("/admin/events/new", methods=["GET", "POST"])
@login_required
def admin_event_new():
    if request.method == "POST":
        category = request.form.get("category")
        title = request.form.get("title")
        event_date = request.form.get("date")
        status = request.form.get("status")
        capacity = request.form.get("capacity")
        description = request.form.get("description")
        location = request.form.get("location")
        time1_start = request.form.get("time1_start")
        time1_end = request.form.get("time1_end")

        time2_start = request.form.get("time2_start")
        time2_end = request.form.get("time2_end")

        capacity_time1 = request.form.get("capacity_time1")
        capacity_time2 = request.form.get("capacity_time2")

        flyer_image = None

        file = request.files.get("flyer_image")
        if file and file.filename != "" and allowed_file(file.filename):
            original_name = secure_filename(file.filename)
            ext = os.path.splitext(original_name)[1].lower()
            unique_name = f"{uuid.uuid4().hex}{ext}"

            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)

            flyer_image = f"/static/uploads/{unique_name}"

        conn = get_db()

        conn.execute(
            """
                INSERT INTO events (
                    category, title, flyer_image, event_date,
                    status, capacity, description, location, time1_start, time1_end, time2_start, time2_end, capacity_time1, capacity_time2
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                category,
                title,
                flyer_image,
                event_date,
                time1_start,
                time1_end,

                time2_start,
                time2_end,

                capacity_time1,
                capacity_time2,
                status,
                capacity,
                description,
                location,

            ),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_events"))

    return render_template("admin_event_new.html")


# イベント下書き


@app.route("/admin/events/<int:event_id>/toggle-status", methods=["POST"])
def admin_event_toggle_status(event_id):
    conn = get_db()

    event = conn.execute(
        """
        SELECT status FROM events WHERE id = ?
    """,
        (event_id,),
    ).fetchone()

    if event:
        new_status = "下書き" if event["status"] == "公開" else "公開"

        conn.execute(
            """
            UPDATE events
            SET status = ?
            WHERE id = ?
        """,
            (new_status, event_id),
        )

        conn.commit()

    conn.close()

    return redirect(url_for("admin_events"))


# イベント編集ルート


@app.route("/admin/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def admin_event_edit(event_id):
    conn = get_db()

    event = conn.execute(
        "SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    if not event:
        conn.close()
        return redirect(url_for("admin_events"))

    if request.method == "POST":
        flyer_image = event["flyer_image"] if "flyer_image" in event.keys(
        ) else None

        file = request.files.get("flyer_image")
        if file and file.filename != "" and allowed_file(file.filename):
            original_name = secure_filename(file.filename)
            ext = os.path.splitext(original_name)[1].lower()
            unique_name = f"{uuid.uuid4().hex}{ext}"

            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)

            flyer_image = f"/static/uploads/{unique_name}"

        conn.execute(
            """
            UPDATE events
            SET category = ?,
                title = ?,
                flyer_image = ?,
                event_date = ?,
                time1_start = ?,
                time1_end = ?,
                time2_start = ?,
                time2_end = ?,
                capacity_time1 = ?,
                capacity_time2 = ?,
                status = ?,
                capacity = ?,
                description = ?,
                location = ?
            WHERE id = ?
        """,
            (
                request.form.get("category"),
                request.form.get("title"),
                flyer_image,
                request.form.get("date"),
                request.form.get("time1_start"),
                request.form.get("time1_end"),
                request.form.get("time2_start"),
                request.form.get("time2_end"),
                request.form.get("capacity_time1"),
                request.form.get("capacity_time2"),
                request.form.get("status"),
                request.form.get("capacity"),
                request.form.get("description"),
                request.form.get("location"),
                event_id,

            ),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("admin_events"))

    conn.close()

    return render_template(
        "admin_event_edit.html", event=event, today=date.today().isoformat()
    )

# 前日リマインドメール送信ルート


@app.route("/admin/events/<int:event_id>/send-reminder", methods=["POST"])
@login_required
def send_event_reminder(event_id):

    conn = get_db()

    event = conn.execute("""
        SELECT *
        FROM events
        WHERE id = ?
    """, (event_id,)).fetchone()

    if not event:
        conn.close()
        return redirect(url_for("admin_events"))

    applications = conn.execute("""
        SELECT *
        FROM applications
        WHERE event_id = ?
        AND status = 'confirmed'
    """, (event_id,)).fetchall()

    event_time = event["start_time"] or "10:00"
    event_location = event["location"] or "未定"
    event_belongings = event["belongings"] or "特にありません"
    event_notes = event["additional_notes"] or "特にありません"

    for app_data in applications:

        cancel_url = url_for(
            "cancel_application",
            token=app_data["cancel_token"],
            _external=True
        )

        try:
            send_application_mail(
                app_data["email"],
                f"【くれよんママ】明日の開催について",
                f"""
{app_data["parent_name"]} 様

明日はイベント開催日です。
ご確認をお願いいたします。

【イベント名】
{event["title"]}

【開催日時】
{event["event_date"]} {event_time}〜

【開催場所】
{event_location}

【持ち物】
{event_belongings}

【ご案内】
{event_notes}

【キャンセルはこちら】
{cancel_url}

明日お会いできることを楽しみにしています。

くれよんママ
"""
            )

        except Exception as e:
            print("リマインドメール送信エラー:", e)

    conn.close()

    flash("前日リマインドメールを送信しました")

    return redirect(url_for("admin_event_edit", event_id=event_id))


# イベント参加者への一斉メール送信ルート

@app.route("/admin/events/<int:event_id>/message", methods=["GET", "POST"])
@login_required
def admin_event_message(event_id):

    conn = get_db()

    event = conn.execute("""
        SELECT *
        FROM events
        WHERE id = ?
    """, (event_id,)).fetchone()

    if not event:
        conn.close()
        return redirect(url_for("admin_applications"))

    if request.method == "POST":

        subject = request.form.get("subject")
        message = request.form.get("message")
        target = request.form.get("target", "confirmed")

        query = """
            SELECT *
            FROM applications
            WHERE event_id = ?
        """

        params = [event_id]

        if target != "all":
            query += " AND status = ?"
            params.append(target)

        applications = conn.execute(query, params).fetchall()

        sent_count = 0

        for app_data in applications:

            if not app_data["email"]:
                continue

            try:

                send_application_mail(
                    app_data["email"],
                    subject,
                    f"""
{app_data["parent_name"]} 様

{message}

【イベント名】
{event["title"]}

くれよんママ
"""
                )

                sent_count += 1

            except Exception as e:
                print("一斉送信エラー:", e)
        conn.execute("""
            INSERT INTO mail_logs (
                event_id,
                subject,
                message,
                target,
                sent_count
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            subject,
            message,
            target,
            sent_count
        ))

        conn.commit()
        flash(f"{sent_count}件のメールを送信しました")

        conn.close()

        return redirect(url_for("admin_applications"))

    conn.close()

    return render_template(
        "admin_event_message.html",
        event=event
    )

# メール送信ログルート


@app.route("/admin/mail-logs")
@login_required
def admin_mail_logs():
    conn = get_db()

    logs = conn.execute("""
        SELECT
            mail_logs.*,
            events.title AS event_title
        FROM mail_logs
        LEFT JOIN events ON mail_logs.event_id = events.id
        ORDER BY mail_logs.created_at DESC
    """).fetchall()

    grouped_logs = []

    for log in logs:
        group = None

        for g in grouped_logs:
            if g["event_id"] == log["event_id"]:
                group = g
                break

        if group is None:
            group = {
                "event_id": log["event_id"],
                "event_title": log["event_title"] or "イベント未設定",
                "count": 0,
                "logs": []
            }
            grouped_logs.append(group)

        group["logs"].append(log)
        group["count"] += 1

    conn.close()

    return render_template(
        "admin_mail_logs.html",
        grouped_logs=grouped_logs
    )


# イベントのチラシ削除


@app.route("/admin/events/<int:event_id>/delete-flyer", methods=["POST"])
def admin_event_delete_flyer(event_id):
    conn = get_db()

    conn.execute(
        """
        UPDATE events
        SET flyer_image = NULL
        WHERE id = ?
    """,
        (event_id,),
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_event_edit", event_id=event_id))


# イベント削除ルート

@app.route("/admin/events/<int:event_id>/delete", methods=["POST"])
@login_required
def admin_event_delete(event_id):
    conn = get_db()

    event = conn.execute("""
        SELECT *
        FROM events
        WHERE id = ?
    """, (event_id,)).fetchone()

    if not event:
        conn.close()
        flash("イベントが見つかりませんでした", "error")
        return redirect(url_for("admin_events"))

    application_count = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM applications
        WHERE event_id = ?
    """, (event_id,)).fetchone()["cnt"]

    image_count = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM event_images
        WHERE event_id = ?
    """, (event_id,)).fetchone()["cnt"]

    mail_log_count = conn.execute("""
        SELECT COUNT(*) AS cnt
        FROM mail_logs
        WHERE event_id = ?
    """, (event_id,)).fetchone()["cnt"]

    if application_count > 0 or image_count > 0 or mail_log_count > 0:
        conn.close()
        flash("申込・画像・送信履歴があるイベントは削除できません。必要な場合は「下書き」に変更してください。", "error")
        return redirect(url_for("admin_events"))

    conn.execute("""
        DELETE FROM events
        WHERE id = ?
    """, (event_id,))

    conn.commit()
    conn.close()

    flash("イベントを削除しました", "success")
    return redirect(url_for("admin_events"))


# イベント画像アップロードルート


@app.route("/admin/event-images/upload", methods=["POST"])
def upload_event_images():
    event_id = request.form.get("event_id")

    if not event_id:
        return redirect(url_for("admin_event_images"))

    if "images" not in request.files:
        return redirect(url_for("admin_event_images", event_id=event_id))

    files = request.files.getlist("images")

    event_folder = os.path.join(UPLOAD_FOLDER, f"event_{event_id}")
    os.makedirs(event_folder, exist_ok=True)

    conn = get_db()

    current_count_row = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM event_images
        WHERE event_id = ?
    """,
        (event_id,),
    ).fetchone()

    current_count = current_count_row["cnt"] if current_count_row else 0
    max_images = 30
    remaining_slots = max_images - current_count

    if remaining_slots <= 0:
        conn.close()
        flash("このイベントにはすでに30枚登録されています", "error")
        return redirect(url_for("admin_event_images", event_id=event_id))

    saved_count = 0

    for file in files:
        if saved_count >= remaining_slots:
            break

        if file and allowed_file(file.filename):
            original_name = secure_filename(file.filename)
            ext = os.path.splitext(original_name)[1].lower()
            unique_name = f"{uuid.uuid4().hex}{ext}"

            save_path = os.path.join(event_folder, unique_name)
            file.save(save_path)

            db_path = f"/static/uploads/event_{event_id}/{unique_name}"

            conn.execute(
                """
                INSERT INTO event_images (event_id, image_path)
                VALUES (?, ?)
            """,
                (event_id, db_path),
            )

            saved_count += 1

    conn.commit()
    conn.close()

    if saved_count < len(files):
        flash(f"{saved_count}枚だけ保存しました。1イベント30枚までです。", "info")
    else:
        flash(f"{saved_count}枚保存しました。", "success")

    return redirect(url_for("admin_event_images", event_id=event_id))


# イベント画像削除ルート


@app.route("/admin/event-images/delete/<int:image_id>", methods=["POST"])
def delete_event_image(image_id):
    conn = get_db()

    image = conn.execute(
        """
        SELECT *
        FROM event_images
        WHERE id = ?
    """,
        (image_id,),
    ).fetchone()

    event_id = None

    if image:
        event_id = image["event_id"]

        try:
            file_path = image["image_path"].lstrip("/")
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

        conn.execute(
            """
            DELETE FROM event_images
            WHERE id = ?
        """,
            (image_id,),
        )
        conn.commit()

    conn.close()

    if event_id:
        return redirect(url_for("admin_event_images", event_id=event_id))

    return redirect(url_for("admin_event_images"))


# イベント動画アップロードルート


@app.route("/admin/event-images/upload-video", methods=["POST"])
def upload_event_video():
    event_id = request.form.get("event_id")

    if not event_id:
        flash("イベントが選択されていません", "error")
        return redirect(url_for("admin_event_images"))

    if "video" not in request.files:
        flash("動画ファイルが選択されていません", "error")
        return redirect(url_for("admin_event_images", event_id=event_id))

    file = request.files["video"]

    if not file or file.filename == "":
        flash("動画ファイルが選択されていません", "error")
        return redirect(url_for("admin_event_images", event_id=event_id))

    if not allowed_video_file(file.filename):
        flash("mp4ファイルのみアップロードできます", "error")
        return redirect(url_for("admin_event_images", event_id=event_id))

    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)

    if size_bytes > MAX_VIDEO_MB * 1024 * 1024:
        flash(f"動画サイズは{MAX_VIDEO_MB}MB以下にしてください", "error")
        return redirect(url_for("admin_event_images", event_id=event_id))

    event_folder = os.path.join(UPLOAD_FOLDER, f"event_{event_id}")
    os.makedirs(event_folder, exist_ok=True)

    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    unique_name = f"video_{uuid.uuid4().hex}{ext}"

    save_path = os.path.join(event_folder, unique_name)
    file.save(save_path)

    db_path = f"/static/uploads/event_{event_id}/{unique_name}"

    conn = get_db()

    old_event = conn.execute(
        """
        SELECT video_path
        FROM events
        WHERE id = ?
    """,
        (event_id,),
    ).fetchone()

    if old_event and old_event["video_path"]:
        try:
            old_path = old_event["video_path"].lstrip("/")
            if os.path.exists(old_path):
                os.remove(old_path)
        except:
            pass

    conn.execute(
        """
        UPDATE events
        SET video_path = ?
        WHERE id = ?
    """,
        (db_path, event_id),
    )

    conn.commit()
    conn.close()

    flash("動画を保存しました", "success")
    return redirect(url_for("admin_event_images", event_id=event_id))


# イベント動画削除ルート


@app.route("/admin/event-images/delete-video/<int:event_id>", methods=["POST"])
def delete_event_video(event_id):
    conn = get_db()

    event = conn.execute(
        """
        SELECT video_path
        FROM events
        WHERE id = ?
    """,
        (event_id,),
    ).fetchone()

    if event and event["video_path"]:
        try:
            file_path = event["video_path"].lstrip("/")
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

        conn.execute(
            """
            UPDATE events
            SET video_path = NULL
            WHERE id = ?
        """,
            (event_id,),
        )

        conn.commit()

    conn.close()

    flash("動画を削除しました", "success")
    return redirect(url_for("admin_event_images", event_id=event_id))


if __name__ == "__main__":
    init_db()
    add_members_page_image_columns()
    init_public_members_table()
    init_site_pages_table()
    init_users_table()
    add_status_column()
    add_event_extra_columns()
    init_member_gallery_table()
    add_application_cancel_columns()
    add_application_child_columns()
    add_time_columns()
    app.run(host="0.0.0.0", port=5000)
