from flask import Flask, request, jsonify, render_template, redirect, url_for, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import scoped_session
import pandas as pd
import requests
import schedule
import time
from datetime import datetime
from threading import Thread

app = Flask(__name__)

from config import Config
app.config.from_object(Config)

db = SQLAlchemy(app)

class ApiCall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_number = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    api_url = db.Column(db.String(200), nullable=False)
    retries = db.Column(db.Integer, nullable=False, default=3)
    interval = db.Column(db.Integer, nullable=False, default=1)
    last_status = db.Column(db.String(50), nullable=True)
    last_called = db.Column(db.DateTime, nullable=True)
    current_retries = db.Column(db.Integer, nullable=False, default=0)

    def __init__(self, name, contact_number, email, api_url, retries=3, interval=1):
        self.name = name
        self.contact_number = contact_number
        self.email = email
        self.api_url = api_url
        self.retries = retries
        self.interval = interval

with app.app_context():
    db.create_all()

def load_csv(file_path):
    new_df = pd.read_csv(file_path)
    for index, row in new_df.iterrows():
        contact_number_str = str(row['contact_number'])
        api_call = ApiCall.query.filter_by(contact_number=contact_number_str).first()
        if not api_call:
            # Add new record if it does not exist
            new_api_call = ApiCall(
                name=row['name'], 
                contact_number=contact_number_str,
                email=row['email'],
                api_url=row['api_url']
            )
            db.session.add(new_api_call)
    db.session.commit()
    schedule_jobs()

def call_api(api_url):
    print(f"Calling API: {api_url}")
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        print(f"API call successful: {api_url}")
        return True
    except requests.RequestException as e:
        print(f"API call failed: {api_url} with error: {e}")
        return False

def job(api_id):
    with app.app_context():
        session = scoped_session(db.session)
        print(f"Executing job for API ID: {api_id}")
        api_call = session.get(ApiCall, api_id)
        if not api_call:
            return
        success = call_api(api_call.api_url)
        api_call.last_called = datetime.now().replace(microsecond=0)
        if success:
            api_call.last_status = 'Success'
            api_call.current_retries = 0
            print(f"API call successful for ID {api_id}. Clearing all scheduled jobs for this API.")
            schedule.clear(f"{api_call.api_url}_retry")
            schedule.clear(f"{api_call.api_url}")
        else:
            if api_call.current_retries < api_call.retries:
                api_call.current_retries += 1
                print(f"Scheduling retry {api_call.current_retries} for API ID: {api_id}")
                schedule.every(api_call.interval).seconds.do(job, api_id).tag(f"{api_call.api_url}_retry")
            else:
                api_call.last_status = 'Failed'
                print(f"Max retries reached for API ID: {api_id}. Stopping retries.")
                schedule.clear(f"{api_call.api_url}_retry")
                schedule.clear(f"{api_call.api_url}")
        session.commit()
        session.remove()

def schedule_jobs():
    schedule.clear()
    api_calls = ApiCall.query.all()
    for api_call in api_calls:
        print(f"Scheduling job for API URL: {api_call.api_url}")
        schedule.every(1).seconds.do(job, api_call.id).tag(f"{api_call.api_url}")
        schedule.every(api_call.retries * api_call.interval + 1).seconds.do(lambda: schedule.clear(f"{api_call.api_url}_retry"))

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    if file:
        file_path = f"./{file.filename}"
        file.save(file_path)
        load_csv(file_path)
        return "File uploaded and scheduled successfully"

@app.route('/')
def index():
    api_calls = ApiCall.query.all()
    return render_template('index.html', api_calls=api_calls)

@app.route('/reset_failed', methods=['POST'])
def reset_failed():
    with app.app_context():
        failed_calls = ApiCall.query.filter_by(last_status='Failed').all()
        for api_call in failed_calls:
            api_call.current_retries = 0
            api_call.last_status = None
            db.session.commit()
            print(f"Resetting and rescheduling failed API URL: {api_call.api_url}")
            schedule.every(1).seconds.do(job, api_call.id).tag(f"{api_call.api_url}")
    return redirect(url_for('index'))

@app.route('/endpoint1', methods=['GET'])
def endpoint1():
    response = {
        'message': 'Hello from endpoint1!',
        'status': 'success'
    }
    return jsonify(response)

@app.route('/endpoint2', methods=['GET'])
def endpoint2():
    response = {
        'message': 'Hello from endpoint2!',
        'status': 'success'
    }
    return jsonify(response)

@app.route('/endpoint3', methods=['GET'])
def endpoint3():
    response = {
        'message': 'Hello from endpoint3!',
        'status': 'success'
    }
    return jsonify(response)

@app.route('/get_api_calls', methods=['GET'])
def get_api_calls():
    api_calls = ApiCall.query.all()
    api_calls_data = [
        {
            'id': api_call.id,
            'name': api_call.name,
            'contact_number': api_call.contact_number,
            'email': api_call.email,
            'api_url': api_call.api_url,
            'retries': api_call.retries,
            'interval': api_call.interval,
            'last_status': api_call.last_status,
            'last_called': api_call.last_called.strftime('%Y-%m-%d %H:%M:%S') if api_call.last_called else None,
            'current_retries': api_call.current_retries
        }
        for api_call in api_calls
    ]
    return jsonify({'api_calls': api_calls_data})

@app.route('/view_logs/<int:id>', methods=['GET'])
def view_logs(id):
    return render_template('view_logs.html', id=id)

@app.route('/edit_api_call/<int:id>', methods=['POST'])
def edit_api_call(id):
    data = request.get_json()
    api_call = ApiCall.query.get(id)
    if api_call:
        api_call.name = data['name']
        api_call.contact_number = data['contact_number']
        api_call.email = data['email']
        api_call.api_url = data['api_url']
        db.session.commit()
        return jsonify({'message': 'API call updated successfully'})
    else:
        return jsonify({'message': 'API call not found'}), 404

@app.route('/delete_api_call/<int:id>', methods=['DELETE'])
def delete_api_call(id):
    api_call = ApiCall.query.get(id)
    if api_call:
        db.session.delete(api_call)
        db.session.commit()
        return jsonify({'message': 'API call deleted successfully'})
    else:
        return jsonify({'message': 'API call not found'}), 404

if __name__ == "__main__":
    scheduler_thread = Thread(target=run_scheduler)
    scheduler_thread.start()
    app.run(host=app.config["HTTP_SERVER_ADDRESS"], port=app.config["HTTP_SERVER_PORT"], debug=app.config["HTTP_SERVER_DEBUG"])


