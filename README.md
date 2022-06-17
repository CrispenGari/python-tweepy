## tweetpy

This is a python package that help us to interact with twitter and python in data mining.

### Hello tweetpy

```python
import tweepy

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

public_tweets = api.home_timeline()
for tweet in public_tweets:
    print(tweet.text)
```

### Getting keys:

1. Go to [Twitter For Developers](https://developer.twitter.com/en/portal/apps/)
2. Create an app
3. After the application has been created go to the `keys and tokens` tab.
4. Under consumer keys you will find ``API_KEY == consumer_key ` and `API_SECRET == consumer_secret`
5. Authentication Tokens you will find `ACCESS_TOKEN` and `ACCESS_TOKEN_SECRET`
6. Then you are ready to go.

### Documentation Reference.

- [tweetpy](https://docs.tweepy.org/en/latest/getting_started.html)
