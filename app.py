import os
from flask import Flask
from routes import main
from models import db
import google.generativeai as genai
import yaml


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdb.sqlite3'
app.config['SECRET_KEY'] = 'your_secret_key'
db.init_app(app)
app.register_blueprint(main)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

with open("key.yaml", "r") as f:
    config = yaml.safe_load(f)
GEMINI_API_KEY = config.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set!")
genai.configure(api_key=GEMINI_API_KEY)

app.llm = genai.GenerativeModel('gemini-2.5-flash')

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)