import datetime
from flask import Flask, render_template, url_for, request, redirect, flash, session, request, redirect, url_for, jsonify, send_file, send_from_directory
from flask_login import login_required
from numpy import e
import pandas as pd
import sqlite3
import io
import os
import csv
from functools import wraps
from datetime import datetime

app = Flask(__name__)

# Generate a random secret key if you don't have one
app.secret_key = os.urandom(24)
current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_db_connection():
    conn = sqlite3.connect('ITAM.db')
    conn.row_factory = sqlite3.Row
    return conn

''' ##### THIS USES SQLALCHEMY FOR THE CONNECTION OF THE BACKEND AND DATABASE

from flask import Flask, render_template, url_for, request, redirect, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuring SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ITAM.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
'''

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('home'))  # Redirect to the login page
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=["GET"])
def home():
    if 'user_email' in session:
        return redirect(url_for('index'))  # Redirect to the index if already logged in
    return render_template('login.html')

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user_accounts WHERE email = ? AND password = ?',
                        (email, password)).fetchone()
    conn.close()
    if user:
        session['user_email'] = email  # Store the logged-in user email in session
        session['user_name'] = user['name']
        session['user_role'] = user['user_role']
        return redirect(url_for('index'))
    else:
        flash('Invalid email or password! Please try again!')
        return redirect(url_for('home'))

@app.route("/index")
@login_required
def index():
    conn = get_db_connection()
    # Fetch all assets
    assets = conn.execute('SELECT * FROM assets ORDER BY updated_at DESC').fetchall()
    # Debug: Print assets to ensure data is being fetched
    print("Assets:", assets)
    # Count the number of assets in the Storage Room
    storage_room_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room"').fetchone()[0]
    monitor_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Monitor"').fetchone()[0]
    desktop_count  = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Desktop"').fetchone()[0]
    laptop_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Laptop"').fetchone()[0]
    headset_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Headset"').fetchone()[0]
    dongle_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Dongle"').fetchone()[0]
    IPPhone_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "IP Phone"').fetchone()[0]
    cctv_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "CCTV Camera"').fetchone()[0]
    switch_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Switch"').fetchone()[0]
    access_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Access Point"').fetchone()[0]
    router_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Router"').fetchone()[0]
    cp_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Cell Phone"').fetchone()[0]
    door_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Door Access"').fetchone()[0]
    server_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "Server"').fetchone()[0]
    ups_count = conn.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room" AND asset_type = "UPS"').fetchone()[0]

    conn.close()

    return render_template('index.html', 
                           assets=assets, 
                           storage_room_count=storage_room_count,
                           monitor_count = monitor_count,
                           desktop_count = desktop_count,
                           laptop_count = laptop_count, 
                           headset_count = headset_count, 
                           dongle_count = dongle_count, 
                           IPPhone_count =  IPPhone_count, 
                           cctv_count = cctv_count,
                           switch_count =  switch_count, 
                           access_count = access_count, 
                           router_count = router_count, 
                           cp_count =  cp_count,
                           door_count = door_count, 
                           server_count =  server_count,
                           ups_count =  ups_count )


@app.route("/export-excel", methods=["POST"])
@login_required
def export_excel():
    data = request.get_json()
    selected_columns = data.get('selectedColumns', [])
    if not selected_columns:
        flash('No columns selected for export.')
        return redirect(url_for('inventory'))
    columns_string = ', '.join(selected_columns)
    conn = get_db_connection()
    query = f'SELECT {columns_string} FROM assets ORDER BY id DESC'
    assets = conn.execute(query).fetchall()
    conn.close()
    assets_list = [dict(row) for row in assets]
    df = pd.DataFrame(assets_list, columns=selected_columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Assets')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="ITAssetsInventory.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
@app.route('/assets/', methods=["POST", "GET"])
@login_required
def assets():
    return render_template('assets.html')

@app.route("/import-csv", methods=["POST"])
@login_required
def import_csv():
    if 'csv_file' not in request.files:
        flash('No file part')
        return redirect(url_for('inventory'))
    file = request.files['csv_file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('inventory'))
    if file and file.filename.endswith('.csv'):
        # Read the CSV file
        csv_file = csv.reader(file.stream.read().decode('utf-8').splitlines())
        next(csv_file)  # Skip header row
        conn = get_db_connection()
        # Create a list to store updated rows
        updated_rows = []
        unique_rows = []
        # Check each row in the CSV
        for row in csv_file:
            #location = row[5]      # Assuming location is the 6th column (index 5)
            #campaign = row[6]      # Assuming campaign is the 7th column (index 6)
            #station_no = row[7]    # Assuming station_no is the 8th column (index 7)
            asset_type = row[1]      # Assuming asset_type is the 5th column (index 4)
            asset_tag = row[3]      # Assuming asset_type is the 5th column (index 4)
            serial_no = row[4]      # Assuming asset_type is the 5th column (index 4)
            # Check for existing rows with the same location, campaign, station_no, and serial_no
            existing_row = conn.execute('SELECT * FROM assets WHERE asset_type = ? AND asset_tag = ? AND serial_no = ?',
                                         (asset_type, asset_tag, serial_no)).fetchone()
            if existing_row:
                # Update the existing row with new data
                conn.execute('UPDATE assets SET site = ?, asset_type = ?, brand = ?, asset_tag = ?, serial_no = ?, location = ?, campaign = ?, station_no = ?, pur_date = ?, si_num = ?, model = ?, specs = ?, ram_slot = ?, ram_capacity = ?, ram_type = ?, pc_name = ?, win_ver = ?, last_upd = ?, completed_by = ? WHERE id = ?',
                             (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], existing_row[0]))  # Use existing row's id for the update
                updated_rows.append(row)
            else:
                # If no duplicate found, add to unique rows for insertion
                unique_rows.append(row)
        # Insert unique rows into the database
        for row in unique_rows:
            conn.execute('INSERT INTO assets (site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                         (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18]))
        conn.commit()
        conn.close()
        # Flash messages
        if updated_rows:
            update_messages = [f"Updated: {', '.join(row)}" for row in updated_rows]
            flash('The following rows were updated:\n' + '\n'.join(update_messages))
        if unique_rows:
            flash('CSV file imported successfully!')
    else:
        flash('Invalid file format. Please upload a CSV file.')
    return redirect(url_for('inventory'))

@app.route('/inventory/', methods=["POST", "GET"])
@login_required
def inventory():
    serial_no = request.args.get('serial_no')
    try:
        conn = get_db_connection()
        if serial_no:
            # Fetch the specific asset based on the serial number
            asset = conn.execute('SELECT * FROM assets WHERE serial_no = ?', (serial_no,)).fetchone()
            if asset:
                assets = [asset]  # Show only the selected asset
            else:
                flash(f'No asset found with serial number: {serial_no}')
                assets = []
        else:
            # Fetch all assets if no serial number is provided
            assets = conn.execute('SELECT * FROM assets ORDER BY updated_at DESC').fetchall()
        conn.close()
    except Exception as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('index'))  # Redirect to the index or handle it as needed
    return render_template('inventory.html', assets=assets)

@app.route('/audit/', methods=["POST", "GET"])
@login_required
def audit():
    try:
        conn = get_db_connection()
        assets = conn.execute('SELECT * FROM assets ORDER BY updated_at DESC').fetchall()
        users = conn.execute('SELECT * FROM user_accounts ORDER BY updated_at DESC').fetchall()
        edit_assets = conn.execute('SELECT * FROM edit_assets WHERE status = "pending" ORDER BY updated_at DESC').fetchall()
        conn.close()
    except Exception as e:
        print("An error occurred:", e)
        return "An error occurred while fetching data.", 500  # Return a 500 error
    return render_template('audit.html', assets=assets, users=users, edit_assets=edit_assets)

#for workstation
@app.route('/workstation/', methods=["POST", "GET"])
@login_required
def workstation():
    return render_template('workstation.html')

#for upload image 
app.config['UPLOAD_FOLDER'] = 'static'

@app.route('/upload_floor_image', methods=['POST'])
def upload_floor_image():
    if 'newImage' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    file = request.files['newImage']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    if file:
        floor = request.form['floor']
        filename = f"{floor.replace(' ', '_').lower()}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Delete old image if it exists
        if os.path.exists(filepath):
            os.remove(filepath)
        # Save the new image
        file.save(filepath)
        return jsonify({'success': True, 'filename': filename})
    return jsonify({'success': False})

#for PO
@app.route('/po/', methods=["POST", "GET"])
def po():
    return render_template('po.html')

@app.route('/systemusers/', methods=["GET"])
@login_required
def system_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM user_accounts').fetchall()
    conn.close()
    return render_template('systemusers.html', users=users)

@app.route('/add-user', methods=["POST"])
@login_required
def add_user():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    role = request.form.get('role')
    conn = get_db_connection()
    conn.execute('INSERT INTO user_accounts (email, name, password, user_role) VALUES (?, ?, ?, ?)',
                 (email, name, password, role))
    conn.commit()
    conn.close()
    flash('New user account added successfully!')
    return redirect(url_for('system_users'))

@app.route('/edit_user/<email>', methods=["GET", "POST"])
@login_required
def edit_user(email):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user_accounts WHERE email = ?', (email,)).fetchone()
    if request.method == "POST":
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        super_admin_password = request.form.get('super_admin_password')
        # Fetch the currently logged-in super-admin user
        super_admin = conn.execute('SELECT * FROM user_accounts WHERE email = ? AND user_role = "Super-Admin"',
                                   (session['user_email'],)).fetchone()
        if not super_admin:
            flash('You must be a super-admin to edit user details.')
            return redirect(url_for('home'))
        # Check if current password is correct
        if current_password != user['password']:
            flash('Current password is incorrect.')
            return render_template('edit_user.html', user=user)
        # Check if super-admin password is correct
        if super_admin_password != super_admin['password']:
            flash('Super-Admin password is incorrect.')
            return render_template('edit_user.html', user=user)
        # Check if new password and confirm password match
        if new_password and new_password != confirm_password:
            flash('New password and confirmation do not match.')
            return render_template('edit_user.html', user=user)
        # Prepare the update data
        update_data = {
            'name': request.form.get('name'),
            'user_role': request.form.get('role'),
            'email': email
        }
        if new_password:
            update_data['password'] = new_password
        # Update user details in the database
        query = 'UPDATE user_accounts SET name = :name, user_role = :user_role {password_clause} WHERE email = :email'.format(
            password_clause=', password = :password' if new_password else ''
        )
        conn.execute(query, update_data)
        conn.commit()
        conn.close()
        flash('User account updated successfully!')
        return redirect(url_for('system_users'))
    conn.close()
    return render_template('edit_user.html', user=user)

@app.route('/delete-user/<email>', methods=["GET", "POST"])
@login_required
def delete_user(email):
    conn = get_db_connection()
    conn.execute('DELETE FROM user_accounts WHERE email = ?', (email,))
    conn.commit()
    conn.close()
    flash('User account deleted successfully!')
    return redirect(url_for('system_users'))

@app.route("/logout")
def logout():
    session.pop('user_email', None)  # Remove user_email from the session
    flash('You have successfully logged out!')
    return redirect(url_for('home'))

@app.after_request
def add_header(response):
    response.cache_control.no_cache = True
    response.cache_control.no_store = True
    response.cache_control.must_revalidate = True
    return response

@app.route('/confirm-delete/<email>', methods=["GET", "POST"])
@login_required
def confirm_delete(email):
    if request.method == "POST":
        # Check the password provided by the logged-in user
        password = request.form.get('password')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user_accounts WHERE email = ?', (session['user_email'],)).fetchone()
        if user and password == user['password']:
            # Password is correct; proceed to delete the user
            conn.execute('DELETE FROM user_accounts WHERE email = ?', (email,))
            conn.commit()
            flash('User account deleted successfully!')
            return redirect(url_for('system_users'))
        else:
            flash('Incorrect password. Please try again.')
            return redirect(url_for('confirm_delete', email=email))
    return render_template('confirm_delete.html', email=email)

@app.route('/add-asset/', methods=["GET", "POST"])
@login_required
def add_asset():
    if request.method == "POST":
        # Log the incoming data for debugging
        print(request.form)  # Print submitted data for debugging
        print("FORM SUBMITTED!!!")
        # Get data from the form
        site = request.form.get('site')  
        asset_type = request.form.get('asset_type')
        brand = request.form.get('brand')
        asset_tag = request.form.get('asset_tag')
        serial_no = request.form.get('serial_no')
        location = request.form.get('location')
        campaign = request.form.get('campaign')
        station_no = request.form.get('station_no')
        pur_date = request.form.get('pur_date')
        si_num = request.form.get('si_num')
        model = request.form.get('model') 
        specs = request.form.get('specs')
        ram_slot = request.form.get('ram_slot')
        ram_capacity = request.form.get('ram_capacity')
        ram_type = request.form.get('ram_type')
        pc_name = request.form.get('pc_name')
        win_ver = request.form.get('win_ver')
        last_upd = request.form.get('last_upd')
        completed_by = request.form.get('completed_by')
        # Check if the serial number already exists, except for "N/A"
        try:
            conn = get_db_connection()
            existing_serial = conn.execute('SELECT COUNT(*) FROM assets WHERE serial_no = ? AND serial_no != "N/A" AND serial_no != ""', (serial_no,)).fetchone()[0]
            if existing_serial > 0:
                flash('Serial number already exists. Please use a unique serial number.')
                return redirect(url_for('add_asset'))
            existing_asset_tag = conn.execute('SELECT COUNT(*) FROM assets WHERE asset_tag = ? AND asset_tag != "N/A" AND asset_tag != ""', (asset_tag,)).fetchone()[0]
            if existing_asset_tag > 0:
                flash('Asset tag already exists. Please use a unique asset tag.')
                return redirect(url_for('add_asset'))
            # Insert the data into the database
            conn.execute('''INSERT INTO assets (site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by))
            conn.commit()
            flash('Asset added successfully!')
        except Exception as e:
            print(f"Error while adding asset: {e}")  # More detailed error logging
            flash('An error occurred while adding the asset: {}'.format(str(e)))  # Show the error message to the user
        finally:
            conn.close()
        return redirect(url_for('inventory'))
    return render_template('add_asset.html')

@app.route('/delete-asset/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def delete_asset(asset_id):
    conn = get_db_connection()
    asset = conn.execute('SELECT * FROM assets WHERE id = ?', (asset_id,)).fetchone()
    if request.method == 'POST':
        password = request.form.get('password')
        user_email = session.get('user_email')
        # Fetch the current user to validate password
        user = conn.execute('SELECT * FROM user_accounts WHERE email = ?', (user_email,)).fetchone()
        if user and password == user['password']:  # Assuming plain-text passwords
            conn.execute('DELETE FROM assets WHERE id = ?', (asset_id,))
            conn.commit()
            flash('Asset deleted successfully.', 'success')
            conn.close()
            return redirect(url_for('inventory'))
        else:
            flash('Invalid password. Please try again.', 'danger')
    conn.close()
    return render_template('delete_asset.html', asset=asset)

@app.route('/edit-asset/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_id):
    conn = get_db_connection()
    asset = conn.execute('SELECT * FROM assets WHERE id = ?', (asset_id,)).fetchone()
    if not asset:
        flash('Asset not found.')
        return redirect(url_for('inventory'))
    if request.method == 'POST':
        # Get data from the form
        site = request.form.get('site')
        asset_type = request.form.get('asset_type')
        brand = request.form.get('brand')
        asset_tag = request.form.get('asset_tag')
        serial_no = request.form.get('serial_no')
        location = request.form.get('location')
        campaign = request.form.get('campaign')
        station_no = request.form.get('station_no')
        pur_date = request.form.get('pur_date')
        si_num = request.form.get('si_num')
        model = request.form.get('model')
        specs = request.form.get('specs')
        ram_slot = request.form.get('ram_slot')
        ram_capacity = request.form.get('ram_capacity')
        ram_type = request.form.get('ram_type')
        pc_name = request.form.get('pc_name')
        win_ver = request.form.get('win_ver')
        last_upd = request.form.get('last_upd')
        completed_by = request.form.get('completed_by')
        # Check for unique serial number and asset tag, excluding "N/A" values and the current asset
        try:
            # Debugging: Print the serial number being checked
            print(f"Checking serial number: {serial_no} for asset ID: {asset_id}")
            # Check if the serial number already exists, excluding the current asset and serial numbers that are "N/A"
            existing_serial = conn.execute(
                'SELECT id FROM assets WHERE serial_no = ? AND id != ? AND serial_no != "N/A"', 
                (serial_no, asset_id)
            ).fetchall()
            print(f"Matching assets with serial number: {existing_serial}")  # Debugging: Print matching asset IDs
            if len(existing_serial) > 0:
                flash('Serial number already exists. Please use a unique serial number.')
                return redirect(url_for('edit_asset', asset_id=asset_id))
            # Debugging: Print the asset tag being checked
            print(f"Checking asset tag: {asset_tag} for asset ID: {asset_id}")
            # Check if the asset tag already exists, excluding the current asset and asset tags that are "N/A"
            existing_asset_tag = conn.execute(
                'SELECT id FROM assets WHERE asset_tag = ? AND id != ? AND asset_tag != "N/A"', 
                (asset_tag, asset_id)
            ).fetchall()
            print(f"Matching assets with asset tag: {existing_asset_tag}")  # Debugging: Print matching asset tag IDs
            if len(existing_asset_tag) > 0:
                flash('Asset tag already exists. Please use a unique asset tag.')
                return redirect(url_for('edit_asset', asset_id=asset_id))
            # Update the data in the database
            conn.execute('''UPDATE assets SET site = ?, asset_type = ?, brand = ?, asset_tag = ?, serial_no = ?, location = ?, campaign = ?, station_no = ?, pur_date = ?, si_num = ?, model = ?, specs = ?, ram_slot = ?, ram_capacity = ?, ram_type = ?, pc_name = ?, win_ver = ?, last_upd = ?, completed_by = ?, updated_at = DATETIME('now', 'localtime') WHERE id = ?''',
                         (site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by, asset_id))
            conn.commit()
            flash('Asset updated successfully!')
        except Exception as e:
            print(f"Error: {e}")
            flash('An error occurred while updating the asset.')
        finally:
            conn.close()
        return redirect(url_for('inventory'))
    conn.close()
    return render_template('edit_asset.html', asset=asset)

@app.route('/request-inventory/', methods=["POST", "GET"])
@login_required
def request_inventory():
    serial_no = request.args.get('serial_no')
    try:
        conn = get_db_connection()
        if serial_no:
            # Fetch the specific asset based on the serial number
            asset = conn.execute('SELECT * FROM assets WHERE serial_no = ?', (serial_no,)).fetchone()
            if asset:
                assets = [asset]  # Show only the selected asset
            else:
                flash(f'No asset found with serial number: {serial_no}')
                assets = []
        else:
            # Fetch all assets if no serial number is provided
            assets = conn.execute('SELECT * FROM assets ORDER BY updated_at DESC').fetchall()
        conn.close()
    except Exception as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('index'))  # Redirect to the index or handle it as needed
    return render_template('request_inventory.html', assets=assets)

@app.route('/request-edit/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def request_edit(asset_id):
    conn = get_db_connection()
    asset = conn.execute('SELECT * FROM assets WHERE id = ?', (asset_id,)).fetchone()
    conn.close()
    if request.method == 'POST':
        data = {
            'id': request.form.get('id'),
            'site': request.form.get('site'),
            'asset_type': request.form.get('asset_type'),
            'brand': request.form.get('brand'),
            'asset_tag': request.form.get('asset_tag'),
            'serial_no': request.form.get('serial_no'),
            'location': request.form.get('location'),
            'campaign': request.form.get('campaign'),
            'station_no': request.form.get('station_no'),
            'pur_date': request.form.get('pur_date'),
            'si_num': request.form.get('si_num'),
            'model': request.form.get('model'),
            'specs': request.form.get('specs'),
            'ram_slot': request.form.get('ram_slot'),
            'ram_capacity': request.form.get('ram_capacity'),
            'ram_type': request.form.get('ram_type'),
            'pc_name': request.form.get('pc_name'),
            'win_ver': request.form.get('win_ver'),
            'last_upd': request.form.get('last_upd'),
            'completed_by': request.form.get('completed_by')  # Correct field from the form
        }
        # Verify the values are correctly fetched
        print(data)  # Debugging purposes
        conn = get_db_connection()
        try:
            conn.execute(
                '''INSERT INTO edit_assets 
                (id, site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, 
                si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (data['id'], data['site'], data['asset_type'], data['brand'], data['asset_tag'], data['serial_no'],
                 data['location'], data['campaign'], data['station_no'], data['pur_date'], data['si_num'], data['model'],
                 data['specs'], data['ram_slot'], data['ram_capacity'], data['ram_type'], data['pc_name'], data['win_ver'],
                 data['last_upd'], data['completed_by'])
            )
            conn.commit()
            flash('Edit request submitted successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred while requesting to edit the asset: {e}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('request_inventory'))
    return render_template('request_edit.html', asset=asset)

@app.route('/audit/approve/<int:id>', methods=['POST'])
@login_required
def approve_edit(id):
    conn = get_db_connection()
    try:
        edit_request = conn.execute('SELECT * FROM edit_assets WHERE id = ?', (id,)).fetchone()
        if not edit_request:
            flash('Edit request not found.', 'danger')
            return redirect(url_for('audit'))
        # Update the assets table with the edit request data
        conn.execute('''UPDATE assets SET site = ?, asset_type = ?, brand = ?, asset_tag = ?, serial_no = ?, location = ?, campaign = ?, station_no = ?, pur_date = ?, si_num = ?, model = ?, specs = ?, ram_slot = ?, ram_capacity = ?, ram_type = ?, pc_name = ?, win_ver = ?, last_upd = ?, completed_by = ?, updated_at = DATETIME('now', 'localtime') WHERE id = ?''',
                     (edit_request['site'], edit_request['asset_type'], edit_request['brand'], edit_request['asset_tag'], edit_request['serial_no'], edit_request['location'], edit_request['campaign'], edit_request['station_no'], edit_request['pur_date'], edit_request['si_num'], edit_request['model'], edit_request['specs'], edit_request['ram_slot'], edit_request['ram_capacity'], edit_request['ram_type'], edit_request['pc_name'], edit_request['win_ver'], edit_request['last_upd'], edit_request['completed_by'], edit_request['id']))
        # Mark the edit request as approved
        conn.execute('UPDATE edit_assets SET status = "approved" WHERE id = ?', (id,))
        conn.execute('DELETE FROM edit_assets WHERE id = ?', (id,))
        conn.commit()
        flash('Edit request approved and applied.', 'success')
    except Exception as e:
        print("An error occurred during approval:", e)
        flash('An error occurred while approving the edit request.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('audit'))

@app.route('/reject_edit/<int:id>', methods=['POST'])
@login_required
def reject_edit(id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM edit_assets WHERE id = ?', (id,))
        conn.commit()
        flash('The edit request has been rejected.', 'success')
    except Exception as e:
        print("An error occurred while rejecting the edit request:", e)
        flash('An error occurred while rejecting the edit request.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('audit'))
if __name__ == "__main__":
    app.run(debug=True)