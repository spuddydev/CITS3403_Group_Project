import unittest
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from app import create_app  # Make sure this function exists in your app

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    DEBUG = False

class SeleniumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # ✅ Create Flask app from factory
        cls.app = create_app(TestConfig)

        # ✅ Start Flask app in background thread (with reloader and debug disabled)
        cls.app_thread = threading.Thread(
            target=cls.app.run,
            kwargs={'port': 5002, 'use_reloader': False, 'debug': False}
        )
        cls.app_thread.setDaemon(True)
        cls.app_thread.start()
        time.sleep(1.5)  # Give Flask time to start

        # ✅ Setup Selenium WebDriver with headless Chrome
        options = Options()
        options.add_argument("--headless")
        cls.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        cls.base_url = "http://localhost:5002/"

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        # Flask dev server will exit when the main thread exits

    def check_page_loads(self, path):
        self.driver.get(self.base_url + path)
        page_source = self.driver.page_source.lower()
        self.assertIn("html", page_source)
        self.assertNotIn("error", page_source)  # Basic sanity check

    def test_homepage_loads(self):
        self.check_page_loads("home")

    def test_settings_page_loads(self):
        self.check_page_loads("settings")

    def test_upload_page_loads(self):
        self.check_page_loads("upload")

    def test_trends_page_loads(self):
        self.check_page_loads("trends")

    def test_register_page_loads(self):
        self.check_page_loads("register")

    def test_profile_page_loads(self):
        self.check_page_loads("profile")

    def test_dashboard_page_loads(self):
        self.check_page_loads("dashboard")

    def test_login_page_loads(self):
        self.check_page_loads("login")
class FlaskAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)

    def setUp(self):
        self.app = self.__class__.app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_home_redirect(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/home', resp.location)

    def test_home_page(self):
        resp = self.client.get('/home')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'html', resp.data.lower())

    def test_login_get(self):
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'login', resp.data.lower())

    def test_login_post_invalid(self):
        resp = self.client.post('/login', data={'username': 'nouser', 'password': 'bad'}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'invalid', resp.data.lower())

    def test_register_get(self):
        resp = self.client.get('/register')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'register', resp.data.lower())

    def test_dashboard_requires_login(self):
        resp = self.client.get('/dashboard')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.location)

    def test_profile_requires_login(self):
        resp = self.client.get('/profile')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.location)

    def test_autocomplete_interests(self):
        resp = self.client.get('/autocomplete_interests?q=test')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'[', resp.data)
if __name__ == '__main__':
    unittest.main()
