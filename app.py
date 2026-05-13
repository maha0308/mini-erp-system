from flask import Flask, render_template, request, redirect, url_for
from datetime import date
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity_sold INTEGER NOT NULL,
            total_price REAL NOT NULL,
            sale_date TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    conn = get_db()
    total_products = conn.execute(
        'SELECT COUNT(*) FROM products'
    ).fetchone()[0]
    total_sales = conn.execute(
        'SELECT COUNT(*) FROM sales'
    ).fetchone()[0]
    total_revenue = conn.execute(
        'SELECT SUM(total_price) FROM sales'
    ).fetchone()[0] or 0
    low_stock = conn.execute(
        'SELECT * FROM products WHERE quantity < 5'
    ).fetchall()
    chart_data = conn.execute('''
        SELECT products.name, SUM(sales.quantity_sold) as total_sold
        FROM sales
        JOIN products ON sales.product_id = products.id
        GROUP BY products.name
    ''').fetchall()
    conn.close()
    chart_labels = [row['name'] for row in chart_data]
    chart_values = [row['total_sold'] for row in chart_data]
    return render_template('dashboard.html',
                           total_products=total_products,
                           total_sales=total_sales,
                           total_revenue=total_revenue,
                           low_stock=low_stock,
                           chart_labels=chart_labels,
                           chart_values=chart_values)

@app.route('/inventory')
def inventory():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('inventory.html', products=products)

@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    category = request.form['category']
    quantity = request.form['quantity']
    price = request.form['price']
    conn = get_db()
    conn.execute(
        'INSERT INTO products (name, category, quantity, price) VALUES (?, ?, ?, ?)',
        (name, category, quantity, price)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('inventory'))

@app.route('/delete_product/<int:id>')
def delete_product(id):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('inventory'))

@app.route('/edit_product/<int:id>', methods=['GET'])
def edit_product(id):
    conn = get_db()
    product = conn.execute(
        'SELECT * FROM products WHERE id = ?', (id,)
    ).fetchone()
    conn.close()
    return render_template('edit_product.html', product=product)

@app.route('/update_product/<int:id>', methods=['POST'])
def update_product(id):
    name = request.form['name']
    category = request.form['category']
    quantity = request.form['quantity']
    price = request.form['price']
    conn = get_db()
    conn.execute('''
        UPDATE products
        SET name = ?, category = ?, quantity = ?, price = ?
        WHERE id = ?
    ''', (name, category, quantity, price, id))
    conn.commit()
    conn.close()
    return redirect(url_for('inventory'))

@app.route('/sales')
def sales():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    all_sales = conn.execute('''
        SELECT sales.id, products.name, sales.quantity_sold,
               sales.total_price, sales.sale_date
        FROM sales
        JOIN products ON sales.product_id = products.id
        ORDER BY sales.id DESC
    ''').fetchall()
    conn.close()
    return render_template('sales.html', products=products, all_sales=all_sales)

@app.route('/add_sale', methods=['POST'])
def add_sale():
    product_id = request.form['product_id']
    quantity_sold = int(request.form['quantity_sold'])
    conn = get_db()
    product = conn.execute(
        'SELECT * FROM products WHERE id = ?', (product_id,)
    ).fetchone()
    if product['quantity'] < quantity_sold:
        conn.close()
        return "❌ Not enough stock! Go back and try again."
    total_price = product['price'] * quantity_sold
    sale_date = date.today().strftime("%Y-%m-%d")
    conn.execute(
        'INSERT INTO sales (product_id, quantity_sold, total_price, sale_date) VALUES (?, ?, ?, ?)',
        (product_id, quantity_sold, total_price, sale_date)
    )
    conn.execute(
        'UPDATE products SET quantity = quantity - ? WHERE id = ?',
        (quantity_sold, product_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('sales'))

@app.route('/reports')
def reports():
    conn = get_db()
    total_revenue = conn.execute(
        'SELECT SUM(total_price) FROM sales'
    ).fetchone()[0] or 0
    total_items_sold = conn.execute(
        'SELECT SUM(quantity_sold) FROM sales'
    ).fetchone()[0] or 0
    best_selling = conn.execute('''
        SELECT products.name,
               SUM(sales.quantity_sold) as total_sold,
               SUM(sales.total_price) as total_revenue
        FROM sales
        JOIN products ON sales.product_id = products.id
        GROUP BY products.name
        ORDER BY total_sold DESC
    ''').fetchall()
    daily_sales = conn.execute('''
        SELECT sale_date,
               SUM(total_price) as daily_revenue,
               COUNT(*) as num_sales
        FROM sales
        GROUP BY sale_date
        ORDER BY sale_date DESC
    ''').fetchall()
    conn.close()
    return render_template('reports.html',
                           total_revenue=total_revenue,
                           total_items_sold=total_items_sold,
                           best_selling=best_selling,
                           daily_sales=daily_sales)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)