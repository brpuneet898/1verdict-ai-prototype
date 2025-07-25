from flask import Flask
from routes import main
from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdb.sqlite3'
app.config['SECRET_KEY'] = 'your_secret_key'
db.init_app(app)
app.register_blueprint(main)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)