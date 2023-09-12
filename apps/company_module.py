import datetime

import pandas as pd
from flask import render_template, request, Blueprint, redirect, url_for
from storage_actions import *
from bson.objectid import ObjectId

company_bp = Blueprint('company', __name__,
                       template_folder='templates_company')


@company_bp.route("/cleaners", methods=['GET', 'POST'])
def cleaners_list():
    if request.method == 'POST':
        f = request.files['file']
        data_xls = pd.read_excel(f)
        create_users([{x: row[x] for x in data_xls.columns} for index, row in data_xls.iterrows()])
        return redirect(url_for('company.cleaners_list'))
    table = pd.DataFrame(get_all_cleaners())
    table = list(table.iterrows())
    table = list(map(lambda x: x[1], table))
    return render_template('employee_registry.html', entries=table)


@company_bp.route('/delete-user/<uid>')
def delete_user(uid):
    """Delete cleaner profile"""
    cleaners.delete_one({'_id': ObjectId(uid)})
    return redirect(url_for('company.cleaners_list'))


@company_bp.route('/edit-user/<uid>')
def edit_user(uid):
    """Edit cleaner profile"""
    return redirect(url_for('company.cleaners_list'))


@company_bp.route('/view-user/<uid>')
def view_user(uid):
    """Edit cleaner profile"""
    user = Cleaner(from_uid=uid)
    plan = user.get_plan()
    return render_template('cleaner_profile.html', user=user, plan=plan, today_date=datetime.date.today(), uid=uid)


@company_bp.route("/view-user/view-cleaning")
def view_user_cleaning():
    """/view-user/<uid>/cleaning?date=<date>"""
    cleaning = Cleaning(Cleaner(from_uid=request.args.get("uid")), request.args.get("date"))
    cleaning.upload()
    return render_template('cleaning_c.html', cleaning=cleaning, uid=request.args.get("uid"),
                           photos=cleaning.get_photos())
