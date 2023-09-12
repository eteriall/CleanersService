import flask
import pandas as pd
from flask import Flask, render_template, request, redirect, Blueprint
from flask_moment import Moment

from storage_actions import create_user, get_all_cleaners
from company_module import company_bp
from cleaners_module import cleaners_bp

app = Flask(__name__)
app.register_blueprint(company_bp, url_prefix='/admin')
app.register_blueprint(cleaners_bp, url_prefix='/cleaners')
moment = Moment(app)
app.secret_key = 'super secret key'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('photo')
    if not file:
        return 'No file selected', 400

    # Save the file to server storage
    file.save('path/to/save/' + file.filename)

    return 'File uploaded successfully'


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=82, debug=True)
