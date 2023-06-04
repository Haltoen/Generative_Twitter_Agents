from datetime import datetime
from flask import Flask, render_template, url_for, flash, redirect, g, request 
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.resolve() # src
sys.path.append(str(parent_dir))

from forms import DeployAgent_form , MakeTweet_form, SearchBar_form
from Database.database_creator import Twitter_DB

app = Flask(__name__)
app.config['SECRET_KEY'] = "very_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

twitter_db = Twitter_DB("twitter_db", True)

user_is_searching = False
user_search_size = 20

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = twitter_db
    return db

@app.teardown_appcontext    
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def fetch_feed():# most recent tweets or searched tweets
    unfomatted_tweets = twitter_db.get_feed(20)
    # Format the fetched tweets
    latest_tweets = [
        {
            "Author": tweet[1][1], 
            "Date": tweet[1][4], 
            "Content": tweet[1][0]  
        }
        for tweet in unfomatted_tweets
    ]
    return latest_tweets

def search_feed(search: str):# most recent tweets or searched tweets
    unfomatted_tweets = twitter_db.search_db(search, user_search_size)
    # Format the fetched tweets
    if unfomatted_tweets is None:
        flash("Error occurred during search: you need to setup cohere.ai api key", "error")
        return [] 
    latest_tweets = [
        {
            "Author": tweet[1][1], 
            "Date": tweet[1][4], 
            "Content": tweet[1][0]  
        }   
        for tweet in unfomatted_tweets
    ]
    return latest_tweets

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        search = request.form.get("search")
        if search == "":
            flash('most recent')
            return render_template("home.html", feed=fetch_feed())
        else:
            flash(f'Search results for: {search}')
            return render_template("home.html", feed=search_feed(search))
    return render_template("home.html", feed=fetch_feed())
    
@app.route("/about")
def about():
    return render_template("about.html", title = "about")

@app.route("/deploy", methods=["GET", "POST"])
def deploy():
    form = DeployAgent_form()
    if form.validate_on_submit():
        name = form.name.data
        flash(f'deployed agent: {name}!', "succes")
        return redirect(url_for("home"))
    return render_template("deploy.html", title="deploy agent", form = form)

@app.route("/tweet", methods=["GET", "POST"])
def tweet():
    form = MakeTweet_form()
    if form.validate_on_submit():
        content = form.content.data
        name = form.name.data
        like_count = 0
        retweet_count = 0
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        twitter_db.insert_tweet((content, " ", name, like_count, retweet_count, date)) #inset into database, needs embeddings.
        flash("Tweet sent", "success")
        return redirect(url_for("home"))
    return render_template("tweet.html", title="Make Tweet", form=form)

if __name__ == "__main__":
    app.run(debug=True)