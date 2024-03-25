from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        # Extract form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
    return render_template('register.html')

@app.route('/report', methods=['POST', 'GET'])
def report():
    if request.method=='POST':
        item_name = request.form.get('item_name')
    return render_template('report.html')

if __name__ == '__main__':
    app.run(debug=True)