#!/usr/bin/env python3
"""
populate_db.py – fills instakill.db with configurable test data.

Usage:
    python populate_db.py [--users N] [--db PATH]

Default: 10 000 users, each with 10-20 posts, 0-10 comments and 0-20 likes per post.
"""

import argparse
import os
import random
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from faker import Faker

fake = Faker()

BATCH_SIZE = 1000
VIDEO_EXTS = [".mp4", ".mov", ".webm"]
PHOTO_EXTS = [".jpg", ".jpeg", ".png", ".webp"]


def now_str():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def random_ts():
    """Random timestamp (epoch milliseconds) within the past 7 days."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    dt = fake.date_time_between_dates(datetime_start=start, datetime_end=end)
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def random_content():
    return " ".join(fake.words(nb=random.randint(1, 10)))[:1000]


def bcrypt_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def flush(conn, sql, batch):
    if batch:
        conn.executemany(sql, batch)
        batch.clear()


def main():
    parser = argparse.ArgumentParser(description="Populate instakill.db with test data")
    parser.add_argument("--users", type=int, default=10_000,
                        help="Number of users to generate (default: 10 000)")
    parser.add_argument("--db", type=str,
                        default=os.path.join("backend", "instakill.db"),
                        help="Path to instakill.db (default: backend/instakill.db)")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        raise FileNotFoundError(
            f"Database not found: {args.db}\nRun the backend first to create it."
        )

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Add media_type column if the backend hasn't added it yet
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(posts)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if "media_type" not in existing_cols:
        conn.execute("ALTER TABLE posts ADD COLUMN media_type VARCHAR(10)")
        conn.commit()
        print("Added media_type column to posts table.")

    # ------------------------------------------------------------------
    # 1. Clean tables (FK-safe order), keep alice and bob
    # ------------------------------------------------------------------
    print("Cleaning existing data (keeping alice and bob)...")
    with conn:
        conn.execute("DELETE FROM comments")
        conn.execute("DELETE FROM likes")
        conn.execute("DELETE FROM posts")
        conn.execute("DELETE FROM users WHERE username NOT IN ('alice', 'bob')")

    # ------------------------------------------------------------------
    # 2. Ensure alice, bob and charlie exist with known passwords
    # ------------------------------------------------------------------
    print("Ensuring alice, bob, charlie exist...")
    seed_hash = bcrypt_hash("password")
    with conn:
        for username, email in [
            ("alice",   "alice@example.com"),
            ("bob",     "bob@example.com"),
            ("charlie", "charlie@example.com"),
        ]:
            conn.execute(
                "INSERT OR IGNORE INTO users "
                "(id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), username, email, seed_hash, now_str()),
            )

    # ------------------------------------------------------------------
    # 3. Generate N users
    # ------------------------------------------------------------------
    print(f"Generating {args.users} users...")
    generated_hash = bcrypt_hash("password")

    used_usernames = {"alice", "bob", "charlie"}
    user_rows = []

    while len(user_rows) < args.users:
        username = fake.user_name()
        if username in used_usernames:
            username = f"{username}{random.randint(1000, 9999)}"
        if username in used_usernames:
            username = f"u{uuid.uuid4().hex[:10]}"
        used_usernames.add(username)
        uid = str(uuid.uuid4())
        email = f"{uid[:8]}@instakill.test"
        user_rows.append((uid, username, email, generated_hash, random_ts()))

        if len(user_rows) % 1000 == 0:
            print(f"  Prepared {len(user_rows)}/{args.users} users")

    print("Inserting users...")
    with conn:
        for i in range(0, len(user_rows), BATCH_SIZE):
            conn.executemany(
                "INSERT INTO users (id, username, email, password_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                user_rows[i: i + BATCH_SIZE],
            )
            print(f"  Users: {min(i + BATCH_SIZE, len(user_rows))}/{len(user_rows)}")

    # ------------------------------------------------------------------
    # 4. Collect all user IDs
    # ------------------------------------------------------------------
    cur.execute("SELECT id FROM users")
    all_user_ids = [row[0] for row in cur.fetchall()]
    print(f"Total users in DB: {len(all_user_ids)}")

    # ------------------------------------------------------------------
    # 5. Generate posts, comments, likes
    # ------------------------------------------------------------------
    print("Generating posts, comments, likes...")

    post_sql = (
        "INSERT INTO posts "
        "(id, author_id, comment_count, content, created_at, image_url, media_type, like_count, updated_at) "
        "VALUES (?, ?, 0, ?, ?, ?, ?, 0, ?)"
    )
    comment_sql = (
        "INSERT INTO comments (id, author_id, content, created_at, post_id) "
        "VALUES (?, ?, ?, ?, ?)"
    )
    like_sql = (
        "INSERT OR IGNORE INTO likes (id, created_at, post_id, user_id) "
        "VALUES (?, ?, ?, ?)"
    )

    post_batch, comment_batch, like_batch = [], [], []
    total_posts = total_comments = total_likes = 0

    conn.execute("BEGIN")

    for idx, (uid, _u, _e, _h, _t) in enumerate(user_rows):
        for _ in range(random.randint(10, 20)):
            post_id = str(uuid.uuid4())
            created_at = random_ts()

            media_type = random.choice(["photo", "video", None])
            if media_type == "photo":
                image_url = f"/media/{uuid.uuid4().hex}{random.choice(PHOTO_EXTS)}"
            elif media_type == "video":
                image_url = f"/media/{uuid.uuid4().hex}{random.choice(VIDEO_EXTS)}"
            else:
                image_url = None

            post_batch.append((post_id, uid, random_content(), created_at,
                                image_url, media_type, created_at))
            total_posts += 1

            # Comments 0-10
            num_c = random.randint(0, 10)
            if num_c:
                for commenter_id in random.sample(all_user_ids, min(num_c, len(all_user_ids))):
                    comment_batch.append((
                        str(uuid.uuid4()), commenter_id,
                        random_content()[:500], random_ts(), post_id
                    ))
                    total_comments += 1

            # Likes 0-20
            num_l = random.randint(0, 20)
            if num_l:
                for liker_id in random.sample(all_user_ids, min(num_l, len(all_user_ids))):
                    like_batch.append((str(uuid.uuid4()), random_ts(), post_id, liker_id))
                    total_likes += 1

        if len(post_batch) >= BATCH_SIZE:
            flush(conn, post_sql, post_batch)
        if len(comment_batch) >= BATCH_SIZE:
            flush(conn, comment_sql, comment_batch)
        if len(like_batch) >= BATCH_SIZE:
            flush(conn, like_sql, like_batch)

        if (idx + 1) % 50 == 0:
            conn.execute("COMMIT")
            conn.execute("BEGIN")
            print(f"  {idx + 1}/{len(user_rows)} users | "
                  f"posts={total_posts} comments={total_comments} likes={total_likes}")

    flush(conn, post_sql, post_batch)
    flush(conn, comment_sql, comment_batch)
    flush(conn, like_sql, like_batch)
    conn.execute("COMMIT")

    # ------------------------------------------------------------------
    # 6. Update denormalized counters
    # ------------------------------------------------------------------
    print("Updating like_count and comment_count...")
    with conn:
        conn.execute("""
            UPDATE posts SET like_count =
                (SELECT COUNT(*) FROM likes WHERE likes.post_id = posts.id)
        """)
        conn.execute("""
            UPDATE posts SET comment_count =
                (SELECT COUNT(*) FROM comments WHERE comments.post_id = posts.id)
        """)

    conn.close()
    print("\nDone!")
    print(f"  Users   : {args.users} generated + alice + bob + charlie (use --users 10000 for full dataset)")
    print(f"  Posts   : {total_posts}")
    print(f"  Comments: {total_comments}")
    print(f"  Likes   : {total_likes}")


if __name__ == "__main__":
    main()
