import sqlite3
conn = sqlite3.connect(r'D:\PremRaj\MoneyLogger\Money-Logger\db.sqlite3')
cur = conn.cursor()

print('=== All columns in savings_savingtransaction ===')
cur.execute('PRAGMA table_info(savings_savingtransaction);')
for c in cur.fetchall():
    print(f'  {c}')

print()
print('=== All columns in savings_savinggoal ===')
cur.execute('PRAGMA table_info(savings_savinggoal);')
for c in cur.fetchall():
    print(f'  {c}')

print()
print('=== django_migrations ===')
cur.execute('SELECT app, name, applied FROM django_migrations ORDER BY app, name;')
for row in cur.fetchall():
    print(f'  {row}')

print()
print('=== All tables matching savings ===')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%saving%';")
for tbl in cur.fetchall():
    print(f'  Table: {tbl[0]}')
    cur.execute(f'PRAGMA table_info({tbl[0]});')
    for col in cur.fetchall():
        print(f'    {col}')

conn.close()
