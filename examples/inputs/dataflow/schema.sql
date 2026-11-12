CREATE TABLE accounts (account_id INTEGER PRIMARY KEY);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(account_id));
