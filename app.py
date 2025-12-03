# server
from flask import Flask, render_template

app = Flask(__name__)

# Route principale
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Le debug=True permet de voir les erreurs en direct
    app.run(debug=True, port=5000)