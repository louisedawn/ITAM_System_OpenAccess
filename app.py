import datetime
from flask import Flask, render_template, url_for, request, redirect, flash, session, request, redirect, url_for, jsonify, send_file, send_from_directory
from flask_login import login_required
from numpy import e
import pandas as pd
import pymysql
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
    conn = pymysql.connect(
        host='localhost',  # or your MariaDB server address
        user='root',  # your MariaDB username
        password='123',  # your MariaDB password
        db='ITAM',  # your MariaDB database name
        cursorclass=pymysql.cursors.DictCursor  # Ensures the results are returned as dictionaries
    )
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
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM user_accounts WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()
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
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM assets ORDER BY updated_at DESC')
        assets = cursor.fetchall()
        # Count the number of assets in different locations
        cursor.execute('SELECT COUNT(*) FROM assets WHERE station_no = "Storage Room"')
        storage_room_count = cursor.fetchone()['COUNT(*)']
        cursor.execute('SELECT COUNT(*) FROM assets WHERE location = "7th Floor"')
        seventh_floor_count = cursor.fetchone()['COUNT(*)']
        cursor.execute('SELECT COUNT(*) FROM assets WHERE location = "19th Floor"')
        nineteenth_floor_count = cursor.fetchone()['COUNT(*)']
        cursor.execute('SELECT COUNT(*) FROM assets WHERE location = "21st Floor"')
        twenty_first_floor_count = cursor.fetchone()['COUNT(*)']
        cursor.execute('SELECT COUNT(*) FROM assets WHERE location = "32nd Floor"')
        thirty_second_floor_count = cursor.fetchone()['COUNT(*)']
        cursor.execute('SELECT COUNT(*) FROM assets WHERE location = "WFH"')
        wfh_count = cursor.fetchone()['COUNT(*)']
        cursor.execute('SELECT COUNT(*) FROM assets WHERE location = "Wise Production Area"')
        wise_production_area_count = cursor.fetchone()['COUNT(*)']
        cursor.execute('SELECT COUNT(*) FROM assets WHERE location = "Vendor"')
        vendor_count = cursor.fetchone()['COUNT(*)']
        cursor.execute('SELECT COUNT(*) FROM assets WHERE location = "JAKA - 5th Floor"')
        jaka_fifth_floor_count = cursor.fetchone()['COUNT(*)']
    conn.close()

    return render_template('index.html', 
                           assets=assets, 
                           storage_room_count=storage_room_count,
                           seventh_floor_count=seventh_floor_count,
                           nineteenth_floor_count=nineteenth_floor_count,
                           twenty_first_floor_count=twenty_first_floor_count,
                           thirty_second_floor_count=thirty_second_floor_count,
                           wfh_count=wfh_count,
                           wise_production_area_count=wise_production_area_count,
                           vendor_count=vendor_count,
                           jaka_fifth_floor_count=jaka_fifth_floor_count)

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
    with conn.cursor() as cursor:
        cursor.execute(query)
        assets = cursor.fetchall()
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
        csv_file = csv.reader(file.stream.read().decode('utf-8').splitlines())
        next(csv_file)  # Skip header row
        conn = get_db_connection()
        with conn.cursor() as cursor:
            updated_rows = []
            unique_rows = []
            
            for row in csv_file:
                if len(row) < 19:
                    print("Warning: Row does not have enough columns:", row)
                    continue
                
                asset_type = row[1]
                asset_tag = row[3]
                serial_no = row[4]
                
                cursor.execute('SELECT * FROM assets WHERE asset_type = %s AND asset_tag = %s AND serial_no = %s',
                               (asset_type, asset_tag, serial_no))
                existing_row = cursor.fetchone()
                
                if existing_row:
                    cursor.execute('''UPDATE assets 
                                      SET site = %s, asset_type = %s, brand = %s, asset_tag = %s, serial_no = %s, location = %s, campaign = %s, station_no = %s, pur_date = %s, si_num = %s, model = %s, specs = %s, ram_slot = %s, ram_capacity = %s, ram_type = %s, pc_name = %s, win_ver = %s, last_upd = %s, completed_by = %s 
                                      WHERE id = %s''',
                                   (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], existing_row['id']))
                    updated_rows.append(row)
                else:
                    unique_rows.append(row)
            
            for row in unique_rows:
                cursor.execute('''INSERT INTO assets (site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by) 
                                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                               (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18]))
            
            conn.commit()
        conn.close()
        
        if updated_rows:
            update_messages = [f"Updated: {', '.join(row)}" for row in updated_rows]
            flash(f'Updated rows:\n' + '\n'.join(update_messages))
        if unique_rows:
            unique_messages = [f"Inserted: {', '.join(row)}" for row in unique_rows]
            flash(f'Inserted new rows:\n' + '\n'.join(unique_messages))
        
        flash('CSV file imported successfully.')
    else:
        flash('Invalid file format. Please upload a CSV file.')
    
    return redirect(url_for('inventory'))

@app.route('/inventory/', methods=["POST", "GET"])
@login_required
def inventory():
    serial_no = request.args.get('serial_no')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if serial_no:
                # Fetch the specific asset based on the serial number
                cursor.execute('SELECT * FROM assets WHERE serial_no = %s', (serial_no,))
                asset = cursor.fetchone()
                if asset:
                    assets = [asset]  # Show only the selected asset
                else:
                    flash(f'No asset found with serial number: {serial_no}')
                    assets = []
            else:
                # Fetch all assets if no serial number is provided
                cursor.execute('SELECT * FROM assets ORDER BY updated_at DESC')
                assets = cursor.fetchall()
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
        with conn.cursor() as cursor:
            # Fetch all assets ordered by the most recently updated
            cursor.execute('SELECT * FROM assets ORDER BY updated_at DESC')
            assets = cursor.fetchall()

            # Fetch all users ordered by the most recently updated
            cursor.execute('SELECT * FROM user_accounts ORDER BY updated_at DESC')
            users = cursor.fetchall()

            # Fetch all pending edits ordered by the most recently updated
            cursor.execute('SELECT * FROM edit_assets WHERE status = "pending" ORDER BY updated_at DESC')
            edit_assets = cursor.fetchall()
        
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

@app.route('/systemusers/', methods=["GET", "POST"])
@login_required
def system_users():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM user_accounts ORDER BY updated_at DESC')
        users = cursor.fetchall()
    conn.close()
    return render_template('systemusers.html', users=users)

@app.route('/add-user', methods=["POST"])
@login_required
def add_user():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    role = request.form.get('role')
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Insert a new user into the user_accounts table
            cursor.execute(
                'INSERT INTO user_accounts (email, name, password, user_role) VALUES (%s, %s, %s, %s)',
                (email, name, password, role)
            )
        conn.commit()
        conn.close()
        flash('New user account added successfully!')
    except Exception as e:
        flash(f'An error occurred while adding the user: {e}')
        return redirect(url_for('system_users'))  # Redirect to the system users page even if an error occurs

    return redirect(url_for('system_users'))

@app.route('/edit_user/<email>', methods=["GET", "POST"])
@login_required
def edit_user(email):
    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Fetch the user details to be edited
            cursor.execute('SELECT * FROM user_accounts WHERE email = %s', (email,))
            user = cursor.fetchone()

            if request.method == "POST":
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                super_admin_password = request.form.get('super_admin_password')

                # Fetch the currently logged-in super-admin user
                cursor.execute('SELECT * FROM user_accounts WHERE email = %s AND user_role = "Super-Admin"',
                               (session['user_email'],))
                super_admin = cursor.fetchone()

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

                # Prepare the update query and data
                update_query = 'UPDATE user_accounts SET name = %s, user_role = %s'
                update_data = [request.form.get('name'), request.form.get('role')]

                if new_password:
                    update_query += ', password = %s'
                    update_data.append(new_password)

                update_query += ' WHERE email = %s'
                update_data.append(email)

                # Execute the update query
                cursor.execute(update_query, tuple(update_data))
                conn.commit()
                flash('User account updated successfully!')
                return redirect(url_for('system_users'))
    except Exception as e:
        flash(f'An error occurred while updating the user: {e}')
        return redirect(url_for('system_users'))  # Redirect to system users page even if an error occurs
    finally:
        conn.close()

    return render_template('edit_user.html', user=user)

@app.route('/delete-user/<email>', methods=["GET", "POST"])
@login_required
def delete_user(email):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Execute the delete query
            cursor.execute('DELETE FROM user_accounts WHERE email = %s', (email,))
            conn.commit()
            flash('User account deleted successfully!')
    except Exception as e:
        flash(f'An error occurred while deleting the user: {e}')
    finally:
        conn.close()

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
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM user_accounts WHERE email = %s', (session['user_email'],))
            user = cursor.fetchone()
            if user and password == user['password']:
                # Password is correct; proceed to delete the user
                cursor.execute('DELETE FROM user_accounts WHERE email = %s', (email,))
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
        print(request.form)
        print("FORM SUBMITTED!!!")
        
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
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM assets WHERE serial_no = %s AND serial_no != "N/A" AND serial_no != ""', (serial_no,))
            existing_serial = cursor.fetchone()[0]
            if existing_serial > 0:
                flash('Serial number already exists. Please use a unique serial number.')
                return redirect(url_for('add_asset'))
            
            cursor.execute('SELECT COUNT(*) FROM assets WHERE asset_tag = %s AND asset_tag != "N/A" AND asset_tag != ""', (asset_tag,))
            existing_asset_tag = cursor.fetchone()[0]
            if existing_asset_tag > 0:
                flash('Asset tag already exists. Please use a unique asset tag.')
                return redirect(url_for('add_asset'))
            
            cursor.execute('''INSERT INTO assets (site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                         (site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by))
            conn.commit()
            flash('Asset added successfully!')
        
        except Exception as e:
            import traceback
            print("Error while adding asset:", e)
            print(traceback.format_exc())
            flash('An error occurred while adding the asset: {}'.format(str(e)))
        
        finally:
            conn.close()
        
        return redirect(url_for('inventory'))
    
    return render_template('add_asset.html')

@app.route('/delete-asset/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def delete_asset(asset_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM assets WHERE id = %s', (asset_id,))
        asset = cursor.fetchone()
        if request.method == 'POST':
            password = request.form.get('password')
            user_email = session.get('user_email')
            # Fetch the current user to validate password
            cursor.execute('SELECT * FROM user_accounts WHERE email = %s', (user_email,))
            user = cursor.fetchone()
            if user and password == user['password']:  # Assuming plain-text passwords
                cursor.execute('DELETE FROM assets WHERE id = %s', (asset_id,))
                conn.commit()
                flash('Asset deleted successfully.', 'success')
                return redirect(url_for('inventory'))
            else:
                flash('Invalid password. Please try again.', 'danger')
    conn.close()
    return render_template('delete_asset.html', asset=asset)

@app.route('/edit-asset/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Fetch the current asset details
            cursor.execute('SELECT * FROM assets WHERE id = %s', (asset_id,))
            asset = cursor.fetchone()
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
                    print(f"Checking serial number: {serial_no} for asset ID: {asset_id}")
                    # Check if the serial number already exists, excluding the current asset and serial numbers that are "N/A"
                    cursor.execute(
                        'SELECT id FROM assets WHERE serial_no = %s AND id != %s AND serial_no != "N/A"',
                        (serial_no, asset_id)
                    )
                    existing_serial = cursor.fetchall()
                    print(f"Matching assets with serial number: {existing_serial}")
                    if existing_serial:
                        flash('Serial number already exists. Please use a unique serial number.')
                        return redirect(url_for('edit_asset', asset_id=asset_id))

                    print(f"Checking asset tag: {asset_tag} for asset ID: {asset_id}")
                    # Check if the asset tag already exists, excluding the current asset and asset tags that are "N/A"
                    cursor.execute(
                        'SELECT id FROM assets WHERE asset_tag = %s AND id != %s AND asset_tag != "N/A"',
                        (asset_tag, asset_id)
                    )
                    existing_asset_tag = cursor.fetchall()
                    print(f"Matching assets with asset tag: {existing_asset_tag}")
                    if existing_asset_tag:
                        flash('Asset tag already exists. Please use a unique asset tag.')
                        return redirect(url_for('edit_asset', asset_id=asset_id))

                    # Update the data in the database
                    cursor.execute('''UPDATE assets SET site = %s, asset_type = %s, brand = %s, asset_tag = %s, serial_no = %s, location = %s, campaign = %s, station_no = %s, pur_date = %s, si_num = %s, model = %s, specs = %s, ram_slot = %s, ram_capacity = %s, ram_type = %s, pc_name = %s, win_ver = %s, last_upd = %s, completed_by = %s, updated_at = NOW() WHERE id = %s''',
                                    (site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by, asset_id))
                    conn.commit()
                    flash('Asset updated successfully!')
                except Exception as e:
                    print(f"Error: {e}")
                    flash('An error occurred while updating the asset.')
    except Exception as e:
        print(f"Error: {e}")
        flash('An error occurred while fetching the asset details.')
    finally:
        conn.close()

    return render_template('edit_asset.html', asset=asset)

@app.route('/request-inventory/', methods=["POST", "GET"])
@login_required
def request_inventory():
    serial_no = request.args.get('serial_no')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if serial_no:
                # Fetch the specific asset based on the serial number
                cursor.execute('SELECT * FROM assets WHERE serial_no = %s', (serial_no,))
                asset = cursor.fetchone()
                if asset:
                    assets = [asset]  # Show only the selected asset
                else:
                    flash(f'No asset found with serial number: {serial_no}')
                    assets = []
            else:
                # Fetch all assets if no serial number is provided
                cursor.execute('SELECT * FROM assets ORDER BY updated_at DESC')
                assets = cursor.fetchall()
        conn.close()
    except Exception as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('index'))  # Redirect to the index or handle it as needed
    return render_template('request_inventory.html', assets=assets)

@app.route('/request-edit/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def request_edit(asset_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM assets WHERE id = %s', (asset_id,))
        asset = cursor.fetchone()
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
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    '''INSERT INTO edit_assets 
                    (id, site, asset_type, brand, asset_tag, serial_no, location, campaign, station_no, pur_date, 
                    si_num, model, specs, ram_slot, ram_capacity, ram_type, pc_name, win_ver, last_upd, completed_by) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
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
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM edit_assets WHERE id = %s', (id,))
            edit_request = cursor.fetchone()
            if not edit_request:
                flash('Edit request not found.', 'danger')
                return redirect(url_for('audit'))
            
            # Update the assets table with the edit request data
            cursor.execute('''UPDATE assets SET site = %s, asset_type = %s, brand = %s, asset_tag = %s, serial_no = %s, location = %s, campaign = %s, station_no = %s, pur_date = %s, si_num = %s, model = %s, specs = %s, ram_slot = %s, ram_capacity = %s, ram_type = %s, pc_name = %s, win_ver = %s, last_upd = %s, completed_by = %s, updated_at = NOW() 
                            WHERE id = %s''',
                           (edit_request['site'], edit_request['asset_type'], edit_request['brand'], edit_request['asset_tag'], edit_request['serial_no'], edit_request['location'], edit_request['campaign'], edit_request['station_no'], edit_request['pur_date'], edit_request['si_num'], edit_request['model'], edit_request['specs'], edit_request['ram_slot'], edit_request['ram_capacity'], edit_request['ram_type'], edit_request['pc_name'], edit_request['win_ver'], edit_request['last_upd'], edit_request['completed_by'], edit_request['id']))
            
            # Mark the edit request as approved
            cursor.execute('UPDATE edit_assets SET status = "approved" WHERE id = %s', (id,))
            cursor.execute('DELETE FROM edit_assets WHERE id = %s', (id,))
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
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM edit_assets WHERE id = %s', (id,))
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