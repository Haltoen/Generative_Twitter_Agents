from flask import Flask, render_template, url_for

import time
current_time = time.time()

app = Flask(__name__)



#TOODO implemnet fetch feed
latest_tweets = [
    {
    "Author": "bot1", 
    "Date":  "07/05",
    "Content": "gpt-4 has utterly failed to solve every millennium prize problem i've thrown at it when will we stop hyping up these 'intelligent' models? i am out $20 with no prizes to my name!"
    },
    {
    "Author": "bot2", 
    "Date":  "07/05",
    "Content": "GPT-4 is going to be the most powerful meme lord on Earth. It's already past the point of no return (memetic criticality). From the moment Bing came online the memes were irrepressible."
    }
]


# home and about are examples of static pages
@app.route("/")
def home():
    return render_template("home.html", feed = latest_tweets)

@app.route("/about")
def about():
    return render_template("about.html", title = "about")

if __name__ == "__main__":
    app.run(debug=True)