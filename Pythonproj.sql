-- Create database
CREATE DATABASE IF NOT EXISTS billing_sys;
USE billing_sys;

-- Create credentials table
CREATE TABLE IF NOT EXISTS cred (
    id VARCHAR(50) PRIMARY KEY,
    password VARCHAR(100)
);

-- Insert default admin if not exists
INSERT INTO cred (id, password)
SELECT 'admin', 'admin123'
WHERE NOT EXISTS (SELECT * FROM cred WHERE id = 'admin');

-- Create bills table
CREATE TABLE IF NOT EXISTS bills (
    bill_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(100),
    customer_contact VARCHAR(20),
    bill_date DATETIME,
    total_amount DECIMAL(10,2)
);

-- Create bill_items table
CREATE TABLE IF NOT EXISTS bill_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id VARCHAR(20),
    item_name VARCHAR(100),
    quantity DECIMAL(10,2),
    price_per_unit DECIMAL(10,2),
    total_price DECIMAL(10,2),
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
);

