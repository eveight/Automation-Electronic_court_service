import os
import pickle
import re
import concurrent.futures
from database import Session
from models import FillingDebtor

from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException, NoSuchWindowException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
import pyautogui
import pandas as pd
import logging
from functools import wraps
import time

from selenium.webdriver.support.wait import WebDriverWait

from filling_debtors.base import GetDataDBDebtors

from creation_civil_receipt.base import Mixin

# Setup logging
logger = logging.getLogger(__name__)


class UpdateDebtorStatus:
    def __init__(self, data_block, user_id):
        self.data_block = data_block
        self.user_id = user_id

    def update_status_in_db(self):
        for v in self.data_block:
            session = Session()
            try:
                pinfl_of_debtor = v.get('debtors_pinfl')
                debtor = session.query(FillingDebtor).filter_by(debtors_pinfl=pinfl_of_debtor,
                                                                 status_of_created=False,
                                                                 user_id=self.user_id).first()
                if debtor:
                    debtor.status_of_created = True
                    session.commit()
                else:
                    raise Exception(f"Дебтор с ПИНФЛ {pinfl_of_debtor} не найден или уже был создан.")
            except Exception as e:
                print(f"[ERROR]: Ошибка обновления строки в бд.")
                logger.error(f"Ошибка обновления строки в бд. {e}")
            finally:
                session.close()


class FillingEcourtBot(Mixin):
    def __init__(self, data_list, user_id):
        self.driver = webdriver.Chrome()
        self.user_id = user_id
        self.token = None
        self.problem_rows = []
        self.CREDS = {}

        self.get_base_dir()
        self.data_list = data_list

    def write_problem_dicts_to_excel(self, output_file='problem_rows.xlsx'):
        if self.problem_rows:
            try:
                df = pd.DataFrame(self.problem_rows)
                df.to_excel(f'{self.dir_to_folder}/{output_file}', sheet_name='Лист1', index=True)
                print(f"Данные успешно записаны в {output_file}")
            except Exception as e:
                logger.error(f"Ошибка записи данных в файл: {e}")
                raise Exception(f"Ошибка записи данных в файл.")

    def get_base_dir(self):
        self.base_dir = os.path.join(self.FOLDER_PATH_BASE, 'filling_ecourt', 'file_for_six_page')
        self.dir_to_folder = os.path.join(self.FOLDER_PATH_BASE, 'filling_ecourt')

    @staticmethod
    def retry_on_error(max_retries=3, wait_time=5):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                retries = 0
                while retries < max_retries:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Error occurred: {e}. Retrying in {wait_time} seconds...")
                        retries += 1
                        time.sleep(wait_time)
                raise Exception(f"Max retries ({max_retries}) exceeded. Last error: {e}")

            return wrapper

        return decorator

    @retry_on_error()
    def wait_and_click(self, by, value, timeout=60):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
        except Exception as e:
            raise Exception(f"Error waiting and click: {value} | {e}")

    @retry_on_error()
    def wait_several_elements_and_click(self, by, value, count_of_element, timeout=20):
        try:
            wait = WebDriverWait(self.driver, timeout)
            wait.until(EC.presence_of_all_elements_located((by, value)))

            buttons = self.driver.find_elements(by, value)

            buttons[count_of_element].click()
        except Exception as e:
            raise Exception(f"Error waiting and click: {value} | {e}")

    @retry_on_error()
    def wait_and_fill(self, by, value, data, timeout=20):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.send_keys(data)
        except Exception as e:
            raise Exception(f"Error waiting and fill: {data} | {e}")

    @retry_on_error()
    def wait_and_clear(self, by, value, timeout=20):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.clear()
        except Exception as e:
            raise Exception(f"Error waiting and clear :| {e}")

    @retry_on_error()
    def wait_and_select(self, by, value, data, timeout=20):
        replace_ = data.replace("'", "\'").replace('"', '\"')
        option_xpath = f"//mat-option[contains(., '{replace_}')]"
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            element.click()
            option_element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, option_xpath))
            )
            option_element.click()

        except Exception as e:
            try:
                option_element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, f"//mat-option[contains(., '{replace_[len(replace_) // 2:]}')]"))
                )
                option_element.click()
            except Exception as e:
                raise Exception(f"Error waiting and select: {data} | {e}")

    @retry_on_error()
    def wait_for_overlay_to_disappear(self, timeout=180):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "cdk-overlay-backdrop"))
            )
        except Exception as e:
            raise Exception(f"Error waiting for overlay to disappear: {e}")

    @retry_on_error()
    def wait_and_select_for_six_page(self, by, value, data, timeout=20):
        try:
            self.wait_for_overlay_to_disappear()

            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()

            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.DOWN)
            time.sleep(1)
            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.DOWN)

            option_xpath = f"//mat-option[contains(., '{data}')]"
            option_element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            )
            option_element.click()
        except Exception as e:
            raise Exception(f"Error waiting and select: {data} | {e}")

    @retry_on_error()
    def wait_write_enter(self, by, value, data, timeout=20):
        time.sleep(2)
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            element.click()
            element.send_keys(Keys.ENTER)
            time.sleep(1)
            numbers = re.findall(r'\d+', data)
            numbers = [int(number) for number in numbers]
            for char in numbers:
                element.send_keys(char)
                time.sleep(0.1)
            element.send_keys(Keys.DOWN)
            element.send_keys(Keys.ENTER)
        except Exception as e:
            raise Exception(f"Error waiting and select: {data} | {e}")

    @retry_on_error()
    def get_files_with_full_paths(self, name_of_folder):

        directory_path = f'{self.base_dir}/{name_of_folder}'
        try:
            folders_with_full_paths = {}
            items = os.listdir(directory_path)
            for item in items:
                item_full_path = os.path.join(directory_path, item)
                if os.path.isfile(item_full_path):
                    folders_with_full_paths[item] = item_full_path
            return folders_with_full_paths
        except Exception as e:
            raise Exception(f"Ошибка при получении списка папок: {e}")

    def _parse_date_for_calendar(self, date):
        timestamp = pd.Timestamp(date)
        year = timestamp.year
        month = timestamp.strftime('%b')
        day = timestamp.day

        return year, month.upper(), day

    def work_with_calendar(self, by, value, date=None, timeout=20):
        element = WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
        element.click()
        year, month, day = self._parse_date_for_calendar(date)
        month_year_element = WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, f'//button[@aria-label="Choose month and year"]'))
        )
        month_year_element.click()

        year_element = WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, f'//div[contains(text(), "{year}")]'))
        )
        year_element.click()

        month_element = WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, f'//div[contains(text(), "{month}")]'))
        )
        month_element.click()

        day_element = WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, f'//div[contains(text(), "{day}")]'))
        )
        day_element.click()

    @retry_on_error()
    def wait_and_upload_file_by_path(self, by, value, path, timeout=20):
        self.wait_for_overlay_to_disappear()
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.click()
            time.sleep(2)

            file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            file_input.send_keys(path)
            time.sleep(3)
            pyautogui.press('esc')
        except Exception as e:
            raise Exception(f"Error waiting and upload file: {value} | {e}")

    def wait_url(self, url):
        try:
            wait = WebDriverWait(self.driver, 120)
            wait.until(EC.url_to_be(url))
        except TimeoutException:
            raise TimeoutException(f'Error waiting url {url}')

    def wait_url_without_id(self, data, url_pattern="https://cabinet.sud.uz/cases/create/civil/receipt/"):
        def check_url(driver):
            return url_pattern in driver.current_url

        try:
            wait = WebDriverWait(self.driver, 30)
            wait.until(check_url)
        except TimeoutException:
            raise TimeoutException(f'Error waiting for URL: {url_pattern}')

    @staticmethod
    def is_exist_token():
        return os.path.exists('token.pkl')

    def save_token(self):
        self.token = self.driver.execute_script('return sessionStorage.getItem("X-AUTH-TOKEN");')
        with open('token.pkl', 'wb') as token_file:
            pickle.dump(self.token, token_file)

    def load_token(self):
        if FillingEcourtBot.is_exist_token():
            with open('token.pkl', 'rb') as token_file:
                token = pickle.load(token_file)
                return token
    #     return None

    def is_logged_in(self):
        # Проверка, залогинен ли пользователь
        self.wait_url("https://cabinet.sud.uz/home")
        try:
            self.driver.find_element(By.XPATH, "//mat-icon[@data-mat-icon-name='logout']")
            return True
        except NoSuchElementException:
            return False

    def login(self):
        self.token = self.load_token()

        self.driver.get("https://cabinet.sud.uz/")

        if self.token:
            script = f'sessionStorage.setItem("X-AUTH-TOKEN", "{self.token}");'
            self.driver.execute_script(script)
            time.sleep(2)
            if self.is_logged_in():
                logger.info('Logged in successfully using saved token')
                return

        if self.is_logged_in():
            logger.info('Logged in successfully')
            self.save_token()
        else:
            logger.info('Login failed')
            self.close()


    def execute_with_timeout(self, func, timeout, *args, **kwargs):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                result = future.result(timeout=timeout)
                return result
            except concurrent.futures.TimeoutError:
                logger.error(f"Function {func.__name__} timed out. Retrying...")
                future.cancel()
                return self.execute_with_timeout(func, timeout, *args, **kwargs)

    def wait_choose_option_and_upload_file(self, value_option, data, v):
        self.wait_and_select_for_six_page(By.CSS_SELECTOR, value_option,
                                          data)
        self.wait_and_upload_file_by_path(By.XPATH,
                                          '//legend[text()="Arizaga ilova qilinadigan hujjatlar"]/following::span[contains(text(), "Yuklash")]',
                                          v)

    def filling_first_page(self):
        self.driver.get('https://cabinet.sud.uz/cases/create')
        self.wait_and_click(By.ID, "mat-radio-3")
        self.wait_and_click(By.ID, "mat-button-toggle-1-button")
        self.wait_and_select(By.ID, "mat-select-value-1", "Buyruq tartibida")
        self.wait_and_click(By.CLASS_NAME, "mat-flat-button")

    def filling_second_page(self, region_court, court_name, plaintiff_name, bank_creditor_inn, court_region_add, court_name_add, court_address_add):
        self.wait_write_enter(By.XPATH, "//input[@placeholder='Viloyat']", region_court)
        self.wait_write_enter(By.XPATH, "//input[@placeholder='Sud nomi']", court_name)
        self.wait_and_select(By.ID, "mat-select-value-3", plaintiff_name)
        if plaintiff_name == '"ANOR BANK" AKSIYADORLIK JAMIYATI':
            time.sleep(2)
            self.wait_and_select(By.XPATH, '//span[contains(@class, "mat-select-placeholder") and contains(text(), "Viloyat (shahar yoki tuman)")]', court_region_add)
            time.sleep(2)
            self.wait_and_select(By.XPATH, '//span[contains(@class, "mat-select-placeholder") and contains(text(), "Tuman nomi")]', court_name_add)
            time.sleep(2)
            self.wait_and_clear(By.XPATH, "//input[@placeholder='Manzili']")
            self.wait_and_fill(By.XPATH, "//input[@placeholder='Manzili']", court_address_add)
            time.sleep(2)
        self.wait_and_click(By.CLASS_NAME, 'bg-success')
        self.wait_and_click(By.XPATH, '//span[contains(text(), "Yuridik shaxs")]')
        self.wait_and_fill(By.XPATH, "//input[@placeholder='12345678910']", bank_creditor_inn)
        self.wait_and_click(By.XPATH, '//span[contains(text(), " Keyingi ")]')

    def filling_third_page(self, claim_number, claim_date, main_debt_amount, penalty, fines):
        self.wait_and_fill(By.XPATH, '//input[@placeholder="Raqam"]', claim_number)
        self.work_with_calendar(By.XPATH, '//input[@placeholder="Choose a date"]', date=claim_date)
        time.sleep(4)
        self.wait_and_select(By.XPATH, f'//span[contains(@class, "mat-select-placeholder") and contains(text(), "Asosiy ish turkumi")]',
                             '111 - ёзма битимга асосланган ва қарздор томонидан тан олинган талаб')
        time.sleep(2)
        self.wait_and_select(By.XPATH, f'//span[contains(@class, "mat-select-placeholder") and contains(text(), "Qo`shimcha")]',
                             '111.2 - майда ва маиший кредит тўловларни ундириш ҳақидаги талаб')
        self.wait_several_elements_and_click(By.XPATH, '//span[contains(text(), "Qo`shish")]', 1)
        self.wait_and_fill(By.XPATH, '//input[@placeholder="Asosiy qarz"]', int(main_debt_amount))
        self.wait_and_fill(By.XPATH, '//input[@placeholder="Penya"]', penalty)
        self.wait_and_fill(By.XPATH, '//input[@placeholder="Jarima"]', fines)
        time.sleep(2)
        self.wait_and_click(By.XPATH, '//span[contains(text(), " Keyingi ")]')

    def filling_fourth_page(self, debtors_pinfl):
        self.wait_and_click(By.XPATH, '//span[text()="Jismoniy shaxs"]')
        self.wait_and_fill(By.XPATH, '//input[@placeholder="12345678910"]', debtors_pinfl)
        self.wait_and_click(By.XPATH, '//span[contains(text(), "Qidirish")]')
        time.sleep(4)
        self.wait_and_click(By.XPATH, '//span[contains(text(), "Qo`shish")]')
        self.wait_and_click(By.XPATH, '//span[contains(text(), " Keyingi ")]')

    def filling_fifth_page(self, court_expenses_receipt_number, county_expenses_receipt_number):
        time.sleep(2)
        self.wait_and_select(By.XPATH, '//span[contains(@class, "mat-select-placeholder") and contains(text(), "Menda imtiyoz mavjud emas")]','Менда имтиёз мавжуд эмас')
        self.wait_and_click(By.XPATH, '//div[contains(@class, "bg-success")]/mat-icon[@svgicon="heroicons_outline:plus"]')
        self.wait_and_fill(By.CSS_SELECTOR, 'input[placeholder="Raqamni kiriting"]', court_expenses_receipt_number)
        self.wait_and_click(By.XPATH, '//span[text()="Kvitantsiya qo`shish"]')
        time.sleep(3)
        self.wait_and_fill(By.CSS_SELECTOR, 'input[placeholder="Raqamni kiriting"]', county_expenses_receipt_number)
        time.sleep(1)
        self.wait_and_click(By.XPATH, '//span[text()="Kvitantsiya qo`shish"]')
        time.sleep(5)
        self.wait_and_click(By.XPATH, '//span[contains(text(), " Keyingi ")]')

    def filling_sixth_page(self, debtors_pinfl):
        dict_files = self.get_files_with_full_paths(debtors_pinfl)
        key_to_delete = []
        for k, v in dict_files.items():
            if 'davo' in k.lower():
                self.wait_and_upload_file_by_path(By.XPATH, '//p[contains(text(), "Fayl yuklash")]', v)
                time.sleep(5)
                key_to_delete.append(k)
            elif 'pr' in k.lower():
                self.execute_with_timeout(self.wait_choose_option_and_upload_file, 30,
                                          'mat-select.select',
                                          ' 4 -  Почта харажати тўланганлиги тўғрисида маълумотнома ',
                                          v)

                time.sleep(4)
                key_to_delete.append(k)
            elif 'db' in k.lower():
                self.execute_with_timeout(self.wait_choose_option_and_upload_file, 30,
                                          'mat-select.select',
                                          ' 3 -  Давлат божи тўланганлиги тўғрисида маълумотнома ',
                                          v)

                key_to_delete.append(k)

        for k in key_to_delete:
            del dict_files[k]

        for k, v in dict_files.items():
            self.execute_with_timeout(self.wait_choose_option_and_upload_file, 30,
                                      'mat-select.select',
                                      ' 9 -  Бошқа ҳужжатлар ',
                                      v)
            time.sleep(3)
        time.sleep(3)
        self.wait_and_click(By.XPATH, '//span[contains(text(), " Keyingi ")]')

    def filling_seventh_page(self):
        time.sleep(2)
        # self.wait_and_click(By.XPATH, '//span[contains(text(), "Murojaat yaratish")]')
        self.wait_several_elements_and_click(By.XPATH,
                                             '//span[contains(text(), "Murojaat yaratish")]',
                                             1)
        time.sleep(3)

    def finish_case(self):
        time.sleep(2)
        self.wait_and_click(By.XPATH, '//span[text()="Sudga yuborish"]')
        time.sleep(3)

    def close(self):
        self.driver.quit()

    def process(self):
        for k, data in self.data_list.items():
            try:
                debtors_pinfl = data['debtors_pinfl']
                self.filling_first_page()
                self.filling_second_page(data['region_court'][0:4], data['court_name'][0:4], data['plaintiff_name'], data['bank_creditor_inn'],
                                         data['court_region_add'], data['court_name_add'], data['court_address_add'])
                self.filling_third_page(data['claim_number'], data['claim_date'], data['main_debt_amount'], data['penalty'], data['fines'])
                self.filling_fourth_page(debtors_pinfl)
                self.filling_fifth_page(data['court_expenses_receipt_number'], data['county_expenses_receipt_number'])
                self.filling_sixth_page(debtors_pinfl)
                self.filling_seventh_page()
                # time.sleep(3)
                # self.wait_url_without_id(data)
                self.finish_case()
                UpdateDebtorStatus([data], self.user_id).update_status_in_db()
            except NoSuchWindowException as e:
                logger.error(f'An error occurred: {e}')
                print('Окно браузера закрыто, невозможность продолжать заполнение е-суда.')
                break
            except Exception as e:
                logger.error(f'An error occurred: {e}')
                print('Непредвиденная ошибка с заполнением е-суда.')
                self.problem_rows.append(data)
                continue


def run(user_id):
    try:
        data_for_automation = GetDataDBDebtors(user_id).get_data_from_db_to_filling_debtors()
        if not data_for_automation:
            print('[INFO]: Нет доступных данных для заполнения е-суда.')
            return

        automation = FillingEcourtBot(data_for_automation, user_id)
        automation.login()
        automation.process()
        automation.write_problem_dicts_to_excel()
        automation.close()
    except Exception as e:
        print(f'[ERROR]: Обнаружены проблемы с заполнением е-суда.')
        logger.error(f'An error occurred: {e}')
