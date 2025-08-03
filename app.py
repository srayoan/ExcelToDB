# app.py

from flask import Flask, render_template_string, request
import pyodbc
import pandas as pd
import io
import webbrowser
import threading
import time

# Initialize the Flask application
app = Flask(__name__)

# IMPORTANT: Database connection details
DB_SERVER = '10.10.1.8'
DB_DATABASE = 'SMSDB'
DB_USERNAME = 'sa'
DB_PASSWORD = 'kolkata@1'
DB_TABLE = 'Dummy'

# Construct the connection string for SSMS
DB_DRIVER = '{ODBC Driver 17 for SQL Server}'
DB_CONN_STR = f'DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USERNAME};PWD={DB_PASSWORD}'

# --- HTML Template for the Web Interface ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL Server Uploader</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen">
    <div class="bg-white p-8 rounded-2xl shadow-xl max-w-lg w-full text-center">
        <h1 class="text-3xl font-bold text-gray-800 mb-6">Upload Excel to SQL Server</h1>
        <form action="/upload" method="post" enctype="multipart/form-data" class="space-y-4">
            <label for="excel_file" class="block text-gray-600 font-medium">Select an Excel file:</label>
            <input type="file" name="excel_file" id="excel_file" accept=".xlsx" class="w-full text-gray-700 bg-gray-50 border border-gray-300 rounded-lg p-2.5 shadow-sm focus:ring-blue-500 focus:border-blue-500">
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition duration-300 transform hover:scale-105 shadow-md">
                Upload and Update
            </button>
        </form>
        {% if message %}
            <div class="mt-6 p-4 rounded-lg text-lg {% if 'Successfully' in message %}bg-green-100 text-green-700{% else %}bg-red-100 text-red-700{% endif %}">
                <p>{{ message }}</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

def open_browser():
    """Waits for the server to start and then opens the web browser."""
    # Try to connect to the server with a short delay
    time.sleep(1) 
    webbrowser.open('http://127.0.0.1:5000')

@app.route('/')
def index():
    """Renders the main page with the file upload form."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles the file upload and database update logic."""
    if 'excel_file' not in request.files:
        return render_template_string(HTML_TEMPLATE, message='No file part in the request.')
    
    file = request.files['excel_file']
    if file.filename == '':
        return render_template_string(HTML_TEMPLATE, message='No selected file.')

    if file:
        try:
            file_stream = io.BytesIO(file.read())
            df = pd.read_excel(file_stream)
            
            # --- FIX: Sanitize column names by replacing spaces with underscores ---
            df.columns = df.columns.str.replace(' ', '_')

            # --- Database Connection and Insertion ---
            conn = pyodbc.connect(DB_CONN_STR)
            cursor = conn.cursor()

            cursor.execute(f"TRUNCATE TABLE {DB_TABLE};")

            columns = ', '.join([f'[{c}]' for c in df.columns])
            placeholders = ', '. join(['?' for _ in df.columns])
            sql_insert = f"INSERT INTO {DB_TABLE} ({columns}) VALUES ({placeholders})"
            
            data_to_insert = [tuple(row) for row in df.values]
            
            cursor.executemany(sql_insert, data_to_insert)

            conn.commit()

            return render_template_string(HTML_TEMPLATE, message='Data uploaded and updated successfully!')
        
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            if sqlstate == '28000':
                error_msg = "Database connection failed. Please check the server details or credentials."
            else:
                error_msg = f"Database error: {ex}"
            return render_template_string(HTML_TEMPLATE, message=error_msg)
        
        except Exception as e:
            return render_template_string(HTML_TEMPLATE, message=f'An error occurred: {e}')
        
        finally:
            if 'conn' in locals():
                conn.close()

if __name__ == '__main__':
    # Start a new thread to open the browser
    threading.Thread(target=open_browser).start()
    
    # Use Waitress to serve the application on the local network
    from waitress import serve
    # '0.0.0.0' makes the server accessible from other computers on the network
    # The port '5000' is the address
    serve(app, host='0.0.0.0', port=5000)



