from flask import Flask, render_template, request
app = Flask(__name__)

import dal

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/go', methods=['POST'])
def go():
    r = dal.makereq(request.form['fname'], request.form['lname'], request.form['pnr'])
    if r.status_code != 200:
        return render_template('error.html')

    data = dal.decode(r.json())

    return render_template('show.html', data=data)

if __name__ == '__main__':
    app.run()