#!/usr/bin/env python3
"""
populate_db_postgres.py – fills a PostgreSQL instakill database with test data.

Usage:
    python populate_db_postgres.py [--users N] [--host HOST] [--port PORT]
                                   [--dbname DBNAME] [--user USER] [--password PASSWORD]

Requires:
    pip install faker bcrypt psycopg2-binary

Default: 10 000 users, each with 10-20 posts, 0-10 comments and 0-20 likes per post.
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import psycopg2
from faker import Faker

fake = Faker()

BATCH_SIZE = 1000
VIDEO_EXTS = [".mp4", ".mov", ".webm"]
PHOTO_EXTS = [".jpg", ".jpeg", ".png", ".webp"]


def now_ms():
    return datetime.now(timezone.utc)


def random_ts():
    """Random datetime within the past 7 days (timezone-aware)."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    dt = fake.date_time_between_dates(datetime_start=start, datetime_end=end)
    return dt.replace(tzinfo=timezone.utc)


def random_content():
    return " ".join(fake.words(nb=random.randint(1, 10)))[:1000]


def bcrypt_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def flush(cur, sql, batch):
    if batch:
        psycopg2.extras.execute_batch(cur, sql, batch, page_size=BATCH_SIZE)
        batch.clear()


def main():
    parser = argparse.ArgumentParser(description="Populate PostgreSQL instakill DB with test data")
    parser.add_argument("--users",    type=int, default=10_000)
    parser.add_argument("--host",     type=str, default="localhost")
    parser.add_argument("--port",     type=int, default=5432)
    parser.add_argument("--dbname",   type=str, default="instakill")
    parser.add_argument("--user",     type=str, default="postgres")
    parser.add_argument("--password", type=str, default="postgres")
    args = parser.parse_args()

    import psycopg2.extras  # noqa: needed for execute_batch

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.dbname,
        user=args.user,
        password=args.password,
    )
    conn.autocommit = False
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # 1. Clean tables (FK-safe order), keep alice and bob
    # ------------------------------------------------------------------
    print("Cleaning existing data (keeping alice and bob)...")
    cur.execute("DELETE FROM comments")
    cur.execute("DELETE FROM likes")
    cur.execute("DELETE FROM posts")
    cur.execute("DELETE FROM users WHERE username NOT IN ('alice', 'bob')")
    conn.commit()

    # ------------------------------------------------------------------
    # 2. Ensure alice, bob and charlie exist with known passwords
    # ------------------------------------------------------------------
    print("Ensuring alice, bob, charlie exist...")
    seed_hash = bcrypt_hash("password")
    for username, email in [
        ("alice",   "alice@example.com"),
        ("bob",     "bob@example.com"),
        ("charlie", "charlie@example.com"),
    ]:
        cur.execute(
            "INSERT INTO users (id, username, email, password_hash, created_at) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING",
            (str(uuid.uuid4()), username, email, seed_hash, now_ms()),
        )
    conn.commit()

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
    user_sql = "INSERT INTO users (id, username, email, password_hash, created_at) VALUES (%s, %s, %s, %s, %s)"
    for i in range(0, len(user_rows), BATCH_SIZE):
        psycopg2.extras.execute_batch(cur, user_sql, user_rows[i: i + BATCH_SIZE], page_size=BATCH_SIZE)
        conn.commit()
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
        "VALUES (%s, %s, 0, %s, %s, %s, %s, 0, %s)"
    )
    comment_sql = (
        "INSERT INTO comments (id, author_id, content, created_at, post_id) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    like_sql = (
        "INSERT INTO likes (id, created_at, post_id, user_id) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING"
    )

    post_batch, comment_batch, like_batch = [], [], []
    total_posts = total_comments = total_likes = 0

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
            flush(cur, post_sql, post_batch)
        if len(comment_batch) >= BATCH_SIZE:
            flush(cur, comment_sql, comment_batch)
        if len(like_batch) >= BATCH_SIZE:
            flush(cur, like_sql, like_batch)

        if (idx + 1) % 50 == 0:
            conn.commit()
            print(f"  {idx + 1}/{len(user_rows)} users | "
                  f"posts={total_posts} comments={total_comments} likes={total_likes}")

    flush(cur, post_sql, post_batch)
    flush(cur, comment_sql, comment_batch)
    flush(cur, like_sql, like_batch)
    conn.commit()

    # ------------------------------------------------------------------
    # 6. Update denormalized counters
    # ------------------------------------------------------------------
    print("Updating like_count and comment_count...")
    cur.execute("""
        UPDATE posts SET like_count =
            (SELECT COUNT(*) FROM likes WHERE likes.post_id = posts.id)
    """)
    cur.execute("""
        UPDATE posts SET comment_count =
            (SELECT COUNT(*) FROM comments WHERE comments.post_id = posts.id)
    """)
    conn.commit()

    cur.close()
    conn.close()
    print("\nDone!")
    print(f"  Users   : {args.users} generated + alice + bob + charlie")
    print(f"  Posts   : {total_posts}")
    print(f"  Comments: {total_comments}")
    print(f"  Likes   : {total_likes}")


if __name__ == "__main__":
    main()
