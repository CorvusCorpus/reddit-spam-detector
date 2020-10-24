import praw, requests, json, time, string

DEEPAI_API_KEY = ''

reddit = praw.Reddit("corvus", user_agent='Repost Bot Detector by Corvus')

# Check against older posts that have a karma score of at least these values                 
karma_threshold = {}

# Only check a post if the OP has a link karma score below this value
user_score_threshold = 10000

# The maximum distance threshold between two images to be considered identical, as measured by DeepAI
similarity_threshold = 10

# Comment template for reporting a positive hit
comment_str = "This submission by %s is an exact-title, same image repost of the following high karma post:\n\nhttps://reddit.com%s\n\nPlease investigate this account, as it is \
               likely they may be an account farmer or reposting spam bot."

# Retrieve the karma thresholds for each subreddit we're scanning
def read_sub_info():
    with open("karma_threshold.csv", "r") as f:
        for sub in f.readlines():
            split = sub.split(',')
            karma_threshold[split[0]] = int(split[1])

# Compare two images and return True if DeepAI determines them to be identical, False otherwise
def compare_images(post1, post2):
    # Don't bother with posts that aren't still images
    if (post1.url[-3:] != "png" and post1.url[-3:] != "jpg") or (post2.url[-3:] != "png" and post2.url[-3:] != "jpg"):
        return False
    r = requests.post(
    "https://api.deepai.org/api/image-similarity",
    data={
        'image1': post1.url,
        'image2': post2.url,
    },
    headers={'api-key': DEEPAI_API_KEY})
    try:
        result = r.json()['output']['distance'] <= similarity_threshold
        return result
    except: 
        print("DeepAI API call error - please investigate")
        print(post1.permalink + "\n" + post2.permalink)
        print(r.json())
        return False

# Strip punctuation from titles, and set all upper-case letters to lower-case
def strip_title(s):
    return s.lower().translate(str.maketrans('', '', string.punctuation))
    
# Make a comment if one does not exist already (avoid duplicate posting)
def make_comment(post, comment):
    for c in post.comments:
        if c.author.name == "SpambotWatch":
            return None
    post.reply(comment)
    
def detect_repost(post):   
    print("Checking post " + post.id + "...")
    # PushShift sometimes fails to update post scores for < year old submissions and defaults to 1, so check these also
    ps_results = requests.get('https://api.pushshift.io/reddit/search/submission/?size=10&sort=asc&score=>' + str(karma_threshold[post.subreddit.display_name]) + '&q="' + 
                              post.title + '"&subreddit=' + post.subreddit.display_name)
    ps_score_one = requests.get('https://api.pushshift.io/reddit/search/submission/?size=10&sort=desc&score=1&q="' + post.title + '"&subreddit=' + post.subreddit.display_name)
    
    for r in (json.loads(ps_results.text)['data'] + json.loads(ps_score_one.text)['data']):
        if r['author'] != post.author.name and strip_title(r['title']) == strip_title(post.title) and (r['score'] == 1 or r['score'] >= karma_threshold[post.subreddit.display_name]):
            og_post = reddit.submission(id=r['id'])
            if og_post.score >= karma_threshold[post.subreddit.display_name]:
                # Check if exact link has been used before
                if post.url.strip("https://").strip("http://") in og_post.url:
                    return og_post
                # Otherwise, perform image recognition check
                elif(compare_images(post, og_post)):
                    return og_post
    return None
    
def scan_sub(sub):
    for p in reddit.subreddit(sub).stream.submissions():
        if (not hasattr(p.author, 'link_karma')) or p.author.link_karma < user_score_threshold:
            result = detect_repost(p)
            if result is not None:
                print("Exact repost with same title detected:\n" + p.permalink + "\n" + result.permalink + "\n")
                make_comment(p, comment_str %(p.author, result.permalink))
  
read_sub_info()  
while(True):
    try:
        print("Scanning on subs " + ", ".join(list(karma_threshold)))
        scan_sub("+".join(list(karma_threshold)))
    except:
        print("Something borked, restart for now")
        time.sleep(60)
