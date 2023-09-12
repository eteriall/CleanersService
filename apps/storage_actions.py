import base64
import datetime
import json
from os import environ

from bson import ObjectId
from cryptography.fernet import Fernet
from xor_cipher import *
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import certifi
from datetime import timedelta

uri = environ.get('DBURI')
ca = certifi.where()
client = MongoClient(uri, server_api=ServerApi('1'), tlsCAFile=ca)
mydb = client["data"]
cleaners = mydb["cleaners"]
companies = mydb['companies']
cleanings = mydb['cleanings']
SECRET_KEY = b'iLovEMiLK'


class Schedule:
    def __init__(self, schedule_string):
        d = schedule_string.lower().replace(' ', '').split(',')
        self.plan = {'пн': False, 'вт': False, 'ср': False, 'чт': False, 'пт': False, 'сб': False, 'вс': False}
        days = list(self.plan.keys())
        if 'все' in d:
            for day in self.plan:
                self.plan[day] = True
        else:
            for el in d:
                start_and_end = el.split('-')
                if len(start_and_end) == 2:
                    start, end = start_and_end
                    working_days = days[days.index(start):days.index(end) + 1]
                    for working_day in working_days:
                        self.plan[working_day] = True
                elif len(start_and_end) == 1:
                    self.plan[days[days.index(start_and_end[0])]] = True

    def get_current_week_plan(self) -> dict:
        """
        (0, 'пн', datetime.date(2023, 8, 7)) True
        (1, 'вт', datetime.date(2023, 8, 8)) False
        ...
        """
        start_day = 1
        end_day = 7
        base_date = datetime.date.today()
        monday = base_date - timedelta(days=base_date.isoweekday() - 1)
        week_dates = [monday + timedelta(days=i) for i in range(7)]
        week_dates = week_dates[start_day - 1:end_day or start_day]
        res = {}
        for day_i, weekday_key in enumerate(self.plan.keys()):
            res[(day_i, weekday_key, week_dates[day_i])] = self.plan[weekday_key]
        return res


class Cleaner:
    def __init__(self, phone=None, from_cookie=None, from_uid=None):
        if from_cookie is not None:
            try:
                # decMessage = xor_string(from_cookie, 0x42)
                data = json.loads(from_cookie)
                for key in data:
                    self.__setattr__(key, data[key])
                self.exists = True
            except:
                self.exists = False
                print('WRONG ENCODING')
        else:
            if from_uid is not None:
                user = cleaners.find_one({'_id': ObjectId(from_uid)})
            else:
                user = get_cleaner_by_phone(phone)
            if user is not None:
                self.name = user.get('Дворник')
                self.n = user.get('№ п/п')
                self.address = user.get('Адрес дворовой территории')
                self.uk = user.get('Наименование УК')
                self.upd = user.get('Управдомом')
                self.phone = user.get('Контакты дворника')
                self.upd_phone = user.get('Контакты управдомом')
                self.schedule_string = user.get('График работы')
                self.exists = True
            else:
                self.exists = False
                print('CANT FIND CLEANER')

    def get_plan(self) -> dict:
        try:
            schedule = Schedule(self.schedule_string)
            return schedule.get_current_week_plan()
        except:
            print("THERE'S NO SCHEDULE STRING")
            return {}

    def __str__(self):
        # s = xor_string(, 0x42)
        return json.dumps(self.__dict__)


class Cleaning:
    def __init__(self, cleaner=None, date=None, from_d_id=None):
        if from_d_id is not None:
            cursor = cleanings.find_one({'_id': ObjectId(from_d_id)})
            self.cleaner = Cleaner(cursor.get('Контакты дворника'))
            self.date = cursor.get('date')
            self.address = self.cleaner.address
            self.company = self.cleaner.uk
        else:
            self.d_id = None
            self.cleaner = cleaner
            self.date = date
            self.address = cleaner.address
            self.company = cleaner.uk

    def upload(self):
        # Check if already exists
        cursor = cleanings.find_one({'date': self.date, 'cleaner_phone': self.cleaner.phone})
        if cursor is None:
            self.d_id = cleanings.insert_one({'date': self.date,
                                              'cleaner_phone': self.cleaner.phone,
                                              'photos': [],
                                              'address': self.address,
                                              'company': self.company,
                                              'is_finished': False})

    def add_photo(self, photo_url):
        cleanings.find_one_and_update({'date': self.date, 'cleaner_phone': self.cleaner.phone},
                                      {'$push': {'photos': photo_url}})

    def finish(self):
        cleanings.find_one_and_update({'date': self.date, 'cleaner_phone': self.cleaner.phone},
                                      {'$set': {'is_finished': True}})

    @property
    def is_finished(self):
        return cleanings.find_one({'date': self.date, 'cleaner_phone': self.cleaner.phone}).get('is_finished', False)

    def get_photos(self):
        list_of_urls = cleanings.find_one({'date': self.date, 'cleaner_phone': self.cleaner.phone}).get('photos')
        return {i: list_of_urls[i] for i in range(len(list_of_urls))}

    def get_str_cleaning(self):
        return f'{self.date}:{self.cleaner.phone}'


def create_user(d):
    """Create new user from json"""
    x = cleaners.insert_one(d)


def create_users(d: list[dict]):
    existing_names = tuple(map(lambda x: x['Дворник'], get_all_cleaners()))
    r = []
    for c in d:
        if c['Дворник'] not in existing_names:
            r += [c]
    """Create new users from lists of json"""
    if r:
        x = cleaners.insert_many(r)


def get_all_cleaners():
    """Get list of all cleaners"""
    cursor = cleaners.find({})
    r = []
    for document in cursor:
        r += [document]
    return r


def get_cleaner_by_phone(phone):
    """Get list of all cleaners"""
    try:
        cursor = cleaners.find_one({'Контакты дворника': int(phone)})
        return cursor
    except:
        return None


def get_all_cleanings(query={}) -> list[Cleaning]:
    """Get all cleanings from database"""
    data = get_all_cleaners()
    for i, el in enumerate(data):
        data[i]['_id'] = str(data[i]['_id'])
    cleaners = {x['Контакты дворника']: Cleaner(from_cookie=json.dumps(x)) for x in data}
    cursor = cleanings.find(query)
    r = []
    for document in cursor:
        r += [Cleaning(cleaners[document['cleaner_phone']], document['date'])]
    return r


def get_cleaner_plan(cleaner_user):
    pass


if __name__ == "__main__":
    #
    # print(a.__dict__)
    # print(str(a))
    # b = Cleaner(from_cookie=str(a))
    # print(b.__dict__)

    # a = Schedule('пн-вт, сб-вс')
    # a.get_current_week_plan()
    print(Schedule('Пн').get_current_week_plan())
