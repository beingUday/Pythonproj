import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
import mysql.connector
import random
import csv


def update_summary():
    total_items = sum(item['quantity'] for item in bill_items)
    summary = f"Total Items: {total_items}\nTotal Cost: {currency_var.get()}{total_var.get():.2f}"
    if bill_items:
        summary += f"\nLast Item: {bill_items[-1]['name']}"
    summary_text.set(summary)


def download_csv():
    if not bill_items:
        messagebox.showwarning("Warning", "No items to export.")
        return

    file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return

    try:
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Customer Name", name_entry.get()])
            writer.writerow(["Contact", contact_entry.get()])
            writer.writerow(["Tax Rate (%)", tax_rate_var.get()])
            writer.writerow([])  # Empty row
            writer.writerow(["Item", "Quantity", "Price", "Tax", "Total"])

            subtotal = 0
            tax_amount = 0

            for item in bill_items:
                subtotal += item['price'] * item['quantity']
                tax_amount += item['tax']
                writer.writerow([item['name'], item['quantity'], item['price'],
                                 item['tax'], item['total']])

            writer.writerow([])
            writer.writerow(["Subtotal", "", "", "", subtotal])
            writer.writerow(["Tax Total", "", "", "", tax_amount])
            writer.writerow(["Grand Total", "", "", "", total_var.get()])

        status_label['text'] = f"Bill exported to {file_path}"
    except Exception as e:
        messagebox.showerror("Error", str(e))


# ========== DATABASE CONNECTION ========== #
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='Uday@01022004',  # 🔁 CHANGE to your MySQL password
        database='billing_sys'
    )


# Try to update database schema if needed
def ensure_database_schema():
    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()

        # Check if tax_rate column exists in bills table
        mycursor.execute("SHOW COLUMNS FROM bills LIKE 'tax_rate'")
        tax_rate_exists = mycursor.fetchone()

        if not tax_rate_exists:
            # Add tax_rate column to bills table
            mycursor.execute("ALTER TABLE bills ADD COLUMN tax_rate FLOAT DEFAULT 0")
            status_label['text'] = "Database updated: Added tax_rate column to bills table"

        # Check if tax_amount column exists in bill_items table
        mycursor.execute("SHOW COLUMNS FROM bill_items LIKE 'tax_amount'")
        tax_amount_exists = mycursor.fetchone()

        if not tax_amount_exists:
            # Add tax_amount column to bill_items table
            mycursor.execute("ALTER TABLE bill_items ADD COLUMN tax_amount FLOAT DEFAULT 0")
            status_label['text'] += ", Added tax_amount column to bill_items table"

        mydb.commit()
        mydb.close()
        return True
    except Exception as e:
        messagebox.showinfo("Database Info", f"Using existing schema: {e}")
        return False


# ========== BILLING FUNCTIONS ========== #
def add_item():
    item_name = item_entry.get()
    try:
        quantity = float(quantity_entry.get())
        price = float(price_entry.get())
    except ValueError:
        messagebox.showerror("Input Error", "Enter valid numeric quantity and price.")
        return

    # Calculate tax for this item
    tax_rate = tax_rate_var.get() / 100  # Convert percentage to decimal
    item_price = quantity * price
    item_tax = item_price * tax_rate
    total_price = item_price + item_tax

    # Display in bill with tax
    bill_text.insert(tk.END, f"{item_name}\t{quantity}\t{price}\t{item_tax:.2f}\t{total_price:.2f}\n")

    # Update grand total
    total = float(total_var.get()) + total_price
    total_var.set(total)

    # Store item details
    bill_items.append({
        'name': item_name,
        'quantity': quantity,
        'price': price,
        'tax': item_tax,
        'total': total_price
    })

    item_entry.delete(0, tk.END)
    quantity_entry.delete(0, tk.END)
    price_entry.delete(0, tk.END)
    update_summary()


def save_bill():
    name = name_entry.get()
    contact = contact_entry.get()
    if not name or not contact:
        messagebox.showerror("Input Error", "Please fill customer name and contact.")
        return
    if not bill_items:
        messagebox.showerror("No Items", "Add at least one item to generate bill.")
        return

    bill_id = f"BL{random.randint(1000, 9999)}"
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total = total_var.get()
    tax_rate = tax_rate_var.get()

    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()

        # Check if the schema was updated
        schema_updated = True
        try:
            # Try to insert into bills with tax_rate
            mycursor.execute(
                "INSERT INTO bills (bill_id, customer_name, customer_contact, bill_date, total_amount, tax_rate) VALUES (%s, %s, %s, %s, %s, %s)",
                (bill_id, name, contact, date, total, tax_rate))
        except mysql.connector.Error as err:
            if "Unknown column 'tax_rate'" in str(err):
                # Fallback to original schema
                schema_updated = False
                mycursor.execute(
                    "INSERT INTO bills (bill_id, customer_name, customer_contact, bill_date, total_amount) VALUES (%s, %s, %s, %s, %s)",
                    (bill_id, name, contact, date, total))
            else:
                raise err

        # Insert each item
        for item in bill_items:
            if schema_updated:
                # Use updated schema with tax_amount
                mycursor.execute(
                    "INSERT INTO bill_items (bill_id, item_name, quantity, price_per_unit, tax_amount, total_price) VALUES (%s, %s, %s, %s, %s, %s)",
                    (bill_id, item['name'], item['quantity'], item['price'], item['tax'], item['total']))
            else:
                # Fallback to original schema
                mycursor.execute(
                    "INSERT INTO bill_items (bill_id, item_name, quantity, price_per_unit, total_price) VALUES (%s, %s, %s, %s, %s)",
                    (bill_id, item['name'], item['quantity'], item['price'], item['total']))

        mydb.commit()
        mydb.close()
        messagebox.showinfo("Success", f"Bill saved with ID: {bill_id}")
        clear_all()

    except Exception as e:
        messagebox.showerror("Database Error", f"Error saving bill: {e}")


def find_bill():
    search_id = search_entry.get()
    if not search_id:
        messagebox.showerror("Input Error", "Enter Bill ID to search.")
        return

    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()

        # Check if tax columns exist
        tax_rate_exists = False
        tax_amount_exists = False

        try:
            mycursor.execute("SHOW COLUMNS FROM bills LIKE 'tax_rate'")
            tax_rate_exists = mycursor.fetchone() is not None

            mycursor.execute("SHOW COLUMNS FROM bill_items LIKE 'tax_amount'")
            tax_amount_exists = mycursor.fetchone() is not None
        except:
            pass

        # Get basic bill info
        if tax_rate_exists:
            mycursor.execute(
                "SELECT bill_id, customer_name, customer_contact, bill_date, total_amount, tax_rate FROM bills WHERE bill_id = %s",
                (search_id,))
        else:
            mycursor.execute(
                "SELECT bill_id, customer_name, customer_contact, bill_date, total_amount FROM bills WHERE bill_id = %s",
                (search_id,))

        bill = mycursor.fetchone()
        if not bill:
            messagebox.showinfo("Not Found", "No bill found with that ID.")
            return

        # Get bill items
        if tax_amount_exists:
            mycursor.execute(
                "SELECT item_name, quantity, price_per_unit, tax_amount, total_price FROM bill_items WHERE bill_id = %s",
                (search_id,))
        else:
            mycursor.execute(
                "SELECT item_name, quantity, price_per_unit, total_price FROM bill_items WHERE bill_id = %s",
                (search_id,))

        items = mycursor.fetchall()

        bill_text.delete(1.0, tk.END)
        bill_text.insert(tk.END, f"Bill ID: {bill[0]}\nName: {bill[1]}\nContact: {bill[2]}\nDate: {bill[3]}\n")

        if tax_rate_exists:
            bill_text.insert(tk.END, f"Tax Rate: {bill[5]}%\n")

        bill_text.insert(tk.END, f"Total: {currency_var.get()}{bill[4]:.2f}\n\n")

        if tax_amount_exists:
            bill_text.insert(tk.END, "Item\tQty\tPrice\tTax\tTotal\n")
        else:
            bill_text.insert(tk.END, "Item\tQty\tPrice\tTotal\n")

        bill_text.insert(tk.END, "-" * 50 + "\n")

        for item in items:
            if tax_amount_exists:
                bill_text.insert(tk.END, f"{item[0]}\t{item[1]}\t{item[2]}\t{item[3]:.2f}\t{item[4]:.2f}\n")
            else:
                # For old schema without tax column
                bill_text.insert(tk.END, f"{item[0]}\t{item[1]}\t{item[2]}\t{item[3]:.2f}\n")

        mydb.close()
    except Exception as e:
        messagebox.showerror("Database Error", f"Error fetching bill: {e}")


def clear_all():
    name_entry.delete(0, tk.END)
    contact_entry.delete(0, tk.END)
    item_entry.delete(0, tk.END)
    quantity_entry.delete(0, tk.END)
    price_entry.delete(0, tk.END)
    bill_text.delete(1.0, tk.END)
    total_var.set(0.0)
    bill_items.clear()
    initialize_bill_header()


def initialize_bill_header():
    """Initialize the bill text area with a header"""
    store_name = store_name_var.get()
    currency = currency_var.get()
    tax = tax_rate_var.get()

    bill_text.delete(1.0, tk.END)
    bill_text.insert(tk.END, f"{store_name}\n")
    bill_text.insert(tk.END, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    bill_text.insert(tk.END, f"Tax Rate: {tax}%\n\n")
    bill_text.insert(tk.END, f"Item\tQty\tPrice\tTax\tTotal\n")
    bill_text.insert(tk.END, "-" * 50 + "\n")


# ========== LOGIN FUNCTION ========== #
def login():
    username = user_entry.get()
    password = pass_entry.get()

    try:
        mydb = get_db_connection()
        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM cred WHERE id = %s AND password = %s", (username, password))
        result = mycursor.fetchone()
        mydb.close()

        if result:
            login_window.destroy()
            billing_app()
        else:
            messagebox.showerror("Login Failed", "Incorrect credentials.")
    except Exception as e:
        messagebox.showerror("Database Error", f"Login failed: {e}")


# ========== BILLING APP UI ========== #
def billing_app():
    global name_entry, contact_entry, item_entry, quantity_entry, price_entry
    global bill_text, total_var, bill_items, search_entry, status_label
    global store_name_var, currency_var, tax_rate_var, summary_text

    # Try to update database schema
    ensure_database_schema()

    bill_items = []
    app = tk.Tk()
    app.title("Billing System")
    app.geometry("1000x700")
    app.configure(bg='#2e2e2e')
    app.resizable(False, False)

    # ==== Styles ====
    label_fg = 'white'
    entry_bg = '#3c3f41'
    entry_fg = 'white'
    btn_font = ('Helvetica', 10, 'bold')

    # ==== Frames ====
    left_frame = tk.Frame(app, bg='#2e2e2e')
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

    right_frame = tk.Frame(app, bg='#2e2e2e')
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

    bottom_frame = tk.Frame(app, bg='#2e2e2e')
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

    # ==== Customer Info ====
    tk.Label(left_frame, text="Customer Name", bg='#2e2e2e', fg=label_fg).grid(row=0, column=0, sticky='w')
    name_entry = tk.Entry(left_frame, bg=entry_bg, fg=entry_fg)
    name_entry.grid(row=0, column=1)

    tk.Label(left_frame, text="Contact", bg='#2e2e2e', fg=label_fg).grid(row=0, column=2, sticky='w')
    contact_entry = tk.Entry(left_frame, bg=entry_bg, fg=entry_fg)
    contact_entry.grid(row=0, column=3)

    # ==== Item Entry ====
    tk.Label(left_frame, text="Item", bg='#2e2e2e', fg=label_fg).grid(row=1, column=0, sticky='w')
    item_entry = tk.Entry(left_frame, bg=entry_bg, fg=entry_fg)
    item_entry.grid(row=1, column=1)

    tk.Label(left_frame, text="Quantity", bg='#2e2e2e', fg=label_fg).grid(row=1, column=2, sticky='w')
    quantity_entry = tk.Entry(left_frame, bg=entry_bg, fg=entry_fg)
    quantity_entry.grid(row=1, column=3)

    tk.Label(left_frame, text="Price", bg='#2e2e2e', fg=label_fg).grid(row=1, column=4, sticky='w')
    price_entry = tk.Entry(left_frame, bg=entry_bg, fg=entry_fg)
    price_entry.grid(row=1, column=5)

    # ==== Buttons ====
    button_frame = tk.Frame(left_frame, bg='#2e2e2e')
    button_frame.grid(row=2, column=0, columnspan=7, pady=10)

    tk.Button(button_frame, text="Add Item", command=add_item, bg='#28a745', fg='white', font=btn_font, width=12).grid(
        row=0, column=0, padx=5)
    tk.Button(button_frame, text="Save Bill", command=save_bill, bg='#007bff', fg='white', font=btn_font,
              width=12).grid(row=0, column=1, padx=5)
    tk.Button(button_frame, text="Download CSV", command=download_csv, bg='#17a2b8', fg='white', font=btn_font,
              width=14).grid(row=0, column=2, padx=5)
    tk.Button(button_frame, text="Clear", command=clear_all, bg='#dc3545', fg='white', font=btn_font, width=12).grid(
        row=0, column=3, padx=5)

    # ==== Total and Bill Display ====
    total_var = tk.DoubleVar(value=0.0)
    tk.Label(left_frame, text="Total", bg='#2e2e2e', fg=label_fg).grid(row=3, column=0, sticky='w')
    tk.Entry(left_frame, textvariable=total_var, state='readonly', bg=entry_bg, fg=entry_fg).grid(row=3, column=1)

    # Summary section
    summary_text = tk.StringVar(value="Total Items: 0\nTotal Cost: ₹0.00")
    summary_label = tk.Label(left_frame, textvariable=summary_text, bg='#1e1e1e', fg='white',
                             justify=tk.LEFT, anchor='w', padx=10, pady=5)
    summary_label.grid(row=3, column=2, columnspan=4, sticky='w')

    bill_text = tk.Text(left_frame, width=100, height=20, bg='#1e1e1e', fg='white')
    bill_text.grid(row=4, column=0, columnspan=7, pady=10)

    # ==== Search ====
    tk.Label(left_frame, text="Search Bill ID", bg='#2e2e2e', fg=label_fg).grid(row=5, column=0)
    search_entry = tk.Entry(left_frame, bg=entry_bg, fg=entry_fg)
    search_entry.grid(row=5, column=1)
    tk.Button(left_frame, text="Find", command=find_bill, bg='#ffc107', fg='black', font=btn_font).grid(row=5, column=2)

    # ==== Right Panel - Settings ==== #
    tk.Label(right_frame, text="Settings", bg='#2e2e2e', fg='white', font=('Helvetica', 14, 'bold')).pack(pady=10)

    # Store Name
    tk.Label(right_frame, text="Store Name:", bg='#2e2e2e', fg='white').pack(anchor='w', padx=10)
    store_name_var = tk.StringVar(value="My Store")
    store_entry = tk.Entry(right_frame, textvariable=store_name_var, bg=entry_bg, fg=entry_fg)
    store_entry.pack(anchor='w', padx=10, fill='x')

    # Currency Symbol
    tk.Label(right_frame, text="Currency Symbol:", bg='#2e2e2e', fg='white').pack(anchor='w', padx=10, pady=(10, 0))
    currency_var = tk.StringVar(value="₹")
    currency_options = ["₹", "$", "€", "£"]
    currency_menu = tk.OptionMenu(right_frame, currency_var, *currency_options)
    currency_menu.config(bg=entry_bg, fg=entry_fg, highlightbackground='#2e2e2e')
    currency_menu.pack(anchor='w', padx=10)

    # Default Tax Rate
    tk.Label(right_frame, text="Default Tax Rate (%):", bg='#2e2e2e', fg='white').pack(anchor='w', padx=10,
                                                                                       pady=(10, 0))
    tax_rate_var = tk.DoubleVar(value=5.0)  # Default to 5% tax
    tax_entry = tk.Entry(right_frame, textvariable=tax_rate_var, bg=entry_bg, fg=entry_fg)
    tax_entry.pack(anchor='w', padx=10, fill='x')

    # Save Settings Button
    def save_settings():
        status_label.config(
            text=f"Settings Saved: Store='{store_name_var.get()}', Symbol='{currency_var.get()}', Tax={tax_rate_var.get()}%")
        initialize_bill_header()  # Update the bill header with new settings

    tk.Button(right_frame, text="Save Settings", command=save_settings, bg='#17a2b8', fg='white', font=btn_font).pack(
        pady=10)

    # ==== Bottom Status Bar ====
    status_label = tk.Label(bottom_frame, text="Welcome to Billing System", bg='#2e2e2e', fg='lightgrey', anchor='w')
    status_label.pack(fill=tk.X, padx=10)

    # Initialize bill header
    initialize_bill_header()


# ========== LOGIN WINDOW ========== #
login_window = tk.Tk()
login_window.title("Login")
login_window.geometry("300x200")
login_window.resizable(False, False)

tk.Label(login_window, text="Username").pack(pady=5)
user_entry = tk.Entry(login_window)
user_entry.pack()

tk.Label(login_window, text="Password").pack(pady=5)
pass_entry = tk.Entry(login_window, show='*')
pass_entry.pack()

tk.Button(login_window, text="Login", command=login).pack(pady=10)

login_window.mainloop()