import auth, os, uuid

print('DB_PATH:', auth.DB_PATH)
print('DB exists:', os.path.exists(auth.DB_PATH))

conn = auth.get_db()
cur = conn.cursor()
try:
    jm = cur.execute("PRAGMA journal_mode;").fetchone()
    sync = cur.execute("PRAGMA synchronous;").fetchone()
    print('journal_mode:', jm)
    print('synchronous:', sync)

    uname = 'test_' + uuid.uuid4().hex[:8]
    email = uname + '@example.com'
    pw = 'password123'
    print('Attempting signup for', uname)
    success, msg = auth.signup_user(uname, email, pw)
    print('signup:', success, msg)

    if success:
        # remove the test user
        c2 = auth.get_db()
        c2.execute('DELETE FROM users WHERE username = ?', (uname,))
        c2.commit()
        c2.close()
        print('cleanup done')

except Exception as e:
    print('Error during checks:', e)
finally:
    conn.close()
