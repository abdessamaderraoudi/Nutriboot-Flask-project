from flask import Flask, render_template, request, jsonify
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_pymongo import PyMongo
from datetime import datetime
from bson.objectid import ObjectId
import bcrypt
import socket
from flask import session
from openai import OpenAI  

app = Flask(__name__)
app.config.from_pyfile('config.py')

client = OpenAI(api_key=app.config['OPENAI_API_KEY'])
mongo = PyMongo(app)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en nutrition sportive."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content
        return jsonify({'reply': reply})
    except Exception as e:
        print(f"Erreur OpenAI : {e}")
        return jsonify({'reply': "Erreur lors de la communication avec le LLM."})





@app.route('/')
def index():
    return render_template('index.html')



# Inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        utilisateur = {
            "nom": nom,
            "prenom": prenom,
            "email": email,
            "mot_de_passe_hache": hashed_pw,
            "date_inscription": datetime.now()
        }

        mongo.db.utilisateurs.insert_one(utilisateur)
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        utilisateur = mongo.db.utilisateurs.find_one({'email': email})

        if utilisateur and bcrypt.checkpw(password.encode('utf-8'), utilisateur['mot_de_passe_hache']):
            session['user_id'] = str(utilisateur['_id'])

            mongo.db.sessions.insert_one({
                "utilisateur_id": utilisateur['_id'],
                "date_connexion": datetime.now(),
                "adresse_ip": request.remote_addr
            })

            return redirect(url_for('dashboard'))

    return render_template('login.html')



@app.route('/logout')
def logout():
    if 'user_id' in session:
        utilisateur_id = ObjectId(session['user_id'])

        # mise à jour de la dernière session
        last_session = mongo.db.sessions.find_one(
            {"utilisateur_id": utilisateur_id},
            sort=[('date_connexion', -1)]
        )

        if last_session and 'date_deconnexion' not in last_session:
            mongo.db.sessions.update_one(
                {'_id': last_session['_id']},
                {'$set': {'date_deconnexion': datetime.now()}}
            )

        session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    utilisateur_id = ObjectId(session['user_id'])
    utilisateur = mongo.db.utilisateurs.find_one({'_id': utilisateur_id})
    sessions = list(mongo.db.sessions.find({'utilisateur_id': utilisateur_id}))

    return render_template('dashboard.html', utilisateur=utilisateur, sessions=sessions)

