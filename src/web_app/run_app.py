from datetime import datetime
from flask import Flask, render_template, url_for, flash, redirect, request 
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent.resolve() # src
sys.path.append(str(parent_dir))
from web_app.forms import DeployAgent_form , MakeTweet_form
from Database.database_creator import Twitter_DB
from utils.functions import create_embedding_bytes, tweet_to_dict
from Agents.game import Agent_Manager
import threading

def start_app (from_scratch: bool, reset: bool):
    print(from_scratch)
    app = Flask(__name__)
    app.config['SECRET_KEY'] = "very_secret_key"

    twitter_db = Twitter_DB(from_scratch, reset)
    agent_manager = Agent_Manager(twitter_db)

    user_search_size = 100

    def fetch_feed():# most recent tweets or searched tweets
        unfomatted_tweets = twitter_db.get_feed(user_search_size, False, None)
        # Format the fetched tweets
        latest_tweets = [tweet_to_dict(tweet) for tweet in unfomatted_tweets]
        return latest_tweets

    def search_feed(search: str):# most recent tweets or searched tweets
        unfomatted_tweets = twitter_db.search_db(search, user_search_size)
        print("SEARCH FEED FUNCTION", unfomatted_tweets)
        if unfomatted_tweets is None:
            flash("Error occurred during search: you need to setup cohere.ai api key", "error")
            return [] 
        search_tweets = [tweet_to_dict(tweet) for tweet in unfomatted_tweets]
        return search_tweets

    ### ROUTES
    feed=fetch_feed()
    @app.route("/", methods=["GET", "POST"])
    def home():
        status = 'Paused' if agent_manager._paused else 'Running'
        pause_unpause = 'Unpause' if agent_manager._paused else 'Pause'
        running = not agent_manager._paused 
        agents = agent_manager.collect_agents()
        flash_msg = 'most recent'
        feed = fetch_feed()
        if request.method == "POST":
            search = request.form.get("search")
            if search == "":
                flash_msg ='most recent'
                feed = fetch_feed()
            else:
                flash_msg = f'Search results for: {search}'
                feed = search_feed(search)
        flash(flash_msg)
        return render_template("home.html", feed=feed, agents=agents, status=status, pause_unpause=pause_unpause, running=running)

    @app.route('/toggle_pause', methods=['POST'])
    def toggle_pause():
        if agent_manager.agents:
            simulation = threading.Thread(target=agent_manager.pause_unpause)
            simulation.start()
        return redirect(url_for("home"))

    
    @app.route('/agents/<agent_name>')
    def agent_details(agent_name):
        agent_reflections=agent_manager.get_agent_memory(agent_name)
        return render_template('agent_details.html', reflections = agent_reflections, title=agent_name, )

    @app.route("/about")
    def about():
        return render_template("about.html", title = "about")

    @app.route("/deploy", methods=["GET", "POST"])
    def deploy():
        form = DeployAgent_form()
        if form.validate_on_submit():
            name = form.name.data
            agent_names = [agent._name for agent in agent_manager.agents]
            if name not in agent_names:
                description = form.description.data
                agent_manager.add_agent(name, description)
                flash(f'deployed agent: {name}!', "success")
                return redirect(url_for("home"))
            else:
                flash("Failed: agent with this name already exists")
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
            Tuple = (content, create_embedding_bytes(content), name, like_count, retweet_count, date)
            twitter_db.insert_tweet(Tuple) #inset into database, needs embeddings.
            flash("Tweet sent", "success")
            return redirect(url_for("home"))
        return render_template("tweet.html", title="Make Tweet", form = form)

    app.run(debug=True)
