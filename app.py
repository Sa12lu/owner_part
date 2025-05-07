from flask import Flask

app = Flask(__name__)
app.secret_key = 'your_secret_key'

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=5002, debug=True)