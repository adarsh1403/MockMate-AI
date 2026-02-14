from flask import Flask, render_template, redirect, url_for, request, flash,session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Interview
from config import Config
from ai_utils import generate_questions, evaluate_answers
import logging
from logging.handlers import RotatingFileHandler
import os


app = Flask(__name__)
app.config.from_object(Config)

# Configure Logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/ai_interview.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('AI Interview startup')
else:
    # In debug mode, log to console as well but still setup basic config for uniformity if needed
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)


db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        # Input validation
        if not name or len(name) < 2:
            flash("Name must be at least 2 characters")
            return redirect(url_for("register"))
        
        if len(name) > 150:
            flash("Name is too long")
            return redirect(url_for("register"))
        
        if not email or "@" not in email:
            flash("Please enter a valid email address")
            return redirect(url_for("register"))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters")
            return redirect(url_for("register"))
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash("Email already exists")
            return redirect(url_for("register"))
        
        try:
            # Create new user
            new_user = User(name=name, email=email)
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash("Account created successfully! Please log in.")
            return redirect(url_for("login"))
        
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {e}", exc_info=True)
            flash("An error occurred. Please try again.")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password")

    return render_template("login.html")


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":

        # Clear any previous interview session
        session.pop("questions", None)
        session.pop("current_index", None)
        session.pop("qa_log", None)

        # Store new configuration
        session["field"] = request.form.get("field")
        session["difficulty"] = request.form.get("difficulty")

        return redirect(url_for("interview"))


    return render_template("dashboard.html", user=current_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))





@app.route("/interview", methods=["GET", "POST"])
@login_required
def interview():

    field = session.get("field")
    difficulty = session.get("difficulty")

    if not field or not difficulty:
        return redirect(url_for("dashboard"))

    # First load → Generate Questions
    if "questions" not in session:
        questions = generate_questions(field, difficulty)
        session["questions"] = questions
        session["current_index"] = 0
        session["qa_log"] = []

    questions = session.get("questions")
    current_index = session.get("current_index", 0)


    # User submitted answer
    if request.method == "POST":

        answer = request.form.get("response")

        # Save Q&A
        qa_log = session.get("qa_log", [])
        qa_log.append((questions[current_index], answer))
        session["qa_log"] = qa_log


        current_index = session.get("current_index", 0)
        current_index += 1
        session["current_index"] = current_index


        # If all 5 answered → evaluate
        if current_index >= len(questions):
            app.logger.debug(f"QA Log: {session.get('qa_log')}")

            evaluation = evaluate_answers(session["qa_log"])

            # Extract average score
            average_score = evaluation["score"]

            # Save to database
            try:
                new_interview = Interview(
                    user_id=current_user.id,
                    field=field,
                    difficulty=difficulty,
                    average_score=average_score
                )

                db.session.add(new_interview)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error saving interview: {e}", exc_info=True)
                # Continue to show results even if save fails

            # Clear interview session
            session.pop("questions", None)
            session.pop("current_index", None)
            session.pop("qa_log", None)
            app.logger.info(f"Evaluation complete: {evaluation}")
            return render_template("result.html", evaluation=evaluation)

    # Show current question
    return render_template(
        "interview.html",
        question=questions[current_index],
        step=current_index + 1,
        progress=int((current_index / len(questions)) * 100))


@app.route("/history")
@login_required
def history():
    interviews = Interview.query.filter_by(
        user_id=current_user.id
    ).order_by(Interview.timestamp.desc()).all()

    


    return render_template("history.html", interviews=interviews)

if __name__ == "__main__":
    app.run(debug=True)





