import random
import string
from os import environ

import pandas as pd
from flask import render_template, request, Blueprint, make_response, redirect, session, url_for, send_from_directory
from storage_actions import *
import traceback
import sys

import requests

cleaners_bp = Blueprint('cleaners', __name__,
                        template_folder='templates_cleaners')

USER_AUTH_CODES = {}
UPLOADED_CLEANINGS = []


@cleaners_bp.route('/main')
def main():
    cookie = from_cookie = request.cookies.get('uinfo')
    if cookie is None:
        return redirect(url_for('cleaners.login'))
    """Main page with data and buttons"""
    try:
        user = Cleaner(from_cookie=request.cookies.get('uinfo'))
        if not user.exists:
            return redirect('/cleaners/login')
        plan = user.get_plan()
        return render_template('main.html', user=user, plan=plan, today_date=datetime.date.today())
    except:
        print(traceback.format_exc())
        return redirect('/cleaners/login')


@cleaners_bp.route('/code', methods=['GET', 'POST'])
def enter_code():
    if request.cookies.get('uinfo') is not None:
        try:
            user = Cleaner(from_cookie=request.cookies.get('uinfo'))
            if user.exists:
                return redirect('/cleaners/main')
        except:
            pass
    try:
        phone = int(request.args['phone'])
        if request.method == 'POST':
            code = int(request.form.get('code'))
            if code == USER_AUTH_CODES[phone]:
                cleaner_user = Cleaner(phone)
                resp = make_response(redirect('/cleaners/main'))
                resp.set_cookie('uinfo', str(cleaner_user))
                return resp
    except:
        pass

    return render_template('code.html', phone=phone)


@cleaners_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login to the service by phone number"""
    try:
        user = Cleaner(from_cookie=request.cookies.get('uinfo'))
        if user.exists:
            return redirect('/cleaners/main')
    except:
        pass
    if request.method == 'POST':
        try:
            phone = int(request.form.get('username'))
            cleaner_user = Cleaner(phone)
            if cleaner_user.exists:
                login_code = random.randint(1000, 9999)
                USER_AUTH_CODES[phone] = login_code
                send_login_code(phone, login_code)
                # resp = make_response(redirect('/cleaners/main'))
                # resp.set_cookie('uinfo', str(cleaner_user))

                return redirect(url_for('cleaners.enter_code', phone=phone))
        except Exception as e:
            raise e
            pass
    return render_template('login.html')


@cleaners_bp.route('/logout')
def logout():
    resp = make_response(redirect('/cleaners/login'))
    resp.set_cookie('uinfo', '', expires=0)
    return resp


# ToDo: Check auth cookie
# ToDo: geo
@cleaners_bp.route('/cleaning')
def cleaning():
    cookie = from_cookie = request.cookies.get('uinfo')
    if cookie is None:
        return redirect(url_for('cleaners.login'))
    user = Cleaner(from_cookie=request.cookies.get('uinfo'))
    date = request.args.get('date')
    cleaning = Cleaning(user, date)
    if cleaning.get_str_cleaning() not in UPLOADED_CLEANINGS:
        cleaning.upload()
    session['prev_url'] = request.url
    return render_template('cleaning.html', cleaning=cleaning, photos=cleaning.get_photos())


@cleaners_bp.route('/finish')
def finish_cleaning():
    user = Cleaner(from_cookie=request.cookies.get('uinfo'))
    date = request.args.get('date')
    cleaning = Cleaning(user, date)
    cleaning.finish()
    return redirect(session.get('prev_url'))


@cleaners_bp.route('/photos/<path:filename>')
def get_photo(filename):
    return send_from_directory('photos', filename)


@cleaners_bp.route('/upload-image', methods=['POST'])
def upload_image():
    """/upload-image?phone=<phone>&date=<date>"""
    if 'photo' not in request.files:
        return 'No file provided', 400

    file = request.files['photo']
    if file.filename == '':
        return 'No file selected', 400
    cleaning = Cleaning(Cleaner(from_cookie=request.cookies.get('uinfo')), request.args.get("date"))
    # Save the file to server storage
    fname = f'photos/{request.args.get("phone")}_{request.args.get("date")}' \
            + f'_{"".join(random.sample(string.ascii_lowercase, 8))}.' + \
            file.filename.split('.')[-1]
    file.save(fname)
    cleaning.add_photo(fname)

    return redirect(session.get('prev_url'))


def send_login_code(phone, code):
    print(phone, code)

    # resp = requests.get(
    #     f'https://smsc.ru/sys/send.php?login=alex1122311&psw=Rassk69874500!&phones={phone}&mes=Твой код дворника для авторизации - {code}')
    # print(resp)
    # print(resp.text)

    sms_text = f'Код авторизации: {code}'
    print(phone, sms_text)

    resp = requests.get(
        f"https://ssl.bs00.ru/?method=push_msg&email={environ.get('SMSLOGIN')}&password={environ.get('SMSPASSWORD')}&text={sms_text}&phone={phone}&sender_name={environ.get('SMSSENDER')}")
    print(resp, resp.text)
